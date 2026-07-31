/**
 * @file    beamformer.c
 * @brief   Filter-and-Sum 子带波束形成器实现
 *
 * 算法流程（每帧）:
 *   1. 多相 FIR 分析滤波（4子带 × 16通道，抽取至子带速率）
 *   2. 整数延迟补偿（环形缓冲）
 *   3. 分数延迟补偿（8阶 sinc FIR）
 *   4. 加权求和（DAS: 等幅相位对齐，16通道→1通道）
 *   5. 多相 FIR 合成（4子带重建，内插至全带 48kHz）
 *
 * 平台: ADSP-21569 SHARC+ | fs=48kHz | 帧=64samples
 * 算力预算: 58.1 MMAC/s（21569 保守口径 1500 MMAC/s，裕量 26×）
 * 延迟预算: < 1.33ms（双缓冲，DMA ping-pong）
 *
 * 定点格式:
 *   输入/输出: Q23 (24bit音频)
 *   FIR 系数:  Q15
 *   FIR 状态:  Q31
 *   MAC 累加:  Q46（64bit）→ 移位至 Q31 输出
 *   波束权重:  Q15（实部），DAS 模式虚部为 0
 */

#include "beamformer.h"
#include "fir.h"
#include "config.h"
#include "fir_coeffs.h"   /* ★ F-DSP-02: 真实 scipy Kaiser 设计系数（替换占位） */
#include <string.h>
#include <stdint.h>

/* ============================================================
 * 静态系数表 — F-DSP-02 修复
 *
 * 系数来自 fir_coeffs.h，由 fir_design_verify.py 用 scipy Kaiser 真实设计：
 *   互补差分低通滤波器组（complementary differential filterbank）
 *     SB0 = LP(1k)         实测阻带 -67dB
 *     SB1 = LP(2k)-LP(1k)  实测阻带 -58dB
 *     SB2 = LP(4k)-LP(2k)  实测阻带 -68dB
 *     SB3 = LP(8k)-LP(4k)  实测阻带 -73dB
 *   求和恒等 = LP(8k) → 通带(0.5-7kHz)重建平坦 0.004dB（freqz 验证）。
 *
 * 注: fir_coeffs.h 提供"全速率参考核"(437抽头)。落地推荐 dyadic 树形
 *     抽取实现（见 dsp_design.md），半带核更短、算力 56 MMAC/s。
 *     此处沿用全速率核作为可直接运行的功能正确性参考实现。
 * ============================================================ */

/* 系数表汇总（指向 fir_coeffs.h 中的真实系数） */
static const int16_t * const g_sb_coef[SUBBAND_COUNT] = {
    g_sb0_coef, g_sb1_coef, g_sb2_coef, g_sb3_coef
};

/* 各子带抽取率表（来自 fir_coeffs.h: SBx_DECIM） */
static const uint16_t g_sb_decim[SUBBAND_COUNT] = {
    SB0_DECIM, SB1_DECIM, SB2_DECIM, SB3_DECIM
};

/* 各子带 FIR 阶数表（统一 SB_NUM_TAPS-1 阶） */
static const uint16_t g_sb_order[SUBBAND_COUNT] = {
    SB_NUM_TAPS - 1, SB_NUM_TAPS - 1, SB_NUM_TAPS - 1, SB_NUM_TAPS - 1
};

/* ============================================================
 * 静态状态缓冲区（L1 SRAM 分配，零初始化）
 * 使用 section pragma 放入 L1 SRAM（SHARC 语法）
 * 状态深度需 >= SB_NUM_TAPS（437）
 * ============================================================ */

/* 分析 FIR 状态（每子带×每通道独立） */
static int32_t g_analysis_state[SUBBAND_COUNT][ARRAY_NUM_ELEMENTS][SB_NUM_TAPS];

/* 合成 FIR 状态（每子带×1通道） */
static int32_t g_synth_state[SUBBAND_COUNT][SB_NUM_TAPS];

/* ============================================================
 * 内部工具函数
 * ============================================================ */

/**
 * 计算各通道的整数/分数延迟（DAS 波束指向）
 *
 * 对于 DAS 波束形成，第 m 通道的延迟为:
 *   tau_m = m × d × sin(theta) / c   （秒）
 *   tau_m_samples = tau_m × fs       （采样数）
 *   int_delay  = floor(tau_m_samples)
 *   frac_delay = tau_m_samples - int_delay  (0 ~ 1)
 *
 * 为避免浮点运算，此函数可接受浮点（在非实时配置阶段调用）
 *
 * @param[in]  steer_angle_deg  波束指向角（度）
 * @param[out] int_delays       各通道整数延迟表 [N_CH]（samples）
 * @param[out] frac_delays_q15  各通道分数延迟 Q15 [N_CH]
 */
static void compute_delays(int16_t   steer_angle_deg,
                           uint16_t *int_delays,
                           int16_t  *frac_delays_q15)
{
    /* 这里允许浮点计算：系数更新是非实时路径 */
    float theta_rad = (float)steer_angle_deg * 3.14159265f / 180.0f;
    float sin_theta = 0.0f;

    /* 简单 sin 近似（非实时路径，可直接使用 math.h sinf） */
    /* #include <math.h> 并启用 CCES 数学库 */
    /* sin_theta = sinf(theta_rad); */
    /* 占位：线性近似（小角度），实际替换为 sinf() */
    sin_theta = theta_rad - (theta_rad * theta_rad * theta_rad) / 6.0f;

    float d_m  = (float)ARRAY_ELEMENT_SPACING_MM / 1000.0f;  /* m */
    float c_ms = (float)SPEED_OF_SOUND_M_S;                   /* m/s */
    float fs   = (float)AUDIO_SAMPLE_RATE_HZ;

    for (uint16_t m = 0u; m < ARRAY_NUM_ELEMENTS; m++) {
        float tau_samp = (float)m * d_m * sin_theta / c_ms * fs;

        /* 负延迟：取绝对值并反向（或对称居中处理，此处简化） */
        if (tau_samp < 0.0f) tau_samp = -tau_samp;

        int_delays[m]      = (uint16_t)tau_samp;
        float frac         = tau_samp - (float)int_delays[m];
        frac_delays_q15[m] = (int16_t)(frac * 32768.0f);
    }
}

/**
 * 计算 DAS 权重（等幅，仅相位/延迟补偿，归一化为 1/N_CH）
 *
 * DAS 权重: w[m] = (1/N_CH) × exp(-j × 2π × fc × tau_m)
 * 对于纯延迟补偿方式，权重为实数 1/N_CH（相位已由延迟补偿）
 */
static void compute_weights(BeamformerState *pBf)
{
    /* DAS: 等幅权重，实部 = 1/N_CH (Q15)，虚部 = 0 */
    int16_t w_re = (int16_t)(32767 / ARRAY_NUM_ELEMENTS);  /* 1/16 in Q15 ≈ 2048 */

    for (int sb = 0; sb < SUBBAND_COUNT; sb++) {
        for (int m = 0; m < ARRAY_NUM_ELEMENTS; m++) {
            pBf->weight_re[sb][m] = w_re;
            pBf->weight_im[sb][m] = 0;
        }
    }
}

/* ============================================================
 * 公共接口实现
 * ============================================================ */

BfError_t beamformer_init(BeamformerState *pBf, const BfConfig_t *pConfig)
{
    if (pBf == NULL || pConfig == NULL) {
        return BF_ERR_NULL_PTR;
    }
    if (pConfig->steer_angle_deg < -45 || pConfig->steer_angle_deg > 45) {
        return BF_ERR_PARAM;
    }

    /* 清零所有状态 */
    memset(pBf, 0, sizeof(BeamformerState));
    pBf->config = *pConfig;

    /* 初始化各子带分析 FIR（16通道） */
    for (int sb = 0; sb < SUBBAND_COUNT; sb++) {
        uint16_t ntaps  = g_sb_order[sb] + 1u;
        uint16_t decim  = g_sb_decim[sb];

        for (int ch = 0; ch < ARRAY_NUM_ELEMENTS; ch++) {
            polyphase_fir_init(&pBf->analysis_fir[sb][ch],
                               g_sb_coef[sb],
                               g_analysis_state[sb][ch],
                               ntaps,
                               decim);
        }

        /* 初始化合成 FIR（1通道，内插，与分析对称） */
        polyphase_fir_init(&pBf->synth_fir[sb],
                           g_sb_coef[sb],
                           g_synth_state[sb],
                           ntaps,
                           decim);
    }

    /* 计算延迟参数并初始化延迟滤波器 */
    uint16_t int_delays[ARRAY_NUM_ELEMENTS];
    int16_t  frac_delays_q15[ARRAY_NUM_ELEMENTS];
    compute_delays(pConfig->steer_angle_deg, int_delays, frac_delays_q15);

    for (int sb = 0; sb < SUBBAND_COUNT; sb++) {
        for (int ch = 0; ch < ARRAY_NUM_ELEMENTS; ch++) {
            int_delay_set(&pBf->channel_delay[sb][ch].int_delay, int_delays[ch]);
            frac_delay_fir_reset(&pBf->channel_delay[sb][ch].frac_delay);
            frac_delay_fir_set_delay(&pBf->channel_delay[sb][ch].frac_delay,
                                     frac_delays_q15[ch]);
        }
    }

    /* 计算 DAS 权重 */
    compute_weights(pBf);

    pBf->initialized = 1u;
    return BF_OK;
}

BfError_t beamformer_set_steer_angle(BeamformerState *pBf,
                                     int16_t          steer_angle_deg)
{
    if (pBf == NULL || !pBf->initialized)        return BF_ERR_NOT_INIT;
    if (steer_angle_deg < -45 || steer_angle_deg > 45) return BF_ERR_PARAM;

    uint16_t int_delays[ARRAY_NUM_ELEMENTS];
    int16_t  frac_delays_q15[ARRAY_NUM_ELEMENTS];
    compute_delays(steer_angle_deg, int_delays, frac_delays_q15);

    /* 非实时上下文：直接更新（无需双缓冲，调用者保证不在中断中调用） */
    for (int sb = 0; sb < SUBBAND_COUNT; sb++) {
        for (int ch = 0; ch < ARRAY_NUM_ELEMENTS; ch++) {
            int_delay_set(&pBf->channel_delay[sb][ch].int_delay, int_delays[ch]);
            frac_delay_fir_set_delay(&pBf->channel_delay[sb][ch].frac_delay,
                                     frac_delays_q15[ch]);
        }
    }

    pBf->config.steer_angle_deg = steer_angle_deg;
    return BF_OK;
}

/**
 * @brief 波束形成核心处理（每帧）
 *
 * 处理流程:
 *   for each 子带 sb in {SB0, SB1, SB2, SB3}:
 *     for each 采样组 (FRAME/M 次输出):
 *       for each 通道 ch:
 *         1. 多相分析抽取 → sub_samp[ch]
 *         2. 整数延迟补偿 → delayed[ch]
 *         3. 分数延迟补偿 → fd_delayed[ch]
 *       4. 加权求和 → beam_out[sb]
 *     end
 *   end
 *   合成上采样 → 全带输出
 */
BfError_t beamformer_process(BeamformerState   *pBf,
                             const int32_t      pInput[][AUDIO_FRAME_SIZE],
                             int32_t           *pOutput)
{
    if (pBf == NULL || pInput == NULL || pOutput == NULL) {
        return BF_ERR_NULL_PTR;
    }
    if (!pBf->initialized) {
        return BF_ERR_NOT_INIT;
    }

    /* 子带输出帧缓冲（每子带，子带速率下的帧大小） */
    /* 最大子带帧 = FRAME / min_decim = 64/2 = 32 samples */
    int32_t subband_out[SUBBAND_COUNT][AUDIO_FRAME_SIZE]; /* 保守大小 */
    int32_t synth_buf[AUDIO_FRAME_SIZE];

    /* 清零输出 */
    memset(pOutput, 0, AUDIO_FRAME_SIZE * sizeof(int32_t));

    /* ---- 各子带处理 ---- */
    for (int sb = 0; sb < SUBBAND_COUNT; sb++) {
        uint16_t M       = g_sb_decim[sb];
        uint16_t sb_len  = AUDIO_FRAME_SIZE / M;  /* 子带帧长度 */

        /* 逐子带帧样点处理 */
        for (uint16_t s = 0u; s < sb_len; s++) {
            int32_t  in_block[16];   /* M 个输入样点（单通道，单多相周期） */
            int64_t  acc = 0;        /* 加权求和累加器，Q46 */

            /* 通道循环：分析 + 延迟补偿 + 加权求和 */
            for (int ch = 0; ch < ARRAY_NUM_ELEMENTS; ch++) {
                /* 取出 M 个连续输入样点（Q23 → Q31） */
                for (uint16_t i = 0u; i < M; i++) {
                    in_block[i] = pInput[ch][s * M + i] << 8;  /* Q23 → Q31 */
                }

                /* 步骤 1: 多相 FIR 分析抽取 */
                int32_t sub_samp = polyphase_fir_decimate(&pBf->analysis_fir[sb][ch],
                                                          in_block);

                /* 步骤 2: 整数延迟补偿 */
                int32_t delayed = int_delay_process(&pBf->channel_delay[sb][ch].int_delay,
                                                    sub_samp);

                /* 步骤 3: 分数延迟补偿（8阶 sinc FIR） */
                int32_t fd_out  = frac_delay_fir_process(&pBf->channel_delay[sb][ch].frac_delay,
                                                          delayed);

                /* 步骤 4a: 加权（DAS: w_re × fd_out，虚部为 0） */
                /* acc += w[ch] × fd_out，Q15 × Q31 → Q46 */
                acc += (int64_t)pBf->weight_re[sb][ch] * (int64_t)fd_out;
            }

            /* 步骤 4b: 归一化并存储子带输出（Q46 → Q31，右移15） */
            subband_out[sb][s] = (int32_t)(acc >> 15);
        }
    }

    /* ---- 多相合成（4子带 → 全带 48kHz）---- */
    memset(synth_buf, 0, sizeof(synth_buf));

    for (int sb = 0; sb < SUBBAND_COUNT; sb++) {
        uint16_t M      = g_sb_decim[sb];
        uint16_t sb_len = AUDIO_FRAME_SIZE / M;
        int32_t  interp_out[16];  /* 单次内插输出 M 个样点 */

        for (uint16_t s = 0u; s < sb_len; s++) {
            /* 步骤 5: 多相 FIR 内插（1 → M 样点） */
            polyphase_fir_interpolate(&pBf->synth_fir[sb],
                                      subband_out[sb][s],
                                      interp_out);

            /* 累加各子带合成结果 */
            for (uint16_t i = 0u; i < M; i++) {
                /* Q31 → Q23 右移 8，累加各子带 */
                pOutput[s * M + i] += interp_out[i] >> 8;
            }
        }
    }

    /* 输出饱和保护（Q23 范围 ±8388607） */
    for (uint16_t n = 0u; n < AUDIO_FRAME_SIZE; n++) {
        if (pOutput[n] >  8388607)  pOutput[n] =  8388607;
        if (pOutput[n] < -8388608)  pOutput[n] = -8388608;
    }

    return BF_OK;
}

void beamformer_reset(BeamformerState *pBf)
{
    if (pBf == NULL) return;

    BfConfig_t saved_config = pBf->config;
    memset(g_analysis_state, 0, sizeof(g_analysis_state));
    memset(g_synth_state,    0, sizeof(g_synth_state));

    /* 重置延迟状态 */
    for (int sb = 0; sb < SUBBAND_COUNT; sb++) {
        for (int ch = 0; ch < ARRAY_NUM_ELEMENTS; ch++) {
            frac_delay_fir_reset(&pBf->channel_delay[sb][ch].frac_delay);
            /* 整数延迟缓冲区清零（保留延迟值） */
            memset(pBf->channel_delay[sb][ch].int_delay.buf, 0,
                   sizeof(pBf->channel_delay[sb][ch].int_delay.buf));
        }
    }

    pBf->config = saved_config;
}
