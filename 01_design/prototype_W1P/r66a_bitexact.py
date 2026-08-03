"""r66a · **路 A 的逐位等价证明** —— `nhs.py` 加 `P.growth_and_gate` 后,默认值下行为是否**逐位**未变。

⛔ 未经 critic 评审。[L2/宿主仿真]。
输出:r66a_bitexact_out.txt   (D6-j:路径唯一)

════════════════════════════════════════════════════════════════════
lead 裁定原话(2026-08-03):
> **「默认值下逐符号等价 ≠ 逐位等价。请用复现对照【实跑证明】行为未变(六条种子逐位相同),
>   而不是靠读表达式 —— 因为"读起来等价"正是这两天反复失效的那种证据。」**

⇒ 本件**不读表达式**。它把**改动前的 `nhs.py` 原件**(git 基线 sha256[0:16] = 706b658842d84316)
  与**改动后的现件**同时载入为两个模块,跑**完全相同**的闭环,逐位比对:
    ① 扩声输出 `y` 的**原始字节**(float64 tobytes,非四舍五入后的 dB)
    ② 求和节点 `loop` 的原始字节
    ③ 全部计数器 `ctr` 字典
    ④ 全部槽状态 (st, f, depth, target)
  **任一不同 ⇒ FAIL。**

════════════════════════════════════════════════════════════════════
⭐ 阳性对照(**没有它,本对照不可能失败 = 不算对照**;D6-d / LESSONS C-2)
════════════════════════════════════════════════════════════════════
只报"六条全同"是**恒真风险**:若比对器本身坏了(比如比了个空对象),它照样输出"全同"。
⇒ 故第三臂:**新模块 `growth_and_gate = True`** 对 **原模块**比 ——
  **必须有差异**。无差异 ⇒ 说明比对器没在比东西,或该参数根本没接上 ⇒ **整件作废**。

预注册(跑前写下):
  Hb1 `growth_and_gate = False` vs 原件:**六条种子 × 三个 G × 三臂,全部逐位相同**。
      证伪:任一格不同 ⇒ 路 A 的"默认不改变行为"不成立 ⇒ 立即回滚 `nhs.py` 并报 lead。
  Hb2 `growth_and_gate = True`  vs 原件:**至少一格出现差异**。
      证伪:全部相同 ⇒ ①该开关没接上,或②比对器无分辨力 ⇒ **整件作废,不得据 Hb1 放行**。
⛔ 本文件不写结论散文。
"""
import sys, importlib.util
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig
from clrig import FS
from r57_bandlimit import band_limit
from msg_meter import MSGMeter

ORIG = ('/tmp/claude-1000/-home-it1234-processor/'
        '530be877-5ec0-4df7-ae7b-ed9cade0a0b7/scratchpad/nhs_orig.py')
GR = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
FRAME, BW, DEPTH, T = 64, 1 / 5, -18.0, 6.0
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
DELTAS = [-1.0, 1.0, 3.0]
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def digest(mod, hb, D, G, src, kind, and_gate=None):
    """跑一次闭环,返回**可逐位比较**的四元组。kind: 'N' 自选 / 'Na' 自选+duck消融 / 'O' 神谕。"""
    if kind == 'O':
        fc, mdb = clrig.critical_points(clrig.h_eff(hb))
        o = list(np.argsort(mdb)[::-1])
        picks, used = [], np.zeros(len(fc), bool)
        for i in o:
            if used[i] or len(picks) >= 8:
                continue
            f_ = float(fc[i])
            picks.append(f_)
            used |= (np.abs(fc - f_) <= max(f_ * BW, 15.))
        a = mod.NHS()
        a.P.bw_oct = BW
        for i, f_ in enumerate(picks[:len(a.slots)]):
            s = a.slots[i]
            s.st = mod.NotchSlot.HOLD
            s.f = f_
            s.depth = DEPTH
            s.target = DEPTH
            s.set_coef(FS, BW)
        a.P.T_low = 999.
        a.duck_gain = lambda: 1.0
    else:
        a = mod.NHS()
        a.P.bw_oct = BW
        if kind == 'Na':
            a.duck_gain = lambda: 1.0
    if and_gate is not None:
        a.P.growth_and_gate = and_gate

    def pf(blk, _a=a):
        return _a.process_frame(blk, GR)
    y, lp = clrig.Loop(hb, D, G, proc=pf).run(src, FRAME)
    slots = tuple((int(s.st), float(s.f), float(s.depth), float(s.target))
                  for s in a.slots)
    return (np.asarray(y, np.float64).tobytes(),
            np.asarray(lp, np.float64).tobytes(),
            tuple(sorted((k, int(v)) for k, v in a.ctr.items()
                         if isinstance(v, (int, np.integer)))),
            slots)


def diff_where(d0, d1):
    names = ('y字节', 'loop字节', 'ctr', 'slots')
    return [n for n, x, z in zip(names, d0, d1) if x != z]


def main():
    W("未经 critic 评审 —— r66a · 路 A 的【逐位】等价证明(不读表达式,实跑比对)")
    W("[L2/宿主仿真]  deps: clrig.py@8ad47ce8d260dd18 r57_bandlimit.py@74036010b514080d")
    W(f"原件(改动前)= {ORIG}")
    W("比对四项:①y 原始字节 ②loop 原始字节 ③ctr 全部计数器 ④全部槽 (st,f,depth,target)")
    W(f"格点:6 条种子 × G ∈ anchor+{DELTAS} × 三臂(N / Na / O),T_OBS={T}s")
    W("")
    m_old = load(ORIG, 'nhs_old')
    m_new = load('/home/it1234/processor/01_design/prototype_W1P/nhs.py', 'nhs_new')
    W(f"原件有 growth_and_gate 属性?{hasattr(m_old.Params(), 'growth_and_gate')}  "
      f"(应为 False)")
    W(f"现件有 growth_and_gate 属性?{hasattr(m_new.Params(), 'growth_and_gate')}  "
      f"(应为 True),默认值 = {m_new.Params().growth_and_gate}(应为 False)")
    W("")
    W(f"{'T60':>5}{'sd':>4}{'Δ':>6}{'臂':>4}  {'Hb1 默认关 vs 原件':>20}  {'Hb2 强制开 vs 原件':>20}")
    n_same = n_cell = 0
    hb2_diff = []
    for (T60, sd) in SEEDS:
        h0, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
        hb = band_limit(h0, 8000.)
        he = clrig.h_eff(hb)
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        src = 1e-3 * np.random.default_rng(sd).standard_normal(int(T * FS))
        for dl in DELTAS:
            G = anchor + dl
            for kind in ('N', 'Na', 'O'):
                d_old = digest(m_old, hb, D, G, src, kind)
                d_off = digest(m_new, hb, D, G, src, kind, and_gate=False)
                d_on = digest(m_new, hb, D, G, src, kind, and_gate=True)
                same = (d_old == d_off)
                w_off = diff_where(d_old, d_off)
                w_on = diff_where(d_old, d_on)
                n_cell += 1
                n_same += int(same)
                if w_on:
                    hb2_diff.append((T60, sd, dl, kind, w_on))
                W(f"{T60:>5.1f}{sd:>4}{dl:>+6.1f}{kind:>4}  "
                  f"{('✅ 逐位相同' if same else '⛔ 不同:' + ','.join(w_off)):>20}  "
                  f"{('差异于 ' + ','.join(w_on) if w_on else '(无差异)'):>20}")
    W("")
    W("=" * 96)
    W(f"  Hb1(默认关 vs 原件):**{n_same}/{n_cell} 格逐位相同**"
      f"  ⇒ {'PASS' if n_same == n_cell else '⛔ FAIL —— 立即回滚 nhs.py 并报 lead'}")
    W(f"  Hb2(强制开 vs 原件,**阳性对照**):{len(hb2_diff)}/{n_cell} 格出现差异"
      f"  ⇒ {'PASS(比对器有分辨力,且开关确实接上了)' if hb2_diff else '⛔ FAIL —— 比对器无分辨力或开关没接上,整件作废'}")
    for x in hb2_diff[:8]:
        W(f"      T60={x[0]}/sd={x[1]} Δ={x[2]:+.1f} 臂{x[3]} ⇒ 差异于 {','.join(x[4])}")
    if len(hb2_diff) > 8:
        W(f"      …另有 {len(hb2_diff)-8} 格")
    W("")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。")
    open('/home/it1234/processor/01_design/prototype_W1P/'
         'r66a_bitexact_out.txt', 'w').write("\n".join(OUT) + "\n")


if __name__ == '__main__':
    main()
