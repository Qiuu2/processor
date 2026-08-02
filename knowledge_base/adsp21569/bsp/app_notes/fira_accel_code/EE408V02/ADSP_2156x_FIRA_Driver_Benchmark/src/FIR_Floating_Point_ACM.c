/*****************************************************************************
 * FIR_Flaoting_Point_ACM.c
 *
 * This example is used to measure the FIRA Device Driver Benchmarks for Legacy and ACM Mode.
 * In  this example, 6 FIR tasks are created and Queued to the accelerator and the driver benchmarks
 * are measured. The measurement is to provide estimate of the driver benchmarks/overheads.
 *
 * Three macros are provided in the header file(FIR_Floating_Point_ACM.h) to measure three types of benchmarks
 *
 * - CREATE_TASK_BENCHMARK : Set this macro to 1 to measure the benchmarks for adi_fir_CreateTask() API.
 * - QUEUE_TASK_BENCHMARK : Set this macro to 1 to measure the benchmarks for adi_fir_QueueTask() API.
 * - INTERRUPT_LATENCY_BENCHMARK: Set this macro to 1 to measure the Interrupt Latency Overhead.Note that the measurement
 *                                involves the total interrupt round trip time including the SEC dispatcher,driver interrupt handler
 *                                and Callback.
 *
 * At a time, only one of the three above mentioned macros can be set to 1.
 *
 *****************************************************************************/

#include <sys/platform.h>
#include "adi_initialize.h"
#include "FIR_Floating_Point_ACM.h"
#include <drivers/fir/adi_fir.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>


/**
 * If you want to use command program arguments, then place them in the following string.
 */
char __argv_string[] = "";

float FirInputBuff1[TAPS1+FIR_WINDOW_SIZE-1];

float CoeffBuff1[TAPS1];

float FirOutputBuff1[FIR_WINDOW_SIZE];

#pragma align 32
uint8_t FirTask1Memory[FIR_MEM_SIZE_TASK1];

#pragma align 32
uint8_t FirTask2Memory[FIR_MEM_SIZE_TASK2];

#pragma align 32
uint8_t FirTask3Memory[FIR_MEM_SIZE_TASK3];


#pragma align 32
uint8_t FirTask4Memory[FIR_MEM_SIZE_TASK4];

#pragma align 32
uint8_t FirTask5Memory[FIR_MEM_SIZE_TASK5];

#pragma align 32
uint8_t FirTask6Memory[FIR_MEM_SIZE_TASK6];

ADI_FIR_DEV_HANDLE hFir;

ADI_FIR_TASK_HANDLE hFirTasks[FIR_NUMBER_OF_TASKS] = {0};

volatile uint32_t FIRTaskDoneCount = 0;
volatile void *FIRCompletedTaskHandles[20] = {0};
void FIRTaskDoneCallback( void * pCBParam, ADI_FIR_EVENT Event, void * pArg);
void PrintCallbackHandles(volatile void *pCompletedTaskHandles, volatile uint32_t TaskDoneCount);

void FIRTaskDoneCallback( void * pCBParam, ADI_FIR_EVENT Event, void * pArg)
{
	switch(Event)
	{
#if  ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM
	    case ADI_FIR_EVENT_CHANNEL_DONE:
#else
	    case ADI_FIR_EVENT_ALL_CHANNEL_DONE:
#endif
	    	FIRCompletedTaskHandles[FIRTaskDoneCount++] = pArg;
	}
}

volatile int count = 0;

int main(int argc, char *argv[])
{
	/**
	 * Initialize managed drivers and/or services that have been added to
	 * the project.
	 * @return zero on success
	 */
	adi_initComponents();

    ADI_FIR_RESULT eFirResult = ADI_FIR_RESULT_SUCCESS;

	ADI_FIR_CHANNEL_INFO FirTask_Channels[4] = {

			{
			    TAPS1,                                                      /* Tap Length */
				FIR_WINDOW_SIZE,                                            /* Window Size */
				ADI_FIR_SAMPLING_SINGLE_RATE,                               /* Sampling */
				1,                                                          /* Sampling Ratio */
#if  ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM
				true,                                                       /* Callback Enable */
				false,                                                      /* Generate Trigger on completion */
				false,                                                      /* Wait for Trigger */
				ADI_FIR_FLOAT_ROUNDING_MODE_IEEE_ROUND_TO_NEAREST_EVEN,     /* Rounding Mode */
				false,                                                      /* Fixed point enable */
				ADI_FIR_FIXED_INPUT_FORMAT_UNSIGNED_INTEGER,                /* Fixed Point format */
#endif /* MODE == ACM */
				TAPS1,                                                      /* Coefficient Count */
				1,                                                          /* Coefficient Modify */
				(void *)CoeffBuff1,                                         /* Coefficient Index */
		        (void *)FirOutputBuff1,                                     /* Output Base */
				FIR_WINDOW_SIZE,                                            /* Output Count */
				1,                                                          /* Output Modify */
				(void *)FirOutputBuff1,                                     /* Output Index */
		        (void *)FirInputBuff1,                                      /* Input Base */
				TAPS1+FIR_WINDOW_SIZE-1,                                    /* Input Count */
				1,                                                          /* Input Modify */
				(void *)FirInputBuff1                                       /* Input Count */

			},
			{
			    TAPS1,                                                      /* Tap Length */
				FIR_WINDOW_SIZE,                                            /* Window Size */
				ADI_FIR_SAMPLING_SINGLE_RATE,                               /* Sampling */
				1,                                                          /* Sampling Ratio */
#if  ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM
				true,                                                       /* Callback Enable */
				false,                                                      /* Generate Trigger on completion */
				false,                                                      /* Wait for Trigger */
				ADI_FIR_FLOAT_ROUNDING_MODE_IEEE_ROUND_TO_NEAREST_EVEN,     /* Rounding Mode */
				false,                                                      /* Fixed point enable */
				ADI_FIR_FIXED_INPUT_FORMAT_UNSIGNED_INTEGER,                /* Fixed Point format */
#endif /* MODE == ACM */
				TAPS1,                                                      /* Coefficient Count */
				1,                                                          /* Coefficient Modify */
				(void *)CoeffBuff1,                                         /* Coefficient Index */
		        (void *)FirOutputBuff1,                                     /* Output Base */
				FIR_WINDOW_SIZE,                                            /* Output Count */
				1,                                                          /* Output Modify */
				(void *)FirOutputBuff1,                                     /* Output Index */
		        (void *)FirInputBuff1,                                      /* Input Base */
				TAPS1+FIR_WINDOW_SIZE-1,                                    /* Input Count */
				1,                                                          /* Input Modify */
				(void *)FirInputBuff1                                       /* Input Count */

			},
			{
			    TAPS1,                                                      /* Tap Length */
				FIR_WINDOW_SIZE,                                            /* Window Size */
				ADI_FIR_SAMPLING_SINGLE_RATE,                               /* Sampling */
				1,                                                          /* Sampling Ratio */
#if  ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM
				true,                                                       /* Callback Enable */
				false,                                                      /* Generate Trigger on completion */
				false,                                                      /* Wait for Trigger */
				ADI_FIR_FLOAT_ROUNDING_MODE_IEEE_ROUND_TO_NEAREST_EVEN,     /* Rounding Mode */
				false,                                                      /* Fixed point enable */
				ADI_FIR_FIXED_INPUT_FORMAT_UNSIGNED_INTEGER,                /* Fixed Point format */
#endif /* MODE == ACM */
				TAPS1,                                                      /* Coefficient Count */
				1,                                                          /* Coefficient Modify */
				(void *)CoeffBuff1,                                         /* Coefficient Index */
		        (void *)FirOutputBuff1,                                     /* Output Base */
				FIR_WINDOW_SIZE,                                            /* Output Count */
				1,                                                          /* Output Modify */
				(void *)FirOutputBuff1,                                     /* Output Index */
		        (void *)FirInputBuff1,                                      /* Input Base */
				TAPS1+FIR_WINDOW_SIZE-1,                                    /* Input Count */
				1,                                                          /* Input Modify */
				(void *)FirInputBuff1                                       /* Input Count */

			},
			{
			    TAPS1,                                                      /* Tap Length */
				FIR_WINDOW_SIZE,                                            /* Window Size */
				ADI_FIR_SAMPLING_SINGLE_RATE,                               /* Sampling */
				1,                                                          /* Sampling Ratio */
#if  ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM
				true,                                                       /* Callback Enable */
				false,                                                      /* Generate Trigger on completion */
				false,                                                      /* Wait for Trigger */
				ADI_FIR_FLOAT_ROUNDING_MODE_IEEE_ROUND_TO_NEAREST_EVEN,     /* Rounding Mode */
				false,                                                      /* Fixed point enable */
				ADI_FIR_FIXED_INPUT_FORMAT_UNSIGNED_INTEGER,                /* Fixed Point format */
#endif /* MODE == ACM */
				TAPS1,                                                      /* Coefficient Count */
				1,                                                          /* Coefficient Modify */
				(void *)CoeffBuff1,                                         /* Coefficient Index */
		        (void *)FirOutputBuff1,                                     /* Output Base */
				FIR_WINDOW_SIZE,                                            /* Output Count */
				1,                                                          /* Output Modify */
				(void *)FirOutputBuff1,                                     /* Output Index */
		        (void *)FirInputBuff1,                                      /* Input Base */
				TAPS1+FIR_WINDOW_SIZE-1,                                    /* Input Count */
				1,                                                          /* Input Modify */
				(void *)FirInputBuff1                                       /* Input Count */

			}

	};

	/* Open the FIR Device */
    eFirResult  = adi_fir_Open(0u,&hFir);
    CHECK_FIR_RESULT(eFirResult)

    eFirResult = adi_fir_RegisterCallback(hFir,FIRTaskDoneCallback,0);
    CHECK_FIR_RESULT(eFirResult)

    START_CYCLE_COUNT

#if (ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM)
	FirTask_Channels[0].bCallbackEnable = true;
#endif /* (ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM) */
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */
    eFirResult = adi_fir_CreateTask(hFir, /* Device Handle*/
    		FirTask_Channels,            /* Pointer to Channel List */
			FIR_NUMBER_OF_CHANNELS_TASK1, /* Number of Channels  */
			&FirTask1Memory,              /* Pointer to Memory */
			FIR_MEM_SIZE_TASK1,           /*Memory Size */
			&hFirTasks[0]);               /* Address to store the handle */
    CHECK_FIR_RESULT(eFirResult)
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */

#if (ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM)
	FirTask_Channels[0].bCallbackEnable = false;
    FirTask_Channels[1].bCallbackEnable = true;
#endif /* (ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM) */
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */
    eFirResult = adi_fir_CreateTask(hFir, /* Device Handle*/
    		FirTask_Channels,            /* Pointer to Channel List */
			FIR_NUMBER_OF_CHANNELS_TASK2, /* Number of Channels  */
			&FirTask2Memory,              /* Pointer to Memory */
			FIR_MEM_SIZE_TASK2,           /*Memory Size */
			&hFirTasks[1]);               /* Address to store the handle */
    CHECK_FIR_RESULT(eFirResult)
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */

#if (ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM)
	FirTask_Channels[0].bCallbackEnable = false;
    FirTask_Channels[1].bCallbackEnable = false;
    FirTask_Channels[2].bCallbackEnable = true;
#endif /* (ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM) */
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */
    eFirResult = adi_fir_CreateTask(hFir, /* Device Handle*/
    		FirTask_Channels,            /* Pointer to Channel List */
			FIR_NUMBER_OF_CHANNELS_TASK3, /* Number of Channels  */
			&FirTask3Memory,              /* Pointer to Memory */
			FIR_MEM_SIZE_TASK3,           /*Memory Size */
			&hFirTasks[2]);               /* Address to store the handle */
    CHECK_FIR_RESULT(eFirResult)
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */

#if (ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM)
	FirTask_Channels[0].bCallbackEnable = false;
    FirTask_Channels[1].bCallbackEnable = false;
    FirTask_Channels[2].bCallbackEnable = false;
    FirTask_Channels[3].bCallbackEnable = true;
#endif /* (ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM) */
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */
    eFirResult = adi_fir_CreateTask(hFir, /* Device Handle*/
    		FirTask_Channels,            /* Pointer to Channel List */
			FIR_NUMBER_OF_CHANNELS_TASK4, /* Number of Channels  */
			&FirTask4Memory,              /* Pointer to Memory */
			FIR_MEM_SIZE_TASK4,           /*Memory Size */
			&hFirTasks[3]);               /* Address to store the handle */
    CHECK_FIR_RESULT(eFirResult)
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */

#if (ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM)
	FirTask_Channels[0].bCallbackEnable = false;
    FirTask_Channels[1].bCallbackEnable = true;
#endif /* (ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM) */
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */
    eFirResult = adi_fir_CreateTask(hFir, /* Device Handle*/
    		FirTask_Channels,            /* Pointer to Channel List */
			FIR_NUMBER_OF_CHANNELS_TASK5, /* Number of Channels  */
			&FirTask5Memory,              /* Pointer to Memory */
			FIR_MEM_SIZE_TASK5,           /*Memory Size */
			&hFirTasks[4]);               /* Address to store the handle */
    CHECK_FIR_RESULT(eFirResult)
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */

#if (ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM)
	FirTask_Channels[0].bCallbackEnable = false;
    FirTask_Channels[1].bCallbackEnable = true;
#endif /* (ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM) */
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */
    eFirResult = adi_fir_CreateTask(hFir, /* Device Handle*/
    		FirTask_Channels,            /* Pointer to Channel List */
			FIR_NUMBER_OF_CHANNELS_TASK6, /* Number of Channels  */
			&FirTask6Memory,              /* Pointer to Memory */
			FIR_MEM_SIZE_TASK6,           /*Memory Size */
			&hFirTasks[5]);               /* Address to store the handle */
    CHECK_FIR_RESULT(eFirResult)
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */

    /* Queue the Tasks Created */

    for(count = 0; count<FIR_NUMBER_OF_TASKS; count++)
    {
#if (QUEUE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */
        eFirResult = adi_fir_QueueTask(hFirTasks[count]);
        CHECK_FIR_RESULT(eFirResult)
#if (QUEUE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */
    }

#if (INTERRUPT_LATENCY_BENCHMARK == 1)

	while(cycle_count<(CYCLES_ARRAY_SIZE))
	{
		TAKE_CYCLE_SNAPSHOT
		asm("nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;\
			nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;\
			nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;\
			nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;\
			nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;");
		asm("nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;\
			nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;\
			nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;\
			nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;\
			nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;");
		TAKE_CYCLE_SNAPSHOT
	}

    uint32_t idx1 = 1;
    uint32_t interrupt_latency = 0;

    while((idx1+2)<(CYCLES_ARRAY_SIZE-1))
    {
        if((cycles_array[idx1+2] - cycles_array[idx1]) > 50)
        {
        	int_latency[lat_idx++] = (cycles_array[idx1+2] - cycles_array[idx1]) ;
        	int_latency[lat_idx++] = idx1+2;
        }
    	idx1 = idx1+1;
    }

#endif /* (INTERRUPT_LATENCY_BENCHMARK == 1) */

    /* Wait for Callbacks */
#if (ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_LEGACY)
    while(FIRTaskDoneCount<FIR_NUMBER_OF_TASKS);
#elif (ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM)
    while(FIRTaskDoneCount<FIR_NUMBER_OF_TASKS);
#endif

    /* Print the Handles received in Callback */
    PrintCallbackHandles(FIRCompletedTaskHandles,FIRTaskDoneCount);

    printf("All Done\n");


#if (CREATE_TASK_BENCHMARK == 1)
    printf("adi_fir_CreateTask overheads:\n");
    printf(" channels = %d, CCLK cycles = %d\n",FIR_NUMBER_OF_CHANNELS_TASK1,cycles_array[1]);
    printf(" channels = %d, CCLK cycles = %d\n",FIR_NUMBER_OF_CHANNELS_TASK2,cycles_array[3]);
    printf(" channels = %d, CCLK cycles = %d\n",FIR_NUMBER_OF_CHANNELS_TASK3,cycles_array[5]);
    printf(" channels = %d, CCLK cycles = %d\n",FIR_NUMBER_OF_CHANNELS_TASK4,cycles_array[7]);
#endif /* (CREATE_TASK_BENCHMARK == 1) */

#if (QUEUE_TASK_BENCHMARK == 1)
    printf("adi_fir_QueueTask overheads:\n");
    printf("Task1 = %d CCLK cycles\n",cycles_array[1]);
    printf("Task2 = %d CCLK cycles\n",cycles_array[3]);
    printf("Task3 = %d CCLK cycles\n",cycles_array[5]);
    printf("Task4 = %d CCLK cycles\n",cycles_array[7]);
    printf("Task5 = %d CCLK cycles\n",cycles_array[9]);
    printf("Task6 = %d CCLK cycles\n",cycles_array[11]);

    printf(" Hence for pushing a task into an empty queue = %d CCLK cycles\n",cycles_array[1]);
    printf(" Hence for pushing a task into an non empty queue = %d CCLK cycles\n",((cycles_array[7] + cycles_array[9] + cycles_array[11])/3));
#endif /* (CREATE_TASK_BENCHMARK == 1) */

#if (INTERRUPT_LATENCY_BENCHMARK == 1)
    printf("Interrupt Latency overheads:\n");
	for( int ii = 0; ii<(lat_idx/2); ii++)
	{
		printf("For Interrupt of task %d = %d CCLK cycles\n",ii+1,int_latency[ii*2]);
	}
    printf("Hence Interrupt Latency if there is only one task in the queue = %d CCLK cycles\n",int_latency[lat_idx-2]);
    printf("Hence Interrupt Latency for dequeing the previous task and starting the next task = %d CCLK cycles\n",((int_latency[2] + int_latency[4] + int_latency[6] + int_latency[8])/4));
#endif /* (INTERRUPT_LATENCY_BENCHMARK == 1) */

    while(1);
}

void PrintCallbackHandles(volatile void *pCompletedTaskHandles, volatile uint32_t TaskDoneCount)
{
	volatile uint32_t count = 0;
	printf("Task Handles received in Callbacks are as follows : \n" );

    for(count=0; count<TaskDoneCount; count++)
    {
    	printf("Handle%d = 0x%X\n",count,*((uint32_t*)pCompletedTaskHandles + count));
    }

}
