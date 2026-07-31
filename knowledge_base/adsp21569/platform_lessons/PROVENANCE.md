# platform_lessons 溯源单(PROVENANCE)
> 复制日:2026-07-30 ｜ 源:ITC 项目 `/home/it1234/algorithm_speaker/Kimi_Agent_多Agent协作方案/itc-enterprise-workflow/`
> **原文件逐字节原样保存**(不注入头注,保完整性,来源注以本单代替——README 规则按此执行)。
> **L 标口径**:各文件内 [L1] 均为 ITC 项目(同芯片 ADSP-21569)实测;本项目引用登记为 `[L1/ITC同芯片实测,场景迁移待本项目复核]`。
> **去产品化状态**:全部为"标注式"(原文含波束成形/阵列几何等 ITC 产品段,使用时按下表提示跳过),未做删除式改写。

| 本库文件 | 源路径(ITC 根下) | 产品特定段提示 |
|---|---|---|
| bringup/STAGE4_BRINGUP_CHECKLIST.md | sprint6/STAGE4_BRINGUP_CHECKLIST.md | 上板 32 坑,平台通用,基本无产品段 |
| bringup/ezkit_bringup_checklist.md | sprint3/audit/ezkit_bringup_checklist.md | EZKIT 板专属(JTAG/boot/跳线);本项目自研板 bring-up 清单以此为模板重写 |
| fira/ITC_dsp-algorithm_SKILL.md | .claude/skills/dsp-algorithm/SKILL.md | **已改名防直装**;波束/几何段使用时跳过;FIRA 五件套+假绿验证+30-50cyc/MAC 段为平台通用真料;进本项目 skill 须走蒸馏 SOP(README 规则③) |
| fixed_point/tree_filterbank.{c,h} | sprint3/dsp/tree_filterbank.{c,h} | 滤波器组结构为 ITC 算法;**可复用的是定点范式**(Q15×Q31→Q46→Q31+饱和原语),非算法本身 |
| cces_template/(整目录) | sprint2/dsp/cces_template/ | CCES 工程骨架(.ldf 内存布局/TDM DMA/SIMD),平台通用 |
| prep/PREP-{DSP-migration,HW-bringup,TST-cyclecount}.md | knowledge_base/ezkit/prep/ | 方法学,平台通用 |

未复制(源侧存在、清单未列):`knowledge_base/ezkit/{INDEX.md,raw/,vendor_docs/}`——如需要 CTO 说一声即补。
