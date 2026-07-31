/**
 * @file    main.c
 * @brief   ITC 定向音柱 — ADSP-21569 主入口与音频中断回调
 *
 * 功能:
 *   1. 系统初始化（时钟、SPORT/TDM、DMA、功放上电）
 *   2. 波束形成器初始化
 *   3. 启动 DMA Ping-Pong
 *   4. 进入主循环（处理低优先级任务）
 *
 * 中断驱动架构:
 *   DMA 中断 (750Hz, 优先级 0) → audio_callback()
 *     → beamformer_process()
 *     → 输出写入 Pong 缓冲
 *
 * 平台: ADSP-21569 | CCES | SHARC Audio Toolbox
 * 版本: v0.1.0 | 2026-05-26
 */

#include <sys/platform.h>       /* ADSP-21569 系统定义 */
#include <sys/adi_core.h>       /* 内核启动 */
#include <adi_initialize.h>     /* CCES 系统初始化 */
#include <drivers/sport/adi_sport.h>  /* SPORT 驱动 */
#include <services/dma/adi_dma.h>     /* DMA 服务 */

#include "config.h"
#include "beamformer.h"

/* ============================================================
 * DMA 缓冲区定义（L1 SRAM，8字节对齐，pragma section）
 * ============================================================ */

/**
 * TDM 输入 Ping-Pong 缓冲区
 * 布局: [2][N_CH × FRAME]，其中 [0]=ping，[1]=pong
 * 大小: 2 × 16 × 64 × 4 = 8192 字节 = 8KB
 */
#pragma align 8
static int32_t g_rx_buf[2][AUDIO_INPUT_CHANNELS * AUDIO_FRAME_SIZE];

/**
 * TDM 输出 Ping-Pong 缓冲区
 * 布局: [2][1 × FRAME]（单声道输出）
 */
#pragma align 8
static int32_t g_tx_buf[2][AUDIO_OUTPUT_CHANNELS * AUDIO_FRAME_SIZE];

/** 当前活跃缓冲区索引（0=ping, 1=pong），DMA 中断中原子切换 */
static volatile uint8_t g_active_buf = 0u;

/** DMA 中断就绪标志 */
static volatile uint8_t g_audio_ready = 0u;

/* ============================================================
 * 波束形成器全局状态
 * ============================================================ */
static BeamformerState g_beamformer;

/* ============================================================
 * 帧格式化工具（TDM 交织 → 平面数组）
 * ============================================================ */

/**
 * @brief TDM 交织格式 → 平面格式
 *
 * TDM DMA 接收数据为交织格式: [s0_ch0, s0_ch1, ..., s0_ch15, s1_ch0, ...]
 * beamformer_process 需要平面格式: pInput[ch][sample]
 *
 * @param[in]  pTdm     TDM 交织输入 [FRAME × N_CH]
 * @param[out] pPlane   平面格式输出 [N_CH][FRAME]
 */
static void tdm_to_plane(const int32_t *pTdm,
                         int32_t        pPlane[][AUDIO_FRAME_SIZE])
{
    for (uint16_t s = 0u; s < AUDIO_FRAME_SIZE; s++) {
        for (uint16_t ch = 0u; ch < AUDIO_INPUT_CHANNELS; ch++) {
            /* TDM 输入: 高24bit有效（左对齐），转Q23（右移8） */
            pPlane[ch][s] = pTdm[s * AUDIO_INPUT_CHANNELS + ch] >> 8;
        }
    }
}

/**
 * @brief 平面格式 → TDM 交织输出
 *
 * @param[in]  pOut   波束形成输出 [FRAME]，Q23
 * @param[out] pTdm   TDM 交织输出 [FRAME × N_CH]（填充slot 0，其他置零）
 */
static void plane_to_tdm(const int32_t *pOut, int32_t *pTdm)
{
    for (uint16_t s = 0u; s < AUDIO_FRAME_SIZE; s++) {
        /* Slot 0: 波束形成输出，Q23 → 左对齐 32bit（高24bit有效） */
        pTdm[s * AUDIO_INPUT_CHANNELS + 0] = pOut[s] << 8;
        /* 其他 Slot: 置零（或复制用于调试） */
        for (uint16_t ch = 1u; ch < AUDIO_INPUT_CHANNELS; ch++) {
            pTdm[s * AUDIO_INPUT_CHANNELS + ch] = 0;
        }
    }
}

/* ============================================================
 * 音频处理回调（DMA 中断调用，优先级 0）
 * ============================================================ */

/**
 * @brief 音频处理回调（每帧 1.33ms 调用一次）
 *
 * 在 DMA 中断服务例程（ISR）中调用。
 * 执行时间约 0.05ms，裕量 26×。
 *
 * @param[in] buf_idx  完成的 DMA 缓冲区索引（0 or 1）
 */
static void audio_callback(uint8_t buf_idx)
{
    /* 平面格式输入缓冲（静态分配，避免栈大数组） */
    static int32_t s_input_plane[AUDIO_INPUT_CHANNELS][AUDIO_FRAME_SIZE];
    static int32_t s_output[AUDIO_FRAME_SIZE];

    /* CPU 负载测量：拉高 GPIO（调试阶段） */
#if ENABLE_CPU_LOAD_MEASUREMENT
    /* *pREG_PORTF_FER |= 0x0001; */  /* 设置 GPIO 为输出 */
    /* *pREG_PORTF_DATA |= 0x0001; */ /* GPIO 拉高 */
#endif

    /* 1. 将 TDM 交织格式转为平面格式 */
    tdm_to_plane(g_rx_buf[buf_idx], s_input_plane);

    /* 2. 波束形成处理 */
    BfError_t err = beamformer_process(&g_beamformer,
                                       (const int32_t (*)[AUDIO_FRAME_SIZE])s_input_plane,
                                       s_output);

    /* 3. 将平面输出转为 TDM 交织格式，写入对面缓冲 */
    uint8_t out_idx = buf_idx ^ 1u;  /* 写入对面缓冲（ping写pong，pong写ping）*/
    plane_to_tdm(s_output, g_tx_buf[out_idx]);

    /* 错误处理（调试阶段） */
    (void)err;

#if ENABLE_CPU_LOAD_MEASUREMENT
    /* *pREG_PORTF_DATA &= ~0x0001; */ /* GPIO 拉低，测量高电平时间 = 处理时间 */
#endif

    g_audio_ready = 1u;
}

/* ============================================================
 * SPORT/DMA 初始化（占位，实际使用 CCES SPORT 驱动）
 * ============================================================ */

/**
 * @brief 初始化 SPORT0 为 TDM-16 接收模式
 *
 * 配置:
 *   - TDM-16（16槽位，32bit/槽）
 *   - BCLK: 24.576 MHz（外部 TCXO 输入）
 *   - FSYNC: 48kHz（外部）
 *   - DMA Ping-Pong: g_rx_buf[0] 和 g_rx_buf[1]
 *
 * @note 实际 CCES 驱动调用见 SHARC Audio Toolbox 示例
 *       此处为框架示意，需替换为 adi_sport_Open() 等 API
 */
static void sport_tdm_init(void)
{
    /*
     * 伪代码 / 框架（CCES SPORT 驱动 API）:
     *
     * ADI_SPORT_HANDLE hSport;
     * adi_sport_Open(0, ADI_HALF_SPORT_A, ADI_SPORT_DIR_RX,
     *                ADI_SPORT_I2S_MODE_NONE,
     *                ADI_SPORT_TDM_MODE, &hSport);
     *
     * adi_sport_ConfigData(hSport, ADI_SPORT_DTYPE_SIGN_FILL,
     *                      32, false, false, false);
     * adi_sport_SetTDMChans(hSport, 16);
     *
     * // 注册 DMA 完成回调
     * adi_sport_RegisterCallback(hSport, sport_dma_callback, NULL);
     *
     * // 提交双缓冲
     * adi_sport_SubmitBuffer(hSport, g_rx_buf[0],
     *                        sizeof(g_rx_buf[0]));
     * adi_sport_SubmitBuffer(hSport, g_rx_buf[1],
     *                        sizeof(g_rx_buf[1]));
     *
     * adi_sport_Enable(hSport, true);
     */
    (void)g_rx_buf;
    (void)g_tx_buf;
}

/* ============================================================
 * 主函数
 * ============================================================ */

int main(void)
{
    /* 1. CCES 系统初始化（时钟、电源、缓存） */
    adi_initComponents();

    /* 2. 初始化波束形成器（前向，0度，声速 343m/s） */
    BfConfig_t bf_cfg = {
        .steer_angle_deg = BEAM_DEFAULT_STEER_ANGLE_DEG,
        .speed_of_sound  = SPEED_OF_SOUND_M_S << 16,  /* Q16 */
    };
    BfError_t err = beamformer_init(&g_beamformer, &bf_cfg);
    if (err != BF_OK) {
        /* 初始化失败：死循环（实际产品应有错误指示 LED） */
        while (1) { /* 故障：检查 err 值 */ }
    }

    /* 3. 初始化 SPORT/TDM/DMA */
    sport_tdm_init();

    /* 4. 进入主循环（低优先级任务） */
    while (1)
    {
        /* 等待音频帧处理完成标志（可选：用于调试输出） */
        if (g_audio_ready) {
            g_audio_ready = 0u;

            /*
             * 主循环任务（低优先级，非实时）:
             *   - 波束指向角更新（来自外部控制接口）
             *   - 状态监控（CPU 负载、溢出检测）
             *   - 串口/UART 控制接口
             *
             * 示例: 接收波束指向命令
             * int16_t new_angle = receive_steer_command();
             * if (new_angle != g_beamformer.config.steer_angle_deg) {
             *     beamformer_set_steer_angle(&g_beamformer, new_angle);
             * }
             */
        }

        /* 低功耗等待（SHARC IDLE 指令） */
        asm("idle;");
    }

    /* 不可达 */
    return 0;
}
