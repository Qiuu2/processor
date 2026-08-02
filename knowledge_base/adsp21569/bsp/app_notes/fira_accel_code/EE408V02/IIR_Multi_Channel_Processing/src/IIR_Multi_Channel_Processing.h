/*********************************************************************************
Copyright(c) 2019 Analog Devices, Inc. All Rights Reserved.
This software is proprietary and confidential. By using this software you agree
to the terms of the associated Analog Devices License Agreement.
*********************************************************************************/

/*****************************************************************************
 * IIR_Multi_Channel_Processing.h
 *****************************************************************************/

#ifndef __IIR_MULTI_CHANNEL_PROCESSING_H__
#define __IIR_MULTI_CHANNEL_PROCESSING_H__

/* Biquads. Note that Biquad number can be varied across channels of a task*/
#define BIQUADS   12

/* Window Size. Note that Window size can be varied across channels in a task */
#define IIR_WINDOW_SIZE    1024

/* Number of IIR Tasks */
#define IIR_NUMBER_OF_TASKS    2

/* Number of Channels in IIR task 1 */
#define IIR_NUMBER_OF_CHANNELS_TASK1    2

/* Number of Channels in IIR task 2 */
#define IIR_NUMBER_OF_CHANNELS_TASK2    2

/* Total Number of Channels */
#define IIR_NUMBER_OF_CHANNELS    (IIR_NUMBER_OF_CHANNELS_TASK1 + IIR_NUMBER_OF_CHANNELS_TASK2)

/* IIR Task 1 Memory Size */
#define IIR_MEM_SIZE_TASK1    (IIR_MEM_SIZE(IIR_NUMBER_OF_CHANNELS_TASK1))

/* IIR Task 2 Memory Size */
#define IIR_MEM_SIZE_TASK2    (IIR_MEM_SIZE(IIR_NUMBER_OF_CHANNELS_TASK2))

/* Macro for checking Result returned by the driver after API call */
#define CHECK_IIR_RESULT(eResult) \
        if(eResult != ADI_IIR_RESULT_SUCCESS)\
		{\
            printf("CHECK_RESULT failed at line %d of file %s \n",__LINE__,__FILE__);\
            exit(-2);\
        }


#define MAX_DIFF_LIMIT 0.001

/* Macro for checking Maximum Diff exceeding the limit */
#define CHECK_MAX_DIFF(max_diff) \
        if(max_diff > MAX_DIFF_LIMIT)\
		{\
            printf("CHECK_MAX_DIFF failed at line %d of file %s \n",__LINE__,__FILE__);\
            exit(-2);\
        }
#endif /* __IIR_MULTI_CHANNEL_PROCESSING_H__ */
