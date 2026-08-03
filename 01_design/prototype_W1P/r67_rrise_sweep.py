"""r67 · `R_RISE` 扫描(lead 裁定第 1 项,候选主因)。两阶段:先测可达性,再谈修法。
⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r67.txt(跑前落盘)。
输出 r67_rrise_sweep_out.txt。deps: nhs.py@31decc8e8d07e085 clrig.py@8ad47ce8d260dd18
      howl_detect.py@fd63e901f2d8be33 msg_meter.py@a0c16fd22b29f083 r57_bandlimit.py@74036010b514080d
⛔ 本文件不写结论性散文;唯一判定语句 = 阈值比较与运行时不变量。
"""
import sys, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import pick_excl

GR = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
FRAME, BW, DEPTH, STEP = 64, 1/5, -18.0, 0.5
SEEDS = [(0.2,0),(0.2,1),(0.2,2),(0.5,0),(0.5,1),(0.5,2)]
RRISE = [18.0, 10.0, 6.0, 3.0]
RUNGS = [6.0, 12.0]                 # ⚠ 截断:不跑 24/48,理由见 PREREG_r67 §算力截断
PHASE_A_D = [1.0, 3.0]              # 阶段 A 的固定增益点(相对 anchor)
# r64 基线 m0(同种子同档,proc=None ⇒ 与 R_RISE 无关);用于 He4 复现核对
R64_M0 = {(0.2,0,6.0):-11.85,(0.2,0,12.0):-11.85,(0.2,1,6.0):-12.93,(0.2,1,12.0):-12.93,
          (0.2,2,6.0):-13.08,(0.2,2,12.0):-13.08,(0.5,0,6.0):-12.49,(0.5,0,12.0):-12.49,
          (0.5,1,6.0):-13.75,(0.5,1,12.0):-13.75,(0.5,2,6.0):-12.52,(0.5,2,12.0):-12.52}
O=[]
def W(s=''):
    O.append(s); print(s); sys.stdout.flush()

def mk(rr, ablate):
    a = NHS(); a.P.bw_oct = BW; a.P.R_RISE = rr
    if ablate: a.duck_gain = lambda: 1.0
    return a

def src_of(T, s): return 1e-3*np.random.default_rng(s).standard_normal(int(T*FS))

def sel_axis(fr, picks):
    """§4 选点轴。bw(Hz)=max(f*BW,15);判据 = |Δf| ≤ BW/2。"""
    if not picks: return dict(top1=None, hit=float('nan'), cov=float('nan'), dmin=[])
    def bw(f): return max(f*BW, 15.0)
    top = max(picks, key=lambda p: 0)  # picks 已按 |F| 降序,首个即最高
    top = picks[0]
    top1 = any(abs(f-top) <= bw(top)/2 for f in fr)
    hit = (sum(1 for f in fr if any(abs(f-p) <= bw(p)/2 for p in picks))/len(fr)) if fr else float('nan')
    cov = sum(1 for p in picks if any(abs(f-p) <= bw(p)/2 for f in fr))/len(picks)
    dmin = [round(min(abs(f-p) for p in picks),1) for f in fr]
    return dict(top1=top1, hit=hit, cov=cov, dmin=dmin)

def counted(alg, hb, D, G, src):
    n = {'ro':0, 'gr':0}
    o_im = alg._imsd
    def w(tr, _o=o_im, _n=n):
        r = _o(tr)
        if tr.rapid_onset: _n['ro'] += 1
        if (r[0] or tr.rapid_onset) and not tr.relaxed: _n['gr'] += 1
        return r
    alg._imsd = w
    def pf(blk,_a=alg): return _a.process_frame(blk, GR)
    clrig.Loop(hb, D, G, proc=pf).run(src, FRAME)
    used = [s for s in alg.slots if s.st != nhs.NotchSlot.FREE]
    return n, [round(float(s.f),1) for s in used], alg

def scan(hb, D, mkf, lo, hi, src, ref):
    G, last, st = lo, None, None
    while G <= hi + 1e-9:
        a = mkf(); rec=[]
        pf = None
        if a is not None:
            def pf(blk,_a=a,_r=rec):
                y=_a.process_frame(blk,GR); _r.append(_a.g_duck_db); return y
        _, lp = clrig.Loop(hb, D, G, proc=pf).run(src, FRAME)
        if HD.is_howling(lp, ref, FS, FRAME)[0]:
            return (float('nan') if last is None else last), st
        last = G
        if a is not None:
            u=[s for s in a.slots if s.st!=nhs.NotchSlot.FREE]
            st=dict(n=len(u), n2=int(a.ctr.get('N2_lvl',0)), gmin=float(np.min(rec)) if rec else 0.,
                    fr=sorted(round(float(s.f),1) for s in u),
                    c8e=int(a.ctr.get('c8_ext',0)), c8h=int(a.ctr.get('c8_howl',0)))
        G += STEP
    return float('nan'), st

def main():
    t0=time.time()
    W("未经 critic 评审 —— r67 · R_RISE 扫描(两阶段:先可达性,再 ΔMSG)")
    W("deps: nhs.py@31decc8e8d07e085 clrig.py@8ad47ce8d260dd18 howl_detect.py@fd63e901f2d8be33")
    W("      msg_meter.py@a0c16fd22b29f083 r57_bandlimit.py@74036010b514080d")
    W("[L2/宿主仿真]  预注册 = PREREG_r67.txt")
    W(f"R_RISE ∈ {RRISE}(其余门不动:N_RISE=2 / S_PLAT=2.0 / MIN_PLAT=3)")
    W(f"⚠ **算力截断(显式留痕)**:阶段 B 阶梯截断为 {RUNGS} s,**不跑 24/48**;理由见 PREREG §算力截断")
    W("⚠ 臂 O 本轮不跑(T_low=999 ⇒ 无候选过门 ⇒ R_RISE 对它恒无影响);上界列引用 r64")
    W("")
    env={}
    for (T60,sd) in SEEDS:
        h0,D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
        hb = band_limit(h0, 8000.); he = clrig.h_eff(hb)
        env[(T60,sd)] = (hb, D, he, pick_excl(he,BW,8),
                         MSGMeter(he,FS).msg(slots=(), g_duck_db=0.)['full']['msg_db'])
    W("="*104); W("阶段 A · 可达性(固定增益,不做扫描)—— 门控:触发数为 0 的档不进阶段 B"); W("="*104)
    W("%8s | %6s%4s%6s | %12s%12s%8s" % ('R_RISE','T60','sd','Δ','rapid_onset','GROWTH入选','挂陷'))
    trig = {r:0 for r in RRISE}
    for rr in RRISE:
        for (T60,sd) in SEEDS:
            hb,D,he,picks,anchor = env[(T60,sd)]
            for dl in PHASE_A_D:
                src = src_of(6.0, sd)
                n,fr,_ = counted(mk(rr, False), hb, D, anchor+dl, src)
                trig[rr] += n['ro']
                W("%8.1f | %6.1f%4d%6.1f | %12d%12d%8d" % (rr,T60,sd,dl,n['ro'],n['gr'],len(fr)))
        W("  ── R_RISE=%.1f 合计 rapid_onset 触发 = **%d**  ⇒ %s" % (
            rr, trig[rr], '进阶段 B' if trig[rr]>0 else '**不进阶段 B**(触发为 0)'))
    W("")
    go = [r for r in RRISE if trig[r]>0]
    W("⇒ 阶段 A 门控结果:进阶段 B 的档 = %s" % (go if go else '**空 —— 四档全 0,He1 被证伪**'))
    W("")
    if not go:
        W("="*104); W("阶段 B 未执行(阶段 A 门控);按 PREREG He1 证伪分支,须回头查 N_RISE。"); W("="*104)
    else:
        W("="*104); W("阶段 B · ΔMSG 同档配对 + §4 选点轴 + 误报侧"); W("="*104)
        W("%7s%6s%4s%6s | %8s%9s%10s | %7s%8s%8s | %6s%7s | %s" % (
          'R_RISE','T60','sd','T_OBS','m0','ΔMSG_有duck','ΔMSG_消融',
          'top1_hit','hit@BW/2','cov','c8ext','c8howl','不变量/挂陷'))
        for rr in ([18.0]+[r for r in go if r!=18.0] if 18.0 not in go else go):
            for (T60,sd) in SEEDS:
                hb,D,he,picks,anchor = env[(T60,sd)]
                for T in RUNGS:
                    src = src_of(T, sd); ref = HD.rms_db(src[:(len(src)//FRAME)*FRAME])
                    m0,_ = scan(hb,D,lambda: None, anchor-3, anchor+4, src, ref)
                    chk = R64_M0.get((T60,sd,T))
                    tag = '' if chk is None else (' m0✅r64' if abs(m0-chk)<1e-9 else ' ⛔m0≠r64(%.2f)'%chk)
                    mn,stn = scan(hb,D,lambda: mk(rr,False), anchor-1, anchor+20, src, ref)
                    ma,sta = scan(hb,D,lambda: mk(rr,True),  anchor-1, anchor+20, src, ref)
                    dn = mn-m0 if np.isfinite(mn) and np.isfinite(m0) else float('nan')
                    da = ma-m0 if np.isfinite(ma) and np.isfinite(m0) else float('nan')
                    ax = sel_axis(stn['fr'] if stn else [], picks)
                    if stn is None: inv='⛔无状态'
                    elif stn['n2']>0 and stn['n']>0: inv='OK'
                    elif np.isfinite(dn) and abs(dn)<=STEP+1e-9: inv='ZERO_ACT'
                    else: inv='⛔FAIL'
                    W("%7.1f%6.1f%4d%6.0f | %8.2f%9.2f%10.2f | %7s%8.2f%8.2f | %6d%7d | %s/%d%s" % (
                      rr,T60,sd,T,m0,dn,da,str(ax['top1']),ax['hit'],ax['cov'],
                      stn['c8e'] if stn else -1, stn['c8h'] if stn else -1,
                      inv, stn['n'] if stn else -1, tag))
            W("")
    W("⚠ 误报侧(主)= 1 − hit@BW/2(挂在非临界点上的陷波 = 纯音质代价零收益)")
    W("⚠ 误报侧(次)= c8ext/c8howl,**已知偏差**:F40.4 实测该探针在深度失稳环路上 30/30 全判外部源")
    W("   ⇒ ⛔ 不拿 c8 单独下结论。")
    W("")
    W("总耗时 %.0f s。⛔ 未经 critic 评审;本文件不含结论性判读。" % (time.time()-t0))
    open('/home/it1234/processor/01_design/prototype_W1P/r67_rrise_sweep_out.txt','w').write("\n".join(O)+"\n")

if __name__ == '__main__':
    main()
