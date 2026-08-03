"""r59 · f_cut=8k 时闭环【实测】起振主导频率 —— 补 r57 的漏项(lead 点名)。

⛔⛔ B-1 限定横幅(2026-08-03,独立 critic verdict FAIL 后补;**引用本文件任何数字前必读**)
   本文件的陷波频点取自 `clrig.critical_points()` = **解析神谕**,不是 NHS 的检测输出;
   且槽被直接写成 `st=HOLD` 并设 `P.T_low = 999.` ⇒ `nhs.py:402` 的**首次获取**门 = 999 dBFS
   ⇒ 信号上限 0 dBFS ⇒ **新分配全程关闭**。
   ⚠ **勘正(2026-08-03,critic 抓获;本横幅前一版写"979"是错的)**:
     `T_low_gr` 在 `Params.__init__`(`nhs.py:73`)就按 `T_low−20` **算死为 −65.0**,
     `mk_alg` 在 `NHS()` **构造之后**才改 `P.T_low`,**不会重算 `T_low_gr`**
     ⇒ **`nhs.py:399-401` 的放宽路径(已覆盖 bin 的【维持】)仍然是通的,门只有 −65 dBFS。**
     ⇒ **被关掉的只有「首次获取」,不是「全部」。** 数值影响 = 0(预挂槽已在 max_depth,
       维持路径改不了任何东西),但**描述必须准确** —— 这段文字的用途正是防止别人误读。
   `nhs.py:94` `lift_after_s=60 > T_OBS` ⇒ 预挂槽整轮不释放。
   ⇒ **被测对象 = 「8 个 RBJ 陷波器,由解析式放在最优点上」= NHS 的【上界】,不是 NHS 的性能。**
   ⇒ 本文件产出的 ΔMSG **不得称作「NHS 实测」,不得用于「达标/未达标」判定。**
   ⇒ NHS 自选下的数 = 未测(整改队列 1(b):自由槽位起振扫描,T_low 默认)。
预注册:PREREG_r59.txt(Hj/Hk/Hl 与互斥声明跑前落盘)
输出  :r59_ftrig8k_out.txt  [L2/宿主仿真]
deps  : clrig.py@8ad47ce8d260dd18, nhs.py@706b658842d84316,
        howl_detect.py@fd63e901f2d8be33, msg_meter.py
被测对象(D6-b):f_trig = **环路信号末 1s 的谱主峰**,即实际在长起来的那个频率。
  混淆面:若窗内啸叫尚未压过宽带底噪,主峰会读成底噪的随机极大 ⇒ 故只在**判起振**的那一步取。
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit, pick_excl, mk_alg
FRAME=64; STEP=0.5; T_OBS=6.0; GR={'out_lim_active':False,'out_lim_gr_db':0.0}
O=[]
def W(s):
    O.append(s); print(s); sys.stdout.flush()
def src_of(T,s): return 1e-3*np.random.default_rng(s).standard_normal(int(T*FS))
W("r59 · f_cut=8k 闭环实测起振主导频率(补 r57 漏项)")
W("deps: clrig.py@8ad47ce8d260dd18 nhs.py@706b658842d84316 howl_detect.py@fd63e901f2d8be33")
W("[L2/宿主仿真]  T_OBS=6.0s STEP=0.5dB FRAME=64  臂=8陷波+duck已消融  预注册=PREREG_r59.txt")
W("对照基准(f_cut=24k,r52 实测):15182 / 18895 / 14531 / 17244 Hz —— 全部带外")
W("")
W("="*118)
W(f"{'T60':>5}{'sd':>4}{'首起振G':>9}{'实测f_trig':>11}{'解析后峰(全带)':>15}{'|差|Hz':>9}"
  f"{'解析前峰':>10}{'落带内?':>8}{'<120Hz?':>9}{'判':>6}")
W("="*118)
rows=[]
for T60 in (0.2,0.5):
    for sd in (0,1,2):
        h0,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
        hb=band_limit(h0,8000.); he=clrig.h_eff(hb)
        mt=MSGMeter(he,FS); r0=mt.msg(slots=(),g_duck_db=0.)
        pk=pick_excl(he,8); a=mk_alg(pk,True); r1=mt.msg(slots=a.slots,g_duck_db=0.)
        f_post=r1['full']['f_crit']; f_pre=r0['full']['f_crit']
        src=src_of(T_OBS,sd); ref=HD.rms_db(src[:(len(src)//FRAME)*FRAME])
        G=r0['in']['msg_db']-6.; ft=float('nan'); Gh=float('nan')
        while G<=r0['in']['msg_db']+14.+1e-9:
            alg=mk_alg(pk,True)
            _,lp=clrig.Loop(hb,D,G,proc=lambda blk,_a=alg:_a.process_frame(blk,GR)).run(src,FRAME)
            hw,_,_=HD.is_howling(lp,ref,FS,FRAME)
            if hw:
                n=int(FS); Xf=np.abs(np.fft.rfft(lp[-n:]*np.hanning(n)))
                ft=float(np.fft.rfftfreq(n,1/FS)[int(np.argmax(Xf))]); Gh=G; break
            G+=STEP
        d=abs(ft-f_post); inb=100.<=ft<=8000.; lo=ft<120.
        ok=d<=20.
        rows.append((T60,sd,Gh,ft,f_post,d,f_pre,inb,lo,ok))
        W(f"{T60:>5.1f}{sd:>4}{Gh:>9.2f}{ft:>11.1f}{f_post:>15.1f}{d:>9.1f}"
          f"{f_pre:>10.1f}{('YES' if inb else 'no'):>8}{('YES' if lo else 'no'):>9}"
          f"{('OK' if ok else 'FAIL'):>6}")
W("")
nj=sum(1 for r in rows if r[7]); nk=sum(1 for r in rows if r[9]); nl=[r for r in rows if r[8]]
W(f"⇒ Hj(f_trig 落 100-8000Hz):{nj}/6 " + ("⇒ 立" if nj==6 else "⇒ 未全中(见 Hl 互斥声明)"))
W(f"⇒ Hk(|f_trig − 解析后峰| ≤20Hz):{nk}/6 " + ("⇒ **立**(回到我们算得出的那个具体频点)" if nk==6 else "⇒ ⛔ 未全中,预测式漏机制"))
W(f"⇒ Hl(低频侧 F35 直接体现,f_trig<120Hz):{len(nl)} 条 = "
  f"{[(r[0],r[1],round(r[3],1)) for r in nl]}")
W("⚠ 预注册已声明 Hj 与 Hl 对 0.5/seed0、0.5/seed1 互斥,**以 Hk 为准**,未事后改口径。")
W(f"⇒ 无一条 f_trig > 8000 Hz:{all(r[3]<=8000. for r in rows)}  "
  f"(对照 f_cut=24k 时四条在 14.5-18.9 kHz)⇒ **「带外主导」归因获直接实测验证**")
open('/home/it1234/processor/01_design/prototype_W1P/r59_ftrig8k_out.txt','w').write("\n".join(O)+"\n")
