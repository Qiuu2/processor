/** @file emit_bitexact.c  写出 C 轨的逐位输出,供 ref_modules.py 对表。⛔ 未过门。 */
#include "chdsp_biquad.h"
#include "chdsp_detector.h"
#include <stdio.h>
#include <math.h>
static uint32_t g=0xFEEDBEEFu;
static uint32_t r32(void){g^=g<<13;g^=g>>17;g^=g<<5;return g;}
int main(void){
    chdsp_biquad_coef_t c; chdsp_bq_t b; chdsp_sat_t s; chdsp_det_t d;
    FILE *fi=fopen("bitexact_bq_in.txt","w"), *fo=fopen("bitexact_bq_out.txt","w");
    FILE *fd=fopen("bitexact_det_out.txt","w");
    int i; int32_t xs[20000];
    if(!fi||!fo||!fd) return 2;
    for(i=0;i<20000;i++){ xs[i]=(int32_t)(r32()>>6)-(int32_t)(1<<25); fprintf(fi,"%d\n",xs[i]); }
    if (chdsp_bq_design(CHDSP_FT_PEAKING,1000.0,1.4,6.0,&c)!=0) return 3;
    chdsp_bq_init(&b); chdsp_bq_set_coef_now(&b,&c); b.bypass=0u; chdsp_sat_reset(&s);
    for(i=0;i<20000;i++) fprintf(fo,"%d\n",chdsp_smp_raw(chdsp_bq_process1(&b,chdsp_smp_from_raw(xs[i]),&s)));
    chdsp_det_init(&d,CHDSP_DET_RMS,10.0,100.0);
    for(i=0;i<20000;i++) fprintf(fd,"%lld\n",(long long)chdsp_pow_raw(chdsp_det_process1(&d,chdsp_smp_from_raw(xs[i]))));
    fclose(fi);fclose(fo);fclose(fd);
    printf("已写出 bitexact_{bq_in,bq_out,det_out}.txt\n");
    return 0;
}
