/*****************************************************************************
 * ADSP-21489_IIR.c
 
 This Code can be used to measure the number of CCLK cycles taken by the IIR Accelerator to perform IIR operation for any combination of Biquads and Window Size on ADSP-21489.
 The number of combinations of {Window,Biquads} for which the cycles are required are given in ParamList.dat file present in the source folder of the project.
 The project Header file(ADSP-21489_IIR.h) has a macro TOTAL_PARAMETERS which should be configured to the number of combinations of {Window,Biquads} present in ParamList.dat file.
 On Execution of the code, the CCLK cycles taken for each combination of {Window,Biquads} are printed on the console and also written to a Excel Sheet in the Debug folder of the project.
 *****************************************************************************/

#include <sys/platform.h>
#include "adi_initialize.h"
#include "ADSP-21489_IIR.h"
#include <stdio.h>
#include <time.h>
#include <services/int/adi_int.h>

#define OFFSET_MASK 0x7FFFF
#define PCI 0x80000

/** 
 * If you want to use command program arguments, then place them in the following string. 
 */
char __argv_string[] = "";

uint32_t IIRA_TCB1[IIR_TCB_SIZE];

float uiOutputBuff1[MAX_WINDOW_SIZE];
float uiInputBuff1[MAX_WINDOW_SIZE];
float uiCoeffBuff1[7*MAX_BIQUADS];

volatile clock_t clock_start;
volatile clock_t clock_stop;
volatile clock_t cycles;

uint32_t iir_param_list[TOTAL_PARAMETERS][2]=
{
	/* Window, Biquads */
#include "ParamList.dat"
};

void IIRA_Init(uint32_t uiIIR_GCTL, uint32_t* uiIIR_CHNPTR)
{
	*pCPIIR=(uint32_t)uiIIR_CHNPTR;
	clock_start=clock();
	*pIIRCTL1=uiIIR_GCTL;
}

int main(int argc, char *argv[])
{
	/**
	 * Initialize managed drivers and/or services that have been added to 
	 * the project.
	 * @return zero on success 
	 */
	adi_initComponents();
	
	FILE * fpout;
	fpout = fopen("Results(cycles).csv","w+");

	for(uint32_t i=0;i<TOTAL_PARAMETERS;i++)
	{
		/* Select the IIR accelerator */
		*pPMCTL1|=(BIT_17);
		/* Replace GP Timer Interrupt */
		//*pPICR1 |= P10I0 | P10I1 | P10I3 | P10I4;
		/* Install the IIR interrupt handler */
		//adi_int_InstallHandler(ADI_CID_P10I,&IIR_DMA_Interrupt_Handler1,0,true);

		//Initialize IIR TCBs
		IIRA_TCB1[0]=((((uint32_t)(IIRA_TCB1+12))& OFFSET_MASK));	//CP
		IIRA_TCB1[1]=iir_param_list[i][1]*7;	//CL
		IIRA_TCB1[2]=1;	//CM
		IIRA_TCB1[3]=(uint32_t)uiCoeffBuff1;	//CI
		IIRA_TCB1[4]=(uint32_t)uiOutputBuff1;	//OB
		IIRA_TCB1[5]=iir_param_list[i][0];	//OL
		IIRA_TCB1[6]=1;	//OM
		IIRA_TCB1[7]=(uint32_t)uiOutputBuff1;	//OI
		IIRA_TCB1[8]=(uint32_t)uiInputBuff1;	//IB
		IIRA_TCB1[9]=iir_param_list[i][0];	//IL
		IIRA_TCB1[10]=1;	//IM
		IIRA_TCB1[11]=(uint32_t)uiInputBuff1;	//II
		IIRA_TCB1[12]=(iir_param_list[i][1]-1)|(iir_param_list[i][0]-1)<<14;	//IIRCTL2

		//Disable the accelerator
		*pIIRCTL1 = 0;

		IIRA_Init(IIR_EN|IIR_DMAEN|IIR_SS/*|BITM_IIR_CTL1_CCINTR*/|((CHANNEL_NO-1)<<1),(uint32_t*)((((uint32_t)(IIRA_TCB1+12))& OFFSET_MASK)));

		//wait till all channels are done
		while((*pIIRDMASTAT & IIR_DMAACDONE) == 0x00000000);

		//wait for Save state to be complete
		while((*pIIRDMASTAT & (IIR_DMACPL|IIR_DMASVDk)) != 0x0);

		clock_stop=clock();
		cycles=clock_stop-clock_start;

		printf("Window size = %d, Biquads = %d, CCLK cycles = %d\n\n",iir_param_list[i][0], iir_param_list[i][1], cycles);
		fprintf(fpout,"%d\n",cycles);
	}

	fclose(fpout);
	return 0;
}

