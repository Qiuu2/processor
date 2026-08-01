# (a') 臂间隙构造算例(adaptive-dsp-2 移交件,2026-08-01)· [L2/桌面数值,确定性无噪]
# 目的:证明三臂豁免可达性表中 case (a') 真实存在——中速跳升轨迹使
#   臂1(当帧 IMSD:快窗 W=4/β_fast=3dB/hop/s_max=1.5dB;长窗 W=8/β_min=0.96/ΔP_min=6)
#   臂2(RAPID_ONSET:≤2 hop 升幅 ≥R_RISE=18dB)
# 双双不中。无噪声即最友好条件(加噪只会抬 s,拒判更稳),故本例为间隙存在性的保守证明。
# 附:R_RISE 敏感性扫描 → "R_RISE 下调是 ROC 第一候选动作"的量化依据。
import numpy as np

BETA_FAST, BETA_MIN, S_MAX, DP_MIN = 3.0, 0.96, 1.5, 6.0
R_RISE, N_RISE = 18.0, 2

def lsfit(y):
    x = np.arange(len(y), dtype=float)
    b, c = np.polyfit(x, y, 1)
    s = np.sqrt(np.mean((y - (b * x + c)) ** 2))
    return b, s, y[-1] - y[0]

def arm1_hits(traj):
    """滑窗扫全轨迹:任一位置快窗或长窗命中即 True(对臂1 最宽容的判法)"""
    hits = []
    for W, cond in [(4, lambda b, s, dP: b >= BETA_FAST and s <= S_MAX),
                    (8, lambda b, s, dP: BETA_MIN <= b and s <= S_MAX and dP >= DP_MIN)]:
        for i in range(len(traj) - W + 1):
            b, s, dP = lsfit(traj[i:i + W])
            if cond(b, s, dP):
                hits.append((W, i, round(b, 2), round(s, 2)))
    return hits

def arm2_hit(traj, r_rise=R_RISE):
    for i in range(len(traj)):
        for j in range(i + 1, min(i + N_RISE, len(traj) - 1) + 1):
            if traj[j] - traj[i] >= r_rise:
                return True
    return False

# 构造:升速 7dB/hop、可见净空 14dB(候选门跨越点→限幅平台),之后平台微纹波
gap_traj = np.array([0.0, 7.0, 14.0, 14.2, 14.1, 14.15, 14.05, 14.1])
print("== (a') 构造例:升速 7dB/hop × 可见净空 14dB,B3 hop=16ms ==")
print("轨迹(PAPR dB,相对候选门跨越点):", gap_traj.tolist())
print("臂1 命中窗(W,起点,b,s):", arm1_hits(gap_traj) or "无 → 臂1 不中")
for i in range(len(gap_traj) - 4 + 1):
    b, s, dP = lsfit(gap_traj[i:i + 4])
    print(f"  快窗@{i}: b={b:+5.2f} s={s:4.2f} dP={dP:+5.1f} -> "
          f"{'HIT' if (b>=BETA_FAST and s<=S_MAX) else 'reject'}")
b, s, dP = lsfit(gap_traj[:8])
print(f"  长窗@0: b={b:+5.2f} s={s:4.2f} dP={dP:+5.1f} -> "
      f"{'HIT' if (BETA_MIN<=b and s<=S_MAX and dP>=DP_MIN) else 'reject'}")
print("臂2 (R_RISE=18):", "HIT" if arm2_hit(gap_traj) else "不中(最大 2-hop 跨度=14dB<18)")
print()

# 间隙域扫描:升速 × 可见净空 → 哪些落入 (a')(臂1、臂2 都不中)
print("== 间隙域扫描(行=升速 dB/hop,列=可见净空 dB;G=间隙,1=臂1收,2=臂2收)==")
headrooms = [8, 10, 12, 14, 16, 18, 20, 24]
print("      " + "".join(f"{h:>5}" for h in headrooms))
for rate in [4, 5, 6, 7, 8, 9, 10, 12]:
    row = []
    for h in headrooms:
        n_rise = int(np.ceil(h / rate))
        tr = np.concatenate([np.arange(0, h, rate), [h] * max(5, 8)])[:12]
        a1 = bool(arm1_hits(tr)); a2 = arm2_hit(tr)
        row.append("1" if a1 else ("2" if a2 else "G"))
    print(f"{rate:>4}  " + "".join(f"{c:>5}" for c in row))
print()
print("== R_RISE 敏感性:同一扫描下 R_RISE=14 与 12 的剩余间隙数 ==")
for rr in [18.0, 14.0, 12.0]:
    n_gap = 0
    for rate in [4, 5, 6, 7, 8, 9, 10, 12]:
        for h in headrooms:
            tr = np.concatenate([np.arange(0, h, rate), [h] * 8])[:12]
            if not arm1_hits(tr) and not arm2_hit(tr, rr):
                n_gap += 1
    print(f"R_RISE={rr:5.1f}dB: 间隙格数 = {n_gap}/64")
print()
print("声明:确定性构造轨迹的存在性/参数敏感性证明,不构成检出率结论;")
print("间隙内轨迹的覆盖=臂3(GR 遥测,IF-v1.2 C11)→ PERSIST,或(无 GR 时)PANIC 机会路径。")
