#!/usr/bin/env bash
# check_baseline_mech —— 【基线机制会不会响】的阴性/阳性对照。⛔ 门禁状态:未过门。
#
# ⭐ 自查(lead 指示):「这个检查失败时,会阻止什么?」
#    答:**任一对照不成立 ⇒ 本脚本 exit 1 ⇒ 阻止 run_all.sh 通过、阻止交付。**
#
# ══════════════════════════════════════════════════════════════════════════════
# ⭐⭐ 它为什么必须存在 —— 而这一条比机制本身更要紧
# ══════════════════════════════════════════════════════════════════════════════
# C 侧**今天没有常驻 FAIL** ⇒ `test/BASELINE_FAILS.txt` 是空的
#   ⇒ `run_kill_matrix.sh` 里那套基线逻辑在今天是一个**恒等式**:空集 == 空集。
# ⇒ ⛔ 而一个**从未被证明会响**的机制,与没有机制的区别只在于**它让人放心**。
#   (本项目已实证过同型:14 条检查看起来很全,而其中大半不依赖被测物。)
# ⇒ ∴ 本脚本在**临时副本**上人为造出一条常驻 FAIL,逐条验四种走法。
#   ⛔ 全程不碰真实工作树(mkwork 复制;真实树的 BASELINE_FAILS.txt 一字不动)。
#
# ⭐ 而最要紧的那一条是 P-1:它证明【超出基线】这个判据确实**没有**把那条常驻 FAIL
#   记成每个变异的战功 —— 那正是设计侧 critic 判过的 BLOCKER-2「把功记在错的缺陷上」。
# ══════════════════════════════════════════════════════════════════════════════
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
BASE="$(cd "$ROOT/.." && pwd)"
FIXED="$BASE/01_design/fixedpoint"
TMPROOT="$(mktemp -d -t chdsp_basemech.XXXXXX)"
trap 'rm -rf "$TMPROOT"' EXIT

pass=0; fail=0
ok(){ echo "  [PASS] $1  $2"; pass=$((pass+1)); }
no(){ echo "  [FAIL] $1  $2"; fail=$((fail+1)); }

# 造一份独立副本(⛔ 不动真实树)
mkwork(){ local w="$1"; rm -rf "$w"; mkdir -p "$w/01_design"
  cp -r "$ROOT" "$w/02_impl"; cp -r "$FIXED" "$w/01_design/fixedpoint"
  rm -rf "$w/02_impl/build" "$w/02_impl/build_kill"; }

# 人为造一条**常驻 FAIL**:把 CHK-B3(LR 极性规则)的断言改成必假。
# ⛔ 它只作用在副本上,且**不是**一个 CHDSP_BROKEN_* 变异 —— 变异是编译期开关,
#   而我们要的是"好版本自己就带一条 FAIL",那正是常驻 FAIL 的形态。
inject_standing_fail(){ local w="$1"
  sed -i 's/OKC("CHK-B3", p2 == 1 \&\& p4 == 0/OKC("CHK-B3", p2 == 0 \&\& p4 == 0/' \
      "$w/02_impl/test/check_modules.c"
  grep -q 'OKC("CHK-B3", p2 == 0' "$w/02_impl/test/check_modules.c"; }

setreg(){ printf '# 测试用登记(仅副本)\n%s\n' "$2" > "$1/02_impl/test/BASELINE_FAILS.txt"; }
runkm(){ ( cd "$1/02_impl" && timeout 900 bash test/run_kill_matrix.sh ) > "$2" 2>&1; echo $?; }

echo "================================================================"
echo "check_baseline_mech —— 基线机制的阴性/阳性对照(硬闸门)"
echo "  ⛔ 判据 = 【退出码】∧【命中该走法自己的失败特征】,两者缺一不可"
echo "     (退出码 1/2 各有多个来源;只看码会让 A 的红把 B 染绿)"
echo "================================================================"

# ── P-0 前提自检:注入确实造出了一条常驻 FAIL ────────────────────────────────
W="$TMPROOT/p0"; mkwork "$W"
if inject_standing_fail "$W"; then ok "P-0a" "注入成功:CHK-B3 断言已改为必假(副本内)"
else no "P-0a" "⛔ 注入失败 ⇒ 下面所有对照都无意义"; fi
setreg "$W" "CHK-B3 | 测试 | 人造常驻 FAIL"
OUT="$TMPROOT/p0.txt"; RC=$(runkm "$W" "$OUT")
if grep -q '阴性对照(无变异):FAIL 集合逐条等于登记' "$OUT"; then
  ok "P-0b" "好版本的 FAIL 集合 = {CHK-B3} = 登记 ⇒ 基线机制认得它"
else no "P-0b" "⛔ 好版本未如预期带上那条常驻 FAIL(见 $OUT)"; fi

# ── ⭐ P-1 关键阳性对照:常驻 FAIL【没有】被记成每个变异的战功 ────────────────
n_mut=$(grep -cE '^\s*\[已杀死\]' "$OUT" || true)
n_b3=$(grep -E '^\s*\[已杀死\]' "$OUT" | grep -c 'CHK-B3' || true)
echo "     (副本内:已杀死 $n_mut 条;其中把 CHK-B3 记为杀手的 $n_b3 条)"
if [ "$n_mut" -gt 0 ] && [ "$n_b3" -eq 0 ]; then
  ok "P-1" "⭐ 常驻 FAIL 【一次都没有】被记成变异的战功 ⇒ 「超出基线」判据确实在起作用"
else
  no "P-1" "⛔ 常驻 FAIL 被记成了 $n_b3 条变异的杀手 ⇒ 正是 BLOCKER-2「把功记在错的缺陷上」"
fi
if [ "$RC" = "0" ]; then ok "P-2" "带一条【已登记】的常驻 FAIL 时,矩阵仍能正常判定(rc=0)"
else no "P-2" "⛔ 带已登记的常驻 FAIL 时矩阵 rc=$RC(须 0)—— 见 $OUT"; fi

# ── N-1 未登记的常驻 FAIL ⇒ 退出码 1 ∧ 命中它自己的特征 ─────────────────────
W="$TMPROOT/n1"; mkwork "$W"; inject_standing_fail "$W" >/dev/null
setreg "$W" "# (故意留空:未登记)"
OUT="$TMPROOT/n1.txt"; RC=$(runkm "$W" "$OUT")
if [ "$RC" = "1" ] && grep -q '未登记.*常驻 FAIL' "$OUT"; then
  ok "N-1" "未登记的常驻 FAIL ⇒ rc=1 ∧ 命中「未登记的常驻 FAIL」"
else no "N-1" "⛔ rc=$RC,或未命中该走法的特征(见 $OUT)"; fi

# ── N-2 登记了、而它 PASS(基线漂移)⇒ 退出码 1 ∧ 自己的特征 ────────────────
W="$TMPROOT/n2"; mkwork "$W"      # ⛔ 不注入 ⇒ CHK-B3 是 PASS 的
setreg "$W" "CHK-B3 | 测试 | 登记为 FAIL 而实际 PASS"
OUT="$TMPROOT/n2.txt"; RC=$(runkm "$W" "$OUT")
if [ "$RC" = "1" ] && grep -q '登记为 FAIL 而实测 PASS' "$OUT"; then
  ok "N-2" "登记为 FAIL 而实测 PASS ⇒ rc=1 ∧ 命中「基线漂移」"
else no "N-2" "⛔ rc=$RC,或未命中该走法的特征(见 $OUT)"; fi

# ── N-3 登记项【不在判定集合里】(被删/改名)⇒ 退出码 2 ────────────────────
W="$TMPROOT/n3"; mkwork "$W"
setreg "$W" "CHK-NOSUCHTAG | 测试 | 登记一个不存在的标识"
OUT="$TMPROOT/n3.txt"; RC=$(runkm "$W" "$OUT")
if [ "$RC" = "2" ] && grep -q '不在本次判定项里' "$OUT"; then
  ok "N-3" "登记项被删/改名 ⇒ **rc=2** ∧ 命中「不在本次判定项里」"
else no "N-3" "⛔ rc=$RC(须 2),或未命中该走法的特征(见 $OUT)"; fi

# ── N-4 登记件缺失 ⇒ 退出码 2,⛔ 不得回退到默认集合 ───────────────────────
W="$TMPROOT/n4"; mkwork "$W"; rm -f "$W/02_impl/test/BASELINE_FAILS.txt"
OUT="$TMPROOT/n4.txt"; RC=$(runkm "$W" "$OUT")
if [ "$RC" = "2" ] && grep -q '找不到基线登记件' "$OUT"; then
  ok "N-4" "登记件缺失 ⇒ **rc=2** ∧ 拒绝回退到默认集合"
else no "N-4" "⛔ rc=$RC(须 2),或未命中该走法的特征(见 $OUT)"; fi

# ── N-5 三种走法的退出码【可区分】(⛔ 不得靠码本身归因)────────────────────
if grep -q '不在本次判定项里' "$TMPROOT/n3.txt" && grep -q '找不到基线登记件' "$TMPROOT/n4.txt" \
   && ! grep -q '找不到基线登记件' "$TMPROOT/n3.txt"; then
  ok "N-5" "⭐ 同为 rc=2 的两条走法各自带【不同的失败特征串】⇒ 可归因,⛔ 不必靠码猜"
else no "N-5" "⛔ 两条 rc=2 的走法无法区分 ⇒ 一条的红会把另一条染绿"; fi

echo
echo "  合计: PASS=$pass  FAIL=$fail"
if [ $fail -eq 0 ]; then
  echo "  ⇒ 基线机制在【有常驻 FAIL】时确实会响,且四种走法各自可归因 ⇒ PASS"
  echo "  ⚠ 而真实树的登记当前为**空** ⇒ 机制此刻是恒等式;本脚本证的是"
  echo "     【它一旦有登记项就会按预期工作】,⛔ 不是"它现在正在拦什么"。"
  exit 0
else
  echo "  ⛔ 基线机制有走法不会响 ⇒ FAIL(⛔ 此时别拿"C 侧已有基线机制"当依据)"
  exit 1
fi
