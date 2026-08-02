/*****************************************************************************
 * Audio_Passthrough_I2S.h
 *****************************************************************************/

#ifndef __AUDIO_PASSTHROUGH_I2S_H__
#define __AUDIO_PASSTHROUGH_I2S_H__

#include <stdint.h>
#include "Processing.h"
#include <sys/platform.h>
#include "adi_initialize.h"
#include <stdio.h>
#include <stdlib.h>
#include <sys/adi_core.h>
#include "adi_initialize.h"
#include <services/int/adi_int.h>
#include <drivers/sport/adi_sport.h>
#include <services/spu/adi_spu.h>
#include <drivers/twi/adi_twi.h>
#include "ADAU_1962Common.h"
#include "ADAU_1979Common.h"
#include <cdef21569.h>
#include "math.h"
#include "sru21569.h"


#define SLEN 23
#define COUNT BLOCK_SIZE*2


#define SPORT_DEVICE_4A 			4u			/* SPORT device number */
#define SPORT_DEVICE_4B 			4u			/* SPORT device number */
#define TWIDEVNUM     				2u         /* TWI device number */

#define BITRATE       				(100u)      /* kHz */
#define DUTYCYCLE     				(50u)       /* percent */
#define PRESCALEVALUE 				(12u)       /* fSCLK/10MHz (112.5 sclk0_0) */
#define BUFFER_SIZE   				(8u)

#define TARGETADDR    				(0x38u)     /* hardware address */
#define TARGETADDR_1962    			(0x04u)     /* hardware address of adau1962 DAC */
#define TARGETADDR_1979    			(0x11u)     /* hardware address of adau1979 ADC */


#define SPORT_4A_SPU  					57
#define SPORT_4B_SPU   					58

#define DMA_NUM_DESC 					2u

#define SUCCESS   0
#define FAILED   -1

#define CHECK_RESULT(eResult) \
        if(eResult != 0)\
		{\
			return (1);\
        }

#define REPORT_ERROR        	 printf
#define DEBUG_INFORMATION        printf



#endif /* __AUDIO_PASSTHROUGH_I2S_H__ */
