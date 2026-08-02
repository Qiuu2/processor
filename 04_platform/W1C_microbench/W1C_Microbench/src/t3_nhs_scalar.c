/*****************************************************************************
 * t3_nhs_scalar.c
 * T3:NHS 判据/状态机标量码 —— adaptive-dsp 请求的第 4 内核
 * (回填其 20k cyc/槽 包络声明,W1_HANDOFF.md §7/§8-1)
 *
 * 来源:01_design/prototype_W1P/nhs.py(P1.0,[L2/宿主仿真],W1-B NHS 算法唯一
 *   权威源的宿主原型)。翻译对象 = 每个分析槽(analysis slot)对 NT=12 条跟踪轨
 *   做一遍的判据/状态机扫描,对应 python 的:
 *     _imsd()        (斜率检测:8 点滑窗线性回归 + 残差标准差,§2.2)
 *     _phpr_veto()   (谐波族否决:sub/2nd/3rd 谐波比较 + 三臂豁免合取门,§3.2)
 *     _is_dom()      (臂3 谓词:本通道 PNPR/PAPR 最高的活跃轨)
 *     _classify()    (PANIC/GROWTH/PERSIST 三态状态机,§3.1-§3.3)
 *
 * ⚠ 诚实边界(必须与任何引用这份周期数的地方一起带走):
 *   ①本文件**只翻译判据/状态机的算术形状**(浮点比较、log10f 若干次、
 *     一次 8 点线性回归、NT×W_LONG 规模的嵌套小循环),**不追求与 nhs.py
 *     逐行功能等价**——没有真实频谱输入、没有真实 IPMP 配对、没有真实
 *     Track 生命周期管理(_update_tracks/_birth/_allocate 均未搬),门限
 *     常数抄自 nhs.py 的 Params 默认值,但用于人工合成的代表性数据,
 *     不构成对任何真实音频场景的判定结果。
 *   ②magnitude 谱 M[] 是编译期确定性合成数据(含几个人工"谐波族"峰值,
 *     用来让谐波否决分支有代表性的走向),不是真实 FFT 输出——T2 内核
 *     单独测 FFT 本身的周期数,两者不重复计入同一个"槽"。
 *   ③本内核的目的只是给 T3(控制逻辑,分支密集、算术强度低)这一档一个
 *     "跑一次 12 轨判据扫描要多少周期"的量级参考,供与 adaptive-dsp 声明的
 *     "20k cyc/槽" 包络做量级对照,不是逐位复现算法结果。
 *
 * 内存放置:
 *   L1 变体 = 默认放置(不加 pragma)。
 *   L2 变体 = 跟踪轨数组与合成谱数组整体搬 L2(#pragma section("seg_l2"))。
 *
 * 全部数字在板上跑出之前 = [L4/未验证]。
 *****************************************************************************/
#include "w1c_config.h"

#if ENABLE_T3_NHS

#include <stdio.h>
#include <math.h>
#include <string.h>
#include <time.h>
#include <stdint.h>
#include "t3_nhs_scalar.h"
#include "w1c_selfcheck.h"

#define T3_NT       12   /* 跟踪轨上限,nhs.py Params.NT */
#define T3_W_LONG    8   /* IMSD 滑窗长度,nhs.py Params.W_long */
#define T3_M_BINS  128   /* 代表性合成谱 bin 数(非真实 FFT 输出,见文件头②) */

/* 门限常数抄自 01_design/prototype_W1P/nhs.py 的 Params 默认值(§1.2/§2.2/§3.2),
 * 用于人工合成数据、不构成真实判定 —— 只是让分支走向与真实算法同构 */
#define T3_T_PAPR         15.0f
#define T3_T_PNPR          8.0f
#define T3_T_PANIC        -6.0f
#define T3_D_SUB          10.0f
#define T3_D_HARM         20.0f
#define T3_S_MAX           1.5f
#define T3_DP_MIN          6.0f
#define T3_BETA_MIN_DBS   60.0f
#define T3_BETA_MAX_DBS  750.0f
#define T3_T_HOP        0.016f   /* HOP_SC/FS_SC = 256/16000 */

typedef struct {
    int   active;
    float papr_hist[T3_W_LONG];
    int   hist_n;
    float last_level;
    int   hit_n, obs_n;
    int   rapid_onset, relaxed, causal_ok;
    int   k_bin;             /* 代表性主瓣 bin(合成谱域,非 Hz) */
} t3_track_t;

/* ---- L1 变体(默认放置) ---- */
static t3_track_t t3_tracks_l1[T3_NT];
static float      t3_M_l1[T3_M_BINS];

/* ---- L2 变体 ---- */
#pragma section("seg_l2")
static t3_track_t t3_tracks_l2[T3_NT];
#pragma section("seg_l2")
static float      t3_M_l2[T3_M_BINS];

/* 合成谱:几个人工"啸叫+谐波族"峰值,幅度确定性非平凡(非全零),
 * 使谐波否决分支(_phpr_veto 同构)在跑的时候真的会走到"否决"和"不否决"两条路 */
static void t3_synth_spectrum(float *M, int n)
{
    int i;
    for (i = 0; i < n; i++) {
        M[i] = 0.01f + 0.002f * (float)(i % 5);   /* 本底噪声,非零 */
    }
    /* 基频峰 + 二次/三次谐波(供谐波族否决分支走到"命中"一侧) */
    if (n > 40)  M[20] = 1.0f;
    if (n > 40)  M[40] = 0.35f;   /* 2nd harmonic */
    if (n > 60)  M[60] = 0.15f;   /* 3rd harmonic */
    if (n > 10)  M[10] = 0.05f;   /* sub-harmonic,幅度不足以触发 sub 否决 */
    if (n > 90)  M[90] = 0.8f;    /* 第二条轨的独立基频峰,无强谐波族 */
}

static void t3_init_tracks(t3_track_t *tr)
{
    int i, j;
    for (i = 0; i < T3_NT; i++) {
        tr[i].active = (i < 4) ? 1 : 0;      /* 4 条活跃轨,代表性负载(非满非空) */
        tr[i].hist_n = T3_W_LONG;
        tr[i].hit_n = 5;
        tr[i].obs_n = 6;
        tr[i].rapid_onset = (i == 2) ? 1 : 0;
        tr[i].relaxed = 0;
        tr[i].causal_ok = (i == 0) ? 1 : 0;
        tr[i].k_bin = (i == 0) ? 20 : (i == 3) ? 90 : (10 + i * 3);
        for (j = 0; j < T3_W_LONG; j++) {
            /* 递增趋势,幅度取决于轨号,使 IMSD 斜率检测有正有负两种走向 */
            tr[i].papr_hist[j] = 10.0f + (float)j * (1.0f + 0.5f * (float)i)
                                  - (float)(i % 3) * 2.0f;
        }
        tr[i].last_level = -20.0f + 3.0f * (float)i;
    }
}

/* _imsd 同构:8 点滑窗线性回归(x=0..7)+ 残差标准差,与门限比较 */
static int t3_imsd(const t3_track_t *tr, float *out_slope)
{
    float sx = 0.0f, sy = 0.0f, sxx = 0.0f, sxy = 0.0f;
    float b, c, s, dP;
    float fw;
    int i;
    const int W = T3_W_LONG;

    fw = (float)W;
    for (i = 0; i < W; i++) {
        float x = (float)i;
        float y = tr->papr_hist[i];
        sx += x; sy += y; sxx += x * x; sxy += x * y;
    }
    /* 标准最小二乘斜率/截距:b = (W*Sxy - Sx*Sy) / (W*Sxx - Sx^2) */
    b = (fw * sxy - sx * sy) / (fw * sxx - sx * sx + 1e-9f);
    c = (sy - b * sx) / fw;

    s = 0.0f;
    for (i = 0; i < W; i++) {
        float x = (float)i;
        float resid = tr->papr_hist[i] - (b * x + c);
        s += resid * resid;
    }
    s = sqrtf(s / (float)W);

    dP = tr->papr_hist[W - 1] - tr->papr_hist[0];
    *out_slope = b;

    return (b >= T3_BETA_MIN_DBS * T3_T_HOP && b <= T3_BETA_MAX_DBS * T3_T_HOP
            && s <= T3_S_MAX && dP >= T3_DP_MIN) ? 1 : 0;
}

/* _phpr_veto 同构:sub/2nd/3rd 谐波比较(log10f)+ family-max/causal 合取门 */
static int t3_phpr_veto(const t3_track_t *tr, const float *M, int n,
                         int imsd_hit, int dom)
{
    int k = tr->k_bin;
    int k2 = k / 2;
    int k3 = k * 2;
    int k4 = k * 3;
    int veto = 0;
    int fam_max = 1;
    int causal;
    int arm1, arm2, arm3;

    if (k <= 2 || k >= n) return 0;

    if (k2 > 2 && 20.0f * log10f(M[k2] / (M[k] + 1e-30f) + 1e-30f) >= -T3_D_SUB) {
        veto = 1;
    }
    if (k3 < n && 20.0f * log10f(M[k3] / (M[k] + 1e-30f) + 1e-30f) >= -T3_D_HARM) {
        veto = 1;
        if (M[k3] > M[k]) fam_max = 0;
    }
    if (k4 < n && 20.0f * log10f(M[k4] / (M[k] + 1e-30f) + 1e-30f) >= -T3_D_HARM) {
        veto = 1;
        if (M[k4] > M[k]) fam_max = 0;
    }
    if (!veto) return 0;

    causal = tr->causal_ok;   /* 简化:不做时序推进,直接读继承标志(同构非等价) */
    arm1 = imsd_hit;
    arm2 = tr->rapid_onset;
    arm3 = dom;   /* 简化:臂3 合取的 gr_ok∧persist_path 折叠进调用方传入的 dom 判据 */

    return (fam_max && causal && (arm1 || arm2 || arm3)) ? 0 : 1;  /* exempt→不否决 */
}

/* _is_dom 同构:活跃轨中 papr_hist 末值最高者 */
static int t3_is_dom(const t3_track_t *tr, int idx)
{
    int i;
    float best = -1e9f;
    int best_i = -1;
    for (i = 0; i < T3_NT; i++) {
        if (!tr[i].active) continue;
        float v = tr[i].papr_hist[T3_W_LONG - 1];
        if (v > best) { best = v; best_i = i; }
    }
    return (best_i == idx);
}

/* _classify 同构:PANIC / GROWTH / PERSIST 三态,逐轨判定 */
static void t3_classify(t3_track_t *tr, const float *M, int n, int *out_counts /* [3] */)
{
    int i;
    int n_panic = 0, n_growth = 0, n_persist = 0;

    for (i = 0; i < T3_NT; i++) {
        float slope;
        int imsd_hit, dom, veto;
        int cls = 0; /* 0=none,1=PANIC,2=GROWTH,3=PERSIST */

        if (!tr[i].active || tr[i].hit_n < 1) continue;

        imsd_hit = t3_imsd(&tr[i], &slope);
        dom = t3_is_dom(tr, i);

        if (tr[i].last_level >= T3_T_PANIC && !tr[i].relaxed) {
            cls = 1;
        } else if ((imsd_hit || tr[i].rapid_onset) && !tr[i].relaxed) {
            veto = t3_phpr_veto(&tr[i], M, n, imsd_hit, dom);
            if (!veto) cls = 2;
        }
        if (cls == 0) {
            float rate = (float)tr[i].hit_n / (float)(tr[i].obs_n > 0 ? tr[i].obs_n : 1);
            if (tr[i].obs_n >= 3 && rate >= 0.70f
                && tr[i].papr_hist[T3_W_LONG - 1] >= (T3_T_PAPR + 6.0f)) {
                veto = t3_phpr_veto(&tr[i], M, n, imsd_hit, dom);
                if (!veto) cls = 3;
            }
        }

        if (cls == 1) n_panic++;
        else if (cls == 2) n_growth++;
        else if (cls == 3) n_persist++;
    }

    out_counts[0] = n_panic;
    out_counts[1] = n_growth;
    out_counts[2] = n_persist;
}

static void t3_run_variant(FILE *fcsv, t3_track_t *tracks, float *M, const char *mem_tag)
{
    volatile clock_t t0, t1, cyc_cold, cyc_warm_total;
    int counts[3];
    int32_t chk;
    int i;

    t3_synth_spectrum(M, T3_M_BINS);
    t3_init_tracks(tracks);

    /* 冷:第一次调用 */
    t0 = clock();
    t3_classify(tracks, M, T3_M_BINS, counts);
    t1 = clock();
    cyc_cold = t1 - t0;
    chk = (counts[0] << 16) ^ (counts[1] << 8) ^ counts[2];
    w1c_checksum_add(chk);
    printf("T3_NHS,%s,cold_1slot,cycles=%d,panic=%d,growth=%d,persist=%d,checksum=%d\n",
           mem_tag, (int)cyc_cold, counts[0], counts[1], counts[2], (int)chk);
    if (fcsv) fprintf(fcsv, "T3_NHS,%s,cold_1slot,%d,%d\n", mem_tag, (int)cyc_cold, (int)chk);

    /* 热:连续 W1C_WARM_REPEAT 个"槽"(每次重新初始化轨状态,避免轨全部老死后
     * active=0 导致后续槽退化为空扫描——那会低估稳态代价) */
    t0 = clock();
    for (i = 0; i < W1C_WARM_REPEAT; i++) {
        t3_init_tracks(tracks);
        t3_classify(tracks, M, T3_M_BINS, counts);
    }
    t1 = clock();
    cyc_warm_total = t1 - t0;
    chk = (counts[0] << 16) ^ (counts[1] << 8) ^ counts[2];
    w1c_checksum_add(chk);
    printf("T3_NHS,%s,warm_avg_of_%d,cycles_total=%d,cycles_avg=%d,checksum=%d\n",
           mem_tag, W1C_WARM_REPEAT, (int)cyc_warm_total,
           (int)(cyc_warm_total / W1C_WARM_REPEAT), (int)chk);
    if (fcsv) fprintf(fcsv, "T3_NHS,%s,warm_avg_of_%d,%d,%d\n",
                       mem_tag, W1C_WARM_REPEAT, (int)cyc_warm_total, (int)chk);
}

void t3_nhs_scalar_run(FILE *fcsv)
{
    printf("\n==== T3: NHS judgement/state-machine scalar kernel (%d tracks) ====\n", T3_NT);
    printf("     (代表性翻译,非 nhs.py 逐行等价;见文件头诚实边界声明)\n");

    t3_run_variant(fcsv, t3_tracks_l1, t3_M_l1, "L1");
    t3_run_variant(fcsv, t3_tracks_l2, t3_M_l2, "L2");
}

#else /* !ENABLE_T3_NHS */

void t3_nhs_scalar_run(FILE *fcsv)
{
    printf("T3_NHS,DISABLED,-,-,-  (see w1c_config.h ENABLE_T3_NHS)\n");
    if (fcsv) fprintf(fcsv, "T3_NHS,DISABLED,-,-,-\n");
}

#endif /* ENABLE_T3_NHS */
