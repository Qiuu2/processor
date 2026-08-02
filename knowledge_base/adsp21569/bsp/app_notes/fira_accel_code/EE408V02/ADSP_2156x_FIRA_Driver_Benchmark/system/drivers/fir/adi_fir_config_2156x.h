/*!
 *****************************************************************************
   @file:    adi_fir_config.h
   @brief:   Configuration options for FIR Driver.
  -----------------------------------------------------------------------------

Copyright (c) 2017 Analog Devices, Inc.

All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
  - Redistributions of source code must retain the above copyright notice,
    this list of conditions and the following disclaimer.
  - Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution.
  - Modified versions of the software must be conspicuously marked as such.
  - This software is licensed solely and exclusively for use with processors
    manufactured by or for Analog Devices, Inc.
  - This software may not be combined or merged with other code in any manner
    that would cause the software to become subject to terms and conditions
    which differ from those listed here.
  - Neither the name of Analog Devices, Inc. nor the names of its
    contributors may be used to endorse or promote products derived
    from this software without specific prior written permission.
  - The use of this software may or may not infringe the patent rights of one
    or more patent holders.  This license does not release you from the
    requirement that you obtain separate licenses from these patent holders
    to use this software.

THIS SOFTWARE IS PROVIDED BY ANALOG DEVICES, INC. AND CONTRIBUTORS "AS IS" AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, NON-INFRINGEMENT,
TITLE, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN
NO EVENT SHALL ANALOG DEVICES, INC. OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, PUNITIVE OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, DAMAGES ARISING OUT OF CLAIMS OF INTELLECTUAL
PROPERTY RIGHTS INFRINGEMENT; PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

*****************************************************************************/

#ifndef ADI_FIR_CONFIG_H
#define ADI_FIR_CONFIG_H

/* This macro enables/disables cache management by the driver. If the application
 * wants to manage cache, this macro has to be disabled
*/
#define ADI_CACHE_MANAGEMENT      (0)


/*Accelerator Mode
 * This Macro allows to set the Accelerator Mode for the Tasks created.
 */

/* Legacy Mode */
#define ADI_FIR_ACCELERATOR_MODE_LEGACY                                     (0u)
/* Auto Configuration Mode */
#define ADI_FIR_ACCELERATOR_MODE_ACM                                        (1u)


/* Configure the Accelerator Mode for the Tasks created.
    It can be configured to one of the following macros:
    - #ADI_FIR_ACCELERATOR_MODE_LEGACY
    - #ADI_FIR_ACCELERATOR_MODE_ACM
 */
#define ADI_FIR_CFG_ACCELERATOR_MODE    (ADI_FIR_ACCELERATOR_MODE_LEGACY)

#if  ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_LEGACY

/* Rounding Mode
 * This Macro allows to set the Output Rounding Mode for the Tasks created.
 */


/* IEEE round to nearest (even) */
#define ADI_FIR_RNDG_MODE_NEAREST_EVEN                                      (0u)

#if defined(__ADSP21569_FAMILY__)

/* Round away from zero */
#define ADI_FIR_RNDG_MODE_TO_ZERO                                           (1u)

#elif defined(__ADSPSC589_FAMILY__) || defined(__ADSPSC573_FAMILY__)

/* IEEE round to +ve infinity */
#define ADI_FIR_RNDG_MODE_POS_INF                                           (1u)
/* IEEE round to -ve infinity */
#define ADI_FIR_RNDG_MODE_NEG_INF                                           (2u)
/* Round to nearest Up */
#define ADI_FIR_RNDG_MODE_NEAREST_UP                                        (3u)
/* Round away from zero */
#define ADI_FIR_RNDG_MODE_AWAY_FROM_ZERO                                    (4u)

#endif /* defined(__ADSP21569_FAMILY__) */

/* Configure the Rounding mode required across all tasks.
    It can be configured to one of the following macros:
    - #ADI_FIR_RNDG_MODE_NEAREST_EVEN
    - #ADI_FIR_RNDG_MODE_POS_INF
    - #ADI_FIR_RNDG_MODE_NEG_INF
    - #ADI_FIR_RNDG_MODE_NEAREST_UP
	- #ADI_FIR_RNDG_MODE_AWAY_FROM_ZERO
 */
#define ADI_FIR_CFG_ROUNDING_MODE    (ADI_FIR_RNDG_MODE_NEAREST_EVEN)

/*
 * This macro enables/disables fixed point mode across all tasks.
 *
 * (0u) - Floating Point Mode
 * (1u) - Fixed point Mode
 */
#define ADI_FIR_FIXED_POINT_MODE            (0u)

#if (ADI_FIR_FIXED_POINT_MODE == 1u)
/* Fixed Point Format
 * This macro allows to set the  Fixed point format as Unsigned Integer or Signed Integer for all tasks.
 * This configuration is applied only in Legacy mode.This macro has effect only if ADI_FIR_FIXED_POINT_MODE is enabled.
 */

/* Unsigned integer */
#define ADI_FIR_IN_FORMAT_UINT              (0u)
/* signed integer */
#define ADI_FIR_IN_FORMAT_SINT              (1u)

/* Configure the Input format required across all tasks.
    It can be configured to one of the following macros:
    - #ADI_FIR_IN_FORMAT_UINT
    - #ADI_FIR_IN_FORMAT_SINT
*/
#define ADI_FIR_CFG_FIXED_INPUT_FORMAT    (ADI_FIR_IN_FORMAT_UINT)

#endif /* (ADI_FIR_FIXED_POINT_MODE == 1u) */

#endif /* ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_LEGACY */

/* Dual Core Driver Mode Support
    Configures the Mode of the Driver as Single Core or Dual Core Mode.
*/

/* The possible values it can be configured to are:

    - 1 : Dual Core mode support.
    - 0 : Single Core Mode support.
*/
#define ADI_FIR_CFG_DUAL_CORE_MODE_SUPPORT      (0)

#if ADI_FIR_CFG_DUAL_CORE_MODE_SUPPORT == 1

/*
 * Configure the Core as Master/Slave Core in Dual Core Environment.
*/

/* The possible values it can be configured to are:

    - 1 : Configure the Core as Master Core.
    - 0 : Configure the Core as Slave Core.
*/
#define ADI_FIR_CFG_MASTER_CORE      (1)

#endif /* ADI_FIR_CFG_DUAL_CORE_MODE_SUPPORT == 1 */
/*
** Verify the macro configuration
*/
#if defined(__ADSP21569_FAMILY__)
#if ((ADI_FIR_CFG_ACCELERATOR_MODE != ADI_FIR_ACCELERATOR_MODE_LEGACY) && \
     (ADI_FIR_CFG_ACCELERATOR_MODE != ADI_FIR_ACCELERATOR_MODE_ACM))
#error "ADI_FIR_CFG_ACCELERATOR_MODE macro is wrongly configured"
#endif /* ADI_FIR_CFG_ACCELERATOR_MODE verification */
#elif defined(__ADSPSC573_FAMILY__) || defined(__ADSPSC589_FAMILY__)
#if ((ADI_FIR_CFG_ACCELERATOR_MODE != ADI_FIR_ACCELERATOR_MODE_LEGACY))
#error "ADI_FIR_CFG_ACCELERATOR_MODE macro is wrongly configured."
#endif /* ADI_FIR_CFG_ACCELERATOR_MODE verification */
#endif /* defined(__ADSP21569_FAMILY__) */

#if  ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_LEGACY

#if defined(__ADSPSC573_FAMILY__) || defined(__ADSPSC589_FAMILY__)
#if ((ADI_FIR_CFG_ROUNDING_MODE != ADI_FIR_RNDG_MODE_NEAREST_EVEN)       && \
     (ADI_FIR_CFG_ROUNDING_MODE != ADI_FIR_RNDG_MODE_POS_INF)            && \
     (ADI_FIR_CFG_ROUNDING_MODE != ADI_FIR_RNDG_MODE_NEG_INF)            && \
     (ADI_FIR_CFG_ROUNDING_MODE != ADI_FIR_RNDG_MODE_NEAREST_UP)         && \
	 (ADI_FIR_CFG_ROUNDING_MODE != ADI_FIR_RNDG_MODE_AWAY_FROM_ZERO))
#error "ADI_FIR_CFG_ROUNDING_MODE macro wrongly configured"
#endif /* ADI_FIR_CFG_ROUNDING_MODE verification */
#elif defined(__ADSP21569_FAMILY__)
#if ((ADI_FIR_CFG_ROUNDING_MODE != ADI_FIR_RNDG_MODE_NEAREST_EVEN)       && \
	 (ADI_FIR_CFG_ROUNDING_MODE != ADI_FIR_RNDG_MODE_TO_ZERO))
#error "ADI_FIR_CFG_ROUNDING_MODE macro wrongly configured"
#endif /* ADI_FIR_CFG_ROUNDING_MODE verification */
#endif /* defined(__ADSPSC573_FAMILY__) || defined(__ADSPSC589_FAMILY__) */

#if  ((ADI_FIR_FIXED_POINT_MODE != 0u)   && \
     (ADI_FIR_FIXED_POINT_MODE != 1u))
#error "ADI_FIR_FIXED_POINT_MODE macro wrongly configured"
#endif /* ADI_FIR_FIXED_POINT_MODE verification */

#if (ADI_FIR_FIXED_POINT_MODE == 1u)

#if ((ADI_FIR_CFG_FIXED_INPUT_FORMAT != ADI_FIR_IN_FORMAT_UINT)       && \
     (ADI_FIR_CFG_FIXED_INPUT_FORMAT != ADI_FIR_IN_FORMAT_SINT))
#error "ADI_FIR_CFG_FIXED_INPUT_FORMAT macro wrongly configured"
#endif /* ADI_FIR_CFG_FIXED_INPUT_FORMAT verification */

#endif /* (ADI_FIR_FIXED_POINT_MODE == 1u) */
#endif /* ADI_FIR_CFG_ACCELERATOR_MODE == ADI_FIR_ACCELERATOR_MODE_LEGACY */

#if defined(__ADSP21569_FAMILY__)
#if ((ADI_FIR_CFG_DUAL_CORE_MODE_SUPPORT != 0))
#error "ADI_FIR_CFG_DUAL_CORE_MODE_SUPPORT macro is wrongly configured"
#endif /* ADI_FIR_CFG_DUAL_CORE_MODE_SUPPORT verification */
#elif defined(__ADSPSC573_FAMILY__) || defined(__ADSPSC589_FAMILY__)
#if ((ADI_FIR_CFG_DUAL_CORE_MODE_SUPPORT != 0) && \
     (ADI_FIR_CFG_DUAL_CORE_MODE_SUPPORT != 1))
#error "ADI_FIR_CFG_DUAL_CORE_MODE_SUPPORT macro is wrongly configured"
#endif /* ADI_FIR_CFG_DUAL_CORE_MODE_SUPPORT verification */
#endif /* defined(__ADSP21569_FAMILY__) */

#if ADI_FIR_CFG_DUAL_CORE_MODE_SUPPORT == 1
#if ((ADI_FIR_CFG_MASTER_CORE != 0) && \
     (ADI_FIR_CFG_MASTER_CORE != 1))
#error "ADI_FIR_CFG_MASTER_CORE macro is wrongly configured"
#endif /* ADI_FIR_CFG_MASTER_CORE verification */
#endif /* ADI_FIR_CFG_DUAL_CORE_MODE_SUPPORT == 1 */

#endif /* ADI_FIR_CONFIG_H */

