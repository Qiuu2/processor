/**
 * @file    chdsp_detector.c
 * @brief   见 chdsp_detector.h。⛔ 门禁状态:未过门。
 */

#include "chdsp_detector.h"
#include "chdsp_tables.h"
#include <math.h>
#include <string.h>

/* ⛔ 仅供自验的坏版本开关:把功率状态截回 Q4.27 精度(= 下溢陷阱)。
 * 出货构建必须为 0,由 CHK-D0 硬闸门核。 */
#ifndef CHDSP_BROKEN_POW_NARROW
#  define CHDSP_BROKEN_POW_NARROW 0
#endif
/* ⛔ 坏版本:attack/release 不分方向(用同一个系数)。 */
#ifndef CHDSP_BROKEN_DET_ONEDIR
#  define CHDSP_BROKEN_DET_ONEDIR 0
#endif

#ifndef CHDSP_BROKEN_SMOOTH_FIXED   /* 1 = 平滑系数不随 tau 变(功率底与 release 解耦) */
#  define CHDSP_BROKEN_SMOOTH_FIXED 0
#endif
chdsp_smooth_q0_31_t chdsp_smooth_from_ms(double tau_ms)
{
    double a;
#if CHDSP_BROKEN_SMOOTH_FIXED
    (void)tau_ms;                       /* ⛔ 坏版本:忽略 tau,固定取 50 ms 的值 */
    tau_ms = 50.0;
#endif
    int64_t r;
    if (!(tau_ms > 0.0)) { return chdsp_smooth_from_raw((int32_t)((1LL << 31) - 1)); }
    a = 1.0 - exp(-1.0 / (tau_ms * 1e-3 * (double)CHDSP_FS_HZ));
    r = (int64_t)(a * 2147483648.0 + 0.5);
    if (r > (int64_t)INT32_MAX) { r = INT32_MAX; }
    if (r < 1) { r = 1; }                 /* ⛔ 不允许退化为 0(否则状态永不更新) */
    return chdsp_smooth_from_raw((int32_t)r);
}

void chdsp_det_init(chdsp_det_t *d, chdsp_det_mode_t mode,
                    double attack_ms, double release_ms)
{
    memset(d, 0, sizeof(*d));
    d->mode = mode;
    d->a_attack  = chdsp_smooth_from_ms(attack_ms);
    d->a_release = chdsp_smooth_from_ms(release_ms);
    d->state = chdsp_pow_from_raw(0);
}

void chdsp_det_reset(chdsp_det_t *d) { d->state = chdsp_pow_from_raw(0); }

chdsp_pow_q8_54_t chdsp_det_process1(chdsp_det_t *d, chdsp_smp_q4_27_t x)
{
    const int64_t xr = (int64_t)chdsp_smp_raw(x);
    int64_t inst = xr * xr;               /* Q8.54:|x|² 精确,无舍入 */
    int64_t s = chdsp_pow_raw(d->state);
    int32_t a;
    chdsp_acc_raw_t d128;

#if CHDSP_BROKEN_POW_NARROW
    /* ⛔ 坏版本:把功率状态截到 Q4.27 的精度(丢 27 位小数)⇒ 安静段塌到 0 */
    inst = (inst >> CHDSP_SMP_FRACBITS) << CHDSP_SMP_FRACBITS;
#endif

    if (d->mode == CHDSP_DET_PEAK) {
        /* 峰值:瞬时值高于状态则立即跟上(attack 仍平滑),低于则按 release 衰落 */
        a = (inst > s) ? CHDSP_RAW(d->a_attack) : CHDSP_RAW(d->a_release);
    } else {
        a = (inst > s) ? CHDSP_RAW(d->a_attack) : CHDSP_RAW(d->a_release);
    }
#if CHDSP_BROKEN_DET_ONEDIR
    a = CHDSP_RAW(d->a_attack);           /* ⛔ 坏版本:不分方向 */
#endif

    /* s += a·(inst − s)。|inst−s| ≤ 2^62,a ≤ 2^31 ⇒ 乘积 ≤ 2^93
     * ⇒ **必须用 128 位中间量**(int64 会溢出)。目标侧用 80-bit MRF。 */
    d128 = (chdsp_acc_raw_t)(inst - s) * (chdsp_acc_raw_t)a;
    s += (int64_t)(d128 >> CHDSP_SMOOTH_FRACBITS);
    if (s < 0) { s = 0; }                 /* 功率非负(舍入可能带来 −1 LSB) */
    d->state = chdsp_pow_from_raw(s);
    return d->state;
}

chdsp_db_q23_8_t chdsp_pow_to_db(chdsp_pow_q8_54_t p)
{
    int64_t v = chdsp_pow_raw(p);
    int32_t e;
    uint64_t m;

    if (v <= 0) { return chdsp_db_from_raw(CHDSP_DB_MUTE_Q8); }

    e = 0;
    { uint64_t t = (uint64_t)v; while (t >>= 1) { e++; } }   /* MSB 位置 */

    /* 归一化到 m ∈ [2^62, 2^63):m = v << (62 − e) */
    m = (e <= 62) ? ((uint64_t)v << (62 - e)) : ((uint64_t)v >> (e - 62));

    {
        const uint64_t frac = m - (1ULL << 62);
        const int32_t  idx  = (int32_t)(frac >> (62 - CHDSP_LOG2_BITS));
        const int64_t  lam  = (int64_t)((frac >> (62 - CHDSP_LOG2_BITS - 31))
                                        & ((1LL << 31) - 1));
        const int64_t  dd   = (int64_t)chdsp_log2_tab_q31[idx + 1]
                            - (int64_t)chdsp_log2_tab_q31[idx];
        const int64_t  lfrac_q31 = (int64_t)chdsp_log2_tab_q31[idx] + ((dd * lam) >> 31);
        /* log2(p) = (e − 54) + lfrac */
        const int64_t log2p_q31 = (((int64_t)(e - CHDSP_POW_FRACBITS)) << 31) + lfrac_q31;
        /* dB = 10·log10(p) = 10·log2(p)/log2(10) = log2(p) · (10/log2(10))
         *    ⚠ 功率口径:10·log10,⛔ 不是 20·log10。
         *    10/log2(10) = 3.010299957 ⇒ Q0.24 定标 */
        const int64_t K10_Q24 = (int64_t)(3.010299956639812 * 16777216.0 + 0.5);
        const chdsp_acc_raw_t q = (chdsp_acc_raw_t)log2p_q31 * (chdsp_acc_raw_t)K10_Q24;
        int64_t db_q8 = (int64_t)((q + ((chdsp_acc_raw_t)1 << 46)) >> 47);  /* 31+24−8 = 47 */
        if (db_q8 < CHDSP_DB_MUTE_Q8) { db_q8 = CHDSP_DB_MUTE_Q8; }
        if (db_q8 > INT32_MAX) { db_q8 = INT32_MAX; }
        return chdsp_db_from_raw((int32_t)db_q8);
    }
}
