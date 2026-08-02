"""r33:F(z) 真实性**第 6 条(极值侧)** + KS 归一化诊断(③,并行不挡路)。

⭐ 第 6 条(Rényi 表示):对 Exp(1) 序统计量,顶部归一化间距 **i·D_i ~ Exp(1),与 N 无关**
   D_i = X(i) − X(i+1)(降序),i = 1..20
   ⚠ **必须跨种子池化** —— 单条 F(z) 只有 ~20 个间距,功效近零。
     **池化才是「≥5 种子」的真正理由**(不是"平均噪声")。
   ⚠ 本条**对 N_crit 的定义之争完全免疫**(N 只通过 X(1)≈ln N 进入)。
   ⭐ 且它是**唯一直接影响 ΔMSG 的分布特征** —— ΔMSG 就是顶部间距。

③ 诊断:矩全对而 KS 独超 ⇒ 最简单的解释是**归一化常数错**(三个矩都是尺度不变量,看不见它)。
   ⇒ 用同一批样本**估出速率**再跑 KS(只检形状不检尺度);
     参数被估计 ⇒ 临界值须 **MC(Lilliefors)**,不得查表。
[L2/宿主仿真]
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
from scipy.stats import kstest
import clrig
# ⚠ h_eff 之辨:本文件测的是 **RIR 自身的统计性质**(像不像真实房间)
#   ⇒ **刻意用 h,不用 h_eff** —— 块延迟是台架的,不是房间的。
#   (r43 已实证:改用 h_eff 后 σ_dB/i·D_i/ratio 几乎不动 ⇒ 结论不受影响)

SEEDS = list(range(8))
TOPI = 20


def crit_power(h):
    _, mdb = clrig.critical_points(h)
    P = 10 ** (mdb / 10.0)
    return P / P.mean()


print("r33 · F(z) 第 6 条(极值侧)+ KS 归一化诊断")
print("[L2/宿主仿真]  ⚠ 工作点向量**已增列 seed**(共用种子会把两个独立点变成一个)\n")

for T60 in [0.2, 0.5]:
    pooled = []
    for sd in SEEDS:
        h, D = clrig.make_F(T60=T60, delay_ms=8.0, seed=sd)
        P = np.sort(crit_power(h))[::-1]
        if len(P) < TOPI + 1:
            continue
        for i in range(1, TOPI + 1):
            pooled.append(i * (P[i - 1] - P[i]))
    pooled = np.array(pooled)
    Dks = kstest(pooled, 'expon').statistic
    print(f"【第6条 极值侧】T60={T60}  池化 {len(SEEDS)} 种子 × 顶部 {TOPI} 间距 = **N={len(pooled)}**")
    print(f"   i·D_i:均值={pooled.mean():.3f}(理论 1)  标准差={pooled.std():.3f}(理论 1)  "
          f"**KS D={Dks:.4f}**")
    print(f"   ⇒ 门:D ≤ 1.36/√N = {1.36/np.sqrt(len(pooled)):.4f}  ⇒ "
          + ("**通过 ✓**" if Dks <= 1.36 / np.sqrt(len(pooled)) else "**不通过**"))
    sys.stdout.flush()

print()
for T60 in [0.2, 0.5]:
    h, D = clrig.make_F(T60=T60, delay_ms=8.0, seed=0)
    P = crit_power(h)
    D_fixed = kstest(P, 'expon').statistic                    # 固定尺度(原做法)
    lam = 1.0 / P.mean()                                      # 由同一批样本估速率
    D_est = kstest(P, lambda x: 1 - np.exp(-lam * x)).statistic
    # Lilliefors MC 临界值(参数被估计 ⇒ 不得查表)
    rng = np.random.default_rng(1)
    null = []
    for _ in range(400):
        y = rng.exponential(1.0, len(P))
        ly = 1.0 / y.mean()
        null.append(kstest(y, lambda x: 1 - np.exp(-ly * x)).statistic)
    crit = float(np.percentile(null, 95))
    print(f"【③诊断】T60={T60}  N={len(P)}")
    print(f"   固定尺度 KS D={D_fixed:.4f}(原做法) | **估尺度后 KS D={D_est:.4f}**  "
          f"Lilliefors 临界值(MC,95%)={crit:.4f}")
    print(f"   ⇒ {'**降到临界值内 ⇒ 归一化常数错,修它**' if D_est <= crit else '**仍超 ⇒ 不是归一化问题,才轮到相关性**'}")
    print(f"   参考:估出的尺度 = {1/lam:.3f}(若≠1 即归一化偏差;4/π={4/np.pi:.3f})")
    sys.stdout.flush()
