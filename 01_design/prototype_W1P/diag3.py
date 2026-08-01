import numpy as np
from experiments import *
from env import synth_speech, FS
from nhs import NHS, Params
a=NHS(P=Params(max_depth=-3.0, depth0=-3.0))
orig=a._analysis_slot; snap=[]
def wrapped(gr):
    orig(gr)
    Xc=np.fft.rfft(a.sc_buf*a.win); M=np.abs(Xc); df=16000.0/1024
    klo,khi=int(120/df),int(7800/df)
    loc=[k for k in range(max(2,klo),khi) if M[k]>M[k-1] and M[k]>=M[k+1]]
    loc.sort(key=lambda k:-M[k]); c=loc[:16]
    if a.slot_seq in (60,120,180,240,300,400,500,600):
        rows=[]
        for k in c[:3]:
            rows.append((round(k*df), round(a._level(M,k),1), round(a._papr(M,k),1), round(a._pnpr(M,k),1)))
        snap.append((a.slot_seq, round(a.t_wall,2), a.gr_hist, rows,
                     sum(1 for t in a.tracks if t.active)))
a._analysis_slot=wrapped
src=synth_speech(10.0)*0.5*3e-3
out,tap=scen_pinned(a,src=src+1e-5*np.random.default_rng(1).normal(0,1,len(src)))
print("slot  t     gr_hist  top3候选(Hz, level dBFS, PAPR dB, PNPR dB)                  轨活")
for s,t,g,rows,na in snap:
    print(f"{s:4d} {t:5.2f}  {g:5d}   {str(rows):58s} {na}")
print(f"\n门限: T_low=-45 T_low_gr=-65 T_papr=15 T_pnpr=8")
