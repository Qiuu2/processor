# critic — Memory
> 新项目,从空累积。每次评审记:工单/verdict/关键 findings/是否漏放(事后发现);定期蒸馏进 skill(过另一独立 critic 实例)。
- 出生先验:`ee-agent-team-starter/00_governance/LESSONS_SEED.md`(特别:假绿最危险、自审≠验证、修正稿自带新错)。
- 2026-07-30 R1 工单[配置骨架首审] verdict=FAILED(BLOCKER F-01 PRD 已入手未入库+MAJOR F-02 critic 轮换纪律缺失;MINOR×6/INFO×2)。教训:配置类交付物先查"制度要求别人的事自己做了没"(F-01 即 LESSON-013 同型)。
- 2026-07-30 R2 同工单修正稿复审(同实例,F-02 规①) verdict=PASSED_WITH_MINOR。修正稿自带遗漏实证:F-11 critic/skill.md:9 残留旧 C10 口径且作者自验"grep 0 命中"声明失实(实际 1 命中,grep 实证);F-12 CLAUDE.md:4 PRD 指针未更新。教训:**作者自验的 grep 声明必须自己重跑**(命令+范围+输出可复现才算数),修正稿的"已全修"永远待证。
