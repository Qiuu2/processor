/**
 * @file    chdsp_fir.h
 * @brief   线性相位 FIR(对称抽头)—— D4 输出链
 * ⛔ 门禁状态:未过门(2026-08-04)。作者:channel-dsp(第 1 实例)
 *
 * ⚠ **群延迟 = (N−1)/2 样本,是硬成本,直接进延迟预算**:
 *   N=512 ⇒ 5.323 ms ｜ 256 ⇒ 2.656 ｜ 128 ⇒ 1.323 ｜ 0(关)⇒ 0
 *   ⛔ N=1024 在任何帧长下超 12 ms,已被 chdsp_config.h 的编译期断言挡住。
 * ⚠ **低频能力**:可控最低频 ≈ 2·fs/N ⇒ 512:187 Hz ｜ 256:375 Hz ｜ 128:750 Hz
 *   ⇒ 「FIR 线性相位」**不等于「全频段线性相位」**,低频仍靠 IIR。
 *
 * ⚠ **目标侧卸载路径待定**:FIRA 定点模式(FXD=1)每输出样本回写 **80-bit = 3×32-bit**
 *   且**不支持 multi-iteration ⇒ ≤1024 taps**,核心侧还须 decimate 输出缓冲
 *   [L2/厂家 HW Ref §38]。**⇒ 本文件是【核心侧参考实现】;FIRA 驱动归 platform-fw。**
 */
#ifndef CHDSP_FIR_H
#define CHDSP_FIR_H
#include "chdsp_config.h"
#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    const chdsp_coef_q4_27_t *h;   /**< 抽头,长度 n(调用方静态分配) */
    chdsp_smp_q4_27_t        *z;   /**< 延迟线,长度 n */
    uint16_t                  n;
    uint16_t                  w;
    uint8_t                   enabled;
} chdsp_fir_t;

/** @return 0 = 成功;非 0 = 参数非法(⛔ 调用方必须处理) */
int  chdsp_fir_init(chdsp_fir_t *f, const chdsp_coef_q4_27_t *taps,
                    chdsp_smp_q4_27_t *state, uint16_t n);
void chdsp_fir_reset(chdsp_fir_t *f);
chdsp_smp_q4_27_t chdsp_fir_process1(chdsp_fir_t *f, chdsp_smp_q4_27_t x, chdsp_sat_t *sat);

/** 群延迟(样本)。对称抽头 ⇒ (n−1)/2。 */
static inline uint16_t chdsp_fir_group_delay(const chdsp_fir_t *f)
{ return (f->n > 0u) ? (uint16_t)((f->n - 1u) / 2u) : 0u; }

/** 设计期:窗函数法低通原型(Kaiser β 由调用方给);对称 ⇒ 线性相位。 */
int chdsp_fir_design_lowpass(double fc_hz, double beta, chdsp_coef_q4_27_t *taps, uint16_t n);

/* 算力自报(解析,⛔ 非实测):n 次 MAC + 1 次窄化 ⇒ n 乘 + (n+4) op / 样本 [L3] */
#define CHDSP_FIR_MUL_PER_SAMPLE(n)  (n)
#ifdef __cplusplus
}
#endif
#endif
