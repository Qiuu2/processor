/*!
 *****************************************************************************
   @file:    adi_iir_config_2156x.h
   @brief:   Configuration options for IIR Driver.
  -----------------------------------------------------------------------------

Copyright (c) 2018 Analog Devices, Inc.

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
/** @addtogroup IIR_Driver IIR Accelerator Driver
 *  @{
 */
 
 /** @addtogroup IIR_Driver_Static_Configuration IIR Accelerator Driver Static Configuration
 *  @{
 */
 
#ifndef ADI_IIR_CONFIG_2156X_H
#define ADI_IIR_CONFIG_2156X_H

#ifdef _MISRA_RULES
#pragma diag(push)
#pragma diag(suppress:misra_rule_5_1:"Allow identifiers to be more than 31 characters")
#endif

/*! This macro enables/disables cache management by the driver.\n If the application
 *  wants to manage cache, this macro has to be set to 0.
*/
#define ADI_CACHE_MANAGEMENT      (0)

/*! Legacy Mode                      */
#define ADI_IIR_ACCELERATOR_MODE_LEGACY                                     (0u)
/*! Auto Configuration Mode          */
#define ADI_IIR_ACCELERATOR_MODE_ACM                                        (1u)


/*! This Macro allows to set the Accelerator Mode for the Tasks created.\n
    It can be configured to one of the following macros:
    - #ADI_IIR_ACCELERATOR_MODE_LEGACY
    - #ADI_IIR_ACCELERATOR_MODE_ACM
 */
#define ADI_IIR_CFG_ACCELERATOR_MODE    (ADI_IIR_ACCELERATOR_MODE_LEGACY)

/*! @cond PRIVATE */
#if  ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_LEGACY
/*! @endcond */

/*! IEEE round to nearest (even)     */
#define ADI_IIR_RNDG_MODE_NEAREST_EVEN                                      (0u)

/*! Round to zero             */
#define ADI_IIR_RNDG_MODE_TO_ZERO                                           (1u)

#if defined(__ADSPSC589_FAMILY__) || defined(__ADSPSC573_FAMILY__)

/*! IEEE round to +ve infinity       */
#define ADI_IIR_RNDG_MODE_POS_INF                                           (2u)
/*! IEEE round to -ve infinity       */
#define ADI_IIR_RNDG_MODE_NEG_INF                                           (3u)
/*! Round to nearest Up              */
#define ADI_IIR_RNDG_MODE_NEAREST_UP                                        (4u)
/*! Round away from zero             */
#define ADI_IIR_RNDG_MODE_AWAY_FROM_ZERO                                    (5u)

#endif /* defined(__ADSPSC589_FAMILY__) || defined(__ADSPSC573_FAMILY__) */

/*! This Macro allows to set the Output Rounding Mode for the Tasks created.\n
    This macro only has effect in Legacy mode.\n
	In Auto Configuration Mode, the Output Rounding Mode can be set as part of ADI_IIR_CHANNEL_INFO.\n
    It can be configured to one of the following macros:
    - #ADI_IIR_RNDG_MODE_NEAREST_EVEN
    - #ADI_IIR_RNDG_MODE_TO_ZERO
 */
#define ADI_IIR_CFG_ROUNDING_MODE    (ADI_IIR_RNDG_MODE_NEAREST_EVEN)

/*! This macro allows to selects between 32-bit IEEE floating-point format or
    40-bit IEEE floating-point format .\n
    This macro only has effect in Legacy mode.\n
	In Auto Configuration Mode, the Forty Bit Enable/disable can be set as part of ADI_IIR_CHANNEL_INFO.\n
    It can be configured to one of the following macros:
    (1) - 40-bit IEEE floating-point\n
    (0) - 32-bit IEEE floating-point
 */
#define ADI_IIR_CFG_FORTYBIT_FLOATING_POINT_SELECT    (0u)

/*! This macro allows to enable/disables Biquad Save State feature for all the IIR Tasks created.\n
    This macro only has effect in Legacy mode.\n
	Auto Configuration Mode, the Save State Enable/disable can be set as part of ADI_IIR_CHANNEL_INFO.\n
    It can be configured to one of the following macros:
    (1) -  Enable Save Biquad State Feature\n
    (0) -  Disable Save Biquad State Feature
 */
#define ADI_IIR_CFG_SAVE_BIQUAD_STATE    (1u)

/*! @cond PRIVATE */
#endif /* ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_LEGACY */
/*! @endcond */

/*! This macro configures the Mode of the Driver as Single Core or Dual Core Mode.\n
    For ADSP-21569 processors, Dual Core Mode is not supported.\n
    The possible values it can be configured to are:
    - 1 : Dual Core mode support.
    - 0 : Single Core Mode support.
*/
#define ADI_IIR_CFG_DUAL_CORE_MODE_SUPPORT      (0)

/*! @cond PRIVATE */
#if ADI_IIR_CFG_DUAL_CORE_MODE_SUPPORT == 1
/*! @endcond */

/*! This macro Configures the Core as Master/Slave Core in Dual Core Environment.\n 
    This macro only has effect when ADI_IIR_CFG_DUAL_CORE_MODE_SUPPORT is set to 1.\n
	For ADSP-21569 processors, Dual Core Mode is not supported and this macro has no effect.\n
    The possible values it can be configured to are:
    - 1 : Configure the Core as Master Core.
    - 0 : Configure the Core as Slave Core.
	
*/
#define ADI_IIR_CFG_MASTER_CORE      (0)


/*! This macro Configures the Software Interrupt which goes to the Slave Core when the driver is operated in Dual Core Mode.\n
    This macro only has effect when ADI_IIR_CFG_DUAL_CORE_MODE_SUPPORT is set to 1.\n
	For ADSP-21569 processors, Dual Core Mode is not supported and this macro has no effect.\n
    The possible values it can be configured to are:

    - INTR_SYS_SOFT0_INT : Configures Software Interrupt 0.
    - INTR_SYS_SOFT1_INT : Configures Software Interrupt 1.
    - INTR_SYS_SOFT2_INT : Configures Software Interrupt 2.
    - INTR_SYS_SOFT3_INT : Configures Software Interrupt 3.
    - INTR_SYS_SOFT4_INT : Configures Software Interrupt 4.
    - INTR_SYS_SOFT5_INT : Configures Software Interrupt 5.
    - INTR_SYS_SOFT6_INT : Configures Software Interrupt 6.
    - INTR_SYS_SOFT7_INT : Configures Software Interrupt 7.
*/
#define ADI_IIR_CFG_SLAVE_SOFT_INTERRUPT      (INTR_SYS_SOFT1_INT)

/*! @cond PRIVATE */
#endif /* ADI_IIR_CFG_DUAL_CORE_MODE_SUPPORT == 1 */
/*! @endcond */

/*
** Verify the macro configuration
*/

#if (defined(__ADSPSC589_FAMILY__) || defined(__ADSPSC573_FAMILY__) || defined(__ADSP21569_FAMILY__))

#if defined(__ADSP21569_FAMILY__)
#if ((ADI_IIR_CFG_ACCELERATOR_MODE != ADI_IIR_ACCELERATOR_MODE_LEGACY) && \
     (ADI_IIR_CFG_ACCELERATOR_MODE != ADI_IIR_ACCELERATOR_MODE_ACM))
#error "ADI_IIR_CFG_ACCELERATOR_MODE macro is wrongly configured"
#endif /* ADI_IIR_CFG_ACCELERATOR_MODE verification */
#elif defined(__ADSPSC573_FAMILY__) || defined(__ADSPSC589_FAMILY__)
#if ((ADI_IIR_CFG_ACCELERATOR_MODE != ADI_IIR_ACCELERATOR_MODE_LEGACY))
#error "ADI_IIR_CFG_ACCELERATOR_MODE macro is wrongly configured."
#endif /* ADI_IIR_CFG_ACCELERATOR_MODE verification */
#endif /* defined(__ADSP21569_FAMILY__) */

#if  ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_LEGACY

#if defined(__ADSPSC573_FAMILY__) || defined(__ADSPSC589_FAMILY__)
#if ((ADI_IIR_CFG_ROUNDING_MODE != ADI_IIR_RNDG_MODE_NEAREST_EVEN)       && \
     (ADI_IIR_CFG_ROUNDING_MODE != ADI_IIR_RNDG_MODE_TO_ZERO)            && \
     (ADI_IIR_CFG_ROUNDING_MODE != ADI_IIR_RNDG_MODE_POS_INF)            && \
     (ADI_IIR_CFG_ROUNDING_MODE != ADI_IIR_RNDG_MODE_NEG_INF)            && \
     (ADI_IIR_CFG_ROUNDING_MODE != ADI_IIR_RNDG_MODE_NEAREST_UP)         && \
	 (ADI_IIR_CFG_ROUNDING_MODE != ADI_IIR_RNDG_MODE_AWAY_FROM_ZERO))
#error "ADI_IIR_CFG_ROUNDING_MODE macro wrongly configured"
#endif /* ADI_IIR_CFG_ROUNDING_MODE verification */
#elif defined(__ADSP21569_FAMILY__)
#if ((ADI_IIR_CFG_ROUNDING_MODE != ADI_IIR_RNDG_MODE_NEAREST_EVEN)       && \
	 (ADI_IIR_CFG_ROUNDING_MODE != ADI_IIR_RNDG_MODE_TO_ZERO))
#error "ADI_IIR_CFG_ROUNDING_MODE macro wrongly configured"
#endif /* ADI_IIR_CFG_ROUNDING_MODE verification */
#endif /* defined(__ADSPSC573_FAMILY__) || defined(__ADSPSC589_FAMILY__) */

#if ((ADI_IIR_CFG_FORTYBIT_FLOATING_POINT_SELECT != 0u)       && \
     (ADI_IIR_CFG_FORTYBIT_FLOATING_POINT_SELECT != 1u))
#error "ADI_IIR_CFG_FORTYBIT_FLOATING_POINT_SELECT macro wrongly configured"
#endif /* ADI_IIR_CFG_FORTYBIT_FLOATING_POINT_SELECT verification */

#if ((ADI_IIR_CFG_SAVE_BIQUAD_STATE != 0u)       && \
     (ADI_IIR_CFG_SAVE_BIQUAD_STATE != 1u))
#error "ADI_IIR_CFG_SAVE_BIQUAD_STATE macro wrongly configured"
#endif /* ADI_IIR_CFG_SAVE_BIQUAD_STATE verification */

#endif /* ADI_IIR_CFG_ACCELERATOR_MODE == ADI_IIR_ACCELERATOR_MODE_LEGACY */

#if defined(__ADSP21569_FAMILY__)
#if ((ADI_IIR_CFG_DUAL_CORE_MODE_SUPPORT != 0))
#error "ADI_IIR_CFG_DUAL_CORE_MODE_SUPPORT macro is wrongly configured"
#endif /* ADI_IIR_CFG_DUAL_CORE_MODE_SUPPORT verification */
#elif defined(__ADSPSC573_FAMILY__) || defined(__ADSPSC589_FAMILY__)
#if ((ADI_IIR_CFG_DUAL_CORE_MODE_SUPPORT != 0) && \
     (ADI_IIR_CFG_DUAL_CORE_MODE_SUPPORT != 1))
#error "ADI_IIR_CFG_DUAL_CORE_MODE_SUPPORT macro is wrongly configured"
#endif /* ADI_IIR_CFG_DUAL_CORE_MODE_SUPPORT verification */
#endif /* defined(__ADSP21569_FAMILY__) */

#if ADI_IIR_CFG_DUAL_CORE_MODE_SUPPORT == 1
#if ((ADI_IIR_CFG_MASTER_CORE != 0) && \
     (ADI_IIR_CFG_MASTER_CORE != 1))
#error "ADI_IIR_CFG_MASTER_CORE macro is wrongly configured"
#endif /* ADI_IIR_CFG_MASTER_CORE verification */
#endif /* ADI_IIR_CFG_DUAL_CORE_MODE_SUPPORT == 1 */

#else

#error "Processor not Supported"

#endif /* (defined(__ADSPSC589_FAMILY__) || defined(__ADSPSC573_FAMILY__) || defined(__ADSP21569_FAMILY__)) */

#ifdef _MISRA_RULES
#pragma diag(pop)
#endif

#endif /* ADI_IIR_CONFIG_2156X_H */

/*@}*/

/*@}*/
