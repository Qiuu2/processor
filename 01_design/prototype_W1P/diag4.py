import numpy as np
from experiments import *
from env import FS
from nhs import NHS, Params
print("=== 钉住峰的**逐 bin 电平**(门实际比较的量)vs tap RMS(此前标定误用的量)===")
print("前向  tapRMS   峰bin电平   差    T_low_gr=-65 判定")
for gf in (40.,45.,50.,52.,55.,60.):
    a=NHS(); rows=[]
    orig=a._analysis_slot
    def w(gr, a=a, rows=rows):
        orig(gr)
        M=np.abs(np.fft.rfft(a.sc_buf*a.win)); df=16000.0/1024
        k=int(round(4031/df))
        if 2<k<len(M)-1 and 1.5 < a.t_wall < 3.0: rows.append(a._level(M,k))
    a._analysis_slot=w
    out,tap=scen_pinned(a,g_fwd=gf)
    rms=tap_level_dbfs(tap,2.0); pk=max(rows) if rows else float('nan')
    print(f"{gf:4.0f}dB {rms:7.1f} {pk:9.1f} {pk-rms:7.1f}   {'过门' if pk>-65 else '**不及门**'}")
