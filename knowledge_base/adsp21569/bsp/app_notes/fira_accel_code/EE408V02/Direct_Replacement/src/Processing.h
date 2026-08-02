#ifndef __PROCESSING_H__
#define __PROCESSING_H__

#include <sys/platform.h>
#include "adi_initialize.h"
#include <drivers/fir/adi_fir.h>
#include <drivers/iir/adi_iir.h>
#include "stdio.h"
#include "stdlib.h"
#include "time.h"
#include "filter.h"

#define BLOCK_SIZE 256									/* Block Size */
#define CIRCULAR_BUFFER_LENGTH 768						/* Circular buffer length for FIR - should be greater than of equal to  BLOCK_SIZE+FIR_TAPS  and multiple of BLOCK_SIZE*/
#define WP_START   CIRCULAR_BUFFER_LENGTH-BLOCK_SIZE	/* Write pointer start, start filling the delay line buffer from this pointer onwards and increment the write pointer by BLOCK_SIZE for each new block */
#define FIRA_INDEX_START (WP_START-FIR_TAPS+1)			/* FIRA start address should be initialized with this value */
#define NCH		   12									/* Total number of channels */
#define FIR_TAPS   512									/* FIR TAPS */
#define IIR_BANDS  5									/* IIR bands */
#define NSECTIONS  4									/* Number of biquad stages per IIR band */

//#define USE_CORE				/* Uncomment this macro to process all the 12 channels using core */
#define USE_ACC					/* Uncomment this macro to process all the 12 channels using accelerator */

/* Macro for checking Result returned by the driver after API call */
#define CHECK_FIR_RESULT(eResult) \
        if(eResult != ADI_FIR_RESULT_SUCCESS)\
		{\
            printf("CHECK_RESULT failed at line %d of file %s \n",__LINE__,__FILE__);\
            exit(-2);\
       }
/* Macro for checking Result returned by the driver after API call */
#define CHECK_IIR_RESULT(eResult) \
        if(eResult != ADI_IIR_RESULT_SUCCESS)\
		{\
            printf("CHECK_RESULT failed at line %d of file %s \n",__LINE__,__FILE__);\
            exit(-2);\
        }
/* Macro to start cycle count */
#define START_CYCLE_COUNT\
		cycle_count=0;\
		clock_start = clock();\

/* Macro to take cycle snapshot */
#define TAKE_CYCLE_SNAPSHOT\
	clock_stop = clock();\
	cycles_array[cycle_count] = clock_stop - clock_start;\
	cycle_count++;\
	cycle_count=cycle_count%100;\
	clock_start = clock_stop;

extern float Input[NCH][CIRCULAR_BUFFER_LENGTH];
extern float Output[NCH][BLOCK_SIZE];
extern volatile int cycle_count;
extern volatile int cycles_array[100];
extern volatile int clock_stop;
extern volatile int clock_start;

/* Function for one time initialization required for FIR/IIR processing */
void Init_FIR_IIR(void);

/* Function for FIR/IIR processing */
void Process_FIR_IIR(void);
#endif
