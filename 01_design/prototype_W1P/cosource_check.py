"""共源核查(常驻,**无条件执行**,不挂任何数值条件)。
⭐ 立法理由(架构侧自废 D 侧后):
   原 D 侧是**数值触发器**(|mean(d)| < 0.354 ⇒ 可疑),被一个与被测量毫无关系的
   实现细节(缩窗把网格锚在解析值上)**悄悄废掉** ⇒ 触发器恒响 = 恒不报警。
   ⇒ **凡"异常检测"型判据,优先用【结构检查】而非【数值阈值】** ——
     结构检查不会被口径变化关掉,也不需要重新标定。
   ⇒ 与"披着谨慎外衣的错误"互补:那一条是判据永远输出"无结论",
     这一条是判据永远输出"告警" —— **两头都是失去信息。**

核查内容:预测路径 与 实测路径 的函数调用交集。
"""
import ast, sys, os
BASE = os.path.dirname(os.path.abspath(__file__))

def calls_in(fn, func_names):
    """返回文件中出现的 clrig/nhs 函数调用名集合。"""
    src = open(os.path.join(BASE, fn), encoding='utf-8').read()
    tree = ast.parse(src)
    out = set()
    for nd in ast.walk(tree):
        if isinstance(nd, ast.Call):
            f = nd.func
            nm = None
            if isinstance(f, ast.Attribute):
                nm = f.attr
            elif isinstance(f, ast.Name):
                nm = f.id
            if nm in func_names:
                out.add(nm)
    return out

PRED = {'predict_dmsg', 'predict_dmsg_iter', 'analytic_msg_db', 'critical_points',
        '_crit_from_H', 'n_crit', 'F_response', 'h_eff'}
MEAS = {'msg', 'howls', 'is_howling', 'run', 'Loop', 'rms_db'}

def report(fn):
    p = calls_in(fn, PRED); m = calls_in(fn, MEAS)
    inter = p & m
    print(f"  {fn}")
    print(f"     预测路径调用: {sorted(p) if p else '无'}")
    print(f"     实测路径调用: {sorted(m) if m else '无'}")
    print(f"     **函数级交集: {sorted(inter) if inter else '空 ✓'}**")
    # 关键断言:MSG_off 必须扫出来,不得取自解析
    src = open(os.path.join(BASE, fn), encoding='utf-8').read()
    bad = []
    for ln in src.splitlines():
        s = ln.strip()
        if s.startswith('#'):
            continue
        if ('m0' in s or 'MSG_off' in s or 'msg_off' in s) and 'analytic_msg_db' in s:
            bad.append(s)
    ok = not bad
    print(f"     ★ MSG_off 必须**扫出来**(不得取自解析式): "
          + ("**通过 ✓**" if ok else f"**违规 ⇒ {bad}**"))
    return (not inter) and ok

if __name__ == '__main__':
    print("共源核查(常驻,无条件执行)\n")
    allok = True
    for fn in ['r45_flat.py', 'r38_paired.py']:
        if os.path.exists(os.path.join(BASE, fn)):
            allok &= report(fn)
    print(f"\n⇒ 总判定:{'**共源核查通过**' if allok else '**存在共源 ⇒ 假吻合风险 ⇒ 结果不得判 A 侧**'}")
    sys.exit(0 if allok else 1)
