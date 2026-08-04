/**
 * @file    chdsp_biquad.c
 * @brief   见 chdsp_biquad.h。⛔ 门禁状态:未过门。
 *
 * 实时路径:无浮点、无除法、无动态分配。
 * 设计期路径(chdsp_bq_design*)用 double,⛔ 仅在非实时的系数计算处调用。
 */

#include "chdsp_biquad.h"
#include <math.h>
#include <string.h>

#ifndef M_PI
#  define M_PI 3.14159265358979323846
#endif

/* ⛔ 仅供自验的坏版本开关(出货构建须全 0,由 CHK-B0 硬闸门核) */
#ifndef CHDSP_BROKEN_BQ_NORAMP     /* 1 = 忽略斜坡,系数直接跳变 */
#  define CHDSP_BROKEN_BQ_NORAMP 0
#endif
#ifndef CHDSP_BROKEN_BQ_TIE_FREE   /* 1 = HPF/LPF 改自由量化(不用结构约束) */
#  define CHDSP_BROKEN_BQ_TIE_FREE 0
#endif
#ifndef CHDSP_BROKEN_BUTTER_COS    /* 1 = butter_q 退回 cos 式(奇数阶会静默算错) */
#  define CHDSP_BROKEN_BUTTER_COS 0
#endif
#ifndef CHDSP_BROKEN_BESSEL_RBJ    /* 1 = Bessel 退回逐节 RBJ(高阶高通会错到 90 dB) */
#  define CHDSP_BROKEN_BESSEL_RBJ 0
#endif

/* ==========================================================================
 * 1. 运行时
 * ========================================================================== */

void chdsp_bq_init(chdsp_bq_t *b)
{
    memset(b, 0, sizeof(*b));
    chdsp_biquad_reset(&b->st);
    /* 默认 = 直通(b0=1,其余 0)。⚠ 这与 bypass 不同:直通仍走一次量化。 */
    b->cur.b0 = chdsp_coef_from_raw(1 << CHDSP_COEF_FRACBITS);
    b->cur.b1 = chdsp_coef_from_raw(0);
    b->cur.b2 = chdsp_coef_from_raw(0);
    b->cur.a1 = chdsp_coef_from_raw(0);
    b->cur.a2 = chdsp_coef_from_raw(0);
    b->target = b->cur;
    b->bypass = 1u;                     /* 出厂默认旁路 */
}

void chdsp_bq_chain_init(chdsp_bq_chain_t *c, chdsp_bq_t *storage, uint16_t n_max)
{
    uint16_t i;
    c->sec = storage; c->n = 0u; c->n_max = n_max;
    for (i = 0u; i < n_max; i++) { chdsp_bq_init(&storage[i]); }
}

void chdsp_bq_set_coef_now(chdsp_bq_t *b, const chdsp_biquad_coef_t *c)
{
    b->cur = *c; b->target = *c; b->ramp_left = 0u; b->ramp_total = 0u;
}

void chdsp_bq_set_coef_ramp(chdsp_bq_t *b, const chdsp_biquad_coef_t *c, uint16_t steps)
{
    if (steps == 0u) { chdsp_bq_set_coef_now(b, c); return; }
    b->target = *c; b->ramp_left = steps; b->ramp_total = steps;
}

/* 一步系数插值:cur += (target − cur) / ramp_left。
 * ⚠ 除法在实时路径:斜坡是**有限步的瞬态**,非稳态开销。若目标侧除法昂贵,
 *   可改为预计算步增量 —— **该优化留待 W1-C 实测后再定,⛔ 现在不加**(D4:先别加机器)。
 * ⚠ 显式写五个成员,⛔ 不用指针别名遍历(强类型 build 下 struct 包装,别名是未定义行为)。 */
static int32_t lerp1(int32_t cur, int32_t tgt, int32_t k)
{
    int64_t d = (int64_t)tgt - (int64_t)cur;
    return cur + (int32_t)(d / k);
}

static void ramp_step(chdsp_bq_t *b)
{
    const int32_t k = (int32_t)b->ramp_left;
    b->cur.b0 = chdsp_coef_from_raw(lerp1(chdsp_coef_raw(b->cur.b0), chdsp_coef_raw(b->target.b0), k));
    b->cur.b1 = chdsp_coef_from_raw(lerp1(chdsp_coef_raw(b->cur.b1), chdsp_coef_raw(b->target.b1), k));
    b->cur.b2 = chdsp_coef_from_raw(lerp1(chdsp_coef_raw(b->cur.b2), chdsp_coef_raw(b->target.b2), k));
    b->cur.a1 = chdsp_coef_from_raw(lerp1(chdsp_coef_raw(b->cur.a1), chdsp_coef_raw(b->target.a1), k));
    b->cur.a2 = chdsp_coef_from_raw(lerp1(chdsp_coef_raw(b->cur.a2), chdsp_coef_raw(b->target.a2), k));
    b->ramp_left--;
    if (b->ramp_left == 0u) { b->cur = b->target; }
}

chdsp_smp_q4_27_t chdsp_bq_process1(chdsp_bq_t *b, chdsp_smp_q4_27_t x, chdsp_sat_t *sat)
{
    if (b->bypass) { return x; }                 /* 逐位透传 */
#if !CHDSP_BROKEN_BQ_NORAMP
    if (b->ramp_left) { ramp_step(b); }
#else
    if (b->ramp_left) { b->cur = b->target; b->ramp_left = 0u; }  /* ⛔ 坏版本:直接跳变 */
#endif
    return chdsp_biquad_df1(&b->cur, &b->st, x, sat);
}

void chdsp_bq_chain_process(chdsp_bq_chain_t *c, const chdsp_smp_q4_27_t *in,
                            chdsp_smp_q4_27_t *out, uint16_t n_samples, chdsp_sat_t *sat)
{
    uint16_t i, k;
    for (i = 0u; i < n_samples; i++) {
        chdsp_smp_q4_27_t v = in[i];
        for (k = 0u; k < c->n; k++) { v = chdsp_bq_process1(&c->sec[k], v, sat); }
        out[i] = v;
    }
}

void chdsp_bq_chain_reset(chdsp_bq_chain_t *c)
{
    uint16_t k;
    for (k = 0u; k < c->n_max; k++) { chdsp_biquad_reset(&c->sec[k].st); }
}

/* ==========================================================================
 * 2. 系数设计(设计期)
 * ========================================================================== */

static int pack(double b0, double b1, double b2, double a1, double a2,
                chdsp_biquad_coef_t *o)
{
    int e = 0;
    e |= chdsp_coef_from_f64(b0, &o->b0);
    e |= chdsp_coef_from_f64(b1, &o->b1);
    e |= chdsp_coef_from_f64(b2, &o->b2);
    e |= chdsp_coef_from_f64(a1, &o->a1);
    e |= chdsp_coef_from_f64(a2, &o->a2);
    return e ? CHDSP_BQ_ERR_COEF_RANGE : CHDSP_BQ_OK;
}

/** ⭐ 主动守【增益包络】—— 解析界只依赖 G_max,与 Q/S/频率无关。
 *  ⛔ 不守 S:S 从 1.0→2.0 只动 +0.0144,是几乎无关的量(D34 §3.2.2 实测)。 */
static int gain_within_envelope(double gdb)
{
    double a = (gdb >= 0.0) ? gdb : -gdb;
    return (a * 1000.0 < (double)CHDSP_COEF_GAIN_ENVELOPE_MDB) ? 1 : 0;
}

int chdsp_bq_design(chdsp_filter_type_t type, double f0, double q, double gdb,
                    chdsp_biquad_coef_t *out)
{
    double w0, c, s, alpha, A, a0;

    if (!(f0 > 0.0) || f0 >= (double)CHDSP_FS_HZ * 0.5) { return CHDSP_BQ_ERR_FREQ; }
    if (!(q > 0.0)) { return CHDSP_BQ_ERR_Q; }
    /* ⭐ 只有带增益的族受包络约束;HPF/LPF/NOTCH/ALLPASS 的解析界恒 ≤2,与增益无关 */
    if ((type == CHDSP_FT_PEAKING || type == CHDSP_FT_LOWSHELF || type == CHDSP_FT_HIGHSHELF)
        && !gain_within_envelope(gdb)) {
        return CHDSP_BQ_ERR_GAIN_ENV;
    }

    w0 = 2.0 * M_PI * f0 / (double)CHDSP_FS_HZ;
    c = cos(w0); s = sin(w0);
    A = pow(10.0, gdb / 40.0);

    switch (type) {
    case CHDSP_FT_PEAKING: {
        alpha = s / (2.0 * q);
        a0 = 1.0 + alpha / A;
        return pack((1.0 + alpha * A) / a0, (-2.0 * c) / a0, (1.0 - alpha * A) / a0,
                    (-2.0 * c) / a0, (1.0 - alpha / A) / a0, out);
    }
    case CHDSP_FT_LOWSHELF: {
        double t;
        alpha = s / 2.0 * sqrt((A + 1.0 / A) * (1.0 / q - 1.0) + 2.0);
        if (!(alpha == alpha)) { return CHDSP_BQ_ERR_Q; }     /* NaN ⇒ S 非法 */
        t = 2.0 * sqrt(A) * alpha;
        a0 = (A + 1.0) + (A - 1.0) * c + t;
        return pack(A * ((A + 1.0) - (A - 1.0) * c + t) / a0,
                    2.0 * A * ((A - 1.0) - (A + 1.0) * c) / a0,
                    A * ((A + 1.0) - (A - 1.0) * c - t) / a0,
                    -2.0 * ((A - 1.0) + (A + 1.0) * c) / a0,
                    ((A + 1.0) + (A - 1.0) * c - t) / a0, out);
    }
    case CHDSP_FT_HIGHSHELF: {
        double t;
        alpha = s / 2.0 * sqrt((A + 1.0 / A) * (1.0 / q - 1.0) + 2.0);
        if (!(alpha == alpha)) { return CHDSP_BQ_ERR_Q; }
        t = 2.0 * sqrt(A) * alpha;
        a0 = (A + 1.0) - (A - 1.0) * c + t;
        return pack(A * ((A + 1.0) + (A - 1.0) * c + t) / a0,
                    -2.0 * A * ((A - 1.0) + (A + 1.0) * c) / a0,
                    A * ((A + 1.0) + (A - 1.0) * c - t) / a0,
                    2.0 * ((A - 1.0) - (A + 1.0) * c) / a0,
                    ((A + 1.0) - (A - 1.0) * c - t) / a0, out);
    }
    case CHDSP_FT_HPF: {
        alpha = s / (2.0 * q); a0 = 1.0 + alpha;
#if CHDSP_BROKEN_BQ_TIE_FREE
        return pack(((1.0 + c) / 2.0) / a0, (-(1.0 + c)) / a0, ((1.0 + c) / 2.0) / a0,
                    (-2.0 * c) / a0, (1.0 - alpha) / a0, out);   /* ⛔ 自由量化 */
#else
        /* ⭐ 结构约束量化:只量化 b0,b1=−2b0,b2=b0 ⇒ DC 零点在量化后仍精确 */
        return chdsp_coef_hplp_from_f64(((1.0 + c) / 2.0) / a0,
                                        (-2.0 * c) / a0, (1.0 - alpha) / a0, 1, out);
#endif
    }
    case CHDSP_FT_LPF: {
        alpha = s / (2.0 * q); a0 = 1.0 + alpha;
#if CHDSP_BROKEN_BQ_TIE_FREE
        return pack(((1.0 - c) / 2.0) / a0, (1.0 - c) / a0, ((1.0 - c) / 2.0) / a0,
                    (-2.0 * c) / a0, (1.0 - alpha) / a0, out);   /* ⛔ 自由量化 */
#else
        return chdsp_coef_hplp_from_f64(((1.0 - c) / 2.0) / a0,
                                        (-2.0 * c) / a0, (1.0 - alpha) / a0, 0, out);
#endif
    }
    case CHDSP_FT_NOTCH: {
        alpha = s / (2.0 * q); a0 = 1.0 + alpha;
        return pack(1.0 / a0, (-2.0 * c) / a0, 1.0 / a0,
                    (-2.0 * c) / a0, (1.0 - alpha) / a0, out);
    }
    case CHDSP_FT_ALLPASS: {
        alpha = s / (2.0 * q); a0 = 1.0 + alpha;
        return pack((1.0 - alpha) / a0, (-2.0 * c) / a0, 1.0,
                    (-2.0 * c) / a0, (1.0 - alpha) / a0, out);
    }
    default: return CHDSP_BQ_ERR_TYPE;
    }
}

/* Butterworth 各节的 Q(偶数阶) */
/** Butterworth 第 k 个双二阶节的 Q。
 *
 * ⭐⭐ 2026-08-04(r8)整改:**sin,不是 cos**。
 *   原写 `1/(2·cos(π(2k+1)/(2n)))`。对**偶数**阶它给出的是**同一个 Q 集合、只是顺序相反**
 *   (证:sin x = cos(π/2−x),而 π/2 − π(2k+1)/(2n) = π(2k′+1)/(2n) 当 k′ = n/2−k−1;
 *    偶数 n 时 k′ 必落在 [0, n/2−1])⇒ 级联顺序不改变总传函 ⇒ **旧代码在当时是对的**。
 *   ⛔ 但对**奇数**阶两式不等:n=3 时 cos 式给 0.5774,正确值是 **1.0**。
 *   ⇒ 本轮加奇数阶,若照搬 cos 式会**静默产出错的滤波器**(编译过、跑得动、频响错)。
 *   ⇒ 已加 CHK-X4 逐位回归:偶数阶(LR2/4/6/8、BW2/4/6/8)系数必须与改动前**逐位相同**
 *     (预注册 PREREG_D34_r8_xover.txt 的证伪条件 F-4)。 */
static double butter_q(int order, int k)
{
#if CHDSP_BROKEN_BUTTER_COS
    return 1.0 / (2.0 * cos(M_PI * (2.0 * k + 1.0) / (2.0 * order)));  /* ⛔ 坏版本 */
#else
    return 1.0 / (2.0 * sin(M_PI * (2.0 * k + 1.0) / (2.0 * order)));
#endif
}

int chdsp_xover_needs_polarity_flip(int lr, int order)
{
    if (!lr) { return 0; }                       /* 非 LR ⇒ 不由本函数管 */
    return ((order % 4) == 2) ? 1 : 0;           /* mod 4 == 2 ⇒ 须反相 */
}

int chdsp_bq_design_xover(int lr, int order, int highpass, double fc,
                          chdsp_biquad_coef_t *out, uint16_t *n_out)
{
    chdsp_filter_type_t t = highpass ? CHDSP_FT_HPF : CHDSP_FT_LPF;
    uint16_t n = 0u;
    int i, e = 0;

    if (order <= 0 || (order % 2) != 0 || order > 8) { return CHDSP_BQ_ERR_ORDER; }

    if (lr) {
        /* LR{order} = (Butterworth order/2 阶)² */
        int bo = order / 2;
        if (bo == 1) {
            /* LR2 = 双实极点重合 ⇒ 单节 Q = 0.5 */
            e |= chdsp_bq_design(t, fc, 0.5, 0.0, &out[n]); n++;
        } else if ((bo % 2) == 0) {
            for (i = 0; i < bo / 2; i++) {
                double q = butter_q(bo, i);
                e |= chdsp_bq_design(t, fc, q, 0.0, &out[n]); n++;
                e |= chdsp_bq_design(t, fc, q, 0.0, &out[n]); n++;
            }
        } else if (bo == 3) {
            /* LR6 = (3 阶 BW)²:3 阶 = 一实极点 + 一 Q=1 节 ⇒ 平方后 = 2×(实) + 2×(Q=1) */
            e |= chdsp_bq_design(t, fc, 0.5, 0.0, &out[n]); n++;
            e |= chdsp_bq_design(t, fc, 1.0, 0.0, &out[n]); n++;
            e |= chdsp_bq_design(t, fc, 1.0, 0.0, &out[n]); n++;
        } else {
            return CHDSP_BQ_ERR_ORDER;
        }
    } else {
        for (i = 0; i < order / 2; i++) {
            e |= chdsp_bq_design(t, fc, butter_q(order, i), 0.0, &out[n]); n++;
        }
    }
    *n_out = n;
    return e;
}

/* ==========================================================================
 * 2b. C 第二批(r8):一阶节 + 通用分频(BW / LR / Bessel,1..8 阶)
 * ==========================================================================
 * 缘起:D3D4 参数表 §4③ 已列 `xo_type = {BW, LR, Bessel}` 与
 *       `xo_slope` 的奇数档(竞品 6/18/30/42),而实现只有 BW/LR 且第一行就
 *       `if (order % 2) return ERR_ORDER;` ⇒ **本件自己写下的合法档位,实现全部拒绝。**
 * 预注册:01_design/d34_chain/PREREG_D34_r8_xover.txt
 * 结果  :01_design/d34_chain/results_xover_r8.txt
 */

int chdsp_bq_design_first_order(int highpass, double fc_hz, chdsp_biquad_coef_t *out)
{
    double K;
    if (!(fc_hz > 0.0) || fc_hz >= (double)CHDSP_FS_HZ * 0.5) { return CHDSP_BQ_ERR_FREQ; }
    K = tan(M_PI * fc_hz / (double)CHDSP_FS_HZ);
    if (highpass) {
        return pack(1.0 / (K + 1.0), -1.0 / (K + 1.0), 0.0, (K - 1.0) / (K + 1.0), 0.0, out);
    }
    return pack(K / (K + 1.0), K / (K + 1.0), 0.0, (K - 1.0) / (K + 1.0), 0.0, out);
}

/* 归一化(−3 dB)Bessel 极点表,order 1..8。
 * 由 01_design/d34_chain/xover_r8.py 的 bessel_poles_norm() 生成:
 * 反 Bessel 多项式 θ_n(s) 求根 + 二分求 −3 dB 频率归一。
 * ⚠ 两轨核过:与 scipy.signal.bessel(norm='mag') 的幅频 max|Δ| = **0.000000 dB**
 *   (1..8 阶 × LP/HP 全部),阳性对照(人为改一节 Q)差 56.5 dB [L2/宿主实测 EXP-10]。 */
typedef struct { double re, im; } chdsp_cpole_t;      /* im = 0 ⇒ 实极点 */

static const chdsp_cpole_t k_bessel_p1[] = { { -1.000000000000, 0.0 } };
static const chdsp_cpole_t k_bessel_p2[] = { { -1.101601330592, 0.636009824757 } };
static const chdsp_cpole_t k_bessel_p3[] = { { -1.322675799910, 0.0 },
                                             { -1.047409161009, 0.999264436281 } };
static const chdsp_cpole_t k_bessel_p4[] = { { -0.995208764350, 1.257105739455 },
                                             { -1.370067830551, 0.410249717494 } };
static const chdsp_cpole_t k_bessel_p5[] = { { -1.502316271447, 0.0 },
                                             { -0.957676548563, 1.471124320730 },
                                             { -1.380877325860, 0.717909587627 } };
static const chdsp_cpole_t k_bessel_p6[] = { { -0.930656522947, 1.661863268943 },
                                             { -1.381858097597, 0.971471890712 },
                                             { -1.571490403616, 0.320896374223 } };
static const chdsp_cpole_t k_bessel_p7[] = { { -1.684368179273, 0.0 },
                                             { -0.909867780623, 1.836451353036 },
                                             { -1.378903216795, 1.191566777801 },
                                             { -1.612038766226, 0.589244506932 } };
static const chdsp_cpole_t k_bessel_p8[] = { { -0.892869718847, 1.998325843641 },
                                             { -1.373841217637, 1.388356575877 },
                                             { -1.636939418127, 0.822795625140 },
                                             { -1.757408400402, 0.272867575102 } };

static const chdsp_cpole_t *const k_bessel[9] = {
    0, k_bessel_p1, k_bessel_p2, k_bessel_p3, k_bessel_p4,
    k_bessel_p5, k_bessel_p6, k_bessel_p7, k_bessel_p8
};
static const uint8_t k_bessel_n[9] = { 0u, 1u, 1u, 2u, 2u, 3u, 3u, 4u, 4u };

/** Bessel 单支:归一化极点 → 单次预畸 → 双线性。⛔ 不走逐节 RBJ(见头文件说明)。 */
static int design_bessel(int order, int highpass, double fc_hz,
                         chdsp_biquad_coef_t *out, uint16_t *n_out)
{
    const double c  = 2.0 * (double)CHDSP_FS_HZ;
    const double wa = c * tan(M_PI * fc_hz / (double)CHDSP_FS_HZ);
    uint16_t n = 0u, i;
    int e = 0;
    /* 高通零点在 z = +1,低通零点在 z = −1;两者都恰好每节 2 个(一阶节 1 个) */
    const double zr = highpass ? 1.0 : -1.0;

#if CHDSP_BROKEN_BESSEL_RBJ
    /* ⛔ 坏版本:退回「逐节 RBJ,f0 = fc·|p|,Q = |p|/(2|Re p|)」那条路。
     *   它对 Butterworth/LR 恰好等价(各节共用同一 ω0),对 Bessel **不等价**。 */
    {
        uint16_t bn = 0u; int bi; int be = 0;
        for (bi = 0; bi < (int)k_bessel_n[order]; bi++) {
            chdsp_cpole_t bp = k_bessel[order][bi];
            double mag = sqrt(bp.re * bp.re + bp.im * bp.im);
            double f0  = fc_hz * mag;
            if (f0 >= (double)CHDSP_FS_HZ * 0.5) { f0 = (double)CHDSP_FS_HZ * 0.499; }
            if (bp.im == 0.0) {
                be |= chdsp_bq_design_first_order(highpass, f0, &out[bn]);
            } else {
                be |= chdsp_bq_design(highpass ? CHDSP_FT_HPF : CHDSP_FT_LPF,
                                      f0, mag / (2.0 * fabs(bp.re)), 0.0, &out[bn]);
            }
            bn++;
        }
        *n_out = bn;
        return be;
    }
#endif

    for (i = 0u; i < k_bessel_n[order]; i++) {
        chdsp_cpole_t p = k_bessel[order][i];
        double sre, sim, dre, dim, den, pr, pi_, b0, b1, b2, a1, a2, g;
        if (p.im == 0.0) {
            /* 实极点 ⇒ 一阶节 */
            sre = highpass ? (wa / p.re) : (wa * p.re);
            pr  = (1.0 + sre / c) / (1.0 - sre / c);
            b0 = 1.0; b1 = -zr; b2 = 0.0;
            a1 = -pr; a2 = 0.0;
            /* 归一:LP 在 z=1、HP 在 z=−1 处增益 1 */
            { double zt = highpass ? -1.0 : 1.0;
              double nu = (zt - zr), de = (zt - pr);
              g = fabs(de / nu); }
        } else {
            /* 共轭对 ⇒ 双二阶。s_hp = wa / p  (复数除法) */
            if (highpass) {
                den = p.re * p.re + p.im * p.im;
                sre = wa * p.re / den;
                sim = -wa * p.im / den;
            } else {
                sre = wa * p.re;
                sim = wa * p.im;
            }
            /* 双线性 z = (1 + s/c)/(1 − s/c),复数 */
            { double nr = 1.0 + sre / c, ni = sim / c;
              double dr = 1.0 - sre / c, di = -sim / c;
              double dd = dr * dr + di * di;
              dre = (nr * dr + ni * di) / dd;
              dim = (ni * dr - nr * di) / dd; }
            pr = dre; pi_ = dim;
            b0 = 1.0; b1 = -2.0 * zr; b2 = zr * zr;
            a1 = -2.0 * pr; a2 = pr * pr + pi_ * pi_;
            { double zt = highpass ? -1.0 : 1.0;
              double nu = (zt - zr) * (zt - zr);
              double dr2 = (zt - pr), di2 = -pi_;
              double de = dr2 * dr2 + di2 * di2;   /* |zt − p|² = (zt−p)(zt−p*) */
              g = fabs(de / nu); }
        }
        b0 *= g; b1 *= g; b2 *= g;
        if (n >= CHDSP_OUT_XO_SECTIONS) { return CHDSP_BQ_ERR_ORDER; }
        e |= pack(b0, b1, b2, a1, a2, &out[n]);
        n++;
    }
    *n_out = n;
    return e ? CHDSP_BQ_ERR_COEF_RANGE : CHDSP_BQ_OK;
}

int chdsp_bq_design_xover2(chdsp_xover_type_t type, int order, int highpass,
                           double fc_hz, chdsp_biquad_coef_t *out, uint16_t *n_out)
{
    chdsp_filter_type_t t = highpass ? CHDSP_FT_HPF : CHDSP_FT_LPF;
    uint16_t n = 0u;
    int i, e = 0;

    if (order <= 0 || order > 8) { return CHDSP_BQ_ERR_ORDER; }
    if (!(fc_hz > 0.0) || fc_hz >= (double)CHDSP_FS_HZ * 0.5) { return CHDSP_BQ_ERR_FREQ; }

    switch (type) {
    case CHDSP_XO_LINKWITZ_RILEY:
        /* ⛔ LR = BW² ⇒ 奇数阶数学上不存在。这不是缺口,是定义。 */
        if ((order % 2) != 0) { return CHDSP_BQ_ERR_ORDER; }
        return chdsp_bq_design_xover(1, order, highpass, fc_hz, out, n_out);

    case CHDSP_XO_BUTTERWORTH:
        if ((order % 2) == 1) {
            /* 奇数阶 = 一个一阶节 + (order−1)/2 个双二阶节 */
            e |= chdsp_bq_design_first_order(highpass, fc_hz, &out[n]); n++;
        }
        for (i = 0; i < order / 2; i++) {
            if (n >= CHDSP_OUT_XO_SECTIONS) { return CHDSP_BQ_ERR_ORDER; }
            e |= chdsp_bq_design(t, fc_hz, butter_q(order, i), 0.0, &out[n]); n++;
        }
        *n_out = n;
        return e;

    case CHDSP_XO_BESSEL:
        return design_bessel(order, highpass, fc_hz, out, n_out);

    default:
        return CHDSP_BQ_ERR_TYPE;
    }
}
