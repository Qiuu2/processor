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

    t1a_biquad_run(fcsv);
    t1b_polyphase_run(fcsv);
    t2_fft_run(fcsv);
    t3_nhs_scalar_run(fcsv);
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
