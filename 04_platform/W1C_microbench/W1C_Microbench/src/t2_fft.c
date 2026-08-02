/*****************************************************************************
 * t2_fft.c
 * T2:1024 点与 2048 点定点 FFT —— DEC-0009 里"无板证上界"的那一档
 *
 * ⚠⚠ 诚实边界(请先读完这段再看数字)⚠⚠
 * 本内核 **没有调用 CCES DSP Run-Time Library 的 rfft()/cfft() 之类库函数**。
 * 原因:本沙箱环境没有装 SHARC 工具链(见 01_design/W1_HANDOFF.md §0 第 9 项,
 * lead 已实查 `/opt/analog/cces/2.12.1` 全树无 cc21k/easm21k/21569 支持包),
 * 我们没有任何办法现场核对 CCES 安装的 DSP 库里 FFT 函数的精确签名/头文件名/
 * 版本号——与其**编个看起来对但可能是错的库函数名**(那是"不确定就编"),
 * 不如老老实实写一个**自包含、标准 C、零 CCES 专有 API 依赖**的定点 FFT:
 * 编译风险最低,数字的"代表性"边界也讲得清楚。
 *
 * 代表性声明(必须原样带到任何引用这份数字的地方):
 *   ①本实现是"输入打包成复数(虚部置 0)后跑完整 N 点复数 FFT"的做法,
 *     不是专用的实数优化 FFT(real-FFT 技巧通常靠共轭对称性省下约一半算量)。
 *     ⇒ 本内核报出的周期数是**保守上界**,不是紧确值;若 CCES 装了官方
 *     rfft() 之类实数专用 FFT,真实值预期更低。
 *   ②定点格式 = Q1.31(int32_t,32-bit 有符号,满幅 [-1,1)),蝶形运算每级
 *     统一右移 1 位做定标(经典"每级除2"防溢出方案,非动态块浮点),
 *     整体输出相对真值缩放 1/N —— 这是为了**周期数代表性**服务的实现选择,
 *     不是本项目的定点格式定案(那是 adaptive-dsp/architect 的活)。
 *   ③MAC 计数口径(供上级折算 cyc/MAC 用,本文件不在片上做除法):
 *     蝶形数 = (N/2)·log2(N);每个蝶形的复数乘法 = 4 次实数乘 + 2 次实数加/减
 *     (未用 3-mult 复数乘法技巧),另有 2 次复数加/减 = 4 次实数加/减。
 *     若按"复数乘加对"计,MAC 数 = (N/2)·log2(N);若展开到实数 MAC,
 *     乘法次数 = 4·(N/2)·log2(N) = 2N·log2(N)。**两种口径都可能被引用,
 *     切勿混用**,本文件只报 cycles,折算交给引用方并注明用的是哪一种。
 *   ④旋转因子表现场用 Python 生成(见 04_platform/W1C_microbench/PROVENANCE.md
 *     的生成脚本记录),Q31 定点,四舍五入,k=0 项 cos=1.0 因满幅溢出钉在
 *     0x7FFFFFFF(= 1 - 2^-31,肉眼可忽略的量化偏差)。
 *
 * 内存放置:
 *   L1 变体 = 默认放置(不加 pragma)。
 *   L2 变体 = 数据数组与旋转因子表整体搬 L2(#pragma section("seg_l2"))。
 *
 * 全部数字在板上跑出之前 = [L4/未验证]。若本文件编译不过,把
 * w1c_config.h 的 ENABLE_T2_FFT 改 0,其余三个内核仍可测。
 *****************************************************************************/
#include "w1c_config.h"

#if ENABLE_T2_FFT

#include <stdio.h>
#include <time.h>
#include <stdint.h>
#include "t2_fft.h"
#include "w1c_selfcheck.h"

typedef struct {
    int32_t re;
    int32_t im;
} cplx_q31_t;

#define T2_N1        1024
#define T2_LOG2_N1    10
#define T2_N2        2048
#define T2_LOG2_N2    11

/* 旋转因子表:N/2 项即可覆盖一次 N 点 DIT FFT 的全部级 */
static const cplx_q31_t t2_tw512_l1[T2_N1 / 2] = {
#include "fft_twiddle_q31_512.dat"
};
static const cplx_q31_t t2_tw1024_l1[T2_N2 / 2] = {
#include "fft_twiddle_q31_1024.dat"
};

#pragma section("seg_l2")
static const cplx_q31_t t2_tw512_l2[T2_N1 / 2] = {
#include "fft_twiddle_q31_512.dat"
};
#pragma section("seg_l2")
static const cplx_q31_t t2_tw1024_l2[T2_N2 / 2] = {
#include "fft_twiddle_q31_1024.dat"
};

/* ---- 数据数组:L1 变体(默认放置)---- */
static cplx_q31_t t2_buf_1024_l1[T2_N1];
static cplx_q31_t t2_buf_2048_l1[T2_N2];

/* ---- 数据数组:L2 变体 ---- */
#pragma section("seg_l2")
static cplx_q31_t t2_buf_1024_l2[T2_N1];
#pragma section("seg_l2")
static cplx_q31_t t2_buf_2048_l2[T2_N2];

static int32_t t2_q31_mul(int32_t a, int32_t b)
{
    int64_t p = (int64_t)a * (int64_t)b;
    return (int32_t)(p >> 31);
}

static void t2_bitrev(cplx_q31_t *x, int n)
{
    int i, j, k;
    j = 0;
    for (i = 0; i < n - 1; i++) {
        if (i < j) {
            cplx_q31_t tmp = x[i];
            x[i] = x[j];
            x[j] = tmp;
        }
        k = n >> 1;
        while (k <= j) {
            j -= k;
            k >>= 1;
        }
        j += k;
    }
}

/* 标准迭代 radix-2 DIT,旋转因子步进 = n/m,每级右移1位定标 */
static void t2_fft_inplace(cplx_q31_t *x, const cplx_q31_t *tw, int n, int log2n)
{
    int stage, m, half, tw_stride, k, j;

    t2_bitrev(x, n);

    for (stage = 1; stage <= log2n; stage++) {
        m = 1 << stage;
        half = m >> 1;
        tw_stride = n / m;
        for (k = 0; k < n; k += m) {
            for (j = 0; j < half; j++) {
                int32_t wr = tw[j * tw_stride].re;
                int32_t wi = tw[j * tw_stride].im;
                int32_t xr = x[k + j + half].re;
                int32_t xi = x[k + j + half].im;
                int32_t tr = t2_q31_mul(wr, xr) - t2_q31_mul(wi, xi);
                int32_t ti = t2_q31_mul(wr, xi) + t2_q31_mul(wi, xr);
                int32_t ur = x[k + j].re;
                int32_t ui = x[k + j].im;
                x[k + j].re      = (ur + tr) >> 1;
                x[k + j].im      = (ui + ti) >> 1;
                x[k + j + half].re = (ur - tr) >> 1;
                x[k + j + half].im = (ui - ti) >> 1;
            }
        }
    }
}

/* 确定性非平凡实数输入(虚部置 0),供自检使用,不追求信号意义 */
static void t2_fill_real_input(cplx_q31_t *x, int n, int seed)
{
    int i;
    for (i = 0; i < n; i++) {
        /* 简单锯齿 + seed 偏移,幅度约为 Q31 满幅的 1/64(~125 * 2^18 ≈ 3.3e7,
         * 满幅 2^31 ≈ 2.1e9),故意留足裕量:每级"和后移位"的标准定标手法
         * 保证幅度不随级数增长,但 (ur+tr) 这一步中间和在移位前短暂存在,
         * 输入越贴近满幅、这一步越可能越界,故留够余量,不是精确算出来的临界值 */
        int32_t v = (int32_t)(((i + seed) % 251) - 125) * (1 << 18);
        x[i].re = v;
        x[i].im = 0;
    }
}

static void t2_run_one(FILE *fcsv, cplx_q31_t *buf, const cplx_q31_t *tw,
                        int n, int log2n, const char *mem_tag)
{
    volatile clock_t t0, t1, cyc_cold, cyc_warm_total;
    int32_t chk;
    int i;

    /* 冷:第一次调用 */
    t2_fill_real_input(buf, n, 1);
    t0 = clock();
    t2_fft_inplace(buf, tw, n, log2n);
    t1 = clock();
    cyc_cold = t1 - t0;
    chk = buf[1].re ^ buf[n / 2].im;
    w1c_checksum_add(chk);
    printf("T2_FFT,%s,N=%d,cold_1call,cycles=%d,checksum=%d\n",
           mem_tag, n, (int)cyc_cold, (int)chk);
    if (fcsv) fprintf(fcsv, "T2_FFT,%s,N=%d,cold_1call,%d,%d\n",
                       mem_tag, n, (int)cyc_cold, (int)chk);

    /* 热:连续 W1C_WARM_REPEAT 次(每次重新填输入+重新做完整 FFT,含 bit-reversal) */
    t0 = clock();
    for (i = 0; i < W1C_WARM_REPEAT; i++) {
        t2_fill_real_input(buf, n, i);
        t2_fft_inplace(buf, tw, n, log2n);
    }
    t1 = clock();
    cyc_warm_total = t1 - t0;
    chk = buf[1].re ^ buf[n / 2].im;
    w1c_checksum_add(chk);
    printf("T2_FFT,%s,N=%d,warm_avg_of_%d,cycles_total=%d,cycles_avg=%d,checksum=%d\n",
           mem_tag, n, W1C_WARM_REPEAT, (int)cyc_warm_total,
           (int)(cyc_warm_total / W1C_WARM_REPEAT), (int)chk);
    if (fcsv) fprintf(fcsv, "T2_FFT,%s,N=%d,warm_avg_of_%d,%d,%d\n",
                       mem_tag, n, W1C_WARM_REPEAT, (int)cyc_warm_total, (int)chk);
}

void t2_fft_run(FILE *fcsv)
{
    printf("\n==== T2: fixed-point complex FFT on real input (Q1.31, radix-2 DIT) ====\n");
    printf("     (自研参考实现,非 CCES 库函数;见文件头诚实边界声明)\n");

    t2_run_one(fcsv, t2_buf_1024_l1, t2_tw512_l1,  T2_N1, T2_LOG2_N1, "L1");
    t2_run_one(fcsv, t2_buf_2048_l1, t2_tw1024_l1, T2_N2, T2_LOG2_N2, "L1");
    t2_run_one(fcsv, t2_buf_1024_l2, t2_tw512_l2,  T2_N1, T2_LOG2_N1, "L2");
    t2_run_one(fcsv, t2_buf_2048_l2, t2_tw1024_l2, T2_N2, T2_LOG2_N2, "L2");
}

#else /* !ENABLE_T2_FFT */

void t2_fft_run(FILE *fcsv)
{
    printf("T2_FFT,DISABLED,-,-,-,-  (see w1c_config.h ENABLE_T2_FFT)\n");
    if (fcsv) fprintf(fcsv, "T2_FFT,DISABLED,-,-,-,-\n");
}

#endif /* ENABLE_T2_FFT */
