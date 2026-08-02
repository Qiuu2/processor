# W1-C 微基准 — Windows + CCES 操作手册

> 面向:CTO(假设不熟悉 CCES,按步骤照做即可)
> 目标:在 ADSP-21569 EZ-Board 上跑出 4 个内核 + 1 个内存 sizeof 自查的真实周期数,
> 回填 DEC-0009(cyc/MAC 分档)与 DEC-0014⑤(WORD32 内存档)两个承重台账。
> **在本手册跑完、结果回传之前,工程里的所有数字都是 [L4/未验证]。**

---

## 0. 先读:这一步不是我们的活,但是前置条件

物理上电、JTAG 接线、BOOT 模式开关、CCES 里建 Debug Session 连仿真器这一整套
硬件 bring-up 步骤,**已经有专门的清单**,别处也在维护、我们不重复造轮子:

```
knowledge_base/adsp21569/platform_lessons/bringup/ezkit_bringup_checklist.md
```

**开始下面第 1-6 步之前,请先按那份清单走完到"Phase 4:CCES 链路自检(ICE Test)"
这一步**——即确认:板子物理版本已核对丝印、JTAG 已断电插好、BOOT MODE 三拨码
已拨到 No-boot(全 0)、板子和仿真器已按顺序上电、CCES 里 ICE Test 五步全打钩。
那份清单里写死的两条安全红线(**禁热插拔 JTAG**、**上电前先确认 BOOT 开关**)
本手册不再重复,请照那边执行。

那份清单走完后,回到这里继续第 1 步(导入工程)。第 7 步会再指回那份清单的
"Phase 5:建 Session",那是唯一还会用到它的地方。

---

## 1. 拷贝工程到 Windows

把这个文件夹整个拷贝到 Windows 机器上(U 盘 / 网络共享 / git 都行):

```
04_platform/W1C_microbench/W1C_Microbench/
```

**放在哪**:选一个**路径里没有空格、没有中文字符**的目录,例如:

```
C:\dsp_work\W1C_Microbench\
```

（原因:Eclipse/CCES 的工作区和路径解析对空格、非 ASCII 字符偶尔会出怪问题,
这是 CCES 使用者常踩的坑,不是本工程特有问题,提前避开。）

**只需要拷 `W1C_Microbench` 这一个文件夹**(里面有 `.project`/`.cproject`/
`system.svc`/`system/`/`src/`)。同目录下的 `PROVENANCE.md`、本手册不需要拷到
Windows,留着参考即可。

---

## 2. 打开 CCES,准备工作区

1. 打开 CrossCore Embedded Studio(CCES)。
2. 如果它提示选择 workspace(工作区)路径,同样选一个**无空格、无中文**的目录,
   例如 `C:\dsp_work\cces_ws`。可以新建一个专门给这次任务用的空工作区,
   不会影响你机器上其它 CCES 工程。

---

## 3. 导入工程

**File → Import… → General → Existing Projects into Workspace → Next**

- **Select root directory**:浏览到你在第 1 步拷贝的 `C:\dsp_work\W1C_Microbench\`
  文件夹(注意选到包含 `.project` 文件的这一层,不是它的上一层)。
- 下面 "Projects" 列表框应该会自动勾出一个项目,名字是 **`W1C_Microbench`**。
  确认它被勾选。
- **不要**勾 "Copy projects into workspace"(勾不勾都行,不影响结果,但不勾
  可以让你之后改文件时改的就是原始拷贝,方便回传)。
- 点 **Finish**。

导入完成后,左侧 Project Explorer 里应该出现 `W1C_Microbench` 这个工程,
展开能看到 `src/`(十来个 `.c`/`.h`/`.dat` 文件)和 `system/` 两个文件夹。

**如果这一步就报错**(比如提示找不到 SHARC 相关的工程类型/nature):
大概率是这台 CCES 装的是 ARM-only 版本、缺 SHARC 工具链和 ADSP-21569 支持包
(我们在 `01_design/W1_HANDOFF.md` 里记过同类问题,但那是另一台机器)。
确认方法:**Help → About CrossCore Embedded Studio → Installation Details**,
看列表里有没有 "SHARC"/"21569" 字样的条目。没有的话,这是缺装 SHARC 支持包
这个前置问题,先解决它,不是本工程代码的问题——报回来,不要在这一步硬试。

---

## 4. 选 Build Configuration = **Release**(重要,不要漏)

右键 `W1C_Microbench` 工程 → **Build Configurations → Set Active → Release**。

**为什么必须是 Release,不能是 Debug**:Debug 配置关掉了编译器优化(`-O` 关),
测出来的周期数会比真实产品跑的优化代码大很多、没法跟 DEC-0009/DEC-0014 里
"2.5 cyc/biquad"这类厂家锚点做对比。工程启动时会在 Console 第一行打印
`build config = Release` 还是 `Debug`,回传时请确认那一行显示的是 Release。

（如果你也想顺手看看 Debug 差多少,跑完 Release 后可以重复第 4-6 步切到 Debug
再跑一遍,两份都发回来也无妨——但主口径对照必须用 Release 那份。）

---

## 5. Build(编译)

右键工程 → **Build Project**(或者选中工程后点工具栏那个锤子图标)。

看下方 **Console** 视图,等它跑完。理想情况是最后一行类似:
```
'Invoke: Make'
Finished building target: ...
```
且没有红色 `Error` 行(黄色 `Warning` 没关系,可以忽略)。

**如果报错**:
1. 先看错误信息里点名的是哪个文件。工程里每个内核都在 `src/w1c_config.h`
   里有独立开关(`ENABLE_T1A_BIQUAD` / `ENABLE_T1B_POLYPHASE` / `ENABLE_T2_FFT`
   / `ENABLE_T3_NHS` / `ENABLE_MEM_SIZEOF`)。
2. 把报错那个内核对应的宏从 `1` 改成 `0`,存盘,重新 Build。
3. 其余内核应该还能编译通过、测出数据——**不要因为一个内核编译不过就放弃整个
   工程**。
4. 把完整的错误文本(红字那几行,越全越好,包含文件名和行号)存下来,连同
   "哪个内核被我关掉了"一起回传——这正是"测不到就如实报,不许估算"的具体
   操作方式。

---

## 6. 建 Debug Session,连板子,跑程序

这一步要用到硬件 bring-up 清单里 **"Phase 5:建 Session + 跑验证程序"** 那一节的
菜单路径,原样照抄一遍(该清单原文用的是别的示例工程,这里换成本工程,菜单
路径完全一样):

1. **Run → Debug Configurations…**,双击 **Application with CrossCore Debugger**
   新建一个配置,名字随便起(比如 `W1C_Microbench Debug`)。
2. Session Wizard 里:
   - **Select Processor**:Processor family = **SHARC**,Processor type =
     **ADSP-21569**。Next。
   - **Select Connection Type**:选 **Emulator**。Next。
   - **Select Platform**:选 **`ADSP-21569 via ICE-1000`**(如果第 0 步的 ICE Test
     显示的是别的型号如 ICE-1500/ICE-2000,这里对应选那个)。Finish。
3. 在这个新配置里,确认 **Project** 一栏指向 `W1C_Microbench`,
   **Configuration** 指向 **Release**(与第 4 步一致)。
4. 先点 **Apply**,再点 **Debug**。CCES 会把程序下载到板子上,停在 `main()`
   入口(Debug 透视图打开)。
5. 点 **Resume**(绿色三角/F5),程序会跑到底(所有内核跑完、`main()` 返回)。

**如果 CCES 提示 "silicon revision mismatch" 之类的警告**:双击工程里的
`system.svc` 打开系统配置图形界面,确认 Processor 一栏选的是 **ADSP-21569**、
si-revision 保持 **0.0**;如果它提示要重新生成 startup/ldf,可以让它生成
(这些是标准 ADI 生成文件,不含我们的自定义逻辑,重新生成不会丢东西)。
如果这一步卡住,先原样报回错误提示文字,不要凭感觉改工程设置。

---

## 7. 结果在哪、怎么存

程序跑的时候,结果会实时打印在 CCES 的 **Console** 视图里,大致长这样
(数字是占位示例,不代表真实结果):
```
T1A_biquad,L1,window=64,biquads=8,cycles=1234,checksum=...
T2_FFT,L1,N=1024,cold_1call,cycles=123456,checksum=...
...
W1C_CHECKSUM_FINAL=...
```

同时,程序会把同样的数据写成一份 CSV 文件:**`Results_W1C.csv`**,写在这次
Debug 运行的**输出目录**里——对 Release 配置来说,通常是:
```
C:\dsp_work\W1C_Microbench\Release\Results_W1C.csv
```
(这是 ADI 原始工程自带的写法,原样保留未改动;如果你在 `Release\` 文件夹下
没找到,去 `Debug\` 文件夹下找找看,或者在 Windows 里搜索文件名
`Results_W1C.csv`。)

**双保险**:不管 CSV 文件找不找得到,请**同时把 Console 视图里的全部文字
原样复制一份存成 .txt**(Console 里右键 → Select All → Copy,粘贴到记事本存盘)。
两份一起回传最稳妥;哪怕 CSV 机制出问题,Console 文字这一份也够用。

### 每一行前缀是什么意思(速查)

| 行前缀 | 对应哪个承重台账 | 说明 |
|---|---|---|
| `T1A_biquad,...` | DEC-0009/DEC-0014①(T1 规整短环) | 8 级 biquad×64 样本为主口径点;另附 35 组 window/biquads 扫描,可与厂家"2.5 cyc/biquad"锚点做量级对照 |
| `T1B_polyphase,...` | DEC-0009(T1,抽取器) | 48k→16k 多相抽取,101-tap,与 AEC 抽取器同形 |
| `T1B_write16_penalty,...` | **DEC-0014⑤ / W1A 文档 V-14** | 直接测"L2 的 <32-bit 写是否真的读改写罚 3 周期",取代目前的估算值(≈0.20%,依赖未核实的 SYSCLK=CCLK/2 假设)。**这一项如果测出来,是本次任务里能直接把一个 [L4/估算] 升级为 [L1/实测] 的最高性价比一项** |
| `T2_FFT,...` | DEC-0009(T2,无板证上界) | 1024/2048 点定点 FFT;**自研参考实现,非 CCES 库函数**,是保守上界不是紧确值(见工程 `PROVENANCE.md`) |
| `T3_NHS,...` | adaptive-dsp 的 20k cyc/槽 包络声明 | 12 轨判据/状态机代表性翻译,非 nhs.py 逐行等价 |
| `MEM_SIZEOF,...` | DEC-0014⑤ / W1-B §8.2 | SHARC 编译器现场 sizeof,判定 WORD32 内存档是否成立 |
| `W1C_CHECKSUM_FINAL=...` | — | 全局自检累加值,见文末"结果自检判读"附录 |

---

## 8. 结束调试(收尾,别漏)

按 bring-up 清单的规矩:**不要直接关软件断电**。先在 CCES 里点
**Disconnect**(断开软硬件连接),再考虑是否要断电、拔 JTAG(拔之前先断电)。

---

## 9. 回传清单(请把下面这些一起发回)

1. **`Results_W1C.csv`**(如果找到了)
2. **Console 输出全文**(.txt,双保险,见第 7 步)
3. 第 3 步 Import 有没有报错(有的话报什么)
4. 实际 Build 用的是 **Release 还是 Debug**(第一行 Console 输出会写)
5. 有没有哪个内核被你在 `w1c_config.h` 里关掉了(`ENABLE_xxx = 0`)、
   关掉前的完整报错文本
6. CCES 的版本号(**Help → About CrossCore Embedded Studio**)
7. 如果第 0 步硬件 bring-up 过程中有任何异常(连不上仿真器、板子灯不对等),
   照 bring-up 清单里的判据描述一并说明

**关于"测不到"**:如果四个内核里有任何一个从头到尾都跑不出数据(编译不过、
或者跑起来死机/挂起、或者 CSV 和 Console 都没有对应那一段输出),**如实回传
"这项 N/A + 原因"**,不需要、也请不要自己估算一个数字填进去——这正是这次
任务的硬要求之一。

---

## 附:关于结果自检(checksum)的判读

每一行结果后面都带一个 `checksum` 数字(内存 sizeof 那部分除外)。这是用来
防止编译器把整段被测代码"优化到不存在"的自检手段(周期测量最常见的假绿
来源)。判读规则,请分两种情况看,**不要混为一谈**:

- **同一组参数下,L1 和 L2 两行 checksum 相同 —— 这是正常的,不是可疑信号。**
  内存放置只影响"算出结果要多少周期",不影响"算出来的结果是什么"——同样的
  输入、同样的算法,放 L1 还是放 L2,算出的数值理应完全一样,只有 `cycles`
  那一列应该不同。（我们在宿主机上跑过一遍验证,T1b/T2/T3 确实是这个模式:
  L1/L2 的 checksum 逐位相同、cycles 不同——这是预期行为。）
- **需要警惕的,是同一个内核在不同参数下(比如 T1a 换 window/biquads、T2 换
  N=1024 换成 2048)checksum 长期是同一个值,尤其恒为 0** —— 这才说明代码
  可能被编译器优化掉、根本没有真的按不同参数跑,请在回传时特别标注出来,
  不用自己判断对错,交给我们复核。
