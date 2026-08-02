/*****************************************************************************
 * w1c_selfcheck.h
 * 结果自检:防止编译器把整段被测代码优化掉(周期测量最常见的假绿)
 *
 * 做法:每个内核跑完一次,把若干代表性输出样本喂给 w1c_checksum_add()。
 * g_w1c_checksum 是 volatile 全局量,编译器不能证明它"不会被外部观察到"
 * (它在 main() 末尾会被 printf 出来),因此不能把喂给它的计算过程连带优化掉。
 *
 * ⚠ 这只挡住"整段代码被 DCE 掉"这一类假绿,不代表数值本身正确
 *   (T2/T3 是我方手写的代表性实现,不追求逐位数值正确,只追求算术强度代表性,
 *   详见 t2_fft.c / t3_nhs_scalar.c 顶部说明)。
 *
 * 判读规则(完整版见 README_WINDOWS.md 末尾附录,供 CTO/回传后判读者使用):
 *   ⚠ 同一组参数下 L1/L2 两个变体 checksum 相同是**正常的**——内存放置只
 *     影响周期数,不影响算出来的值,不要把这个当可疑信号。
 *   真正要警惕的是:同一个内核换了不同参数(如 T1a 换 window/biquads、
 *   T2 换 N)之后 checksum 长期恒为同一个值、尤其恒为 0——这才说明代码
 *   可能被优化掉、没有真的按参数跑,按"测不到"处理,不要采信该行周期数。
 *****************************************************************************/
#ifndef W1C_SELFCHECK_H
#define W1C_SELFCHECK_H

#include <stdint.h>

extern volatile uint32_t g_w1c_checksum;

static void w1c_checksum_add(int32_t v)
{
    g_w1c_checksum = (uint32_t)((g_w1c_checksum * 1000003u) ^ (uint32_t)v);
}

#endif /* W1C_SELFCHECK_H */
