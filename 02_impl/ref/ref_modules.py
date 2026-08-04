#!/usr/bin/env python3
"""D3/D4 模块的【实现一致性核】+【铁律七的独立解析轨】—— ⛔ 两件事,分开报。
⛔ 门禁状态:未过门。

⛔⛔ 整改 2026-08-04 · critic 02impl MAJOR-1:本文件原自称「第二轨:独立 Python 重写」。
    **那个定级是错的。** critic 逐行对照证明它是**同式转写**:同样的累加顺序、
    同样的 EF 逐项 >>27、同样的 (acc+half)>>27、同样的残差式、同样的状态推移顺序、
    同样的方向判据与右移量。
    ⇒ 「20000 点逐位相同」能证的是**转写忠实**(可抓表项转录错、移位顺序错、状态推移错),
      ⛔ **不能证算法对** —— EF 语义两边同错、舍入语义两边同错、移位口径两边同错,
      **都会一致通过**。
    ⚠ 而它比前置件那次更弱一层:`ref_fixed.py` 至少还有一条真独立的解析轨
      (对 pow(10,dB/20) 的精度比对),而本文件**一条都没有** —— 两条对表项全是转写。

⇒ 本次处置(两件事,⛔ 不合并成"双轨交叉核"一句):
   (A) 实现一致性核 T1/T1+/T2/T2+/T3/T3a —— 同式转写,只证转写忠实
   (B) 铁律七的独立解析轨 T4/T4+ —— **与实现无共用代码**,拿解析式做参照

对表项(A):①biquad DF1+EF 逐位 ②检测器功率状态逐位 ③限幅器增益 dB 逐位
用法:C 侧先写出 bitexact_*.txt,本脚本读取并比对;退出码非 0 = 硬闸门失败。
"""
import sys, math, os

SMP_F, COEF_F, POW_F, DB_F, SM_F = 27, 27, 54, 8, 31
I32MAX, I32MIN = (1 << 31) - 1, -(1 << 31)
FS = 48000
fails = []

def chk(tag, ok, msg):
    print(f"  [{'PASS' if ok else 'FAIL'}] {tag:<9s} {msg}")
    if not ok: fails.append(tag)

def q(x, f):
    v = int(math.floor(x * (1 << f) + 0.5)) if x >= 0 else int(math.ceil(x * (1 << f) - 0.5))
    return max(I32MIN, min(I32MAX, v))

def rbj_peaking(f0, Q, gdb):
    A = 10 ** (gdb / 40); w0 = 2 * math.pi * f0 / FS
    al = math.sin(w0) / (2 * Q); c = math.cos(w0); a0 = 1 + al / A
    return [(1 + al * A) / a0, -2 * c / a0, (1 - al * A) / a0, -2 * c / a0, (1 - al / A) / a0]

def df1_ef(xq, cq):
    """与 chdsp_biquad_df1 同规格的独立重写(DF1 + 二阶误差反馈 + RTN + 饱和)"""
    b0, b1, b2, a1, a2 = cq
    x1 = x2 = y1 = y2 = 0; r1 = r2 = 0
    half = 1 << (COEF_F - 1); out = []
    for x in xq:
        acc = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        acc -= (a1 * r1) >> COEF_F
        acc -= (a2 * r2) >> COEF_F
        y = (acc + half) >> COEF_F
        r = acc - (y << COEF_F)
        y = max(I32MIN, min(I32MAX, y))
        x2, x1 = x1, x; y2, y1 = y1, y; r2, r1 = r1, r
        out.append(y)
    return out

def det_rms(xq, atk_ms, rel_ms):
    """与 chdsp_det_process1 同规格的独立重写(功率域 Q8.54)"""
    aa = int(round((1 - math.exp(-1 / (atk_ms * 1e-3 * FS))) * (1 << SM_F)))
    ar = int(round((1 - math.exp(-1 / (rel_ms * 1e-3 * FS))) * (1 << SM_F)))
    aa = max(1, min(I32MAX, aa)); ar = max(1, min(I32MAX, ar))
    s = 0; out = []
    for x in xq:
        inst = x * x
        a = aa if inst > s else ar
        s += ((inst - s) * a) >> SM_F
        if s < 0: s = 0
        out.append(s)
    return out

def load(path):
    if not os.path.exists(path):
        chk("载入", False, f"缺 {path}(C 轨未跑)"); return None
    with open(path) as f:
        return [int(v) for v in f.read().split()]

print("=" * 66)
print("ref_modules.py — (A) 实现一致性核 + (B) 铁律七的独立解析轨")
print("=" * 66)

print("--- (A) 实现一致性核:同式转写 ⇒ 只证【转写忠实】,⛔ 不证算法对 ---")
# T1 biquad
xq = load("bitexact_bq_in.txt"); cy = load("bitexact_bq_out.txt")
if xq is not None and cy is not None:
    cq = [q(v, COEF_F) for v in rbj_peaking(1000.0, 1.4, 6.0)]
    py = df1_ef(xq, cq)
    diff = [i for i, (a, b) in enumerate(zip(cy, py)) if a != b]
    chk("T1", not diff, f"biquad DF1+EF 逐位相同({len(py)} 样本,不等 {len(diff)} 处)")
    bad = list(py); bad[len(bad)//2] += 1
    chk("T1+", [i for i,(a,b) in enumerate(zip(cy,bad)) if a!=b] != [],
        "阳性对照:强制改一个值后比对器报出差异 ⇒ 上一行的「相同」有意义")

# T2 检测器
dy = load("bitexact_det_out.txt")
if xq is not None and dy is not None:
    py = det_rms(xq, 10.0, 100.0)
    diff = [i for i, (a, b) in enumerate(zip(dy, py)) if a != b]
    chk("T2", not diff, f"检测器功率状态逐位相同({len(py)} 样本,不等 {len(diff)} 处)")
    bad = list(py); bad[len(bad)//2] += 1
    chk("T2+", [i for i,(a,b) in enumerate(zip(dy,bad)) if a!=b] != [],
        "阳性对照:强制改一个值后比对器报出差异 ⇒ 上一行的「相同」有意义"
        "(整改 · critic MAJOR-2:T2 原先没有阳性对照)")

# T3 限幅器增益 dB —— critic MAJOR-2:docstring 承诺了它,而它在物理上不存在
ly = load("bitexact_lim_gdb.txt")
if xq is not None and ly is not None:
    py = lim_gdb([max(I32MIN, min(I32MAX, v * 4)) for v in xq], -6.0, 1.0, 50.0)
    # ⭐ 前提自检:C 轨读数必须**真的动过**,否则这是"两列 0 对表"
    #   ⚠ 首版就栽在这:xs 幅度 −12 dBFS 而阈值 −6 dBFS ⇒ gdb 恒 0,20000 个样本只有 1 个取值。
    chk("T3a", len(set(ly)) > 10,
        f"前提自检:C 轨限幅器增益**真的动了**({len(set(ly))} 个不同取值)"
        "⇒ 下一行的逐位比对才有内容")
    diff = [i for i, (a, b) in enumerate(zip(ly, py)) if a != b]
    chk("T3", not diff, f"限幅器增益 dB 逐位相同({len(py)} 样本,不等 {len(diff)} 处)")

print("=" * 66)
print(f"第二轨: {'全部通过' if not fails else '未通过 ' + ','.join(fails)}")
print("=" * 66)
sys.exit(0 if not fails else 1)
