"""r79 · 等预算线合并件 —— **只读逐格 json,⛔ 不重跑仿真**(D6-j)。
⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r79.txt。输出 r79_isobudget_out.txt。
⛔ 本文件不含结论性散文;判定语句 = 预注册里已写死的机械检查。
"""
import sys, os, json, glob
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
FLOOR = 0.25 * (2 ** 0.5)
SE = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
T = [('N08', 8, '8×1/8'), ('N10', 10, '10×1/10'),
     ('N16', 16, '16×1/16'), ('N24', 24, '24×1/24')]
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)


def main():
    R = []
    for p in glob.glob(DIR + 'r79_cell_*.json'):
        R += json.load(open(p))
    K = {(r['tag'], r['T60'], r['sd']): r for r in R}
    R78 = []
    for p in glob.glob(DIR + 'r78_cell_*.json'):
        R78 += json.load(open(p))
    K78 = {(r['tag'], r['T60'], r['sd']): r for r in R78}
    miss = [(t, a, b) for t, _, _ in T for (a, b) in SE if (t, a, b) not in K]

    W("未经 critic 评审 —— r79 · **等预算线** NN × bw_oct ≡ 1.00 倍频程  [L2/宿主仿真]")
    W("预注册 = PREREG_r79.txt(跑前落盘)。⛔ 只读逐格 json。⛔ 未 commit。")
    W("⛔⛔ **全程不用「上界」一词** —— r78 已实测该名在 bw_oct ≤ 1/8 上不成立;")
    W("     本轮四格**全部**在 1/8 及以下 ⇒ 一律称 `臂O@神谕选点`。")
    W("⛔⛔ **呈报 = 同条件内比较**;**仪器底 0.354 dB**,差值 < 它 ⇒ 写「不可判」。")
    W("⚠ 职C:各档的臂 O 是【该 NN 与该预算下的】臂 O,**不是同一个基准**(D6-af 红线)。")
    W("⚠ 职D:评价尺子**钉死 1/5**,四档共用。")
    W("⚠ 参照 R05(8×1/5 = 1.60 oct,**超预算**)复用 r78 的 C1,⛔ 只作对照不作结论。")
    if miss:
        W(f"⛔⛔ 缺格:{miss}")
    W("")

    # ── §A 三列主表 ────────────────────────────────────────────
    for col, nm in (('dO', '臂O@神谕选点'), ('dA', 'ΔMSG_自选@消融(**兜底消融列**)'),
                    ('n_notch', '挂陷数(整数,不受仪器底约束)')):
        W("=" * 112)
        W(f"§A  {nm}   等预算线 1.00 oct   |  末列 = R05 参照(1.60 oct,超预算)")
        W("=" * 112)
        W(f"{'T60':>5}{'sd':>4}" + "".join(f"{n:>13}" for _, _, n in T) + f"{'[R05]':>13}")
        for (t60, sd) in SE:
            cells = []
            for tag, _, _ in T:
                v = K.get((tag, t60, sd), {}).get(col)
                cells.append(f"{v:>13.2f}" if isinstance(v, float) else f"{v:>13}")
            v5 = K78.get(('C1', t60, sd), {}).get(col)
            cells.append(f"{v5:>13.2f}" if isinstance(v5, float) else f"{v5:>13}")
            W(f"{t60:>5.1f}{sd:>4}" + "".join(cells))
        W("")

    # ── §S ⭐ 饱和点 ───────────────────────────────────────────
    W("=" * 112)
    W("§S  ⭐⭐ **Hc2:饱和点** —— ⛔ 不报「NN 越大越好」,报【在哪一档饱和】")
    W(f"    饱和判据(预注册写死):相邻档配对差的中位 < 仪器底 {FLOOR:.3f} dB ⇒ 视为已饱和")
    W("=" * 112)
    W(f"{'档':>12}{'逐条配对差':>44}{'可判格':>8}{'中位':>8}{'升/降/平':>10}  判定")
    for i in range(len(T) - 1):
        a, b = T[i][0], T[i + 1][0]
        d = [K[(b, t, s)]['dO'] - K[(a, t, s)]['dO'] for (t, s) in SE
             if (a, t, s) in K and (b, t, s) in K]
        if not d:
            continue
        nj = sum(1 for x in d if abs(x) >= FLOOR)
        med = float(np.median(d))
        W(f"{a+'→'+b:>12}{str([round(x,2) for x in d]):>44}{nj:>6}/6{med:>+8.2f}"
          f"{f'{sum(1 for x in d if x>0)}/{sum(1 for x in d if x<0)}/{sum(1 for x in d if x==0)}':>10}"
          f"  {'**已饱和**(中位在仪器底之下)' if abs(med) < FLOOR else '仍在改善'}")
    W("")
    W(f"{'配置':>6}{'NN':>4}{'臂O≥4':>8}{'臂O≥5':>8}{'臂O中位':>9}"
      f"{'自选≥4':>8}{'自选中位':>9}{'Z中位':>8}{'挂陷/NN中位':>12}")
    for tag, nn, _ in T + [('R05', 8, '')]:
        src = K78 if tag == 'R05' else K
        key = 'C1' if tag == 'R05' else tag
        rs = [src[(key, t, s)] for (t, s) in SE if (key, t, s) in src]
        if not rs:
            continue
        dO = [r['dO'] for r in rs]
        dA = [r['dA'] for r in rs]
        Z = [r['dO'] - r['dA'] for r in rs]
        oc = [r['n_notch'] / nn for r in rs]
        W(f"{tag:>6}{nn:>4}{sum(1 for x in dO if x>=4):>6}/6{sum(1 for x in dO if x>=5):>6}/6"
          f"{np.median(dO):>9.2f}{sum(1 for x in dA if x>=4):>6}/6{np.median(dA):>9.2f}"
          f"{np.median(Z):>+8.2f}{np.median(oc):>12.2f}")
    W("  ⚠ R05 = 超预算 1.60 oct 参照,⛔ 不作结论")
    W("")

    # ── §H Hc1 不对称 ─────────────────────────────────────────
    W("=" * 112)
    W("§H  ⭐ **Hc1(lead 预注册的不对称)** —— 物理依据:模态带宽 ≈ 2.2/T60")
    W("    预测:T60=0.5(模态 4.4 Hz)应【明显受益】于多而窄;T60=0.2(模态 11.0 Hz)应【更早饱和】")
    W("    ⛔ 预注册写死:若实测反过来 ⇒ 记 F 条,不替 lead 圆")
    W("=" * 112)
    for lay in (0.2, 0.5):
        d = [K[('N24', lay, s)]['dO'] - K[('N08', lay, s)]['dO']
             for (t, s) in SE if t == lay and ('N24', lay, s) in K]
        W(f"  T60={lay}(模态带宽 {2.2/lay:.1f} Hz)  臂O 的 N08→N24 变化:"
          f"{[round(x,2) for x in d]}  升 {sum(1 for x in d if x>0)}/3  中位 {np.median(d):+.2f}")
        for tag, _, _ in T:
            v = [K[(tag, lay, s)]['dO'] for (t, s) in SE if t == lay and (tag, lay, s) in K]
            W(f"      {tag} 臂O {[round(x,2) for x in v]}  ≥5dB **{sum(1 for x in v if x>=5)}/3**"
              f"  ≥4dB {sum(1 for x in v if x>=4)}/3")
        W("")

    # ── §N ⭐ 自选臂是否跟得上 ─────────────────────────────────
    W("=" * 112)
    W("§N  ⭐⭐ **自选臂跟不跟得上**:天花板抬起来了,NHS 用不用得上那些槽")
    W("=" * 112)
    W(f"{'T60':>5}{'sd':>4}" + "".join(f"{n+' 挂陷/NN':>16}" for _, _, n in T))
    for (t60, sd) in SE:
        W(f"{t60:>5.1f}{sd:>4}"
          + "".join(f"{K[(tag,t60,sd)]['n_notch']:>7}/{nn:<3}"
                    f"{K[(tag,t60,sd)]['n_notch']/nn:>6.2f}" if (tag, t60, sd) in K else f"{'—':>16}"
                    for tag, nn, _ in T))
    W("")

    # ── §I 倒挂 + INV-O ───────────────────────────────────────
    W("=" * 112)
    W("§I  倒挂(臂 Na ≥ 臂 O)与 INV-O(挂陷==NN ∧ 频点逐一==picks)")
    W("=" * 112)
    bad = [r for r in R if not r['invO']]
    W(f"  INV-O FAIL:**{len(bad)} / {len(R)}**"
      + ('  ✅ 全部 OK ⇒ 倒挂不是「臂 O 构造散了」造成的' if not bad else ''))
    for r in bad:
        W(f"     ⛔ {r['tag']} T60={r['T60']} sd={r['sd']}: 臂O挂陷={r['n_notch_O']}/{r['nn']}")
    neg = sorted([r for r in R if np.isfinite(r['Z']) and r['Z'] < 0], key=lambda r: r['Z'])
    W(f"  倒挂格:**{len(neg)} / {len(R)}**")
    for r in neg:
        W(f"     {r['tag']} T60={r['T60']} sd={r['sd']}: 自选@消融={r['dA']:.2f} "
          f"臂O={r['dO']:.2f} Z={r['Z']:+.2f}  "
          + ('**在仪器底之上,可判**' if abs(r['Z']) > FLOOR else '(底下,不可判)'))
    W("")

    # ── §F 地板 + 占用 ────────────────────────────────────────
    W("=" * 112)
    W("§F  15 Hz 地板效应 与 占用普查")
    W("=" * 112)
    W("  ① 地板:`_bw_hz = max(f·bw, 15Hz)` ⇒ f < 15/bw 处匹配窗被顶成 15 Hz")
    W("     ⚠ 地板**只作用于匹配窗,不作用于滤波器形状** ⇒ 低频段两者不一致")
    for tag, _, _ in T:
        v = [K[(tag, t, s)]['pct_floor'] for (t, s) in SE if (tag, t, s) in K]
        ff = K[(tag, 0.2, 0)]['f_floor']
        W(f"     {tag}(转折 {ff:.0f} Hz):挂陷频点落在地板段内的比例 "
          f"{[round(x,1) for x in v]} %  最大 {max(v):.1f}%")
    W("     ⇒ 该比例即「本档有多少结论可能被地板污染」——⛔ 判读时须剔除")
    tfr = [r['table_full'] / max(r['slots_n'], 1) for r in R]
    n0r = [r['n0'] / max(r['slots_n'], 1) for r in R]
    n1r = [r['n1'] / max(r['slots_n'], 1) for r in R]
    nt = [r['ntr_max'] for r in R]
    W(f"  ② 占用(n_cand 已提到 **48**,四格恒定):")
    W(f"     `table_full`/槽 = {min(tfr):.3f} – {max(tfr):.3f} ⇒ **截断仍在 "
      f"{100*min(tfr):.1f}–{100*max(tfr):.1f}% 的槽上发生**(48 < 局部极大数)")
    W(f"     `N0_locmax`/槽 = {min(n0r):.1f} – {max(n0r):.1f};`N1_cand`/槽 = "
      f"{min(n1r):.2f} – {max(n1r):.2f}")
    W(f"     `n_track` 峰值 = [{min(nt)}, {max(nt)}] / 12;触顶格 "
      f"{sum(1 for x in nt if x >= 12)}/{len(nt)}")
    W("")
    W("  ③ `n_cand` 单独效应(r79-N08 @48 vs r78-C2 @16;**同 NN 同 bw,只差 n_cand**):")
    for (t60, sd) in SE:
        a, b = K.get(('N08', t60, sd)), K78.get(('C2', t60, sd))
        if not (a and b):
            continue
        d = a['dA'] - b['dA']
        W(f"     T60={t60} sd={sd}: 自选@消融 16→48: {b['dA']:.2f} → {a['dA']:.2f}  "
          f"Δ={d:+.2f}  " + ('**可判**' if abs(d) > FLOOR else '(底下,不可判)')
          + f"  挂陷 {b['n_notch']} → {a['n_notch']}")
    W("")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。全部 [L2/宿主仿真]。⛔ 未 commit。")
    outp = os.environ.get('R79_MERGE_OUT', DIR + 'r79_isobudget_out.txt')
    with open(outp, 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    print(f"[written] {outp}")


if __name__ == '__main__':
    main()
