"""ΔMSG 的**双列报数接口** —— 纪律做成接口约束,不做成"这次我记得"。

═══════════════════════════════════════════════════════════════════════════
为什么有这个文件(lead 裁定,2026-08-03,critic verdict BLOCKER B-1 之后)
═══════════════════════════════════════════════════════════════════════════
**B-1 的成因不是"我们不知道选点来自神谕",而是"上一轮那个构造是对的,复制过来时限定没跟着走"**
(F39 / D6-o:**代码会复制,限定不会**)。

⇒ 因此修法不能是"下次记得写清楚",必须让**单列在类型上不可表达**:
> **凡报任何 NHS 相关的 ΔMSG,一律双列(神谕选点 / NHS 自选),不提供单列接口。**

与 `msg_meter.MSGMeter.msg()` 恒返回「带内/全带」两列**完全同源** ——
那一条挡住的是"频带口径"被静默丢掉,这一条挡住的是"选点来源"被静默丢掉。
两次都是同一个失效形态:**一个数有两个必需限定,而接口允许只说一个。**

═══════════════════════════════════════════════════════════════════════════
三个臂的定义(**不得混用,不得只报一个**)
═══════════════════════════════════════════════════════════════════════════
  ORACLE   选点 = 解析临界点(`clrig.critical_points`),槽钉死 HOLD,`T_low=999`
           ⇒ NHS 的【上界】。**禁止称"NHS 实测"、禁止用于达标判定。**
  NHS_SELF `NHS()` 默认参数(`T_low=-45`)、槽全空、检测/分类/分配全开
           ⇒ **这才是 NHS 的性能。** 名字里出现 "NHS" 的结论,必须由这一列支撑。
  FLAT     等代价平坦衰减(不含任何陷波)⇒ **baseline = 最笨的那个办法**(D6-n)。
           **⚠ baseline 不是"不做"。**

[L2/宿主仿真]
"""


class MissingArm(Exception):
    """少给一个臂就抛 —— 这是本模块存在的唯一理由。"""


class DMSGReport:
    """ΔMSG 的双列(+baseline)报数体。**构造时缺任一必需臂即抛异常。**

    ⚠ 本类**不提供**返回单个 ΔMSG 的方法或属性 —— 那是 B-1 的形状。
      要拿数只能经 `rows()` / `format()`,它们恒输出全部臂。
    """

    REQUIRED = ('oracle', 'nhs_self')      # flat 为 baseline,单独校验

    def __init__(self, workpoint, oracle=None, nhs_self=None, flat=None,
                 nhs_self_note='', allow_missing_nhs=False):
        """workpoint: dict,**必须含 `选点来源` 与 `T_low` 两键**(B-1 漏掉的那一维)。
        allow_missing_nhs: **仅**允许在"本轮明确不宣称任何 NHS 性能"时置 True,
                           且此时 `format()` 会强制打出禁用横幅。"""
        # ⚠ 不得写成 `locals()[k]` —— 推导式在 py3 有独立作用域,取不到外层局部变量,
        #   会抛 KeyError 而**不是**抛 MissingArm ⇒ 守护者自己坏掉。
        #   (2026-08-03 首次自测即命中:"守护者同样需要被守护"当场兑现。)
        given = dict(oracle=oracle, nhs_self=nhs_self, flat=flat)
        miss = [k for k in self.REQUIRED if given[k] is None]
        if miss and not (allow_missing_nhs and miss == ['nhs_self']):
            raise MissingArm(
                f"缺臂 {miss} —— 双列是硬要求(B-1)。"
                f"若本轮确实不测 NHS 自选,须显式传 allow_missing_nhs=True,"
                f"届时输出会带『不得称 NHS 性能』横幅。")
        for k in ('选点来源', 'T_low'):
            if k not in workpoint:
                raise MissingArm(f"工作点向量缺 `{k}` —— 这正是 B-1 漏掉的那一维(D6/F39)。")
        self.wp = dict(workpoint)
        self.oracle = oracle
        self.nhs_self = nhs_self
        self.flat = flat
        self.note = nhs_self_note
        self.allow_missing_nhs = allow_missing_nhs

    def delta_win(self):
        """`Δ_win = ΔMSG_oracle − ΔMSG_flat`(>0 = 陷波在 MSG 轴上赢过等代价平坦衰减)。
        ⚠ 只覆盖 **MSG 轴**;SD(音质轴)未仪表化 ⇒ **不得据此宣称任何一方"更好"**。"""
        if self.oracle is None or self.flat is None:
            return None
        return self.oracle - self.flat

    def delta_win_self(self):
        """同上,但用 **NHS 自选** 那一列 —— 这才是产品意义上的胜负。"""
        if self.nhs_self is None or self.flat is None:
            return None
        return self.nhs_self - self.flat

    def rows(self):
        return dict(oracle=self.oracle, nhs_self=self.nhs_self, flat=self.flat,
                    delta_win_oracle=self.delta_win(),
                    delta_win_nhs=self.delta_win_self(), workpoint=self.wp)

    def format(self):
        o = '  n/a' if self.oracle is None else f'{self.oracle:5.2f}'
        n = '  n/a' if self.nhs_self is None else f'{self.nhs_self:5.2f}'
        f = '  n/a' if self.flat is None else f'{self.flat:5.2f}'
        dw = self.delta_win()
        dws = self.delta_win_self()
        s = (f"ORACLE(上界) {o} | NHS自选 {n} | FLAT(等代价baseline) {f} | "
             f"Δwin_oracle {'n/a' if dw is None else f'{dw:+5.2f}'} | "
             f"Δwin_nhs {'n/a' if dws is None else f'{dws:+5.2f}'}")
        if self.allow_missing_nhs and self.nhs_self is None:
            s += "\n    ⛔ 本行未测 NHS 自选 ⇒ **不得由本行推出任何『NHS 的性能』结论**"
        if self.note:
            s += f"\n    注:{self.note}"
        return s

    @staticmethod
    def flat_dmsg_from_cost(cost_db):
        """等代价平坦衰减臂的 ΔMSG —— **解析精确,无须仿真**。
        环路里串一个常数增益 `10^(cost/20)`(cost<0)⇒ 开环增益整体平移 |cost| dB
        ⇒ **MSG 恰好抬高 |cost| dB**,对所有频点一致、无近似。
        ⇒ 故 `ΔMSG_flat = |cost_db|`。(仍建议抽样闭环复核一次,证明台架无额外损失。)"""
        return abs(float(cost_db))
