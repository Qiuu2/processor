/* 	This code shows real time implementation of the "Direct Replacement" Usage Model of the ADSP-2156x FIR/IIR Accelerators. 
	The real time audio framework uses ADAU1979 ADC and the ADAU1962a DAC on the EZ-Kit to  receive/send 2 channel I2S audio.
	The audio input should be supplied at the first left red and while RCA jacks of the port J7 and should be listened out
	from the first left red and while RCA jacks of the port J17. 
	
	- The code performs real time FIR/IIR processing on 12 channels of audio data. 	
	- Each channel passes through a 512 tap FIR filter followed by a 5 band IIR equalizer. 
	- For simplification, FIR filter used is an All-Pass filter (b0 coefficient is one and all other coefficients are zeros).
	- Each IIR band is an 8th order IIR filter implemented with 4 cascaded biquad stages. The output of each band is multiplied with 
	  the respective gain (from 0.0 min to 1.0 max) and added together to generate the final output. IIRGains flag can be set/cleared dynamically 
	  via CCES memory browser to bypass/enable processing.
	- The block size used is 256 samples per channel. 
	- The example code uses only two channel audio input and output of the ADSP-21569 EZ-Kit. The input data for rest of the 10 channels is â€œzeroâ€�.
	   Since we are interested only in the measurement of the performance numbers, this limitation doesnnâ€™t affect our results.
	- All the buffers are placed in internal (L1) memory.
	- BypassProcessing flag can be set/cleared dynamically via CCES memory browser to bypass/enable processing.
	- cycles_array array can be observed in the expressions window to see the periodic cycle count snapshot trace. This information can be used to calculate MIPS details. 
	- The macro USE_CORE and USE_ACC in "Processing.h" can be used to switch between the "Core Only" and "Accelerator Only" implementation.
*/

#include "Audio_Passthrough_I2S.h"
#include "Processing.h"

/* ADC and DAC configuration tables */
struct Config_Table
{
	short Reg_Add;
	char  Value;
};

char Config_read_DAC[28];
char Config_read_ADC[16];
int count;

struct Config_Table Config_array_DAC[28] = {
		   	    {     ADAU1962_PDN_CTRL_1,		0x00},
		   	    {     ADAU1962_PDN_CTRL_2,	    0xff},
		   	    {     ADAU1962_PDN_CTRL_3,	    0x0f },
		   	    {     ADAU1962_DAC_CTRL0,		0x01},
		   	    {     ADAU1962_DAC_CTRL1,		0x01 },
		   	    {     ADAU1962_DAC_CTRL2,		0x00 },
		   	    {     ADAU1962_DAC_MUTE1,	    0x0},
		   	    {     ADAU1962_DAC_MUTE2,	    0x00},
		   	    {     ADAU1962_MSTR_VOL,		0x00 },
			    {     ADAU1962_DAC1_VOL,	    0x00 } ,
			    {     ADAU1962_DAC2_VOL,		0x00  },
				{     ADAU1962_DAC3_VOL,		0x00 },
				{     ADAU1962_DAC4_VOL,		0x00 },
				{     ADAU1962_DAC5_VOL,		0x00 },
				{     ADAU1962_DAC6_VOL,		0x00  },
				{     ADAU1962_DAC7_VOL,		0x00 },
				{     ADAU1962_DAC8_VOL,	    0x00 },
				{     ADAU1962_DAC9_VOL,		0x00  },
				{     ADAU1962_DAC10_VOL,		0x00},
				{     ADAU1962_DAC11_VOL,		0x00},
				{     ADAU1962_DAC12_VOL,		0x00 },
				{     ADAU1962_PAD_STRGTH,		0x00 },
				{     ADAU1962_DAC_PWR1,		0xaa },
				{     ADAU1962_DAC_PWR2,		0xaa },
				{     ADAU1962_DAC_PWR3,		0xaa },
				{     ADAU1962_PDN_CTRL_2,	    0x00},
				{     ADAU1962_PDN_CTRL_3,	    0x00 },
				{     ADAU1962_DAC_CTRL0,		0x00}

};

struct Config_Table Config_array_ADC[16] = {
		 {ADAU1979_REG_BOOST			,	0x00},
		 {ADAU1979_REG_MICBIAS			,	0x00},
		 {ADAU1979_REG_BLOCK_POWER_SAI	,	0x30},
		 {ADAU1979_REG_SAI_CTRL0		,	0x02},
		 {ADAU1979_REG_SAI_CTRL1		,	0x00},
		 {ADAU1979_REG_CMAP12			,	0x01},
		 {ADAU1979_REG_CMAP34			,	0x00},
		 {ADAU1979_REG_SAI_OVERTEMP		,	0x30},
		 {ADAU1979_REG_POST_ADC_GAIN1 	,	0xA0},
		 {ADAU1979_REG_POST_ADC_GAIN2 	,	0xA0},
		 {ADAU1979_REG_POST_ADC_GAIN3 	,	0xA0},
		 {ADAU1979_REG_POST_ADC_GAIN4 	,	0xA0},
		 {ADAU1979_REG_ADC_CLIP			,	0x00},
		 {ADAU1979_REG_DC_HPF_CAL		,	0x00},
		 {ADAU1979_REG_BLOCK_POWER_SAI	,	0x33},
		 {ADAU1979_REG_MISC_CONTROL		,	0x00}
};



/* SPORT TX and RX buffers */
ADI_CACHE_ALIGN static int   int_SP0ABuffer1[COUNT];
ADI_CACHE_ALIGN static int   int_SP0ABuffer2[COUNT];
ADI_CACHE_ALIGN static int   int_SP0ABuffer4[COUNT];
ADI_CACHE_ALIGN static int   int_SP0ABuffer5[COUNT];


/* SPORT DMA Descriptors */
ADI_PDMA_DESC_LIST iDESC_LIST_1_SP1A;
ADI_PDMA_DESC_LIST iDESC_LIST_2_SP1A;
ADI_PDMA_DESC_LIST iSRC_LIST_1_SP0A;
ADI_PDMA_DESC_LIST iSRC_LIST_2_SP0A;


/* Count to track the number of callBacks for SPORT transfer */
volatile uint8_t CallbackCount = 0;

/* Memory required for SPORT */
static uint8_t SPORTMemory4A[ADI_SPORT_MEMORY_SIZE];
static uint8_t SPORTMemory4B[ADI_SPORT_MEMORY_SIZE];

/* SPORT Handle */
static ADI_SPORT_HANDLE hSPORTDev4ATx;//TX
static ADI_SPORT_HANDLE hSPORTDev4BRx;//RX

/* Memory required for TWI */
uint8_t TwideviceMemory[ADI_TWI_MEMORY_SIZE];

/* TWI driver handle */
static ADI_TWI_HANDLE hTwiDevice;

/* SPU handle */
static ADI_SPU_HANDLE      ghSpu;

/* Memory required for the SPU operation */
uint8_t  SpuMemory[ADI_SPU_MEMORY_SIZE];


/* Dev buffer for configuring ADC-DAC through TWI*/
static uint8_t devBuffer[BUFFER_SIZE];

/* Flag for synchronization between core and SPORT DMA */
volatile bool  BlockReady = false;

/* Flag to optionally bypass processing */
volatile bool BypassProcessing = false;

int ADAU_1962_Pllinit(void);
int ADAU_1979_Pllinit(void);
void Switch_Configurator(void);
void ADAU_1962_init(void);
void ADAU_1979_init(void);
void SRU_Init(void);
static int Sport_Init(void);
static int SPU_init(void);
extern void ConfigSoftSwitches_ADC_DAC(void);
extern void ConfigSoftSwitches_ADAU_Reset(void);
static void Process_Block(void);
void Block_Fixed_To_Float( int * Fixed_In, float * Float_Out_L, float * Float_Out_R, int size );
void Block_Float_To_Fixed( int * Fixed_Out, float * Float_In_L, float * Float_In_R, int size  );

void main()
{
	/**
	 * Initialize managed drivers and/or services that have been added to
	 * the project.
	 * @return zero on success
	 */
	adi_initComponents();

    /* making all the SPORT transactions as secure master */
    if(SPU_init() != SUCCESS)
    {
        REPORT_ERROR("Failed to initialize SPU\n");
    }

    /* Soft Switch Configuration */
	Switch_Configurator();

	/* SRU Initialization */
	SRU_Init();

	/* ADC-DAC Initialization */
	ADAU_1962_init();
	ADAU_1979_init();

	/* One time FIR/IIR accelerator initialization */
	Init_FIR_IIR();

	/* SPORT Initialization */
	Sport_Init();

	START_CYCLE_COUNT

	while(1)
	{
		/* Wait till next block of data is received */
		while(BlockReady==false);

		/* Clear BlockReady flag for next iteration */
		BlockReady = false;

		/* Process current block */
		Process_Block();
	}
}

/* SPORT RX callback */
static void SPORTCallback(
    void        *pAppHandle,
    uint32_t     nEvent,
    void        *pArg
)
{
	int i;

	ADI_SPORT_RESULT eResult;
    /* CASEOF (event type) */
    switch (nEvent)
    {
        /* CASE (buffer processed) */
        case ADI_SPORT_EVENT_RX_BUFFER_PROCESSED:
        		CallbackCount +=1;
        		BlockReady = true;
        		break;
        default:
        	 break;
    }
    /* return */
}

/* SPU Initialization */
static int SPU_init(void)
{
    if(adi_spu_Init(0, SpuMemory, NULL, NULL, &ghSpu) != ADI_SPU_SUCCESS)
    {
    	REPORT_ERROR("Failed to initialize SPU service\n");
		return FAILED;
    }

    /* Make SPORT 0A to generate secure transactions */
    if(adi_spu_EnableMasterSecure(ghSpu, SPORT_4A_SPU, true) != ADI_SPU_SUCCESS)
    {
    	REPORT_ERROR("Failed to enable Master secure for SPORT0A\n");
		return FAILED;
    }

    /* Make SPORT 0B to generate secure transactions */
    if(adi_spu_EnableMasterSecure(ghSpu, SPORT_4B_SPU, true) != ADI_SPU_SUCCESS)
    {
    	REPORT_ERROR("Failed to enable Master secure for SPORT0B\n");
		return FAILED;
    }

    return SUCCESS;
}

/* Soft Switch Configuration */
void Switch_Configurator()
{
	int delay11=0xffff;


	/* Software Switch Configuration for Enabling ADC-DAC */
	ConfigSoftSwitches_ADC_DAC();

	while(delay11--)
	{
		asm("nop;");
	}

	/* Software Switch Configuration for Re-Setting ADC-DAC  */
	ConfigSoftSwitches_ADAU_Reset();


	/* wait for Codec to up */
	delay11=0xffff;
	while(delay11--)
	{
		asm("nop;");
	}
}

/* SRU Initialization */
void SRU_Init(void)
{
	*pREG_PADS0_DAI0_IE=0x1ffffe;
	*pREG_PADS0_DAI1_IE=0x1ffffe;

    SRU2(LOW,DAI1_PBEN05_I);

    SRU2(DAI1_PB05_O,SPT4_ACLK_I);
    SRU2(DAI1_PB05_O,SPT4_BCLK_I);

    SRU2(DAI1_PB04_O,SPT4_AFS_I);
    SRU2(DAI1_PB04_O,SPT4_BFS_I);
    SRU2(LOW,DAI1_PBEN04_I);

    SRU2(SPT4_AD0_O,DAI1_PB01_I);
    SRU2(HIGH,DAI1_PBEN01_I);

    SRU2(DAI1_PB05_O,DAI1_PB12_I);

    SRU2(HIGH,DAI1_PBEN12_I);

    SRU2(DAI1_PB04_O,DAI1_PB20_I);

    SRU2(HIGH,DAI1_PBEN20_I);

    SRU2(DAI1_PB06_O,SPT4_BD0_I);
    SRU2(LOW,DAI1_PBEN06_I);

}

/* Prepare SPORT Descriptors */
static void PrepareDescriptors (void)
{

	iDESC_LIST_1_SP1A.pStartAddr	= (int *)int_SP0ABuffer1;
	iDESC_LIST_1_SP1A.Config		= ENUM_DMA_CFG_XCNT_INT ;
	iDESC_LIST_1_SP1A.XCount		= COUNT;
	iDESC_LIST_1_SP1A.XModify		= 4;
	iDESC_LIST_1_SP1A.YCount		= 0;
	iDESC_LIST_1_SP1A.YModify		= 0;
	iDESC_LIST_1_SP1A.pNxtDscp		= &iDESC_LIST_2_SP1A;

	iDESC_LIST_2_SP1A.pStartAddr	= (int *)int_SP0ABuffer2;
	iDESC_LIST_2_SP1A.Config		= ENUM_DMA_CFG_XCNT_INT ;
	iDESC_LIST_2_SP1A.XCount		= COUNT;
	iDESC_LIST_2_SP1A.XModify		= 4;
	iDESC_LIST_2_SP1A.YCount		= 0;
	iDESC_LIST_2_SP1A.YModify		= 0;
	iDESC_LIST_2_SP1A.pNxtDscp		= &iDESC_LIST_1_SP1A;

	iSRC_LIST_1_SP0A.pStartAddr		=(int *)int_SP0ABuffer4;
	iSRC_LIST_1_SP0A.Config			= ENUM_DMA_CFG_XCNT_INT ;
	iSRC_LIST_1_SP0A.XCount			= COUNT;
	iSRC_LIST_1_SP0A.XModify		= 4;
	iSRC_LIST_1_SP0A.YCount			= 0;
	iSRC_LIST_1_SP0A.YModify		= 0;
	iSRC_LIST_1_SP0A.pNxtDscp		= &iSRC_LIST_2_SP0A;

	iSRC_LIST_2_SP0A.pStartAddr		=(int *)int_SP0ABuffer5;
	iSRC_LIST_2_SP0A.Config			= ENUM_DMA_CFG_XCNT_INT;
	iSRC_LIST_2_SP0A.XCount			= COUNT;
	iSRC_LIST_2_SP0A.XModify		= 4;
	iSRC_LIST_2_SP0A.YCount			= 0;
	iSRC_LIST_2_SP0A.YModify		= 0;
	iSRC_LIST_2_SP0A.pNxtDscp		= &iSRC_LIST_1_SP0A;
}

/* SPORT Initialization */
static int Sport_Init(void)
{
    /* SPORT return code */
    ADI_SPORT_RESULT    eResult;

	/* Open the SPORT Device 4A */
	eResult = adi_sport_Open(SPORT_DEVICE_4A,ADI_HALF_SPORT_A,ADI_SPORT_DIR_TX, ADI_SPORT_I2S_MODE, SPORTMemory4A,ADI_SPORT_MEMORY_SIZE,&hSPORTDev4ATx);
	CHECK_RESULT(eResult);
	/* Open the SPORT Device 4B*/
	eResult = adi_sport_Open(SPORT_DEVICE_4B,ADI_HALF_SPORT_B,ADI_SPORT_DIR_RX, ADI_SPORT_I2S_MODE, SPORTMemory4B,ADI_SPORT_MEMORY_SIZE,&hSPORTDev4BRx);
	CHECK_RESULT(eResult);

	/* Register SPORT Callback function */
	eResult = adi_sport_RegisterCallback(hSPORTDev4BRx,SPORTCallback,NULL);
	CHECK_RESULT(eResult);

	/* Prepare descriptors */
	PrepareDescriptors();

	/* Submit the first buffer for Rx.  */
	eResult = adi_sport_DMATransfer(hSPORTDev4BRx,&iSRC_LIST_1_SP0A,(DMA_NUM_DESC),ADI_PDMA_DESCRIPTOR_LIST, ADI_SPORT_CHANNEL_PRIM);
	CHECK_RESULT(eResult);
	/* Submit the first buffer for Tx.  */
	eResult = adi_sport_DMATransfer(hSPORTDev4ATx,&iDESC_LIST_1_SP1A,(DMA_NUM_DESC),ADI_PDMA_DESCRIPTOR_LIST, ADI_SPORT_CHANNEL_PRIM);
	CHECK_RESULT(eResult);

	/*Enable the Sport Device 4B */
	eResult = adi_sport_Enable(hSPORTDev4BRx,true);
	CHECK_RESULT(eResult);
	/*Enable the Sport Device 4A */
	eResult = adi_sport_Enable(hSPORTDev4ATx,true);
	CHECK_RESULT(eResult);

	return 0;

}

/* Function to write 8 bit register via TWI */
void Write_TWI_8bit_Reg(unsigned char Reg_ID, unsigned char Tx_Data)
{
	devBuffer[0] = Reg_ID;
	devBuffer[1] = Tx_Data;
	adi_twi_Write(hTwiDevice, devBuffer, 2u, false);
}

/* Function to read 8 bit register via TWI */
unsigned char Read_TWI_8bit_Reg(unsigned char Reg_ID)
{
	ADI_TWI_RESULT eResult;
	unsigned char Rx_Data;

	/* write register address */
	devBuffer[0] = Reg_ID;
	eResult = adi_twi_Write(hTwiDevice, devBuffer, 1u, true);
	if(eResult!=ADI_TWI_SUCCESS)
	{
		REPORT_ERROR("TWI write failed 0x%08X\n", eResult);
	}

	/* read register value */
	eResult = adi_twi_Read(hTwiDevice, &Rx_Data, 1u, false);
	if(eResult!=ADI_TWI_SUCCESS)
	{
		REPORT_ERROR("TWI Read failed 0x%08X\n", eResult);
	}

	return Rx_Data;
}

/* TWI one time initialization */
int Init_TWI(void)
{

	ADI_TWI_RESULT eResult;

	eResult = adi_twi_Open(TWIDEVNUM, ADI_TWI_MASTER, &TwideviceMemory[0],
			   	ADI_TWI_MEMORY_SIZE, &hTwiDevice);
	CHECK_RESULT(eResult);

	eResult = adi_twi_SetPrescale(hTwiDevice, PRESCALEVALUE);
	CHECK_RESULT(eResult);

	eResult = adi_twi_SetBitRate(hTwiDevice, BITRATE);
	CHECK_RESULT(eResult);

	eResult = adi_twi_SetDutyCycle(hTwiDevice, DUTYCYCLE);
	CHECK_RESULT(eResult);

	eResult = adi_twi_SetHardwareAddress(hTwiDevice, TARGETADDR);
	CHECK_RESULT(eResult);

	return 0;
}
/*****************************************************************************************************************************/

/* ADAU 1962 Initialization */
void ADAU_1962_init(void)
{	int i;
    Init_TWI();
     ADAU_1962_Pllinit();

		for(i=0;i<28;i++)
		{
			/* write value */
			Write_TWI_8bit_Reg(Config_array_DAC[i].Reg_Add,Config_array_DAC[i].Value);
			Config_read_DAC[i]=Read_TWI_8bit_Reg(Config_array_DAC[i].Reg_Add);
            if(Config_array_DAC[i].Value!= Config_read_DAC[i])
			{
            	DEBUG_INFORMATION("\n fail");
			}
		}
}

/* ADAU 1962 PLL Initialization */
int ADAU_1962_Pllinit(void)
{
	int status,delay1=0xffff;

	ADI_TWI_RESULT eResult;

   	eResult = adi_twi_SetHardwareAddress(hTwiDevice, TARGETADDR_1962);
   	CHECK_RESULT(eResult);

		Write_TWI_8bit_Reg(ADAU1962_PLL_CTL_CTRL0,0x01);
		while(delay1--)
				{
					asm("nop;");
				}

		Write_TWI_8bit_Reg(ADAU1962_PLL_CTL_CTRL0,0x05);

		delay1=0xffff;
				while(delay1--)
						{
							asm("nop;");
						}

		Write_TWI_8bit_Reg(ADAU1962_PLL_CTL_CTRL1,0x22);
		delay1=0xffff;
		while(delay1--)
		{
			asm("nop;");
		}
		status=Read_TWI_8bit_Reg(ADAU1962_PLL_CTL_CTRL1);
		while(!((status & 0x4)>>2)  )
		{
			status=Read_TWI_8bit_Reg(ADAU1962_PLL_CTL_CTRL1);
		}

		return 0;
}

/* ADAU 1979 Initialization */
void ADAU_1979_init(void)
{	int i;
     Init_TWI();
     ADAU_1979_Pllinit();
		for(i=0;i<16;i++)
		{
			Write_TWI_8bit_Reg(Config_array_ADC[i].Reg_Add,Config_array_ADC[i].Value);
			Config_read_ADC[i]=Read_TWI_8bit_Reg(Config_array_ADC[i].Reg_Add);
            if(Config_array_ADC[i].Value!= Config_read_ADC[i])
			{
            	DEBUG_INFORMATION("\n fail");
			}
		}
}

/* ADAU 1979 PLL Initialization */
int ADAU_1979_Pllinit(void)
{

	int status,delay1=0xffff;

	ADI_TWI_RESULT eResult;

   	eResult = adi_twi_SetHardwareAddress(hTwiDevice, TARGETADDR_1979);
   	CHECK_RESULT(eResult);

   	Write_TWI_8bit_Reg(ADAU1979_REG_POWER,0x01);
	Write_TWI_8bit_Reg(ADAU1979_REG_PLL,0x03);
	status=Read_TWI_8bit_Reg(ADAU1979_REG_PLL);
	while(delay1--)
			{
				asm("nop;");
			}
	while(!((status & 0x80)>>7)  )
	{
		status=Read_TWI_8bit_Reg(ADAU1979_REG_PLL);
		asm("nop;");
	}

	return 0;

}


/* Convert fixed point data to floating point with 2^-31 scaling */
void Block_Fixed_To_Float( int * Fixed_In, float * Float_Out_L, float * Float_Out_R, int size )
{
	int i;

	for (i=0;i<size;i++)
	{
		Float_Out_L[i]  = ((float) (Fixed_In[2*i]<<8))   * (1.0/2147483648.0);
		Float_Out_R[i]  = ((float) (Fixed_In[2*i+1]<<8)) * (1.0/2147483648.0);
	}
}

/* Convert floating point data to fixed point with 2^-31 scaling */
void Block_Float_To_Fixed( int * Fixed_Out, float * Float_In_L, float * Float_In_R, int size  )
{

	int i;
	for (i=0;i<size;i++)
	{
		Fixed_Out[2*i]   = ((int) (2147483648.0*Float_In_L[i]))>>8;
		Fixed_Out[2*i+1] = ((int) (2147483648.0*Float_In_R[i]))>>8;
	}
}

/* Write pointer for circular buffer access for FIR accelerator processing */
volatile unsigned int wp = WP_START;

/* Function to process a block of data, total 12 channels are processed but only the first two channels use valid audio data */
static void Process_Block()
{
	int i;

	/* Ping buffer */
	if(CallbackCount==1)
	{
		if(BypassProcessing==false)
		{
		  /* Accelerator Processing */
		  /* Accelerator needs input buffer to hold at least BLOCK_SIZE+FIR_TAPS-1 words for delay line preload, thus we need to maintain circular buffering */
		   #ifdef USE_ACC
				Block_Fixed_To_Float( (int*)&int_SP0ABuffer4, &Input[0][wp], &Input[1][wp], BLOCK_SIZE );
				wp+=BLOCK_SIZE;
				wp=wp%(CIRCULAR_BUFFER_LENGTH);
		   /* Core Processing */
		   #else
				Block_Fixed_To_Float( (int*)&int_SP0ABuffer4, Input[0], Input[1], BLOCK_SIZE );
		   #endif

		   TAKE_CYCLE_SNAPSHOT
		   Process_FIR_IIR();
		   TAKE_CYCLE_SNAPSHOT

		   Block_Float_To_Fixed( (int*)&int_SP0ABuffer1, Output[0], Output[1], BLOCK_SIZE  );
		}
		else
		{
			for(i=0;i<COUNT;i++)
		    {
			   int_SP0ABuffer1[i]=int_SP0ABuffer4[i]; /*Copy ADC buffer to DAC buffer */
		    }
		}
	}

	/* Pong buffer */
	if(CallbackCount==2)
	{
		if(BypassProcessing==false)
		{
			/* Accelerator Processing */
			/* Accelerator needs input buffer to hold at least BLOCK_SIZE+FIR_TAPS-1 words for delay line preload, thus we need to maintain circular buffering */
			#ifdef USE_ACC
					Block_Fixed_To_Float( (int*)&int_SP0ABuffer5, &Input[0][wp], &Input[1][wp], BLOCK_SIZE );
					wp+=BLOCK_SIZE;
					wp=wp%(CIRCULAR_BUFFER_LENGTH);
			/* Core Processing */
			#else
					Block_Fixed_To_Float( (int*)&int_SP0ABuffer5, Input[0], Input[1], BLOCK_SIZE );
			#endif

			TAKE_CYCLE_SNAPSHOT
			Process_FIR_IIR();
			TAKE_CYCLE_SNAPSHOT

			Block_Float_To_Fixed( (int*)&int_SP0ABuffer2, Output[0], Output[1], BLOCK_SIZE  );
		}
		else
		{
			for(i=0;i<COUNT;i++)
		    {
			   int_SP0ABuffer2[i]=int_SP0ABuffer5[i]; /*Copy ADC buffer to DAC buffer */
		    }
		}

	    CallbackCount=0;
	}
}
