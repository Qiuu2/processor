"""r29 ②:C 臂 ext=42 vs A 臂 55,少的 13 个去哪了?
若也是被断言吃掉的**立即释放机会** ⇒ (丙) 立即重探的收益比现在看到的更大。
方法:在 C 臂配置下,统计被判仪表故障的探针,其**若不丢弃**本会走向什么判决 ——
      用同一 M 复算 ext/howl/abstain(纯离线复算,不改行为)。
[L2/宿主仿真·合成料]
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np, nhs, fp_suite as S
from nhs import NHS, FRAME
GR={'out_lim_active':False,'out_lim_gr_db':0.0}
DUR=200.0; N=6
for nm,mk in [('钢琴',S.m_piano),('多人交谈',S.m_multitalk)]:
    would={'ext':0,'howl':0,'abstain_L0':0,'abstain_L1':0,'unknown':0}; nf=0
    for sd in range(N):
        a=NHS()
        orig=a._probe_tick
        def patched(M,df,a=a,orig=orig,would=would):
            snap={si:dict(pr) for si,pr in a.probes.items()}
            n0=len(a.c8_log); nfa0=a.ctr.get('instrument_fault',0)
            orig(M,df)
            if a.ctr.get('instrument_fault',0)>nfa0:
                # 找出本槽被判故障的探针,离线复算"若不丢弃会怎样"
                for e in a.events[-4:]:
                    if e[1]!='INSTRUMENT_FAULT': continue
                    for si,pr in snap.items():
                        if abs(pr['f']-e[2])>1.0: continue
                        k=int(round(pr['f']/df))
                        if not (0<k<len(M)): would['unknown']+=1; break
                        L0=a._level(M,k); FL=a._floor_level(M,df)
                        gate=FL+a.P.probe_floor_M
                        # L0 退化 ⇒ 该探针即使跑完也必然弃权(L0 侧触发)
                        would['abstain_L0' if L0<=gate else 'ext']+=1
                        break
        a._probe_tick=patched
        mat=mk(DUR,1000+sd); n=(len(mat)//FRAME)*FRAME
        for i in range(0,n,FRAME): a.process_frame(mat[i:i+FRAME],GR)
        nf+=a.ctr.get('instrument_fault',0)
    tot=sum(would.values())
    print(f"【{nm}】C 臂仪表故障 {nf} 例;离线复算「若不丢弃」的去向(可归类 {tot}):")
    for k,v in would.items():
        if v: print(f"    {k:<12} {v:>4} ({v/max(tot,1)*100:>5.1f}%)")
    print(f"    ⇒ 其中**本会立即释放槽位(ext)**= {would['ext']} 例"
          f" ⇒ {'**(丙) 能救回这些**' if would['ext']>0 else '这些本来也不会立即释放'}")
