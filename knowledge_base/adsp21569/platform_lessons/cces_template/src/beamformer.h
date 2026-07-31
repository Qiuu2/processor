/**
 * @file    beamformer.h
 * @brief   Filter-and-Sum 子带波束形成器接口
 *
 * 结构：
 *   4 子带多相分析 → 延迟补偿（整数+分数） → 加权求和 → 多相合成
 *
 * 支持:
 *   - DAS（延迟求和）固定权重波束形成
 *   - 波束指向角实时更新（原子切换，非实时上下文）
 *   - 16 通道输入，1 通道输出
 *
 * 平台: ADSP-21569 SHARC+
 */

#ifndef ITC_BEAMFORMER_H
#define ITC_BEAMFORMER_H

#include <stdint.h>
#include "config.h"
#include "fir.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================
 * 公共数据类型
 * ============================================================ */

/** 波束形成器错误码 */
typedef enum {
    BF_OK              = 0,    /**< 无错误 */
    BF_ERR_NULL_PTR    = -1,   /**< 空指针 */
    BF_ERR_PARAM       = -2,   /**< 参数越界 */
    BF_ERR_NOT_INIT    = -3,   /**< 未初始化 */
} BfError_t;

/** 子带枚举 */
typedef enum {
    BF_SUBBAND_0 = 0,  /**< 500–1kHz  (宽波束) */
    BF_SUBBAND_1 = 1,  /**< 1k–2kHz   (关键指向) */
    BF_SUBBAND_2 = 2,  /**< 2k–4kHz   (高频指向) */
    BF_SUBBAND_3 = 3,  /**< 4k–8kHz   (超高频) */
    BF_SUBBAND_COUNT = SUBBAND_COUNT,
} BfSubband_t;

/**
 * @brief 波束形成器配置参数（初始化时设置）
 */
typedef struct {
    int16_t steer_angle_deg;  /**< 波束指向角，单位：度（-45 ~ +45） */
    int32_t speed_of_sound;   /**< 声速（Q16 格式，343 m/s = 343 << 16） */
} BfConfig_t;

/**
 * @brief 单通道单子带延迟状态
 */
typedef struct {
    IntDelayState int_delay;      /**< 整数延迟环形缓冲 */
    FracDelayFirState frac_delay; /**< 分数延迟 FIR */
} BfChannelDelay;

/**
 * @brief 波束形成器完整状态（静态分配）
 *
 * 内存布局（估算）:
 *   analysis_fir: 4子带 × 16通道 × sizeof(PolyphaseFirState) ≈ 4KB
 *   channel_delay: 4子带 × 16通道 × sizeof(BfChannelDelay)  ≈ 14KB
 *   synth_fir:    4子带 × sizeof(PolyphaseFirState)          ≈ 0.5KB
 *   weights:      4子带 × 16通道 × 2（复数 Q15）              ≈ 256B
 *   Total: ~19KB（L1 SRAM 分配）
 */
typedef struct {
    /* 多相分析滤波器（4子带 × 16通道） */
    PolyphaseFirState analysis_fir[BF_SUBBAND_COUNT][ARRAY_NUM_ELEMENTS];

    /* 延迟补偿（4子带 × 16通道） */
    BfChannelDelay channel_delay[BF_SUBBAND_COUNT][ARRAY_NUM_ELEMENTS];

    /* 多相合成滤波器（4子带 × 1输出通道） */
    PolyphaseFirState synth_fir[BF_SUBBAND_COUNT];

    /* 波束权重（Q15 实部/虚部，4子带 × 16通道） */
    int16_t weight_re[BF_SUBBAND_COUNT][ARRAY_NUM_ELEMENTS]; /**< 实部 Q15 */
    int16_t weight_im[BF_SUBBAND_COUNT][ARRAY_NUM_ELEMENTS]; /**< 虚部 Q15（DAS 模式为 0）*/

    /* 当前配置 */
    BfConfig_t config;

    /* 初始化标志 */
    uint8_t initialized;
} BeamformerState;

/* ============================================================
 * 公共接口
 * ============================================================ */

/**
 * @brief  初始化波束形成器
 *
 * 分配所有滤波器系数，计算延迟参数，清零所有状态。
 * 必须在 audio_callback 使用之前调用（通常在 main() 中）。
 *
 * @param[out] pBf      波束形成器状态（调用者分配）
 * @param[in]  pConfig  初始配置（波束指向角等）
 * @return              BF_OK 或错误码
 *
 * @note 调用时间约 5ms（系数计算），不可在实时上下文调用
 */
BfError_t beamformer_init(BeamformerState *pBf, const BfConfig_t *pConfig);

/**
 * @brief  更新波束指向角
 *
 * 在非实时上下文（主循环或低优先级任务）中更新波束指向。
 * 新系数计算完成后原子切换，下一帧中断自动使用新系数。
 *
 * @param[in,out] pBf             波束形成器状态
 * @param[in]     steer_angle_deg 新指向角（-45 ~ +45 度）
 * @return                        BF_OK 或错误码
 *
 * @note 调用时间约 1ms，不可在音频中断中调用
 */
BfError_t beamformer_set_steer_angle(BeamformerState *pBf,
                                     int16_t          steer_angle_deg);

/**
 * @brief  波束形成处理（每帧）
 *
 * 核心实时处理函数，在 DMA 中断回调中调用。
 * 处理时间约 0.05ms @ 1500 MMAC/s（裕量 26×）。
 *
 * @param[in,out] pBf     波束形成器状态
 * @param[in]     pInput  输入缓冲区 [ARRAY_NUM_ELEMENTS][AUDIO_FRAME_SIZE]，Q23
 * @param[out]    pOutput 输出缓冲区 [AUDIO_FRAME_SIZE]，Q23
 * @return                BF_OK 或错误码
 *
 * @warning 此函数必须在 AUDIO_FRAME_SIZE / AUDIO_SAMPLE_RATE_HZ = 1.33ms 内完成
 * @note    输入/输出缓冲区需对齐到 8 字节边界（DMA 要求）
 */
BfError_t beamformer_process(BeamformerState   *pBf,
                             const int32_t      pInput[][AUDIO_FRAME_SIZE],
                             int32_t           *pOutput);

/**
 * @brief  复位波束形成器状态（清零所有滤波器状态，保留配置）
 * @param[in,out] pBf  波束形成器状态
 */
void beamformer_reset(BeamformerState *pBf);

#ifdef __cplusplus
}
#endif

#endif /* ITC_BEAMFORMER_H */
