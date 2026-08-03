"""r71 · `_allocate` 耦合缺陷的【确切形态】—— 先测清楚,再谈修法(lead 裁定主线)。
⛔ 未经 critic 评审。[L2/宿主仿真]。输出 r71_allocate_coupling_out.txt (D6-j)
deps: nhs.py@31decc8e8d07e085 clrig.py@8ad47ce8d260dd18 r57_bandlimit.py@74036010b514080d

════════════════════════════════════════════════════════════════════
代码事实(`nhs.py:_allocate`,逐行读出,非推测)
════════════════════════════════════════════════════════════════════
```
for h in howls:                                   # ← 对【每一个】被分类为 howl 的条目
    same = [槽 with |s.f − f| ≤ bw/2]
    if same:
        s.target = max(max_depth, s.target + depth_step)   # ← 每条目【加深一步 −3 dB】
        s.st = ENGAGE ; continue                            # ← 无速率限制、无最小间隔
    ...
    撞顶(deepened=False ∧ 已达 max_depth):
        g_duck_db = max(−6.0, g_duck_db − 1.0)              # ← 同样【每次复检一步】,无速率限制
```
⇒ **两个执行器(`target` 步进、`g_duck` 步进)都以【每分类事件一步】驱动,均无速率限制。**
⇒ 而**实际深度**由 `_slots_tick` 以 `ramp_db_per_s = 60 dB/s` 向 `target` 爬
  ⇒ 一步 3 dB 需 **50 ms**,而分析槽 ≈ **42.7 ms**
  ⇒ **若每槽都分类命中,`target` 会跑在 `depth` 前面 —— 系统在【上一次动作尚未生效前】就再次下令。**

════════════════════════════════════════════════════════════════════
预注册(跑前落盘)
════════════════════════════════════════════════════════════════════
Hk1 · **超前量存在**:每次 `deepen` 时刻的 `|target − depth|` 中位 > 0。
      量化:报该量的分布,以及"下令次数 / 已生效步数"之比。
      证伪:恒 ≈ 0 ⇒ 爬升快于下令 ⇒ 耦合不成立,须另找机理。
Hk2 · **加深间隔 < 生效所需时间**:相邻 `deepen` 间隔中位 < 50 ms(= 3 dB ÷ 60 dB/s)。
      证伪:间隔 ≫ 50 ms ⇒ 不存在"未生效即再下令"。
Hk3 · **撞顶时间随检出率缩短**:`R_RISE` 18 → 3 时,首次 `DEPTH_EXHAUSTED` 的槽序号提前。
      证伪:两者相同 ⇒ 检出率与深度消耗**未耦合**,推翻 F48.1。
Hk4 · **duck 步进同样无速率限制**:撞顶后 `duck-depth` 事件的间隔 ≈ 分析槽间隔(非固定时间常数)。
Hk5 · **⭐ 反事实(D6-d:拿掉被测物这个数应该等于多少)**:
      加一条**最小生效守卫**(`|target − depth| > 1e-9` 时跳过本次加深),其余一律不动
      ⇒ 预测:撞顶被推迟或消失、挂陷数上升。
      ⚠ **这是【诊断性反事实】,不是提交的修法** —— 它只用来确认耦合是不是那条因果链;
        真正的修法(速率限制?观测后再动作?)须另行设计并过门。⛔ 其数不得当作修法收益引用。
⛔ 本文件不写结论散文。
"""
import sys, numpy as np
sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import clrig, nhs
from nhs import NHS, NotchSlot
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import pick_excl
GR={'out_lim_active':False,'out_lim_gr_db':0.0}
FRAME,BW=64,1/5
SEEDS=[(0.2,0),(0.2,1),(0.2,2),(0.5,0),(0.5,1),(0.5,2)]
O=[]
def W(s=''):
    O.append(s); print(s); sys.stdout.flush()

class Guarded(NHS):
    """Hk5 诊断性反事实:上一步未生效前不再下令加深。⛔ 非提交修法。"""
    def _allocate(self, howls, M=None, df=None):
        keep=[]
        for h in howls:
            bw=self._bw_hz(h['f'])
            same=[s for s in self.slots if s.st!=NotchSlot.FREE and abs(s.f-h['f'])<=bw/2]
            if same and abs(same[0].target-same[0].depth)>1e-9:
                self.ctr['guard_skip']=self.ctr.get('guard_skip',0)+1
                continue
            keep.append(h)
        return super()._allocate(keep, M, df)

def run(cls, hb, D, G, src, rr):
    a=cls(); a.P.bw_oct=BW; a.P.R_RISE=rr
    trace=[]
    o_al=a._allocate
    def w_al(howls,*x,_o=o_al,_a=a,_t=trace):
        pre={id(s):(s.target,s.depth) for s in _a.slots}
        r=_o(howls,*x)
        for s in _a.slots:
            if s.st!=NotchSlot.FREE and id(s) in pre:
                t0,d0=pre[id(s)]
                if s.target<t0-1e-9:
                    _t.append(dict(seq=_a.slot_seq,t=_a.t_wall,f=round(float(s.f),1),
                                   target=s.target,depth=d0,lead=abs(t0-d0)))
        return r
    a._allocate=w_al
    def pf(b,_a=a): return _a.process_frame(b,GR)
    clrig.Loop(hb,D,G,proc=pf).run(src,FRAME)
    used=[s for s in a.slots if s.st!=NotchSlot.FREE]
    ex=[e for e in a.events if len(e)>=2 and e[1]=='DEPTH_EXHAUSTED']
    dk=[e for e in a.events if len(e)>=2 and e[1]=='duck-depth']
    return dict(trace=trace, slots=len(used), fr=sorted(round(float(s.f),1) for s in used),
                first_ex=(ex[0][0] if ex else None), n_duck=len(dk),
                duck_seqs=[e[0] for e in dk], ctr=dict(a.ctr))

def main():
    P=nhs.Params()
    step_ms=abs(P.depth_step)/P.ramp_db_per_s*1000.
    W("未经 critic 评审 —— r71 · `_allocate` 耦合缺陷的确切形态   [L2/宿主仿真]")
    W("deps: nhs.py@31decc8e8d07e085 clrig.py@8ad47ce8d260dd18")
    W("代码事实:加深 = 每个 howl 条目一步(%.1f dB),**无速率限制**;实际深度以 %.0f dB/s 爬"
      % (P.depth_step, P.ramp_db_per_s))
    W("  ⇒ 一步生效需 **%.1f ms**;分析槽 ≈ 42.7 ms ⇒ 每槽命中即【上一步未生效就再下令】" % step_ms)
    W("")
    W("%5s%4s%7s | %8s%9s%9s | %10s%9s | %8s%8s"%('T60','sd','R_RISE',
      'deepen数','超前中位','超前max','首次撞顶槽','duck数','挂陷','频点=top3?'))
    H1,H2=[],[]
    for (T60,sd) in SEEDS:
        h0,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
        hb=band_limit(h0,8000.); he=clrig.h_eff(hb)
        picks=pick_excl(he,BW,8); top3=sorted(round(float(p),1) for p in picks[:3])
        anchor=MSGMeter(he,FS).msg(slots=(),g_duck_db=0.)['full']['msg_db']
        src=1e-3*np.random.default_rng(sd).standard_normal(int(6.0*FS))
        for rr in (18.0,3.0):
            r=run(NHS,hb,D,anchor+3.0,src,rr)
            lead=[x['lead'] for x in r['trace']]
            ts=[x['t'] for x in r['trace']]
            gaps=[(ts[i+1]-ts[i])*1000. for i in range(len(ts)-1) if ts[i+1]>ts[i]]
            H1+=lead; H2+=gaps
            W("%5.1f%4d%7.1f | %8d%9.2f%9.2f | %10s%9d | %8d%8s"%(T60,sd,rr,len(r['trace']),
              np.median(lead) if lead else float('nan'), max(lead) if lead else float('nan'),
              str(r['first_ex']), r['n_duck'], r['slots'],
              str(sorted(r['fr'])==top3 if r['slots']==3 else '-')))
    W("-"*104)
    if H1: W("  Hk1 超前量 |target−depth| 合计 n=%d:中位 **%.2f dB** / p95 %.2f / max %.2f"%(
        len(H1),np.median(H1),np.percentile(H1,95),max(H1)))
    if H2: W("  Hk2 相邻 deepen 间隔 n=%d:中位 **%.1f ms** / p05 %.1f(生效需 %.1f ms)"%(
        len(H2),np.median(H2),np.percentile(H2,5),step_ms))
    W("")
    W("="*104); W("Hk5 · 诊断性反事实(加最小生效守卫)⛔ 非提交修法,其数不得当修法收益引用"); W("="*104)
    W("%5s%4s%7s | %10s%10s | %10s%10s | %8s"%('T60','sd','R_RISE','基线挂陷','守卫挂陷',
      '基线首撞顶','守卫首撞顶','守卫跳过'))
    for (T60,sd) in SEEDS:
        h0,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
        hb=band_limit(h0,8000.); he=clrig.h_eff(hb)
        anchor=MSGMeter(he,FS).msg(slots=(),g_duck_db=0.)['full']['msg_db']
        src=1e-3*np.random.default_rng(sd).standard_normal(int(6.0*FS))
        for rr in (18.0,3.0):
            b=run(NHS,hb,D,anchor+3.0,src,rr); g=run(Guarded,hb,D,anchor+3.0,src,rr)
            W("%5.1f%4d%7.1f | %10d%10d | %10s%10s | %8d"%(T60,sd,rr,b['slots'],g['slots'],
              str(b['first_ex']),str(g['first_ex']),g['ctr'].get('guard_skip',0)))
    W("")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。")
    open('/home/it1234/processor/01_design/prototype_W1P/r71_allocate_coupling_out.txt','w').write("\n".join(O)+"\n")

if __name__=='__main__': main()
