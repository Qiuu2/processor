#!/usr/bin/env python3
"""
d34 杀伤矩阵驱动件(自 r16 起机械化;此前是手工跑 + 手工抄表)
⭐⭐ 本文件名**刻意不带轮次号**(2026-08-05 · critic D3D4-r3 MAJOR-2):
   上一版叫 `run_killmatrix_r16.py`,而 critic 用本文件自己的模块头当证据 ——
   「r16 起机械化,此前是手工跑」= **驱动件是每轮换的** ⇒ 换件时没有任何东西强迫
   新件带上基线登记。⇒ ∴ 驱动件与登记件**都**改成轮次无关的名字。
   ⚠ 而【结果件】仍带轮次(results_d34_rN_killmatrix.txt)—— 那是 02impl-r11 的教训,
     两件事方向相反:**工具不带轮次,产物必须带轮次。**
⛔ 门禁状态:未过门。

⭐⭐ 本轮它必须改的那一件事:**好版本不再是「FAIL = 0」**。
   EXP-5c(**参数字典范围上的最坏**噪声底突破 PRD)是一条**如实为 FAIL 的检查**
   (预先写死在 PREREG_D34_r16_addendum §3:⛔ 不退役、⛔ 不改判据)。
⇒ 于是「杀死 = 出现了 FAIL」这个旧判据**失效**:它会把基线里那条 FAIL
  算成每一个变异的战功 ⇒ **6 条假杀伤**。
⇒ 新判据:**杀死 = FAIL 集合【超出基线】**。基线本身必须逐条具名登记。

用法: python3 run_killmatrix.py > results_d34_rN_killmatrix.txt
退出码: 0 = 全部变异都被杀死且基线与登记相符;非 0 = 有变异存活 / 基线漂移
"""
import subprocess
import sys
import os
import datetime
import hashlib

D = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(D, "d34_analysis.py")

# ⛔⛔ 登记**不在本文件里**(critic D3D4-r3 MAJOR-2 修法①,2026-08-05)
#   上一版把 `BASELINE_EXPECTED = {"EXP-5c"}` 写死在这里,而**本文件名带轮次号**。
#   ⇒ critic 用本项目自己的历史当证据:本文件模块头就写着「r16 起机械化;此前是手工跑 + 手工抄表」
#     = **驱动件是每轮换的** ⇒ r17 写新驱动件时,**没有任何东西强迫它带上这份登记**。
#   ⇒ ⛔ 那不需要任何人想洗掉它 —— 只需要有人重写驱动件时没读本文件。
# ⇒ ∴ 登记移到**不带轮次号**的 `BASELINE_FAILS.txt`;本文件只读它。
#   ⛔ 读不到就【中止】,⛔ 不回退到内嵌默认值 —— 回退等于把逃逸路径又开回来。
_REG = os.path.join(D, "BASELINE_FAILS.txt")
if not os.path.exists(_REG):
    sys.stderr.write(f"⛔ 找不到登记件 {_REG};⛔ 拒绝在无登记的情况下跑杀伤矩阵。\n")
    sys.exit(2)
BASELINE_EXPECTED = set()
for _ln in open(_REG, encoding="utf-8"):
    _ln = _ln.strip()
    if _ln and not _ln.startswith("#") and not _ln.startswith("|"):
        BASELINE_EXPECTED.add(_ln.split("|")[0].strip())

MUTANTS = ["polarity", "qcoef", "freeq", "hpf_order", "xo_order", "qcoef_and_freeq",
           "noisemodel_countbug", "noisemodel_nointer"]

# ==========================================================================
# 声明的【基线翻绿】(Y12，2026-08-05)—— 一条常驻 FAIL 的证伪证据长什么样
# --------------------------------------------------------------------------
# 先说清那个不对称：
#   普通检查 是绿的 => 证伪证据 = 存在一个缺陷让它变红（= 被杀死）
#   常驻 FAIL 已经是红的 => 它不可能再被杀死
#     => 形态反过来：存在一个缺陷让它【翻绿】 => 证明它不是恒 FAIL
# 本表逐条声明「哪个变异被允许让哪条基线项翻绿，以及为什么」：
#   未声明的翻绿 仍判 FAIL（那是"变异改动了它不该改的东西"）
#   已声明的翻绿 记为该基线项的【证伪证据】
# 边界（必须守住）：本表【不改变任何判据】，它只解释一次预期内的翻绿。
#   「声明我预期它翻绿」与「把判据放宽到它不再红」是两件事，
#   而它们在结果文件里长得很像。
# ==========================================================================
EXPECTED_LOST = {
    "noisemodel_nointer": ({"EXP-5c"},
        "该变异拿掉级间传函 => 噪声模型退化回直接功率相加 => 最坏合法配置算出来与各节增益=1 相同"
        "（-163.81 <= -106）=> EXP-5c 翻绿。=> 这【就是】EXP-5c 的证伪证据："
        "它红是因为级间增益那一项，不是因为它恒红。"),
}


def run(broken=None):
    cmd = [sys.executable, SCRIPT] + ([f"--broken={broken}"] if broken else [])
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    fails = []
    total = ""
    for ln in p.stdout.splitlines():
        s = ln.strip()
        if s.startswith("[FAIL]"):
            fails.append(s.split()[1])
        if s.startswith("合计:"):
            total = s
    return set(fails), total, p.returncode


print("=" * 88)
print("results_d34_killmatrix —— 杀伤矩阵(基线感知版;⚠ 轮次以文件名为准)")
print(f"deps: d34_analysis.py@{hashlib.sha256(open(SCRIPT,'rb').read()).hexdigest()[:16]}")
print(f"跑批时间: {datetime.datetime.now().astimezone().isoformat(timespec='seconds')}   门禁状态: 未过门")
print("=" * 88)
print("""
⭐ 判据变更(r16):**杀死 = FAIL 集合超出基线**,⛔ 不再是「出现 FAIL」。
   缘由:好版本自 r16 起带一条如实为 FAIL 的检查(EXP-5c)。
   若沿用旧判据,那一条会被记成每个变异的战功 ⇒ 6 条假杀伤。
   ⇒ 这与 critic BLOCKER-2 打的是同一个病:**把功记在错的缺陷上**。
""")

rc = 0
base_fails, base_total, base_rc = run(None)
print(f"基线(出货构建) FAIL 集合 = {sorted(base_fails)}")
print(f"  {base_total}")
if base_fails != BASELINE_EXPECTED:
    print(f"  [FAIL] 基线登记  实测 {sorted(base_fails)} ≠ 登记 {sorted(BASELINE_EXPECTED)}"
          f"  ⇒ ⛔ 基线漂移,矩阵结果不可信")
    rc = 1
else:
    print(f"  [PASS] 基线登记  与 BASELINE_EXPECTED 逐条相符 ⇒ 下面的"
          f"「杀死」全部是【超出基线】的部分")
print()
print(f"{'变异':<18s} {'超出基线杀死的 EXP':<46s} {'合计'}")
print("-" * 88)
for m in MUTANTS:
    f, t, _ = run(m)
    killed = sorted(f - base_fails)
    lost = sorted(base_fails - f)
    exp_lost, why = EXPECTED_LOST.get(m, (set(), ""))
    lost_undeclared = [x for x in lost if x not in exp_lost]
    lost_declared = [x for x in lost if x in exp_lost]
    note = ""
    # ⛔ 未杀死【且】没有任何声明内的基线翻绿 ⇒ 存活
    if not killed and not lost_declared:
        rc = 1
        note += "  \u26d4 \u53d8\u5f02\u672a\u88ab\u6740\u6b7b\uff08\u5b58\u6d3b\uff09"
    if lost_undeclared:
        note += f"  \u26d4 \u57fa\u7ebf\u4e2d\u7684 {lost_undeclared} \u5728\u672c\u53d8\u5f02\u4e0b\u53cd\u800c PASS \u21d2 \u53d8\u5f02\u6539\u52a8\u4e86\u5b83\u4e0d\u8be5\u6539\u7684\u4e1c\u897f"
        rc = 1
    if lost_declared:
        note += f"  \u2b50 \u58f0\u660e\u5185\u7684\u57fa\u7ebf\u7ffb\u7eff {lost_declared} \u21d2 \u8bb0\u4e3a\u8be5\u57fa\u7ebf\u9879\u7684\u3010\u8bc1\u4f2a\u8bc1\u636e\u3011"
    _kills = ' '.join(killed) if killed else '(\u65e0)'
    print(f"{m:<20s} {_kills:<46s} {t}{note}")
    if lost_declared:
        print(f"{'':<20s} \u21b3 {why}")

print("-" * 88)
print("\n⚠ 未知变异名闸门(critic BLOCKER-2 修法④,r16 补做):")
p = subprocess.run([sys.executable, SCRIPT, "--broken=__nonexistent__"],
                   capture_output=True, text=True, timeout=1800)
# ⛔⛔ 退出码 2 现在有【两个来源】:未知变异名 与 META-1(登记项缺失)。
#   ⇒ 只看 "== 2" 会让 META-1 的红把这一条染绿 —— 那正是本文件在别处修掉的那个病
#     (把功记在错的缺陷上)。⇒ ∴ 必须同时核【它自己的失败特征】。
ok_guard = (p.returncode == 2 and "未知的 --broken 名" in p.stderr)
print(f"  [{'PASS' if ok_guard else 'FAIL'}] --broken=__nonexistent__ 退出码 = {p.returncode}(须 = 2)"
      f" ∧ stderr 命中「未知的 --broken 名」(须命中,⛔ 否则那个 2 可能来自 META-1)")
if not ok_guard:
    rc = 1

# ⭐ META-1 反向闸门:基线跑批的退出码**不得**是 2 —— 2 意味着登记项已从判定集合里消失。
print("\n⚠ META-1(登记项必须存在)在基线上的状态:")
ok_meta = (base_rc != 2)
print(f"  [{'PASS' if ok_meta else 'FAIL'}] 基线跑批退出码 = {base_rc}(⛔ 不得为 2;2 = 登记项不见了)")
if not ok_meta:
    rc = 1

# ---- 基线项的证伪证据汇总(⛔ 每条基线项都必须有,否则它可能是恒 FAIL)----
print()
print("⭐ 基线项的证伪证据(⛔ 常驻 FAIL 不能靠『被杀死』证明自己有分辨力)")
for tag in sorted(BASELINE_EXPECTED):
    provers = [m for m, (ls, _) in EXPECTED_LOST.items() if tag in ls]
    if provers:
        print(f"  [PASS] {tag:<10s} 存在使它【翻绿】的变异:{provers} ⇒ 它不是恒 FAIL")
    else:
        print(f"  [FAIL] {tag:<10s} ⛔ **没有任何变异能让它翻绿** ⇒ 无法排除它是恒 FAIL")
        print(f"         ⇒ ⛔ 不得声称『该维已被变异覆盖』(设计件 Y12)")
        rc = 1

print("=" * 88)
print(f"退出码 = {rc}")
sys.exit(rc)
