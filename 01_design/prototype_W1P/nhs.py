"""W1-P 宿主原型 · NHS 算法核心(浮点)
adaptive-dsp(第 3 实例)· 2026-08-01 · 全部产出 [L2/宿主仿真]

对应设计件 `01_design/W1B_NHS_algorithm_design.md` v1.4(已冻结,本文件不改它)。
**本阶段只验算法行为,不做定点**(阶段 2 再移植)。

可复用件溯源(lead 清单):
  - PAPR 式:PX4 `GyroFFT.cpp:514` 同构(其对**幅度比**取 10log10;本文按设计件
    §1.2 勘正为 **20log10 = 常规 dB**,PX4 参数值不可直搬)。
  - IPMP:PX4 最近频率配对 + 0.25bin 豁免 + 7 点中值 + 100ms 老化(移植重标)。
  - Quinn 第二估计器:PX4 `EstimatePeakFrequencyBin` 同式浮点重写。
  - RBJ peaking(负增益)biquad,**系数式**出自 RBJ Cookbook(W0 已核);
    ⚠ **实现结构 = DF2T,非 DF1**(`scipy.signal.lfilter(b,a,·,zi=·)` 即转置直接II型)。
    本行此前写 "DF1" 是错的(r9 勘正)。定点移植**必须显式选型**:DF1 与 DF2T
    在此不等价 —— 陷波器 Q≈7.2(bw=1/5 oct)时 DF2T 的状态变量承载中间和,
    其溢出点与 DF1 的抽头和不同;`zi` 的物理含义也随结构改变。
    移植件须自证所选结构,不得默认"照抄 b/a 即可"。
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

# ★ r9 勘正(MAJOR):深度状态机跃迁的容差。
#   原实现用 `1e-6` / `1e-9` dB 做 ENGAGE→HOLD 与 LIFT→STANDBY 的判据。它们在本
#   浮点原型里"能work",**只因为斜坡两端各有一次精确钳位**(`max(target,·)` /
#   `min(0.0,·)`)把差值压成 exact 0.0 —— 也就是说这两个数不是容差,是**伪装成容差
#   的精确相等判断**。定点移植会两头翻车:
#     · dB 量以 Q7.8 存 ⇒ 量化步长 3.9e-3 dB,比 1e-6 大三个数量级。若移植件的斜坡
#       用饱和减法累加而非精确钳位,`|depth-target| < 1e-6` **永不成立**
#       ⇒ 槽位卡死在 ENGAGE,depth 到位但状态机不迁移,lift 计时永不启动。
#     · 同理 `depth >= -1e-9` 退化为"精确等于 0";若舍入把 depth 留在 -0.0039dB,
#       槽位**永不**回 STANDBY ⇒ 槽位泄漏,可用槽单调减少直至全部耗尽。
#   取值依据:须 << 一个斜坡步长(ramp 60dB/s × T_hop 16ms = **0.96 dB**),
#   且 >> 定点量化步长(Q7.8 = 3.9e-3 dB)。0.05dB 距上界 19×、距下界 12.8×。
#   [L2/宿主仿真] 本值是设计裕度推算,非实测标定;定点移植须按实际 Q 格式复核。
DEPTH_EPS_DB = 0.05
from scipy.signal import firwin as _firwin
_AA_LP = _firwin(49, 0.9 * (FS_SC / 2) / (FS / 2))   # 抽取抗混叠低通


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
        self.causal_min = 2          # ⛔ r12 作废:旧 causal 口径(轨龄 vs 否决起点),实测恒真
        # ── ⭐ r66 判据组合开关(2026-08-03,lead 裁定"路 A";**默认 False = 现行行为**)
        #   True  ⇒ GROWTH 入选式关掉 `rapid_onset` 那条 OR 旁路,退化为「必须 IMSD 命中」
        #   缘由:JAES 2010 Table 2 的最优组合是三项【逻辑与】(PHPR∧PNPR∧IMSD,PD=95% 时 PFA=3%),
        #        而我方 `:860` 用 `(imsd_hit ∨ rapid_onset)` 把 AND 拆成了 OR。
        #   ⚠ **不得据此宣称"复现了原文最优组合"** —— 原文的 IMSD 是【谱距离,QM 帧/0.5dB】,
        #     我方 `_imsd` 是【自研构型:PAPR 轨迹 LS 斜率,dB/s】,是两个不同的量(r66 §1)。
        #   ⚠ 只改 `:860` 一处;`rapid_onset` 在 PHPR 否决豁免臂 2(`_phpr_veto` 内)另有用途,
        #     全局置假会连带改动那一处 = 两处一起改。
        self.growth_and_gate = False
        # ── ⭐ r75 分配名额优先级开关(2026-08-03,lead 裁定;**默认 False = 现行行为**)
        #   True ⇒ `_classify` 截断前的排序键插入「是否已挂陷」布尔秩
        #          ⇒ 每槽唯一的 howl 名额优先给【尚未被挂】的峰
        #   缘由:`nhs.py:891` `return out[:1]...` 是硬截断 ⇒ 供给恒为 1 howl/槽;
        #        而排序键 `(不是PANIC, −b)` 里**没有"是否已挂陷"项**
        #        ⇒ 已挂峰的复检只要斜率高就能挤掉未挂的新峰 ⇒ 饿死(F52/F55)。
        #   ⚠ 不引入任何新阈值:`_notch_covers` 是既有谓词(`:711`),只是上提到排序键。
        self.prefer_unnotched = False
        # ── r12 新判据(IF-v1.8):族成员到达时刻 vs 候选自身增长起点
        self.grow_onset_db = 3.0     # 候选自身"增长起点" = 电平较诞生电平上升 ≥ 此值
        self.fam_late_min = 2        # 族成员须**晚到** ≥ 此槽数,才算因果下游
        self.R_RISE, self.N_RISE, self.S_PLAT, self.MIN_PLAT = 18.0, 2, 2.0, 3
        self.T_exempt_s, self.T_shadow_s = 10.0, 60.0
        self.N_gr = 2
        self.inherit_credit = False   # F10:数值信用继承默认**关**(实测有害)
        # 陷波(§4)
        self.bw_oct, self.depth0, self.depth_step, self.max_depth = 1/5, -3.0, -3.0, -18.0
        self.ramp_db_per_s = 3.0 / 0.050
        self.lift_after_s, self.lift_step_s, self.reclaim_s = 60.0, 5.0, 30.0
        # ── C8-②(IF-v1.8)事后甄别探针:**物理实验,非统计推断**(与 C11-① LIFT 探针同范式)
        #   真挂浅陷 → 测该 bin 在 **tap** 上的实际下降 → 判 → 外部音则快撤。
        # ⚠ 阈值参照与合同表**不同**:合同表设观测点在陷波**之后**(外部音 ⇒ ΔL≈d);
        #   本实现 tap 在陷波器**之前**(C10 v1.6)⇒ 陷波在 tap 下游、不影响 tap 读数
        #   ⇒ **外部音的预期是 ΔL ≈ 0**,啸叫是"环路被打断"的大幅下降。判据结构不变
        #   (啸叫 ≫ 外部音),但门须对着 0 设,不是对着 d 设。已报架构侧走 C9。
        self.probe_hops = 16         # 挂陷后观察槽数(16×16ms = **256ms**)
        #   ⚠ 窗长**两侧都有物理边界**,不是任意取值(r13 实测,见 results_w1p_r13):
        #     下界:128ms 时环路尚未衰落 ⇒ 啸叫 ΔL 中位仅 2.43dB,与外部音**完全重叠**;
        #     上界:1024ms 时外部素材自身已变(音符结束)⇒ 外部音 ΔL max 涨到 29.4dB,
        #           重叠**再次出现**。256ms 是两条边界之间的窗口。
        self.probe_thr_db = 8.0      # (C8-② 遗留,C8-③ 后不再用于判定)
        # ── C8-③(IF-v1.8 差分形式):修 F25「探针没有对照」
        #   判外部 ⟺ |ΔL_f − ΔL_rest| ≤ X   ← **正向有界断言**(声称二者接近)
        #   判啸叫 ⟺ 否则                    ← **默认分支**(残余良性:留一个空频点浅陷,LIFT 回收)
        # ⚠ 方向说明(r14 §0.1 已提出反对,写在实现之前):
        #   转来的字面式是「判外部 ⟺ (ΔL_f − ΔL_rest) > X」,但那会把**真啸叫**
        #   (ΔL_f 大、ΔL_rest≈0 ⇒ 差分大)判成外部并撤陷 = **漏检**,
        #   恰是硬要求①明令避免的残余 ⇒ 判为符号方向笔误,按上式实现。
        self.probe_X_db = 8.0        # [L4/待 ROC];D-H 两端各有**不同机制**的论证:
        #   下界(太小):估计方差 —— 外部持续音 ΔL 波动实测 max 3.77dB ⇒ 噪声即可越门
        #                ⇒ 判啸叫 ⇒ 陷波留在乐音上 ⇒ 已归零四类劣化。须 > 4dB。
        #   上界(太大):环路打断幅度上限 —— 啸叫差分 ≈ ΔL_f,实测 p10 = 18.22dB
        #                ⇒ X ≳18 时真啸叫落进"判外部"区 ⇒ **撤掉真啸叫 = 漏检**。须 < 18dB。
        #   取 8.0:距下界 4.2dB、距上界 10.2dB,偏下界侧(代价不对称:漏检 ≫ 多留陷波)。
        # ★ r24 P0:**测量有效性门**(不是门限)。数值底 = 20log10(1e-30) = −600dB;
        #   T_low = −45dBFS;真实音频不可能到 −250dBFS
        #   ⇒ 该门**只拒绝数值退化的读数,物理上不可能拒绝任何真实候选** = 最弱的门。
        #   ⚠ 它**不触碰"历史累积判定"**:轨仍可凭累积被判 PERSIST;
        #     被拦的只有"当前帧根本没有测量"。洞是**在无观测帧上挂陷**,不是依赖累积。
        self.level_valid_db = -250.0
        self.probe_floor_M = 10.0    # ★ r15 机制B:弃权门。L0/L1 均须 > 底噪 + M,否则**弃权**
        #   D-H 两端(不同机制):下界 = 本底估计不确定度(1024点Hann 单bin 噪声 2自由度 χ²,
        #     σ≈5.6dB;M≲6 时纯噪声起伏即被当作有效读数 ⇒ ε 地板伪值仍进判定)⇒ M>6;
        #     上界 = 真啸叫早期低电平段被逐出定义域(候选入选前提已是 PAPR≥T_papr=15dB;
        #     M≥15 则凡合法候选皆可能弃权 ⇒ 机制空转 = 漏检向)⇒ M<15。取 10.0。[L4]
        self.rest_excl_bw = 1.0      # ΔL_rest 剔除 f 的 ±此倍陷波带宽。D-H 两端:
        #   太窄 ⇒ 陷波/啸叫自身裙边漏进 rest ⇒ 共模被"自己"污染 ⇒ 差分被压小 ⇒ 漏检向;
        #   太宽 ⇒ rest 基底变小方差变大 + 剔掉同源邻近谐波 ⇒ 抵消力下降 ⇒ 假啸叫回升。
        #   256ms 实测间隔:外部音 max **3.77dB** ── 间隔 14.5dB ── 啸叫 p10 **18.22dB**。
        #   取 8.0 偏向外部音一侧,因**代价不对称**:撤掉真啸叫(漏检)远重于多留一个陷波。
        #   距啸叫 p10 有 10.2dB 余量,距外部音 max 有 4.2dB 余量。
        self.ext_ttl_s = 20.0        # 判为外部音后该频点的保鲜期(避免每次误报都探一遍)
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
        self.exhausted_flag = False # ★ r17c:本次占用是否已记过 EXHAUSTED(防每复检重复计数)
        # ★★ r27 结构性修法(架构侧裁定):**豁免条件必须写成肯定式**。
        #   原实现 `not from_abstain` 是**否定式** ⇒ 任何**新增的无判决类别**默认落进
        #   「刷新租约」这一支 = **危险侧** ⇒ 每加一条无判决路径,就自动重新引入
        #   C6-② 修掉的无限推迟 bug(仪表故障孤儿即此)。
        #   改为肯定式:**只有持有肯定分类结论的占用才刷新租约**;
        #   弃权 / 仪表故障 / 未来任何新类别 **一律默认不刷新 = 安全侧**。
        #   ⚠ 倒下的不是 C6-② 那条修法,是**它的适用范围没有随新路径扩张**。
        self.has_affirmative_verdict = False   # ★ 肯定式:仅"判啸叫"时置位
        self.from_abstain = False   # ★ r17:保留供诊断分类;**不再用于安全分支**
        self.lv_pre = None          # ★ r15 机制③:挂陷前该 bin 电平(LIFT 回归判定基准)
        self.zi = np.zeros(2)
        self._coef_key = None
        self.t_last_hit = 0.0; self.t_lift = 0.0

    def set_coef(self, fs, bw_oct, coef_fs=None):
        # ★ C6 修:原实现**每槽对每个非 FREE 槽无条件重算**(实测 2.68 次/槽,
        #   8 槽全占时达 8 次/槽,超 C6 的 1.5 次/槽上限 5.3×),
        #   而实测**参数真正改变**只有 0.298 次/槽 ⇒ **88.9% 是无谓重算**。
        #   C6 的立法理由是执行器队列排空(最坏 64 滤波器/85ms),
        #   超速会造成队列积压与深度斜坡失序 —— 功能性问题,不只是算力。
        #   改为**仅在 (f, depth, bw, 状态) 实际变化时重算**。
        key = (self.st, round(self.f, 6), round(self.depth, 6), round(bw_oct, 6),
               coef_fs or fs)
        if key == getattr(self, '_coef_key', None):
            return
        self._coef_key = key
        if self.st == self.FREE or self.depth >= -DEPTH_EPS_DB:
            self.b = np.array([1.0, 0, 0]); self.a = np.array([1.0, 0, 0]); return
        self.b, self.a = rbj_peaking(coef_fs or fs, self.f, self.depth, bw_oct)


# ---------------------------------------------------------------- 轨(Track)
class Track:
    __slots__ = ('active', 'f', 'fmed', 'papr_hist', 'pnpr_hist', 'seq_hist', 'hist_n', 't_born',
                 't_last_seen', 'obs_n', 'hit_n', 't_veto', 'miss_run', 'unobs_run',
                 'rapid_onset', 'relaxed', 'causal_ok', 'last_level', 'last_obs_seq',
                 't_born_wall', 't_half_wall', 'lv0', 't_grow0', 't_fam0')

    def __init__(self):
        self.active = False; self.f = 0.0; self.fmed = []
        self.papr_hist = []; self.pnpr_hist = []; self.seq_hist = []; self.hist_n = 0
        self.t_born = 0; self.t_last_seen = 0; self.obs_n = 0; self.hit_n = 0
        self.t_veto = -1; self.miss_run = 0; self.unobs_run = 0
        self.rapid_onset = False; self.relaxed = False; self.causal_ok = False
        self.last_level = -120.0; self.last_obs_seq = 0
        self.t_born_wall = 0.0; self.t_half_wall = 0.0
        self.lv0 = -120.0; self.t_grow0 = -1; self.t_fam0 = -1


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
        self._aa_tail = np.zeros(len(_AA_LP) - 1)
        self.slot_seq = 0
        self.t_wall = 0.0
        self.frame_i = 0
        self.win = np.hanning(NFFT)
        self.g_duck_db = 0.0
        self.events = []
        self.gr_hist = 0
        self.skip_plan = None               # 人为跳槽(B9 场景)
        self.log = []                       # 每槽快照
        self.p0_block_log = []      # ★ r26 纯遥测:P0 拦下的候选留痕
        self.c8_log = []            # C8-② 判决留痕
        self.probes = {}            # C8-② 在测探针:slot_idx -> dict
        self.ext_reg = []           # C8-② 外部音登记:[(f, 到期墙钟)]
        self.cls_log = []           # r11 分类归因(只记录)
        self.phpr_log = []          # r11 归因遥测(只记录)
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
        # ★ r9 勘正(MAJOR):宽带兜底衰减(§4.4)此前**只在 nhs.py 里算,不在 nhs.py 里施加**
        #   —— 8 个台架各自写 `y * gf * alg.duck_gain()`。后果:按 DEC-0016 只照本文件
        #   做 bit-exact 移植的 C 件会**完整实现 g_duck 的全部状态演化、然后把它扔掉**,
        #   槽位耗尽时的最后一道兜底静默消失,且因 duck 只在满槽时才动,常规测试测不到。
        #   现收进权威源。⚠ 施加点必须在陷波器**之后**(宽带兜底作用于链输出)。
        y = y * self.duck_gain()
        return y

    def _sidechain_push(self, x):
        # ★ 台架修(critic 第四条):3 点均值抗混叠严重不足
        #   (7k −2.6dB / 9k −4.6dB / 11k −7.5dB,而 9k/11k 会折叠回 7k/5k 检测带内)
        #   ⇒ 污染误报套件与 PAPR/PNPR 的分母。改为 48 阶 FIR 低通(截止 0.9×8k)。
        self.acc = np.concatenate([self.acc, x])
        k = (len(self.acc) // DEC) * DEC
        if k:
            seg = np.concatenate([self._aa_tail, self.acc[:k]])
            filt = np.convolve(seg, _AA_LP, mode='valid')
            self._aa_tail = seg[-(len(_AA_LP) - 1):] if len(_AA_LP) > 1 else np.zeros(0)
            d = filt[::DEC]
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
        # ★ M-1 修:Hann 窗相干增益 = 0.5 ⇒ 正弦峰值 = A*N/2*0.5 = A*N/4
        #   原式漏了这一项 ⇒ **全频段系统性低读 6.02dB**(critic 四频点实测 6.03dB)
        #   影响所有依赖绝对电平的结论(T_low_gr 失效临界 / bin 域折算 / F5)
        return 20 * np.log10(M[k] * 4.0 / NFFT + 1e-30) + self.cal

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
        # ── 漏斗遥测(r10;**只计数,不改行为**;D6-d 要求逐级条件分母)
        self.ctr['N0_locmax'] = self.ctr.get('N0_locmax', 0) + len(loc)
        self.ctr['N1_cand']   = self.ctr.get('N1_cand', 0)   + len(cands)
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
            self.ctr['N2_lvl'] = self.ctr.get('N2_lvl', 0) + 1
            if pa < P.T_papr or pn < P.T_pnpr:
                continue
            self.ctr['N3_gate'] = self.ctr.get('N3_gate', 0) + 1
            f = self._quinn(Xc, k) * df
            obs[k] = dict(f=f, lv=lv, papr=pa, pnpr=pn, relaxed=relaxed)

        self._update_tracks(obs, M, df, table_full, min_cand_mag, gr_ok)
        self._causal_scan(M, df)                       # ★ r12:须在 _classify 之前
        howls = self._classify(M, df, gr_ok)
        self.ctr['N5_howl'] = self.ctr.get('N5_howl', 0) + len(howls)
        self._allocate(howls, M, df)
        self._slots_tick()
        if 'B14' not in self.B:
            self._probe_tick(M, df)          # ★ C8-② 事后甄别
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
        self.ctr['N4_born'] = self.ctr.get('N4_born', 0) + 1   # 漏斗遥测(r10,只计数)
        tr.__init__()
        tr.active = True; tr.f = o['f']; tr.fmed = [o['f']]
        tr.papr_hist = [o['papr']]; tr.pnpr_hist = [o['pnpr']]
        tr.seq_hist = [self.slot_seq]; tr.hist_n = 1
        tr.lv0 = o['lv']; tr.t_grow0 = -1; tr.t_fam0 = -1        # ★ r12 因果时序基准
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
        tr.pnpr_hist = (tr.pnpr_hist + [o['pnpr']])[-P.W_long:]   # ★ B-1:此前被丢弃
        tr.seq_hist = (tr.seq_hist + [self.slot_seq])[-P.W_long:]
        tr.hist_n = min(tr.hist_n + 1, P.W_long)
        tr.t_last_seen = self.slot_seq; tr.last_obs_seq = self.slot_seq
        tr.obs_n += 1; tr.hit_n += 1; tr.miss_run = 0; tr.unobs_run = 0
        tr.last_level = o['lv']
        # ★ MAJOR 修:`relaxed` 原为**粘滞**(只置位不清除)⇒ 一旦经放宽门入轨,
        #   即使电平后来升到 0dBFS 也**终身**被挡在 PANIC/GROWTH 之外
        #   ⇒ **C12 的输入侧担保被一个粘滞标志架空**(critic 实证:0dBFS 轨判 PERSIST,
        #      置 False 后判 PANIC)。
        #   正解:relaxed 反映**当前**是否仍需放宽 —— 电平一旦够常规门 T_low,
        #   该轨不再需要放宽,应释放,恢复 PANIC/GROWTH 资格。
        tr.relaxed = bool(o['lv'] < self.P.T_low)
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
        # ★ P19(已落地,vP1.1):**删除 maintenance 直读**。
        #   依据:实测进入分支 3171 次,现行合取门过门比例 **0.0%**;PNPR 中位 −16dB
        #   ⇒ 「被挤出候选表」的绝大多数是该频点确实没有峰了,不是「峰在但排不进」。
        #   原代码块见 verdict 引用的 vP1.0 :427-433。
        k = int(round(tr.f / df))
        unobs = bool(0 < k < len(M) - 1 and table_full and M[k] < min_cand_mag)
        if 'B10' in self.B:                     # broken:未观测一律当未命中
            unobs = False
        # ★ P20(已落地,vP1.1):三态**降为诊断事件,不再参与老化决策**。
        #   依据:机制触达充分(未观测 3140 次)、内部效果符合预言(轨死亡 92 vs 43),
        #   但**输出级零差异**;且其危害前提已被 m-1 的 PERSIST 模型重写消除(F15)。
        if unobs:
            self.ctr['unobs'] += 1              # 仅计数上报,**不再 return**
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
    def _floor_level(self, M, df):
        """检测带内的稳健本底估计(中位数)。用于机制 B 的弃权门。
        取中位数而非均值:窄带峰不得抬高本底估计。"""
        P = self.P
        klo, khi = int(P.f_det_lo/df), min(int(P.f_det_hi/df), len(M) - 1)
        seg = M[max(2, klo):khi]
        if len(seg) == 0:
            return -300.0
        return 20 * np.log10(float(np.median(seg)) * 4.0 / NFFT + 1e-30) + self.cal

    def _rest_level(self, M, df, f):
        """C8-③ 共模基准:剔除 f 的 ±rest_excl_bw 个陷波带宽后,检测带内的能量和电平(dB)。
        ⇒ 它回答「这次下降里有多少是**整个源**一起掉的」—— 即 F25 指出探针缺的那个**对照**。
        ⚠ 硬要求②:本函数与 c8 判决**只写进 c8_log/ctr**,
           **「探针判为啸叫」不得被任何其他机制当作正向证据**(CHECK S 守着)。"""
        P = self.P
        klo, khi = int(P.f_det_lo/df), min(int(P.f_det_hi/df), len(M) - 1)
        half = self._bw_hz(f) * P.rest_excl_bw / 2.0
        ka, kb = int((f - half)/df), int((f + half)/df)
        seg = M[max(2, klo):khi].astype(float) ** 2
        idx = np.arange(max(2, klo), khi)
        seg = seg[(idx < ka) | (idx > kb)]
        return 10 * np.log10(float(seg.sum()) + 1e-30)

    # ══════════════════════════════════════════════════════════════════════
    # ⭐⭐ 不变量(架构侧预裁,**不是实现细节**):**探针必须在 tap 读**。
    #   C8-② 的判别力**完全**来自「tap 在陷波器组上游」:
    #     真啸叫被挂陷 ⇒ 环路断 ⇒ 源真跌 ⇒ **tap 看得见**;
    #     外部源     ⇒ 陷波在 tap 下游 ⇒ **tap 读数不变**。
    #   ⇒ **若把取数点挪到陷波下游,两类都会跌 ⇒ 判别力归零。**
    #   ⇒ 本函数的 `M` 必须来自 `_analysis_slot` 的 `sc_buf`(由 `_sidechain_push(x)` 喂,
    #     `x` = `process_frame` 入参 = 陷波器组**之前**)。**不得为省一次 FFT 挪到下游。**
    #   查证(r24):`process_frame` 首行即 `_sidechain_push(x)`,陷波在其后 ⇒ 现状正确。
    # ══════════════════════════════════════════════════════════════════════
    def _probe_tick(self, M, df):
        """C8-② 事后甄别 —— **物理实验**:浅陷已真挂上,这里只读它在 tap 上造成的实际后果。
        判据(不是统计量阈值,是对干预的响应):
          ΔL = L0 − L1 ≥ probe_thr_db  ⇒ **环路被打断** ⇒ 啸叫 ⇒ 保留
          ΔL 小                        ⇒ **源仍在**     ⇒ 外部持续音 ⇒ 撤陷 + 登记保鲜期
        ⚠ 先验不可分依然成立:本机制**不能在动作之前**区分,只把"事后以有界代价可分"变成可能。
        """
        P = self.P
        done = []
        for si, pr in self.probes.items():
            s = self.slots[si]
            k = int(round(pr['f'] / df))
            if not (0 < k < len(M)):
                done.append(si); continue
            if pr['L0'] is None:                       # 挂陷当槽:记下干预前读数
                pr['L0'] = self._level(M, k)
                # ⛔ r31 撤除:**成对读数一致性断言**已删。撤除依据(读码 + 实测双证):
                #   ①**原意在当前架构下不可实现**:判据路径(`lv = self._level(M,k)`)与
                #     探针路径(`pr['L0'] = self._level(M,k)`)**同 M、同函数、同 bin**
                #     ⇒ 同时刻读必然逐位相等 ⇒ 恒真、零分辨力
                #     (与"mic 置零对单边式恒真"同族)。它只能检出**时间**不一致。
                #   ②**它检出的那一类,P0 已在源头封死**:B 臂 176 例全是
                #     "L0 退化 ∧ lv_trig 有效",而 P0 直接不让退化帧挂陷。
                #   ③**P0 之后它只剩过触发**:r30 实测 C 臂 20 例故障
                #     **L0 退化 0% / lv_trig 退化 0% / 两者皆正常但不一致 100%**
                #     (|差| 中位 47dB)⇒ 吃掉的是**电平合法变化**的真实判决。
                #   ④它丢弃探针却保留陷波 ⇒ 制造"故障孤儿"(F31),B 臂占用 +21%。
                pr['R0'] = self._rest_level(M, df, pr['f'])     # ★ C8-③ 共模基准
                pr['FL'] = self._floor_level(M, df)             # ★ r15 本底基准
                s.lv_pre = pr['L0']                            # ★ r15 机制③ 基准
                continue
            if self.slot_seq - pr['seq0'] < P.probe_hops:
                continue
            if s.st == NotchSlot.FREE or abs(s.f - pr['f']) > self._bw_hz(pr['f'])/2:
                done.append(si); continue              # 槽已被改派,探针作废
            L1 = self._level(M, k)
            dL = pr['L0'] - L1
            dR = pr['R0'] - self._rest_level(M, df, pr['f'])    # ★ 共模(剔除 f 邻域)
            # ── ★ r15 机制 B:三态。L0/L1 任一不在有效量程 ⇒ **弃权**(第三态)
            #   弃权 ≠ 判啸叫,也 ≠ 判外部:保留陷波(偏置原则),但**不登记保鲜期**
            #   —— 登记是对"这是外部源"的正向断言,弃权没有作出该断言。
            fl = pr['FL'] + P.probe_floor_M
            if pr['L0'] <= fl or L1 <= fl:
                self.ctr['c8_abstain'] = self.ctr.get('c8_abstain', 0) + 1
                s.from_abstain = True                      # ★ r17:标记来源,供刷新条件与回收优先序用
                self.c8_log.append(dict(f=pr['f'], dL=float(dL), dR=float(dR),
                                        diff=float('nan'), cls=pr['cls'], verdict='abstain'))
                done.append(si); continue
            # ── ★ r15 机制 A:共模项**单边钳位**(rest 上升不携带"环路被打断"的信息,
            #   不得增加判啸叫的证据)+ **去绝对值**(f 处电平**上升**不可能是啸叫证据)
            diff = dL - max(dR, 0.0)
            is_ext = diff <= P.probe_X_db                       # (乙)本层主张
            is_ext_A = abs(diff) <= P.probe_X_db                # (甲)裁定①字面,仅记录不采用
            if not is_ext:
                self.ctr['c8_howl'] = self.ctr.get('c8_howl', 0) + 1
                s.from_abstain = False                     # ★ r17:已正向分类为啸叫
                s.has_affirmative_verdict = True           # ★★ r27 肯定式:唯一置位点
                self.events.append((self.slot_seq, 'c8-howl', round(pr['f'], 1)))
                # 硬要求③:「裸纯音停掉」**单独计数**(共模无从抵消:ΔL_f 巨大而 ΔL_rest≈0)
                #   ⚠ 纯诊断计数,**不参与任何判定**。
                if dL >= 30.0 and abs(dR) <= 3.0:
                    self.ctr['c8_bare_stop'] = self.ctr.get('c8_bare_stop', 0) + 1
            else:
                self.ctr['c8_ext'] = self.ctr.get('c8_ext', 0) + 1
                self.events.append((self.slot_seq, 'c8-ext-retract', round(pr['f'], 1)))
                s.st = NotchSlot.FREE; s.depth = 0.0; s.target = 0.0
                s.set_coef(FS, P.bw_oct)               # 真撤陷(系数回恒等)
                self.ext_reg.append((pr['f'], self.t_wall + P.ext_ttl_s))
            self.c8_log.append(dict(f=pr['f'], dL=float(dL), dR=float(dR), diff=float(diff),
                                    cls=pr['cls'], verdict='ext' if is_ext else 'howl',
                                    verdict_A='ext' if is_ext_A else 'howl'))
            done.append(si)
        # ── ★ r15 机制③(裁定③):**不新增探针**,只在既有 LIFT 释放处记录
        #   「该频点是否回来」。LIFT 的周期性释放本身就是"真把深度还回去"的物理实验,
        #   此前只是**不记录结果**。本轮补记录,作为模糊带/弃权带的**独立证据**。
        # ⚠ 已知局限(预注册 §0.4 已声明):「回来了」同时兼容 ①外部源仍在 ②环路仍热重新长起;
        #   单次不足以区分,能区分的是**回来的形状**(需多点采样)。
        #   ⇒ 本轮**只记录计数,不据以改判**。且结论在 lift_after_s(60s)后才到 ⇒ 仅事后裁决。
        for s2 in self.slots:
            if s2.st != NotchSlot.LIFT or s2.lv_pre is None:
                continue
            k2 = int(round(s2.f / df))
            if not (0 < k2 < len(M)):
                continue
            back = self._level(M, k2) >= s2.lv_pre - 6.0        # 回到挂陷前 6dB 以内 = "回来了"
            self.ctr['lift_obs'] = self.ctr.get('lift_obs', 0) + 1
            if back:
                self.ctr['lift_return'] = self.ctr.get('lift_return', 0) + 1

        for si in done:
            self.probes.pop(si, None)
        self.ext_reg = [(f, e) for f, e in self.ext_reg if self.t_wall < e]

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

    def _fam_present(self, f, M, df):
        """谐波族成员是否出现(与 _phpr_veto 的否决触发条件**同式同源**,不得各写一份)。"""
        P = self.P
        k = int(round(f / df))
        if not (0 < k < len(M)):
            return False
        k2 = int(round(f/2 / df))
        if k2 > 2 and 20*np.log10(M[k2]/(M[k]+1e-30)+1e-30) >= -P.D_sub:
            return True
        for n in (2, 3):
            kn = int(round(f*n / df))
            if kn < len(M) and 20*np.log10(M[kn]/(M[k]+1e-30)+1e-30) >= -P.D_harm:
                return True
        return False

    def _causal_scan(self, M, df):
        """★ r12(IF-v1.8):逐槽记录两个时刻,供重定义后的 causal_ok 使用。
          t_grow0 = 候选**自身**增长起点(电平较诞生电平升 ≥ grow_onset_db 的首槽)
          t_fam0  = **谐波族成员**首次出现的槽
        物理:削波谐波由候选自己长大后产生 ⇒ **后到**;乐音族成员与基频**同时到**。
        ⇒ causal_ok := (t_fam0 − t_grow0) ≥ fam_late_min,**只测族成员的时间,不测候选斜率**
          ⇒ 与 imsd_hit **不同源**,不构成 GROWTH 入选式的子式(D6-e)。"""
        P = self.P
        for tr in self.tracks:
            if not tr.active:
                continue
            if tr.t_grow0 < 0 and tr.last_level >= tr.lv0 + P.grow_onset_db:
                tr.t_grow0 = self.slot_seq
            if tr.t_fam0 < 0 and self._fam_present(tr.f, M, df):
                tr.t_fam0 = self.slot_seq
            if (not tr.causal_ok) and tr.t_grow0 >= 0 and tr.t_fam0 >= 0 \
                    and (tr.t_fam0 - tr.t_grow0) >= P.fam_late_min:
                tr.causal_ok = True          # 一旦确立即保持(并可经 Shadow 继承)

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
            self.phpr_log.append(dict(seq=self.slot_seq, tid=id(tr), f=tr.f, veto_trig=False,
                                      fam_max=None, causal=None, arm1=None, arm2=None,
                                      arm3=None, exempt=None, sub=False))
            return False
        if tr.t_veto < 0:
            tr.t_veto = self.slot_seq
        # 合取门 ①族内最大
        fam_max = True
        for n in (2, 3):
            kn = int(round(tr.f*n / df))
            if kn < len(M) and M[kn] > M[k]:
                fam_max = False
        # 合取门 ②因果时序 —— ★ r12 **重定义**(IF-v1.8)
        #   旧式 `(t_veto - t_born) >= causal_min` 测的是"候选轨龄相对否决起点",
        #   实测**几乎恒真**(钢琴 4814/4814、弓弦 9027/9027)⇒ 它测的不是因果。
        #   新式由 _causal_scan 维护:族成员到达时刻**晚于**候选自身增长起点。
        #   ⚠ 不得沿用旧式,不得二者取或。
        causal = tr.causal_ok
        # ③臂
        arm1 = imsd_hit
        arm2 = tr.rapid_onset
        dom = self._is_dom(tr)
        arm3 = gr_ok and persist_path and dom
        # ★ r12 D6-e 修:GROWTH 路**移除全部三臂**。
        #   理由(实测 1:1 闭合):arm1 = imsd_hit、arm2 = rapid_onset **都是 GROWTH
        #   入选式 `(imsd_hit ∨ rapid_onset)` 的析取项** ⇒ GROWTH 成立 ⟹ 臂成立
        #   ⇒ 谐波否决对增长路结构性空转。arm3 含 persist_path,在 GROWTH 路恒假(死臂)。
        #   GROWTH 改由**与 imsd_hit 不同源**的族到达时序单独把关。
        if persist_path:
            exempt = fam_max and causal and (arm1 or arm2 or arm3)
        else:
            exempt = fam_max and causal
        # ── PHPR 归因遥测(r11;**只记录,不改行为**):回答"六判据为什么没拦住"
        self.phpr_log.append(dict(seq=self.slot_seq, tid=id(tr), f=tr.f, veto_trig=True,
                                  fam_max=fam_max, causal=causal,
                                  arm1=bool(arm1), arm2=bool(arm2), arm3=bool(arm3),
                                  exempt=bool(exempt),
                                  sub=bool(k2 > 2 and 20*np.log10(M[k2]/(M[k]+1e-30)+1e-30) >= -P.D_sub)))
        return not exempt

    def _is_dom(self, tr):
        """臂3 谓词 dom:本通道已跟踪轨中 PNPR 最高者(局部统计,§3.2 修正2)。"""
        act = [t for t in self.tracks if t.active]
        if not act:
            return False
        # ★ B-1 修:此前 docstring 写 PNPR 而代码取 papr_hist,且 Track 无 PNPR 存储位
        #   ⇒ 结构上不可能按 PNPR 实现。而 CHECK F-2 恰证明掩蔽下 PAPR 塌陷、唯一存活是 PNPR
        #   ⇒ 臂3 在它唯一被需要的场景里用了刚被证伪的统计量。现按 PNPR 实现。
        return tr is max(act, key=lambda t: (t.pnpr_hist[-1] if t.pnpr_hist else -99))

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
            # ⭐ r66:`growth_and_gate=False`(默认)时,本式与改前**逐符号等价**;
            #   等价性不靠"读起来一样"证明,靠 `r66a_bitexact.py` 的**逐位实跑对照**证明。
            elif (imsd_hit or (tr.rapid_onset and not P.growth_and_gate)) \
                    and not tr.relaxed:
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
            # ── 分类归因遥测(r11;只记录,不改行为):按**轨身份**归属,不靠频率匹配
            self.cls_log.append(dict(seq=self.slot_seq, tid=id(tr), cls=cls,
                                     imsd=bool(imsd_hit), ronset=bool(tr.rapid_onset),
                                     relaxed=bool(tr.relaxed), lv=float(tr.last_level)))
            if cls:
                out.append(dict(cls=cls, f=float(np.median(tr.fmed)), tr=tr,
                                lv=tr.last_level, b=b))
        # ⭐ r75:`prefer_unnotched=False`(默认)时第二键恒为 False ⇒ 常量分量不影响排序
        #   ⇒ 与改前**逐符号等价**;等价性由 r75a 的逐位实跑对照证明,不靠"读起来一样"。
        out.sort(key=lambda h: (h['cls'] != 'PANIC',
                                self._notch_covers(h['f']) if P.prefer_unnotched else False,
                                -h['b']))
        return out[:1] if out and out[0]['cls'] != 'PANIC' else out[:2]

    # ---------------- 状态机 / 分配 ----------------
    def _allocate(self, howls, M=None, df=None):
        P = self.P
        for h in howls:
            f = h['f']; bw = self._bw_hz(f)
            same = [s for s in self.slots if s.st != NotchSlot.FREE and abs(s.f - f) <= bw/2]
            if same:
                s = same[0]
                # ★ r17(架构侧裁定):`t_last_hit` 刷新 ⟺ 本次复检**导致了加深动作**
                #   ∧ 探针未判「外部」且未「弃权」。
                # 根因:tap 在陷波器组入口、陷波在其**下游** ⇒ **外部持续源永远在 tap 上
                #   看得见 ⇒ 永远复检** ⇒ 刷新不正当。
                #   「该峰仍被检出」**不是**「该陷波仍被需要」的证据。
                # 关键性质:只在"导致加深"时刷新 ⇒ 推迟量被加深梯级上界钉死
                #   (depth_step=-3、max_depth=-18 ⇒ **≤6 步**)⇒ **无限推迟 → 有界推迟**。
                old_target = s.target
                if s.st == NotchSlot.STANDBY:
                    s.st = NotchSlot.ENGAGE; s.target = P.depth0
                else:
                    s.target = max(P.max_depth, s.target + P.depth_step)
                    s.st = NotchSlot.ENGAGE
                deepened = (s.target < old_target - 1e-9)
                if not deepened and old_target <= P.max_depth + 1e-9:
                    # ★ r17:已达 max_depth 仍被复检 ⇒ **压不住** ⇒ EXHAUSTED。
                    #   修法前该路径被"永久占槽"掩盖,从不显形。
                    # ★ r17c 口径勘正(DEC-0010):原实现**每次复检计一次** ⇒ 实测被放大 11×
                    #   (20s 试次:12 次挂陷 → 132 次计数,而不同频点只有 12 个)。
                    #   ⇒ 改为**每次占用只计一次**(状态转移计数,不是轮询计数)。
                    #   通则:凡计数器必须写明"每什么计一次";"每复检"与"每事件"不是同一个量。
                    # ⛔ r20 真缺陷修复(架构侧读权威源查实):
                    #   原实现**只发事件、无任何动作**,而宽带兜底挂在 `if not free:` 上;
                    #   撞顶时槽仍占着 ⇒ `free` 非空 ⇒ **g_duck 永不触发**
                    #   ⇒ 那些 EXHAUSTED 全是「报警但不作为」的**静默失效**,
                    #      且上位机会以为兜底在动。**与发生率无关,必须封。**
                    #   ⇒ 拆分:事件由**撞顶**发 = DEPTH_EXHAUSTED(本处,挂宽带兜底动作);
                    #           事件由**槽位耗尽**发 = SLOTS_EXHAUSTED(见下方 `if not free:`)。
                    #      二者**不同源、不同因、各挂各的动作**,不得共用一个"兜底"族参数。
                    if not s.exhausted_flag:
                        s.exhausted_flag = True
                        self.ctr['depth_exhausted'] = self.ctr.get('depth_exhausted', 0) + 1
                        self.events.append((self.slot_seq, 'DEPTH_EXHAUSTED', round(f, 1)))
                    self.ctr['depth_exhausted_rechecks'] = \
                        self.ctr.get('depth_exhausted_rechecks', 0) + 1
                    # ★ 撞顶 ⇒ 该频点靠加深已无出路 ⇒ **必须有动作**,否则是静默失效
                    self.g_duck_db = max(-6.0, self.g_duck_db - 1.0)
                    self.events.append((self.slot_seq, 'duck-depth', round(self.g_duck_db, 1)))
                if deepened and s.has_affirmative_verdict:   # ★★ r27 肯定式(原为 not from_abstain)
                    s.t_last_hit = self.t_wall
                self.events.append((self.slot_seq, 'deepen', round(f, 1)))
                continue
            # ── C8-② 保鲜期:已判为外部音的频点,期内不再挂陷(代价 = 每个不同外部音一次)
            if 'B14' not in self.B and any(abs(fr - f) <= bw/2 and self.t_wall < exp
                                           for fr, exp in self.ext_reg):
                self.ctr['c8_suppressed'] = self.ctr.get('c8_suppressed', 0) + 1
                continue
            free = [s for s in self.slots if s.st == NotchSlot.FREE]
            if not free:
                # ★ r17 回收优先序:**弃权产生的占用优先于已正向分类的占用被回收**(零成本)
                free = sorted([s for s in self.slots if s.st == NotchSlot.STANDBY],
                              key=lambda s: (s.has_affirmative_verdict, s.t_last_hit))  # ★ r27 肯定式
            if not free:
                # ★ r17b **可抢占**(架构侧升级):正向分类的真啸叫可**直接抢走**
                #   由「弃权」产生的占用(不限于 STANDBY)。
                #   理由:弃权 = 探针**没能作出判断**,该占用不携带"这是真啸叫"的正向证据;
                #   而本候选已通过分类 ⇒ 证据强度不对称 ⇒ 让强证据优先占资源。
                #   ⇒ 对「真啸叫拿不到槽」这一**资源害**,W_eff ≈ 0 ⇒ 该害消失;
                #     只剩「多挂一个浅陷」的**音质害**。二者是**不同的害**,须分开报。
                # ★ r27 肯定式:可被抢占的 = **未持有肯定结论**的占用(含弃权/故障/在飞)
                pre = sorted([s for s in self.slots if (not s.has_affirmative_verdict)
                              and s.st != NotchSlot.FREE], key=lambda s: s.t_last_hit)
                if pre:
                    self.ctr['preempt'] = self.ctr.get('preempt', 0) + 1
                    self.events.append((self.slot_seq, 'preempt', round(f, 1)))
                    free = pre[:1]
            if not free:
                # ★ r20:**槽位耗尽**路径 —— 与撞顶不同源,单列事件
                self.ctr['slots_exhausted'] = self.ctr.get('slots_exhausted', 0) + 1
                # ★ D-K 计数单位:**每个被拒绝的候选计一次**(不是每帧、不是每复检)
                #   —— 供 B_obs = n_blocked / (n_carried + n_blocked) 直接取数
                self.ctr['n_blocked'] = self.ctr.get('n_blocked', 0) + 1
                self.g_duck_db = max(-6.0, self.g_duck_db - 1.0)   # 宽带兜底(§4.4)
                self.events.append((self.slot_seq, 'SLOTS_EXHAUSTED', round(f, 1)))
                self.events.append((self.slot_seq, 'duck-slots', round(self.g_duck_db, 1)))
                continue
            # ★ r24 P0 有效性门:当前槽必须**确实有测量**,否则不新挂陷。
            #   拦挂陷而非只拦探针:若只拦探针,陷波仍挂在静默帧上且**再无任何判决路径**
            #   (连弃权都不会记)⇒ 比现状更差。
            if M is not None and df is not None:
                _k = int(round(f / df))
                _lv_now = self._level(M, _k) if (0 < _k < len(M)) else float('-inf')
                if not (0 < _k < len(M)) or _lv_now <= P.level_valid_db:
                    self.ctr['p0_blocked_novalid'] = self.ctr.get('p0_blocked_novalid', 0) + 1
                    # ★ r26 纯遥测:留痕被拦候选的**实际电平**,供"门是否过强"判定
                    self.p0_block_log.append(dict(seq=self.slot_seq, f=float(f),
                                                  lv=float(_lv_now), t=float(self.t_wall)))
                    continue
            self.ctr['n_carried'] = self.ctr.get('n_carried', 0) + 1   # ★ D-K:每个成功入槽的候选一次
            s = free[0]
            s.st = NotchSlot.ENGAGE; s.f = f; s.depth = 0.0
            s.from_abstain = False                          # ★ r17:新占用,来源待探针判定
            s.has_affirmative_verdict = False               # ★★ r27:新占用默认**无**肯定结论
            s.exhausted_flag = False                        # ★ r17c:新占用,耗尽标记重置
            s.target = P.depth0 if h['cls'] != 'PANIC' else -9.0
            s.t_last_hit = self.t_wall
            self.events.append((self.slot_seq, f"engage-{h['cls']}", round(f, 1)))
            if 'B14' not in self.B:                    # ── C8-② 开探针(浅陷已挂,数据已有)
                self.probes[self.slots.index(s)] = dict(f=f, seq0=self.slot_seq, L0=None,
                                                        d=abs(P.depth0), cls=h['cls'])
                self.ctr['c8_probe_started'] = self.ctr.get('c8_probe_started', 0) + 1

    def _slots_tick(self):
        P = self.P
        dt = P.T_hop
        for s in self.slots:
            if s.st == NotchSlot.FREE:
                continue
            if s.st == NotchSlot.ENGAGE:
                step = P.ramp_db_per_s * dt
                s.depth = max(s.target, s.depth - step)
                if abs(s.depth - s.target) < DEPTH_EPS_DB:
                    s.st = NotchSlot.HOLD
            elif s.st == NotchSlot.HOLD:
                if self.t_wall - s.t_last_hit >= P.lift_after_s and 'B6' not in self.B:
                    s.st = NotchSlot.LIFT; s.t_lift = self.t_wall
            elif s.st == NotchSlot.LIFT:
                if self.t_wall - s.t_lift >= P.lift_step_s:
                    s.depth = min(0.0, s.depth + 3.0); s.t_lift = self.t_wall
                    s.target = s.depth
                if s.depth >= -DEPTH_EPS_DB:
                    s.st = NotchSlot.STANDBY; s.t_last_hit = self.t_wall
            elif s.st == NotchSlot.STANDBY:
                if self.t_wall - s.t_last_hit >= P.reclaim_s:
                    s.st = NotchSlot.FREE
            coef_fs = 44100.0 if 'B3' in self.B else FS      # broken:错误 fs
            s.set_coef(FS, P.bw_oct, coef_fs=coef_fs)
        if self.g_duck_db < 0 and not any(s.st == NotchSlot.ENGAGE for s in self.slots):
            self.g_duck_db = min(0.0, self.g_duck_db + 1.0 * dt)
