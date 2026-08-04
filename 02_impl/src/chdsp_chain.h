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
#include "chdsp_notch.h"
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
    /** ⭐ 陷波器组的**槽位簿记**(整改 2026-08-04:PRD §二.5「三种工作模式」的落地)。
     *  原先这里是 `chdsp_notch_mode_t notch_mode[CHDSP_NOTCH_COUNT]` —— 它在 init 里被赋值,
     *  **而全库零消费者**(D6-ao 接线审计)⇒ 三种模式只是一个形状,没有任何行为。
     *  ⛔ 本 bank 只做确定性簿记;**哪个频率要陷波由 AFC 定**(经 hook_afc / request)。 */
    chdsp_notch_bank_t  notch_bank;
    chdsp_alg_hook_t    hook_afc;          /**< 由 adaptive-dsp 决定陷波参数 */
    /* ⑦ ⑧ */
    chdsp_delay_t       delay;
    chdsp_limiter_t     prot;
    /* 遥测 */
    chdsp_sat_t         sat;
    /** ⭐ C-B 的落地点(整改 2026-08-04 · critic m-6 · D6-ao):
     *  **链内(非输出端)饱和 = 设计缺陷,不是运行工况**(前置件 §4.3 消费者 C-B)。
     *  D3 输出的是 smp(Q4.27),**链上没有合法削波点** ⇒ 本通道任何饱和都是链内饱和。
     *  ⇒ `CHDSP_DEBUG_ASSERT=1` 时逐帧累计,供 D14 bring-up 与自验断言消费。
     *  ⛔ 计数而不 abort:abort 会让「饱和行为」本身无法被测(CHK-1 正要测它)。 */
    uint32_t            internal_sat_frames;
} chdsp_in_ch_t;

/**
 * @param delay_buf  ≥ CHDSP_IN_DELAY_MAX_SAMPLES + 1
 * @param look_buf   保护限幅前视缓冲
 * @return 0 = 成功(⛔ 非 0 调用方必须处理)
 */
/** 链内饱和帧数(C-B)。⛔ 出货构建下应恒为 0;非 0 = 增益结构有缺陷,不是"偶尔削一下"。 */
static inline uint32_t chdsp_in_ch_internal_sat_frames(const chdsp_in_ch_t *ch)
{ return ch->internal_sat_frames; }

int  chdsp_in_ch_init(chdsp_in_ch_t *ch, chdsp_smp_q4_27_t *delay_buf, uint32_t delay_cap,
                      chdsp_smp_q4_27_t *look_buf, uint32_t look_cap);
void chdsp_in_ch_reset(chdsp_in_ch_t *ch);
void chdsp_in_ch_process(chdsp_in_ch_t *ch, const chdsp_io_q0_31_t *in,
                         chdsp_smp_q4_27_t *out, uint16_t n);

/* ==========================================================================
 * ✳ AFC 接口(r13)—— 陷波器组接进 D3 真实链路
 * ==========================================================================
 * ⛔⛔ 职责边界(重申):**本层不含 AFC 算法**(CTO 裁定:算法层未定死之前不 C 化)。
 *   这里提供的是**接口**:AFC 在它自己的 hook 回调里调 `chdsp_in_ch_notch_request()`,
 *   由本层做确定性槽位簿记 + 写系数;**哪个频率、什么时候、放多深由 AFC 定**。
 *
 * ⭐ 链序保证(⛔ 这是本接口能工作的前提):D3 的顺序是
 *      … → PEQ×8 → **hook_afc** → **陷波器组** → 延时 → 保护限幅
 *   ⇒ AFC 在 hook 里看到的是 PEQ 之后的信号,而它请求的陷波**在同一块内生效**。
 *   ⇒ 若有人把 hook_afc 挪到陷波之后,本接口就变成"下一块才生效" ⇒ 已由 CHK-A3 机械锁住。
 *
 * ⚠⚠ **给 AFC 实现者的一条硬限定(⛔ 别在这上面建判定)**:
 *   W1-P 实测(`01_design/W1P_CLOSEOUT/01_NHS_numbers.md` §2 + §1.1,⚠ 未过门):
 *     · 头条表口径:**不确定度 = ±0.50 dB(一格),方向未定**;
 *       ⛔ 而**唯一的方向性证据指向【高估】**(检测器漏掉小超量失稳)⇒ **不得读作下界**。
 *     · 单臂检测器偏差实测跨度 **−0.486 … +0.197 dB**(r89 六格)。
 *   ⇒ **∴ 任何拿检测器读数做的【判定】,都要留 ≥0.5 dB 的余量,且不得假定方向。**
 *   ⛔ 去原文核,不要引本注释的转述。
 */

/** 把 AFC 回调挂上,并令 `user` 指向本通道 ⇒ 回调里可直接 `chdsp_in_ch_notch_request()`。 */
void chdsp_in_ch_bind_afc(chdsp_in_ch_t *ch, chdsp_alg_hook_fn fn);

/** 设定陷波器组工作模式(PRD §二.5 三种)。⚠ 语义 [L4/我定的,PRD 未定义,须 CTO 确认]。 */
void chdsp_in_ch_notch_set_mode(chdsp_in_ch_t *ch, chdsp_notch_mode_t mode, uint16_t n_fixed);

/** **上位机路径**:装机时把固定陷波写进指定槽。 */
int  chdsp_in_ch_notch_set_fixed(chdsp_in_ch_t *ch, uint16_t idx,
                                 double f_hz, double q, double depth_db);

/** **AFC 路径**:运行期请求一个陷波(只用动态槽;满则回收 LRU;固定槽永不被占)。 */
int  chdsp_in_ch_notch_request(chdsp_in_ch_t *ch, double f_hz, double q,
                               double depth_db, uint16_t *out_idx);

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
