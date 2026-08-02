/************************************************************************
 *
 * sru21569.h : version 2.9.0.2
 *
 * (c) Copyright 2017-2018 Analog Devices, Inc.  All rights reserved.
 *
 ************************************************************************/

#ifndef _SRU21569_H
#define _SRU21569_H

#if defined(_ADI_COMPILER)
#pragma system_header
#endif

#if defined(_MISRA_2004_RULES) || defined(_MISRA_2012_RULES)
#pragma diag(push)
#ifdef _MISRA_2012_RULES
#pragma diag(suppress:misra2012_rule_20_7)
#pragma diag(suppress:misra2012_rule_20_10)
#pragma diag(suppress:misra2012_rule_20_11)
#else
#pragma diag(suppress:misra_rule_19_4)
#pragma diag(suppress:misra_rule_19_7:"ADI header allows function-like macros")
#pragma diag(suppress:misra_rule_19_10)
#pragma diag(suppress:misra_rule_19_12:"ADI header allows multiple instances of the # or ## operators")
#pragma diag(suppress:misra_rule_19_13:"ADI header will use the # and ## preprocessor operators")
#endif /* _MISRA_2004_RULES */
#endif /* _MISRA_RULES */

/*
** Add an SRUDEBUG macro define to 1 to the preprocessor definitions in
** project options or source file for the Assembler/Compiler to allow the SRU
** macro to check its inputs for validity. Without this check, it is possible
** to have an errorless/warningless build that does not have valid signals
** routed according to the groupings in the ADSP-2156x Hardware Reference, caused
** by invalid user input. Enabling error checking increases the memory used
** by the macro. Once the routings are verified, it is no longer necessary
** to enable the error checking mechanism.
*/

#if !defined(SRUDEBUG)
# define SRUDEBUG 0
#endif

/* We need the following header file for the SRU register address definitions */
#include <sys/platform.h>

/*
** Macro: SRU
** Reads, modifies and writes back a particular SRU register to change a single
** SRU assignment (i.e. selects an input to an output).
*/
#if !SRUDEBUG
# if defined (_LANGUAGE_C)
#  define SRU(out,in)                        \
     do {                                    \
       *(volatile unsigned int *) in##_REG = \
         ((unsigned int)sru_field(out,in) |  \
         (* (volatile unsigned int *) in##_REG & (unsigned int)sru_mask(out,in))); \
     } while (0)
  
#  define SRU2(out,in)                       \
     do {                                    \
       *(volatile unsigned int *) in##_REG = \
         ((unsigned int)sru2_field(out,in) | \
         (* (volatile unsigned int *) in##_REG & (unsigned int)sru2_mask(out,in))); \
     } while (0)     
     
# else
#   define SRU(out,in)        \
      r0=dm(in##_REG);        \
      r1=sru_mask(out,in);    \
      r0=r0 and r1;           \
      r1=sru_field(out,in);   \
      r0=r0 or r1;            \
      dm(in##_REG)=r0;

#   define SRU2(out,in)       \
      r0=dm(in##_REG);        \
      r1=sru2_mask(out,in);   \
      r0=r0 and r1;           \
      r1=sru2_field(out,in);  \
      r0=r0 or r1;            \
      dm(in##_REG)=r0;
# endif
#else /* SRUDEBUG */
/*
** Macro: SRU with error checking
** Checks for incompatible input and output selections. Valid routings will
** read, modify and write back a particular SRU register to change a single
** SRU assignment (i.e. selects an input to an output).
** Invalid routings will hang infinitely with the PC pointing to the offending
** routing code.
** The compiler will generate warnings for unreachable code when the routing
** is invalid.
*/
# if defined (_LANGUAGE_C)
#  define SRU(out,in)                         \
     do {                                     \
       SRU_ERROR_CHECK(out,in)                \
       * (volatile unsigned int *) in##_REG = \
           ((unsigned int)sru_field(out,in) | \
            (* (volatile unsigned int *) in##_REG & (unsigned int)sru_mask(out,in))); \
     } while (0)
#  define SRU_ERROR_CHECK(out,in) if(!sru_check(out,in)) { while(1){} }

#  define SRU2(out,in)                        \
     do {                                     \
       SRU2_ERROR_CHECK(out,in)               \
       * (volatile unsigned int *) in##_REG = \
           ((unsigned int)sru2_field(out,in) | \
            (* (volatile unsigned int *) in##_REG & (unsigned int)sru2_mask(out,in))); \
     } while (0)
#  define SRU2_ERROR_CHECK(out,in) if(!sru2_check(out,in)) while(1);

# else
#   define SRU(out,in)        \
      SRU_ERROR_CHECK(out,in) \
      r0=dm(in##_REG);        \
      r1=sru_mask(out,in);    \
      r0=r0 and r1;           \
      r1=sru_field(out,in);   \
      r0=r0 or r1;            \
      dm(in##_REG)=r0;
#   define SRU_ERROR_CHECK(out,in) \
      r1 = sru_check(out,in);      \
      r1 = pass r1;                \
      if ne jump(pc,LEGAL_ROUTING?); \
      ILLEGAL_ROUTING_DETECTED?:   \
      jump(pc,0);                  \
      LEGAL_ROUTING?:
     
#   define SRU2(out,in)        \
      SRU2_ERROR_CHECK(out,in) \
      r0=dm(in##_REG);        \
      r1=sru2_mask(out,in);    \
      r0=r0 and r1;           \
      r1=sru2_field(out,in);   \
      r0=r0 or r1;            \
      dm(in##_REG)=r0;
#   define SRU2_ERROR_CHECK(out,in) \
      r1 = sru2_check(out,in);      \
      r1 = pass r1;                \
      if ne jump(pc,LEGAL_ROUTING?); \
      ILLEGAL_ROUTING_DETECTED?:   \
      jump(pc,0);                  \
      LEGAL_ROUTING?:     
# endif
#endif /* SRUDEBUG */


/*
**   Macro: sru_field
**   Creates the bit field for a given input and output signal.
*/

#define sru_field(out,in) \
    (((in##_GROUP & GROUP_A) >> LOG_GROUP_A) * A_##out \
    |((in##_GROUP & GROUP_B) >> LOG_GROUP_B) * B_##out \
    |((in##_GROUP & GROUP_C) >> LOG_GROUP_C) * C_##out \
    |((in##_GROUP & GROUP_D) >> LOG_GROUP_D) * D_##out \
    |((in##_GROUP & GROUP_E) >> LOG_GROUP_E) * E_##out \
    |((in##_GROUP & GROUP_F) >> LOG_GROUP_F) * F_##out \
    |((in##_GROUP & GROUP_G) >> LOG_GROUP_G) * G_##out )  << in##_SHIFT
    
#define sru2_field(out,in) \
    (((in##_GROUP & GROUP_A2) >> LOG_GROUP_A2) * A2_##out \
    |((in##_GROUP & GROUP_B2) >> LOG_GROUP_B2) * B2_##out \
    |((in##_GROUP & GROUP_C2) >> LOG_GROUP_C2) * C2_##out \
    |((in##_GROUP & GROUP_D2) >> LOG_GROUP_D2) * D2_##out \
    |((in##_GROUP & GROUP_E2) >> LOG_GROUP_E2) * E2_##out \
    |((in##_GROUP & GROUP_F2) >> LOG_GROUP_F2) * F2_##out \
    |((in##_GROUP & GROUP_G2) >> LOG_GROUP_G2) * G2_##out )  << in##_SHIFT    

/*
**   Macro: sru_mask
**   Creates a mask which can be used for clearing the bitfield belonging
**   to the given input and output signal.
*/
#define sru_mask(out,in) \
     ~((((in##_GROUP & GROUP_A) >> LOG_GROUP_A) * MASK_A \
       |((in##_GROUP & GROUP_B) >> LOG_GROUP_B) * MASK_B \
       |((in##_GROUP & GROUP_C) >> LOG_GROUP_C) * MASK_C \
       |((in##_GROUP & GROUP_D) >> LOG_GROUP_D) * MASK_D \
       |((in##_GROUP & GROUP_E) >> LOG_GROUP_E) * MASK_E \
       |((in##_GROUP & GROUP_F) >> LOG_GROUP_F) * MASK_F \
       |((in##_GROUP & GROUP_G) >> LOG_GROUP_G) * MASK_G) << in##_SHIFT)

#define sru2_mask(out,in) \
     ~((((in##_GROUP & GROUP_A2) >> LOG_GROUP_A2) * MASK_A2 \
       |((in##_GROUP & GROUP_B2) >> LOG_GROUP_B2) * MASK_B2 \
       |((in##_GROUP & GROUP_C2) >> LOG_GROUP_C2) * MASK_C2 \
       |((in##_GROUP & GROUP_D2) >> LOG_GROUP_D2) * MASK_D2 \
       |((in##_GROUP & GROUP_E2) >> LOG_GROUP_E2) * MASK_E2 \
       |((in##_GROUP & GROUP_F2) >> LOG_GROUP_F2) * MASK_F2 \
       |((in##_GROUP & GROUP_G2) >> LOG_GROUP_G2) * MASK_G2) << in##_SHIFT)
       

/*
**   Macro: sru_check
**   Creates the bit field for a given input and output signal to test for
**   errors. Returns 0 if the routing is invalid
*/
#define sru_check(out,in) \
    (((((in##_GROUP & GROUP_A) >> LOG_GROUP_A)*0xFF) & (~A_##out)) \
    |((((in##_GROUP & GROUP_B) >> LOG_GROUP_B)*0xFF) & (~B_##out)) \
    |((((in##_GROUP & GROUP_C) >> LOG_GROUP_C)*0xFF) & (~C_##out)) \
    |((((in##_GROUP & GROUP_D) >> LOG_GROUP_D)*0xFF) & (~D_##out)) \
    |((((in##_GROUP & GROUP_E) >> LOG_GROUP_E)*0xFF) & (~E_##out)) \
    |((((in##_GROUP & GROUP_F) >> LOG_GROUP_F)*0xFF) & (~F_##out)) \
    |((((in##_GROUP & GROUP_G) >> LOG_GROUP_G)*0xFF) & (~G_##out)) )
    
#define sru2_check(out,in) \
    (((((in##_GROUP & GROUP_A2)>> LOG_GROUP_A2)*0xFF) & (~A2_##out)) \
    |((((in##_GROUP & GROUP_B2)>> LOG_GROUP_B2)*0xFF) & (~B2_##out)) \
    |((((in##_GROUP & GROUP_C2)>> LOG_GROUP_C2)*0xFF) & (~C2_##out)) \
    |((((in##_GROUP & GROUP_D2)>> LOG_GROUP_D2)*0xFF) & (~D2_##out)) \
    |((((in##_GROUP & GROUP_E2)>> LOG_GROUP_E2)*0xFF) & (~E2_##out)) \
    |((((in##_GROUP & GROUP_F2)>> LOG_GROUP_F2)*0xFF) & (~F2_##out)) \
    |((((in##_GROUP & GROUP_G2)>> LOG_GROUP_G2)*0xFF) & (~G2_##out)) )

/*  Logarithm of Group ID Numbers */
#define LOG_GROUP_A     0
#define LOG_GROUP_B     1
#define LOG_GROUP_C     2
#define LOG_GROUP_D     3
#define LOG_GROUP_E     4
#define LOG_GROUP_F     5
#define LOG_GROUP_G     6
#define LOG_GROUP_A2    7
#define LOG_GROUP_B2    8
#define LOG_GROUP_C2    9
#define LOG_GROUP_D2    10
#define LOG_GROUP_E2    11
#define LOG_GROUP_F2    12
#define LOG_GROUP_G2    13

/*  Group ID numbers */
#define GROUP_A         (0x01 << LOG_GROUP_A)
#define GROUP_B         (0x01 << LOG_GROUP_B)
#define GROUP_C         (0x01 << LOG_GROUP_C)
#define GROUP_D         (0x01 << LOG_GROUP_D)
#define GROUP_E         (0x01 << LOG_GROUP_E)
#define GROUP_F         (0x01 << LOG_GROUP_F)
#define GROUP_G         (0x01 << LOG_GROUP_G)
#define GROUP_A2        (0x01 << LOG_GROUP_A2)
#define GROUP_B2        (0x01 << LOG_GROUP_B2)
#define GROUP_C2        (0x01 << LOG_GROUP_C2)
#define GROUP_D2        (0x01 << LOG_GROUP_D2)
#define GROUP_E2        (0x01 << LOG_GROUP_E2)
#define GROUP_F2        (0x01 << LOG_GROUP_F2)
#define GROUP_G2        (0x01 << LOG_GROUP_G2)

/*  Group Base Masks
**  The actual field masks can be computed by shifting them to the proper
**  location
*/
#define MASK_A          0x1f
#define MASK_B          0x3f
#define MASK_C          0x1f
#define MASK_D          0x7f
#define MASK_E          0x1f
#define MASK_F          0x3f
#define MASK_G          0x01
#define MASK_A2         0x1f
#define MASK_B2         0x3f
#define MASK_C2         0x1f
#define MASK_D2         0x7f
#define MASK_E2         0x1f
#define MASK_F2         0x3f
#define MASK_G2         0x01

/*============================================================================*/
/*   Group A - Serial Clock Signals                                           */
/* ===========================================================================*/

/* -------------------------------------------- */
/*   Group ID Assignments */
/* -------------------------------------------- */

/* DAI0 */

/* DAI0_CLK0 */
#define SPT0_ACLK_I_GROUP          GROUP_A
#define SPT0_BCLK_I_GROUP          GROUP_A
#define SPT1_ACLK_I_GROUP          GROUP_A
#define SPT1_BCLK_I_GROUP          GROUP_A
#define SPT2_ACLK_I_GROUP          GROUP_A
#define SPT2_BCLK_I_GROUP          GROUP_A

/* DAI0_CLK1 */
#define SRC0_CLK_IP_I_GROUP        GROUP_A
#define SRC0_CLK_OP_I_GROUP        GROUP_A
#define SRC1_CLK_IP_I_GROUP        GROUP_A
#define SRC1_CLK_OP_I_GROUP        GROUP_A
#define SRC2_CLK_IP_I_GROUP        GROUP_A
#define SRC2_CLK_OP_I_GROUP        GROUP_A

/* DAI0_CLK2 */
#define SRC3_CLK_IP_I_GROUP        GROUP_A
#define SRC3_CLK_OP_I_GROUP        GROUP_A
#define SPDIF0_TX_CLK_I_GROUP      GROUP_A

/* DAI0_CLK3 */
#define SPDIF0_TX_HFCLK_I_GROUP    GROUP_A

/* DAI0_CLK4 */
#define PCG0_EXTCLKA_I_GROUP       GROUP_A
#define PCG0_EXTCLKB_I_GROUP       GROUP_A
#define SPDIF0_TX_EXT_SYNC_I_GROUP GROUP_A
#define PCG0_SYNC_CLKA_I_GROUP     GROUP_A
#define PCG0_SYNC_CLKB_I_GROUP     GROUP_A

/* DAI0_CLK5 */
#define SPT3_ACLK_I_GROUP          GROUP_A
#define SPT3_BCLK_I_GROUP          GROUP_A

/* DAI1 */

/* DAI1_CLK0 */
#define SPT4_ACLK_I_GROUP          GROUP_A2
#define SPT4_BCLK_I_GROUP          GROUP_A2
#define SPT5_ACLK_I_GROUP          GROUP_A2
#define SPT5_BCLK_I_GROUP          GROUP_A2
#define SPT6_ACLK_I_GROUP          GROUP_A2
#define SPT6_BCLK_I_GROUP          GROUP_A2

/* DAI1_CLK1 */
#define SRC4_CLK_IP_I_GROUP        GROUP_A2
#define SRC4_CLK_OP_I_GROUP        GROUP_A2
#define SRC5_CLK_IP_I_GROUP        GROUP_A2
#define SRC5_CLK_OP_I_GROUP        GROUP_A2
#define SRC6_CLK_IP_I_GROUP        GROUP_A2
#define SRC6_CLK_OP_I_GROUP        GROUP_A2

/* DAI1_CLK2 */
#define SRC7_CLK_IP_I_GROUP        GROUP_A2
#define SRC7_CLK_OP_I_GROUP        GROUP_A2
#define SPDIF1_TX_CLK_I_GROUP      GROUP_A2

/* DAI1_CLK3 */
#define SPDIF1_TX_HFCLK_I_GROUP    GROUP_A2

/* DAI1_CLK4 */
#define PCG0_EXTCLKC_I_GROUP       GROUP_A2
#define PCG0_EXTCLKD_I_GROUP       GROUP_A2
#define SPDIF1_TX_EXT_SYNC_I_GROUP GROUP_A2
#define PCG0_SYNC_CLKC_I_GROUP     GROUP_A2
#define PCG0_SYNC_CLKD_I_GROUP     GROUP_A2

/* DAI1_CLK5 */
#define SPT7_ACLK_I_GROUP          GROUP_A2
#define SPT7_BCLK_I_GROUP          GROUP_A2

/* -------------------------------------------- */
/*   Register Assignments */
/* -------------------------------------------- */

/* DAI0 */

#define SPT0_ACLK_I_REG          REG_DAI0_CLK0
#define SPT0_BCLK_I_REG          REG_DAI0_CLK0
#define SPT1_ACLK_I_REG          REG_DAI0_CLK0
#define SPT1_BCLK_I_REG          REG_DAI0_CLK0
#define SPT2_ACLK_I_REG          REG_DAI0_CLK0
#define SPT2_BCLK_I_REG          REG_DAI0_CLK0

#define SRC0_CLK_IP_I_REG        REG_DAI0_CLK1
#define SRC0_CLK_OP_I_REG        REG_DAI0_CLK1
#define SRC1_CLK_IP_I_REG        REG_DAI0_CLK1
#define SRC1_CLK_OP_I_REG        REG_DAI0_CLK1
#define SRC2_CLK_IP_I_REG        REG_DAI0_CLK1
#define SRC2_CLK_OP_I_REG        REG_DAI0_CLK1

#define SRC3_CLK_IP_I_REG        REG_DAI0_CLK2
#define SRC3_CLK_OP_I_REG        REG_DAI0_CLK2
#define SPDIF0_TX_CLK_I_REG      REG_DAI0_CLK2

#define SPDIF0_TX_HFCLK_I_REG    REG_DAI0_CLK3

#define PCG0_EXTCLKA_I_REG       REG_DAI0_CLK4
#define PCG0_EXTCLKB_I_REG       REG_DAI0_CLK4
#define SPDIF0_TX_EXT_SYNC_I_REG REG_DAI0_CLK4
#define PCG0_SYNC_CLKA_I_REG     REG_DAI0_CLK4
#define PCG0_SYNC_CLKB_I_REG     REG_DAI0_CLK4

#define SPT3_ACLK_I_REG          REG_DAI0_CLK5
#define SPT3_BCLK_I_REG          REG_DAI0_CLK5

/* DAI1 */

#define SPT4_ACLK_I_REG          REG_DAI1_CLK0
#define SPT4_BCLK_I_REG          REG_DAI1_CLK0
#define SPT5_ACLK_I_REG          REG_DAI1_CLK0
#define SPT5_BCLK_I_REG          REG_DAI1_CLK0
#define SPT6_ACLK_I_REG          REG_DAI1_CLK0
#define SPT6_BCLK_I_REG          REG_DAI1_CLK0
                                          
#define SRC4_CLK_IP_I_REG        REG_DAI1_CLK1 
#define SRC4_CLK_OP_I_REG        REG_DAI1_CLK1 
#define SRC5_CLK_IP_I_REG        REG_DAI1_CLK1 
#define SRC5_CLK_OP_I_REG        REG_DAI1_CLK1 
#define SRC6_CLK_IP_I_REG        REG_DAI1_CLK1 
#define SRC6_CLK_OP_I_REG        REG_DAI1_CLK1 
                                           
#define SRC7_CLK_IP_I_REG        REG_DAI1_CLK2 
#define SRC7_CLK_OP_I_REG        REG_DAI1_CLK2 
#define SPDIF1_TX_CLK_I_REG      REG_DAI1_CLK2 
                                          
#define SPDIF1_TX_HFCLK_I_REG    REG_DAI1_CLK3 
                                          
#define PCG0_EXTCLKC_I_REG       REG_DAI1_CLK4
#define PCG0_EXTCLKD_I_REG       REG_DAI1_CLK4
#define SPDIF1_TX_EXT_SYNC_I_REG REG_DAI1_CLK4 
#define PCG0_SYNC_CLKC_I_REG     REG_DAI1_CLK4
#define PCG0_SYNC_CLKD_I_REG     REG_DAI1_CLK4

#define SPT7_ACLK_I_REG          REG_DAI1_CLK5 
#define SPT7_BCLK_I_REG          REG_DAI1_CLK5 

/* -------------------------------------------- */
/*   Shift Values for Bit Fields */
/* -------------------------------------------- */

/* DAI0 */
                        
/*  DAI0_CLK0 */         
#define SPT0_ACLK_I_SHIFT          0
#define SPT0_BCLK_I_SHIFT          5
#define SPT1_ACLK_I_SHIFT          10
#define SPT1_BCLK_I_SHIFT          15
#define SPT2_ACLK_I_SHIFT          20
#define SPT2_BCLK_I_SHIFT          25
                        
/* DAI0_CLK1 */          
#define SRC0_CLK_IP_I_SHIFT        0
#define SRC0_CLK_OP_I_SHIFT        5
#define SRC1_CLK_IP_I_SHIFT        10
#define SRC1_CLK_OP_I_SHIFT        15
#define SRC2_CLK_IP_I_SHIFT        20
#define SRC2_CLK_OP_I_SHIFT        25
                        
/* DAI0_CLK2 */          
#define SRC3_CLK_IP_I_SHIFT        0
#define SRC3_CLK_OP_I_SHIFT        5
#define SPDIF0_TX_CLK_I_SHIFT      10
                        
/*  DAI0_CLK3 */         
#define SPDIF0_TX_HFCLK_I_SHIFT    25

/*  DAI0_CLK4 */
#define PCG0_EXTCLKA_I_SHIFT       0
#define PCG0_EXTCLKB_I_SHIFT       5
#define SPDIF0_TX_EXT_SYNC_I_SHIFT 15
#define PCG0_SYNC_CLKA_I_SHIFT     20
#define PCG0_SYNC_CLKB_I_SHIFT     25

/*  DAI0_CLK5 */
#define SPT3_ACLK_I_SHIFT          0
#define SPT3_BCLK_I_SHIFT          5

/* DAI1 */

/*  DAI1_CLK0 */         
#define SPT4_ACLK_I_SHIFT          0
#define SPT4_BCLK_I_SHIFT          5
#define SPT5_ACLK_I_SHIFT          10
#define SPT5_BCLK_I_SHIFT          15
#define SPT6_ACLK_I_SHIFT          20
#define SPT6_BCLK_I_SHIFT          25
                        
/* DAI1_CLK1 */          
#define SRC4_CLK_IP_I_SHIFT        0
#define SRC4_CLK_OP_I_SHIFT        5
#define SRC5_CLK_IP_I_SHIFT        10
#define SRC5_CLK_OP_I_SHIFT        15
#define SRC6_CLK_IP_I_SHIFT        20
#define SRC6_CLK_OP_I_SHIFT        25
                        
/* DAI1_CLK2 */          
#define SRC7_CLK_IP_I_SHIFT        0
#define SRC7_CLK_OP_I_SHIFT        5
#define SPDIF1_TX_CLK_I_SHIFT      10
                        
/*  DAI1_CLK3 */         
#define SPDIF1_TX_HFCLK_I_SHIFT    25

/*  DAI1_CLK4 */
#define PCG0_EXTCLKC_I_SHIFT       0
#define PCG0_EXTCLKD_I_SHIFT       5
#define SPDIF1_TX_EXT_SYNC_I_SHIFT 15
#define PCG0_SYNC_CLKC_I_SHIFT     20
#define PCG0_SYNC_CLKD_I_SHIFT     25

/*  DAI1_CLK5 */
#define SPT7_ACLK_I_SHIFT          0
#define SPT7_BCLK_I_SHIFT          5

/* -------------------------------------------- */
/*   Bit Field Codes */
/* -------------------------------------------- */

/* DAI0 */

#define A_DAI0_PB01_O            0x00
#define A_DAI0_PB02_O            0x01
#define A_DAI0_PB03_O            0x02
#define A_DAI0_PB04_O            0x03
#define A_DAI0_PB05_O            0x04
#define A_DAI0_PB06_O            0x05
#define A_DAI0_PB07_O            0x06
#define A_DAI0_PB08_O            0x07
#define A_DAI0_PB09_O            0x08
#define A_DAI0_PB10_O            0x09
#define A_DAI0_PB11_O            0x0a
#define A_DAI0_PB12_O            0x0b
#define A_DAI0_PB13_O            0x0c
#define A_DAI0_PB14_O            0x0d
#define A_DAI0_CRS_PB03_O        0x0e
#define A_DAI0_CRS_PB05_O        0x0f
#define A_DAI0_PB17_O            0x10
#define A_DAI0_PB18_O            0x11
#define A_DAI0_PB19_O            0x12
#define A_DAI0_PB20_O            0x13
#define A_SPT0_ACLK_O            0x14
#define A_SPT0_BCLK_O            0x15
#define A_SPT1_ACLK_O            0x16
#define A_SPT1_BCLK_O            0x17
#define A_SPT2_ACLK_O            0x18
#define A_SPT2_BCLK_O            0x19
#define A_SPDIF0_RX_CLK_O        0x1a
#define A_SPDIF0_RX_TDMCLK_O     0x1b
#define A_PCG0_CLKA_O            0x1c
#define A_PCG0_CLKB_O            0x1d
#define A_LOW                    0x1e
#define A_HIGH                   0x1f

/* DAI1 */
#define A2_DAI1_PB01_O           0x00
#define A2_DAI1_PB02_O           0x01   
#define A2_DAI1_PB03_O           0x02   
#define A2_DAI1_PB04_O           0x03   
#define A2_DAI1_PB05_O           0x04   
#define A2_DAI1_PB06_O           0x05   
#define A2_DAI1_PB07_O           0x06   
#define A2_DAI1_PB08_O           0x07   
#define A2_DAI1_PB09_O           0x08   
#define A2_DAI1_PB10_O           0x09   
#define A2_DAI1_PB11_O           0x0a   
#define A2_DAI1_PB12_O           0x0b   
#define A2_DAI1_PB13_O           0x0c   
#define A2_DAI1_PB14_O           0x0d   
#define A2_DAI1_CRS_PB03_O       0x0e
#define A2_DAI1_CRS_PB05_O       0x0f
#define A2_DAI1_PB17_O           0x10   
#define A2_DAI1_PB18_O           0x11   
#define A2_DAI1_PB19_O           0x12   
#define A2_DAI1_PB20_O           0x13   
#define A2_SPT4_ACLK_O           0x14    
#define A2_SPT4_BCLK_O           0x15    
#define A2_SPT5_ACLK_O           0x16    
#define A2_SPT5_BCLK_O           0x17    
#define A2_SPT6_ACLK_O           0x18    
#define A2_SPT6_BCLK_O           0x19    
#define A2_SPDIF1_RX_CLK_O       0x1a    
#define A2_SPDIF1_RX_TDMCLK_O    0x1b    
#define A2_PCG0_CLKC_O           0x1c    
#define A2_PCG0_CLKD_O           0x1d    
#define A2_LOW                   0x1e    
#define A2_HIGH                  0x1f    

/*============================================================================*/
/*   Group B - Serial Data Signals                                            */
/* ===========================================================================*/

/* -------------------------------------------- */
/*   Group ID Assignments */
/* -------------------------------------------- */

/* DAI0 */

/* DAI0_DAT0 */
#define SPT0_AD0_I_GROUP        GROUP_B
#define SPT0_AD1_I_GROUP        GROUP_B 
#define SPT0_BD0_I_GROUP        GROUP_B
#define SPT0_BD1_I_GROUP        GROUP_B 
#define SPT1_AD0_I_GROUP        GROUP_B

/* DAI0_DAT1 */
#define SPT1_AD1_I_GROUP        GROUP_B
#define SPT1_BD0_I_GROUP        GROUP_B
#define SPT1_BD1_I_GROUP        GROUP_B
#define SPT2_AD0_I_GROUP        GROUP_B
#define SPT2_AD1_I_GROUP        GROUP_B

/* DAI0_DAT2 */
#define SPT2_BD0_I_GROUP        GROUP_B
#define SPT2_BD1_I_GROUP        GROUP_B
#define SRC0_DAT_IP_I_GROUP     GROUP_B
#define SRC1_DAT_IP_I_GROUP     GROUP_B
#define SRC2_DAT_IP_I_GROUP     GROUP_B

/* DAI0_DAT3 */
#define SRC3_DAT_IP_I_GROUP     GROUP_B
#define SRC0_DAT_TDM_OP_I_GROUP GROUP_B
#define SRC1_DAT_TDM_OP_I_GROUP GROUP_B
#define SRC2_DAT_TDM_OP_I_GROUP GROUP_B
#define SRC3_DAT_TDM_OP_I_GROUP GROUP_B

/* DAI0_DAT4 */
#define SPDIF0_TX_DAT_I_GROUP   GROUP_B

/* DAI0_DAT5 */
#define SPDIF0_RX_I_GROUP       GROUP_B

/* DAI0_DAT6 */
#define SPT3_AD0_I_GROUP        GROUP_B
#define SPT3_AD1_I_GROUP        GROUP_B
#define SPT3_BD0_I_GROUP        GROUP_B
#define SPT3_BD1_I_GROUP        GROUP_B

/* DAI1 */

/* DAI1_DAT0 */
#define SPT4_AD0_I_GROUP        GROUP_B2
#define SPT4_AD1_I_GROUP        GROUP_B2 
#define SPT4_BD0_I_GROUP        GROUP_B2
#define SPT4_BD1_I_GROUP        GROUP_B2 
#define SPT5_AD0_I_GROUP        GROUP_B2

/* DAI1_DAT1 */
#define SPT5_AD1_I_GROUP        GROUP_B2
#define SPT5_BD0_I_GROUP        GROUP_B2
#define SPT5_BD1_I_GROUP        GROUP_B2
#define SPT6_AD0_I_GROUP        GROUP_B2
#define SPT6_AD1_I_GROUP        GROUP_B2

/* DAI1_DAT2 */
#define SPT6_BD0_I_GROUP        GROUP_B2
#define SPT6_BD1_I_GROUP        GROUP_B2
#define SRC4_DAT_IP_I_GROUP     GROUP_B2
#define SRC5_DAT_IP_I_GROUP     GROUP_B2
#define SRC6_DAT_IP_I_GROUP     GROUP_B2
                                        
/* DAI1_DAT3 */
#define SRC7_DAT_IP_I_GROUP     GROUP_B2
#define SRC4_DAT_TDM_OP_I_GROUP GROUP_B2
#define SRC5_DAT_TDM_OP_I_GROUP GROUP_B2
#define SRC6_DAT_TDM_OP_I_GROUP GROUP_B2
#define SRC7_DAT_TDM_OP_I_GROUP GROUP_B2

/* DAI1_DAT4 */
#define SPDIF1_TX_DAT_I_GROUP   GROUP_B2

/* DAI1_DAT5 */
#define SPDIF1_RX_I_GROUP       GROUP_B2

/* DAI1_DAT6 */
#define SPT7_AD0_I_GROUP        GROUP_B2
#define SPT7_AD1_I_GROUP        GROUP_B2
#define SPT7_BD0_I_GROUP        GROUP_B2
#define SPT7_BD1_I_GROUP        GROUP_B2

/* -------------------------------------------- */
/*   Register Assignments */
/* -------------------------------------------- */

/* DAI0 */

/* DAI0_DAT0 */
#define SPT0_AD0_I_REG         REG_DAI0_DAT0
#define SPT0_AD1_I_REG         REG_DAI0_DAT0
#define SPT0_BD0_I_REG         REG_DAI0_DAT0
#define SPT0_BD1_I_REG         REG_DAI0_DAT0
#define SPT1_AD0_I_REG         REG_DAI0_DAT0

/* DAI0_DAT1 */
#define SPT1_AD1_I_REG         REG_DAI0_DAT1
#define SPT1_BD0_I_REG         REG_DAI0_DAT1
#define SPT1_BD1_I_REG         REG_DAI0_DAT1
#define SPT2_AD0_I_REG         REG_DAI0_DAT1
#define SPT2_AD1_I_REG         REG_DAI0_DAT1

/* DAI0_DAT2 */
#define SPT2_BD0_I_REG         REG_DAI0_DAT2
#define SPT2_BD1_I_REG         REG_DAI0_DAT2
#define SRC0_DAT_IP_I_REG      REG_DAI0_DAT2
#define SRC1_DAT_IP_I_REG      REG_DAI0_DAT2
#define SRC2_DAT_IP_I_REG      REG_DAI0_DAT2

/* DAI0_DAT3 */
#define SRC3_DAT_IP_I_REG      REG_DAI0_DAT3
#define SRC0_DAT_TDM_OP_I_REG  REG_DAI0_DAT3
#define SRC1_DAT_TDM_OP_I_REG  REG_DAI0_DAT3
#define SRC2_DAT_TDM_OP_I_REG  REG_DAI0_DAT3
#define SRC3_DAT_TDM_OP_I_REG  REG_DAI0_DAT3

/* DAI0_DAT4 */
#define SPDIF0_TX_DAT_I_REG    REG_DAI0_DAT4

/* DAI0_DAT5 */
#define SPDIF0_RX_I_REG        REG_DAI0_DAT5

/* DAI0_DAT6 */
#define SPT3_AD0_I_REG         REG_DAI0_DAT6
#define SPT3_AD1_I_REG         REG_DAI0_DAT6
#define SPT3_BD0_I_REG         REG_DAI0_DAT6
#define SPT3_BD1_I_REG         REG_DAI0_DAT6

/* DAI1 */

/* DAI1_DAT0 */
#define SPT4_AD0_I_REG         REG_DAI1_DAT0
#define SPT4_AD1_I_REG         REG_DAI1_DAT0
#define SPT4_BD0_I_REG         REG_DAI1_DAT0
#define SPT4_BD1_I_REG         REG_DAI1_DAT0
#define SPT5_AD0_I_REG         REG_DAI1_DAT0

/* DAI1_DAT1 */
#define SPT5_AD1_I_REG         REG_DAI1_DAT1
#define SPT5_BD0_I_REG         REG_DAI1_DAT1
#define SPT5_BD1_I_REG         REG_DAI1_DAT1
#define SPT6_AD0_I_REG         REG_DAI1_DAT1
#define SPT6_AD1_I_REG         REG_DAI1_DAT1

/* DAI1_DAT2 */
#define SPT6_BD0_I_REG         REG_DAI1_DAT2
#define SPT6_BD1_I_REG         REG_DAI1_DAT2
#define SRC4_DAT_IP_I_REG      REG_DAI1_DAT2
#define SRC5_DAT_IP_I_REG      REG_DAI1_DAT2
#define SRC6_DAT_IP_I_REG      REG_DAI1_DAT2

/* DAI1_DAT3 */
#define SRC7_DAT_IP_I_REG      REG_DAI1_DAT3
#define SRC4_DAT_TDM_OP_I_REG  REG_DAI1_DAT3
#define SRC5_DAT_TDM_OP_I_REG  REG_DAI1_DAT3
#define SRC6_DAT_TDM_OP_I_REG  REG_DAI1_DAT3
#define SRC7_DAT_TDM_OP_I_REG  REG_DAI1_DAT3

#define SRC4_DAT_OP_I_REG (SRC4_DAT_TDM_OP_I_REG)
#define SRC5_DAT_OP_I_REG (SRC5_DAT_TDM_OP_I_REG)
#define SRC6_DAT_OP_I_REG (SRC6_DAT_TDM_OP_I_REG)
#define SRC7_DAT_OP_I_REG (SRC7_DAT_TDM_OP_I_REG)

/* DAI1_DAT4 */
#define SPDIF1_TX_DAT_I_REG    REG_DAI1_DAT4

/* DAI1_DAT5 */
#define SPDIF1_RX_I_REG        REG_DAI1_DAT5

/* DAI1_DAT6 */
#define SPT7_AD0_I_REG         REG_DAI1_DAT6
#define SPT7_AD1_I_REG         REG_DAI1_DAT6
#define SPT7_BD0_I_REG         REG_DAI1_DAT6
#define SPT7_BD1_I_REG         REG_DAI1_DAT6

/* -------------------------------------------- */
/*   Shift Values for Bit Fields */
/* -------------------------------------------- */

/* DAI0  */

/*  DAI0_DAT0 */
#define SPT0_AD0_I_SHIFT        0
#define SPT0_AD1_I_SHIFT        6
#define SPT0_BD0_I_SHIFT        12
#define SPT0_BD1_I_SHIFT        18
#define SPT1_AD0_I_SHIFT        24

/*  DAI0_DAT1 */
#define SPT1_AD1_I_SHIFT        0
#define SPT1_BD0_I_SHIFT        6
#define SPT1_BD1_I_SHIFT        12
#define SPT2_AD0_I_SHIFT        18
#define SPT2_AD1_I_SHIFT        24

/*  DAI0_DAT2 */
#define SPT2_BD0_I_SHIFT        0
#define SPT2_BD1_I_SHIFT        6
#define SRC0_DAT_IP_I_SHIFT     12
#define SRC1_DAT_IP_I_SHIFT     18
#define SRC2_DAT_IP_I_SHIFT     24

/*  DAI0_DAT3 */
#define SRC3_DAT_IP_I_SHIFT     0
#define SRC0_DAT_TDM_OP_I_SHIFT 6
#define SRC1_DAT_TDM_OP_I_SHIFT 12
#define SRC2_DAT_TDM_OP_I_SHIFT 18
#define SRC3_DAT_TDM_OP_I_SHIFT 24

/*  DAI0_DAT4 */
#define SPDIF0_TX_DAT_I_SHIFT   0

/*  DAI0_DAT5 */
#define SPDIF0_RX_I_SHIFT       24

/*  DAI0_DAT6 */
#define SPT3_AD0_I_SHIFT        0
#define SPT3_AD1_I_SHIFT        6
#define SPT3_BD0_I_SHIFT        12
#define SPT3_BD1_I_SHIFT        18

/* DAI1 */

/*  DAI1_DAT0 */
#define SPT4_AD0_I_SHIFT        0
#define SPT4_AD1_I_SHIFT        6
#define SPT4_BD0_I_SHIFT        12
#define SPT4_BD1_I_SHIFT        18
#define SPT5_AD0_I_SHIFT        24

/*  DAI1_DAT1 */
#define SPT5_AD1_I_SHIFT        0
#define SPT5_BD0_I_SHIFT        6
#define SPT5_BD1_I_SHIFT        12
#define SPT6_AD0_I_SHIFT        18
#define SPT6_AD1_I_SHIFT        24

/*  DAI1_DAT2 */
#define SPT6_BD0_I_SHIFT        0
#define SPT6_BD1_I_SHIFT        6
#define SRC4_DAT_IP_I_SHIFT     12
#define SRC5_DAT_IP_I_SHIFT     18
#define SRC6_DAT_IP_I_SHIFT     24

/*  DAI1_DAT3 */
#define SRC7_DAT_IP_I_SHIFT     0
#define SRC4_DAT_TDM_OP_I_SHIFT 6
#define SRC5_DAT_TDM_OP_I_SHIFT 12
#define SRC6_DAT_TDM_OP_I_SHIFT 18
#define SRC7_DAT_TDM_OP_I_SHIFT 24

/*  DAI1_DAT4 */
#define SPDIF1_TX_DAT_I_SHIFT   0

/*  DAI1_DAT5 */
#define SPDIF1_RX_I_SHIFT       24

/*  DAI1_DAT6 */
#define SPT7_AD0_I_SHIFT        0
#define SPT7_AD1_I_SHIFT        6
#define SPT7_BD0_I_SHIFT        12
#define SPT7_BD1_I_SHIFT        18

/* -------------------------------------------- */
/*   Bit Field Codes */
/* -------------------------------------------- */

/* DAI0 */
#define B_DAI0_PB01_O          0x00
#define B_DAI0_PB02_O          0x01
#define B_DAI0_PB03_O          0x02
#define B_DAI0_PB04_O          0x03
#define B_DAI0_PB05_O          0x04
#define B_DAI0_PB06_O          0x05
#define B_DAI0_PB07_O          0x06
#define B_DAI0_PB08_O          0x07
#define B_DAI0_PB09_O          0x08
#define B_DAI0_PB10_O          0x09
#define B_DAI0_PB11_O          0x0a
#define B_DAI0_PB12_O          0x0b
#define B_DAI0_PB13_O          0x0c
#define B_DAI0_PB14_O          0x0d
#define B_DAI0_PB15_O          0x0e
#define B_DAI0_PB16_O          0x0f
#define B_DAI0_PB17_O          0x10
#define B_DAI0_PB18_O          0x11
#define B_DAI0_PB19_O          0x12
#define B_DAI0_PB20_O          0x13
#define B_SPT0_AD0_O           0x14
#define B_SPT0_AD1_O           0x15
#define B_SPT0_BD0_O           0x16
#define B_SPT0_BD1_O           0x17
#define B_SPT1_AD0_O           0x18
#define B_SPT1_AD1_O           0x19
#define B_SPT1_BD0_O           0x1a
#define B_SPT1_BD1_O           0x1b
#define B_SPT2_AD0_O           0x1c
#define B_SPT2_AD1_O           0x1d
#define B_SPT2_BD0_O           0x1e
#define B_SPT2_BD1_O           0x1f
#define B_SRC0_DAT_OP_O        0x20
#define B_SRC1_DAT_OP_O        0x21
#define B_SRC2_DAT_OP_O        0x22
#define B_SRC3_DAT_OP_O        0x23
#define B_SRC0_TDM_IP_O        0x24
#define B_SRC1_TDM_IP_O        0x25
#define B_SRC2_TDM_IP_O        0x26
#define B_SRC3_TDM_IP_O        0x27
#define B_SPDIF0_RX_DAT_O      0x28
#define B_SPT3_AD0_O           0x2c
#define B_SPT3_AD1_O           0x2d
#define B_SPT3_BD0_O           0x2e
#define B_SPT3_BD1_O           0x2f
#define B_SPDIF0_TX_O          0x30
#define B_SRC3_CRS_DAT_OP_O    0x31
#define B_SRC3_CRS_TDM_IP_O    0x32
#define B_LOW                  0x3e
#define B_HIGH                 0x3f

/* DAI1 */
#define B2_DAI1_PB01_O         0x00
#define B2_DAI1_PB02_O         0x01
#define B2_DAI1_PB03_O         0x02
#define B2_DAI1_PB04_O         0x03
#define B2_DAI1_PB05_O         0x04
#define B2_DAI1_PB06_O         0x05
#define B2_DAI1_PB07_O         0x06
#define B2_DAI1_PB08_O         0x07
#define B2_DAI1_PB09_O         0x08
#define B2_DAI1_PB10_O         0x09
#define B2_DAI1_PB11_O         0x0a
#define B2_DAI1_PB12_O         0x0b
#define B2_DAI1_PB13_O         0x0c
#define B2_DAI1_PB14_O         0x0d
#define B2_DAI1_PB15_O         0x0e
#define B2_DAI1_PB16_O         0x0f
#define B2_DAI1_PB17_O         0x10
#define B2_DAI1_PB18_O         0x11
#define B2_DAI1_PB19_O         0x12
#define B2_DAI1_PB20_O         0x13
#define B2_SPT4_AD0_O          0x14
#define B2_SPT4_AD1_O          0x15
#define B2_SPT4_BD0_O          0x16
#define B2_SPT4_BD1_O          0x17
#define B2_SPT5_AD0_O          0x18
#define B2_SPT5_AD1_O          0x19
#define B2_SPT5_BD0_O          0x1a
#define B2_SPT5_BD1_O          0x1b
#define B2_SPT6_AD0_O          0x1c
#define B2_SPT6_AD1_O          0x1d
#define B2_SPT6_BD0_O          0x1e
#define B2_SPT6_BD1_O          0x1f
#define B2_SRC4_DAT_OP_O       0x20
#define B2_SRC5_DAT_OP_O       0x21
#define B2_SRC6_DAT_OP_O       0x22
#define B2_SRC7_DAT_OP_O       0x23
#define B2_SRC4_TDM_IP_O       0x24
#define B2_SRC5_TDM_IP_O       0x25
#define B2_SRC6_TDM_IP_O       0x26
#define B2_SRC7_TDM_IP_O       0x27
#define B2_SPDIF1_RX_DAT_O     0x28
#define B2_SPT7_AD0_O          0x2c
#define B2_SPT7_AD1_O          0x2d
#define B2_SPT7_BD0_O          0x2e
#define B2_SPT7_BD1_O          0x2f
#define B2_SPDIF1_TX_O         0x30
#define B2_SRC3_CRS_DAT_OP_O   0x31
#define B2_SRC3_CRS_TDM_IP_O   0x32
#define B2_LOW                 0x3e
#define B2_HIGH                0x3f

/*============================================================================*/
/*   Group C - Fame Sync Signals                                              */
/* ===========================================================================*/

/* -------------------------------------------- */
/*   Group ID Assignments */
/* -------------------------------------------- */

/* DAI0 */

/*  DAI0_FS0 */
#define SPT0_AFS_I_GROUP       GROUP_C
#define SPT0_BFS_I_GROUP       GROUP_C
#define SPT1_AFS_I_GROUP       GROUP_C
#define SPT1_BFS_I_GROUP       GROUP_C
#define SPT2_AFS_I_GROUP       GROUP_C
#define SPT2_BFS_I_GROUP       GROUP_C

/*  DAI0_FS1 */
#define SRC0_FS_IP_I_GROUP     GROUP_C
#define SRC0_FS_OP_I_GROUP     GROUP_C
#define SRC1_FS_IP_I_GROUP     GROUP_C
#define SRC1_FS_OP_I_GROUP     GROUP_C
#define SRC2_FS_IP_I_GROUP     GROUP_C
#define SRC2_FS_OP_I_GROUP     GROUP_C

/*  DAI0_FS2 */
#define SRC3_FS_IP_I_GROUP     GROUP_C
#define SRC3_FS_OP_I_GROUP     GROUP_C
#define SPDIF0_TX_FS_I_GROUP   GROUP_C

/*  DAI0_FS3 */

/*  DAI0_FS4 */
#define SPT3_AFS_I_GROUP       GROUP_C
#define SPT3_BFS_I_GROUP       GROUP_C

/* DAI1 */

/*  DAI1_FS0 */
#define SPT4_AFS_I_GROUP       GROUP_C2
#define SPT4_BFS_I_GROUP       GROUP_C2
#define SPT5_AFS_I_GROUP       GROUP_C2
#define SPT5_BFS_I_GROUP       GROUP_C2
#define SPT6_AFS_I_GROUP       GROUP_C2
#define SPT6_BFS_I_GROUP       GROUP_C2

/*  DAI1_FS1 */
#define SRC4_FS_IP_I_GROUP     GROUP_C2
#define SRC4_FS_OP_I_GROUP     GROUP_C2
#define SRC5_FS_IP_I_GROUP     GROUP_C2
#define SRC5_FS_OP_I_GROUP     GROUP_C2
#define SRC6_FS_IP_I_GROUP     GROUP_C2
#define SRC6_FS_OP_I_GROUP     GROUP_C2

/*  DAI1_FS2 */
#define SRC7_FS_IP_I_GROUP     GROUP_C2
#define SRC7_FS_OP_I_GROUP     GROUP_C2
#define SPDIF1_TX_FS_I_GROUP   GROUP_C2

/*  DAI1_FS3 */

/*  DAI1_FS4 */
#define SPT7_AFS_I_GROUP       GROUP_C2
#define SPT7_BFS_I_GROUP       GROUP_C2

/* -------------------------------------------- */
/*   Register Assignments */
/* -------------------------------------------- */

/* DAI0 */
#define SPT0_AFS_I_REG         REG_DAI0_FS0
#define SPT0_BFS_I_REG         REG_DAI0_FS0
#define SPT1_AFS_I_REG         REG_DAI0_FS0
#define SPT1_BFS_I_REG         REG_DAI0_FS0
#define SPT2_AFS_I_REG         REG_DAI0_FS0
#define SPT2_BFS_I_REG         REG_DAI0_FS0

#define SRC0_FS_IP_I_REG       REG_DAI0_FS1
#define SRC0_FS_OP_I_REG       REG_DAI0_FS1
#define SRC1_FS_IP_I_REG       REG_DAI0_FS1
#define SRC1_FS_OP_I_REG       REG_DAI0_FS1
#define SRC2_FS_IP_I_REG       REG_DAI0_FS1
#define SRC2_FS_OP_I_REG       REG_DAI0_FS1

#define SRC3_FS_IP_I_REG       REG_DAI0_FS2
#define SRC3_FS_OP_I_REG       REG_DAI0_FS2
#define SPDIF0_TX_FS_I_REG     REG_DAI0_FS2

#define SPT3_AFS_I_REG         REG_DAI0_FS4
#define SPT3_BFS_I_REG         REG_DAI0_FS4   

/* DAI1 */
#define SPT4_AFS_I_REG         REG_DAI1_FS0
#define SPT4_BFS_I_REG         REG_DAI1_FS0
#define SPT5_AFS_I_REG         REG_DAI1_FS0
#define SPT5_BFS_I_REG         REG_DAI1_FS0
#define SPT6_AFS_I_REG         REG_DAI1_FS0
#define SPT6_BFS_I_REG         REG_DAI1_FS0

#define SRC4_FS_IP_I_REG       REG_DAI1_FS1
#define SRC4_FS_OP_I_REG       REG_DAI1_FS1
#define SRC5_FS_IP_I_REG       REG_DAI1_FS1
#define SRC5_FS_OP_I_REG       REG_DAI1_FS1
#define SRC6_FS_IP_I_REG       REG_DAI1_FS1
#define SRC6_FS_OP_I_REG       REG_DAI1_FS1

#define SRC7_FS_IP_I_REG       REG_DAI1_FS2
#define SRC7_FS_OP_I_REG       REG_DAI1_FS2
#define SPDIF1_TX_FS_I_REG     REG_DAI1_FS2

#define SPT7_AFS_I_REG         REG_DAI1_FS4
#define SPT7_BFS_I_REG         REG_DAI1_FS4

/* -------------------------------------------- */
/*   Shift Values for Bit Fields */
/* -------------------------------------------- */

/* DAI0 */

/*  DAI0_FS0 */
#define SPT0_AFS_I_SHIFT       0
#define SPT0_BFS_I_SHIFT       5
#define SPT1_AFS_I_SHIFT       10
#define SPT1_BFS_I_SHIFT       15
#define SPT2_AFS_I_SHIFT       20
#define SPT2_BFS_I_SHIFT       25

/*  DAI0_FS1 */
#define SRC0_FS_IP_I_SHIFT     0
#define SRC0_FS_OP_I_SHIFT     5
#define SRC1_FS_IP_I_SHIFT     10
#define SRC1_FS_OP_I_SHIFT     15
#define SRC2_FS_IP_I_SHIFT     20
#define SRC2_FS_OP_I_SHIFT     25

/*  DAI0_FS2 */
#define SRC3_FS_IP_I_SHIFT     0
#define SRC3_FS_OP_I_SHIFT     5
#define SPDIF0_TX_FS_I_SHIFT   10

/*  DAI0_FS3 */

/*  DAI0_FS4 */
#define SPT3_AFS_I_SHIFT       0
#define SPT3_BFS_I_SHIFT       5

/* DAI1 */

/*  DAI1_FS0 */
#define SPT4_AFS_I_SHIFT       0
#define SPT4_BFS_I_SHIFT       5
#define SPT5_AFS_I_SHIFT       10
#define SPT5_BFS_I_SHIFT       15
#define SPT6_AFS_I_SHIFT       20
#define SPT6_BFS_I_SHIFT       25

/* DAI1_FS1 */
#define SRC4_FS_IP_I_SHIFT     0
#define SRC4_FS_OP_I_SHIFT     5
#define SRC5_FS_IP_I_SHIFT     10
#define SRC5_FS_OP_I_SHIFT     15
#define SRC6_FS_IP_I_SHIFT     20
#define SRC6_FS_OP_I_SHIFT     25

/* DAI1_FS2 */
#define SRC7_FS_IP_I_SHIFT     0
#define SRC7_FS_OP_I_SHIFT     5
#define SPDIF1_TX_FS_I_SHIFT   10

/* DAI1_FS3 */

/* DAI1_FS4 */
#define SPT7_AFS_I_SHIFT       0
#define SPT7_BFS_I_SHIFT       5

/* -------------------------------------------- */
/*   Bit Field Codes */
/* -------------------------------------------- */

/* DAI0 */
#define C_DAI0_PB01_O            0x00
#define C_DAI0_PB02_O            0x01
#define C_DAI0_PB03_O            0x02
#define C_DAI0_PB04_O            0x03
#define C_DAI0_PB05_O            0x04
#define C_DAI0_PB06_O            0x05
#define C_DAI0_PB07_O            0x06
#define C_DAI0_PB08_O            0x07
#define C_DAI0_PB09_O            0x08
#define C_DAI0_PB10_O            0x09
#define C_DAI0_PB11_O            0x0a
#define C_DAI0_PB12_O            0x0b
#define C_DAI0_PB13_O            0x0c
#define C_DAI0_PB14_O            0x0d
#define C_DAI0_CRS_PB04_O        0x0e
#define C_DAI0_CRS_PB06_O        0x0f
#define C_DAI0_PB17_O            0x10
#define C_DAI0_PB18_O            0x11
#define C_DAI0_PB19_O            0x12
#define C_DAI0_PB20_O            0x13
#define C_SPT0_AFS_O             0x14
#define C_SPT0_BFS_O             0x15
#define C_SPT1_AFS_O             0x16
#define C_SPT1_BFS_O             0x17
#define C_SPT2_AFS_O             0x18
#define C_SPT2_BFS_O             0x19
#define C_SPDIF0_RX_FS_O         0x1a
#define C_PCG0_FSA_O             0x1c
#define C_PCG0_FSB_O             0x1d
#define C_LOW                    0x1e
#define C_HIGH                   0x1f

/* DAI1 */
#define C2_DAI1_PB01_O           0x01
#define C2_DAI1_PB02_O           0x01
#define C2_DAI1_PB03_O           0x02
#define C2_DAI1_PB04_O           0x03
#define C2_DAI1_PB05_O           0x04
#define C2_DAI1_PB06_O           0x05
#define C2_DAI1_PB07_O           0x06
#define C2_DAI1_PB08_O           0x07
#define C2_DAI1_PB09_O           0x08
#define C2_DAI1_PB10_O           0x09
#define C2_DAI1_PB11_O           0x0a
#define C2_DAI1_PB12_O           0x0b
#define C2_DAI1_PB13_O           0x0c
#define C2_DAI1_PB14_O           0x0d
#define C2_DAI1_CRS_PB04_O       0x0e
#define C2_DAI1_CRS_PB06_O       0x0f
#define C2_DAI1_PB17_O           0x10
#define C2_DAI1_PB18_O           0x11
#define C2_DAI1_PB19_O           0x12
#define C2_DAI1_PB20_O           0x13
#define C2_SPT4_AFS_O            0x14
#define C2_SPT4_BFS_O            0x15
#define C2_SPT5_AFS_O            0x16
#define C2_SPT5_BFS_O            0x17
#define C2_SPT6_AFS_O            0x18
#define C2_SPT6_BFS_O            0x19
#define C2_SPDIF1_RX_FS_O        0x1a
#define C2_PCG0_FSC_O            0x1c
#define C2_PCG0_FSD_O            0x1d
#define C2_LOW                   0x1e
#define C2_HIGH                  0x1f

/*============================================================================*/
/*   Group D - Pin Input Signals */
/* ===========================================================================*/

/* -------------------------------------------- */
/*   Group ID Assignments */
/* -------------------------------------------- */

/* DAI0 */

/*  DAI0_PIN0 */
#define DAI0_PB01_I_GROUP        GROUP_D
#define DAI0_PB02_I_GROUP        GROUP_D
#define DAI0_PB03_I_GROUP        GROUP_D
#define DAI0_PB04_I_GROUP        GROUP_D

/*  DAI0_PIN1 */
#define DAI0_PB05_I_GROUP        GROUP_D
#define DAI0_PB06_I_GROUP        GROUP_D
#define DAI0_PB07_I_GROUP        GROUP_D
#define DAI0_PB08_I_GROUP        GROUP_D

/*  DAI0_PIN2 */
#define DAI0_PB09_I_GROUP        GROUP_D
#define DAI0_PB10_I_GROUP        GROUP_D
#define DAI0_PB11_I_GROUP        GROUP_D
#define DAI0_PB12_I_GROUP        GROUP_D

/*  DAI0_PIN3 */
#define DAI0_PB13_I_GROUP        GROUP_D
#define DAI0_PB14_I_GROUP        GROUP_D
#define DAI0_PB15_I_GROUP        GROUP_D
#define DAI0_PB16_I_GROUP        GROUP_D

/*  DAI0_PIN4 */
#define DAI0_PB17_I_GROUP        GROUP_D
#define DAI0_PB18_I_GROUP        GROUP_D
#define DAI0_PB19_I_GROUP        GROUP_D
#define DAI0_PB20_I_GROUP        GROUP_D
#define INV_DAI0_PB19_I_GROUP    GROUP_G
#define INV_DAI0_PB20_I_GROUP    GROUP_G

/* DAI1 */

/*  DAI1_PIN0 */
#define DAI1_PB01_I_GROUP        GROUP_D2
#define DAI1_PB02_I_GROUP        GROUP_D2
#define DAI1_PB03_I_GROUP        GROUP_D2
#define DAI1_PB04_I_GROUP        GROUP_D2

/*  DAI1_PIN1 */
#define DAI1_PB05_I_GROUP        GROUP_D2
#define DAI1_PB06_I_GROUP        GROUP_D2
#define DAI1_PB07_I_GROUP        GROUP_D2
#define DAI1_PB08_I_GROUP        GROUP_D2

/*  DAI1_PIN2 */
#define DAI1_PB09_I_GROUP        GROUP_D2
#define DAI1_PB10_I_GROUP        GROUP_D2
#define DAI1_PB11_I_GROUP        GROUP_D2
#define DAI1_PB12_I_GROUP        GROUP_D2

/*  DAI1_PIN3 */
#define DAI1_PB13_I_GROUP        GROUP_D2
#define DAI1_PB14_I_GROUP        GROUP_D2
#define DAI1_PB15_I_GROUP        GROUP_D2
#define DAI1_PB16_I_GROUP        GROUP_D2

/*  DAI1_PIN4 */
#define DAI1_PB17_I_GROUP        GROUP_D2
#define DAI1_PB18_I_GROUP        GROUP_D2
#define DAI1_PB19_I_GROUP        GROUP_D2
#define DAI1_PB20_I_GROUP        GROUP_D2
#define INV_DAI1_PB19_I_GROUP    GROUP_G2
#define INV_DAI1_PB20_I_GROUP    GROUP_G2

/* -------------------------------------------- */
/*   Register Assignments */
/* -------------------------------------------- */

/* DAI0 */

#define DAI0_PB01_I_REG          REG_DAI0_PIN0
#define DAI0_PB02_I_REG          REG_DAI0_PIN0
#define DAI0_PB03_I_REG          REG_DAI0_PIN0
#define DAI0_PB04_I_REG          REG_DAI0_PIN0
                                 
#define DAI0_PB05_I_REG          REG_DAI0_PIN1
#define DAI0_PB06_I_REG          REG_DAI0_PIN1
#define DAI0_PB07_I_REG          REG_DAI0_PIN1
#define DAI0_PB08_I_REG          REG_DAI0_PIN1
                                 
#define DAI0_PB09_I_REG          REG_DAI0_PIN2
#define DAI0_PB10_I_REG          REG_DAI0_PIN2
#define DAI0_PB11_I_REG          REG_DAI0_PIN2
#define DAI0_PB12_I_REG          REG_DAI0_PIN2
                                 
#define DAI0_PB13_I_REG          REG_DAI0_PIN3
#define DAI0_PB14_I_REG          REG_DAI0_PIN3
#define DAI0_PB15_I_REG          REG_DAI0_PIN3
#define DAI0_PB16_I_REG          REG_DAI0_PIN3

#define DAI0_PB17_I_REG          REG_DAI0_PIN4
#define DAI0_PB18_I_REG          REG_DAI0_PIN4
#define DAI0_PB19_I_REG          REG_DAI0_PIN4
#define DAI0_PB20_I_REG          REG_DAI0_PIN4
#define INV_DAI0_PB19_I_REG      REG_DAI0_PIN4
#define INV_DAI0_PB20_I_REG      REG_DAI0_PIN4
           
/* DAI1 */

#define DAI1_PB01_I_REG          REG_DAI1_PIN0
#define DAI1_PB02_I_REG          REG_DAI1_PIN0
#define DAI1_PB03_I_REG          REG_DAI1_PIN0
#define DAI1_PB04_I_REG          REG_DAI1_PIN0
                                        
#define DAI1_PB05_I_REG          REG_DAI1_PIN1
#define DAI1_PB06_I_REG          REG_DAI1_PIN1
#define DAI1_PB07_I_REG          REG_DAI1_PIN1
#define DAI1_PB08_I_REG          REG_DAI1_PIN1
                                        
#define DAI1_PB09_I_REG          REG_DAI1_PIN2
#define DAI1_PB10_I_REG          REG_DAI1_PIN2
#define DAI1_PB11_I_REG          REG_DAI1_PIN2
#define DAI1_PB12_I_REG          REG_DAI1_PIN2
                                        
#define DAI1_PB13_I_REG          REG_DAI1_PIN3
#define DAI1_PB14_I_REG          REG_DAI1_PIN3
#define DAI1_PB15_I_REG          REG_DAI1_PIN3
#define DAI1_PB16_I_REG          REG_DAI1_PIN3
                                        
#define DAI1_PB17_I_REG          REG_DAI1_PIN4
#define DAI1_PB18_I_REG          REG_DAI1_PIN4
#define DAI1_PB19_I_REG          REG_DAI1_PIN4
#define DAI1_PB20_I_REG          REG_DAI1_PIN4
#define INV_DAI1_PB19_I_REG      REG_DAI1_PIN4
#define INV_DAI1_PB20_I_REG      REG_DAI1_PIN4

/* -------------------------------------------- */
/*   Shift Values for Bit Fields */
/* -------------------------------------------- */

/* DAI0 */

/*  DAI0_PIN0 */
#define DAI0_PB01_I_SHIFT        0
#define DAI0_PB02_I_SHIFT        7
#define DAI0_PB03_I_SHIFT        14
#define DAI0_PB04_I_SHIFT        21

/*  DAI0_PIN1 */
#define DAI0_PB05_I_SHIFT        0
#define DAI0_PB06_I_SHIFT        7
#define DAI0_PB07_I_SHIFT        14
#define DAI0_PB08_I_SHIFT        21

/*  DAI0_PIN2 */
#define DAI0_PB09_I_SHIFT        0
#define DAI0_PB10_I_SHIFT        7
#define DAI0_PB11_I_SHIFT        14
#define DAI0_PB12_I_SHIFT        21

/*  DAI0_PIN3 */
#define DAI0_PB13_I_SHIFT        0
#define DAI0_PB14_I_SHIFT        7
#define DAI0_PB15_I_SHIFT        14
#define DAI0_PB16_I_SHIFT        21

/* DAI0_PIN4 */
#define DAI0_PB17_I_SHIFT        0
#define DAI0_PB18_I_SHIFT        7
#define DAI0_PB19_I_SHIFT        14
#define DAI0_PB20_I_SHIFT        21
#define INV_DAI0_PB19_I_SHIFT    28
#define INV_DAI0_PB20_I_SHIFT    29

/* DAI1 */

/*  DAI1_PIN0 */
#define DAI1_PB01_I_SHIFT        0
#define DAI1_PB02_I_SHIFT        7
#define DAI1_PB03_I_SHIFT        14
#define DAI1_PB04_I_SHIFT        21

/*  DAI1_PIN1 */
#define DAI1_PB05_I_SHIFT        0
#define DAI1_PB06_I_SHIFT        7
#define DAI1_PB07_I_SHIFT        14
#define DAI1_PB08_I_SHIFT        21

/*  DAI1_PIN2 */
#define DAI1_PB09_I_SHIFT        0
#define DAI1_PB10_I_SHIFT        7
#define DAI1_PB11_I_SHIFT        14
#define DAI1_PB12_I_SHIFT        21

/*  DAI1_PIN3 */
#define DAI1_PB13_I_SHIFT        0
#define DAI1_PB14_I_SHIFT        7
#define DAI1_PB15_I_SHIFT        14
#define DAI1_PB16_I_SHIFT        21

/* DAI1_PIN4 */
#define DAI1_PB17_I_SHIFT        0
#define DAI1_PB18_I_SHIFT        7
#define DAI1_PB19_I_SHIFT        14
#define DAI1_PB20_I_SHIFT        21
#define INV_DAI1_PB19_I_SHIFT    28
#define INV_DAI1_PB20_I_SHIFT    29

/* -------------------------------------------- */
/*   Bit Field Codes */
/* -------------------------------------------- */

/* DAI0 */

#define D_DAI0_PB01_O          0x00
#define D_DAI0_PB02_O          0x01
#define D_DAI0_PB03_O          0x02
#define D_DAI0_PB04_O          0x03
#define D_DAI0_PB05_O          0x04
#define D_DAI0_PB06_O          0x05
#define D_DAI0_PB07_O          0x06
#define D_DAI0_PB08_O          0x07
#define D_DAI0_PB09_O          0x08
#define D_DAI0_PB10_O          0x09
#define D_DAI0_PB11_O          0x0a
#define D_DAI0_PB12_O          0x0b
#define D_DAI0_PB13_O          0x0c
#define D_DAI0_PB14_O          0x0d
#define D_DAI0_PB15_O          0x0e
#define D_DAI0_PB16_O          0x0f
#define D_DAI0_PB17_O          0x10
#define D_DAI0_PB18_O          0x11
#define D_DAI0_PB19_O          0x12
#define D_DAI0_PB20_O          0x13
#define D_SPT0_AD0_O           0x14
#define D_SPT0_AD1_O           0x15
#define D_SPT0_BD0_O           0x16
#define D_SPT0_BD1_O           0x17
#define D_SPT1_AD0_O           0x18
#define D_SPT1_AD1_O           0x19
#define D_SPT1_BD0_O           0x1a
#define D_SPT1_BD1_O           0x1b
#define D_SPT2_AD0_O           0x1c
#define D_SPT2_AD1_O           0x1d
#define D_SPT2_BD0_O           0x1e
#define D_SPT2_BD1_O           0x1f
#define D_SPT0_ACLK_O          0x20
#define D_SPT0_BCLK_O          0x21
#define D_SPT1_ACLK_O          0x22
#define D_SPT1_BCLK_O          0x23
#define D_SPT2_ACLK_O          0x24
#define D_SPT2_BCLK_O          0x25
#define D_SPT0_AFS_O           0x26
#define D_SPT0_BFS_O           0x27
#define D_SPT1_AFS_O           0x28
#define D_SPT1_BFS_O           0x29
#define D_SPT2_AFS_O           0x2a
#define D_SPT2_BFS_O           0x2b
#define D_SPT3_AD0_O           0x2c
#define D_SPT3_AD1_O           0x2d
#define D_SPT3_BD0_O           0x2e
#define D_SPT3_BD1_O           0x2f
#define D_MLB0_CLKOUT_O        0x30
#define D_SPDIF0_TX_BLKSTART_O 0x31
#define D_SPT3_ACLK_O          0x34
#define D_SPT3_BCLK_O          0x35
#define D_SPT3_AFS_O           0x36
#define D_SPT3_BFS_O           0x37
#define D_PCG0_CLKA_O          0x38
#define D_PCG0_CLKB_O          0x39
#define D_PCG0_FSA_O           0x3a
#define D_PCG0_FSB_O           0x3b
#define D_SRC0_DAT_OP_O        0x3d
#define D_SRC1_DAT_OP_O        0x3e
#define D_SRC2_DAT_OP_O        0x3f
#define D_SRC3_DAT_OP_O        0x40
#define D_SPDIF0_RX_DAT_O      0x41
#define D_SPDIF0_RX_FS_O       0x42
#define D_SPDIF0_RX_CLK_O      0x43
#define D_SPDIF0_RX_TDMCLK_O   0x44
#define D_SPDIF0_TX_O          0x45
#define D_SPT0_ATDV_O          0x46
#define D_SPT0_BTDV_O          0x47
#define D_SPT1_ATDV_O          0x48
#define D_SPT1_BTDV_O          0x49
#define D_SPT2_ATDV_O          0x4a
#define D_SPT2_BTDV_O          0x4b
#define D_SPT3_ATDV_O          0x4c
#define D_SPT3_BTDV_O          0x4d
#define D_PCG0_CRS_CLKC_O      0x50
#define D_PCG0_CRS_CLKD_O      0x51
#define D_PCG0_CRS_FSC_O       0x52
#define D_PCG0_CRS_FSD_O       0x53
#define D_DAI0_CRS_PB03_O      0x54
#define D_DAI0_CRS_PB04_O      0x55
#define D_DAI0_CRS_PB05_O      0x56
#define D_DAI0_CRS_PB06_O      0x57
#define D_LOW                  0x7e
#define D_HIGH                 0x7f

/* DAI1 */

#define D2_DAI1_PB01_O            0x00
#define D2_DAI1_PB02_O            0x01
#define D2_DAI1_PB03_O            0x02
#define D2_DAI1_PB04_O            0x03
#define D2_DAI1_PB05_O            0x04
#define D2_DAI1_PB06_O            0x05
#define D2_DAI1_PB07_O            0x06
#define D2_DAI1_PB08_O            0x07
#define D2_DAI1_PB09_O            0x08
#define D2_DAI1_PB10_O            0x09
#define D2_DAI1_PB11_O            0x0a
#define D2_DAI1_PB12_O            0x0b
#define D2_DAI1_PB13_O            0x0c
#define D2_DAI1_PB14_O            0x0d
#define D2_DAI1_PB15_O            0x0e
#define D2_DAI1_PB16_O            0x0f
#define D2_DAI1_PB17_O            0x10
#define D2_DAI1_PB18_O            0x11
#define D2_DAI1_PB19_O            0x12
#define D2_DAI1_PB20_O            0x13
#define D2_SPT4_AD0_O             0x14
#define D2_SPT4_AD1_O             0x15
#define D2_SPT4_BD0_O             0x16
#define D2_SPT4_BD1_O             0x17
#define D2_SPT5_AD0_O             0x18
#define D2_SPT5_AD1_O             0x19
#define D2_SPT5_BD0_O             0x1a
#define D2_SPT5_BD1_O             0x1b
#define D2_SPT6_AD0_O             0x1c
#define D2_SPT6_AD1_O             0x1d
#define D2_SPT6_BD0_O             0x1e
#define D2_SPT6_BD1_O             0x1f
#define D2_SPT4_ACLK_O            0x20
#define D2_SPT4_BCLK_O            0x21
#define D2_SPT5_ACLK_O            0x22
#define D2_SPT5_BCLK_O            0x23
#define D2_SPT6_ACLK_O            0x24
#define D2_SPT6_BCLK_O            0x25
#define D2_SPT4_AFS_O             0x26
#define D2_SPT4_BFS_O             0x27
#define D2_SPT5_AFS_O             0x28
#define D2_SPT5_BFS_O             0x29
#define D2_SPT6_AFS_O             0x2a
#define D2_SPT6_BFS_O             0x2b
#define D2_SPT7_AD0_O             0x2c
#define D2_SPT7_AD1_O             0x2d
#define D2_SPT7_BD0_O             0x2e
#define D2_SPT7_BD1_O             0x2f
#define D2_MLB0_CLKOUT_O          0x30
#define D2_SPDIF1_TX_BLKSTART_O   0x31
#define D2_SPT7_ACLK_O            0x34
#define D2_SPT7_BCLK_O            0x35
#define D2_SPT7_AFS_O             0x36
#define D2_SPT7_BFS_O             0x37
#define D2_PCG0_CLKC_O            0x38
#define D2_PCG0_CLKD_O            0x39
#define D2_PCG0_FSC_O             0x3a
#define D2_PCG0_FSD_O             0x3b
#define D2_SRC4_DAT_OP_O          0x3d
#define D2_SRC5_DAT_OP_O          0x3e
#define D2_SRC6_DAT_OP_O          0x3f
#define D2_SRC7_DAT_OP_O          0x40
#define D2_SPDIF1_RX_DAT_O        0x41
#define D2_SPDIF1_RX_FS_O         0x42
#define D2_SPDIF1_RX_CLK_O        0x43
#define D2_SPDIF1_RX_TDMCLK_O     0x44
#define D2_SPDIF1_TX_O            0x45
#define D2_SPT4_ATDV_O            0x46
#define D2_SPT4_BTDV_O            0x47
#define D2_SPT5_ATDV_O            0x48
#define D2_SPT5_BTDV_O            0x49
#define D2_SPT6_ATDV_O            0x4a
#define D2_SPT6_BTDV_O            0x4b
#define D2_SPT7_ATDV_O            0x4c
#define D2_SPT7_BTDV_O            0x4d
#define D2_PCG0_CRS_CLKA_O        0x50
#define D2_PCG0_CRS_CLKB_O        0x51
#define D2_PCG0_CRS_FSA_O         0x52
#define D2_PCG0_CRS_FSB_O         0x53
#define D2_DAI1_CRS_PB03_O        0x54
#define D2_DAI1_CRS_PB04_O        0x55
#define D2_DAI1_CRS_PB05_O        0x56
#define D2_DAI1_CRS_PB06_O        0x57
#define D2_LOW                    0x7e
#define D2_HIGH                   0x7f

/*============================================================================*/
/*   Group E - Miscellaneous SRU Signals */
/*============================================================================*/

/* -------------------------------------------- */
/*   Group ID Assignments */
/* -------------------------------------------- */     

/* DAI0 */

/*  DAI0_MISC0 */
#define DAI0_MISCA0_I_GROUP      GROUP_E
#define DAI0_INT_6_I_GROUP       GROUP_E
#define DAI0_MISCA1_I_GROUP      GROUP_E
#define DAI0_INT_7_I_GROUP       GROUP_E
#define DAI0_MISCA2_I_GROUP      GROUP_E
#define DAI0_INT_8_I_GROUP       GROUP_E
#define DAI0_MISCA3_I_GROUP      GROUP_E
#define DAI0_INT_9_I_GROUP       GROUP_E
#define DAI0_MISCA4_I_GROUP      GROUP_E
#define DAI0_MISCA5_I_GROUP      GROUP_E
#define DAI0_INV_MISCA4_I_GROUP  GROUP_G
#define DAI0_INV_MISCA5_I_GROUP  GROUP_G

/*  DAI0_MISC1 */
#define DAI0_INT_0_I_GROUP       GROUP_E
#define DAI0_INT_1_I_GROUP       GROUP_E
#define DAI0_INT_2_I_GROUP       GROUP_E
#define DAI0_INT_3_I_GROUP       GROUP_E
#define DAI0_INT_4_I_GROUP       GROUP_E
#define DAI0_INT_5_I_GROUP       GROUP_E
#define DAI1_INV_MISCA4_I_GROUP  GROUP_G2
#define DAI1_INV_MISCA5_I_GROUP  GROUP_G2

/* DAI1 */

/*  DAI1_MISC0 */
#define DAI1_MISCA0_I_GROUP      GROUP_E2
#define DAI1_INT_6_I_GROUP       GROUP_E2
#define DAI1_MISCA1_I_GROUP      GROUP_E2
#define DAI1_INT_7_I_GROUP       GROUP_E2
#define DAI1_MISCA2_I_GROUP      GROUP_E2
#define DAI1_INT_8_I_GROUP       GROUP_E2
#define DAI1_MISCA3_I_GROUP      GROUP_E2
#define DAI1_INT_9_I_GROUP       GROUP_E2
#define DAI1_MISCA4_I_GROUP      GROUP_E2
#define DAI1_MISCA5_I_GROUP      GROUP_E2

/*  DAI1_MISC1 */
#define DAI1_INT_0_I_GROUP       GROUP_E2
#define DAI1_INT_1_I_GROUP       GROUP_E2
#define DAI1_INT_2_I_GROUP       GROUP_E2
#define DAI1_INT_3_I_GROUP       GROUP_E2
#define DAI1_INT_4_I_GROUP       GROUP_E2
#define DAI1_INT_5_I_GROUP       GROUP_E2

/* -------------------------------------------- */
/*   Register Assignments */
/* -------------------------------------------- */   

/* DAI0 */
#define DAI0_MISCA0_I_REG       REG_DAI0_MISC0
#define DAI0_INT_6_I_REG        REG_DAI0_MISC0
#define DAI0_MISCA1_I_REG       REG_DAI0_MISC0
#define DAI0_INT_7_I_REG        REG_DAI0_MISC0
#define DAI0_MISCA2_I_REG       REG_DAI0_MISC0
#define DAI0_INT_8_I_REG        REG_DAI0_MISC0
#define DAI0_MISCA3_I_REG       REG_DAI0_MISC0
#define DAI0_INT_9_I_REG        REG_DAI0_MISC0
#define DAI0_MISCA4_I_REG       REG_DAI0_MISC0
#define DAI0_MISCA5_I_REG       REG_DAI0_MISC0
#define DAI0_INV_MISCA4_I_REG   REG_DAI0_MISC0
#define DAI0_INV_MISCA5_I_REG   REG_DAI0_MISC0

#define DAI0_INT_0_I_REG        REG_DAI0_MISC1
#define DAI0_INT_1_I_REG        REG_DAI0_MISC1
#define DAI0_INT_2_I_REG        REG_DAI0_MISC1
#define DAI0_INT_3_I_REG        REG_DAI0_MISC1
#define DAI0_INT_4_I_REG        REG_DAI0_MISC1
#define DAI0_INT_5_I_REG        REG_DAI0_MISC1

/* DAI1 */
#define DAI1_MISCA0_I_REG       REG_DAI1_MISC0
#define DAI1_INT_6_I_REG        REG_DAI1_MISC0
#define DAI1_MISCA1_I_REG       REG_DAI1_MISC0
#define DAI1_INT_7_I_REG        REG_DAI1_MISC0
#define DAI1_MISCA2_I_REG       REG_DAI1_MISC0
#define DAI1_INT_8_I_REG        REG_DAI1_MISC0
#define DAI1_MISCA3_I_REG       REG_DAI1_MISC0
#define DAI1_INT_9_I_REG        REG_DAI1_MISC0
#define DAI1_MISCA4_I_REG       REG_DAI1_MISC0
#define DAI1_MISCA5_I_REG       REG_DAI1_MISC0
#define DAI1_INV_MISCA4_I_REG   REG_DAI1_MISC0
#define DAI1_INV_MISCA5_I_REG   REG_DAI1_MISC0

#define DAI1_INT_0_I_REG        REG_DAI1_MISC1
#define DAI1_INT_1_I_REG        REG_DAI1_MISC1
#define DAI1_INT_2_I_REG        REG_DAI1_MISC1
#define DAI1_INT_3_I_REG        REG_DAI1_MISC1
#define DAI1_INT_4_I_REG        REG_DAI1_MISC1
#define DAI1_INT_5_I_REG        REG_DAI1_MISC1

/* -------------------------------------------- */
/*   Shift Values for Bit Fields */
/* -------------------------------------------- */

/* DAI0 */

/*  DAI0_MISC0 */
#define DAI0_MISCA0_I_SHIFT      0
#define DAI0_INT_6_I_SHIFT       0
#define DAI0_MISCA1_I_SHIFT      5
#define DAI0_INT_7_I_SHIFT       5
#define DAI0_MISCA2_I_SHIFT      10
#define DAI0_INT_8_I_SHIFT       10
#define DAI0_MISCA3_I_SHIFT      15
#define DAI0_INT_9_I_SHIFT       15
#define DAI0_MISCA4_I_SHIFT      20
#define DAI0_MISCA5_I_SHIFT      25
#define DAI0_INV_MISCA4_I_SHIFT  30
#define DAI0_INV_MISCA5_I_SHIFT  31

/*  DAI0_MISC1  */
#define DAI0_INT_0_I_SHIFT       0
#define DAI0_INT_1_I_SHIFT       5
#define DAI0_INT_2_I_SHIFT       10
#define DAI0_INT_3_I_SHIFT       15
#define DAI0_INT_4_I_SHIFT       20
#define DAI0_INT_5_I_SHIFT       25
                                 
/* DAI1 */

/*  DAI1_MISC0 */
#define DAI1_MISCA0_I_SHIFT      0
#define DAI1_INT_6_I_SHIFT       0
#define DAI1_MISCA1_I_SHIFT      5
#define DAI1_INT_7_I_SHIFT       5
#define DAI1_MISCA2_I_SHIFT      10
#define DAI1_INT_8_I_SHIFT       10
#define DAI1_MISCA3_I_SHIFT      15
#define DAI1_INT_9_I_SHIFT       15
#define DAI1_MISCA4_I_SHIFT      20
#define DAI1_MISCA5_I_SHIFT      25
#define DAI1_INV_MISCA4_I_SHIFT  30
#define DAI1_INV_MISCA5_I_SHIFT  31

/*  DAI1_MISC1 */
#define DAI1_INT_0_I_SHIFT       0
#define DAI1_INT_1_I_SHIFT       5
#define DAI1_INT_2_I_SHIFT       10
#define DAI1_INT_3_I_SHIFT       15
#define DAI1_INT_4_I_SHIFT       20
#define DAI1_INT_5_I_SHIFT       25

/* -------------------------------------------- */
/*   Bit Field Codes */
/* -------------------------------------------- */

/* DAI0 */

#define E_DAI0_PB01_O            0x00
#define E_DAI0_PB02_O            0x01
#define E_DAI0_PB03_O            0x02
#define E_DAI0_PB04_O            0x03
#define E_DAI0_PB05_O            0x04
#define E_DAI0_PB06_O            0x05
#define E_DAI0_PB07_O            0x06
#define E_DAI0_PB08_O            0x07
#define E_DAI0_PB09_O            0x08
#define E_DAI0_PB10_O            0x09
#define E_DAI0_PB11_O            0x0a
#define E_DAI0_PB12_O            0x0b
#define E_DAI0_PB13_O            0x0c
#define E_DAI0_PB14_O            0x0d
#define E_DAI0_PB15_O            0x0e
#define E_DAI0_PB16_O            0x0f
#define E_DAI0_PB17_O            0x10
#define E_DAI0_PB18_O            0x11
#define E_DAI0_PB19_O            0x12
#define E_DAI0_PB20_O            0x13
#define E_SPT0_AFS_O             0x14
#define E_SPT0_BFS_O             0x15
#define E_SPT1_AFS_O             0x16
#define E_SPT1_BFS_O             0x17
#define E_SPT2_AFS_O             0x18
#define E_SPT2_BFS_O             0x19
#define E_SPDIF0_TX_BLKSTART_O   0x1a
#define E_PCG0_FSA_O             0x1b
#define E_PCG0_CLKB_O            0x1c
#define E_PCG0_FSB_O             0x1d
#define E_LOW                    0x1e
#define E_HIGH                   0x1f

/* DAI1 */

#define E2_DAI1_PB01_O           0x00
#define E2_DAI1_PB02_O           0x01
#define E2_DAI1_PB03_O           0x02
#define E2_DAI1_PB04_O           0x03
#define E2_DAI1_PB05_O           0x04
#define E2_DAI1_PB06_O           0x05
#define E2_DAI1_PB07_O           0x06
#define E2_DAI1_PB08_O           0x07
#define E2_DAI1_PB09_O           0x08
#define E2_DAI1_PB10_O           0x09
#define E2_DAI1_PB11_O           0x0a
#define E2_DAI1_PB12_O           0x0b
#define E2_DAI1_PB13_O           0x0c
#define E2_DAI1_PB14_O           0x0d
#define E2_DAI1_PB15_O           0x0e
#define E2_DAI1_PB16_O           0x0f
#define E2_DAI1_PB17_O           0x10
#define E2_DAI1_PB18_O           0x11
#define E2_DAI1_PB19_O           0x12
#define E2_DAI1_PB20_O           0x13
#define E2_SPT4_AFS_O            0x14
#define E2_SPT4_BFS_O            0x15
#define E2_SPT5_AFS_O            0x16
#define E2_SPT5_BFS_O            0x17
#define E2_SPT6_AFS_O            0x18
#define E2_SPT6_BFS_O            0x19
#define E2_SPDIF1_TX_BLKSTART_O  0x1a
#define E2_PCG0_FSC_O            0x1b
#define E2_PCG0_CLKD_O           0x1c
#define E2_PCG0_FSD_O            0x1d
#define E2_LOW                   0x1e
#define E2_HIGH                  0x1f

#define G_LOW                    0x00
#define G_HIGH                   0x01

#define G2_LOW                   0x00
#define G2_HIGH                  0x01

/*============================================================================*/
/*   Group F - Pin Buffer Enable Signals */
/*============================================================================*/

/* -------------------------------------------- */
/*   Group ID Assignments */
/* -------------------------------------------- */

/* DAI0 */

#define DAI0_PBEN01_I_GROUP      GROUP_F
#define DAI0_PBEN02_I_GROUP      GROUP_F
#define DAI0_PBEN03_I_GROUP      GROUP_F
#define DAI0_PBEN04_I_GROUP      GROUP_F
#define DAI0_PBEN05_I_GROUP      GROUP_F
        
#define DAI0_PBEN06_I_GROUP      GROUP_F
#define DAI0_PBEN07_I_GROUP      GROUP_F
#define DAI0_PBEN08_I_GROUP      GROUP_F
#define DAI0_PBEN09_I_GROUP      GROUP_F
#define DAI0_PBEN10_I_GROUP      GROUP_F
        
#define DAI0_PBEN11_I_GROUP      GROUP_F
#define DAI0_PBEN12_I_GROUP      GROUP_F
#define DAI0_PBEN13_I_GROUP      GROUP_F
#define DAI0_PBEN14_I_GROUP      GROUP_F
#define DAI0_PBEN15_I_GROUP      GROUP_F
        
#define DAI0_PBEN16_I_GROUP      GROUP_F
#define DAI0_PBEN17_I_GROUP      GROUP_F
#define DAI0_PBEN18_I_GROUP      GROUP_F
#define DAI0_PBEN19_I_GROUP      GROUP_F
#define DAI0_PBEN20_I_GROUP      GROUP_F

/* DAI1 */

#define DAI1_PBEN01_I_GROUP      GROUP_F2
#define DAI1_PBEN02_I_GROUP      GROUP_F2
#define DAI1_PBEN03_I_GROUP      GROUP_F2
#define DAI1_PBEN04_I_GROUP      GROUP_F2
#define DAI1_PBEN05_I_GROUP      GROUP_F2
                                   
#define DAI1_PBEN06_I_GROUP      GROUP_F2
#define DAI1_PBEN07_I_GROUP      GROUP_F2
#define DAI1_PBEN08_I_GROUP      GROUP_F2
#define DAI1_PBEN09_I_GROUP      GROUP_F2
#define DAI1_PBEN10_I_GROUP      GROUP_F2
                                   
#define DAI1_PBEN11_I_GROUP      GROUP_F2
#define DAI1_PBEN12_I_GROUP      GROUP_F2
#define DAI1_PBEN13_I_GROUP      GROUP_F2
#define DAI1_PBEN14_I_GROUP      GROUP_F2
#define DAI1_PBEN15_I_GROUP      GROUP_F2
                                   
#define DAI1_PBEN16_I_GROUP      GROUP_F2
#define DAI1_PBEN17_I_GROUP      GROUP_F2
#define DAI1_PBEN18_I_GROUP      GROUP_F2
#define DAI1_PBEN19_I_GROUP      GROUP_F2
#define DAI1_PBEN20_I_GROUP      GROUP_F2

/*-------------------------------------------- */
/*  Register Assignments */
/*-------------------------------------------- */

/* DAI0 */
#define DAI0_PBEN01_I_REG        REG_DAI0_PBEN0
#define DAI0_PBEN02_I_REG        REG_DAI0_PBEN0
#define DAI0_PBEN03_I_REG        REG_DAI0_PBEN0
#define DAI0_PBEN04_I_REG        REG_DAI0_PBEN0
#define DAI0_PBEN05_I_REG        REG_DAI0_PBEN0
                                 
#define DAI0_PBEN06_I_REG        REG_DAI0_PBEN1
#define DAI0_PBEN07_I_REG        REG_DAI0_PBEN1
#define DAI0_PBEN08_I_REG        REG_DAI0_PBEN1
#define DAI0_PBEN09_I_REG        REG_DAI0_PBEN1
#define DAI0_PBEN10_I_REG        REG_DAI0_PBEN1
                                 
#define DAI0_PBEN11_I_REG        REG_DAI0_PBEN2
#define DAI0_PBEN12_I_REG        REG_DAI0_PBEN2
#define DAI0_PBEN13_I_REG        REG_DAI0_PBEN2
#define DAI0_PBEN14_I_REG        REG_DAI0_PBEN2
#define DAI0_PBEN15_I_REG        REG_DAI0_PBEN2
                                 
#define DAI0_PBEN16_I_REG        REG_DAI0_PBEN3
#define DAI0_PBEN17_I_REG        REG_DAI0_PBEN3
#define DAI0_PBEN18_I_REG        REG_DAI0_PBEN3
#define DAI0_PBEN19_I_REG        REG_DAI0_PBEN3
#define DAI0_PBEN20_I_REG        REG_DAI0_PBEN3

/* DAI1 */
#define DAI1_PBEN01_I_REG        REG_DAI1_PBEN0
#define DAI1_PBEN02_I_REG        REG_DAI1_PBEN0
#define DAI1_PBEN03_I_REG        REG_DAI1_PBEN0
#define DAI1_PBEN04_I_REG        REG_DAI1_PBEN0
#define DAI1_PBEN05_I_REG        REG_DAI1_PBEN0
                                 
#define DAI1_PBEN06_I_REG        REG_DAI1_PBEN1
#define DAI1_PBEN07_I_REG        REG_DAI1_PBEN1
#define DAI1_PBEN08_I_REG        REG_DAI1_PBEN1
#define DAI1_PBEN09_I_REG        REG_DAI1_PBEN1
#define DAI1_PBEN10_I_REG        REG_DAI1_PBEN1
                                 
#define DAI1_PBEN11_I_REG        REG_DAI1_PBEN2
#define DAI1_PBEN12_I_REG        REG_DAI1_PBEN2
#define DAI1_PBEN13_I_REG        REG_DAI1_PBEN2
#define DAI1_PBEN14_I_REG        REG_DAI1_PBEN2
#define DAI1_PBEN15_I_REG        REG_DAI1_PBEN2
                                 
#define DAI1_PBEN16_I_REG        REG_DAI1_PBEN3
#define DAI1_PBEN17_I_REG        REG_DAI1_PBEN3
#define DAI1_PBEN18_I_REG        REG_DAI1_PBEN3
#define DAI1_PBEN19_I_REG        REG_DAI1_PBEN3
#define DAI1_PBEN20_I_REG        REG_DAI1_PBEN3

/* -------------------------------------------- */
/*   Shift Values for Bit Fields */
/* -------------------------------------------- */
  
/* DAI0     */

/*  DAI0_PBEN0 */
#define DAI0_PBEN01_I_SHIFT      0
#define DAI0_PBEN02_I_SHIFT      6
#define DAI0_PBEN03_I_SHIFT      12
#define DAI0_PBEN04_I_SHIFT      18
#define DAI0_PBEN05_I_SHIFT      24
    
/*  DAI0_PBEN1 */
#define DAI0_PBEN06_I_SHIFT      0
#define DAI0_PBEN07_I_SHIFT      6
#define DAI0_PBEN08_I_SHIFT      12
#define DAI0_PBEN09_I_SHIFT      18
#define DAI0_PBEN10_I_SHIFT      24
    
/*  DAI0_PBEN2 */
#define DAI0_PBEN11_I_SHIFT      0
#define DAI0_PBEN12_I_SHIFT      6
#define DAI0_PBEN13_I_SHIFT      12
#define DAI0_PBEN14_I_SHIFT      18
#define DAI0_PBEN15_I_SHIFT      24

/*  DAI0_PBEN3 */
#define DAI0_PBEN16_I_SHIFT      0
#define DAI0_PBEN17_I_SHIFT      6
#define DAI0_PBEN18_I_SHIFT      12
#define DAI0_PBEN19_I_SHIFT      18
#define DAI0_PBEN20_I_SHIFT      24

/* DAI1 */

/*  DAI1_PBEN0 */
#define DAI1_PBEN01_I_SHIFT      0
#define DAI1_PBEN02_I_SHIFT      6
#define DAI1_PBEN03_I_SHIFT      12
#define DAI1_PBEN04_I_SHIFT      18
#define DAI1_PBEN05_I_SHIFT      24
    
/*  DAI1_PBEN1 */
#define DAI1_PBEN06_I_SHIFT      0
#define DAI1_PBEN07_I_SHIFT      6
#define DAI1_PBEN08_I_SHIFT      12
#define DAI1_PBEN09_I_SHIFT      18
#define DAI1_PBEN10_I_SHIFT      24
    
/*  DAI1_PBEN2 */
#define DAI1_PBEN11_I_SHIFT      0
#define DAI1_PBEN12_I_SHIFT      6
#define DAI1_PBEN13_I_SHIFT      12
#define DAI1_PBEN14_I_SHIFT      18
#define DAI1_PBEN15_I_SHIFT      24

/*  DAI1_PBEN3 */
#define DAI1_PBEN16_I_SHIFT      0
#define DAI1_PBEN17_I_SHIFT      6
#define DAI1_PBEN18_I_SHIFT      12
#define DAI1_PBEN19_I_SHIFT      18
#define DAI1_PBEN20_I_SHIFT      24

/* -------------------------------------------- */
/*   Bit Field Codes */
/* -------------------------------------------- */

/* DAI0 */

#define F_LOW                  0x00
#define F_HIGH                 0x01
#define F_DAI0_MISCA0_O        0x02
#define F_DAI0_MISCA1_O        0x03
#define F_DAI0_MISCA2_O        0x04
#define F_DAI0_MISCA3_O        0x05
#define F_DAI0_MISCA4_O        0x06
#define F_DAI0_MISCA5_O        0x07
#define F_SPT0_ACLK_PBEN_O     0x08
#define F_SPT0_AFS_PBEN_O      0x09
#define F_SPT0_AD0_PBEN_O      0x0a
#define F_SPT0_AD1_PBEN_O      0x0b
#define F_SPT0_BCLK_PBEN_O     0x0c
#define F_SPT0_BFS_PBEN_O      0x0d
#define F_SPT0_BD0_PBEN_O      0x0e
#define F_SPT0_BD1_PBEN_O      0x0f
#define F_SPT1_ACLK_PBEN_O     0x10
#define F_SPT1_AFS_PBEN_O      0x11
#define F_SPT1_AD0_PBEN_O      0x12
#define F_SPT1_AD1_PBEN_O      0x13
#define F_SPT1_BCLK_PBEN_O     0x14
#define F_SPT1_BFS_PBEN_O      0x15
#define F_SPT1_BD0_PBEN_O      0x16
#define F_SPT1_BD1_PBEN_O      0x17
#define F_SPT2_ACLK_PBEN_O     0x18
#define F_SPT2_AFS_PBEN_O      0x19
#define F_SPT2_AD0_PBEN_O      0x1a
#define F_SPT2_AD1_PBEN_O      0x1b
#define F_SPT2_BCLK_PBEN_O     0x1c
#define F_SPT2_BFS_PBEN_O      0x1d
#define F_SPT2_BD0_PBEN_O      0x1e
#define F_SPT2_BD1_PBEN_O      0x1f
#define F_SPT3_ACLK_PBEN_O     0x20
#define F_SPT3_AFS_PBEN_O      0x21
#define F_SPT3_AD0_PBEN_O      0x22
#define F_SPT3_AD1_PBEN_O      0x23
#define F_SPT3_BCLK_PBEN_O     0x24
#define F_SPT3_BFS_PBEN_O      0x25
#define F_SPT3_BD0_PBEN_O      0x26
#define F_SPT3_BD1_PBEN_O      0x27
#define F_SPT0_ATDV_PBEN_O     0x28
#define F_SPT0_BTDV_PBEN_O     0x29
#define F_SPT1_ATDV_PBEN_O     0x2a
#define F_SPT1_BTDV_PBEN_O     0x2b
#define F_SPT2_ATDV_PBEN_O     0x2c
#define F_SPT2_BTDV_PBEN_O     0x2d
#define F_SPT3_ATDV_PBEN_O     0x2e
#define F_SPT3_BTDV_PBEN_O     0x2f

/* DAI1 */

#define F2_LOW                  0x00
#define F2_HIGH                 0x01
#define F2_DAI1_MISCA0_O        0x02
#define F2_DAI1_MISCA1_O        0x03
#define F2_DAI1_MISCA2_O        0x04
#define F2_DAI1_MISCA3_O        0x05
#define F2_DAI1_MISCA4_O        0x06
#define F2_DAI1_MISCA5_O        0x07
#define F2_SPT4_ACLK_PBEN_O     0x08
#define F2_SPT4_AFS_PBEN_O      0x09
#define F2_SPT4_AD0_PBEN_O      0x0a
#define F2_SPT4_AD1_PBEN_O      0x0b
#define F2_SPT4_BCLK_PBEN_O     0x0c
#define F2_SPT4_BFS_PBEN_O      0x0d
#define F2_SPT4_BD0_PBEN_O      0x0e
#define F2_SPT4_BD1_PBEN_O      0x0f
#define F2_SPT5_ACLK_PBEN_O     0x10
#define F2_SPT5_AFS_PBEN_O      0x11
#define F2_SPT5_AD0_PBEN_O      0x12
#define F2_SPT5_AD1_PBEN_O      0x13
#define F2_SPT5_BCLK_PBEN_O     0x14
#define F2_SPT5_BFS_PBEN_O      0x15
#define F2_SPT5_BD0_PBEN_O      0x16
#define F2_SPT5_BD1_PBEN_O      0x17
#define F2_SPT6_ACLK_PBEN_O     0x18
#define F2_SPT6_AFS_PBEN_O      0x19
#define F2_SPT6_AD0_PBEN_O      0x1a
#define F2_SPT6_AD1_PBEN_O      0x1b
#define F2_SPT6_BCLK_PBEN_O     0x1c
#define F2_SPT6_BFS_PBEN_O      0x1d
#define F2_SPT6_BD0_PBEN_O      0x1e
#define F2_SPT6_BD1_PBEN_O      0x1f
#define F2_SPT7_ACLK_PBEN_O     0x20
#define F2_SPT7_AFS_PBEN_O      0x21
#define F2_SPT7_AD0_PBEN_O      0x22
#define F2_SPT7_AD1_PBEN_O      0x23
#define F2_SPT7_BCLK_PBEN_O     0x24
#define F2_SPT7_BFS_PBEN_O      0x25
#define F2_SPT7_BD0_PBEN_O      0x26
#define F2_SPT7_BD1_PBEN_O      0x27
#define F2_SPT4_ATDV_PBEN_O     0x28
#define F2_SPT4_BTDV_PBEN_O     0x29
#define F2_SPT5_ATDV_PBEN_O     0x2a
#define F2_SPT5_BTDV_PBEN_O     0x2b
#define F2_SPT6_ATDV_PBEN_O     0x2c
#define F2_SPT6_BTDV_PBEN_O     0x2d
#define F2_SPT7_ATDV_PBEN_O     0x2e
#define F2_SPT7_BTDV_PBEN_O     0x2f

/*============================================================================*/
/* Backwards compatibility:                                                   */
/*   The following macros used incorrect naming conventions and have been     */
/*   renamed. They are deprecated and provided for temporary backwards        */
/*   compatibility only.                                                      */
/*============================================================================*/

#define E_SPT0A_FS_O            E_SPT0_AFS_O
#define E_SPT0B_FS_O            E_SPT0_BFS_O
#define E_SPT1A_FS_O            E_SPT1_AFS_O
#define E_SPT1B_FS_O            E_SPT1_BFS_O
#define E_SPT2A_FS_O            E_SPT2_AFS_O
#define E_SPT2B_FS_O            E_SPT2_BFS_O
#define E2_SPT4A_FS_O           E2_SPT4_AFS_O
#define E2_SPT4B_FS_O           E2_SPT4_BFS_O
#define E2_SPT5A_FS_O           E2_SPT5_AFS_O
#define E2_SPT5B_FS_O           E2_SPT5_BFS_O
#define E2_SPT6A_FS_O           E2_SPT6_AFS_O
#define E2_SPT6B_FS_O           E2_SPT6_BFS_O

#define SRC0_DAT_OP_I_REG       REG_DAI0_DAT3
#define SRC1_DAT_OP_I_REG       REG_DAI0_DAT3
#define SRC2_DAT_OP_I_REG       REG_DAI0_DAT3
#define SRC3_DAT_OP_I_REG       REG_DAI0_DAT3

#define SRC0_TDM_OP_I_GROUP     SRC0_DAT_TDM_OP_I_GROUP
#define SRC1_TDM_OP_I_GROUP     SRC1_DAT_TDM_OP_I_GROUP
#define SRC2_TDM_OP_I_GROUP     SRC2_DAT_TDM_OP_I_GROUP
#define SRC3_TDM_OP_I_GROUP     SRC3_DAT_TDM_OP_I_GROUP
#define SRC4_TDM_OP_I_GROUP     SRC4_DAT_TDM_OP_I_GROUP
#define SRC5_TDM_OP_I_GROUP     SRC5_DAT_TDM_OP_I_GROUP
#define SRC6_TDM_OP_I_GROUP     SRC6_DAT_TDM_OP_I_GROUP
#define SRC7_TDM_OP_I_GROUP     SRC7_DAT_TDM_OP_I_GROUP
#define SRC0_TDM_OP_I_REG       SRC0_DAT_TDM_OP_I_REG
#define SRC1_TDM_OP_I_REG       SRC1_DAT_TDM_OP_I_REG
#define SRC2_TDM_OP_I_REG       SRC2_DAT_TDM_OP_I_REG
#define SRC3_TDM_OP_I_REG       SRC3_DAT_TDM_OP_I_REG
#define SRC4_TDM_OP_I_REG       SRC4_DAT_TDM_OP_I_REG
#define SRC5_TDM_OP_I_REG       SRC5_DAT_TDM_OP_I_REG
#define SRC6_TDM_OP_I_REG       SRC6_DAT_TDM_OP_I_REG
#define SRC7_TDM_OP_I_REG       SRC7_DAT_TDM_OP_I_REG
#define SRC0_TDM_OP_I_SHIFT     SRC0_DAT_TDM_OP_I_SHIFT
#define SRC1_TDM_OP_I_SHIFT     SRC1_DAT_TDM_OP_I_SHIFT
#define SRC2_TDM_OP_I_SHIFT     SRC2_DAT_TDM_OP_I_SHIFT
#define SRC3_TDM_OP_I_SHIFT     SRC3_DAT_TDM_OP_I_SHIFT
#define SRC4_TDM_OP_I_SHIFT     SRC4_DAT_TDM_OP_I_SHIFT
#define SRC5_TDM_OP_I_SHIFT     SRC5_DAT_TDM_OP_I_SHIFT
#define SRC6_TDM_OP_I_SHIFT     SRC6_DAT_TDM_OP_I_SHIFT
#define SRC7_TDM_OP_I_SHIFT     SRC7_DAT_TDM_OP_I_SHIFT

#define PCG0_EXTTRIG_CLKA_I_GROUP PCG0_EXTCLKA_I_GROUP
#define PCG0_EXTTRIG_CLKB_I_GROUP PCG0_EXTCLKB_I_GROUP
#define PCG0_EXTTRIG_CLKC_I_GROUP PCG0_EXTCLKC_I_GROUP
#define PCG0_EXTTRIG_CLKD_I_GROUP PCG0_EXTCLKD_I_GROUP
#define PCG0_EXTTRIG_CLKA_I_REG   PCG0_EXTCLKA_I_REG
#define PCG0_EXTTRIG_CLKB_I_REG   PCG0_EXTCLKB_I_REG
#define PCG0_EXTTRIG_CLKC_I_REG   PCG0_EXTCLKC_I_REG
#define PCG0_EXTTRIG_CLKD_I_REG   PCG0_EXTCLKD_I_REG

#define SPDIF0_PLLCLK_I_GROUP     GROUP_A
#define SPDIF1_PLLCLK_I_GROUP     GROUP_A2

#define SPDIF0_TX_SYNC_I_GROUP    GROUP_A
#define SPDIF1_TX_SYNC_I_GROUP    GROUP_A2 /* old def21489.h nomenclature */

/*============================================================================*/
/*   Dummy Signals                                                            */
/*   The signals listed below don't exist in the given group but they are     */
/*   required by the preprocessor for evaluating the macros sru_fields and    */
/*   sru_mask. The code assigned to them is arbitrary.                        */
/*============================================================================*/

#define _DUMMY_VALUE 0xffffffff

/* Dummy macro definitions for group A */

#define A_DAI0_CRS_PB04_O          _DUMMY_VALUE
#define A_DAI0_CRS_PB06_O          _DUMMY_VALUE
#define A_DAI0_MISCA0_O            _DUMMY_VALUE
#define A_DAI0_MISCA1_O            _DUMMY_VALUE
#define A_DAI0_MISCA2_O            _DUMMY_VALUE
#define A_DAI0_MISCA3_O            _DUMMY_VALUE
#define A_DAI0_MISCA4_O            _DUMMY_VALUE
#define A_DAI0_MISCA5_O            _DUMMY_VALUE
#define A_DAI0_PB15_O              _DUMMY_VALUE
#define A_DAI0_PB16_O              _DUMMY_VALUE
#define A_MLB0_CLKOUT_O            _DUMMY_VALUE
#define A_PCG0_CRS_CLKC_O          _DUMMY_VALUE
#define A_PCG0_CRS_CLKD_O          _DUMMY_VALUE
#define A_PCG0_CRS_FSC_O           _DUMMY_VALUE
#define A_PCG0_CRS_FSD_O           _DUMMY_VALUE
#define A_PCG0_FSA_O               _DUMMY_VALUE
#define A_PCG0_FSB_O               _DUMMY_VALUE
#define A_SPDIF0_RX_DAT_O          _DUMMY_VALUE
#define A_SPDIF0_RX_FS_O           _DUMMY_VALUE
#define A_SPDIF0_TX_BLKSTART_O     _DUMMY_VALUE
#define A_SPDIF0_TX_O              _DUMMY_VALUE
#define A_SPT0A_FS_O               _DUMMY_VALUE
#define A_SPT0B_FS_O               _DUMMY_VALUE
#define A_SPT0_ACLK_PBEN_O         _DUMMY_VALUE
#define A_SPT0_AD0_O               _DUMMY_VALUE
#define A_SPT0_AD0_PBEN_O          _DUMMY_VALUE
#define A_SPT0_AD1_O               _DUMMY_VALUE
#define A_SPT0_AD1_PBEN_O          _DUMMY_VALUE
#define A_SPT0_AFS_O               _DUMMY_VALUE
#define A_SPT0_AFS_PBEN_O          _DUMMY_VALUE
#define A_SPT0_ATDV_O              _DUMMY_VALUE
#define A_SPT0_ATDV_PBEN_O         _DUMMY_VALUE
#define A_SPT0_BCLK_PBEN_O         _DUMMY_VALUE
#define A_SPT0_BD0_O               _DUMMY_VALUE
#define A_SPT0_BD0_PBEN_O          _DUMMY_VALUE
#define A_SPT0_BD1_O               _DUMMY_VALUE
#define A_SPT0_BD1_PBEN_O          _DUMMY_VALUE
#define A_SPT0_BFS_O               _DUMMY_VALUE
#define A_SPT0_BFS_PBEN_O          _DUMMY_VALUE
#define A_SPT0_BTDV_O              _DUMMY_VALUE
#define A_SPT0_BTDV_PBEN_O         _DUMMY_VALUE
#define A_SPT1A_FS_O               _DUMMY_VALUE
#define A_SPT1B_FS_O               _DUMMY_VALUE
#define A_SPT1_ACLK_PBEN_O         _DUMMY_VALUE
#define A_SPT1_AD0_O               _DUMMY_VALUE
#define A_SPT1_AD0_PBEN_O          _DUMMY_VALUE
#define A_SPT1_AD1_O               _DUMMY_VALUE
#define A_SPT1_AD1_PBEN_O          _DUMMY_VALUE
#define A_SPT1_AFS_O               _DUMMY_VALUE
#define A_SPT1_AFS_PBEN_O          _DUMMY_VALUE
#define A_SPT1_ATDV_O              _DUMMY_VALUE
#define A_SPT1_ATDV_PBEN_O         _DUMMY_VALUE
#define A_SPT1_BCLK_PBEN_O         _DUMMY_VALUE
#define A_SPT1_BD0_O               _DUMMY_VALUE
#define A_SPT1_BD0_PBEN_O          _DUMMY_VALUE
#define A_SPT1_BD1_O               _DUMMY_VALUE
#define A_SPT1_BD1_PBEN_O          _DUMMY_VALUE
#define A_SPT1_BFS_O               _DUMMY_VALUE
#define A_SPT1_BFS_PBEN_O          _DUMMY_VALUE
#define A_SPT1_BTDV_O              _DUMMY_VALUE
#define A_SPT1_BTDV_PBEN_O         _DUMMY_VALUE
#define A_SPT2A_FS_O               _DUMMY_VALUE
#define A_SPT2B_FS_O               _DUMMY_VALUE
#define A_SPT2_ACLK_PBEN_O         _DUMMY_VALUE
#define A_SPT2_AD0_O               _DUMMY_VALUE
#define A_SPT2_AD0_PBEN_O          _DUMMY_VALUE
#define A_SPT2_AD1_O               _DUMMY_VALUE
#define A_SPT2_AD1_PBEN_O          _DUMMY_VALUE
#define A_SPT2_AFS_O               _DUMMY_VALUE
#define A_SPT2_AFS_PBEN_O          _DUMMY_VALUE
#define A_SPT2_ATDV_O              _DUMMY_VALUE
#define A_SPT2_ATDV_PBEN_O         _DUMMY_VALUE
#define A_SPT2_BCLK_PBEN_O         _DUMMY_VALUE
#define A_SPT2_BD0_O               _DUMMY_VALUE
#define A_SPT2_BD0_PBEN_O          _DUMMY_VALUE
#define A_SPT2_BD1_O               _DUMMY_VALUE
#define A_SPT2_BD1_PBEN_O          _DUMMY_VALUE
#define A_SPT2_BFS_O               _DUMMY_VALUE
#define A_SPT2_BFS_PBEN_O          _DUMMY_VALUE
#define A_SPT2_BTDV_O              _DUMMY_VALUE
#define A_SPT2_BTDV_PBEN_O         _DUMMY_VALUE
#define A_SPT3_ACLK_O              _DUMMY_VALUE
#define A_SPT3_ACLK_PBEN_O         _DUMMY_VALUE
#define A_SPT3_AD0_O               _DUMMY_VALUE
#define A_SPT3_AD0_PBEN_O          _DUMMY_VALUE
#define A_SPT3_AD1_O               _DUMMY_VALUE
#define A_SPT3_AD1_PBEN_O          _DUMMY_VALUE
#define A_SPT3_AFS_O               _DUMMY_VALUE
#define A_SPT3_AFS_PBEN_O          _DUMMY_VALUE
#define A_SPT3_ATDV_O              _DUMMY_VALUE
#define A_SPT3_ATDV_PBEN_O         _DUMMY_VALUE
#define A_SPT3_BCLK_O              _DUMMY_VALUE
#define A_SPT3_BCLK_PBEN_O         _DUMMY_VALUE
#define A_SPT3_BD0_O               _DUMMY_VALUE
#define A_SPT3_BD0_PBEN_O          _DUMMY_VALUE
#define A_SPT3_BD1_O               _DUMMY_VALUE
#define A_SPT3_BD1_PBEN_O          _DUMMY_VALUE
#define A_SPT3_BFS_O               _DUMMY_VALUE
#define A_SPT3_BFS_PBEN_O          _DUMMY_VALUE
#define A_SPT3_BTDV_O              _DUMMY_VALUE
#define A_SPT3_BTDV_PBEN_O         _DUMMY_VALUE
#define A_SRC0_DAT_OP_O            _DUMMY_VALUE
#define A_SRC0_TDM_IP_O            _DUMMY_VALUE
#define A_SRC1_DAT_OP_O            _DUMMY_VALUE
#define A_SRC1_TDM_IP_O            _DUMMY_VALUE
#define A_SRC2_DAT_OP_O            _DUMMY_VALUE
#define A_SRC2_TDM_IP_O            _DUMMY_VALUE
#define A_SRC3_CRS_DAT_OP_O        _DUMMY_VALUE
#define A_SRC3_CRS_TDM_IP_O        _DUMMY_VALUE
#define A_SRC3_DAT_OP_O            _DUMMY_VALUE
#define A_SRC3_TDM_IP_O            _DUMMY_VALUE

/* Dummy macro definitions for group B */

#define B_DAI0_CRS_PB03_O          _DUMMY_VALUE
#define B_DAI0_CRS_PB04_O          _DUMMY_VALUE
#define B_DAI0_CRS_PB05_O          _DUMMY_VALUE
#define B_DAI0_CRS_PB06_O          _DUMMY_VALUE
#define B_DAI0_MISCA0_O            _DUMMY_VALUE
#define B_DAI0_MISCA1_O            _DUMMY_VALUE
#define B_DAI0_MISCA2_O            _DUMMY_VALUE
#define B_DAI0_MISCA3_O            _DUMMY_VALUE
#define B_DAI0_MISCA4_O            _DUMMY_VALUE
#define B_DAI0_MISCA5_O            _DUMMY_VALUE
#define B_MLB0_CLKOUT_O            _DUMMY_VALUE
#define B_PCG0_CLKA_O              _DUMMY_VALUE
#define B_PCG0_CLKB_O              _DUMMY_VALUE
#define B_PCG0_CRS_CLKC_O          _DUMMY_VALUE
#define B_PCG0_CRS_CLKD_O          _DUMMY_VALUE
#define B_PCG0_CRS_FSC_O           _DUMMY_VALUE
#define B_PCG0_CRS_FSD_O           _DUMMY_VALUE
#define B_PCG0_FSA_O               _DUMMY_VALUE
#define B_PCG0_FSB_O               _DUMMY_VALUE
#define B_SPDIF0_RX_CLK_O          _DUMMY_VALUE
#define B_SPDIF0_RX_FS_O           _DUMMY_VALUE
#define B_SPDIF0_RX_TDMCLK_O       _DUMMY_VALUE
#define B_SPDIF0_TX_BLKSTART_O     _DUMMY_VALUE
#define B_SPT0A_FS_O               _DUMMY_VALUE
#define B_SPT0B_FS_O               _DUMMY_VALUE
#define B_SPT0_ACLK_O              _DUMMY_VALUE
#define B_SPT0_ACLK_PBEN_O         _DUMMY_VALUE
#define B_SPT0_AD0_PBEN_O          _DUMMY_VALUE
#define B_SPT0_AD1_PBEN_O          _DUMMY_VALUE
#define B_SPT0_AFS_O               _DUMMY_VALUE
#define B_SPT0_AFS_PBEN_O          _DUMMY_VALUE
#define B_SPT0_ATDV_O              _DUMMY_VALUE
#define B_SPT0_ATDV_PBEN_O         _DUMMY_VALUE
#define B_SPT0_BCLK_O              _DUMMY_VALUE
#define B_SPT0_BCLK_PBEN_O         _DUMMY_VALUE
#define B_SPT0_BD0_PBEN_O          _DUMMY_VALUE
#define B_SPT0_BD1_PBEN_O          _DUMMY_VALUE
#define B_SPT0_BFS_O               _DUMMY_VALUE
#define B_SPT0_BFS_PBEN_O          _DUMMY_VALUE
#define B_SPT0_BTDV_O              _DUMMY_VALUE
#define B_SPT0_BTDV_PBEN_O         _DUMMY_VALUE
#define B_SPT1A_FS_O               _DUMMY_VALUE
#define B_SPT1B_FS_O               _DUMMY_VALUE
#define B_SPT1_ACLK_O              _DUMMY_VALUE
#define B_SPT1_ACLK_PBEN_O         _DUMMY_VALUE
#define B_SPT1_AD0_PBEN_O          _DUMMY_VALUE
#define B_SPT1_AD1_PBEN_O          _DUMMY_VALUE
#define B_SPT1_AFS_O               _DUMMY_VALUE
#define B_SPT1_AFS_PBEN_O          _DUMMY_VALUE
#define B_SPT1_ATDV_O              _DUMMY_VALUE
#define B_SPT1_ATDV_PBEN_O         _DUMMY_VALUE
#define B_SPT1_BCLK_O              _DUMMY_VALUE
#define B_SPT1_BCLK_PBEN_O         _DUMMY_VALUE
#define B_SPT1_BD0_PBEN_O          _DUMMY_VALUE
#define B_SPT1_BD1_PBEN_O          _DUMMY_VALUE
#define B_SPT1_BFS_O               _DUMMY_VALUE
#define B_SPT1_BFS_PBEN_O          _DUMMY_VALUE
#define B_SPT1_BTDV_O              _DUMMY_VALUE
#define B_SPT1_BTDV_PBEN_O         _DUMMY_VALUE
#define B_SPT2A_FS_O               _DUMMY_VALUE
#define B_SPT2B_FS_O               _DUMMY_VALUE
#define B_SPT2_ACLK_O              _DUMMY_VALUE
#define B_SPT2_ACLK_PBEN_O         _DUMMY_VALUE
#define B_SPT2_AD0_PBEN_O          _DUMMY_VALUE
#define B_SPT2_AD1_PBEN_O          _DUMMY_VALUE
#define B_SPT2_AFS_O               _DUMMY_VALUE
#define B_SPT2_AFS_PBEN_O          _DUMMY_VALUE
#define B_SPT2_ATDV_O              _DUMMY_VALUE
#define B_SPT2_ATDV_PBEN_O         _DUMMY_VALUE
#define B_SPT2_BCLK_O              _DUMMY_VALUE
#define B_SPT2_BCLK_PBEN_O         _DUMMY_VALUE
#define B_SPT2_BD0_PBEN_O          _DUMMY_VALUE
#define B_SPT2_BD1_PBEN_O          _DUMMY_VALUE
#define B_SPT2_BFS_O               _DUMMY_VALUE
#define B_SPT2_BFS_PBEN_O          _DUMMY_VALUE
#define B_SPT2_BTDV_O              _DUMMY_VALUE
#define B_SPT2_BTDV_PBEN_O         _DUMMY_VALUE
#define B_SPT3_ACLK_O              _DUMMY_VALUE
#define B_SPT3_ACLK_PBEN_O         _DUMMY_VALUE
#define B_SPT3_AD0_PBEN_O          _DUMMY_VALUE
#define B_SPT3_AD1_PBEN_O          _DUMMY_VALUE
#define B_SPT3_AFS_O               _DUMMY_VALUE
#define B_SPT3_AFS_PBEN_O          _DUMMY_VALUE
#define B_SPT3_ATDV_O              _DUMMY_VALUE
#define B_SPT3_ATDV_PBEN_O         _DUMMY_VALUE
#define B_SPT3_BCLK_O              _DUMMY_VALUE
#define B_SPT3_BCLK_PBEN_O         _DUMMY_VALUE
#define B_SPT3_BD0_PBEN_O          _DUMMY_VALUE
#define B_SPT3_BD1_PBEN_O          _DUMMY_VALUE
#define B_SPT3_BFS_O               _DUMMY_VALUE
#define B_SPT3_BFS_PBEN_O          _DUMMY_VALUE
#define B_SPT3_BTDV_O              _DUMMY_VALUE
#define B_SPT3_BTDV_PBEN_O         _DUMMY_VALUE

/* Dummy macro definitions for group C */

#define C_DAI0_CRS_PB03_O          _DUMMY_VALUE
#define C_DAI0_CRS_PB05_O          _DUMMY_VALUE
#define C_DAI0_MISCA0_O            _DUMMY_VALUE
#define C_DAI0_MISCA1_O            _DUMMY_VALUE
#define C_DAI0_MISCA2_O            _DUMMY_VALUE
#define C_DAI0_MISCA3_O            _DUMMY_VALUE
#define C_DAI0_MISCA4_O            _DUMMY_VALUE
#define C_DAI0_MISCA5_O            _DUMMY_VALUE
#define C_DAI0_PB15_O              _DUMMY_VALUE
#define C_DAI0_PB16_O              _DUMMY_VALUE
#define C_MLB0_CLKOUT_O            _DUMMY_VALUE
#define C_PCG0_CLKA_O              _DUMMY_VALUE
#define C_PCG0_CLKB_O              _DUMMY_VALUE
#define C_PCG0_CRS_CLKC_O          _DUMMY_VALUE
#define C_PCG0_CRS_CLKD_O          _DUMMY_VALUE
#define C_PCG0_CRS_FSC_O           _DUMMY_VALUE
#define C_PCG0_CRS_FSD_O           _DUMMY_VALUE
#define C_SPDIF0_RX_CLK_O          _DUMMY_VALUE
#define C_SPDIF0_RX_DAT_O          _DUMMY_VALUE
#define C_SPDIF0_RX_TDMCLK_O       _DUMMY_VALUE
#define C_SPDIF0_TX_BLKSTART_O     _DUMMY_VALUE
#define C_SPDIF0_TX_O              _DUMMY_VALUE
#define C_SPT0A_FS_O               _DUMMY_VALUE
#define C_SPT0B_FS_O               _DUMMY_VALUE
#define C_SPT0_ACLK_O              _DUMMY_VALUE
#define C_SPT0_ACLK_PBEN_O         _DUMMY_VALUE
#define C_SPT0_AD0_O               _DUMMY_VALUE
#define C_SPT0_AD0_PBEN_O          _DUMMY_VALUE
#define C_SPT0_AD1_O               _DUMMY_VALUE
#define C_SPT0_AD1_PBEN_O          _DUMMY_VALUE
#define C_SPT0_AFS_PBEN_O          _DUMMY_VALUE
#define C_SPT0_ATDV_O              _DUMMY_VALUE
#define C_SPT0_ATDV_PBEN_O         _DUMMY_VALUE
#define C_SPT0_BCLK_O              _DUMMY_VALUE
#define C_SPT0_BCLK_PBEN_O         _DUMMY_VALUE
#define C_SPT0_BD0_O               _DUMMY_VALUE
#define C_SPT0_BD0_PBEN_O          _DUMMY_VALUE
#define C_SPT0_BD1_O               _DUMMY_VALUE
#define C_SPT0_BD1_PBEN_O          _DUMMY_VALUE
#define C_SPT0_BFS_PBEN_O          _DUMMY_VALUE
#define C_SPT0_BTDV_O              _DUMMY_VALUE
#define C_SPT0_BTDV_PBEN_O         _DUMMY_VALUE
#define C_SPT1A_FS_O               _DUMMY_VALUE
#define C_SPT1B_FS_O               _DUMMY_VALUE
#define C_SPT1_ACLK_O              _DUMMY_VALUE
#define C_SPT1_ACLK_PBEN_O         _DUMMY_VALUE
#define C_SPT1_AD0_O               _DUMMY_VALUE
#define C_SPT1_AD0_PBEN_O          _DUMMY_VALUE
#define C_SPT1_AD1_O               _DUMMY_VALUE
#define C_SPT1_AD1_PBEN_O          _DUMMY_VALUE
#define C_SPT1_AFS_PBEN_O          _DUMMY_VALUE
#define C_SPT1_ATDV_O              _DUMMY_VALUE
#define C_SPT1_ATDV_PBEN_O         _DUMMY_VALUE
#define C_SPT1_BCLK_O              _DUMMY_VALUE
#define C_SPT1_BCLK_PBEN_O         _DUMMY_VALUE
#define C_SPT1_BD0_O               _DUMMY_VALUE
#define C_SPT1_BD0_PBEN_O          _DUMMY_VALUE
#define C_SPT1_BD1_O               _DUMMY_VALUE
#define C_SPT1_BD1_PBEN_O          _DUMMY_VALUE
#define C_SPT1_BFS_PBEN_O          _DUMMY_VALUE
#define C_SPT1_BTDV_O              _DUMMY_VALUE
#define C_SPT1_BTDV_PBEN_O         _DUMMY_VALUE
#define C_SPT2A_FS_O               _DUMMY_VALUE
#define C_SPT2B_FS_O               _DUMMY_VALUE
#define C_SPT2_ACLK_O              _DUMMY_VALUE
#define C_SPT2_ACLK_PBEN_O         _DUMMY_VALUE
#define C_SPT2_AD0_O               _DUMMY_VALUE
#define C_SPT2_AD0_PBEN_O          _DUMMY_VALUE
#define C_SPT2_AD1_O               _DUMMY_VALUE
#define C_SPT2_AD1_PBEN_O          _DUMMY_VALUE
#define C_SPT2_AFS_PBEN_O          _DUMMY_VALUE
#define C_SPT2_ATDV_O              _DUMMY_VALUE
#define C_SPT2_ATDV_PBEN_O         _DUMMY_VALUE
#define C_SPT2_BCLK_O              _DUMMY_VALUE
#define C_SPT2_BCLK_PBEN_O         _DUMMY_VALUE
#define C_SPT2_BD0_O               _DUMMY_VALUE
#define C_SPT2_BD0_PBEN_O          _DUMMY_VALUE
#define C_SPT2_BD1_O               _DUMMY_VALUE
#define C_SPT2_BD1_PBEN_O          _DUMMY_VALUE
#define C_SPT2_BFS_PBEN_O          _DUMMY_VALUE
#define C_SPT2_BTDV_O              _DUMMY_VALUE
#define C_SPT2_BTDV_PBEN_O         _DUMMY_VALUE
#define C_SPT3_ACLK_O              _DUMMY_VALUE
#define C_SPT3_ACLK_PBEN_O         _DUMMY_VALUE
#define C_SPT3_AD0_O               _DUMMY_VALUE
#define C_SPT3_AD0_PBEN_O          _DUMMY_VALUE
#define C_SPT3_AD1_O               _DUMMY_VALUE
#define C_SPT3_AD1_PBEN_O          _DUMMY_VALUE
#define C_SPT3_AFS_O               _DUMMY_VALUE
#define C_SPT3_AFS_PBEN_O          _DUMMY_VALUE
#define C_SPT3_ATDV_O              _DUMMY_VALUE
#define C_SPT3_ATDV_PBEN_O         _DUMMY_VALUE
#define C_SPT3_BCLK_O              _DUMMY_VALUE
#define C_SPT3_BCLK_PBEN_O         _DUMMY_VALUE
#define C_SPT3_BD0_O               _DUMMY_VALUE
#define C_SPT3_BD0_PBEN_O          _DUMMY_VALUE
#define C_SPT3_BD1_O               _DUMMY_VALUE
#define C_SPT3_BD1_PBEN_O          _DUMMY_VALUE
#define C_SPT3_BFS_O               _DUMMY_VALUE
#define C_SPT3_BFS_PBEN_O          _DUMMY_VALUE
#define C_SPT3_BTDV_O              _DUMMY_VALUE
#define C_SPT3_BTDV_PBEN_O         _DUMMY_VALUE
#define C_SRC0_DAT_OP_O            _DUMMY_VALUE
#define C_SRC0_TDM_IP_O            _DUMMY_VALUE
#define C_SRC1_DAT_OP_O            _DUMMY_VALUE
#define C_SRC1_TDM_IP_O            _DUMMY_VALUE
#define C_SRC2_DAT_OP_O            _DUMMY_VALUE
#define C_SRC2_TDM_IP_O            _DUMMY_VALUE
#define C_SRC3_CRS_DAT_OP_O        _DUMMY_VALUE
#define C_SRC3_CRS_TDM_IP_O        _DUMMY_VALUE
#define C_SRC3_DAT_OP_O            _DUMMY_VALUE
#define C_SRC3_TDM_IP_O            _DUMMY_VALUE

/* Dummy macro definitions for group D */

#define D_DAI0_MISCA0_O            _DUMMY_VALUE
#define D_DAI0_MISCA1_O            _DUMMY_VALUE
#define D_DAI0_MISCA2_O            _DUMMY_VALUE
#define D_DAI0_MISCA3_O            _DUMMY_VALUE
#define D_DAI0_MISCA4_O            _DUMMY_VALUE
#define D_DAI0_MISCA5_O            _DUMMY_VALUE
#define D_SPT0A_FS_O               _DUMMY_VALUE
#define D_SPT0B_FS_O               _DUMMY_VALUE
#define D_SPT0_ACLK_PBEN_O         _DUMMY_VALUE
#define D_SPT0_AD0_PBEN_O          _DUMMY_VALUE
#define D_SPT0_AD1_PBEN_O          _DUMMY_VALUE
#define D_SPT0_AFS_PBEN_O          _DUMMY_VALUE
#define D_SPT0_ATDV_PBEN_O         _DUMMY_VALUE
#define D_SPT0_BCLK_PBEN_O         _DUMMY_VALUE
#define D_SPT0_BD0_PBEN_O          _DUMMY_VALUE
#define D_SPT0_BD1_PBEN_O          _DUMMY_VALUE
#define D_SPT0_BFS_PBEN_O          _DUMMY_VALUE
#define D_SPT0_BTDV_PBEN_O         _DUMMY_VALUE
#define D_SPT1A_FS_O               _DUMMY_VALUE
#define D_SPT1B_FS_O               _DUMMY_VALUE
#define D_SPT1_ACLK_PBEN_O         _DUMMY_VALUE
#define D_SPT1_AD0_PBEN_O          _DUMMY_VALUE
#define D_SPT1_AD1_PBEN_O          _DUMMY_VALUE
#define D_SPT1_AFS_PBEN_O          _DUMMY_VALUE
#define D_SPT1_ATDV_PBEN_O         _DUMMY_VALUE
#define D_SPT1_BCLK_PBEN_O         _DUMMY_VALUE
#define D_SPT1_BD0_PBEN_O          _DUMMY_VALUE
#define D_SPT1_BD1_PBEN_O          _DUMMY_VALUE
#define D_SPT1_BFS_PBEN_O          _DUMMY_VALUE
#define D_SPT1_BTDV_PBEN_O         _DUMMY_VALUE
#define D_SPT2A_FS_O               _DUMMY_VALUE
#define D_SPT2B_FS_O               _DUMMY_VALUE
#define D_SPT2_ACLK_PBEN_O         _DUMMY_VALUE
#define D_SPT2_AD0_PBEN_O          _DUMMY_VALUE
#define D_SPT2_AD1_PBEN_O          _DUMMY_VALUE
#define D_SPT2_AFS_PBEN_O          _DUMMY_VALUE
#define D_SPT2_ATDV_PBEN_O         _DUMMY_VALUE
#define D_SPT2_BCLK_PBEN_O         _DUMMY_VALUE
#define D_SPT2_BD0_PBEN_O          _DUMMY_VALUE
#define D_SPT2_BD1_PBEN_O          _DUMMY_VALUE
#define D_SPT2_BFS_PBEN_O          _DUMMY_VALUE
#define D_SPT2_BTDV_PBEN_O         _DUMMY_VALUE
#define D_SPT3_ACLK_PBEN_O         _DUMMY_VALUE
#define D_SPT3_AD0_PBEN_O          _DUMMY_VALUE
#define D_SPT3_AD1_PBEN_O          _DUMMY_VALUE
#define D_SPT3_AFS_PBEN_O          _DUMMY_VALUE
#define D_SPT3_ATDV_PBEN_O         _DUMMY_VALUE
#define D_SPT3_BCLK_PBEN_O         _DUMMY_VALUE
#define D_SPT3_BD0_PBEN_O          _DUMMY_VALUE
#define D_SPT3_BD1_PBEN_O          _DUMMY_VALUE
#define D_SPT3_BFS_PBEN_O          _DUMMY_VALUE
#define D_SPT3_BTDV_PBEN_O         _DUMMY_VALUE
#define D_SRC0_TDM_IP_O            _DUMMY_VALUE
#define D_SRC1_TDM_IP_O            _DUMMY_VALUE
#define D_SRC2_TDM_IP_O            _DUMMY_VALUE
#define D_SRC3_CRS_DAT_OP_O        _DUMMY_VALUE
#define D_SRC3_CRS_TDM_IP_O        _DUMMY_VALUE
#define D_SRC3_TDM_IP_O            _DUMMY_VALUE

/* Dummy macro definitions for group E */

#define E_DAI0_CRS_PB03_O          _DUMMY_VALUE
#define E_DAI0_CRS_PB04_O          _DUMMY_VALUE
#define E_DAI0_CRS_PB05_O          _DUMMY_VALUE
#define E_DAI0_CRS_PB06_O          _DUMMY_VALUE
#define E_DAI0_MISCA0_O            _DUMMY_VALUE
#define E_DAI0_MISCA1_O            _DUMMY_VALUE
#define E_DAI0_MISCA2_O            _DUMMY_VALUE
#define E_DAI0_MISCA3_O            _DUMMY_VALUE
#define E_DAI0_MISCA4_O            _DUMMY_VALUE
#define E_DAI0_MISCA5_O            _DUMMY_VALUE
#define E_MLB0_CLKOUT_O            _DUMMY_VALUE
#define E_PCG0_CLKA_O              _DUMMY_VALUE
#define E_PCG0_CRS_CLKC_O          _DUMMY_VALUE
#define E_PCG0_CRS_CLKD_O          _DUMMY_VALUE
#define E_PCG0_CRS_FSC_O           _DUMMY_VALUE
#define E_PCG0_CRS_FSD_O           _DUMMY_VALUE
#define E_SPDIF0_RX_CLK_O          _DUMMY_VALUE
#define E_SPDIF0_RX_DAT_O          _DUMMY_VALUE
#define E_SPDIF0_RX_FS_O           _DUMMY_VALUE
#define E_SPDIF0_RX_TDMCLK_O       _DUMMY_VALUE
#define E_SPDIF0_TX_O              _DUMMY_VALUE
#define E_SPT0_ACLK_O              _DUMMY_VALUE
#define E_SPT0_ACLK_PBEN_O         _DUMMY_VALUE
#define E_SPT0_AD0_O               _DUMMY_VALUE
#define E_SPT0_AD0_PBEN_O          _DUMMY_VALUE
#define E_SPT0_AD1_O               _DUMMY_VALUE
#define E_SPT0_AD1_PBEN_O          _DUMMY_VALUE
#define E_SPT0_AFS_PBEN_O          _DUMMY_VALUE
#define E_SPT0_ATDV_O              _DUMMY_VALUE
#define E_SPT0_ATDV_PBEN_O         _DUMMY_VALUE
#define E_SPT0_BCLK_O              _DUMMY_VALUE
#define E_SPT0_BCLK_PBEN_O         _DUMMY_VALUE
#define E_SPT0_BD0_O               _DUMMY_VALUE
#define E_SPT0_BD0_PBEN_O          _DUMMY_VALUE
#define E_SPT0_BD1_O               _DUMMY_VALUE
#define E_SPT0_BD1_PBEN_O          _DUMMY_VALUE
#define E_SPT0_BFS_PBEN_O          _DUMMY_VALUE
#define E_SPT0_BTDV_O              _DUMMY_VALUE
#define E_SPT0_BTDV_PBEN_O         _DUMMY_VALUE
#define E_SPT1_ACLK_O              _DUMMY_VALUE
#define E_SPT1_ACLK_PBEN_O         _DUMMY_VALUE
#define E_SPT1_AD0_O               _DUMMY_VALUE
#define E_SPT1_AD0_PBEN_O          _DUMMY_VALUE
#define E_SPT1_AD1_O               _DUMMY_VALUE
#define E_SPT1_AD1_PBEN_O          _DUMMY_VALUE
#define E_SPT1_AFS_PBEN_O          _DUMMY_VALUE
#define E_SPT1_ATDV_O              _DUMMY_VALUE
#define E_SPT1_ATDV_PBEN_O         _DUMMY_VALUE
#define E_SPT1_BCLK_O              _DUMMY_VALUE
#define E_SPT1_BCLK_PBEN_O         _DUMMY_VALUE
#define E_SPT1_BD0_O               _DUMMY_VALUE
#define E_SPT1_BD0_PBEN_O          _DUMMY_VALUE
#define E_SPT1_BD1_O               _DUMMY_VALUE
#define E_SPT1_BD1_PBEN_O          _DUMMY_VALUE
#define E_SPT1_BFS_PBEN_O          _DUMMY_VALUE
#define E_SPT1_BTDV_O              _DUMMY_VALUE
#define E_SPT1_BTDV_PBEN_O         _DUMMY_VALUE
#define E_SPT2_ACLK_O              _DUMMY_VALUE
#define E_SPT2_ACLK_PBEN_O         _DUMMY_VALUE
#define E_SPT2_AD0_O               _DUMMY_VALUE
#define E_SPT2_AD0_PBEN_O          _DUMMY_VALUE
#define E_SPT2_AD1_O               _DUMMY_VALUE
#define E_SPT2_AD1_PBEN_O          _DUMMY_VALUE
#define E_SPT2_AFS_PBEN_O          _DUMMY_VALUE
#define E_SPT2_ATDV_O              _DUMMY_VALUE
#define E_SPT2_ATDV_PBEN_O         _DUMMY_VALUE
#define E_SPT2_BCLK_O              _DUMMY_VALUE
#define E_SPT2_BCLK_PBEN_O         _DUMMY_VALUE
#define E_SPT2_BD0_O               _DUMMY_VALUE
#define E_SPT2_BD0_PBEN_O          _DUMMY_VALUE
#define E_SPT2_BD1_O               _DUMMY_VALUE
#define E_SPT2_BD1_PBEN_O          _DUMMY_VALUE
#define E_SPT2_BFS_PBEN_O          _DUMMY_VALUE
#define E_SPT2_BTDV_O              _DUMMY_VALUE
#define E_SPT2_BTDV_PBEN_O         _DUMMY_VALUE
#define E_SPT3_ACLK_O              _DUMMY_VALUE
#define E_SPT3_ACLK_PBEN_O         _DUMMY_VALUE
#define E_SPT3_AD0_O               _DUMMY_VALUE
#define E_SPT3_AD0_PBEN_O          _DUMMY_VALUE
#define E_SPT3_AD1_O               _DUMMY_VALUE
#define E_SPT3_AD1_PBEN_O          _DUMMY_VALUE
#define E_SPT3_AFS_O               _DUMMY_VALUE
#define E_SPT3_AFS_PBEN_O          _DUMMY_VALUE
#define E_SPT3_ATDV_O              _DUMMY_VALUE
#define E_SPT3_ATDV_PBEN_O         _DUMMY_VALUE
#define E_SPT3_BCLK_O              _DUMMY_VALUE
#define E_SPT3_BCLK_PBEN_O         _DUMMY_VALUE
#define E_SPT3_BD0_O               _DUMMY_VALUE
#define E_SPT3_BD0_PBEN_O          _DUMMY_VALUE
#define E_SPT3_BD1_O               _DUMMY_VALUE
#define E_SPT3_BD1_PBEN_O          _DUMMY_VALUE
#define E_SPT3_BFS_O               _DUMMY_VALUE
#define E_SPT3_BFS_PBEN_O          _DUMMY_VALUE
#define E_SPT3_BTDV_O              _DUMMY_VALUE
#define E_SPT3_BTDV_PBEN_O         _DUMMY_VALUE
#define E_SRC0_DAT_OP_O            _DUMMY_VALUE
#define E_SRC0_TDM_IP_O            _DUMMY_VALUE
#define E_SRC1_DAT_OP_O            _DUMMY_VALUE
#define E_SRC1_TDM_IP_O            _DUMMY_VALUE
#define E_SRC2_DAT_OP_O            _DUMMY_VALUE
#define E_SRC2_TDM_IP_O            _DUMMY_VALUE
#define E_SRC3_CRS_DAT_OP_O        _DUMMY_VALUE
#define E_SRC3_CRS_TDM_IP_O        _DUMMY_VALUE
#define E_SRC3_DAT_OP_O            _DUMMY_VALUE
#define E_SRC3_TDM_IP_O            _DUMMY_VALUE

/* Dummy macro definitions for group F */

#define F_DAI0_CRS_PB03_O          _DUMMY_VALUE
#define F_DAI0_CRS_PB04_O          _DUMMY_VALUE
#define F_DAI0_CRS_PB05_O          _DUMMY_VALUE
#define F_DAI0_CRS_PB06_O          _DUMMY_VALUE
#define F_DAI0_PB01_O              _DUMMY_VALUE
#define F_DAI0_PB02_O              _DUMMY_VALUE
#define F_DAI0_PB03_O              _DUMMY_VALUE
#define F_DAI0_PB04_O              _DUMMY_VALUE
#define F_DAI0_PB05_O              _DUMMY_VALUE
#define F_DAI0_PB06_O              _DUMMY_VALUE
#define F_DAI0_PB07_O              _DUMMY_VALUE
#define F_DAI0_PB08_O              _DUMMY_VALUE
#define F_DAI0_PB09_O              _DUMMY_VALUE
#define F_DAI0_PB10_O              _DUMMY_VALUE
#define F_DAI0_PB11_O              _DUMMY_VALUE
#define F_DAI0_PB12_O              _DUMMY_VALUE
#define F_DAI0_PB13_O              _DUMMY_VALUE
#define F_DAI0_PB14_O              _DUMMY_VALUE
#define F_DAI0_PB15_O              _DUMMY_VALUE
#define F_DAI0_PB16_O              _DUMMY_VALUE
#define F_DAI0_PB17_O              _DUMMY_VALUE
#define F_DAI0_PB18_O              _DUMMY_VALUE
#define F_DAI0_PB19_O              _DUMMY_VALUE
#define F_DAI0_PB20_O              _DUMMY_VALUE
#define F_MLB0_CLKOUT_O            _DUMMY_VALUE
#define F_PCG0_CLKA_O              _DUMMY_VALUE
#define F_PCG0_CLKB_O              _DUMMY_VALUE
#define F_PCG0_CRS_CLKC_O          _DUMMY_VALUE
#define F_PCG0_CRS_CLKD_O          _DUMMY_VALUE
#define F_PCG0_CRS_FSC_O           _DUMMY_VALUE
#define F_PCG0_CRS_FSD_O           _DUMMY_VALUE
#define F_PCG0_FSA_O               _DUMMY_VALUE
#define F_PCG0_FSB_O               _DUMMY_VALUE
#define F_SPDIF0_RX_CLK_O          _DUMMY_VALUE
#define F_SPDIF0_RX_DAT_O          _DUMMY_VALUE
#define F_SPDIF0_RX_FS_O           _DUMMY_VALUE
#define F_SPDIF0_RX_TDMCLK_O       _DUMMY_VALUE
#define F_SPDIF0_TX_BLKSTART_O     _DUMMY_VALUE
#define F_SPDIF0_TX_O              _DUMMY_VALUE
#define F_SPT0A_FS_O               _DUMMY_VALUE
#define F_SPT0B_FS_O               _DUMMY_VALUE
#define F_SPT0_ACLK_O              _DUMMY_VALUE
#define F_SPT0_AD0_O               _DUMMY_VALUE
#define F_SPT0_AD1_O               _DUMMY_VALUE
#define F_SPT0_AFS_O               _DUMMY_VALUE
#define F_SPT0_ATDV_O              _DUMMY_VALUE
#define F_SPT0_BCLK_O              _DUMMY_VALUE
#define F_SPT0_BD0_O               _DUMMY_VALUE
#define F_SPT0_BD1_O               _DUMMY_VALUE
#define F_SPT0_BFS_O               _DUMMY_VALUE
#define F_SPT0_BTDV_O              _DUMMY_VALUE
#define F_SPT1A_FS_O               _DUMMY_VALUE
#define F_SPT1B_FS_O               _DUMMY_VALUE
#define F_SPT1_ACLK_O              _DUMMY_VALUE
#define F_SPT1_AD0_O               _DUMMY_VALUE
#define F_SPT1_AD1_O               _DUMMY_VALUE
#define F_SPT1_AFS_O               _DUMMY_VALUE
#define F_SPT1_ATDV_O              _DUMMY_VALUE
#define F_SPT1_BCLK_O              _DUMMY_VALUE
#define F_SPT1_BD0_O               _DUMMY_VALUE
#define F_SPT1_BD1_O               _DUMMY_VALUE
#define F_SPT1_BFS_O               _DUMMY_VALUE
#define F_SPT1_BTDV_O              _DUMMY_VALUE
#define F_SPT2A_FS_O               _DUMMY_VALUE
#define F_SPT2B_FS_O               _DUMMY_VALUE
#define F_SPT2_ACLK_O              _DUMMY_VALUE
#define F_SPT2_AD0_O               _DUMMY_VALUE
#define F_SPT2_AD1_O               _DUMMY_VALUE
#define F_SPT2_AFS_O               _DUMMY_VALUE
#define F_SPT2_ATDV_O              _DUMMY_VALUE
#define F_SPT2_BCLK_O              _DUMMY_VALUE
#define F_SPT2_BD0_O               _DUMMY_VALUE
#define F_SPT2_BD1_O               _DUMMY_VALUE
#define F_SPT2_BFS_O               _DUMMY_VALUE
#define F_SPT2_BTDV_O              _DUMMY_VALUE
#define F_SPT3_ACLK_O              _DUMMY_VALUE
#define F_SPT3_AD0_O               _DUMMY_VALUE
#define F_SPT3_AD1_O               _DUMMY_VALUE
#define F_SPT3_AFS_O               _DUMMY_VALUE
#define F_SPT3_ATDV_O              _DUMMY_VALUE
#define F_SPT3_BCLK_O              _DUMMY_VALUE
#define F_SPT3_BD0_O               _DUMMY_VALUE
#define F_SPT3_BD1_O               _DUMMY_VALUE
#define F_SPT3_BFS_O               _DUMMY_VALUE
#define F_SPT3_BTDV_O              _DUMMY_VALUE
#define F_SRC0_DAT_OP_O            _DUMMY_VALUE
#define F_SRC0_TDM_IP_O            _DUMMY_VALUE
#define F_SRC1_DAT_OP_O            _DUMMY_VALUE
#define F_SRC1_TDM_IP_O            _DUMMY_VALUE
#define F_SRC2_DAT_OP_O            _DUMMY_VALUE
#define F_SRC2_TDM_IP_O            _DUMMY_VALUE
#define F_SRC3_CRS_DAT_OP_O        _DUMMY_VALUE
#define F_SRC3_CRS_TDM_IP_O        _DUMMY_VALUE
#define F_SRC3_DAT_OP_O            _DUMMY_VALUE
#define F_SRC3_TDM_IP_O            _DUMMY_VALUE

/* Dummy macro definitions for group G */

#define G_DAI0_CRS_PB03_O          _DUMMY_VALUE
#define G_DAI0_CRS_PB04_O          _DUMMY_VALUE
#define G_DAI0_CRS_PB05_O          _DUMMY_VALUE
#define G_DAI0_CRS_PB06_O          _DUMMY_VALUE
#define G_DAI0_MISCA0_O            _DUMMY_VALUE
#define G_DAI0_MISCA1_O            _DUMMY_VALUE
#define G_DAI0_MISCA2_O            _DUMMY_VALUE
#define G_DAI0_MISCA3_O            _DUMMY_VALUE
#define G_DAI0_MISCA4_O            _DUMMY_VALUE
#define G_DAI0_MISCA5_O            _DUMMY_VALUE
#define G_DAI0_PB01_O              _DUMMY_VALUE
#define G_DAI0_PB02_O              _DUMMY_VALUE
#define G_DAI0_PB03_O              _DUMMY_VALUE
#define G_DAI0_PB04_O              _DUMMY_VALUE
#define G_DAI0_PB05_O              _DUMMY_VALUE
#define G_DAI0_PB06_O              _DUMMY_VALUE
#define G_DAI0_PB07_O              _DUMMY_VALUE
#define G_DAI0_PB08_O              _DUMMY_VALUE
#define G_DAI0_PB09_O              _DUMMY_VALUE
#define G_DAI0_PB10_O              _DUMMY_VALUE
#define G_DAI0_PB11_O              _DUMMY_VALUE
#define G_DAI0_PB12_O              _DUMMY_VALUE
#define G_DAI0_PB13_O              _DUMMY_VALUE
#define G_DAI0_PB14_O              _DUMMY_VALUE
#define G_DAI0_PB15_O              _DUMMY_VALUE
#define G_DAI0_PB16_O              _DUMMY_VALUE
#define G_DAI0_PB17_O              _DUMMY_VALUE
#define G_DAI0_PB18_O              _DUMMY_VALUE
#define G_DAI0_PB19_O              _DUMMY_VALUE
#define G_DAI0_PB20_O              _DUMMY_VALUE
#define G_MLB0_CLKOUT_O            _DUMMY_VALUE
#define G_PCG0_CLKA_O              _DUMMY_VALUE
#define G_PCG0_CLKB_O              _DUMMY_VALUE
#define G_PCG0_CRS_CLKC_O          _DUMMY_VALUE
#define G_PCG0_CRS_CLKD_O          _DUMMY_VALUE
#define G_PCG0_CRS_FSC_O           _DUMMY_VALUE
#define G_PCG0_CRS_FSD_O           _DUMMY_VALUE
#define G_PCG0_FSA_O               _DUMMY_VALUE
#define G_PCG0_FSB_O               _DUMMY_VALUE
#define G_SPDIF0_RX_CLK_O          _DUMMY_VALUE
#define G_SPDIF0_RX_DAT_O          _DUMMY_VALUE
#define G_SPDIF0_RX_FS_O           _DUMMY_VALUE
#define G_SPDIF0_RX_TDMCLK_O       _DUMMY_VALUE
#define G_SPDIF0_TX_BLKSTART_O     _DUMMY_VALUE
#define G_SPDIF0_TX_O              _DUMMY_VALUE
#define G_SPT0A_FS_O               _DUMMY_VALUE
#define G_SPT0B_FS_O               _DUMMY_VALUE
#define G_SPT0_ACLK_O              _DUMMY_VALUE
#define G_SPT0_ACLK_PBEN_O         _DUMMY_VALUE
#define G_SPT0_AD0_O               _DUMMY_VALUE
#define G_SPT0_AD0_PBEN_O          _DUMMY_VALUE
#define G_SPT0_AD1_O               _DUMMY_VALUE
#define G_SPT0_AD1_PBEN_O          _DUMMY_VALUE
#define G_SPT0_AFS_O               _DUMMY_VALUE
#define G_SPT0_AFS_PBEN_O          _DUMMY_VALUE
#define G_SPT0_ATDV_O              _DUMMY_VALUE
#define G_SPT0_ATDV_PBEN_O         _DUMMY_VALUE
#define G_SPT0_BCLK_O              _DUMMY_VALUE
#define G_SPT0_BCLK_PBEN_O         _DUMMY_VALUE
#define G_SPT0_BD0_O               _DUMMY_VALUE
#define G_SPT0_BD0_PBEN_O          _DUMMY_VALUE
#define G_SPT0_BD1_O               _DUMMY_VALUE
#define G_SPT0_BD1_PBEN_O          _DUMMY_VALUE
#define G_SPT0_BFS_O               _DUMMY_VALUE
#define G_SPT0_BFS_PBEN_O          _DUMMY_VALUE
#define G_SPT0_BTDV_O              _DUMMY_VALUE
#define G_SPT0_BTDV_PBEN_O         _DUMMY_VALUE
#define G_SPT1A_FS_O               _DUMMY_VALUE
#define G_SPT1B_FS_O               _DUMMY_VALUE
#define G_SPT1_ACLK_O              _DUMMY_VALUE
#define G_SPT1_ACLK_PBEN_O         _DUMMY_VALUE
#define G_SPT1_AD0_O               _DUMMY_VALUE
#define G_SPT1_AD0_PBEN_O          _DUMMY_VALUE
#define G_SPT1_AD1_O               _DUMMY_VALUE
#define G_SPT1_AD1_PBEN_O          _DUMMY_VALUE
#define G_SPT1_AFS_O               _DUMMY_VALUE
#define G_SPT1_AFS_PBEN_O          _DUMMY_VALUE
#define G_SPT1_ATDV_O              _DUMMY_VALUE
#define G_SPT1_ATDV_PBEN_O         _DUMMY_VALUE
#define G_SPT1_BCLK_O              _DUMMY_VALUE
#define G_SPT1_BCLK_PBEN_O         _DUMMY_VALUE
#define G_SPT1_BD0_O               _DUMMY_VALUE
#define G_SPT1_BD0_PBEN_O          _DUMMY_VALUE
#define G_SPT1_BD1_O               _DUMMY_VALUE
#define G_SPT1_BD1_PBEN_O          _DUMMY_VALUE
#define G_SPT1_BFS_O               _DUMMY_VALUE
#define G_SPT1_BFS_PBEN_O          _DUMMY_VALUE
#define G_SPT1_BTDV_O              _DUMMY_VALUE
#define G_SPT1_BTDV_PBEN_O         _DUMMY_VALUE
#define G_SPT2A_FS_O               _DUMMY_VALUE
#define G_SPT2B_FS_O               _DUMMY_VALUE
#define G_SPT2_ACLK_O              _DUMMY_VALUE
#define G_SPT2_ACLK_PBEN_O         _DUMMY_VALUE
#define G_SPT2_AD0_O               _DUMMY_VALUE
#define G_SPT2_AD0_PBEN_O          _DUMMY_VALUE
#define G_SPT2_AD1_O               _DUMMY_VALUE
#define G_SPT2_AD1_PBEN_O          _DUMMY_VALUE
#define G_SPT2_AFS_O               _DUMMY_VALUE
#define G_SPT2_AFS_PBEN_O          _DUMMY_VALUE
#define G_SPT2_ATDV_O              _DUMMY_VALUE
#define G_SPT2_ATDV_PBEN_O         _DUMMY_VALUE
#define G_SPT2_BCLK_O              _DUMMY_VALUE
#define G_SPT2_BCLK_PBEN_O         _DUMMY_VALUE
#define G_SPT2_BD0_O               _DUMMY_VALUE
#define G_SPT2_BD0_PBEN_O          _DUMMY_VALUE
#define G_SPT2_BD1_O               _DUMMY_VALUE
#define G_SPT2_BD1_PBEN_O          _DUMMY_VALUE
#define G_SPT2_BFS_O               _DUMMY_VALUE
#define G_SPT2_BFS_PBEN_O          _DUMMY_VALUE
#define G_SPT2_BTDV_O              _DUMMY_VALUE
#define G_SPT2_BTDV_PBEN_O         _DUMMY_VALUE
#define G_SPT3_ACLK_O              _DUMMY_VALUE
#define G_SPT3_ACLK_PBEN_O         _DUMMY_VALUE
#define G_SPT3_AD0_O               _DUMMY_VALUE
#define G_SPT3_AD0_PBEN_O          _DUMMY_VALUE
#define G_SPT3_AD1_O               _DUMMY_VALUE
#define G_SPT3_AD1_PBEN_O          _DUMMY_VALUE
#define G_SPT3_AFS_O               _DUMMY_VALUE
#define G_SPT3_AFS_PBEN_O          _DUMMY_VALUE
#define G_SPT3_ATDV_O              _DUMMY_VALUE
#define G_SPT3_ATDV_PBEN_O         _DUMMY_VALUE
#define G_SPT3_BCLK_O              _DUMMY_VALUE
#define G_SPT3_BCLK_PBEN_O         _DUMMY_VALUE
#define G_SPT3_BD0_O               _DUMMY_VALUE
#define G_SPT3_BD0_PBEN_O          _DUMMY_VALUE
#define G_SPT3_BD1_O               _DUMMY_VALUE
#define G_SPT3_BD1_PBEN_O          _DUMMY_VALUE
#define G_SPT3_BFS_O               _DUMMY_VALUE
#define G_SPT3_BFS_PBEN_O          _DUMMY_VALUE
#define G_SPT3_BTDV_O              _DUMMY_VALUE
#define G_SPT3_BTDV_PBEN_O         _DUMMY_VALUE
#define G_SRC0_DAT_OP_O            _DUMMY_VALUE
#define G_SRC0_TDM_IP_O            _DUMMY_VALUE
#define G_SRC1_DAT_OP_O            _DUMMY_VALUE
#define G_SRC1_TDM_IP_O            _DUMMY_VALUE
#define G_SRC2_DAT_OP_O            _DUMMY_VALUE
#define G_SRC2_TDM_IP_O            _DUMMY_VALUE
#define G_SRC3_CRS_DAT_OP_O        _DUMMY_VALUE
#define G_SRC3_CRS_TDM_IP_O        _DUMMY_VALUE
#define G_SRC3_DAT_OP_O            _DUMMY_VALUE
#define G_SRC3_TDM_IP_O            _DUMMY_VALUE

/* Dummy macro definitions for group A2 */

#define A2_DAI1_CRS_PB04_O         _DUMMY_VALUE
#define A2_DAI1_CRS_PB06_O         _DUMMY_VALUE
#define A2_DAI1_MISCA0_O           _DUMMY_VALUE
#define A2_DAI1_MISCA1_O           _DUMMY_VALUE
#define A2_DAI1_MISCA2_O           _DUMMY_VALUE
#define A2_DAI1_MISCA3_O           _DUMMY_VALUE
#define A2_DAI1_MISCA4_O           _DUMMY_VALUE
#define A2_DAI1_MISCA5_O           _DUMMY_VALUE
#define A2_DAI1_PB15_O             _DUMMY_VALUE
#define A2_DAI1_PB16_O             _DUMMY_VALUE
#define A2_MLB0_CLKOUT_O           _DUMMY_VALUE
#define A2_PCG0_CRS_CLKA_O         _DUMMY_VALUE
#define A2_PCG0_CRS_CLKB_O         _DUMMY_VALUE
#define A2_PCG0_CRS_FSA_O          _DUMMY_VALUE
#define A2_PCG0_CRS_FSB_O          _DUMMY_VALUE
#define A2_PCG0_FSC_O              _DUMMY_VALUE
#define A2_PCG0_FSD_O              _DUMMY_VALUE
#define A2_SPDIF1_RX_DAT_O         _DUMMY_VALUE
#define A2_SPDIF1_RX_FS_O          _DUMMY_VALUE
#define A2_SPDIF1_TX_BLKSTART_O    _DUMMY_VALUE
#define A2_SPDIF1_TX_O             _DUMMY_VALUE
#define A2_SPT4A_FS_O              _DUMMY_VALUE
#define A2_SPT4B_FS_O              _DUMMY_VALUE
#define A2_SPT4_ACLK_PBEN_O        _DUMMY_VALUE
#define A2_SPT4_AD0_O              _DUMMY_VALUE
#define A2_SPT4_AD0_PBEN_O         _DUMMY_VALUE
#define A2_SPT4_AD1_O              _DUMMY_VALUE
#define A2_SPT4_AD1_PBEN_O         _DUMMY_VALUE
#define A2_SPT4_AFS_O              _DUMMY_VALUE
#define A2_SPT4_AFS_PBEN_O         _DUMMY_VALUE
#define A2_SPT4_ATDV_O             _DUMMY_VALUE
#define A2_SPT4_ATDV_PBEN_O        _DUMMY_VALUE
#define A2_SPT4_BCLK_PBEN_O        _DUMMY_VALUE
#define A2_SPT4_BD0_O              _DUMMY_VALUE
#define A2_SPT4_BD0_PBEN_O         _DUMMY_VALUE
#define A2_SPT4_BD1_O              _DUMMY_VALUE
#define A2_SPT4_BD1_PBEN_O         _DUMMY_VALUE
#define A2_SPT4_BFS_O              _DUMMY_VALUE
#define A2_SPT4_BFS_PBEN_O         _DUMMY_VALUE
#define A2_SPT4_BTDV_O             _DUMMY_VALUE
#define A2_SPT4_BTDV_PBEN_O        _DUMMY_VALUE
#define A2_SPT5A_FS_O              _DUMMY_VALUE
#define A2_SPT5B_FS_O              _DUMMY_VALUE
#define A2_SPT5_ACLK_PBEN_O        _DUMMY_VALUE
#define A2_SPT5_AD0_O              _DUMMY_VALUE
#define A2_SPT5_AD0_PBEN_O         _DUMMY_VALUE
#define A2_SPT5_AD1_O              _DUMMY_VALUE
#define A2_SPT5_AD1_PBEN_O         _DUMMY_VALUE
#define A2_SPT5_AFS_O              _DUMMY_VALUE
#define A2_SPT5_AFS_PBEN_O         _DUMMY_VALUE
#define A2_SPT5_ATDV_O             _DUMMY_VALUE
#define A2_SPT5_ATDV_PBEN_O        _DUMMY_VALUE
#define A2_SPT5_BCLK_PBEN_O        _DUMMY_VALUE
#define A2_SPT5_BD0_O              _DUMMY_VALUE
#define A2_SPT5_BD0_PBEN_O         _DUMMY_VALUE
#define A2_SPT5_BD1_O              _DUMMY_VALUE
#define A2_SPT5_BD1_PBEN_O         _DUMMY_VALUE
#define A2_SPT5_BFS_O              _DUMMY_VALUE
#define A2_SPT5_BFS_PBEN_O         _DUMMY_VALUE
#define A2_SPT5_BTDV_O             _DUMMY_VALUE
#define A2_SPT5_BTDV_PBEN_O        _DUMMY_VALUE
#define A2_SPT6A_FS_O              _DUMMY_VALUE
#define A2_SPT6B_FS_O              _DUMMY_VALUE
#define A2_SPT6_ACLK_PBEN_O        _DUMMY_VALUE
#define A2_SPT6_AD0_O              _DUMMY_VALUE
#define A2_SPT6_AD0_PBEN_O         _DUMMY_VALUE
#define A2_SPT6_AD1_O              _DUMMY_VALUE
#define A2_SPT6_AD1_PBEN_O         _DUMMY_VALUE
#define A2_SPT6_AFS_O              _DUMMY_VALUE
#define A2_SPT6_AFS_PBEN_O         _DUMMY_VALUE
#define A2_SPT6_ATDV_O             _DUMMY_VALUE
#define A2_SPT6_ATDV_PBEN_O        _DUMMY_VALUE
#define A2_SPT6_BCLK_PBEN_O        _DUMMY_VALUE
#define A2_SPT6_BD0_O              _DUMMY_VALUE
#define A2_SPT6_BD0_PBEN_O         _DUMMY_VALUE
#define A2_SPT6_BD1_O              _DUMMY_VALUE
#define A2_SPT6_BD1_PBEN_O         _DUMMY_VALUE
#define A2_SPT6_BFS_O              _DUMMY_VALUE
#define A2_SPT6_BFS_PBEN_O         _DUMMY_VALUE
#define A2_SPT6_BTDV_O             _DUMMY_VALUE
#define A2_SPT6_BTDV_PBEN_O        _DUMMY_VALUE
#define A2_SPT7_ACLK_O             _DUMMY_VALUE
#define A2_SPT7_ACLK_PBEN_O        _DUMMY_VALUE
#define A2_SPT7_AD0_O              _DUMMY_VALUE
#define A2_SPT7_AD0_PBEN_O         _DUMMY_VALUE
#define A2_SPT7_AD1_O              _DUMMY_VALUE
#define A2_SPT7_AD1_PBEN_O         _DUMMY_VALUE
#define A2_SPT7_AFS_O              _DUMMY_VALUE
#define A2_SPT7_AFS_PBEN_O         _DUMMY_VALUE
#define A2_SPT7_ATDV_O             _DUMMY_VALUE
#define A2_SPT7_ATDV_PBEN_O        _DUMMY_VALUE
#define A2_SPT7_BCLK_O             _DUMMY_VALUE
#define A2_SPT7_BCLK_PBEN_O        _DUMMY_VALUE
#define A2_SPT7_BD0_O              _DUMMY_VALUE
#define A2_SPT7_BD0_PBEN_O         _DUMMY_VALUE
#define A2_SPT7_BD1_O              _DUMMY_VALUE
#define A2_SPT7_BD1_PBEN_O         _DUMMY_VALUE
#define A2_SPT7_BFS_O              _DUMMY_VALUE
#define A2_SPT7_BFS_PBEN_O         _DUMMY_VALUE
#define A2_SPT7_BTDV_O             _DUMMY_VALUE
#define A2_SPT7_BTDV_PBEN_O        _DUMMY_VALUE
#define A2_SRC3_CRS_DAT_OP_O       _DUMMY_VALUE
#define A2_SRC3_CRS_TDM_IP_O       _DUMMY_VALUE
#define A2_SRC4_DAT_OP_O           _DUMMY_VALUE
#define A2_SRC4_TDM_IP_O           _DUMMY_VALUE
#define A2_SRC5_DAT_OP_O           _DUMMY_VALUE
#define A2_SRC5_TDM_IP_O           _DUMMY_VALUE
#define A2_SRC6_DAT_OP_O           _DUMMY_VALUE
#define A2_SRC6_TDM_IP_O           _DUMMY_VALUE
#define A2_SRC7_DAT_OP_O           _DUMMY_VALUE
#define A2_SRC7_TDM_IP_O           _DUMMY_VALUE

/* Dummy macro definitions for group B2 */

#define B2_DAI1_CRS_PB03_O         _DUMMY_VALUE
#define B2_DAI1_CRS_PB04_O         _DUMMY_VALUE
#define B2_DAI1_CRS_PB05_O         _DUMMY_VALUE
#define B2_DAI1_CRS_PB06_O         _DUMMY_VALUE
#define B2_DAI1_MISCA0_O           _DUMMY_VALUE
#define B2_DAI1_MISCA1_O           _DUMMY_VALUE
#define B2_DAI1_MISCA2_O           _DUMMY_VALUE
#define B2_DAI1_MISCA3_O           _DUMMY_VALUE
#define B2_DAI1_MISCA4_O           _DUMMY_VALUE
#define B2_DAI1_MISCA5_O           _DUMMY_VALUE
#define B2_MLB0_CLKOUT_O           _DUMMY_VALUE
#define B2_PCG0_CLKC_O             _DUMMY_VALUE
#define B2_PCG0_CLKD_O             _DUMMY_VALUE
#define B2_PCG0_CRS_CLKA_O         _DUMMY_VALUE
#define B2_PCG0_CRS_CLKB_O         _DUMMY_VALUE
#define B2_PCG0_CRS_FSA_O          _DUMMY_VALUE
#define B2_PCG0_CRS_FSB_O          _DUMMY_VALUE
#define B2_PCG0_FSC_O              _DUMMY_VALUE
#define B2_PCG0_FSD_O              _DUMMY_VALUE
#define B2_SPDIF1_RX_CLK_O         _DUMMY_VALUE
#define B2_SPDIF1_RX_FS_O          _DUMMY_VALUE
#define B2_SPDIF1_RX_TDMCLK_O      _DUMMY_VALUE
#define B2_SPDIF1_TX_BLKSTART_O    _DUMMY_VALUE
#define B2_SPT4A_FS_O              _DUMMY_VALUE
#define B2_SPT4B_FS_O              _DUMMY_VALUE
#define B2_SPT4_ACLK_O             _DUMMY_VALUE
#define B2_SPT4_ACLK_PBEN_O        _DUMMY_VALUE
#define B2_SPT4_AD0_PBEN_O         _DUMMY_VALUE
#define B2_SPT4_AD1_PBEN_O         _DUMMY_VALUE
#define B2_SPT4_AFS_O              _DUMMY_VALUE
#define B2_SPT4_AFS_PBEN_O         _DUMMY_VALUE
#define B2_SPT4_ATDV_O             _DUMMY_VALUE
#define B2_SPT4_ATDV_PBEN_O        _DUMMY_VALUE
#define B2_SPT4_BCLK_O             _DUMMY_VALUE
#define B2_SPT4_BCLK_PBEN_O        _DUMMY_VALUE
#define B2_SPT4_BD0_PBEN_O         _DUMMY_VALUE
#define B2_SPT4_BD1_PBEN_O         _DUMMY_VALUE
#define B2_SPT4_BFS_O              _DUMMY_VALUE
#define B2_SPT4_BFS_PBEN_O         _DUMMY_VALUE
#define B2_SPT4_BTDV_O             _DUMMY_VALUE
#define B2_SPT4_BTDV_PBEN_O        _DUMMY_VALUE
#define B2_SPT5A_FS_O              _DUMMY_VALUE
#define B2_SPT5B_FS_O              _DUMMY_VALUE
#define B2_SPT5_ACLK_O             _DUMMY_VALUE
#define B2_SPT5_ACLK_PBEN_O        _DUMMY_VALUE
#define B2_SPT5_AD0_PBEN_O         _DUMMY_VALUE
#define B2_SPT5_AD1_PBEN_O         _DUMMY_VALUE
#define B2_SPT5_AFS_O              _DUMMY_VALUE
#define B2_SPT5_AFS_PBEN_O         _DUMMY_VALUE
#define B2_SPT5_ATDV_O             _DUMMY_VALUE
#define B2_SPT5_ATDV_PBEN_O        _DUMMY_VALUE
#define B2_SPT5_BCLK_O             _DUMMY_VALUE
#define B2_SPT5_BCLK_PBEN_O        _DUMMY_VALUE
#define B2_SPT5_BD0_PBEN_O         _DUMMY_VALUE
#define B2_SPT5_BD1_PBEN_O         _DUMMY_VALUE
#define B2_SPT5_BFS_O              _DUMMY_VALUE
#define B2_SPT5_BFS_PBEN_O         _DUMMY_VALUE
#define B2_SPT5_BTDV_O             _DUMMY_VALUE
#define B2_SPT5_BTDV_PBEN_O        _DUMMY_VALUE
#define B2_SPT6A_FS_O              _DUMMY_VALUE
#define B2_SPT6B_FS_O              _DUMMY_VALUE
#define B2_SPT6_ACLK_O             _DUMMY_VALUE
#define B2_SPT6_ACLK_PBEN_O        _DUMMY_VALUE
#define B2_SPT6_AD0_PBEN_O         _DUMMY_VALUE
#define B2_SPT6_AD1_PBEN_O         _DUMMY_VALUE
#define B2_SPT6_AFS_O              _DUMMY_VALUE
#define B2_SPT6_AFS_PBEN_O         _DUMMY_VALUE
#define B2_SPT6_ATDV_O             _DUMMY_VALUE
#define B2_SPT6_ATDV_PBEN_O        _DUMMY_VALUE
#define B2_SPT6_BCLK_O             _DUMMY_VALUE
#define B2_SPT6_BCLK_PBEN_O        _DUMMY_VALUE
#define B2_SPT6_BD0_PBEN_O         _DUMMY_VALUE
#define B2_SPT6_BD1_PBEN_O         _DUMMY_VALUE
#define B2_SPT6_BFS_O              _DUMMY_VALUE
#define B2_SPT6_BFS_PBEN_O         _DUMMY_VALUE
#define B2_SPT6_BTDV_O             _DUMMY_VALUE
#define B2_SPT6_BTDV_PBEN_O        _DUMMY_VALUE
#define B2_SPT7_ACLK_O             _DUMMY_VALUE
#define B2_SPT7_ACLK_PBEN_O        _DUMMY_VALUE
#define B2_SPT7_AD0_PBEN_O         _DUMMY_VALUE
#define B2_SPT7_AD1_PBEN_O         _DUMMY_VALUE
#define B2_SPT7_AFS_O              _DUMMY_VALUE
#define B2_SPT7_AFS_PBEN_O         _DUMMY_VALUE
#define B2_SPT7_ATDV_O             _DUMMY_VALUE
#define B2_SPT7_ATDV_PBEN_O        _DUMMY_VALUE
#define B2_SPT7_BCLK_O             _DUMMY_VALUE
#define B2_SPT7_BCLK_PBEN_O        _DUMMY_VALUE
#define B2_SPT7_BD0_PBEN_O         _DUMMY_VALUE
#define B2_SPT7_BD1_PBEN_O         _DUMMY_VALUE
#define B2_SPT7_BFS_O              _DUMMY_VALUE
#define B2_SPT7_BFS_PBEN_O         _DUMMY_VALUE
#define B2_SPT7_BTDV_O             _DUMMY_VALUE
#define B2_SPT7_BTDV_PBEN_O        _DUMMY_VALUE

/* Dummy macro definitions for group C2 */

#define C2_DAI1_CRS_PB03_O         _DUMMY_VALUE
#define C2_DAI1_CRS_PB05_O         _DUMMY_VALUE
#define C2_DAI1_MISCA0_O           _DUMMY_VALUE
#define C2_DAI1_MISCA1_O           _DUMMY_VALUE
#define C2_DAI1_MISCA2_O           _DUMMY_VALUE
#define C2_DAI1_MISCA3_O           _DUMMY_VALUE
#define C2_DAI1_MISCA4_O           _DUMMY_VALUE
#define C2_DAI1_MISCA5_O           _DUMMY_VALUE
#define C2_DAI1_PB15_O             _DUMMY_VALUE
#define C2_DAI1_PB16_O             _DUMMY_VALUE
#define C2_MLB0_CLKOUT_O           _DUMMY_VALUE
#define C2_PCG0_CLKC_O             _DUMMY_VALUE
#define C2_PCG0_CLKD_O             _DUMMY_VALUE
#define C2_PCG0_CRS_CLKA_O         _DUMMY_VALUE
#define C2_PCG0_CRS_CLKB_O         _DUMMY_VALUE
#define C2_PCG0_CRS_FSA_O          _DUMMY_VALUE
#define C2_PCG0_CRS_FSB_O          _DUMMY_VALUE
#define C2_SPDIF1_RX_CLK_O         _DUMMY_VALUE
#define C2_SPDIF1_RX_DAT_O         _DUMMY_VALUE
#define C2_SPDIF1_RX_TDMCLK_O      _DUMMY_VALUE
#define C2_SPDIF1_TX_BLKSTART_O    _DUMMY_VALUE
#define C2_SPDIF1_TX_O             _DUMMY_VALUE
#define C2_SPT4A_FS_O              _DUMMY_VALUE
#define C2_SPT4B_FS_O              _DUMMY_VALUE
#define C2_SPT4_ACLK_O             _DUMMY_VALUE
#define C2_SPT4_ACLK_PBEN_O        _DUMMY_VALUE
#define C2_SPT4_AD0_O              _DUMMY_VALUE
#define C2_SPT4_AD0_PBEN_O         _DUMMY_VALUE
#define C2_SPT4_AD1_O              _DUMMY_VALUE
#define C2_SPT4_AD1_PBEN_O         _DUMMY_VALUE
#define C2_SPT4_AFS_PBEN_O         _DUMMY_VALUE
#define C2_SPT4_ATDV_O             _DUMMY_VALUE
#define C2_SPT4_ATDV_PBEN_O        _DUMMY_VALUE
#define C2_SPT4_BCLK_O             _DUMMY_VALUE
#define C2_SPT4_BCLK_PBEN_O        _DUMMY_VALUE
#define C2_SPT4_BD0_O              _DUMMY_VALUE
#define C2_SPT4_BD0_PBEN_O         _DUMMY_VALUE
#define C2_SPT4_BD1_O              _DUMMY_VALUE
#define C2_SPT4_BD1_PBEN_O         _DUMMY_VALUE
#define C2_SPT4_BFS_PBEN_O         _DUMMY_VALUE
#define C2_SPT4_BTDV_O             _DUMMY_VALUE
#define C2_SPT4_BTDV_PBEN_O        _DUMMY_VALUE
#define C2_SPT5A_FS_O              _DUMMY_VALUE
#define C2_SPT5B_FS_O              _DUMMY_VALUE
#define C2_SPT5_ACLK_O             _DUMMY_VALUE
#define C2_SPT5_ACLK_PBEN_O        _DUMMY_VALUE
#define C2_SPT5_AD0_O              _DUMMY_VALUE
#define C2_SPT5_AD0_PBEN_O         _DUMMY_VALUE
#define C2_SPT5_AD1_O              _DUMMY_VALUE
#define C2_SPT5_AD1_PBEN_O         _DUMMY_VALUE
#define C2_SPT5_AFS_PBEN_O         _DUMMY_VALUE
#define C2_SPT5_ATDV_O             _DUMMY_VALUE
#define C2_SPT5_ATDV_PBEN_O        _DUMMY_VALUE
#define C2_SPT5_BCLK_O             _DUMMY_VALUE
#define C2_SPT5_BCLK_PBEN_O        _DUMMY_VALUE
#define C2_SPT5_BD0_O              _DUMMY_VALUE
#define C2_SPT5_BD0_PBEN_O         _DUMMY_VALUE
#define C2_SPT5_BD1_O              _DUMMY_VALUE
#define C2_SPT5_BD1_PBEN_O         _DUMMY_VALUE
#define C2_SPT5_BFS_PBEN_O         _DUMMY_VALUE
#define C2_SPT5_BTDV_O             _DUMMY_VALUE
#define C2_SPT5_BTDV_PBEN_O        _DUMMY_VALUE
#define C2_SPT6A_FS_O              _DUMMY_VALUE
#define C2_SPT6B_FS_O              _DUMMY_VALUE
#define C2_SPT6_ACLK_O             _DUMMY_VALUE
#define C2_SPT6_ACLK_PBEN_O        _DUMMY_VALUE
#define C2_SPT6_AD0_O              _DUMMY_VALUE
#define C2_SPT6_AD0_PBEN_O         _DUMMY_VALUE
#define C2_SPT6_AD1_O              _DUMMY_VALUE
#define C2_SPT6_AD1_PBEN_O         _DUMMY_VALUE
#define C2_SPT6_AFS_PBEN_O         _DUMMY_VALUE
#define C2_SPT6_ATDV_O             _DUMMY_VALUE
#define C2_SPT6_ATDV_PBEN_O        _DUMMY_VALUE
#define C2_SPT6_BCLK_O             _DUMMY_VALUE
#define C2_SPT6_BCLK_PBEN_O        _DUMMY_VALUE
#define C2_SPT6_BD0_O              _DUMMY_VALUE
#define C2_SPT6_BD0_PBEN_O         _DUMMY_VALUE
#define C2_SPT6_BD1_O              _DUMMY_VALUE
#define C2_SPT6_BD1_PBEN_O         _DUMMY_VALUE
#define C2_SPT6_BFS_PBEN_O         _DUMMY_VALUE
#define C2_SPT6_BTDV_O             _DUMMY_VALUE
#define C2_SPT6_BTDV_PBEN_O        _DUMMY_VALUE
#define C2_SPT7_ACLK_O             _DUMMY_VALUE
#define C2_SPT7_ACLK_PBEN_O        _DUMMY_VALUE
#define C2_SPT7_AD0_O              _DUMMY_VALUE
#define C2_SPT7_AD0_PBEN_O         _DUMMY_VALUE
#define C2_SPT7_AD1_O              _DUMMY_VALUE
#define C2_SPT7_AD1_PBEN_O         _DUMMY_VALUE
#define C2_SPT7_AFS_O              _DUMMY_VALUE
#define C2_SPT7_AFS_PBEN_O         _DUMMY_VALUE
#define C2_SPT7_ATDV_O             _DUMMY_VALUE
#define C2_SPT7_ATDV_PBEN_O        _DUMMY_VALUE
#define C2_SPT7_BCLK_O             _DUMMY_VALUE
#define C2_SPT7_BCLK_PBEN_O        _DUMMY_VALUE
#define C2_SPT7_BD0_O              _DUMMY_VALUE
#define C2_SPT7_BD0_PBEN_O         _DUMMY_VALUE
#define C2_SPT7_BD1_O              _DUMMY_VALUE
#define C2_SPT7_BD1_PBEN_O         _DUMMY_VALUE
#define C2_SPT7_BFS_O              _DUMMY_VALUE
#define C2_SPT7_BFS_PBEN_O         _DUMMY_VALUE
#define C2_SPT7_BTDV_O             _DUMMY_VALUE
#define C2_SPT7_BTDV_PBEN_O        _DUMMY_VALUE
#define C2_SRC3_CRS_DAT_OP_O       _DUMMY_VALUE
#define C2_SRC3_CRS_TDM_IP_O       _DUMMY_VALUE
#define C2_SRC4_DAT_OP_O           _DUMMY_VALUE
#define C2_SRC4_TDM_IP_O           _DUMMY_VALUE
#define C2_SRC5_DAT_OP_O           _DUMMY_VALUE
#define C2_SRC5_TDM_IP_O           _DUMMY_VALUE
#define C2_SRC6_DAT_OP_O           _DUMMY_VALUE
#define C2_SRC6_TDM_IP_O           _DUMMY_VALUE
#define C2_SRC7_DAT_OP_O           _DUMMY_VALUE
#define C2_SRC7_TDM_IP_O           _DUMMY_VALUE

/* Dummy macro definitions for group D2 */

#define D2_DAI1_MISCA0_O           _DUMMY_VALUE
#define D2_DAI1_MISCA1_O           _DUMMY_VALUE
#define D2_DAI1_MISCA2_O           _DUMMY_VALUE
#define D2_DAI1_MISCA3_O           _DUMMY_VALUE
#define D2_DAI1_MISCA4_O           _DUMMY_VALUE
#define D2_DAI1_MISCA5_O           _DUMMY_VALUE
#define D2_SPT4A_FS_O              _DUMMY_VALUE
#define D2_SPT4B_FS_O              _DUMMY_VALUE
#define D2_SPT4_ACLK_PBEN_O        _DUMMY_VALUE
#define D2_SPT4_AD0_PBEN_O         _DUMMY_VALUE
#define D2_SPT4_AD1_PBEN_O         _DUMMY_VALUE
#define D2_SPT4_AFS_PBEN_O         _DUMMY_VALUE
#define D2_SPT4_ATDV_PBEN_O        _DUMMY_VALUE
#define D2_SPT4_BCLK_PBEN_O        _DUMMY_VALUE
#define D2_SPT4_BD0_PBEN_O         _DUMMY_VALUE
#define D2_SPT4_BD1_PBEN_O         _DUMMY_VALUE
#define D2_SPT4_BFS_PBEN_O         _DUMMY_VALUE
#define D2_SPT4_BTDV_PBEN_O        _DUMMY_VALUE
#define D2_SPT5A_FS_O              _DUMMY_VALUE
#define D2_SPT5B_FS_O              _DUMMY_VALUE
#define D2_SPT5_ACLK_PBEN_O        _DUMMY_VALUE
#define D2_SPT5_AD0_PBEN_O         _DUMMY_VALUE
#define D2_SPT5_AD1_PBEN_O         _DUMMY_VALUE
#define D2_SPT5_AFS_PBEN_O         _DUMMY_VALUE
#define D2_SPT5_ATDV_PBEN_O        _DUMMY_VALUE
#define D2_SPT5_BCLK_PBEN_O        _DUMMY_VALUE
#define D2_SPT5_BD0_PBEN_O         _DUMMY_VALUE
#define D2_SPT5_BD1_PBEN_O         _DUMMY_VALUE
#define D2_SPT5_BFS_PBEN_O         _DUMMY_VALUE
#define D2_SPT5_BTDV_PBEN_O        _DUMMY_VALUE
#define D2_SPT6A_FS_O              _DUMMY_VALUE
#define D2_SPT6B_FS_O              _DUMMY_VALUE
#define D2_SPT6_ACLK_PBEN_O        _DUMMY_VALUE
#define D2_SPT6_AD0_PBEN_O         _DUMMY_VALUE
#define D2_SPT6_AD1_PBEN_O         _DUMMY_VALUE
#define D2_SPT6_AFS_PBEN_O         _DUMMY_VALUE
#define D2_SPT6_ATDV_PBEN_O        _DUMMY_VALUE
#define D2_SPT6_BCLK_PBEN_O        _DUMMY_VALUE
#define D2_SPT6_BD0_PBEN_O         _DUMMY_VALUE
#define D2_SPT6_BD1_PBEN_O         _DUMMY_VALUE
#define D2_SPT6_BFS_PBEN_O         _DUMMY_VALUE
#define D2_SPT6_BTDV_PBEN_O        _DUMMY_VALUE
#define D2_SPT7_ACLK_PBEN_O        _DUMMY_VALUE
#define D2_SPT7_AD0_PBEN_O         _DUMMY_VALUE
#define D2_SPT7_AD1_PBEN_O         _DUMMY_VALUE
#define D2_SPT7_AFS_PBEN_O         _DUMMY_VALUE
#define D2_SPT7_ATDV_PBEN_O        _DUMMY_VALUE
#define D2_SPT7_BCLK_PBEN_O        _DUMMY_VALUE
#define D2_SPT7_BD0_PBEN_O         _DUMMY_VALUE
#define D2_SPT7_BD1_PBEN_O         _DUMMY_VALUE
#define D2_SPT7_BFS_PBEN_O         _DUMMY_VALUE
#define D2_SPT7_BTDV_PBEN_O        _DUMMY_VALUE
#define D2_SRC3_CRS_DAT_OP_O       _DUMMY_VALUE
#define D2_SRC3_CRS_TDM_IP_O       _DUMMY_VALUE
#define D2_SRC4_TDM_IP_O           _DUMMY_VALUE
#define D2_SRC5_TDM_IP_O           _DUMMY_VALUE
#define D2_SRC6_TDM_IP_O           _DUMMY_VALUE
#define D2_SRC7_TDM_IP_O           _DUMMY_VALUE

/* Dummy macro definitions for group E2 */

#define E2_DAI1_CRS_PB03_O         _DUMMY_VALUE
#define E2_DAI1_CRS_PB04_O         _DUMMY_VALUE
#define E2_DAI1_CRS_PB05_O         _DUMMY_VALUE
#define E2_DAI1_CRS_PB06_O         _DUMMY_VALUE
#define E2_DAI1_MISCA0_O           _DUMMY_VALUE
#define E2_DAI1_MISCA1_O           _DUMMY_VALUE
#define E2_DAI1_MISCA2_O           _DUMMY_VALUE
#define E2_DAI1_MISCA3_O           _DUMMY_VALUE
#define E2_DAI1_MISCA4_O           _DUMMY_VALUE
#define E2_DAI1_MISCA5_O           _DUMMY_VALUE
#define E2_MLB0_CLKOUT_O           _DUMMY_VALUE
#define E2_PCG0_CLKC_O             _DUMMY_VALUE
#define E2_PCG0_CRS_CLKA_O         _DUMMY_VALUE
#define E2_PCG0_CRS_CLKB_O         _DUMMY_VALUE
#define E2_PCG0_CRS_FSA_O          _DUMMY_VALUE
#define E2_PCG0_CRS_FSB_O          _DUMMY_VALUE
#define E2_SPDIF1_RX_CLK_O         _DUMMY_VALUE
#define E2_SPDIF1_RX_DAT_O         _DUMMY_VALUE
#define E2_SPDIF1_RX_FS_O          _DUMMY_VALUE
#define E2_SPDIF1_RX_TDMCLK_O      _DUMMY_VALUE
#define E2_SPDIF1_TX_O             _DUMMY_VALUE
#define E2_SPT4_ACLK_O             _DUMMY_VALUE
#define E2_SPT4_ACLK_PBEN_O        _DUMMY_VALUE
#define E2_SPT4_AD0_O              _DUMMY_VALUE
#define E2_SPT4_AD0_PBEN_O         _DUMMY_VALUE
#define E2_SPT4_AD1_O              _DUMMY_VALUE
#define E2_SPT4_AD1_PBEN_O         _DUMMY_VALUE
#define E2_SPT4_AFS_PBEN_O         _DUMMY_VALUE
#define E2_SPT4_ATDV_O             _DUMMY_VALUE
#define E2_SPT4_ATDV_PBEN_O        _DUMMY_VALUE
#define E2_SPT4_BCLK_O             _DUMMY_VALUE
#define E2_SPT4_BCLK_PBEN_O        _DUMMY_VALUE
#define E2_SPT4_BD0_O              _DUMMY_VALUE
#define E2_SPT4_BD0_PBEN_O         _DUMMY_VALUE
#define E2_SPT4_BD1_O              _DUMMY_VALUE
#define E2_SPT4_BD1_PBEN_O         _DUMMY_VALUE
#define E2_SPT4_BFS_PBEN_O         _DUMMY_VALUE
#define E2_SPT4_BTDV_O             _DUMMY_VALUE
#define E2_SPT4_BTDV_PBEN_O        _DUMMY_VALUE
#define E2_SPT5_ACLK_O             _DUMMY_VALUE
#define E2_SPT5_ACLK_PBEN_O        _DUMMY_VALUE
#define E2_SPT5_AD0_O              _DUMMY_VALUE
#define E2_SPT5_AD0_PBEN_O         _DUMMY_VALUE
#define E2_SPT5_AD1_O              _DUMMY_VALUE
#define E2_SPT5_AD1_PBEN_O         _DUMMY_VALUE
#define E2_SPT5_AFS_PBEN_O         _DUMMY_VALUE
#define E2_SPT5_ATDV_O             _DUMMY_VALUE
#define E2_SPT5_ATDV_PBEN_O        _DUMMY_VALUE
#define E2_SPT5_BCLK_O             _DUMMY_VALUE
#define E2_SPT5_BCLK_PBEN_O        _DUMMY_VALUE
#define E2_SPT5_BD0_O              _DUMMY_VALUE
#define E2_SPT5_BD0_PBEN_O         _DUMMY_VALUE
#define E2_SPT5_BD1_O              _DUMMY_VALUE
#define E2_SPT5_BD1_PBEN_O         _DUMMY_VALUE
#define E2_SPT5_BFS_PBEN_O         _DUMMY_VALUE
#define E2_SPT5_BTDV_O             _DUMMY_VALUE
#define E2_SPT5_BTDV_PBEN_O        _DUMMY_VALUE
#define E2_SPT6_ACLK_O             _DUMMY_VALUE
#define E2_SPT6_ACLK_PBEN_O        _DUMMY_VALUE
#define E2_SPT6_AD0_O              _DUMMY_VALUE
#define E2_SPT6_AD0_PBEN_O         _DUMMY_VALUE
#define E2_SPT6_AD1_O              _DUMMY_VALUE
#define E2_SPT6_AD1_PBEN_O         _DUMMY_VALUE
#define E2_SPT6_AFS_PBEN_O         _DUMMY_VALUE
#define E2_SPT6_ATDV_O             _DUMMY_VALUE
#define E2_SPT6_ATDV_PBEN_O        _DUMMY_VALUE
#define E2_SPT6_BCLK_O             _DUMMY_VALUE
#define E2_SPT6_BCLK_PBEN_O        _DUMMY_VALUE
#define E2_SPT6_BD0_O              _DUMMY_VALUE
#define E2_SPT6_BD0_PBEN_O         _DUMMY_VALUE
#define E2_SPT6_BD1_O              _DUMMY_VALUE
#define E2_SPT6_BD1_PBEN_O         _DUMMY_VALUE
#define E2_SPT6_BFS_PBEN_O         _DUMMY_VALUE
#define E2_SPT6_BTDV_O             _DUMMY_VALUE
#define E2_SPT6_BTDV_PBEN_O        _DUMMY_VALUE
#define E2_SPT7_ACLK_O             _DUMMY_VALUE
#define E2_SPT7_ACLK_PBEN_O        _DUMMY_VALUE
#define E2_SPT7_AD0_O              _DUMMY_VALUE
#define E2_SPT7_AD0_PBEN_O         _DUMMY_VALUE
#define E2_SPT7_AD1_O              _DUMMY_VALUE
#define E2_SPT7_AD1_PBEN_O         _DUMMY_VALUE
#define E2_SPT7_AFS_O              _DUMMY_VALUE
#define E2_SPT7_AFS_PBEN_O         _DUMMY_VALUE
#define E2_SPT7_ATDV_O             _DUMMY_VALUE
#define E2_SPT7_ATDV_PBEN_O        _DUMMY_VALUE
#define E2_SPT7_BCLK_O             _DUMMY_VALUE
#define E2_SPT7_BCLK_PBEN_O        _DUMMY_VALUE
#define E2_SPT7_BD0_O              _DUMMY_VALUE
#define E2_SPT7_BD0_PBEN_O         _DUMMY_VALUE
#define E2_SPT7_BD1_O              _DUMMY_VALUE
#define E2_SPT7_BD1_PBEN_O         _DUMMY_VALUE
#define E2_SPT7_BFS_O              _DUMMY_VALUE
#define E2_SPT7_BFS_PBEN_O         _DUMMY_VALUE
#define E2_SPT7_BTDV_O             _DUMMY_VALUE
#define E2_SPT7_BTDV_PBEN_O        _DUMMY_VALUE
#define E2_SRC3_CRS_DAT_OP_O       _DUMMY_VALUE
#define E2_SRC3_CRS_TDM_IP_O       _DUMMY_VALUE
#define E2_SRC4_DAT_OP_O           _DUMMY_VALUE
#define E2_SRC4_TDM_IP_O           _DUMMY_VALUE
#define E2_SRC5_DAT_OP_O           _DUMMY_VALUE
#define E2_SRC5_TDM_IP_O           _DUMMY_VALUE
#define E2_SRC6_DAT_OP_O           _DUMMY_VALUE
#define E2_SRC6_TDM_IP_O           _DUMMY_VALUE
#define E2_SRC7_DAT_OP_O           _DUMMY_VALUE
#define E2_SRC7_TDM_IP_O           _DUMMY_VALUE

/* Dummy macro definitions for group F2 */

#define F2_DAI1_CRS_PB03_O         _DUMMY_VALUE
#define F2_DAI1_CRS_PB04_O         _DUMMY_VALUE
#define F2_DAI1_CRS_PB05_O         _DUMMY_VALUE
#define F2_DAI1_CRS_PB06_O         _DUMMY_VALUE
#define F2_DAI1_PB01_O             _DUMMY_VALUE
#define F2_DAI1_PB02_O             _DUMMY_VALUE
#define F2_DAI1_PB03_O             _DUMMY_VALUE
#define F2_DAI1_PB04_O             _DUMMY_VALUE
#define F2_DAI1_PB05_O             _DUMMY_VALUE
#define F2_DAI1_PB06_O             _DUMMY_VALUE
#define F2_DAI1_PB07_O             _DUMMY_VALUE
#define F2_DAI1_PB08_O             _DUMMY_VALUE
#define F2_DAI1_PB09_O             _DUMMY_VALUE
#define F2_DAI1_PB10_O             _DUMMY_VALUE
#define F2_DAI1_PB11_O             _DUMMY_VALUE
#define F2_DAI1_PB12_O             _DUMMY_VALUE
#define F2_DAI1_PB13_O             _DUMMY_VALUE
#define F2_DAI1_PB14_O             _DUMMY_VALUE
#define F2_DAI1_PB15_O             _DUMMY_VALUE
#define F2_DAI1_PB16_O             _DUMMY_VALUE
#define F2_DAI1_PB17_O             _DUMMY_VALUE
#define F2_DAI1_PB18_O             _DUMMY_VALUE
#define F2_DAI1_PB19_O             _DUMMY_VALUE
#define F2_DAI1_PB20_O             _DUMMY_VALUE
#define F2_MLB0_CLKOUT_O           _DUMMY_VALUE
#define F2_PCG0_CLKC_O             _DUMMY_VALUE
#define F2_PCG0_CLKD_O             _DUMMY_VALUE
#define F2_PCG0_CRS_CLKA_O         _DUMMY_VALUE
#define F2_PCG0_CRS_CLKB_O         _DUMMY_VALUE
#define F2_PCG0_CRS_FSA_O          _DUMMY_VALUE
#define F2_PCG0_CRS_FSB_O          _DUMMY_VALUE
#define F2_PCG0_FSC_O              _DUMMY_VALUE
#define F2_PCG0_FSD_O              _DUMMY_VALUE
#define F2_SPDIF1_RX_CLK_O         _DUMMY_VALUE
#define F2_SPDIF1_RX_DAT_O         _DUMMY_VALUE
#define F2_SPDIF1_RX_FS_O          _DUMMY_VALUE
#define F2_SPDIF1_RX_TDMCLK_O      _DUMMY_VALUE
#define F2_SPDIF1_TX_BLKSTART_O    _DUMMY_VALUE
#define F2_SPDIF1_TX_O             _DUMMY_VALUE
#define F2_SPT4A_FS_O              _DUMMY_VALUE
#define F2_SPT4B_FS_O              _DUMMY_VALUE
#define F2_SPT4_ACLK_O             _DUMMY_VALUE
#define F2_SPT4_AD0_O              _DUMMY_VALUE
#define F2_SPT4_AD1_O              _DUMMY_VALUE
#define F2_SPT4_AFS_O              _DUMMY_VALUE
#define F2_SPT4_ATDV_O             _DUMMY_VALUE
#define F2_SPT4_BCLK_O             _DUMMY_VALUE
#define F2_SPT4_BD0_O              _DUMMY_VALUE
#define F2_SPT4_BD1_O              _DUMMY_VALUE
#define F2_SPT4_BFS_O              _DUMMY_VALUE
#define F2_SPT4_BTDV_O             _DUMMY_VALUE
#define F2_SPT5A_FS_O              _DUMMY_VALUE
#define F2_SPT5B_FS_O              _DUMMY_VALUE
#define F2_SPT5_ACLK_O             _DUMMY_VALUE
#define F2_SPT5_AD0_O              _DUMMY_VALUE
#define F2_SPT5_AD1_O              _DUMMY_VALUE
#define F2_SPT5_AFS_O              _DUMMY_VALUE
#define F2_SPT5_ATDV_O             _DUMMY_VALUE
#define F2_SPT5_BCLK_O             _DUMMY_VALUE
#define F2_SPT5_BD0_O              _DUMMY_VALUE
#define F2_SPT5_BD1_O              _DUMMY_VALUE
#define F2_SPT5_BFS_O              _DUMMY_VALUE
#define F2_SPT5_BTDV_O             _DUMMY_VALUE
#define F2_SPT6A_FS_O              _DUMMY_VALUE
#define F2_SPT6B_FS_O              _DUMMY_VALUE
#define F2_SPT6_ACLK_O             _DUMMY_VALUE
#define F2_SPT6_AD0_O              _DUMMY_VALUE
#define F2_SPT6_AD1_O              _DUMMY_VALUE
#define F2_SPT6_AFS_O              _DUMMY_VALUE
#define F2_SPT6_ATDV_O             _DUMMY_VALUE
#define F2_SPT6_BCLK_O             _DUMMY_VALUE
#define F2_SPT6_BD0_O              _DUMMY_VALUE
#define F2_SPT6_BD1_O              _DUMMY_VALUE
#define F2_SPT6_BFS_O              _DUMMY_VALUE
#define F2_SPT6_BTDV_O             _DUMMY_VALUE
#define F2_SPT7_ACLK_O             _DUMMY_VALUE
#define F2_SPT7_AD0_O              _DUMMY_VALUE
#define F2_SPT7_AD1_O              _DUMMY_VALUE
#define F2_SPT7_AFS_O              _DUMMY_VALUE
#define F2_SPT7_ATDV_O             _DUMMY_VALUE
#define F2_SPT7_BCLK_O             _DUMMY_VALUE
#define F2_SPT7_BD0_O              _DUMMY_VALUE
#define F2_SPT7_BD1_O              _DUMMY_VALUE
#define F2_SPT7_BFS_O              _DUMMY_VALUE
#define F2_SPT7_BTDV_O             _DUMMY_VALUE
#define F2_SRC3_CRS_DAT_OP_O       _DUMMY_VALUE
#define F2_SRC3_CRS_TDM_IP_O       _DUMMY_VALUE
#define F2_SRC4_DAT_OP_O           _DUMMY_VALUE
#define F2_SRC4_TDM_IP_O           _DUMMY_VALUE
#define F2_SRC5_DAT_OP_O           _DUMMY_VALUE
#define F2_SRC5_TDM_IP_O           _DUMMY_VALUE
#define F2_SRC6_DAT_OP_O           _DUMMY_VALUE
#define F2_SRC6_TDM_IP_O           _DUMMY_VALUE
#define F2_SRC7_DAT_OP_O           _DUMMY_VALUE
#define F2_SRC7_TDM_IP_O           _DUMMY_VALUE

/* Dummy macro definitions for group G2 */

#define G2_DAI1_CRS_PB03_O         _DUMMY_VALUE
#define G2_DAI1_CRS_PB04_O         _DUMMY_VALUE
#define G2_DAI1_CRS_PB05_O         _DUMMY_VALUE
#define G2_DAI1_CRS_PB06_O         _DUMMY_VALUE
#define G2_DAI1_MISCA0_O           _DUMMY_VALUE
#define G2_DAI1_MISCA1_O           _DUMMY_VALUE
#define G2_DAI1_MISCA2_O           _DUMMY_VALUE
#define G2_DAI1_MISCA3_O           _DUMMY_VALUE
#define G2_DAI1_MISCA4_O           _DUMMY_VALUE
#define G2_DAI1_MISCA5_O           _DUMMY_VALUE
#define G2_DAI1_PB01_O             _DUMMY_VALUE
#define G2_DAI1_PB02_O             _DUMMY_VALUE
#define G2_DAI1_PB03_O             _DUMMY_VALUE
#define G2_DAI1_PB04_O             _DUMMY_VALUE
#define G2_DAI1_PB05_O             _DUMMY_VALUE
#define G2_DAI1_PB06_O             _DUMMY_VALUE
#define G2_DAI1_PB07_O             _DUMMY_VALUE
#define G2_DAI1_PB08_O             _DUMMY_VALUE
#define G2_DAI1_PB09_O             _DUMMY_VALUE
#define G2_DAI1_PB10_O             _DUMMY_VALUE
#define G2_DAI1_PB11_O             _DUMMY_VALUE
#define G2_DAI1_PB12_O             _DUMMY_VALUE
#define G2_DAI1_PB13_O             _DUMMY_VALUE
#define G2_DAI1_PB14_O             _DUMMY_VALUE
#define G2_DAI1_PB15_O             _DUMMY_VALUE
#define G2_DAI1_PB16_O             _DUMMY_VALUE
#define G2_DAI1_PB17_O             _DUMMY_VALUE
#define G2_DAI1_PB18_O             _DUMMY_VALUE
#define G2_DAI1_PB19_O             _DUMMY_VALUE
#define G2_DAI1_PB20_O             _DUMMY_VALUE
#define G2_MLB0_CLKOUT_O           _DUMMY_VALUE
#define G2_PCG0_CLKC_O             _DUMMY_VALUE
#define G2_PCG0_CLKD_O             _DUMMY_VALUE
#define G2_PCG0_CRS_CLKA_O         _DUMMY_VALUE
#define G2_PCG0_CRS_CLKB_O         _DUMMY_VALUE
#define G2_PCG0_CRS_FSA_O          _DUMMY_VALUE
#define G2_PCG0_CRS_FSB_O          _DUMMY_VALUE
#define G2_PCG0_FSC_O              _DUMMY_VALUE
#define G2_PCG0_FSD_O              _DUMMY_VALUE
#define G2_SPDIF1_RX_CLK_O         _DUMMY_VALUE
#define G2_SPDIF1_RX_DAT_O         _DUMMY_VALUE
#define G2_SPDIF1_RX_FS_O          _DUMMY_VALUE
#define G2_SPDIF1_RX_TDMCLK_O      _DUMMY_VALUE
#define G2_SPDIF1_TX_BLKSTART_O    _DUMMY_VALUE
#define G2_SPDIF1_TX_O             _DUMMY_VALUE
#define G2_SPT4A_FS_O              _DUMMY_VALUE
#define G2_SPT4B_FS_O              _DUMMY_VALUE
#define G2_SPT4_ACLK_O             _DUMMY_VALUE
#define G2_SPT4_ACLK_PBEN_O        _DUMMY_VALUE
#define G2_SPT4_AD0_O              _DUMMY_VALUE
#define G2_SPT4_AD0_PBEN_O         _DUMMY_VALUE
#define G2_SPT4_AD1_O              _DUMMY_VALUE
#define G2_SPT4_AD1_PBEN_O         _DUMMY_VALUE
#define G2_SPT4_AFS_O              _DUMMY_VALUE
#define G2_SPT4_AFS_PBEN_O         _DUMMY_VALUE
#define G2_SPT4_ATDV_O             _DUMMY_VALUE
#define G2_SPT4_ATDV_PBEN_O        _DUMMY_VALUE
#define G2_SPT4_BCLK_O             _DUMMY_VALUE
#define G2_SPT4_BCLK_PBEN_O        _DUMMY_VALUE
#define G2_SPT4_BD0_O              _DUMMY_VALUE
#define G2_SPT4_BD0_PBEN_O         _DUMMY_VALUE
#define G2_SPT4_BD1_O              _DUMMY_VALUE
#define G2_SPT4_BD1_PBEN_O         _DUMMY_VALUE
#define G2_SPT4_BFS_O              _DUMMY_VALUE
#define G2_SPT4_BFS_PBEN_O         _DUMMY_VALUE
#define G2_SPT4_BTDV_O             _DUMMY_VALUE
#define G2_SPT4_BTDV_PBEN_O        _DUMMY_VALUE
#define G2_SPT5A_FS_O              _DUMMY_VALUE
#define G2_SPT5B_FS_O              _DUMMY_VALUE
#define G2_SPT5_ACLK_O             _DUMMY_VALUE
#define G2_SPT5_ACLK_PBEN_O        _DUMMY_VALUE
#define G2_SPT5_AD0_O              _DUMMY_VALUE
#define G2_SPT5_AD0_PBEN_O         _DUMMY_VALUE
#define G2_SPT5_AD1_O              _DUMMY_VALUE
#define G2_SPT5_AD1_PBEN_O         _DUMMY_VALUE
#define G2_SPT5_AFS_O              _DUMMY_VALUE
#define G2_SPT5_AFS_PBEN_O         _DUMMY_VALUE
#define G2_SPT5_ATDV_O             _DUMMY_VALUE
#define G2_SPT5_ATDV_PBEN_O        _DUMMY_VALUE
#define G2_SPT5_BCLK_O             _DUMMY_VALUE
#define G2_SPT5_BCLK_PBEN_O        _DUMMY_VALUE
#define G2_SPT5_BD0_O              _DUMMY_VALUE
#define G2_SPT5_BD0_PBEN_O         _DUMMY_VALUE
#define G2_SPT5_BD1_O              _DUMMY_VALUE
#define G2_SPT5_BD1_PBEN_O         _DUMMY_VALUE
#define G2_SPT5_BFS_O              _DUMMY_VALUE
#define G2_SPT5_BFS_PBEN_O         _DUMMY_VALUE
#define G2_SPT5_BTDV_O             _DUMMY_VALUE
#define G2_SPT5_BTDV_PBEN_O        _DUMMY_VALUE
#define G2_SPT6A_FS_O              _DUMMY_VALUE
#define G2_SPT6B_FS_O              _DUMMY_VALUE
#define G2_SPT6_ACLK_O             _DUMMY_VALUE
#define G2_SPT6_ACLK_PBEN_O        _DUMMY_VALUE
#define G2_SPT6_AD0_O              _DUMMY_VALUE
#define G2_SPT6_AD0_PBEN_O         _DUMMY_VALUE
#define G2_SPT6_AD1_O              _DUMMY_VALUE
#define G2_SPT6_AD1_PBEN_O         _DUMMY_VALUE
#define G2_SPT6_AFS_O              _DUMMY_VALUE
#define G2_SPT6_AFS_PBEN_O         _DUMMY_VALUE
#define G2_SPT6_ATDV_O             _DUMMY_VALUE
#define G2_SPT6_ATDV_PBEN_O        _DUMMY_VALUE
#define G2_SPT6_BCLK_O             _DUMMY_VALUE
#define G2_SPT6_BCLK_PBEN_O        _DUMMY_VALUE
#define G2_SPT6_BD0_O              _DUMMY_VALUE
#define G2_SPT6_BD0_PBEN_O         _DUMMY_VALUE
#define G2_SPT6_BD1_O              _DUMMY_VALUE
#define G2_SPT6_BD1_PBEN_O         _DUMMY_VALUE
#define G2_SPT6_BFS_O              _DUMMY_VALUE
#define G2_SPT6_BFS_PBEN_O         _DUMMY_VALUE
#define G2_SPT6_BTDV_O             _DUMMY_VALUE
#define G2_SPT6_BTDV_PBEN_O        _DUMMY_VALUE
#define G2_SPT7_ACLK_O             _DUMMY_VALUE
#define G2_SPT7_ACLK_PBEN_O        _DUMMY_VALUE
#define G2_SPT7_AD0_O              _DUMMY_VALUE
#define G2_SPT7_AD0_PBEN_O         _DUMMY_VALUE
#define G2_SPT7_AD1_O              _DUMMY_VALUE
#define G2_SPT7_AD1_PBEN_O         _DUMMY_VALUE
#define G2_SPT7_AFS_O              _DUMMY_VALUE
#define G2_SPT7_AFS_PBEN_O         _DUMMY_VALUE
#define G2_SPT7_ATDV_O             _DUMMY_VALUE
#define G2_SPT7_ATDV_PBEN_O        _DUMMY_VALUE
#define G2_SPT7_BCLK_O             _DUMMY_VALUE
#define G2_SPT7_BCLK_PBEN_O        _DUMMY_VALUE
#define G2_SPT7_BD0_O              _DUMMY_VALUE
#define G2_SPT7_BD0_PBEN_O         _DUMMY_VALUE
#define G2_SPT7_BD1_O              _DUMMY_VALUE
#define G2_SPT7_BD1_PBEN_O         _DUMMY_VALUE
#define G2_SPT7_BFS_O              _DUMMY_VALUE
#define G2_SPT7_BFS_PBEN_O         _DUMMY_VALUE
#define G2_SPT7_BTDV_O             _DUMMY_VALUE
#define G2_SPT7_BTDV_PBEN_O        _DUMMY_VALUE
#define G2_SRC3_CRS_DAT_OP_O       _DUMMY_VALUE
#define G2_SRC3_CRS_TDM_IP_O       _DUMMY_VALUE
#define G2_SRC4_DAT_OP_O           _DUMMY_VALUE
#define G2_SRC4_TDM_IP_O           _DUMMY_VALUE
#define G2_SRC5_DAT_OP_O           _DUMMY_VALUE
#define G2_SRC5_TDM_IP_O           _DUMMY_VALUE
#define G2_SRC6_DAT_OP_O           _DUMMY_VALUE
#define G2_SRC6_TDM_IP_O           _DUMMY_VALUE
#define G2_SRC7_DAT_OP_O           _DUMMY_VALUE
#define G2_SRC7_TDM_IP_O           _DUMMY_VALUE

#if defined(_MISRA_2004_RULES) || defined(_MISRA_2012_RULES)
#pragma diag(pop)
#endif /* _MISRA_RULES */

#endif /* _SRU21569_H */
