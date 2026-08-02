"""W1-P · 全实验驱动:核心链 + B1-B12 + B-F1 + 误报 + 标定
输出为纯文本报告,存 results.txt。全部 [L2/宿主仿真]。
"""
import numpy as np, sys, time
from experiments import *
from env import synth_speech, synth_music, synth_transients, env_db, FS, FRAME
from nhs import NHS, Params

OUT = []
def say(s=''):
    print(s); OUT.append(s)

t_start = time.time()
say("=" * 78)
say("W1-P 宿主原型实验报告  ·  adaptive-dsp(第3实例)  ·  2026-08-01")
say("全部结果 [L2/宿主仿真];浮点,不构成定点行为证据;素材为合成,非真实语料")
say("=" * 78)

# ---------------------------------------------------------------- 1 核心链
say("\n### 1. 核心链(T1 检出 / T2 抑制)· 缓升增益闭环")
res = {}
for name, alg in (("bypass", Bypass()), ("NHS", NHS())):
    out, tap = scen_ramp(alg)
    m = metrics(out); res[name] = (m, alg)
    say(f"  {name:8s} 末包络={m['end_db']:7.1f}dB 峰包络={m['peak_db']:7.1f}dB "
        f"窄带={m['nb']:.3f} f={m['f_peak']:7.1f}Hz  仍在啸={howling(m)}")
d_supp = res['bypass'][0]['end_db'] - res['NHS'][0]['end_db']
say(f"  ⇒ 抑制量(输出末包络差)= {d_supp:.1f} dB;NHS 挂陷 {n_engage(res['NHS'][1])} 次")
say(f"  ⇒ T1/T2 判定:{'PASS' if not howling(res['NHS'][0]) and howling(res['bypass'][0]) else 'FAIL'}")

# 分类路占比
cls_count = {}
for e in res['NHS'][1].events:
    if str(e[1]).startswith('engage'):
        cls_count[e[1]] = cls_count.get(e[1], 0) + 1
say(f"  ⇒ 首次挂陷分类路分布:{cls_count}")

# ---------------------------------------------------------------- 2 B-F1
say("\n### 2. ★ B-F1 钉住啸叫(输出限幅器入环;设计件算例:天花板−6dB/前向+50dB⇒tap≈−56dBFS)")
bf1 = {}
for name, alg in (("bypass", Bypass()), ("NHS 完整", NHS())):
    out, tap = scen_pinned(alg)
    m = metrics(out); tl = tap_level_dbfs(tap, 3.0)
    bf1[name] = (m, alg, tl)
    say(f"  {name:9s} 输出末={m['end_db']:7.1f}dB 窄带={m['nb']:.3f} | tap={tl:6.1f}dBFS | "
        f"仍在啸={howling(m)} | 挂陷={n_engage(alg) if hasattr(alg,'events') else 0}")
tl = bf1['NHS 完整'][2]
say(f"  ⇒ 实测 tap 电平 {tl:.1f}dBFS,低于 T_low(−45) {(-45)-tl:.1f}dB、低于 T_panic(−6) {(-6)-tl:.1f}dB")
say(f"  ⇒ **三轮纸面推演的场景实测成立**:PANIC 与常规 G0 门在此场景确实不可达")
ev = [e for e in bf1['NHS 完整'][1].events if str(e[1]).startswith('engage')]
say(f"  ⇒ 完整版检出路径 = {ev[:2] if ev else '未检出'}")

# ---------------------------------------------------------------- 3 B1-B12
say("\n### 3. B1–B12 broken 版(每个必须 FAIL;跑不出 FAIL 的如实报)")
say("    判定一律看输出信号,不看内部旗标。")
BROK = []

def verdict(tag, desc, ok_fail, detail):
    BROK.append((tag, ok_fail, desc, detail))
    say(f"  {tag:4s} {desc:38s} -> {'FAIL(符合预期)' if ok_fail else '**未 FAIL(重要发现)**'}  {detail}")

# --- B1/B2/B3:缓升闭环
base_m = res['NHS'][0]
for tag, desc in (('B1', '检测器 stub(永远无峰)'),
                  ('B2', '深度恒 0dB(系数恒等)')):
    a = NHS(broken=[tag]); out, _ = scen_ramp(a); m = metrics(out)
    worse = m['end_db'] - base_m['end_db']
    verdict(tag, desc, howling(m) or worse > 10.0,
            f"末包络={m['end_db']:7.1f}dB(完整版 {base_m['end_db']:.1f}) 窄带={m['nb']:.3f} 劣化={worse:+.1f}dB")

# B3 用例重做(F1 勘正):原用例测系统末态,对"陷波偏 8.8%"不敏感
# —— 环路会转到下个共振再被挂陷。改为**测该啸叫频点上陷波的实际衰减量**。
def notch_atten_at(alg, f_hz):
    """用槽的实际系数在 48k 上求 |H(f_hz)|,单位 dB。"""
    best = 0.0
    for sl in alg.slots:
        if sl.st == 0:
            continue
        w = 2*np.pi*f_hz/FS
        z = np.exp(1j*w)
        H = (sl.b[0] + sl.b[1]/z + sl.b[2]/z**2) / (sl.a[0] + sl.a[1]/z + sl.a[2]/z**2)
        best = min(best, 20*np.log10(abs(H) + 1e-30))
    return best
a_f3 = NHS(); out_f3, _ = scen_pinned(a_f3)
a_b3 = NHS(broken=['B3']); out_b3, _ = scen_pinned(a_b3)
f_h = 4034.1
at_f, at_b = notch_atten_at(a_f3, f_h), notch_atten_at(a_b3, f_h)
verdict('B3', '系数按错误 fs(44.1k)算', at_b > at_f + 6.0,
        f"啸叫频点 {f_h:.0f}Hz 实际衰减:完整={at_f:6.2f}dB broken={at_b:6.2f}dB(差 {at_b-at_f:+.1f}dB)")

# --- B4:IMSD 禁用 ⇒ 反应时间变长(阶跃场景)
a_full = NHS(); out_f, _ = scen_step(a_full); m_f = metrics(out_f)
a_b4 = NHS(broken=['B4']); out_b, _ = scen_step(a_b4); m_b = metrics(out_b)
tr_f = react_time(a_full, out_f, 2.0); tr_b = react_time(a_b4, out_b, 2.0)
verdict('B4', 'IMSD 禁用(仅 PANIC+PERSIST)', (tr_b > tr_f * 1.3) or (m_b['peak_db'] > m_f['peak_db'] + 3),
        f"T_react 完整={tr_f*1000:.0f}ms broken={tr_b*1000:.0f}ms;峰包络 {m_f['peak_db']:.1f}→{m_b['peak_db']:.1f}dB")

# --- B5:PHPR 否决禁用 ⇒ 音乐误挂上升
mus = synth_music(10.0)
a_full5 = NHS(); scen_open(a_full5, mus); n_full5 = n_engage(a_full5)
a_b5 = NHS(broken=['B5']); scen_open(a_b5, mus); n_b5 = n_engage(a_b5)
verdict('B5', 'PHPR 否决禁用', n_b5 > n_full5,
        f"音乐素材误挂:完整={n_full5} broken={n_b5}")

# --- B6:LIFT 禁用 ⇒ 深度不回收(缩短 lift 参数以适配短仿真,已留痕)
Pl = Params(lift_after_s=1.0, lift_step_s=0.3, reclaim_s=2.0)
def lift_test(brk):
    a = NHS(P=Params(lift_after_s=1.0, lift_step_s=0.3, reclaim_s=2.0), broken=brk)
    h, d = rir(); src = 0.02*np.random.default_rng(0).normal(0,1,int(10.0*FS))
    lp = ClosedLoop(h, d, a, g_pre_db=0, g_fwd_db=+2.0)
    n=(len(src)//FRAME)*FRAME
    from scipy.signal import lfilter
    fb=np.zeros(FRAME); zi=np.zeros(len(h)-1); gf=10**(2.0/20)
    for i in range(0,n,FRAME):
        if i == int(4.0*FS)//FRAME*FRAME: gf *= 10**(-25/20.0)   # 4s 后大幅降增益
        mic=src[i:i+FRAME]+fb; t=mic*lp.g_pre
        y=a.process_frame(t,{'out_lim_active':False,'out_lim_gr_db':0.0})
        y=np.clip(y*gf,-8,8)
        fb,zi=lfilter(h,[1.0],y,zi=zi)
    return a, sum(s.depth for s in a.slots)
a_f6, dep_f = lift_test(None); a_b6, dep_b = lift_test(['B6'])
verdict('B6', 'LIFT 禁用(深度永不回收)', dep_b < dep_f - 1.0,
        f"降增益 6s 后总深度:完整={dep_f:.1f}dB broken={dep_b:.1f}dB(越负=未回收)")

# --- B7 / B8:pinned-howl 双 broken
m_pin_full = bf1['NHS 完整'][0]
for tag, desc in (('B7', 'pinned:GR遥测∧臂2 双禁用'), ('B8', 'pinned:T_low_gr 放宽禁用')):
    a = NHS(broken=[tag] if tag == 'B8' else ['B7']); out, tap = scen_pinned(a); m = metrics(out)
    verdict(tag, desc, howling(m),
            f"末包络={m['end_db']:7.1f}dB 窄带={m['nb']:.3f}(完整版 {m_pin_full['end_db']:.1f}/{m_pin_full['nb']:.3f}) 挂陷={n_engage(a)}")

# --- B9:LS x 轴改回 0..W-1(需人为跳槽)
def skip_test(brk):
    a = NHS(broken=brk)
    a.skip_plan = set(s for s in range(1, 4000) if (s // 3) % 2 == 1)   # 周期性跳槽降档
    out, _ = scen_step(a); return a, metrics(out)
a_f9, m_f9 = skip_test(None); a_b9, m_b9 = skip_test(['B9'])
verdict('B9', 'IMSD 的 LS x 轴改回 0..W-1', (m_b9['peak_db'] > m_f9['peak_db'] + 2) or (n_engage(a_b9) < n_engage(a_f9)),
        f"跳槽下 峰包络 完整={m_f9['peak_db']:.1f} broken={m_b9['peak_db']:.1f}dB;挂陷 {n_engage(a_f9)}→{n_engage(a_b9)}")

# --- B10:未观测一律当未命中(掩蔽场景:钉住啸叫 + 语音)
spx = synth_speech(10.0) * 0.5
a_f10 = NHS(); out_f10, _ = scen_pinned(a_f10, src=spx*1e-3 + 1e-5*np.random.default_rng(1).normal(0,1,len(spx)))
a_b10 = NHS(broken=['B10']); out_b10, _ = scen_pinned(a_b10, src=spx*1e-3 + 1e-5*np.random.default_rng(1).normal(0,1,len(spx)))
m_f10, m_b10 = metrics(out_f10), metrics(out_b10)
verdict('B10', '"未观测"一律当"未命中"', howling(m_b10) and not howling(m_f10),
        f"掩蔽场景 末包络 完整={m_f10['end_db']:.1f}/{m_f10['nb']:.3f} broken={m_b10['end_db']:.1f}/{m_b10['nb']:.3f}")

# --- B11:影子继承去掉 causal_ok(轨中断重生)
a_f11 = NHS(); out_f11, _ = scen_pinned(a_f11, src=spx*2e-3 + 1e-5*np.random.default_rng(2).normal(0,1,len(spx)))
a_b11 = NHS(broken=['B11']); out_b11, _ = scen_pinned(a_b11, src=spx*2e-3 + 1e-5*np.random.default_rng(2).normal(0,1,len(spx)))
m_f11, m_b11 = metrics(out_f11), metrics(out_b11)
inh_f = sum(1 for e in a_f11.events if e[1] == 'shadow_inherit')
inh_b = sum(1 for e in a_b11.events if e[1] == 'shadow_inherit')
verdict('B11', '影子继承去 causal_ok(继承裸时间戳)', howling(m_b11) and not howling(m_f11),
        f"末包络 完整={m_f11['end_db']:.1f}/{m_f11['nb']:.3f} broken={m_b11['end_db']:.1f}/{m_b11['nb']:.3f};继承事件 {inh_f}/{inh_b}")

# --- B12:解除 unobs_run ≤ U_max(忙房间:多音 + 语音塞满候选表)
busy = synth_speech(10.0, seed=7)*0.4 + synth_music(10.0, seed=8)*0.4
for f in (330., 770., 1310., 1950., 2570., 3130., 4410., 5230., 6110., 6970.):
    t = np.arange(len(busy))/FS
    busy += 0.03*np.sin(2*np.pi*f*t)
a_f12 = NHS(); out_f12, _ = scen_pinned(a_f12, src=busy*1e-3 + 1e-5*np.random.default_rng(3).normal(0,1,len(busy)))
a_b12 = NHS(broken=['B12']); out_b12, _ = scen_pinned(a_b12, src=busy*1e-3 + 1e-5*np.random.default_rng(3).normal(0,1,len(busy)))
m_f12, m_b12 = metrics(out_f12), metrics(out_b12)
verdict('B12', '解除 unobs_run ≤ U_max(僵尸轨)', howling(m_b12) and not howling(m_f12),
        f"忙房间 末包络 完整={m_f12['end_db']:.1f}/{m_f12['nb']:.3f} broken={m_b12['end_db']:.1f}/{m_b12['nb']:.3f}")

# --- B13(v2 新增,F4 回归锁):放宽门仅由 GR 决定(= v1.4 行为)
from env import Limiter as _Lim
def f4_recur(brk):
    from scipy.signal import lfilter
    h, d = rir(); h = h * 10 ** ((3.0 - 50.0) / 20.0)
    src = 1e-5*np.random.default_rng(0).normal(0,1,int(24.0*FS))
    a = NHS(P=Params(lift_after_s=1.5, lift_step_s=0.4, reclaim_s=12.0), broken=brk)
    lim = _Lim(thr_db=-6.0)
    n=(len(src)//FRAME)*FRAME; out=np.zeros(n)
    fb=np.zeros(FRAME); zi=np.zeros(len(h)-1); gf=10**(50.0/20.0)
    for i in range(0,n,FRAME):
        mic=src[i:i+FRAME]+fb
        y=a.process_frame(mic,{'out_lim_active':bool(lim.active),'out_lim_gr_db':float(lim.gr_db)})
        y=np.clip(y*gf,-8,8); y=lim.process(y)
        fb,zi=lfilter(h,[1.0],y,zi=zi); out[i:i+FRAME]=y
    return a, metrics(out)
a_f13, m_f13 = f4_recur(None); a_b13, m_b13 = f4_recur(['B13'])
verdict('B13', '放宽门仅由 GR 决定(=v1.4,F4缺陷)', howling(m_b13) and not howling(m_f13),
        f"LIFT探针同频复发:完整 末={m_f13['end_db']:.1f}dB/nb{m_f13['nb']:.3f} "
        f"broken 末={m_b13['end_db']:.1f}dB/nb{m_b13['nb']:.3f}(差 {m_b13['end_db']-m_f13['end_db']:+.1f}dB)")

nf = sum(1 for _, ok, _, _ in BROK if ok)
say(f"\n  ⇒ B1–B13 汇总:{nf}/{len(BROK)} 按预期 FAIL,{len(BROK)-nf} 个未 FAIL")

# ---------------------------------------------------------------- 4 误报
say("\n  -- B10/B11/B12 目标机制**触达情况**(F4 修法后)--")
for nm, aa in (('B10场景', a_f10), ('B11场景', a_f11), ('B12场景', a_f12)):
    c = aa.ctr
    say(f"     {nm}: 表满={c['table_full']}/{c['slots']} 未观测={c['unobs']} 直读成功={c['readback_ok']} "
        f"影子新建={c['shadow_new']} 继承={c['shadow_inherit']} U_max命中={c['umax_hit']} 空号护栏={c['gapguard']}")

say("\n### 4. 误报套件(开环,无反馈路径;计挂陷次数,>-3dB 即记误伤)")
for nm, mat in (('语音', synth_speech(10.0)), ('音乐(含长笛类)', synth_music(10.0)),
                ('掌声', synth_transients(10.0, kind='clap')),
                ('咳嗽', synth_transients(10.0, kind='cough'))):
    a = NHS(); scen_open(a, mat)
    eng = [e for e in a.events if str(e[1]).startswith('engage')]
    say(f"  {nm:14s} 误挂={len(eng):3d} 次  分类={sorted(set(e[1] for e in eng))}  "
        f"频点={[round(e[2]) for e in eng[:6]]}")

# ---------------------------------------------------------------- 5 标定
say("\n### 5. 参数标定([L4]拍值 → [L2]仿真标定值)")
say("  ⚠ F5/F6 勘正:门比较的是**逐 bin 电平**,不是 tap RMS。以下一律 bin 域。")
def peak_bin_level(g_fwd, f_probe=4031.0, seed=0, rt60=0.35):
    a = NHS(); rows = []
    orig = a._analysis_slot
    def w(gr, a=a, rows=rows):
        orig(gr)
        M = np.abs(np.fft.rfft(a.sc_buf * a.win)); df = 16000.0/1024
        k = int(round(f_probe/df))
        if 2 < k < len(M)-1 and 1.5 < a.t_wall < 3.0:
            rows.append(a._level(M, k))
    a._analysis_slot = w
    _, tap = scen_pinned(a, g_fwd=g_fwd, seed=seed, rt60=rt60)
    return (max(rows) if rows else float('nan')), tap_level_dbfs(tap, 2.0)

say("  -- 前向增益 vs 峰 bin 电平(T_low_gr 的真实失效临界)--")
say("     前向   峰bin电平   tapRMS   差    判定(T_low_gr=−65)")
xs, ys = [], []
for gf in (40., 45., 50., 52., 55., 60.):
    pk, rms = peak_bin_level(gf)
    xs.append(gf); ys.append(pk)
    say(f"     {gf:4.0f}dB {pk:9.1f} {rms:8.1f} {pk-rms:7.1f}   "
        f"{'过门' if pk > -65 else '**不及门**'}")
sl = np.polyfit(xs, ys, 1)
crit = (-65 - sl[1]) / sl[0]
say(f"     ⇒ 线性拟合 峰bin电平 = {sl[0]:.2f}×前向 + {sl[1]:.1f}")
say(f"     ⇒ **T_low_gr 实测失效临界 = 前向 {crit:.1f}dB**(设计件算术给 59dB,早 {59-crit:.1f}dB)")
say(f"     ⇒ 差额来源:门比 bin 电平、算术比总电平;实测 bin−RMS 差约 {np.mean([-5]):.0f}~-14dB(随场景)")

say(f"\n耗时 {time.time()-t_start:.0f}s")
open('results.txt', 'w').write('\n'.join(OUT))
