# critic — Memory
> 新项目,从空累积。每次评审记:工单/verdict/关键 findings/是否漏放(事后发现);定期蒸馏进 skill(过另一独立 critic 实例)。
- 出生先验:`ee-agent-team-starter/00_governance/LESSONS_SEED.md`(特别:假绿最危险、自审≠验证、修正稿自带新错)。
- 2026-07-30 R1 工单[配置骨架首审] verdict=FAILED(BLOCKER F-01 PRD 已入手未入库+MAJOR F-02 critic 轮换纪律缺失;MINOR×6/INFO×2)。教训:配置类交付物先查"制度要求别人的事自己做了没"(F-01 即 LESSON-013 同型)。
- 2026-07-30 R2 同工单修正稿复审(同实例,F-02 规①) verdict=PASSED_WITH_MINOR。修正稿自带遗漏实证:F-11 critic/skill.md:9 残留旧 C10 口径且作者自验"grep 0 命中"声明失实(实际 1 命中,grep 实证);F-12 CLAUDE.md:4 PRD 指针未更新。教训:**作者自验的 grep 声明必须自己重跑**(命令+范围+输出可复现才算数),修正稿的"已全修"永远待证。
- 2026-07-30 R3 W0 D0 技术雷达首审(全新实例 critic-w0,规②) verdict=PASSED_WITH_MINOR。统计全对上(197=58+73+46+20;131 核验分维 14/16/8/6/11/7/8/10/12/16/13/10;capability 124/5/2 与 JSON 逐项吻合);90 条核验 flags 无一被 D0 遗漏;WebFetch 直抓 6 条主源(SpeexDSP/Monocypher/MbedTLS LICENSE+PR5800/chapro/REW EULA)0 偏差。MINOR×2:Dante「已核」标签不满足 §6.4 自定义(evidence=Wikipedia,条款原文未读);「3 个 unresolved」与 JSON 字段口径(1 unresolved+2 na)对不上。教训:**文献型交付物先抓它自己的两档定义,再专挑 evidence_url 最弱的条目打**(Wikipedia/登录墙/抽查类=「性质核验」混入「已核」档是高发型);高特异性数字(文件数/commit 数/变体数)是转写幻觉最好试纸,本次 9/9 可溯源。闭环:F-01~F-04 落地稿经本实例重跑 grep(0/0/2/0)+四区域目检确认无新错,v1.0 转正 commit 8c08de0,独立门闭环、待 CTO 第三关。
