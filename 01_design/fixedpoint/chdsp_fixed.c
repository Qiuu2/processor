/**
 * @file    chdsp_fixed.c
 * @brief   chdsp_fixed.h 的非 inline 实现(dB↔线性、设计期转换)
 *
 * ⛔ 门禁状态:**未过门**(2026-08-04)。见 chdsp_fixed.h 文件头。
 *
 * 实时路径:无浮点、无除法、无动态分配。
 * 设计期路径(chdsp_*_from_f64)用 double,**仅在非实时的系数计算处调用**。
 */

#include "chdsp_fixed.h"
#include "chdsp_tables.h"

/* ==========================================================================
 * dB → 线性增益
 * --------------------------------------------------------------------------
 *   g = 10^(dB/20) = 2^(dB·K),  K = log2(10)/20
 *   u_q32 = dB·K·2^32   ← (db_q8 · K_q40) >> 16
 *   n     = floor(u)    ← 算术右移 32
 *   f     = u − n ∈ [0,1)
 *   v     = 2^f  由 129 项表 + 线性内插得到(Q2.29)
 *   g     = v · 2^n     ⇒ Q4.27 下移位量 = n − 2
 * ========================================================================== */
chdsp_gain_q4_27_t chdsp_db_to_gain(chdsp_db_q23_8_t db_t)
{
    int32_t db = CHDSP_RAW(db_t);

    /* 肯定式钳位:先把输入压进已论证的定义域,再计算(团队纪律 D-2)。
     * ⇒ 任何异常/未来新增的取值默认落安全侧,而不是落进未定义的计算。 */
    if (db > CHDSP_DB_MAX_Q8)  { db = CHDSP_DB_MAX_Q8; }
    if (db <= CHDSP_DB_MUTE_Q8) { return CHDSP_MK(chdsp_gain_q4_27_t, 0); }  /* 精确静音 */

    {
        const int64_t u_q32 = ((int64_t)db * CHDSP_K_Q40) >> 16;
        const int32_t n     = (int32_t)(u_q32 >> 32);                 /* floor */
        const int64_t f_q32 = u_q32 - (((int64_t)n) << 32);           /* ∈ [0, 2^32) */
        const int32_t idx   = (int32_t)(f_q32 >> (32 - CHDSP_EXP2_BITS));
        const int64_t lam   = f_q32 - (((int64_t)idx) << (32 - CHDSP_EXP2_BITS));
        const int64_t d     = (int64_t)chdsp_exp2_tab_q29[idx + 1]
                            - (int64_t)chdsp_exp2_tab_q29[idx];
        const int64_t half_lam = ((int64_t)1) << (32 - CHDSP_EXP2_BITS - 1);
        int64_t v_q29 = (int64_t)chdsp_exp2_tab_q29[idx]
                      + ((d * lam + half_lam) >> (32 - CHDSP_EXP2_BITS));
        int32_t sh = n - 2;                                            /* Q2.29 → Q4.27 */
        int64_t g;

        if (sh >= 0) {
            g = v_q29 << sh;
        } else {
            const int32_t s = -sh;
            g = (v_q29 + (((int64_t)1) << (s - 1))) >> s;              /* 就近舍入 */
        }
        return CHDSP_MK(chdsp_gain_q4_27_t, chdsp_sat_i64_to_i32(g, (chdsp_sat_t *)0));
    }
}

/* ==========================================================================
 * 线性 → dB(仅供电平表/诊断显示)
 *   log2(g_raw) = e + log2(m),m ∈ [1,2)
 *   dB = 20·log10(g) = log2(g)/K,g = g_raw·2^−27
 * ========================================================================== */
chdsp_db_q23_8_t chdsp_gain_to_db(chdsp_gain_q4_27_t g_t)
{
    int32_t g = CHDSP_RAW(g_t);
    int32_t e;
    uint32_t m;

    if (g <= 0) { return CHDSP_MK(chdsp_db_q23_8_t, CHDSP_DB_MUTE_Q8); }

    /* e = MSB 位置(g 的最高置位位号) */
    e = 0;
    { uint32_t t = (uint32_t)g; while (t >>= 1u) { e++; } }

    /* 归一化到 m ∈ [2^30, 2^31):m = g << (30 − e) */
    m = (e <= 30) ? ((uint32_t)g << (30 - e)) : ((uint32_t)g >> (e - 30));

    {
        /* log2(m/2^30) ∈ [0,1) 查表 */
        const uint32_t frac = m - (1u << 30);                         /* ∈ [0, 2^30) */
        const int32_t  idx  = (int32_t)(frac >> (30 - CHDSP_LOG2_BITS));
        const int64_t  lam  = (int64_t)(frac - ((uint32_t)idx << (30 - CHDSP_LOG2_BITS)));
        const int64_t  d    = (int64_t)chdsp_log2_tab_q31[idx + 1]
                            - (int64_t)chdsp_log2_tab_q31[idx];
        const int64_t  lfrac_q31 = (int64_t)chdsp_log2_tab_q31[idx]
                            + ((d * lam) >> (30 - CHDSP_LOG2_BITS));
        /* log2(g) = (e − 27) + lfrac ,以 Q0.31 累计后转 dB(Q23.8) */
        const int64_t log2g_q31 = (((int64_t)(e - CHDSP_GAIN_FRACBITS)) << 31) + lfrac_q31;
        /* dB = log2g / K = log2g · (1/K) ;  INVK 为 Q0.24 */
        const int64_t db_q55 = log2g_q31 * CHDSP_INVK_Q24;            /* Q(31+24)=Q55 */
        const int64_t db_q8  = (db_q55 + (((int64_t)1) << 46)) >> 47; /* 55 − 8 = 47,就近 */
        int64_t r = db_q8;
        if (r < CHDSP_DB_MUTE_Q8) { r = CHDSP_DB_MUTE_Q8; }
        return CHDSP_MK(chdsp_db_q23_8_t, (int32_t)r);
    }
}

/* ==========================================================================
 * 设计期转换(非实时)—— 超范围是**硬失败**,不是警告
 * ========================================================================== */
static int f64_to_fixed(double x, int fracbits, int32_t *out)
{
    double scaled;
    if (!(x == x)) { return -1; }                        /* NaN */
    scaled = x * (double)(((int64_t)1) << fracbits);
    if (scaled >  2147483647.0) { return -1; }
    if (scaled < -2147483648.0) { return -1; }
    /* 就近舍入(半值远离零),与实时路径的 RTN 口径一致到 ±0.5 LSB */
    *out = (int32_t)(scaled >= 0.0 ? (scaled + 0.5) : (scaled - 0.5));
    return 0;
}

int chdsp_coef_from_f64(double x, chdsp_coef_q4_27_t *out)
{
    int32_t r;
    /* ⭐ 显式用常数守界(整改 2026-08-04 · critic m-6 · D6-ao 接线审计)
     * 原先只靠 f64_to_fixed 的 int32 边界,而它**碰巧**等价于 |x| < 16
     * (因为 16·2^27 = 2^31 恰好越过 INT32_MAX)⇒ §3.4「对 |x| ≥ 16 返回非 0」
     * 是**碰巧成立**,而 CHDSP_COEF_ABS_MAX_INT 全库【零消费者】。
     * ⇒ 现在改成:那个常数**真的**是拦截依据 —— 改它就改行为。 */
    if (!(x > -(double)CHDSP_COEF_ABS_MAX_INT && x < (double)CHDSP_COEF_ABS_MAX_INT)) {
        return -1;
    }
    if (f64_to_fixed(x, CHDSP_COEF_FRACBITS, &r) != 0) { return -1; }
    *out = CHDSP_MK(chdsp_coef_q4_27_t, r);
    return 0;
}

int chdsp_gain_from_f64(double x, chdsp_gain_q4_27_t *out)
{
    int32_t r;
    if (f64_to_fixed(x, CHDSP_GAIN_FRACBITS, &r) != 0) { return -1; }
    *out = CHDSP_MK(chdsp_gain_q4_27_t, r);
    return 0;
}

int chdsp_coef_hplp_from_f64(double b0, double a1, double a2, int hp,
                             chdsp_biquad_coef_t *out)
{
    int32_t rb0, ra1, ra2;
    int64_t rb1;
    if (f64_to_fixed(b0, CHDSP_COEF_FRACBITS, &rb0) != 0) { return -1; }
    if (f64_to_fixed(a1, CHDSP_COEF_FRACBITS, &ra1) != 0) { return -1; }
    if (f64_to_fixed(a2, CHDSP_COEF_FRACBITS, &ra2) != 0) { return -1; }
    /* b1 = ∓2·b0 由**已量化的 b0** 精确导出 ⇒ b0+b1+b2 (或 b0−b1+b2) 恒为 0 */
    rb1 = hp ? (-2LL * (int64_t)rb0) : (2LL * (int64_t)rb0);
    if (rb1 > INT32_MAX || rb1 < INT32_MIN) { return -1; }
    out->b0 = CHDSP_MK(chdsp_coef_q4_27_t, rb0);
    out->b1 = CHDSP_MK(chdsp_coef_q4_27_t, (int32_t)rb1);
    out->b2 = CHDSP_MK(chdsp_coef_q4_27_t, rb0);
    out->a1 = CHDSP_MK(chdsp_coef_q4_27_t, ra1);
    out->a2 = CHDSP_MK(chdsp_coef_q4_27_t, ra2);
    return 0;
}

double chdsp_smp_to_f64(chdsp_smp_q4_27_t x)
{ return (double)CHDSP_RAW(x) / (double)(((int64_t)1) << CHDSP_SMP_FRACBITS); }
double chdsp_io_to_f64(chdsp_io_q0_31_t x)
{ return (double)CHDSP_RAW(x) / (double)(((int64_t)1) << CHDSP_IO_FRACBITS); }
double chdsp_coef_to_f64(chdsp_coef_q4_27_t x)
{ return (double)CHDSP_RAW(x) / (double)(((int64_t)1) << CHDSP_COEF_FRACBITS); }
double chdsp_gain_to_f64(chdsp_gain_q4_27_t x)
{ return (double)CHDSP_RAW(x) / (double)(((int64_t)1) << CHDSP_GAIN_FRACBITS); }

/* 66-bit 安全域:|acc| < 2^65 */
int chdsp_acc_in_range(chdsp_acc_t a)
{
    const chdsp_acc_raw_t lim = ((chdsp_acc_raw_t)1) << 65;
    const chdsp_acc_raw_t v = CHDSP_RAW(a);
    return (v < lim && v > -lim) ? 0 : -1;
}
