/*****************************************************************************
 * FIR_Core_Throughput_21569.c
 
 This Code can be used to measure the number of CCLK cycles taken by the core to perform FIR operation using the CCES Library function for any combination of Taps and Window Size on ADSP-21569.
 The number of combinations of {Window,Taps} for which the cycles are required are given in ParamList.dat file present in the source folder of the project.
 The project Header file(FIR_Core_Throughput_21569.h) has a macro TOTAL_PARAMETERS which should be configured to the number of combinations of {Window,Taps} present in ParamList.dat file.
 On Execution of the code, the CCLK cycles taken for each combination of {Window,Taps} are printed on the console and also written to a Excel Sheet in the Debug folder of the project.
 *****************************************************************************/

#include <sys/platform.h>
#include "adi_initialize.h"
#include "FIR_Core_Throughput_21569.h"
#include <filter.h>
#include <stdio.h>
#include <time.h>

/** 
 * If you want to use command program arguments, then place them in the following string. 
 */
char __argv_string[] = "";

volatile clock_t clock_start;
volatile clock_t clock_stop;
volatile clock_t cycles;

float input[MAX_WINDOW_SIZE];
float output[MAX_WINDOW_SIZE];
float pm coeffs[MAX_TAP_LENGTH];     /* coeffs array must be         */
                                     /* initialized and in PM memory */
float state[MAX_TAP_LENGTH+1];

uint32_t fir_param_list[TOTAL_PARAMETERS][2]=
{
	/* Window, Taps */
#include "ParamList.dat"
};

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


		for(int j=0;j<MAX_TAP_LENGTH+1;j++)
		{
			state[j] = 0;
		}

		clock_start=clock();

		fir(&input[0], &output[0], &coeffs[0], &state[0], fir_param_list[i][0], fir_param_list[i][1]);

		clock_stop=clock();
		cycles=clock_stop-clock_start;

		printf("Window size = %d, Tap length = %d, CCLK cycles = %d\n\n",fir_param_list[i][0], fir_param_list[i][1], cycles);
		fprintf(fpout,"%d\n",cycles);
	}
	fclose(fpout);

	return 0;
}

