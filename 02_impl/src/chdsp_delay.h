/**
 * @file    chdsp_delay.h
 * @brief   整数样本延时线(环形缓冲)—— 输入/输出延时 + 限幅器前视共用
 *
 * ⛔ 门禁状态:未过门(2026-08-04)。作者:channel-dsp(第 1 实例)
 *
 * ⚠ **内存账(D3D4_CHANNEL_CHAIN §4⑥)**:缓冲 = 时长 × 48 样本/ms × 4 B。
 *   200 ms × 8 通道 = 307.2 kB(L1 = 640 kB 的 48%);
 *   1200 ms × 8 通道 = 1843.2 kB **超 L2(1024 kB)⇒ 须外挂 DDR3**。
 *   ⇒ 缓冲由**调用方静态分配**,本模块不分配 ⇒ 放哪一级存储由链接脚本决定,不由本模块决定。
 *
 * ⚠ 延时**不改变信号内容**,故不引入量化器,不进 §噪声账。
 */

#ifndef CHDSP_DELAY_H
#define CHDSP_DELAY_H

#include "chdsp_config.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    chdsp_smp_q4_27_t *buf;      /**< 调用方静态分配,长度 = cap */
    uint32_t           cap;      /**< 缓冲容量(样本);须 ≥ max_delay + 1 */
    uint32_t           w;        /**< 写指针 */
    uint32_t           d;        /**< 当前延时(样本) */
    uint32_t           d_target; /**< 斜坡目标 */
} chdsp_delay_t;

/** @return 0 = 成功;非 0 = cap 不足或参数非法(⛔ 调用方必须处理) */
int  chdsp_delay_init(chdsp_delay_t *dl, chdsp_smp_q4_27_t *storage,
                      uint32_t cap_samples, uint32_t init_delay_samples);
void chdsp_delay_reset(chdsp_delay_t *dl);

/** 设置延时。⚠ 直接跳变会爆音 ⇒ 由 `chdsp_delay_step_toward()` 每样本走 1 步。 */
int  chdsp_delay_set(chdsp_delay_t *dl, uint32_t samples);

/** 处理一个样本。 */
chdsp_smp_q4_27_t chdsp_delay_process1(chdsp_delay_t *dl, chdsp_smp_q4_27_t x);

/**
 * 读取"当前样本之前 n 个样本"的值,**不推进写指针**。
 * 供限幅器前视用:侧链看未来 = 音频路延后 n,侧链读延后前的值。
 */
chdsp_smp_q4_27_t chdsp_delay_peek(const chdsp_delay_t *dl, uint32_t n_back);

/* ==========================================================================
 * 算力自报(解析估计,⛔ 非实测)
 * ==========================================================================
 * 每样本:1 次写 + 1 次读 + 2 次指针回绕比较 ⇒ **0 乘 + 4 op / 样本** [L3/解析]
 * ⚠ 若缓冲落在 L3/DDR3,每样本的读写要过外部总线 ⇒ 须块 DMA。
 *   **该形态归 platform-fw,本模块不实现。**
 */
#define CHDSP_DELAY_MUL_PER_SAMPLE      0
#define CHDSP_DELAY_OTHER_OP_PER_SAMPLE 4

#ifdef __cplusplus
}
#endif
#endif /* CHDSP_DELAY_H */
