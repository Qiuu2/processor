/**
 * @file    config.h
 * @brief   ITC 定向音柱 — 全局配置宏定义
 *
 * 平台: ADSP-21569 SHARC+
 * 项目: ITC 16通道定向音柱 (Column Speaker)
 * 版本: v0.1.0
 *
 * 所有算法参数的唯一配置入口，修改此文件即可调整系统参数。
 */

#ifndef ITC_COLUMN_SPEAKER_CONFIG_H
#define ITC_COLUMN_SPEAKER_CONFIG_H

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================
 * 平台标识
 * ============================================================ */
#define PLATFORM_ADSP21569          1
#define PLATFORM_NAME               "ADSP-21569 SHARC+"

/* ============================================================
 * 音频接口参数
 * ============================================================ */
/** 系统采样率 (Hz) */
#define AUDIO_SAMPLE_RATE_HZ        48000u

/** TDM 输入通道数（阵元数量） */
#define AUDIO_INPUT_CHANNELS        16u

/** TDM 输出通道数（通常为1，单声道输出到功放） */
#define AUDIO_OUTPUT_CHANNELS       1u

/** 每帧采样数（每 DMA 中断处理的样点数） */
#define AUDIO_FRAME_SIZE            64u

/** TDM 槽数（= 输入通道数） */
#define TDM_SLOT_COUNT              AUDIO_INPUT_CHANNELS

/** TDM 每槽位宽 (bits) */
#define TDM_SLOT_WIDTH_BITS         32u

/**
 * BCLK = fs × slots × bits = 48000 × 16 × 32 = 24,576,000 Hz
 * 外部 TCXO: 24.576MHz（推荐），或 DSP PLL 分频
 */
#define BCLK_FREQ_HZ                24576000u

/* ============================================================
 * 阵列物理参数
 * ============================================================ */
/** 阵元数（必须与 AUDIO_INPUT_CHANNELS 一致） */
#define ARRAY_NUM_ELEMENTS          16u

/** 阵元间距 (mm) [L1 拆机实测 / DEC-S3-GEOM-01：竞品 L1 拆解实测 d=55mm] */
#define ARRAY_ELEMENT_SPACING_MM    55u

/** 声速 (m/s) @ 20°C */
#define SPEED_OF_SOUND_M_S          343u

/** 最大波束偏转角 (度)，超过此角度波束性能下降 */
#define BEAM_MAX_STEER_ANGLE_DEG    45

/* ============================================================
 * 子带波束形成参数
 * ============================================================ */
/** 子带数量 */
#define SUBBAND_COUNT               4u

/** 各子带抽取率（注：实际抽取率宏 SBx_DECIM 定义在 fir_coeffs.h，与此一致） */
#define SB0_DECIMATION_RATE         16u   /* 0-1kHz   → 3000 Hz 子带率 */
#define SB1_DECIMATION_RATE         8u    /* 1k-2kHz  → 6000 Hz 子带率 */
#define SB2_DECIMATION_RATE         4u    /* 2k-4kHz  → 12000 Hz 子带率 */
#define SB3_DECIMATION_RATE         2u    /* 4k-8kHz  → 24000 Hz 子带率 */

/**
 * ★ F-DSP-02 修复说明：FIR 阶数不再用纸面占位值（旧 31/63 已废弃）。
 * 真实系数与抽头数由 fir_design_verify.py 生成，定义在 fir_coeffs.h：
 *   SB_NUM_TAPS = 437（统一全速率参考核，Kaiser β=5.65，阻带 58-73dB）
 * 落地推荐 dyadic 树形半带核（63 抽头/级），见 dsp_design.md。
 * 以下宏仅为旧接口兼容保留，实际代码用 fir_coeffs.h 的 SB_NUM_TAPS。
 */
#define SB_PROTO_FIR_TAPS_REF       437u  /* 全速率参考核抽头数 */
#define HALFBAND_FIR_TAPS           63u   /* dyadic 树形半带核抽头数 */

/** 分数延迟 FIR 阶数（sinc-windowed Kaiser, β=5.65） */
#define FRAC_DELAY_FIR_ORDER        8u

/**
 * 最大整数延迟 (samples @ 48kHz)
 * = ceil((N_CH-1) × d × sin(45°) / c × fs) + 边界
 * = ceil(15 × 0.055 × 0.707 / 343 × 48000) + 10 = ceil(81.64) + 10 = 92
 *   [L3 解析推算，几何参数 d=0.055 来自 DEC-S3-GEOM-01]
 * 注：broadside-only 工况下分数延迟≈0，此延迟线缓冲实际几乎不用，
 *     但为最坏情况（±45° 偏转）正确性须按 d=0.055 重算。
 */
#define MAX_INT_DELAY_SAMPLES       92u

/* ============================================================
 * 默认波束指向
 * ============================================================ */
/** 默认波束指向角 (度，0 = 正前方) */
#define BEAM_DEFAULT_STEER_ANGLE_DEG    0

/* ============================================================
 * Q 格式定义
 * ============================================================ */
/** Q15: 16bit 定点，范围 [-1, 1)，用于 FIR 系数、波束权重 */
#define Q15_ONE                     32767
#define Q15_MIN                     (-32768)

/** Q31: 32bit 定点，用于 FIR 状态、MAC 累加 */
#define Q31_ONE                     2147483647L
#define Q31_MIN                     (-2147483648L)

/** Q23: 32bit 存储 24bit 音频，范围 [-1, 1) */
#define AUDIO_SAMPLE_Q_FORMAT       23u

/* ============================================================
 * 调试与日志
 * ============================================================ */
/** 使能调试断言（Release 模式关闭） */
#ifndef NDEBUG
#define ITC_DEBUG_ASSERT_ENABLED    1
#else
#define ITC_DEBUG_ASSERT_ENABLED    0
#endif

/** CPU 负载测量（通过 GPIO 翻转引脚，示波器测量） */
#define ENABLE_CPU_LOAD_MEASUREMENT 0   /* 设为 1 启用，仅开发阶段 */

/* ============================================================
 * 编译时静态断言（参数一致性检查）
 * ============================================================ */
#if (AUDIO_INPUT_CHANNELS != ARRAY_NUM_ELEMENTS)
#error "AUDIO_INPUT_CHANNELS must equal ARRAY_NUM_ELEMENTS"
#endif

#if (AUDIO_FRAME_SIZE % SB0_DECIMATION_RATE != 0)
#error "AUDIO_FRAME_SIZE must be divisible by maximum decimation rate (16)"
#endif

#ifdef __cplusplus
}
#endif

#endif /* ITC_COLUMN_SPEAKER_CONFIG_H */
