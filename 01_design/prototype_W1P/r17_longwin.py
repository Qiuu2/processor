"""r16:长窗(100s)同种子双臂 —— 验证 lead 的「弃权代价被 LIFT 吸收」假设。
⚠ 不修改 nhs.py(预注册要求哈希不变);槽位状态迁移在**外部**跟踪。
[L2/宿主仿真·合成料];p̂ 绝对值标 [偏低/待重测];先验不可分依然成立。
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import nhs
import fp_suite as S
from nhs import NHS, FS, FRAME, NotchSlot

TRIAL_S = 100.0          # > 95s 完整回收(HOLD60 + LIFT步5 + reclaim30)
N = 20
GR_OFF = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
HELD = (NotchSlot.ENGAGE, NotchSlot.HOLD, NotchSlot.LIFT)   # "仍挂着"(STANDBY 深度已回 0)


def run_long(mk, seed, abstain_on):
    a = NHS()
    if not abstain_on:
        a.P.probe_floor_M = -999.0
    mat = mk(TRIAL_S, 1000 + seed)
    n = (len(mat) // FRAME) * FRAME
    held_at_6s = None
    prev_state = [s.st for s in a.slots]
    prev_f = [s.f for s in a.slots]
    # 每个槽位「当前占用」的溯源:是否由弃权判决产生、是否经历过 LIFT
    occ_from_abstain = [False] * len(a.slots)
    occ_saw_lift = [False] * len(a.slots)
    n_ab_occ = 0            # 由弃权产生的占用数(分母)
    n_ab_lift = 0           # 其中经历过 LIFT 的(分子)
    seen_c8 = 0
    for i in range(0, n, FRAME):
        a.process_frame(mat[i:i + FRAME], GR_OFF)
        # 新增的 c8 判决 -> 标记对应槽位来源
        while seen_c8 < len(a.c8_log):
            r = a.c8_log[seen_c8]; seen_c8 += 1
            if r['verdict'] != 'abstain':
                continue
            for si, s in enumerate(a.slots):
                if s.st in HELD and abs(s.f - r['f']) < 1.0:
                    if not occ_from_abstain[si]:
                        occ_from_abstain[si] = True
                        occ_saw_lift[si] = False
                        n_ab_occ += 1
                    break
        # 槽位状态迁移
        for si, s in enumerate(a.slots):
            if s.st == NotchSlot.LIFT and prev_state[si] != NotchSlot.LIFT:
                if occ_from_abstain[si] and not occ_saw_lift[si]:
                    occ_saw_lift[si] = True
                    n_ab_lift += 1
            # 槽位被改派(频率变了)或回 FREE ⇒ 该次占用结束
            if s.st == NotchSlot.FREE or abs(s.f - prev_f[si]) > 1.0:
                occ_from_abstain[si] = False
                occ_saw_lift[si] = False
            prev_state[si] = s.st
            prev_f[si] = s.f
        if held_at_6s is None and (i + FRAME) >= int(6.0 * FS):
            held_at_6s = sum(1 for s in a.slots if s.st in HELD)
    held_end = sum(1 for s in a.slots if s.st in HELD)
    c = a.ctr
    return dict(h6=held_at_6s or 0, hend=held_end,
                ab=c.get('c8_abstain', 0), hw=c.get('c8_howl', 0), ex=c.get('c8_ext', 0),
                ab_occ=n_ab_occ, ab_lift=n_ab_lift,
                lift_obs=c.get('lift_obs', 0), lift_ret=c.get('lift_return', 0),
                exh=c.get('exhausted', 0),
                held_end_free=sum(1 for s in a.slots if s.st != NotchSlot.FREE))


print("r17 · 长窗 100s 同种子双臂 —— t_last_hit 刷新条件修法后")
print(f"[L2/宿主仿真·合成料]  试次={TRIAL_S}s(>95s 完整回收)  N={N}/臂")
print("⚠ 功效:N=20 ⇒ 比例量 Wilson 半宽 ≈±0.20@p=0.5,**只能分辨 ~2×**;")
print("   主判用**配对连续量**(窗末累积占用,每试次 0-8),p̂ 仅参考。")
print()
print(f"{'类':<12}{'臂':<14}{'末挂陷@6s':>11}{'窗末累积占用@100s':>14}"
      f"{'弃权数':>8}{'弃权占用':>9}{'其中经LIFT':>11}{'回收比例':>9}{'LIFT观测':>9}{'EXHAUST':>9}{'非FREE@100s':>12}")

for nm, mk in [('钢琴', S.m_piano), ('裸纯音停', S.m_bare_stop)]:
    store = {}
    for on in (True, False):
        acc = dict(h6=0, hend=0, ab=0, ab_occ=0, ab_lift=0, lo=0, exh=0, nf=0)
        for i in range(N):
            r = run_long(mk, i, on)
            acc['h6'] += r['h6']; acc['hend'] += r['hend']
            acc['ab'] += r['ab']; acc['ab_occ'] += r['ab_occ']
            acc['ab_lift'] += r['ab_lift']; acc['lo'] += r['lift_obs']
            acc['exh'] += r['exh']; acc['nf'] += r['held_end_free']
        rec = acc['ab_lift'] / acc['ab_occ'] if acc['ab_occ'] else float('nan')
        store[on] = (acc['h6'] / N, acc['hend'] / N, rec)
        lab = '弃权开(r15)' if on else '弃权关(对照)'
        rs = f"{rec*100:.1f}%" if acc['ab_occ'] else "n/a"
        print(f"{nm:<12}{lab:<14}{acc['h6']/N:>11.2f}{acc['hend']/N:>14.2f}"
              f"{acc['ab']:>8}{acc['ab_occ']:>9}{acc['ab_lift']:>11}{rs:>9}{acc['lo']:>9}{acc['exh']:>9}{acc['nf']/N:>12.2f}")
        sys.stdout.flush()
    d6 = store[True][0] - store[False][0]
    de = store[True][1] - store[False][1]
    print(f"{'':<12}{'⇒ 双臂差':<14}{d6:>+11.2f}{de:>+14.2f}"
          f"   {'**gap 扩大/维持 ⇒ 代价是真的**' if de >= d6 - 0.2 else '**gap 收敛 ⇒ 窗口伪影**'}")
    sys.stdout.flush()
