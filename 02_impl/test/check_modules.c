/**
 * @file    check_modules.c
 * @brief   D3/D4 各模块的自验 —— **全部是硬闸门**
 *
 * ⛔ 门禁状态:未过门(2026-08-04)。作者:channel-dsp(第 1 实例)
 *
 * ============================================================================
 * ⭐⭐ 本文件的每一条检查失败时,**进程以非 0 退出**。
 *     自查一句(lead 指示):「这个检查失败时,会阻止什么?」
 *     答:**阻止构建流水线继续 / 阻止杀伤矩阵判定通过**。
 *     ⛔ 若某条只打印不影响退出码,它就是【输出行】不是【检查】,必须改。
 *     机械保证:`FAILED()` 递增 g_fail;`main()` 末尾 `return g_fail ? 1 : 0`;
 *     且 `run_all.sh` 对退出码断言(见该脚本)。
 * ============================================================================
 *
 * ⚠ 自验纪律:本文件 **#include 并调用被测模块的函数**,⛔ 禁止转写其公式。
 *   第二轨(Python 独立重写)在 `ref/ref_modules.py`,不共用任何代码。
 */

#include "chdsp_chain.h"
#include "chdsp_biquad.h"
#include "chdsp_detector.h"
#include "chdsp_dynamics.h"
#include "chdsp_fir.h"
#include <stdio.h>
#include <math.h>
#include <string.h>
#include <stdlib.h>

static int g_fail = 0, g_pass = 0;
static void OKC(const char *tag, int cond, const char *msg)
{
    if (cond) { g_pass++; } else { g_fail++; }
    printf("  [%s] %-9s %s\n", cond ? "PASS" : "FAIL", tag, msg);
}

/* 确定性 PRNG */
static uint32_t g_rng = 0x2468ACE1u;
static uint32_t rnd32(void)
{ g_rng ^= g_rng << 13; g_rng ^= g_rng >> 17; g_rng ^= g_rng << 5; return g_rng; }
static double rndn(void)
{ double s = 0.0; int i; for (i = 0; i < 12; i++) { s += (double)rnd32() / 4294967296.0; } return s - 6.0; }

static chdsp_smp_q4_27_t smp_f(double v)
{ return chdsp_smp_from_raw((int32_t)floor(v * ldexp(1.0, CHDSP_SMP_FRACBITS) + 0.5)); }

/* 静态缓冲(⛔ 尺寸全部走 config 常量,不写字面量) */
static chdsp_smp_q4_27_t g_dly_in[CHDSP_IN_DELAY_MAX_SAMPLES + CHDSP_FRAME_SAMPLES];
static chdsp_smp_q4_27_t g_look_in[CHDSP_FRAME_SAMPLES * 4];
static chdsp_smp_q4_27_t g_dly_out[CHDSP_OUT_DELAY_MAX_SAMPLES + CHDSP_FRAME_SAMPLES];
static chdsp_smp_q4_27_t g_look_out[CHDSP_FRAME_SAMPLES * 4];
static chdsp_smp_q4_27_t g_spk_r[CHDSP_FRAME_SAMPLES * 4];
static chdsp_smp_q4_27_t g_spk_p[CHDSP_FRAME_SAMPLES * 4];
static chdsp_coef_q4_27_t g_fir_h[(CHDSP_OUT_FIR_TAPS > 0) ? CHDSP_OUT_FIR_TAPS : 1];
static chdsp_smp_q4_27_t  g_fir_z[(CHDSP_OUT_FIR_TAPS > 0) ? CHDSP_OUT_FIR_TAPS : 1];

int main(void)
{
    printf("================================================================\n");
    printf("check_modules  —  D3/D4 各模块自验(**全部硬闸门**)\n");
    printf("  config: fs=%d L=%d IN_PEQ=%d OUT_PEQ=%d NOTCH=%d FIR=%d XO_SEC=%d\n",
           CHDSP_FS_HZ, CHDSP_FRAME_SAMPLES, CHDSP_IN_PEQ_BANDS, CHDSP_OUT_PEQ_BANDS,
           CHDSP_NOTCH_COUNT, CHDSP_OUT_FIR_TAPS, CHDSP_OUT_XO_SECTIONS);
    printf("================================================================\n\n");

    /* ================= biquad ================= */
    printf("biquad\n");
    {   /* CHK-B1 ⭐ 断言【具体那条错误码】,⛔ 不是"非 0"
         * 缘起:critic 判 check_negcompile 为 BLOCKER —— 它的 expect_fail 只问
         *   「编译是否失败」⇒ 任何错误都算 PASS ⇒ 把被测物整个拿走也 5/5 PASS。
         * ⇒ 同一个原理施于本处:只断言「返回非 0」会让【任何一种失败】冒充【预期的失败】。 */
        chdsp_biquad_coef_t c;
        int r_ok   = chdsp_bq_design(CHDSP_FT_PEAKING,   1000.0, 1.0,  15.0, &c);
        int r_gain = chdsp_bq_design(CHDSP_FT_HIGHSHELF,   20.0, 1.0,  24.0, &c);
        int r_freq = chdsp_bq_design(CHDSP_FT_PEAKING,  30000.0, 1.0,   0.0, &c);
        int r_q    = chdsp_bq_design(CHDSP_FT_PEAKING,   1000.0, 0.0,   0.0, &c);
        int r_type = chdsp_bq_design(CHDSP_FT_COUNT,     1000.0, 1.0,   0.0, &c);
        printf("      +15dB peak=%d(期 %d) +24dB 架式=%d(期 %d) f0=30k=%d(期 %d) Q=0=%d(期 %d) 非法类型=%d(期 %d)\n",
               r_ok, CHDSP_BQ_OK, r_gain, CHDSP_BQ_ERR_GAIN_ENV, r_freq, CHDSP_BQ_ERR_FREQ,
               r_q, CHDSP_BQ_ERR_Q, r_type, CHDSP_BQ_ERR_TYPE);
        OKC("CHK-B1", r_ok == CHDSP_BQ_OK && r_gain == CHDSP_BQ_ERR_GAIN_ENV
                      && r_freq == CHDSP_BQ_ERR_FREQ && r_q == CHDSP_BQ_ERR_Q
                      && r_type == CHDSP_BQ_ERR_TYPE,
            "⭐ 五种情形各自返回【它自己那条】错误码(⛔ 不是「非 0 即算过」)");
    }
    {   /* CHK-B1b ⭐ 守的是【增益】不是【S】—— 直接证伪那句过时表述 */
        chdsp_biquad_coef_t c;
        int s_big = chdsp_bq_design(CHDSP_FT_HIGHSHELF, 20.0, 2.0, 15.0, &c);   /* S=2 > 1 */
        int s_ok  = chdsp_bq_design(CHDSP_FT_HIGHSHELF, 20.0, 1.0, 15.0, &c);
        int g_18  = chdsp_bq_design(CHDSP_FT_HIGHSHELF, 20.0, 1.0, 18.1, &c);   /* 超包络 */
        int g_17  = chdsp_bq_design(CHDSP_FT_HIGHSHELF, 20.0, 1.0, 17.9, &c);   /* 界内 */
        printf("      S=2.0@+15dB=%d  S=1.0@+15dB=%d  |  G=+18.1dB=%d  G=+17.9dB=%d\n",
               s_big, s_ok, g_18, g_17);
        OKC("CHK-B1b", s_big == CHDSP_BQ_OK && s_ok == CHDSP_BQ_OK
                       && g_18 == CHDSP_BQ_ERR_GAIN_ENV && g_17 == CHDSP_BQ_OK,
            "⭐ S>1 不触发拦截(它几乎不影响界);增益跨 18.0618 dB 才触发 "
            "⇒ 直接证伪 chdsp_fixed.h:446 那句「S>1 ⇒ 界失效」");
    }
    {   /* CHK-B2 HPF/LPF 结构约束量化 ⇒ DC/Nyquist 零点精确(扫 fc) */
        int i, nz_hp = 0, nz_lp = 0, N = 400;
        for (i = 0; i < N; i++) {
            double fc = 20.0 * pow(1000.0, (double)i / (double)(N - 1));
            chdsp_biquad_coef_t h, l;
            if (chdsp_bq_design(CHDSP_FT_HPF, fc, 0.7071, 0.0, &h) == 0) {
                double s = chdsp_coef_to_f64(h.b0) + chdsp_coef_to_f64(h.b1)
                         + chdsp_coef_to_f64(h.b2);
                if (s != 0.0) { nz_hp++; }
            }
            if (chdsp_bq_design(CHDSP_FT_LPF, fc, 0.7071, 0.0, &l) == 0) {
                double s = chdsp_coef_to_f64(l.b0) - chdsp_coef_to_f64(l.b1)
                         + chdsp_coef_to_f64(l.b2);
                if (s != 0.0) { nz_lp++; }
            }
        }
        printf("      fc 扫 %d 点: HPF@DC 非零 %d 处;LPF@Nyq 非零 %d 处\n", N, nz_hp, nz_lp);
        OKC("CHK-B2", nz_hp == 0 && nz_lp == 0,
            "结构约束量化使 DC/Nyquist 零点在量化后恒精确(0 处破坏)");
    }
    {   /* CHK-B3 LR 极性规则 */
        int p2 = chdsp_xover_needs_polarity_flip(1, 2);
        int p4 = chdsp_xover_needs_polarity_flip(1, 4);
        int p6 = chdsp_xover_needs_polarity_flip(1, 6);
        int p8 = chdsp_xover_needs_polarity_flip(1, 8);
        printf("      LR2=%d LR4=%d LR6=%d LR8=%d (1=须反相)\n", p2, p4, p6, p8);
        OKC("CHK-B3", p2 == 1 && p4 == 0 && p6 == 1 && p8 == 0,
            "阶数 mod 4 == 2 ⇒ 须反相;== 0 ⇒ 同相");
    }
    {   /* CHK-B4 系数斜坡:①中间系数恒在稳定三角内 ②输出无跳变 */
        chdsp_bq_t b; chdsp_biquad_coef_t c0, c1; chdsp_sat_t sat;
        int i, out_tri = 0; double maxjump = 0.0, prev = 0.0;
        chdsp_bq_init(&b); chdsp_sat_reset(&sat);
        (void)chdsp_bq_design(CHDSP_FT_PEAKING, 100.0, 8.0, +12.0, &c0);
        (void)chdsp_bq_design(CHDSP_FT_PEAKING, 4000.0, 0.7, -10.0, &c1);
        chdsp_bq_set_coef_now(&b, &c0); b.bypass = 0u;
        for (i = 0; i < 2000; i++) { (void)chdsp_bq_process1(&b, smp_f(0.05 * sin(i * 0.1)), &sat); }
        chdsp_bq_set_coef_ramp(&b, &c1, 480u);       /* 10 ms 斜坡 */
        for (i = 0; i < 2000; i++) {
            double a1, a2, y;
            y = chdsp_smp_to_f64(chdsp_bq_process1(&b, smp_f(0.05 * sin(i * 0.1)), &sat));
            a1 = chdsp_coef_to_f64(b.cur.a1); a2 = chdsp_coef_to_f64(b.cur.a2);
            if (!(fabs(a2) < 1.0 && fabs(a1) < 1.0 + a2)) { out_tri++; }
            if (i > 0 && fabs(y - prev) > maxjump) { maxjump = fabs(y - prev); }
            prev = y;
        }
        printf("      斜坡 480 步:越出稳定三角 %d 次;输出最大逐样本跳变 %.4e\n", out_tri, maxjump);
        OKC("CHK-B4", out_tri == 0 && maxjump < 0.02,
            "稳定三角是凸集 ⇒ 线性插值恒稳定;且无输出跳变(防爆音)");
    }

    /* ================= detector ================= */
    printf("\ndetector\n");
    {   /* CHK-D1 对称时间常数 ⇒ 读数 = 均值功率 */
        double worst = 0.0; double lv;
        for (lv = -20.0; lv >= -100.0; lv -= 20.0) {
            chdsp_det_t d; int i; chdsp_pow_q8_54_t p = chdsp_pow_from_raw(0);
            double amp = pow(10.0, lv / 20.0), got, exp_db = lv - 3.0103;
            chdsp_det_init(&d, CHDSP_DET_RMS, 100.0, 100.0);
            for (i = 0; i < CHDSP_FS_HZ * 3; i++) {
                p = chdsp_det_process1(&d, smp_f(amp * sin(2.0 * M_PI * 1000.0 * i / CHDSP_FS_HZ)));
            }
            got = (double)chdsp_db_raw(chdsp_pow_to_db(p)) / 256.0;
            if (fabs(got - exp_db) > worst) { worst = fabs(got - exp_db); }
        }
        printf("      对称 atk=rel=100ms,−20…−100 dBFS:最大偏离均值功率 = %.3f dB\n", worst);
        OKC("CHK-D1", worst <= 0.05, "对称时读数精确等于均值功率(≤0.05 dB)");
    }
    {   /* CHK-D2 拆两条:①非塌陷(本模块真正声称的那件事)②精度(须离功率底有余量)
         * ⚠ 初版把两者写成一个断言,并在 −120 dBFS 上要求 ±1 dB —— 而该点距
         *   release=100ms 的功率底(−125.74 dB)只有 2.7 dB ⇒ 截断偏置使读数低 1.45 dB。
         *   ⇒ **精度断言被下错了地方**,拆开:非塌陷仍在 −120,精度移到有 ≥20 dB 余量处。 */
        chdsp_det_t d; int i; chdsp_pow_q8_54_t p = chdsp_pow_from_raw(0);
        double amp = pow(10.0, -120.0 / 20.0), got;
        chdsp_det_init(&d, CHDSP_DET_RMS, 100.0, 100.0);
        for (i = 0; i < CHDSP_FS_HZ * 3; i++) {
            p = chdsp_det_process1(&d, smp_f(amp * sin(2.0 * M_PI * 1000.0 * i / CHDSP_FS_HZ)));
        }
        got = (double)chdsp_db_raw(chdsp_pow_to_db(p)) / 256.0;
        printf("      −120 dBFS ⇒ 状态 raw = %lld,读数 %.2f dB(功率底 −125.74,余量 2.7 dB)\n",
               (long long)chdsp_pow_raw(p), got);
        OKC("CHK-D2a", chdsp_pow_raw(p) > 0,
            "⭐ 功率状态用 Q8.54 ⇒ −120 dBFS **不塌到 0**(⛔ Q4.27 会塌 —— 这是本条真正测的事)");
        {
            chdsp_det_t d2; chdsp_pow_q8_54_t p2 = chdsp_pow_from_raw(0);
            double a2 = pow(10.0, -100.0 / 20.0), g2;
            chdsp_det_init(&d2, CHDSP_DET_RMS, 100.0, 100.0);
            for (i = 0; i < CHDSP_FS_HZ * 3; i++) {
                p2 = chdsp_det_process1(&d2, smp_f(a2 * sin(2.0 * M_PI * 1000.0 * i / CHDSP_FS_HZ)));
            }
            g2 = (double)chdsp_db_raw(chdsp_pow_to_db(p2)) / 256.0;
            printf("      −100 dBFS(距底 22.7 dB)⇒ 读数 %.2f dB(期望 −103.01)\n", g2);
            OKC("CHK-D2b", fabs(g2 - (-103.01)) <= 0.2,
                "离功率底 ≥20 dB 处精度 ≤0.2 dB");
        }
    }
    {   /* CHK-D3 功率底 vs release —— 锁住那张表 */
        double a50  = 1.0 - exp(-1.0 / (0.050 * CHDSP_FS_HZ));
        double a3k  = 1.0 - exp(-1.0 / (3.000 * CHDSP_FS_HZ));
        double f50  = 10.0 * log10((1.0 / a50) / ldexp(1.0, CHDSP_POW_FRACBITS));
        double f3k  = 10.0 * log10((1.0 / a3k) / ldexp(1.0, CHDSP_POW_FRACBITS));
        printf("      功率底: release 50ms ⇒ %.2f dB;3000ms ⇒ %.2f dB\n", f50, f3k);
        OKC("CHK-D3", f50 < -125.0 && f3k < -108.0 && f3k > -114.0,
            "功率底随 release 变化,最长 release 下 ≈ −111 dB(比门限量程下沿低 31 dB)");
    }

    /* ================= dynamics ================= */
    printf("\ndynamics\n");
    {   /* CHK-Y1 ⭐ 门的【默认状态】—— 一个什么都不设的对象必须落关门侧(团队纪律 D6-k) */
        chdsp_gate_t g;
        memset(&g, 0, sizeof(g));      /* ⭐ 什么都不设:全 0 */
        printf("      memset 全 0 的门对象:state = %d(0 = CLOSED)\n", (int)g.state);
        OKC("CHK-Y1a", g.state == CHDSP_GATE_CLOSED,
            "⭐ 什么都不设的对象默认落【关门】侧(D6-k:显式设值的测试验不了默认值)");
        /* 肯定式:低电平下必须保持关闭 */
        chdsp_gate_init(&g, -45.0, 20.0, 3.0, 60.0, 1.0, 0.0, 50.0);
        g.enabled = 1u;
        {
            int i; chdsp_db_q23_8_t gd; double last = 0.0;
            for (i = 0; i < CHDSP_FS_HZ; i++) {
                (void)chdsp_gate_gain1(&g, smp_f(1e-4 * rndn()), &gd);  /* ≈ −80 dBFS */
                last = (double)chdsp_db_raw(gd) / 256.0;
            }
            printf("      −80 dBFS 噪声下门增益 = %.2f dB,state = %d\n", last, (int)g.state);
            OKC("CHK-Y1b", g.state == CHDSP_GATE_CLOSED && last < -20.0,
                "远低于门限时门保持关闭且确实衰减(肯定式条件生效)");
        }
    }
    {   /* CHK-Y2 迟滞防颤振:门限附近抖动时开合次数应有限 */
        chdsp_gate_t g; int i, toggles = 0; chdsp_gate_state_t prev;
        chdsp_gate_init(&g, -45.0, 20.0, 3.0, 60.0, 1.0, 20.0, 50.0);
        g.enabled = 1u; prev = g.state;
        for (i = 0; i < CHDSP_FS_HZ; i++) {
            /* 电平在门限上下 ±1 dB 缓慢摆动 */
            double lv = -45.0 + 1.0 * sin(2.0 * M_PI * 3.0 * i / CHDSP_FS_HZ);
            double amp = pow(10.0, lv / 20.0) * 1.41421356;
            (void)chdsp_gate_gain1(&g, smp_f(amp * sin(2.0 * M_PI * 500.0 * i / CHDSP_FS_HZ)), 0);
            if (g.state != prev) { toggles++; prev = g.state; }
        }
        printf("      门限 ±1 dB 摆动 1 秒:状态切换 %d 次(迟滞 3 dB ⇒ 应很少)\n", toggles);
        OKC("CHK-Y2", toggles <= 4, "迟滞抑制了门限附近的颤振");
    }
    {   /* CHK-Y3 ⭐ 限幅器前视 ⇒ 阶跃到满量程时无过冲 */
        chdsp_limiter_t l; int i; double peak = 0.0;
        (void)chdsp_limiter_init(&l, g_look_out, sizeof(g_look_out) / sizeof(g_look_out[0]),
                                 -6.0, 1.0, 50.0);
        l.enabled = 1u;
        for (i = 0; i < CHDSP_FS_HZ / 10; i++) {
            double v = (i < 2000) ? 0.0 : 0.9;      /* 阶跃到 −0.9 dBFS 级 */
            double y = chdsp_smp_to_f64(chdsp_limiter_process1(&l, smp_f(v), 0, 0));
            if (i > 2000 && fabs(y) > peak) { peak = fabs(y); }
        }
        printf("      阶跃后输出峰值 = %.4f(阈值 −6 dBFS = %.4f)\n", peak, pow(10.0, -6.0 / 20.0));
        OKC("CHK-Y3", peak <= pow(10.0, -6.0 / 20.0) * 1.15,
            "前视使阶跃过冲 ≤15%(⛔ 无前视的反馈式会明显过冲)");
    }
    {   /* CHK-Y4 压缩器软拐点:增益曲线在拐点处连续 */
        chdsp_comp_t c; double maxstep = 0.0, prev = 0.0; int i;
        chdsp_comp_init(&c, -20.0, 4.0, 12.0, 1.0, 1.0, 0.0, CHDSP_DET_RMS);
        c.enabled = 1u;
        for (i = 0; i < 200; i++) {
            double lv = -40.0 + 0.25 * i, g;
            chdsp_db_q23_8_t gd;
            double amp = pow(10.0, lv / 20.0) * 1.41421356;
            int k;
            chdsp_comp_reset(&c);
            for (k = 0; k < 4800; k++) {
                (void)chdsp_comp_gain1(&c, smp_f(amp * sin(2.0 * M_PI * 500.0 * k / CHDSP_FS_HZ)), &gd);
            }
            g = (double)chdsp_db_raw(gd) / 256.0;
            if (i > 0 && fabs(g - prev) > maxstep) { maxstep = fabs(g - prev); }
            prev = g;
        }
        printf("      输入每升 0.25 dB,增益最大跳变 = %.3f dB(软拐点 12 dB)\n", maxstep);
        OKC("CHK-Y4", maxstep <= 0.25, "软拐点使增益曲线连续(硬拐点会在阈值处跳)");
    }

    /* ================= FIR ================= */
    printf("\nFIR\n");
#if CHDSP_OUT_FIR_TAPS > 0
    {   /* CHK-F1 对称 ⇒ 线性相位;群延迟 = (N−1)/2 */
        chdsp_fir_t f; int i, asym = 0; uint16_t N = CHDSP_OUT_FIR_TAPS;
        int e = chdsp_fir_design_lowpass(8000.0, 5.65, g_fir_h, N);
        for (i = 0; i < N / 2; i++) {
            if (chdsp_coef_raw(g_fir_h[i]) != chdsp_coef_raw(g_fir_h[N - 1 - i])) { asym++; }
        }
        (void)chdsp_fir_init(&f, g_fir_h, g_fir_z, N);
        printf("      设计返回 %d;非对称抽头对数 = %d;群延迟 = %u 样本(期望 %u)\n",
               e, asym, (unsigned)chdsp_fir_group_delay(&f), (unsigned)((N - 1) / 2));
        OKC("CHK-F1", e == 0 && asym == 0 && chdsp_fir_group_delay(&f) == (N - 1) / 2,
            "抽头严格对称 ⇒ 线性相位;群延迟 = (N−1)/2");
    }
    {   /* CHK-F2 关闭时逐位透传 */
        chdsp_fir_t f; int i, bad = 0;
        (void)chdsp_fir_init(&f, g_fir_h, g_fir_z, CHDSP_OUT_FIR_TAPS);
        f.enabled = 0u;
        for (i = 0; i < 5000; i++) {
            chdsp_smp_q4_27_t x = chdsp_smp_from_raw((int32_t)(rnd32() >> 5) - (1 << 26));
            if (chdsp_smp_raw(chdsp_fir_process1(&f, x, 0)) != chdsp_smp_raw(x)) { bad++; }
        }
        printf("      关闭状态 5000 样本:不等 %d 处\n", bad);
        OKC("CHK-F2", bad == 0, "FIR 关闭 = 逐位透传(⛔ 不得偷偷改动样本)");
    }
#else
    printf("      (CHDSP_OUT_FIR_TAPS = 0,FIR 检查跳过 —— **显式跳过,不是静默**)\n");
#endif

    /* ================= chain ================= */
    printf("\nchain\n");
    {   /* CHK-C1 ⭐ D4 顺序:阻带激励下的链内电平 */
        chdsp_out_ch_t ch; chdsp_out_bufs_t b; uint16_t nx = 0; int i;
        chdsp_biquad_coef_t xo[CHDSP_OUT_XO_SECTIONS], pk;
        double peak_after_xo = 0.0, peak_after_peq = 0.0;
        memset(&b, 0, sizeof(b));
        b.delay_buf = g_dly_out; b.delay_cap = sizeof(g_dly_out)/sizeof(g_dly_out[0]);
        b.lim_look = g_look_out; b.lim_cap = sizeof(g_look_out)/sizeof(g_look_out[0]);
        b.spk_rms = g_spk_r; b.spk_rms_cap = sizeof(g_spk_r)/sizeof(g_spk_r[0]);
        b.spk_peak = g_spk_p; b.spk_peak_cap = sizeof(g_spk_p)/sizeof(g_spk_p[0]);
        b.fir_state = g_fir_z; b.fir_h = g_fir_h; b.fir_taps = 0u;
        (void)chdsp_out_ch_init(&ch, &b);
        (void)chdsp_bq_design_xover(1, 4, 1, 120.0, xo, &nx);
        for (i = 0; i < (int)nx; i++) { chdsp_bq_set_coef_now(&ch.xo_hp_sec[i], &xo[i]);
                                        ch.xo_hp_sec[i].bypass = 0u; }
        ch.xo_hp.n = nx;
        (void)chdsp_bq_design(CHDSP_FT_PEAKING, 40.0, 1.0, +12.0, &pk);
        chdsp_bq_set_coef_now(&ch.peq_sec[0], &pk); ch.peq_sec[0].bypass = 0u; ch.peq.n = 1u;
        /* 40 Hz 正弦(落在分频阻带),标称 −20 dBFS */
        {
            chdsp_bq_t hp[CHDSP_OUT_XO_SECTIONS], pq; chdsp_sat_t s2; int k;
            chdsp_sat_reset(&s2);
            for (i = 0; i < (int)nx; i++) { chdsp_bq_init(&hp[i]);
                chdsp_bq_set_coef_now(&hp[i], &xo[i]); hp[i].bypass = 0u; }
            chdsp_bq_init(&pq); chdsp_bq_set_coef_now(&pq, &pk); pq.bypass = 0u;
            for (k = 0; k < 48000; k++) {
                double v = 0.1 * sin(2.0 * M_PI * 40.0 * k / CHDSP_FS_HZ);
                chdsp_smp_q4_27_t t = smp_f(v);
                /* 本设计顺序:分频 → PEQ */
                for (i = 0; i < (int)nx; i++) { t = chdsp_bq_process1(&hp[i], t, &s2); }
                if (k > 24000 && fabs(chdsp_smp_to_f64(t)) > peak_after_xo)
                    { peak_after_xo = fabs(chdsp_smp_to_f64(t)); }
                t = chdsp_bq_process1(&pq, t, &s2);
            }
            /* 反序:PEQ → 分频 */
            chdsp_bq_init(&pq); chdsp_bq_set_coef_now(&pq, &pk); pq.bypass = 0u;
            for (i = 0; i < (int)nx; i++) { chdsp_bq_init(&hp[i]);
                chdsp_bq_set_coef_now(&hp[i], &xo[i]); hp[i].bypass = 0u; }
            for (k = 0; k < 48000; k++) {
                double v = 0.1 * sin(2.0 * M_PI * 40.0 * k / CHDSP_FS_HZ);
                chdsp_smp_q4_27_t t = chdsp_bq_process1(&pq, smp_f(v), &s2);
                if (k > 24000 && fabs(chdsp_smp_to_f64(t)) > peak_after_peq)
                    { peak_after_peq = fabs(chdsp_smp_to_f64(t)); }
                for (i = 0; i < (int)nx; i++) { t = chdsp_bq_process1(&hp[i], t, &s2); }
            }
        }
        printf("      40 Hz 阻带激励(−20 dBFS):分频在前的链内峰 %.5f;PEQ 在前 %.5f ⇒ 差 %.2f dB\n",
               peak_after_xo, peak_after_peq, 20.0 * log10(peak_after_peq / peak_after_xo));
        OKC("CHK-C1", 20.0 * log10(peak_after_peq / peak_after_xo) >= 20.0,
            "分频在前使阻带链内电平低 ≥20 dB(设计件 §2③ 的实测 31.14 dB)");
    }
    {   /* CHK-C2 分频极性规则被链使用 */
        chdsp_out_ch_t ch; chdsp_out_bufs_t b;
        memset(&b, 0, sizeof(b));
        b.delay_buf = g_dly_out; b.delay_cap = sizeof(g_dly_out)/sizeof(g_dly_out[0]);
        b.lim_look = g_look_out; b.lim_cap = sizeof(g_look_out)/sizeof(g_look_out[0]);
        b.spk_rms = g_spk_r; b.spk_rms_cap = sizeof(g_spk_r)/sizeof(g_spk_r[0]);
        b.spk_peak = g_spk_p; b.spk_peak_cap = sizeof(g_spk_p)/sizeof(g_spk_p[0]);
        b.fir_state = g_fir_z; b.fir_h = g_fir_h; b.fir_taps = 0u;
        (void)chdsp_out_ch_init(&ch, &b);
        ch.xo_polarity_flip = (int8_t)chdsp_xover_needs_polarity_flip(1, 2);
        {
            chdsp_io_q0_31_t o[CHDSP_FRAME_SAMPLES];
            chdsp_smp_q4_27_t in[CHDSP_FRAME_SAMPLES];
            int i; double s = 0.0;
            for (i = 0; i < CHDSP_FRAME_SAMPLES; i++) { in[i] = smp_f(0.1); }
            chdsp_out_ch_process(&ch, in, o, CHDSP_FRAME_SAMPLES);
            for (i = 0; i < CHDSP_FRAME_SAMPLES; i++) { s += chdsp_io_to_f64(o[i]); }
            printf("      LR2 ⇒ flip=%d;直流 0.1 输入的输出和 = %+.4f(应为负 ⇒ 极性已翻)\n",
                   (int)ch.xo_polarity_flip, s);
            OKC("CHK-C2", ch.xo_polarity_flip == 1 && s < 0.0,
                "LR2 的极性翻转规则确实作用在链上(⛔ 不只是个返回值)");
        }
    }
    {   /* CHK-C4 ⭐ 算法插入点真的在链上(触达证明) */
        chdsp_in_ch_t ich;
        chdsp_io_q0_31_t in[CHDSP_FRAME_SAMPLES];
        chdsp_smp_q4_27_t out[CHDSP_FRAME_SAMPLES];
        int i, e;
        e = chdsp_in_ch_init(&ich, g_dly_in, sizeof(g_dly_in)/sizeof(g_dly_in[0]),
                             g_look_in, sizeof(g_look_in)/sizeof(g_look_in[0]));
        for (i = 0; i < CHDSP_FRAME_SAMPLES; i++) { in[i] = chdsp_io_from_raw(1 << 20); }
        chdsp_in_ch_process(&ich, in, out, CHDSP_FRAME_SAMPLES);
        printf("      init=%d;钩子调用次数 AEC=%u ANC=%u AGC=%u AFC=%u\n", e,
               ich.hook_aec.call_count, ich.hook_anc.call_count,
               ich.hook_agc.call_count, ich.hook_afc.call_count);
        OKC("CHK-C4", e == 0 && ich.hook_aec.call_count == 1u && ich.hook_anc.call_count == 1u
                      && ich.hook_agc.call_count == 1u && ich.hook_afc.call_count == 1u,
            "⭐ 四个 ✳ 插入点每帧各被调用一次 ⇒ 它们真的在链上,不是文档里的箭头");
    }


    /* ================= 补:杀伤矩阵抓出的无分辨力检查(r2) ================= */
    printf("\n补充检查(杀伤矩阵抓出 10 个变异存活后新增)\n");
    {   /* CHK-B4b 直接测【斜坡机制本身】,不测输出跳变
         * ⚠ 原 CHK-B4 用「输出跳变 <0.02」判斜坡 —— 而 DF1 状态连续本来就不跳,
         *   所以关掉斜坡也照样通过。⇒ 那条对 BQ_NORAMP 零分辨力。 */
        chdsp_bq_t b; chdsp_biquad_coef_t c0, c1; chdsp_sat_t sat;
        int i, distinct = 0; int32_t seen[8]; int nseen = 0;
        chdsp_bq_init(&b); chdsp_sat_reset(&sat);
        (void)chdsp_bq_design(CHDSP_FT_PEAKING, 100.0, 8.0, +12.0, &c0);
        (void)chdsp_bq_design(CHDSP_FT_PEAKING, 4000.0, 0.7, -10.0, &c1);
        chdsp_bq_set_coef_now(&b, &c0); b.bypass = 0u;
        chdsp_bq_set_coef_ramp(&b, &c1, 480u);
        for (i = 0; i < 8; i++) {
            (void)chdsp_bq_process1(&b, smp_f(0.01), &sat);
            { int k, found = 0; int32_t v = chdsp_coef_raw(b.cur.a1);
              for (k = 0; k < nseen; k++) { if (seen[k] == v) { found = 1; } }
              if (!found && nseen < 8) { seen[nseen++] = v; } }
        }
        distinct = nseen;
        printf("      斜坡前 8 个样本内 a1 出现的不同取值数 = %d(斜坡应逐步变 ⇒ >2)\n", distinct);
        OKC("CHK-B4b", distinct > 2,
            "⭐ 直接测斜坡机制:a1 在斜坡内逐样本取到多个中间值(⛔ 跳变版只有 1 个)");
    }
    {   /* CHK-D1b 非对称检测器 ⇒ 读数须【介于均值与峰值之间】
         * ⚠ 原 CHK-D1 用 atk=rel 对称 ⇒ 对「不分方向」的变异零分辨力。 */
        chdsp_det_t d; int i; chdsp_pow_q8_54_t p = chdsp_pow_from_raw(0);
        double amp = pow(10.0, -20.0 / 20.0), got;
        chdsp_det_init(&d, CHDSP_DET_RMS, 10.0, 100.0);      /* 非对称 */
        for (i = 0; i < CHDSP_FS_HZ * 3; i++) {
            p = chdsp_det_process1(&d, smp_f(amp * sin(2.0 * M_PI * 1000.0 * i / CHDSP_FS_HZ)));
        }
        got = (double)chdsp_db_raw(chdsp_pow_to_db(p)) / 256.0;
        printf("      atk=10ms rel=100ms @−20 dBFS ⇒ 读数 %.2f dB(均值 −23.01,峰值 −20.00)\n", got);
        OKC("CHK-D1b", got > -23.01 + 0.5 && got < -20.00 - 0.3,
            "⭐ 非对称时读数严格介于均值与峰值之间(⛔ 不分方向的版本会贴到峰值)");
    }
    {   /* CHK-Y1c ⭐ 门的肯定式条件:电平落在【迟滞带内】时,从 CLOSED 出发必须【保持关闭】
         * ⚠ 原 CHK-Y1b 用 −80 dBFS(远低于门限)⇒ 肯定式与否定式给同一答案,零分辨力。
         *   分辨力只在 (thr−hyst, thr) 这一带里:肯定式要求 L≥thr 才开,否定式只要 L≥thr−hyst 就开。 */
        chdsp_gate_t g; chdsp_det_t probe; int i; double amp, Lread;
        chdsp_pow_q8_54_t pp = chdsp_pow_from_raw(0);
        /* ⚠ 先用同参数的独立探针测出【检测器实际读到多少】,再据此断言门的反应。
         *   初版直接按「信号均值功率」设电平 ⇒ 而非对称检测器读数偏高 ⇒ 实际落在带外,
         *   测试因此对 GATE_NEGATIVE 没有分辨力。**这正是 EXP-2c 的教训,我自己没应用。** */
        amp = pow(10.0, -46.5 / 20.0) * 1.41421356;
        chdsp_det_init(&probe, CHDSP_DET_RMS, 50.0, 50.0);   /* 对称 ⇒ 读数 = 均值功率 */
        for (i = 0; i < CHDSP_FS_HZ; i++) {
            pp = chdsp_det_process1(&probe, smp_f(amp * sin(2.0 * M_PI * 500.0 * i / CHDSP_FS_HZ)));
        }
        Lread = (double)chdsp_db_raw(chdsp_pow_to_db(pp)) / 256.0;
        chdsp_gate_init(&g, -45.0, 20.0, 3.0, 60.0, 50.0, 0.0, 50.0);  /* 同为对称 */
        g.enabled = 1u;
        for (i = 0; i < CHDSP_FS_HZ; i++) {
            (void)chdsp_gate_gain1(&g, smp_f(amp * sin(2.0 * M_PI * 500.0 * i / CHDSP_FS_HZ)), 0);
        }
        printf("      独立探针读数 L = %.2f dB(迟滞带 −48…−45);门 state = %d\n", Lread, (int)g.state);
        OKC("CHK-Y1c0", Lread > -48.0 && Lread < -45.0,
            "⭐ 前提自检:检测器读数确实落在迟滞带内 ⇒ 本检查有分辨力");
        OKC("CHK-Y1c", g.state == CHDSP_GATE_CLOSED,
            "⭐ 肯定式:迟滞带内不开门(⛔ 否定式豁免版会开)");
    }
    {   /* CHK-Y2b 迟滞:门限附近【快速】抖动 ⇒ 无迟滞会颤振
         * ⚠ 原 CHK-Y2 用 3 Hz 缓慢摆动 + 检测器平滑 ⇒ 无迟滞也不颤,零分辨力。 */
        /* ⭐ 决定性构造:先升到 thr+0.5(开门),再降到 thr−1.5 ——
         *   该点仍在迟滞带(thr−3, thr)内 ⇒ **有迟滞应保持 OPEN,无迟滞应变 CLOSED**。
         *   ⚠ 初版用「±2 dB 正弦抖动」⇒ 检测器平滑把抖动吃掉了,两种版本都只切换 1 次
         *     ⇒ 对 NO_HYST 零分辨力。 */
        chdsp_gate_t g; int i; chdsp_gate_state_t after_up, after_down;
        double a_up = pow(10.0, (-45.0 + 0.5) / 20.0) * 1.41421356;
        double a_dn = pow(10.0, (-45.0 - 1.5) / 20.0) * 1.41421356;
        chdsp_gate_init(&g, -45.0, 20.0, 3.0, 60.0, 20.0, 0.0, 20.0);  /* 对称,读数=均值 */
        g.enabled = 1u;
        for (i = 0; i < CHDSP_FS_HZ / 2; i++) {
            (void)chdsp_gate_gain1(&g, smp_f(a_up * sin(2.0 * M_PI * 500.0 * i / CHDSP_FS_HZ)), 0);
        }
        after_up = g.state;
        for (i = 0; i < CHDSP_FS_HZ / 2; i++) {
            (void)chdsp_gate_gain1(&g, smp_f(a_dn * sin(2.0 * M_PI * 500.0 * i / CHDSP_FS_HZ)), 0);
        }
        after_down = g.state;
        printf("      升到 thr+0.5 ⇒ state=%d;再降到 thr−1.5(仍在迟滞带内)⇒ state=%d\n",
               (int)after_up, (int)after_down);
        OKC("CHK-Y2b0", after_up == CHDSP_GATE_OPEN, "前提自检:thr+0.5 确实把门打开了");
        OKC("CHK-Y2b", after_down != CHDSP_GATE_CLOSED,
            "⭐ 迟滞带内不关门(⛔ 无迟滞版在 thr−1.5 就会关)");
    }
    {   /* CHK-Y4b 软拐点的【平滑性】,不是【连续性】
         * ⚠ 原 CHK-Y4 测「相邻步的增益跳变」—— 硬拐点也是连续的,只是不光滑
         *   ⇒ 那条对 COMP_HARDKNEE 零分辨力。改测拐点中心处与解析软拐点值的一致性。 */
        chdsp_comp_t c; chdsp_db_q23_8_t gd; int k;
        double amp, got, want, W = 12.0, R = 4.0, slope = 1.0 - 1.0 / R;
        chdsp_comp_init(&c, -20.0, R, W, 1.0, 1.0, 0.0, CHDSP_DET_RMS);
        c.enabled = 1u;
        amp = pow(10.0, -20.0 / 20.0) * 1.41421356;    /* L = thr,拐点中心 */
        for (k = 0; k < CHDSP_FS_HZ / 2; k++) {
            (void)chdsp_comp_gain1(&c, smp_f(amp * sin(2.0 * M_PI * 500.0 * k / CHDSP_FS_HZ)), &gd);
        }
        got  = (double)chdsp_db_raw(gd) / 256.0;
        want = -slope * (0.0 + W / 2.0) * (0.0 + W / 2.0) / (2.0 * W);   /* = −slope·W/8 */
        printf("      L = thr 处增益 = %.3f dB(软拐点解析 %.3f;硬拐点应为 0.000)\n", got, want);
        OKC("CHK-Y4b", fabs(got - want) <= 0.3,
            "⭐ 拐点中心的增益等于软拐点解析值(⛔ 硬拐点版在此处为 0)");
    }
    {   /* CHK-C1b ⭐ D4 顺序:经【真正的链函数】观测,用饱和粘滞位作可观测量
         * ⚠ 原 CHK-C1 在测试里自己搭 biquad ⇒ 根本没走 chdsp_out_ch_process
         *   ⇒ 对 CHAIN_ORDER 变异零分辨力。 */
        chdsp_out_ch_t ch; chdsp_out_bufs_t b; uint16_t nx = 0; int i, k;
        chdsp_biquad_coef_t xo[CHDSP_OUT_XO_SECTIONS], pk;
        chdsp_io_q0_31_t o[CHDSP_FRAME_SAMPLES];
        chdsp_smp_q4_27_t in[CHDSP_FRAME_SAMPLES];
        memset(&b, 0, sizeof(b));
        b.delay_buf = g_dly_out; b.delay_cap = sizeof(g_dly_out)/sizeof(g_dly_out[0]);
        b.lim_look = g_look_out; b.lim_cap = sizeof(g_look_out)/sizeof(g_look_out[0]);
        b.spk_rms = g_spk_r; b.spk_rms_cap = sizeof(g_spk_r)/sizeof(g_spk_r[0]);
        b.spk_peak = g_spk_p; b.spk_peak_cap = sizeof(g_spk_p)/sizeof(g_spk_p[0]);
        b.fir_state = g_fir_z; b.fir_h = g_fir_h; b.fir_taps = 0u;
        (void)chdsp_out_ch_init(&ch, &b);
        (void)chdsp_bq_design_xover(1, 4, 1, 120.0, xo, &nx);
        for (i = 0; i < (int)nx; i++) { chdsp_bq_set_coef_now(&ch.xo_hp_sec[i], &xo[i]);
                                        ch.xo_hp_sec[i].bypass = 0u; }
        ch.xo_hp.n = nx;
        (void)chdsp_bq_design(CHDSP_FT_PEAKING, 40.0, 1.0, +15.0, &pk);
        chdsp_bq_set_coef_now(&ch.peq_sec[0], &pk); ch.peq_sec[0].bypass = 0u; ch.peq.n = 1u;
        /* 输出增益拉高,使「PEQ 在前」必然把 40 Hz 推过 Q4.27 上限而「分频在前」不会 */
        ch.gain = chdsp_db_to_gain(chdsp_db(20));
        chdsp_sat_reset(&ch.sat);
        for (k = 0; k < 200; k++) {
            for (i = 0; i < CHDSP_FRAME_SAMPLES; i++) {
                double t = (double)(k * CHDSP_FRAME_SAMPLES + i);
                in[i] = smp_f(0.9 * sin(2.0 * M_PI * 40.0 * t / CHDSP_FS_HZ));
            }
            chdsp_out_ch_process(&ch, in, o, CHDSP_FRAME_SAMPLES);
        }
        printf("      经真链函数,40 Hz@−0.9dBFS + 输出增益 +20dB:饱和粘滞 = %u,计数 = %u\n",
               (unsigned)ch.sat.sat_sticky, (unsigned)ch.sat.sat_count);
        OKC("CHK-C1b", ch.sat.sat_sticky == 0u,
            "⭐ 分频在前 ⇒ 阻带大信号先被衰减 ⇒ 链内不饱和(⛔ PEQ 在前会饱和)");
    }
    {   /* CHK-C3 ⭐ D3 的 HPF 位置:经【真正的链函数】观测
         * 素材 = 45 Hz 隆隆(−20 dBFS)+ 静默;门开着。
         * HPF 在动态之前 ⇒ 侧链读数低 ⇒ 门关闭 ⇒ 输出被压;
         * HPF 在动态之后 ⇒ 隆隆顶开门 ⇒ 输出明显更大。 */
        chdsp_in_ch_t ich; chdsp_io_q0_31_t in[CHDSP_FRAME_SAMPLES];
        chdsp_smp_q4_27_t out[CHDSP_FRAME_SAMPLES];
        chdsp_biquad_coef_t hp; uint16_t nh = 0; int i, k; double e = 0.0;
        (void)chdsp_in_ch_init(&ich, g_dly_in, sizeof(g_dly_in)/sizeof(g_dly_in[0]),
                               g_look_in, sizeof(g_look_in)/sizeof(g_look_in[0]));
        (void)chdsp_bq_design_xover(0, 2, 1, 80.0, &hp, &nh);
        chdsp_bq_set_coef_now(&ich.hpf_sec[0], &hp); ich.hpf_sec[0].bypass = 0u; ich.hpf.n = 1u;
        /* ⚠ 门限必须落在【HPF 前后两个侧链读数之间】,否则两种链序给同一答案 ⇒ 无分辨力。
         *   这正是我在设计件 EXP-2c 得到的结论,初版写 C 检查时没有应用。
         *   先用两个独立探针量出两个读数,再据此定门限并断言它确实夹在中间。 */
        {
            chdsp_det_t p_raw, p_hpf; chdsp_bq_t hb; chdsp_sat_t s3;
            chdsp_pow_q8_54_t a1 = chdsp_pow_from_raw(0), a2 = chdsp_pow_from_raw(0);
            double L_raw, L_hpf;
            chdsp_det_init(&p_raw, CHDSP_DET_RMS, 50.0, 50.0);
            chdsp_det_init(&p_hpf, CHDSP_DET_RMS, 50.0, 50.0);
            chdsp_bq_init(&hb); chdsp_bq_set_coef_now(&hb, &hp); hb.bypass = 0u;
            chdsp_sat_reset(&s3);
            for (i = 0; i < CHDSP_FS_HZ; i++) {
                chdsp_smp_q4_27_t v = smp_f(0.1 * sin(2.0 * M_PI * 45.0 * i / CHDSP_FS_HZ));
                a1 = chdsp_det_process1(&p_raw, v);
                a2 = chdsp_det_process1(&p_hpf, chdsp_bq_process1(&hb, v, &s3));
            }
            L_raw = (double)chdsp_db_raw(chdsp_pow_to_db(a1)) / 256.0;
            L_hpf = (double)chdsp_db_raw(chdsp_pow_to_db(a2)) / 256.0;
            printf("      侧链读数:无 HPF = %.2f dB;过 HPF = %.2f dB;门限取其中点 %.2f\n",
                   L_raw, L_hpf, (L_raw + L_hpf) / 2.0);
            OKC("CHK-C3a", (L_raw - L_hpf) > 6.0,
                "⭐ 前提自检:两种链序的侧链读数相差 >6 dB ⇒ 门限有落点 ⇒ 本检查有分辨力");
            chdsp_gate_init(&ich.gate, (L_raw + L_hpf) / 2.0, 20.0, 1.0, 60.0, 50.0, 0.0, 50.0);
        }
        ich.gate.enabled = 1u;
        for (k = 0; k < 400; k++) {
            for (i = 0; i < CHDSP_FRAME_SAMPLES; i++) {
                double t = (double)(k * CHDSP_FRAME_SAMPLES + i);
                in[i] = chdsp_io_from_raw((int32_t)floor(0.1 * sin(2.0 * M_PI * 45.0 * t / CHDSP_FS_HZ)
                                                         * 2147483647.0));
            }
            chdsp_in_ch_process(&ich, in, out, CHDSP_FRAME_SAMPLES);
            if (k > 200) { for (i = 0; i < CHDSP_FRAME_SAMPLES; i++) {
                double v = chdsp_smp_to_f64(out[i]); e += v * v; } }
        }
        e = 10.0 * log10(e / (double)(199 * CHDSP_FRAME_SAMPLES) + 1e-300);
        printf("      45 Hz 隆隆 −20 dBFS 经真链:输出功率 = %.2f dB\n", e);
        OKC("CHK-C3", e < -50.0,
            "⭐ HPF 在动态之前 ⇒ 隆隆不顶开门 ⇒ 输出被压(⛔ HPF 在后会顶开门)");
    }

    printf("\n================================================================\n");
    printf("合计: PASS=%d  FAIL=%d\n", g_pass, g_fail);
    printf("退出码 = %d  ⇒ **本文件的每条检查都是硬闸门**\n", g_fail ? 1 : 0);
    printf("================================================================\n");
    return g_fail ? 1 : 0;
}
