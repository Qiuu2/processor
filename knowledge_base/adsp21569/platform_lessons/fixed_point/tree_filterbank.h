/**
 * @file    tree_filterbank.h
 * @brief   4 子带 dyadic 树形半带 FIR 分频结构（差分金字塔，PR 精确）
 *
 * 这是 DEC-S2-002 锁定的"dyadic 树形半带 FIR"结构的真实 C 实现，
 * 取代 cces_template 中的 437 抽头全速率参考核（裕量仅 1.0×、决策层面"不可行"）。
 *
 * ── 结构选型说明（诚实记录，桌面验证支撑）──
 *   候选 A：临界采样 QMF 八度树（半带 LP + 镜像 HP）
 *           → 子带隔离干净，但线性相位半带 QMF 非真 PR，重建误差 ~25dB（实测，不可用）。
 *   候选 B（本实现）：差分金字塔（Laplacian / differential pyramid）
 *           coarse = dec2(LP(x))，detail = x_delayed − interp2(coarse)
 *           → 求和 telescoping 恒等 → 重建误差 ~1e-16（与全速率差分组同量级）。
 *           代价：detail 子带隔离不如 QMF 干净（跨倍频程有泄漏），
 *                 在"各子带增益差异大"时交叠区出现纹波（见 tree_verify.py）。
 *                 对 broadside DAS（各子带等增益、Dolph 加权在阵元维度）→ 完美重建。
 *
 * ── 频段说明（重要，须与声学/规格对齐）──
 *   /2 树从 48kHz 的自然倍频程交叉点为 12k / 6k / 3k / 1.5k，
 *   而非规格标称的 8k / 4k / 2k / 1k。子带标签为"标称/近似"，
 *   重建与 MCPS（芯片选型驱动）不依赖精确边界；精确边界对齐是后续声学规格事项。
 *
 *   子带映射（本实现）：
 *     SB0 = coarse a3  @ fs/8  = 6 kHz    （0 – ~1.5k 标称低频宽波束）
 *     SB1 = detail d3  @ fs/4  = 12 kHz   （~1.5k – 3k）
 *     SB2 = detail d2  @ fs/2  = 24 kHz   （~3k – 6k）
 *     SB3 = detail d1  @ fs    = 48 kHz   （~6k – 12k，含 4-8k 指向核心区）
 *
 * 定点：系数 Q15，状态/中间 Q31，MAC 累加 Q46（int64）。
 * 平台：ADSP-21569 / 21565 SHARC+（半带 ~半数系数为 0，硬件可跳过零乘）。
 *
 * ── 饱和保护 + headroom 约定（PF-4 TASK-PF4-FIX-01，CTO 已批立即修）──
 *   缺陷（PF-4 + Critic 确认，[L2 host]）：半带核 Σ|h_q15|/32768 = 1.7309 > 1，
 *   对抗性满量程激励下 hb_push_filter 回量化 acc>>15 最坏 1.73× Q31 FS，
 *   原无饱和 → int64→int32 窄化符号翻转爆音；hb_interp2 ×2 复合到 3.46×。
 *   修复：所有 Q31 回量化 / ×2 / 合成 int32 相加点加饱和钳位（见 .c）。
 *
 *   ★ 系统级 headroom 约定（与饱和兜底并存，二者都要，不可相互替代）：
 *     半带链路输入预留 −4.8 dB（= 1/1.7309 线性）相对 Q31 满量程，
 *     把 1.73× 上界压回 ≤1×，常态节目素材不进软削波；饱和仅作对抗峰值兜底。
 *     headroom 取值的最终标定（节点①实际触发率）属 EZKIT [L1]，非桌面。
 */

#ifndef ITC_TREE_FILTERBANK_H
#define ITC_TREE_FILTERBANK_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define TFB_HB_TAPS        63          /* 半带 FIR 抽头数（与 fir_design_verify.py 一致） */
#define TFB_NUM_LEVELS     3           /* dyadic 树层数（→ 4 子带） */
#define TFB_NUM_SUBBANDS   4

/* ============================================================
 * EZKIT MCPS 实测挂钩（默认关闭；上 EV-21569-EZKIT 时打开）
 *
 * 用法：在 dsp_main.c 帧回调里包裹 tfb_analyze/tfb_synthesize：
 *     TFB_LOAD_START();
 *     tfb_analyze(...); ... beam ...; tfb_synthesize(...);
 *     TFB_LOAD_STOP();
 *
 * 两种实测手段（择一或并用）：
 *   (A) Cycle counter（推荐，精确）：读 SHARC+ CCNT/EMUCLK 周期寄存器，
 *       cycles_per_frame → MCPS = cycles × FS / FRAME / 1e6 / (MAC/cycle)。
 *       21569 单核 1GHz、每周期 ~1-2 定点 MAC，标称峰值 ~1000-2000 MMAC/s。
 *   (B) GPIO 翻转 + 示波器：帧开始拉高 PORTx，结束拉低，
 *       占空比 = 处理时间/帧周期(1.333ms@64smp)，× 帧周期得 WCET。
 *
 * 实测目标（R1 P0 关闭条件）：满负载 16ch WCET < 帧周期，且裕量 ≥10×。
 * ============================================================ */
#ifndef ENABLE_CPU_LOAD_MEASUREMENT
#define ENABLE_CPU_LOAD_MEASUREMENT 0
#endif

#if ENABLE_CPU_LOAD_MEASUREMENT
  /* —— 平台相关，上板时填实际寄存器；以下为占位声明 —— */
  extern volatile uint32_t *g_tfb_cyc_reg;   /* 指向 SHARC+ 周期计数寄存器（如 *pREG_..._CCNT） */
  extern uint32_t           g_tfb_cyc_start; /* 帧起始周期快照 */
  extern uint32_t           g_tfb_cyc_accum; /* 累计/最坏周期（供主循环读） */
  /* GPIO：上板替换为 *pREG_PORTx_DATA_SET / _CLR */
  void tfb_gpio_high(void);
  void tfb_gpio_low(void);
  #define TFB_LOAD_START()  do { g_tfb_cyc_start = *g_tfb_cyc_reg; tfb_gpio_high(); } while (0)
  #define TFB_LOAD_STOP()   do { uint32_t d = *g_tfb_cyc_reg - g_tfb_cyc_start; \
                                 if (d > g_tfb_cyc_accum) g_tfb_cyc_accum = d; /* 记最坏 */ \
                                 tfb_gpio_low(); } while (0)
#else
  #define TFB_LOAD_START()  do {} while (0)
  #define TFB_LOAD_STOP()   do {} while (0)
#endif

/* 半带 FIR 状态（单实例，环形延迟线）。decim/interp 各级各通道一个实例。 */
typedef struct {
    int32_t  state[TFB_HB_TAPS];   /* Q31 延迟线 */
    uint16_t widx;                 /* 写指针 */
} HbFirState;

/* 一条树通道（一个阵列处理通道）的全部半带状态 + detail 暂存。 */
typedef struct {
    /* 分析：每级一个 decimating 半带 + 一个用于求 detail 的 interpolating 半带 */
    HbFirState ana_dec[TFB_NUM_LEVELS];     /* dec2(LP(·)) 各级 */
    HbFirState ana_int[TFB_NUM_LEVELS];     /* interp2 重建 coarse 以求 detail */
    /* 合成：每级一个 interpolating 半带 */
    HbFirState syn_int[TFB_NUM_LEVELS];
    uint8_t    initialized;
} TreeChannelState;

/**
 * @brief 全局半带系数（Q15）。由 tfb_set_coeffs() 注入（来自 fir_design_verify.py 导出）。
 *        所有级/通道共享同一原型半带核。
 */
void tfb_set_coeffs(const int16_t *hb_coef_q15, uint16_t ntaps);

/** @brief 初始化一个树通道（清零全部状态）。 */
void tfb_channel_init(TreeChannelState *ch);

/**
 * @brief 对一帧输入做 3 级差分金字塔分析。
 * @param[in]  ch        通道状态
 * @param[in]  in        输入帧 [frame] @ 48kHz, Q31
 * @param[in]  frame     帧长（必须是 8 的倍数，保证各级抽取整除）
 * @param[out] sb0       SB0 coarse [frame/8] @6kHz, Q31
 * @param[out] sb1       SB1 detail [frame/4] @12kHz, Q31
 * @param[out] sb2       SB2 detail [frame/2] @24kHz, Q31
 * @param[out] sb3       SB3 detail [frame]   @48kHz, Q31
 */
void tfb_analyze(TreeChannelState *ch, const int32_t *in, uint16_t frame,
                 int32_t *sb0, int32_t *sb1, int32_t *sb2, int32_t *sb3);

/**
 * @brief 由 4 子带重建一帧全速率输出（差分金字塔合成）。
 *        各子带可乘以增益 g[]（Q31，broadside DAS 时全为 1.0=0x7FFFFFFF）。
 * @param[out] out   重建帧 [frame] @48kHz, Q31
 */
void tfb_synthesize(TreeChannelState *ch,
                    const int32_t *sb0, const int32_t *sb1,
                    const int32_t *sb2, const int32_t *sb3,
                    uint16_t frame, int32_t *out);

#ifdef __cplusplus
}
#endif
#endif /* ITC_TREE_FILTERBANK_H */
