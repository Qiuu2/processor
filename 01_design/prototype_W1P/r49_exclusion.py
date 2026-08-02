"""r49 ①:三臂选点策略对比 —— 批量 / 批量+排他区 / 顺序挂(神谕层)。
⭐ 机制:临界点间距 17–36Hz,陷波带宽 504Hz@2.5kHz ⇒ 一个陷波覆盖 14–30 个临界点
   ⇒ 按临界点排序取 top-8 **必然从同一簇里挑出多个**(seed1 实测:2518.7 与 2590.6Hz 只差 72Hz)。
   ⇒ **顺序挂之所以赢,不只是跟上了相位扰动,而是它【天然带去重】**
     (挂一个 ⇒ 重算 ⇒ 被覆盖的整簇从候选里消失)。
   ⇒ 排他区选点是等价的便宜做法:选中一个后剔除其 ±1 带宽内的所有候选。
   ⇒ **若它能拿到接近顺序挂的收益,则 3.26dB 从"调试期收益"变成"运行期也能拿"**
     (不必付顺序挂 4–8s 的整定时间)。
同时报**全带中位 |N|**(宽带衰减)—— SD 落地前的**临时代理指标**,⚠ **它不是 SD**。
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
from scipy.signal import freqz
import clrig, nhs
from clrig import FS
P = nhs.Params()
def notch_H(f0, fgrid):
    A = 10**(P.max_depth/40.); w0 = 2*np.pi*f0/FS
    al = np.sin(w0)*np.sinh(np.log(2)/2*P.bw_oct*w0/np.sin(w0))
    b = np.array([1+al*A, -2*np.cos(w0), 1-al*A]); a = np.array([1+al/A, -2*np.cos(w0), 1-al/A])
    _, Hn = freqz(b, a, worN=2*np.pi*fgrid/FS)
    return Hn
def bw_of(f): return max(f*P.bw_oct, 15.0)
def evaluate(he, picks):
    f0,H0 = clrig.F_response(he); m=(f0>=100)&(f0<=8000)
    fm=f0[m]; Hm=H0[m].copy(); Hn_tot=np.ones(len(fm),dtype=complex)
    for f_ in picks: Hn_tot = Hn_tot*notch_H(f_,fm)
    _,m0 = clrig._crit_from_H(fm,Hm); _,m1 = clrig._crit_from_H(fm,Hm*Hn_tot)
    bb = 20*np.log10(np.median(np.abs(Hn_tot)))          # 全带中位 |N|(宽带衰减代理)
    return float(m0.max()-m1.max()), float(bb)
def pick_batch(he,k=8):
    fc,mdb = clrig.critical_points(he); o=np.argsort(mdb)[::-1]
    return [float(fc[i]) for i in o[:k]]
def pick_excl(he,k=8):
    """贪心 + 排他区:选中一个后剔除其 ±1 带宽内的所有候选。"""
    fc,mdb = clrig.critical_points(he); o=list(np.argsort(mdb)[::-1])
    picks=[]; used=np.zeros(len(fc),bool)
    for i in o:
        if used[i] or len(picks)>=k: continue
        f_=float(fc[i]); picks.append(f_)
        bw=bw_of(f_); used |= (np.abs(fc-f_) <= bw)
    return picks
def pick_seq(he,k=8):
    """顺序挂:每挂一个重算临界集再选下一个。"""
    f0,H0=clrig.F_response(he); m=(f0>=100)&(f0<=8000)
    fm=f0[m]; H=H0[m].copy(); picks=[]
    for _ in range(k):
        fc,mdb = clrig._crit_from_H(fm,H)
        if len(fc)==0: break
        f_=float(fc[int(np.argmax(mdb))]); picks.append(f_)
        H = H*notch_H(f_,fm)
    return picks
print("r49 · 三臂选点策略(神谕层)")
print("⚠ 全带中位|N| 是 SD 的**临时代理**,**不是 SD**\n")
print(f"{'T60':>5}{'seed':>5} | " + " | ".join(f"{n:>22}" for n in ['批量 ΔMSG/宽带','批量+排他区','顺序挂']))
res={'batch':[], 'excl':[], 'seq':[]}
for T60 in [0.2,0.5]:
    for sd in [0,1,2]:
        h,_=clrig.make_F(T60=T60,delay_ms=8.,seed=sd); he=clrig.h_eff(h)
        row=[]
        for nm,fn in [('batch',pick_batch),('excl',pick_excl),('seq',pick_seq)]:
            pk=fn(he,8); d,bb=evaluate(he,pk); res[nm].append(d)
            row.append(f"{d:>7.2f} dB /{bb:>6.2f} dB")
        print(f"{T60:>5.1f}{sd:>5} | " + " | ".join(f"{r:>22}" for r in row))
        sys.stdout.flush()
print()
for nm,lbl in [('batch','批量'),('excl','批量+排他区'),('seq','顺序挂')]:
    a=np.array(res[nm]); print(f"  {lbl:<12} ΔMSG 均值 = {a.mean():5.2f} dB  (min {a.min():.2f} max {a.max():.2f})")
b=np.array(res['batch']); e=np.array(res['excl']); s=np.array(res['seq'])
print(f"\n  排他区相对批量的增益 = **{(e-b).mean():+.2f} dB**")
print(f"  顺序挂相对批量的增益 = **{(s-b).mean():+.2f} dB**")
rec=(e-b).mean()/max((s-b).mean(),1e-9)*100
print(f"  ⇒ **排他区拿回了顺序挂增益的 {rec:.0f}%**"
      + ("  ⇒ **可在运行期拿到,不必付 4–8s 整定**" if rec>70 else "  ⇒ 回收不足,顺序挂仍有独立价值"))
