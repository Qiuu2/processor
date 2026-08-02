"""r40 ②:修尺子 —— T 敏感性 + 源频谱覆盖 + 量化残差。
线索:对照④ 的偏差**方向相反**(一条低于解析、一条高于)⇒ 指向分辨力/随机性,非系统错。
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np, clrig, howl_detect as HD
from clrig import FS
FRAME=64; STEP=0.5
def src_of(T,seed): return 1e-3*np.random.default_rng(seed).standard_normal(int(T*FS))
def ref_db(T,seed):
    s=src_of(T,seed); n=(len(s)//FRAME)*FRAME; return HD.rms_db(s[:n])
def howls(h,D,G,T,seed):
    lp=clrig.Loop(h,D,G); _,loop=lp.run(src_of(T,seed),FRAME)
    return HD.is_howling(loop, ref_db(T,seed), FS, FRAME)[0]
def msg(h,D,T,seed,lo=-40.,hi=20.):
    G=lo; last=lo
    while G<=hi:
        if howls(h,D,G,T,seed): return last
        last=G; G+=STEP
    return float('inf')

print("r40 ② · 修尺子\n")
print("【源频谱覆盖】当前源 = standard_normal(白噪) —— 实测确认,不假定")
s=src_of(3.0,0); S=np.abs(np.fft.rfft(s)); f=np.fft.rfftfreq(len(s),1/FS)
m=(f>=100)&(f<=8000); band=20*np.log10(S[m]+1e-30)
# 按 1/3 倍频程分档看有没有谱洞
edges=np.geomspace(100,8000,25); mids=[]
for a,b in zip(edges[:-1],edges[1:]):
    mm=(f>=a)&(f<b)
    if mm.sum(): mids.append(np.median(20*np.log10(S[mm]+1e-30)))
mids=np.array(mids)
print(f"   1/3 oct 分档中位电平:极差={mids.max()-mids.min():.2f}dB  σ={mids.std():.2f}dB")
print(f"   ⇒ {'**近似平坦,无谱洞 ⇒ 嫌疑2 排除**' if mids.max()-mids.min()<6 else '**有谱洞 ⇒ 嫌疑2 成立**'}")

print("\n【T 敏感性】预注册证伪条件③:T 与 2T 的 MSG 差 > 1dB ⇒ 观察时长不足")
print(f"{'T60':>5}{'seed':>5}{'解析':>8}{'MSG@3s':>9}{'MSG@6s':>9}{'MSG@12s':>10}{'|3s−6s|':>9}{'|6s−12s|':>10}")
for T60 in [0.2,0.5]:
    for sd in [0,1,2]:
        h,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
        ana,_=clrig.analytic_msg_db(clrig.h_eff(h))
        m3=msg(h,D,3.0,sd); m6=msg(h,D,6.0,sd); m12=msg(h,D,12.0,sd)
        print(f"{T60:>5.1f}{sd:>5}{ana:>8.2f}{m3:>9.2f}{m6:>9.2f}{m12:>10.2f}"
              f"{abs(m3-m6):>9.2f}{abs(m6-m12):>10.2f}")
        sys.stdout.flush()
print("\n【量化残差】阶梯 0.5dB ⇒ MSG 量化误差 ±0.25dB(从 1.64dB 偏差预算里扣除后仍余 ~1.4dB)")
