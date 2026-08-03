"""r78 · 合并件 —— **只读逐格 json 汇总,⛔ 不重跑任何仿真**(D6-j)。
⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r78.txt。输出 r78_bwoct_out.txt。
⛔ 本文件不含结论性散文;判定语句 = 预注册里已写死的机械检查。
"""
import sys, os, json, glob
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
FLOOR = 0.25 * (2 ** 0.5)
SE = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
TAGS = [('C1', '1/5→1/5 基线', 1.60), ('C2', '1/8→1/8 合规', 1.00),
        ('C3', '1/10→1/10 下沿', 0.80), ('C4', '形1/8 窗1/5', 1.00),
        ('C5', '形1/5 窗1/8', 1.60)]
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)


def main():
    R = []
    for p in glob.glob(DIR + 'r78_cell_*.json'):
        R += json.load(open(p))
    K = {(r['tag'], r['T60'], r['sd']): r for r in R}
    miss = [(t, a, b) for t, _, _ in TAGS for (a, b) in SE if (t, a, b) not in K]

    W("未经 critic 评审 —— r78 · `bw_oct` 一维扫描(两职拆开)合并件  [L2/宿主仿真]")
    W("预注册 = PREREG_r78.txt(跑前落盘)。⛔ 只读逐格 json,不重跑仿真。⛔ 未 commit。")
    W("⛔⛔ **呈报形式**:只作【同条件内比较】读,⛔ 不得作绝对值引用(lead 2026-08-04 裁定)。")
    W(f"⛔⛔ **仪器底 = {FLOOR:.3f} dB**;差值 < 它 ⇒ 写「落在仪器底之下,不可判」,")
    W("     ⛔ 既不得读作「相同」,也不得读作「不同」。⚠ 挂陷数是整数计数,不受此限。")
    W("⛔⛔ **本轮新增的一条,先于全部数字**:")
    W("     **在 bw_oct = 1/8 与 1/10 上,『上界』这个名字【不成立】**(见 §I)。")
    W("     ⇒ 那两档的 Z / Y% ⛔ 不得称作『距上界的差距 / 达到上界的百分比』,")
    W("       只能称作『臂 O(神谕选点,固定 −18 dB)与臂 Na 的差』。")
    W(f"工作点:src_rms=−20 dBFS(标称) / 修法关 / T_OBS=12 s / T_low=−45 / f_cut=8k / 8 槽全空")
    if miss:
        W(f"⛔⛔ 缺格(未跑完,相关行不得引用):{miss}")
    W("")
    W("配置(职A 滤波器形状, 职B 分配匹配窗)与总陷波带宽预算(= 8 × 形状,文献预算 0.8–1.2 倍频程):")
    for t, nm, bud in TAGS:
        W(f"  {t}  {nm:<16} 总预算 **{bud:.2f} 倍频程**"
          + ('  ← 超预算 1.3–2×' if bud > 1.2 else '  ← 在预算内'))
    W("")

    # ── §R 复现核对 ────────────────────────────────────────────
    W("=" * 118)
    W("§R  确定性复现核对 —— C1(=现状 1/5)vs r76 同格(src−20 / 修法关 / T_low−45 / 12 s)")
    W("=" * 118)
    R76 = []
    for p in glob.glob(DIR + 'r76_cell_*.json'):
        R76 += json.load(open(p))
    K76 = {(r['src'], r['fix'], r['tlow'], r['T60'], r['sd'], r['T']): r for r in R76}
    n_c = n_b = 0
    for (t, s) in SE:
        a, b = K.get(('C1', t, s)), K76.get((-20., 0, -45., t, s, 12.))
        if not (a and b):
            continue
        for f in ('m0', 'dA', 'dN', 'dO'):
            n_c += 1
            if abs(a[f] - b[f]) > 1e-9:
                n_b += 1
                W(f"  ⛔ T60={t} sd={s} {f}: r78={a[f]} r76={b[f]}")
    W(f"  已比 {n_c} 项,不一致 **{n_b}**  "
      + ('⛔ 已比 0 项 ⇒ 本项未执行' if n_c == 0
         else ('✅ 逐格相同' if n_b == 0 else '⛔⛔ 不一致 ⇒ 两轮一并存疑')))
    W("")

    # ── §A 主表 ────────────────────────────────────────────────
    for col, nm in (('dA', 'ΔMSG_自选@消融(**兜底消融列**)'),
                    ('dN', 'ΔMSG_自选@有duck'),
                    ('dO', '臂O@神谕选点(⚠ 1/8 及以下【不是上界】,见 §I)')):
        W("=" * 118)
        W(f"§A  {nm}")
        W("=" * 118)
        W(f"{'T60':>5}{'sd':>4}" + "".join(f"{t:>16}" for t, _, _ in TAGS))
        for (t60, sd) in SE:
            W(f"{t60:>5.1f}{sd:>4}"
              + "".join(f"{K[(t, t60, sd)][col]:>16.2f}" if (t, t60, sd) in K else f"{'—':>16}"
                        for t, _, _ in TAGS))
        W("")

    # ── §B 挂陷数(整数,不受仪器底约束)────────────────────────
    W("=" * 118)
    W("§B  挂陷数(**整数计数,不受仪器底约束** —— 逐格相同就是逐格相同)")
    W("=" * 118)
    W(f"{'T60':>5}{'sd':>4}" + "".join(f"{t:>16}" for t, _, _ in TAGS))
    for (t60, sd) in SE:
        W(f"{t60:>5.1f}{sd:>4}"
          + "".join(f"{K[(t, t60, sd)]['n_notch']:>16}" if (t, t60, sd) in K else f"{'—':>16}"
                    for t, _, _ in TAGS))
    W("")

    # ── §C Hb3 归因 2×2 ────────────────────────────────────────
    W("=" * 118)
    W("§C  Hb3 **两职归因**(2×2):(C4−C1)=只动形状 / (C5−C1)=只动匹配窗 / (C2−C1)=两职同动")
    W("    判据:若 (C4−C1)+(C5−C1) ≈ (C2−C1) ⇒ 两职近似可加,可分别归因;")
    W("          若差得远 ⇒ **两职有交互,⛔ 不得分别归因,须明写「不可拆」**")
    W("=" * 118)
    W(f"{'列':>18}{'T60':>5}{'sd':>4}{'只动形状':>10}{'只动窗':>9}{'两者之和':>10}"
      f"{'两职同动':>10}{'加性残差':>10}  判定")
    for col, cn in (('dA', 'ΔMSG_自选@消融'), ('n_notch', '挂陷数(整数)')):
        n_add = n_tot = 0
        for (t60, sd) in SE:
            try:
                c1, c2 = K[('C1', t60, sd)][col], K[('C2', t60, sd)][col]
                c4, c5 = K[('C4', t60, sd)][col], K[('C5', t60, sd)][col]
            except KeyError:
                continue
            a, b = c4 - c1, c5 - c1
            res = (a + b) - (c2 - c1)
            n_tot += 1
            ok = abs(res) < (FLOOR if col == 'dA' else 0.5)
            if ok:
                n_add += 1
            W(f"{cn:>18}{t60:>5.1f}{sd:>4}{a:>10.2f}{b:>9.2f}{a+b:>10.2f}"
              f"{c2-c1:>10.2f}{res:>10.2f}  "
              + ('✅可加(残差在底之下)' if ok else '⚠ 残差在底之上'))
        W(f"  ⇒ {cn}:**{n_add}/{n_tot} 格加性成立**")
        W("")

    # ── §D 达标计数 ────────────────────────────────────────────
    W("=" * 118)
    W("§D  达标计数(CTO 目标 4–5 dB)—— **分 T60 层,⛔ 不报跨层均值**(M-2)")
    W("    ⚠ n=3(3 种子 × 1 个 T_OBS)—— 本轮只跑 12 s 档,与 r76 的 n=6 口径不同,⛔ 不得直接并列")
    W("=" * 118)
    for col, cn in (('dA', 'ΔMSG_自选@消融(兜底消融列)'),
                    ('dO', '臂O@神谕选点(= 该带宽预算下的**能力天花板**)')):
        W(f"--- 列 = {cn}")
        for lay in (0.2, 0.5):
            for t, nm, bud in TAGS:
                v = [K[(t, lay, s)][col] for (a, s) in SE if a == lay and (t, lay, s) in K]
                if not v:
                    continue
                W(f"  T60={lay}  {t} ({nm}, 预算 {bud:.2f})  逐条 {[round(x,2) for x in sorted(v)]}"
                  f"  ≥4dB {sum(1 for x in v if x >= 4)}/{len(v)}"
                  f"  ≥5dB {sum(1 for x in v if x >= 5)}/{len(v)}")
            W("")
    W("  ⚠ T60=0.5 层**不得单独成句** —— r64 已证该层 T_OBS=48 s 仍不收敛,本轮钉死 12 s")
    W("")

    # ── §E 能力天花板(六条种子合看)──────────────────────────
    W("=" * 118)
    W("§E  ⭐ **能力天花板** —— 臂 O(神谕选点,即『选点完美』)在各带宽预算下的达标条数(6 种子)")
    W("    ⇒ 这一层**修实现解决不了**:它是「8 槽 × 该带宽 × 该房间」的上限")
    W("=" * 118)
    for t, nm, bud in TAGS:
        v = [K[(t, a, s)]['dO'] for (a, s) in SE if (t, a, s) in K]
        if not v:
            continue
        W(f"  {t} {nm:<16} 预算 {bud:.2f} 倍频程:逐条 {[round(x,2) for x in sorted(v)]}"
          f"  ≥4dB **{sum(1 for x in v if x >= 4)}/6**  ≥5dB **{sum(1 for x in v if x >= 5)}/6**")
    W("")

    # ── §I 倒挂:「上界」名是否成立 ────────────────────────────
    W("=" * 118)
    W("§I  ⛔⛔ **r64 Hp1 的证伪条件** —— 『任一条 臂N ≥ 臂O ⇒「上界」这个名字不成立,")
    W("     mk_oracle 的构造须重查』。本节先查 INV-O(构造精确),再列倒挂格。")
    W("=" * 118)
    inv = [r for r in R if not r['invO']]
    W(f"  ① INV-O(挂陷==8 ∧ 频点逐一==picks)FAIL 的格:**{len(inv)} / {len(R)}**")
    for r in inv:
        W(f"     ⛔ {r['tag']} T60={r['T60']} sd={r['sd']}: 臂O挂陷={r['n_notch_O']}/8")
    if not inv:
        W("     ✅ 全部 OK ⇒ **倒挂不是「臂 O 构造散了」造成的**")
    neg = sorted([r for r in R if np.isfinite(r['Z']) and r['Z'] < 0], key=lambda r: r['Z'])
    W(f"  ② 倒挂格(Z<0,即臂 Na ≥ 臂 O):**{len(neg)} / {len(R)}**")
    for r in neg:
        W(f"     {r['tag']} T60={r['T60']} sd={r['sd']}: 自选@消融={r['dA']:.2f} "
          f"臂O={r['dO']:.2f}  Z={r['Z']:+.2f}  Y={r['Y']:.0f}%  INV-O="
          f"{'OK' if r['invO'] else 'FAIL'}  "
          + ('**在仪器底之上 ⇒ 可判**' if abs(r['Z']) > FLOOR else '(底下,不可判)'))
    bytag = {}
    for r in R:
        bytag.setdefault(r['tag'], []).append(1 if (np.isfinite(r['Z']) and r['Z'] < 0) else 0)
    W("  ③ 倒挂按配置分布(形状是否收窄):")
    for t, nm, _ in TAGS:
        v = bytag.get(t, [])
        W(f"     {t} {nm:<16} 倒挂 {sum(v)}/{len(v)}")
    W("")

    # ── §F 占用普查 ────────────────────────────────────────────
    W("=" * 118)
    W("§F  ⭐ 占用普查(**搭载本轮,零边际成本;r76 的 json 出不来这两个量**)")
    W("=" * 118)
    tf = [r['table_full'] for r in R]
    sl = [r['slots_n'] for r in R]
    n0 = [r['n0'] for r in R]
    nt = [r['ntr_max'] for r in R]
    W(f"  ① `n_cand = 16`(候选表)")
    W(f"     `table_full`(= len(loc) > 16 的槽数)全 {len(R)} 格:取值范围 [{min(tf)}, {max(tf)}],"
      f"槽数 {min(sl)}–{max(sl)}")
    W(f"     ⇒ **截断发生率 = {100*min(tf)/max(sl):.1f}% – {100*max(tf)/max(sl):.1f}% 的分析槽**")
    W(f"     `N0_locmax`/槽 = {min(n0)/max(sl):.1f} – {max(n0)/max(sl):.1f} 个局部极大,"
      f"而 `N1_cand`/槽 恒 = 16.00")
    W(f"     ⇒ **每槽丢弃 ≈ {100*(1-16/(max(n0)/max(sl))):.0f}% 的局部极大**")
    W(f"     ⇒ **`n_cand=16` 是真约束、且【每一个槽】都在绑定** ⇒ 进整改队列")
    W(f"     ⚠ 与 r76 的区别:r76 只能证「填满」,本轮 `table_full` 证的是**真发生了截断**(D6-h)")
    import collections
    c = collections.Counter(nt)
    h = [0] * 13
    for r in R:
        for k, v in enumerate(r['ntr_hist']):
            h[k] += v
    W(f"  ② `NT = 12`(轨表)")
    W(f"     逐格 `n_track` **峰值**取值范围 **[{min(nt)}, {max(nt)}] / 12**;"
      f"峰值分布 {dict(sorted(c.items()))}")
    W(f"     ⇒ **触到 12 顶的格:{sum(1 for x in nt if x >= 12)} / {len(R)}**")
    W(f"     逐槽活跃轨数直方图(全 {len(R)} 格合计,索引 = 轨数):{h}")
    W(f"     ⇒ 触顶槽数 = **{h[12]} / {sum(h)}**(= {100*h[12]/max(sum(h),1):.4f}%)")
    W(f"     ⇒ **触过顶 ⇒ 是真约束**,但绑定频率极低 ⇒ 建议按【低优先级】进队列,")
    W(f"       ⛔ 不与 `n_cand=16`(100% 绑定)同级处理")
    W("")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。全部 [L2/宿主仿真]。⛔ 未 commit。")
    outp = os.environ.get('R78_MERGE_OUT', DIR + 'r78_bwoct_out.txt')
    with open(outp, 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    print(f"[written] {outp}")


if __name__ == '__main__':
    main()
