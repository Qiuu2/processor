#!/usr/bin/env python3
"""
d34 杀伤矩阵驱动件(r16 起机械化;此前是手工跑 + 手工抄表)
⛔ 门禁状态:未过门。

⭐⭐ 本轮它必须改的那一件事:**好版本不再是「FAIL = 0」**。
   EXP-5c(**参数字典范围上的最坏**噪声底突破 PRD)是一条**如实为 FAIL 的检查**
   (预先写死在 PREREG_D34_r16_addendum §3:⛔ 不退役、⛔ 不改判据)。
⇒ 于是「杀死 = 出现了 FAIL」这个旧判据**失效**:它会把基线里那条 FAIL
  算成每一个变异的战功 ⇒ **6 条假杀伤**。
⇒ 新判据:**杀死 = FAIL 集合【超出基线】**。基线本身必须逐条具名登记。

用法: python3 run_killmatrix_r16.py > results_d34_r16_killmatrix.txt
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

MUTANTS = ["polarity", "qcoef", "freeq", "hpf_order", "xo_order", "qcoef_and_freeq"]


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
print("results_d34_r16_killmatrix —— 杀伤矩阵(基线感知版)")
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
    if not killed:
        rc = 1
    note = f"  ⛔ 变异未被杀死(存活)" if not killed else ""
    if lost:
        note += f"  ⛔ 基线中的 {lost} 在本变异下反而 PASS ⇒ 变异改动了它不该改的东西"
        rc = 1
    print(f"{m:<18s} {' '.join(killed) if killed else '(无)':<46s} {t}{note}")

print("-" * 88)
print("\n⚠ 未知变异名闸门(critic BLOCKER-2 修法④,r16 补做):")
p = subprocess.run([sys.executable, SCRIPT, "--broken=__nonexistent__"],
                   capture_output=True, text=True, timeout=1800)
ok_guard = (p.returncode == 2)
print(f"  [{'PASS' if ok_guard else 'FAIL'}] --broken=__nonexistent__ 退出码 = {p.returncode}(须 = 2)")
if not ok_guard:
    rc = 1

print("=" * 88)
print(f"退出码 = {rc}")
sys.exit(rc)
