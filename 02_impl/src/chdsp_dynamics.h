/**
 * @file    chdsp_dynamics.h
 * @brief   动态处理器:噪声门/扩展器 · 压缩器 · 限幅器 · 音箱保护限幅
 *
 * ⛔ 门禁状态:未过门(2026-08-04)。作者:channel-dsp(第 1 实例)
 * ⛔ 边界:**不含 AGC / automixer / 语音闪避** —— 那些归 adaptive-dsp。
 *
 * ---------------------------------------------------------------------------
 * 拓扑(三者同构,便于共用检查与变异)
 * ---------------------------------------------------------------------------
 *   x → [检测器(峰值/RMS + attack/release)] → 功率 → dB
 *                                                ↓
 *                                       [静态曲线(dB 域)]
 *                                                ↓ gain_db
 *                                       [dB → 线性 Q4.27]
 *   x(可经前视延时)──────────────────────────× ──→ y
 *
 * ⚠ **平滑只在检测器一处**(前馈型)。⛔ 不在增益上再加一级平滑 ——
 *   两级平滑会让 attack/release 参数与实际时间常数对不上,而**界面上看不出来**。
 *   (与 D4「值不值它的复杂度」同向:先不加第二级机器。)
 *
 * ⚠ **被测对象声明(团队纪律 D6-b)**:
 *   检测器在 **attack ≠ release** 时,稳态读数**不等于均值功率**,而是介于
 *   **均值功率与峰值功率之间**。实测(atk=10ms/rel=100ms,1 kHz 正弦):
 *   读数 −20.89 dB,均值 −23.01,峰值 −20.00。
 *   **对称时(atk=rel)读数精确等于均值功率**(实测误差 0.00 dB)。
 *   ⇒ ⛔ 不得把它叫作"RMS 值"而不带这句限定。
 *
 * ⚠ **检测器的功率底与 release 时间常数耦合**(定点固有,非缺陷):
 *   增量 α·(inst−s) < 1 LSB 时截断为 0 ⇒ 底 ≈ (1/α) LSB。实测:
 *   release  50 ms ⇒ −128.75 dB ｜ 100 ms ⇒ −125.74 ｜ 500 ms ⇒ −118.75
 *   ｜ 1000 ms ⇒ −115.74 ｜ **3000 ms ⇒ −110.97 dB**
 *   ⇒ 最长 release 下的底比 PRD 的 >106 dB 动态范围**只低 5 dB**;
 *     但比门限量程下沿(−80 dBFS)低 31 dB ⇒ **对判据用途充分**。
 *   ⇒ 该数由 CHK-D3 硬闸门锁住,改坏即 FAIL。
 */

#ifndef CHDSP_DYNAMICS_H
#define CHDSP_DYNAMICS_H

#include "chdsp_config.h"
#include "chdsp_detector.h"
#include "chdsp_delay.h"

#ifdef __cplusplus
extern "C" {
#endif

/** 静态曲线斜率,Q16.15(int32):范围 ±65536,覆盖 (R−1) ≤ 19 与 (1−1/R) ≤ 1。 */
CHDSP_DEFTYPE(chdsp_slope_q16_15_t, int32_t);
#define CHDSP_SLOPE_FRACBITS 15
static inline chdsp_slope_q16_15_t chdsp_slope_from_raw(int32_t r)
{ return CHDSP_MK(chdsp_slope_q16_15_t, r); }
chdsp_slope_q16_15_t chdsp_slope_from_f64(double v);

/* ==========================================================================
 * 1. 噪声门 / 扩展器
 * ==========================================================================
 * 静态曲线(dB 域,向下扩展):
 *   L ≥ thr        ⇒ gain_db = 0
 *   L <  thr       ⇒ gain_db = (L − thr) · (R − 1),下钳到 −range_db
 * ⇒ R = 20 时,thr 以下 3 dB ⇒ −57 dB(等效噪声门,与竞品「比率 1:20 即等效噪声门」同口径)
 *
 * 迟滞 + hold 由状态机实现:
 *   CLOSED --(L ≥ thr)--> OPEN
 *   OPEN   --(L < thr − hyst)--> HOLD(计时 hold_samples)--> CLOSED
 * ⚠ **肯定式条件**(团队纪律 D-2):开门走「持有肯定结论」的分支,
 *   新增/异常状态默认落**关门**侧,⛔ 不写「若非关门则开门」。
 */
typedef enum { CHDSP_GATE_CLOSED = 0, CHDSP_GATE_OPEN = 1, CHDSP_GATE_HOLD = 2 } chdsp_gate_state_t;

typedef struct {
    chdsp_det_t          det;
    chdsp_db_q23_8_t     thr_db;
    chdsp_db_q23_8_t     hyst_db;
    chdsp_db_q23_8_t     range_db;     /**< 最大衰减量(正值),gain 下钳到 −range */
    chdsp_slope_q16_15_t slope;        /**< = R − 1 */
    uint32_t             hold_samples;
    uint32_t             hold_left;
    chdsp_gate_state_t   state;
    uint8_t              enabled;
} chdsp_gate_t;

void chdsp_gate_init(chdsp_gate_t *g, double thr_dbfs, double ratio, double knee_hyst_db,
                     double range_db, double attack_ms, double hold_ms, double release_ms);
void chdsp_gate_reset(chdsp_gate_t *g);
/** @return 应用于音频的线性增益;并回写 gain_db(可为 NULL)供遥测 */
chdsp_gain_q4_27_t chdsp_gate_gain1(chdsp_gate_t *g, chdsp_smp_q4_27_t sidechain,
                                    chdsp_db_q23_8_t *gain_db_out);

/* ==========================================================================
 * 2. 压缩器(软拐点)
 * ==========================================================================
 *   2(L−thr) < −W          ⇒ gain_db = 0
 *   |2(L−thr)| ≤ W         ⇒ gain_db = (1/R − 1)·(L − thr + W/2)² / (2W)
 *   2(L−thr) >  W          ⇒ gain_db = (thr − L)·(1 − 1/R)
 * ⚠ 软拐点段有一次平方 ⇒ 每样本 +1 乘。
 */
typedef struct {
    chdsp_det_t          det;
    chdsp_db_q23_8_t     thr_db;
    chdsp_db_q23_8_t     knee_db;      /**< W */
    chdsp_slope_q16_15_t slope;        /**< = 1 − 1/R */
    chdsp_db_q23_8_t     makeup_db;
    uint8_t              enabled;
} chdsp_comp_t;

void chdsp_comp_init(chdsp_comp_t *c, double thr_dbfs, double ratio, double knee_db,
                     double attack_ms, double release_ms, double makeup_db,
                     chdsp_det_mode_t det_mode);
void chdsp_comp_reset(chdsp_comp_t *c);
chdsp_gain_q4_27_t chdsp_comp_gain1(chdsp_comp_t *c, chdsp_smp_q4_27_t sidechain,
                                    chdsp_db_q23_8_t *gain_db_out);

/* ==========================================================================
 * 3. 限幅器(砖墙 + 前视)
 * ==========================================================================
 * ⚠ **前视 1 ms 不可降为 0**(架构侧已裁定):降到 0 ⇒ 反馈式 ⇒ 过冲不受控,
 *   而输出限幅器的职责是保护高音单元 ⇒ **一个会过冲的保护器,在它唯一该起作用的那一刻失效**。
 * ⇒ 前视 = 音频路经延时线延后 N 样本,侧链读**未延后**的值。
 */
typedef struct {
    chdsp_det_t      det;              /**< 峰值检测,attack 极快 */
    chdsp_db_q23_8_t thr_db;
    chdsp_delay_t    look;             /**< 音频路前视延时 */
    uint32_t         look_samples;
    uint8_t          enabled;
} chdsp_limiter_t;

/** @return 0 = 成功;非 0 = 前视缓冲不足(⛔ 调用方必须处理) */
int  chdsp_limiter_init(chdsp_limiter_t *l, chdsp_smp_q4_27_t *look_storage,
                        uint32_t look_cap, double thr_dbfs,
                        double lookahead_ms, double release_ms);
void chdsp_limiter_reset(chdsp_limiter_t *l);
/** 处理一个样本(含前视延时)。 */
chdsp_smp_q4_27_t chdsp_limiter_process1(chdsp_limiter_t *l, chdsp_smp_q4_27_t x,
                                         chdsp_sat_t *sat, chdsp_db_q23_8_t *gr_db_out);

/* ==========================================================================
 * 4. 音箱保护限幅(PRD §三.5)—— **双通道**:长期功率(RMS)+ 短期峰值
 * ==========================================================================
 * ⚠ 两者时间常数相差 2–3 个数量级,**不能合成一个检测器**。
 * ⚠⚠ **本模块全部阈值/时间常数都是 [L4/我定的数]**:真值取决于所接音箱的
 *    功率、音圈热阻、Xmax —— **本项目不知道用户接什么音箱**。
 *    ⇒ 出厂默认只是保守占位,**必须现场设定**。
 *    ⇒ 一个「看起来在保护、实际不匹配」的限幅器,比没有更危险。
 */
typedef struct {
    chdsp_limiter_t rms_stage;   /**< 长期功率:RMS 检测,慢 */
    chdsp_limiter_t peak_stage;  /**< 短期峰值:峰值检测,快 */
    uint8_t         enabled;
} chdsp_spk_guard_t;

int  chdsp_spk_guard_init(chdsp_spk_guard_t *s,
                          chdsp_smp_q4_27_t *rms_look, uint32_t rms_cap,
                          chdsp_smp_q4_27_t *peak_look, uint32_t peak_cap,
                          double rms_thr_dbfs, double rms_tc_ms,
                          double peak_thr_dbfs, double peak_attack_ms);
chdsp_smp_q4_27_t chdsp_spk_guard_process1(chdsp_spk_guard_t *s, chdsp_smp_q4_27_t x,
                                           chdsp_sat_t *sat);

/* ==========================================================================
 * 算力自报(解析估计,⛔ 非实测)
 * ==========================================================================
 * 每个动态块每样本 = 检测器(2 乘 + 5 op)+ 功率→dB(2 乘 + 12 op)
 *                   + 静态曲线(门 1 乘 / 压限 2 乘)+ dB→线性(2 乘 + 12 op)
 *                   + 增益相乘(1 乘 + 窄化 3 op)
 * ⇒ **门 ≈ 8 乘 + 33 op;压限 ≈ 9 乘 + 33 op / 样本** [L3/解析]
 * ⇒ 限幅器另加前视延时 4 op。
 * ⚠ 可能的优化:增益计算降到块速率(每 L 样本一次)⇒ dB 转换次数降 1/L。
 *   **⛔ 现在不做**:attack 0.1 ms = 4.8 样本,块速率 L=64 会破坏快 attack。
 *   待 W1-C 实测后再定是否分档。
 */
#define CHDSP_GATE_MUL_PER_SAMPLE   8
#define CHDSP_COMP_MUL_PER_SAMPLE   9
#define CHDSP_DYN_OTHER_OP_PER_SAMPLE 33

#ifdef __cplusplus
}
#endif
#endif /* CHDSP_DYNAMICS_H */
