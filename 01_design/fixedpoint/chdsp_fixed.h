/**
 * @file    chdsp_fixed.h
 * @brief   CONF-DSP-88 · 定点格式与量纲约定 —— 全模块唯一 include 源
 *
 * ============================================================================
 * ⛔⛔ 门禁状态:**未过门**(2026-08-04)
 *     本文件尚未经独立 critic 评审。禁止 release / 冻结 / 被其他工件引用为依据 /
 *     对外承诺。归档性使用须带 `[未过门]` 前缀。
 *     作者:channel-dsp(第 1 实例)｜ 归属交付物:D3/D4 的前置件「定点格式与量纲约定」
 * ============================================================================
 *
 * 平台:ADSP-21569 SHARC+ 单核 ｜ fs = 48 kHz ｜ 定点口径(DEC-0006)
 *
 * ---------------------------------------------------------------------------
 * ⭐ 本文件存在的理由(读之前先读这一段)
 * ---------------------------------------------------------------------------
 * 量纲错误不能靠注释防。本文件把「样本 / 系数 / 增益 / dB / 累加器」做成
 * **互不可赋值的类型**,并且**不向调用方暴露任何移位量** —— 所有定标转换只能
 * 经本文件的函数发生。⇒「用错量纲」在类型层就编译不过。
 *
 *   ⛔ 调用方永远不写:  (int32_t)(acc >> 27)      ← 这类代码是本文件要消灭的对象
 *   ✅ 调用方只写:      chdsp_acc_to_smp(&acc, &sat)
 *
 * `CHDSP_STRICT_TYPES=1`(默认)下类型是 struct ⇒ 混用编译不过。
 * 目标 build 可置 0 换回裸 int32_t 以避免 ABI 开销,但**必须与 =1 的构建逐位一致**
 * (check_fixed.c 的 CHK-9 就是这条的机械证明)。
 *
 * ---------------------------------------------------------------------------
 * ⚠ 前提(变了就要重审本文件)
 * ---------------------------------------------------------------------------
 * P1. 标称输入电平 +4 dBu ⇔ −20 dBFS(CTO 2026-08-04 拍板),余量 20 dB。
 *     ⚠ **这是【设计标称】,不是模拟前端的实况。** 本项目参考 codec 为
 *     ADAU1979:满量程差分输入 = **4.5 V rms(typ)= +15.28 dBu** [L2/厂家 datasheet]。
 *     ⇒ 要实现「+4 dBu ⇔ −20 dBFS」,模拟前端须在 ADC 前提供 **−8.72 dB** 的净衰减
 *       (使 0 dBFS ⇔ +24 dBu = 12.28 V rms)。
 *     ⇒ 若前端为单位增益直入,则实际为「+4 dBu ⇔ −11.28 dBFS」,余量只有 11.28 dB,
 *       本文件 §余量策略 的两个数须重算。**模拟前端选型定稿后必须回核本条。**
 * P2. dBFS 参考约定 = **峰值参考**:0 dBFS ⇔ |x| = 1.0。
 *     (与 IF-v1.4 回执确立的项目约定同源。对正弦而言与「满幅正弦 RMS = 0 dBFS」
 *      约定给出相同读数;对噪声/节目素材两者差 3.01 dB ⇒ 本项目一律用峰值参考。)
 * P3. codec 为 24-bit(ADAU1979 / ADAU1962A),TDM 槽宽 32 bit,数据左对齐。
 * P4. 累加器为 SHARC+ 定点 MRF = **80 bit(64 bit 结果 + 16 guard)**
 *     [L2/厂家:SHARC+ Core Programming Reference,"Multiplier ... 80-bit fixed-point
 *      accumulator";HW Ref §38 "A 32-bit fixed-point operation generates 80-bit
 *      results (64-bit result + 16 guard bits)"]。
 *     ⚠ **注意:SHARC+ 的「40-bit」是【扩展精度浮点】格式,不是定点。**
 *        定点数据在 40-bit 寄存器里左对齐占高 32 bit,低 8 bit 读时忽略、写时清零
 *        [L2/厂家 Core PR §Data Registers] ⇒ **定点路径拿不到那 8 bit。**
 *        定点的额外精度来自 80-bit MRF,不来自 40-bit 寄存器宽度。
 *
 * ---------------------------------------------------------------------------
 * 格式表(唯一事实源;改这张表 = 改全项目接口)
 * ---------------------------------------------------------------------------
 *  类型                      Q 记法   位宽  范围            LSB      用途
 *  chdsp_io_q0_31_t          Q0.31    32   [−1, 1)         2^−31   codec 边界样本
 *  chdsp_smp_q4_27_t         Q4.27    32   [−16, 16)       2^−27   链内样本(+24.08dB 余量)
 *  chdsp_coef_q4_27_t        Q4.27    32   [−16, 16)       2^−27   滤波器系数
 *  chdsp_gain_q4_27_t        Q4.27    32   [−16, 16)       2^−27   线性增益
 *  chdsp_db_q23_8_t          Q23.8    32   ±2^23 dB        1/256dB dB 域参数
 *  chdsp_acc_t               Q9.54+   ≥66  见 §累加器      2^−54   MAC 累加器
 *
 *  ⚠ **Q 记法口径(全项目统一,继承 W1-A §3.1-1 的记法统一声明)**:
 *     写 `Qm.n` = **1 符号位 + m 整数位 + n 小数位**,总位宽 = 1+m+n。
 *     故 Q0.31 = 32 bit 范围 [−1,1);Q4.27 = 32 bit 范围 [−16,16)。
 *     常见异名「Q5.27 / Q1.31」(把符号计入整数位)与此**同物异名**,本项目不用。
 *     单数字写法 `Qn` 一律读作 `Q0.n`(故旧文里的「Q31」= 本文 Q0.31,「Q15」= Q0.15)。
 *
 * ---------------------------------------------------------------------------
 * 承重结论一览(全部有出处;数字的完整工作点见 D34_FIXEDPOINT_CONVENTION_v0.1.md)
 * ---------------------------------------------------------------------------
 *  · 溢出策略 = **饱和**,禁回绕。回绕 = 符号翻转 = 满量程爆音。
 *  · 舍入策略 = **就近舍入(RTN)**,禁截断。截断在 DF1 递归里产生的 DC 偏置被
 *    该节的 |1/A(1)| 放大(20 Hz BW HPF:A(1)=1+a1+a2=6.8412e−6 ⇒ |1/A(1)| = **1.4617e5**
 *    ⇒ 半 LSB(2^−28)经它 = **−65.3 dBFS** 直流)。
 *    〔整改 2026-08-04 · critic m-5:原写「≈1.0e5 ⇒ −68.6 dBFS」——**那个 1.0e5 无出处**。
 *      (results_design_bounds §C 的 1.4617e5 是 max|1/A|,与本处的 |1/A(1)| 是不同的量,
 *       只是数值恰好相同。)⇒ 方向不变(真值更坏 3.3 dB),但这是承重论证里的无源数。〕
 *  · biquad 结构 = **DF1**,禁 DF2/DF2T。理由是量的:DF2 内节点峰值增益
 *    max|1/A| 在 PEQ 20 Hz/Q=20/+15 dB 处达 **135.1 dB(5.71e6)⇒ 需额外 23 bit 整数位**,
 *    32-bit 装不下 [L2/宿主仿真]。
 *  · **二阶误差反馈(EF)为必选,不是可选优化。** 取 C(z)=A(z) ⇒ 噪声传函 ≡ 1。
 *    实测(定点仿真,8 个算例,Q4.27):有 EF 一律 −173.3x dBFS(与 q²/12 预测差 ≤0.02 dB),
 *    与该节 NG(40–91 dB)无关;无 EF 则最坏 **−84.44 dBFS** ⇒ **连 PRD 的 >106 dB 都不过**。
 *    〔整改 2026-08-04 · critic m-4:原写 −84.75,那是**临时脚本**的数;
 *      归档 C 轨实测(results_r3_detail/out_CHDSP_BROKEN_NOEF.txt:50)是 −84.44。
 *      ⛔ 只用有 deps 行的那份。〕
 *  · 0 dB 的 PEQ 节在 DF1 下是**逐位恒等**(b≡a ⇒ 累加器低位恒 0),
 *    旁路它的理由是**省算力**,⛔ 不是省噪声(此处曾有一条我自己写下并当场被证伪的断言)。
 */

#ifndef CHDSP_FIXED_H
#define CHDSP_FIXED_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ==========================================================================
 * 0. 构建开关
 * ========================================================================== */

/** 强类型开关。=1(默认):量纲混用编译不过。=0:退化为裸整数(仅目标 build 的
 *  ABI 逃生口),**须由 CHK-9 证明与 =1 逐位一致后才允许使用**。 */
#ifndef CHDSP_STRICT_TYPES
#  define CHDSP_STRICT_TYPES 1
#endif

/** 调试断言(累加器越界 / 参数域)。Release 置 0。 */
#ifndef CHDSP_DEBUG_ASSERT
#  define CHDSP_DEBUG_ASSERT 1
#endif

/** ⛔ 仅供自验用的「坏版本」开关。出货构建下三者必须全为 0,由 CHK-0 机械核。 */
#ifndef CHDSP_BROKEN_WRAP        /* 1 = 窄化改回绕(去掉饱和) */
#  define CHDSP_BROKEN_WRAP 0
#endif
#ifndef CHDSP_BROKEN_TRUNC       /* 1 = 窄化改截断(去掉就近舍入) */
#  define CHDSP_BROKEN_TRUNC 0
#endif
#ifndef CHDSP_BROKEN_NOEF        /* 1 = 关掉误差反馈 */
#  define CHDSP_BROKEN_NOEF 0
#endif

/* C99 静态断言(不依赖 C11) */
#define CHDSP_STATIC_ASSERT(cond, tag) \
    typedef char chdsp_static_assert_##tag[(cond) ? 1 : -1]

/* ==========================================================================
 * 1. 格式常数 —— 唯一定义处
 * ========================================================================== */

#define CHDSP_IO_FRACBITS     31   /**< codec 边界样本小数位 */
#define CHDSP_SMP_FRACBITS    27   /**< 链内样本小数位 */
#define CHDSP_COEF_FRACBITS   27   /**< 系数小数位 */
#define CHDSP_GAIN_FRACBITS   27   /**< 线性增益小数位(与样本同域,便于共用 MAC) */
#define CHDSP_DB_FRACBITS      8   /**< dB 量小数位 ⇒ 步进 1/256 dB */

/** 链内余量 = 样本整数位数,单位 dB。4 bit ⇒ 24.0824 dB。 */
#define CHDSP_HEADROOM_BITS   (CHDSP_IO_FRACBITS - CHDSP_SMP_FRACBITS)   /* = 4 */

/** 累加器→样本的重量化移位。**唯一一处出现移位量的地方。** */
#define CHDSP_ACC_TO_SMP_SHIFT  (CHDSP_COEF_FRACBITS)                    /* = 27 */
CHDSP_STATIC_ASSERT(CHDSP_SMP_FRACBITS + CHDSP_COEF_FRACBITS
                    - CHDSP_ACC_TO_SMP_SHIFT == CHDSP_SMP_FRACBITS, acc_shift);
CHDSP_STATIC_ASSERT(CHDSP_HEADROOM_BITS == 4, headroom_bits);

/** 系数绝对值硬上界(Q4.27 可表示范围)。设计期系数必须 < 此值,否则 chdsp_coef_from_f64 失败。 */
#define CHDSP_COEF_ABS_MAX_INT  16          /* 2^(31-27) */

/** dB 域可用区间。低于 CHDSP_DB_MUTE 一律给出精确 0(静音)。 */
#define CHDSP_DB_MUTE_Q8    (-144 * 256)    /**< −144.0 dB ⇒ 增益精确 0 */
#define CHDSP_DB_MAX_Q8     ( +24 * 256)    /**< +24.0 dB ⇒ 增益 15.849 < 16 ✓ */

/* ==========================================================================
 * 2. 强类型
 * ========================================================================== */

#if CHDSP_STRICT_TYPES
#  define CHDSP_DEFTYPE(name, base) typedef struct { base v; } name
#  define CHDSP_RAW(x)              ((x).v)
#  define CHDSP_MK(T, raw)          ((T){ (raw) })
#else
#  define CHDSP_DEFTYPE(name, base) typedef base name
#  define CHDSP_RAW(x)              (x)
#  define CHDSP_MK(T, raw)          ((T)(raw))
#endif

/** codec 边界样本,Q0.31。1.0 = 0 dBFS(峰值参考)。 */
CHDSP_DEFTYPE(chdsp_io_q0_31_t,   int32_t);
/** 链内样本,Q4.27。**与 io 同一个 0 dBFS 参考**,只是多 4 bit 整数余量。 */
CHDSP_DEFTYPE(chdsp_smp_q4_27_t,  int32_t);
/** 滤波器系数,Q4.27,无量纲。 */
CHDSP_DEFTYPE(chdsp_coef_q4_27_t, int32_t);
/** 线性增益,Q4.27,无量纲。 */
CHDSP_DEFTYPE(chdsp_gain_q4_27_t, int32_t);
/** dB 量,Q23.8。 */
CHDSP_DEFTYPE(chdsp_db_q23_8_t,   int32_t);

/* ---- 累加器 ---------------------------------------------------------------
 * ⚠ 这里有两个不同的量,**不许混为一谈**(r2 的 CHK-11b 就是踩了这一脚):
 *
 *  (a)【类型范围上界,构造上不可超越】|X|≤2^31 ∧ |C|≤2^31 ⇒ |X·C| ≤ 2^62;
 *      DF1+EF 一节 = **5 个大项 + 2 个小项**(⛔ 不是「7 个每项 ≤2^62」):
 *        · 5 个 x/y 乘积项:各 |X·C| ≤ 2^31·2^31 = 2^62
 *        · 2 个 EF 修正项 :**经 >>27 之后 ≤ 2^31**,比大项小 31 bit ⇒ 可忽略
 *      ⇒ 真界 = 5·2^62 + 2·2^31 = 2^64.322 ⇒ **需 66 bit 有符号**。
 *      〔整改 2026-08-04 · critic m-7:原按「7·2^62 = 2^64.807」推。
 *        **结论 66 bit 不变**,但按「7 项」外推会高估 —— 下次有人加项时会错。〕
 *      [L2/宿主实测 CHK-3:log2 = 64.807]
 *  (b)【本项目参数范围内的实测占用】最坏合法配置(低架 20 Hz S=1 +15 dB,
 *      满量程方波激励)实测 **58.005 bit** [L2/宿主实测 CHK-11]。
 *
 *  ⇒ **int64(63 bit 有效)在 (b) 下够用、在 (a) 下不够。**
 *    本文件按 (a) 要求 ≥66 bit,理由不是"保守",而是:
 *    (b) 是**经验扫描**,随参数范围放宽而失效(与 b 系数上界同一性质);
 *    而 SHARC+ 的 MRF 本来就是 80 bit,按 (a) 要求**不花任何代价**。
 *  ⛔ 因此禁止把累加器降到 int64 —— 但**理由必须写成上面这句,不得写成
 *    "int64 在真实工况下会溢出"(那句已被 r2 实测证伪)**。
 *   · 目标(SHARC+):MRF = 80 bit ⇒ 相对 (a) 富余 14 bit ✓
 *   · 宿主参考实现:__int128
 * -------------------------------------------------------------------------- */
#if defined(__SIZEOF_INT128__)
typedef __int128 chdsp_acc_raw_t;
#  define CHDSP_ACC_HAS_128 1
#else
#  error "chdsp_fixed.h 需要 128-bit 整数(宿主)或 SHARC+ 80-bit MRF(目标)。int64 位宽不足,见 §累加器。"
#endif

CHDSP_DEFTYPE(chdsp_acc_t, chdsp_acc_raw_t);

/** 饱和/溢出遥测。⚠ 报警必须接处置(团队纪律 D3):本结构的消费者在 §7 写死。 */
typedef struct {
    uint32_t sat_count;    /**< 本统计窗内发生窄化饱和的次数 */
    uint8_t  sat_sticky;   /**< 粘滞位:发生过即置 1,由消费者显式清 */
} chdsp_sat_t;

/* ==========================================================================
 * 3. 构造 / 取值(唯一合法的「进出类型」通道)
 * ========================================================================== */

static inline chdsp_io_q0_31_t   chdsp_io_from_raw(int32_t r)   { return CHDSP_MK(chdsp_io_q0_31_t, r); }
static inline chdsp_smp_q4_27_t  chdsp_smp_from_raw(int32_t r)  { return CHDSP_MK(chdsp_smp_q4_27_t, r); }
static inline chdsp_coef_q4_27_t chdsp_coef_from_raw(int32_t r) { return CHDSP_MK(chdsp_coef_q4_27_t, r); }
static inline chdsp_gain_q4_27_t chdsp_gain_from_raw(int32_t r) { return CHDSP_MK(chdsp_gain_q4_27_t, r); }
static inline chdsp_db_q23_8_t   chdsp_db_from_raw(int32_t r)   { return CHDSP_MK(chdsp_db_q23_8_t, r); }

static inline int32_t chdsp_io_raw(chdsp_io_q0_31_t x)   { return CHDSP_RAW(x); }
static inline int32_t chdsp_smp_raw(chdsp_smp_q4_27_t x) { return CHDSP_RAW(x); }
static inline int32_t chdsp_coef_raw(chdsp_coef_q4_27_t x){ return CHDSP_RAW(x); }
static inline int32_t chdsp_gain_raw(chdsp_gain_q4_27_t x){ return CHDSP_RAW(x); }
static inline int32_t chdsp_db_raw(chdsp_db_q23_8_t x)   { return CHDSP_RAW(x); }

/** dB 便利构造:整数 dB。小数 dB 用 chdsp_db_from_millidb()。 */
static inline chdsp_db_q23_8_t chdsp_db(int32_t whole_db)
{ return CHDSP_MK(chdsp_db_q23_8_t, whole_db << CHDSP_DB_FRACBITS); }
/** dB 便利构造:千分之一 dB(参数字典若用 0.1 dB 步进,传 100 的倍数)。 */
static inline chdsp_db_q23_8_t chdsp_db_from_millidb(int32_t mdb)
{ return CHDSP_MK(chdsp_db_q23_8_t, (int32_t)(((int64_t)mdb * 256 + (mdb >= 0 ? 500 : -500)) / 1000)); }

/* ==========================================================================
 * 4. 饱和原语
 * ==========================================================================
 * ⛔ 音频里回绕 = 正峰翻成大负值 = 满量程爆音。所有窄化点一律饱和。
 * 目标侧对应指令:`MRF = SAT MRF`(两补码分数),溢出可由 STKY.MOS 粘滞位读出
 * [L2/厂家 Core PR §Multiply Register Instruction Types / Arithmetic Status]。
 */
static inline int32_t chdsp_sat_i64_to_i32(int64_t v, chdsp_sat_t *st)
{
#if CHDSP_BROKEN_WRAP
    (void)st; return (int32_t)v;                    /* ⛔ 坏版本:回绕 */
#else
    if (v > (int64_t)INT32_MAX) { if (st) { st->sat_count++; st->sat_sticky = 1u; } return INT32_MAX; }
    if (v < (int64_t)INT32_MIN) { if (st) { st->sat_count++; st->sat_sticky = 1u; } return INT32_MIN; }
    return (int32_t)v;
#endif
}

/* ⚠ D6-ao 接线审计(2026-08-04 · critic m-6):本函数**全库零消费者**。
 *   保留理由:它是「饱和加」的规范写法,D3/D4 的求和/混音落地时会用到(矩阵求和尚未 C 化)。
 *   ⛔ 在有第一个消费者之前,它**未被任何测试覆盖** —— 不得假定它对。 */
static inline int32_t chdsp_sat_add_i32(int32_t a, int32_t b, chdsp_sat_t *st)
{ return chdsp_sat_i64_to_i32((int64_t)a + (int64_t)b, st); }

/* ==========================================================================
 * 5. 累加器 —— **调用方看不到任何移位量**
 * ========================================================================== */

static inline void chdsp_acc_clear(chdsp_acc_t *a)
{ CHDSP_RAW(*a) = (chdsp_acc_raw_t)0; }

/** acc += x·c */
static inline void chdsp_acc_mac(chdsp_acc_t *a, chdsp_smp_q4_27_t x, chdsp_coef_q4_27_t c)
{ CHDSP_RAW(*a) += (chdsp_acc_raw_t)CHDSP_RAW(x) * (chdsp_acc_raw_t)CHDSP_RAW(c); }

/** acc −= x·c */
static inline void chdsp_acc_msub(chdsp_acc_t *a, chdsp_smp_q4_27_t x, chdsp_coef_q4_27_t c)
{ CHDSP_RAW(*a) -= (chdsp_acc_raw_t)CHDSP_RAW(x) * (chdsp_acc_raw_t)CHDSP_RAW(c); }

/** 直接把一个链内样本加进累加器(等价于乘 1.0,但不花一次乘法)。 */
/* ⚠ D6-ao 接线审计(2026-08-04 · critic m-6):本函数**全库零消费者**。同上,未被覆盖。 */
static inline void chdsp_acc_add_smp(chdsp_acc_t *a, chdsp_smp_q4_27_t x)
{ CHDSP_RAW(*a) += ((chdsp_acc_raw_t)CHDSP_RAW(x)) << CHDSP_COEF_FRACBITS; }

/**
 * 累加器 → 链内样本。**就近舍入 + 饱和**,移位量由格式推出。
 * @param resid_out 可为 NULL;否则回写舍入残差 r = acc − (y << SHIFT)(累加器单位),
 *                  供二阶误差反馈使用。
 */
static inline chdsp_smp_q4_27_t chdsp_acc_to_smp_r(chdsp_acc_t a, chdsp_sat_t *st,
                                                   chdsp_acc_raw_t *resid_out)
{
    const chdsp_acc_raw_t acc = CHDSP_RAW(a);
#if CHDSP_BROKEN_TRUNC
    const chdsp_acc_raw_t q = acc >> CHDSP_ACC_TO_SMP_SHIFT;                  /* ⛔ 坏版本:截断 */
#else
    const chdsp_acc_raw_t half = ((chdsp_acc_raw_t)1) << (CHDSP_ACC_TO_SMP_SHIFT - 1);
    const chdsp_acc_raw_t q = (acc + half) >> CHDSP_ACC_TO_SMP_SHIFT;         /* 就近舍入 */
#endif
    if (resid_out) { *resid_out = acc - (q << CHDSP_ACC_TO_SMP_SHIFT); }
    /* 饱和到 int32 */
    int32_t y;
#if CHDSP_BROKEN_WRAP
    (void)st; y = (int32_t)q;
#else
    if      (q > (chdsp_acc_raw_t)INT32_MAX) { if (st) { st->sat_count++; st->sat_sticky = 1u; } y = INT32_MAX; }
    else if (q < (chdsp_acc_raw_t)INT32_MIN) { if (st) { st->sat_count++; st->sat_sticky = 1u; } y = INT32_MIN; }
    else                                     { y = (int32_t)q; }
#endif
    return CHDSP_MK(chdsp_smp_q4_27_t, y);
}

static inline chdsp_smp_q4_27_t chdsp_acc_to_smp(chdsp_acc_t a, chdsp_sat_t *st)
{ return chdsp_acc_to_smp_r(a, st, NULL); }

/* ==========================================================================
 * 6. I/O 边界转换 —— 唯一合法的 Q0.31 ↔ Q4.27 通道
 * ========================================================================== */

/** codec → 链内。右移 CHDSP_HEADROOM_BITS。**无损**:codec 为 24-bit,
 *  Q4.27 仍在 ADC LSB 之下留 **4** bit(2^−27 = 2^−23/16 ⇒ 16 = 2^4)。
 *  〔整改 2026-08-04 · critic m-3:原写 3 bit,与文档 §2.2 的 4 bit 矛盾;**正确是 4**。〕 */
static inline chdsp_smp_q4_27_t chdsp_io_to_smp(chdsp_io_q0_31_t x)
{ return CHDSP_MK(chdsp_smp_q4_27_t, (int32_t)(CHDSP_RAW(x) >> CHDSP_HEADROOM_BITS)); }

/** 链内 → codec。左移 + **饱和**。这是全链**唯一合法的削波点**;
 *  在它之前必须由输出限幅器把电平压住(D4 职责)。 */
static inline chdsp_io_q0_31_t chdsp_smp_to_io(chdsp_smp_q4_27_t x, chdsp_sat_t *st)
{
    const int64_t v = ((int64_t)CHDSP_RAW(x)) << CHDSP_HEADROOM_BITS;
    return CHDSP_MK(chdsp_io_q0_31_t, chdsp_sat_i64_to_i32(v, st));
}

/* ==========================================================================
 * 7. 饱和遥测的**消费者**(D3:加了报警必须同时接上处置)
 * ==========================================================================
 * 本文件只产生事实(计数 + 粘滞位),判断留给接收方(Interface contract #7)。
 * 已定的三个消费者(D3/D4 落地时逐条接线,缺任一即视为本机制未闭环):
 *   C-A 诊断遥测:每统计窗把 {sat_count, sat_sticky} 随电平表上报上位机 → CLIP 指示。
 *   C-B Debug 构建:CHDSP_DEBUG_ASSERT=1 时,链内(非输出端)饱和直接 assert
 *       —— 链内饱和意味着余量策略被突破,属设计缺陷,不是运行工况。
 *   C-C 输出保护:输出端饱和计数进入 D4 音箱保护限幅器的输入(持续饱和 ⇒ 降增益)。
 */
static inline void chdsp_sat_reset(chdsp_sat_t *st) { st->sat_count = 0u; st->sat_sticky = 0u; }
static inline int  chdsp_sat_tripped(const chdsp_sat_t *st) { return st->sat_sticky != 0u; }

/* ==========================================================================
 * 8. 二阶误差反馈(EF)—— **必选**,不是可选优化
 * ==========================================================================
 * 原理:DF1 的输出量化误差 E 经 1/A(z) 到达输出 ⇒ 噪声增益 = Σ|h_{1/A}|²,
 * 在低频高 Q 处可达 91 dB。把 C(z)=A(z) 的误差反馈加回累加器 ⇒ 噪声传函 C/A ≡ 1。
 * 实测:8 个算例,有 EF 一律 −173.3x dBFS,与 NG(40–91 dB)无关 [L2/宿主定点仿真]。
 * 代价:2 乘 + 2 移位 + 2 状态字 / 节 / 样本。
 */
typedef struct {
    chdsp_acc_raw_t r1, r2;   /**< 前两次舍入残差(累加器单位) */
} chdsp_ef_t;

static inline void chdsp_ef_clear(chdsp_ef_t *ef) { ef->r1 = 0; ef->r2 = 0; }

/** 把 EF 修正项加进累加器。须在 chdsp_acc_to_smp_r() 之前调用。 */
static inline void chdsp_ef_inject(chdsp_acc_t *a, const chdsp_ef_t *ef,
                                   chdsp_coef_q4_27_t a1, chdsp_coef_q4_27_t a2)
{
#if CHDSP_BROKEN_NOEF
    (void)a; (void)ef; (void)a1; (void)a2;            /* ⛔ 坏版本:不做 EF */
#else
    CHDSP_RAW(*a) -= ((chdsp_acc_raw_t)CHDSP_RAW(a1) * ef->r1) >> CHDSP_COEF_FRACBITS;
    CHDSP_RAW(*a) -= ((chdsp_acc_raw_t)CHDSP_RAW(a2) * ef->r2) >> CHDSP_COEF_FRACBITS;
#endif
}

static inline void chdsp_ef_push(chdsp_ef_t *ef, chdsp_acc_raw_t r)
{ ef->r2 = ef->r1; ef->r1 = r; }

/* ==========================================================================
 * 9. 规范 biquad(DF1 + EF)—— 本约定的**数值参照实现**
 * ==========================================================================
 * ⚠ 为什么把它放在约定文件里:本文件报的噪声底只在**这个结构**下成立
 *   (D6:数必须带工作点向量)。换结构 ⇒ 噪声结论作废,须重测。
 * 系数约定:y = b0·x + b1·x1 + b2·x2 − a1·y1 − a2·y2   (a0 已归一化为 1)
 */
typedef struct {
    chdsp_coef_q4_27_t b0, b1, b2, a1, a2;
} chdsp_biquad_coef_t;

typedef struct {
    chdsp_smp_q4_27_t x1, x2, y1, y2;
    chdsp_ef_t        ef;
} chdsp_biquad_state_t;

static inline void chdsp_biquad_reset(chdsp_biquad_state_t *s)
{
    s->x1 = s->x2 = s->y1 = s->y2 = chdsp_smp_from_raw(0);
    chdsp_ef_clear(&s->ef);
}

static inline chdsp_smp_q4_27_t
chdsp_biquad_df1(const chdsp_biquad_coef_t *c, chdsp_biquad_state_t *s,
                 chdsp_smp_q4_27_t x, chdsp_sat_t *st)
{
    chdsp_acc_t     acc;
    chdsp_acc_raw_t r;
    chdsp_smp_q4_27_t y;

    chdsp_acc_clear(&acc);
    chdsp_acc_mac (&acc, x,     c->b0);
    chdsp_acc_mac (&acc, s->x1, c->b1);
    chdsp_acc_mac (&acc, s->x2, c->b2);
    chdsp_acc_msub(&acc, s->y1, c->a1);
    chdsp_acc_msub(&acc, s->y2, c->a2);
    chdsp_ef_inject(&acc, &s->ef, c->a1, c->a2);

    y = chdsp_acc_to_smp_r(acc, st, &r);

    s->x2 = s->x1; s->x1 = x;
    s->y2 = s->y1; s->y1 = y;
    chdsp_ef_push(&s->ef, r);
    return y;
}

/* ==========================================================================
 * 10. 增益 —— 唯一的「样本 × 增益」通道
 * ========================================================================== */
static inline chdsp_smp_q4_27_t
chdsp_apply_gain(chdsp_smp_q4_27_t x, chdsp_gain_q4_27_t g, chdsp_sat_t *st)
{
    chdsp_acc_t acc;
    chdsp_acc_clear(&acc);
    CHDSP_RAW(acc) = (chdsp_acc_raw_t)CHDSP_RAW(x) * (chdsp_acc_raw_t)CHDSP_RAW(g);
    return chdsp_acc_to_smp(acc, st);
}

/* ==========================================================================
 * 11. dB ↔ 线性(实现见 chdsp_fixed.c)
 * ========================================================================== */

/**
 * dB → 线性增益。
 * · db 先钳到 [CHDSP_DB_MUTE_Q8, CHDSP_DB_MAX_Q8](**肯定式**:先钳后算,
 *   新增/异常输入自动落安全侧,团队纪律 D-2)。
 * · db ≤ CHDSP_DB_MUTE_Q8 ⇒ 精确返回 0(静音,不是「很小的数」)。
 * · 精度指标(实测,见 check_fixed.c CHK-7):见 D34 约定文档 §7。
 */
chdsp_gain_q4_27_t chdsp_db_to_gain(chdsp_db_q23_8_t db);

/**
 * 线性 → dB(仅供电平表/诊断显示,⛔ 不得用于音频路判据)。
 * 输入 0 或负 ⇒ 返回 CHDSP_DB_MUTE_Q8。
 */
chdsp_db_q23_8_t chdsp_gain_to_db(chdsp_gain_q4_27_t g);

/* ==========================================================================
 * 12. 设计期(非实时)辅助:double → 定点,带**硬失败**
 * ==========================================================================
 * ⚠ 这是 D-1 的执行点:系数超范围**不是警告,是失败**。
 *   系数上界 |c| < 16 的依据分两类,不可混:
 *     · a1, a2 ——【数学界】稳定三角:|a1| < 1+a2 < 2、|a2| < 1。构造上不可超越。
 *     · b0,b1,b2 ——【解析界】(约定文档 §3.2.0,权威表述):
 *
 *           max|b| ≤ 2 · 10^(G_max/20)        —— 只依赖 G_max
 *
 *       峰型 ≤ max(2,A²)、架式 ≤ 2A²、HPF/LPF ≤ 2(A = 10^(G/40))。
 *       ⭐ **该界与 Q、S、频率、fs 全部无关** —— 三者随便放宽都不会翻掉它。
 *
 *       ⇒ 因此**唯一会使本界失效的参数是增益**:
 *
 *           ⛔ 触发条件 = G_max ≥ 18.0618 dB   (= 20·log10(8),此时 max|b| 达 16)
 *
 *       ⇒ 守 G_max,⛔ 不要去守 S 或 Q —— 守错了等于没守(团队纪律 D6-r)。
 *       该硬包络属 D2 参数字典管辖(台账 C3),本函数是它的机械兜底。
 *
 *  【整改留痕 · 2026-08-04 · channel-dsp 实例 #2 · critic MAJOR-4】
 *    原文曾写:「b0,b1,b2 ——【经验扫描界】…最大 11.2148…参数范围一旦放宽
 *              (S>1 或 |G|>15 dB),该界立即失效」。
 *    ⇒ 撤回理由:约定文档 §3.2.2 已**实扫证伪 S 这一支**(S 1.0→2.0 只把 max|b|
 *       从 11.2148 推到 11.2292,+0.0144)⇒ S 根本不是驱动量;而 §3.2.0 的解析界
 *       与 S 在形式上就无关。旧写法会把读者引去守一个几乎不起作用的常数,
 *       同时**真正会翻掉 Q4.27 的增益包络无人守**。
 *    ⇒ 原经验值 11.2148 保留在约定文档 §3.2.1(历史扫描表)与 CHK-8 测试常量中,
 *       那两处是**事实记录**,不是界的依据。
 *
 * 返回 0 = 成功;非 0 = 超范围(调用方必须处理,不得忽略)。
 */
int chdsp_coef_from_f64(double x, chdsp_coef_q4_27_t *out);
int chdsp_gain_from_f64(double x, chdsp_gain_q4_27_t *out);

/**
 * ⭐ HPF / LPF 的**结构约束量化**——DC / Nyquist 零点由构造保证,而不是靠运气。
 *
 * 缘起(r2 CHK-5f 实测):对 b0,b1,b2 各自独立取整,**500 个 fc 里有 251 个**
 * 破坏了高通的 DC 零点,最坏单节 DC 增益 **−59.26 dB @ 20 Hz** —— 对超低音分频
 * 这是硬缺陷。r1 曾在 fc=80 Hz 恰好得到精确 0,**那是巧合,不是保证**。
 *
 * 修法:只量化 b0,令 b1 = ∓2·b0、b2 = b0(RBJ 双线性 HPF/LPF 的解析结构),
 * 则 b0+b1+b2(高通 @DC)与 b0−b1+b2(低通 @Nyquist)在**量化后仍精确为 0**。
 * 实测 500/500 点精确 0。
 * ⚠ 只适用于 b1 = ∓2b0 ∧ b2 = b0 的族(Butterworth/LR 的 HPF、LPF)。
 *   PEQ / shelf 不属于该族,不得套用。
 * @param hp 非 0 = 高通(b1 = −2b0);0 = 低通(b1 = +2b0)
 */
int chdsp_coef_hplp_from_f64(double b0, double a1, double a2, int hp,
                             chdsp_biquad_coef_t *out);

/** 定点 → double,仅供自验/离线分析。 */
double chdsp_smp_to_f64(chdsp_smp_q4_27_t x);
double chdsp_io_to_f64(chdsp_io_q0_31_t x);
double chdsp_coef_to_f64(chdsp_coef_q4_27_t x);
double chdsp_gain_to_f64(chdsp_gain_q4_27_t x);

/** 累加器越界自检(调试用)。返回 0 = 在 66-bit 安全域内。 */
int chdsp_acc_in_range(chdsp_acc_t a);

#ifdef __cplusplus
}
#endif
#endif /* CHDSP_FIXED_H */
