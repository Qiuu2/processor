/*****************************************************************************
 * t1a_biquad.c
 * T1a:8 级 biquad 链吞吐 —— DEC-0009/DEC-0014 的 T1(规整短环)主口径点
 *
 * 依据(逐字照搬调用方式,未改算法):
 *   knowledge_base/adsp21569/bsp/app_notes/fira_accel_code/EE408V02/
 *     ADSP_2156x_IIR_Core_Performance/src/IIR_Core_Throughput_21569.c
 *   (ADI 官方 EE-408 Rev2 附带工程;biquad() 声明于 <filter.h>,
 *    参数顺序 = (input*, output*, coeffs*, state*, window, biquads) 直接抄自该文件的
 *    实际调用,不是凭空猜的签名)
 *
 * 对照锚点(DEC-0014①):ADI EE-408 原文 —— SHARC+ 核心执行 IIR = 2.5 cyc/biquad
 *   (biquad = 5 MAC ⇒ 0.5 cyc/MAC)[L2/厂家公布]。本内核跑出的 window=64,biquads=8
 *   一行,cycles/8 ≈ 应与 2.5 cyc/biquad 同量级 —— 若差出一个数量级,不要自行"调整"
 *   数据去凑锚点,原样报回,连同该行 checksum 一起交回上级判读。
 *
 * 内存放置:
 *   L1 变体 = 不加任何 section pragma,沿用 ADI 原工程的默认放置(落在 L1 block,
 *             与厂家 2.5 cyc/biquad 锚点的测量条件一致)。
 *   L2 变体 = 仅把 DM 侧工作缓冲(input/output/state)搬到 L2(#pragma section("seg_l2"));
 *             coeffs 的 "pm"(SHARC 编译器的 Program Memory 总线限定符)保持默认位置不变
 *             ——这是 DEC-0009 里 biquad() 靠 PM/DM 双总线单周期双 MAC 的硬件前提,
 *             我们没有把 "pm" 限定符和 "seg_l2" pragma 同时叠加在同一数组上,
 *             因为这个组合我们没有工具链可以编译验证、风险未知,
 *             故意只测"DM 缓冲搬 L2"这一半(也正是 DEC-0014⑤ ECC 读改写代价发生的那一侧)。
 *             全 L2(含 pm 系数)是一个尚未尝试的后续项,见 PROVENANCE.md。
 *
 * 全部数字在板上跑出之前 = [L4/未验证]。
 *****************************************************************************/
#include "w1c_config.h"

#if ENABLE_T1A_BIQUAD

#include <filter.h>
#include <stdio.h>
#include <time.h>
#include <stdint.h>
#include "t1a_biquad.h"
#include "w1c_selfcheck.h"

#define T1A_TOTAL_PARAMETERS 35
#define T1A_MAX_BIQUADS      64
#define T1A_MAX_WINDOW       1024

/* ---- L1 变体(默认放置,不加 pragma,与 ADI 原工程一致) ---- */
static float t1a_input_l1[T1A_MAX_WINDOW];
static float t1a_output_l1[T1A_MAX_WINDOW];
static float t1a_state_l1[2 * T1A_MAX_BIQUADS];
static float pm t1a_coeffs[5 * T1A_MAX_BIQUADS];   /* pm = PM 总线数据空间限定符,两变体共用同一份 */

/* ---- L2 变体:只搬 DM 侧工作缓冲 ---- */
#pragma section("seg_l2")
static float t1a_input_l2[T1A_MAX_WINDOW];
#pragma section("seg_l2")
static float t1a_output_l2[T1A_MAX_WINDOW];
#pragma section("seg_l2")
static float t1a_state_l2[2 * T1A_MAX_BIQUADS];

static uint32_t t1a_param_list[T1A_TOTAL_PARAMETERS][2] = {
    /* Window, Biquads —— 与 ADI ADSP_2156x_IIR_Core_Performance 的 ParamList.dat 完全一致 */
#include "ParamList.dat"
};

/* 确定性非平凡输入(非全零),仅供自检使用,不追求信号意义 */
static void t1a_init_input(float *buf, int n)
{
    int i;
    for (i = 0; i < n; i++) {
        buf[i] = (float)((i % 17) - 8) * 0.01f;
    }
}

static void t1a_run_one(FILE *fcsv, uint32_t window, uint32_t biquads,
                         float *in, float *out, const float pm *coef, float *st,
                         const char *mem_tag)
/* ⚠ `coef` 必须带 `pm` 限定符:<filter.h> 的 biquad() 原型是
 *   biquad(const float dm *in, float dm *out, const float pm *coeffs, float dm *state, int, int)
 * 系数放 PM 总线是 SHARC 单周期双 MAC 的【硬件前提】(DEC-0009)。
 * t1a_coeffs 在 :49 声明时带了 pm,但形参此前写成裸 `float *` ⇒ 限定符在传参处丢失
 * ⇒ 板上编译报 cc0223「argument of type "float *" is incompatible with
 *    parameter of type "const pm float *"」。桌面自测查不出:桌面无 PM/DM 之分。 */
{
    volatile clock_t t0, t1, cyc;
    uint32_t j;
    int32_t chk;

    for (j = 0; j < 2 * biquads; j++) {
        st[j] = 0.0f;
    }
    t1a_init_input(in, (int)window);

    t0 = clock();
    biquad(&in[0], &out[0], &coef[0], &st[0], window, biquads);
    t1 = clock();
    cyc = t1 - t0;

    chk = (int32_t)(out[0] * 1000.0f) ^ (int32_t)(out[window - 1] * 1000.0f);
    w1c_checksum_add(chk);

    printf("T1A_biquad,%s,window=%d,biquads=%d,cycles=%d,checksum=%d\n",
           mem_tag, (int)window, (int)biquads, (int)cyc, (int)chk);
    if (fcsv) {
        fprintf(fcsv, "T1A_biquad,%s,%d,%d,%d,%d\n",
                mem_tag, (int)window, (int)biquads, (int)cyc, (int)chk);
    }
}

void t1a_biquad_run(FILE *fcsv)
{
    uint32_t i;

    printf("\n==== T1A: biquad {window,biquads} sweep (CCES <filter.h> biquad()) ====\n");

    /* 35 组扫描,L1 放置,与 ADI 原工程范围完全一致(可与 DEC-0014 锚点做 slope 对照) */
    for (i = 0; i < T1A_TOTAL_PARAMETERS; i++) {
        t1a_run_one(fcsv, t1a_param_list[i][0], t1a_param_list[i][1],
                    t1a_input_l1, t1a_output_l1, t1a_coeffs, t1a_state_l1, "L1");
    }

    /* DEC-0009/DEC-0014 主口径点:window=64, biquads=8,额外测一次 L2(仅 DM 侧) */
    t1a_run_one(fcsv, 64, 8, t1a_input_l2, t1a_output_l2, t1a_coeffs, t1a_state_l2,
                "L2dm_pmDefault");
}

#else /* !ENABLE_T1A_BIQUAD */

void t1a_biquad_run(FILE *fcsv)
{
    printf("T1A_biquad,DISABLED,-,-,-,-  (see w1c_config.h ENABLE_T1A_BIQUAD)\n");
    if (fcsv) {
        fprintf(fcsv, "T1A_biquad,DISABLED,-,-,-,-\n");
    }
}

#endif /* ENABLE_T1A_BIQUAD */
