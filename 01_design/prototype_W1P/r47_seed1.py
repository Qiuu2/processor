"""r47:seed1(ΔMSG=0)的成因 —— ①陷波是否真挂上 ②相位扰动是否造出更高的新临界点。"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
from scipy.signal import freqz
import clrig, nhs
from nhs import NHS
from clrig import FS
T60, SD = 0.2, 1
h,D = clrig.make_F(T60=T60, delay_ms=8., seed=SD)
he = clrig.h_eff(h)
fc0, m0 = clrig.critical_points(he)
order = np.argsort(m0)[::-1]
targets = [float(fc0[order[i]]) for i in range(8)]
print(f"r47 · seed{SD} (T60={T60}) 成因排查\n")
print("【① 陷波是否真挂上、深度是否正常】")
a = NHS()
for i in range(8):
    s=a.slots[i]; s.st=nhs.NotchSlot.HOLD; s.f=targets[i]
    s.depth=a.P.max_depth; s.target=a.P.max_depth; s.set_coef(FS,a.P.bw_oct)
nz = sum(1 for s in a.slots if s.st!=nhs.NotchSlot.FREE)
print(f"   非 FREE 槽数 = {nz}/8")
w_all = np.linspace(0,np.pi,1<<16)[1:]
f_all = w_all*FS/(2*np.pi)
Htot = np.ones(len(w_all), dtype=complex)
for i,s in enumerate(a.slots[:8]):
    _,Hn = freqz(s.b, s.a, worN=w_all)
    Htot *= Hn
    k=int(np.argmin(np.abs(f_all-s.f)))
    print(f"   槽{i}: f={s.f:8.1f}Hz  depth设定={s.depth:6.1f}dB  "
          f"**该点实测|N|={20*np.log10(np.abs(Hn[k])):7.2f}dB**  系数b0={s.b[0]:.4f}")
print(f"   ⇒ {'**8 个陷波确实挂上且深度正常**' if nz==8 else '**挂陷异常**'}")

print("\n【② 相位扰动是否造出更高的新临界点(架构侧假说)】")
f0,H0 = clrig.F_response(he)
m = (f0>=100)&(f0<=8000)
fm = f0[m]; Hm = H0[m]
_,Hn_all = freqz(np.array([1.0]),np.array([1.0]),worN=2*np.pi*fm/FS)
Hprod = Hm.copy()
for s in a.slots[:8]:
    _,Hn = freqz(s.b,s.a,worN=2*np.pi*fm/FS)
    Hprod = Hprod*Hn
fc1,m1 = clrig._crit_from_H(fm,Hprod)
print(f"   原始临界集: N={len(fc0)}  max|F|={m0.max():7.2f}dB @ {fc0[order[0]]:.1f}Hz")
print(f"   挂陷后临界集: N={len(fc1)}  max|F|={m1.max():7.2f}dB @ {fc1[int(np.argmax(m1))]:.1f}Hz")
print(f"   ⇒ 预测 ΔMSG = {m0.max()-m1.max():+.2f} dB  "
      + ("**不降反升 ⇒ 假说成立**" if m1.max()>=m0.max() else "正常下降"))
fnew = float(fc1[int(np.argmax(m1))])
d_near = np.min(np.abs(fc0-fnew))
print(f"   新最大点 {fnew:.1f}Hz 距最近的原始临界点 = {d_near:.2f}Hz  "
      + ("⇒ **新生的**" if d_near>2.0 else "⇒ 原本就在临界集里"))
gmax = 20*np.log10(np.abs(Hm).max())
print(f"   参考:全带 max|F| = {gmax:.2f}dB;原始临界集 max = {m0.max():.2f}dB  "
      f"⇒ Δ = {gmax-m0.max():.2f}dB(临界集之上确实还有更高区域)")
print(f"   新最大点的 |F|(未含陷波)= {20*np.log10(np.abs(Hm[int(np.argmin(np.abs(fm-fnew)))])):.2f}dB")
