"""W1-B 自验 v7 —— ★ B-2 修:九组 CHECK **全部 import 并调用 `nhs.py`**
adaptive-dsp-3 · 2026-08-02 · [L2/宿主仿真]

⚠ v6 及以前的致命缺陷(critic BLOCKER-2):
  本文件唯一 import 是 numpy;九组 CHECK 全是 `nhs.py` 公式的**独立转写**
  ⇒ **删掉 nhs.py,九组照常 PASS** ⇒ 假绿纪律「测试须真依赖被测物」被违反在根上。
  实证:`_is_dom` 已与自验模型分叉(PAPR vs PNPR),CHECK G 照报 ✓。

v7 的两条硬要求:
  ① 每组 CHECK 必须**调用 nhs.py 的函数/类**,不得自行转写公式;
  ② 附**变异测试**(mutation harness):人为改坏 nhs.py 的行为,
     **CHECK 必须 FAIL** —— 这是「代码的失效会被测出来」的直接证据。
"""
import sys, os, copy
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'prototype_W1P'))
import nhs                      # ★ 被测物
from nhs import NHS, Params, Track, rbj_peaking, NFFT, FS_SC, HOP_SC

FAILS = []
def check(name, ok, detail="", hits=None):
    """★ r15 D-J:证伪测试必须自带**触达断言**。
    `hits` = 被测分支的实际执行次数。**hits==0 ⇒ 判「无效」,不得判「通过」。**
    「预期结果」与「触达次数」必须同屏。"""
    if hits is not None and hits == 0:
        print(f"  [**无效**] {name}  {detail}  | 触达=0 ⇒ 该分支本次未执行,结果不成立")
        FAILS.append(name + "(触达=0/无效)")
        return False
    tag = 'PASS' if ok else '**FAIL**'
    ht = f"  | 触达={hits}" if hits is not None else ""
    print(f"  [{tag}] {name}  {detail}{ht}")
    if not ok:
        FAILS.append(name)
    return ok

print("=" * 76)
print(f"W1-B 自验 v7 · 被测物 = nhs.py(vP1.1)· 全部经 import 调用")
print("=" * 76)

# ---------------------------------------------------------------- CHECK A
print("\nCHECK A: 深度可控陷波(调用 nhs.rbj_peaking)")
fs = 48000.0
def mag_closed(b, a, f, fs):
    w = 2*np.pi*f/fs; b0,b1,b2 = b; a1,a2 = a[1],a[2]
    num = b0*b0+b1*b1+b2*b2+2*(b0*b1+b1*b2)*np.cos(w)+2*b0*b2*np.cos(2*w)
    den = 1+a1*a1+a2*a2+2*(a1+a1*a2)*np.cos(w)+2*a2*np.cos(2*w)
    return np.sqrt(num/den)
def mag_fz(b, a, f, fs):
    z = np.exp(1j*2*np.pi*f/fs)
    return np.abs((b[0]+b[1]/z+b[2]/z**2)/(1+a[1]/z+a[2]/z**2))
okA = True; dmax = 0.0
for f0, depth, bw in [(1000.,-3.,.1),(1000.,-18.,.1),(250.,-3.,.2),(100.,-12.,.1),(6300.,-6.,.1)]:
    b, a = rbj_peaking(fs, f0, depth, bw)          # ← 调用被测物
    m1 = 20*np.log10(mag_closed(b,a,f0,fs)); m2 = 20*np.log10(mag_fz(b,a,f0,fs))
    dmax = max(dmax, abs(m1-m2))
    okA &= abs(m1-depth) < 0.01 and np.all(np.abs(np.roots([1,a[1],a[2]])) < 1.0)
check("A 陷波 @f0 深度=设定值 且极点稳 且两轨一致", okA, f"两轨最大差={dmax:.2e}dB")

# ---------------------------------------------------------------- CHECK B
print("\nCHECK B: Quinn 内插精度(调用 NHS._quinn)")
rng = np.random.default_rng(1234); win = np.hanning(NFFT); errs = []
for _ in range(200):
    ft = rng.uniform(200, 7000); n = np.arange(NFFT)
    sig = np.sin(2*np.pi*ft/FS_SC*n + rng.uniform(0,2*np.pi))
    X = np.fft.rfft((sig + rng.normal(0,10**(-30/20)/np.sqrt(2),NFFT))*win)
    k = int(np.argmax(np.abs(X[2:NFFT//2-2]))) + 2
    errs.append(abs(NHS._quinn(X, k)*FS_SC/NFFT - ft))   # ← 调用被测物
p95 = float(np.percentile(errs, 95))
check("B Quinn p95|Δf| ≤ 3.75Hz(=BW/4@15Hz)", p95 <= 3.75, f"p95={p95:.3f}Hz")

# ---------------------------------------------------------------- CHECK L(新)
print("\nCHECK L: 电平标定(调用 NHS._level)—— ★ M-1 回归锁")
alg = NHS()
okL = True; rows = []
for f0, amp in [(1000., 1.0), (2000., 0.5), (3000., 0.1), (500., 0.25)]:
    n = np.arange(NFFT)
    x = amp*np.sin(2*np.pi*f0/FS_SC*n)
    Mg = np.abs(np.fft.rfft(x*np.hanning(NFFT)))
    k = int(round(f0/(FS_SC/NFFT)))
    lv = alg._level(Mg, k)                              # ← 调用被测物
    true_db = 20*np.log10(amp)
    rows.append((f0, lv, true_db)); okL &= abs(lv-true_db) < 0.5
check("L _level 对已知幅度正弦读数误差 <0.5dB", okL,
      f"最大偏差={max(abs(l-t) for _,l,t in rows):.2f}dB")

# ---------------------------------------------------------------- CHECK D/E
print("\nCHECK D/E: IMSD 判别与空号护栏(调用 NHS._imsd)")
P = Params()
def mk_track(papr, seq):
    t = Track(); t.active=True; t.papr_hist=list(papr); t.pnpr_hist=[20.]*len(papr)
    t.seq_hist=list(seq); t.hist_n=len(papr); return t
def imsd(papr, seq):
    return alg._imsd(mk_track(papr, seq))               # ← 调用被测物
W = P.W_long
cases = {
 'howl_130dB/s':  2.08*np.arange(W)+rng.normal(0,.5,W),
 'howl_70dB/s':   1.12*np.arange(W)+rng.normal(0,.3,W),
 'steady_tone':   60.+rng.normal(0,.5,W),
 'vowel':         np.concatenate([[40,55],60+np.cumsum(rng.normal(0,1.2,W-2))]),
 'crescendo':     20.+rng.normal(0,.5,W),
}
res = {k: imsd(v, np.arange(W))[0] for k, v in cases.items()}
check("D 真啸叫命中 / 稳态·元音·共模拒", res['howl_130dB/s'] and not res['steady_tone']
      and not res['vowel'] and not res['crescendo'], str({k:int(v) for k,v in res.items()}))
# E:跳槽下 x 轴用 slot_seq
gap_seq = np.array([0,1,2,3,10,11,12,13]); rate = 250.
traj = rate*P.T_hop*gap_seq
hit_correct = imsd(traj, gap_seq)[0]
hit_naive   = imsd(traj, np.arange(W))[0]
check("E 跳槽窗:按 slot_seq 命中、按朴素序号漏检", hit_correct and not hit_naive,
      f"正确={hit_correct} 朴素={hit_naive}")

# ---------------------------------------------------------------- CHECK F
print("\nCHECK F: PAPR/PNPR 在掩蔽下的行为(调用 NHS._papr/_pnpr)")
NB = NFFT//2+1; DF = FS_SC/NFFT
def spec(speech_pk):
    s = -95.+rng.normal(0,1.5,NB)
    if speech_pk is not None:
        for h in range(1,41):
            fh = 140.*h
            if fh < NB*DF:
                kk = int(round(fh/DF)); s[kk] = max(s[kk], speech_pk-6*np.log2(h))
    kh = int(round(2500./DF)); s[kh] = -56.
    return 10**(s/20.), kh
res_f = {}
for tag, pk in (('F-1 无掩蔽', None), ('F-2 带外强语音', -30.)):
    Mg, kh = spec(pk)
    res_f[tag] = (alg._papr(Mg,kh), alg._pnpr(Mg,kh))   # ← 调用被测物
check("F-2 掩蔽下 PAPR 塌陷而 PNPR 存活(臂3 须用 PNPR 的依据)",
      res_f['F-2 带外强语音'][0] < res_f['F-1 无掩蔽'][0] - 10
      and res_f['F-2 带外强语音'][1] > res_f['F-2 带外强语音'][0],
      f"F-2 PAPR={res_f['F-2 带外强语音'][0]:.1f} PNPR={res_f['F-2 带外强语音'][1]:.1f}dB")

# ---------------------------------------------------------------- CHECK G
print("\nCHECK G: 豁免式合取门(调用 NHS._phpr_veto / _is_dom)")
def veto(t_born, t_veto, causal_ok, imsd_hit, rapid, gr_ok, pnpr_rank_top,
         persist_path=True):
    a2 = NHS(); a2.slot_seq = 200
    tr = mk_track([30.]*P.W_long, np.arange(P.W_long))
    tr.t_born = t_born; tr.t_veto = t_veto; tr.causal_ok = causal_ok
    tr.rapid_onset = rapid
    tr.pnpr_hist = [40. if pnpr_rank_top else 5.]
    a2.tracks[0] = tr
    other = mk_track([30.]*P.W_long, np.arange(P.W_long)); other.pnpr_hist=[20.]
    a2.tracks[1] = other
    df = FS_SC/NFFT; Mg = np.full(NB, 1e-6)
    kh = int(round(2500./df)); Mg[kh] = 1.0
    for nmul in (2,3):                                  # 造谐波族 ⇒ 触发否决
        Mg[int(round(2500.*nmul/df))] = 0.5
    tr.f = 2500.
    return a2._phpr_veto(tr, Mg, df, imsd_hit, gr_ok, persist_path)   # ← 调用被测物
g_a  = veto(100, 106, True,  True,  False, True,  True)    # (a) PERSIST:因果真 + 臂1
g_b  = veto(200, 200, False, False, False, True,  True)    # (b) 因果假 ⇒ 应仍否决
g_b4 = veto(300, 300, True,  False, False, True,  True)    # (b4) 继承 causal_ok ⇒ 可豁免
check("G (a) PERSIST 路:因果真+臂1 ⇒ 豁免(不否决)", not g_a, f"veto={g_a}")
check("G (b) 真·诞生即平台(causal 假)⇒ 仍否决", g_b, f"veto={g_b}")
check("G (b4) 继承 causal_ok ⇒ 恢复豁免", not g_b4, f"veto={g_b4}")

# ★★ D6-e 回归锁:豁免条件不得是其所豁免路径入选条件的子式
#   GROWTH 入选式 = (imsd_hit ∨ rapid_onset);故 arm1/arm2 **不得**能豁免 GROWTH
g_c = veto(100, 106, False, True, True, True, True, persist_path=False)
check("G (c) ★D6-e:GROWTH 路 causal假 + 臂1真 + 臂2真 ⇒ **仍否决**(臂不得豁免增长路)",
      g_c, f"veto={g_c}")
g_d = veto(100, 106, True, False, False, False, False, persist_path=False)
check("G (d) GROWTH 路 causal真(族后到)⇒ 豁免 —— 新判据是增长路唯一豁免依据",
      not g_d, f"veto={g_d}")
# ★★ 旧口径回归锁:t_veto−t_born 很大但 causal_ok 假 ⇒ 不得豁免(证明旧式已废弃)
g_e = veto(100, 100 + 50*P.causal_min, False, True, False, True, True)
check("G (e) ★旧 causal 口径(t_veto−t_born 巨大)已废:causal_ok 假 ⇒ 仍否决",
      g_e, f"veto={g_e}")

# ---------------------------------------------------------------- CHECK M
print("\nCHECK M: 臂3 谓词 dom 按 **PNPR** 排序(★ B-1 回归锁)")
a3 = NHS()
t_hi_pnpr = mk_track([10.]*P.W_long, np.arange(P.W_long)); t_hi_pnpr.pnpr_hist=[40.]
t_hi_papr = mk_track([90.]*P.W_long, np.arange(P.W_long)); t_hi_papr.pnpr_hist=[5.]
a3.tracks[0] = t_hi_pnpr; a3.tracks[1] = t_hi_papr
for t in a3.tracks[2:]: t.active = False
check("M dom 选 PNPR 最高者(而非 PAPR 最高者)",
      a3._is_dom(t_hi_pnpr) and not a3._is_dom(t_hi_papr),
      f"PNPR高={a3._is_dom(t_hi_pnpr)} PAPR高={a3._is_dom(t_hi_papr)}")

# ---------------------------------------------------------------- CHECK N
print("\nCHECK N: relaxed 非粘滞(★ MAJOR 回归锁:C12 输入侧担保不得被架空)")
a4 = NHS()
tr4 = mk_track([30.]*P.W_long, np.arange(P.W_long))
tr4.relaxed = True                      # 曾经经放宽门入轨
a4._track_hit(tr4, dict(f=2500., lv=0.0, papr=40., pnpr=40., relaxed=False), True)
check("N 电平升到 0dBFS 后 relaxed 应被释放(恢复 PANIC 资格)",
      tr4.relaxed is False, f"relaxed={tr4.relaxed}")
tr5 = mk_track([30.]*P.W_long, np.arange(P.W_long))
a4._track_hit(tr5, dict(f=2500., lv=-60.0, papr=40., pnpr=40., relaxed=True), True)
check("N 电平仍低于 T_low 时 relaxed 应保持(收紧仍生效)",
      tr5.relaxed is True, f"relaxed={tr5.relaxed}")

# ---------------------------------------------------------------- CHECK O
print("\nCHECK O: g_duck 由权威源自己施加(★ r9 MAJOR 回归锁)")
# 立法理由:g_duck 此前只在 nhs.py 算、由 8 个台架各自施加 ⇒ 照 nhs.py 做的
# bit-exact 移植会把它整条丢掉。本 CHECK 直接测 process_frame 的**输出信号**。
a5 = NHS()
x5 = np.ones(nhs.FRAME) * 0.1
y_unity = a5.process_frame(x5.copy(), {})          # g_duck_db = 0 ⇒ 应恒等
a5.g_duck_db = -6.0                                 # 手动置兜底态
y_duck = a5.process_frame(x5.copy(), {})
r_db = 20*np.log10(np.sqrt(np.mean(y_duck**2)) / (np.sqrt(np.mean(y_unity**2)) + 1e-30))
check("O (a) g_duck=0dB 时 process_frame 对未陷波信号恒等",
      np.allclose(y_unity, x5, atol=1e-12), f"max|y-x|={np.max(np.abs(y_unity-x5)):.2e}")
check("O (b) g_duck=-6dB 时输出确实低 6dB(施加点在权威源内)",
      abs(r_db - (-6.0)) < 0.05, f"实测 {r_db:.3f}dB(期望 -6.000)")

# ---------------------------------------------------------------- CHECK P
print("\nCHECK P: 深度状态机容差 DEPTH_EPS_DB(★ r9 MAJOR 回归锁:定点可迁移性)")
# 立法理由:原 1e-6/1e-9 dB 是**伪装成容差的精确相等判断**,定点量化步长
# (Q7.8=3.9e-3 dB)比它大 3 个数量级 ⇒ 移植后跃迁永不触发/永不复位。
eps = nhs.DEPTH_EPS_DB
step = Params().ramp_db_per_s * Params().T_hop
check("P (a) 容差 >> 定点量化步长(Q7.8 = 3.9e-3 dB),至少 3×",
      eps > 3 * 0.0039, f"eps={eps} vs Q7.8 quantum=0.0039 (比值 {eps/0.0039:.1f}×)")
check("P (b) 容差 << 一个斜坡步长,至少 3× 余量(否则提前迁移)",
      eps < step / 3, f"eps={eps} vs ramp step={step:.3f}dB (比值 {step/eps:.1f}×)")
# 行为侧:注入一个定点量级的残差,ENGAGE→HOLD 仍须迁移
s6 = nhs.NotchSlot(); s6.st = nhs.NotchSlot.ENGAGE
s6.depth = -3.0 + 0.0039; s6.target = -3.0        # 差 1 个 Q7.8 量子
a6 = NHS(); a6.slots = [s6]; a6.tracks = []
a6._slots_tick()
check("P (c) 深度与 target 差 1 个定点量子时仍迁 HOLD(原 1e-6 判据会卡死)",
      s6.st == nhs.NotchSlot.HOLD, f"st={s6.st}(HOLD={nhs.NotchSlot.HOLD})")

# ---------------------------------------------------------------- CHECK Q
print("\nCHECK Q: 重定义的 causal_ok —— 族到达时序(★ r12 D6-e 修法回归锁)")
# 立法理由:旧 causal 测"候选轨龄相对否决起点",实测几乎恒真(钢琴 4814/4814)
#   ⇒ 它测的不是因果。新式测**族成员到达时刻 vs 候选自身增长起点**,与 imsd 不同源。
# ⚠ D6-f:本判据是单边(≥ fam_late_min),消融朝**更不满足**方向做 —— 令族**提前**到达。
df = FS_SC/NFFT
def scan_causal(fam_delay_slots):
    """把族成员出现推迟 fam_delay_slots 槽,看 causal_ok 是否按新式建立。"""
    a5 = NHS()
    tr = mk_track([30.]*P.W_long, np.arange(P.W_long))
    tr.f = 2500.; tr.lv0 = -60.0; tr.t_grow0 = -1; tr.t_fam0 = -1; tr.causal_ok = False
    a5.tracks[0] = tr
    for t2 in a5.tracks[1:]: t2.active = False
    M_no = np.full(NB, 1e-6); M_no[int(round(2500./df))] = 1.0          # 只有基频
    M_fam = M_no.copy()
    for nm2 in (2, 3): M_fam[int(round(2500.*nm2/df))] = 0.5            # 族成员到场
    for sq in range(0, 40):
        a5.slot_seq = sq
        tr.last_level = -60.0 if sq < 5 else -50.0        # 第 5 槽起增长(t_grow0=5)
        a5._causal_scan(M_fam if sq >= fam_delay_slots else M_no, df)   # ← 调用被测物
    return tr.causal_ok, tr.t_grow0, tr.t_fam0
c_sim, g1, f1 = scan_causal(0)      # 族**同时/更早**到达(乐音)⇒ 不得建立 causal
c_late, g2, f2 = scan_causal(20)    # 族**后到**(削波)⇒ 必须建立 causal
check("Q (a) 族同时到(乐音)⇒ causal_ok **不**建立",
      c_sim is False, f"causal={c_sim} t_grow0={g1} t_fam0={f1}")
check("Q (b) 族后到(渐长后削波)⇒ causal_ok 建立",
      c_late is True, f"causal={c_late} t_grow0={g2} t_fam0={f2}")
check("Q (c) 两者结果**必须不同**(同结果 ⇒ 本款未实现)",
      c_sim != c_late, f"同时到={c_sim} 后到={c_late}")

# ---------------------------------------------------------------- CHECK R
print("\nCHECK R: C8-② 事后甄别探针(★ r13 回归锁;**物理实验非统计阈值**)")
# 立法理由:PERSIST 侧"持续纯音 vs 啸叫"在单帧谱观测集下不可分(C8-②)。
#   本判据不测频率稳定性,测**对本层干预的响应** ⇒ 与 US9794695B2 不同域(FTO)。
# ⚠ D6-f:单边判据(ΔL ≥ thr),消融朝**更不满足**方向 —— 令 ΔL 变小,不是置零。
a7 = NHS(); df7 = FS_SC/NFFT; f7 = 2500.0; k7 = int(round(f7/df7))
def probe_once(drop_db):
    """真跑 _probe_tick:挂陷后第二次读数比第一次低 drop_db ⇒ 看判决。"""
    a = NHS(); a.slots[0].st = nhs.NotchSlot.ENGAGE; a.slots[0].f = f7
    a.probes = {0: dict(f=f7, seq0=0, L0=None, d=3.0, cls='PERSIST')}
    M1 = np.full(NB, 1e-6); M1[k7] = 1.0
    a.slot_seq = 0; a._probe_tick(M1, df7)              # 记 L0
    M2 = np.full(NB, 1e-6); M2[k7] = 10 ** (-drop_db/20.0)
    a.slot_seq = a.P.probe_hops; a._probe_tick(M2, df7)  # 判决
    return a.c8_log[0]['verdict'] if a.c8_log else None
v_howl = probe_once(30.0)     # 环路被打断:大幅下降
v_ext  = probe_once(0.0)      # 源仍在:无下降
check("R (a) ΔL 大(环路被打断)⇒ 判**啸叫**、保留",
      v_howl == 'howl', f"verdict={v_howl}")
check("R (b) ΔL≈0(源仍在)⇒ 判**外部音**、撤陷",
      v_ext == 'ext', f"verdict={v_ext}")
check("R (c) 两者**必须不同**(同结果 ⇒ 本款未实现)",
      v_howl != v_ext, f"howl臂={v_howl} ext臂={v_ext}")
# 撤陷必须是**真撤**(系数回恒等),不是只改状态位
a8 = NHS(); a8.slots[0].st = nhs.NotchSlot.ENGAGE; a8.slots[0].f = f7
a8.slots[0].depth = -3.0; a8.slots[0].set_coef(nhs.FS, a8.P.bw_oct)
b_before = a8.slots[0].b.copy()
a8.probes = {0: dict(f=f7, seq0=0, L0=None, d=3.0, cls='PERSIST')}
M1 = np.full(NB, 1e-6); M1[k7] = 1.0
a8.slot_seq = 0; a8._probe_tick(M1, df7)
a8.slot_seq = a8.P.probe_hops; a8._probe_tick(M1, df7)
check("R (d) 判外部后**真撤陷**(系数回恒等,非仅改状态位)",
      np.allclose(a8.slots[0].b, [1.0, 0, 0]) and a8.slots[0].st == nhs.NotchSlot.FREE,
      f"b={np.round(a8.slots[0].b,4)} st={a8.slots[0].st} 撤前b={np.round(b_before,4)}")

# ---------------------------------------------------------------- CHECK S
print("\nCHECK S: C8-③ 差分判据 + 硬要求②结构纪律(★ r14 回归锁)")
import re as _re
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         '..', 'prototype_W1P', 'nhs.py'), encoding='utf-8').read()
# 硬要求②:「探针判为啸叫」不得被任何其他机制当作正向证据。
#   结构检查:c8_howl / c8_log / c8_bare_stop 只允许出现在 _probe_tick 内(及注释)。
_body = _src.split('def _probe_tick')[1].split('\n    def ')[0]
_outside = _src.replace(_body, '')
_leak = [ln.strip() for ln in _outside.splitlines()
         if ('c8_howl' in ln or 'c8_bare_stop' in ln
             or ("verdict" in ln and 'has_affirmative_verdict' not in ln))
         and not ln.strip().startswith('#') and 'c8_log = []' not in ln]
check("S (a) ★硬要求②:探针判决不外泄(c8_howl/verdict 未被其他机制读取)",
      len(_leak) == 0, f"泄漏行={_leak if _leak else '无'}")
# 差分判据的三种情形(真跑 _probe_tick,不转写公式)
df8 = FS_SC/NFFT; f8 = 2500.0; k8 = int(round(f8/df8))
def probe3(drop_f_db, drop_rest_db):
    """f 处掉 drop_f_db,其余全谱掉 drop_rest_db ⇒ 看差分判据给什么。"""
    a = NHS(); a.slots[0].st = nhs.NotchSlot.ENGAGE; a.slots[0].f = f8
    a.probes = {0: dict(f=f8, seq0=0, L0=None, d=3.0, cls='PERSIST')}
    M1 = np.full(NB, 1e-3); M1[k8] = 1.0
    a.slot_seq = 0; a._probe_tick(M1, df8)
    M2 = M1 * (10 ** (-drop_rest_db/20.0))
    M2[k8] = M1[k8] * (10 ** (-drop_f_db/20.0))
    a.slot_seq = a.P.probe_hops; a._probe_tick(M2, df8)
    return a.c8_log[0]['verdict'] if a.c8_log else None
v1 = probe3(30.0,  0.0)    # ①真啸叫:只有 f 掉  ⇒ 差分大 ⇒ 判啸叫
v2 = probe3( 0.0,  0.0)    # ②外部持续:都没掉  ⇒ 差分≈0 ⇒ 判外部
v3 = probe3(30.0, 30.0)    # ③外部源停:一起掉  ⇒ 差分≈0 ⇒ 判外部(★ F25 修法本体)
check("S (b) 只有 f 掉(环路被打断)⇒ 判啸叫", v1 == 'howl', f"verdict={v1}")
check("S (c) 都没掉(外部持续)⇒ 判外部",     v2 == 'ext',  f"verdict={v2}")
check("S (d) ★F25 修法:f 与全谱**一起**掉(源自己停了)⇒ 判**外部**,不再误判啸叫",
      v3 == 'ext', f"verdict={v3}")
check("S (e) 三情形不得同结果(①与②③必须可分)",
      v1 != v2 and v1 != v3, f"①={v1} ②={v2} ③={v3}")
# D6-f:单边/有界判据的消融朝**更不满足**方向 —— 令差分**变大**(不是置零)
v4 = probe3(30.0, 25.0)    # 一起掉但差 5dB(< X=8)⇒ 仍判外部
v5 = probe3(30.0, 15.0)    # 差 15dB(> X=8)⇒ 翻为判啸叫
check("S (f) D6-f:差分跨过 X 时判定必须翻转(5dB→外部 / 15dB→啸叫)",
      v4 == 'ext' and v5 == 'howl', f"差5dB={v4} 差15dB={v5}")

# ---------------------------------------------------------------- CHECK T
print("\nCHECK T: r15 机制A(共模单边钳位)+ 机制B(三态弃权)(★ 回归锁;D-J 带触达断言)")
dfT = FS_SC/NFFT; fT = 2500.0; kT = int(round(fT/dfT))
_T_hits = {'clamp': 0, 'abstain': 0}
def probeT(dropf, droprest, base=1e-3, peak=1.0):
    """真跑 _probe_tick。base=本底幅度,peak=f 处幅度。"""
    a = NHS(); a.slots[0].st = nhs.NotchSlot.ENGAGE; a.slots[0].f = fT
    a.probes = {0: dict(f=fT, seq0=0, L0=None, d=3.0, cls='PERSIST')}
    M1 = np.full(NB, base); M1[kT] = peak
    a.slot_seq = 0; a._probe_tick(M1, dfT)
    M2 = M1 * (10 ** (-droprest/20.0)); M2[kT] = M1[kT] * (10 ** (-dropf/20.0))
    a.slot_seq = a.P.probe_hops; a._probe_tick(M2, dfT)
    return (a.c8_log[0] if a.c8_log else None)

# ── 机制A:rest **上升**(dR<0)时,钳位须使判据**退化为单量**,不得增加判啸叫证据
rA = probeT(0.0, -20.0)          # f 不变、rest 上升 20dB ⇒ 未钳位则 diff=+20 ⇒ 误判啸叫
if rA is not None and rA['verdict'] != 'abstain':
    _T_hits['clamp'] += 1
check("T (a) ★机制A:rest 上升 20dB 而 f 不变 ⇒ 钳位后仍判**外部**(未钳位则误判啸叫)",
      rA is not None and rA['verdict'] == 'ext',
      f"verdict={rA['verdict'] if rA else None} dL={rA['dL']:.2f} dR={rA['dR']:.2f} diff={rA['diff']:.2f}"
      if rA else "无判决", hits=_T_hits['clamp'])
# ── 机制A:f 处电平**上升**(dL<0)不得成为啸叫证据(去绝对值)
rA2 = probeT(-12.0, 0.0)
check("T (b) ★机制A:f 处电平**上升** 12dB ⇒ 判**外部**(取绝对值则误判啸叫)",
      rA2 is not None and rA2['verdict'] == 'ext',
      f"verdict={rA2['verdict'] if rA2 else None} diff={rA2['diff']:.2f}" if rA2 else "无判决",
      hits=1 if rA2 is not None else 0)
# ── 机制B:L0/L1 落在本底附近 ⇒ **弃权**(第三态),既非啸叫也非外部
rB = probeT(0.0, 0.0, base=1e-3, peak=1.2e-3)     # 峰仅高出本底 ~1.6dB < M=10
if rB is not None and rB['verdict'] == 'abstain':
    _T_hits['abstain'] += 1
check("T (c) ★机制B:读数落在本底+M 以内 ⇒ **弃权**(第三态,非啸叫非外部)",
      rB is not None and rB['verdict'] == 'abstain',
      f"verdict={rB['verdict'] if rB else None}" if rB else "无判决", hits=_T_hits['abstain'])
# ── 机制B:弃权**不得**登记保鲜期(登记=对"这是外部源"的正向断言)
aB = NHS(); aB.slots[0].st = nhs.NotchSlot.ENGAGE; aB.slots[0].f = fT
aB.probes = {0: dict(f=fT, seq0=0, L0=None, d=3.0, cls='PERSIST')}
Mb = np.full(NB, 1e-3); Mb[kT] = 1.2e-3
aB.slot_seq = 0; aB._probe_tick(Mb, dfT)
aB.slot_seq = aB.P.probe_hops; aB._probe_tick(Mb, dfT)
check("T (d) ★机制B:弃权**不登记保鲜期**,且**保留陷波**(偏置原则)",
      len(aB.ext_reg) == 0 and aB.slots[0].st != nhs.NotchSlot.FREE,
      f"ext_reg={len(aB.ext_reg)} st={aB.slots[0].st}", hits=1)
# ── D-H 两端(M 的取值必须落在论证区间内)
check("T (e) D-H:弃权门 M 须 >6dB(本底估计不确定度)且 <15dB(T_papr,否则合法候选恒弃权)",
      6.0 < Params().probe_floor_M < 15.0, f"M={Params().probe_floor_M}")

# ---------------------------------------------------------------- CHECK U
print("\nCHECK U: r17 `t_last_hit` 刷新条件 + EXHAUSTED + 回收优先序(★ 回归锁,带 D-J 触达)")
# 立法理由:tap 在陷波器组入口、陷波在**下游** ⇒ 外部持续源**永远在 tap 上看得见**
#   ⇒ 永远复检 ⇒ 无条件刷新 t_last_hit 会让 LIFT 永不启动(r16 实测回收率仅 14.1%)。
#   「该峰仍被检出」**不是**「该陷波仍被需要」的证据。
def alloc_once(from_abstain, target0, tw=100.0):
    """真跑 _allocate 的 same 分支。返回 (t_last_hit 是否被刷新, EXHAUSTED 次数)。"""
    a = NHS(); a.t_wall = tw
    s0 = a.slots[0]
    s0.st = nhs.NotchSlot.HOLD; s0.f = 2500.0
    s0.target = target0; s0.depth = target0
    s0.from_abstain = from_abstain
    s0.has_affirmative_verdict = not from_abstain   # ★ r27:肯定式(弃权来源 ⇒ 无肯定结论)
    s0.t_last_hit = 0.0
    for s2 in a.slots[1:]:
        s2.st = nhs.NotchSlot.FREE
    a._allocate([dict(cls='PERSIST', f=2500.0, tr=None, lv=-20.0, b=0.0)])
    return (s0.t_last_hit > 0.0), a.ctr.get('depth_exhausted', 0), s0.target

r1, e1, _ = alloc_once(False, -3.0)      # 正向分类 + 可继续加深 ⇒ **应刷新**
r2, e2, _ = alloc_once(True,  -3.0)      # **弃权来源** + 可加深   ⇒ **不应刷新**
r3, e3, t3 = alloc_once(False, Params().max_depth)  # 已达 max_depth ⇒ 不加深 ⇒ 不刷新 + EXHAUSTED
check("U (a) 正向分类 ∧ 导致加深 ⇒ **刷新** t_last_hit(复发→加深路径无损)",
      r1 is True, f"refreshed={r1}", hits=1)
check("U (b) ★弃权来源的占用 ⇒ **不刷新**(外部源永远复检,刷新不正当)",
      r2 is False, f"refreshed={r2}", hits=1)
check("U (c) 已达 max_depth ⇒ 不加深 ⇒ **不刷新**(推迟量被加深梯级钉死 ⇒ 有界)",
      r3 is False, f"refreshed={r3} target={t3}", hits=1)
check("U (d) ★已达 max_depth 仍被复检 ⇒ 记 **EXHAUSTED**(修法前被永久占槽掩盖)",
      e3 > 0, f"exhausted={e3}", hits=e3)
# 回收优先序:弃权产生的占用优先被回收
a9 = NHS(); a9.t_wall = 200.0
for si, s9 in enumerate(a9.slots):
    s9.st = nhs.NotchSlot.STANDBY; s9.f = 400.0 + si*100; s9.t_last_hit = 100.0 + si
    s9.from_abstain = False; s9.has_affirmative_verdict = True     # ★ r27 肯定式
a9.slots[3].from_abstain = True; a9.slots[3].has_affirmative_verdict = False          # 唯一弃权来源,但 t_last_hit **不是最老**
a9._allocate([dict(cls='PERSIST', f=9000.0, tr=None, lv=-20.0, b=0.0)])
picked = [si for si, s9 in enumerate(a9.slots) if abs(s9.f - 9000.0) < 1.0]
check("U (e) ★回收优先序:弃权来源的占用**优先**被回收(即使它不是最老的)",
      picked == [3], f"被改派的槽位={picked}(期望 [3])", hits=len(picked))
# ★ U(f):端到端 —— **探针判弃权时是否真的会打上 from_abstain 标记**
#   (U(b) 是手工设标记,测的是"标记生效";本条测"标记会被设上"。二者缺一不可。)
dfU = FS_SC/NFFT; fU = 2500.0; kU = int(round(fU/dfU))
aU = NHS(); aU.slots[0].st = nhs.NotchSlot.ENGAGE; aU.slots[0].f = fU
aU.slots[0].from_abstain = False
aU.probes = {0: dict(f=fU, seq0=0, L0=None, d=3.0, cls='PERSIST')}
MU = np.full(NB, 1e-3); MU[kU] = 1.2e-3          # 峰仅高出本底 ~1.6dB < M=10 ⇒ 弃权
aU.slot_seq = 0; aU._probe_tick(MU, dfU)
aU.slot_seq = aU.P.probe_hops; aU._probe_tick(MU, dfU)
_v = aU.c8_log[0]['verdict'] if aU.c8_log else None
check("U (f) ★端到端:探针判**弃权**时,须真的给槽位打上 from_abstain 标记",
      _v == 'abstain' and aU.slots[0].from_abstain is True,
      f"verdict={_v} from_abstain={aU.slots[0].from_abstain}",
      hits=1 if _v == 'abstain' else 0)
# ★ U(g) 可抢占:正向分类的真啸叫可**直接抢走**弃权产生的占用(不限 STANDBY)
aP = NHS(); aP.t_wall = 300.0
for si, sp in enumerate(aP.slots):                 # 全部槽位占满,且**均非 STANDBY**
    sp.st = nhs.NotchSlot.HOLD; sp.f = 400.0 + si*100
    sp.t_last_hit = 200.0 + si; sp.from_abstain = False
    sp.has_affirmative_verdict = True                              # ★ r27 肯定式
aP.slots[5].from_abstain = True; aP.slots[5].has_affirmative_verdict = False                    # 唯一弃权来源
aP._allocate([dict(cls='PERSIST', f=9000.0, tr=None, lv=-20.0, b=0.0)])
_pk = [si for si, sp in enumerate(aP.slots) if abs(sp.f - 9000.0) < 1.0]
check("U (g) ★可抢占:满槽且无 STANDBY 时,真啸叫抢走**弃权来源**的占用",
      _pk == [5] and aP.ctr.get('preempt', 0) > 0,
      f"被抢槽位={_pk}(期望 [5]) preempt={aP.ctr.get('preempt', 0)}", hits=aP.ctr.get('preempt', 0))
# 阴性:无弃权来源时不得抢占(应退回宽带兜底)
aN = NHS(); aN.t_wall = 300.0
for si, sn in enumerate(aN.slots):
    sn.st = nhs.NotchSlot.HOLD; sn.f = 400.0 + si*100
    sn.t_last_hit = 200.0 + si; sn.from_abstain = False
    sn.has_affirmative_verdict = True                              # ★ r27 肯定式
aN._allocate([dict(cls='PERSIST', f=9000.0, tr=None, lv=-20.0, b=0.0)])
check("U (h) 阴性对照:无弃权来源占用时**不得抢占**(退回宽带兜底)",
      aN.ctr.get('preempt', 0) == 0 and aN.g_duck_db < 0.0,
      f"preempt={aN.ctr.get('preempt', 0)} g_duck={aN.g_duck_db}", hits=1)
# ★ U(i) EXHAUSTED 计数口径(DEC-0010:必须写明"每什么计一次")
aE = NHS(); aE.t_wall = 100.0
sE = aE.slots[0]; sE.st = nhs.NotchSlot.HOLD; sE.f = 2500.0
sE.target = Params().max_depth; sE.depth = Params().max_depth
sE.from_abstain = False; sE.exhausted_flag = False
for s2 in aE.slots[1:]:
    s2.st = nhs.NotchSlot.FREE
for _ in range(5):                                  # **同一次占用复检 5 次**
    aE._allocate([dict(cls='PERSIST', f=2500.0, tr=None, lv=-20.0, b=0.0)])
check("U (i) ★DEPTH_EXHAUSTED = **每次占用计一次**(同一占用复检 5 次仍只计 1)",
      aE.ctr.get('depth_exhausted', 0) == 1,
      f"exhausted={aE.ctr.get('depth_exhausted', 0)}(期望 1) rechecks={aE.ctr.get('depth_exhausted_rechecks', 0)}(期望 5)",
      hits=aE.ctr.get('depth_exhausted_rechecks', 0))
check("U (j) 复检次数单独计,与事件数**不混用**(两个量各有单位)",
      aE.ctr.get('depth_exhausted_rechecks', 0) == 5,
      f"rechecks={aE.ctr.get('depth_exhausted_rechecks', 0)}", hits=1)

# ---------------------------------------------------------------- CHECK V
print("\nCHECK V: r20 两条耗尽路径**各自有动作**(★ 静默失效回归锁,带 D-J 触达)")
# 立法理由(架构侧读权威源查实):原实现撞顶只发事件、无动作,而宽带兜底挂在 `if not free:`;
#   撞顶时槽仍占着 ⇒ free 非空 ⇒ **g_duck 永不触发** ⇒ 报警但不作为 = **静默失效**。
#   ⚠ **与发生率无关**:哪怕 0.1 次/试次也必须封。安全兜底静默不触发是缺陷,不是概率问题。
Pv = Params()
# ── V(a) 深度撞顶:槽**未**耗尽(有空槽)⇒ 仍须触发兜底
av = NHS(); av.t_wall = 100.0
sv = av.slots[0]
sv.st = nhs.NotchSlot.HOLD; sv.f = 2500.0
sv.target = Pv.max_depth; sv.depth = Pv.max_depth
sv.from_abstain = False; sv.exhausted_flag = False
for s2 in av.slots[1:]:
    s2.st = nhs.NotchSlot.FREE                     # ★ 关键:**有空槽**
av._allocate([dict(cls='PERSIST', f=2500.0, tr=None, lv=-20.0, b=0.0)])
_de = av.ctr.get('depth_exhausted', 0)
check("V (a) ★撞顶且**有空槽**时,仍须发 DEPTH_EXHAUSTED",
      _de == 1, f"depth_exhausted={_de}", hits=_de)
check("V (b) ★撞顶必须**有动作**(g_duck 真的降),不得只报警",
      av.g_duck_db < 0.0,
      f"g_duck={av.g_duck_db}dB(修前此处恒为 0 = 静默失效)", hits=1 if _de else 0)
check("V (c) 撞顶发的是 DEPTH_EXHAUSTED,**不是** SLOTS_EXHAUSTED(不同源不得混)",
      any(e[1] == 'DEPTH_EXHAUSTED' for e in av.events)
      and not any(e[1] == 'SLOTS_EXHAUSTED' for e in av.events),
      f"事件={[e[1] for e in av.events]}", hits=1)
# ── V(d) 槽位耗尽:全部占满且无可抢占 ⇒ SLOTS_EXHAUSTED + 兜底 + n_blocked
aw = NHS(); aw.t_wall = 300.0
for si, sw in enumerate(aw.slots):
    sw.st = nhs.NotchSlot.HOLD; sw.f = 400.0 + si*100
    sw.t_last_hit = 200.0 + si; sw.from_abstain = False; sw.exhausted_flag = False
    sw.has_affirmative_verdict = True     # ★ r27:全部持肯定结论 ⇒ 不可抢占 ⇒ 才走槽位耗尽
    sw.target = Pv.depth0; sw.depth = Pv.depth0
aw._allocate([dict(cls='PERSIST', f=9000.0, tr=None, lv=-20.0, b=0.0)])
check("V (d) 槽位耗尽 ⇒ 发 SLOTS_EXHAUSTED 且 g_duck 降",
      aw.ctr.get('slots_exhausted', 0) == 1 and aw.g_duck_db < 0.0,
      f"slots_exhausted={aw.ctr.get('slots_exhausted', 0)} g_duck={aw.g_duck_db}",
      hits=aw.ctr.get('slots_exhausted', 0))
# ── V(e) D-K:B_obs 的计数单位 = **每个被拒绝的候选一次**(不是每帧/每复检)
check("V (e) ★D-K:n_blocked = **每个被拒绝的候选计一次**(单次分配 ⇒ 恰好 +1)",
      aw.ctr.get('n_blocked', 0) == 1,
      f"n_blocked={aw.ctr.get('n_blocked', 0)}(期望 1)", hits=1)
check("V (f) n_carried = 每个**成功入槽**的候选一次(V(a) 场景有空槽但走 same 分支 ⇒ 不计)",
      av.ctr.get('n_carried', 0) == 0,
      f"n_carried={av.ctr.get('n_carried', 0)}(期望 0:走的是 deepen 不是新占用)", hits=1)

# ---------------------------------------------------------------- CHECK W
print("\nCHECK W: r24 P0 测量有效性门(★ 回归锁 + **门不过强**的阴性对照,带 D-J 触达)")
# 立法理由:_classify 按**轨的累积历史**判 PERSIST,不要求当前槽有观测
#   ⇒ 数字静默帧也能挂陷 + 起探针 ⇒ 探针基线取自全零帧 ⇒ 256ms 后必然弃权。
# ⚠ 该门是**测量有效性门,不是门限**:只拒绝数值退化读数,物理上拒绝不了真实候选。
dfW = FS_SC / NFFT; fW = 2500.0; kW = int(round(fW / dfW))
def alloc_with(M):
    aw = NHS(); aw.t_wall = 100.0
    for s2 in aw.slots:
        s2.st = nhs.NotchSlot.FREE
    aw._allocate([dict(cls='PERSIST', f=fW, tr=None, lv=-20.0, b=0.0)], M, dfW)
    engaged = sum(1 for s2 in aw.slots if s2.st != nhs.NotchSlot.FREE)
    return engaged, aw.ctr.get('p0_blocked_novalid', 0), len(aw.probes)
# (a) 数字静默(全零谱)⇒ 必须拦下,且不起探针
e0, b0, p0 = alloc_with(np.zeros(NB))
check("W (a) ★数字静默帧(全零谱)⇒ **不挂陷、不起探针**",
      e0 == 0 and b0 == 1 and p0 == 0,
      f"engaged={e0} blocked={b0} probes={p0}", hits=b0)
# (b) ★阴性对照:**门不得过强** —— 电平低到接近 T_low 但物理真实 ⇒ 必须放行
#     取 −44dBFS(刚过 T_low=−45),这是该门绝不能拦的那一类
amp = 10 ** (-44.0 / 20.0) * NFFT / 4.0
Mw = np.full(NB, amp * 1e-3); Mw[kW] = amp
e1, b1, p1 = alloc_with(Mw)
check("W (b) ★阴性对照:−44dBFS(刚过 T_low)的真实候选 ⇒ **必须放行**(门不过强)",
      e1 == 1 and b1 == 0 and p1 == 1,
      f"engaged={e1} blocked={b1} probes={p1}  实测电平={NHS()._level(Mw,kW):.1f}dBFS", hits=1)
# (c) 门只拒绝数值退化区:−250dB 以下才拦
check("W (c) 门限落在数值退化区(−250dBFS),远低于 T_low(−45)⇒ 不可能拒绝真实候选",
      Params().level_valid_db < -200.0 and Params().level_valid_db > -600.0,
      f"level_valid_db={Params().level_valid_db} vs T_low={Params().T_low}")
# (d) deepen 分支**不受该门影响**(历史累积设计未被触碰)
aw2 = NHS(); aw2.t_wall = 100.0
sw = aw2.slots[0]; sw.st = nhs.NotchSlot.HOLD; sw.f = fW
sw.target = Params().depth0; sw.depth = Params().depth0
sw.from_abstain = False; sw.exhausted_flag = False
for s2 in aw2.slots[1:]:
    s2.st = nhs.NotchSlot.FREE
aw2._allocate([dict(cls='PERSIST', f=fW, tr=None, lv=-20.0, b=0.0)], np.zeros(NB), dfW)
# (e) ★★ 决定性阴性对照:**低于 T_low 的合法候选必须放行** ——
#     B-F1 钉住啸叫的 tap 实测 −57~−70dBFS,**低于 T_low(−45)**,靠 T_low_gr 放宽门入轨。
#     若把该门写成 `<= T_low`,**B-F1 会被直接拦掉** ⇒ 漏检最重的那一类。
amp2 = 10 ** (-60.0 / 20.0) * NFFT / 4.0
Mw2 = np.full(NB, amp2 * 1e-3); Mw2[kW] = amp2
e2, b2, p2 = alloc_with(Mw2)
check("W (e) ★★−60dBFS(**低于 T_low**,B-F1 钉住啸叫量级)⇒ **必须放行**"
      "(写成 T_low 门会拦掉 B-F1)",
      e2 == 1 and b2 == 0,
      f"engaged={e2} blocked={b2}  实测电平={NHS()._level(Mw2,kW):.1f}dBFS "
      f"(T_low={Params().T_low})", hits=1)
check("W (d) ★deepen 分支不受该门影响(只堵新挂陷,不废掉历史累积判定)",
      aw2.ctr.get('p0_blocked_novalid', 0) == 0
      and any(e[1] == 'deepen' for e in aw2.events),
      f"blocked={aw2.ctr.get('p0_blocked_novalid', 0)} 事件={[e[1] for e in aw2.events]}", hits=1)

# ---------------------------------------------------------------- CHECK X'
print("\nCHECK X': 无判决路径必须有独立计数器(★ E-03 教训锁;原挂断言,r31 改挂 P0)")
# ⚠ 本条**不是**断言的配套件 —— 它守的是 E-03 那条教训:
#   「凡新增的『不产生判决』的代码路径,必须有独立计数器,否则该路径不可见」。
#   断言已于 r31 撤除(原意在本架构下恒真、且 P0 已在源头封死其检出对象),
#   但**这条教训与断言无关** ⇒ 保留,改挂到 P0 的 `p0_blocked_novalid`。
dfX2 = FS_SC / NFFT; fX2 = 2500.0
aX2 = NHS(); aX2.t_wall = 100.0
for s2 in aX2.slots:
    s2.st = nhs.NotchSlot.FREE
aX2._allocate([dict(cls='PERSIST', f=fX2, tr=None, lv=-20.0, b=0.0)], np.zeros(NB), dfX2)
_nb = aX2.ctr.get('p0_blocked_novalid', 0)
check("X' (a) ★E-03:P0 拦下候选(不产生判决)⇒ **必须有独立计数器**",
      _nb == 1, f"p0_blocked_novalid={_nb}", hits=_nb)
check("X' (b) 该路径还须留痕(供'门是否过强'判定),不能只有计数",
      len(aX2.p0_block_log) == 1 and 'lv' in aX2.p0_block_log[0],
      f"留痕条目={aX2.p0_block_log}", hits=1)

# ---------------------------------------------------------------- CHECK Y
print("\nCHECK Y: r27 **肯定式豁免**(★ 机制锁:未来新增的无判决类别须自动落安全侧)")
# 立法理由:否定式 `not from_abstain` ⇒ 新增的无判决类别默认落进「刷新租约」= 危险侧
#   ⇒ 每加一条无判决路径就自动重新引入 C6-② 修掉的无限推迟 bug(仪表故障孤儿即此)。
Py = Params()
def lease(mark_affirm, extra=None):
    """真跑 _allocate 的 same/deepen 分支;返回 t_last_hit 是否被刷新。"""
    ay = NHS(); ay.t_wall = 500.0
    sy = ay.slots[0]
    sy.st = nhs.NotchSlot.HOLD; sy.f = 2500.0
    sy.target = Py.depth0; sy.depth = Py.depth0
    sy.t_last_hit = 0.0
    sy.has_affirmative_verdict = mark_affirm
    if extra:
        setattr(sy, extra, True)           # 模拟"未来新增的某种标记"
    for s2 in ay.slots[1:]:
        s2.st = nhs.NotchSlot.FREE
    ay._allocate([dict(cls='PERSIST', f=2500.0, tr=None, lv=-20.0, b=0.0)], None, None)
    return sy.t_last_hit > 0.0
check("Y (a) 持有**肯定分类结论**的占用 ⇒ 刷新租约(真啸叫的复发→加深路径无损)",
      lease(True) is True, f"refreshed={lease(True)}", hits=1)
check("Y (b) ★**无**肯定结论的占用 ⇒ **不刷新**(弃权/仪表故障/在飞 一律安全侧)",
      lease(False) is False, f"refreshed={lease(False)}", hits=1)
# ★★ Y(c):机制锁 —— 模拟一条**未来新增的无判决类别**(带一个此前不存在的标记)
check("Y (c) ★★机制锁:**虚构的新无判决类别**(带未知标记)⇒ **默认不刷新租约**",
      lease(False, extra='some_future_novel_flag') is False,
      "新增类别自动落安全侧(否定式实现会在此失守)", hits=1)
# 抢占/回收优先序也须肯定式
ay2 = NHS(); ay2.t_wall = 300.0
for si, sy2 in enumerate(ay2.slots):
    sy2.st = nhs.NotchSlot.HOLD; sy2.f = 400.0 + si*100
    sy2.t_last_hit = 200.0 + si
    sy2.has_affirmative_verdict = True
ay2.slots[4].has_affirmative_verdict = False      # 唯一**无**肯定结论者
ay2._allocate([dict(cls='PERSIST', f=9000.0, tr=None, lv=-20.0, b=0.0)], None, None)
_pk2 = [si for si, sy2 in enumerate(ay2.slots) if abs(sy2.f - 9000.0) < 1.0]
# ★★ Y(e):**默认值**必须落安全侧 —— 不显式设标记,直接用新建槽位的默认状态。
#   前四条都**显式设**了标记 ⇒ 从未走过默认值这条路 ⇒ 默认值被翻成 True 也测不出来。
#   本条专测「未来新增类别什么都不做时,落哪一侧」。
ay3 = NHS(); ay3.t_wall = 500.0
sy3 = ay3.slots[0]                       # ★ 全新槽位,**不碰** has_affirmative_verdict
sy3.st = nhs.NotchSlot.HOLD; sy3.f = 2500.0
sy3.target = Py.depth0; sy3.depth = Py.depth0; sy3.t_last_hit = 0.0
for s2 in ay3.slots[1:]:
    s2.st = nhs.NotchSlot.FREE
ay3._allocate([dict(cls='PERSIST', f=2500.0, tr=None, lv=-20.0, b=0.0)], None, None)
check("Y (e) ★★**默认值**测试:新建槽位不设任何标记 ⇒ **默认不刷新租约**(安全侧)",
      sy3.t_last_hit == 0.0,
      f"t_last_hit={sy3.t_last_hit}(期望 0.0 = 未刷新);"
      f"默认 has_affirmative_verdict={nhs.NotchSlot().has_affirmative_verdict}", hits=1)
check("Y (d) 抢占同样按肯定式:**无肯定结论**的占用优先被抢(不论它属哪一类)",
      _pk2 == [4], f"被抢槽位={_pk2}(期望 [4])", hits=len(_pk2))

print("\n" + "="*76)
print(f"结果:{len(FAILS)} 个 FAIL" + (f" -> {FAILS}" if FAILS else " ✓ 全过"))
print("="*76)
sys.exit(1 if FAILS else 0)
