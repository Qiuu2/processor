/**
 * @file    fir.h
 * @brief   FIR 滤波器接口（多相实现 + 分数延迟）
 *
 * 提供两类 FIR 实现：
 *   1. PolyphaseFir  — 带抽取/内插的多相 FIR，用于子带分析/合成
 *   2. FracDelayFir  — 分数延迟 FIR（sinc-windowed Kaiser），用于波束延迟补偿
 *
 * 定点格式:
 *   系数: Q15 (int16_t)
 *   状态: Q31 (int32_t)
 *   输出: Q31 (int32_t)，调用者负责移位到最终格式
 */

#ifndef ITC_FIR_H
#define ITC_FIR_H

#include <stdint.h>
#include "config.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================
 * 多相 FIR（分析滤波器：带抽取）
 * ============================================================ */

/**
 * @brief 多相 FIR 状态结构体（单通道，带 M 倍抽取）
 *
 * 使用方式：
 *   - 每个子带、每个通道各一个实例
 *   - 调用 polyphase_fir_decimate() 每 M 个输入产生 1 个输出
 */
typedef struct {
    const int16_t *coef;     /**< FIR 系数数组 [N+1], Q15，只读，多通道共享 */
    int32_t  *state;         /**< 延迟线状态 [N+1], Q31，每通道独立 */
    uint16_t  num_taps;      /**< FIR 抽头数 = 原型阶数 + 1 */
    uint16_t  decim_rate;    /**< 抽取率 M */
    uint16_t  phase_idx;     /**< 当前多相分支索引（0 to M-1） */
    uint16_t  state_idx;     /**< 状态环形缓冲写指针 */
} PolyphaseFirState;

/**
 * @brief  初始化多相 FIR 状态
 * @param[out] pState    状态结构体（调用者分配）
 * @param[in]  pCoef     原型 FIR 系数（共享，长度 num_taps，Q15）
 * @param[in]  pStateBuf 状态缓冲区（调用者分配，长度 num_taps，Q31）
 * @param[in]  numTaps   抽头数（= 原型 FIR 阶数 + 1）
 * @param[in]  decimRate 抽取率 M
 */
void polyphase_fir_init(PolyphaseFirState *pState,
                        const int16_t     *pCoef,
                        int32_t           *pStateBuf,
                        uint16_t           numTaps,
                        uint16_t           decimRate);

/**
 * @brief  多相 FIR 抽取处理（每帧）
 *
 * 输入 M 个样点，输出 1 个子带样点。
 * 调用 FRAME_SIZE/M 次以处理完一帧。
 *
 * @param[in,out] pState  FIR 状态
 * @param[in]     pIn     输入样点数组（长度 decimRate），Q23
 * @return                子带输出样点，Q31
 *
 * @note 调用者应将输入 Q23 转换为 Q31 后传入（左移 8 位）
 */
int32_t polyphase_fir_decimate(PolyphaseFirState *pState,
                               const int32_t     *pIn);

/**
 * @brief  多相 FIR 内插处理（合成，每帧）
 *
 * 输入 1 个子带样点，输出 M 个全带样点。
 *
 * @param[in,out] pState   FIR 状态（合成滤波器，参数与分析相同）
 * @param[in]     input    子带输入，Q31
 * @param[out]    pOut     输出样点数组（长度 decimRate），Q31
 */
void polyphase_fir_interpolate(PolyphaseFirState *pState,
                               int32_t            input,
                               int32_t           *pOut);

/* ============================================================
 * 分数延迟 FIR（波束延迟补偿）
 * ============================================================ */

/**
 * @brief 分数延迟 FIR 状态（单通道，单子带）
 *
 * 8 阶 sinc-windowed Kaiser FIR，分数延迟范围 [0, 1) 采样
 */
typedef struct {
    int16_t  coef[FRAC_DELAY_FIR_ORDER];  /**< 8 个 FIR 系数，Q15 */
    int32_t  state[FRAC_DELAY_FIR_ORDER]; /**< 延迟线状态，Q31 */
    uint8_t  state_idx;                   /**< 环形缓冲写指针 */
} FracDelayFirState;

/**
 * @brief  计算分数延迟 FIR 系数（sinc-windowed Kaiser）
 *
 * 根据目标分数延迟 frac（0 ≤ frac < 1）计算 8 阶 FIR 系数。
 * 在波束指向更新时调用，结果存入 FracDelayFirState.coef[]。
 *
 * @param[out] pState   分数延迟 FIR 状态
 * @param[in]  frac_q15 目标分数延迟，Q15 格式（0 = 零延迟，32767 ≈ 1采样延迟）
 */
void frac_delay_fir_set_delay(FracDelayFirState *pState, int16_t frac_q15);

/**
 * @brief  重置分数延迟 FIR 状态（状态清零）
 * @param[out] pState  状态结构体
 */
void frac_delay_fir_reset(FracDelayFirState *pState);

/**
 * @brief  分数延迟 FIR 处理（单样点）
 *
 * @param[in,out] pState  FIR 状态
 * @param[in]     input   输入样点，Q31
 * @return                延迟补偿后输出，Q31
 */
int32_t frac_delay_fir_process(FracDelayFirState *pState, int32_t input);

/* ============================================================
 * 整数延迟（环形缓冲）
 * ============================================================ */

/**
 * @brief 整数延迟缓冲区状态（单通道）
 *
 * 支持 0 到 MAX_INT_DELAY_SAMPLES-1 采样的整数延迟，
 * 与分数延迟 FIR 级联，实现任意时延补偿。
 */
typedef struct {
    int32_t  buf[MAX_INT_DELAY_SAMPLES]; /**< 环形缓冲区，Q31 */
    uint16_t write_idx;                  /**< 写指针 */
    uint16_t delay;                      /**< 当前整数延迟（采样数） */
} IntDelayState;

/**
 * @brief  设置整数延迟值并重置缓冲区
 * @param[out] pState  状态结构体
 * @param[in]  delay   整数延迟，单位：采样（必须 < MAX_INT_DELAY_SAMPLES）
 */
void int_delay_set(IntDelayState *pState, uint16_t delay);

/**
 * @brief  整数延迟写入 + 读出（单样点）
 *
 * @param[in,out] pState  延迟状态
 * @param[in]     input   当前输入，Q31
 * @return                延迟后的输出，Q31
 */
int32_t int_delay_process(IntDelayState *pState, int32_t input);

#ifdef __cplusplus
}
#endif

#endif /* ITC_FIR_H */
