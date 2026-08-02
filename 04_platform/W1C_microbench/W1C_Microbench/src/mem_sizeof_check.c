/*****************************************************************************
 * mem_sizeof_check.c
 * DEC-0014 ⑤ / W1-B §8.2 内存对账 —— 第三轨:SHARC 编译器现场 sizeof
 *
 * 来源:01_design/selfcheck_W1B/mem_sizeof.c(adaptive-dsp 第 3 实例,[L2/桌面数值],
 *   x86-64/gcc -O0 求值,第二轨)。本文件把**同一批结构体定义逐字段原样搬到这里**,
 *   只求 SHARC 编译器(CCES)现场算出的 sizeof 数字,不改动任何字段/顺序/类型语义。
 *
 * 唯一受控偏差(必须带着这行一起读数字):
 *   原文件用 `_Bool` 声明布尔字段;本文件改用 `uint8_t`(理由:C99 `_Bool`
 *   在部分嵌入式编译器上支持度不确定,而 `_Bool` 在几乎所有实现里 sizeof 恰为 1,
 *   与 uint8_t 等价;若 SHARC 编译器的 _Bool 不是 1 字节,这里的替换会**低估**
 *   差异——回传数字时请一并注明本行,不要吞掉这条注记)。
 *   原文件用 `%zu`(size_t)格式化;本文件为避免嵌入式 libio 对 "z" 长度修饰符的
 *   支持不确定性,一律转 (int) 用 %d 打印(本文件涉及的尺寸都远小于 2^31,
 *   转换不丢信息)。
 *
 * 目的:一次性判定 W1-B §8.2 争的"WORD32 档(经典 SHARC 字寻址,每标量占 32bit)
 *   是否成立"——若 SHARC 编译器给出的 sizeof 明显不同于"字节紧凑打包"的直觉,
 *   本文件会把两种口径(结构体 sizeof 直接乘 通道数 vs 手算 WORD32 上界)都打出来,
 *   不擅自判定哪个对,交回上级判读。
 *
 * 这不是一个"周期数"内核,不需要 clock()/checksum 自检——sizeof 是编译期常量,
 * 编译器没有办法把它"优化掉出错",风险类型与其余四个内核不同。
 *****************************************************************************/
#include "w1c_config.h"

#if ENABLE_MEM_SIZEOF

#include <stdio.h>
#include <stdint.h>
#include "mem_sizeof_check.h"

#define NN     8    /* 陷波槽/通道(DEC-0007.3) */
#define NT    12    /* 跟踪轨上限 */
#define W_MAX 10    /* IMSD 窗上限 */
#define NCH    8    /* 通道数 */
#define C3_KB 16    /* IF-v1.4 C3 内存包络(KB) */

typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32;

/* ---------- A. v1.2 盘面结构(按 §5.5 定义逐字段照抄,_Bool→uint8_t 见文件头) ---------- */
typedef struct { float f[7]; u8 idx; } medfilt7_v12_t;
typedef struct {
  u8 active; float f_hz; medfilt7_v12_t fmed; u16 pair_id;
  float papr_hist[W_MAX]; u32 seq_hist[W_MAX];
  u8 hist_n; u32 t_born, t_last_seen; u8 hits4;
  u16 obs_n, hit_n; u32 t_veto_start; u8 rapid_onset; u8 relaxed_entry;
} Track_v12;
typedef struct {
  u8 mode, st, exec_id;
  float f_hz, bw_oct, depth_db, target_db, base_db;
  u32 t_last_hit, t_lift_start, t_engage;
} NotchSlot_v12;
typedef struct { float f_hz; u32 t_removed; u8 rapid_onset; u32 t_veto_start; u16 persist_credit; } Shadow_v12;
typedef struct { float p[25]; } PresetParams_v12;      /* §6+§2.2+§3.2 计 ≥25 项 */
typedef struct {
  NotchSlot_v12 slot[NN]; Track_v12 trk[NT];
  float g_duck_db; u32 t_duck_quiet; Shadow_v12 shadow[NN];
  u8 gr_valid_prev, lock; PresetParams_v12 P;       /* v1.2:预设参数**按通道各存一份** */
} AfcChannel_v12;

/* ---------- B. v1.3 收窄后结构(四项改动,见 §8.2) ---------- */
typedef struct { u16 f_bin_q6[7]; u8 idx; } medfilt7_v13_t;
typedef struct {
  u8 active; float f_hz; medfilt7_v13_t fmed; u16 pair_id;
  float papr_hist[W_MAX]; u8 seq_delta[W_MAX];
  u8 hist_n; u32 t_born, t_last_seen; u8 hits4;
  u16 obs_n, hit_n; u32 t_veto_start;
  u8 flags;                 /* rapid_onset|relaxed_entry|causal_ok|... 位域打包 */
  u8 miss_run, unobs_run;   /* m-8 / MAJOR-5 */
} Track_v13;
typedef struct { float f_hz; u32 t_removed; u16 obs_credit, hit_credit; u8 flags; } Shadow_v13;
typedef struct {
  NotchSlot_v12 slot[NN]; Track_v13 trk[NT];
  float g_duck_db; u32 t_duck_quiet; Shadow_v13 shadow[NT];  /* 扩到 NT(m-8) */
  u8 gr_valid_prev, lock;
  const PresetParams_v12 *P;   /* 共享指针,不按通道复制;§5.5 已同源(m-3) */
} AfcChannel_v13;

/* 全局(非按通道):跨通道频率登记表 §5.6 */
typedef struct { float f_hz; u32 hop; u8 ch; } RegEntry;
#define NREG 32

/* WORD32 上界(经典 SHARC 字寻址:每个标量域占 32bit)——纯算术,与 sizeof 无关,
 * 照抄host文件,含其 m-4 勘正(v1.3 Track 末组标量数由 9 改 10) */
static int word32_track_v12(void){ return 4*(1+1+7+1+1) + 4*W_MAX + 4*W_MAX + 4*9; }
static int word32_track_v13(void){ return 4*(1+1+7+1+1) + 4*W_MAX + 4*W_MAX + 4*10; }

void mem_sizeof_check_run(FILE *fcsv)
{
    int ch12 = (int)sizeof(AfcChannel_v12);
    int ch13 = (int)sizeof(AfcChannel_v13);
    int glob = (int)sizeof(RegEntry) * NREG;
    int tot12 = ch12 * NCH + glob;
    int tot13 = ch13 * NCH + glob;
    int t12, t13, slot32, sh12_32, sh13_32, preset32;
    long c12, c13, g32, w32_v12, w32_v13;

    printf("\n==== MEM_SIZEOF: SHARC 编译器现场 sizeof(DEC-0014(5)/W1-B (8.2 第三轨)====\n");
    printf("MEM_SIZEOF,struct_sizes,Track_v12=%d,NotchSlot=%d,Shadow_v12=%d,PresetParams=%d,AfcChannel_v12=%d\n",
           (int)sizeof(Track_v12), (int)sizeof(NotchSlot_v12), (int)sizeof(Shadow_v12),
           (int)sizeof(PresetParams_v12), ch12);
    printf("MEM_SIZEOF,struct_sizes,Track_v13=%d,Shadow_v13=%d,AfcChannel_v13=%d\n",
           (int)sizeof(Track_v13), (int)sizeof(Shadow_v13), ch13);
    printf("MEM_SIZEOF,global,RegEntry_x%d=%d\n", NREG, glob);

    printf("MEM_SIZEOF,envelope_C3=%dKB,v1.2_total=%dB(%.2fKB)_%s\n",
           C3_KB, tot12, tot12 / 1024.0, (tot12 > C3_KB * 1024) ? "OVER" : "within");
    printf("MEM_SIZEOF,envelope_C3=%dKB,v1.3_total=%dB(%.2fKB)_%s\n",
           C3_KB, tot13, tot13 / 1024.0, (tot13 > C3_KB * 1024) ? "OVER" : "within");

    t12 = word32_track_v12(); t13 = word32_track_v13();
    slot32 = 4 * 11; sh12_32 = 4 * 5; sh13_32 = 4 * 5; preset32 = 4 * 25;
    c12 = (long)slot32 * NN + (long)t12 * NT + 4 * 2 + (long)sh12_32 * NN + 4 * 2 + preset32;
    c13 = (long)slot32 * NN + (long)t13 * NT + 4 * 2 + (long)sh13_32 * NT + 4 * 2 + 4;
    g32 = 4L * 3 * NREG;
    w32_v12 = c12 * NCH + g32;
    w32_v13 = c13 * NCH + g32;

    printf("MEM_SIZEOF,WORD32_upper_bound,v1.2=%ldB(%.2fKB)_%s,v1.3=%ldB(%.2fKB)_%s\n",
           w32_v12, w32_v12 / 1024.0, (w32_v12 > (long)C3_KB * 1024) ? "OVER" : "within",
           w32_v13, w32_v13 / 1024.0, (w32_v13 > (long)C3_KB * 1024) ? "OVER" : "within");

    if (fcsv) {
        fprintf(fcsv, "MEM_SIZEOF,AfcChannel_v12,%d\n", ch12);
        fprintf(fcsv, "MEM_SIZEOF,AfcChannel_v13,%d\n", ch13);
        fprintf(fcsv, "MEM_SIZEOF,v1.2_total_B,%d\n", tot12);
        fprintf(fcsv, "MEM_SIZEOF,v1.3_total_B,%d\n", tot13);
        fprintf(fcsv, "MEM_SIZEOF,WORD32_v1.2_B,%ld\n", w32_v12);
        fprintf(fcsv, "MEM_SIZEOF,WORD32_v1.3_B,%ld\n", w32_v13);
    }
}

#else /* !ENABLE_MEM_SIZEOF */

void mem_sizeof_check_run(FILE *fcsv)
{
    printf("MEM_SIZEOF,DISABLED,-  (see w1c_config.h ENABLE_MEM_SIZEOF)\n");
    if (fcsv) fprintf(fcsv, "MEM_SIZEOF,DISABLED,-\n");
}

#endif /* ENABLE_MEM_SIZEOF */
