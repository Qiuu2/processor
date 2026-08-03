"""r70 · ②③ 可达性门控 + **下游三候选定位**(lead 裁定:先测,再谈修)。
⛔ 未经 critic 评审。[L2/宿主仿真]。输出 r70_gate_downstream_out.txt (D6-j)
deps: nhs.py@31decc8e8d07e085 clrig.py@8ad47ce8d260dd18 r57_bandlimit.py@74036010b514080d

════════════════════════════════════════════════════════════════════
预注册(跑前落盘)
════════════════════════════════════════════════════════════════════
**Part 1 · ②③ 门控**——问「换成原文形式后,候选门的【判定】会不会改变」。
  静态口径:在**同一批谱、同一批候选**上同时算旧式与新式,数**判定翻转**次数。
  ②`_papr_jaes` = 式(6)(7):`10log10( |Y_k|² / mean_j(|Y_j|²) )` = 峰值功率 / 平均 bin 功率
     ⚠ **二义(我方选择,须留痕)**:原文 `M` = DFT 长(1024,双边);我方谱为**单边 513 bin**。
       本实现用**单边 513 bin 求均值** ⇒ 上限 = `10log10(513) = 27.10 dB`;
       门取「与原文同一相对位置」= 上限 − 1.12 = **25.98 dB**
       (原文 M=4096 时上限 36.12、ROC 最优 35.00 ⇒ 差 1.12)。
       ⇒ **同时打印 PAPR_jaes 的分布**,使任何门值下的翻转数都可推。
  ③`_pnpr_jaes` = 式(9)+AND:`min_{m∈{±2,±3,±4}} 20log10(|Y_k|/|Y_{k+m}|) ≥ T_PNPR=8 dB`
  Hg1 判定翻转数 = 0 ⇒ 该改法在本工作点集上**不可达** ⇒ 不进阶段 B(与 r66b/r67 同门控)。
  Hg2 翻转数 > 0 ⇒ 报**翻转方向**(旧过新否 / 旧否新过)与净变化。

**Part 2 · 下游三候选**(lead 点名,先测不修):
  候选 A `_phpr_veto` 否决:调用数 / 否决数 / 否决率
  候选 B `NT=12` 轨表:活跃轨峰值 / table_full / n_blocked
  候选 C `_allocate` 仲裁:入参 howls 数 / n_carried / slots_exhausted / preempt / p0_blocked
  **切入点 = `0.2/sd2` 的负相关**(R_RISE 18→3:分类 23→12、挂陷 3→1)——逐环节打点,看在哪一节掉的。
  Hg3 若掉在 A(否决数随 R_RISE 下降而升)⇒ 多出来的 GROWTH 被 PHPR 吃掉;
  Hg4 若掉在 C(howls 数升而 n_carried 不升)⇒ 卡在分配/仲裁;
  Hg5 若 B 从未接近满(r66c 旁证:峰值 5/12)⇒ 轨表容量**不是**瓶颈,如实排除。
⛔ 本文件不写结论散文。
"""
import sys, numpy as np
sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import clrig, nhs
from nhs import NHS, FS_SC, NFFT
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
GR={'out_lim_active':False,'out_lim_gr_db':0.0}
FRAME,BW = 64,1/5
SEEDS=[(0.2,0),(0.2,1),(0.2,2),(0.5,0),(0.5,1),(0.5,2)]
T_PNPR_J, MSET = 8.0, (-4,-3,-2,2,3,4)
O=[]
def W(s=''):
    O.append(s); print(s); sys.stdout.flush()

def papr_jaes(M,k):
    p=M.astype(float)**2
    return 10*np.log10(p[k]/(p.mean()+1e-300)+1e-300)
def pnpr_jaes(M,k):
    v=[]
    for m in MSET:
        j=k+m
        if 0<=j<len(M): v.append(20*np.log10(M[k]/(M[j]+1e-30)+1e-30))
    return min(v) if v else 0.0

def probe(alg, hb, D, G, src):
    P=alg.P
    rec={'pairs':[], 'veto_call':0,'veto_true':0,'howls':0,'ntr':0,'entry':0}
    o_pa,o_pn,o_vt,o_al,o_im = alg._papr, alg._pnpr, alg._phpr_veto, alg._allocate, alg._imsd
    box={'M':None,'k':None,'pa':None}
    def w_pa(M,k,_o=o_pa,_b=box):
        _b['M'],_b['k']=M,k; v=_o(M,k); _b['pa']=v; return v
    def w_pn(M,k,_o=o_pn,_b=box,_r=rec):
        v=_o(M,k)
        _r['pairs'].append((_b['pa'],v,papr_jaes(M,k),pnpr_jaes(M,k)))
        return v
    def w_vt(*a,_o=o_vt,_r=rec):
        _r['veto_call']+=1; r=_o(*a)
        if r: _r['veto_true']+=1
        return r
    def w_al(howls,*a,_o=o_al,_r=rec):
        _r['howls']+=len(howls); return _o(howls,*a)
    def w_im(tr,_o=o_im,_r=rec):
        r=_o(tr)
        if (r[0] or tr.rapid_onset) and not tr.relaxed: _r['entry']+=1
        return r
    alg._papr,alg._pnpr,alg._phpr_veto,alg._allocate,alg._imsd = w_pa,w_pn,w_vt,w_al,w_im
    def pf(b,_a=alg,_r=rec):
        y=_a.process_frame(b,GR)
        _r['ntr']=max(_r['ntr'],sum(1 for t in _a.tracks if t.active)); return y
    clrig.Loop(hb,D,G,proc=pf).run(src,FRAME)
    rec['slots']=len([s for s in alg.slots if s.st!=nhs.NotchSlot.FREE])
    rec['ctr']=dict(alg.ctr)
    return rec

def main():
    P=nhs.Params()
    CEIL=10*np.log10((NFFT//2)+1); T_PAPR_J=CEIL-1.12
    W("未经 critic 评审 —— r70 · ②③ 门控 + 下游三候选定位   [L2/宿主仿真]")
    W("deps: nhs.py@31decc8e8d07e085 clrig.py@8ad47ce8d260dd18")
    W("旧门:T_papr=%.1f T_pnpr=%.1f  |  新门:T_papr_jaes=%.2f(上限 %.2f −1.12) T_pnpr_jaes=%.1f 邻元%s"
      % (P.T_papr,P.T_pnpr,T_PAPR_J,CEIL,T_PNPR_J,list(MSET)))
    W("")
    env={}
    for (T60,sd) in SEEDS:
        h0,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
        hb=band_limit(h0,8000.); he=clrig.h_eff(hb)
        env[(T60,sd)]=(hb,D,MSGMeter(he,FS).msg(slots=(),g_duck_db=0.)['full']['msg_db'])
    W("="*112); W("Part 1 · ②③ 门控(静态,同一批谱同一批候选上算两套公式,数【判定翻转】)"); W("="*112)
    W("%5s%4s%6s | %8s | %10s%10s%10s | %10s%10s%10s"%('T60','sd','Δ','门前候选',
      '②旧过','②新过','②翻转','③旧过','③新过','③翻转'))
    A=dict(n=0,po=0,pn=0,pf=0,qo=0,qn=0,qf=0)
    allp=[]
    for (T60,sd) in SEEDS:
        hb,D,anchor=env[(T60,sd)]
        for dl in (1.0,3.0):
            a=NHS(); a.P.bw_oct=BW
            src=1e-3*np.random.default_rng(sd).standard_normal(int(6.0*FS))
            r=probe(a,hb,D,anchor+dl,src)
            pr=r['pairs']; allp+=pr
            po=sum(1 for x in pr if x[0]>=P.T_papr); pn=sum(1 for x in pr if x[2]>=T_PAPR_J)
            pf=sum(1 for x in pr if (x[0]>=P.T_papr)!=(x[2]>=T_PAPR_J))
            qo=sum(1 for x in pr if x[1]>=P.T_pnpr); qn=sum(1 for x in pr if x[3]>=T_PNPR_J)
            qf=sum(1 for x in pr if (x[1]>=P.T_pnpr)!=(x[3]>=T_PNPR_J))
            for k,v in (('n',len(pr)),('po',po),('pn',pn),('pf',pf),('qo',qo),('qn',qn),('qf',qf)):
                A[k]+=v
            W("%5.1f%4d%6.1f | %8d | %10d%10d%10d | %10d%10d%10d"%(T60,sd,dl,len(pr),po,pn,pf,qo,qn,qf))
    W("-"*112)
    W("%5s%10s | %8d | %10d%10d%10d | %10d%10d%10d"%('合计','',A['n'],A['po'],A['pn'],A['pf'],A['qo'],A['qn'],A['qf']))
    pj=np.array([x[2] for x in allp]); qj=np.array([x[3] for x in allp])
    W("  PAPR_jaes 分布:max %.2f / p99 %.2f / p95 %.2f / 中位 %.2f dB(门 %.2f)"%(
      pj.max(),np.percentile(pj,99),np.percentile(pj,95),np.median(pj),T_PAPR_J))
    W("  PNPR_jaes 分布:max %.2f / p99 %.2f / p95 %.2f / 中位 %.2f dB(门 %.1f)"%(
      qj.max(),np.percentile(qj,99),np.percentile(qj,95),np.median(qj),T_PNPR_J))
    W("  ⇒ Hg1/Hg2:② 翻转 **%d** / ③ 翻转 **%d**  ⇒ %s"%(A['pf'],A['qf'],
      '两者皆 0 ⇒ 均不可达,不进阶段 B' if A['pf']==0 and A['qf']==0 else '有翻转,详见上表'))
    W("")
    W("="*112); W("Part 2 · 下游三候选(A=PHPR否决 / B=NT轨表 / C=_allocate 仲裁)"); W("="*112)
    W("%5s%4s%7s | %7s%9s%9s%8s | %7s%7s | %8s%9s%9s%8s"%('T60','sd','R_RISE',
      '入选式','A:否决调用','A:否决数','A:否决率','B:轨峰','B:候选表满_非轨表','C:howls','C:carried','C:exhaust','挂陷'))
    for (T60,sd) in SEEDS:
        hb,D,anchor=env[(T60,sd)]
        for rr in (18.0,3.0):
            a=NHS(); a.P.bw_oct=BW; a.P.R_RISE=rr
            src=1e-3*np.random.default_rng(sd).standard_normal(int(6.0*FS))
            r=probe(a,hb,D,anchor+3.0,src); c=r['ctr']
            vr=(r['veto_true']/r['veto_call']) if r['veto_call'] else float('nan')
            W("%5.1f%4d%7.1f | %7d%9d%9d%8.2f | %7d%7d | %8d%9d%9d%8d"%(
              T60,sd,rr,r['entry'],r['veto_call'],r['veto_true'],vr,
              r['ntr'],c.get('table_full',0),r['howls'],c.get('n_carried',0),
              c.get('slots_exhausted',0),r['slots']))
    W("")
    W("⚠ B 列旁证(r66c):活跃轨峰值 5/12 ⇒ 轨表容量先验较低,但照测(Hg5)。")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。")
    open('/home/it1234/processor/01_design/prototype_W1P/r70_gate_downstream_out.txt','w').write("\n".join(O)+"\n")

if __name__=='__main__': main()
