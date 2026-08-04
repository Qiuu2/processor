/**
 * @file    chdsp_detector.h
 * @brief   电平检测器(峰值 / RMS + attack/release)—— 门 / 压限 / 限幅 / AGC 共用
 *
 * ⛔ 门禁状态:未过门(2026-08-04)。作者:channel-dsp(第 1 实例)
 *
 * ---------------------------------------------------------------------------
 * ⭐⭐ 一个必须先说清的定点陷阱:**RMS 的状态不能放在 Q4.27**
 * ---------------------------------------------------------------------------
 * RMS 检测器的状态是 **x²** 的平滑值。x² 的 dB 动态范围是信号的**两倍**:
 *   信号 −100 dBFS ⇒ x² = −200 dB
 *   而 Q4.27 的 LSB = 2⁻²⁷ = **−162.6 dBFS** ⇒ **x² 直接下溢到 0**
 *   ⇒ 检测器在安静段读数恒为 0 ⇒ 门永远打不开 / 压限永远不动
 * **⇒ 故功率域状态用 `chdsp_pow_q8_54_t`(int64,54 位小数)**:
 *   LSB = 2⁻⁵⁴ ⇒ 恰好等于 Q4.27 样本相乘后的自然精度,**无额外损失**;
 *   范围 ±256 覆盖链内满量程 (±16)² = 256。
 * ⇒ 该陷阱由 `test/check_detector.c` 的 CHK-D2 机械验证(硬闸门):
 *   把功率状态改回 Q4.27 ⇒ 安静段读数塌到 0 ⇒ 检查必须 FAIL。
 *
 * ⚠ 同族前车:critic 在 W2P verdict 的 FX-3 已指出「一阶平滑跨越 ≥120 dB 动态范围,
 *   定点须块浮点或指数标度」。本文件的处置是**加宽状态**,不是块浮点。
 */

#ifndef CHDSP_DETECTOR_H
#define CHDSP_DETECTOR_H

#include "chdsp_config.h"

#ifdef __cplusplus
extern "C" {
#endif

/** 功率域标量,Q8.54(int64):1 符号 + 8 整数 + 54 小数。范围 ±256,LSB 2⁻⁵⁴。 */
CHDSP_DEFTYPE(chdsp_pow_q8_54_t, int64_t);
#define CHDSP_POW_FRACBITS 54
CHDSP_STATIC_ASSERT(CHDSP_POW_FRACBITS == 2 * CHDSP_SMP_FRACBITS, pow_frac_matches_smp2);

/** 一阶平滑系数 α = 1 − exp(−1/(τ·fs)),Q0.31。 */
CHDSP_DEFTYPE(chdsp_smooth_q0_31_t, int32_t);
#define CHDSP_SMOOTH_FRACBITS 31

static inline chdsp_pow_q8_54_t chdsp_pow_from_raw(int64_t r)
{ return CHDSP_MK(chdsp_pow_q8_54_t, r); }
static inline int64_t chdsp_pow_raw(chdsp_pow_q8_54_t p) { return CHDSP_RAW(p); }
static inline chdsp_smooth_q0_31_t chdsp_smooth_from_raw(int32_t r)
{ return CHDSP_MK(chdsp_smooth_q0_31_t, r); }

typedef enum {
    CHDSP_DET_PEAK = 0,
    CHDSP_DET_RMS  = 1
} chdsp_det_mode_t;

typedef struct {
    chdsp_det_mode_t     mode;
    chdsp_smooth_q0_31_t a_attack;   /**< 上行(电平升)平滑系数 */
    chdsp_smooth_q0_31_t a_release;  /**< 下行(电平降)平滑系数 */
    chdsp_pow_q8_54_t    state;      /**< 功率域(RMS)或幅度平方域(峰值统一用功率域) */
} chdsp_det_t;

/** 设计期:由时间常数(ms)算平滑系数。τ 定义 = 达到 1−1/e 的时间。 */
chdsp_smooth_q0_31_t chdsp_smooth_from_ms(double tau_ms);

void chdsp_det_init(chdsp_det_t *d, chdsp_det_mode_t mode,
                    double attack_ms, double release_ms);
void chdsp_det_reset(chdsp_det_t *d);

/** 送一个样本,返回**功率域**的当前检测值(Q8.54,非负)。 */
chdsp_pow_q8_54_t chdsp_det_process1(chdsp_det_t *d, chdsp_smp_q4_27_t x);

/**
 * 功率 → dB(Q23.8)。`10·log10(p)`。
 * ⚠ **口径**:输入是**功率**,故用 10·log10 而不是 20·log10。
 *   与 `chdsp_gain_to_db()`(输入是**幅度**,用 20·log10)是**两个不同的函数**,
 *   ⛔ 不得互换 —— 这正是本项目栽过的「同族二义」面(DEC-0010)。
 * p ≤ 0 ⇒ 返回 CHDSP_DB_MUTE_Q8。
 */
chdsp_db_q23_8_t chdsp_pow_to_db(chdsp_pow_q8_54_t p);

/* ==========================================================================
 * 算力自报(解析估计,⛔ 非实测)
 * ==========================================================================
 * 峰值:1 次绝对值 + 1 次平方(乘)+ 1 次比较 + 1 次平滑(1 乘 + 1 移位 + 2 加)
 *      ⇒ ≈ 2 乘 + 5 其它 op / 样本 [L3/解析]
 * RMS :同上(去掉比较,attack/release 仍按方向选系数)⇒ ≈ 2 乘 + 5 op / 样本
 * 功率→dB:前导零计数 + 128 项表内插 + 一次乘 ⇒ ≈ 2 乘 + 12 其它 op / 次 [L3/解析]
 * ⚠ 若日后把增益计算降到块速率,dB 转换次数按 1/L 降 —— **该优化待实测后再定,现在不做**。
 */
#define CHDSP_DET_MUL_PER_SAMPLE      2
#define CHDSP_DET_OTHER_OP_PER_SAMPLE 5
#define CHDSP_POW2DB_MUL              2
#define CHDSP_POW2DB_OTHER_OP        12

#ifdef __cplusplus
}
#endif
#endif /* CHDSP_DETECTOR_H */
