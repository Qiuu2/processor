"""⛔ 占位:`modal_rig` 已改名为 `modal_rig_BROKEN_seam16dB`(2026-08-04)。
改名理由 = 警告必须进【文件名】—— 文件头是段落,而段落会被摘掉、不会被 import 的人读到。
缺陷见 FINDINGS.md F81(f_cross 接缝 +16.66 dB 谱密度倾斜 ⇒ 产出的 ΔMSG 全是伪影)。
"""
raise ImportError(
    "modal_rig 已改名 modal_rig_BROKEN_seam16dB —— 该 plant **已知损坏未修**:"
    "f_cross=600 Hz 接缝造成 +16.66 dB 谱密度倾斜,产出的 ΔMSG 全部是伪影(FINDINGS F81)。"
    "⛔ 不得用于任何结论;若只是要**复现伪影证据**,显式 import modal_rig_BROKEN_seam16dB。")
