/**
 * @file    chdsp_notch.h
 * @brief   AFC 陷波器组 —— **槽位簿记**(三种工作模式)。⛔ 门禁状态:未过门。
 *
 * ============================================================================
 * ⛔⛔ 职责边界(先读这一段,它决定本文件不做什么)
 * ----------------------------------------------------------------------------
 * PRD §二.5:「每通道独立 16 点陷波防啸叫,**三种工作模式**」。
 *   ⚠ 待定项 ①:点数 PRD 写 16、DEC-0007 改 8,**两者未收敛** ⇒ 走 `CHDSP_NOTCH_COUNT`。
 *   ⚠ 待定项 ②:**三种模式 PRD 未定义其语义** ⇒ 下面的语义是我按工程惯例推的,
 *     标 [L4/我定的语义],**须 CTO / 上位机对标确认**。⛔ 不得当成已确认。
 *
 * **本文件只做【确定性簿记】**:
 *   给定「请在频率 f 上放一个陷波」这个请求 —— **放进哪个槽、哪些槽可以被回收、
 *   复位时什么留下什么清掉**。这些是纯机械规则,可穷举测试。
 *
 * **⛔ 本文件不决定**:
 *   **哪个频率需要陷波、什么时候放、放多深** —— 那是 AFC(adaptive-dsp)的事,
 *   经 `hook_afc` 或 `chdsp_notch_bank_request()` 传进来。
 *   ⇒ 本文件对"啸叫检测"零知识,**这是有意的**:算法层未定死之前不 C 化(CTO 裁定)。
 *
 * ============================================================================
 * 三种模式的语义 [L4/我定的语义,待确认]
 * ----------------------------------------------------------------------------
 *   FIXED    全部槽 = 固定槽。装机/调试时由**上位机**设定,运行期 AFC **不得占用**。
 *            ⇒ `request()` 一律返回 `NO_SLOT`。⇒ 「重启后仍在」。
 *   DYNAMIC  全部槽 = 动态槽。AFC 可自由分配;槽满时**回收最早分配的那个**(LRU)。
 *   HYBRID   前 `n_fixed` 个是固定槽,其余动态。
 *            ⇒ AFC 只能动动态槽,**固定槽在任何压力下都不被回收**。
 *
 * ⭐ 为什么 FIXED 这一档很可能不是摆设:低频段(45–250 Hz)的反馈点位置稳定、
 *   而该段同时受多条限制挤压 ⇒ 「装机时设定的固定陷波」很可能是那一段唯一可行的处置。
 *   ⇒ 这条是**产品判断,不是我的裁决**,已报 lead。
 */
#ifndef CHDSP_NOTCH_H
#define CHDSP_NOTCH_H

#include "chdsp_config.h"
#include "chdsp_biquad.h"

/** 槽位分配/设定的返回码。⛔ 各自不同,不得"非 0 即算过"。 */
typedef enum {
    CHDSP_NOTCH_OK           =  0,
    CHDSP_NOTCH_ERR_NO_SLOT  = -1,  /**< 没有可用的**动态**槽(含 FIXED 模式下的一律拒绝) */
    CHDSP_NOTCH_ERR_IDX      = -2,  /**< 槽号越界 */
    CHDSP_NOTCH_ERR_NOT_FIXED= -3,  /**< 想往非固定槽写"固定陷波" */
    CHDSP_NOTCH_ERR_PARAM    = -4   /**< 频率/Q/深度非法(由 chdsp_bq_design 判定) */
} chdsp_notch_err_t;

typedef struct {
    uint8_t  in_use;      /**< 该槽当前装着陷波 */
    uint8_t  is_fixed;    /**< 固定槽 ⇒ ⛔ 动态分配不得占用、不得回收 */
    uint32_t seq;         /**< 分配序号,用于 LRU 回收(0 = 未分配过) */
    double   f_hz;        /**< 记录用(设计期/遥测),⛔ 不在实时路径读 */
} chdsp_notch_slot_t;

typedef struct {
    chdsp_notch_mode_t  mode;
    uint16_t            n_fixed;      /**< 固定槽数:FIXED ⇒ 全部;DYNAMIC ⇒ 0;HYBRID ⇒ 配置值 */
    uint32_t            seq_next;
    chdsp_notch_slot_t  slot[CHDSP_NOTCH_COUNT];
    /* 遥测(⛔ 出货也保留:它们是"AFC 是否在打转"的唯一可观测量) */
    uint32_t            evict_count;  /**< 因槽满而回收的次数 */
    uint32_t            reject_count; /**< 因无动态槽而被拒的次数 */
} chdsp_notch_bank_t;

/**
 * @param mode     三种模式之一
 * @param n_fixed  仅 HYBRID 使用;FIXED/DYNAMIC 下本参数被忽略(分别按全固定/全动态)
 * ⚠ 本函数**不碰滤波器系数** —— 它只重置簿记。系数由 chain 侧的 bq_chain 管。
 */
void chdsp_notch_bank_init(chdsp_notch_bank_t *b, chdsp_notch_mode_t mode, uint16_t n_fixed);

/** 该槽是否为固定槽。 */
static inline int chdsp_notch_slot_is_fixed(const chdsp_notch_bank_t *b, uint16_t i)
{ return (i < CHDSP_NOTCH_COUNT) ? (int)b->slot[i].is_fixed : 0; }

/** 当前占用数 / 可用动态槽数(遥测与判据用)。 */
uint16_t chdsp_notch_bank_used(const chdsp_notch_bank_t *b);
uint16_t chdsp_notch_bank_free_dynamic(const chdsp_notch_bank_t *b);

/**
 * **装机时**把一个固定陷波写进指定槽(上位机路径,⛔ 不是 AFC 路径)。
 * @return NOT_FIXED 若该槽不是固定槽;IDX 若越界;PARAM 若系数非法。
 */
int chdsp_notch_bank_set_fixed(chdsp_notch_bank_t *b, chdsp_bq_chain_t *chain,
                               uint16_t idx, double f_hz, double q, double depth_db);

/**
 * **运行期** AFC 请求一个陷波(AFC 路径)。
 * 规则:①只用动态槽 ②有空用空 ③满了回收**最早分配的动态槽**(LRU)
 *       ④⛔ 任何情况下不得占用/回收固定槽
 * @param out_idx 成功时写入被占用的槽号(可传 0 忽略)
 * @return NO_SLOT 若一个动态槽都没有(FIXED 模式必然如此)
 */
int chdsp_notch_bank_request(chdsp_notch_bank_t *b, chdsp_bq_chain_t *chain,
                             double f_hz, double q, double depth_db, uint16_t *out_idx);

/** 释放一个槽(固定槽也可释放,但只有上位机路径该调)。 */
int chdsp_notch_bank_release(chdsp_notch_bank_t *b, chdsp_bq_chain_t *chain, uint16_t idx);

/**
 * ⭐ 复位**动态**槽,固定槽原样保留 —— 这是「重启后仍在」的机械形式。
 * ⛔ 与 `chdsp_bq_chain_reset()` 不同:那个只清滤波器状态,不动簿记。
 */
void chdsp_notch_bank_reset_dynamic(chdsp_notch_bank_t *b, chdsp_bq_chain_t *chain);

#endif /* CHDSP_NOTCH_H */
