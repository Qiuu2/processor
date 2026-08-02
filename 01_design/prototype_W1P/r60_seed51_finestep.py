"""r60 · Hk 的唯一失败条(0.5/seed1)—— 用更细阶梯 + 更长观察窗直接测,不靠解释。

r59 实测:f_trig = 213.0 Hz(= 挂陷后【带内】峰 213.2,差 0.2 Hz),
          而挂陷后【全带】峰在 22.3 Hz ⇒ Hk(|差|≤20Hz)FAIL。
盘面已有的量:该条 ΔMSG_带内 6.61 / ΔMSG_全带 6.33 ⇒ **两个候选临界点只差 0.28 dB**,
             **低于扫描阶梯 0.5 dB** ⇒ 扫描在原理上分辨不了它们。

⇒ 这是一个**解释**。按 F34,解释不算数,去测:把阶梯降到 0.1 dB、观察窗加到 12 s。

预注册(先写死):
  Hm · 细阶梯+长窗下,f_trig 移到 22.3 Hz 附近(|差|≤20Hz)且 ΔMSG → 6.33 ±0.2
       ⇒ **原因 = 分辨力,不是"预测式漏机制"**。
  Hm'· f_trig 仍停在 213 Hz 且 ΔMSG 仍 ≥6.5
       ⇒ **22.3 Hz 那个点在闭环里够不到** ⇒ 另有机制(疑:逐帧 RMS 判据对低频音的固有限制
          —— frame=64 样本=1.33ms,22.3Hz 一个周期 44.8ms=33.6 帧 ⇒ 帧 RMS 随瞬时包络起伏,
          可能在每个过零处跌破 3dB 释放门 ⇒ 末段"保持"判据不成立)。**须单独查,不得含糊。**
[L2/宿主仿真]  deps: clrig.py@8ad47ce8d260dd18 nhs.py@706b658842d84316
                     howl_detect.py@fd63e901f2d8be33 msg_meter.py
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit, pick_excl, mk_alg
FRAME=64; GR={'out_lim_active':False,'out_lim_gr_db':0.0}
O=[]
def W(s):
    O.append(s); print(s); sys.stdout.flush()
def src_of(T,s): return 1e-3*np.random.default_rng(s).standard_normal(int(T*FS))
T60,sd=0.5,1
h0,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
hb=band_limit(h0,8000.); he=clrig.h_eff(hb)
mt=MSGMeter(he,FS); r0=mt.msg(slots=(),g_duck_db=0.)
pk=pick_excl(he,8); a=mk_alg(pk,True); r1=mt.msg(slots=a.slots,g_duck_db=0.)
W("r60 · 0.5/seed1 细阶梯复测(Hk 唯一失败条)")
W("deps: clrig.py@8ad47ce8d260dd18 nhs.py@706b658842d84316 howl_detect.py@fd63e901f2d8be33")
W("[L2/宿主仿真]  f_cut=8k  臂=8陷波+duck已消融  预注册=本文件头")
W(f"挂陷前:MSG_带内 {r0['in']['msg_db']:+.3f} @ {r0['in']['f_crit']:.1f}Hz | "
  f"MSG_全带 {r0['full']['msg_db']:+.3f} @ {r0['full']['f_crit']:.1f}Hz")
W(f"挂陷后:MSG_带内 {r1['in']['msg_db']:+.3f} @ {r1['in']['f_crit']:.1f}Hz | "
  f"MSG_全带 {r1['full']['msg_db']:+.3f} @ {r1['full']['f_crit']:.1f}Hz")
W(f"⇒ 两个候选临界点相差 **{r1['in']['msg_db']-r1['full']['msg_db']:.3f} dB**"
  f"(挂陷后带内 vs 全带)")
W("")
# ⚠ 窄窗扫描:m0 已知 ≈ -13.75、mk 已知 ≈ -7.25(r57 §2,STEP=0.5)
#   ⇒ 只在各自阈值邻域细扫,避免 170 步全扫(上一次因此超时,属操作层问题非物理)
WIN={'基线':(-15.0,-12.5),'8陷':(-8.5,-5.5)}
for T_OBS,STEP in ((12.0,0.1),(24.0,0.1)):
    src=src_of(T_OBS,sd); ref=HD.rms_db(src[:(len(src)//FRAME)*FRAME])
    out={}
    for nm,mk in (('基线',lambda:None),('8陷',lambda:mk_alg(pk,True))):
        lo_,hi_=WIN[nm]; G=lo_; last=None; ft=float('nan'); Gh=float('nan')
        while G<=hi_+1e-9:
            alg=mk()
            pf=None if alg is None else (lambda blk,_a=alg:_a.process_frame(blk,GR))
            _,lp=clrig.Loop(hb,D,G,proc=pf).run(src,FRAME)
            hw,_,_=HD.is_howling(lp,ref,FS,FRAME)
            if hw:
                n=int(2*FS); Xf=np.abs(np.fft.rfft(lp[-n:]*np.hanning(n)))
                ft=float(np.fft.rfftfreq(n,1/FS)[int(np.argmax(Xf))]); Gh=G; break
            last=G; G+=STEP
        out[nm]=(last,ft,Gh)
    d=out['8陷'][0]-out['基线'][0]
    W(f"T_OBS={T_OBS:4.1f}s STEP={STEP:.1f}dB: m0={out['基线'][0]:+.2f} mk={out['8陷'][0]:+.2f} "
      f"**ΔMSG={d:+.2f}**  挂陷臂 f_trig={out['8陷'][1]:8.1f}Hz "
      f"(|−22.3|={abs(out['8陷'][1]-r1['full']['f_crit']):7.1f}Hz)")
W("")
W(f"判读锚:ΔMSG_带内神谕 = {r0['in']['msg_db']*0+6.61:.2f} / ΔMSG_全带神谕 = "
  f"{r1['full']['msg_db']-r0['full']['msg_db']:.2f};f_trig 若移向 22.3Hz ⇒ Hm 立(分辨力问题)")
open('/home/it1234/processor/01_design/prototype_W1P/r60_seed51_out.txt','w').write("\n".join(O)+"\n")
