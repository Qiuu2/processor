/*****************************************************************************
 * w1c_main.c
 * W1-C 微基准 · 主程序
 *
 * 顺序跑四个内核 + 一个 sizeof 自查,每一行结果同时:
 *   ①printf 到 Console(CCES 调试会话默认把目标 stdout 接到 Console 视图,
 *     与 ADI 原工程 FIR_Core_Throughput_21569.c / IIR_Core_Throughput_21569.c
 *     的做法完全一致——这两个文件本身就是本工程的直接底座)
 *   ②fprintf 到 "Results_W1C.csv"(通过 CCES 的 host-file-I/O/semihosting
 *     写到宿主 PC 上,同样是 ADI 原工程 `fopen("Results(Cycles).csv","w+")`
 *     的原始写法,未改动这一机制本身)
 *
 * 产出方:verification teammate(首次上岗)。全部数字在 CTO 于 CCES+EZ-Board
 * 上跑出结果、回传之前,一律 [L4/未验证]。
 *****************************************************************************/
#include <sys/platform.h>
#include "adi_initialize.h"
#include <stdio.h>
#include <time.h>    /* clock(), clock_t -- needed by w1c_clock_selftest */
#include <stdint.h>

#include "w1c_config.h"
#include "w1c_selfcheck.h"
#include "t1a_biquad.h"
#include "t1b_polyphase.h"
#include "t2_fft.h"
#include "t3_nhs_scalar.h"
#include "mem_sizeof_check.h"

volatile uint32_t g_w1c_checksum = 0;

char __argv_string[] = "";


/*****************************************************************************
 * w1c_clock_selftest -- validate the RULER before trusting anything it measures.
 *
 * Why this exists: every number this program prints is `clock()` deltas.
 * The checksum machinery (w1c_selfcheck.h) guards against the compiler
 * DELETING a kernel -- it does NOT guard against the TIMER being wrong.
 * If clock() returned milliseconds instead of core cycles, every result would
 * be off by ~1e6 and still look like a plausible number.
 *
 * Three checks, each able to FAIL:
 *   C1 monotonic + nonzero : back-to-back clock() must differ by > 0
 *   C2 linearity           : 1x / 2x / 4x work must give ~1 / ~2 / ~4 cycles
 *   C3 magnitude plausible : a 4000-iteration volatile add loop must land in
 *                            [2e3, 2e6] cycles. Outside that, the unit is
 *                            almost certainly not core cycles.
 * A FAIL here invalidates EVERY other line of output. Report it, do not
 * "interpret" the numbers that follow.
 *****************************************************************************/
static void w1c_clock_selftest(FILE *fcsv)
{
    volatile clock_t a, b;
    volatile int32_t acc;
    clock_t d[3];
    const int32_t N[3] = { 1000, 2000, 4000 };
    int32_t i, n, c1, c2, c3;
    double r2, r4;

    a = clock();
    b = clock();
    c1 = ((clock_t)(b - a) > (clock_t)0) ? 1 : 0;

    for (n = 0; n < 3; n++) {
        acc = 0;
        a = clock();
        for (i = 0; i < N[n]; i++) { acc = acc + i; }   /* volatile acc => not removable */
        b = clock();
        d[n] = b - a;
    }
    r2 = (d[0] != (clock_t)0) ? ((double)d[1] / (double)d[0]) : 0.0;
    r4 = (d[0] != (clock_t)0) ? ((double)d[2] / (double)d[0]) : 0.0;
    c2 = ((r2 > 1.7) && (r2 < 2.3) && (r4 > 3.4) && (r4 < 4.6)) ? 1 : 0;
    c3 = (((long)d[2] >= 2000L) && ((long)d[2] <= 2000000L)) ? 1 : 0;

    printf("CLK_SELFTEST,back_to_back=%d,C1_nonzero=%s\n",
           (int)(clock_t)(b - a), c1 ? "PASS" : "**FAIL**");
    printf("CLK_SELFTEST,loop1000=%d,loop2000=%d,loop4000=%d\n",
           (int)d[0], (int)d[1], (int)d[2]);
    printf("CLK_SELFTEST,ratio_2x=%.3f,ratio_4x=%.3f,C2_linear=%s\n",
           r2, r4, c2 ? "PASS" : "**FAIL**");
    printf("CLK_SELFTEST,C3_magnitude=%s  [4000-iter loop expected 2e3..2e6 core cycles]\n",
           c3 ? "PASS" : "**FAIL**");
    if (!(c1 && c2 && c3)) {
        printf("!! CLK_SELFTEST FAILED -- every cycle number below is INVALID.\n");
        printf("!! Report the failure; do NOT interpret the numbers that follow.\n");
    }
    if (fcsv) {
        fprintf(fcsv, "CLK_SELFTEST,back_to_back,%d,%s\n", (int)(clock_t)(b - a), c1 ? "PASS" : "FAIL");
        fprintf(fcsv, "CLK_SELFTEST,loops,%d,%d,%d\n", (int)d[0], (int)d[1], (int)d[2]);
        fprintf(fcsv, "CLK_SELFTEST,ratios,%.3f,%.3f,%s\n", r2, r4, c2 ? "PASS" : "FAIL");
        fprintf(fcsv, "CLK_SELFTEST,magnitude,%s\n", c3 ? "PASS" : "FAIL");
    }
}

int main(int argc, char *argv[])
{
    FILE *fcsv;

    adi_initComponents();

    printf("\n");
    printf("############################################################\n");
    printf("# W1-C microbench — CONF-DSP-88 / ADSP-21569\n");
#if defined(NDEBUG)
    printf("# build config = Release (optimized, -O on)\n");
#elif defined(_DEBUG)
    printf("# build config = Debug (NOT optimized — do not compare to DEC-0009/0014 anchors)\n");
#else
    printf("# build config = unknown (neither NDEBUG nor _DEBUG defined)\n");
#endif
    printf("# processor    = ADSP-21569, si-revision 0.0 (per system.svc)\n");
    printf("# clock()      = CCLK cycles (see <time.h> on SHARC; volatile clock_t)\n");
    printf("############################################################\n");

    fcsv = fopen("Results_W1C.csv", "w+");
    if (fcsv) {
        fprintf(fcsv, "# W1-C microbench results. columns vary per kernel block; see README_WINDOWS.md\n");
    } else {
        printf("!! fopen(\"Results_W1C.csv\") FAILED — host file I/O not available in this session.\n");
        printf("!! Copy the full Console text instead; that alone is enough (see README N/A rule).\n");
    }

    w1c_clock_selftest(fcsv);

    t1a_biquad_run(fcsv);
    t1b_polyphase_run(fcsv);
    t2_fft_run(fcsv);
    t3_nhs_scalar_run(fcsv);
    w1c_clk_readback_run(fcsv);
    mem_sizeof_check_run(fcsv);

    printf("\n==== DONE ====\n");
    printf("W1C_CHECKSUM_FINAL=%u  (非零、且逐次运行有变化才算正常;见 w1c_selfcheck.h 判读规则)\n",
           (unsigned int)g_w1c_checksum);

    if (fcsv) {
        fprintf(fcsv, "W1C_CHECKSUM_FINAL,%u\n", (unsigned int)g_w1c_checksum);
        fclose(fcsv);
    }

    return 0;
}
