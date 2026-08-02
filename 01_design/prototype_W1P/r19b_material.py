"""r19b:①素材 vs 系统(λ 衰减归因)②按裁定③改指标:峰值占用 / 到峰时间 / 时长分布。
⚠ 修 r19 的度量 bug:原分箱 round(f/max(f*0.2,15)) 在 f>75Hz 时恒 = 5 ⇒ 所有频点同箱。
   改为**对数频率分箱**(1/5 倍频程,与 bw_oct 一致)。
⚠ 已查证:注册表复检**不刷新 TTL**(代码 + 实测)⇒ 架构侧「永久登记」假说不成立。
⚠ 不再报任何需要稳态假设的量。[L2/宿主仿真·合成料]
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import nhs
import fp_suite as S
from nhs import NHS, FS, FRAME, NotchSlot

GR_OFF = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
HELD = (NotchSlot.ENGAGE, NotchSlot.HOLD, NotchSlot.LIFT)
OCC = HELD + (NotchSlot.STANDBY,)
DUR = 200.0
N = 6


def fbin(f):
    """1/5 倍频程对数分箱(与 bw_oct=1/5 一致)。修 r19 的**分段常数**分箱 bug。
    ⚠ 原式 `round(f / max(f*0.2, 15.0))`:**f ≥ 75Hz 时 = 5(常数);f < 75Hz 时 = f/15(非常数)**
      ⇒ 是**分段常数**,不是全域常数。检测带(120–7800Hz)全在常数段内 ⇒ 结论不变。"""
    return int(round(np.log2(max(f, 20.0)) * 5.0))


def bin_selftest():
    """★ D-L 绝对量前置门:比值判据 R=U/N_mat 的分子分母**共用**分箱函数
    ⇒ 分箱塌缩时 U=N_mat=1 ⇒ **R≡1 ⇒ 判据干净地输出「素材主导」而不报异常**。
    ⇒ 引入比值本为消共模误差,结果连"仪表坏了"这个共模也消掉了。
    ⇒ 故 **R 生效前必须先过三条绝对量门**。返回 (是否通过, 明细)。"""
    msgs = []
    ok = True
    # 门①:f∈[100,8000] 箱号严格不减,且总箱数 > 1
    fs = np.geomspace(100.0, 8000.0, 400)
    bs = [fbin(f) for f in fs]
    mono = all(b2 >= b1 for b1, b2 in zip(bs, bs[1:]))
    nb = len(set(bs))
    msgs.append(f"门①单调不减={mono} 总箱数={nb}(须>1)")
    ok &= mono and nb > 1
    # 门②:N 个已知间隔正弦 ⇒ 箱数须 = N
    probe = [200.0 * (2 ** (k / 2.0)) for k in range(6)]      # 半倍频程间隔,必落不同 1/5 箱
    n_exp, n_got = len(probe), len(set(fbin(f) for f in probe))
    msgs.append(f"门②已知 {n_exp} 音 ⇒ 实得箱数={n_got}(须相等)")
    ok &= (n_got == n_exp)
    return ok, msgs


def trial(mk, seed, dur):
    a = NHS()
    mat = mk(dur, 1000 + seed)
    n = (len(mat) // FRAME) * FRAME
    occ_t, held_t, ts = [], [], []
    cur = [None] * len(a.slots)
    recs = []
    ab_times = []
    seen_ev = 0
    pre_f = set()
    for i in range(0, n, FRAME):
        a.process_frame(mat[i:i + FRAME], GR_OFF)
        while seen_ev < len(a.events):
            e = a.events[seen_ev]; seen_ev += 1
            if e[1] == 'preempt':
                pre_f.add(round(e[2], 0))
        for si, s in enumerate(a.slots):
            occupied = s.st in OCC
            reass = occupied and cur[si] is not None and abs(s.f - cur[si][3]) > 1.0
            if cur[si] is not None and (not occupied or reass):
                why = ('preempt' if round(s.f, 0) in pre_f else 'reassign') if reass \
                      else ('lift' if cur[si][2] else 'other')
                recs.append((a.t_wall - cur[si][0], why, cur[si][1]))
                cur[si] = None
            if occupied and cur[si] is None:
                cur[si] = [a.t_wall, s.from_abstain, False, s.f]
            if cur[si] is not None:
                if s.from_abstain:
                    cur[si][1] = True
                if s.st == NotchSlot.LIFT:
                    cur[si][2] = True
        if i % (FRAME * 12) == 0:
            ts.append(a.t_wall)
            occ_t.append(sum(1 for s in a.slots if s.st in OCC))
            held_t.append(sum(1 for s in a.slots if s.st in HELD))
    for si in range(len(a.slots)):
        if cur[si] is not None:
            recs.append((a.t_wall - cur[si][0], 'CENSORED', cur[si][1]))
    fs = [e[2] for e in a.events if 'engage' in str(e[1])]
    # 弃权到达时刻(用 c8_log 顺序近似 —— 每条 abstain 记录对应一次到达)
    n_ab = sum(1 for r in a.c8_log if r['verdict'] == 'abstain')
    return dict(ts=np.array(ts), occ=np.array(occ_t), held=np.array(held_t),
                recs=recs, nab=n_ab, fbins=set(fbin(f) for f in fs), neng=len(fs))


# ★ D-L 门①②:R 生效前必须先过绝对量自检
_ok, _msgs = bin_selftest()
print("【分箱自检(D-L 前置门)】" + ("**通过**" if _ok else "**故障 ⇒ 拒绝输出 R,任何"素材主导"结论无效**"))
for _m in _msgs:
    print("   " + _m)
if not _ok:
    print("⛔ 分箱仪表故障 ⇒ **本轮不得输出 R,也不得读作素材枯竭**")
    sys.exit(1)
print()

print("r19b · 素材 vs 系统(λ 归因)+ 新指标(峰值/到峰/时长分布)")
print(f"[L2/宿主仿真·合成料]  窗={DUR:.0f}s  N={N}")
print("⚠ 已查证:注册表复检**不刷新 TTL**(代码+实测)⇒「永久登记」假说**不成立**")
print("⚠ 修 r19 度量 bug:频点分箱原为恒定值,现改 1/5 倍频程对数分箱")
print("⚠ **不报任何需要稳态假设的量**\n")

print(f"{'素材':<10}{'峰值占用OCC':>12}{'到峰时间s':>10}{'峰值HELD':>10}"
      f"{'不同频点箱':>11}{'挂陷次数':>9}{'弃权数':>8}{'λ整窗/s':>10}")
store = {}
for nm, mk in [('钢琴', S.m_piano), ('多人交谈', S.m_multitalk), ('空调', S.m_hvac)]:
    peaks, tpk, pkh, nb, ne, na, allrec = [], [], [], set(), 0, 0, []
    for i in range(N):
        r = trial(mk, i, DUR)
        peaks.append(r['occ'].max()); tpk.append(float(r['ts'][int(np.argmax(r['occ']))]))
        pkh.append(r['held'].max()); nb |= r['fbins']; ne += r['neng']; na += r['nab']
        allrec += r['recs']
    store[nm] = allrec
    _gate3 = "" if len(nb) > 2 else "  ⛔**门③:N_mat≤2 判仪表故障,不得读作素材枯竭**"
    print(f"{nm:<10}{np.mean(peaks):>12.2f}{np.mean(tpk):>10.1f}{np.mean(pkh):>10.2f}"
          f"{len(nb):>11}{ne:>9}{na:>8}{na/(N*DUR):>10.4f}{_gate3}")
    sys.stdout.flush()

print("\n" + "=" * 84)
print("【占用时长分布】按释放原因分列 + 显式截尾(不需任何模型)")
from collections import Counter
for nm, recs in store.items():
    ab = [r for r in recs if r[2]]
    if not ab:
        print(f"  {nm}: 弃权占用 0 段 ⇒ **未触达,无结论**"); continue
    cens = [r for r in ab if r[1] == 'CENSORED']
    unc = [r for r in ab if r[1] != 'CENSORED']
    print(f"  {nm}: 弃权占用 {len(ab)} 段,**截尾 {len(cens)} 段 = {len(cens)/len(ab)*100:.0f}%**")
    if unc:
        d = np.array([r[0] for r in unc])
        cnt = Counter(r[1] for r in unc)
        print(f"     未截尾 n={len(unc)}  p10={np.percentile(d,10):.1f}s "
              f"p50={np.percentile(d,50):.1f}s p90={np.percentile(d,90):.1f}s")
        print(f"     释放原因: " + "  ".join(f"{k}={v}" for k, v in cnt.most_common()))
    if cens:
        dc = np.array([r[0] for r in cens])
        print(f"     ⚠ 截尾段观测 p50={np.percentile(dc,50):.1f}s —— **真实 ≥ 此值,不并入均值**")
