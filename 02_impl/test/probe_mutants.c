/** @file probe_mutants.c
 *  ⭐⭐ 变异自证探针。⛔ 门禁状态:未过门。
 *
 *  ============================================================================
 *  这是什么 / 为什么必须有
 *  ----------------------------------------------------------------------------
 *  杀伤矩阵报「16/16 全杀」看起来完美无缺。但它只回答了一个问题:
 *      「打开这个宏之后,有检查变红了吗?」
 *  它**没有**回答另一个问题:
 *      「这个宏真的做了它名字声称的那件事吗?」
 *
 *  前任的实证(memory 任务三):`CHDSP_BROKEN_HPF_AFTER_DYN` 声称"把 HPF 挪到动态之后",
 *  实际挪到了 AEC 钩子之后 —— **仍在动态之前**。
 *  ⇒ 它当时"存活"了,反而逼人去看;**若它恰好被别的检查杀死,就会留下一条【假的杀伤记录】**。
 *  ⇒ **存活是可见的,假杀伤是隐形的。** 而一份 16/16 的报告看起来完美无缺。
 *
 *  ⇒ ∴ 每个变异进杀伤矩阵**之前**,必须先自证:
 *      **跑一条只测它声称改变的那件事的探针,断言探针读数确实变了。**
 *      探针没变 ⇒ 该变异无效 ⇒ ⛔ 不许进杀伤矩阵,不计入杀伤率。
 *
 *  ============================================================================
 *  本文件的角色
 *  ----------------------------------------------------------------------------
 *  编译一次得到一个二进制,打印**全部**探针读数,每行 `PROBE <TAG> <值>`。
 *  `check_mutants_valid.sh` 把它编译 N+1 次(好版本 + 每个变异一次),
 *  对变异 M **只比较 M 自己那一行**(其余行变不变都不关心)。
 *
 *  ⚠ 本文件**不做断言、不判 PASS/FAIL** —— 它只是把"声称被改变的那个量"读出来。
 *    判定在脚本里。这样探针与判据分离,探针本身不会因变异而换题目。
 *
 *  ⚠ 链序类变异(CHAIN_ORDER / XO_POLARITY / HPF_AFTER_DYN)**不在这里**:
 *    它们声称的是**结构**(某模块在某模块之前/之后),行为探针证不了"位置"。
 *    ⇒ 由 check_mutants_valid.sh 的 Phase A 用 `gcc -E` 读预处理后的真实调用顺序来证。
 *      那才是能抓住"挪了,但没挪到声称的地方"的那一种。
 */
#include "chdsp_config.h"
#include "chdsp_biquad.h"
#include "chdsp_detector.h"
#include "chdsp_dynamics.h"
#include "chdsp_fir.h"
#include "chdsp_delay.h"
#include "chdsp_notch.h"
#include "chdsp_chain.h"
#include <stdio.h>
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static chdsp_coef_q4_27_t g_fir_h[CHDSP_OUT_FIR_TAPS];
static chdsp_smp_q4_27_t  g_fir_z[CHDSP_OUT_FIR_TAPS];
static chdsp_smp_q4_27_t  g_look[4096];
static chdsp_smp_q4_27_t  g_dly2[CHDSP_IN_DELAY_MAX_SAMPLES + CHDSP_FRAME_SAMPLES];
static chdsp_smp_q4_27_t  g_look2[CHDSP_FRAME_SAMPLES * 4];

static chdsp_smp_q4_27_t smp_f(double v)
{
    double s = v * (double)(1 << CHDSP_SMP_FRACBITS);
    if (s >  2147483647.0) { s =  2147483647.0; }
    if (s < -2147483648.0) { s = -2147483648.0; }
    return chdsp_smp_from_raw((int32_t)s);
}

static uint32_t g_rng = 123456789u;
static uint32_t rnd32(void)
{ g_rng ^= g_rng << 13; g_rng ^= g_rng >> 17; g_rng ^= g_rng << 5; return g_rng; }

int main(void)
{
    /* ---- P_WRAP:窄化溢出时是【饱和】还是【回绕】 -------------------------
     * 声称改变的行为:溢出处理。读数 = 一个必然溢出的值经 smp→io 后的 raw。 */
    {
        chdsp_sat_t st; chdsp_smp_q4_27_t x;
        chdsp_sat_reset(&st);
        x = smp_f(4.0);                       /* Q0.31 装不下 ⇒ 必然溢出 */
        printf("PROBE P_WRAP %ld\n", (long)chdsp_io_raw(chdsp_smp_to_io(x, &st)));
    }

    /* ---- P_TRUNC:窄化时是【就近舍入】还是【截断】 ------------------------
     * 声称改变的行为:舍入。构造一个恰好 .5 的中间结果:
     *   raw(x)=3, g=0.5 ⇒ 3·2^26 = 1.5·2^27 ⇒ >>27 得 1.5 ⇒ 舍入=2,截断=1。 */
    {
        chdsp_sat_t st; chdsp_smp_q4_27_t x; chdsp_gain_q4_27_t g;
        chdsp_sat_reset(&st);
        x = chdsp_smp_from_raw(3);
        g = chdsp_gain_from_raw(1 << (CHDSP_GAIN_FRACBITS - 1));   /* = 0.5 */
        printf("PROBE P_TRUNC %ld\n", (long)chdsp_smp_raw(chdsp_apply_gain(x, g, &st)));
    }

    /* ---- P_NOEF:误差反馈开/关 -------------------------------------------
     * 声称改变的行为:量化噪声底(EF 把噪声传函压成 ≡1)。
     * 读数 = 定点 biquad 相对 double 参照的误差功率 dBFS(整数化到 0.01 dB)。
     * ⛔ 不读 ef.r1/r2:`chdsp_ef_push` 是无条件的,只有 inject 被关 ⇒ 状态照样非零。 */
    {
        chdsp_biquad_coef_t c; chdsp_biquad_state_t s; chdsp_sat_t st;
        double y1 = 0.0, y2 = 0.0, x1 = 0.0, x2 = 0.0, e2 = 0.0;
        double b0, b1, b2, a1, a2;
        int i, N = 60000, SKIP = 4000;
        chdsp_sat_reset(&st); chdsp_biquad_reset(&s);
        (void)chdsp_bq_design(CHDSP_FT_PEAKING, 20.0, 20.0, 15.0, &c);
        b0 = chdsp_coef_to_f64(c.b0); b1 = chdsp_coef_to_f64(c.b1);
        b2 = chdsp_coef_to_f64(c.b2); a1 = chdsp_coef_to_f64(c.a1);
        a2 = chdsp_coef_to_f64(c.a2);
        g_rng = 987654321u;
        for (i = 0; i < N; i++) {
            double xv = ((double)(int32_t)(rnd32() >> 8) / 8388608.0 - 1.0) * 0.03;
            double yr = b0*xv + b1*x1 + b2*x2 - a1*y1 - a2*y2;
            double yf = chdsp_smp_to_f64(chdsp_biquad_df1(&c, &s, smp_f(xv), &st));
            x2 = x1; x1 = xv; y2 = y1; y1 = yr;
            if (i >= SKIP) { double d = yf - yr; e2 += d * d; }
        }
        e2 /= (double)(N - SKIP);
        printf("PROBE P_NOEF %ld\n", (long)(10.0 * log10(e2 + 1e-300) * 100.0));
    }

    /* ---- P_BQ_NORAMP:系数斜坡 vs 直接跳变 --------------------------------
     * 声称改变的行为:系数是否逐样本插值。读数 = 斜坡前 8 样本内 a1 的不同取值数。 */
    {
        chdsp_bq_t b; chdsp_biquad_coef_t c0, c1; chdsp_sat_t sat;
        int i, nseen = 0; int32_t seen[8];
        chdsp_bq_init(&b); chdsp_sat_reset(&sat);
        (void)chdsp_bq_design(CHDSP_FT_PEAKING, 100.0, 8.0, +12.0, &c0);
        (void)chdsp_bq_design(CHDSP_FT_PEAKING, 4000.0, 0.7, -10.0, &c1);
        chdsp_bq_set_coef_now(&b, &c0); b.bypass = 0u;
        chdsp_bq_set_coef_ramp(&b, &c1, 480u);
        for (i = 0; i < 8; i++) {
            int k, found = 0; int32_t v;
            (void)chdsp_bq_process1(&b, smp_f(0.01), &sat);
            v = chdsp_coef_raw(b.cur.a1);
            for (k = 0; k < nseen; k++) { if (seen[k] == v) { found = 1; } }
            if (!found && nseen < 8) { seen[nseen++] = v; }
        }
        printf("PROBE P_BQ_NORAMP %d\n", nseen);
    }

    /* ---- P_BQ_TIE_FREE:HPF/LPF 结构约束量化 vs 自由量化 -------------------
     * 声称改变的行为:DC 零点是否由构造保证。读数 = 400 个 fc 中 b0+b1+b2 ≠ 0 的个数。 */
    {
        int i, nz = 0, N = 400;
        for (i = 0; i < N; i++) {
            double fc = 20.0 * pow(1000.0, (double)i / (double)(N - 1));
            chdsp_biquad_coef_t h;
            if (chdsp_bq_design(CHDSP_FT_HPF, fc, 0.7071, 0.0, &h) == 0) {
                double sum = chdsp_coef_to_f64(h.b0) + chdsp_coef_to_f64(h.b1)
                           + chdsp_coef_to_f64(h.b2);
                if (sum != 0.0) { nz++; }
            }
        }
        printf("PROBE P_BQ_TIE_FREE %d\n", nz);
    }

    /* ---- P_POW_NARROW:功率状态位宽 Q8.54 vs 截回 Q4.27 --------------------
     * 声称改变的行为:极低电平下 x² 是否下溢到 0。读数 = −120 dBFS 处功率状态 raw。 */
    {
        chdsp_det_t d; int i; chdsp_pow_q8_54_t p = chdsp_pow_from_raw(0);
        double amp = pow(10.0, -120.0 / 20.0) * 1.41421356;
        chdsp_det_init(&d, CHDSP_DET_RMS, 50.0, 50.0);
        for (i = 0; i < CHDSP_FS_HZ; i++) {
            p = chdsp_det_process1(&d, smp_f(amp * sin(2.0 * M_PI * 500.0 * i / CHDSP_FS_HZ)));
        }
        printf("PROBE P_POW_NARROW %lld\n", (long long)chdsp_pow_raw(p));
    }

    /* ---- P_DET_ONEDIR:attack/release 是否分方向 ---------------------------
     * 声称改变的行为:非对称时读数应介于均值与峰值之间;不分方向会贴到峰值。
     * 读数 = 非对称检测器读数(1/256 dB)。 */
    {
        chdsp_det_t d; int i; chdsp_pow_q8_54_t p = chdsp_pow_from_raw(0);
        double amp = pow(10.0, -20.0 / 20.0);
        chdsp_det_init(&d, CHDSP_DET_RMS, 10.0, 100.0);
        for (i = 0; i < CHDSP_FS_HZ * 3; i++) {
            p = chdsp_det_process1(&d, smp_f(amp * sin(2.0 * M_PI * 1000.0 * i / CHDSP_FS_HZ)));
        }
        printf("PROBE P_DET_ONEDIR %ld\n", (long)chdsp_db_raw(chdsp_pow_to_db(p)));
    }

    /* ---- P_GATE_NEGATIVE:门是肯定式还是否定式豁免 -------------------------
     * 声称改变的行为:迟滞带内从 CLOSED 出发是否开门。读数 = 终态 state。 */
    {
        chdsp_gate_t g; int i;
        double amp = pow(10.0, -46.5 / 20.0) * 1.41421356;   /* 落在 (−48,−45) 带内 */
        chdsp_gate_init(&g, -45.0, 20.0, 3.0, 60.0, 50.0, 0.0, 50.0);
        g.enabled = 1u;
        for (i = 0; i < CHDSP_FS_HZ; i++) {
            (void)chdsp_gate_gain1(&g, smp_f(amp * sin(2.0 * M_PI * 500.0 * i / CHDSP_FS_HZ)), 0);
        }
        printf("PROBE P_GATE_NEGATIVE %d\n", (int)g.state);
    }

    /* ---- P_NO_HYST:迟滞是否存在 ------------------------------------------
     * 声称改变的行为:先开门(thr+0.5),再降到 thr−1.5(仍在带内)是否保持 OPEN。
     * 读数 = 降下来之后的 state。 */
    {
        chdsp_gate_t g; int i;
        double a_up = pow(10.0, (-45.0 + 0.5) / 20.0) * 1.41421356;
        double a_dn = pow(10.0, (-45.0 - 1.5) / 20.0) * 1.41421356;
        chdsp_gate_init(&g, -45.0, 20.0, 3.0, 60.0, 20.0, 0.0, 20.0);
        g.enabled = 1u;
        for (i = 0; i < CHDSP_FS_HZ / 2; i++) {
            (void)chdsp_gate_gain1(&g, smp_f(a_up * sin(2.0 * M_PI * 500.0 * i / CHDSP_FS_HZ)), 0);
        }
        for (i = 0; i < CHDSP_FS_HZ / 2; i++) {
            (void)chdsp_gate_gain1(&g, smp_f(a_dn * sin(2.0 * M_PI * 500.0 * i / CHDSP_FS_HZ)), 0);
        }
        printf("PROBE P_NO_HYST %d\n", (int)g.state);
    }

    /* ---- P_LIM_NOLOOK:限幅器前视 ------------------------------------------
     * 声称改变的行为:阶跃过冲。读数 = 阶跃后输出峰值(×1e6 取整)。 */
    {
        chdsp_limiter_t l; int i; double peak = 0.0;
        (void)chdsp_limiter_init(&l, g_look, sizeof(g_look)/sizeof(g_look[0]), -6.0, 1.0, 50.0);
        l.enabled = 1u;
        for (i = 0; i < CHDSP_FS_HZ / 10; i++) {
            double v = (i < 2000) ? 0.0 : 0.9;
            double y = chdsp_smp_to_f64(chdsp_limiter_process1(&l, smp_f(v), 0, 0));
            if (i > 2000 && fabs(y) > peak) { peak = fabs(y); }
        }
        printf("PROBE P_LIM_NOLOOK %ld\n", (long)(peak * 1e6));
    }

    /* ---- P_COMP_HARDKNEE:软拐点 vs 硬拐点 ---------------------------------
     * 声称改变的行为:拐点中心处的增益(软拐点 = −slope·W/8,硬拐点 = 0)。
     * 读数 = L = thr 处的增益(1/256 dB)。 */
    {
        chdsp_comp_t c; chdsp_db_q23_8_t gd = chdsp_db_from_raw(0); int k;
        double amp = pow(10.0, -20.0 / 20.0) * 1.41421356;
        chdsp_comp_init(&c, -20.0, 4.0, 12.0, 1.0, 1.0, 0.0, CHDSP_DET_RMS);
        c.enabled = 1u;
        for (k = 0; k < CHDSP_FS_HZ / 2; k++) {
            (void)chdsp_comp_gain1(&c, smp_f(amp * sin(2.0 * M_PI * 500.0 * k / CHDSP_FS_HZ)), &gd);
        }
        printf("PROBE P_COMP_HARDKNEE %ld\n", (long)chdsp_db_raw(gd));
    }

    /* ---- P_FIR_ASYM:抽头对称性 --------------------------------------------
     * 声称改变的行为:线性相位所依赖的抽头对称。读数 = 非对称抽头对数。 */
    {
        int i, asym = 0; uint16_t N = CHDSP_OUT_FIR_TAPS;
        (void)chdsp_fir_design_lowpass(8000.0, 5.65, g_fir_h, N);
        for (i = 0; i < N / 2; i++) {
            if (chdsp_coef_raw(g_fir_h[i]) != chdsp_coef_raw(g_fir_h[N - 1 - i])) { asym++; }
        }
        printf("PROBE P_FIR_ASYM %d\n", asym);
    }

    /* ---- P_FIR_NOBYPASS:关闭时是否逐位透传 --------------------------------
     * 声称改变的行为:disabled 状态下是否改动样本。读数 = 5000 样本中不等的个数。 */
    {
        chdsp_fir_t f; int i, bad = 0;
        (void)chdsp_fir_init(&f, g_fir_h, g_fir_z, CHDSP_OUT_FIR_TAPS);
        f.enabled = 0u;
        g_rng = 24680u;
        for (i = 0; i < 5000; i++) {
            chdsp_smp_q4_27_t x = chdsp_smp_from_raw((int32_t)(rnd32() >> 5) - (1 << 26));
            if (chdsp_smp_raw(chdsp_fir_process1(&f, x, 0)) != chdsp_smp_raw(x)) { bad++; }
        }
        printf("PROBE P_FIR_NOBYPASS %d\n", bad);
    }

    /* ---- P_BUTTER_COS:butter_q 的 sin/cos 之别 ------------------------------
     * 声称改变的行为:**奇数阶** Butterworth 的 Q(n=3:sin 式 1.0 vs cos 式 0.5774)。
     * 读数 = BW3 低通第 2 节(那个双二阶节)的 a1 raw。 */
    {
        chdsp_biquad_coef_t sec[CHDSP_OUT_XO_SECTIONS]; uint16_t n = 0u;
        int e = chdsp_bq_design_xover2(CHDSP_XO_BUTTERWORTH, 3, 0, 1000.0, sec, &n);
        printf("PROBE P_BUTTER_COS %ld\n",
               (e == CHDSP_BQ_OK && n >= 2u) ? (long)chdsp_coef_raw(sec[1].a1) : -999999L);
    }

    /* ---- P_BESSEL_RBJ:Bessel 的设计路径 -------------------------------------
     * 声称改变的行为:Bessel 改走逐节 RBJ ⇒ 系数不同(高阶高通差最大)。
     * 读数 = Bessel8 高通全部节的 a1 raw 之和。 */
    {
        chdsp_biquad_coef_t sec[CHDSP_OUT_XO_SECTIONS]; uint16_t n = 0u;
        int e = chdsp_bq_design_xover2(CHDSP_XO_BESSEL, 8, 1, 1000.0, sec, &n);
        long acc = 0; uint16_t i;
        if (e == CHDSP_BQ_OK) { for (i = 0u; i < n; i++) { acc += (long)chdsp_coef_raw(sec[i].a1); } }
        else { acc = -999999L; }
        printf("PROBE P_BESSEL_RBJ %ld\n", acc);
    }

    /* ---- P_XO_UNIT:极性规则算在【阶数 n】还是【dB/oct】上 --------------------
     * 声称改变的行为:四个 LR 档位的极性判定。读数 = 四个 flip 值打包成一个整数。 */
    {
        long v = 0; int i; static const int32_t NS[4] = { 2, 4, 6, 8 };
        for (i = 0; i < 4; i++) {
            v = v * 10 + (chdsp_xover_needs_polarity_flip(1, chdsp_xo_order(NS[i])) + 2);
        }
        printf("PROBE P_XO_UNIT %ld\n", v);
    }

    /* ---- P_NOTCH_EVICT:回收时是否会动【固定槽】-----------------------------
     * 声称改变的行为:HYBRID 下持续回收压力后,固定槽是否还完好。
     * 读数 = 固定槽 0 的 f_hz(好版本恒为装机值 100;坏版本会被 AFC 频率覆盖)。 */
    {
        chdsp_notch_bank_t b; chdsp_bq_t sec[CHDSP_NOTCH_COUNT]; chdsp_bq_chain_t ch;
        const uint16_t NF = (uint16_t)(CHDSP_NOTCH_COUNT / 2);
        int i;
        chdsp_bq_chain_init(&ch, sec, CHDSP_NOTCH_COUNT);
        chdsp_notch_bank_init(&b, CHDSP_NOTCH_MODE_HYBRID, NF);
        for (i = 0; i < (int)NF; i++) {
            (void)chdsp_notch_bank_set_fixed(&b, &ch, (uint16_t)i, 100.0 + i, 8.0, -6.0);
        }
        for (i = 0; i < CHDSP_NOTCH_COUNT * 5; i++) {
            (void)chdsp_notch_bank_request(&b, &ch, 1000.0 + 10.0 * i, 8.0, -6.0, 0);
        }
        printf("PROBE P_NOTCH_EVICT %ld\n", (long)b.slot[0].f_hz);
    }

    /* ---- P_NOTCH_RESET:复位动态槽时固定槽是否留下 --------------------------
     * 声称改变的行为:「重启后仍在」。读数 = 复位后仍占用的槽数。 */
    {
        chdsp_notch_bank_t b; chdsp_bq_t sec[CHDSP_NOTCH_COUNT]; chdsp_bq_chain_t ch;
        const uint16_t NF = (uint16_t)(CHDSP_NOTCH_COUNT / 2);
        int i;
        chdsp_bq_chain_init(&ch, sec, CHDSP_NOTCH_COUNT);
        chdsp_notch_bank_init(&b, CHDSP_NOTCH_MODE_HYBRID, NF);
        for (i = 0; i < (int)NF; i++) {
            (void)chdsp_notch_bank_set_fixed(&b, &ch, (uint16_t)i, 100.0 + i, 8.0, -6.0);
        }
        for (i = 0; i < CHDSP_NOTCH_COUNT; i++) {
            (void)chdsp_notch_bank_request(&b, &ch, 2000.0 + 10.0 * i, 8.0, -6.0, 0);
        }
        chdsp_notch_bank_reset_dynamic(&b, &ch);
        printf("PROBE P_NOTCH_RESET %u\n", (unsigned)chdsp_notch_bank_used(&b));
    }

    /* ---- P_GUARD_BY_S:包络守卫守的是【增益】还是【S】-----------------------
     * 声称改变的行为:CHK-B1b 的四个工作点的返回码。
     * 读数 = 四个返回码打包(好版本 = OK/OK/ERR_GAIN_ENV/OK)。 */
    {
        chdsp_biquad_coef_t c; long v = 0;
        int r[4]; int i;
        r[0] = chdsp_bq_design(CHDSP_FT_HIGHSHELF, 20.0, 2.0, 15.0, &c);  /* S=2 @+15dB */
        r[1] = chdsp_bq_design(CHDSP_FT_HIGHSHELF, 20.0, 1.0, 15.0, &c);
        r[2] = chdsp_bq_design(CHDSP_FT_HIGHSHELF, 20.0, 1.0, 18.1, &c);  /* 超包络 */
        r[3] = chdsp_bq_design(CHDSP_FT_HIGHSHELF, 20.0, 1.0, 17.9, &c);
        for (i = 0; i < 4; i++) { v = v * 10 + (long)(-r[i]); }
        printf("PROBE P_GUARD_BY_S %ld\n", v);
    }

    /* ══ r12:为 MAJOR-5 的 14 条欠账补的探针 ══ */
    {   /* P_NOTCH_MRU:槽满时回收【最早】还是【最新】。读数 = 被复用的槽号 */
        chdsp_notch_bank_t b; chdsp_bq_t sec[CHDSP_NOTCH_COUNT]; chdsp_bq_chain_t ch;
        int i; uint16_t k = 0xFFFFu;
        chdsp_bq_chain_init(&ch, sec, CHDSP_NOTCH_COUNT);
        chdsp_notch_bank_init(&b, CHDSP_NOTCH_MODE_DYNAMIC, 0u);
        for (i = 0; i < CHDSP_NOTCH_COUNT; i++)
            (void)chdsp_notch_bank_request(&b, &ch, 200.0 + i, 8.0, -6.0, 0);
        (void)chdsp_notch_bank_request(&b, &ch, 9000.0, 8.0, -6.0, &k);
        printf("PROBE P_NOTCH_MRU %u\n", (unsigned)k);
    }
    {   /* P_NOTCH_NOWRITE:request 有没有真的写系数。读数 = 该节 bypass 标志 */
        chdsp_notch_bank_t b; chdsp_bq_t sec[CHDSP_NOTCH_COUNT]; chdsp_bq_chain_t ch;
        uint16_t k = 0u;
        chdsp_bq_chain_init(&ch, sec, CHDSP_NOTCH_COUNT);
        chdsp_notch_bank_init(&b, CHDSP_NOTCH_MODE_DYNAMIC, 0u);
        (void)chdsp_notch_bank_request(&b, &ch, 1000.0, 8.0, -18.0, &k);
        printf("PROBE P_NOTCH_NOWRITE %d\n", (int)ch.sec[k].bypass + 10 * (int)ch.n);
    }
    {   /* P_HOOK_SKIP:AGC 插入点是否真被调用。读数 = call_count */
        chdsp_in_ch_t ich; chdsp_io_q0_31_t in[CHDSP_FRAME_SAMPLES];
        chdsp_smp_q4_27_t out[CHDSP_FRAME_SAMPLES]; int i;
        (void)chdsp_in_ch_init(&ich, g_dly2, (uint32_t)(sizeof(g_dly2)/sizeof(g_dly2[0])),
                               g_look2, (uint32_t)(sizeof(g_look2)/sizeof(g_look2[0])));
        for (i = 0; i < CHDSP_FRAME_SAMPLES; i++) in[i] = chdsp_io_from_raw(1 << 20);
        chdsp_in_ch_process(&ich, in, out, CHDSP_FRAME_SAMPLES);
        printf("PROBE P_HOOK_SKIP %u\n", (unsigned)ich.hook_agc.call_count);
    }
    {   /* P_NO_SATTEL:链内饱和是否被计数。读数 = internal_sat_frames */
        chdsp_in_ch_t ich; chdsp_biquad_coef_t pc;
        chdsp_io_q0_31_t in[CHDSP_FRAME_SAMPLES]; chdsp_smp_q4_27_t out[CHDSP_FRAME_SAMPLES];
        int i;
        (void)chdsp_in_ch_init(&ich, g_dly2, (uint32_t)(sizeof(g_dly2)/sizeof(g_dly2[0])),
                               g_look2, (uint32_t)(sizeof(g_look2)/sizeof(g_look2[0])));
        ich.trim = chdsp_db_to_gain(chdsp_db(24));
        (void)chdsp_bq_design(CHDSP_FT_PEAKING, 1000.0, 1.0, 15.0, &pc);
        ich.peq.n = 1u; chdsp_bq_set_coef_now(&ich.peq_sec[0], &pc); ich.peq_sec[0].bypass = 0u;
        for (i = 0; i < CHDSP_FRAME_SAMPLES; i++)
            in[i] = chdsp_io_from_raw((int32_t)(2147483647.0 * sin(2.0*M_PI*1000.0*i/CHDSP_FS_HZ)));
        chdsp_in_ch_process(&ich, in, out, CHDSP_FRAME_SAMPLES);
        printf("PROBE P_NO_SATTEL %u\n", (unsigned)chdsp_in_ch_internal_sat_frames(&ich));
    }
    {   /* P_SLOPE_CONV:dB/oct → 阶数 的换算因子 */
        printf("PROBE P_SLOPE_CONV %ld\n",
               (long)chdsp_xo_order_n(chdsp_xo_order_from_slope(chdsp_xo_slope(12))));
    }
    {   /* P_XO_NORANGE:误喂 dB/oct 时的量程守卫 */
        printf("PROBE P_XO_NORANGE %d\n",
               chdsp_xover_needs_polarity_flip(1, chdsp_xo_order(24)));
    }
    {   /* P_BUTTER_KOFF:BW4 第 2 节的 a1(butter_q 的 k 取值直接决定它) */
        chdsp_biquad_coef_t sec[CHDSP_OUT_XO_SECTIONS]; uint16_t n = 0u;
        int e = chdsp_bq_design_xover2(CHDSP_XO_BUTTERWORTH, 4, 0, 1000.0, sec, &n);
        /* ⚠ 必须取 sec[0]:KOFF 下 BW4 的 Q 集合从 {1.3066, 0.5412} 退化成 {0.5412, 0.5412}
         *   ⇒ **sec[1] 恰好不变**,取它就没有分辨力(首版就是这样,被断言① 当场抓出)。 */
        printf("PROBE P_BUTTER_KOFF %ld\n",
               (e == CHDSP_BQ_OK && n >= 2u) ? (long)chdsp_coef_raw(sec[0].a1) : -999999L);
    }
    {   /* P_BESSEL_SCALE:Bessel4 的 max|b| raw(归一化写错会放大它) */
        chdsp_biquad_coef_t sec[CHDSP_OUT_XO_SECTIONS]; uint16_t n = 0u; long w = 0;
        if (chdsp_bq_design_xover2(CHDSP_XO_BESSEL, 4, 0, 1000.0, sec, &n) == CHDSP_BQ_OK) {
            uint16_t i; for (i = 0u; i < n; i++) {
                long r[3]; int j; r[0]=(long)chdsp_coef_raw(sec[i].b0);
                r[1]=(long)chdsp_coef_raw(sec[i].b1); r[2]=(long)chdsp_coef_raw(sec[i].b2);
                for (j=0;j<3;j++){ long v = r[j]<0?-r[j]:r[j]; if (v>w) w=v; } }
        } else { w = -1; }
        printf("PROBE P_BESSEL_SCALE %ld\n", w);
    }
    {   /* P_LR_ODD_OK:LR 奇数阶是否被拒 */
        chdsp_biquad_coef_t sec[CHDSP_OUT_XO_SECTIONS]; uint16_t n = 0u;
        printf("PROBE P_LR_ODD_OK %d\n",
               chdsp_bq_design_xover2(CHDSP_XO_LINKWITZ_RILEY, 3, 0, 1000.0, sec, &n));
    }
    {   /* P_FIRSTORDER:一阶节的 max|b| raw */
        chdsp_biquad_coef_t c; long w = 0; int i;
        for (i = 0; i < 60; i++) {
            double fc = 20.0 * pow(1000.0, (double)i / 59.0);
            if (chdsp_bq_design_first_order(0, fc, &c) == CHDSP_BQ_OK) {
                long r[2]; int j; r[0]=(long)chdsp_coef_raw(c.b0); r[1]=(long)chdsp_coef_raw(c.b1);
                for (j=0;j<2;j++){ long v=r[j]<0?-r[j]:r[j]; if (v>w) w=v; } }
        }
        printf("PROBE P_FIRSTORDER %ld\n", w);
    }
    {   /* P_SMOOTH_FIXED:平滑系数是否随 tau 变 */
        printf("PROBE P_SMOOTH_FIXED %ld\n",
               (long)chdsp_smooth_raw(chdsp_smooth_from_ms(3000.0)));
    }
    {   /* P_GATE_ENUM:安全状态是不是 0(⇒ 全 0 初始化落安全侧) */
        printf("PROBE P_GATE_ENUM %d\n", (int)CHDSP_GATE_CLOSED);
    }
    {   /* P_COEF_NOCONST:系数界是否由具名常数显式守 */
        chdsp_coef_q4_27_t c;
        /* ⚠ 两道守卫只在【负边界 −16.0】处不等价:int32 判据是 `scaled < −2^31` (严格小于),
         *   而 −16.0 恰好 = −2^31 ⇒ 它**通过** int32 判据;只有具名常数判据 (|x| < 16) 拦得住。
         *   ⇒ 探针必须取这个点,否则两版读数相同(首版取 15.99999995/16.0 就是这样,无分辨力)。 */
        printf("PROBE P_COEF_NOCONST %d\n",
               chdsp_coef_from_f64(-16.0, &c) * 10 + chdsp_coef_from_f64(16.0, &c));
    }

    /* ---- P_BESSEL_FREEQ:Bessel 走结构约束量化还是自由量化 ---------------------
     * 声称改变的行为:量化后零点是否仍精确。读数 = 零点非 0 的节数。 */
    {
        chdsp_biquad_coef_t sec[CHDSP_OUT_XO_SECTIONS]; uint16_t n; int order, hp, i, k, bad = 0;
        for (order = 1; order <= 8; order++) for (hp = 0; hp < 2; hp++) for (k = 0; k < 25; k++) {
            double fc = 20.0 * pow(1000.0, (double)k / 24.0);
            if (chdsp_bq_design_xover2(CHDSP_XO_BESSEL, order, hp, fc, sec, &n) != CHDSP_BQ_OK)
                { continue; }
            for (i = 0; i < (int)n; i++) {
                double b0 = chdsp_coef_to_f64(sec[i].b0), b1 = chdsp_coef_to_f64(sec[i].b1),
                       b2 = chdsp_coef_to_f64(sec[i].b2);
                if ((hp ? (b0 + b1 + b2) : (b0 - b1 + b2)) != 0.0) { bad++; }
            }
        }
        printf("PROBE P_BESSEL_FREEQ %d\n", bad);
    }

    return 0;
}
