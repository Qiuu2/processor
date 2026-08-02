/*****************************************************************************
 * w1c_config.h
 * W1-C 微基准 · 总开关
 *
 * 产出方:verification teammate(首次上岗)· 2026-08-01
 * L 标:本文件本身不产生任何数字,不需要 L 标;它控制的四个内核产出的周期数
 *       在 CTO 于板上跑出结果、回传之前,一律 [L4/未验证]。
 *
 * 用途:如果导入 CCES 后某一个内核编译不过(例如我方对某个 CCES 库函数签名
 * 或某个编译器 pragma 的猜测有误),把对应宏改成 0、重新 Build,
 * 其余三个内核仍然可以测出数据 —— 不许因为一个内核编译失败就整体放弃,
 * 也不许把编译不过的那项悄悄估算填表:main() 里对应位置会打印
 * "DISABLED (see w1c_config.h)",照抄回传即可,这就是"如实报 N/A"。
 *****************************************************************************/
#ifndef W1C_CONFIG_H
#define W1C_CONFIG_H

/* ---- 四个内核 + 内存 sizeof 自查,各自独立开关 ---- */
#define ENABLE_T1A_BIQUAD     1   /* T1:8 级 biquad × 64 样本(规整短环,DEC-0009/0014 主口径点) */
#define ENABLE_T1B_POLYPHASE  1   /* T1:48k→16k 多相抽取(101-tap ÷3,与 AEC 抽取器同形) */
#define ENABLE_T2_FFT         1   /* T2:1024/2048 点定点 FFT */
#define ENABLE_T3_NHS         1   /* T3:NHS 判据/状态机标量码(adaptive-dsp 20k cyc/槽 包络回填钩子) */
#define ENABLE_MEM_SIZEOF     1   /* DEC-0014 ⑤ / W1-B §8.2 WORD32 档:SHARC 编译器现场 sizeof */

/* 每个耗时内核的"热"重复测量次数(冷启动 1 次 + 热平均 N 次,见各内核文件注释) */
#define W1C_WARM_REPEAT       32

#endif /* W1C_CONFIG_H */
