"""`marks` · **不适用 ≠ 一个数** —— 四记号互斥取值域 + 聚合护栏 + 闸门自证。
⛔ 未经 critic 评审。起因 = critic `W1P_CLOSEOUT_r12` MAJOR-2(实测已出错两处)。

⭐⭐ 为什么必须是**结构**而不是**标注**(critic 给的理由,我复核成立):
    `nan` 是一个**数**,而它的全部比较都返回 False:
        nan < x ⇒ False   ·   nan > x ⇒ False   ·   nan == nan ⇒ False
    ⇒ 任何判据碰到它,**两侧分支都不成立** ⇒ 不报 PASS 也不报 FAIL ⇒ **它蒸发**
    ⇒ ⇒ ∴ 用 nan 表示"不适用",**在构造上保证了每一个碰到它的闸门都会静音**
    ⇒ 这不是"忘了写明",是【选了一个会让闸门蒸发的值】。

⭐ 而它与「诬告对的」是同一枚硬币的两面:
    那条 = **正常项长得像故障** ⇒ 有人去修没坏的东西
    本条 = **不适用项长得像数据** ⇒ 没人去修,因为它看起来已经有值了

四记号(互斥,⛔ nan 不得作为其中任何一个的载体):
    Value(x)      —— 一个真实测得的数
    UNCONVERGED   —— 测了,而未收敛(**有实义**:r91 的 0.5/2 就是这一类)
    NOT_APPLICABLE—— **本轮未跑** ⇒ 连一次测量都没发生
    GATE_NOT_RUN  —— 闸门的**输入不可得** ⇒ 闸门未执行
"""
import math


class Mark:
    """互斥记号基类。⛔ 不是数 ⇒ 任何算术/比较都会显式抛错,而不是静默返回 False。"""
    __slots__ = ('why',)
    KIND = '?'

    def __init__(self, why=''):
        self.why = why

    def __repr__(self):
        return f"{self.KIND}" + (f"({self.why})" if self.why else "")

    # ⭐ 关键:⛔ 不让它伪装成数 —— 碰它的代码必须显式处理,否则当场炸
    def __lt__(self, o): raise TypeError(f"⛔ 记号 {self!r} 不可比较 —— 它不是一个数")
    __gt__ = __le__ = __ge__ = __lt__
    def __add__(self, o): raise TypeError(f"⛔ 记号 {self!r} 不可参与算术")
    __radd__ = __sub__ = __mul__ = __truediv__ = __abs__ = __add__
    def __float__(self): raise TypeError(f"⛔ 记号 {self!r} 不可转 float(⛔ 尤其不得转 nan)")


class Unconverged(Mark):
    KIND = '未收敛'


class NotApplicable(Mark):
    KIND = '不适用(本轮未跑)'


class GateNotRun(Mark):
    KIND = '闸门未执行'


UNCONVERGED, NOT_APPLICABLE, GATE_NOT_RUN = Unconverged, NotApplicable, GateNotRun


class AggregateBlocked(Exception):
    """聚合护栏触发 ⇒ **中止并报 FAIL**,⛔ 不得跳过、不得静默返回。"""


def _guard(vals, op):
    """聚合护栏(修法②):遇 `不适用` / `闸门未执行` ⇒ **中止并报 FAIL**。
    ⚠ 而 `未收敛` 同样拦 —— `PREREG_r91 §2-②` 已为它立过这条规矩(该档 max 整体不可用)。
    ⭐ 而"不适用"**比"未收敛"更该拦** —— 它连一次测量都没发生过。"""
    bad = [v for v in vals if isinstance(v, Mark)]
    if bad:
        kinds = sorted({b.KIND for b in bad})
        raise AggregateBlocked(
            f"⛔⛔ **{op} 被聚合护栏中止 ⇒ FAIL**:输入含 {len(bad)} 个非数值记号 {kinds}。"
            f"⇒ ⛔ 不得跳过它们求 {op};⇒ 正确产出是「该档 {op} 不可报」。")
    if any((isinstance(v, float) and math.isnan(v)) for v in vals):
        raise AggregateBlocked(
            f"⛔⛔ **{op} 遇到 nan ⇒ FAIL**。⇒ nan 会让闸门蒸发(见模块头)"
            f"⇒ 请改用四记号之一,⛔ 不得用 nan 表示『不适用』。")
    return [float(v) for v in vals]


def safe_max(vals):
    return max(_guard(vals, 'max'))


def safe_median(vals):
    v = sorted(_guard(vals, '中位'))
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def gate(name, inputs, predicate, why_unavailable='输入不适用'):
    """闸门自证(修法③):输入不可得 ⇒ **显式打印「⛔ 闸门未执行」**,⛔ 不许只印一个值。
    返回 (状态串, 是否放行)。⇒ 三态:PASS / FAIL / **闸门未执行**(⛔ 后者不得当 PASS)。"""
    if any(isinstance(x, Mark) or (isinstance(x, float) and math.isnan(x)) for x in inputs):
        return (f"⛔ **闸门未执行**({why_unavailable}) —— ⛔ 既非 PASS 亦非 FAIL,"
                f"⛔ 不得当作通过", False)
    return (("✅ PASS" if predicate(*inputs) else "⛔ **FAIL**"), bool(predicate(*inputs)))


def selftest():
    """⭐ 护栏必须能失败 —— 本函数是它的阳性对照(假绿纪律)。"""
    out = []
    ok = 0
    # ① 正常路径必须照常算
    try:
        assert safe_max([1.0, 3.0, 2.0]) == 3.0 and safe_median([1., 2., 3.]) == 2.0
        out.append("  ✅ ① 正常输入:max/中位 照常返回"); ok += 1
    except Exception as e:
        out.append(f"  ⛔ ① 正常输入却失败:{e}")
    # ② 三种记号都必须【中止】
    for mk in (UNCONVERGED('0.5/2'), NOT_APPLICABLE('本轮未跑 Na'), GATE_NOT_RUN()):
        try:
            safe_max([1.0, mk, 2.0]); out.append(f"  ⛔ ② {mk!r} **没被拦住** ⇒ 护栏失效")
        except AggregateBlocked:
            out.append(f"  ✅ ② {mk!r} 被中止并报 FAIL"); ok += 1
    # ③ nan 必须被拦(它正是那个会让闸门蒸发的值)
    try:
        safe_max([1.0, float('nan')]); out.append("  ⛔ ③ nan **没被拦住**")
    except AggregateBlocked:
        out.append("  ✅ ③ nan 被中止并报 FAIL"); ok += 1
    # ④ 记号不得伪装成数
    try:
        _ = UNCONVERGED() < 1.0; out.append("  ⛔ ④ 记号可比较 ⇒ 它在伪装成数")
    except TypeError:
        out.append("  ✅ ④ 记号不可比较(⛔ 不伪装成数)"); ok += 1
    # ⑤ 闸门自证三态
    s1, p1 = gate('复现', [3.0, 3.0], lambda a, b: a == b)
    s2, p2 = gate('复现', [3.0, 4.0], lambda a, b: a == b)
    s3, p3 = gate('复现', [NOT_APPLICABLE('本轮未跑'), 3.0], lambda a, b: a == b)
    if s1.startswith('✅') and s2.startswith('⛔ **FAIL') and '闸门未执行' in s3 and not p3:
        out.append("  ✅ ⑤ 闸门三态:PASS / FAIL / **闸门未执行**(后者不放行)"); ok += 1
    else:
        out.append(f"  ⛔ ⑤ 闸门三态异常:{s1} | {s2} | {s3}")
    return ok, len(out), out


if __name__ == '__main__':
    ok, n, lines = selftest()
    print("marks.py 自测(⭐ 护栏必须能失败 —— 这是它的阳性对照)")
    print("\n".join(lines))
    print(f"⇒ {ok}/{n} 通过 ⇒ {'✅ 护栏有效且可失败' if ok == n else '⛔ 护栏本身有问题'}")
