/*********************************************************************************
 * 归档说明（PM，2026-06-03）：本文件由 CTO 提供（claude.ai 技术顾问随 FIRA 工作单贴出），
 * 是此前 gap G1「adi_fir_2156x.h / SHARC FIRA 驱动签名缺失」的权威闭合件。
 * 本机 CCES(ARM-only) 无此头，仓库原先也无 → 归档于此（C8/铁律六，外部输入入库）。
 * SHARC 侧真实文件位于 CCES 安装 lib/src/drivers/Source/fir/（实现 .c）+ include（本头）。
 * 关键：21569 FIRA 走 LEGACY 或 ACM；config 见同目录 adi_fir_config_2156x.h（仓库已有多份）。
 *********************************************************************************/
/*!
* @file      adi_fir_legacy_2156x.h
* @brief     FIR driver API Header file（21569 SHARC FIRA Legacy 模式）
*/
#ifndef __ADI_FIR_LEGACY_2156X_H__
#define __ADI_FIR_LEGACY_2156X_H__

/* DEFINES（任务/TCB 内存计算） */
#define ADI_FIR_TASK_INFO_SIZE   (28u + ADI_CACHE_LINE_LENGTH)  /* Legacy 28u / ACM 24u */
#define ADI_FIR_TCB_INFO_SIZE    (52u)                          /* Legacy 52u / ACM 64u */
#define FIR_MEM_SIZE(NO_OF_CHANNELS) (ADI_FIR_TASK_INFO_SIZE + ((NO_OF_CHANNELS) * ADI_FIR_TCB_INFO_SIZE))

/* TYPEDEFS */
typedef void* ADI_FIR_DEV_HANDLE;
typedef void* ADI_FIR_TASK_HANDLE;

/* ENUMS */
typedef enum { ADI_FIR_TASK_STATE_NONE, ADI_FIR_TASK_STATE_QUEUED,
               ADI_FIR_TASK_STATE_RUNNING, ADI_FIR_TASK_STATE_COMPLETED } ADI_FIR_TASK_STATE;

typedef enum { ADI_FIR_RESULT_SUCCESS, ADI_FIR_RESULT_FAILED, ADI_FIR_RESULT_INVALID_HANDLE,
               ADI_FIR_RESULT_INVALID_STATE, ADI_FIR_RESULT_INVALID_OPERATION,
               ADI_FIR_RESULT_TASK_STATE_RUNNING } ADI_FIR_RESULT;

/* 抽取/插值（★我方树形用 DECIMATION） */
typedef enum { ADI_FIR_SAMPLING_SINGLE_RATE,  /* 无抽取/插值 */
               ADI_FIR_SAMPLING_DECIMATION,   /* 抽取 */
               ADI_FIR_SAMPLING_INTERPOLATION /* 插值 */ } ADI_FIR_SAMPLING;

/* 21569 浮点舍入：仅 NEAREST_EVEN / TO_ZERO */
typedef enum { ADI_FIR_FLOAT_ROUNDING_MODE_IEEE_ROUND_TO_NEAREST_EVEN = 0,
               ADI_FIR_FLOAT_ROUNDING_MODE_IEEE_ROUND_TO_ZERO         = 1 } ADI_FIR_FLOAT_ROUNDING_MODE;

/* ★R14 命门：定点输入格式（仅 UNSIGNED / SIGNED INTEGER；我方有符号 PCM 用 SIGNED） */
typedef enum { ADI_FIR_FIXED_INPUT_FORMAT_UNSIGNED_INTEGER,
               ADI_FIR_FIXED_INPUT_FORMAT_SIGNED_INTEGER } ADI_FIR_FIXED_INPUT_FORMAT;

/* 通道配置（Legacy：无内联定点格式字段——格式经 config 宏 或运行时 FixedPointEnable） */
typedef struct {
    uint32_t  nTapLength;          /* Tap 数 */
    uint32_t  nWindowSize;         /* Window Size */
    ADI_FIR_SAMPLING eSampling;    /* 采样模式（SINGLE/DECIMATION/INTERP） */
    uint32_t  nSamplingRatio;      /* 采样比（抽取/插值率） */
    uint32_t  nCoefficientCount;   void* pCoefficientIndex;  int32_t nCoefficientModify;
    void*  pOutputBuffBase;  uint32_t nOutputBuffCount;  int32_t nOutputBuffModify;  void* pOutputBuffIndex;
    void*  pInputBuffBase;   uint32_t nInputBuffCount;   int32_t nInputBuffModify;   void* pInputBuffIndex;
} ADI_FIR_CHANNEL_INFO;

/* 缓冲索引（ACM 任务复用时更新；Legacy 由硬件完成后自动更新索引） */
typedef struct {
    void* pOutputBuffBase; uint32_t nOutputBuffCount; int32_t nOutputBuffModify; void* pOutputBuffIndex;
    void* pInputBuffBase;  uint32_t nInputBuffCount;  int32_t nInputBuffModify;  void* pInputBuffIndex;
} ADI_FIR_CHANNEL_BUFFER_INFO;

typedef enum { ADI_FIR_EVENT_CHANNEL_DONE, ADI_FIR_EVENT_ALL_CHANNEL_DONE } ADI_FIR_EVENT;

/* ==================== API（10 函数，全确认） ==================== */
ADI_FIR_RESULT adi_fir_Open(uint8_t nDeviceNum, ADI_FIR_DEV_HANDLE *phFirHandle);
ADI_FIR_RESULT adi_fir_CreateTask(ADI_FIR_DEV_HANDLE hFirHandle, ADI_FIR_CHANNEL_INFO *pChannelList,
                                  uint32_t nNumChannels, void *pMemory, uint32_t nMemSize,
                                  ADI_FIR_TASK_HANDLE *phFirTask);
ADI_FIR_RESULT adi_fir_QueueTask(ADI_FIR_TASK_HANDLE hFirTask);
ADI_FIR_RESULT adi_fir_DeleteTask(ADI_FIR_TASK_HANDLE hFirTask);
ADI_FIR_RESULT adi_fir_GetFirTaskStatus(ADI_FIR_TASK_HANDLE hFirTask, ADI_FIR_TASK_STATE *TaskStatus);
/* ★R14 运行时入口：把任务设为定点 + 指定 SIGNED/UNSIGNED 格式 */
ADI_FIR_RESULT adi_fir_FixedPointEnable(ADI_FIR_TASK_HANDLE hFirTask, ADI_FIR_FIXED_INPUT_FORMAT eInputFormat);
ADI_FIR_RESULT adi_fir_FloatingPointEnable(ADI_FIR_TASK_HANDLE hFirTask, ADI_FIR_FLOAT_ROUNDING_MODE eRoundingMode);
ADI_FIR_RESULT adi_fir_Close(ADI_FIR_DEV_HANDLE hFirHandle);
ADI_FIR_RESULT adi_fir_RegisterCallback(ADI_FIR_DEV_HANDLE hFirHandle, ADI_CALLBACK pfCallback, void *pCBParam);
/* ACM 任务复用时更新缓冲索引（Legacy 不需要：硬件自动更新） */
ADI_FIR_RESULT adi_fir_UpdateTask(ADI_FIR_TASK_HANDLE hFirTask, ADI_FIR_CHANNEL_BUFFER_INFO *pChannelParamsList,
                                  uint32_t nNumChannels);

#endif /* __ADI_FIR_LEGACY_2156X_H__ */
