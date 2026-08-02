"""★ B-2 的直接证据:变异测试 —— 人为改坏 nhs.py,CHECK 必须 FAIL。
「能 import」不等于「真依赖」;本文件证明后者。
adaptive-dsp-3 · 2026-08-02 · [L2/宿主仿真]
"""
import io, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.join(HERE, '..', 'prototype_W1P')
NHS = os.path.join(PROTO, 'nhs.py')
CHK = os.path.join(HERE, 'check_w1b.py')

MUTANTS = [
    ('M31 租约刷新退回**否定式**(新无判决类别默认落危险侧)',
     "                if deepened and s.has_affirmative_verdict:",
     "                if deepened and not s.from_abstain:"),
    ('M32 ★机制锁:肯定标记的**默认值**翻成 True(=未来新类别默认落危险侧)',
     "        self.has_affirmative_verdict = False   # ★ 肯定式",
     "        self.has_affirmative_verdict = True    # MUTANT"),
    ('M28 P0 有效性门失效(退回:静默帧也挂陷起探针)',
     "                if not (0 < _k < len(M)) or _lv_now <= P.level_valid_db:",
     "                if False:"),
    ('M29 P0 门写成门限(用 T_low 而非数值有效性 ⇒ 过强,废掉历史累积)',
     "                if not (0 < _k < len(M)) or _lv_now <= P.level_valid_db:",
     "                if not (0 < _k < len(M)) or _lv_now <= P.T_low:"),
    ('M25 撞顶退回「只报警不作为」(=静默失效缺陷本体)',
     "                    self.g_duck_db = max(-6.0, self.g_duck_db - 1.0)\n                    self.events.append((self.slot_seq, 'duck-depth', round(self.g_duck_db, 1)))",
     "                    pass  # MUTANT:只报警不作为"),
    ('M26 两条耗尽路径混用同一事件(不同源被合并)',
     "                self.events.append((self.slot_seq, 'DEPTH_EXHAUSTED', round(f, 1)))",
     "                self.events.append((self.slot_seq, 'SLOTS_EXHAUSTED', round(f, 1)))"),
    ('M27 n_blocked 退回每帧计数(=EXHAUSTED 放大 11× 的同型第二例)',
     "                self.ctr['n_blocked'] = self.ctr.get('n_blocked', 0) + 1",
     "                self.ctr['n_blocked'] = self.ctr.get('n_blocked', 0) + 12"),
    ('M24 EXHAUSTED 退回每复检计一次(口径放大 11×,DEC-0010 缺陷本体)',
     "                    if not s.exhausted_flag:",
     "                    if True:"),
    ('M22 可抢占失效(真啸叫抢不走弃权占用 ⇒ 资源害不消失)',
     "                if pre:",
     "                if False:"),
    ('M23 可抢占无差别(连正向分类的占用也抢 ⇒ 抢掉真啸叫的陷波)',
     "                pre = sorted([s for s in self.slots if (not s.has_affirmative_verdict)\n                              and s.st != NotchSlot.FREE], key=lambda s: s.t_last_hit)",
     "                pre = sorted([s for s in self.slots if s.st != NotchSlot.FREE], key=lambda s: s.t_last_hit)"),
    ('M19 t_last_hit 退回无条件刷新(=r16 实证的永不回收缺陷)',
     "                if deepened and s.has_affirmative_verdict:   # ★★ r27 肯定式(原为 not from_abstain)\n                    s.t_last_hit = self.t_wall",
     "                s.t_last_hit = self.t_wall"),
    ('M20 弃权来源标记失效(弃权占用被当作正向分类)',
     "                s.from_abstain = True                      # ★ r17",
     "                s.from_abstain = False                     # MUTANT"),
    ('M21 回收优先序去掉弃权优先(退回纯 LRU)',
     "                              key=lambda s: (s.has_affirmative_verdict, s.t_last_hit))  # ★ r27 肯定式",
     "                              key=lambda s: s.t_last_hit)"),
    ('M17 去掉共模单边钳位(退回 r14 形态:rest 上升也算判啸叫证据)',
     "            diff = dL - max(dR, 0.0)",
     "            diff = dL - dR"),
    ('M18 弃权门失效(三态退回两态,ε 地板伪值重新进入判定)',
     "            if pr['L0'] <= fl or L1 <= fl:",
     "            if False:"),
    ('M14 C8-③ 探针恒判啸叫(=从不撤陷,机制空转)',
     "            is_ext = diff <= P.probe_X_db",
     "            is_ext = diff <= -1e9"),
    ('M16 C8-③ 丢掉共模项(退回 C8-② 单量判据 = F25 缺陷本体)',
     "            diff = dL - max(dR, 0.0)",
     "            diff = dL"),
    ('M15 C8-② 撤陷只改状态位、不还原系数(假撤陷)',
     "                s.set_coef(FS, P.bw_oct)               # 真撤陷(系数回恒等)",
     "                pass                                   # MUTANT:不还原系数"),
    ('M11 GROWTH 路恢复三臂豁免(=r11 实证的 D6-e 结构缺陷)',
     "            exempt = fam_max and causal",
     "            exempt = fam_max and (causal or arm1 or arm2)"),
    ('M12 causal 退回旧口径(轨龄 vs 否决起点,实测恒真)',
     "        causal = tr.causal_ok\n",
     "        causal = tr.causal_ok or ((tr.t_veto - tr.t_born) >= P.causal_min)\n"),
    ('M13 _causal_scan 的晚到判据改为绝对值(丢掉方向性)',
     "and (tr.t_fam0 - tr.t_grow0) >= P.fam_late_min",
     "and abs(tr.t_fam0 - tr.t_grow0) >= P.fam_late_min"),
    ('M9 g_duck 不施加(=r9 前的缺陷:算了但扔掉)',
     "y = y * self.duck_gain()",
     "y = y * 1.0                 # MUTANT"),
    ('M10 深度容差退回 1e-9(=伪装成容差的精确相等,定点不可迁移)',
     "DEPTH_EPS_DB = 0.05",
     "DEPTH_EPS_DB = 1e-9"),
    ('M1 _is_dom 退回 PAPR(=vP1.0 的 B-1 缺陷)',
     "return tr is max(act, key=lambda t: (t.pnpr_hist[-1] if t.pnpr_hist else -99))",
     "return tr is max(act, key=lambda t: (t.papr_hist[-1] if t.papr_hist else -99))"),
    ('M2 _level 退回漏 Hann 相干增益(=M-1 缺陷)',
     "return 20 * np.log10(M[k] * 4.0 / NFFT + 1e-30) + self.cal",
     "return 20 * np.log10(M[k] * 2.0 / NFFT + 1e-30) + self.cal"),
    ('M3 rbj_peaking 系数符号错',
     "b = np.array([1 + alpha*A, -2*np.cos(w0), 1 - alpha*A])",
     "b = np.array([1 + alpha*A, +2*np.cos(w0), 1 - alpha*A])"),
    ('M4 _quinn 去掉修正项(退化为整 bin)',
     "return k + (d if np.isfinite(d) and abs(d) < 1 else 0.0)",
     "return float(k)"),
    ('M5 _imsd 的 LS x 轴改回 0..W-1',
     "x = sq - sq[0] if 'B9' not in self.B else np.arange(len(y), dtype=float)",
     "x = np.arange(len(y), dtype=float)"),
    ('M6 _phpr_veto 去掉「因果时序」合取项',
     "exempt = fam_max and causal and (arm1 or arm2 or arm3)",
     "exempt = fam_max and (arm1 or arm2 or arm3)"),
    ('M8 relaxed 退回粘滞(=critic 实证的 C12 架空缺陷)',
     "tr.relaxed = bool(o['lv'] < self.P.T_low)",
     "tr.relaxed = tr.relaxed or o['relaxed']"),
    ('M7 _pnpr 恒返回 0(判据失效)',
     "        return 20 * np.log10(M[k] / (np.mean(M[idx]) + 1e-30) + 1e-30)",
     "        return 0.0"),
]

def _purge_pyc():
    """★ 必须清字节码缓存:.pyc 失效判据是 mtime+size,而**等长变异**
    (如 `* 4.0` → `* 2.0`)在同秒内改动会被判为未变 ⇒ 加载陈旧字节码
    ⇒ 变异被误报为「存活」。本项目已因此误判过一次。"""
    for d in (PROTO, HERE):
        pc = os.path.join(d, '__pycache__')
        if os.path.isdir(pc):
            shutil.rmtree(pc, ignore_errors=True)

def run_check(env_extra=None):
    _purge_pyc()
    e = dict(os.environ); e.update(env_extra or {})
    e['PYTHONDONTWRITEBYTECODE'] = '1'
    r = subprocess.run([sys.executable, CHK], capture_output=True, text=True, env=e)
    return r.returncode, r.stdout

orig = io.open(NHS, encoding='utf-8').read()
print("=" * 84)
print("变异测试:改坏 nhs.py ⇒ CHECK 必须 FAIL(证明自验真依赖被测物)")
print("=" * 84)
rc0, out0 = run_check()
print(f"  基线(未变异):exit={rc0}  {'✓ 全过' if rc0 == 0 else '✗ 基线就挂,先修'}")
if rc0 != 0:
    print(out0); sys.exit(2)

results = []
try:
    for name, old, new in MUTANTS:
        if old not in orig:
            print(f"  [跳过] {name} —— 锚点未命中(源已变?)"); results.append((name, None)); continue
        io.open(NHS, 'w', encoding='utf-8').write(orig.replace(old, new, 1))
        rc, out = run_check()
        killed = rc != 0
        fails = [l.strip() for l in out.splitlines() if '**FAIL**' in l]
        results.append((name, killed))
        print(f"  [{'✓ 杀死' if killed else '✗ **存活**'}] {name}")
        for f in fails:
            print(f"        {f}")
finally:
    io.open(NHS, 'w', encoding='utf-8').write(orig)      # always restore

rc_r, _ = run_check()
print(f"\n  还原校验:exit={rc_r} {'✓ 源已还原' if rc_r == 0 else '✗ 还原失败!'}")
k = sum(1 for _, v in results if v is True); n = sum(1 for _, v in results if v is not None)
_sk = [nm for nm, r in results if r is None]
_ev = [r for _, r in results if r is not None]
print(f"\n  ⇒ **变异杀死率 = {sum(1 for r in _ev if r)}/{len(_ev)}**"
      + (f"  ⚠ **另有 {len(_sk)} 个跳过，不计入分母**" if _sk else ""))
if _sk:
    print("  ⚠ **跳过 = 该处已无人守**（锚点随源码变动而失效），不得藏在满分后面：")
    for nm in _sk:
        print(f"      · {nm}")
    print("  ⚠ 纪律：改了源码就要同步改变异锚点；否则回归锁静默失效。")
