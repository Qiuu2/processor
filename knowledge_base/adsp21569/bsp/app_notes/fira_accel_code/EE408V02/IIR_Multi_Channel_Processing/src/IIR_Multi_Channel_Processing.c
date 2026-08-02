/*********************************************************************************
Copyright(c) 2019 Analog Devices, Inc. All Rights Reserved.
This software is proprietary and confidential. By using this software you agree
to the terms of the associated Analog Devices License Agreement.
*********************************************************************************/

/*****************************************************************************
 * IIR_Multi_Channel_Processing.c
 *****************************************************************************/
#include <sys/platform.h>
#include "adi_initialize.h"
#include "IIR_Multi_Channel_Processing.h"
#include <drivers/iir/adi_iir.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

/** 
 * If you want to use command program arguments, then place them in the following string. 
 */
char __argv_string[] = "";

float IirInputBuff1[IIR_WINDOW_SIZE]=
{
	#include "iir_input_window_1024.dat"
};

float IirInputBuff2[IIR_WINDOW_SIZE]=
{
	#include "iir_input_window_1024.dat"
};

float IirInputBuff3[IIR_WINDOW_SIZE]=
{
	#include "iir_input_window_1024.dat"
};

float IirInputBuff4[IIR_WINDOW_SIZE]=
{
	#include "iir_input_window_1024.dat"
};

/* For N biquad stages, the order of coefficients should be as follows:
b01, b11, -a11, b21, -a21, dk21, dk11,
b02, b12, -a12, b22, -a22, dk22, dk12,
,......
b0N, b1N, -a1N, b2N, -a2N, dk2N, dk1N.
where bxN and axN are the coefficients ([b, a]) for the Nth biquad stage. For more details, Please refer ADSP-SC58x SHARC Processor
Hardware Reference*/
float CoeffBuff1[7*BIQUADS]=
{
	#include "iir_coeffs_biquads_12.dat"
};

float CoeffBuff2[7*BIQUADS]=
{
	#include "iir_coeffs_biquads_12.dat"
};

float CoeffBuff3[7*BIQUADS]=
{
	#include "iir_coeffs_biquads_12.dat"
};

float CoeffBuff4[7*BIQUADS]=
{
	#include "iir_coeffs_biquads_12.dat"
};

/* Gain due to second order biquads cascade. After filtering the input through the SOS Biquads, the output has to be multiplied
 * by the Gain.
 */
float SOS_Gain1[1]=
{
	#include "iir_sos_gain_biquads_12.dat"
};

float SOS_Gain2[1]=
{
	#include "iir_sos_gain_biquads_12.dat"
};
float SOS_Gain3[1]=
{
	#include "iir_sos_gain_biquads_12.dat"
};

float SOS_Gain4[1]=
{
	#include "iir_sos_gain_biquads_12.dat"
};

float IirOutputBuff1[IIR_WINDOW_SIZE];
float IirOutputBuff2[IIR_WINDOW_SIZE];
float IirOutputBuff3[IIR_WINDOW_SIZE];
float IirOutputBuff4[IIR_WINDOW_SIZE];

float IirExpectedOutputBuff1[IIR_WINDOW_SIZE]=
{
    #include "iir_output_biquads_12_window_1024.dat"
};

#pragma align 32
uint8_t IirTask1Memory[IIR_MEM_SIZE_TASK1];

#pragma align 32
uint8_t IirTask2Memory[IIR_MEM_SIZE_TASK2];

ADI_IIR_DEV_HANDLE hIir;

ADI_IIR_TASK_HANDLE hIirTasks[IIR_NUMBER_OF_TASKS] = {0};

volatile uint32_t IIRTaskDoneCount = 0;
volatile void *IIRCompletedTaskHandles[60] = {0};
void IIRTaskDoneCallback( void * pCBParam, ADI_IIR_EVENT Event, void * pArg);

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

	ADI_IIR_RESULT eIirResult = ADI_IIR_RESULT_SUCCESS;
	
	/* Arrays containing the Information of Channels in each Task */
	
	ADI_IIR_CHANNEL_INFO IirTask1_Channels[IIR_NUMBER_OF_CHANNELS_TASK1] = {
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
				(void *)CoeffBuff2,                                       /* Coefficient Index */
				(void *)IirOutputBuff2,                                   /* Output Base */
				IIR_WINDOW_SIZE,                                          /* Output Length */
				1,                                                        /* Output Modify */
				(void *)IirOutputBuff2,                                   /* Output Index */
				(void *)IirInputBuff2,                                    /* Input Base */
				IIR_WINDOW_SIZE,                                          /* Input Count */
				1,                                                        /* Input Modify */
				(void *)IirInputBuff2                                     /* Input Index */
			}
	};

	ADI_IIR_CHANNEL_INFO IirTask2_Channels[IIR_NUMBER_OF_CHANNELS_TASK1] = {
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
				(void *)CoeffBuff3,                                       /* Coefficient Index */
				(void *)IirOutputBuff3,                                   /* Output Base */
				IIR_WINDOW_SIZE,                                          /* Output Length */
				1,                                                        /* Output Modify */
				(void *)IirOutputBuff3,                                   /* Output Index */
				(void *)IirInputBuff3,                                    /* Input Base */
				IIR_WINDOW_SIZE,                                          /* Input Count */
				1,                                                        /* Input Modify */
				(void *)IirInputBuff3                                     /* Input Index */
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
				(void *)CoeffBuff4,                                       /* Coefficient Index */
				(void *)IirOutputBuff4,                                   /* Output Base */
				IIR_WINDOW_SIZE,                                          /* Output Length */
				1,                                                        /* Output Modify */
				(void *)IirOutputBuff4,                                   /* Output Index */
				(void *)IirInputBuff4,                                    /* Input Base */
				IIR_WINDOW_SIZE,                                          /* Input Count */
				1,                                                        /* Input Modify */
				(void *)IirInputBuff4                                     /* Input Index */
			}
	};

	/* Open the IIR Device */
    eIirResult  = adi_iir_Open(0u,&hIir);
    CHECK_IIR_RESULT(eIirResult);

    /* Register the Callback */
    eIirResult = adi_iir_RegisterCallback(hIir,IIRTaskDoneCallback,0);
    CHECK_IIR_RESULT(eIirResult);

    /* Create Accelerator Tasks */
    eIirResult = adi_iir_CreateTask(hIir, /* Device Handle */
    		IirTask1_Channels,            /* Pointer to Channel List */
			IIR_NUMBER_OF_CHANNELS_TASK1, /* Number of Channels */
			&IirTask1Memory,              /* Pointer to Task Memory */
			IIR_MEM_SIZE_TASK1,           /* Memory Size */
			&hIirTasks[0]);               /* Address to store handle */
    CHECK_IIR_RESULT(eIirResult);

    eIirResult = adi_iir_CreateTask(hIir, /* Device Handle */
    		IirTask2_Channels,            /* Pointer to Channel List */
			IIR_NUMBER_OF_CHANNELS_TASK2, /* Number of Channels */
			&IirTask2Memory,              /* Pointer to Task Memory */
			IIR_MEM_SIZE_TASK2,           /* Memory Size */
			&hIirTasks[1]);               /* Address to store handle */
    CHECK_IIR_RESULT(eIirResult);

    /* Queue the Tasks Created */
    for(count = 0; count<IIR_NUMBER_OF_TASKS; count++)
    {
        eIirResult = adi_iir_QueueTask(hIirTasks[count]);
        CHECK_IIR_RESULT(eIirResult);
    }

    /* 
	   In Legacy Mode,the callbacks are received after completion of all the channels of the task. Hence wait untill we get 
	   as many callbacks as the number of tasks queued(i.e 2).
	   In Auto Configuration Mode(ACM),the callbacks are customisable with each channel of a task.
       In this example, since all the channels of both tasks are configured to generate callback after their completion, 
	   wait untill we get as many callbacks as the total number of channels in both the tasks.(i.e 4) 
	*/
#if (ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_LEGACY)
    while(IIRTaskDoneCount<IIR_NUMBER_OF_TASKS);
#elif (ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_ACM)
    while(IIRTaskDoneCount<IIR_NUMBER_OF_CHANNELS);
#endif

    /* Print the Handles received in Callback */
    PrintCallbackHandles(IIRCompletedTaskHandles,IIRTaskDoneCount);

    /* Check Buffer Contents */
    CheckIIRBufferContents();

    printf("All Done\n");


}
/*This function is used to scale the obtained output.Since the processing through Second Order Biquads introduces
 * a gain in the Output,the outputs obtained need to scaled before comparing against the expected MATLAB outputs.
 * The gain depends on the number/configuration of the second order cascaded sections and is obtained through
 * MATLAB(iir_sos_gain_biquads_12.dat)
 */
void ScaleOutput(float *Buffer, uint32_t count, float gain)
{
	volatile uint32_t i = 0;
	for(i=0;i<count;i++)
	{
		Buffer[i] *= gain;
	}
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

void CheckIIRBufferContents(void)
{
	volatile float max_diff;
	ScaleOutput(IirOutputBuff1,IIR_WINDOW_SIZE,SOS_Gain1[0]);
	max_diff=Find_Max_Diff(IirOutputBuff1, IirExpectedOutputBuff1,IIR_WINDOW_SIZE);
	CHECK_MAX_DIFF(max_diff)

	ScaleOutput(IirOutputBuff2,IIR_WINDOW_SIZE,SOS_Gain2[0]);
	max_diff=Find_Max_Diff(IirOutputBuff2, IirExpectedOutputBuff1,IIR_WINDOW_SIZE);
	CHECK_MAX_DIFF(max_diff)

	ScaleOutput(IirOutputBuff3,IIR_WINDOW_SIZE,SOS_Gain3[0]);
	max_diff=Find_Max_Diff(IirOutputBuff3, IirExpectedOutputBuff1,IIR_WINDOW_SIZE);
	CHECK_MAX_DIFF(max_diff)

	ScaleOutput(IirOutputBuff4,IIR_WINDOW_SIZE,SOS_Gain4[0]);
	max_diff=Find_Max_Diff(IirOutputBuff4, IirExpectedOutputBuff1,IIR_WINDOW_SIZE);
	CHECK_MAX_DIFF(max_diff)

    printf("Buffer Contents Verified\n");
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

