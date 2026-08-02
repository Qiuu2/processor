/*****************************************************************************
 * t1a_biquad.h
 *****************************************************************************/
#ifndef T1A_BIQUAD_H
#define T1A_BIQUAD_H

#include <stdio.h>

/* 跑 T1a 全部测量,把每一行同时打到 Console(printf)和 CSV(fcsv,可为 NULL)。 */
void t1a_biquad_run(FILE *fcsv);

#endif /* T1A_BIQUAD_H */
