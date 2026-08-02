
#include "Processing.h"

/* Input Buffer */
float Input[NCH][CIRCULAR_BUFFER_LENGTH];

/* IIR Output Buffers */
float IIROutput[NCH][BLOCK_SIZE*IIR_BANDS];

/* Final Output Buffer */
float Output[NCH][BLOCK_SIZE];

/* FIR Coefficients */
float pm FIRCoeffs[FIR_TAPS] =
{
		#include "fir_coeffs.dat"
};

/* IIR Coefficients */
float IIRCoeffs[NCH][IIR_BANDS*NSECTIONS*7] =
{
		#include "iira_coeffs.dat"
};

/* FIR task memory */
#pragma align 32
uint8_t FirTaskMemory[FIR_MEM_SIZE(NCH)];

/* IIR task memory */
#pragma align 32
uint8_t IirTaskMemory[NCH][IIR_MEM_SIZE(IIR_BANDS)];

/* FIR device handle */
ADI_FIR_DEV_HANDLE hFir;

/* FIR task handle */
ADI_FIR_TASK_HANDLE hFirTask;

/* Variable to track FIR task done */
volatile uint32_t FIRTaskDone = 0;

/* FIR channel information */
ADI_FIR_CHANNEL_INFO FirTaskChannels[NCH];

/* FIR task done callback */
void FIRTaskDoneCallback( void * pCBParam, ADI_FIR_EVENT Event, void * pArg);

/* IIR device handle */
ADI_IIR_DEV_HANDLE hIir;

/* IIR task handle */
ADI_IIR_TASK_HANDLE hIirTasks[NCH];

/* IIR channel information */
ADI_IIR_CHANNEL_INFO IirTaskChannels[NCH][IIR_BANDS];

/* Variable to track FIR tasks done */
volatile uint32_t IIRTaskDoneCount = 0;

/* IIR task done callback */
void IIRTaskDoneCallback( void * pCBParam, ADI_IIR_EVENT Event, void * pArg);

void InitializeFIRTaskChannels(void);
void InitializeIIRTaskChannels(void);

/* IIR gains supplied by the user */
float IIRGains[IIR_BANDS] = {1.0, 1.0, 1.0, 1.0, 1.0};

/* IIR gains generated from MATLAB */
float IIRGains1[NCH*IIR_BANDS] = {
	#include "gains.dat"
};

/* For cycle count */
volatile int cycle_count;
volatile int cycles_array[100];
volatile int clock_stop;
volatile int clock_start;

/* One time initialization for FIR/IIR processing */
void Init_FIR_IIR()
{
	int i;

	/* FIR result */
	ADI_FIR_RESULT eFirResult = ADI_FIR_RESULT_SUCCESS;

	/* IIR result */
	ADI_IIR_RESULT eIirResult = ADI_IIR_RESULT_SUCCESS;

	/* Initialize FIR task channels */
	InitializeFIRTaskChannels();

	/* Initialize IIR task channels */
	InitializeIIRTaskChannels();

	/* Open the FIR Device */
	eFirResult  = adi_fir_Open(0u,&hFir);

	/* Register the Callback */
	eFirResult = adi_fir_RegisterCallback(hFir,FIRTaskDoneCallback,0);

	/* Create Accelerator Tasks */
	eFirResult = adi_fir_CreateTask(hFir, /* Device Handle*/
			FirTaskChannels,              /* Pointer to Channel List */
			NCH,					  	  /* Number of Channels  */
			&FirTaskMemory,               /* Pointer to Memory */
			FIR_MEM_SIZE(NCH),           	/*Memory Size */
			&hFirTask);               /* Address to store the handle */

	/* Open the IIR Device */
	eIirResult  = adi_iir_Open(0u,&hIir);

	/* Register the Callback */
	eIirResult = adi_iir_RegisterCallback(hIir,IIRTaskDoneCallback,0);

	/* Create Accelerator Tasks */
	for(i=0;i<NCH;i++)
	{
		eIirResult = adi_iir_CreateTask(hIir, /* Device Handle */
				IirTaskChannels[i],           /* Pointer to Channel List */
				5, 							  /* Number of Channels */
				&IirTaskMemory[i],            /* Pointer to Task Memory */
				IIR_MEM_SIZE(IIR_BANDS),      /* Memory Size */
				&hIirTasks[i]);               /* Address to store handle */
	}
}

/* FIR/IIR processing */
void Process_FIR_IIR()
{
	TAKE_CYCLE_SNAPSHOT

	int i, j; float gains[5];

	/* FIR result */
	ADI_FIR_RESULT eFirResult = ADI_FIR_RESULT_SUCCESS;

	/* IIR result */
	ADI_IIR_RESULT eIirResult = ADI_IIR_RESULT_SUCCESS;

	/* Use previous frame's IIR output to generate output for this frame - data pipelining */
	if(IIRTaskDoneCount==NCH)
	{
		for(i=0;i<NCH;i++)
		{
			for(j=0;j<BLOCK_SIZE;j++)
			{
				Output[i][j] = IIROutput[i][j]*IIRGains[0]*IIRGains1[i*IIR_BANDS+0]+IIROutput[i][BLOCK_SIZE+j]*IIRGains[1]*IIRGains1[i*IIR_BANDS+1]+IIROutput[i][2*BLOCK_SIZE+j]*IIRGains[2]*IIRGains1[i*IIR_BANDS+2]+IIROutput[i][3*BLOCK_SIZE+j]*IIRGains[3]*IIRGains1[i*IIR_BANDS+3]+IIROutput[i][4*BLOCK_SIZE+j]*IIRGains[4]*IIRGains1[i*IIR_BANDS+4];
			}
		}

		IIRTaskDoneCount=0;
	}


	/* Queue FIR task and come out, no need to wait for the accelerator processing done, IIR tasks will be queued inside FIR */
	TAKE_CYCLE_SNAPSHOT
	eFirResult = adi_fir_QueueTask(hFirTask);
	TAKE_CYCLE_SNAPSHOT
}

/* Initialize FIR task channels */
void InitializeFIRTaskChannels(void)
{
	int i;

	for(i=0; i<NCH; i++)
	{
		FirTaskChannels[i].nTapLength 			= 	FIR_TAPS;
		FirTaskChannels[i].nWindowSize 			= 	BLOCK_SIZE;
		FirTaskChannels[i].eSampling 			= 	ADI_FIR_SAMPLING_SINGLE_RATE;
		FirTaskChannels[i].nSamplingRatio 		= 	1;
		FirTaskChannels[i].nCoefficientCount 	= 	FIR_TAPS;
		FirTaskChannels[i].nCoefficientModify 	= 	1;
		FirTaskChannels[i].pCoefficientIndex 	= 	(void*)&FIRCoeffs;
		FirTaskChannels[i].pOutputBuffBase 		= 	(void*)&Output[i];
		FirTaskChannels[i].nOutputBuffCount 	= 	BLOCK_SIZE;
		FirTaskChannels[i].nOutputBuffModify 	= 	1;
		FirTaskChannels[i].pOutputBuffIndex 	= 	(void*)&Output[i];
		FirTaskChannels[i].pInputBuffBase 		= 	(void*)&Input[i];
		FirTaskChannels[i].nInputBuffModify		= 	1;
		FirTaskChannels[i].nInputBuffCount 		= 	CIRCULAR_BUFFER_LENGTH;
		FirTaskChannels[i].pInputBuffIndex 		= 	(void*)&Input[i][FIRA_INDEX_START];
	}
}

/* Initialize IIR task channels */
void InitializeIIRTaskChannels(void)
{
	int i, j;

	for(i=0; i<NCH; i++)
	{
		for(j=0; j<IIR_BANDS; j++)
		{
			IirTaskChannels[i][j].nBiquads 				= 	NSECTIONS;
			IirTaskChannels[i][j].nWindowSize 			= 	BLOCK_SIZE;
			IirTaskChannels[i][j].nCoefficientLength 	= 	7*NSECTIONS;
			IirTaskChannels[i][j].nCoefficientModify 	= 	1;
			IirTaskChannels[i][j].pCoefficientIndex 	= 	(void*)&IIRCoeffs[i][j*NSECTIONS*7];
			IirTaskChannels[i][j].pOutputBuffBase 		= 	(void*)&IIROutput[i][j*BLOCK_SIZE];
			IirTaskChannels[i][j].nOutputBuffLength 	= 	BLOCK_SIZE;
			IirTaskChannels[i][j].nOutputBuffModify 	= 	1;
			IirTaskChannels[i][j].pOutputBuffIndex 		= 	(void*)&IIROutput[i][j*BLOCK_SIZE];
			IirTaskChannels[i][j].pInputBuffBase 		= 	(void*)&Output[i];
			IirTaskChannels[i][j].nInputBuffModify 		= 	1;
			IirTaskChannels[i][j].nInputBuffLength 		= 	BLOCK_SIZE;
			IirTaskChannels[i][j].pInputBuffIndex 		= 	(void*)&Output[i];
		}
	}
}

/* FIR task done callback */
void FIRTaskDoneCallback( void * pCBParam, ADI_FIR_EVENT Event, void * pArg)
{
	TAKE_CYCLE_SNAPSHOT
	int i;
	switch(Event)
	{
	    case ADI_FIR_EVENT_ALL_CHANNEL_DONE:
	    	FIRTaskDone = 1;
			for(i=0;i<NCH;i++)
			{
				adi_iir_QueueTask(hIirTasks[i]);
			}
	}
	TAKE_CYCLE_SNAPSHOT
}

/* IIR task done callback */
void IIRTaskDoneCallback( void * pCBParam, ADI_IIR_EVENT Event, void * pArg)
{
	TAKE_CYCLE_SNAPSHOT
	int i,j;
	switch(Event)
	{
	    case ADI_IIR_EVENT_ALL_CHANNEL_DONE:
	    	IIRTaskDoneCount++;
	}
	TAKE_CYCLE_SNAPSHOT
}

