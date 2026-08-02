/*****************************************************************************
 * IIR_Floating_Point_ACM.h
 *****************************************************************************/

#ifndef __IIR_FLOATING_POINT_ACM_H__
#define __IIR_FLOATING_POINT_ACM_H__

/* Biquads. Note that Biquad number can be varied across channels of a task*/
#define BIQUADS   8

/* Window Size. Note that Window size can be varied across channels in a task */
#define IIR_WINDOW_SIZE    128

/* Number of IIR Tasks */
#define IIR_NUMBER_OF_TASKS    6

/* Number of Channels in IIR task 1 */
#define IIR_NUMBER_OF_CHANNELS_TASK1    1

/* Number of Channels in IIR task 2 */
#define IIR_NUMBER_OF_CHANNELS_TASK2    2

#define IIR_NUMBER_OF_CHANNELS_TASK3    3

#define IIR_NUMBER_OF_CHANNELS_TASK4    4

#define IIR_NUMBER_OF_CHANNELS_TASK5    2

#define IIR_NUMBER_OF_CHANNELS_TASK6    2

/* Total Number of Channels */
#define IIR_NUMBER_OF_CHANNELS    (IIR_NUMBER_OF_CHANNELS_TASK1 + IIR_NUMBER_OF_CHANNELS_TASK2 + IIR_NUMBER_OF_CHANNELS_TASK3 + IIR_NUMBER_OF_CHANNELS_TASK4 + IIR_NUMBER_OF_CHANNELS_TASK5 + IIR_NUMBER_OF_CHANNELS_TASK6)

/* IIR Task 1 Memory Size */
#define IIR_MEM_SIZE_TASK1    (IIR_MEM_SIZE(IIR_NUMBER_OF_CHANNELS_TASK1))

/* IIR Task 2 Memory Size */
#define IIR_MEM_SIZE_TASK2    (IIR_MEM_SIZE(IIR_NUMBER_OF_CHANNELS_TASK2))

#define IIR_MEM_SIZE_TASK3    (IIR_MEM_SIZE(IIR_NUMBER_OF_CHANNELS_TASK3))

#define IIR_MEM_SIZE_TASK4    (IIR_MEM_SIZE(IIR_NUMBER_OF_CHANNELS_TASK4))

#define IIR_MEM_SIZE_TASK5    (IIR_MEM_SIZE(IIR_NUMBER_OF_CHANNELS_TASK5))

#define IIR_MEM_SIZE_TASK6    (IIR_MEM_SIZE(IIR_NUMBER_OF_CHANNELS_TASK6))

/* Macro for checking Result returned by the driver after API call */
#define CHECK_IIR_RESULT(eResult) \
        if(eResult != ADI_IIR_RESULT_SUCCESS)\
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

#endif /* __IIR_FLOATING_POINT_ACM_H__ */
