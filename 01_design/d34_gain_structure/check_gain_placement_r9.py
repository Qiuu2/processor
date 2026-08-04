#!/usr/bin/env python3
"""
r9:增益在链上的【位置】对量化噪声底的影响。
⛔ 门禁状态:未过门(未经独立 critic 评审)。

⚠ 本件放在新目录 `01_design/d34_gain_structure/`,因为 `d34_chain/` 当前处于 critic 评审锁。
  ⇒ 解锁后建议并入 d34_chain(⛔ 我不自行搬,须 lead 定)。

缘起(两条,都是 lead 转 critic)
① critic:噪声底那条在 D3/D4 比在前置件更严重,因为**我这一侧有增益模块**
   —— `comp_makeup` 量程 0…+20 dB。转述的数是链末 **−143.72**。
② critic MAJOR-2 的处置建议之一:「**把大增益放在链尾**」。

模型(初等解析,可手算复核):N 个量化器,增益 G 插在第 k 个之后
  ⇒ 上游 k 个的噪声**经过** G 被放大,下游 N−k 个不被
  ⇒ 链末噪声功率 = q²·[G²·k + (N−k)]

结论
· 转述的 −143.72 对应 **k = N**(增益在所有量化器之后)。
  **而 D3 实际链序是「压缩(含 makeup)在 PEQ×8 之【前】」⇒ k = 1 ⇒ 实为 −153.02。**
  两者差 9.21 dB,**完全由 makeup 的位置决定**。
· ⛔ **「把大增益放在链尾」在噪声轴上是反向的**:k 越大,被放大的上游量化器越多,
  k=N 比 k=0 差整整 G(本例 20 dB)。**正确方向是「大增益尽量靠前」。**
  ⚠ 但这只是噪声轴 —— 增益靠前会更早吃掉链内余量(饱和轴)。
    **两轴冲突,须一起权衡;⛔ 不能用一轴的理由替代另一轴。**
"""
import math
Q=-173.35   # 单节噪声底 [L2/宿主实测,任务一]
def floor_db(N, G_db, k):
    """N 个量化器,一个 G_db 的增益插在第 k 个之后 ⇒ 链末噪声 dBFS
       上游 k 个的噪声被放大 G;下游 N-k 个不被放大。"""
    g2 = 10**(G_db/10.0)
    return Q + 10*math.log10(g2*k + (N-k))

print("  D3 输入链 9 个量化器(HPF 1 + PEQ 8);comp_makeup = +20 dB")
print(f"    各节增益=1(文档模型)                       : {floor_db(9,0,0):8.2f} dBFS")
print(f"    ⭐ 我的实际链序(comp 在 PEQ【之前】⇒ k=1) : {floor_db(9,20,1):8.2f} dBFS   (只放大 HPF 那 1 个)")
print(f"    若 comp 在 PEQ【之后】(k=9)                : {floor_db(9,20,9):8.2f} dBFS   (= lead 转述的 −143.72 那一档)")
print()
print("  ⇒ 差别 = %.2f dB,**完全由 makeup 在链上的位置决定**" % (floor_db(9,20,9)-floor_db(9,20,1)))
print()
print("  ⭐⭐ 顺带核 critic 那条处置建议:「把大增益放在链尾」")
print(f"    {'增益位置 k':<28}{'链末噪声':>12}")
for k in (0,1,4,8,9):
    print(f"    {('k=%d'%k) + (' (最前)' if k==0 else ' (最尾)' if k==9 else ''):<28}{floor_db(9,20,k):>10.2f} dBFS")
print("  ⇒ 增益插得**越靠前**,被它放大的上游量化器**越少** ⇒ 噪声越低。")
print("  ⇒ ⛔ 「把大增益放在链尾」在噪声轴上是**反向**的:k=9 比 k=0 差 %.2f dB。" % (floor_db(9,20,9)-floor_db(9,20,0)))
print("     (它在**余量/饱和**轴上可能另有理由,但那是另一维,不能替代噪声轴。)")
print()
print("  对标(D3 链,+20 dB makeup,我的实际链序 k=1):")
v=floor_db(9,20,1)
print(f"    PRD ≤ −106 dBFS ⇒ 余量 {abs(v)-106:.2f} dB {'✓' if v< -106 else '⛔'}")
print(f"    设计目标 ≤ −120  ⇒ 余量 {abs(v)-120:.2f} dB {'✓' if v< -120 else '⛔'}")
import math
Q=-173.35   # 单节噪声底 [L2/宿主实测,任务一]
def floor_db(N, G_db, k):
    """N 个量化器,一个 G_db 的增益插在第 k 个之后 ⇒ 链末噪声 dBFS
       上游 k 个的噪声被放大 G;下游 N-k 个不被放大。"""
    g2 = 10**(G_db/10.0)
    return Q + 10*math.log10(g2*k + (N-k))

print("  D3 输入链 9 个量化器(HPF 1 + PEQ 8);comp_makeup = +20 dB")
print(f"    各节增益=1(文档模型)                       : {floor_db(9,0,0):8.2f} dBFS")
print(f"    ⭐ 我的实际链序(comp 在 PEQ【之前】⇒ k=1) : {floor_db(9,20,1):8.2f} dBFS   (只放大 HPF 那 1 个)")
print(f"    若 comp 在 PEQ【之后】(k=9)                : {floor_db(9,20,9):8.2f} dBFS   (= lead 转述的 −143.72 那一档)")
print()
print("  ⇒ 差别 = %.2f dB,**完全由 makeup 在链上的位置决定**" % (floor_db(9,20,9)-floor_db(9,20,1)))
print()
print("  ⭐⭐ 顺带核 critic 那条处置建议:「把大增益放在链尾」")
print(f"    {'增益位置 k':<28}{'链末噪声':>12}")
for k in (0,1,4,8,9):
    print(f"    {('k=%d'%k) + (' (最前)' if k==0 else ' (最尾)' if k==9 else ''):<28}{floor_db(9,20,k):>10.2f} dBFS")
print("  ⇒ 增益插得**越靠前**,被它放大的上游量化器**越少** ⇒ 噪声越低。")
print("  ⇒ ⛔ 「把大增益放在链尾」在噪声轴上是**反向**的:k=9 比 k=0 差 %.2f dB。" % (floor_db(9,20,9)-floor_db(9,20,0)))
print("     (它在**余量/饱和**轴上可能另有理由,但那是另一维,不能替代噪声轴。)")
print()
print("  对标(D3 链,+20 dB makeup,我的实际链序 k=1):")
v=floor_db(9,20,1)
print(f"    PRD ≤ −106 dBFS ⇒ 余量 {abs(v)-106:.2f} dB {'✓' if v< -106 else '⛔'}")
print(f"    设计目标 ≤ −120  ⇒ 余量 {abs(v)-120:.2f} dB {'✓' if v< -120 else '⛔'}")
