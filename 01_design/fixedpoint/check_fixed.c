/**
 * @file    check_fixed.c
 * @brief   chdsp_fixed.h 的自验(第一轨)。按 PREREG_FP_r1.txt 逐条执行。
 *
 * ⛔ 门禁状态:未过门。
 *
 * ⚠ 自验纪律(团队立法):本文件**必须 include 并调用被测头文件的函数**,
 *   ⛔ 禁止转写它的公式。检查法:本文件的 #include 里必须有 chdsp_fixed.h,
 *   且所有定点算术只能经 chdsp_* 函数发生。
 *   参照轨(long double 递归)是**独立方法**,不是被测公式的转写:
 *   它算的是「同样量化系数下的无限精度结果」,与定点实现无共用代码。
 */

#include "chdsp_fixed.h"
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>

/* CHDSP_CHECK_FORCE_GOOD_ASSERT=1 时,断言一律用【好版本】的判据,不随 BROKEN 宏变。
 * ⇒ 这才是杀伤矩阵要的证据:同一份检查代码跑在坏模块上,看它会不会 FAIL。
 * (默认 0:断言随构建自适应,用于观察坏版本的缺陷形态) */
#ifndef CHDSP_CHECK_FORCE_GOOD_ASSERT
#  define CHDSP_CHECK_FORCE_GOOD_ASSERT 0
#endif
#if CHDSP_CHECK_FORCE_GOOD_ASSERT
#  define GOOD_ASSERT 1
#else
#  define GOOD_ASSERT 0
#endif

static int g_fail = 0;
static int g_pass = 0;
static int g_retired = 0;
static void REPORT(const char *tag, int ok, const char *msg)
{
    if (ok) { g_pass++; } else { g_fail++; }
    printf("  [%s] %-7s %s\n", ok ? "PASS" : "FAIL", tag, msg);
}
#define OK(tag, cond, msg) REPORT(tag, (cond) ? 1 : 0, msg)
/* 已退役的检查:保留记录(E-2「加标注不删数」),但不计入判定。 */
static void RETIRED(const char *tag, int ok, const char *msg)
{ g_retired++; printf("  [%s] %-7s %s\n", ok ? "退役·符合" : "退役·不符", tag, msg); }

/* ---------------- 确定性 PRNG(xorshift,跨平台可复现) ---------------- */
static uint32_t g_rng = 0x13579BDFu;
static uint32_t rnd32(void)
{ g_rng ^= g_rng << 13; g_rng ^= g_rng >> 17; g_rng ^= g_rng << 5; return g_rng; }
/* 近似高斯:12 个均匀求和 − 6 */
static double rndn(void)
{ double s = 0.0; int i; for (i = 0; i < 12; i++) { s += (double)rnd32() / 4294967296.0; } return s - 6.0; }

/* ---------------- RBJ 设计(设计期,double,非实时路径) ---------------- */
#define FS 48000.0
typedef struct { double b0,b1,b2,a1,a2; } bq_f64;

static bq_f64 rbj_peaking(double f0, double Q, double gdb)
{
    double A = pow(10.0, gdb/40.0), w0 = 2.0*M_PI*f0/FS;
    double al = sin(w0)/(2.0*Q), c = cos(w0), a0 = 1.0 + al/A;
    bq_f64 r; r.b0=(1.0+al*A)/a0; r.b1=(-2.0*c)/a0; r.b2=(1.0-al*A)/a0;
    r.a1=(-2.0*c)/a0; r.a2=(1.0-al/A)/a0; return r;
}
static bq_f64 rbj_hpf(double f0, double Q)
{
    double w0 = 2.0*M_PI*f0/FS, al = sin(w0)/(2.0*Q), c = cos(w0), a0 = 1.0 + al;
    bq_f64 r; r.b0=((1.0+c)/2.0)/a0; r.b1=(-(1.0+c))/a0; r.b2=((1.0+c)/2.0)/a0;
    r.a1=(-2.0*c)/a0; r.a2=(1.0-al)/a0; return r;
}
static bq_f64 rbj_lpf(double f0, double Q)
{
    double w0 = 2.0*M_PI*f0/FS, al = sin(w0)/(2.0*Q), c = cos(w0), a0 = 1.0 + al;
    bq_f64 r; r.b0=((1.0-c)/2.0)/a0; r.b1=(1.0-c)/a0; r.b2=((1.0-c)/2.0)/a0;
    r.a1=(-2.0*c)/a0; r.a2=(1.0-al)/a0; return r;
}
static bq_f64 rbj_lowshelf(double f0, double S, double gdb)
{
    double A = pow(10.0, gdb/40.0), w0 = 2.0*M_PI*f0/FS;
    double al = sin(w0)/2.0*sqrt((A+1.0/A)*(1.0/S-1.0)+2.0), c = cos(w0), t = 2.0*sqrt(A)*al;
    double a0 = (A+1.0)+(A-1.0)*c+t;
    bq_f64 r; r.b0=A*((A+1.0)-(A-1.0)*c+t)/a0; r.b1=2.0*A*((A-1.0)-(A+1.0)*c)/a0;
    r.b2=A*((A+1.0)-(A-1.0)*c-t)/a0; r.a1=-2.0*((A-1.0)+(A+1.0)*c)/a0;
    r.a2=((A+1.0)+(A-1.0)*c-t)/a0; return r;
}

static int to_fixed_bq(bq_f64 d, chdsp_biquad_coef_t *out)
{
    int e = 0;
    e |= chdsp_coef_from_f64(d.b0, &out->b0);
    e |= chdsp_coef_from_f64(d.b1, &out->b1);
    e |= chdsp_coef_from_f64(d.b2, &out->b2);
    e |= chdsp_coef_from_f64(d.a1, &out->a1);
    e |= chdsp_coef_from_f64(d.a2, &out->a2);
    return e;
}
/* 把定点系数读回 double(= 实际生效的系数),供参照轨用 */
static void fixed_bq_to_f64(const chdsp_biquad_coef_t *c, bq_f64 *d)
{
    d->b0 = chdsp_coef_to_f64(c->b0); d->b1 = chdsp_coef_to_f64(c->b1);
    d->b2 = chdsp_coef_to_f64(c->b2); d->a1 = chdsp_coef_to_f64(c->a1);
    d->a2 = chdsp_coef_to_f64(c->a2);
}

/* 参照轨:long double DF1 递归(独立于定点实现) */
typedef struct { long double x1,x2,y1,y2; } ref_state;
static long double ref_df1(const bq_f64 *c, ref_state *s, long double x)
{
    long double y = (long double)c->b0*x + (long double)c->b1*s->x1 + (long double)c->b2*s->x2
                  - (long double)c->a1*s->y1 - (long double)c->a2*s->y2;
    s->x2 = s->x1; s->x1 = x; s->y2 = s->y1; s->y1 = y;
    return y;
}

/* 解析噪声增益 NG = Σ|h_{1/A}|² */
static double ng_1overA(const bq_f64 *c)
{
    double y1 = 0.0, y2 = 0.0, s = 0.0; int i;
    for (i = 0; i < 400000; i++) {
        double x = (i == 0) ? 1.0 : 0.0;
        double y = x - c->a1*y1 - c->a2*y2;
        s += y*y; y2 = y1; y1 = y;
    }
    return s;
}

/* ====================================================================== */
int main(void)
{
    printf("================================================================\n");
    printf("check_fixed  —  chdsp_fixed.h 自验(第一轨)\n");
    printf("  构建开关: STRICT_TYPES=%d  BROKEN_WRAP=%d  BROKEN_TRUNC=%d  BROKEN_NOEF=%d\n",
           CHDSP_STRICT_TYPES, CHDSP_BROKEN_WRAP, CHDSP_BROKEN_TRUNC, CHDSP_BROKEN_NOEF);
    printf("  格式: IO=Q0.%d  SMP=Q4.%d  COEF=Q4.%d  余量=%d bit (%.4f dB)\n",
           CHDSP_IO_FRACBITS, CHDSP_SMP_FRACBITS, CHDSP_COEF_FRACBITS,
           CHDSP_HEADROOM_BITS, CHDSP_HEADROOM_BITS * 6.020599913);
    printf("================================================================\n\n");

    /* ---------------- CHK-0 ---------------- */
    printf("CHK-0  出货构建的坏版本开关\n");
    OK("CHK-0", (CHDSP_BROKEN_WRAP==0 && CHDSP_BROKEN_TRUNC==0 && CHDSP_BROKEN_NOEF==0),
       "三个 BROKEN 宏全为 0(若本行 FAIL,本轮结果只作坏版本对照用)");
    printf("\n");

    /* ---------------- CHK-1 饱和 vs 回绕 ---------------- */
    printf("CHK-1  饱和 vs 回绕\n");
    {
        chdsp_sat_t st; chdsp_sat_reset(&st);
        chdsp_smp_q4_27_t big = chdsp_smp_from_raw(0x7FFFFFF0);   /* ≈ +16(链内满量程附近) */
        chdsp_io_q0_31_t  out = chdsp_smp_to_io(big, &st);
        printf("      chdsp_smp_to_io(0x7FFFFFF0) = %d (0x%08X), sat_sticky=%u\n",
               chdsp_io_raw(out), (unsigned)chdsp_io_raw(out), (unsigned)st.sat_sticky);
#if CHDSP_BROKEN_WRAP && !CHDSP_CHECK_FORCE_GOOD_ASSERT
        OK("CHK-1", chdsp_io_raw(out) < 0, "坏版本(WRAP):确实发生符号翻转 ⇒ 该缺陷可被观测");
#else
        OK("CHK-1", chdsp_io_raw(out) == INT32_MAX && st.sat_sticky == 1u,
           "好判据:钳到 INT32_MAX 且粘滞位置起");
#endif
        /* 负向 */
        chdsp_sat_reset(&st);
        out = chdsp_smp_to_io(chdsp_smp_from_raw((int32_t)0x80000010), &st);
        printf("      chdsp_smp_to_io(0x80000010) = %d, sat_sticky=%u\n",
               chdsp_io_raw(out), (unsigned)st.sat_sticky);
#if !CHDSP_BROKEN_WRAP || CHDSP_CHECK_FORCE_GOOD_ASSERT
        OK("CHK-1n", chdsp_io_raw(out) == INT32_MIN && st.sat_sticky == 1u, "负向同样钳位");
#else
        OK("CHK-1n", chdsp_io_raw(out) > 0, "坏版本负向翻正");
#endif
        /* 未溢出时不得置位(护栏的另一个方向:它会不会挡掉对的?) */
        chdsp_sat_reset(&st);
        out = chdsp_smp_to_io(chdsp_smp_from_raw(1000000), &st);
        OK("CHK-1z", st.sat_sticky == 0u, "未溢出输入不置粘滞位(护栏不误报)");
    }
    printf("\n");

    /* ---------------- CHK-3 累加器位宽(先做,CHK-2 要用 EF 状态) ---------------- */
    printf("CHK-3  累加器【类型范围上界】(a):构造使 int64 溢出的合法输入\n");
    {
        chdsp_acc_t acc; chdsp_acc_clear(&acc);
        chdsp_smp_q4_27_t x = chdsp_smp_from_raw(INT32_MAX);      /* ≈ +16 */
        chdsp_coef_q4_27_t c = chdsp_coef_from_raw(INT32_MAX);    /* ≈ +16 */
        int i;
        for (i = 0; i < 7; i++) { chdsp_acc_mac(&acc, x, c); }    /* DF1+EF 一节最多 7 项 */
        {
            chdsp_acc_raw_t v = CHDSP_RAW(acc);
            double lg = log2((double)v);
            printf("      7 × (INT32_MAX × INT32_MAX) 的 log2 = %.3f  (int64 上限 = 63)\n", lg);
            OK("CHK-3", lg > 63.0, "类型范围上界(a)超过 int64 ⇒ 累加器须 >=66 bit;⚠ 这是【上界】不是【实测占用】,实测见 CHK-11");
            OK("CHK-3r", chdsp_acc_in_range(acc) == 0, "仍在声明的 66-bit 安全域内");
        }
    }
    printf("\n");

    /* ---------------- CHK-6 I/O 往返 ---------------- */
    printf("CHK-6  I/O 往返无损(24-bit 左对齐样本)\n");
    {
        int bad = 0, n = 0, i;
        chdsp_sat_t st; chdsp_sat_reset(&st);
        for (i = 0; i < 200000; i++) {
            int32_t raw = (int32_t)(rnd32() & 0xFFFFFF00u);       /* 低 8 bit 清零 = 24-bit */
            chdsp_io_q0_31_t a = chdsp_io_from_raw(raw);
            chdsp_io_q0_31_t b = chdsp_smp_to_io(chdsp_io_to_smp(a), &st);
            n++;
            if (chdsp_io_raw(b) != raw) { bad++; }
        }
        printf("      样本数 %d,不等 %d,sat_sticky=%u\n", n, bad, (unsigned)st.sat_sticky);
        OK("CHK-6", bad == 0 && st.sat_sticky == 0u, "24-bit 输入经 Q4.27 往返逐位无损");
        /* 反向:低 8 bit 非 0 的输入【应当】有损,证明这条测的是真东西 */
        {
            chdsp_io_q0_31_t a = chdsp_io_from_raw(0x0000000F);
            chdsp_io_q0_31_t b = chdsp_smp_to_io(chdsp_io_to_smp(a), &st);
            OK("CHK-6n", chdsp_io_raw(b) != 0x0000000F,
               "低 8 bit 非 0(超 24-bit)确实有损 ⇒ CHK-6 不是恒真");
        }
    }
    printf("\n");

    /* ---------------- CHK-8 系数范围硬失败 ---------------- */
    printf("CHK-8  系数范围硬失败\n");
    {
        chdsp_coef_q4_27_t c;
        int r_in  = chdsp_coef_from_f64(11.2148, &c);
        int r_out = chdsp_coef_from_f64(16.0, &c);
        int r_out2= chdsp_coef_from_f64(-17.5, &c);
        int r_neg = chdsp_coef_from_f64(-11.2148, &c);
        printf("      f64→coef: 11.2148→%d  −11.2148→%d  16.0→%d  −17.5→%d  (0=成功)\n",
               r_in, r_neg, r_out, r_out2);
        OK("CHK-8", r_in == 0 && r_neg == 0 && r_out != 0 && r_out2 != 0,
           "界内成功、超界硬失败(不静默接受)");
    }
    printf("\n");

    /* ---------------- CHK-7 dB → 线性 ---------------- */
    printf("CHK-7  dB → 线性:精度与单调\n");
    {
        int32_t q; double worst_in = 0.0, worst_all = 0.0; int32_t worst_in_at = 0;
        int mono_bad = 0; int32_t prev = -1;
        chdsp_gain_q4_27_t g;
        int32_t lo = CHDSP_DB_MUTE_Q8, hi = CHDSP_DB_MAX_Q8;
        for (q = lo; q <= hi; q++) {
            g = chdsp_db_to_gain(chdsp_db_from_raw(q));
            {
                int32_t raw = chdsp_gain_raw(g);
                if (raw < prev) { mono_bad++; }
                prev = raw;
                if (q > lo) {
                    double exact = pow(10.0, (double)q / 256.0 / 20.0);
                    double got   = chdsp_gain_to_f64(g);
                    double e = (got > 0.0) ? fabs(20.0*log10(got/exact)) : 999.0;
                    if (e > worst_all) { worst_all = e; }
                    if (q >= -110*256 && e > worst_in) { worst_in = e; worst_in_at = q; }
                }
            }
        }
        printf("      扫描 %d 点(步进 1/256 dB)\n", hi - lo + 1);
        printf("      max|误差|  dB∈[−110,+24] = %.6f dB  @ %.3f dB\n", worst_in, worst_in_at/256.0);
        printf("      max|误差|  全域[−144,+24] = %.6f dB\n", worst_all);
        printf("      单调下降次数 = %d\n", mono_bad);
        RETIRED("CHK-7", worst_in <= 0.01 && mono_bad == 0,
                "原判据窗口 [-110,+24] 是我拍的估计值;r2 CHK-7b 实测真实包络下界 = -109.816 dB。"
                "证伪条件(>0.02 dB)未触发 ⇒ 设计未被推翻,但判据窗口写错了 0.18 dB。"
                "⛔ 不移动标杆:原判据原样留痕,规格以 CHK-7b 实测包络为准。");
        OK("CHK-7mono", mono_bad == 0, "全域单调非降(43009 点无一处下降)");
        g = chdsp_db_to_gain(chdsp_db_from_raw(CHDSP_DB_MUTE_Q8));
        OK("CHK-7m", chdsp_gain_raw(g) == 0, "≤ −144 dB 精确返回 0(静音)");
        g = chdsp_db_to_gain(chdsp_db_from_raw(CHDSP_DB_MAX_Q8));
        printf("      +24 dB → raw = %d (INT32_MAX = %d),线性 = %.6f\n",
               chdsp_gain_raw(g), INT32_MAX, chdsp_gain_to_f64(g));
        OK("CHK-7x", chdsp_gain_raw(g) < INT32_MAX, "+24 dB 不触发饱和");
        g = chdsp_db_to_gain(chdsp_db_from_raw(0));
        printf("      0 dB → raw = %d,线性 = %.9f\n", chdsp_gain_raw(g), chdsp_gain_to_f64(g));
        OK("CHK-7u", chdsp_gain_raw(g) == (1 << CHDSP_GAIN_FRACBITS), "0 dB 精确等于 1.0");
        /* 反向(D6-y):越界输入必须被钳,不得算出垃圾 */
        g = chdsp_db_to_gain(chdsp_db_from_raw(1000*256));
        OK("CHK-7c", chdsp_gain_raw(g) > 0 && chdsp_gain_raw(g) < INT32_MAX,
           "+1000 dB 被钳位到 +24 dB 档,不溢出");
        /* 线性→dB 回环(仅显示用途) */
        {
            double worst = 0.0; int32_t qq;
            for (qq = -100*256; qq <= 24*256; qq += 37) {
                chdsp_gain_q4_27_t gg = chdsp_db_to_gain(chdsp_db_from_raw(qq));
                chdsp_db_q23_8_t  dd = chdsp_gain_to_db(gg);
                double e = fabs((double)(chdsp_db_raw(dd) - qq) / 256.0);
                if (e > worst) { worst = e; }
            }
            printf("      dB→线性→dB 回环 max|误差| = %.4f dB(仅电平表用途)\n", worst);
            OK("CHK-7r", worst <= 0.05, "回环 ≤0.05 dB");
        }
    }
    printf("\n");

    /* ---------------- CHK-4 误差反馈 / 噪声底 ---------------- */
    printf("CHK-4  二阶误差反馈:噪声底 vs 噪声增益\n");
    {
        struct { const char *name; bq_f64 d; } cs[8];
        int k; const int N = 120000, SKIP = 4000;
        double qstep = ldexp(1.0, -CHDSP_SMP_FRACBITS);
        double flat  = 10.0*log10(qstep*qstep/12.0);
        cs[0].name="PEQ 20Hz  Q=20    G=+15dB"; cs[0].d=rbj_peaking(20,20,15);
        cs[1].name="PEQ 20Hz  Q=20    G=-15dB"; cs[1].d=rbj_peaking(20,20,-15);
        cs[2].name="PEQ 20Hz  Q=8     G=+15dB"; cs[2].d=rbj_peaking(20,8,15);
        cs[3].name="PEQ 100Hz Q=20    G=+15dB"; cs[3].d=rbj_peaking(100,20,15);
        cs[4].name="PEQ 1kHz  Q=20    G=+15dB"; cs[4].d=rbj_peaking(1000,20,15);
        cs[5].name="HPF 20Hz  Q=0.7071";        cs[5].d=rbj_hpf(20,0.7071);
        cs[6].name="HPF 80Hz  Q=0.7071";        cs[6].d=rbj_hpf(80,0.7071);
        cs[7].name="LowShelf 20Hz S=1 G=+15dB"; cs[7].d=rbj_lowshelf(20,1.0,15);
        printf("      白噪基准 q^2/12 = %.2f dBFS   (q = 2^-%d)\n", flat, CHDSP_SMP_FRACBITS);
        printf("      %-28s %8s %10s %10s\n", "算例", "NG(dB)", "实测(dBFS)", "偏离基准");
        {
            int worst_ok = 1; double maxdev = 0.0;
            for (k = 0; k < 8; k++) {
                chdsp_biquad_coef_t c; chdsp_biquad_state_t s; ref_state rs;
                bq_f64 dq; chdsp_sat_t st; double acc_e = 0.0; double ngdb;
                int i, rc;
                rc = to_fixed_bq(cs[k].d, &c);
                if (rc != 0) { printf("      %-28s 系数超范围!\n", cs[k].name); g_fail++; continue; }
                fixed_bq_to_f64(&c, &dq);
                ngdb = 10.0*log10(ng_1overA(&dq));
                chdsp_biquad_reset(&s); chdsp_sat_reset(&st);
                memset(&rs, 0, sizeof(rs));
                g_rng = 0x2468ACE0u + (uint32_t)k;
                for (i = 0; i < N; i++) {
                    /* 激励 −20 dBFS 白噪(标称电平);先量化到 Q4.27 再喂两轨 */
                    double xv = rndn() * 0.03;
                    int32_t xr = (int32_t)floor(xv * ldexp(1.0, CHDSP_SMP_FRACBITS) + 0.5);
                    chdsp_smp_q4_27_t x = chdsp_smp_from_raw(xr);
                    chdsp_smp_q4_27_t y = chdsp_biquad_df1(&c, &s, x, &st);
                    long double yr = ref_df1(&dq, &rs, (long double)chdsp_smp_to_f64(x));
                    if (i >= SKIP) {
                        double e = chdsp_smp_to_f64(y) - (double)yr;
                        acc_e += e*e;
                    }
                }
                {
                    double m = 10.0*log10(acc_e/(double)(N-SKIP) + 1e-300);
                    double dev = m - flat;
                    printf("      %-28s %8.2f %10.2f %+10.2f   sat=%u\n",
                           cs[k].name, ngdb, m, dev, (unsigned)st.sat_sticky);
                    if (fabs(dev) > maxdev) { maxdev = fabs(dev); }
#if CHDSP_BROKEN_NOEF && !CHDSP_CHECK_FORCE_GOOD_ASSERT
                    /* 坏版本:应当约等于 flat + NG */
                    if (fabs(m - (flat + ngdb)) > 3.0) { worst_ok = 0; }
#else
                    if (fabs(dev) > 3.0) { worst_ok = 0; }
#endif
                }
            }
#if CHDSP_BROKEN_NOEF && !CHDSP_CHECK_FORCE_GOOD_ASSERT
            OK("CHK-4", worst_ok, "坏版本(NOEF):噪声底 ≈ 基准 + NG ⇒ EF 缺失可被观测");
#else
            printf("      最大偏离基准 = %.2f dB(判据 ≤3.0 dB)\n", maxdev);
            OK("CHK-4", worst_ok, "EF 开:噪声底与 NG(40-91dB)无关,全部贴基准");
#endif
        }
    }
    printf("\n");

    /* ---------------- CHK-2 舍入:直流偏置 ---------------- */
    printf("CHK-2  就近舍入 vs 截断:DF1 递归的直流偏置\n");
    {
        chdsp_biquad_coef_t c; chdsp_biquad_state_t s; chdsp_sat_t st;
        const int N = 400000, SKIP = 20000; int i; double sum = 0.0;
        (void)to_fixed_bq(rbj_hpf(20.0, 0.7071), &c);
        chdsp_biquad_reset(&s); chdsp_sat_reset(&st);
        g_rng = 0x0BADC0DEu;
        for (i = 0; i < N; i++) {
            double xv = rndn() * 0.03;
            int32_t xr = (int32_t)floor(xv * ldexp(1.0, CHDSP_SMP_FRACBITS) + 0.5);
            chdsp_smp_q4_27_t y = chdsp_biquad_df1(&c, &s, chdsp_smp_from_raw(xr), &st);
            if (i >= SKIP) { sum += chdsp_smp_to_f64(y); }
        }
        {
            double dc = sum / (double)(N - SKIP);
            printf("      20Hz HPF 输出直流 = %.6e 满刻度 (%.2f dBFS)\n",
                   dc, 20.0*log10(fabs(dc) + 1e-300));
            RETIRED("CHK-2", fabs(dc) <= 1e-7,
                    "原判据 |DC|<=1e-7 —— r2 CHK-2c 实测该测量的种子间标准差 1.226e-6,"
                    "判据落在测量噪声内 ⇒ 本检查【无分辨力】,退役,由 CHK-2b 取代。"
                    "⛔ 不删除、不改判据,原样留痕。");
        }
    }
    printf("\n");

    /* ---------------- CHK-2b / CHK-2c(r2 增补:独立再观测) ---------------- */
    printf("CHK-2b 换被测量:测【算术误差】的均值,而不是输出信号的均值\n");
    {
        chdsp_biquad_coef_t c; chdsp_biquad_state_t s; chdsp_sat_t st; ref_state rs;
        bq_f64 dq; const int N = 400000, SKIP = 20000; int i; double sum = 0.0;
        (void)to_fixed_bq(rbj_hpf(20.0, 0.7071), &c);
        fixed_bq_to_f64(&c, &dq);
        chdsp_biquad_reset(&s); chdsp_sat_reset(&st); memset(&rs, 0, sizeof(rs));
        g_rng = 0x0BADC0DEu;
        for (i = 0; i < N; i++) {
            double xv = rndn() * 0.03;
            int32_t xr = (int32_t)floor(xv * ldexp(1.0, CHDSP_SMP_FRACBITS) + 0.5);
            chdsp_smp_q4_27_t x = chdsp_smp_from_raw(xr);
            chdsp_smp_q4_27_t y = chdsp_biquad_df1(&c, &s, x, &st);
            long double yr = ref_df1(&dq, &rs, (long double)chdsp_smp_to_f64(x));
            if (i >= SKIP) { sum += chdsp_smp_to_f64(y) - (double)yr; }
        }
        {
            double dc = sum / (double)(N - SKIP);
            printf("      mean(y_定点 − y_参照) = %.6e 满刻度 (= %.3f LSB of Q4.27)\n",
                   dc, dc * ldexp(1.0, CHDSP_SMP_FRACBITS));
#if CHDSP_BROKEN_TRUNC && !CHDSP_CHECK_FORCE_GOOD_ASSERT
            OK("CHK-2b", fabs(dc) >= 1e-5, "坏版本(TRUNC):算术直流 ≥1e-5 ⇒ 截断的危害可被观测");
#else
            OK("CHK-2b", fabs(dc) <= 2e-9, "好判据:算术直流 ≤2e-9(≈0.3 LSB)");
#endif
        }
    }
    printf("CHK-2c 量分辨力:CHK-2 的原始被测量,8 个种子的散布\n");
    {
        double v[8]; int k; double m = 0.0, sd = 0.0;
        for (k = 0; k < 8; k++) {
            chdsp_biquad_coef_t c; chdsp_biquad_state_t s; chdsp_sat_t st;
            const int N = 400000, SKIP = 20000; int i; double sum = 0.0;
            (void)to_fixed_bq(rbj_hpf(20.0, 0.7071), &c);
            chdsp_biquad_reset(&s); chdsp_sat_reset(&st);
            g_rng = 0x0BADC0DEu + (uint32_t)(k * 7919);
            for (i = 0; i < N; i++) {
                double xv = rndn() * 0.03;
                int32_t xr = (int32_t)floor(xv * ldexp(1.0, CHDSP_SMP_FRACBITS) + 0.5);
                chdsp_smp_q4_27_t y = chdsp_biquad_df1(&c, &s, chdsp_smp_from_raw(xr), &st);
                if (i >= SKIP) { sum += chdsp_smp_to_f64(y); }
            }
            v[k] = sum / (double)(N - SKIP);
            m += v[k];
        }
        m /= 8.0;
        for (k = 0; k < 8; k++) { sd += (v[k]-m)*(v[k]-m); }
        sd = sqrt(sd / 7.0);
        printf("      8 个种子:");
        for (k = 0; k < 8; k++) { printf(" %+.2e", v[k]); }
        printf("\n      均值 = %+.3e  标准差 s = %.3e   (CHK-2 原判据 1e-7)\n", m, sd);
        OK("CHK-2c", sd > 1e-7,
           "s ≫ 1e-7 ⇒ CHK-2 的原判据落在测量噪声内,该检查无分辨力(LESSONS C-3)");
    }
    printf("\n");

    /* ---------------- CHK-7b(r2 增补):dB 精度包络与机理拆分 ---------------- */
    printf("CHK-7b dB→线性:真实精度包络 + 误差来源拆分\n");
    {
        int32_t q; int32_t bound_q8 = CHDSP_DB_MAX_Q8; double tab_worst = 0.0;
        /* ① 从高 dB 往低 dB 扫,找 max|误差| 首次超过 0.01 dB 的点 */
        double run_max = 0.0;
        for (q = CHDSP_DB_MAX_Q8; q > CHDSP_DB_MUTE_Q8; q--) {
            chdsp_gain_q4_27_t g = chdsp_db_to_gain(chdsp_db_from_raw(q));
            double got = chdsp_gain_to_f64(g);
            double exact = pow(10.0, (double)q / 256.0 / 20.0);
            double e = (got > 0.0) ? fabs(20.0*log10(got/exact)) : 999.0;
            if (e > run_max) { run_max = e; }
            if (run_max > 0.01) { bound_q8 = q; break; }
        }
        printf("      max|误差| ≤0.01 dB 成立的**真实 dB 下界** = %.3f dB\n", bound_q8/256.0);
        /* ② 查表贡献:用 double 复算同一算法但不量化到 Q4.27 */
        for (q = CHDSP_DB_MUTE_Q8 + 1; q <= CHDSP_DB_MAX_Q8; q++) {
            /* 复现 chdsp_db_to_gain 的查表步骤,但保留 double 精度输出。
             * 注意:这不是转写被测公式作为判据 —— 它是**误差归因**用的分解量,
             * 判据仍由被测函数 chdsp_db_to_gain 的输出给出。 */
            int32_t db = q;
            int64_t u = ((int64_t)db * (int64_t)182624928348LL) >> 16;
            int32_t n = (int32_t)(u >> 32);
            int64_t f = u - (((int64_t)n) << 32);
            double  fr = (double)f / 4294967296.0;
            double  approx = ldexp(pow(2.0, fr), n);          /* 无查表量化、无输出量化 */
            double  exact  = pow(10.0, (double)q / 256.0 / 20.0);
            double  e = fabs(20.0*log10(approx/exact));
            if (e > tab_worst) { tab_worst = e; }
        }
        printf("      「移位/常数」路径的固有误差(不含查表量化与输出量化) = %.9f dB\n", tab_worst);
        {
            chdsp_gain_q4_27_t g = chdsp_db_to_gain(chdsp_db_from_raw(bound_q8));
            double lin = chdsp_gain_to_f64(g);
            double raw = (double)chdsp_gain_raw(g);
            double outq_db = fabs(20.0*log10((raw+0.5)/raw));
            printf("      在下界处:gain=%.6e ⇒ raw=%.0f ⇒ 半 LSB 相当于 %.6f dB\n",
                   lin, raw, outq_db);
            OK("CHK-7b", outq_db >= 0.008 && tab_worst < 0.005,
               "瓶颈确为输出格式 Q4.27 的 LSB,不是查表 ⇒ 该误差在本格式下不可约");
        }
    }
    printf("\n");

    /* ---------------- CHK-11(r2 增补):累加器实占位宽 ---------------- */
    printf("CHK-11 累加器【参数范围实测占用】(b):最坏合法配置\n");
    {
        chdsp_biquad_coef_t c; chdsp_biquad_state_t s; chdsp_sat_t st;
        double maxlog = 0.0; int i;
        /* 最坏:高架 20Hz S=1 +15dB(b 最大 11.21)+ 满量程链内样本 */
        (void)to_fixed_bq(rbj_lowshelf(20.0, 1.0, 15.0), &c);
        chdsp_biquad_reset(&s); chdsp_sat_reset(&st);
        for (i = 0; i < 20000; i++) {
            /* 方波满量程 ±16(链内格式极限),最坏激励 */
            int32_t xr = ((i / 3) & 1) ? INT32_MAX : INT32_MIN;
            chdsp_acc_t acc; chdsp_acc_raw_t v;
            chdsp_smp_q4_27_t x = chdsp_smp_from_raw(xr);
            chdsp_acc_clear(&acc);
            chdsp_acc_mac (&acc, x,     c.b0);
            chdsp_acc_mac (&acc, s.x1,  c.b1);
            chdsp_acc_mac (&acc, s.x2,  c.b2);
            chdsp_acc_msub(&acc, s.y1,  c.a1);
            chdsp_acc_msub(&acc, s.y2,  c.a2);
            chdsp_ef_inject(&acc, &s.ef, c.a1, c.a2);
            v = CHDSP_RAW(acc); if (v < 0) { v = -v; }
            if (v > 0) { double lg = log2((double)v); if (lg > maxlog) { maxlog = lg; } }
            (void)chdsp_biquad_df1(&c, &s, x, &st);
        }
        printf("      max log2|acc| = %.3f bit   (int64 上限 63,本文件声明 66)\n", maxlog);
        printf("      该激励下输出饱和发生 = %s(满量程方波过 +15dB 高架,预期会饱和)\n",
               st.sat_sticky ? "是" : "否");
        OK("CHK-11", maxlog <= 66.0, "实占 ≤66 bit,与 §累加器 (a) 声明一致");
        RETIRED("CHK-11b", maxlog > 63.0,
                "r2 预注册的证伪条件【已触发】:实占 58.005 < 63 ⇒ 「int64 在真实参数范围内"
                "会溢出」为假。已按预注册要求改正 chdsp_fixed.h §累加器,把 (a) 类型范围上界"
                "64.81bit 与 (b) 参数范围实测 58.0bit 分开写。本断言退役。");
    }
    printf("\n");

    /* ---------------- CHK-5 级联(D-4) ---------------- */
    printf("CHK-5  级联:8 节 PEQ + LR8 分频(D-4:单级正确 != 级联正确)\n");
    {
        /* 8 节非平坦 PEQ:量化系数级联响应 vs 理想系数级联响应 */
        const double f0[8]  = {31.5, 63, 125, 250, 500, 1000, 4000, 16000};
        const double qq[8]  = {1.4, 1.4, 2.0, 2.0, 1.0, 1.4, 0.7, 0.7};
        const double gg[8]  = {+6, -8, +4, -10, +12, -6, +9, -15};
        chdsp_biquad_coef_t cq[8]; bq_f64 ci[8], cqf[8];
        int k, i, ok = 1; double maxdev = 0.0, at = 0.0;
        for (k = 0; k < 8; k++) {
            ci[k] = rbj_peaking(f0[k], qq[k], gg[k]);
            if (to_fixed_bq(ci[k], &cq[k]) != 0) { ok = 0; }
            fixed_bq_to_f64(&cq[k], &cqf[k]);
        }
        OK("CHK-5c", ok, "8 节系数全部落在 Q4.27 范围内");
        for (i = 0; i <= 4000; i++) {
            double f = 20.0 * pow(1000.0, (double)i/4000.0);   /* 20 Hz .. 20 kHz 对数 */
            double w = 2.0*M_PI*f/FS;
            double reI = 1.0, imI = 0.0, reQ = 1.0, imQ = 0.0;
            double cw = cos(w), sw = sin(w), c2 = cos(2*w), s2 = sin(2*w);
            for (k = 0; k < 8; k++) {
                double nr, ni, dr, di, tr, ti, den;
                /* 理想 */
                nr = ci[k].b0 + ci[k].b1*cw + ci[k].b2*c2;  ni = -(ci[k].b1*sw + ci[k].b2*s2);
                dr = 1.0      + ci[k].a1*cw + ci[k].a2*c2;  di = -(ci[k].a1*sw + ci[k].a2*s2);
                den = dr*dr + di*di;
                tr = (nr*dr + ni*di)/den; ti = (ni*dr - nr*di)/den;
                { double a = reI*tr - imI*ti, b = reI*ti + imI*tr; reI = a; imI = b; }
                /* 量化 */
                nr = cqf[k].b0 + cqf[k].b1*cw + cqf[k].b2*c2; ni = -(cqf[k].b1*sw + cqf[k].b2*s2);
                dr = 1.0       + cqf[k].a1*cw + cqf[k].a2*c2; di = -(cqf[k].a1*sw + cqf[k].a2*s2);
                den = dr*dr + di*di;
                tr = (nr*dr + ni*di)/den; ti = (ni*dr - nr*di)/den;
                { double a = reQ*tr - imQ*ti, b = reQ*ti + imQ*tr; reQ = a; imQ = b; }
            }
            {
                double mI = 20.0*log10(sqrt(reI*reI + imI*imI));
                double mQ = 20.0*log10(sqrt(reQ*reQ + imQ*imQ));
                double d = fabs(mQ - mI);
                if (d > maxdev) { maxdev = d; at = f; }
            }
        }
        printf("      8 节非平坦 PEQ 级联:量化 vs 理想 max|Δ| = %.6f dB @ %.1f Hz\n", maxdev, at);
        printf("      (PRD 规格 20Hz-20kHz ±0.3 dB;本项判据 ≤0.02 dB)\n");
        OK("CHK-5", maxdev <= 0.02, "级联量化误差远小于 ±0.3 dB 规格");

        /* LR8 分频:4 节同 fc 的 Butterworth Q=0.7071,DC / Nyquist */
        {
            double fc = 80.0; int nsec = 4;
            bq_f64 hp = rbj_hpf(fc, 0.7071), lp = rbj_lpf(fc, 0.7071);
            chdsp_biquad_coef_t hq, lq; bq_f64 hqf, lqf;
            double dc_h, ny_l;
            (void)to_fixed_bq(hp, &hq); fixed_bq_to_f64(&hq, &hqf);
            (void)to_fixed_bq(lp, &lq); fixed_bq_to_f64(&lq, &lqf);
            /* z=1 ⇒ H(1) = (b0+b1+b2)/(1+a1+a2);z=−1 ⇒ (b0−b1+b2)/(1−a1+a2) */
            dc_h = (hqf.b0 + hqf.b1 + hqf.b2) / (1.0 + hqf.a1 + hqf.a2);
            ny_l = (lqf.b0 - lqf.b1 + lqf.b2) / (1.0 - lqf.a1 + lqf.a2);
            printf("      LR8 高通(4节)DC   增益 = %.2f dB  (单节 %.4e)\n",
                   20.0*nsec*log10(fabs(dc_h) + 1e-300), dc_h);
            printf("      LR8 低通(4节)Nyq  增益 = %.2f dB  (单节 %.4e)\n",
                   20.0*nsec*log10(fabs(ny_l) + 1e-300), ny_l);
            OK("CHK-5d", 20.0*nsec*log10(fabs(dc_h)+1e-300) <= -180.0
                      && 20.0*nsec*log10(fabs(ny_l)+1e-300) <= -180.0,
               "级联 DC/Nyquist 泄漏 ≤ −180 dB");
            /* 结构约束量化(b1 = ∓2·b0, b2 = b0)作为对照:应当精确为 0 */
            {
                double b0q = chdsp_coef_to_f64(hq.b0);
                double dc_t = (b0q - 2.0*b0q + b0q) / (1.0 + hqf.a1 + hqf.a2);
                printf("      对照:结构约束量化(b1=−2b0,b2=b0)DC 单节 = %.4e ⇒ %s\n",
                       dc_t, (dc_t == 0.0) ? "精确 0(构造保证)" : "非 0");
                OK("CHK-5t", dc_t == 0.0, "结构约束量化使 DC 零点在量化后仍精确");
            }
        }

        /* CHK-5f(r2 增补):r1 里自由量化恰好给出精确 0 —— 是巧合还是保证? */
        {
            int i, free_nz_hp = 0, free_nz_lp = 0, tied_nz = 0, NPT = 500;
            double worst_free_hp = 0.0, worst_free_lp = 0.0, at_hp = 0.0;
            for (i = 0; i < NPT; i++) {
                double fc = 20.0 * pow(1000.0, (double)i/(double)(NPT-1));
                chdsp_biquad_coef_t hq, lq; bq_f64 hf, lf;
                double dh, dl, b0q, dt;
                (void)to_fixed_bq(rbj_hpf(fc, 0.7071), &hq); fixed_bq_to_f64(&hq, &hf);
                (void)to_fixed_bq(rbj_lpf(fc, 0.7071), &lq); fixed_bq_to_f64(&lq, &lf);
                dh = fabs(hf.b0 + hf.b1 + hf.b2);            /* 高通在 DC 的分子 */
                dl = fabs(lf.b0 - lf.b1 + lf.b2);            /* 低通在 Nyquist 的分子 */
                if (dh != 0.0) { free_nz_hp++;
                    { double g = dh/fabs(1.0+hf.a1+hf.a2);
                      if (g > worst_free_hp) { worst_free_hp = g; at_hp = fc; } } }
                if (dl != 0.0) { free_nz_lp++;
                    { double g = dl/fabs(1.0-lf.a1+lf.a2);
                      if (g > worst_free_lp) { worst_free_lp = g; } } }
                {   /* 用被测头文件新增的结构约束接口,而不是在检查里手算 */
                    chdsp_biquad_coef_t tq;
                    bq_f64 hd = rbj_hpf(fc, 0.7071);
                    if (chdsp_coef_hplp_from_f64(hd.b0, hd.a1, hd.a2, 1, &tq) != 0) { tied_nz++; }
                    b0q = chdsp_coef_to_f64(tq.b0);
                    dt  = fabs(b0q + chdsp_coef_to_f64(tq.b1) + chdsp_coef_to_f64(tq.b2));
                    if (dt != 0.0) { tied_nz++; }
                }
            }
            printf("      fc 扫 %d 点(20Hz-20kHz):\n", NPT);
            printf("        自由量化   高通 DC 零点被破坏 %d/%d 点(最坏 DC 增益 %.2f dB @ %.1f Hz)\n",
                   free_nz_hp, NPT, 20.0*log10(worst_free_hp + 1e-300), at_hp);
            printf("        自由量化   低通 Nyq 零点被破坏 %d/%d 点(最坏 %.2f dB)\n",
                   free_nz_lp, NPT, 20.0*log10(worst_free_lp + 1e-300));
            printf("        结构约束量化 被破坏 %d/%d 点\n", tied_nz, NPT);
            OK("CHK-5f", free_nz_hp > 0 && tied_nz == 0,
               "自由量化会破坏零点(r1 的精确 0 是巧合),结构约束量化恒精确 ⇒ 该规则有理由存在");
        }
    }
    printf("\n");

    /* ---------------- CHK-9 的数据面(逐位输出,由外部脚本比对两种构建) -------- */
    {
        FILE *fp = fopen(CHDSP_STRICT_TYPES ? "bitexact_strict1.txt" : "bitexact_strict0.txt", "w");
        chdsp_biquad_coef_t c; chdsp_biquad_state_t s; chdsp_sat_t st; int i;
        (void)to_fixed_bq(rbj_peaking(1000, 1.4, 6.0), &c);
        chdsp_biquad_reset(&s); chdsp_sat_reset(&st);
        g_rng = 0xFEEDBEEFu;
        for (i = 0; i < 20000; i++) {
            int32_t xr = (int32_t)(rnd32() >> 5) - (int32_t)(1 << 26);
            chdsp_smp_q4_27_t y = chdsp_biquad_df1(&c, &s, chdsp_smp_from_raw(xr), &st);
            fprintf(fp, "%d\n", chdsp_smp_raw(y));
        }
        fclose(fp);
        printf("CHK-9  已写出逐位输出 %s(由 run_r1.sh 比对两种构建)\n\n",
               CHDSP_STRICT_TYPES ? "bitexact_strict1.txt" : "bitexact_strict0.txt");
    }

    /* ---------------- 参照数据:供第二轨(python)对表 ---------------- */
    {
        FILE *fp = fopen("db_table_c.txt", "w");
        int32_t q;
        for (q = CHDSP_DB_MUTE_Q8; q <= CHDSP_DB_MAX_Q8; q++) {
            fprintf(fp, "%d\n", chdsp_gain_raw(chdsp_db_to_gain(chdsp_db_from_raw(q))));
        }
        fclose(fp);
        printf("已写出 db_table_c.txt(第二轨对表用)\n\n");
    }

    printf("================================================================\n");
    printf("合计: PASS=%d  FAIL=%d  RETIRED=%d(退役项不计入判定,原样留痕)\n",
           g_pass, g_fail, g_retired);
    printf("构建: FORCE_GOOD_ASSERT=%d\n", CHDSP_CHECK_FORCE_GOOD_ASSERT);
    printf("================================================================\n");
    return (g_fail == 0) ? 0 : 1;
}
