"""r76 · 合并件 —— **只读已产出的 json,⛔ 不重跑任何仿真**(D6-j)。
⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r76.txt。
输出 r76_srclevel_full_out.txt。

⛔ 本文件不含任何结论性散文;所有判定语句 = 预注册里已写死的机械检查。
"""
import sys, os, json, glob
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
RUNGS = [6.0, 12.0]
SRC = [-60., -40., -30., -20., -10.]
STEP = 0.5
# ⛔ 仪器底(架构侧 2026-08-04 定量):STEP=0.5 ⇒ 单次读数半格 0.25 ⇒ 两个独立读数之差的底
#    = 0.25×√2 = 0.354 dB。**差值 < 0.354 ⇒ 不可分辨,不得据此说"相同"或"不同"。**
#    ⚠ 本轮 ΔMSG 全部落在 0.5 栅格上 ⇒ 差值只可能是 0.00 或 ≥0.50
#      ⇒ **凡差值 0.00 一律"不可判",凡非零一律在底之上** —— 没有中间情形。
FLOOR = 0.25 * (2 ** 0.5)
TARGETS = (4.0, 5.0)
INCOMP_LO, INCOMP_HI = 1.0, 99.0        # 过门率(%)不可比档判据(PREREG §5⑤)
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)


def key(r):
    return (r['src'], r['fix'], r['tlow'], r['T60'], r['sd'], r['T'])


def fmt(x, w=8, p=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return f"{'—':>{w}}"
    return f"{x:>{w}.{p}f}"


def load():
    R = {}
    miss = []
    for tag in ('s60f0', 's60f1', 's40f0', 's40f1', 's30f0', 's30f1',
                's20f0', 's20f1', 's10f0', 's10f1', 't50s60', 't50s20'):
        p = DIR + f'r76_cell_{tag}.json'
        if not os.path.exists(p):
            miss.append(tag)
            continue
        for r in json.load(open(p)):
            R[key(r)] = r
    return R, miss


def parse_r75():
    """解析 r75 的定宽表,用于**确定性复现核对**。⛔ 只读,不改。"""
    p = DIR + 'r75_srclevel_fix_out.txt'
    if not os.path.exists(p):
        return {}
    out = {}
    for ln in open(p):
        if '|' not in ln or ln.count('|') != 2:
            continue
        a, b, c = [x.strip() for x in ln.split('|')]
        try:
            src, fx, T60, sd, T = a.split()
            m0, dN, dA = [float(x) for x in b.split()]
            rate = float(c.split()[0].rstrip('%'))
            nn = int(c.split()[1])
        except Exception:
            continue
        out[(float(src), 1 if fx == '开' else 0, -45., float(T60), int(sd), float(T))] = \
            dict(m0=m0, dN=dN, dA=dA, rate=rate / 100., n_notch=nn)
    return out


def main():
    R, miss = load()
    r75 = parse_r75()
    W("未经 critic 评审 —— r76 · 源电平扫描【补齐】合并件  [L2/宿主仿真]  预注册 = PREREG_r76.txt")
    W("deps: nhs.py(prefer_unnotched 默认 False,逐位等价由 r75a 实跑证明:24/24 PASS,阳性对照 9/24)")
    W("      clrig.py / howl_detect.py / msg_meter.py / r57_bandlimit.py / r61_bwoct_baseline.py")
    W("⛔ 本件只读逐格 json 汇总,不重跑仿真。⛔ 不含结论性判读。")
    W("⛔ 修法臂(prefer_unnotched=True)= **非提交修法**,其数不得当修法收益引用。")
    W("⚠ B-1 的 1.00–2.50 dB 系在 **src_rms = −60 dBFS** 上测得,而**标称为 −20 dBFS**。")
    if miss:
        W(f"⛔⛔ 缺格(未跑完 ⇒ 相关行留空,**不得当结果引用**):{miss}")
    W("")
    W("列名(D6-t 全限定,⛔ 不得简称为裸 ΔMSG):")
    W("  ΔMSG_自选@有duck = ΔMSG_实测@带限8k_NHS自选_有duck_[L2/宿主仿真]")
    W("  ΔMSG_自选@消融   = ΔMSG_实测@带限8k_NHS自选_duck消融_[L2/宿主仿真]  ← **兜底消融列**")
    W("  ΔMSG_上界@神谕   = ΔMSG_上界@带限8k_神谕选点_[L2/宿主仿真]  ⛔ 禁称『NHS 实测』")
    W("")

    # ── §R 复现核对 ────────────────────────────────────────────────
    W("=" * 118)
    W("§R  **确定性复现核对** —— r76 的 −20/−60 档 vs r75 同格(同种子同参数应逐格相同)")
    W("=" * 118)
    if not r75:
        W("  ⛔ 未找到 r75_srclevel_fix_out.txt,无法核对")
    else:
        n_cmp = n_bad = 0
        bad = []
        for k, v in r75.items():
            if k not in R:
                continue
            n_cmp += 1
            a = R[k]
            for fld in ('m0', 'dN', 'dA'):
                # ⚠ r75 是 %8.2f 打印件 ⇒ 比对须在【打印精度】上做,不是 1e-9
                #   (m0 = anchor−3+k·0.5,anchor 非整数 ⇒ 直接比原值会假报不一致)
                x, y = a[fld], v[fld]
                if np.isfinite(x) != np.isfinite(y) or \
                        (np.isfinite(x) and abs(round(x, 2) - y) > 1e-9):
                    n_bad += 1
                    bad.append((k, fld, y, round(x, 2)))
            # 过门率同理:r75 打的是 %7.2f%% ⇒ 分数域的舍入界 = 5e-5,取 1e-4 留半格
            if abs(a['rate'] - v['rate']) > 1e-4 or a['n_notch'] != v['n_notch']:
                n_bad += 1
                bad.append((k, 'rate/挂陷', (round(v['rate'], 5), v['n_notch']),
                            (round(a['rate'], 5), a['n_notch'])))
        W(f"  可比格 {n_cmp} / r75 共 {len(r75)} 格;不一致项 **{n_bad}**")
        if n_cmp == 0:
            # ⚠ 假绿纪律:检查了 0 格不能报 ✅ —— "没查到不一致" ≠ "一致"
            W("  ⛔ **可比格 = 0 ⇒ 本项未执行**,不得读作通过")
        elif n_bad:
            W("  ⛔⛔ **不一致 ⇒ 台架有隐藏状态 ⇒ r75 与 r76 一并存疑,须先查清再报数**")
            for b in bad[:20]:
                W(f"     {b}")
        else:
            W("  ✅ 逐格相同 ⇒ 台架确定性成立(该结论只覆盖被比对的这些格)")
    W("")

    # ── §E Hr3 标度不变性 ──────────────────────────────────────────
    W("=" * 118)
    W("§E  Hr3 **标度不变性**(臂 m0 对源电平应【逐位不变】;证伪 ⇒ 整轮作废)")
    W("=" * 118)
    bad = []
    n_chk = 0
    for (T60, sd) in SEEDS:
        for T in RUNGS:
            v = [(L, R[(L, 0, -45., T60, sd, T)]['m0']) for L in SRC
                 if (L, 0, -45., T60, sd, T) in R]
            if len(v) < 2:       # ⚠ 只有 0/1 档时无从比较,不得计入"已查"
                continue
            n_chk += 1
            u = sorted(set(round(x[1], 6) for x in v))
            W(f"  T60={T60} sd={sd} T_OBS={T:.0f}s: m0 逐档 {[(int(a), round(b,2)) for a,b in v]}"
              f"   {'✅逐位相同' if len(u) == 1 else '⛔ 不同:' + str(u)}")
            if len(u) != 1:
                bad.append((T60, sd, T, u))
    W(f"  ⇒ 已查 {n_chk} 组(每组须 ≥2 档才可比)/ 违反条数 **{len(bad)}**  "
      + ('⛔ **已查 0 组 ⇒ 本项未执行**,不得读作通过' if n_chk == 0
         else ('✅ Hr3 未被证伪' if not bad else '⛔⛔ Hr3 被证伪 ⇒ 整轮作废')))
    W("")

    # ── §A 跨源电平主表 ────────────────────────────────────────────
    for col, nm in (('dA', 'ΔMSG_自选@消融(**兜底消融列**)'),
                    ('dN', 'ΔMSG_自选@有duck'),
                    ('dO', 'ΔMSG_上界@神谕(仅修法【关】格跑)')):
        for fx in (0, 1):
            if col == 'dO' and fx == 1:
                continue
            W("=" * 118)
            W(f"§A  {nm}   修法={'开(**非提交修法**)' if fx else '关'}   T_low=−45")
            W("=" * 118)
            W(f"{'T60':>5}{'sd':>4}{'T_OBS':>7}" + "".join(f"{int(L):>10}" for L in SRC)
              + f"{'极差':>9}")
            for (T60, sd) in SEEDS:
                for T in RUNGS:
                    v = [R.get((L, fx, -45., T60, sd, T), {}).get(col, float('nan')) for L in SRC]
                    fin = [x for x in v if x is not None and np.isfinite(x)]
                    W(f"{T60:>5.1f}{sd:>4}{T:>7.0f}" + "".join(fmt(x, 10) for x in v)
                      + fmt(max(fin) - min(fin) if len(fin) > 1 else float('nan'), 9))
            W("  ⚠ 跨档差**混着两个效应**:效应A(三个绝对门相对位置平移)+ 效应B(扫描终点 G 平移)")
            W("    ⇒ 拆开须并读 §G(固定 G 表)与 §L(报数点绝对电平 lp_rms@m)")
            W("")

    # ── §P 过门率 / 挂陷 / 四量 vs 源电平 ──────────────────────────
    W("=" * 118)
    W("§P  过门率(扫描口径,含效应 B)/ 挂陷数 / 选点四量  vs 源电平   修法=关  T_low=−45")
    W("=" * 118)
    W(f"{'T60':>5}{'sd':>4}{'T_OBS':>7}{'量':>10}" + "".join(f"{int(L):>10}" for L in SRC))
    for (T60, sd) in SEEDS:
        for T in RUNGS:
            g = lambda L, k: R.get((L, 0, -45., T60, sd, T), {}).get(k, float('nan'))
            for k, nm, p in (('rate', '过门率%', 2), ('n_notch', '挂陷', 0),
                             ('top1', 'top1_hit', 0), ('hit', 'hit', 2),
                             ('cov', 'cov', 2), ('panic', 'PANIC', 0)):
                vals = []
                for L in SRC:
                    x = g(L, k)
                    if k == 'rate' and x is not None and np.isfinite(x):
                        x = 100 * x
                    if k == 'top1':
                        vals.append(f"{str(x):>10}")
                    else:
                        vals.append(fmt(x if x is not None else float('nan'), 10, p))
                W(f"{T60:>5.1f}{sd:>4}{T:>7.0f}{nm:>10}" + "".join(vals))
            W("")
    W("  四量定义:挂陷=非 FREE 槽数 / top1_hit=是否命中神谕第一峰 / "
      "hit=挂陷落在某 pick 邻域的比例 / cov=picks 被覆盖的比例(邻域 = max(f·bw_oct,15Hz)/2)")
    W("")

    # ── §J 不可比档 ────────────────────────────────────────────────
    W("=" * 118)
    W(f"§J  **不可比档**(PREREG §5⑤:过门率 <{INCOMP_LO}% 或 >{INCOMP_HI}% ⇒ 该档 ΔMSG 单列,不进跨档比较)")
    W("=" * 118)
    for L in SRC:
        for fx in (0, 1):
            v = [R[(L, fx, -45., T60, sd, T)]['rate'] for (T60, sd) in SEEDS for T in RUNGS
                 if (L, fx, -45., T60, sd, T) in R and np.isfinite(R[(L, fx, -45., T60, sd, T)]['rate'])]
            if not v:
                continue
            lo, hi = 100 * min(v), 100 * max(v)
            flag = ('⛔不可比(近0)' if hi < INCOMP_LO else
                    ('⛔不可比(近100)' if lo > INCOMP_HI else '可比'))
            W(f"  src={int(L):>4} 修法={'开' if fx else '关'}: 过门率 [{lo:.2f}%, {hi:.2f}%]  ⇒ {flag}")
    W("")

    # ── §S 修法配对差 ──────────────────────────────────────────────
    W("=" * 118)
    W("§S  修法配对差 δ = ΔMSG(修法开) − ΔMSG(修法关),同源电平同档配对   ⛔ Hr6:变号不得平均")
    W("=" * 118)
    for col, nm in (('dA', 'ΔMSG_自选@消融'), ('dN', 'ΔMSG_自选@有duck')):
        W(f"--- 列 = {nm}")
        for L in SRC:
            for T in RUNGS:
                v = []
                for (T60, sd) in SEEDS:
                    a = R.get((L, 0, -45., T60, sd, T)); b = R.get((L, 1, -45., T60, sd, T))
                    if a and b and np.isfinite(a[col]) and np.isfinite(b[col]):
                        v.append((T60, sd, round(b[col] - a[col], 2), a['n_notch'], b['n_notch']))
                if not v:
                    continue
                s = [x[2] for x in v]
                sign = ('⚠ **变号 —— 按 Hr6 不得平均**'
                        if (any(x > 0 for x in s) and any(x < 0 for x in s)) else '同号')
                W(f"  src={int(L):>4} T_OBS={T:.0f}s  δ(T60,sd,δ,挂陷关,挂陷开):{v}")
                W(f"        符号:正 {sum(1 for x in s if x>0)} / 零 {sum(1 for x in s if x==0)}"
                  f" / 负 {sum(1 for x in s if x<0)}  ⇒ {sign}")
        W("")

    # ── §T 臂 T ────────────────────────────────────────────────────
    W("=" * 118)
    W("§T  臂 T:只动 `T_low`(−45 → −50),源电平固定 —— 拆开『三门齐动』(Hr7)")
    W("   ⚠ `T_low_gr` 在 Params.__init__ 按 T_low−20 算死,构造后不重算 ⇒ 本臂天然只动一个门")
    W("=" * 118)
    W(f"{'src':>6}{'T60':>5}{'sd':>4}{'T_OBS':>7}"
      f"{'ΔMSG消融@−45':>14}{'ΔMSG消融@−50':>14}{'δ_门':>8}"
      f"{'过门率@−45':>12}{'过门率@−50':>12}{'挂陷@−45':>10}{'挂陷@−50':>10}")
    for L in (-60., -20.):
        for (T60, sd) in SEEDS:
            for T in RUNGS:
                a = R.get((L, 0, -45., T60, sd, T)); b = R.get((L, 0, -50., T60, sd, T))
                if not a or not b:
                    continue
                W(f"{int(L):>6}{T60:>5.1f}{sd:>4}{T:>7.0f}"
                  f"{fmt(a['dA'],14)}{fmt(b['dA'],14)}{fmt(b['dA']-a['dA'],8)}"
                  f"{fmt(100*a['rate'],11)}%{fmt(100*b['rate'],11)}%"
                  f"{a['n_notch']:>10}{b['n_notch']:>10}")
        W("")
    W("  ⇒ Hr7 对照量:『门下移 5 dB』的 δ_门  vs  『源上移 5 dB』的效应")
    W("    ⚠ 源电平栅格是 10/20 dB 步长,**没有 5 dB 档** ⇒ 只能与 −60→−40(20 dB)比,")
    W("      ⛔ 不得线性内插(过门率对电平是强非线性,见 §P)。本项只给两端的机械读数。")
    W("")

    # ── §I 不变量汇总 ──────────────────────────────────────────────
    W("=" * 118)
    W("§I  不变量汇总(INV-N 三分 / INV-O 构造精确;⚠ 与派单口径的偏离见 PREREG_r76 §4)")
    W("=" * 118)
    from collections import Counter
    for fx in (0, 1):
        for L in SRC:
            rs = [R[(L, fx, -45., T60, sd, T)] for (T60, sd) in SEEDS for T in RUNGS
                  if (L, fx, -45., T60, sd, T) in R]
            if not rs:
                continue
            cN = Counter(r['inv_N'] for r in rs)
            cO = Counter(r['inv_O'] for r in rs)
            W(f"  src={int(L):>4} 修法={'开' if fx else '关'}  n={len(rs)}  "
              f"INV_N {dict(cN)}   INV_O {dict(cO)}")
            for r in rs:
                if r['inv_N'] == 'FAIL' or r['inv_O'] == 'FAIL':
                    W(f"     ⛔ FAIL 格 T60={r['T60']} sd={r['sd']} T={r['T']:.0f}s "
                      f"INV_N={r['inv_N']} INV_O={r['inv_O']} "
                      f"挂陷O={r['n_notch_O']} N2_lvl_O={r['n2_O']}(诊断)")
    W("  INV_N 三档:OK=动作发生 / ZERO_ACT=全程零动作(**合法的不利结果,照常计入**)/ "
      "FAIL=零动作却有收益 ⇒ 该臂两列作废")
    W("  INV_O 两档(**构造精确**):OK=挂陷8 ∧ 频点==picks / FAIL=构造已散 ⇒ 只作废『上界』一列")
    W("  ⇒ **按臂作废,不按行**(PREREG_r64 修订 B-2)")
    W("")

    # ── §K 达标计数 ────────────────────────────────────────────────
    W("=" * 118)
    W("§K  达标计数(CTO 目标 4–5 dB)—— **分 T60 层,⛔ 不报跨层均值**(M-2)")
    W("=" * 118)
    for col, nm in (('dA', 'ΔMSG_自选@消融(兜底消融列)'), ('dN', 'ΔMSG_自选@有duck'),
                    ('dO', 'ΔMSG_上界@神谕')):
        W(f"--- 列 = {nm}")
        for fx in (0, 1):
            if col == 'dO' and fx == 1:
                continue
            for lay in (0.2, 0.5):
                for L in SRC:
                    rs = [R[(L, fx, -45., lay, sd, T)] for (t, sd) in SEEDS if t == lay
                          for T in RUNGS if (L, fx, -45., lay, sd, T) in R]
                    inv_ok = [r for r in rs
                              if (r['inv_O'] != 'FAIL' if col == 'dO' else r['inv_N'] != 'FAIL')
                              and np.isfinite(r[col])]
                    if not inv_ok:
                        continue
                    v = [r[col] for r in inv_ok]
                    W(f"  T60={lay} src={int(L):>4} 修法={'开' if fx else '关'}  n={len(v)}  "
                      f"逐条 {[round(x,2) for x in v]}  范围 [{min(v):.2f}, {max(v):.2f}]  "
                      f"≥4dB {sum(1 for x in v if x>=TARGETS[0])}/{len(v)}  "
                      f"≥5dB {sum(1 for x in v if x>=TARGETS[1])}/{len(v)}")
            W("")
    W("  ⚠ T60=0.5 层:r64 已证该层 T_OBS=48 s 仍不收敛,本轮钉死 {6,12} s")
    W("    ⇒ **该层的数不得单独成句,须与『该层在 48 s 仍不收敛』同段出现**")
    W("")

    # ── §L 报数点绝对电平(效应 B 的量化)────────────────────────
    W("=" * 118)
    W("§L  **报数点绝对电平** lp_rms@m(求和节点 RMS)—— 效应 B 有多大,看这张")
    W("=" * 118)
    W(f"{'T60':>5}{'sd':>4}{'T_OBS':>7}{'臂':>5}" + "".join(f"{int(L):>10}" for L in SRC))
    for (T60, sd) in SEEDS:
        for T in RUNGS:
            for k, nm in (('lp_m0', 'm0'), ('lp_N', 'N'), ('lp_Na', 'Na'), ('lp_O', 'O')):
                v = [R.get((L, 0, -45., T60, sd, T), {}).get(k, float('nan')) for L in SRC]
                W(f"{T60:>5.1f}{sd:>4}{T:>7.0f}{nm:>5}"
                  + "".join(fmt(x if x is not None else float('nan'), 10) for x in v))
            W("")
    W("  ⇒ 若某臂的 lp_rms 在【低源电平】档反而更高 ⇒ 该档存活到更高的 G ⇒ 效应 B 在起作用")
    W("")

    # ── §G 固定 G 表摘要 ──────────────────────────────────────────
    W("=" * 118)
    W("§G  固定 G 表摘要(**只含效应 A**;全表见 r76_fixedG_out.txt)")
    W("=" * 118)
    p = DIR + 'r76_fixedG.json'
    if not os.path.exists(p):
        W("  ⛔ r76_fixedG.json 不存在 ⇒ 未跑完,**不得引用日志当结果**")
    else:
        F = json.load(open(p))
        SRCF = sorted(set(r['src'] for r in F))
        DG = sorted(set(r['dg'] for r in F))
        for dg in DG:
            W(f"--- ΔG = anchor{dg:+.0f} dB")
            W(f"{'T60':>5}{'sd':>4}{'量':>10}" + "".join(f"{int(L):>10}" for L in SRCF))
            for (T60, sd) in SEEDS:
                for k, nm, p2 in (('n2', 'N2_lvl', 0), ('rate', '过门率%', 2),
                                  ('n_notch', '挂陷', 0), ('lp_rms', 'lp_rms', 2),
                                  ('howl', '起振', 0)):
                    row = []
                    for L in SRCF:
                        m = [r for r in F if r['dg'] == dg and r['T60'] == T60
                             and r['sd'] == sd and r['src'] == L]
                        if not m:
                            row.append(f"{'—':>10}")
                        elif k == 'howl':
                            row.append(f"{str(m[0][k]):>10}")
                        elif k == 'rate':
                            row.append(fmt(100 * m[0][k], 10, 2))
                        else:
                            row.append(fmt(m[0][k], 10, p2))
                    W(f"{T60:>5.1f}{sd:>4}{nm:>10}" + "".join(row))
                W("")
        nonmono, n_pair = [], 0
        for dg in DG:
            for (T60, sd) in SEEDS:
                v = sorted([(r['src'], r['n2']) for r in F
                            if r['dg'] == dg and r['T60'] == T60 and r['sd'] == sd])
                for i in range(len(v) - 1):
                    n_pair += 1
                    if v[i + 1][1] < v[i][1]:
                        nonmono.append((dg, T60, sd, v[i], v[i + 1]))
        W(f"  Hr2 单调性(固定 G 下 N2_lvl 随源电平单调不减):**已比 {n_pair} 对相邻档**,"
          f"违反 **{len(nonmono)}**"
          + ('  ⛔ 已比 0 对 ⇒ 本项未执行,不得读作通过' if n_pair == 0 else ''))
        for x in nonmono[:20]:
            W(f"     ⛔ {x}")
    W("")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。全部 [L2/宿主仿真]。⛔ 未 commit。")
    # D6-j:注册路径唯一。**只有注册跑写 DIR 下那个路径**;
    #      冒烟/试跑须用 `R76_MERGE_OUT` 指到别处,不得复用注册路径。
    outp = os.environ.get('R76_MERGE_OUT', DIR + 'r76_srclevel_full_out.txt')
    with open(outp, 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    print(f"[written] {outp}")


if __name__ == '__main__':
    main()
