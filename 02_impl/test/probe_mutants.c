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
#include <stdio.h>
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static chdsp_coef_q4_27_t g_fir_h[CHDSP_OUT_FIR_TAPS];
static chdsp_smp_q4_27_t  g_fir_z[CHDSP_OUT_FIR_TAPS];
static chdsp_smp_q4_27_t  g_look[4096];

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

    return 0;
}
