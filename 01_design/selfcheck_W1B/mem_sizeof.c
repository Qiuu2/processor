/* W1-B §8.2 内存对账的**第二轨**(MAJOR-3 修法要求:手算之外的独立路径)
 * adaptive-dsp(第 3 实例)· 2026-08-01 · [L2/桌面数值]
 *
 * 目的:用编译器实际布局(含对齐填充)复核 §8.2 的内存数,取代 v1.2 的手估 ≈14KB。
 * 定级声明:本文件在 **x86-64 / gcc** 上求值,是**宿主代理**,不是目标板数字。
 *   目标平台 ADSP-21569(SHARC+)的 char/short 宽度与对齐规则须由 W1-C 工具链确认
 *   —— 经典 SHARC 为**字寻址**(char 亦占 32bit),若本项目工具链落此档,
 *   下方 "WORD32" 列才是有效上界。两列都报,不挑对自己有利的那列。
 *
 * 编译:gcc -O0 -Wall -o mem_sizeof mem_sizeof.c && ./mem_sizeof
 */
#include <stdio.h>
#include <stdint.h>

#define NN     8    /* 陷波槽/通道(DEC-0007.3) */
#define NT    12    /* 跟踪轨上限 */
#define W_MAX 10    /* IMSD 窗上限 */
#define NCH    8    /* 通道数 */
#define C3_KB 16    /* IF-v1.4 C3 内存包络(KB) */

typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32;

/* ---------- A. v1.2 盘面结构(按 §5.5 定义逐字段照抄) ---------- */
typedef struct { float f[7]; u8 idx; } medfilt7_v12_t;
typedef struct {
  _Bool active; float f_hz; medfilt7_v12_t fmed; u16 pair_id;
  float papr_hist[W_MAX]; u32 seq_hist[W_MAX];
  u8 hist_n; u32 t_born, t_last_seen; u8 hits4;
  u16 obs_n, hit_n; u32 t_veto_start; _Bool rapid_onset; _Bool relaxed_entry;
} Track_v12;
typedef struct {
  u8 mode, st, exec_id;
  float f_hz, bw_oct, depth_db, target_db, base_db;
  u32 t_last_hit, t_lift_start, t_engage;
} NotchSlot_v12;
typedef struct { float f_hz; u32 t_removed; _Bool rapid_onset; u32 t_veto_start; u16 persist_credit; } Shadow_v12;
typedef struct { float p[25]; } PresetParams_v12;      /* §6+§2.2+§3.2 计 ≥25 项 */
typedef struct {
  NotchSlot_v12 slot[NN]; Track_v12 trk[NT];
  float g_duck_db; u32 t_duck_quiet; Shadow_v12 shadow[NN];
  _Bool gr_valid_prev, lock; PresetParams_v12 P;       /* v1.2:预设参数**按通道各存一份** */
} AfcChannel_v12;

/* ---------- B. v1.3 收窄后结构(四项改动,见 §8.2) ---------- */
/* ①seq_hist u32[10] → u8 增量[10](窗内空号已被 §2.2 门限约束,u8 足量)
   ②medfilt7 float[7] → u16[7](bin×64 定点;主谱 bin 索引 ≤ 上限,u16 足量)
   ③PresetParams 按通道各存一份 → 共享预设库指针(预设是参数包,不随通道变)
   ④Track 增 miss_run(m-8:连续未观测/未命中计数,原规则在给出状态上不可实现)
      与 unobs_run;Shadow 扩到 NT 条并加 causal_ok(MAJOR-1/2 修法所需) */
typedef struct { u16 f_bin_q6[7]; u8 idx; } medfilt7_v13_t;
typedef struct {
  _Bool active; float f_hz; medfilt7_v13_t fmed; u16 pair_id;
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
  _Bool gr_valid_prev, lock;
  const PresetParams_v12 *P;   /* 共享指针,不按通道复制;§5.5 已同源(m-3) */
} AfcChannel_v13;

/* 全局(非按通道):跨通道频率登记表 §5.6 */
typedef struct { float f_hz; u32 hop; u8 ch; } RegEntry;
#define NREG 32

/* 字寻址(经典 SHARC)上界:每个标量域占 32bit,数组按元素计 32bit
 * ⚠ m-4 勘正(critic-w1b-r3):v1.3 版本此二函数**函数体完全相同**,末组均按 9 个标量计;
 *   而 v1.3 的 Track 末组实为 **10 个**(增 miss_run/unobs_run,flags 替 2 个 bool)
 *   ⇒ WORD32 档 v1.3 少算 4B×NT×NCH = 384B。**第二轨自身的算术必须与结构同源。**
 *   ("仍越界"的结论不变,方向 = 低估。) */
/* v1.2 Track 末组标量:hist_n,t_born,t_last_seen,hits4,obs_n,hit_n,t_veto_start,
 *                      rapid_onset,relaxed_entry = 9 */
static int word32_track_v12(void){ return 4*(1+1+7+1+1) + 4*W_MAX + 4*W_MAX + 4*9; }
/* v1.3 Track 末组标量:hist_n,t_born,t_last_seen,hits4,obs_n,hit_n,t_veto_start,
 *                      miss_run,unobs_run,flags = 10 */
static int word32_track_v13(void){ return 4*(1+1+7+1+1) + 4*W_MAX + 4*W_MAX + 4*10; }

int main(void){
  size_t ch12 = sizeof(AfcChannel_v12), ch13 = sizeof(AfcChannel_v13);
  size_t glob  = sizeof(RegEntry)*NREG;
  size_t tot12 = ch12*NCH + glob, tot13 = ch13*NCH + glob;

  printf("=== 结构尺寸(gcc x86-64 默认对齐;宿主代理,非目标板)===\n");
  printf("  [v1.2 盘面] Track=%zuB  NotchSlot=%zuB  Shadow=%zuB  PresetParams=%zuB  AfcChannel=%zuB\n",
         sizeof(Track_v12), sizeof(NotchSlot_v12), sizeof(Shadow_v12), sizeof(PresetParams_v12), ch12);
  printf("  [v1.3 收窄] Track=%zuB  NotchSlot=%zuB  Shadow=%zuB  AfcChannel=%zuB\n",
         sizeof(Track_v13), sizeof(NotchSlot_v12), sizeof(Shadow_v13), ch13);
  printf("  全局登记表(%d 条)=%zuB\n\n", NREG, glob);

  printf("=== 对 IF-v1.4 C3 包络(%d KB = %d B)===\n", C3_KB, C3_KB*1024);
  printf("  v1.2 总计 = %zuB×%d + %zuB = %zuB = %.2f KB  -> 占包络 %.1f%%  %s\n",
         ch12, NCH, glob, tot12, tot12/1024.0, 100.0*tot12/(C3_KB*1024.0),
         tot12 > (size_t)C3_KB*1024 ? "**越界**" : "在包络内");
  printf("  v1.3 总计 = %zuB×%d + %zuB = %zuB = %.2f KB  -> 占包络 %.1f%%  %s\n",
         ch13, NCH, glob, tot13, tot13/1024.0, 100.0*tot13/(C3_KB*1024.0),
         tot13 > (size_t)C3_KB*1024 ? "**越界**" : "在包络内");
  printf("  v1.3 相对 v1.2 节省 = %zuB = %.2f KB\n\n", tot12-tot13, (tot12-tot13)/1024.0);

  printf("=== WORD32 上界(经典 SHARC 字寻址:每标量占 32bit)===\n");
  {
    int t12 = word32_track_v12(), t13 = word32_track_v13();
    int slot32 = 4*11, sh12_32 = 4*5, sh13_32 = 4*5, preset32 = 4*25;
    long c12 = (long)slot32*NN + (long)t12*NT + 4*2 + (long)sh12_32*NN + 4*2 + preset32;
    long c13 = (long)slot32*NN + (long)t13*NT + 4*2 + (long)sh13_32*NT + 4*2 + 4;
    long g32 = 4*3*NREG;
    printf("  v1.2 = %ldB = %.2f KB  %s\n", c12*NCH+g32, (c12*NCH+g32)/1024.0,
           (c12*NCH+g32) > C3_KB*1024L ? "**越界**" : "在包络内");
    printf("  v1.3 = %ldB = %.2f KB  %s\n", c13*NCH+g32, (c13*NCH+g32)/1024.0,
           (c13*NCH+g32) > C3_KB*1024L ? "**越界**" : "在包络内");
    printf("  注:WORD32 下 ①seq_hist u8 化与 ②medfilt u16 化**不产生节省**(标量仍占 32bit),\n");
    printf("      仅 ③预设共享 有效 ⇒ **该档下必须走 IF-v1.4 C9 与提供方重议 C3,或降 NT/W_MAX**。\n");
  }
  return 0;
}
