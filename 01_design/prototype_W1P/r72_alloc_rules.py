"""r72 · `_allocate` 现行规则的测量(lead 三问)+ ⭐「加深 vs 开新槽 是否竞争同一资源」直测。
⛔ 未经 critic 评审。[L2/宿主仿真]。输出 r72_alloc_rules_out.txt (D6-j)
deps: nhs.py@31decc8e8d07e085 clrig.py@8ad47ce8d260dd18 r57_bandlimit.py@74036010b514080d

════════════════════════════════════════════════════════════════════
代码事实(先给,再测)—— 回答 lead 的问 ① 与问 ②
════════════════════════════════════════════════════════════════════
```
for h in howls:                                            # ← 循环体是【每个 howl 条目】
    bw   = self._bw_hz(f)                                  #   = max(f * bw_oct, 15.0)
    same = [s for s in slots if s.st != FREE and |s.f − f| <= bw/2]
    if same:  ...加深...; continue                          # ← 该条目【只】做加深
    ...C8 保鲜期...
    free = [FREE 槽]  (无则回收 STANDBY)                    # ← 该条目【只】做开新槽
```
**⇒ 问① 的答案**:判定量 = **`|Δf|` 对 `BW/2`**,而 `BW = max(f·bw_oct, 15 Hz)`
  ⇒ **判定阈值【就是陷波带宽本身】**;`bw_oct = 1/5` 与 15 Hz 下限均 **[L4/待标定]**
  ⇒ **与 C-8b 两门、`R_RISE` 同族(自定数、未标定)⇒ 应进欠账台账。**
  ⚠ **并且它把两件事绑在一起**:改 `bw_oct`(整改队列第 2 项)会**同时改变分配行为**,不只是滤波形状。

**⇒ 问② 的答案(代码层)**:**不竞争。** 循环对**每个 howl 条目**独立处理,
  一个分析槽内可以发生**多次加深 + 多次新分配**,**没有"每槽一次动作"的预算**。
  **⇒ 故 lead 设想的结构性解法(「每槽允许一次加深 + 一次新分配」)【解决不了本缺陷】,
    因为二者本来就都不受限。**
  **⇒ 真正的竞争发生在【被控对象】里**:加深(及撞顶后的 `g_duck`)压低整个环路
    ⇒ 别的峰再也长不到能被检出 ⇒ **新分配不是被"预算"挡住的,是被"没有候选"饿死的。**

════════════════════════════════════════════════════════════════════
预注册(跑前落盘)
════════════════════════════════════════════════════════════════════
Hm1 · **不竞争**(问②):存在同一分析槽内 `deepen ≥1 且 new_alloc ≥1` 的槽。
      证伪:恒不共存 ⇒ 确实存在某种互斥,须回头查(那会推翻上面的代码判读)。
Hm2 · **匹配阈值是否绑定**:`|Δf| / (BW/2)` 的分布。
      若中位 ≪ 1 ⇒ 匹配几乎总是"稳稳落在窗内" ⇒ **阈值不是决定性的**,调它无用;
      若集中在 1 附近 ⇒ 阈值敏感,须标定。
Hm3 · ⭐ **饿死假说(问②的真机理)**:`0.2/sd2` 上 `R_RISE=3` 比 `=18` 少挂 2 个陷波;
      预测:那两个频点(神谕 top-2/top-3)的**旁链电平**在 `g_duck` 介入后**掉到 `T_low=−45` 以下**
      ⇒ 它们连候选都进不去 ⇒ 不是"分配被拒",是"没有候选"。
      证伪:两档下该频点电平几乎相同 ⇒ 饿死假说不成立,须另找机理。
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

def run(hb,D,G,src,rr,watch=()):
    a=NHS(); a.P.bw_oct=BW; a.P.R_RISE=rr
    st={'per':{}, 'ratio':[], 'lv':{f:[] for f in watch}, 'duck_seq':None}
    o_al=a._allocate
    def w_al(howls,M=None,df=None,_o=o_al,_a=a,_s=st):
        seq=_a.slot_seq
        d=n=0
        for h in howls:
            f=h['f']; bw=_a._bw_hz(f)
            same=[s for s in _a.slots if s.st!=NotchSlot.FREE and abs(s.f-f)<=bw/2]
            if same:
                d+=1; _s['ratio'].append(abs(same[0].f-f)/(bw/2))
            else: n+=1
        if d or n:
            p=_s['per'].setdefault(seq,[0,0]); p[0]+=d; p[1]+=n
        # 旁链电平采样(watch 频点)
        if M is not None and df:
            for f in watch:
                k=int(round(f/df))
                if 0<=k<len(M): _s['lv'][f].append((seq, _a._level(M,k)))
        if _s['duck_seq'] is None and _a.g_duck_db<0: _s['duck_seq']=seq
        return _o(howls,M,df)
    a._allocate=w_al
    def pf(b,_a=a): return _a.process_frame(b,GR)
    clrig.Loop(hb,D,G,proc=pf).run(src,FRAME)
    used=[s for s in a.slots if s.st!=NotchSlot.FREE]
    return st, len(used), sorted(round(float(s.f),1) for s in used)

def main():
    P=nhs.Params()
    W("未经 critic 评审 —— r72 · `_allocate` 现行规则 + 加深/开新槽是否竞争   [L2/宿主仿真]")
    W("deps: nhs.py@31decc8e8d07e085 clrig.py@8ad47ce8d260dd18")
    W("问①答:判定量 = |Δf| 对 **BW/2**,BW = max(f·bw_oct, 15Hz);bw_oct=%.4f 与 15Hz 下限均 [L4/待标定]"%P.bw_oct)
    W("        ⇒ 与 C-8b 两门、R_RISE 同族(自定数、未标定)⇒ 应进欠账台账")
    W("        ⚠ 且改 bw_oct(整改队列第 2 项)会**同时改变分配行为**,不只改滤波形状")
    W("问②答(代码层):**不竞争** —— 循环对每个 howl 条目独立处理,一槽内可多次加深+多次新分配,无预算")
    W("")
    W("="*100); W("Hm1 · 同一分析槽内 加深/新分配 是否共存(直测)"); W("="*100)
    W("%5s%4s%7s | %10s%10s%12s%12s"%('T60','sd','R_RISE','有动作槽','仅加深','仅新分配','**两者共存**'))
    co=0
    for (T60,sd) in SEEDS:
        h0,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
        hb=band_limit(h0,8000.); he=clrig.h_eff(hb)
        anchor=MSGMeter(he,FS).msg(slots=(),g_duck_db=0.)['full']['msg_db']
        src=1e-3*np.random.default_rng(sd).standard_normal(int(6.0*FS))
        for rr in (18.0,3.0):
            s,_,_=run(hb,D,anchor+3.0,src,rr)
            per=s['per']; both=sum(1 for v in per.values() if v[0]>0 and v[1]>0)
            od=sum(1 for v in per.values() if v[0]>0 and v[1]==0)
            on=sum(1 for v in per.values() if v[0]==0 and v[1]>0)
            co+=both
            W("%5.1f%4d%7.1f | %10d%10d%12d%12d"%(T60,sd,rr,len(per),od,on,both))
    W("  ⇒ Hm1:两者共存的槽合计 **%d** ⇒ %s"%(co,
      '**不竞争**(代码判读得到实测支持)' if co>0 else '⛔ 恒不共存 ⇒ 存在某种互斥,代码判读须重查'))
    W("")
    W("="*100); W("Hm2 · 匹配阈值 |Δf|/(BW/2) 分布 —— 阈值是不是决定性的"); W("="*100)
    allr=[]
    for (T60,sd) in SEEDS:
        h0,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
        hb=band_limit(h0,8000.); he=clrig.h_eff(hb)
        anchor=MSGMeter(he,FS).msg(slots=(),g_duck_db=0.)['full']['msg_db']
        src=1e-3*np.random.default_rng(sd).standard_normal(int(6.0*FS))
        s,_,_=run(hb,D,anchor+3.0,src,18.0); allr+=s['ratio']
    if allr:
        a=np.array(allr)
        W("  n=%d  中位 **%.4f** / p95 %.4f / max %.4f  (1.0 = 恰在窗边)"%(
          len(a),np.median(a),np.percentile(a,95),a.max()))
        W("  落在 [0.8, 1.0] 的比例 = **%.2f%%**"%(100*np.mean((a>=0.8)&(a<=1.0))))
        W("  ⇒ %s"%('中位 ≪1 ⇒ 匹配稳稳落在窗内 ⇒ **该阈值不是决定性的,调它无用**'
                    if np.median(a)<0.3 else '集中在窗边 ⇒ 阈值敏感,须标定'))
    W("")
    W("="*100); W("Hm3 · ⭐ 饿死假说:0.2/sd2 上少挂的那两个频点,电平掉到 T_low 以下了吗"); W("="*100)
    T60,sd=0.2,2
    h0,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
    hb=band_limit(h0,8000.); he=clrig.h_eff(hb)
    picks=pick_excl(he,BW,8); anchor=MSGMeter(he,FS).msg(slots=(),g_duck_db=0.)['full']['msg_db']
    src=1e-3*np.random.default_rng(sd).standard_normal(int(6.0*FS))
    watch=(float(picks[1]), float(picks[2]))
    W("  被监视频点 = 神谕 top2/top3 = %.1f / %.1f Hz;T_low = %.1f dBFS"%(watch[0],watch[1],P.T_low))
    for rr in (18.0,3.0):
        s,n,fr=run(hb,D,anchor+3.0,src,rr,watch=watch)
        W("  --- R_RISE=%.1f 挂陷 %d @%s   g_duck 首次介入槽 = %s"%(rr,n,fr,s['duck_seq']))
        for f in watch:
            v=[x[1] for x in s['lv'][f]]
            if v:
                W("      @%.1f Hz  电平中位 %.1f / p95 %.1f / max %.1f dBFS  超 T_low 的比例 %.1f%%"%(
                  f,np.median(v),np.percentile(v,95),max(v),100*np.mean(np.array(v)>=P.T_low)))
    W("")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。")
    open('/home/it1234/processor/01_design/prototype_W1P/r72_alloc_rules_out.txt','w').write("\n".join(O)+"\n")

if __name__=='__main__': main()
