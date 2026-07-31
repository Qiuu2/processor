/**
 * @file    tree_filterbank.c
 * @brief   4 子带 dyadic 树形半带 FIR（差分金字塔）实现 — 详见 tree_filterbank.h
 *
 * 实时核心路径：无浮点、无除法、无动态分配。所有缓冲由调用者静态分配。
 * MAC：Q15(coef) × Q31(state) → Q46(int64) 累加 → 右移 15 → Q31。
 *
 * 半带优化备注：半带核约半数抽头为 0（偶数抽头除中心外为 0）。本参考实现
 *   为清晰起见做全长卷积；SHARC 上可用零系数跳过表把 MAC 数砍半（见 MCPS 备注）。
 */

#include "tree_filterbank.h"
#include <string.h>
#include <stdint.h>

/* ============================================================
 * 饱和保护原语（PF-4 TASK-PF4-FIX-01，CTO 已批立即修）
 * ------------------------------------------------------------
 * 缺陷背景（PF-4 评审 + Critic 独立复核确认，[L2 host 桌面]）：
 *   半带核 Σ|h_q15|/32768 = 1.7309 > 1（中心抽头≈0.5 + 相邻正负交替）。
 *   对抗性满量程、与抽头符号逐点对齐的宽带激励下，hb_push_filter 的
 *   回量化 acc>>15 最坏达 1.7309× Q31 满量程，超 INT32_MAX；
 *   原 `return (int32_t)(acc>>15)` 无饱和 → int64→int32 窄化环绕/符号翻转
 *   （正峰翻成大负值 → 爆音/毛刺）。hb_interp2 的 ×2 复合到 3.46×。
 *
 * 修复策略（最小侵入，只加饱和/钳位，不改频率特性、不改系数、不改算法路线）：
 *   1) 所有 Q31 回量化点 / ×2 增益点 / int32+int32 合成相加点加中间饱和钳位
 *      到 [INT32_MIN, INT32_MAX]，把环绕爆音转为干净软削波（对抗激励下）。
 *   2) 标称信号（带限正弦、PR 单位增益激励）下绝不触及饱和阈值 →
 *      数值与修复前逐位一致（标称不激活，回归 SNR 不回退）。
 *
 * 系统级 headroom 约定（与饱和兜底并存，二者都要，不可互相替代）：
 *   半带链路输入预留 −4.8 dB（= 1/1.7309 线性）相对 Q31 满量程，
 *   把 1.73× 上界压回 ≤1×，使常态节目素材不进入软削波区；
 *   饱和钳位仅作对抗性峰值的最后兜底，防止符号翻转。
 *   注：−4.8 dB headroom 取值与节点①实际触发率的上板校准属 EZKIT [L1]，
 *       本任务为 host 桌面 [L2]，不声称 SHARC 实测。
 * ============================================================ */

/* 回归对照开关：定义 TFB_DISABLE_SAT 时饱和退化为原始环绕窄化，
 * 用于桌面 bit-exact 回归（证明 headroom 内修复与修复前逐位一致）。出货勿定义。 */
#ifdef TFB_DISABLE_SAT
static inline int32_t sat_i64_to_i32(int64_t v) { return (int32_t)v; }
static inline int32_t sat_add_i32(int32_t a, int32_t b) { return (int32_t)(a + b); }
#else
/* int64 → int32 饱和窄化（钳位到 Q31 范围，防符号翻转） */
static inline int32_t sat_i64_to_i32(int64_t v)
{
    if (v > (int64_t)INT32_MAX) { return INT32_MAX; }
    if (v < (int64_t)INT32_MIN) { return INT32_MIN; }
    return (int32_t)v;
}

/* int32 + int32 饱和相加（合成端逐子带相加，最坏可达 2× → 钳位） */
static inline int32_t sat_add_i32(int32_t a, int32_t b)
{
    int64_t s = (int64_t)a + (int64_t)b;
    if (s > (int64_t)INT32_MAX) { return INT32_MAX; }
    if (s < (int64_t)INT32_MIN) { return INT32_MIN; }
    return (int32_t)s;
}
#endif

/* ---- 全局半带系数（共享只读） ---- */
static const int16_t *g_hb = 0;
static uint16_t       g_hb_n = 0;

void tfb_set_coeffs(const int16_t *hb_coef_q15, uint16_t ntaps)
{
    g_hb   = hb_coef_q15;
    g_hb_n = ntaps;
}

void tfb_channel_init(TreeChannelState *ch)
{
    memset(ch, 0, sizeof(*ch));
    ch->initialized = 1u;
}

/* ============================================================
 * 半带 FIR 卷积原语（环形延迟线，单样点推进）
 * ============================================================ */

/* 推入一个样点并产出一个全长卷积结果（Q31）。 */
static int32_t hb_push_filter(HbFirState *s, int32_t x)
{
    uint16_t N = g_hb_n;
    uint16_t idx = s->widx;
    int64_t acc = 0;
    uint16_t k;

    s->state[idx] = x;
    idx = (uint16_t)((idx + 1u < N) ? (idx + 1u) : 0u);
    s->widx = idx;

    /* y = Σ h[k]·state[最新..最旧]，环形读出 */
    for (k = 0u; k < N; k++) {
        uint16_t rd = (uint16_t)((idx + k < N) ? (idx + k) : (idx + k - N));
        acc += (int64_t)g_hb[k] * (int64_t)s->state[rd];
    }
    /* Q46 >>15 → Q31，加中间饱和（PF-4 FIX-01）：Σ|h|=1.73>1，对抗激励
     * 下 acc>>15 最坏 1.73× FS，原 (int32_t) 窄化会符号翻转爆音 → 钳位。
     * 标称（带限正弦/PR 单位增益）下 |acc>>15| < FS，不触发，逐位同修复前。 */
    return sat_i64_to_i32(acc >> 15);
}

/* ---- decimate-by-2：N 个输入 → N/2 个输出（半带 LP 后取偶样点） ---- */
static void hb_decimate2(HbFirState *s, const int32_t *in, uint16_t n_in, int32_t *out)
{
    uint16_t i, o = 0u;
    for (i = 0u; i < n_in; i++) {
        int32_t y = hb_push_filter(s, in[i]);
        if ((i & 1u) == 1u) {            /* 取每对的第 2 个（抽取相位） */
            out[o++] = y;
        }
    }
}

/* ---- interpolate-by-2：N 个输入 → 2N 个输出（零插值后半带 LP，×2 增益补偿） ----
 * 即上采样 2×：每个输入样点之间插 0，过半带，乘 2。 */
static void hb_interp2(HbFirState *s, const int32_t *in, uint16_t n_in, int32_t *out)
{
    uint16_t i, o = 0u;
    for (i = 0u; i < n_in; i++) {
        /* 相位 0：真实样点 */
        int32_t y0 = hb_push_filter(s, in[i]);
        out[o++] = sat_i64_to_i32((int64_t)y0 * 2);   /* ×2 内插增益补偿（PF-4 FIX-01：补饱和，复合最坏 3.46×） */
        /* 相位 1：插入的 0 */
        int32_t y1 = hb_push_filter(s, 0);
        out[o++] = sat_i64_to_i32((int64_t)y1 * 2);
    }
}

/* ============================================================
 * 差分金字塔分析（3 级）
 *   coarse_{l+1} = dec2(LP(coarse_l))
 *   detail_l     = coarse_l − interp2(coarse_{l+1})   （时域残差，telescoping → PR）
 * ============================================================ */
void tfb_analyze(TreeChannelState *ch, const int32_t *in, uint16_t frame,
                 int32_t *sb0, int32_t *sb1, int32_t *sb2, int32_t *sb3)
{
    /* 各级 coarse 缓冲（帧内静态上限：frame 必须是 8 的倍数） */
    int32_t a1[256] = {0}, a2[128] = {0}, a3[64] = {0};
    int32_t r1[512] = {0}, r2[256] = {0}, r3[128] = {0};   /* interp2 重建（用于求 detail） */
    uint16_t f0 = frame, f1 = frame/2u, f2 = frame/4u, f3 = frame/8u;
    uint16_t i;

    /* L1: a1 = dec2(x)  (f0 -> f1) */
    hb_decimate2(&ch->ana_dec[0], in, f0, a1);
    /* L2: a2 = dec2(a1) (f1 -> f2) */
    hb_decimate2(&ch->ana_dec[1], a1, f1, a2);
    /* L3: a3 = dec2(a2) (f2 -> f3) */
    hb_decimate2(&ch->ana_dec[2], a2, f2, a3);

    /* 重建各级 coarse 以求 detail（detail = 本级 − interp2(下一级 coarse)） */
    hb_interp2(&ch->ana_int[2], a3, f3, r3);   /* f3 -> f2 */
    hb_interp2(&ch->ana_int[1], a2, f2, r2);   /* f2 -> f1 */
    hb_interp2(&ch->ana_int[0], a1, f1, r1);   /* f1 -> f0 */

    /* detail 子带（时域残差） */
    for (i = 0u; i < f2; i++) sb1[i] = a2[i] - r3[i];   /* SB1 detail @f2 */
    for (i = 0u; i < f1; i++) sb2[i] = a1[i] - r2[i];   /* SB2 detail @f1 */
    for (i = 0u; i < f0; i++) sb3[i] = in[i] - r1[i];   /* SB3 detail @f0 */
    for (i = 0u; i < f3; i++) sb0[i] = a3[i];           /* SB0 coarse @f3 */

    /* NOTE: 与 tree_filterbank.h 的频率映射保持一致：
     *   SB0=coarse(f/8), SB1=detail@f/4, SB2=detail@f/2, SB3=detail@f
     * tfb_analyze 输出长度：sb0=frame/8, sb1=frame/4, sb2=frame/2, sb3=frame
     * （sb1 写在 a2 域=f2=frame/4；sb2 写在 a1 域=f1=frame/2；sb3 写在 in 域=f0=frame） */
}

/* ============================================================
 * 差分金字塔合成（3 级，逆向 telescoping）
 *   coarse_l = interp2(g·coarse_{l+1}) + g·detail_l
 * broadside DAS：g 全为 1.0（Q31 = 0x7FFFFFFF）→ 精确重建。
 * 这里 g 以 Q31 传入，乘法 Q31×Q31→Q62 右移 31 回 Q31。
 * ============================================================ */
static int32_t q31_mul(int32_t a, int32_t b)
{
    return (int32_t)(((int64_t)a * (int64_t)b) >> 31);
}

void tfb_synthesize(TreeChannelState *ch,
                    const int32_t *sb0, const int32_t *sb1,
                    const int32_t *sb2, const int32_t *sb3,
                    uint16_t frame, int32_t *out)
{
    int32_t a2p[256], a1p[512];
    int32_t up3[128], up2[256], up1[512];
    uint16_t f0 = frame, f1 = frame/2u, f2 = frame/4u, f3 = frame/8u;
    uint16_t i;

    /* a2' = interp2(sb0) + sb1   (f3 -> f2, 加 detail@f2)
     * int32+int32 合成相加加饱和（PF-4 FIX-01）：各项近满量程时 additive 可达 2× → 钳位。
     * 标称 PR 下 up3+sb1 代数 telescoping 回到原信号 ≤FS，不触发，逐位同修复前。 */
    hb_interp2(&ch->syn_int[2], sb0, f3, up3);          /* f3 -> f2 */
    for (i = 0u; i < f2; i++) a2p[i] = sat_add_i32(up3[i], sb1[i]);

    /* a1' = interp2(a2') + sb2   (f2 -> f1) */
    hb_interp2(&ch->syn_int[1], a2p, f2, up2);          /* f2 -> f1 */
    for (i = 0u; i < f1; i++) a1p[i] = sat_add_i32(up2[i], sb2[i]);

    /* out = interp2(a1') + sb3   (f1 -> f0) */
    hb_interp2(&ch->syn_int[0], a1p, f1, up1);          /* f1 -> f0 */
    for (i = 0u; i < f0; i++) out[i] = sat_add_i32(up1[i], sb3[i]);

    (void)q31_mul;  /* 增益钩子：broadside DAS 全 1.0 时无需逐子带缩放，
                     * 非 DAS（未来加权）时在上面各 detail/coarse 加 q31_mul(·, g[sb]) */
}
