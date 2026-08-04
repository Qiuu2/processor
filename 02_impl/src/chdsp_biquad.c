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
    if (b->ramp_left) { ramp_step(b); }
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
    return e;
}

int chdsp_bq_design(chdsp_filter_type_t type, double f0, double q, double gdb,
                    chdsp_biquad_coef_t *out)
{
    double w0, c, s, alpha, A, a0;

    if (!(f0 > 0.0) || f0 >= (double)CHDSP_FS_HZ * 0.5) { return -1; }
    if (!(q > 0.0)) { return -1; }

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
        if (!(alpha == alpha)) { return -1; }                 /* NaN ⇒ S 非法 */
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
        if (!(alpha == alpha)) { return -1; }
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
        /* ⭐ 结构约束量化:只量化 b0,b1=−2b0,b2=b0 ⇒ DC 零点在量化后仍精确 */
        return chdsp_coef_hplp_from_f64(((1.0 + c) / 2.0) / a0,
                                        (-2.0 * c) / a0, (1.0 - alpha) / a0, 1, out);
    }
    case CHDSP_FT_LPF: {
        alpha = s / (2.0 * q); a0 = 1.0 + alpha;
        return chdsp_coef_hplp_from_f64(((1.0 - c) / 2.0) / a0,
                                        (-2.0 * c) / a0, (1.0 - alpha) / a0, 0, out);
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
    default: return -1;
    }
}

/* Butterworth 各节的 Q(偶数阶) */
static double butter_q(int order, int k)
{ return 1.0 / (2.0 * cos(M_PI * (2.0 * k + 1.0) / (2.0 * order))); }

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

    if (order <= 0 || (order % 2) != 0 || order > 8) { return -1; }

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
            return -1;
        }
    } else {
        for (i = 0; i < order / 2; i++) {
            e |= chdsp_bq_design(t, fc, butter_q(order, i), 0.0, &out[n]); n++;
        }
    }
    *n_out = n;
    return e;
}
