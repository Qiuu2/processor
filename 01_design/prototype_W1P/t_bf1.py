import numpy as np
from experiments import *
from nhs import NHS
print("=== B-F1 钉住啸叫实测(输出限幅器入环,tap 远低于 T_panic)===")
for name, alg in (("bypass", Bypass()), ("NHS 完整", NHS())):
    out, tap = scen_pinned(alg)
    m = metrics(out); tl = tap_level_dbfs(tap, 2.0)
    print(f"{name:10s}: 输出末={m['end_db']:6.1f}dB 窄带={m['nb']:.3f} f={m['f_peak']:6.1f}Hz "
          f"| tap RMS={tl:6.1f}dBFS | 仍在啸={howling(m)}")
    if hasattr(alg,'events') and alg.events:
        eng=[e for e in alg.events if str(e[1]).startswith('engage')]
        print(f"    engage 事件={len(eng)} 前3={eng[:3]}  末陷波={[(round(s.f,1),round(s.depth,1)) for s in alg.slots if s.st!=0]}")
    elif hasattr(alg,'events'):
        print(f"    事件=0(**完全没检出**)")

print("\n=== 钉住过程时间线(bypass,确认限幅器钉的是啸叫)===")
out,tap = scen_pinned(Bypass())
e=env_db(out)
for t in (0.5,1,2,4,6,9):
    i=int(t*FS); seg=out[max(0,i-8192):i]
    if len(seg)>=4096:
        X=np.abs(np.fft.rfft(seg[-4096:]*np.hanning(4096)))
        print(f"  t={t:4.1f}s 输出包络={e[i]:7.1f}dB 窄带={X.max()**2/np.sum(X**2):.3f} f={np.argmax(X)*FS/4096:7.1f}Hz  tap={20*np.log10(np.sqrt(np.mean(tap[max(0,i-8192):i]**2))+1e-30):7.1f}dBFS")
