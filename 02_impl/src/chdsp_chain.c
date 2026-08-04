/** @file chdsp_chain.c  见 chdsp_chain.h。⛔ 门禁状态:未过门。 */
#include "chdsp_chain.h"
#include <string.h>
#include <math.h>

/* ⛔ 坏版本(出货须全 0,由 CHK-C0 硬闸门核) */
#ifndef CHDSP_BROKEN_CHAIN_ORDER      /* 1 = D4 把 PEQ 放到分频【之前】 */
#  define CHDSP_BROKEN_CHAIN_ORDER 0
#endif
#ifndef CHDSP_BROKEN_XO_POLARITY      /* 1 = 忽略 LR 极性规则 */
#  define CHDSP_BROKEN_XO_POLARITY 0
#endif
#ifndef CHDSP_BROKEN_HPF_AFTER_DYN    /* 1 = D3 把 HPF 放到动态处理【之后】 */
#  define CHDSP_BROKEN_HPF_AFTER_DYN 0
#endif

void chdsp_hook_clear(chdsp_alg_hook_t *h) { h->fn = 0; h->user = 0; h->call_count = 0u; }

void chdsp_hook_run(chdsp_alg_hook_t *h, chdsp_smp_q4_27_t *buf, uint16_t n)
{
    h->call_count++;
    if (h->fn) { h->fn(h->user, buf, n); }   /* 未挂算法 ⇒ 逐位透传 */
}

/* ---------------------------------------------------------------- D3 */
int chdsp_in_ch_init(chdsp_in_ch_t *ch, chdsp_smp_q4_27_t *dbuf, uint32_t dcap,
                     chdsp_smp_q4_27_t *lbuf, uint32_t lcap)
{
    int e = 0; uint16_t i;
    memset(ch, 0, sizeof(*ch));
    ch->polarity = 1;
    ch->trim = chdsp_gain_from_raw(1 << CHDSP_GAIN_FRACBITS);
    chdsp_bq_chain_init(&ch->hpf,   ch->hpf_sec,   CHDSP_IN_HPF_SECTIONS);
    chdsp_bq_chain_init(&ch->peq,   ch->peq_sec,   CHDSP_IN_PEQ_BANDS);
    chdsp_bq_chain_init(&ch->notch, ch->notch_sec, CHDSP_NOTCH_COUNT);
    for (i = 0u; i < CHDSP_NOTCH_COUNT; i++) { ch->notch_mode[i] = CHDSP_NOTCH_MODE_DYNAMIC; }
    chdsp_hook_clear(&ch->hook_aec); chdsp_hook_clear(&ch->hook_anc);
    chdsp_hook_clear(&ch->hook_agc); chdsp_hook_clear(&ch->hook_afc);
    chdsp_gate_init(&ch->gate, -45.0, 4.0, 3.0, 60.0, 1.0, 50.0, 200.0);
    chdsp_comp_init(&ch->comp, -20.0, 3.0, 6.0, 10.0, 100.0, 0.0, CHDSP_DET_RMS);
    e |= chdsp_delay_init(&ch->delay, dbuf, dcap, 0u);
    e |= chdsp_limiter_init(&ch->prot, lbuf, lcap, -1.0, 1.0, 50.0);
    chdsp_sat_reset(&ch->sat);
    return e;
}

void chdsp_in_ch_reset(chdsp_in_ch_t *ch)
{
    chdsp_bq_chain_reset(&ch->hpf); chdsp_bq_chain_reset(&ch->peq);
    chdsp_bq_chain_reset(&ch->notch);
    chdsp_gate_reset(&ch->gate); chdsp_comp_reset(&ch->comp);
    chdsp_delay_reset(&ch->delay); chdsp_limiter_reset(&ch->prot);
    chdsp_sat_reset(&ch->sat);
}

void chdsp_in_ch_process(chdsp_in_ch_t *ch, const chdsp_io_q0_31_t *in,
                         chdsp_smp_q4_27_t *out, uint16_t n)
{
    uint16_t i;
    /* ① 极性 + ② 前置增益 + I/O 域转换 */
    for (i = 0u; i < n; i++) {
        chdsp_smp_q4_27_t s = chdsp_io_to_smp(in[i]);
        if (ch->polarity < 0) { s = chdsp_smp_from_raw(-chdsp_smp_raw(s)); }
        if (ch->mute) { s = chdsp_smp_from_raw(0); }
        out[i] = chdsp_apply_gain(s, ch->trim, &ch->sat);
    }
#if !CHDSP_BROKEN_HPF_AFTER_DYN
    /* ③ HPF —— 在动态处理之前(保护侧链不被隆隆声驱动) */
    chdsp_bq_chain_process(&ch->hpf, out, out, n, &ch->sat);
#endif
    /* ✳ AEC → ✳ ANC(此前只允许 LTI 且系数静态的模块) */
    chdsp_hook_run(&ch->hook_aec, out, n);
    chdsp_hook_run(&ch->hook_anc, out, n);
    /* ④ 门 → ⑤ 压缩 */
    for (i = 0u; i < n; i++) {
        chdsp_gain_q4_27_t g = chdsp_gate_gain1(&ch->gate, out[i], 0);
        out[i] = chdsp_apply_gain(out[i], g, &ch->sat);
        g = chdsp_comp_gain1(&ch->comp, out[i], 0);
        out[i] = chdsp_apply_gain(out[i], g, &ch->sat);
    }
#if CHDSP_BROKEN_HPF_AFTER_DYN
    /* ⛔ 坏版本:HPF 放到【动态处理之后】—— 侧链因此看到未滤的隆隆声。
     * ⚠ 初版把它放在 AEC 钩子之后、门之前 ⇒ **仍在动态之前** ⇒ 变异没实现它声称的缺陷,
     *   因而在杀伤矩阵里"存活"。由杀伤矩阵抓出后改到此处。 */
    chdsp_bq_chain_process(&ch->hpf, out, out, n, &ch->sat);
#endif
    /* ✳ AGC */
    chdsp_hook_run(&ch->hook_agc, out, n);
    /* ⑥ PEQ → ✳ AFC 陷波器组 */
    chdsp_bq_chain_process(&ch->peq, out, out, n, &ch->sat);
    chdsp_hook_run(&ch->hook_afc, out, n);
    chdsp_bq_chain_process(&ch->notch, out, out, n, &ch->sat);
    /* ⑦ 延时 → ⑧ 保护限幅 */
    for (i = 0u; i < n; i++) {
        out[i] = chdsp_delay_process1(&ch->delay, out[i]);
        out[i] = chdsp_limiter_process1(&ch->prot, out[i], &ch->sat, 0);
    }
#if CHDSP_DEBUG_ASSERT
    /* ⭐ C-B 接线(critic m-6):D3 链上没有合法削波点 ⇒ 任何饱和都是【链内饱和】= 设计缺陷。
     * ⛔ 计数不 abort —— abort 会让饱和行为本身无法被测。消费者:D14 bring-up + 自验。 */
    if (chdsp_sat_tripped(&ch->sat)) { ch->internal_sat_frames++; }
#endif
}

/* ---------------------------------------------------------------- D4 */
int chdsp_out_ch_init(chdsp_out_ch_t *ch, const chdsp_out_bufs_t *b)
{
    int e = 0;
    memset(ch, 0, sizeof(*ch));
    ch->polarity = 1;
    ch->gain = chdsp_gain_from_raw(1 << CHDSP_GAIN_FRACBITS);
    ch->mute_cur = chdsp_gain_from_raw(1 << CHDSP_GAIN_FRACBITS);
    ch->mute_step_raw = 0;
    chdsp_bq_chain_init(&ch->xo_hp, ch->xo_hp_sec, CHDSP_OUT_XO_SECTIONS);
    chdsp_bq_chain_init(&ch->xo_lp, ch->xo_lp_sec, CHDSP_OUT_XO_SECTIONS);
    chdsp_bq_chain_init(&ch->peq,   ch->peq_sec,   CHDSP_OUT_PEQ_BANDS);
    ch->xo_polarity_flip = 0;
    e |= chdsp_fir_init(&ch->fir, b->fir_h, b->fir_state, b->fir_taps);
    e |= chdsp_delay_init(&ch->delay, b->delay_buf, b->delay_cap, 0u);
    e |= chdsp_limiter_init(&ch->out_lim, b->lim_look, b->lim_cap, -0.5, 1.0, 50.0);
    e |= chdsp_spk_guard_init(&ch->spk, b->spk_rms, b->spk_rms_cap,
                              b->spk_peak, b->spk_peak_cap,
                              -12.0, 2000.0, -3.0, 0.5);
    chdsp_sat_reset(&ch->sat);
    return e;
}

void chdsp_out_ch_reset(chdsp_out_ch_t *ch)
{
    chdsp_bq_chain_reset(&ch->xo_hp); chdsp_bq_chain_reset(&ch->xo_lp);
    chdsp_bq_chain_reset(&ch->peq);
    chdsp_fir_reset(&ch->fir); chdsp_delay_reset(&ch->delay);
    chdsp_limiter_reset(&ch->out_lim);
    chdsp_limiter_reset(&ch->spk.rms_stage); chdsp_limiter_reset(&ch->spk.peak_stage);
    chdsp_sat_reset(&ch->sat);
}

void chdsp_out_ch_set_mute(chdsp_out_ch_t *ch, int on, double ramp_ms)
{
    double n = ramp_ms * 1e-3 * (double)CHDSP_FS_HZ;
    int32_t tgt = on ? 0 : (1 << CHDSP_GAIN_FRACBITS);
    int32_t cur = chdsp_gain_raw(ch->mute_cur);
    ch->mute = (uint8_t)(on ? 1 : 0);
    ch->mute_step_raw = (n >= 1.0) ? (int32_t)(((double)tgt - (double)cur) / n)
                                   : (tgt - cur);
    if (ch->mute_step_raw == 0) { ch->mute_step_raw = (tgt >= cur) ? 1 : -1; }
}

void chdsp_out_ch_process(chdsp_out_ch_t *ch, const chdsp_smp_q4_27_t *in,
                          chdsp_io_q0_31_t *out, uint16_t n)
{
    static chdsp_smp_q4_27_t tmp[CHDSP_FRAME_SAMPLES];
    uint16_t i;
    const uint16_t m = (n <= CHDSP_FRAME_SAMPLES) ? n : CHDSP_FRAME_SAMPLES;

    /* ① 输出增益 + ② 极性 */
    for (i = 0u; i < m; i++) {
        chdsp_smp_q4_27_t s = in[i];
        if (ch->polarity < 0) { s = chdsp_smp_from_raw(-chdsp_smp_raw(s)); }
        tmp[i] = chdsp_apply_gain(s, ch->gain, &ch->sat);
    }
#if CHDSP_BROKEN_CHAIN_ORDER
    chdsp_bq_chain_process(&ch->peq, tmp, tmp, m, &ch->sat);      /* ⛔ PEQ 提前 */
#endif
    /* ③ 分频:高通支 + 低通支;⚠ 极性由阶数规则定 */
    chdsp_bq_chain_process(&ch->xo_hp, tmp, tmp, m, &ch->sat);
    chdsp_bq_chain_process(&ch->xo_lp, tmp, tmp, m, &ch->sat);
#if !CHDSP_BROKEN_XO_POLARITY
    if (ch->xo_polarity_flip) {
        for (i = 0u; i < m; i++) { tmp[i] = chdsp_smp_from_raw(-chdsp_smp_raw(tmp[i])); }
    }
#endif
#if !CHDSP_BROKEN_CHAIN_ORDER
    /* ④ PEQ —— 在分频之后(阻带大信号先被衰减,省 31.14 dB 链内电平) */
    chdsp_bq_chain_process(&ch->peq, tmp, tmp, m, &ch->sat);
#endif
    /* ⑤ FIR → ⑥ 延时 → ⑦ 输出限幅 → ⑧ 音箱保护 → ⑨ 斜坡静音 */
    for (i = 0u; i < m; i++) {
        chdsp_smp_q4_27_t v = chdsp_fir_process1(&ch->fir, tmp[i], &ch->sat);
        v = chdsp_delay_process1(&ch->delay, v);
        v = chdsp_limiter_process1(&ch->out_lim, v, &ch->sat, 0);
        v = chdsp_spk_guard_process1(&ch->spk, v, &ch->sat);
        /* ⑨ 斜坡静音 */
        {
            int32_t g = chdsp_gain_raw(ch->mute_cur);
            int32_t tgt = ch->mute ? 0 : (1 << CHDSP_GAIN_FRACBITS);
            if (g != tgt) {
                g += ch->mute_step_raw;
                if ((ch->mute_step_raw > 0 && g > tgt) ||
                    (ch->mute_step_raw < 0 && g < tgt)) { g = tgt; }
                ch->mute_cur = chdsp_gain_from_raw(g);
            }
            v = chdsp_apply_gain(v, ch->mute_cur, &ch->sat);
        }
        out[i] = chdsp_smp_to_io(v, &ch->sat);
    }
}
