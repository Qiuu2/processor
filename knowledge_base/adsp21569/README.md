# knowledge_base/adsp21569 — 平台资料库(ADSP-21569,DEC-0006)
> 复制来源与清单:`00_input/DSP_ADSP21569_infocard.md`(2026-07-30 CTO)。资料到位后由 lead 对照清单核对(目录/大小)并在 decisions_log 外部输入台账补登。

## bsp/ — 🟢 第 1 层:ADI 官方料(整包照搬,目录名保持原样)
datasheets/ hw_reference/ app_notes/ sw_reference/ reference_design/ ibis_models/ fira_headers/
- 最小集 ~95M,**不含** a2b/(CTO 确认 2026-07-30:本产品无 A2B 外设,日后出数字麦克风串形态再补)与 installers_windows/(Linux 开发,.deb 在手)。
- 官方文档,与产品无关,不做任何改写。

## platform_lessons/ — 🟡 第 2 层:ITC 项目踩坑平台知识(真金,须去产品化)
bringup/(上板32坑+EZKIT bring-up 清单)｜fira/(FIRA 集成五件套+假绿验证)｜fixed_point/(Q15×Q31→Q46→Q31 饱和原语参考实现)｜cces_template/(.ldf/TDM DMA/SIMD 工程骨架)｜prep/(迁移/bring-up/cycle 方法学)

**入库规则**:
1. 来源注以 `platform_lessons/PROVENANCE.md` 统一承载(原文件逐字节原样,不注入头注保完整性);L 标口径:[L1/ITC同芯片实测,场景迁移待本项目复核]。
2. 去产品化:删除/标注波束成形、阵列几何等 ITC 产品特定段。
3. **禁直装为 skill**:ITC 的 dsp-algorithm SKILL.md 只进本目录当真料仓;进本项目角色 skill §A 必须走蒸馏 SOP(miner→CTO 核→A/B/C→独立 critic→commit),防"披别人的 skill 当本事"。
