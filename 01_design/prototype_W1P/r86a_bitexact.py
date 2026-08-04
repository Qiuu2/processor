"""r86a · `recheck_free` 默认关的**逐位等价**实跑对照(+ 阳性对照)。
⛔ 未经 critic 评审。[L2/宿主仿真]。lead 2026-08-04 批(补 `VERSIONS.txt` 等价链缺环)。
输出 r86a_bitexact_out.txt(D6-j 路径唯一)。形态照 `r78a_bitexact.py`。

被证的两件(缺一不可,D6-y 双向):
  ① 全部开关取默认(含 `recheck_free=False`)⇒ 与**链末端归档版** `c2eb9bef77bc06ea` 逐位相同
     —— 靠实跑逐位比对,⛔ 不靠"读起来一样"
  ② **阳性对照**:强制 `recheck_free=True` ⇒ **必须出现差异**
     —— 否则说明开关根本没接上,①的"相同"就毫无意义(r77/r66a 的教训:器械要能失败)

⚠ 对照臂怎么来(比 r78a 更强的一种):**不做重实现,直接取归档版本原文** ——
  `git show 5c56d025:01_design/prototype_W1P/nhs.py` → `nhs_legacy_c2eb9bef.py`,
  **跑前现场复算 sha256[0:16] 并断言 == c2eb9bef77bc06ea**(= VERSIONS.txt 链末端)。
  ⇒ 对照臂的身份不靠我转述,靠哈希。

⚠⚠ 而缺的**不止一环**(本件跑前查明,`git log -- nhs.py`):
      c2eb9bef(链末端,r78)→ 57ced119(r84 漏斗遥测)→ 47a57d21(r85 preempt_log)
                            → b77a0524(r86 recheck_free,当前版)
  ⇒ 故本件对照的是 **c2eb9bef ↔ 当前版**,一次性覆盖三跳(而非只覆盖 r86 那一跳)。
  ⇒ r84/r85 两跳自称"只计数不改行为" —— 那也是**未经实跑证实的声称**,同族。

⚠ ctr 键集怎么比:新版新增了纯计数键(F1–F5 / A1 / A2 / A3 / A3_cmd_db)⇒ 键集必然不同。
  ⇒ **行为等价的判据 = y / loop / slots 三项逐位 + ctr 【共有键】逐值**;
    新增键**单列**为"纯计数新增",⛔ 不计入差异,也⛔ 不藏起来。
"""
import sys, os, json, glob, time, hashlib, subprocess, importlib.util
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import GR, FRAME

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
LEGACY_FILE = 'nhs_legacy_c2eb9bef.py'
LEGACY_SHA = 'c2eb9bef77bc06ea'          # = VERSIONS.txt 等价链末端
BW_OCT, TLOW, F_CUT = 1 / 5, -45., 8000.
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
A_T_OBS, A_DG, A_SRC = 3.0, [1.0, 3.0], [-20., -60.]     # 块 A = r78a 同工作点
B_T_OBS, B_SRC = 12.0, -20.                              # 块 B = r87 闸门同工作点
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def sha(f):
    return hashlib.sha256(open(DIR + f, 'rb').read()).hexdigest()[:16]


def regen_legacy():
    """⭐ 现场从 git 取归档版,跑完即删 —— **不在目录里留一个与 `nhs.py` 难分辨的副本**。
    (本项目高发病:一个东西的身份从名字/内容看不出来 ⇒ 迟早被误当成另一个。)"""
    src = subprocess.run(['git', 'show', '5c56d025:01_design/prototype_W1P/nhs.py'],
                         cwd='/home/it1234/processor', capture_output=True, check=True).stdout
    with open(DIR + LEGACY_FILE, 'wb') as fp:
        fp.write(src)


def load_legacy():
    spec = importlib.util.spec_from_file_location('nhs_legacy', DIR + LEGACY_FILE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run(mod, hb, D, G, src, rf):
    """rf=None ⇒ 不碰该开关(归档版没有它)。"""
    a = mod.NHS()
    a.P.bw_oct = BW_OCT
    a.P.T_low = TLOW
    if rf is not None:
        a.P.recheck_free = bool(rf)
    y, lp = clrig.Loop(hb, D, G, proc=lambda b, _a=a: _a.process_frame(b, GR)).run(src, FRAME)
    used = [s for s in a.slots if s.st != mod.NotchSlot.FREE]
    return dict(y=y, lp=lp, ctr={k: v for k, v in sorted(a.ctr.items())},
                slots=sorted((round(float(s.f), 6), round(float(s.depth), 6), int(s.st))
                             for s in used))


def cmp(r1, r2):
    """返回 (差异项列表, 仅 r2 有的新增键)。行为判据 = y/loop/slots + ctr 共有键。"""
    d = []
    if not np.array_equal(r1['y'], r2['y']):
        d.append('y')
    if not np.array_equal(r1['lp'], r2['lp']):
        d.append('loop')
    if r1['slots'] != r2['slots']:
        d.append('slots')
    both = set(r1['ctr']) & set(r2['ctr'])
    if any(r1['ctr'][k] != r2['ctr'][k] for k in both):
        d.append('ctr共有键')
    added = sorted(set(r2['ctr']) - set(r1['ctr']))
    return d, added


def block(tag, cells):
    """cells = [(T60, sd, src_db, T_OBS, G, 标签)]。返回 (n_eq, n_tot, n_pos, added_union)。"""
    LEG = load_legacy()
    n_eq = n_pos = n_tot = 0
    added_u = set()
    W(f"{'T60':>5}{'sd':>4}{'src':>6}{'T':>5}{'G':>9} | {'①默认 vs 归档c2eb9bef':>26}"
      f" | {'②阳性(强制 recheck_free=True)':>30}")
    for (T60, sd, src_db, T, G, note) in cells:
        h0, D = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
        hb = band_limit(h0, F_CUT)
        src = np.random.default_rng(sd).standard_normal(int(T * FS)) * (10 ** (src_db / 20.))
        a_new = run(nhs, hb, D, G, src, False)     # 当前版,开关默认关
        a_old = run(LEG, hb, D, G, src, None)      # 归档版 c2eb9bef(无该开关)
        a_pos = run(nhs, hb, D, G, src, True)      # 阳性:强制开
        d1, add1 = cmp(a_old, a_new)
        d2, _ = cmp(a_new, a_pos)
        added_u |= set(add1)
        n_tot += 1
        n_eq += int(not d1)
        n_pos += int(bool(d2))
        W(f"{T60:>5.1f}{sd:>4}{int(src_db):>6}{T:>5.0f}{G:>9.2f} | "
          f"{('✅逐位相同' if not d1 else '⛔差异于 ' + ','.join(d1)):>26} | "
          f"{('✅出现差异于 ' + ','.join(d2) if d2 else '⛔(无差异)'):>30}")
    return n_eq, n_tot, n_pos, added_u


def main():
    t0 = time.time()
    W("未经 critic 评审 —— r86a · `recheck_free` 默认关的逐位等价 + 阳性对照  [L2/宿主仿真]")
    W("⚠ 器械必须能失败(r77/r66a 教训)⇒ 阳性对照与等价对照**同等必报**。")
    W("")
    # ── 对照臂身份:现场从 git 取 + 复算哈希,不靠转述 ──────────
    regen_legacy()
    got = sha(LEGACY_FILE)
    W("=" * 118)
    W("§0 对照臂身份(现场复算,⛔ 不靠转述)")
    W("=" * 118)
    W(f"   归档件 {LEGACY_FILE}  sha256[0:16] = {got}  期望 {LEGACY_SHA}  ⇒ "
      f"{'✅ 相符(= VERSIONS.txt 链末端)' if got == LEGACY_SHA else '⛔ 不符'}")
    W(f"   来源:git show 5c56d025:01_design/prototype_W1P/nhs.py(**本件跑前现场取,跑完即删**)")
    W(f"   当前版 nhs.py sha256[0:16] = {sha('nhs.py')}")
    W(f"   ⚠ 两版之间共 **3 跳**:c2eb9bef →(r84 漏斗遥测)57ced119 →(r85 preempt_log)"
      f"47a57d21 →(r86 recheck_free)b77a0524")
    W(f"   ⇒ 本件一次性对照首尾两端 ⇒ 三跳一并被证(或一并被否)")
    W("")
    if got != LEGACY_SHA:
        W("⛔ 对照臂哈希不符 ⇒ 本件作废,不出结论。")
        os.remove(DIR + LEGACY_FILE)
        with open(DIR + 'r86a_bitexact_out.txt', 'w') as fp:
            fp.write("\n".join(OUT) + "\n")
        sys.exit(1)
    W("   判据:行为等价 = y(输出信号)/ loop(求和节点)/ slots(陷波器状态)三项逐位")
    W("        + ctr **共有键**逐值;新增的纯计数键单列(⛔ 不计入差异,也不藏)")
    W("")

    # ── 块 A:r78a 同工作点 ───────────────────────────────────────
    W("=" * 118)
    W(f"§A 块 A(= r78a 同工作点,便于横比):T_OBS={A_T_OBS:.0f}s / ΔG∈{A_DG} / "
      f"src∈{[int(x) for x in A_SRC]} / bw_oct=1/5 / T_low=−45")
    W("=" * 118)
    cellsA = []
    for (T60, sd) in SEEDS:
        h0, D = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
        he = clrig.h_eff(band_limit(h0, F_CUT))
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        for L in A_SRC:
            for dg in A_DG:
                cellsA.append((T60, sd, L, A_T_OBS, anchor + dg, f'anchor{dg:+.0f}'))
    eqA, totA, posA, addA = block('A', cellsA)
    W("")

    # ── 块 B:r87 闸门同工作点(该处修法可达性已发表:5/6)────────
    W("=" * 118)
    W(f"§B 块 B(= r87 闸门同工作点,该处开关可达性已发表 5/6):T_OBS={B_T_OBS:.0f}s / "
      f"src={int(B_SRC)} / G = r76 已落盘的基线终点(m0+dA)")
    W("   ⚠ 选它的理由**跑前写明**:块 A 是短窗,开关可能天然打不到 ⇒ 需要一个"
      "【可达性已独立发表】的工作点,免得 ② 的失败被归因错(r66a:『没打到』与『打了没用』同形)")
    W("=" * 118)
    R = []
    for p in glob.glob(DIR + 'r76_cell_*.json'):
        R += json.load(open(p))
    K = {(r['src'], r['fix'], r['tlow'], r['T60'], r['sd'], r['T']): r for r in R}
    cellsB = []
    for (T60, sd) in SEEDS:
        rec = K.get((B_SRC, 0, TLOW, T60, sd, B_T_OBS))
        if rec is None or not np.isfinite(rec.get('dA', float('nan'))):
            continue
        cellsB.append((T60, sd, B_SRC, B_T_OBS, rec['m0'] + rec['dA'], 'r76终点'))
    eqB, totB, posB, addB = block('B', cellsB)
    W("")

    # ── 判定 ────────────────────────────────────────────────────
    eq, tot, pos = eqA + eqB, totA + totB, posA + posB
    W("=" * 118)
    W("§V 判定")
    W("=" * 118)
    W(f"  ① 默认(recheck_free=False)vs 归档 c2eb9bef:**{eq}/{tot} 逐位相同**"
      f"(块A {eqA}/{totA} · 块B {eqB}/{totB})⇒ "
      f"{'PASS' if eq == tot else '⛔ FAIL,立即回滚 nhs.py 并全库反扫引用'}")
    W(f"  ② 阳性对照(强制 recheck_free=True):**{pos}/{tot} 出现差异**"
      f"(块A {posA}/{totA} · 块B {posB}/{totB})⇒ "
      f"{'PASS(比对器有分辨力且开关确实接上了)' if pos > 0 else '⛔ FAIL:开关没接上 ⇒ ①的「相同」无意义'}")
    W(f"  新增纯计数键(仅当前版有,⛔ 不计入差异):{sorted(addA | addB)}")
    W("")
    os.remove(DIR + LEGACY_FILE)          # 跑完即删,见 regen_legacy 注释
    W(f"   对照臂副本 {LEGACY_FILE} **已删除**(可由上面那条 git 命令原样再取,哈希已留痕)")
    W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    with open(DIR + 'r86a_bitexact_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    json.dump(dict(eq=eq, tot=tot, pos=pos, eqA=eqA, totA=totA, posA=posA,
                   eqB=eqB, totB=totB, posB=posB, added=sorted(addA | addB),
                   legacy_sha=got, cur_sha=sha('nhs.py')),
              open(DIR + 'r86a_bitexact.json', 'w'))


if __name__ == '__main__':
    main()
