/*****************************************************************************
 * FIR_Throughput_21569.c
 
 This Code can be used to measure the number of CCLK cycles taken by the FIR Accelerator to perform FIR operation for any combination of Taps and Window Size on ADSP-21569.
 The number of combinations of {Window,Taps} for which the cycles are required are given in ParamList.dat file present in the source folder of the project.
 The project Header file(FIR_Throughput_21569.h) has a macro TOTAL_PARAMETERS which should be configured to the number of combinations of {Window,Taps} present in ParamList.dat file.
 On Execution of the code, the CCLK cycles taken for each combination of {Window,Taps} are printed on the console and also written to a Excel Sheet in the Debug folder of the project.
 *****************************************************************************/

/* Note : The numbers measured are with cache disabled */

#include <sys/platform.h>
#include "adi_initialize.h"
#include "FIR_Throughput_21569.h"
#include <stdio.h>
#include <time.h>

volatile clock_t clock_start;
volatile clock_t clock_stop;
volatile clock_t cycles;

int FIRA_TCB[FIR_TCB_SIZE];

#pragma section("seg_l1_block1")
float InputBuff[MAX_TAP_LENGTH+MAX_WINDOW_SIZE-1];

#pragma section("seg_l1_block1")
float CoeffBuff[MAX_TAP_LENGTH];

#pragma section("seg_l1_block1")
float OutputBuff[MAX_WINDOW_SIZE];

uint32_t fir_param_list[TOTAL_PARAMETERS][2]=
{
	/* Window, Taps */
#include "ParamList.dat"
};

void FIRA_Init(uint32_t uiFIR_GCTL, uint32_t* uiFIR_CHNPTR)
{
	*pREG_FIR0_CHNPTR=(uint32_t)uiFIR_CHNPTR;
	clock_start=clock();
	*pREG_FIR0_CTL1=uiFIR_GCTL;
}

uint32_t i = 0;
int main(int argc, char *argv[])
{
	/**
	 * Initialize managed drivers and/or services that have been added to 
	 * the project.
	 * @return zero on success 
	 */
	adi_initComponents();
	
	FILE * fpout;

	fpout = fopen("Results(Cycles).csv","w+");

	for(i=0;i<TOTAL_PARAMETERS;i++)
	{
		//Initialize FIR TCBs for both the channels
		FIRA_TCB[0]=0;//((int)(FIRA_TCB2+12)>>2)|MP_OFFSET;	//CP
		FIRA_TCB[1]=fir_param_list[i][1];	//CL
		FIRA_TCB[2]=1;	//CM
		FIRA_TCB[3]=((int)CoeffBuff>>2)|MP_OFFSET;	//CI
		FIRA_TCB[4]=((int)OutputBuff>>2)|MP_OFFSET;	//OB
		FIRA_TCB[5]=fir_param_list[i][0];	//OL
		FIRA_TCB[6]=1;	//OM
		FIRA_TCB[7]=((int)OutputBuff>>2)|MP_OFFSET;	//OI
		FIRA_TCB[8]=((int)InputBuff>>2)|MP_OFFSET;	//IB
		FIRA_TCB[9]=fir_param_list[i][1]+fir_param_list[i][0]-1;	//IL
		FIRA_TCB[10]=1;	//IM
		FIRA_TCB[11]=((int)InputBuff>>2)|MP_OFFSET;	//II
		FIRA_TCB[12]=(fir_param_list[i][1]-1)|(fir_param_list[i][0]-1)<<BITP_FIR_CTL2_WINDOW;	//FIRCTL2

		//Disable accelerator
		*pREG_FIR0_CTL1 &= ~(BITM_FIR_CTL1_EN);

		//Start the IIR accelerator
		FIRA_Init(BITM_FIR_CTL1_EN|BITM_FIR_CTL1_DMAEN|(CHANNEL_NO-1)<<BITP_FIR_CTL1_CH|BITM_FIR_CTL1_BURSTEN,(uint32_t *)(((int)(FIRA_TCB+12)>>2)|MP_OFFSET));

		//wait till all channels are done
		while((*pREG_FIR0_DMASTAT & BITM_FIR_DMASTAT_ACDONE) == 0x00000000);

		clock_stop=clock();
		cycles=clock_stop-clock_start;

		printf("Window size = %d, Tap length = %d, CCLK cycles = %d\n\n",fir_param_list[i][0], fir_param_list[i][1], cycles);
		fprintf(fpout,"%d\n",cycles);
	}
	fclose(fpout);
    return 0;
}

