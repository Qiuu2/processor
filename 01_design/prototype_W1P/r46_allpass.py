"""r46:**全通滤波器测试** —— 验证台架的【相位通路】。
⭐ 立法理由(架构侧):平坦衰减是纯**幅度**改变,证明台架能正确测幅度差,
   **不证明它能正确处理相位结构变化** —— 而陷波的关键效应恰恰是
   「相位改变导致临界点移动」(我们花了一整轮才确认这一点)。
⇒ 插入**纯全通**(|H|≡1,只改相位)⇒ 幅度完全不变,临界点集会移动
⇒ 用迭代式算出预期 ΔMSG,与实测比。
   相符 ⇒ 相位通路准 ⇒ 与平坦扫描(纯幅度,已过)**张成陷波的作用空间**;
   不符 ⇒ 问题正在相位通路上,**而那正是陷波起作用的通路** ⇒ 必须修。
⚠ 全通的 |H|≡1 必须**实测验证**,不能假定(否则它就不是纯相位干预)。
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
from scipy.signal import lfilter
import clrig, howl_detect as HD
from clrig import FS
FRAME=64; STEP=0.5; T_OBS=6.0
BOUND=[]
def allpass(a_coef):
    """一阶全通 H(z) = (a + z^-1)/(1 + a z^-1),|H(e^jw)| ≡ 1。"""
    return np.array([a_coef,1.0]), np.array([1.0,a_coef])
def src_of(T,seed): return 1e-3*np.random.default_rng(seed).standard_normal(int(T*FS))
def ref_db(T,seed):
    s=src_of(T,seed); n=(len(s)//FRAME)*FRAME; return HD.rms_db(s[:n])
def howls(h,D,G,pf,T,seed):
    lp=clrig.Loop(h,D,G,proc=pf()); _,loop=lp.run(src_of(T,seed),FRAME)
    return HD.is_howling(loop, ref_db(T,seed), FS, FRAME)[0]
def msg(h,D,pf,T,seed,lo,hi,tag=''):
    G=lo; last=None
    while G<=hi+1e-9:
        if howls(h,D,G,pf,T,seed):
            if last is None: BOUND.append((tag,'下界')); return float('nan')
            return last
        last=G; G+=STEP
    BOUND.append((tag,'上界')); return float('nan')
def ap_proc(b,a):
    st={'zi':np.zeros(max(len(a),len(b))-1)}
    def f():
        st['zi']=np.zeros(max(len(a),len(b))-1)
        def g(blk):
            y,st['zi']=lfilter(b,a,blk,zi=st['zi']); return y
        return g
    return f
print("r46 · 全通测试(相位通路)")
print(f"[L2/宿主仿真] 阶梯={STEP}dB T={T_OBS}s\n")
print("【前置:全通的 |H| 确实 ≡1 吗?实测,不假定】")
for ac in [0.5,0.8,-0.7]:
    b,a=allpass(ac); w=np.linspace(0,np.pi,4096)[1:]
    from scipy.signal import freqz
    _,H=freqz(b,a,worN=w); mag=np.abs(H)
    print(f"   a={ac:+.2f}:  |H| min={mag.min():.6f}  max={mag.max():.6f}  "
          f"极差={20*np.log10(mag.max()/mag.min()):.2e} dB  "
          + ("**纯相位 ✓**" if abs(mag.max()-1)<1e-9 and abs(mag.min()-1)<1e-9 else "**非纯相位 ⇒ 该测试无效**"))
print()
print(f"{'T60':>5}{'seed':>5}{'a':>7}{'解析':>8}{'基线':>8}{'加全通':>9}{'实测Δ':>8}{'预测Δ':>8}{'|差|':>7}")
for T60 in [0.2,0.5]:
    for sd in [0,1]:
        h,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
        he=clrig.h_eff(h); ana,_=clrig.analytic_msg_db(he)
        m0=msg(h,D,lambda:None,T_OBS,sd,ana-6,ana+6,f'{T60}/{sd}/base')
        for ac in [0.5,-0.7]:
            b,a=allpass(ac)
            # 预测:把全通并入环路响应后重算解析 MSG
            f_,H_=clrig.F_response(he); from scipy.signal import freqz
            _,Hap=freqz(b,a,worN=2*np.pi*f_/FS)
            fc,mdb=clrig._crit_from_H(f_[(f_>=100)&(f_<=8000)],(H_*Hap)[(f_>=100)&(f_<=8000)])
            ana2=-mdb.max() if len(mdb) else float('nan')
            pred=ana2-ana
            mA=msg(h,D,ap_proc(b,a),T_OBS,sd,ana+pred-6,ana+pred+6,f'{T60}/{sd}/ap{ac}')
            d=mA-m0 if np.isfinite(mA) and np.isfinite(m0) else float('nan')
            print(f"{T60:>5.1f}{sd:>5}{ac:>7.2f}{ana:>8.2f}{m0:>8.2f}{mA:>9.2f}{d:>8.2f}{pred:>8.2f}{abs(d-pred):>7.2f}")
            sys.stdout.flush()
print(f"\n【边界命中】{len(BOUND)} 次" + ("" if not BOUND else f": {BOUND}"))
print("判据:|实测Δ − 预测Δ| < 1.0 dB ⇒ 相位通路准")
