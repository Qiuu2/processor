/**
 * @file    chdsp_biquad.h
 * @brief   biquad 级联内核(DF1 + 二阶误差反馈)+ 系数设计 + 系数斜坡
 *
 * ⛔ 门禁状态:未过门(2026-08-04)。作者:channel-dsp(第 1 实例)
 *
 * 数值约定全部继承 `chdsp_fixed.h`,⛔ 本文件不重新定义任何 Q 格式或移位量。
 *   · 结构 DF1(DF2 内节点最坏 135.13 dB ⇒ 需 23 bit 整数位,32-bit 装不下)
 *   · 二阶误差反馈 C(z)=A(z) **必选**(关掉最坏 −84.44 dBFS,连 PRD >106 dB 都不过)
 *   · 系数 Q4.27,解析界 max|b| ≤ 2·10^(G_max/20) ⇒ G_max < 18.0618 dB
 *
 * ---------------------------------------------------------------------------
 * ⭐ 系数斜坡(参数跳变防爆音)—— 为什么线性插值是安全的
 * ---------------------------------------------------------------------------
 * 二阶节的稳定域是 **稳定三角**:|a2| < 1 且 |a1| < 1 + a2。
 * **该集合是凸集** ⇒ 两个稳定系数点的**任意线性插值仍在三角内 ⇒ 仍稳定**。
 * ⇒ 故 a 系数可以直接线性插值,**不需要**双实例交叉淡入(省一半算力)。
 * ⇒ 该性质由 `test/check_biquad.c` 的 CHK-B4 机械验证(硬闸门)。
 * ⚠ b 系数无稳定性约束,线性插值天然安全。
 * ⚠ DF1 的状态是 x/y(真实信号),不是 DF2 的内部高增益节点
 *   ⇒ 切系数时状态连续即可,输出不跳。
 */

#ifndef CHDSP_BIQUAD_H
#define CHDSP_BIQUAD_H

#include "chdsp_config.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ==========================================================================
 * 1. 一节 biquad(运行时)
 * ========================================================================== */

/** 一节的系数 + 状态 + 斜坡目标。`chdsp_biquad_coef_t`/`_state_t` 来自 chdsp_fixed.h。 */
typedef struct {
    chdsp_biquad_coef_t  cur;        /**< 当前生效系数 */
    chdsp_biquad_coef_t  target;     /**< 斜坡目标 */
    chdsp_biquad_state_t st;
    uint16_t             ramp_left;  /**< 剩余斜坡步数;0 = 已到位 */
    uint16_t             ramp_total; /**< 本次斜坡总步数(用于插值分母) */
    uint8_t              bypass;     /**< 1 = 旁路(逐位透传,⛔ 不是"增益 0 dB 的节") */
} chdsp_bq_t;

/** 级联容器。N 由调用方按 config 常量给,⛔ 不得写字面量。 */
typedef struct {
    chdsp_bq_t *sec;      /**< 指向调用方静态分配的节数组 */
    uint16_t    n;        /**< 实际启用节数 */
    uint16_t    n_max;    /**< 数组容量(编译期常量传入) */
} chdsp_bq_chain_t;

void chdsp_bq_init(chdsp_bq_t *b);
void chdsp_bq_chain_init(chdsp_bq_chain_t *c, chdsp_bq_t *storage, uint16_t n_max);

/** 立即设置系数(不斜坡)。用于初始化 / 预设整体切换(须配合静音)。 */
void chdsp_bq_set_coef_now(chdsp_bq_t *b, const chdsp_biquad_coef_t *c);

/**
 * 设置斜坡目标。`steps` = 斜坡样本数;0 等同立即设置。
 * ⚠ 斜坡期间每样本插值一次 ⇒ 每节多 5 次插值(加/减/移位),算力见 §算力自报。
 */
void chdsp_bq_set_coef_ramp(chdsp_bq_t *b, const chdsp_biquad_coef_t *c, uint16_t steps);

/** 处理一个样本(单节)。 */
chdsp_smp_q4_27_t chdsp_bq_process1(chdsp_bq_t *b, chdsp_smp_q4_27_t x, chdsp_sat_t *sat);

/** 处理一个块(级联)。in/out 可相同(原地)。 */
void chdsp_bq_chain_process(chdsp_bq_chain_t *c, const chdsp_smp_q4_27_t *in,
                            chdsp_smp_q4_27_t *out, uint16_t n_samples, chdsp_sat_t *sat);

/** 复位全部状态(bypass↔active 切换语义:状态清零,系数不动)。 */
void chdsp_bq_chain_reset(chdsp_bq_chain_t *c);

/* ==========================================================================
 * 2. 系数设计(**设计期**,double;⛔ 不在实时路径调用)
 * ==========================================================================
 * 全部返回 0 = 成功,非 0 = 失败(系数超 Q4.27 范围 / 参数非法)。
 * ⛔ 失败必须由调用方处理 —— 这是 D-1 的执行点,不是警告。
 */
/** 设计期错误码。⭐ **必须可区分** —— 检查要断言「预期的那条具体失败」,
 *  ⛔ 不是"任何失败"。(critic 对 check_negcompile 的 BLOCKER 同源:
 *     `expect_fail` 只问"编译是否失败" ⇒ 任何错误都算过 ⇒ 被测物拿走也 PASS。) */
typedef enum {
    CHDSP_BQ_OK              =  0,
    CHDSP_BQ_ERR_FREQ        = -1,  /**< f0 ≤ 0 或 ≥ Nyquist */
    CHDSP_BQ_ERR_Q           = -2,  /**< Q/S ≤ 0 或使 α 为 NaN */
    CHDSP_BQ_ERR_GAIN_ENV    = -3,  /**< ⭐ 增益超 Q4.27 的解析硬包络(18.0618 dB) */
    CHDSP_BQ_ERR_COEF_RANGE  = -4,  /**< 某个系数实际超 Q4.27(兜底,理论上被 -3 提前拦住) */
    CHDSP_BQ_ERR_TYPE        = -5,
    CHDSP_BQ_ERR_ORDER       = -6
} chdsp_bq_err_t;

typedef enum {
    CHDSP_FT_PEAKING = 0,
    CHDSP_FT_LOWSHELF,
    CHDSP_FT_HIGHSHELF,
    CHDSP_FT_LPF,
    CHDSP_FT_HPF,
    CHDSP_FT_NOTCH,
    CHDSP_FT_ALLPASS,
    CHDSP_FT_COUNT
} chdsp_filter_type_t;

/**
 * RBJ Audio EQ Cookbook 归一化系数。
 * @param gain_db 仅 PEAKING / LOWSHELF / HIGHSHELF 使用;其余忽略
 * @param q       PEAKING/LPF/HPF/NOTCH/ALLPASS 用 Q;架式用 S(slope)
 * ⚠ LPF/HPF 走**结构约束量化**(只量化 b0,b1=∓2b0,b2=b0)⇒ DC/Nyquist 零点在量化后仍精确。
 *   实测:自由量化在 251/500 个 fc 上破坏 DC 零点,最坏单节 DC 增益 −59.26 dB。
 */
int chdsp_bq_design(chdsp_filter_type_t type, double f0_hz, double q_or_s,
                    double gain_db, chdsp_biquad_coef_t *out);

/**
 * Butterworth / Linkwitz-Riley 分频器的一支(高通或低通)展开成级联系数。
 * @param lr        非 0 = Linkwitz-Riley(= Butterworth 的平方);0 = Butterworth
 * @param order     总阶数。LR 只有偶数阶存在(LR = BW²)⇒ lr!=0 时 order ∈ {2,4,6,8}
 * @param highpass  非 0 = 高通
 * @param out       至少 order/2 节
 * @param n_out     实际写入节数
 * ⚠ **LR 的求和极性由阶数决定**:order mod 4 == 0 ⇒ 同相;== 2 ⇒ **须反相**。
 *   由 `chdsp_xover_needs_polarity_flip()` 给出,⛔ 不得由界面自由选。
 */
int chdsp_bq_design_xover(int lr, int order, int highpass, double fc_hz,
                          chdsp_biquad_coef_t *out, uint16_t *n_out);

/* ==========================================================================
 * 2a. ⛔⛔ 分频「阶数 n」与「斜率 dB/oct」是两个量 —— 用类型把它们分开
 * ==========================================================================
 * 事故形态(2026-08-04,lead 急件 / critic 设计侧):
 *   设计件 §4③ 的表头把 **12/24/36/48** 叫「LR 阶数」,而下一行「阶数 mod 4」
 *   算的是 **2/4/6/8**。§0 只写「阶数 mod 4 == 0 ⇒ 同相」,**不说是哪个「阶数」**。
 *   而参数字典里的 `xo_slope` 值域正是 {12,24,36,48} dB/oct
 *   ⇒ 实现方按参数值直接套 ⇒ 12/24/36/48 mod 4 **全 = 0** ⇒ **全判同相**
 *   ⇒ LR2 / LR6 在分频点出现深谷(实测 65.86 / 56.32 dB)。
 *
 * ⚠ 实证(本文件改动前):
 *     chdsp_xover_needs_polarity_flip(1, 12/24/36/48) = 0, 0, 0, 0
 *     chdsp_xover_needs_polarity_flip(1,  2/ 4/ 6/ 8) = 1, 0, 1, 0   ← 正确答案
 *
 * ⭐ 而**设计函数**(chdsp_bq_design_xover/xover2)早就有 `order > 8 ⇒ ERR_ORDER`
 *   ⇒ 喂 dB/oct 会**当场硬失败**,是安全的。
 *   **只有极性函数没有量程守卫,而它恰恰返回一个"看起来合理"的布尔值。**
 *   ⇒ 教训:**返回 bool 的函数最危险 —— 它没有"非法输入"这个取值。**
 *
 * ⇒ 修法(D-1「用接口不允许来防,不用文档提醒来防」,复用本项目已有的强类型机制):
 *   ① 两个量各自成类型 ⇒ 传错**编译不过**(STRICT_TYPES=1);
 *   ② 标识符自带单位:`_n` vs `_db_oct`,⛔ 不许有叫「order」而值域是 dB/oct 的东西;
 *   ③ 运行期量程守卫(STRICT_TYPES=0 下的兜底):非法 ⇒ 返回 −1,⛔ 不是 0。
 */
/** 分频**阶数 n**(2/4/6/8…)。⛔ 不是 dB/oct。 */
CHDSP_DEFTYPE(chdsp_xo_order_t, int32_t);
/** 分频**斜率 dB/oct**(12/24/36/48)。⛔ 不是阶数。 */
CHDSP_DEFTYPE(chdsp_xo_slope_t, int32_t);

static inline chdsp_xo_order_t chdsp_xo_order(int32_t n)
{ return CHDSP_MK(chdsp_xo_order_t, n); }
static inline int32_t chdsp_xo_order_n(chdsp_xo_order_t o)
{ return CHDSP_RAW(o); }
static inline chdsp_xo_slope_t chdsp_xo_slope(int32_t db_oct)
{ return CHDSP_MK(chdsp_xo_slope_t, db_oct); }
static inline int32_t chdsp_xo_slope_db_oct(chdsp_xo_slope_t s)
{ return CHDSP_RAW(s); }

/** dB/oct → 阶数(6 dB/oct = 1 阶)。非 6 的倍数 ⇒ 返回 n = 0(非法,下游会拒)。 */
#ifndef CHDSP_BROKEN_SLOPE_CONV      /* 1 = dB/oct→阶数 换算用错因子(6 dB/oct = 1 阶) */
#  define CHDSP_BROKEN_SLOPE_CONV 0
#endif
static inline chdsp_xo_order_t chdsp_xo_order_from_slope(chdsp_xo_slope_t s)
{
    int32_t d = CHDSP_RAW(s);
#if CHDSP_BROKEN_SLOPE_CONV
    return CHDSP_MK(chdsp_xo_order_t, ((d > 0) && (d % 12 == 0)) ? (d / 12) : 0);  /* ⛔ */
#else
    return CHDSP_MK(chdsp_xo_order_t, ((d > 0) && (d % 6 == 0)) ? (d / 6) : 0);
#endif
}
static inline chdsp_xo_slope_t chdsp_xo_slope_from_order(chdsp_xo_order_t o)
{ return CHDSP_MK(chdsp_xo_slope_t, CHDSP_RAW(o) * 6); }

/**
 * LR 分频器的该**阶数 n** 是否需要把一支反相后再求和。
 * @param lr       非 0 = Linkwitz-Riley;0 = 其它类型(BW/Bessel)⇒ 恒返回 0
 * @param order_n  **阶数 n**(2/4/6/8),⛔ 不是 dB/oct
 * @return 1 = 须反相;0 = 同相;**−1 = 参数非法(⛔ 调用方必须处理,不得当 0 用)**
 *
 * ⚠ 规则 `n mod 4 == 2 ⇒ 反相` **只对 LR 成立**:
 *   LR = BW² 是全通求和分频,选对极性后求和精确平坦(实测 0.0000 dB)。
 *   **Bessel 不是**(两个相位都不平坦,最好 1.686 dB)⇒ 本函数对非 LR 返回 0 是正确行为。
 *   **BW 奇数阶求和恒平坦**(0.0000 dB,与极性无关)。
 */
int chdsp_xover_needs_polarity_flip(int lr, chdsp_xo_order_t order_n);

/* ==========================================================================
 * 2b. 分频类型(C 第二批,r8)—— 补齐参数表 §4③ 已列出但实现拿不出来的档位
 * ========================================================================== */
typedef enum {
    CHDSP_XO_BUTTERWORTH = 0,
    CHDSP_XO_LINKWITZ_RILEY,        /**< = Butterworth²,⛔ 只有偶数阶存在 */
    CHDSP_XO_BESSEL,
    CHDSP_XO_TYPE_COUNT
} chdsp_xover_type_t;

/**
 * 一阶 LPF/HPF(双线性 + 预畸),以双二阶形式返回(b2 = a2 = 0)。
 * 奇数阶 Butterworth / Bessel 必含一个这样的节。
 * ⚠ max|b| ≤ 1 [L2/宿主实测 EXP-9b] ⇒ Q4.27 装得下,不需要额外包络检查。
 */
int chdsp_bq_design_first_order(int highpass, double fc_hz, chdsp_biquad_coef_t *out);

/**
 * ⭐ 分频器设计(**通用版**,支持 BW/LR/Bessel × 1..8 阶)。
 * @param type  见 chdsp_xover_type_t
 * @param order 1..8。⛔ LR 只接受偶数阶(LR = BW²,奇数阶数学上不存在)
 * @param out   至少 (order+1)/2 节;LR 需 order/2 节
 *
 * ⛔⛔ **Bessel 走的不是逐节 RBJ 那条路**(r8 证伪条件 F-2 命中后定位):
 *   Butterworth/LR 的所有节共用同一个 ω0 = ωc ⇒「逐节各自预畸」与「整支预畸一次」重合,
 *   所以 RBJ 那条路对它们是对的。**Bessel 各节 ω0 互不相同 ⇒ 重合消失。**
 *   照搬 RBJ 逐节设计,8 阶高通与独立第二轨(scipy)差 **91.7 dB**。
 *   ⇒ Bessel 用【归一化极点表 → 单次预畸 → 双线性】。
 *
 * ⚠ **Bessel 的 LP+HP 求和不平坦**(实测最好一相 1.686 dB @4 阶,最差 25.4 dB @8 阶)
 *   ⇒ `chdsp_xover_needs_polarity_flip()` 那条「阶数 mod 4」规则**对 Bessel 不适用**。
 *   Bessel 的卖点是群延迟平坦,不是求和平坦。[L2/宿主实测 EXP-11]
 */
int chdsp_bq_design_xover2(chdsp_xover_type_t type, int order, int highpass,
                           double fc_hz, chdsp_biquad_coef_t *out, uint16_t *n_out);

/* ==========================================================================
 * 3. 算力自报(解析估计,⛔ 非实测)
 * ==========================================================================
 * 每节每样本(DF1 + 二阶 EF,整数模式):
 *   5 次 MAC(b0,b1,b2,a1,a2)
 * + 2 次 EF 乘 + 2 次移位
 * + 1 次舍入加 + 1 次移位 + 饱和比较 2 次
 * + 状态搬移 6 次
 * ⇒ **≈ 7 乘 + 12 其它 op / 节 / 样本** [L3/解析]
 * 斜坡期间另加 5 次插值(乘 + 移位 + 加)⇒ +5 乘 [L3/解析]
 * ⚠ ⛔ 这是**解析估计,不是周期数**。SHARC+ 的实际 cyc/biquad 待 W1-C 微基准;
 *   厂家锚点 2.5 cyc/biquad 是**浮点**数(EE-408 基准代码为 float),定点值未测。
 */
#define CHDSP_BQ_MUL_PER_SEC_PER_SAMPLE      7
#define CHDSP_BQ_OTHER_OP_PER_SEC_PER_SAMPLE 12
#define CHDSP_BQ_RAMP_EXTRA_MUL              5

#ifdef __cplusplus
}
#endif
#endif /* CHDSP_BIQUAD_H */
