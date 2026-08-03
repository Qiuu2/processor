"""r73 · **惰性机制全清点**(lead 裁定主线)。判据 = 「它一共【动作】过几次」,不是「逻辑对不对」。
⛔ 未经 critic 评审。[L2/宿主仿真]。输出 r73_inertia_census_out.txt (D6-j)
deps: nhs.py@31decc8e8d07e085 clrig.py@8ad47ce8d260dd18 r57_bandlimit.py@74036010b514080d

════════════════════════════════════════════════════════════════════
方法(lead 点名要写进方法本身)
════════════════════════════════════════════════════════════════════
**每个机制报两个数,分开报,不合并:**
```
被求值次数(eval)   = 那段代码被走到几次
动作次数(act)      = 它真的改变了状态几次
```
> **「动作 0 次」与「求值 0 次」是两种完全不同的病:**
> **前者 = 门太严(代码在跑,条件不满足);后者 = 那段代码【根本没被走到】(上游就断了)。**
> **⇒ 只报其一会把两者混为一谈。**
⇒ **D4 问「有没有收益」;本清点问「有没有【发生】」。** 二者不可互相替代。

判读档(跑前写死):
  ⛔ 死       act == 0 且 eval > 0        —— 门在实测分布之外(如 `rapid_onset`)
  ⛔ 不可达   eval == 0                    —— 上游断路,该段从未被走到
  ⚠ 近惰性   0 < act/eval ≤ 1%
  ✅ 活       act/eval > 1%
⚠ **本清点是【行为】测量,不是【正确性】测量**:一个机制"活"不代表它做对了,
  只代表它发生过。⛔ 不得把"活"读作"有效"。
⛔ 本文件不写结论散文。
"""
import sys, numpy as np
sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import clrig, nhs
from nhs import NHS, NotchSlot
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
GR={'out_lim_active':False,'out_lim_gr_db':0.0}
FRAME,BW=64,1/5
SEEDS=[(0.2,0),(0.2,1),(0.2,2),(0.5,0),(0.5,1),(0.5,2)]
DELTAS=[1.0,3.0]
O=[]
def W(s=''):
    O.append(s); print(s); sys.stdout.flush()

def census(hb,D,G,src):
    a=NHS(); a.P.bw_oct=BW
    c={k:0 for k in ('cls_eval','cls_panic','cls_growth','cls_persist','cls_none',
                     'ro_eval','ro_act','veto_call','veto_true','relax_eval','relax_act',
                     'alloc_h','alloc_deep','alloc_new')}
    o_im,o_vt,o_al = a._imsd, a._phpr_veto, a._allocate
    def w_im(tr,_o=o_im,_c=c,_a=a):
        _c['cls_eval']+=1
        if len(tr.papr_hist)>=_a.P.MIN_PLAT+1: _c['ro_eval']+=1
        if tr.rapid_onset: _c['ro_act']+=1
        return _o(tr)
    def w_vt(*x,_o=o_vt,_c=c):
        _c['veto_call']+=1; r=_o(*x)
        if r: _c['veto_true']+=1
        return r
    def w_al(howls,M=None,df=None,_o=o_al,_c=c,_a=a):
        _c['alloc_h']+=len(howls)
        for h in howls:
            bw=_a._bw_hz(h['f'])
            if [s for s in _a.slots if s.st!=NotchSlot.FREE and abs(s.f-h['f'])<=bw/2]:
                _c['alloc_deep']+=1
            else: _c['alloc_new']+=1
        return _o(howls,M,df)
    a._imsd,a._phpr_veto,a._allocate = w_im,w_vt,w_al
    def pf(b,_a=a): return _a.process_frame(b,GR)
    clrig.Loop(hb,D,G,proc=pf).run(src,FRAME)
    c.update({('ctr_'+k):v for k,v in a.ctr.items() if isinstance(v,(int,np.integer))})
    return c

def main():
    W("未经 critic 评审 —— r73 · 惰性机制全清点(动作次数 / 被求值次数,分开报)  [L2/宿主仿真]")
    W("deps: nhs.py@31decc8e8d07e085 clrig.py@8ad47ce8d260dd18")
    W("判读档:⛔死 = act==0 ∧ eval>0(门太严) | ⛔不可达 = eval==0(上游断路) | ⚠近惰性 ≤1% | ✅活 >1%")
    W("⚠ 本清点测【行为】不测【正确性】:『活』不等于『有效』。")
    W("")
    T={}
    for (T60,sd) in SEEDS:
        h0,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
        hb=band_limit(h0,8000.); he=clrig.h_eff(hb)
        anchor=MSGMeter(he,FS).msg(slots=(),g_duck_db=0.)['full']['msg_db']
        src=1e-3*np.random.default_rng(sd).standard_normal(int(6.0*FS))
        for dl in DELTAS:
            c=census(hb,D,anchor+dl,src)
            for k,v in c.items(): T[k]=T.get(k,0)+v
    g=lambda k: T.get(k,0)
    ROWS=[
     ('候选提取:局部极大→top-16',            'ctr_N1_cand','ctr_N0_locmax'),
     ('电平门 T_low(候选过门)',              'ctr_N2_lvl','ctr_N1_cand'),
     ('窄带门 PAPR∧PNPR',                     'ctr_N3_gate','ctr_N2_lvl'),
     ('建轨 N4_born',                          'ctr_N4_born','ctr_N3_gate'),
     ('⭐ rapid_onset(臂2 快升签名)',        'ro_act','ro_eval'),
     ('⭐ PHPR 否决',                          'veto_true','veto_call'),
     ('分类:PANIC',                           'cls_panic','cls_eval'),
     ('分类:产出 howl(N5)',                 'ctr_N5_howl','cls_eval'),
     ('分配:加深已有槽',                      'alloc_deep','alloc_h'),
     ('分配:开新槽',                          'alloc_new','alloc_h'),
     ('分配:成功入槽 n_carried',              'ctr_n_carried','alloc_new'),
     ('分配:抢占 preempt',                    'ctr_preempt','alloc_new'),
     ('分配:被阻 n_blocked',                  'ctr_n_blocked','alloc_new'),
     ('槽位耗尽 SLOTS_EXHAUSTED',              'ctr_slots_exhausted','alloc_new'),
     ('深度撞顶 DEPTH_EXHAUSTED',              'ctr_depth_exhausted','alloc_deep'),
     ('C8-② 探针:启动',                      'ctr_c8_probe_started','ctr_n_carried'),
     ('C8-② 探针:判外部源(撤陷)',          'ctr_c8_ext','ctr_c8_probe_started'),
     ('C8-② 探针:判啸叫',                    'ctr_c8_howl','ctr_c8_probe_started'),
     ('C8-② 探针:弃权',                      'ctr_c8_abstain','ctr_c8_probe_started'),
     ('C8 保鲜期抑制挂陷',                     'ctr_c8_suppressed','alloc_new'),
     ('影子表:新建',                          'ctr_shadow_new','ctr_N4_born'),
     ('影子表:继承',                          'ctr_shadow_inherit','ctr_N4_born'),
     ('空号护栏 gapguard',                     'ctr_gapguard','ctr_N4_born'),
     ('未观测计数 unobs',                      'ctr_unobs','cls_eval'),
     ('LIFT 观测 / 回归',                      'ctr_lift_return','ctr_lift_obs'),
     ('候选表满 table_full',                   'ctr_table_full','ctr_slots'),
    ]
    W("%-34s %10s %10s %9s  %s"%('机制','动作(act)','求值(eval)','act/eval','判读'))
    W("-"*96)
    dead=[]; unreach=[]; near=[]
    for name,ka,ke in ROWS:
        act,ev=g(ka),g(ke)
        if ev==0: v='⛔不可达(eval=0)'; unreach.append(name)
        elif act==0: v='⛔死(门太严)'; dead.append(name)
        else:
            r=act/ev
            if r<=0.01: v='⚠近惰性'; near.append((name,r))
            else: v='✅活'
        W("%-34s %10d %10d %9s  %s"%(name,act,ev,
          ('%.4f'%(act/ev)) if ev else 'n/a', v))
    W("-"*96)
    W("")
    W("⇒ **⛔死(act=0 而 eval>0,门太严)共 %d 条**:%s"%(len(dead),dead))
    W("⇒ **⛔不可达(eval=0,上游断路)共 %d 条**:%s"%(len(unreach),unreach))
    W("⇒ **⚠近惰性(≤1%%)共 %d 条**:%s"%(len(near),[(n,'%.4f'%r) for n,r in near]))
    W("")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。")
    open('/home/it1234/processor/01_design/prototype_W1P/r73_inertia_census_out.txt','w').write("\n".join(O)+"\n")

if __name__=='__main__': main()
