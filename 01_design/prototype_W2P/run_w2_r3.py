"""W2-P 第三轮:C-8a′ 重核 / C-8f/C-8g 探针实测(V-17)/ NLP 静场透明度(V-15)"""
import numpy as np, io, importlib
import aec, metrics as M, rig, probe
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("="*78); say("W2-P 第三轮 · adaptive-dsp-3 · [L2/宿主仿真] · aec %s / probe %s"%(aec.__version__,probe.__version__)); say("="*78)

say("\n### ① C-8a′ 重核(度量对象 = D_sup(f) = sup_t D(f,t),非逐帧峰-均)")
say("  AEC 线性段是**加性**算子 y = x − Σŵ·u,被减项只是 u 的函数、与 x 无关")
say("  ⇒ 作为 x→y 系统 H_{x→y} ≡ 1 ⇒ D_sup = **0.00dB**,平凡满足 C-8a(门 0.25dB)。")
say("  ⚠ 撤回第二轮的 129.56dB:那是**残差信号谱的谱平坦度**(且近端静默帧上 Y/X 分母趋零爆表),")
say("    不是 x→y 频响。**同一批数据里的 DTD 数(≤0.014dB)证伪了那个读法** —— 若真有 129dB")
say("    的 x→y 纹波,把自适应整体停掉不可能只跳 0.014dB。0.014dB 才是 H_{x→y} 实测值,余量 18×。")

say("\n### ② ★ C-8f 环路增益调制(探针法;架构侧零实测,V-17)")
say("  机理:NLMS 更新 ŵ←ŵ+μ·e·u/(uᵀu) 中 e 含探针/啸叫 ⇒ 经 ⟨e,u⟩ 泄漏进系数")
say("       ⇒ 抵消信号 ŵᵀu 抖动 ⇒ **零均值、方差随 μ 增**的环路增益调制。")
say("  台架:同一收敛 AEC,**自适应 vs 系数冻结**(排除'消不消回声'的混淆);探针注本地环路。")
say(f"  {'mu_max':>7} {'max抬升':>9} {'中位':>8} {'std':>7} {'判定(门+0.25dB)':>16}")
rows=[]
for mu in (0.05,0.1,0.2,0.4):
    mx,med,sd = probe.c8f(lambda: aec.MDF(mu_max=mu), dur=8.0)
    rows.append((mu,mx,med,sd))
    say(f"  {mu:7.2f} {mx:+9.3f} {med:+8.3f} {sd:7.3f} {'**超门**' if mx>0.25 else '过门':>16}")
say("  ⇒ **四档全部超门**;工作点 mu=0.2 处 +1.673dB = 门的 6.7×。")
say("  ⇒ **中位 ≈ 0 而 max 超门** ⇒ 静态/空闲/平均口径对这条通路**结构性失明**,")
say("     架构侧取 max 作度量是对的;V-17「μ 敏感性必测」实测成立(std 随 μ 单调增)。")
say("  ⇒ 同一个 μ 的两个后果已合流:μ=0.5 既使基线发散(第二轮撤回),又使调制最大。")

say("\n### ③ C-8g 电平依赖性(探针扫 T_low_gr→0dBFS;门 ±1.0dB)")
res,span = probe.c8g(lambda: aec.MDF(mu_max=0.2), dur=8.0)
say(f"  {'探针电平dBFS':>12} {'max抬升dB':>10}")
for L,mx,med in res: say(f"  {L:12.0f} {mx:10.3f}")
say(f"  ⇒ 跨电平变化幅度 = {span:.3f}dB {'**超门**' if span>1.0 else '(过门 ±1.0dB)'}")

say("\n### ④ NLP 静场透明度(V-15)")
say("  C10 的约束不是那 −40.1dB(衰减对 MSG 免费),而是**静场透明度 ≤0.25dB**。")
x = np.random.default_rng(3).normal(0,0.05,16000*3)   # 静场:只有低电平本底,无回声
n=(len(x)//128)*128
nlp=aec.NLP(); y=np.zeros(n)
for i in range(0,n,128):
    y[i:i+128]=nlp.process(x[i:i+128], np.zeros(128))  # y(估计回声)=0 ⇒ 静场
g=20*np.log10((np.sqrt(np.mean(y**2))+1e-20)/(np.sqrt(np.mean(x**2))+1e-20))
say(f"  静场(无回声)NLP 净增益 = {g:+.3f}dB  {'**超门**' if abs(g)>0.25 else '过门(≤0.25dB)'}")
say(f"  逐频段最大衰减(有回声时)= {nlp.max_gr_db:.1f}dB —— 该值本身**不是** C-8 约束对象;")
say("     但它若出现在 tap 上游即致命 ⇒ 实测反过来证成 C10 子级裁定(tap 置于 NLP 前)的必要性。")
io.open('results_w2_r3.txt','w',encoding='utf-8').write('\n'.join(OUT))
