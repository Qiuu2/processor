/*********************************************************************************
Copyright(c) 2019 Analog Devices, Inc. All Rights Reserved.
This software is proprietary and confidential. By using this software you agree
to the terms of the associated Analog Devices License Agreement.
*********************************************************************************/

/*****************************************************************************
 * FIR_Multi_Channel_Processing.c
 *****************************************************************************/

#include <sys/platform.h>
#include "adi_initialize.h"
#include "FIR_Multi_Channel_Processing.h"
#include <drivers/fir/adi_fir.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

/** 
 * If you want to use command program arguments, then place them in the following string. 
 */
char __argv_string[] = "";

float FirInputBuff1[TAPS1+FIR_WINDOW_SIZE-1]=
{
	#include "fir_input_taps_64_window_1024.dat"
};

float FirInputBuff2[TAPS1+FIR_WINDOW_SIZE-1]=
{
	#include "fir_input_taps_64_window_1024.dat"
};

float FirInputBuff3[TAPS2+FIR_WINDOW_SIZE-1]=
{
	#include "fir_input_taps_4096_window_1024.dat"
};

float FirInputBuff4[TAPS2+FIR_WINDOW_SIZE-1]=
{
	#include "fir_input_taps_4096_window_1024.dat"
};

float CoeffBuff1[TAPS1]=
{
	#include "fir_coeffs_64.dat"
};

float CoeffBuff2[TAPS1]=
{
	#include "fir_coeffs_64.dat"
};

float CoeffBuff3[TAPS2]=
{
	#include "fir_coeffs_4096.dat"
};

float CoeffBuff4[TAPS2]=
{
	#include "fir_coeffs_4096.dat"
};

float FirOutputBuff1[FIR_WINDOW_SIZE];

float FirOutputBuff2[FIR_WINDOW_SIZE];

float FirOutputBuff3[FIR_WINDOW_SIZE];

float FirOutputBuff4[FIR_WINDOW_SIZE];

float FirExpectedOutputBuff1[FIR_WINDOW_SIZE]=
{
	#include "fir_output_taps_64_window_1024.dat"
};

float FirExpectedOutputBuff2[FIR_WINDOW_SIZE]=
{
	#include "fir_output_taps_4096_window_1024.dat"
};

#pragma align 32
uint8_t FirTask1Memory[FIR_MEM_SIZE_TASK1];

#pragma align 32
uint8_t FirTask2Memory[FIR_MEM_SIZE_TASK2];

ADI_FIR_DEV_HANDLE hFir;

ADI_FIR_TASK_HANDLE hFirTasks[FIR_NUMBER_OF_TASKS] = {0};

volatile uint32_t FIRTaskDoneCount = 0;
volatile void *FIRCompletedTaskHandles[20] = {0};
void FIRTaskDoneCallback( void * pCBParam, ADI_FIR_EVENT Event, void * pArg);

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

void CheckFIRBufferContents(void);
float Find_Max_Diff(float* uiBuff_actual, float* uiBuff_expected, unsigned int uiCount);
void PrintCallbackHandles(volatile void *pCompletedTaskHandles, volatile uint32_t TaskDoneCount);

int main(int argc, char *argv[])
{
	/**
	 * Initialize managed drivers and/or services that have been added to 
	 * the project.
	 * @return zero on success 
	 */
	adi_initComponents();
	
    ADI_FIR_RESULT eFirResult = ADI_FIR_RESULT_SUCCESS;

    /* Arrays containing the Information of Channels in each Task */
	
	ADI_FIR_CHANNEL_INFO FirTask1_Channels[FIR_NUMBER_OF_CHANNELS_TASK1] = {

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
				(void *)CoeffBuff2,                                         /* Coefficient Index */
		        (void *)FirOutputBuff2,                                     /* Output Base */
				FIR_WINDOW_SIZE,                                            /* Output Count */
				1,                                                          /* Output Modify */
				(void *)FirOutputBuff2,                                     /* Output Index */
		        (void *)FirInputBuff2,                                      /* Input Base */
				TAPS1+FIR_WINDOW_SIZE-1,                                    /* Input Count */
				1,                                                          /* Input Modify */
				(void *)FirInputBuff2                                       /* Input Count */

			}

	};

	ADI_FIR_CHANNEL_INFO FirTask2_Channels[FIR_NUMBER_OF_CHANNELS_TASK2] = {

			{
				TAPS2,                                                      /* Tap Length */
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
				TAPS2,                                                      /* Coefficient Count */
				1,                                                          /* Coefficient Modify */
				(void *)CoeffBuff3,                                         /* Coefficient Index */
		        (void *)FirOutputBuff3,                                     /* Output Base */
				FIR_WINDOW_SIZE,                                            /* Output Count */
				1,                                                          /* Output Modify */
				(void *)FirOutputBuff3,                                     /* Output Index */
		        (void *)FirInputBuff3,                                      /* Input Base */
				TAPS2+FIR_WINDOW_SIZE-1,                                    /* Input Count */
				1,                                                          /* Input Modify */
				(void *)FirInputBuff3                                       /* Input Count */

			},
			{
				TAPS2,                                                      /* Tap Length */
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
				TAPS2,                                                      /* Coefficient Count */
				1,                                                          /* Coefficient Modify */
				(void *)CoeffBuff4,                                         /* Coefficient Index */
		        (void *)FirOutputBuff4,                                     /* Output Base */
				FIR_WINDOW_SIZE,                                            /* Output Count */
				1,                                                          /* Output Modify */
				(void *)FirOutputBuff4,                                     /* Output Index */
		        (void *)FirInputBuff4,                                      /* Input Base */
				TAPS2+FIR_WINDOW_SIZE-1,                                    /* Input Count */
				1,                                                          /* Input Modify */
				(void *)FirInputBuff4                                       /* Input Count */

			}

	};

	/* Open the FIR Device */
    eFirResult  = adi_fir_Open(0u,&hFir);
    CHECK_FIR_RESULT(eFirResult)

    /* Register the Callback */
    eFirResult = adi_fir_RegisterCallback(hFir,FIRTaskDoneCallback,0);
    CHECK_FIR_RESULT(eFirResult)

    /* Create Accelerator Tasks */
    eFirResult = adi_fir_CreateTask(hFir, /* Device Handle*/
    		FirTask1_Channels,            /* Pointer to Channel List */
			FIR_NUMBER_OF_CHANNELS_TASK1, /* Number of Channels  */
			&FirTask1Memory,              /* Pointer to Memory */
			FIR_MEM_SIZE_TASK1,           /*Memory Size */
			&hFirTasks[0]);               /* Address to store the handle */
    CHECK_FIR_RESULT(eFirResult)

    eFirResult = adi_fir_CreateTask(hFir, /* Device Handle*/
    		FirTask2_Channels,            /* Pointer to Channel List */
			FIR_NUMBER_OF_CHANNELS_TASK2, /* Number of Channels  */
			&FirTask2Memory,              /* Pointer to Memory */
			FIR_MEM_SIZE_TASK2,           /*Memory Size */
			&hFirTasks[1]);               /* Address to store the handle */
    CHECK_FIR_RESULT(eFirResult)

    /* Queue the Tasks Created */
    for(count = 0; count<FIR_NUMBER_OF_TASKS; count++)
    {
        eFirResult = adi_fir_QueueTask(hFirTasks[count]);
        CHECK_FIR_RESULT(eFirResult)
    }

    /* 
	   In Legacy Mode,the callbacks are received after completion of all the channels of the task. Hence wait untill we get 
	   as many callbacks as the number of tasks queued(i.e 2).
	   In Auto Configuration Mode(ACM),the callbacks are customisable with each channel of a task.
       In this example, since all the channels of both tasks are configured to generate callback after their completion, 
	   wait untill we get as many callbacks as the total number of channels in both the tasks.(i.e 4) 
	*/
#if (ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_LEGACY)
    while(FIRTaskDoneCount<FIR_NUMBER_OF_TASKS);
#elif (ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_ACM)
    while(FIRTaskDoneCount<FIR_NUMBER_OF_CHANNELS);
#endif

    /* Print the Handles received in Callback */
    PrintCallbackHandles(FIRCompletedTaskHandles,FIRTaskDoneCount);

    /* Check Buffer Contents */
    CheckFIRBufferContents();

    printf("All Done\n");

}



/* This function is used to find the maximum difference between the expected and actual results */
float Find_Max_Diff(float* uiBuff_actual, float* uiBuff_expected, unsigned int uiCount)
{
	volatile uint32_t i; float temp, temp1;
	float max_diff=0; float diff;
	float* pt = uiBuff_actual; float*  pt1 = uiBuff_expected;

	for(i=0;i<uiCount;i++)
	{
		temp=*pt++; temp1=*pt1++;

		if(temp>temp1)
			diff = temp-temp1;
		else
			diff = temp1-temp;

		if(temp1!=0.0&&diff>max_diff)
			max_diff=diff/temp1;
	}

	return max_diff;
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

void CheckFIRBufferContents(void)
{
	volatile float max_diff;
	max_diff=Find_Max_Diff(FirOutputBuff1, FirExpectedOutputBuff1,FIR_WINDOW_SIZE);
	CHECK_MAX_DIFF(max_diff)
	max_diff=Find_Max_Diff(FirOutputBuff2, FirExpectedOutputBuff1,FIR_WINDOW_SIZE);
	CHECK_MAX_DIFF(max_diff)
	max_diff=Find_Max_Diff(FirOutputBuff3, FirExpectedOutputBuff2,FIR_WINDOW_SIZE);
	CHECK_MAX_DIFF(max_diff)
	max_diff=Find_Max_Diff(FirOutputBuff4, FirExpectedOutputBuff2,FIR_WINDOW_SIZE);
	CHECK_MAX_DIFF(max_diff)
    printf("Buffer Contents Verified\n");
}

