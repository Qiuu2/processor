/*****************************************************************************
 * IIR_Floating_Point_ACM.c
 * This example is used to measure the IIRA Device Driver Benchmarks for Legacy and ACM Mode.
 * In  this example, 6 IIR tasks are created and Queued to the accelerator and the driver benchmarks
 * are measured. The measurement is to provide estimate of the driver benchmarks/overheads.
 *
 * Three macros are provided in the header file(FIR_Floating_Point_ACM.h) to measure three types of benchmarks
 *
 * - CREATE_TASK_BENCHMARK : Set this macro to 1 to measure the benchmarks for adi_iir_CreateTask() API.
 * - QUEUE_TASK_BENCHMARK : Set this macro to 1 to measure the benchmarks for adi_iir_QueueTask() API.
 * - INTERRUPT_LATENCY_BENCHMARK: Set this macro to 1 to measure the Interrupt Latency Overhead.Note that the measurement
 *                                involves the total interrupt round trip time including the SEC dispatcher,driver interrupt handler
 *                                and Callback.
 *
 * At a time, only one of the three above mentioned macros can be set to 1.
 *****************************************************************************/

#include <sys/platform.h>
#include "adi_initialize.h"
#include "IIR_Floating_Point_ACM.h"
#include <drivers/iir/adi_iir.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

/** 
 * If you want to use command program arguments, then place them in the following string. 
 */
char __argv_string[] = "";

float IirInputBuff1[IIR_WINDOW_SIZE];

/* For N biquad stages, the order of coefficients should be as follows:
b01, b11, -a11, b21, -a21, dk21, dk11,
b02, b12, -a12, b22, -a22, dk22, dk12,
,......
b0N, b1N, -a1N, b2N, -a2N, dk2N, dk1N.
where bxN and axN are the coefficients ([b, a]) for the Nth biquad stage. For more details, Please refer ADSP-SC58x SHARC Processor
Hardware Reference*/
float CoeffBuff1[7*BIQUADS];

float IirOutputBuff1[IIR_WINDOW_SIZE];


#pragma align 32
uint8_t IirTask1Memory[IIR_MEM_SIZE_TASK1];

#pragma align 32
uint8_t IirTask2Memory[IIR_MEM_SIZE_TASK2];

#pragma align 32
uint8_t IirTask3Memory[IIR_MEM_SIZE_TASK3];

#pragma align 32
uint8_t IirTask4Memory[IIR_MEM_SIZE_TASK4];

#pragma align 32
uint8_t IirTask5Memory[IIR_MEM_SIZE_TASK5];

#pragma align 32
uint8_t IirTask6Memory[IIR_MEM_SIZE_TASK6];

ADI_IIR_DEV_HANDLE hIir;

ADI_IIR_TASK_HANDLE hIirTasks[IIR_NUMBER_OF_TASKS] = {0};

volatile uint32_t IIRTaskDoneCount = 0;
volatile void *IIRCompletedTaskHandles[60] = {0};
void IIRTaskDoneCallback( void * pCBParam, ADI_IIR_EVENT Event, void * pArg);
void PrintCallbackHandles(volatile void *pCompletedTaskHandles, volatile uint32_t TaskDoneCount);

void IIRTaskDoneCallback( void * pCBParam, ADI_IIR_EVENT Event, void * pArg)
{
	switch(Event)
	{
#if  ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM
	    case ADI_IIR_EVENT_CHANNEL_DONE:
#else
	    case ADI_IIR_EVENT_ALL_CHANNEL_DONE:
#endif
	    	IIRCompletedTaskHandles[IIRTaskDoneCount++] = pArg;
	}
}

volatile int count = 0;

void CheckIIRBufferContents(void);

int main(int argc, char *argv[])
{
	/**
	 * Initialize managed drivers and/or services that have been added to 
	 * the project.
	 * @return zero on success 
	 */
	adi_initComponents();

	ADI_IIR_RESULT eIirResult = ADI_IIR_RESULT_SUCCESS;
	
	ADI_IIR_CHANNEL_INFO IirTask_Channels[4] = {
			{
				BIQUADS,                                                  /*Biquads */
				IIR_WINDOW_SIZE,                                          /* Window Size */
#if  ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM
                true,                                                     /* Callback Enable */
				false,                                                    /* Generate Trigger on completion */
				false,                                                    /* Wait for Trigger */
				ADI_IIR_FLOAT_ROUNDING_MODE_IEEE_ROUND_TO_NEAREST_EVEN,   /* Rounding Mode */
				false,                                                    /* Forty Bit Mode Select */
				true,                                                     /* Save Biquad States */
#endif /* MODE == ACM */
				BIQUADS*7,                                                /* Coefficient Count */
				1,                                                        /* Coefficient Modify */
				(void *)CoeffBuff1,                                       /* Coefficient Index */
				(void *)IirOutputBuff1,                                   /* Output Base */
				IIR_WINDOW_SIZE,                                          /* Output Length */
				1,                                                        /* Output Modify */
				(void *)IirOutputBuff1,                                   /* Output Index */
				(void *)IirInputBuff1,                                    /* Input Base */
				IIR_WINDOW_SIZE,                                          /* Input Count */
				1,                                                        /* Input Modify */
				(void *)IirInputBuff1                                     /* Input Index */
			},
			{
					BIQUADS,                                                  /*Biquads */
					IIR_WINDOW_SIZE,                                          /* Window Size */
	#if  ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM
	                true,                                                     /* Callback Enable */
					false,                                                    /* Generate Trigger on completion */
					false,                                                    /* Wait for Trigger */
					ADI_IIR_FLOAT_ROUNDING_MODE_IEEE_ROUND_TO_NEAREST_EVEN,   /* Rounding Mode */
					false,                                                    /* Forty Bit Mode Select */
					true,                                                     /* Save Biquad States */
	#endif /* MODE == ACM */
					BIQUADS*7,                                                /* Coefficient Count */
					1,                                                        /* Coefficient Modify */
					(void *)CoeffBuff1,                                       /* Coefficient Index */
					(void *)IirOutputBuff1,                                   /* Output Base */
					IIR_WINDOW_SIZE,                                          /* Output Length */
					1,                                                        /* Output Modify */
					(void *)IirOutputBuff1,                                   /* Output Index */
					(void *)IirInputBuff1,                                    /* Input Base */
					IIR_WINDOW_SIZE,                                          /* Input Count */
					1,                                                        /* Input Modify */
					(void *)IirInputBuff1                                     /* Input Index */
			},
			{
					BIQUADS,                                                  /*Biquads */
					IIR_WINDOW_SIZE,                                          /* Window Size */
	#if  ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM
					true,                                                     /* Callback Enable */
					false,                                                    /* Generate Trigger on completion */
					false,                                                    /* Wait for Trigger */
					ADI_IIR_FLOAT_ROUNDING_MODE_IEEE_ROUND_TO_NEAREST_EVEN,   /* Rounding Mode */
					false,                                                    /* Forty Bit Mode Select */
					true,                                                     /* Save Biquad States */
	#endif /* MODE == ACM */
					BIQUADS*7,                                                /* Coefficient Count */
					1,                                                        /* Coefficient Modify */
					(void *)CoeffBuff1,                                       /* Coefficient Index */
					(void *)IirOutputBuff1,                                   /* Output Base */
					IIR_WINDOW_SIZE,                                          /* Output Length */
					1,                                                        /* Output Modify */
					(void *)IirOutputBuff1,                                   /* Output Index */
					(void *)IirInputBuff1,                                    /* Input Base */
					IIR_WINDOW_SIZE,                                          /* Input Count */
					1,                                                        /* Input Modify */
					(void *)IirInputBuff1                                     /* Input Index */
			},
			{
					BIQUADS,                                                  /*Biquads */
					IIR_WINDOW_SIZE,                                          /* Window Size */
	#if  ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM
					true,                                                     /* Callback Enable */
					false,                                                    /* Generate Trigger on completion */
					false,                                                    /* Wait for Trigger */
					ADI_IIR_FLOAT_ROUNDING_MODE_IEEE_ROUND_TO_NEAREST_EVEN,   /* Rounding Mode */
					false,                                                    /* Forty Bit Mode Select */
					true,                                                     /* Save Biquad States */
	#endif /* MODE == ACM */
					BIQUADS*7,                                                /* Coefficient Count */
					1,                                                        /* Coefficient Modify */
					(void *)CoeffBuff1,                                       /* Coefficient Index */
					(void *)IirOutputBuff1,                                   /* Output Base */
					IIR_WINDOW_SIZE,                                          /* Output Length */
					1,                                                        /* Output Modify */
					(void *)IirOutputBuff1,                                   /* Output Index */
					(void *)IirInputBuff1,                                    /* Input Base */
					IIR_WINDOW_SIZE,                                          /* Input Count */
					1,                                                        /* Input Modify */
					(void *)IirInputBuff1                                     /* Input Index */
			}

	};


	/* Open the IIR Device */
    eIirResult  = adi_iir_Open(0u,&hIir);
    CHECK_IIR_RESULT(eIirResult);

    eIirResult = adi_iir_RegisterCallback(hIir,IIRTaskDoneCallback,0);
    CHECK_IIR_RESULT(eIirResult);

    START_CYCLE_COUNT

#if  ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM
    IirTask_Channels[0].bCallbackEnable = true;
#endif /* ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM */
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */
    eIirResult = adi_iir_CreateTask(hIir, /* Device Handle */
    		IirTask_Channels,            /* Pointer to Channel List */
			IIR_NUMBER_OF_CHANNELS_TASK1, /* Number of Channels */
			&IirTask1Memory,              /* Pointer to Task Memory */
			IIR_MEM_SIZE_TASK1,           /* Memory Size */
			&hIirTasks[0]);               /* Address to store handle */
    CHECK_IIR_RESULT(eIirResult);
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */

#if  ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM
    IirTask_Channels[0].bCallbackEnable = false;
    IirTask_Channels[1].bCallbackEnable = true;
#endif /* ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM */
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */
    eIirResult = adi_iir_CreateTask(hIir, /* Device Handle */
    		IirTask_Channels,            /* Pointer to Channel List */
			IIR_NUMBER_OF_CHANNELS_TASK2, /* Number of Channels */
			&IirTask2Memory,              /* Pointer to Task Memory */
			IIR_MEM_SIZE_TASK2,           /* Memory Size */
			&hIirTasks[1]);               /* Address to store handle */
    CHECK_IIR_RESULT(eIirResult);
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */

#if  ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM
    IirTask_Channels[0].bCallbackEnable = false;
    IirTask_Channels[1].bCallbackEnable = false;
    IirTask_Channels[2].bCallbackEnable = true;
#endif /* ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM */
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */
    eIirResult = adi_iir_CreateTask(hIir, /* Device Handle */
    		IirTask_Channels,            /* Pointer to Channel List */
			IIR_NUMBER_OF_CHANNELS_TASK3, /* Number of Channels */
			&IirTask3Memory,              /* Pointer to Task Memory */
			IIR_MEM_SIZE_TASK3,           /* Memory Size */
			&hIirTasks[2]);               /* Address to store handle */
    CHECK_IIR_RESULT(eIirResult);
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */

#if  ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM
    IirTask_Channels[0].bCallbackEnable = false;
    IirTask_Channels[1].bCallbackEnable = false;
    IirTask_Channels[2].bCallbackEnable = false;
    IirTask_Channels[3].bCallbackEnable = true;
#endif /* ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM */
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */
    eIirResult = adi_iir_CreateTask(hIir, /* Device Handle */
    		IirTask_Channels,            /* Pointer to Channel List */
			IIR_NUMBER_OF_CHANNELS_TASK4, /* Number of Channels */
			&IirTask4Memory,              /* Pointer to Task Memory */
			IIR_MEM_SIZE_TASK4,           /* Memory Size */
			&hIirTasks[3]);               /* Address to store handle */
    CHECK_IIR_RESULT(eIirResult);
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */

#if  ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM
    IirTask_Channels[0].bCallbackEnable = false;
    IirTask_Channels[1].bCallbackEnable = true;
#endif /* ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM */
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */
    eIirResult = adi_iir_CreateTask(hIir, /* Device Handle */
    		IirTask_Channels,            /* Pointer to Channel List */
			IIR_NUMBER_OF_CHANNELS_TASK5, /* Number of Channels */
			&IirTask5Memory,              /* Pointer to Task Memory */
			IIR_MEM_SIZE_TASK5,           /* Memory Size */
			&hIirTasks[4]);               /* Address to store handle */
    CHECK_IIR_RESULT(eIirResult);
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */

#if  ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM
    IirTask_Channels[0].bCallbackEnable = false;
    IirTask_Channels[1].bCallbackEnable = true;
#endif /* ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM */
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */
    eIirResult = adi_iir_CreateTask(hIir, /* Device Handle */
    		IirTask_Channels,            /* Pointer to Channel List */
			IIR_NUMBER_OF_CHANNELS_TASK6, /* Number of Channels */
			&IirTask6Memory,              /* Pointer to Task Memory */
			IIR_MEM_SIZE_TASK6,           /* Memory Size */
			&hIirTasks[5]);               /* Address to store handle */
    CHECK_IIR_RESULT(eIirResult);
#if (CREATE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */

    /* Queue the Tasks Created */
    for(count = 0; count<IIR_NUMBER_OF_TASKS; count++)
    {
#if (QUEUE_TASK_BENCHMARK == 1)
	TAKE_CYCLE_SNAPSHOT
#endif /* CREATE_TASK_BENCHMARK == 1 */
        eIirResult = adi_iir_QueueTask(hIirTasks[count]);
        CHECK_IIR_RESULT(eIirResult);
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
#if (ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_LEGACY)
    while(IIRTaskDoneCount<IIR_NUMBER_OF_TASKS);
#elif (ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM)
    while(IIRTaskDoneCount<IIR_NUMBER_OF_TASKS);
#endif

    /* Print the Handles received in Callback */
    PrintCallbackHandles(IIRCompletedTaskHandles,IIRTaskDoneCount);

    printf("All Done\n");

#if (CREATE_TASK_BENCHMARK == 1)
    printf("adi_iir_CreateTask overheads:\n");
    printf(" channels = %d, CCLK cycles = %d\n",IIR_NUMBER_OF_CHANNELS_TASK1,cycles_array[1]);
    printf(" channels = %d, CCLK cycles = %d\n",IIR_NUMBER_OF_CHANNELS_TASK2,cycles_array[3]);
    printf(" channels = %d, CCLK cycles = %d\n",IIR_NUMBER_OF_CHANNELS_TASK3,cycles_array[5]);
    printf(" channels = %d, CCLK cycles = %d\n",IIR_NUMBER_OF_CHANNELS_TASK4,cycles_array[7]);
#endif /* (CREATE_TASK_BENCHMARK == 1) */

#if (QUEUE_TASK_BENCHMARK == 1)
    printf("adi_iir_QueueTask overheads:\n");
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

