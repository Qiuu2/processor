/** @file emit_bitexact.c  写出 C 轨的逐位输出,供 ref_modules.py 对表。⛔ 未过门。 */
#include "chdsp_biquad.h"
#include "chdsp_detector.h"
#include "chdsp_dynamics.h"
#include <stdio.h>
#include <math.h>
static uint32_t g=0xFEEDBEEFu;
static uint32_t r32(void){g^=g<<13;g^=g>>17;g^=g<<5;return g;}
int main(void){
    chdsp_biquad_coef_t c; chdsp_bq_t b; chdsp_sat_t s; chdsp_det_t d;
    FILE *fi=fopen("bitexact_bq_in.txt","w"), *fo=fopen("bitexact_bq_out.txt","w");
    FILE *fd=fopen("bitexact_det_out.txt","w");
    /* ⭐ 整改 2026-08-04 · critic MAJOR-2:docstring 承诺「③限幅器增益 dB 逐位」,
     * 而限幅器数据**从来没有被导出过** ⇒ 第三条对表项在物理上不存在。现补上。
     * ⚠ 限幅器恰是有变异的模块(LIM_NOLOOK),且其前视缓冲是唯一直接进延迟预算的一项。 */
    FILE *fl=fopen("bitexact_lim_gdb.txt","w");
    static chdsp_smp_q4_27_t look[4096];
    chdsp_limiter_t L; chdsp_db_q23_8_t gdb;
    int i; int32_t xs[20000];
    if(!fi||!fo||!fd||!fl) return 2;
    for(i=0;i<20000;i++){ xs[i]=(int32_t)(r32()>>6)-(int32_t)(1<<25); fprintf(fi,"%d\n",xs[i]); }
    if (chdsp_bq_design(CHDSP_FT_PEAKING,1000.0,1.4,6.0,&c)!=0) return 3;
    chdsp_bq_init(&b); chdsp_bq_set_coef_now(&b,&c); b.bypass=0u; chdsp_sat_reset(&s);
    for(i=0;i<20000;i++) fprintf(fo,"%d\n",chdsp_smp_raw(chdsp_bq_process1(&b,chdsp_smp_from_raw(xs[i]),&s)));
    chdsp_det_init(&d,CHDSP_DET_RMS,10.0,100.0);
    for(i=0;i<20000;i++) fprintf(fd,"%lld\n",(long long)chdsp_pow_raw(chdsp_det_process1(&d,chdsp_smp_from_raw(xs[i]))));
    /* ③ 限幅器:同一激励下逐样本的**增益 dB**(Q23.8 raw) */
    if (chdsp_limiter_init(&L, look, (uint32_t)(sizeof(look)/sizeof(look[0])),
                           -6.0, 1.0, 50.0) != 0) { return 4; }
    L.enabled = 1u; chdsp_sat_reset(&s);
    for(i=0;i<20000;i++){
        (void)chdsp_limiter_process1(&L, chdsp_smp_from_raw(xs[i]), &s, &gdb);
        fprintf(fl,"%d\n",(int)chdsp_db_raw(gdb));
    }
    fclose(fi);fclose(fo);fclose(fd);fclose(fl);
    printf("已写出 bitexact_{bq_in,bq_out,det_out,lim_gdb}.txt\n");
    return 0;
}
