/*****************************************************************************
 * mem_sizeof_check.h
 *****************************************************************************/
#ifndef MEM_SIZEOF_CHECK_H
#define MEM_SIZEOF_CHECK_H

#include <stdio.h>

void mem_sizeof_check_run(FILE *fcsv);

/* 时钟树回读 + 基本类型 sizeof。见 w1c_config.h 的 ENABLE_CLK_READBACK。 */
void w1c_clk_readback_run(FILE *fcsv);

#endif /* MEM_SIZEOF_CHECK_H */
