/** @file chdsp_fir.c  见 chdsp_fir.h。⛔ 门禁状态:未过门。 */
#include "chdsp_fir.h"
#include <math.h>
#include <string.h>
#ifndef M_PI
#  define M_PI 3.14159265358979323846
#endif
/* ⛔ 坏版本:抽头不对称(破坏线性相位) */
#ifndef CHDSP_BROKEN_FIR_ASYM
#  define CHDSP_BROKEN_FIR_ASYM 0
#endif

int chdsp_fir_init(chdsp_fir_t *f, const chdsp_coef_q4_27_t *taps,
                   chdsp_smp_q4_27_t *state, uint16_t n)
{
    uint16_t i;
    if (n == 0u) { memset(f, 0, sizeof(*f)); return 0; }   /* n=0 ⇒ 关闭,合法 */
    if (taps == 0 || state == 0) { return -1; }
    f->h = taps; f->z = state; f->n = n; f->w = 0u; f->enabled = 0u;
    for (i = 0u; i < n; i++) { state[i] = chdsp_smp_from_raw(0); }
    return 0;
}

void chdsp_fir_reset(chdsp_fir_t *f)
{
    uint16_t i;
    f->w = 0u;
    for (i = 0u; i < f->n; i++) { f->z[i] = chdsp_smp_from_raw(0); }
}

chdsp_smp_q4_27_t chdsp_fir_process1(chdsp_fir_t *f, chdsp_smp_q4_27_t x, chdsp_sat_t *sat)
{
    chdsp_acc_t acc;
    uint16_t k, idx;
    if (f->n == 0u || !f->enabled) { return x; }
    f->z[f->w] = x;
    f->w = (uint16_t)((f->w + 1u < f->n) ? (f->w + 1u) : 0u);
    chdsp_acc_clear(&acc);
    idx = f->w;
    for (k = 0u; k < f->n; k++) {
        chdsp_acc_mac(&acc, f->z[idx], f->h[k]);
        idx = (uint16_t)((idx + 1u < f->n) ? (idx + 1u) : 0u);
    }
    return chdsp_acc_to_smp(acc, sat);
}

static double i0(double x)
{
    double s = 1.0, t = 1.0; int k;
    for (k = 1; k < 40; k++) { t *= (x / (2.0 * k)) * (x / (2.0 * k)); s += t; }
    return s;
}

int chdsp_fir_design_lowpass(double fc, double beta, chdsp_coef_q4_27_t *taps, uint16_t n)
{
    int i, M;
    double *w;
    static double tmp[1024];
    if (n == 0u) { return 0; }
    if (n > 1024u || taps == 0) { return -1; }
    if (!(fc > 0.0) || fc >= (double)CHDSP_FS_HZ * 0.5) { return -1; }
    M = (int)n - 1;
    w = tmp;
    for (i = 0; i <= M; i++) {
        double m = (double)i - (double)M / 2.0;
        double sinc = (fabs(m) < 1e-12) ? (2.0 * fc / (double)CHDSP_FS_HZ)
                    : sin(2.0 * M_PI * fc * m / (double)CHDSP_FS_HZ) / (M_PI * m);
        double r = 2.0 * (double)i / (double)M - 1.0;
        double kw = i0(beta * sqrt(1.0 - r * r)) / i0(beta);
        w[i] = sinc * kw;
    }
#if CHDSP_BROKEN_FIR_ASYM
    w[0] *= 1.5;                       /* ⛔ 坏版本:破坏对称 ⇒ 非线性相位 */
#endif
    for (i = 0; i <= M; i++) {
        if (chdsp_coef_from_f64(w[i], &taps[i]) != 0) { return -1; }
    }
    return 0;
}
