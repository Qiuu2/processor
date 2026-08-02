/*****************************************************************************
 * ADSP-21489_FIR.c
 
 This Code can be used to measure the number of CCLK cycles taken by the FIR Accelerator to perform FIR operation for any combination of Taps and Window Size on ADSP-21489.
 The number of combinations of {Window,Taps} for which the cycles are required are given in ParamList.dat file present in the source folder of the project.
 The project Header file(ADSP-21489_FIR.h) has a macro TOTAL_PARAMETERS which should be configured to the number of combinations of {Window,Taps} present in ParamList.dat file.
 On Execution of the code, the CCLK cycles taken for each combination of {Window,Taps} are printed on the console and also written to a Excel Sheet in the Debug folder of the project.
 *****************************************************************************/

#include <sys/platform.h>
#include "adi_initialize.h"
#include "ADSP-21489_FIR.h"
#include <stdio.h>
#include <time.h>
#include <services/int/adi_int.h>

#define OFFSET_MASK 0x7FFFF
#define PCI 0x80000

uint32_t FIRA_TCB1[FIR_TCB_SIZE];

float uiOutputBuff1[MAX_WINDOW_SIZE];
float uiInputBuff1[MAX_TAP_LENGTH+MAX_WINDOW_SIZE-1];
float uiCoeffBuff1[MAX_TAP_LENGTH];

uint32_t fir_param_list[TOTAL_PARAMETERS][2]=
{
	/* Window, Taps */
#include "ParamList.dat"
};

volatile clock_t clock_start;
volatile clock_t clock_stop;
volatile clock_t cycles;

void FIRA_Init(uint32_t uiFIR_GCTL, uint32_t* uiFIR_CHNPTR)
{
	*pCPFIR=(uint32_t)uiFIR_CHNPTR;
	clock_start=clock();
	*pFIRCTL1=uiFIR_GCTL;
}


int main(int argc, char *argv[])
{

	int i;

	adi_initComponents();

	/* Select the FIR accelerator */
	*pPMCTL1&=~(BIT_17|BIT_18);
	/* Replace GP Timer Interrupt */
	//*pPICR1 |= P10I0 | P10I1 | P10I3 | P10I4;
	/* Install the FIR interrupt handler */
	//adi_int_InstallHandler(ADI_CID_P10I,&FIR_DMA_Interrupt_Handler1,0,true);

	FILE * fpout;

	fpout = fopen("Results(Cycles).csv","w+");

	for(i=0;i<TOTAL_PARAMETERS;i++)
	{
		//Initialize FIR TCBs
		FIRA_TCB1[0]=0;//((((uint32_t)(FIRA_TCB2+12))& OFFSET_MASK));	//CP
		FIRA_TCB1[1]=fir_param_list[i][1];	//CL
		FIRA_TCB1[2]=1;	//CM
		FIRA_TCB1[3]=(uint32_t)uiCoeffBuff1;	//CI
		FIRA_TCB1[4]=(uint32_t)uiOutputBuff1;	//OB
		FIRA_TCB1[5]=fir_param_list[i][0];	//OL
		FIRA_TCB1[6]=1;	//OM
		FIRA_TCB1[7]=(uint32_t)uiOutputBuff1;	//OI
		FIRA_TCB1[8]=(uint32_t)uiInputBuff1;	//IB
		FIRA_TCB1[9]=fir_param_list[i][1]+fir_param_list[i][0]-1;	//IL
		FIRA_TCB1[10]=1;	//IM
		FIRA_TCB1[11]=(uint32_t)uiInputBuff1;	//II
		FIRA_TCB1[12]=(fir_param_list[i][1]-1)|(fir_param_list[i][0]-1)<<14;	//FIRCTL2

		//Disable the accelerator
		*pFIRCTL1=0;

		//Start the FIR accelerator
		FIRA_Init(FIR_EN|FIR_DMAEN|(CHANNEL_NO-1)<<1,(uint32_t*)((((uint32_t)(FIRA_TCB1+12))& OFFSET_MASK)));

		//wait till all channels are done
		while((*pFIRDMASTAT & FIR_DMAACDONE) == 0x00000000);

		clock_stop=clock();
		cycles=clock_stop-clock_start;

		printf("Window size = %d, Tap length = %d, CCLK cycles = %d\n\n",fir_param_list[i][0], fir_param_list[i][1], cycles);
		fprintf(fpout,"%d\n",cycles);
    }

	fclose(fpout);
    return 0;
}
