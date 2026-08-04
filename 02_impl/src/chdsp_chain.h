/**
 * @file    chdsp_chain.h
 * @brief   D3 输入通道链 / D4 输出通道链 —— 按 D3D4_CHANNEL_CHAIN_v0.1 §1/§2 的链序
 *
 * ⛔ 门禁状态:未过门(2026-08-04)。作者:channel-dsp(第 1 实例)
 *
 * ---------------------------------------------------------------------------
 * D3 输入链(✳ = 算法层插入点,归 adaptive-dsp,**本实现只留钩子不实现**)
 * ---------------------------------------------------------------------------
 *   ① 极性 → ② 前置增益 → ③ HPF
 *      →〔✳ AEC〕→〔✳ ANC〕
 *   → ④ 门/扩展器 → ⑤ 压缩器 →〔✳ AGC〕
 *   → ⑥ PEQ×8 →〔✳ AFC 陷波器组〕
 *   → ⑦ 延时 → ⑧ 保护限幅 → (去矩阵)
 *
 * ⚠ **我给 AEC 的硬约束(交 adaptive-dsp / 架构侧)**:
 *   **AEC 之前只允许【线性时不变、且系数不随时间改变】的模块。**
 *   ③ HPF 是 LTI ⇒ 可在 AEC 之前;④⑤ 与 ✳AGC/✳AFC 都是非线性或时变 ⇒ 必须在 AEC 之后。
 *   ⚠ ② 前置增益若**运行时可变**(推子拖动)严格说也是时变 ⇒ 本实现在增益变化时
 *     置 `evt_gain_changed`,由 AEC 侧决定是否冻结/重收敛。**该信号的语义归架构侧。**
 *
 * ---------------------------------------------------------------------------
 * D4 输出链
 * ---------------------------------------------------------------------------
 *   (矩阵求和)→ ① 输出增益 → ② 极性 → ③ 分频(HPF+LPF)→ ④ PEQ×10
 *   → ⑤ 线性相位 FIR → ⑥ 延时 → ⑦ 输出限幅 → ⑧ 音箱保护限幅 → ⑨ 斜坡静音 → DAC
 *
 * ⚠ **分频必须在 PEQ 之前**:二者总传函严格相等(差 2.8e−14 dB)⇒ 顺序不能用传函选;
 *   选它的唯一理由是**定点链内电平** —— 阻塞带激励下省 **31.14 dB**(实测 EXP-1a)。
 * ⚠ **LR 分频的求和极性由阶数决定**(mod 4 == 2 ⇒ 须反相),由
 *   `chdsp_xover_needs_polarity_flip()` 给出;写反 ⇒ 分频点 87.72 dB 深谷。
 */

#ifndef CHDSP_CHAIN_H
#define CHDSP_CHAIN_H

#include "chdsp_config.h"
#include "chdsp_biquad.h"
#include "chdsp_dynamics.h"
#include "chdsp_fir.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ==========================================================================
 * ✳ 算法层插入点的钩子 —— **只有形状,没有实现**
 * ==========================================================================
 * ⛔ CTO 裁定:NHS 控制路径四个缺陷未清之前不 C 化 ⇒ 本项目里这些一律为
 *    「透传 + 计数」的占位。**⛔ 不得在本文件里实现任何自适应算法。**
 * @param user  由 adaptive-dsp 提供的上下文;为 NULL 时占位实现逐位透传。
 */
typedef void (*chdsp_alg_hook_fn)(void *user, chdsp_smp_q4_27_t *buf, uint16_t n);

typedef struct {
    chdsp_alg_hook_fn fn;
    void             *user;
    uint32_t          call_count;   /**< 遥测:被调用次数(证明钩子真的在链上) */
} chdsp_alg_hook_t;

void chdsp_hook_clear(chdsp_alg_hook_t *h);
void chdsp_hook_run(chdsp_alg_hook_t *h, chdsp_smp_q4_27_t *buf, uint16_t n);

/* ==========================================================================
 * D3 输入通道
 * ========================================================================== */
typedef struct {
    /* ① ② */
    int8_t              polarity;          /**< +1 / −1 */
    chdsp_gain_q4_27_t  trim;
    uint8_t             mute;
    uint8_t             evt_gain_changed;  /**< 增益/极性变更事件(供 ✳AEC 消费) */
    /* ③ HPF */
    chdsp_bq_t          hpf_sec[CHDSP_IN_HPF_SECTIONS];
    chdsp_bq_chain_t    hpf;
    /* ✳ */
    chdsp_alg_hook_t    hook_aec;
    chdsp_alg_hook_t    hook_anc;
    /* ④ ⑤ */
    chdsp_gate_t        gate;
    chdsp_comp_t        comp;
    /* ✳ */
    chdsp_alg_hook_t    hook_agc;
    /* ⑥ PEQ */
    chdsp_bq_t          peq_sec[CHDSP_IN_PEQ_BANDS];
    chdsp_bq_chain_t    peq;
    /* ✳ AFC 陷波器组:形状留够 CHDSP_NOTCH_COUNT 节 + 三种模式 */
    chdsp_bq_t          notch_sec[CHDSP_NOTCH_COUNT];
    chdsp_bq_chain_t    notch;
    chdsp_notch_mode_t  notch_mode[CHDSP_NOTCH_COUNT];
    chdsp_alg_hook_t    hook_afc;          /**< 由 adaptive-dsp 决定陷波参数 */
    /* ⑦ ⑧ */
    chdsp_delay_t       delay;
    chdsp_limiter_t     prot;
    /* 遥测 */
    chdsp_sat_t         sat;
} chdsp_in_ch_t;

/**
 * @param delay_buf  ≥ CHDSP_IN_DELAY_MAX_SAMPLES + 1
 * @param look_buf   保护限幅前视缓冲
 * @return 0 = 成功(⛔ 非 0 调用方必须处理)
 */
int  chdsp_in_ch_init(chdsp_in_ch_t *ch, chdsp_smp_q4_27_t *delay_buf, uint32_t delay_cap,
                      chdsp_smp_q4_27_t *look_buf, uint32_t look_cap);
void chdsp_in_ch_reset(chdsp_in_ch_t *ch);
void chdsp_in_ch_process(chdsp_in_ch_t *ch, const chdsp_io_q0_31_t *in,
                         chdsp_smp_q4_27_t *out, uint16_t n);

/* ==========================================================================
 * D4 输出通道
 * ========================================================================== */
typedef struct {
    /* ① ② */
    int8_t              polarity;
    chdsp_gain_q4_27_t  gain;
    uint8_t             mute;             /**< 目标态;实际走斜坡 */
    chdsp_gain_q4_27_t  mute_cur;         /**< 斜坡当前值 */
    int32_t             mute_step_raw;    /**< 每样本步进(Q4.27 raw) */
    /* ③ 分频:高通支 + 低通支各一条级联 */
    chdsp_bq_t          xo_hp_sec[CHDSP_OUT_XO_SECTIONS];
    chdsp_bq_t          xo_lp_sec[CHDSP_OUT_XO_SECTIONS];
    chdsp_bq_chain_t    xo_hp, xo_lp;
    int8_t              xo_polarity_flip; /**< 由 chdsp_xover_needs_polarity_flip() 定 */
    /* ④ */
    chdsp_bq_t          peq_sec[CHDSP_OUT_PEQ_BANDS];
    chdsp_bq_chain_t    peq;
    /* ⑤ */
    chdsp_fir_t         fir;
    /* ⑥ ⑦ ⑧ */
    chdsp_delay_t       delay;
    chdsp_limiter_t     out_lim;
    chdsp_spk_guard_t   spk;
    chdsp_sat_t         sat;
} chdsp_out_ch_t;

typedef struct {                 /**< 输出通道所需的全部缓冲(调用方静态分配) */
    chdsp_smp_q4_27_t *delay_buf;   uint32_t delay_cap;
    chdsp_smp_q4_27_t *lim_look;    uint32_t lim_cap;
    chdsp_smp_q4_27_t *spk_rms;     uint32_t spk_rms_cap;
    chdsp_smp_q4_27_t *spk_peak;    uint32_t spk_peak_cap;
    chdsp_smp_q4_27_t *fir_state;   uint16_t fir_taps;
    const chdsp_coef_q4_27_t *fir_h;
} chdsp_out_bufs_t;

int  chdsp_out_ch_init(chdsp_out_ch_t *ch, const chdsp_out_bufs_t *b);
void chdsp_out_ch_reset(chdsp_out_ch_t *ch);
void chdsp_out_ch_process(chdsp_out_ch_t *ch, const chdsp_smp_q4_27_t *in,
                          chdsp_io_q0_31_t *out, uint16_t n);

/** 设置静音(斜坡,ms)。⚠ 硬切会爆音 ⇒ 本接口不提供硬切。 */
void chdsp_out_ch_set_mute(chdsp_out_ch_t *ch, int on, double ramp_ms);

/* ==========================================================================
 * 算力自报(解析估计,⛔ 非实测;单通道单样本)
 * ==========================================================================
 * D3 = HPF(2 节)+ PEQ(8 节)+ 陷波(8 节)= 18 节 × 7 乘  = 126 乘
 *    + 门 8 乘 + 压限 9 乘 + 保护限幅 9 乘 + 增益 1 乘     =  27 乘
 *    ⇒ **≈ 153 乘 + 约 300 其它 op / 样本 / 通道** [L3/解析]
 * D4 = 分频(最多 8 节)+ PEQ(10 节)= 18 节 × 7 乘        = 126 乘
 *    + FIR(N 抽头)                                        =   N 乘
 *    + 输出限幅 9 + 音箱保护 18 + 增益 1                    =  28 乘
 *    ⇒ **≈ 154 + N 乘 / 样本 / 通道**(N=256 ⇒ 410 乘) [L3/解析]
 * ⇒ 8 进 8 出全开:(153 + 410) × 8 × 48000 ≈ **216 M乘/s** [L3/解析]
 * ⚠⚠ **这是【乘法次数】,不是【周期数】。** SHARC+ 的 cyc/MAC 待 W1-C 微基准;
 *   厂家锚点 2.5 cyc/biquad 是**浮点**数(EE-408 基准代码为 float),定点值未测。
 *   ⛔ 不得据本节数字做任何选型/承诺。
 */
#define CHDSP_IN_CH_MUL_PER_SAMPLE   (CHDSP_IN_BIQUADS_PER_CH * CHDSP_BQ_MUL_PER_SEC_PER_SAMPLE \
                                      + CHDSP_GATE_MUL_PER_SAMPLE + 2 * CHDSP_COMP_MUL_PER_SAMPLE + 1)
#define CHDSP_OUT_CH_MUL_PER_SAMPLE  (CHDSP_OUT_BIQUADS_PER_CH * CHDSP_BQ_MUL_PER_SEC_PER_SAMPLE \
                                      + CHDSP_OUT_FIR_TAPS + 3 * CHDSP_COMP_MUL_PER_SAMPLE + 1)

#ifdef __cplusplus
}
#endif
#endif /* CHDSP_CHAIN_H */
