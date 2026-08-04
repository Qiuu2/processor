/**
 * @file    chdsp_delay.c
 * @brief   见 chdsp_delay.h。⛔ 门禁状态:未过门。
 */
#include "chdsp_delay.h"
#include <string.h>

int chdsp_delay_init(chdsp_delay_t *dl, chdsp_smp_q4_27_t *storage,
                     uint32_t cap_samples, uint32_t init_delay_samples)
{
    uint32_t i;
    if (storage == 0 || cap_samples == 0u) { return -1; }
    if (init_delay_samples >= cap_samples) { return -1; }
    dl->buf = storage; dl->cap = cap_samples;
    dl->w = 0u; dl->d = init_delay_samples; dl->d_target = init_delay_samples;
    for (i = 0u; i < cap_samples; i++) { storage[i] = chdsp_smp_from_raw(0); }
    return 0;
}

void chdsp_delay_reset(chdsp_delay_t *dl)
{
    uint32_t i;
    dl->w = 0u;
    for (i = 0u; i < dl->cap; i++) { dl->buf[i] = chdsp_smp_from_raw(0); }
}

int chdsp_delay_set(chdsp_delay_t *dl, uint32_t samples)
{
    if (samples >= dl->cap) { return -1; }   /* ⛔ 硬失败,不静默钳位 */
    dl->d_target = samples;
    return 0;
}

chdsp_smp_q4_27_t chdsp_delay_process1(chdsp_delay_t *dl, chdsp_smp_q4_27_t x)
{
    uint32_t r;
    /* 每样本最多走一步,避免延时跳变造成的爆音 */
    if (dl->d < dl->d_target)      { dl->d++; }
    else if (dl->d > dl->d_target) { dl->d--; }

    dl->buf[dl->w] = x;
    r = (dl->w >= dl->d) ? (dl->w - dl->d) : (dl->w + dl->cap - dl->d);
    dl->w++;
    if (dl->w >= dl->cap) { dl->w = 0u; }
    return dl->buf[r];
}

chdsp_smp_q4_27_t chdsp_delay_peek(const chdsp_delay_t *dl, uint32_t n_back)
{
    uint32_t last = (dl->w == 0u) ? (dl->cap - 1u) : (dl->w - 1u);
    uint32_t r = (last >= n_back) ? (last - n_back) : (last + dl->cap - n_back);
    return dl->buf[r];
}
