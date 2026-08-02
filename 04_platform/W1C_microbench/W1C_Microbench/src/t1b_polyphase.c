/*****************************************************************************
 * t1b_polyphase.c
 * T1b:多相抽取 48 kHz → 16 kHz(DEC=3),与 AEC 抽取器"同形"
 *
 * 参数依据:01_design/W1A_AFC_architecture_budget.md §4.7(3)——
 *   "抽取/内插滤波器规格由 TCLw 频段反推……⇒ ~101 tap、往返群延迟 2.06 ms,
 *    且不可与 AFC 旁链那只 72-tap 复用"。本内核取 101-tap 原型、DEC=3,
 *   即该处所指的 AEC 抽取器规格,而非 AFC 旁链的 72-tap 抽取器。
 *   系数为我方现场生成的 Hamming 窗 sinc 低通(截止 fs/6,Q15,DC 增益归一,
 *   见 decim_coef_q15_101.dat 生成脚本),**不是产品定版系数**——本内核只
 *   追求"101-tap Q15×Q31 环形多相卷积"这一算术形状与 MAC 计数,不追求
 *   通阻带指标;若 adaptive-dsp 后续定版系数改变,不影响这里的周期数量级。
 *
 * 算法实现依据(逐结构改写,非逐字复制):
 *   knowledge_base/adsp21569/platform_lessons/cces_template/src/fir.c
 *     的 polyphase_fir_decimate()/polyphase_fir_init()(Q15 系数 × Q31 状态,
 *     环形延迟线,标准 C,无 CCES 专有 API 依赖,风险最低)。
 *
 * 内存放置:
 *   L1 变体 = 默认放置(不加 pragma)。
 *   L2 变体 = coef/state/输入输出缓冲整体搬 L2(#pragma section("seg_l2"));
 *             本内核全部是普通 DM 数据,没有 T1a 那种 "pm" 总线限定符纠缠,
 *             是本项目里"整体搬 L2"风险最低的一个内核。
 *
 * 附加探针(t1b_write16_penalty_probe):直接回填 DEC-0014⑤ / W1A 文档 V-14——
 *   "L2 SRAM 有 ECC,任何 <32-bit 写 = 读改写 3 周期" 这条厂家文档断言
 *   ([L2/厂家 System Optimization Techniques]),目前 W1A 里挂的是**估算**
 *   (≈0.20%,且依赖"SYSCLK=CCLK/2"这个未核对的假设 [L4/待核 datasheet])。
 *   本内核的主体(101-tap 状态/系数)全是 32-bit(Q31/int32_t 或 16-bit 系数但
 *   按 32-bit 对齐访问),**不会真的踩中这条 <32-bit 写的惩罚**——为此专门
 *   加一段独立探针:对一段 int16_t(16-bit,真正 <32-bit)数组做连续写入,
 *   L1/L2 各测一次,直接测出这条惩罚是否成立、量级多少,而不是继续依赖估算。
 *
 * 全部数字在板上跑出之前 = [L4/未验证]。
 *****************************************************************************/
#include "w1c_config.h"

#if ENABLE_T1B_POLYPHASE

#include <stdio.h>
#include <string.h>
#include <time.h>
#include <stdint.h>
#include "t1b_polyphase.h"
#include "w1c_selfcheck.h"

#define T1B_NUM_TAPS   101
#define T1B_DECIM_M    3
/* 48kHz 下一个 64 样本产品帧对应的抽取调用次数(向上取整,含尾数余量) */
#define T1B_CALLS_PER_FRAME  ((64 + T1B_DECIM_M - 1) / T1B_DECIM_M)   /* = 22 */

typedef struct {
    const int16_t *coef;
    int32_t       *state;
    uint16_t       num_taps;
    uint16_t       decim_rate;
    uint16_t       state_idx;
} T1bPolyState;

static const int16_t t1b_coef[T1B_NUM_TAPS] = {
#include "decim_coef_q15_101.dat"
};

/* ---- L1 变体(默认放置) ---- */
static int32_t t1b_state_l1[T1B_NUM_TAPS];
static int32_t t1b_in_l1[T1B_DECIM_M];

/* ---- L2 变体 ---- */
#pragma section("seg_l2")
static int32_t t1b_state_l2[T1B_NUM_TAPS];
#pragma section("seg_l2")
static int32_t t1b_in_l2[T1B_DECIM_M];

/* ---- DEC-0014⑤/V-14 探针专用:真正的 <32-bit(16-bit)数据,L1/L2 各一份 ---- */
#define T1B_PROBE_N 256
static int16_t t1b_probe_l1[T1B_PROBE_N];
#pragma section("seg_l2")
static int16_t t1b_probe_l2[T1B_PROBE_N];

static void t1b_init(T1bPolyState *st, int32_t *state_buf)
{
    st->coef = t1b_coef;
    st->state = state_buf;
    st->num_taps = T1B_NUM_TAPS;
    st->decim_rate = T1B_DECIM_M;
    st->state_idx = 0;
    memset(state_buf, 0, (size_t)T1B_NUM_TAPS * sizeof(int32_t));
}

/* 每 M 个新样点 -> 1 个抽取输出(Q15 系数 x Q31 状态 -> Q46 累加 -> 右移15 回 Q31)。
 * 结构改写自 platform_lessons/cces_template/src/fir.c: polyphase_fir_decimate() */
static int32_t t1b_decimate(T1bPolyState *st, const int32_t *in)
{
    uint16_t M = st->decim_rate;
    uint16_t N = st->num_taps;
    uint16_t idx = st->state_idx;
    int64_t acc = 0;
    uint16_t i, k, rd;

    for (i = 0; i < M; i++) {
        st->state[idx] = in[i];
        idx = (uint16_t)((idx + 1u < N) ? (idx + 1u) : 0u);
    }
    st->state_idx = idx;

    for (k = 0; k < N; k++) {
        rd = (uint16_t)((idx + k < N) ? (idx + k) : (idx + k - N));
        acc += (int64_t)st->coef[k] * (int64_t)st->state[rd];
    }
    return (int32_t)(acc >> 15);
}

static void t1b_fill_input(int32_t *in, int seed)
{
    int i;
    for (i = 0; i < T1B_DECIM_M; i++) {
        in[i] = (int32_t)((seed + i) * 12345) & 0x00FFFFFF; /* 非平凡、非全零 */
    }
}

/* DEC-0014⑤/V-14 探针:连续写 T1B_PROBE_N 个 int16_t(真正 <32-bit),L1/L2 各一次。
 * 若厂家文档断言成立,L2 那一行的 cycles 应明显高于 L1(读改写 3 周期/次量级)。
 * 这是本文件里唯一"只测周期、不做多相卷积"的部分,独立于上面的抽取器逻辑。 */
static void t1b_write16_penalty_probe(FILE *fcsv)
{
    volatile clock_t t0, t1, cyc_l1, cyc_l2;
    int16_t chk16;
    int i;

    t0 = clock();
    for (i = 0; i < T1B_PROBE_N; i++) {
        t1b_probe_l1[i] = (int16_t)(i * 3 + 1);
    }
    t1 = clock();
    cyc_l1 = t1 - t0;
    chk16 = t1b_probe_l1[T1B_PROBE_N - 1];
    w1c_checksum_add(chk16);
    printf("T1B_write16_penalty,L1,N=%d,cycles=%d,checksum=%d\n",
           T1B_PROBE_N, (int)cyc_l1, (int)chk16);
    if (fcsv) fprintf(fcsv, "T1B_write16_penalty,L1,%d,%d,%d\n",
                       T1B_PROBE_N, (int)cyc_l1, (int)chk16);

    t0 = clock();
    for (i = 0; i < T1B_PROBE_N; i++) {
        t1b_probe_l2[i] = (int16_t)(i * 3 + 1);
    }
    t1 = clock();
    cyc_l2 = t1 - t0;
    chk16 = t1b_probe_l2[T1B_PROBE_N - 1];
    w1c_checksum_add(chk16);
    printf("T1B_write16_penalty,L2,N=%d,cycles=%d,checksum=%d\n",
           T1B_PROBE_N, (int)cyc_l2, (int)chk16);
    if (fcsv) fprintf(fcsv, "T1B_write16_penalty,L2,%d,%d,%d\n",
                       T1B_PROBE_N, (int)cyc_l2, (int)chk16);
}

void t1b_polyphase_run(FILE *fcsv)
{
    T1bPolyState st_l1, st_l2;
    volatile clock_t t0, t1, cyc_cold, cyc_warm_total, cyc_frame;
    int32_t out, chk;
    int i;

    printf("\n==== T1B: polyphase decimate 48k->16k (101-tap, DEC=3) ====\n");

    /* ---------------- L1 ---------------- */
    t1b_init(&st_l1, t1b_state_l1);
    t1b_fill_input(t1b_in_l1, 1);

    /* 冷:第一次调用(含首次取指/取数的 cache 冷启动效应) */
    t0 = clock();
    out = t1b_decimate(&st_l1, t1b_in_l1);
    t1 = clock();
    cyc_cold = t1 - t0;
    chk = out; w1c_checksum_add(chk);
    printf("T1B_polyphase,L1,cold_1call,cycles=%d,checksum=%d\n", (int)cyc_cold, (int)chk);
    if (fcsv) fprintf(fcsv, "T1B_polyphase,L1,cold_1call,%d,%d\n", (int)cyc_cold, (int)chk);

    /* 热:连续 W1C_WARM_REPEAT 次,整体计时后取平均(稳态吞吐,不含首次冷启动) */
    t0 = clock();
    for (i = 0; i < W1C_WARM_REPEAT; i++) {
        t1b_fill_input(t1b_in_l1, i);
        out = t1b_decimate(&st_l1, t1b_in_l1);
    }
    t1 = clock();
    cyc_warm_total = t1 - t0;
    chk = out; w1c_checksum_add(chk);
    printf("T1B_polyphase,L1,warm_avg_of_%d,cycles_total=%d,cycles_avg=%d,checksum=%d\n",
           W1C_WARM_REPEAT, (int)cyc_warm_total, (int)(cyc_warm_total / W1C_WARM_REPEAT), (int)chk);
    if (fcsv) fprintf(fcsv, "T1B_polyphase,L1,warm_avg_of_%d,%d,%d\n",
                       W1C_WARM_REPEAT, (int)cyc_warm_total, (int)chk);

    /* 每 64 样本产品帧摊销(22 次调用为一组,整体计时) */
    t0 = clock();
    for (i = 0; i < T1B_CALLS_PER_FRAME; i++) {
        t1b_fill_input(t1b_in_l1, i);
        out = t1b_decimate(&st_l1, t1b_in_l1);
    }
    t1 = clock();
    cyc_frame = t1 - t0;
    chk = out; w1c_checksum_add(chk);
    printf("T1B_polyphase,L1,per_frame_64smp_%dcalls,cycles=%d,checksum=%d\n",
           T1B_CALLS_PER_FRAME, (int)cyc_frame, (int)chk);
    if (fcsv) fprintf(fcsv, "T1B_polyphase,L1,per_frame_64smp_%dcalls,%d,%d\n",
                       T1B_CALLS_PER_FRAME, (int)cyc_frame, (int)chk);

    /* ---------------- L2 ---------------- */
    t1b_init(&st_l2, t1b_state_l2);
    t1b_fill_input(t1b_in_l2, 1);

    t0 = clock();
    out = t1b_decimate(&st_l2, t1b_in_l2);
    t1 = clock();
    cyc_cold = t1 - t0;
    chk = out; w1c_checksum_add(chk);
    printf("T1B_polyphase,L2,cold_1call,cycles=%d,checksum=%d\n", (int)cyc_cold, (int)chk);
    if (fcsv) fprintf(fcsv, "T1B_polyphase,L2,cold_1call,%d,%d\n", (int)cyc_cold, (int)chk);

    t0 = clock();
    for (i = 0; i < W1C_WARM_REPEAT; i++) {
        t1b_fill_input(t1b_in_l2, i);
        out = t1b_decimate(&st_l2, t1b_in_l2);
    }
    t1 = clock();
    cyc_warm_total = t1 - t0;
    chk = out; w1c_checksum_add(chk);
    printf("T1B_polyphase,L2,warm_avg_of_%d,cycles_total=%d,cycles_avg=%d,checksum=%d\n",
           W1C_WARM_REPEAT, (int)cyc_warm_total, (int)(cyc_warm_total / W1C_WARM_REPEAT), (int)chk);
    if (fcsv) fprintf(fcsv, "T1B_polyphase,L2,warm_avg_of_%d,%d,%d\n",
                       W1C_WARM_REPEAT, (int)cyc_warm_total, (int)chk);

    /* ---------------- DEC-0014⑤/V-14 16-bit 写惩罚探针 ---------------- */
    t1b_write16_penalty_probe(fcsv);
}

#else /* !ENABLE_T1B_POLYPHASE */

void t1b_polyphase_run(FILE *fcsv)
{
    printf("T1B_polyphase,DISABLED,-,-,-  (see w1c_config.h ENABLE_T1B_POLYPHASE)\n");
    if (fcsv) fprintf(fcsv, "T1B_polyphase,DISABLED,-,-,-\n");
}

#endif /* ENABLE_T1B_POLYPHASE */
