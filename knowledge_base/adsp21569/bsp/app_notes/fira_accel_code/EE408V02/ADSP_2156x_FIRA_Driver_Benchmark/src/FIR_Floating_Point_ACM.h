/*****************************************************************************
 * FIR_Flaoting_Point_ACM.h
 *****************************************************************************/

#ifndef __FIR_FLAOTING_POINT_ACM_H__
#define __FIR_FLAOTING_POINT_ACM_H__

/* Number of Taps 1. Note that Tap length can be varied across channels in a task.*/
#define TAPS1    64

/* Window Size. Note that Window size can be varied across channels in a task */
#define FIR_WINDOW_SIZE    256

/* Number of FIR Tasks */
#define FIR_NUMBER_OF_TASKS 6

/* Number of Channels in FIR task 1 */
#define FIR_NUMBER_OF_CHANNELS_TASK1 1

#define FIR_NUMBER_OF_CHANNELS_TASK2 2

#define FIR_NUMBER_OF_CHANNELS_TASK3 3

#define FIR_NUMBER_OF_CHANNELS_TASK4 4

#define FIR_NUMBER_OF_CHANNELS_TASK5 2

#define FIR_NUMBER_OF_CHANNELS_TASK6 2

/* Total Number of Channels */
#define FIR_NUMBER_OF_CHANNELS    (FIR_NUMBER_OF_CHANNELS_TASK1 + FIR_NUMBER_OF_CHANNELS_TASK2 + FIR_NUMBER_OF_CHANNELS_TASK3 + FIR_NUMBER_OF_CHANNELS_TASK4 + FIR_NUMBER_OF_CHANNELS_TASK5 + FIR_NUMBER_OF_CHANNELS_TASK6)

/* FIR Task 1 Memory Size */
#define FIR_MEM_SIZE_TASK1    (FIR_MEM_SIZE(FIR_NUMBER_OF_CHANNELS_TASK1))

#define FIR_MEM_SIZE_TASK2    (FIR_MEM_SIZE(FIR_NUMBER_OF_CHANNELS_TASK2))

#define FIR_MEM_SIZE_TASK3    (FIR_MEM_SIZE(FIR_NUMBER_OF_CHANNELS_TASK3))

#define FIR_MEM_SIZE_TASK4    (FIR_MEM_SIZE(FIR_NUMBER_OF_CHANNELS_TASK4))

#define FIR_MEM_SIZE_TASK5    (FIR_MEM_SIZE(FIR_NUMBER_OF_CHANNELS_TASK5))

#define FIR_MEM_SIZE_TASK6    (FIR_MEM_SIZE(FIR_NUMBER_OF_CHANNELS_TASK6))

/* Macro for checking Result returned by the driver after API call */
#define CHECK_FIR_RESULT(eResult) \
        if(eResult != ADI_FIR_RESULT_SUCCESS)\
		{\
            printf("CHECK_RESULT failed at line %d of file %s \n",__LINE__,__FILE__);\
            exit(-2);\
        }

#define CREATE_TASK_BENCHMARK        (1)
#define QUEUE_TASK_BENCHMARK         (0)
#define INTERRUPT_LATENCY_BENCHMARK  (0)

#if ((CREATE_TASK_BENCHMARK == 1) || (QUEUE_TASK_BENCHMARK == 1) || (INTERRUPT_LATENCY_BENCHMARK == 1) )
#include <time.h>

#define CYCLES_ARRAY_SIZE (3000)
volatile int cycle_count;
volatile int cycles_array[CYCLES_ARRAY_SIZE];
volatile clock_t clock_stop;
volatile clock_t clock_start;
volatile int int_latency[50];
volatile int lat_idx = 0;

#define START_CYCLE_COUNT\
		cycle_count=0;\
		clock_start = clock();

#define TAKE_CYCLE_SNAPSHOT\
	clock_stop = clock();\
	cycles_array[cycle_count] = clock_stop - clock_start;\
	cycle_count++;\
	clock_start = clock_stop;\

#endif /* (CREATE_TASK_BENCHMARK == 1 || QUEUE_TASK_BENCHMARK == 1 || INTERRUPT_LATENCY_BENCHMARK == 1 ) */

#if (((CREATE_TASK_BENCHMARK == 1) && (QUEUE_TASK_BENCHMARK == 1) && (INTERRUPT_LATENCY_BENCHMARK == 1)) != 0 )
#error "Benchmark macros incorrectly configured"
#endif /* (((CREATE_TASK_BENCHMARK == 1) && (QUEUE_TASK_BENCHMARK == 1) && (INTERRUPT_LATENCY_BENCHMARK == 1)) != 0 ) */

#endif /* __FIR_FLAOTING_POINT_ACM_H__ */
