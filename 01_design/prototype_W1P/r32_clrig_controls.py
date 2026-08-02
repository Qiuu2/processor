"""⛔ 已作废:模态合成时代的遗留,仍调用 critical_points(modes, D_EFF)
   而 clrig 早已改为噪声 RIR + FIR 口径 ⇒ **本文件不可运行、不可引用**。
"""
# """r32:闭环台架四条对照 —— **这一步的产物是一把可信的尺子,不是结论**。
# 四条不全过,不进入 ΔMSG 测量。
# [L2/宿主仿真]
# 
# MSG 测量 = **二分 + 显式观察时长 T**(不是爬升):
#   · 爬升把"观察多久"藏在速率里;二分把它变成**显式参数**。
#   · 每个 MSG **必须带 T 一起报**;并做 T vs 2T 敏感性。
#   · 物理上限:稳定环路的建立时间 ∝ 1/(1−|GF|) 发散 ⇒ **MSG 只能测到有限精度,精度由 T 决定**。
# """
# import sys
# sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
# import numpy as np
# import clrig
# import howl_detect as HD
# from clrig import FS
# 
# FRAME = 64
# GR_OFF = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
# 
# 
# def make_src(T_s, seed=0, amp=1e-3):
#     return amp * np.random.default_rng(seed).standard_normal(int(T_s * FS))
# 
# 
# def ref_level_db(proc_factory, G_db, T_s, seed=0):
#     """REF = 同 src、同 G、**断开反馈** 时的输出宽带 RMS。
#     ⇒ 把 G 本身的放大从判据里除掉。"""
#     src = make_src(T_s, seed)
#     proc = proc_factory()
#     n = (len(src) // FRAME) * FRAME
#     out = np.zeros(n)
#     for i in range(0, n, FRAME):
#         blk = src[i:i + FRAME]
#         out[i:i + FRAME] = proc(blk) if proc is not None else blk
#     return HD.rms_db(out)
# 
# 
# def diverges(modes, D, G_db, proc_factory, T_s, seed=0):
#     src = make_src(T_s, seed)
#     lp = clrig.Loop(modes, D, G_db, proc=proc_factory())
#     y = lp.run(src, FRAME)
#     ref = ref_level_db(proc_factory, G_db, T_s, seed)
#     div, lvl, grow = HD.is_divergent(y, ref, T_s, FS)
#     return div, lvl, grow
# 
# 
# def measure_msg(modes, D, proc_factory, T_s, lo=-30.0, hi=40.0, tol=0.25, seed=0):
#     """二分求 MSG:最大的不发散 G。返回 (MSG_dB, 迭代次数)。"""
#     it = 0
#     if diverges(modes, D, lo, proc_factory, T_s, seed)[0]:
#         return float('nan'), 0            # 下界就发散 ⇒ 无法测
#     if not diverges(modes, D, hi, proc_factory, T_s, seed)[0]:
#         return float('inf'), 0            # 上界仍不发散 ⇒ 台架造不出啸叫
#     while hi - lo > tol:
#         mid = 0.5 * (lo + hi); it += 1
#         if diverges(modes, D, mid, proc_factory, T_s, seed)[0]:
#             hi = mid
#         else:
#             lo = mid
#     return lo, it
# 
# 
# print("r32 · 闭环台架四条对照")
# print("[L2/宿主仿真]  MSG = 二分 + 显式观察时长 T;**每个 MSG 必带 T**\n")
# 
# K = 4
# modes, D = clrig.make_F(K=K, D=240)
# D_EFF = D + FRAME          # ★ 块处理引入 1 帧环路延迟
# print(f"F(z):K={K} 模态 {[round(f) for f, _, _ in modes]}Hz  Q=30  D={D} 样本  "
#       f"**D_eff = D + frame = {D_EFF}**")
# 
# # ── 对照③ 退化:N_eff 的可执行定义 vs 旧的(错的)|F| 极大值数
# print("\n【对照③ 退化】N_eff = 相位条件成立的临界频点数(**不是 |F| 极大值数**)")
# fc, mdb = clrig.critical_points(modes, D_EFF)
# print(f"   临界点总数 = {len(fc)}(纯延迟使相位快旋 ⇒ 临界点密集)")
# for m in [1, 3, 6, 10]:
#     print(f"     N_eff(margin={m:>2}dB) = {clrig.n_eff(modes, D_EFF, m):>4}")
# print(f"   对照:|F| 极大值数 = {clrig.n_peaks_absF(modes, D_EFF)}  (= 设定 K = {K})")
# print(f"   ⇒ 两者**不是同一个量**:|F| 极大值数 = K = {K};而 N_eff 随 margin 变化。")
# print(f"   ⇒ **D 直接影响 N_eff**:D={D} 时 N_eff(3dB)={clrig.n_eff(modes, D, 3)},"
#       f" D_eff={D_EFF} 时 = {clrig.n_eff(modes, D_EFF, 3)}")
# 
# # ── 对照④ 解析一致性(纯信号链自检,不涉及 NHS)
# msg_ana, mx = clrig.analytic_msg_db(modes, D_EFF)
# print(f"\n【对照④ 解析一致性】(**纯信号链自检,零 NHS 参与**)")
# print(f"   解析 MSG = −20log10(max{{|F| : ∠F≡0}}) = **{msg_ana:.2f} dB**"
#       f"   (临界点上 max|F| = {mx:.2f} dB)")
# print(f"   对照:若错用 max|F|(不加相位条件)⇒ MSG = "
#       f"{-20*np.log10(np.abs(clrig.F_response(modes, D_EFF)[1]).max()):.2f} dB  ← **会低估**")
# 
# for T in [2.0, 4.0]:
#     msg_m, it = measure_msg(modes, D_EFF, lambda: None, T)
#     d = msg_m - msg_ana if np.isfinite(msg_m) else float('nan')
#     print(f"   实测 MSG(NHS 关, T={T:.0f}s) = {msg_m:>7.2f} dB  "
#           f"(二分 {it} 次)  |差| = {abs(d):.2f} dB  "
#           f"⇒ {'**相符 ✓**' if abs(d) < 1.0 else '**不符 ⇒ 台架有 bug,先修台架**'}")
#     sys.stdout.flush()
# 
# # ── 对照① 阴性:关 NHS 必须起振
# print(f"\n【对照① 阴性】关 NHS,G 扫到上限前**必须起振**")
# for G in [msg_ana - 3, msg_ana + 3, msg_ana + 10]:
#     div, lvl, grow = diverges(modes, D_EFF, G, lambda: None, 3.0)
#     print(f"   G={G:>6.2f}dB ⇒ 发散={str(div):<5} 末段={lvl:>7.1f}dB 增长={grow:>6.2f}dB")
# print(f"   ⇒ {'**台架能造出啸叫 ✓**' if diverges(modes, D_EFF, msg_ana+10, lambda: None, 3.0)[0] else '**⛔ 造不出啸叫 ⇒ 后续全部无效**'}")