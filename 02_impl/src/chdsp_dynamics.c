/**
 * @file    chdsp_dynamics.c
 * @brief   见 chdsp_dynamics.h。⛔ 门禁状态:未过门。
 */

#include "chdsp_dynamics.h"
#include <math.h>
#include <string.h>

/* ⛔ 仅供自验的坏版本开关(出货构建须全 0,由 CHK-Y0 硬闸门核) */
#ifndef CHDSP_BROKEN_GATE_NEGATIVE   /* 1 = 把开门条件写成否定式豁免(D-2 反面) */
#  define CHDSP_BROKEN_GATE_NEGATIVE 0
#endif
#ifndef CHDSP_BROKEN_NO_HYST         /* 1 = 去掉迟滞 */
#  define CHDSP_BROKEN_NO_HYST 0
#endif
#ifndef CHDSP_BROKEN_LIM_NOLOOK      /* 1 = 去掉前视(侧链与音频同相)*/
#  define CHDSP_BROKEN_LIM_NOLOOK 0
#endif
#ifndef CHDSP_BROKEN_COMP_HARDKNEE   /* 1 = 软拐点退化为硬拐点 */
#  define CHDSP_BROKEN_COMP_HARDKNEE 0
#endif

chdsp_slope_q16_15_t chdsp_slope_from_f64(double v)
{
    double s = v * 32768.0;
    if (s >  2147483647.0) { s =  2147483647.0; }
    if (s < -2147483648.0) { s = -2147483648.0; }
    return chdsp_slope_from_raw((int32_t)(s >= 0.0 ? (s + 0.5) : (s - 0.5)));
}

/* dB(Q23.8) × slope(Q16.15) → dB(Q23.8) */
static int32_t db_mul_slope(int32_t db_q8, chdsp_slope_q16_15_t sl)
{
    int64_t p = (int64_t)db_q8 * (int64_t)CHDSP_RAW(sl);
    return (int32_t)((p + (1LL << (CHDSP_SLOPE_FRACBITS - 1))) >> CHDSP_SLOPE_FRACBITS);
}

/* ==========================================================================
 * 1. 噪声门 / 扩展器
 * ========================================================================== */

void chdsp_gate_init(chdsp_gate_t *g, double thr_dbfs, double ratio, double hyst_db,
                     double range_db, double attack_ms, double hold_ms, double release_ms)
{
    memset(g, 0, sizeof(*g));
    chdsp_det_init(&g->det, CHDSP_DET_RMS, attack_ms, release_ms);
    g->thr_db   = chdsp_db_from_millidb((int32_t)(thr_dbfs * 1000.0));
    g->hyst_db  = chdsp_db_from_millidb((int32_t)(hyst_db  * 1000.0));
    g->range_db = chdsp_db_from_millidb((int32_t)(range_db * 1000.0));
    g->slope    = chdsp_slope_from_f64(ratio - 1.0);
    g->hold_samples = (uint32_t)(hold_ms * 1e-3 * (double)CHDSP_FS_HZ);
    g->hold_left = 0u;
    g->state = CHDSP_GATE_CLOSED;        /* ⭐ 默认落安全侧(关门) */
    g->enabled = 0u;
}

void chdsp_gate_reset(chdsp_gate_t *g)
{
    chdsp_det_reset(&g->det);
    g->state = CHDSP_GATE_CLOSED; g->hold_left = 0u;
}

chdsp_gain_q4_27_t chdsp_gate_gain1(chdsp_gate_t *g, chdsp_smp_q4_27_t sc,
                                    chdsp_db_q23_8_t *gdb_out)
{
    chdsp_pow_q8_54_t p = chdsp_det_process1(&g->det, sc);
    int32_t L   = chdsp_db_raw(chdsp_pow_to_db(p));
    int32_t thr = chdsp_db_raw(g->thr_db);
    int32_t hys = chdsp_db_raw(g->hyst_db);
    int32_t gdb = 0;

    if (!g->enabled) {
        if (gdb_out) { *gdb_out = chdsp_db_from_raw(0); }
        return chdsp_db_to_gain(chdsp_db_from_raw(0));
    }

#if CHDSP_BROKEN_NO_HYST
    hys = 0;
#endif

    /* ⭐ 肯定式状态机(D-2):只有"持有肯定结论"才进 OPEN;
     *    新增/异常状态默认落 CLOSED 侧。 */
#if CHDSP_BROKEN_GATE_NEGATIVE
    /* ⛔ 坏版本:否定式豁免 —— 「只要不是明显低于门限就开门」 */
    if (!(L < thr - hys)) { g->state = CHDSP_GATE_OPEN; }
    else                  { g->state = CHDSP_GATE_CLOSED; }
#else
    switch (g->state) {
    case CHDSP_GATE_OPEN:
        if (L < thr - hys) { g->state = CHDSP_GATE_HOLD; g->hold_left = g->hold_samples; }
        break;
    case CHDSP_GATE_HOLD:
        if (L >= thr) { g->state = CHDSP_GATE_OPEN; }
        else if (g->hold_left == 0u) { g->state = CHDSP_GATE_CLOSED; }
        else { g->hold_left--; }
        break;
    case CHDSP_GATE_CLOSED:
    default:
        if (L >= thr) { g->state = CHDSP_GATE_OPEN; }   /* 肯定式:达到门限才开 */
        break;
    }
#endif

    if (g->state == CHDSP_GATE_CLOSED) {
        int32_t range = chdsp_db_raw(g->range_db);
        gdb = db_mul_slope(L - thr, g->slope);          /* L<thr ⇒ 负 */
        if (gdb > 0) { gdb = 0; }
        if (gdb < -range) { gdb = -range; }
    } else {
        gdb = 0;                                        /* OPEN / HOLD ⇒ 不衰减 */
    }
    if (gdb_out) { *gdb_out = chdsp_db_from_raw(gdb); }
    return chdsp_db_to_gain(chdsp_db_from_raw(gdb));
}

/* ==========================================================================
 * 2. 压缩器
 * ========================================================================== */

void chdsp_comp_init(chdsp_comp_t *c, double thr_dbfs, double ratio, double knee_db,
                     double attack_ms, double release_ms, double makeup_db,
                     chdsp_det_mode_t det_mode)
{
    memset(c, 0, sizeof(*c));
    chdsp_det_init(&c->det, det_mode, attack_ms, release_ms);
    c->thr_db    = chdsp_db_from_millidb((int32_t)(thr_dbfs * 1000.0));
    c->knee_db   = chdsp_db_from_millidb((int32_t)(knee_db  * 1000.0));
    c->slope     = chdsp_slope_from_f64(1.0 - 1.0 / ratio);
    c->makeup_db = chdsp_db_from_millidb((int32_t)(makeup_db * 1000.0));
    c->enabled = 0u;
}

void chdsp_comp_reset(chdsp_comp_t *c) { chdsp_det_reset(&c->det); }

chdsp_gain_q4_27_t chdsp_comp_gain1(chdsp_comp_t *c, chdsp_smp_q4_27_t sc,
                                    chdsp_db_q23_8_t *gdb_out)
{
    chdsp_pow_q8_54_t p = chdsp_det_process1(&c->det, sc);
    int32_t L   = chdsp_db_raw(chdsp_pow_to_db(p));
    int32_t thr = chdsp_db_raw(c->thr_db);
    int32_t W   = chdsp_db_raw(c->knee_db);
    int32_t ov  = L - thr;
    int32_t gdb;

    if (!c->enabled) {
        if (gdb_out) { *gdb_out = chdsp_db_from_raw(0); }
        return chdsp_db_to_gain(chdsp_db_from_raw(0));
    }
#if CHDSP_BROKEN_COMP_HARDKNEE
    W = 0;
#endif

    if (2 * ov < -W) {
        gdb = 0;
    } else if (2 * ov <= W && W > 0) {
        /* 软拐点:gain = −slope·(ov + W/2)² / (2W)。ov,W 为 Q23.8 ⇒ 平方要降回 Q23.8 */
        int64_t t = (int64_t)ov + (int64_t)W / 2;
        int64_t sq = (t * t) >> CHDSP_DB_FRACBITS;      /* Q23.8 */
        int64_t den = 2 * (int64_t)W;
        /* ⚠ sq 是 Q8 的 dB²,den 是 Q8 的 dB ⇒ 直接相除得到【整数 dB】,丢了 Q8 标度。
         *   必须先左移 CHDSP_DB_FRACBITS 再除,结果才是 Q8 的 dB。
         *   (本行原写 `sq/den`,由 CHK-Y4 抓出:拐点上沿出现 4.625 dB 跳变) */
        int32_t v = (den != 0) ? (int32_t)((sq << CHDSP_DB_FRACBITS) / den) : 0;
        gdb = -db_mul_slope(v, c->slope);
    } else {
        gdb = -db_mul_slope(ov, c->slope);
    }
    gdb += chdsp_db_raw(c->makeup_db);
    if (gdb_out) { *gdb_out = chdsp_db_from_raw(gdb); }
    return chdsp_db_to_gain(chdsp_db_from_raw(gdb));
}

/* ==========================================================================
 * 3. 限幅器(砖墙 + 前视)
 * ========================================================================== */

int chdsp_limiter_init(chdsp_limiter_t *l, chdsp_smp_q4_27_t *storage, uint32_t cap,
                       double thr_dbfs, double lookahead_ms, double release_ms)
{
    uint32_t n;
    memset(l, 0, sizeof(*l));
    n = (uint32_t)(lookahead_ms * 1e-3 * (double)CHDSP_FS_HZ);
#if CHDSP_BROKEN_LIM_NOLOOK
    n = 0u;                                   /* ⛔ 坏版本:去掉前视 */
#endif
    /* attack 由前视长度决定:在前视窗内把增益压下去 ⇒ attack ≈ lookahead */
    chdsp_det_init(&l->det, CHDSP_DET_PEAK,
                   (lookahead_ms > 0.0) ? lookahead_ms * 0.25 : 0.05, release_ms);
    l->thr_db = chdsp_db_from_millidb((int32_t)(thr_dbfs * 1000.0));
    l->look_samples = n;
    l->enabled = 0u;
    return chdsp_delay_init(&l->look, storage, cap, n);
}

void chdsp_limiter_reset(chdsp_limiter_t *l)
{ chdsp_det_reset(&l->det); chdsp_delay_reset(&l->look); }

chdsp_smp_q4_27_t chdsp_limiter_process1(chdsp_limiter_t *l, chdsp_smp_q4_27_t x,
                                         chdsp_sat_t *sat, chdsp_db_q23_8_t *gr_out)
{
    /* 侧链看**未延时**的 x(= 看未来);音频路走延时线 */
    chdsp_pow_q8_54_t p = chdsp_det_process1(&l->det, x);
    int32_t L   = chdsp_db_raw(chdsp_pow_to_db(p));
    int32_t thr = chdsp_db_raw(l->thr_db);
    int32_t gdb = 0;
    chdsp_smp_q4_27_t xd = chdsp_delay_process1(&l->look, x);

    if (!l->enabled) {
        if (gr_out) { *gr_out = chdsp_db_from_raw(0); }
        return xd;
    }
    if (L > thr) { gdb = thr - L; }           /* 比率 ∞ ⇒ 超出多少压多少 */
    if (gr_out) { *gr_out = chdsp_db_from_raw(gdb); }
    return chdsp_apply_gain(xd, chdsp_db_to_gain(chdsp_db_from_raw(gdb)), sat);
}

/* ==========================================================================
 * 4. 音箱保护限幅(双通道)
 * ========================================================================== */

int chdsp_spk_guard_init(chdsp_spk_guard_t *s,
                         chdsp_smp_q4_27_t *rms_look, uint32_t rms_cap,
                         chdsp_smp_q4_27_t *peak_look, uint32_t peak_cap,
                         double rms_thr_dbfs, double rms_tc_ms,
                         double peak_thr_dbfs, double peak_attack_ms)
{
    int e = 0;
    memset(s, 0, sizeof(*s));
    /* 长期功率支:RMS 检测(用 limiter 结构但检测器换 RMS),前视 0(热保护不需要前视) */
    e |= chdsp_limiter_init(&s->rms_stage, rms_look, rms_cap, rms_thr_dbfs, 0.0, rms_tc_ms);
    s->rms_stage.det.mode = CHDSP_DET_RMS;
    s->rms_stage.det.a_attack = chdsp_smooth_from_ms(rms_tc_ms);
    /* 短期峰值支 */
    e |= chdsp_limiter_init(&s->peak_stage, peak_look, peak_cap, peak_thr_dbfs,
                            peak_attack_ms, 50.0);
    s->enabled = 0u;
    return e;
}

chdsp_smp_q4_27_t chdsp_spk_guard_process1(chdsp_spk_guard_t *s, chdsp_smp_q4_27_t x,
                                           chdsp_sat_t *sat)
{
    chdsp_smp_q4_27_t y;
    if (!s->enabled) { return x; }
    s->rms_stage.enabled = 1u; s->peak_stage.enabled = 1u;
    y = chdsp_limiter_process1(&s->rms_stage, x, sat, 0);
    y = chdsp_limiter_process1(&s->peak_stage, y, sat, 0);
    return y;
}
