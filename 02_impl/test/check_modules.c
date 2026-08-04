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

static int g_fail = 0, g_pass = 0, g_regress = 0;
/* ⭐ 整改 2026-08-04 · critic MAJOR-4:
 * 交付件 results_impl_r1.txt 是 CTO / lead / 下一个 critic 读的**唯一入口**,
 * 而它原先只有一行「合计: PASS=29」——**没有任何标记区分**
 *   ①「这条有证伪证据(有变异杀得死它)」与
 *   ②「作者已知它证不了它名字里那件事」。
 * ⇒ 读者的自然理解是①,而其中六条是②。
 * ⇒ 凡 tag 里带「保留为回归项」的,单独计数并在汇总行标出。
 * ⛔ 它们仍计入 PASS/FAIL 与退出码 —— 它们**确实还在测别的真东西**(E-2:加标注不删数)。 */
static void OKC(const char *tag, int cond, const char *msg)
{
    if (cond) { g_pass++; } else { g_fail++; }
    if (strstr(tag, "保留为回归项") != NULL) { g_regress++; }
    printf("  [%s] %s %s\n", cond ? "PASS" : "FAIL", tag, msg);
}

/* 确定性 PRNG */

/* ── 测试用的**假 AFC**:只做一件事 —— 第一次被调到时请求一个 1 kHz 陷波。
 *    ⛔ 这不是 AFC 算法,它对啸叫检测零知识;它只用来证明【接口通了】。 */
static int g_fake_afc_called = 0;
static void fake_afc(void *user, chdsp_smp_q4_27_t *buf, uint16_t n)
{
    chdsp_in_ch_t *ch = (chdsp_in_ch_t *)user;
    (void)buf; (void)n;
    if (!g_fake_afc_called) {
        g_fake_afc_called = 1;
        (void)chdsp_in_ch_notch_request(ch, 1000.0, 8.0, -18.0, 0);
    }
}

static uint32_t g_rng = 0x2468ACE1u;
static uint32_t rnd32(void)
{ g_rng ^= g_rng << 13; g_rng ^= g_rng >> 17; g_rng ^= g_rng << 5; return g_rng; }
static double rndn(void)
{ double s = 0.0; int i; for (i = 0; i < 12; i++) { s += (double)rnd32() / 4294967296.0; } return s - 6.0; }

static chdsp_smp_q4_27_t smp_f(double v)
{ return chdsp_smp_from_raw((int32_t)floor(v * ldexp(1.0, CHDSP_SMP_FRACBITS) + 0.5)); }

/* 级联在频率 f 处的复频响(设计期 double,仅自验用)。⛔ 不转写被测公式,只读被测物产出的系数。 */
static void casc_h(const chdsp_biquad_coef_t *sec, int n, double f, double *re, double *im)
{
    double w = 2.0 * M_PI * f / (double)CHDSP_FS_HZ;
    double hr = 1.0, hi = 0.0;
    int i, t;
    for (i = 0; i < n; i++) {
        double bc[3], ac[3], br = 0.0, bi = 0.0, ar = 0.0, ai = 0.0, dr, di, dd, nr, ni;
        bc[0] = chdsp_coef_to_f64(sec[i].b0); bc[1] = chdsp_coef_to_f64(sec[i].b1);
        bc[2] = chdsp_coef_to_f64(sec[i].b2);
        ac[0] = 1.0; ac[1] = chdsp_coef_to_f64(sec[i].a1); ac[2] = chdsp_coef_to_f64(sec[i].a2);
        for (t = 0; t < 3; t++) {
            double cw = cos(-w * t), sw = sin(-w * t);
            br += bc[t] * cw; bi += bc[t] * sw;
            ar += ac[t] * cw; ai += ac[t] * sw;
        }
        dd = ar * ar + ai * ai;
        dr = (br * ar + bi * ai) / dd; di = (bi * ar - br * ai) / dd;
        nr = hr * dr - hi * di; ni = hr * di + hi * dr;
        hr = nr; hi = ni;
    }
    *re = hr; *im = hi;
}

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
            "⇒ 机械守住『界的唯一驱动量是增益』(chdsp_fixed.h §12 已于 2026-08-04 "
            "按 critic MAJOR-4 改正;本条是它的可执行形式,⛔ 不许再退回按 S 守)");
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
    {   /* CHK-B3 LR 极性规则 —— ⛔ 按【阶数 n】,不是 dB/oct */
        int p2 = chdsp_xover_needs_polarity_flip(1, chdsp_xo_order(2));
        int p4 = chdsp_xover_needs_polarity_flip(1, chdsp_xo_order(4));
        int p6 = chdsp_xover_needs_polarity_flip(1, chdsp_xo_order(6));
        int p8 = chdsp_xover_needs_polarity_flip(1, chdsp_xo_order(8));
        printf("      n=2:%d n=4:%d n=6:%d n=8:%d (1=须反相)\n", p2, p4, p6, p8);
        OKC("CHK-B3", p2 == 1 && p4 == 0 && p6 == 1 && p8 == 0,
            "**n** mod 4 == 2 ⇒ 须反相;== 0 ⇒ 同相");
    }
    {   /* CHK-B3u ⭐⭐ 单位守卫:喂 dB/oct 必须【当场非法】,⛔ 不许返回一个合理的 0
         * 事故形态:设计件把 12/24/36/48 叫「阶数」,而 mod 4 算的是 2/4/6/8。
         *   实现方按参数值套 ⇒ 12/24/36/48 mod 4 全 = 0 ⇒ **全判同相**
         *   ⇒ LR2/LR6 分频点深谷。
         * ⚠ STRICT_TYPES=1 下这根本编译不过(见负编译 N8);本条守的是 =0 的兜底。 */
        int s12 = chdsp_xover_needs_polarity_flip(1, chdsp_xo_order(12));
        int s24 = chdsp_xover_needs_polarity_flip(1, chdsp_xo_order(24));
        int s36 = chdsp_xover_needs_polarity_flip(1, chdsp_xo_order(36));
        int s48 = chdsp_xover_needs_polarity_flip(1, chdsp_xo_order(48));
        printf("      误喂 dB/oct:12→%d 24→%d 36→%d 48→%d(期望全 −1 = 非法)\n",
               s12, s24, s36, s48);
        OKC("CHK-B3u", s12 == -1 && s24 == -1 && s36 == -1 && s48 == -1,
            "⭐ 误把 dB/oct 当阶数 ⇒ 返回 −1(⛔ 改动前它返回 0 = 全判同相)");
    }
    {   /* CHK-B3c dB/oct ↔ 阶数 换算,以及非法斜率 */
        int ok = 1, i;
        static const int32_t SL[4] = { 12, 24, 36, 48 };
        static const int32_t NN[4] = {  2,  4,  6,  8 };
        for (i = 0; i < 4; i++) {
            if (chdsp_xo_order_n(chdsp_xo_order_from_slope(chdsp_xo_slope(SL[i]))) != NN[i]) { ok = 0; }
            if (chdsp_xo_slope_db_oct(chdsp_xo_slope_from_order(chdsp_xo_order(NN[i]))) != SL[i]) { ok = 0; }
        }
        printf("      12/24/36/48 dB/oct ⇒ n = %d/%d/%d/%d;非 6 倍数(如 10)⇒ n = %d\n",
               chdsp_xo_order_n(chdsp_xo_order_from_slope(chdsp_xo_slope(12))),
               chdsp_xo_order_n(chdsp_xo_order_from_slope(chdsp_xo_slope(24))),
               chdsp_xo_order_n(chdsp_xo_order_from_slope(chdsp_xo_slope(36))),
               chdsp_xo_order_n(chdsp_xo_order_from_slope(chdsp_xo_slope(48))),
               chdsp_xo_order_n(chdsp_xo_order_from_slope(chdsp_xo_slope(10))));
        OKC("CHK-B3c", ok == 1
            && chdsp_xo_order_n(chdsp_xo_order_from_slope(chdsp_xo_slope(10))) == 0,
            "dB/oct ↔ 阶数 双向换算正确;非 6 倍数 ⇒ n=0(非法,下游会拒)");
    }
    {   /* CHK-B3s ⭐⭐ **会拦人的那条**:对四个档位各跑一次,断言分频点求和幅度。
         * ⛔ 不是打印,是进退出码。
         * ① 用规则给的极性 ⇒ 求和必须平坦(|sum| ≈ 0 dB)
         * ② 阳性对照:用**相反**极性 ⇒ 必须出现深谷 ⇒ 证明本条有分辨力
         *   (若两种极性都平坦,这条检查就是恒真的,PASS 不构成证据)
         * ⚠ LR2 是我们唯一能装进延迟预算的低延迟档(1.576 ms),而它恰好落在
         *   「须反相」那一档 ⇒ 一旦读反,唯一的低延迟出路带着一个深谷。 */
        static const int32_t NS[4] = { 2, 4, 6, 8 };
        const double FC = 1000.0;
        chdsp_biquad_coef_t hp[CHDSP_OUT_XO_SECTIONS], lp[CHDSP_OUT_XO_SECTIONS];
        uint16_t nh, nl; int i, bad_flat = 0, bad_ctrl = 0;
        double worst_flat = 0.0, best_notch = 0.0;
        for (i = 0; i < 4; i++) {
            chdsp_xo_order_t n = chdsp_xo_order(NS[i]);
            int flip = chdsp_xover_needs_polarity_flip(1, n);
            double hr, hi, lr_, li, sr, si, mag_ok, mag_bad;
            if (flip < 0) { bad_flat++; continue; }
            if (chdsp_bq_design_xover2(CHDSP_XO_LINKWITZ_RILEY, NS[i], 1, FC, hp, &nh) != CHDSP_BQ_OK ||
                chdsp_bq_design_xover2(CHDSP_XO_LINKWITZ_RILEY, NS[i], 0, FC, lp, &nl) != CHDSP_BQ_OK) {
                bad_flat++; continue;
            }
            casc_h(hp, (int)nh, FC, &hr, &hi);
            casc_h(lp, (int)nl, FC, &lr_, &li);
            /* 规则给的极性 */
            sr = lr_ + (flip ? -hr : hr); si = li + (flip ? -hi : hi);
            mag_ok = 20.0 * log10(sqrt(sr * sr + si * si) + 1e-300);
            /* 阳性对照:相反极性 */
            sr = lr_ + (flip ? hr : -hr); si = li + (flip ? hi : -hi);
            mag_bad = 20.0 * log10(sqrt(sr * sr + si * si) + 1e-300);
            printf("      LR%d(n=%d,%s):规则极性 %+7.3f dB | 反着来 %+8.2f dB\n",
                   NS[i] * 6, NS[i], flip ? "须反相" : "同相", mag_ok, mag_bad);
            if (fabs(mag_ok) > 0.1) { bad_flat++; }
            if (fabs(mag_ok) > worst_flat) { worst_flat = fabs(mag_ok); }
            if (mag_bad > -20.0) { bad_ctrl++; }
            if (i == 0 || mag_bad > best_notch) { best_notch = mag_bad; }
        }
        OKC("CHK-B3s", bad_flat == 0,
            "⭐ 四个档位按【规则给的极性】求和均平坦(最坏 |偏离| ≤0.1 dB)");
        OKC("CHK-B3s+", bad_ctrl == 0,
            "⭐ 阳性对照:极性反着来 ⇒ 四档全部出现 ≥20 dB 深谷 ⇒ 上一条不是恒真");
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
        OKC("CHK-B4(斜坡机制部分已被 CHK-B4b 取代·保留为回归项)",
            out_tri == 0 && maxjump < 0.02,
            "稳定三角是凸集 ⇒ 线性插值恒稳定(**本条真正在测的事,仍有效**)。"
            "⛔ 但其中「无输出跳变」一半对 BQ_NORAMP 变异【零分辨力】:DF1 状态连续本来就不跳"
            " ⇒ 关掉斜坡照样过。斜坡机制的分辨力在 CHK-B4b");
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
        OKC("CHK-D1(方向性部分已被 CHK-D1b 取代·保留为回归项)", worst <= 0.05,
            "对称时读数精确等于均值功率(≤0.05 dB)(**本条真正在测的事,仍有效**)。"
            "⛔ 但它对 DET_ONEDIR 变异【零分辨力】:atk=rel 对称时"
            "「不分方向」的坏版本与好版本**完全等价**。方向性的分辨力在 CHK-D1b");
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
    {   /* CHK-D3 功率底 vs release —— 锁住那张表
         * ⛔⛔ 整改 2026-08-05:本条原先**根本没调被测物** —— 它用 exp()/ldexp() 在测试里
         *   把公式重算了一遍,与 chdsp_* 一个函数都不沾 ⇒ **任何产品变异都杀不死它**。
         *   ⇒ 这正是 critic MAJOR-4 点名 CHK-C1 的那个形状(在测试里自己搭一套)。
         *   ⇒ 现改为调用**产品的** chdsp_smooth_from_ms() 取 α,再由它算功率底。 */
        double a50  = (double)chdsp_smooth_raw(chdsp_smooth_from_ms(50.0))   / 2147483648.0;
        double a3k  = (double)chdsp_smooth_raw(chdsp_smooth_from_ms(3000.0)) / 2147483648.0;
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
            OKC("CHK-Y1b(已被 CHK-Y1c 取代·保留为回归项)",
                g.state == CHDSP_GATE_CLOSED && last < -20.0,
                "远低于门限时门保持关闭且确实衰减。"
                "⛔ 本条对 GATE_NEGATIVE 变异【零分辨力】:−80 dBFS 远低于门限,"
                "肯定式与否定式给同一答案 ⇒ 它证不了「肯定式条件生效」。分辨力在 CHK-Y1c");
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
        OKC("CHK-Y2(已被 CHK-Y2b 取代·保留为回归项)", toggles <= 4,
            "门限附近切换次数有界。"
            "⛔ 本条对 NO_HYST 变异【零分辨力】:3 Hz 缓慢摆动被检测器平滑吃掉,"
            "无迟滞也不颤 ⇒ 它证不了「迟滞在起作用」。分辨力在 CHK-Y2b");
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
        OKC("CHK-Y4(已被 CHK-Y4b 取代·保留为回归项)", maxstep <= 0.25,
            "增益曲线相邻步无大跳变。"
            "⛔ 本条对 COMP_HARDKNEE 变异【零分辨力】:**硬拐点也是连续的**,只是不光滑"
            " ⇒ 它证不了软拐点。分辨力在 CHK-Y4b(拐点中心 vs 软拐点解析值)"
            "〔整改 2026-08-04 · critic MAJOR-4:原括注「硬拐点会在阈值处跳」**已删** —— "
            "那是我自己亲手证伪的一句,却仍作为一条 PASS 的理由印在交付件里〕");
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
        OKC("CHK-C1(已被 CHK-C1b 取代·保留为回归项)",
            20.0 * log10(peak_after_peq / peak_after_xo) >= 20.0,
            "两种顺序的阻带链内电平差 ≥20 dB。"
            "⛔ 本条对 CHAIN_ORDER 变异【零分辨力】:它在测试里**自己搭 biquad 链**,"
            "根本没调 chdsp_out_ch_process ⇒ 链序变异改不到它。分辨力在 CHK-C1b"
            "〔整改 2026-08-04 · critic MAJOR-4:原括注引「设计件 §2③ 实测 31.14 dB」**已删** —— "
            "本条没走被测链,⛔ 不得拿设计件的数为它背书〕");
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
        ch.xo_polarity_flip = (int8_t)chdsp_xover_needs_polarity_flip(1, chdsp_xo_order(2));
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

    /* ================= 陷波器组:三种工作模式(PRD §二.5 待定项②)================= */
    printf("\n陷波器组 · 三种工作模式(PRD §二.5)\n");
    {   /* CHK-N1 ⭐ FIXED:AFC 一律拿不到槽,且固定陷波不被动 */
        chdsp_notch_bank_t b; chdsp_bq_t sec[CHDSP_NOTCH_COUNT]; chdsp_bq_chain_t ch;
        int i, r_set, r_req = CHDSP_NOTCH_OK, rejected = 0;
        chdsp_bq_chain_init(&ch, sec, CHDSP_NOTCH_COUNT);
        chdsp_notch_bank_init(&b, CHDSP_NOTCH_MODE_FIXED, 0u);
        r_set = chdsp_notch_bank_set_fixed(&b, &ch, 0u, 120.0, 8.0, -6.0);
        for (i = 0; i < CHDSP_NOTCH_COUNT + 4; i++) {
            r_req = chdsp_notch_bank_request(&b, &ch, 300.0 + 10.0 * i, 8.0, -6.0, 0);
            if (r_req == CHDSP_NOTCH_ERR_NO_SLOT) { rejected++; }
        }
        printf("      FIXED:set_fixed=%d(期 0);%d 次 AFC 请求 ⇒ 被拒 %d 次;"
               "占用 %u;固定陷波 f=%.0f Hz\n",
               r_set, CHDSP_NOTCH_COUNT + 4, rejected,
               (unsigned)chdsp_notch_bank_used(&b), b.slot[0].f_hz);
        OKC("CHK-N1", r_set == CHDSP_NOTCH_OK && rejected == CHDSP_NOTCH_COUNT + 4
                      && chdsp_notch_bank_used(&b) == 1u && b.slot[0].f_hz == 120.0,
            "⭐ FIXED:AFC 请求**全部被拒**(⛔ 不得挪用固定槽),固定陷波原封不动");
    }
    {   /* CHK-N2 ⭐ DYNAMIC:填满后回收【最早那个】,⛔ 不是随便挑一个 */
        chdsp_notch_bank_t b; chdsp_bq_t sec[CHDSP_NOTCH_COUNT]; chdsp_bq_chain_t ch;
        int i; uint16_t idx0 = 0xFFFFu, idx_evict = 0xFFFFu; double f_after;
        chdsp_bq_chain_init(&ch, sec, CHDSP_NOTCH_COUNT);
        chdsp_notch_bank_init(&b, CHDSP_NOTCH_MODE_DYNAMIC, 0u);
        for (i = 0; i < CHDSP_NOTCH_COUNT; i++) {
            uint16_t k = 0xFFFFu;
            (void)chdsp_notch_bank_request(&b, &ch, 200.0 + 10.0 * i, 8.0, -6.0, &k);
            if (i == 0) { idx0 = k; }
        }
        /* 再来一个 ⇒ 必须回收 idx0(最早分配的那个) */
        (void)chdsp_notch_bank_request(&b, &ch, 9000.0, 8.0, -6.0, &idx_evict);
        f_after = b.slot[idx0].f_hz;
        printf("      DYNAMIC:填满 %u 槽;第 %u 次请求 ⇒ 占用槽 %u(最早那个是 %u),"
               "该槽 f 由 200 变成 %.0f;evict=%u reject=%u\n",
               (unsigned)CHDSP_NOTCH_COUNT, (unsigned)CHDSP_NOTCH_COUNT + 1u,
               (unsigned)idx_evict, (unsigned)idx0, f_after,
               (unsigned)b.evict_count, (unsigned)b.reject_count);
        OKC("CHK-N2", idx_evict == idx0 && f_after == 9000.0
                      && b.evict_count == 1u && b.reject_count == 0u
                      && chdsp_notch_bank_used(&b) == (uint16_t)CHDSP_NOTCH_COUNT,
            "⭐ DYNAMIC:槽满时回收**最早分配的那个**(LRU),占用数不变");
    }
    {   /* CHK-N3 ⭐⭐ HYBRID:固定槽在**任何压力下**都不被回收 —— 这是本组最要紧的一条 */
        const uint16_t NF = (uint16_t)(CHDSP_NOTCH_COUNT / 2);
        chdsp_notch_bank_t b; chdsp_bq_t sec[CHDSP_NOTCH_COUNT]; chdsp_bq_chain_t ch;
        int i, fixed_intact = 1;
        chdsp_bq_chain_init(&ch, sec, CHDSP_NOTCH_COUNT);
        chdsp_notch_bank_init(&b, CHDSP_NOTCH_MODE_HYBRID, NF);
        for (i = 0; i < (int)NF; i++) {
            (void)chdsp_notch_bank_set_fixed(&b, &ch, (uint16_t)i, 100.0 + i, 8.0, -6.0);
        }
        /* 猛灌:远超动态槽数 */
        for (i = 0; i < CHDSP_NOTCH_COUNT * 5; i++) {
            (void)chdsp_notch_bank_request(&b, &ch, 1000.0 + 10.0 * i, 8.0, -6.0, 0);
        }
        for (i = 0; i < (int)NF; i++) {
            if (b.slot[i].f_hz != 100.0 + i || !b.slot[i].in_use) { fixed_intact = 0; }
        }
        printf("      HYBRID(固定 %u / 动态 %u):灌 %d 次请求后 —— 固定槽完好=%d;"
               "evict=%u;可用动态槽=%u\n",
               (unsigned)NF, (unsigned)(CHDSP_NOTCH_COUNT - NF), CHDSP_NOTCH_COUNT * 5,
               fixed_intact, (unsigned)b.evict_count,
               (unsigned)chdsp_notch_bank_free_dynamic(&b));
        OKC("CHK-N3", fixed_intact == 1 && b.evict_count > 0u
                      && chdsp_notch_bank_used(&b) == (uint16_t)CHDSP_NOTCH_COUNT,
            "⭐⭐ HYBRID:固定槽在持续回收压力下**一个都没被动**(⛔ 这是 FIXED 语义的全部意义)");
    }
    {   /* CHK-N4 ⭐「重启后仍在」:复位动态槽 ⇒ 固定留、动态清 */
        const uint16_t NF = (uint16_t)(CHDSP_NOTCH_COUNT / 2);
        chdsp_notch_bank_t b; chdsp_bq_t sec[CHDSP_NOTCH_COUNT]; chdsp_bq_chain_t ch;
        int i; uint16_t used_before, used_after;
        chdsp_bq_chain_init(&ch, sec, CHDSP_NOTCH_COUNT);
        chdsp_notch_bank_init(&b, CHDSP_NOTCH_MODE_HYBRID, NF);
        for (i = 0; i < (int)NF; i++) {
            (void)chdsp_notch_bank_set_fixed(&b, &ch, (uint16_t)i, 100.0 + i, 8.0, -6.0);
        }
        for (i = 0; i < CHDSP_NOTCH_COUNT; i++) {
            (void)chdsp_notch_bank_request(&b, &ch, 2000.0 + 10.0 * i, 8.0, -6.0, 0);
        }
        used_before = chdsp_notch_bank_used(&b);
        chdsp_notch_bank_reset_dynamic(&b, &ch);
        used_after = chdsp_notch_bank_used(&b);
        printf("      复位前占用 %u ⇒ 复位动态槽后占用 %u(期望 = 固定槽数 %u)\n",
               (unsigned)used_before, (unsigned)used_after, (unsigned)NF);
        OKC("CHK-N4", used_before == (uint16_t)CHDSP_NOTCH_COUNT && used_after == NF
                      && b.slot[0].f_hz == 100.0,
            "⭐「重启后仍在」:固定槽保留、动态槽清空(⛔ 不是全清也不是全留)");
    }
    {   /* CHK-N5 ⭐ 触达证明:bank 真的驱动了滤波器链,⛔ 不只是簿记 */
        chdsp_notch_bank_t b; chdsp_bq_t sec[CHDSP_NOTCH_COUNT]; chdsp_bq_chain_t ch;
        chdsp_sat_t st; int i; double e_on = 0.0, e_off = 0.0;
        const double F = 1000.0;
        const int NS = CHDSP_FS_HZ / 10, SKIP = NS / 2;   /* ⚠ SKIP 必须 < NS,见下 */
        chdsp_bq_chain_init(&ch, sec, CHDSP_NOTCH_COUNT); chdsp_sat_reset(&st);
        chdsp_notch_bank_init(&b, CHDSP_NOTCH_MODE_DYNAMIC, 0u);
        /* 无陷波:链上 n=0 ⇒ 逐位透传 */
        for (i = 0; i < NS; i++) {
            chdsp_smp_q4_27_t x = smp_f(0.1 * sin(2.0 * M_PI * F * i / CHDSP_FS_HZ));
            chdsp_smp_q4_27_t y = x;
            chdsp_bq_chain_process(&ch, &y, &y, 1u, &st);
            if (i > SKIP) { double v = chdsp_smp_to_f64(y); e_off += v * v; }
        }
        /* 在 1 kHz 放一个 −18 dB 的陷波 ⇒ 同一激励能量必须显著下降 */
        (void)chdsp_notch_bank_request(&b, &ch, F, 8.0, -18.0, 0);
        chdsp_bq_chain_reset(&ch);
        for (i = 0; i < NS; i++) {
            chdsp_smp_q4_27_t x = smp_f(0.1 * sin(2.0 * M_PI * F * i / CHDSP_FS_HZ));
            chdsp_smp_q4_27_t y = x;
            chdsp_bq_chain_process(&ch, &y, &y, 1u, &st);
            if (i > SKIP) { double v = chdsp_smp_to_f64(y); e_on += v * v; }
        }
        printf("      1 kHz 激励:无陷波能量 %.4e;放 −18 dB 陷波后 %.4e ⇒ 衰减 %.2f dB\n",
               e_off, e_on, 10.0 * log10(e_on / (e_off + 1e-300) + 1e-300));
        /* ⭐⭐ 前提自检 —— 本条首跑时是【假绿】:窗口写成 i > 4800 而循环只到 4799
         *   ⇒ 两个能量都是 0 ⇒ 判据在 1e−300/1e−300 上通过,**什么也没测**。
         *   ⇒ 教训与 CHK-Y1c0 同族:**先量出被测量的实际值,再据此断言**。 */
        OKC("CHK-N5a", e_off > 1e-6,
            "⭐ 前提自检:无陷波时确实有能量通过(⛔ 否则下一条是在 0/0 上通过)");
        OKC("CHK-N5", e_off > 1e-6
                      && 10.0 * log10(e_on / (e_off + 1e-300) + 1e-300) < -12.0,
            "⭐ 触达证明:request() 真的改变了音频(⛔ 不只是改了个结构体字段)");
    }

    /* ================= ✳ AFC 接口:陷波器组接进 D3 真实链路(r13)================= */
    printf("\n✳ AFC 接口(陷波器组 ↔ D3 真实链路)\n");
    {   /* CHK-A1 ⭐ 触达证明:AFC 在 hook 里请求的陷波,**经真实 D3 链**作用到音频上
         * ⛔ 与 CHK-N5 的区别:N5 用的是独立 bq_chain;本条走 chdsp_in_ch_process 全链。 */
        chdsp_in_ch_t ich; chdsp_io_q0_31_t in[CHDSP_FRAME_SAMPLES];
        chdsp_smp_q4_27_t out[CHDSP_FRAME_SAMPLES];
        int k, i; double e_off = 0.0, e_on = 0.0;
        const double F = 1000.0;
        /* —— 不挂 AFC:能量应通过 —— */
        (void)chdsp_in_ch_init(&ich, g_dly_in, sizeof(g_dly_in)/sizeof(g_dly_in[0]),
                               g_look_in, sizeof(g_look_in)/sizeof(g_look_in[0]));
        for (k = 0; k < 40; k++) {
            for (i = 0; i < CHDSP_FRAME_SAMPLES; i++) {
                double t = (double)(k * CHDSP_FRAME_SAMPLES + i);
                in[i] = chdsp_io_from_raw((int32_t)(0.1 * 2147483647.0
                          * sin(2.0 * M_PI * F * t / CHDSP_FS_HZ)));
            }
            chdsp_in_ch_process(&ich, in, out, CHDSP_FRAME_SAMPLES);
            if (k >= 20) { for (i = 0; i < CHDSP_FRAME_SAMPLES; i++) {
                double v = chdsp_smp_to_f64(out[i]); e_off += v * v; } }
        }
        /* —— 挂上假 AFC:它在 hook 里请求 1 kHz −18 dB —— */
        g_fake_afc_called = 0;
        (void)chdsp_in_ch_init(&ich, g_dly_in, sizeof(g_dly_in)/sizeof(g_dly_in[0]),
                               g_look_in, sizeof(g_look_in)/sizeof(g_look_in[0]));
        chdsp_in_ch_bind_afc(&ich, fake_afc);
        for (k = 0; k < 40; k++) {
            for (i = 0; i < CHDSP_FRAME_SAMPLES; i++) {
                double t = (double)(k * CHDSP_FRAME_SAMPLES + i);
                in[i] = chdsp_io_from_raw((int32_t)(0.1 * 2147483647.0
                          * sin(2.0 * M_PI * F * t / CHDSP_FS_HZ)));
            }
            chdsp_in_ch_process(&ich, in, out, CHDSP_FRAME_SAMPLES);
            if (k >= 20) { for (i = 0; i < CHDSP_FRAME_SAMPLES; i++) {
                double v = chdsp_smp_to_f64(out[i]); e_on += v * v; } }
        }
        printf("      经真实 D3 链:无 AFC 能量 %.4e;挂 AFC(请求 −18 dB @1 kHz)后 %.4e ⇒ %.2f dB\n",
               e_off, e_on, 10.0 * log10(e_on / (e_off + 1e-300) + 1e-300));
        OKC("CHK-A1a", e_off > 1e-6 && g_fake_afc_called == 1,
            "⭐ 前提自检:无陷波时确有能量,且 AFC 回调确实被调到过");
        OKC("CHK-A1", e_off > 1e-6
                      && 10.0 * log10(e_on / (e_off + 1e-300) + 1e-300) < -12.0,
            "⭐ AFC 经 hook 请求的陷波**在真实 D3 链上生效**(⛔ 不是只改了簿记)");
    }
    {   /* CHK-A2 ⭐ FIXED 模式下,AFC 的请求经真实链路仍被拒,且固定陷波不动 */
        chdsp_in_ch_t ich; int r_set, r_req;
        (void)chdsp_in_ch_init(&ich, g_dly_in, sizeof(g_dly_in)/sizeof(g_dly_in[0]),
                               g_look_in, sizeof(g_look_in)/sizeof(g_look_in[0]));
        chdsp_in_ch_notch_set_mode(&ich, CHDSP_NOTCH_MODE_FIXED, 0u);
        r_set = chdsp_in_ch_notch_set_fixed(&ich, 0u, 120.0, 8.0, -6.0);
        r_req = chdsp_in_ch_notch_request(&ich, 3000.0, 8.0, -6.0, 0);
        printf("      FIXED:装机写固定陷波=%d(期 0);AFC 请求=%d(期 %d);槽 0 的 f=%.0f\n",
               r_set, r_req, CHDSP_NOTCH_ERR_NO_SLOT, ich.notch_bank.slot[0].f_hz);
        OKC("CHK-A2", r_set == CHDSP_NOTCH_OK && r_req == CHDSP_NOTCH_ERR_NO_SLOT
                      && ich.notch_bank.slot[0].f_hz == 120.0,
            "⭐ FIXED:AFC 经真实接口的请求被拒,装机陷波原封不动");
    }
    {   /* CHK-A3 ⭐⭐ 「同块生效」:AFC 在 hook 里请求的陷波,**本块就要作用到本块的输出上**
         * ⇒ 若 hook_afc 被挪到陷波之后,第 0 块会是【未加陷波】的,从下一块才开始生效。
         * ⚠ 我первый版把这条写成 `OKC("CHK-A3", 1, ...)` 占位 —— 那是"输出行不是检查",
         *   正是我这几轮一直在删的东西。⇒ 改成**只看第 0 块**的行为判据。 */
        chdsp_in_ch_t ich; chdsp_io_q0_31_t in[CHDSP_FRAME_SAMPLES];
        chdsp_smp_q4_27_t out[CHDSP_FRAME_SAMPLES];
        int i; double e0_plain = 0.0, e0_afc = 0.0;
        const double F = 1000.0;
        for (i = 0; i < CHDSP_FRAME_SAMPLES; i++) {
            in[i] = chdsp_io_from_raw((int32_t)(0.1 * 2147483647.0
                      * sin(2.0 * M_PI * F * i / CHDSP_FS_HZ)));
        }
        (void)chdsp_in_ch_init(&ich, g_dly_in, sizeof(g_dly_in)/sizeof(g_dly_in[0]),
                               g_look_in, sizeof(g_look_in)/sizeof(g_look_in[0]));
        chdsp_in_ch_process(&ich, in, out, CHDSP_FRAME_SAMPLES);
        for (i = 0; i < CHDSP_FRAME_SAMPLES; i++)
            { double v = chdsp_smp_to_f64(out[i]); e0_plain += v * v; }
        g_fake_afc_called = 0;
        (void)chdsp_in_ch_init(&ich, g_dly_in, sizeof(g_dly_in)/sizeof(g_dly_in[0]),
                               g_look_in, sizeof(g_look_in)/sizeof(g_look_in[0]));
        chdsp_in_ch_bind_afc(&ich, fake_afc);
        chdsp_in_ch_process(&ich, in, out, CHDSP_FRAME_SAMPLES);
        for (i = 0; i < CHDSP_FRAME_SAMPLES; i++)
            { double v = chdsp_smp_to_f64(out[i]); e0_afc += v * v; }
        printf("      **第 0 块**:无 AFC %.4e;挂 AFC %.4e ⇒ 差 %.2f dB(同块生效则应显著为负)\n",
               e0_plain, e0_afc, 10.0 * log10(e0_afc / (e0_plain + 1e-300) + 1e-300));
        /* ⚠ 判据取 −0.5 dB,理由是**先量出分辨力再定判据**(不是拍的):
         *   第 0 块滤波器尚未稳态 ⇒ 好版本只到 **−1.64 dB**(不是稳态的 −18);
         *   而坏版本(hook 在陷波之后)第 0 块**逐位不变 ⇒ 恰好 0.00 dB**。
         *   ⇒ 两者相距 1.64 dB,取 −0.5 留双边余量。⛔ 我首版拍了 −3.0,好版本自己过不去。 */
        OKC("CHK-A3", e0_plain > 1e-9
                      && 10.0 * log10(e0_afc / (e0_plain + 1e-300) + 1e-300) < -0.5,
            "⭐ 同块生效:AFC 本块请求的陷波作用在**本块**输出上(⛔ hook 若在陷波之后,第 0 块不受影响)");
    }

    /* ================= m-6 接线审计的机械形式 ================= */
    printf("\n接线(critic m-6 · D6-ao)\n");
    {   /* CHK-M6a ⭐ `CHDSP_COEF_ABS_MAX_INT` 现在**真的**是拦截依据,不是碰巧
         * 原先只靠 f64_to_fixed 的 int32 边界,而 16·2^27 = 2^31 恰好越过 INT32_MAX
         * ⇒ §3.4「对 |x| ≥ 16 返回非 0」是**碰巧成立**,那个常数零消费者。 */
        chdsp_coef_q4_27_t c;
        int lo = chdsp_coef_from_f64(15.9999999, &c);      /* 界内 */
        int at = chdsp_coef_from_f64(16.0, &c);            /* 恰好在界上 ⇒ 须拒 */
        int hi = chdsp_coef_from_f64(16.0000001, &c);      /* 界外 */
        int ng = chdsp_coef_from_f64(-16.0, &c);           /* 负向同样 */
        printf("      15.9999999→%d(期 0) 16.0→%d(期 −1) 16.0000001→%d(期 −1) −16.0→%d(期 −1)\n",
               lo, at, hi, ng);
        OKC("CHK-M6a", lo == 0 && at == -1 && hi == -1 && ng == -1,
            "⭐ |x| < CHDSP_COEF_ABS_MAX_INT 是**显式**判据(⛔ 不再靠 int32 边界碰巧等价)");
    }
    {   /* CHK-M6b ⭐ C-B 接线:链内饱和被记到遥测上(⛔ 不是"定义了个字段") */
        chdsp_in_ch_t ich; chdsp_biquad_coef_t pc;
        chdsp_io_q0_31_t in[CHDSP_FRAME_SAMPLES];
        chdsp_smp_q4_27_t out[CHDSP_FRAME_SAMPLES];
        int i; uint32_t sat_hot, sat_cold;
        /* —— 阳性:满量程 + 最大 trim + 一段 +15 dB PEQ ⇒ 必然越过 Q4.27 的 ±16 —— */
        (void)chdsp_in_ch_init(&ich, g_dly_in, sizeof(g_dly_in)/sizeof(g_dly_in[0]),
                               g_look_in, sizeof(g_look_in)/sizeof(g_look_in[0]));
        ich.trim = chdsp_db_to_gain(chdsp_db(24));
        (void)chdsp_bq_design(CHDSP_FT_PEAKING, 1000.0, 1.0, 15.0, &pc);
        ich.peq.n = 1u; chdsp_bq_set_coef_now(&ich.peq_sec[0], &pc); ich.peq_sec[0].bypass = 0u;
        for (i = 0; i < CHDSP_FRAME_SAMPLES; i++) {
            in[i] = chdsp_io_from_raw((int32_t)(2147483647.0 *
                        sin(2.0 * M_PI * 1000.0 * i / CHDSP_FS_HZ)));
        }
        chdsp_in_ch_process(&ich, in, out, CHDSP_FRAME_SAMPLES);
        sat_hot = chdsp_in_ch_internal_sat_frames(&ich);
        /* —— 阴性:同一条链,标称 −20 dBFS、单位增益、无提升 —— */
        (void)chdsp_in_ch_init(&ich, g_dly_in, sizeof(g_dly_in)/sizeof(g_dly_in[0]),
                               g_look_in, sizeof(g_look_in)/sizeof(g_look_in[0]));
        for (i = 0; i < CHDSP_FRAME_SAMPLES; i++) {
            in[i] = chdsp_io_from_raw((int32_t)(0.1 * 2147483647.0 *
                        sin(2.0 * M_PI * 1000.0 * i / CHDSP_FS_HZ)));
        }
        chdsp_in_ch_process(&ich, in, out, CHDSP_FRAME_SAMPLES);
        sat_cold = chdsp_in_ch_internal_sat_frames(&ich);
        printf("      满量程+24dB trim+15dB PEQ ⇒ 链内饱和帧 %u;标称 −20 dBFS 单位增益 ⇒ %u\n",
               (unsigned)sat_hot, (unsigned)sat_cold);
        OKC("CHK-M6b", sat_hot > 0u && sat_cold == 0u,
            "⭐ C-B 真的接上了:链内饱和被记录,而正常工作点下恒 0(⛔ 两个方向都测)");
    }

    /* ================= C 第二批(r8):分频补全 ================= */
    printf("\n分频补全(C 第二批 r8:奇数阶 + Bessel)\n");
    {   /* CHK-X1 ⭐ Y7 闭合:Bessel 全族系数装得进 Q4.27
         * ⛔ 顺序纪律:先扫界(EXP-9)后实现。本条是那个扫描结论的**机械形式**。 */
        chdsp_biquad_coef_t sec[CHDSP_OUT_XO_SECTIONS];
        uint16_t n; int order, hp, i, bad = 0, worst_raw = 0;
        for (order = 1; order <= 8; order++) {
            for (hp = 0; hp < 2; hp++) {
                int e = chdsp_bq_design_xover2(CHDSP_XO_BESSEL, order, hp, 1000.0, sec, &n);
                if (e != CHDSP_BQ_OK) { bad++; continue; }
                for (i = 0; i < (int)n; i++) {
                    int32_t r[3]; int j;
                    r[0] = chdsp_coef_raw(sec[i].b0); r[1] = chdsp_coef_raw(sec[i].b1);
                    r[2] = chdsp_coef_raw(sec[i].b2);
                    for (j = 0; j < 3; j++) {
                        int32_t a = r[j] < 0 ? -r[j] : r[j];
                        if (a > worst_raw) { worst_raw = a; }
                    }
                }
            }
        }
        /* ⚠ ⛔ 判据写法留痕:初版写 `worst_raw < (16 << CHDSP_COEF_FRACBITS)`,
         *   而 16<<27 = 2³¹ **溢出 int32** ⇒ 常量变成 −2147483648 ⇒ 判据恒假。
         *   ⇒ 「Q4.27 的上界」在 raw 域**根本表示不出来**(|c|<16 ⟺ raw ≤ INT32_MAX)。
         *   ⇒ 这与本项目「界的种类」那条同族:先问这个界在**这个类型里**存不存在。 */
        printf("      Bessel 1..8 阶 × LP/HP:设计失败 %d 次;max|b| = %.6f(Q4.27 上限 16)\n",
               bad, (double)worst_raw / (double)(1 << CHDSP_COEF_FRACBITS));
        OKC("CHK-X1", bad == 0
                      && (double)worst_raw / (double)(1 << CHDSP_COEF_FRACBITS) <= 2.0,
            "⭐ Y7 闭合:Bessel 全族 max|b| ≤ 2 ⇒ 装得进 Q4.27(EXP-9 解析预测兑现)");
    }
    {   /* CHK-X2 ⭐ 两轨:C 的 Bessel 响应 vs python 轨(xover_r8.py,scipy 交叉核过)
         * ⛔ 参考值是**独立轨算出来的**,不是从本实现回读的。 */
        static const double FQ[5]  = { 100.0, 500.0, 1000.0, 2000.0, 8000.0 };
        static const double REF_LP[5] = { -0.027664, -0.703579, -3.010300, -13.513101, -61.304440 };
        static const double REF_HP[5] = { -65.731200, -13.432177, -3.010300, -0.698961, -0.035760 };
        chdsp_biquad_coef_t sec[CHDSP_OUT_XO_SECTIONS];
        uint16_t n; int hp, i, k; double worst = 0.0;
        for (hp = 0; hp < 2; hp++) {
            if (chdsp_bq_design_xover2(CHDSP_XO_BESSEL, 4, hp, 1000.0, sec, &n) != CHDSP_BQ_OK) {
                worst = 999.0; break;
            }
            for (k = 0; k < 5; k++) {
                double w = 2.0 * M_PI * FQ[k] / (double)CHDSP_FS_HZ, mag = 1.0, d;
                for (i = 0; i < (int)n; i++) {
                    double br = 0.0, bi = 0.0, ar = 1.0, ai = 0.0, cw, sw;
                    int t;
                    double bc[3], ac[3];
                    bc[0] = chdsp_coef_to_f64(sec[i].b0); bc[1] = chdsp_coef_to_f64(sec[i].b1);
                    bc[2] = chdsp_coef_to_f64(sec[i].b2);
                    ac[0] = 1.0; ac[1] = chdsp_coef_to_f64(sec[i].a1);
                    ac[2] = chdsp_coef_to_f64(sec[i].a2);
                    br = bi = 0.0; ar = ai = 0.0;
                    for (t = 0; t < 3; t++) {
                        cw = cos(-w * t); sw = sin(-w * t);
                        br += bc[t] * cw; bi += bc[t] * sw;
                        ar += ac[t] * cw; ai += ac[t] * sw;
                    }
                    mag *= sqrt((br * br + bi * bi) / (ar * ar + ai * ai));
                }
                d = fabs(20.0 * log10(mag) - (hp ? REF_HP[k] : REF_LP[k]));
                if (d > worst) { worst = d; }
            }
        }
        printf("      Bessel4 @fc=1k,5 个频点 × LP/HP:与 python 轨 max|Δ| = %.6f dB\n", worst);
        OKC("CHK-X2", worst <= 0.02,
            "⭐ 两轨:C 的 Bessel 与独立 python 轨(已与 scipy 逐点核过)一致 ≤0.02 dB");
    }
    {   /* CHK-X3 ⭐⭐ butter_q 的 sin/cos 之别 —— 这一条守的是【奇数阶】
         * 偶数阶下 sin 式与 cos 式给出**同一个 Q 集合**(顺序相反)⇒ 旧代码当时是对的;
         * 奇数阶下不等(n=3:cos 式 0.5774,正确 1.0)。
         * ⇒ 本条直接测 3 阶 BW 的响应,cos 式会当场翻红。 */
        static const double FQ[5]  = { 100.0, 500.0, 1000.0, 2000.0, 8000.0 };
        static const double REF[5] = { -0.000004, -0.066905, -3.010300, -18.239613, -56.694609 };
        chdsp_biquad_coef_t sec[CHDSP_OUT_XO_SECTIONS];
        uint16_t n; int i, k; double worst = 0.0;
        if (chdsp_bq_design_xover2(CHDSP_XO_BUTTERWORTH, 3, 0, 1000.0, sec, &n) != CHDSP_BQ_OK) {
            worst = 999.0;
        } else {
            for (k = 0; k < 5; k++) {
                double w = 2.0 * M_PI * FQ[k] / (double)CHDSP_FS_HZ, mag = 1.0, d;
                for (i = 0; i < (int)n; i++) {
                    double bc[3], ac[3], br = 0.0, bi = 0.0, ar = 0.0, ai = 0.0;
                    int t;
                    bc[0] = chdsp_coef_to_f64(sec[i].b0); bc[1] = chdsp_coef_to_f64(sec[i].b1);
                    bc[2] = chdsp_coef_to_f64(sec[i].b2);
                    ac[0] = 1.0; ac[1] = chdsp_coef_to_f64(sec[i].a1);
                    ac[2] = chdsp_coef_to_f64(sec[i].a2);
                    for (t = 0; t < 3; t++) {
                        double cw = cos(-w * t), sw = sin(-w * t);
                        br += bc[t] * cw; bi += bc[t] * sw;
                        ar += ac[t] * cw; ai += ac[t] * sw;
                    }
                    mag *= sqrt((br * br + bi * bi) / (ar * ar + ai * ai));
                }
                d = fabs(20.0 * log10(mag) - REF[k]);
                if (d > worst) { worst = d; }
            }
        }
        printf("      BW3(奇数阶,含一阶节)LP:节数 %u,与 python 轨 max|Δ| = %.6f dB\n",
               (unsigned)n, worst);
        OKC("CHK-X3", n == 2u && worst <= 0.02,
            "⭐ 奇数阶 BW 正确(守的是 butter_q 用 sin;cos 式在此处会翻红)");
    }
    {   /* CHK-X4 F-4 回归:偶数阶必须与改动前**逐位相同**
         * 做法:sin 式与 cos 式各自设计,断言两者产出的系数【集合】逐位相同。
         * ⇒ 这就是「butter_q 从 cos 改 sin 没有动偶数阶」的机械证明。 */
        chdsp_biquad_coef_t a[CHDSP_OUT_XO_SECTIONS], b[CHDSP_OUT_XO_SECTIONS];
        uint16_t na, nb; int order, hp, bad = 0;
        for (order = 2; order <= 8; order += 2) {
            for (hp = 0; hp < 2; hp++) {
                int i, j, matched = 0;
                if (chdsp_bq_design_xover2(CHDSP_XO_BUTTERWORTH, order, hp, 1234.0, a, &na)
                    != CHDSP_BQ_OK) { bad++; continue; }
                /* 用 cos 式重建同一组 Q(即旧实现),逐节设计 */
                nb = 0u;
                for (i = 0; i < order / 2; i++) {
                    double q = 1.0 / (2.0 * cos(M_PI * (2.0 * i + 1.0) / (2.0 * order)));
                    if (chdsp_bq_design(hp ? CHDSP_FT_HPF : CHDSP_FT_LPF, 1234.0, q, 0.0, &b[nb])
                        != CHDSP_BQ_OK) { bad++; }
                    nb++;
                }
                if (na != nb) { bad++; continue; }
                /* ⭐ **多重集**比对:每个 b 只能被配掉一次(⛔ 不是"每个 a 找到某个 b")
                 * 〔整改 2026-08-05:原写法在 a 有重复元素时会用同一个 b 配多次
                 *   ⇒ a={Q1,Q1} 与 b={Q1,Q2} 会被判为"全部匹配" ⇒ 本条比它声称的弱。
                 *   是写 CHDSP_BROKEN_BUTTER_KOFF 变异时发现的:butter_q 的 k 偏一位
                 *   使偶数阶 Q 集合退化成两个相同值,而本条**没有变红**。〕 */
                { int used[CHDSP_OUT_XO_SECTIONS]; int u;
                  for (u = 0; u < (int)nb; u++) { used[u] = 0; }
                  for (i = 0; i < (int)na; i++) {
                    for (j = 0; j < (int)nb; j++) {
                        if (used[j]) { continue; }
                        if (chdsp_coef_raw(a[i].b0) == chdsp_coef_raw(b[j].b0) &&
                            chdsp_coef_raw(a[i].b1) == chdsp_coef_raw(b[j].b1) &&
                            chdsp_coef_raw(a[i].b2) == chdsp_coef_raw(b[j].b2) &&
                            chdsp_coef_raw(a[i].a1) == chdsp_coef_raw(b[j].a1) &&
                            chdsp_coef_raw(a[i].a2) == chdsp_coef_raw(b[j].a2)) {
                            used[j] = 1; matched++; break; }
                    }
                  } }
                if (matched != (int)na) { bad++; }
            }
        }
        printf("      偶数阶 BW 2/4/6/8 × LP/HP:sin 式 vs cos 式系数集合不匹配 %d 处\n", bad);
        OKC("CHK-X4", bad == 0,
            "⭐ F-4 回归:butter_q 改 sin **没有动偶数阶**(逐位同集合)");
    }
    {   /* CHK-X5 LR 奇数阶必须被拒(LR = BW²,奇数阶数学上不存在,这不是缺口) */
        chdsp_biquad_coef_t sec[CHDSP_OUT_XO_SECTIONS]; uint16_t n;
        int e3 = chdsp_bq_design_xover2(CHDSP_XO_LINKWITZ_RILEY, 3, 0, 1000.0, sec, &n);
        int e4 = chdsp_bq_design_xover2(CHDSP_XO_LINKWITZ_RILEY, 4, 0, 1000.0, sec, &n);
        int e9 = chdsp_bq_design_xover2(CHDSP_XO_BESSEL, 9, 0, 1000.0, sec, &n);
        printf("      LR3=%d(期 %d) LR4=%d(期 %d) Bessel9=%d(期 %d)\n",
               e3, CHDSP_BQ_ERR_ORDER, e4, CHDSP_BQ_OK, e9, CHDSP_BQ_ERR_ORDER);
        OKC("CHK-X5", e3 == CHDSP_BQ_ERR_ORDER && e4 == CHDSP_BQ_OK && e9 == CHDSP_BQ_ERR_ORDER,
            "各自返回【它自己那条】错误码(⛔ 不是「非 0 即算过」)");
    }
    {   /* CHK-X6 ⭐ 一阶节 max|b| ≤ 1(EXP-9b 的机械形式) */
        chdsp_biquad_coef_t c; int i, hp, bad = 0; int32_t worst = 0;
        for (i = 0; i < 300; i++) {
            double fc = 20.0 * pow(1000.0, (double)i / 299.0);
            for (hp = 0; hp < 2; hp++) {
                int32_t r[3]; int j;
                if (chdsp_bq_design_first_order(hp, fc, &c) != CHDSP_BQ_OK) { bad++; continue; }
                r[0] = chdsp_coef_raw(c.b0); r[1] = chdsp_coef_raw(c.b1); r[2] = chdsp_coef_raw(c.b2);
                for (j = 0; j < 3; j++) {
                    int32_t v = r[j] < 0 ? -r[j] : r[j];
                    if (v > worst) { worst = v; }
                }
            }
        }
        printf("      一阶节 300 个 fc × LP/HP:失败 %d;max|b| raw = %d(1.0 = %d)\n",
               bad, worst, 1 << CHDSP_COEF_FRACBITS);
        OKC("CHK-X6", bad == 0 && worst <= (1 << CHDSP_COEF_FRACBITS),
            "一阶节 max|b| ≤ 1 ⇒ Q4.27 装得下,不需额外包络检查");
    }

    printf("\n================================================================\n");
    printf("合计: PASS=%d  FAIL=%d\n", g_pass, g_fail);
    printf("  其中 %d 条标为【已知零分辨力·保留为回归项】(critic MAJOR-4)\n", g_regress);
    printf("  ⛔ 这 %d 条【不构成】对它们名字里那件事的证据 —— 各自的分辨力在被指名的替代条上。\n",
           g_regress);
    printf("  ⇒ 有效判据数 = %d\n", g_pass - g_regress);
    printf("退出码 = %d  ⇒ **本文件的每条检查都是硬闸门**\n", g_fail ? 1 : 0);
    printf("================================================================\n");
    return g_fail ? 1 : 0;
}
