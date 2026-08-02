# PROVENANCE — W1-C 微基准 CCES 工程

> 产出方:`verification` teammate(首次上岗)· 2026-08-01
> 铁律六(外部输入 24h 入库 + 来源留痕)适用对象:本目录混合了三类来源的文件——
> ①ADI 官方原始件(逐字节复制,版权头保留)②我方既有代码的结构化改写
> ③本次新写的胶水/测量代码。下面逐类交代,不含糊。
>
> **全局声明**:本工程本身 = **[L4/未验证]**,直到 CTO 在 CCES + ADSP-21569 EZ-Board
> 上实际编译、运行、回传结果为止。本文件不产生任何 cyc/MAC 数字,只交代"这些代码
> 从哪来、为什么这么写、哪些地方是我们自己的假设"。

---

## 1. 逐字节复制的 ADI 官方原始件(版权头保留,未改动内容)

来源工程(整包在 `knowledge_base/adsp21569/bsp/`,受 `.gitignore` 排除,故本次复制出来):
```
knowledge_base/adsp21569/bsp/app_notes/fira_accel_code/EE408V02/
  ADSP_2156x_FIR_Core_Performance/          ← 本工程的底座(EE-408 Rev2 附带工程之一)
    system.svc
    system/adi_initialize.c, adi_initialize.h
    system/startup_ldf/app.ldf, app_IVT.s, app_startup.s, app_heaptab.c
  ADSP_2156x_IIR_Core_Performance/
    src/ParamList.dat                        ← T1a biquad 的 35 组 {window,biquads} 扫描表
```

**复制到**:`04_platform/W1C_microbench/W1C_Microbench/{system.svc, system/, src/ParamList.dat}`

**校验**(复制时跑过,逐字节相同):
```
diff system.svc                       <ADI原文>/system.svc                        → 相同
diff system/adi_initialize.c          <ADI原文>/system/adi_initialize.c           → 相同
```
`system/startup_ldf/*`、`src/ParamList.dat` 同法复制,未手工改动任何字节。

**未改动版权头示例**(`system/startup_ldf/app.ldf` 开头):
```
/*
** ADSP-21569 linker description file generated on Mar 05, 2019 at 11:49:00.
*/
/*
** Copyright (C) 2000-2019 Analog Devices Inc., All Rights Reserved.
** ...
*/
```

**唯一改动的文件**(非 ADI 版权内容,工程元数据):`.project`、`.cproject` ——
把 ADI 原工程的项目名 `FIR_Core_Throughput_21569` 改为本工程名 `W1C_Microbench`
(仅改 `<name>` 与 `workspace_loc:/…` 路径引用,编译器/汇编器/链接器全部选项
逐条保留原值:`-proc ADSP-21569`、`-si-revision 0.0`、Debug 关优化/Release 开优化、
`-e`/`-ip` 等 flag 均未动)。

**为什么选这两个 ADI 工程做底座**:
- `ADSP_2156x_FIR_Core_Performance` 是 EE-408 Rev2 里体积最小、依赖最少的"核心
  (非加速器)吞吐测量"工程——只依赖 `adi_sec_Init()`(中断控制器),不依赖任何
  音频编解码器/SPORT/TWI 驱动,不需要板上外设跑通就能测核心周期,风险最低。
- `ADSP_2156x_IIR_Core_Performance` 的 `IIR_Core_Throughput_21569.c` 是
  DEC-0014①锚点(ADI EE-408 原文 "SHARC+ core takes 2.5 cycles per biquad")
  背后同款测量方法论的现成实现——T1a 直接沿用其 `biquad()` 调用方式与
  `ParamList.dat` 扫描表,保证与锚点口径可比。

---

## 2. 结构化改写的我方既有代码(非 ADI 原创,可自由改写,标明出处)

| 本工程文件 | 改写自 | 说明 |
|---|---|---|
| `src/t1b_polyphase.c` 的 `t1b_decimate()` | `knowledge_base/adsp21569/platform_lessons/cces_template/src/fir.c` 的 `polyphase_fir_decimate()` | 算法结构逐字段保留(Q15 系数 × Q31 状态环形缓冲,标准 C,零 CCES 专有 API),精简掉本次用不到的内插/分数延迟/整数延迟三段 |
| `src/mem_sizeof_check.c` 的全部结构体 | `01_design/selfcheck_W1B/mem_sizeof.c`(adaptive-dsp 第 3 实例,[L2/桌面 gcc]) | 字段/顺序/类型语义逐字照抄,唯一受控偏差 = `_Bool`→`uint8_t`(见该文件头注) |
| `src/t3_nhs_scalar.c` 的判据/状态机骨架 | `01_design/prototype_W1P/nhs.py`(P1.0,`_imsd`/`_phpr_veto`/`_is_dom`/`_classify`) | **代表性翻译,非逐行等价**——只搬算术形状(浮点比较/log10f/8点线性回归/NT×W_LONG 嵌套小循环),门限常数抄自其 `Params` 默认值,合成数据非真实频谱。见该文件头"诚实边界"整段。 |

---

## 3. 本次新写、需要现场生成的数据文件(可复现脚本,原样保留)

### 3.1 FFT 旋转因子表(Q31 定点)

生成脚本(跑于本沙箱 Python3,产出直接写入 `src/fft_twiddle_q31_512.dat` 与
`src/fft_twiddle_q31_1024.dat`,C 数组初始化列表格式,与 ADI 原工程
`ParamList.dat` 的"生成后 #include 进数组初始化列表"手法一致):

```python
import math

def q31(x):
    v = round(x * 2147483648.0)
    if v > 2147483647: v = 2147483647
    if v < -2147483648: v = -2147483648
    return v

def gen(n_half, path):
    N = 2 * n_half
    lines = []
    for k in range(n_half):
        theta = 2.0 * math.pi * k / N
        c = math.cos(theta)
        s = -math.sin(theta)
        lines.append("{ %d, %d },\n" % (q31(c), q31(s)))
    with open(path, "w") as f:
        f.writelines(lines)

gen(512,  ".../src/fft_twiddle_q31_512.dat")   # 供 N=1024 点 FFT
gen(1024, ".../src/fft_twiddle_q31_1024.dat")  # 供 N=2048 点 FFT
```

约定:`{cos(2πk/N), -sin(2πk/N)}`(标准 DIT 正向 FFT 旋转因子),k=0..N/2-1,
Q1.31 定点(四舍五入;k=0 的 cos=1.0 因满幅溢出钉在 `0x7FFFFFFF`)。

### 3.2 多相抽取原型系数(Q15 定点,101-tap)

生成脚本(Hamming 窗 sinc 低通,截止 fs/6,DC 增益归一,产出
`src/decim_coef_q15_101.dat`):

```python
import math

N = 101
M = 3
fc = 1.0 / (2.0 * M)

def sinc(x):
    if abs(x) < 1e-12: return 1.0
    return math.sin(math.pi * x) / (math.pi * x)

center = (N - 1) / 2.0
coeffs = []
for n in range(N):
    h = 2.0 * fc * sinc(2.0 * fc * (n - center))
    w = 0.54 - 0.46 * math.cos(2.0 * math.pi * n / (N - 1))
    coeffs.append(h * w)

s = sum(coeffs)
coeffs = [c / s for c in coeffs]

def q15(x):
    v = round(x * 32768.0)
    if v > 32767: v = 32767
    if v < -32768: v = -32768
    return v

with open(".../src/decim_coef_q15_101.dat", "w") as f:
    f.writelines("%d,\n" % q15(c) for c in coeffs)
```

**参数依据**:`01_design/W1A_AFC_architecture_budget.md` §4.7(3)——AEC 抽取器
"~101 tap"规格(48k→16k,与 AFC 旁链那只 72-tap 抽取器**不同**、不可复用)。
**这不是产品定版系数**——只是让 T1b 内核跑出"101-tap Q15×Q31 环形多相卷积"
这个算术形状对应的周期数,系数本身的通阻带指标未经校验,产品定版由
adaptive-dsp 出具时会不同,但周期数量级不受系数具体数值影响(MAC 次数不变)。

---

## 4. 已知限制 / 未尝试项(诚实边界,供后续跟进)

1. **T1a 的 L2 变体只搬了 DM 侧工作缓冲,没有把 `pm` 系数一起搬 L2**——
   我们没有工具链可以编译验证 "`pm` 限定符 + `#pragma section("seg_l2")`"
   这个组合是否合法/是否还能维持 biquad() 的双总线单周期双 MAC 优势,
   风险未知,故只测了风险较低的那一半(也恰是 DEC-0014⑤ ECC 读改写代价
   实际发生的那一侧:DM 数据写)。若需要"系数也在 L2"的完整数据点,
   需另起一轮,建议先问 CTO 手头 CCES 版本的 Compiler and Library Manual
   是否明确允许该组合。
2. **T2 FFT 没有调用 CCES DSP Run-Time Library 的 rfft()/cfft()**,自己写了
   一个跑在"实数打包成复数"上的 radix-2 DIT 参考实现——具体原因、口径边界、
   MAC 计数换算见 `src/t2_fft.c` 文件头。**这是保守上界,不是紧确值**。
3. **T3 是代表性翻译,不是 nhs.py 的逐行移植**——具体边界见
   `src/t3_nhs_scalar.c` 文件头。
4. 本工程未在任何 SHARC 工具链上编译过(本沙箱无 `cc21k`/`easm21k`,
   见 `01_design/W1_HANDOFF.md` §0 第 9 项 lead 实查记录)——所有语法/API
   假设(尤其 `#pragma section(...)`、`pm` 限定符、`<filter.h>` 的
   `biquad()` 签名)均以 **本目录 §1 逐字节复制的 ADI 官方代码里能找到的
   实际用法** 为准,凡是找不到实际先例、靠记忆/推测写的地方,均已在对应
   源文件头注里显式标出。
