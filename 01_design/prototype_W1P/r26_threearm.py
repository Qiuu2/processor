"""r26:三臂拆分 —— 断言与 P0 门各自贡献多少、是否冗余。
臂A 两者全关 / 臂B 只开断言 / 臂C 断言+P0
⚠ r24 双臂的混杂:对照臂里**断言已开**(仪表故障 33/17)⇒ 弃权 29→1 是**断言**干的,不是 P0。
判据重写(架构侧指出 r24 的两个形式缺陷):
  · 原式 `挂陷降幅(%) >= 弃权率降幅(pp)` —— **量纲不同,不可比大小**;
  · 且两者同为 0 时 `0>=0` **无条件打响**。
  ⇒ 改为:两侧都用**绝对计数差**,并加前置门「至少一侧变化 >= 3 例,否则判『无分辨力』」。
[L2/宿主仿真·合成料]
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np, nhs, fp_suite as S
from nhs import NHS, FRAME, NotchSlot
GR={'out_lim_active':False,'out_lim_gr_db':0.0}
OCC=(NotchSlot.ENGAGE,NotchSlot.HOLD,NotchSlot.LIFT,NotchSlot.STANDBY)
DUR=200.0; N=6
ARMS=[('A 全关',False,False),('B 只开断言',True,False),('C 断言+P0',True,True)]
def trial(mk,sd,assert_on,p0_on):
    a=NHS()
    if not assert_on: a.P.pair_read_tol_db=1e9
    if not p0_on: a.P.level_valid_db=-1e9
    mat=mk(DUR,1000+sd); n=(len(mat)//FRAME)*FRAME
    occ=[];b1=[]
    for i in range(0,n,FRAME):
        a.process_frame(mat[i:i+FRAME],GR)
        if i%(FRAME*12)==0 and a.t_wall>=150.0:
            o=[s for s in a.slots if s.st in OCC]
            occ.append(len(o)); b1.append(sum(1 for s in o if s.from_abstain))
    c=a.ctr
    return dict(probe=c.get('c8_probe_started',0),
                ab=sum(1 for r in a.c8_log if r['verdict']=='abstain'),
                ex=sum(1 for r in a.c8_log if r['verdict']=='ext'),
                hw=sum(1 for r in a.c8_log if r['verdict']=='howl'),
                eng=sum(1 for e in a.events if 'engage' in str(e[1])),
                blk=c.get('p0_blocked_novalid',0), flt=c.get('instrument_fault',0),
                occ=np.mean(occ) if occ else 0, b1=np.mean(b1) if b1 else 0,
                blog=list(a.p0_block_log),
                engf=[e[2] for e in a.events if 'engage' in str(e[1])])
print("r26 · 三臂拆分(断言 / P0 各自贡献)")
print(f"[L2/宿主仿真·合成料]  窗={DUR:.0f}s  N={N}\n")
print(f"{'素材':<9}{'臂':<12}{'探针':>6}{'挂陷':>6}{'弃权':>6}{'ext':>6}{'howl':>6}"
      f"{'仪表故障':>9}{'P0拦':>6}{'平台占用':>9}{'b1':>6}")
R={}
for nm,mk in [('钢琴',S.m_piano),('多人交谈',S.m_multitalk)]:
    for lbl,aon,pon in ARMS:
        T={k:0 for k in ['probe','ab','ex','hw','eng','blk','flt']}; O=[];B=[];BL=[];EF=[]
        for sd in range(N):
            r=trial(mk,sd,aon,pon)
            for k in T: T[k]+=r[k]
            O.append(r['occ']);B.append(r['b1']);BL+=r['blog'];EF+=r['engf']
        R[(nm,lbl)]=(T,np.mean(O),np.mean(B),BL,EF)
        print(f"{nm:<9}{lbl:<12}{T['probe']:>6}{T['eng']:>6}{T['ab']:>6}{T['ex']:>6}"
              f"{T['hw']:>6}{T['flt']:>9}{T['blk']:>6}{np.mean(O):>9.2f}{np.mean(B):>6.2f}")
        sys.stdout.flush()
print("\n"+"="*94)
print("【各自贡献 / 是否冗余】(绝对计数差,量纲一致)")
for nm in ['钢琴','多人交谈']:
    A=R[(nm,'A 全关')][0]; B=R[(nm,'B 只开断言')][0]; C=R[(nm,'C 断言+P0')][0]
    print(f"\n  【{nm}】弃权数:A={A['ab']}  B={B['ab']}  C={C['ab']}")
    print(f"     断言单独贡献 = A−B = **{A['ab']-B['ab']}** 例")
    print(f"     P0  边际贡献 = B−C = **{B['ab']-C['ab']}** 例")
    tot=A['ab']-C['ab']
    if tot>0:
        print(f"     合计 {tot} 例;断言占 {(A['ab']-B['ab'])/tot*100:.0f}%,P0 占 {(B['ab']-C['ab'])/tot*100:.0f}%")
    # ★★ r29 判据勘正(R27-5):**冗余 = 在【所有相关指标】上边际贡献均≈0**,
    #   不是在选定的一个指标上。旧判语只看弃权数 ⇒ 而那恰是断言先吃掉的指标。
    #   ⚠ 且"冗余"这个提法本身问错了 —— 两者是**上下游互补**:
    #     P0 减少断言需要处理的对象;断言兜住 P0 漏掉的。
    _O=R[(nm,'A 全关')]; _P=R[(nm,'B 只开断言')]; _Q=R[(nm,'C 断言+P0')]
    _ind=[('平台占用',_P[1],_Q[1],'lower'),('ext',B['ex'],C['ex'],'higher'),
          ('故障孤儿数',B['flt'],C['flt'],'lower'),('挂陷总数',B['eng'],C['eng'],'lower'),
          ('弃权数',B['ab'],C['ab'],'lower')]
    print(f"     ── P0 的边际贡献(B→C),**逐指标**:")
    _n_eff=0
    for _lbl,_b,_c,_dir in _ind:
        _d=_c-_b
        _sig=(abs(_d)>=0.3*max(abs(_b),1e-9)) or (abs(_d)>=3 and _lbl!='平台占用')
        if _sig: _n_eff+=1
        print(f"        {_lbl:<10} {_b:>7.2f} → {_c:>7.2f}  ({_d:+.2f})  "
              f"{'**有显著边际**' if _sig else '≈0'}")
    print(f"     ⇒ **{_n_eff}/{len(_ind)} 项有显著边际贡献** ⇒ "
          + ("**不冗余**(仅在断言先吃掉的那个指标上为 0)" if _n_eff>=2
             else "**各指标均≈0 ⇒ 可议冗余**"))
    print(f"     挂陷:A={A['eng']} B={B['eng']} C={C['eng']}  |  ext:A={A['ex']} B={B['ex']} C={C['ex']}")
    # 重写后的"门过强"判据
    d_eng=B['eng']-C['eng']; d_ab=B['ab']-C['ab']
    if max(abs(d_eng),abs(d_ab))<3:
        v="**无分辨力**(两侧变化均 <3 例,不作判定)"
    elif d_eng>d_ab:
        v=f"**门过强嫌疑**:挂陷少了 {d_eng} 例,弃权只少 {d_ab} 例"
    else:
        v=f"✓ 门未过强(挂陷少 {d_eng},弃权少 {d_ab})"
    print(f"     ② 重写判据(绝对计数,前置门≥3例): {v}")
print("\n"+"="*94)
print("【③ 被 P0 拦下的候选,其实际电平】")
for nm in ['钢琴','多人交谈']:
    BL=R[(nm,'C 断言+P0')][3]; EF=R[(nm,'C 断言+P0')][4]
    if not BL:
        print(f"  {nm}: P0 未拦下任何候选 ⇒ 无样本"); continue
    lv=np.array([r['lv'] for r in BL])
    deg=(lv<=-250).sum()
    print(f"  {nm}: 被拦 {len(BL)} 例  |  电平 <=−250dBFS(退化)= **{deg}/{len(BL)} = {deg/len(BL)*100:.0f}%**")
    print(f"       电平 中位={np.median(lv):.1f}  min={lv.min():.1f}  max={lv.max():.1f}")
    real=[r for r in BL if r['lv']>-250]
    if real:
        print(f"       ⚠ **有真实电平被拦 {len(real)} 例**,max={max(r['lv'] for r in real):.1f}dBFS ⇒ 须查是否过强")
    # 被拦频点后续是否仍被成功挂上
    reeng=0
    for r in BL:
        if any(abs(f-r['f'])<max(r['f']*0.2,15.0)/2 for f in EF): reeng+=1
    print(f"       被拦频点**后续仍被成功挂上** = {reeng}/{len(BL)} = {reeng/len(BL)*100:.0f}%"
          f"  ⇒ {'**只是推迟,不是丢失**' if reeng/len(BL)>0.5 else '多数确实丢失'}")
