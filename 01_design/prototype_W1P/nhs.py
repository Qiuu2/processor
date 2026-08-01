"""W1-P 宿主原型 · NHS 算法核心(浮点)
adaptive-dsp(第 3 实例)· 2026-08-01 · 全部产出 [L2/宿主仿真]

对应设计件 `01_design/W1B_NHS_algorithm_design.md` v1.4(已冻结,本文件不改它)。
**本阶段只验算法行为,不做定点**(阶段 2 再移植)。

可复用件溯源(lead 清单):
  - PAPR 式:PX4 `GyroFFT.cpp:514` 同构(其对**幅度比**取 10log10;本文按设计件
    §1.2 勘正为 **20log10 = 常规 dB**,PX4 参数值不可直搬)。
  - IPMP:PX4 最近频率配对 + 0.25bin 豁免 + 7 点中值 + 100ms 老化(移植重标)。
  - Quinn 第二估计器:PX4 `EstimatePeakFrequencyBin` 同式浮点重写。
  - RBJ peaking(负增益)biquad DF1:RBJ Cookbook(W0 已核)。
  - IMSD:**全域无同构,本文自研**(D0c §1.8)。
  ⚠ 专利隔离(US9794695B2):IPMP 做成可切换模块 `ipmp_mode ∈ {px4, off, alt}`,
     法务要绕只动这一块,不长进主干。
"""
import numpy as np
from scipy.signal import lfilter

# ============================================================================
# 版本化(DEC-0016:本文件是 NHS **算法行为的唯一权威源**)
#   改动 = 新版本号 + decisions_log 台账行 + W1-B 引用版本同步(与合同引用同规矩)
#   ⚠ 本件尚未过任何门:全部 [L2/宿主仿真],未经独立 critic 评审
# ============================================================================
__version__ = "P1.0"


FS = 48000.0
FRAME = 64
FS_SC = 16000.0          # 旁链(48k→16k 抽取 3:1)
NFFT = 1024              # 64ms 分析窗
HOP_SC = 256             # 16ms/通道
DEC = 3


# ------------------------------------------------------------------ 参数
class Params:
    """设计件 §6「语音·小房间」预设 + §1-§5 初值。全部 [L4/待标定] → 本原型标定为 [L2]。"""
    def __init__(self, **kw):
        # 判据门(§1.2;PAPR/PNPR 均 20log10 幅度比 = 常规 dB)
        self.T_papr = 15.0
        self.T_pnpr = 8.0
        self.T_papr_high = self.T_papr + 6.0
        self.T_low = -45.0
        self.T_low_gr = self.T_low - 20.0
        self.T_panic = -6.0
        self.f_det_lo, self.f_det_hi = 120.0, 7800.0
        self.n_cand = 16
        # IMSD(§2.2;dB/s 定义,按槽换算)
        self.beta_min_dbs, self.beta_max_dbs, self.beta_fast_dbs = 60.0, 750.0, 190.0
        self.s_max, self.dP_min = 1.5, 6.0
        self.W_long, self.W_short = 8, 4
        # 跟踪 / 可观测性(§1.2-D)
        self.hit_need, self.age_miss = 3, 6
        self.gap_guard_ratio = 2.0        # 空号护栏(F2 勘正,原 1.5)
        self.U_hold, self.U_max, self.readback_budget = 24, 32, 4
        # PERSIST(§3.3)
        self.P_persist_s, self.persist_hit_rate = 1.0, 0.70
        # PHPR(§3.2)
        self.T_harm, self.D_sub, self.D_harm = 10.0, 10.0, 20.0
        self.causal_min = 2
        self.R_RISE, self.N_RISE, self.S_PLAT, self.MIN_PLAT = 18.0, 2, 2.0, 3
        self.T_exempt_s, self.T_shadow_s = 10.0, 60.0
        self.N_gr = 2
        self.inherit_credit = False   # F10:数值信用继承默认**关**(实测有害)
        # 陷波(§4)
        self.bw_oct, self.depth0, self.depth_step, self.max_depth = 1/5, -3.0, -3.0, -18.0
        self.ramp_db_per_s = 3.0 / 0.050
        self.lift_after_s, self.lift_step_s, self.reclaim_s = 60.0, 5.0, 30.0
        self.NN, self.NT = 8, 12
        for k, v in kw.items():
            setattr(self, k, v)

    @property
    def T_hop(self):
        return HOP_SC / FS_SC          # 0.016 s

    def beta(self, dbs):
        return dbs * self.T_hop


# ------------------------------------------------------- 陷波器(RBJ peaking cut)
def rbj_peaking(fs, f0, gain_db, bw_oct):
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2 * np.pi * f0 / fs
    alpha = np.sin(w0) * np.sinh(np.log(2) / 2 * bw_oct * w0 / np.sin(w0))
    b = np.array([1 + alpha*A, -2*np.cos(w0), 1 - alpha*A])
    a = np.array([1 + alpha/A, -2*np.cos(w0), 1 - alpha/A])
    return b / a[0], a / a[0]


class NotchSlot:
    FREE, ENGAGE, HOLD, LIFT, STANDBY = 0, 1, 2, 3, 4

    def __init__(self):
        self.st = self.FREE
        self.f = 0.0; self.depth = 0.0; self.target = 0.0
        self.b = np.array([1.0, 0, 0]); self.a = np.array([1.0, 0, 0])
        self.zi = np.zeros(2)
        self.t_last_hit = 0.0; self.t_lift = 0.0

    def set_coef(self, fs, bw_oct, coef_fs=None):
        if self.st == self.FREE or self.depth >= -1e-9:
            self.b = np.array([1.0, 0, 0]); self.a = np.array([1.0, 0, 0]); return
        self.b, self.a = rbj_peaking(coef_fs or fs, self.f, self.depth, bw_oct)


# ---------------------------------------------------------------- 轨(Track)
class Track:
    __slots__ = ('active', 'f', 'fmed', 'papr_hist', 'seq_hist', 'hist_n', 't_born',
                 't_last_seen', 'obs_n', 'hit_n', 't_veto', 'miss_run', 'unobs_run',
                 'rapid_onset', 'relaxed', 'causal_ok', 'last_level', 'last_obs_seq',
                 't_born_wall', 't_half_wall')

    def __init__(self):
        self.active = False; self.f = 0.0; self.fmed = []
        self.papr_hist = []; self.seq_hist = []; self.hist_n = 0
        self.t_born = 0; self.t_last_seen = 0; self.obs_n = 0; self.hit_n = 0
        self.t_veto = -1; self.miss_run = 0; self.unobs_run = 0
        self.rapid_onset = False; self.relaxed = False; self.causal_ok = False
        self.last_level = -120.0; self.last_obs_seq = 0
        self.t_born_wall = 0.0; self.t_half_wall = 0.0


class Shadow:
    __slots__ = ('f', 't_removed_wall', 'causal_ok', 'rapid_onset', 'obs_c', 'hit_c')

    def __init__(self, f, tw, c, r, o, h):
        self.f = f; self.t_removed_wall = tw; self.causal_ok = c
        self.rapid_onset = r; self.obs_c = o; self.hit_c = h


# ---------------------------------------------------------------- NHS 主体
class NHS:
    def __init__(self, P=None, broken=None, ipmp_mode='px4', cal_offset_db=0.0):
        self.P = P or Params()
        self.B = set(broken or [])          # broken 版开关(B1..B12)
        self.ipmp_mode = ipmp_mode
        self.cal = cal_offset_db
        self.slots = [NotchSlot() for _ in range(self.P.NN)]
        self.tracks = [Track() for _ in range(self.P.NT)]
        self.shadows = []
        self.sc_buf = np.zeros(NFFT)        # 16k 域分析缓冲
        self.dec_state = None
        self.acc = np.zeros(0)
        self.slot_seq = 0
        self.t_wall = 0.0
        self.frame_i = 0
        self.win = np.hanning(NFFT)
        self.g_duck_db = 0.0
        self.events = []
        self.gr_hist = 0
        self.skip_plan = None               # 人为跳槽(B9 场景)
        self.log = []                       # 每槽快照
        self.ctr = dict(table_full=0, unobs=0, readback_ok=0, shadow_new=0,
                        shadow_inherit=0, umax_hit=0, gapguard=0, slots=0)

    # ---------------- 执行器 ----------------
    def duck_gain(self):
        return 10 ** (self.g_duck_db / 20.0)

    def process_frame(self, x, gr=None):
        """音频域每帧:先取检测 tap(陷波器组**入口**,链序 C-3),再过陷波器组。"""
        self._sidechain_push(x)
        self.frame_i += 1
        self.t_wall += FRAME / FS
        if self.frame_i % (HOP_SC // (FS_SC * FRAME / FS) if False else 12) == 0:
            self._maybe_slot(gr or {})
        y = x
        for s in self.slots:
            if s.st == NotchSlot.FREE:
                continue
            if 'B2' in self.B:              # broken:深度恒 0dB(系数恒等)
                continue
            y, s.zi = lfilter(s.b, s.a, y, zi=s.zi)
        return y

    def _sidechain_push(self, x):
        self.acc = np.concatenate([self.acc, x])
        k = (len(self.acc) // DEC) * DEC
        if k:
            d = self.acc[:k].reshape(-1, DEC).mean(axis=1)   # 简易抽取(含抗混叠平均)
            self.acc = self.acc[k:]
            if len(d):
                self.sc_buf = np.concatenate([self.sc_buf, d])[-NFFT:]

    # ---------------- 旁链分析槽 ----------------
    def _maybe_slot(self, gr):
        need = HOP_SC / FS_SC
        if not hasattr(self, '_next_slot_t'):
            self._next_slot_t = need
        if self.t_wall + 1e-9 < self._next_slot_t:
            return
        self._next_slot_t += need
        self.slot_seq += 1
        if self.skip_plan and self.slot_seq in self.skip_plan:
            return                                            # 交付被跳过(C1 降档)
        self._analysis_slot(gr)

    def _spectrum(self):
        X = np.abs(np.fft.rfft(self.sc_buf * self.win))
        return X

    def _papr(self, M, k):
        tot = np.sum(M)
        return 20 * np.log10((len(M) - 1) * M[k] / max(tot - M[k], 1e-30) + 1e-30)

    def _pnpr(self, M, k):
        df = FS_SC / NFFT
        f = k * df
        kk = int(round(max(187.0, f * (2 ** (1/3) - 1)) / df))
        lo, hi = max(0, k - kk), min(len(M), k + kk + 1)
        idx = [j for j in range(lo, hi) if abs(j - k) > 3]
        if not idx:
            return 0.0
        return 20 * np.log10(M[k] / (np.mean(M[idx]) + 1e-30) + 1e-30)

    def _level(self, M, k):
        return 20 * np.log10(M[k] * 2.0 / NFFT + 1e-30) + self.cal

    @staticmethod
    def _quinn(X, k):
        """PX4 EstimatePeakFrequencyBin 同式(Quinn's second estimator)。"""
        def tau(x):
            return 0.25*np.log(3*x*x + 6*x + 1) - np.sqrt(6)/24*np.log(
                (x + 1 - np.sqrt(2/3)) / (x + 1 + np.sqrt(2/3)))
        try:
            ap = (X[k+1].real*X[k].real + X[k+1].imag*X[k].imag) / (abs(X[k])**2)
            dp = -ap / (1 - ap)
            am = (X[k-1].real*X[k].real + X[k-1].imag*X[k].imag) / (abs(X[k])**2)
            dm = am / (1 - am)
            d = (dp + dm)/2 + tau(dp*dp) - tau(dm*dm)
            return k + (d if np.isfinite(d) and abs(d) < 1 else 0.0)
        except Exception:
            return float(k)

    def _analysis_slot(self, gr):
        P = self.P
        Xc = np.fft.rfft(self.sc_buf * self.win)
        M = np.abs(Xc)
        df = FS_SC / NFFT
        # ---- 供给层:候选提取 = top-N 相对 + 频带门,**无绝对电平门**(IF-v1.4 C4)
        klo, khi = int(P.f_det_lo/df), min(int(P.f_det_hi/df), len(M)-3)
        loc = [k for k in range(max(2, klo), khi)
               if M[k] > M[k-1] and M[k] >= M[k+1]]
        loc.sort(key=lambda k: -M[k])
        cands = loc[:P.n_cand]
        if 'B1' in self.B:                                     # broken:检测器 stub
            cands = []
        table_full = (len(loc) > P.n_cand)
        self.ctr['slots'] += 1
        if table_full: self.ctr['table_full'] += 1
        min_cand_mag = min([M[k] for k in cands]) if cands else 0.0

        # ---- GR 遥测(IF-v1.4 C11);broken B7 禁用
        # IF-v1.4 C11 作用域:out_lim(逐母线)+ dynEQ_in(本通道 8 段动态 PEQ)
        # 判断(θ_route/聚合)归本层;这里按"与本通道环路相关"取或
        gr_active = bool(gr.get('out_lim_active', False)) or bool(gr.get('dyn_active', False))
        if 'B7' in self.B:
            gr_active = False
        self.gr_hist = self.gr_hist + 1 if gr_active else 0
        gr_ok = self.gr_hist >= P.N_gr

        # ---- G0 门 + 候选门
        obs = {}
        for k in cands:
            lv = self._level(M, k)
            pa, pn = self._papr(M, k), self._pnpr(M, k)
            gate = P.T_low
            relaxed = False
            if not ('B8' in self.B):
                # ★ F4 修法(原型 v2):放宽门有**两个**前提,acquisition 与 maintenance 分开
                #   (a) GR 持续 active —— 原条件,负责**首次获取**(此时本层还没挂陷波)
                #   (b) 本层在该频点**已挂陷波**(槽非 FREE 且 |Δf| ≤ BW/2)—— 负责**维持**
                # 为什么必须有 (b):GR 只是"此处有被钉住的啸叫"的**代理量**;算法一旦成功,
                #   限幅器松开 ⇒ 代理量消失 ⇒ 放宽自熄灭 ⇒ 看不见自己正在压的那个峰
                #   ⇒ "复发→加深"永久失效(F4)。(b) 依赖的是**本层已采取的动作**,
                #   不依赖"此刻能否观察到该峰",故打断了"观察成功→治好→观察不到"的循环。
                cov = self._notch_covers(k * df)
                if 'B13' in self.B:            # broken:退回 v1.4 行为(仅 GR 决定)
                    cov = False
                if gr_ok or cov:
                    gate = P.T_low_gr
                    relaxed = lv < P.T_low
            if lv < gate:
                continue
            if pa < P.T_papr or pn < P.T_pnpr:
                continue
            f = self._quinn(Xc, k) * df
            obs[k] = dict(f=f, lv=lv, papr=pa, pnpr=pn, relaxed=relaxed)

        self._update_tracks(obs, M, df, table_full, min_cand_mag, gr_ok)
        howls = self._classify(M, df, gr_ok)
        self._allocate(howls)
        self._slots_tick()
        self.log.append(dict(seq=self.slot_seq, t=self.t_wall, n_cand=len(cands),
                             n_track=sum(1 for t in self.tracks if t.active),
                             howls=[(h['cls'], round(h['f'], 1)) for h in howls],
                             gr=gr_active,
                             notches=[(round(s.f, 1), round(s.depth, 1))
                                      for s in self.slots if s.st != NotchSlot.FREE]))

    # ---------------- IPMP 跟踪(可切换模块:专利隔离)----------------
    def _pair(self, tr, obs, df):
        if self.ipmp_mode == 'off':
            return None
        best, bestd = None, 1e9
        for k, o in obs.items():
            d = abs(o['f'] - tr.f)
            tol = max(0.25 * df, 0.01 * tr.f) if self.ipmp_mode == 'px4' else 0.5 * df
            if d < tol * 4 and d < bestd:
                best, bestd = k, d
        return best

    def _update_tracks(self, obs, M, df, table_full, min_cand_mag, gr_ok):
        P = self.P
        used = set()
        for tr in self.tracks:
            if not tr.active:
                continue
            k = self._pair(tr, {k: o for k, o in obs.items() if k not in used}, df)
            if k is not None:
                used.add(k); o = obs[k]
                self._track_hit(tr, o, gr_ok)
            else:
                self._track_missing(tr, M, df, table_full, min_cand_mag, gr_ok)
        # 新轨(常规门优先于放宽门,§5.3 准入优先级)
        for k, o in sorted(obs.items(), key=lambda kv: kv[1]['relaxed']):
            if k in used:
                continue
            if any(t.active and abs(t.f - o['f']) < max(0.25*df, 0.01*o['f'])*4
                   for t in self.tracks):
                continue
            slot = self._alloc_track(o)
            if slot is None:
                continue
            self._birth(slot, o, gr_ok)

    def _alloc_track(self, o):
        for t in self.tracks:
            if not t.active:
                return t
        cand = [t for t in self.tracks if t.relaxed and t.hit_n < 3]
        if cand:
            return min(cand, key=lambda t: t.hit_n)
        if 'B12' in self.B:
            return None
        cand = [t for t in self.tracks if t.unobs_run > self.P.U_max]   # 锁3:保护有条件
        return min(cand, key=lambda t: t.unobs_run) if cand else None

    def _birth(self, tr, o, gr_ok):
        P = self.P
        tr.__init__()
        tr.active = True; tr.f = o['f']; tr.fmed = [o['f']]
        tr.papr_hist = [o['papr']]; tr.seq_hist = [self.slot_seq]; tr.hist_n = 1
        tr.t_born = self.slot_seq; tr.t_born_wall = self.t_wall
        tr.t_last_seen = self.slot_seq; tr.last_obs_seq = self.slot_seq
        tr.obs_n = 1; tr.hit_n = 1; tr.relaxed = o['relaxed']
        tr.last_level = o['lv']; tr.t_half_wall = self.t_wall
        # 影子继承(§3.2 修正1):继承 causal_ok 布尔,**不继承裸时间戳**
        for sh in list(self.shadows):
            if abs(sh.f - o['f']) > self._bw_hz(o['f']) / 2:
                continue
            if self.t_wall - sh.t_removed_wall > P.T_shadow_s:
                continue
            # ★ F9(修 F4 时掉出来的新证伪项):v1.4 设计件 §3.2 缓解② 要求继承时
            #   "GR 仍 active"。但**重生的那一刻啸叫刚开始长回来、还没顶到天花板**,
            #   限幅器尚未动作 ⇒ gr_ok 恒 False ⇒ **影子继承永不发生**(实测 shadow_new=4/继承=0)。
            #   这与 F4 是**同一个病**:拿 GR(代理量)当"啸叫存在"的前提,而机制恰恰
            #   必须在"啸叫尚未到达天花板"时工作。
            #   修法同构:改用非自指证据 —— 该频点有本层已挂/正在 LIFT 的陷波。
            cov_inh = self._notch_covers(o['f'])
            if 'B13' in self.B:      # 双禁用:两个 notch-keyed 出口一起关(同 B7 范式)
                cov_inh = False
            if not (gr_ok or cov_inh):
                continue
            if 'B11' in self.B:                     # broken:继承裸时间戳(v1.2 行为)
                tr.t_veto = int(sh.t_removed_wall / P.T_hop)
                tr.causal_ok = False
            else:
                tr.causal_ok = sh.causal_ok
            tr.rapid_onset = sh.rapid_onset
            # ★ F10(修 F9 时又掉出来的一条):v1.4 设计件 §3.2 缓解③ 要求继承
            #   "已累计的 PERSIST 驻留信用"。但**轨是因为连续未命中才死的**,
            #   ⇒ 死亡时刻的信用恰是**命中率最差**的那一份;继承它反而**毒化**重生轨,
            #   使其比从零开始更慢达到 PERSIST(实测:开启信用继承后 F4 场景由
            #   末 −46.8dB 退化到 −9.0dB 仍在啸)。
            #   处置:**只继承豁免签名(causal_ok / rapid_onset,即 -2 的原始提案),
            #   不继承数值信用**。信用继承须待 ROC 给出"按死亡前最佳窗口继承"的口径。
            if P.inherit_credit:
                age = (self.t_wall - sh.t_removed_wall) / max(P.T_shadow_s, 1e-9)
                decay = max(0.0, 1.0 - age)
                tr.obs_n += int(sh.obs_c * decay); tr.hit_n += int(sh.hit_c * decay)
            self.shadows.remove(sh)
            self.events.append((self.slot_seq, 'shadow_inherit', round(o['f'], 1)))
            self.ctr['shadow_inherit'] += 1
            break

    def _track_hit(self, tr, o, gr_ok):
        P = self.P
        tr.f = o['f']; tr.fmed = (tr.fmed + [o['f']])[-7:]
        tr.papr_hist = (tr.papr_hist + [o['papr']])[-P.W_long:]
        tr.seq_hist = (tr.seq_hist + [self.slot_seq])[-P.W_long:]
        tr.hist_n = min(tr.hist_n + 1, P.W_long)
        tr.t_last_seen = self.slot_seq; tr.last_obs_seq = self.slot_seq
        tr.obs_n += 1; tr.hit_n += 1; tr.miss_run = 0; tr.unobs_run = 0
        tr.last_level = o['lv']
        if o['relaxed']:
            tr.relaxed = True
        # 折半:墙钟触发(m-1 勘正:窗长是墙钟量,分母是可观测槽)
        if self.t_wall - tr.t_half_wall >= P.P_persist_s:
            tr.obs_n //= 2; tr.hit_n //= 2; tr.t_half_wall = self.t_wall
        # 臂2 快升入台签名
        h = tr.papr_hist
        if len(h) >= P.MIN_PLAT + 1:
            for i in range(len(h) - P.MIN_PLAT):
                for j in range(i+1, min(i + P.N_RISE, len(h) - P.MIN_PLAT) + 1):
                    if h[j] - h[i] >= P.R_RISE and np.std(h[j:]) <= P.S_PLAT:
                        tr.rapid_onset = True

    def _track_missing(self, tr, M, df, table_full, min_cand_mag, gr_ok):
        P = self.P
        # maintenance:候选表满 ∧ 本轨弱于表内最小 ⇒ 直读主谱复测(§1.2-B)
        k = int(round(tr.f / df))
        unobs = False
        if 0 < k < len(M) - 1:
            if table_full and M[k] < min_cand_mag:
                lv, pa, pn = self._level(M, k), self._papr(M, k), self._pnpr(M, k)
                if pa >= P.T_papr and pn >= P.T_pnpr:
                    self._track_hit(tr, dict(f=tr.f, lv=lv, papr=pa, pnpr=pn,
                                             relaxed=tr.relaxed), gr_ok)
                    self.ctr['readback_ok'] += 1
                    return
                unobs = True
        if 'B10' in self.B:                     # broken:未观测一律当未命中
            unobs = False
        if unobs and tr.unobs_run > P.U_max: self.ctr['umax_hit'] += 1
        if unobs and tr.unobs_run <= P.U_max:
            tr.unobs_run += 1
            self.ctr['unobs'] += 1
            return                              # 不计老化、不进分母
        tr.unobs_run = 0
        tr.obs_n += 1; tr.miss_run += 1
        if self.t_wall - tr.t_half_wall >= P.P_persist_s:
            tr.obs_n //= 2; tr.hit_n //= 2; tr.t_half_wall = self.t_wall
        age_lim = P.U_hold if gr_ok else P.age_miss
        if tr.miss_run >= age_lim:
            self.shadows.append(Shadow(tr.f, self.t_wall, tr.causal_ok, tr.rapid_onset,
                                       tr.obs_n, tr.hit_n))
            self.ctr['shadow_new'] += 1
            self.shadows = self.shadows[-P.NT:]
            tr.active = False

    # ---------------- 分类 ----------------
    def _bw_hz(self, f):
        return max(f * self.P.bw_oct, 15.0)

    def _notch_covers(self, f):
        """F4:该频点是否处在本层**已挂陷波**的覆盖内(含 LIFT/STANDBY)。

        退出条件 = 该槽走完自己的生命周期(LIFT 抬到 0dB → STANDBY → reclaim 到期 → FREE)。
        **这不是"再挂个 hold 计时器"**:LIFT 会真的把深度还回去、真的改变环路增益,
        然后看啸叫回不回来 —— 那是**对物理世界做实验**,不是对自身信念做推论。
        故退出判据非自指:世界回答"还需不需要压",而不是算法回答"我还看不看得见"。
        """
        for sl in self.slots:
            if sl.st == NotchSlot.FREE:
                continue
            if abs(sl.f - f) <= self._bw_hz(sl.f) / 2:
                return True
        return False

    def _imsd(self, tr):
        P = self.P
        if tr.hist_n < P.W_long:
            return False, 0.0
        y = np.array(tr.papr_hist[-P.W_long:], float)
        sq = np.array(tr.seq_hist[-P.W_long:], float)
        x = sq - sq[0] if 'B9' not in self.B else np.arange(len(y), dtype=float)
        span = x[-1]
        # 空号护栏:v1.4 用 2(span+1)>3W(空号>W/2 即拒)。原型实测该取值在跳槽下
        # **频繁拒判**,把"算得不准"换成"干脆不算",闭环里后者代价更大(F2)。
        # 改为参数化,默认放宽到"空号 ≤ W_used"(span+1 ≤ 2W);门限入 ROC。
        if 'B9' not in self.B and (span + 1) > P.gap_guard_ratio * P.W_long:
            self.ctr['gapguard'] += 1
            return False, 0.0                       # 窗内空号过半:不出判定
        b, c = np.polyfit(x, y, 1)
        s = float(np.sqrt(np.mean((y - (b*x + c))**2)))
        dP = y[-1] - y[0]
        ok = (P.beta(P.beta_min_dbs) <= b <= P.beta(P.beta_max_dbs)
              and s <= P.s_max and dP >= P.dP_min)
        return bool(ok), float(b)

    def _phpr_veto(self, tr, M, df, imsd_hit, gr_ok, persist_path):
        """PHPR 谐波族否决 + 三臂豁免。豁免式 = 族最大 ∧ 因果时序 ∧ (臂1∨臂2∨臂3∧dom)"""
        P = self.P
        if 'B5' in self.B:
            return False
        k = int(round(tr.f / df))
        if not (0 < k < len(M)):
            return False
        veto = False
        k2 = int(round(tr.f/2 / df))
        if k2 > 2 and 20*np.log10(M[k2]/(M[k]+1e-30)+1e-30) >= -P.D_sub:
            veto = True
        for n in (2, 3):
            kn = int(round(tr.f*n / df))
            if kn < len(M) and 20*np.log10(M[kn]/(M[k]+1e-30)+1e-30) >= -P.D_harm:
                veto = True
        if not veto:
            return False
        if tr.t_veto < 0:
            tr.t_veto = self.slot_seq
        # 合取门 ①族内最大
        fam_max = True
        for n in (2, 3):
            kn = int(round(tr.f*n / df))
            if kn < len(M) and M[kn] > M[k]:
                fam_max = False
        # 合取门 ②因果时序(重生轨用继承的 causal_ok)
        causal = tr.causal_ok or ((tr.t_veto - tr.t_born) >= P.causal_min)
        if causal:
            tr.causal_ok = True
        # ③臂
        arm1 = imsd_hit
        arm2 = tr.rapid_onset
        dom = self._is_dom(tr)
        arm3 = gr_ok and persist_path and dom
        exempt = fam_max and causal and (arm1 or arm2 or arm3)
        return not exempt

    def _is_dom(self, tr):
        """臂3 谓词 dom:本通道已跟踪轨中 PNPR 最高者(局部统计,§3.2 修正2)。"""
        act = [t for t in self.tracks if t.active]
        if not act:
            return False
        return tr is max(act, key=lambda t: (t.papr_hist[-1] if t.papr_hist else -99))

    def _classify(self, M, df, gr_ok):
        P = self.P
        out = []
        for tr in self.tracks:
            if not tr.active or tr.hit_n < 1:
                continue
            imsd_hit, b = self._imsd(tr)
            if 'B4' in self.B:
                imsd_hit = False
            cls = None
            if tr.last_level >= P.T_panic and not tr.relaxed:
                cls = 'PANIC'
            elif (imsd_hit or tr.rapid_onset) and not tr.relaxed:
                if not self._phpr_veto(tr, M, df, imsd_hit, gr_ok, False):
                    cls = 'GROWTH'
            if cls is None:
                need = max(1, int(P.P_persist_s / P.T_hop * 0.5))
                rate = tr.hit_n / max(tr.obs_n, 1)
                gate = P.T_papr_high
                if tr.obs_n >= need and rate >= P.persist_hit_rate \
                        and (tr.papr_hist[-1] if tr.papr_hist else -99) >= gate:
                    if not self._phpr_veto(tr, M, df, imsd_hit, gr_ok, True):
                        cls = 'PERSIST'
            if cls:
                out.append(dict(cls=cls, f=float(np.median(tr.fmed)), tr=tr,
                                lv=tr.last_level, b=b))
        out.sort(key=lambda h: (h['cls'] != 'PANIC', -h['b']))
        return out[:1] if out and out[0]['cls'] != 'PANIC' else out[:2]

    # ---------------- 状态机 / 分配 ----------------
    def _allocate(self, howls):
        P = self.P
        for h in howls:
            f = h['f']; bw = self._bw_hz(f)
            same = [s for s in self.slots if s.st != NotchSlot.FREE and abs(s.f - f) <= bw/2]
            if same:
                s = same[0]
                if s.st == NotchSlot.STANDBY:
                    s.st = NotchSlot.ENGAGE; s.target = P.depth0
                else:
                    s.target = max(P.max_depth, s.target + P.depth_step)
                    s.st = NotchSlot.ENGAGE
                s.t_last_hit = self.t_wall
                self.events.append((self.slot_seq, 'deepen', round(f, 1)))
                continue
            free = [s for s in self.slots if s.st == NotchSlot.FREE]
            if not free:
                free = sorted([s for s in self.slots if s.st == NotchSlot.STANDBY],
                              key=lambda s: s.t_last_hit)
            if not free:
                self.g_duck_db = max(-6.0, self.g_duck_db - 1.0)   # 宽带兜底(§4.4)
                self.events.append((self.slot_seq, 'duck', round(self.g_duck_db, 1)))
                continue
            s = free[0]
            s.st = NotchSlot.ENGAGE; s.f = f; s.depth = 0.0
            s.target = P.depth0 if h['cls'] != 'PANIC' else -9.0
            s.t_last_hit = self.t_wall
            self.events.append((self.slot_seq, f"engage-{h['cls']}", round(f, 1)))

    def _slots_tick(self):
        P = self.P
        dt = P.T_hop
        for s in self.slots:
            if s.st == NotchSlot.FREE:
                continue
            if s.st == NotchSlot.ENGAGE:
                step = P.ramp_db_per_s * dt
                s.depth = max(s.target, s.depth - step)
                if abs(s.depth - s.target) < 1e-6:
                    s.st = NotchSlot.HOLD
            elif s.st == NotchSlot.HOLD:
                if self.t_wall - s.t_last_hit >= P.lift_after_s and 'B6' not in self.B:
                    s.st = NotchSlot.LIFT; s.t_lift = self.t_wall
            elif s.st == NotchSlot.LIFT:
                if self.t_wall - s.t_lift >= P.lift_step_s:
                    s.depth = min(0.0, s.depth + 3.0); s.t_lift = self.t_wall
                    s.target = s.depth
                if s.depth >= -1e-9:
                    s.st = NotchSlot.STANDBY; s.t_last_hit = self.t_wall
            elif s.st == NotchSlot.STANDBY:
                if self.t_wall - s.t_last_hit >= P.reclaim_s:
                    s.st = NotchSlot.FREE
            coef_fs = 44100.0 if 'B3' in self.B else FS      # broken:错误 fs
            s.set_coef(FS, P.bw_oct, coef_fs=coef_fs)
        if self.g_duck_db < 0 and not any(s.st == NotchSlot.ENGAGE for s in self.slots):
            self.g_duck_db = min(0.0, self.g_duck_db + 1.0 * dt)
