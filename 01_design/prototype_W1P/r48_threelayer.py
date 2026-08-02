"""r48:三层分解 ①神谕·迭代重选 ②神谕·一次性 ③实测。
⚠ **信息假设必须写清**(否则 ①−③ 会被读成"实现很差",而其中含**原理上不可得的信息优势**):
   ① 知道 F(z) + 每步重新优选  ⇒ **信息论上界,产品原理上达不到**
   ② 知道 F(z) + 按原始临界集一次性选 ⇒ **仍是神谕**(真实算法按检出的谱峰选,不按临界集)
   ③ 真实算法:只看麦克风信号,**不知道反馈路径**  ⇒ **只有它是产品**
⚠ 一个建立在产品拿不到的信息上的"上界",**拿它当 KPI 会逼团队追一个够不着的数**。
差值命名:①−② = **不重选的代价**(可实施的设计选项);②−③ = **其余实现损失**
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
from scipy.signal import freqz
import clrig, nhs
from nhs import NHS
from clrig import FS
def oracle_oneshot(he, k=8):
    """② 从**原始**临界集取 top-k,一次性挂上,重算临界集最大值。"""
    f0,H0 = clrig.F_response(he); m=(f0>=100)&(f0<=8000)
    fm=f0[m]; Hm=H0[m].copy()
    fc0,m0 = clrig._crit_from_H(fm,Hm)
    order=np.argsort(m0)[::-1]
    P=nhs.Params(); A=10**(P.max_depth/40.)
    Hp=Hm.copy()
    for i in range(k):
        f_=float(fc0[order[i]]); w0=2*np.pi*f_/FS
        al=np.sin(w0)*np.sinh(np.log(2)/2*P.bw_oct*w0/np.sin(w0))
        b=np.array([1+al*A,-2*np.cos(w0),1-al*A]); a=np.array([1+al/A,-2*np.cos(w0),1-al/A])
        _,Hn=freqz(b,a,worN=2*np.pi*fm/FS); Hp=Hp*Hn
    _,m1=clrig._crit_from_H(fm,Hp)
    return float(m0.max()-m1.max())
print("r48 · 三层分解(①② 解析部分)")
print("⚠ ①② 均为**神谕**(知道 F(z));只有 ③ 是产品\n")
print(f"{'T60':>5}{'seed':>5}{'①迭代重选':>11}{'②一次性':>10}{'①−②':>9}{'  ← 不重选的代价':>0}")
gaps=[]
for T60 in [0.2,0.5]:
    for sd in [0,1,2]:
        h,_=clrig.make_F(T60=T60,delay_ms=8.,seed=sd); he=clrig.h_eff(h)
        p1,_=clrig.predict_dmsg_iter(he,8)
        p2=oracle_oneshot(he,8)
        gaps.append(p1-p2)
        print(f"{T60:>5.1f}{sd:>5}{p1:>11.2f}{p2:>10.2f}{p1-p2:>9.2f}")
g=np.array(gaps)
print(f"\n【不重选的代价】均值 = **{g.mean():.2f} dB**  σ = {g.std():.2f}  "
      f"min={g.min():.2f} max={g.max():.2f}")
print(f"   ⇒ {'**稳定在 2dB 量级 ⇒ 是一个可实施的设计选项,单独报架构侧与 D13**' if abs(g.mean()-2)<1.2 and g.std()<1.5 else '离散度大,须更多样本'}")
