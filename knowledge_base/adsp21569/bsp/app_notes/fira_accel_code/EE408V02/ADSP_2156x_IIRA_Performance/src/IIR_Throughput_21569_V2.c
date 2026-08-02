/*****************************************************************************
 * IIR_Throughput_21569_V2.c
 This Code can be used to measure the number of CCLK cycles taken by the IIR Accelerator to perform IIR operation for any combination of Biquads and Window Size on ADSP-21569.
 The number of combinations of {Window,Biquads} for which the cycles are required are given in ParamList.dat file present in the source folder of the project.
 The project Header file(IIR_Throughput_21569_V2.h) has a macro TOTAL_PARAMETERS which should be configured to the number of combinations of {Window,Biquads} present in ParamList.dat file.
 On Execution of the code, the CCLK cycles taken for each combination of {Window,Biquads} are printed on the console and also written to a Excel Sheet in the Debug folder of the project.
 *****************************************************************************/

#include <sys/platform.h>
#include "adi_initialize.h"
#include "IIR_Throughput_21569_V2.h"
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>

volatile clock_t clock_start;
volatile clock_t clock_stop;
volatile clock_t cycles;

uint32_t IIRA_TCB[IIR_TCB_SIZE];

#pragma section("seg_l1_block1")
float OutputBuff[MAX_WINDOW_SIZE];

#pragma section("seg_l1_block1")
float InputBuff[MAX_WINDOW_SIZE];

#pragma section("seg_l1_block1")
float CoeffBuff[7*MAX_BIQUADS];


uint32_t iir_param_list[TOTAL_PARAMETERS][2]=
{
	/* Window, Biquads */
#include "ParamList.dat"
};

void IIRA_Init(uint32_t uiIIR_GCTL, uint32_t* uiIIR_CHNPTR)
{
	*pREG_IIR0_CHNPTR=(uint32_t)uiIIR_CHNPTR;
	clock_start=clock();
	*pREG_IIR0_CTL1=uiIIR_GCTL;
}

int main()
{

	uint32_t i;

	adi_initComponents();

	FILE * fpout;
	fpout = fopen("Results(cycles).csv","w+");

	for(i=0;i<TOTAL_PARAMETERS;i++)
	{
		//Initialize IIR TCBs
		IIRA_TCB[0]=((uint32_t)(IIRA_TCB+12)>>2)|MP_OFFSET;	//CP
		IIRA_TCB[1]=iir_param_list[i][1]*7;	//CL
		IIRA_TCB[2]=1;	//CM
		IIRA_TCB[3]=((uint32_t)CoeffBuff>>2)|MP_OFFSET;	//CI
		IIRA_TCB[4]=((uint32_t)OutputBuff>>2)|MP_OFFSET;	//OB
		IIRA_TCB[5]=iir_param_list[i][0];	//OL
		IIRA_TCB[6]=1;	//OM
		IIRA_TCB[7]=((uint32_t)OutputBuff>>2)|MP_OFFSET;	//OI
		IIRA_TCB[8]=((uint32_t)InputBuff>>2)|MP_OFFSET;	//IB
		IIRA_TCB[9]=iir_param_list[i][0];	//IL
		IIRA_TCB[10]=1;	//IM
		IIRA_TCB[11]=((uint32_t)InputBuff>>2)|MP_OFFSET;	//II
		IIRA_TCB[12]=(iir_param_list[i][1]-1)|((iir_param_list[i][0]-1)<<BITP_IIR_CTL2_WINDOW);	//IIRCTL2

		//Disable accelerator
		*pREG_IIR0_CTL1 &= ~BITM_IIR_CTL1_EN;

		//Start the IIR accelerator
		IIRA_Init(BITM_IIR_CTL1_EN|BITM_IIR_CTL1_DMAEN|((CHANNEL_NO-1)<<BITP_IIR_CTL1_CH)|BITM_IIR_CTL1_BURSTEN|BITM_IIR_CTL1_SS,(uint32_t*)(((uint32_t)(IIRA_TCB+12)>>2)|MP_OFFSET));

		//wait till all channels are done
		while((*pREG_IIR0_DMASTAT & BITM_IIR_DMASTAT_ACDONE) == 0x00000000);

		//wait for Save state to be complete
		while((*pREG_IIR0_DMASTAT & (BITM_IIR_DMASTAT_CPLD|BITM_IIR_DMASTAT_SVDK)) != 0x0);

		clock_stop=clock();
		cycles=clock_stop-clock_start;

		printf("Window size = %d, Biquads = %d, CCLK cycles = %d\n\n",iir_param_list[i][0], iir_param_list[i][1], cycles);
		fprintf(fpout,"%d\n",cycles);
	}
	fclose(fpout);
	return 0;
}
