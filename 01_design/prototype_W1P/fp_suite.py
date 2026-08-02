"""误报套件 v2(r10 重设计)—— 两台仪器分开报,9 类各自出数。
仪器 A「漏斗率」:逐级条件通过率 N0→N6,分母逐级真变化(高分辨,定位判据作用点)。
仪器 B「误报率」:独立试次(全新 NHS 状态 + 互不重叠素材),二值记,Wilson CI。
   —— 立此形态的理由:一次 engage 占住槽位 ≈105s(lift60+爬升≤15+reclaim30),
      engage 事件强自相关 ⇒ 单条长片段不产生独立样本。
全部 [L2/宿主仿真·合成料]:只支持判据变体间**相对**比较,不支持绝对误报率断言。
"""
import numpy as np, sys
from scipy.signal import butter, lfilter
import nhs, env
from nhs import NHS, FRAME, FS

# ----------------------------------------------------------------- 素材(9 类)
def _norm(x, a=0.25):
    return a * x / (np.max(np.abs(x)) + 1e-12)

def m_flute(dur, seed):                      # 1 已知阳性,正对照
    return env.synth_music(dur, seed=seed)

def m_strings(dur, seed):                    # 2 持续弓弦:强稳态谐波,最像啸叫
    rng = np.random.default_rng(seed); n = int(dur*FS); t = np.arange(n)/FS
    x = np.zeros(n)
    for f in [196.0, 293.7, 440.0, 659.3]:
        vib = 1 + 0.004*np.sin(2*np.pi*rng.uniform(4.5, 6.5)*t + rng.uniform(0, 6))
        amp = 0.6 + 0.4*np.sin(2*np.pi*rng.uniform(0.1, 0.3)*t + rng.uniform(0, 6))
        for k in range(1, 15):
            x += amp*(0.9/k**1.15)*np.sin(2*np.pi*f*k*np.cumsum(vib)/FS + rng.uniform(0, 6))
    return _norm(x)

def m_piano(dur, seed):                      # 3 有起音有衰减,谐波密
    rng = np.random.default_rng(seed); n = int(dur*FS); x = np.zeros(n)
    for _ in range(max(1, int(dur*2.5))):
        p = rng.integers(0, max(1, n-int(1.2*FS))); ln = int(1.2*FS)
        t = np.arange(ln)/FS; f = rng.choice([220., 261.6, 329.6, 392., 523.3])
        dec = np.exp(-t/rng.uniform(0.4, 0.9))
        atk = np.minimum(1.0, t/0.006)
        for k in range(1, 16):
            x[p:p+ln] += atk*dec*(0.9/k**1.2)*np.sin(2*np.pi*f*k*t + rng.uniform(0, 6))
    return _norm(x)

def m_clap(dur, seed):    return env.synth_transients(dur, seed=seed, kind='clap')      # 4
def m_cough(dur, seed):   return env.synth_transients(dur, seed=seed, kind='cough')     # 5

def m_keyboard(dur, seed):                   # 6 冲击,高频
    rng = np.random.default_rng(seed); n = int(dur*FS); x = np.zeros(n)
    for _ in range(max(1, int(dur*6))):
        p = rng.integers(0, max(1, n-3000)); ln = int(0.012*FS)
        t = np.arange(ln)/FS
        env_ = np.exp(-t/0.0025)
        b, a = butter(2, [2500/(FS/2), 9000/(FS/2)], btype='band')
        x[p:p+ln] += lfilter(b, a, rng.normal(0, 1, ln))*env_
    return _norm(x, 0.2)

def m_hvac(dur, seed):                       # 7 稳态宽带 + 叶片通过频率窄线谱(先验最危险)
    rng = np.random.default_rng(seed); n = int(dur*FS); t = np.arange(n)/FS
    b, a = butter(2, 900/(FS/2), btype='low')
    x = lfilter(b, a, rng.normal(0, 1, n))                       # 宽带风噪
    bpf = rng.uniform(280, 420)                                  # 叶片通过频率
    for k in range(1, 6):                                        # + 其谐波族
        x += (0.30/k)*np.sin(2*np.pi*bpf*k*t + rng.uniform(0, 6))
    return _norm(x, 0.18)

def m_multitalk(dur, seed):                  # 8 重叠语音
    rng = np.random.default_rng(seed)
    xs = [env.synth_speech(dur, seed=int(rng.integers(0, 1 << 30)),
                           f0=float(rng.uniform(95, 210))) for _ in range(3)]
    L = min(len(v) for v in xs)
    return _norm(sum(v[:L] for v in xs))

def m_farend(dur, seed):                     # 9 远端重放(→ IF-v1.7 C14)
    rng = np.random.default_rng(seed); n = int(dur*FS); t = np.arange(n)/FS
    x = env.synth_music(dur, seed=seed)[:n]
    x = x + 0.5*np.sin(2*np.pi*rng.uniform(700, 1400)*t)          # 远端单音重放
    b, a = butter(2, [300/(FS/2), 3400/(FS/2)], btype='band')      # 远端链带限
    return _norm(lfilter(b, a, x))

def m_bare_stop(dur, seed):                  # 10(r15 重造)裸纯音停 + **换频重来**
    """r14 版失败:纯音在响时已被判外部并登记保鲜期(ttl 20s > 试次 6s)
      ⇒ 停止时该频点不再挂陷 ⇒ **探针不启动 ⇒ 失效面从未触达**(裸停单计=0 即证据)。
    r15 重造:停止后**换一个新频率重来**,使停止事件之后仍有新挂陷发生。
    ⚠ D-J:本构造必须报告 c8_bare_stop 分支的实际执行次数;**0 次 ⇒ 判无效,非通过**。"""
    rng = np.random.default_rng(seed); n = int(dur*FS); t = np.arange(n)/FS
    x = rng.normal(0, 3e-4, n)
    # ★ r15 二次重造:失效面要求**探针在飞行中时源停止**。
    #   纯音须持续到足以入轨+挂陷(≈1.0-1.2s),然后在探针窗(256ms)内**硬停**。
    #   故用一串**各自不同频率**的短促纯音(避开彼此保鲜期),每段 1.25s。
    seg = int(0.32 * FS)   # ★ 见 r15 时序实测:挂陷@段起+0.09s、判决@+0.256s
                           #   ⇒ 音长须落在 [0.09,0.35]s 才能让**停止发生在探针飞行中**
    fs_list = list(rng.uniform(500, 3500, size=max(1, n // seg)))
    for j, f0 in enumerate(fs_list):
        a0, b0 = j * seg, min(n, (j + 1) * seg)
        x[a0:b0] += 0.25 * np.sin(2 * np.pi * float(f0) * t[a0:b0])
    return x


CLASSES = [('1 音乐-长笛', m_flute), ('2 音乐-弓弦', m_strings), ('3 音乐-钢琴', m_piano),
           ('4 掌声', m_clap), ('5 咳嗽', m_cough), ('6 键盘', m_keyboard),
           ('7 空调/风扇', m_hvac), ('8 多人交谈', m_multitalk), ('9 远端重放', m_farend), ('10 裸纯音停', m_bare_stop)]

GR_OFF = {'out_lim_active': False, 'out_lim_gr_db': 0.0}

def _run(alg, mat):
    n = (len(mat)//FRAME)*FRAME
    for i in range(0, n, FRAME):
        alg.process_frame(mat[i:i+FRAME], GR_OFF)
    return sum(1 for e in alg.events if 'engage' in str(e[1]))

# ----------------------------------------------------------------- 仪器 A
def instrument_A(dur=60.0):
    print("=" * 92)
    print("仪器 A「漏斗率」—— 逐级条件通过率(分母逐级真变化);每类各自出数,不合并")
    print("=" * 92)
    print(f"{'类':<14}{'N0局大':>9}{'N1候选':>8}{'N1/槽':>7}{'N2电平':>8}{'N3判据':>8}"
          f"{'N4入轨':>8}{'N5howl':>8}{'N6挂陷':>7}  |  {'r2=N2/N1':>9}{'r3=N3/N2':>9}"
          f"{'r4=N4/N3':>9}{'r5=N5/N4':>9}")
    rows = []
    for name, mk in CLASSES:
        a = NHS(); n6 = _run(a, mk(dur, 100))
        c = a.ctr; sl = c['slots']
        g = lambda k: c.get(k, 0)
        r = lambda x, y: (x/y if y else float('nan'))
        rows.append((name, g('N0_locmax'), g('N1_cand'), g('N1_cand')/sl, g('N2_lvl'),
                     g('N3_gate'), g('N4_born'), g('N5_howl'), n6))
        print(f"{name:<14}{g('N0_locmax'):>9}{g('N1_cand'):>8}{g('N1_cand')/sl:>7.2f}"
              f"{g('N2_lvl'):>8}{g('N3_gate'):>8}{g('N4_born'):>8}{g('N5_howl'):>8}{n6:>7}"
              f"  |  {r(g('N2_lvl'),g('N1_cand')):>9.4f}{r(g('N3_gate'),g('N2_lvl')):>9.4f}"
              f"{r(g('N4_born'),g('N3_gate')):>9.4f}{r(g('N5_howl'),g('N4_born')):>9.4f}")
    return rows

# ----------------------------------------------------------------- 仪器 B
def wilson(k, n, z=1.96):
    if n == 0: return (float('nan'),)*2
    p = k/n; d = 1 + z*z/n
    c = (p + z*z/(2*n))/d
    h = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return (max(0.0, c-h), min(1.0, c+h))

def instrument_B(N=50, trial_s=6.0, settle_s=1.0):
    print("\n" + "=" * 92)
    print(f"仪器 B「误报率」pilot —— N={N} 独立试次/类,试次={trial_s}s(前 {settle_s}s 稳定不计)")
    print("  独立性来源:每试次全新 NHS 状态 + 互不重叠素材段(engage 自相关 ≈105s,故不可用单条长片段)")
    print("=" * 92)
    print(f"{'类':<14}{'k(有挂陷试次)':>15}{'N':>5}{'p̂':>9}{'Wilson 95% CI':>22}"
          f"{'2×分辨所需N':>13}")
    out = []
    for name, mk in CLASSES:
        k = 0
        for i in range(N):
            a = NHS()
            mat = mk(trial_s, 1000 + i)                # 每试次不同 seed ⇒ 段不重叠
            ns = int(settle_s*FS)//FRAME*FRAME
            _run(a, mat[:ns])                          # 稳定段:跑但不计
            base = sum(1 for e in a.events if 'engage' in str(e[1]))
            n6 = _run(a, mat[ns:])
            k += 1 if (n6 - base) > 0 else 0
        p = k/N; lo, hi = wilson(k, N)
        need = (46.0/p) if p > 0 else float('inf')
        out.append((name, k, N, p, lo, hi, need))
        ns_ = f"{need:.0f}" if np.isfinite(need) else "∞"
        print(f"{name:<14}{k:>15}{N:>5}{p:>9.3f}   [{lo:>6.3f}, {hi:>6.3f}]{ns_:>13}")
    return out

# ----------------------------------------------------------------- B-F1 斜率检验
def bf1_slope():
    import experiments as E
    print("\n" + "=" * 92)
    print("B-F1 钉住判据(新):限幅器阈值移 Δ dB ⇒ tap 平台电平移 Δ dB,**物理预测斜率 = 1.0**")
    print("  PASS 判据:斜率 ∈ [0.85,1.15] 且 R² ≥ 0.98 且 末2s 极差 ≤ 1.0dB")
    print("  空对照(必须 FAIL):关限幅器 ⇒ 无平台,电平跑到数值天花板")
    print("=" * 92)
    # ⚠ 适用域(r10 实测立):斜率检验只在**钉住区**成立。thr 升高到 tap 越过检测门后,
    #   NHS 检出并压掉啸叫 ⇒ tap 落到底噪、与 thr 无关(实测 −12/−9/−6 三点同为 −99.47dB)
    #   ⇒ 那已不是"钉住"场景,不该纳入回归。故扫描区间下移至钉住区。
    thrs = [-30., -27., -24., -21., -18., -15.]
    lv, rng_db, neng = [], [], []
    for th in thrs:
        a = NHS(); _out, tap = E.scen_pinned(a, dur=10.0, thr_db=th)
        tap = np.asarray(tap, dtype=float)
        # 平台电平 = 末 2s 的 0.1s 窗 RMS 序列均值(dBFS);极差按同一序列算
        w = int(0.1*FS); tail = tap[-int(2.0*FS):]
        segs = np.array([20*np.log10(np.sqrt(np.mean(tail[i:i+w]**2))+1e-30)
                         for i in range(0, len(tail)-w, w)])
        lv.append(float(np.mean(segs))); rng_db.append(float(np.ptp(segs)))
        ne = sum(1 for e in a.events if 'engage' in str(e[1])); neng.append(ne)
        print(f"  thr={th:>6.1f}dBFS  平台电平={lv[-1]:>8.2f}dB  末段极差={rng_db[-1]:>5.2f}dB"
              f"  挂陷={ne:>3}  (设计算例 thr−50 = {th-50.0:>6.1f}dB)")
    if max(neng) > 0:
        print(f"  ⚠ 有 thr 点发生挂陷(engage>0)⇒ 该点已非纯钉住态,回归结果须按此解读")
    A = np.vstack([thrs, np.ones(len(thrs))]).T
    sl, ic = np.linalg.lstsq(A, np.array(lv), rcond=None)[0]
    pred = A @ np.array([sl, ic])
    ss_res = float(np.sum((np.array(lv)-pred)**2))
    ss_tot = float(np.sum((np.array(lv)-np.mean(lv))**2))
    r2 = 1 - ss_res/ss_tot if ss_tot > 0 else float('nan')
    ok = (0.85 <= sl <= 1.15) and (r2 >= 0.98) and (max(rng_db) <= 1.0)
    print(f"\n  斜率={sl:.4f}(预测 1.0)  R²={r2:.5f}  最大末段极差={max(rng_db):.2f}dB"
          f"  ⇒ {'PASS' if ok else '**FAIL**'}")

    # ── 空对照:关限幅器。若判据有效,此处**必须 FAIL**(否则判据没在测限幅器)
    print("\n  【空对照】关限幅器(limiter=None)—— 必须 FAIL,否则判据测的不是限幅器")
    import env as _env
    lv0, rg0 = [], []
    for th in thrs:
        a = NHS()
        h, d = E.rir(0.35, 0)
        h = h * 10 ** ((3.0 - 50.0) / 20.0)
        src = 1e-5*np.random.default_rng(0).normal(0, 1, int(10.0*FS))
        lp = _env.ClosedLoop(h, d, a, g_pre_db=0, g_fwd_db=50.0, limiter=None)
        _, _o, tap = lp.run(src)
        tap = np.asarray(tap, float)
        w = int(0.1*FS); tail = tap[-int(2.0*FS):]
        segs = np.array([20*np.log10(np.sqrt(np.mean(tail[i:i+w]**2))+1e-30)
                         for i in range(0, len(tail)-w, w)])
        lv0.append(float(np.mean(segs))); rg0.append(float(np.ptp(segs)))
        print(f"    thr={th:>6.1f}(名义,实际无限幅)  电平={lv0[-1]:>8.2f}dB  极差={rg0[-1]:>5.2f}dB")
    sl0, ic0 = np.linalg.lstsq(A, np.array(lv0), rcond=None)[0]
    p0 = A @ np.array([sl0, ic0])
    sr = float(np.sum((np.array(lv0)-p0)**2)); st = float(np.sum((np.array(lv0)-np.mean(lv0))**2))
    r20 = 1 - sr/st if st > 0 else float('nan')
    ok0 = (0.85 <= sl0 <= 1.15) and (r20 >= 0.98) and (max(rg0) <= 1.0)
    print(f"    空对照 斜率={sl0:.4f}  R²={r20 if np.isfinite(r20) else float('nan'):.5f}"
          f"  最大极差={max(rg0):.2f}dB  ⇒ {'**空对照竟 PASS ⇒ 判据无效**' if ok0 else 'FAIL ✓(对照能失败)'}")
    return sl, r2, max(rng_db), ok, sl0, r20, max(rg0), ok0

if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what in ('A', 'all'):  instrument_A(float(sys.argv[2]) if len(sys.argv) > 2 else 60.0)
    if what in ('B', 'all'):  instrument_B(50)
    if what in ('F', 'all'):  bf1_slope()
