/** @file chdsp_notch.c  见 chdsp_notch.h。⛔ 门禁状态:未过门。 */
#include "chdsp_notch.h"
#include <string.h>

/* ⛔ 仅供自验的坏版本开关(出货构建须全 0) */
#ifndef CHDSP_BROKEN_NOTCH_EVICT_FIXED   /* 1 = 回收时把固定槽也算进候选 */
#  define CHDSP_BROKEN_NOTCH_EVICT_FIXED 0
#endif
#ifndef CHDSP_BROKEN_NOTCH_RESET_ALL     /* 1 = 复位动态槽时把固定槽也清掉 */
#  define CHDSP_BROKEN_NOTCH_RESET_ALL 0
#endif

void chdsp_notch_bank_init(chdsp_notch_bank_t *b, chdsp_notch_mode_t mode, uint16_t n_fixed)
{
    uint16_t i, nf;
    memset(b, 0, sizeof(*b));
    b->mode = mode;
    switch (mode) {
    case CHDSP_NOTCH_MODE_FIXED:   nf = (uint16_t)CHDSP_NOTCH_COUNT; break;
    case CHDSP_NOTCH_MODE_DYNAMIC: nf = 0u; break;
    default:                       /* HYBRID */
        nf = (n_fixed <= (uint16_t)CHDSP_NOTCH_COUNT) ? n_fixed : (uint16_t)CHDSP_NOTCH_COUNT;
        break;
    }
    b->n_fixed  = nf;
    b->seq_next = 1u;
    for (i = 0u; i < (uint16_t)CHDSP_NOTCH_COUNT; i++) {
        b->slot[i].is_fixed = (uint8_t)((i < nf) ? 1 : 0);
    }
}

uint16_t chdsp_notch_bank_used(const chdsp_notch_bank_t *b)
{
    uint16_t i, n = 0u;
    for (i = 0u; i < (uint16_t)CHDSP_NOTCH_COUNT; i++) { if (b->slot[i].in_use) { n++; } }
    return n;
}

uint16_t chdsp_notch_bank_free_dynamic(const chdsp_notch_bank_t *b)
{
    uint16_t i, n = 0u;
    for (i = 0u; i < (uint16_t)CHDSP_NOTCH_COUNT; i++) {
        if (!b->slot[i].is_fixed && !b->slot[i].in_use) { n++; }
    }
    return n;
}

/* 把一个陷波真正写进滤波器链(⛔ 簿记与系数必须同时改,否则遥测会撒谎) */
static int place(chdsp_notch_bank_t *b, chdsp_bq_chain_t *chain, uint16_t idx,
                 double f_hz, double q, double depth_db)
{
    chdsp_biquad_coef_t c;
    /* AFC 陷波 = 负增益峰型(depth_db ≤ 0);depth 为 0 ⇒ 视为"不衰减",仍占槽但旁路 */
    int e = chdsp_bq_design(CHDSP_FT_PEAKING, f_hz, q, depth_db, &c);
    if (e != CHDSP_BQ_OK) { return CHDSP_NOTCH_ERR_PARAM; }
    if (chain != 0) {
        chdsp_bq_set_coef_now(&chain->sec[idx], &c);
        chain->sec[idx].bypass = (uint8_t)((depth_db == 0.0) ? 1 : 0);
        if (chain->n <= idx) { chain->n = (uint16_t)(idx + 1u); }
    }
    b->slot[idx].in_use = 1u;
    b->slot[idx].f_hz   = f_hz;
    b->slot[idx].seq    = b->seq_next++;
    return CHDSP_NOTCH_OK;
}

int chdsp_notch_bank_set_fixed(chdsp_notch_bank_t *b, chdsp_bq_chain_t *chain,
                               uint16_t idx, double f_hz, double q, double depth_db)
{
    if (idx >= (uint16_t)CHDSP_NOTCH_COUNT) { return CHDSP_NOTCH_ERR_IDX; }
    if (!b->slot[idx].is_fixed)             { return CHDSP_NOTCH_ERR_NOT_FIXED; }
    return place(b, chain, idx, f_hz, q, depth_db);
}

int chdsp_notch_bank_request(chdsp_notch_bank_t *b, chdsp_bq_chain_t *chain,
                             double f_hz, double q, double depth_db, uint16_t *out_idx)
{
    uint16_t i, pick = (uint16_t)CHDSP_NOTCH_COUNT;
    uint32_t oldest = 0xFFFFFFFFu;
    int evicting = 0;

    /* ① 先找空闲的**动态**槽 */
    for (i = 0u; i < (uint16_t)CHDSP_NOTCH_COUNT; i++) {
        if (!b->slot[i].is_fixed && !b->slot[i].in_use) { pick = i; break; }
    }
    /* ② 没有空闲 ⇒ 回收**最早分配的动态槽**(LRU) */
    if (pick == (uint16_t)CHDSP_NOTCH_COUNT) {
        for (i = 0u; i < (uint16_t)CHDSP_NOTCH_COUNT; i++) {
#if CHDSP_BROKEN_NOTCH_EVICT_FIXED
            /* ⛔ 坏版本:把固定槽也算进回收候选 —— 这正是 FIXED/HYBRID 要防的事 */
            if (!b->slot[i].in_use) { continue; }
#else
            if (b->slot[i].is_fixed || !b->slot[i].in_use) { continue; }
#endif
            if (b->slot[i].seq < oldest) { oldest = b->slot[i].seq; pick = i; }
        }
        evicting = (pick != (uint16_t)CHDSP_NOTCH_COUNT);
    }
    /* ③ 一个动态槽都没有(FIXED 模式必然如此)⇒ 拒绝,⛔ 不得挪用固定槽 */
    if (pick >= (uint16_t)CHDSP_NOTCH_COUNT) {
        b->reject_count++;
        return CHDSP_NOTCH_ERR_NO_SLOT;
    }
    if (evicting) { b->evict_count++; }
    {
        int e = place(b, chain, pick, f_hz, q, depth_db);
        if (e != CHDSP_NOTCH_OK) { return e; }
    }
    if (out_idx != 0) { *out_idx = pick; }
    return CHDSP_NOTCH_OK;
}

int chdsp_notch_bank_release(chdsp_notch_bank_t *b, chdsp_bq_chain_t *chain, uint16_t idx)
{
    if (idx >= (uint16_t)CHDSP_NOTCH_COUNT) { return CHDSP_NOTCH_ERR_IDX; }
    b->slot[idx].in_use = 0u;
    b->slot[idx].seq    = 0u;
    b->slot[idx].f_hz   = 0.0;
    if (chain != 0) { chain->sec[idx].bypass = 1u; }
    return CHDSP_NOTCH_OK;
}

void chdsp_notch_bank_reset_dynamic(chdsp_notch_bank_t *b, chdsp_bq_chain_t *chain)
{
    uint16_t i;
    for (i = 0u; i < (uint16_t)CHDSP_NOTCH_COUNT; i++) {
#if !CHDSP_BROKEN_NOTCH_RESET_ALL
        if (b->slot[i].is_fixed) { continue; }   /* ⭐「重启后仍在」的机械形式 */
#endif
        b->slot[i].in_use = 0u;
        b->slot[i].seq    = 0u;
        b->slot[i].f_hz   = 0.0;
        if (chain != 0) { chain->sec[i].bypass = 1u; }
    }
}
