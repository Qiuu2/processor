"""补测④(我自加):方差支的实际后果 —— 异方差是否真把 IMSD 拒掉?若是,稳健拟合能否救?"""
import numpy as np, io
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("\n### 补测④(自加)· 方差支的后果链验证:异方差 → s 抬高 → s_max 拒判 → 漏检")
say("  依据:补测① 实测 −45dBFS 档调制 std = 1.317dB,而 IMSD 的 s_max = 1.5dB —— **同量级**。")
BETA_MIN,BETA_MAX,S_MAX,DP_MIN = 0.96,12.0,1.5,6.0   # @B3 槽
W=8; HOP=0.016
rng=np.random.default_rng(7)
def imsd_ls(y):
    x=np.arange(len(y),dtype=float)
    b,c=np.polyfit(x,y,1); s=float(np.sqrt(np.mean((y-(b*x+c))**2)))
    return b,s,(BETA_MIN<=b<=BETA_MAX and s<=S_MAX and y[-1]-y[0]>=DP_MIN)
def imsd_theilsen(y):
    """稳健斜率:Theil-Sen(中位数斜率)+ MAD 残差 —— 对异方差/离群点不敏感。"""
    x=np.arange(len(y),dtype=float)
    sl=[(y[j]-y[i])/(x[j]-x[i]) for i in range(len(y)) for j in range(i+1,len(y))]
    b=float(np.median(sl)); c=float(np.median(y-b*x))
    r=y-(b*x+c); s=float(1.4826*np.median(np.abs(r-np.median(r))))
    return b,s,(BETA_MIN<=b<=BETA_MAX and s<=S_MAX and y[-1]-y[0]>=DP_MIN)
say(f"  {'调制std':>8} {'LS命中率':>9} {'LS中位s':>9} {'TheilSen命中率':>14} {'TS中位s':>9}")
for mod_std in (0.0, 0.3, 0.6, 1.0, 1.317, 1.8):
    hl=[];sl_=[];ht=[];st_=[]
    for _ in range(400):
        beta_dbs=120.0                       # 真啸叫 120dB/s(远高于 β_min=60)
        y=beta_dbs*HOP*np.arange(W)+rng.normal(0,0.25,W)      # 真实轨迹+固有 shimmer
        y=y+rng.normal(0,mod_std,W)                           # ★ AEC 调制引入的异方差
        b,s,ok=imsd_ls(y);   hl.append(ok); sl_.append(s)
        b2,s2,ok2=imsd_theilsen(y); ht.append(ok2); st_.append(s2)
    say(f"  {mod_std:8.3f} {np.mean(hl)*100:8.1f}% {np.median(sl_):9.3f} {np.mean(ht)*100:13.1f}% {np.median(st_):9.3f}")
say("  ⇒ 若 LS 命中率随调制 std 塌落而 Theil-Sen 保持 ⇒ **修法归我方拟合,一 dB MSG 都不用花**(架构侧方差支判词)。")
say("  ⇒ 若两者同步塌落 ⇒ 稳健拟合救不了,须回头找别的修法(如加长 W_long 平均掉抖动)。")

say("\n  -- 备选修法:加长窗(靠平均压方差)--")
for Wl in (8,10,12,16):
    hl=[]
    for _ in range(400):
        y=120.0*HOP*np.arange(Wl)+rng.normal(0,0.25,Wl)+rng.normal(0,1.317,Wl)
        x=np.arange(Wl,dtype=float); b,c=np.polyfit(x,y,1)
        s=float(np.sqrt(np.mean((y-(b*x+c))**2)))
        hl.append(BETA_MIN<=b<=BETA_MAX and s<=S_MAX and y[-1]-y[0]>=DP_MIN)
    say(f"     W_long={Wl:2d}(={Wl*16}ms)  LS 命中率={np.mean(hl)*100:5.1f}%  ⚠ 代价:T_decide 由 128ms 增至 {Wl*16}ms")
io.open('results_w2_r4.txt','a',encoding='utf-8').write('\n'+'\n'.join(OUT))
