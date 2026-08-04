/**
 * @file    chdsp_config.h
 * @brief   CONF-DSP-88 · D3/D4 通道链 —— **全部尺寸的唯一定义处**
 *
 * ============================================================================
 * ⛔⛔ 门禁状态:**未过门**(2026-08-04)
 *     未经独立 critic 评审。禁止 release / 冻结 / 下游引用为依据 / 对外承诺。
 *     作者:channel-dsp(第 1 实例)
 * ============================================================================
 *
 * ⭐ **本文件存在的唯一理由:让"仍在动的尺寸"只有一个改动点。**
 *   已经证明会被反复改的:FIR 抽头、分频阶数与 fc、陷波数、PEQ 段数。
 *   ⇒ 它们是**延迟预算的调节旋钮**(D3D4_CHANNEL_CHAIN §5.4/§5.8/§5.10)。
 *   ⛔ **任何 .c/.h 里不得出现这些尺寸的字面量。**
 *      机械检查:`test/check_no_magic.sh`(硬闸门,发现魔数即 exit 1)。
 *
 * 基线(以它们为准,⛔ 不在此重新设计):
 *   · 量纲与定点约定 = `01_design/D34_FIXEDPOINT_CONVENTION_v0.1.md` + `chdsp_fixed.h`
 *   · 链序与参数表   = `01_design/D3D4_CHANNEL_CHAIN_v0.1.md`
 */

#ifndef CHDSP_CONFIG_H
#define CHDSP_CONFIG_H

#include "chdsp_fixed.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ==========================================================================
 * 1. 系统级
 * ========================================================================== */
#define CHDSP_FS_HZ                 48000       /**< 采样率 [L2/PRD §一.1] */
#define CHDSP_FRAME_SAMPLES         64          /**< 帧长 L [L4/我定的数;延迟账见 §5.4] */
#define CHDSP_IN_CHANNELS           8           /**< [L2/PRD §一.2] */
#define CHDSP_OUT_CHANNELS          8           /**< [L2/PRD §一.2] */

/* ==========================================================================
 * 2. D3 输入链尺寸
 * ========================================================================== */
#define CHDSP_IN_HPF_SECTIONS       2           /**< HPF 最大阶数 / 2(BW24 ⇒ 2 节) */
#define CHDSP_IN_PEQ_BANDS          8           /**< [L2/PRD §二.4「每路输入8段」] */
#define CHDSP_IN_DELAY_MAX_MS       100         /**< [L4/我定的数;内存账见 §4④] */

/* ==========================================================================
 * 3. D4 输出链尺寸
 * ========================================================================== */
#define CHDSP_OUT_XO_SECTIONS       4           /**< 分频单支最大节数(LR8 = 4 biquad) */
#define CHDSP_OUT_PEQ_BANDS         10          /**< [L2/PRD §三.2「10段参量均衡」] */
#define CHDSP_OUT_DELAY_MAX_MS      200         /**< [L4/我定的数;1200ms 需 DDR3,见 §4⑥] */

/**
 * 线性相位 FIR 抽头数。**延迟预算的主调节旋钮之一。**
 * 候选 {0(关), 128, 256, 512};⛔ 1024 在任何帧长下超 12 ms 预算。
 * 每档放弃什么见 D3D4_CHANNEL_CHAIN §5.10①。
 */
#ifndef CHDSP_OUT_FIR_TAPS
#  define CHDSP_OUT_FIR_TAPS        256
#endif

/* ==========================================================================
 * 4. ✳ 插入点(算法层,归 adaptive-dsp)—— 本实现**只留形状,不实现**
 * ==========================================================================
 * ⛔ CTO 裁定:NHS 控制路径有四个未清缺陷,定死之前不 C 化。
 *    ⇒ 本文件只定义**尺寸与接口形状**,算法本体由 adaptive-dsp 提供。
 */

/**
 * AFC/NHS 陷波器个数。
 * ⚠ **待定项 ①**:PRD §二.5 明文「每通道独立 **16** 点陷波」;
 *    DEC-0007 改为 **8** 点(依据竞品量产口径 + 算力)。**两者未收敛。**
 * ⇒ 本值走 config,改一处即可;⛔ 不得在别处写字面量。
 */
#ifndef CHDSP_NOTCH_COUNT
#  define CHDSP_NOTCH_COUNT         8
#endif

/**
 * ⚠ **待定项 ②**:PRD §二.5 要求陷波器有**三种工作模式**,我们目前只有一种。
 * ⇒ 按 lead 指示:**接口预留三种模式的形状,即使现在只实现一种**。
 * ⇒ 实现状态见 `chdsp_notch_stub.h`。
 */
typedef enum {
    CHDSP_NOTCH_MODE_FIXED   = 0,   /**< 固定:不被新反馈点占用,重启后仍在 */
    CHDSP_NOTCH_MODE_DYNAMIC = 1,   /**< 动态/自动:参与循环复用 */
    CHDSP_NOTCH_MODE_HYBRID  = 2    /**< 混合:部分固定 + 部分动态 */
} chdsp_notch_mode_t;
#define CHDSP_NOTCH_MODE_COUNT      3

/* ==========================================================================
 * 5. 派生量 + 编译期一致性断言
 * ==========================================================================
 * ⭐ 派生量不得手写,必须由上面的基本量推出 —— 否则改一个忘一个。
 */

/** 延时线样本数(向上取整到帧的整数倍,便于块处理) */
#define CHDSP_MS_TO_SAMPLES(ms)     (((ms) * CHDSP_FS_HZ) / 1000)
#define CHDSP_IN_DELAY_MAX_SAMPLES  CHDSP_MS_TO_SAMPLES(CHDSP_IN_DELAY_MAX_MS)
#define CHDSP_OUT_DELAY_MAX_SAMPLES CHDSP_MS_TO_SAMPLES(CHDSP_OUT_DELAY_MAX_MS)

/** FIR 群延迟(样本);线性相位 ⇒ (N−1)/2。N=0(关)时为 0。 */
#define CHDSP_OUT_FIR_GROUP_DELAY_SAMPLES \
    ((CHDSP_OUT_FIR_TAPS > 0) ? ((CHDSP_OUT_FIR_TAPS - 1) / 2) : 0)

/** 每通道的 biquad 总数(算力/内存记账用) */
#define CHDSP_IN_BIQUADS_PER_CH   (CHDSP_IN_HPF_SECTIONS + CHDSP_IN_PEQ_BANDS + CHDSP_NOTCH_COUNT)
#define CHDSP_OUT_BIQUADS_PER_CH  (2 * CHDSP_OUT_XO_SECTIONS + CHDSP_OUT_PEQ_BANDS)

/* ---- 断言:改坏一个尺寸,编译就停 ---- */
CHDSP_STATIC_ASSERT(CHDSP_FS_HZ == 48000, fs_is_48k);
CHDSP_STATIC_ASSERT(CHDSP_FRAME_SAMPLES > 0 &&
                    (CHDSP_FRAME_SAMPLES & (CHDSP_FRAME_SAMPLES - 1)) == 0, frame_pow2);
CHDSP_STATIC_ASSERT(CHDSP_OUT_FIR_TAPS == 0 || CHDSP_OUT_FIR_TAPS == 128 ||
                    CHDSP_OUT_FIR_TAPS == 256 || CHDSP_OUT_FIR_TAPS == 512,
                    fir_taps_in_candidate_set);
/** ⭐ 延迟预算硬闸:FIR 群延迟 + 块 I/O(2L)+ 转换器 47.9844 样本 < 12 ms = 576 样本 */
CHDSP_STATIC_ASSERT(CHDSP_OUT_FIR_GROUP_DELAY_SAMPLES + 2 * CHDSP_FRAME_SAMPLES + 48 < 576,
                    fixed_latency_within_12ms);
CHDSP_STATIC_ASSERT(CHDSP_NOTCH_COUNT >= 1 && CHDSP_NOTCH_COUNT <= 16, notch_count_range);
CHDSP_STATIC_ASSERT(CHDSP_IN_DELAY_MAX_SAMPLES % CHDSP_FRAME_SAMPLES == 0, in_delay_frame_aligned);
CHDSP_STATIC_ASSERT(CHDSP_OUT_DELAY_MAX_SAMPLES % CHDSP_FRAME_SAMPLES == 0, out_delay_frame_aligned);

/* ==========================================================================
 * 5b. ⭐⭐ 系数格式 Q4.27 的【解析硬包络】—— 守的是【增益】,不是 S
 * ==========================================================================
 * 解析界(D34_FIXEDPOINT_CONVENTION §3.2.0):
 *   峰型 max|b| ≤ max(2, A²) ｜ 架式 max|b| ≤ 2A² ｜ HPF/LPF ≤ 2,A = 10^(G/40)
 *   ⇒ 全族 max|b| ≤ 2·10^(G_max/20)  —— **只依赖 G_max,与 Q、S、频率完全无关**
 *   ⇒ Q4.27(|c| < 16)要求 2·10^(G/20) < 16 ⇒ **G_max < 20·log₁₀8 = 18.0618 dB**
 *
 * ⚠⚠ **一处必须纠正的历史表述**:`chdsp_fixed.h` 的注释仍写
 *    「参数范围一旦放宽(**S>1** 或 |G|>15 dB),该界立即失效」——
 *    **`S>1` 那一半已被 D34 §3.2.2 亲手证伪**:S 从 1.0→2.0 只把 max|b| 从
 *    11.2148 推到 11.2292(+0.0144),**几乎不起作用**;真正的驱动量只有增益。
 *    ⇒ **若照那句去守 S,就会守着一个几乎无关的量,而真正会翻掉 Q4.27 的
 *      增益包络没有人守**(团队纪律 D6-r:锁错字串的 lint 比没有 lint 更坏)。
 *    ⇒ 本文件按【解析界】守增益。`chdsp_fixed.h` 的那句待评审窗口结束后订正
 *      (D6-s:评审期内不改被审件;整改件见 01_design/fix_queue_r1/)。
 */
/** 解析硬包络,毫 dB。2·10^(G/20) = 16 ⇒ G = 20·log10(8) = 18.06180 dB */
#define CHDSP_COEF_GAIN_ENVELOPE_MDB   18061
/** 产品参数量程建议上限(留 3 dB 余量),⛔ 须与 D2 参数字典锁死 */
#define CHDSP_PARAM_GAIN_MAX_MDB       15000
CHDSP_STATIC_ASSERT(CHDSP_PARAM_GAIN_MAX_MDB < CHDSP_COEF_GAIN_ENVELOPE_MDB, gain_within_envelope);

/* ==========================================================================
 * 6. ⚠ 待定项与硬件约束 —— 标在代码里,⛔ 不许默认
 * ========================================================================== */

/**
 * ⚠ **待定项 ③:IIRA 的硬件系数格式未知。**
 * lead 与我各查一次,ADSP-2156x HW Ref §38 的 IIRA 段只有 `FORTYBIT`(32/40-bit IEEE
 * 浮点二选一)与 `RND`,**无系数字长/定标的明文**。
 * ⇒ 本实现的 biquad **全部走 SHARC+ 核心**(DEC-0014:IIRA 比核心慢 0.42×)⇒ 目前不受影响。
 * ⇒ **⛔ 若日后有任何一段卸载到 IIRA,其系数格式由硬件定死,不得默认可以沿用 Q4.27。**
 *    使用前必须查明并回填本条。
 */
#define CHDSP_IIRA_COEF_FORMAT_UNKNOWN  1

/**
 * ⚠ **硬件约束(DEC-0022)**:模拟前端的 **−8.72 dB 净衰减必须在【前置放大器之后】**。
 * 依据:ADAU1979 满量程差分输入 4.5 V rms = +15.28 dBu [L2/厂家];
 *       而「+4 dBu ⇔ −20 dBFS」要求 0 dBFS ⇔ +24 dBu ⇒ 需 −8.72 dB 净衰减。
 * ⇒ 若衰减放在**前置放大器之前**,话筒信号先被衰减 8.72 dB 再放大
 *    ⇒ 前置放大器的噪声被同等放大 ⇒ **输入等效噪声恶化 8.72 dB**。
 * ⇒ 本约束属硬件/原理图,软件侧无法补偿,**写在此处仅为不让它丢失**。
 */
#define CHDSP_AFE_PAD_AFTER_PREAMP_REQUIRED  1

#ifdef __cplusplus
}
#endif
#endif /* CHDSP_CONFIG_H */
