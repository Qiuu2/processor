"""r66d · `R_RISE=18dB` 是不是**定在了另一个量的域上**?——电平域 vs PAPR 域直接对比。

⛔ 未经 critic 评审。[L2/宿主仿真]。输出:r66d_rise_domain_out.txt (D6-j)
deps: nhs.py@31decc8e8d07e085 clrig.py@8ad47ce8d260dd18

════════════════════════════════════════════════════════════════
缘起(盘面证据,非推测)
════════════════════════════════════════════════════════════════
`W1B_v1.2:322` 定义臂2 = 「任意 ≤N_RISE=2 槽内**升幅** ≥R_RISE=18dB,其后平台」
—— **"升幅"没有写明【哪个量的升幅】**。而 `nhs.py:555` 取的是 `tr.papr_hist`。
支撑该疑虑的两条盘面事实:
  ① `nhs.py:852` 留有前科注释:「★ B-1 修:此前 docstring 写 PNPR 而代码取 papr_hist」
     ⇒ **同一个数据结构上已经发生过一次"文档说的量 ≠ 代码取的量"**;
  ② 设计侧 64 格间隙扫描用的是「**升速 4–12 dB/槽 × 净空 8–24 dB**」
     ⇒ 那是**电平**域的量级;而 PAPR 是**比值**统计,峰一旦主导全谱就封顶
     (上限 10log10(M) = 30.1 dB @M=1024)⇒ **PAPR 的升幅天然远小于电平的升幅**。

⇒ 若电平域升幅能达 ~18 dB 而 PAPR 域达不到,则 **R_RISE 是"定在电平域、施加在 PAPR 域"**
  = 同族二义(每侧/全宽、10log/20log、单边/双边…)的**又一例**,
  **修法就不是"把 18 调小",而是"把它施加到正确的量上"** —— 两者处置完全不同。

预注册(跑前写死):
  Hd1 电平域 ≤2 槽升幅的**最大值** ≥ 18 dB ⇒ **域错配假说成立**(修法 = 改施加对象)
  Hd2 电平域也远达不到 18 dB      ⇒ **域错配假说不成立**,R_RISE 就是单纯定高了
                                    (修法 = 标定该门,按 lead 的扫描臂做)
  ⚠ 两者都要报;⛔ 不许只报支持某一侧的那个。
⛔ 本文件不写结论散文。
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit

GR = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
FRAME, BW, T = 64, 1/5, 6.0
SEEDS = [(0.2,0),(0.2,1),(0.2,2),(0.5,0),(0.5,1),(0.5,2)]
DELTAS = [-1.0, 1.0, 3.0]
O=[]
def W(s=''):
    O.append(s); print(s); sys.stdout.flush()

def run(alg, hb, D, G, src):
    """经 `_imsd` 钩子逐(轨,槽)采样:PAPR 轨迹 + 电平轨迹(按轨 id 归集)。"""
    lv_hist = {}
    pa_hist = []
    o_im = alg._imsd
    def w(tr, _o=o_im):
        pa_hist.append(list(tr.papr_hist))
        lv_hist.setdefault(id(tr), []).append(float(tr.last_level))
        return _o(tr)
    alg._imsd = w
    def pf(blk, _a=alg): return _a.process_frame(blk, GR)
    clrig.Loop(hb, D, G, proc=pf).run(src, FRAME)
    return pa_hist, list(lv_hist.values())

def max_rise(h, n_rise=2, min_plat=3):
    """与 nhs.py:556-559 同一双重循环口径(含 MIN_PLAT 尾部保留)。"""
    best = -99.
    if len(h) < min_plat + 1: return None
    for i in range(len(h)-min_plat):
        for j in range(i+1, min(i+n_rise, len(h)-min_plat)+1):
            best = max(best, h[j]-h[i])
    return best

def main():
    P = nhs.Params()
    W("未经 critic 评审 —— r66d · R_RISE 的【域】核对:电平域 vs PAPR 域   [L2/宿主仿真]")
    W("deps: nhs.py@31decc8e8d07e085 clrig.py@8ad47ce8d260dd18")
    W(f"门:R_RISE={P.R_RISE} dB / N_RISE={P.N_RISE} 槽 / MIN_PLAT={P.MIN_PLAT}")
    W("⚠ 两个域用**同一个** max_rise 口径(与 nhs.py:556-559 双重循环一致)")
    W("")
    W("%5s%4s%6s | %26s | %26s" % ('T60','sd','Δ','PAPR 域 ≤2槽升幅(dB)','电平域 ≤2槽升幅(dB)'))
    W("%5s%4s%6s | %8s%9s%9s | %8s%9s%9s" % ('','','','最大','p95','中位','最大','p95','中位'))
    PA, LV = [], []
    for (T60, sd) in SEEDS:
        h0, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
        hb = band_limit(h0, 8000.); he = clrig.h_eff(hb)
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        src = 1e-3*np.random.default_rng(sd).standard_normal(int(T*FS))
        for dl in DELTAS:
            pa_h, lv_h = run((lambda: (lambda a: (setattr(a.P,'bw_oct',BW), a)[1])(NHS()))(),
                             hb, D, anchor+dl, src)
            pa = [x for x in (max_rise(h) for h in pa_h) if x is not None]
            lv = [x for x in (max_rise(h) for h in lv_h) if x is not None]
            PA += pa; LV += lv
            f = lambda v: (max(v), np.percentile(v,95), np.median(v)) if v else (float('nan'),)*3
            a1,a2,a3 = f(pa); b1,b2,b3 = f(lv)
            W("%5.1f%4d%6.1f | %8.2f%9.2f%9.2f | %8.2f%9.2f%9.2f" % (T60,sd,dl,a1,a2,a3,b1,b2,b3))
    W("-"*86)
    for nm, v in (('PAPR 域', PA), ('电平域', LV)):
        if v:
            W("  合计 %s(n=%d):最大 **%.2f** / p95 %.2f / 中位 %.2f dB   门=%.1f ⇒ 达门 **%d/%d**"
              % (nm, len(v), max(v), np.percentile(v,95), np.median(v), P.R_RISE,
                 sum(1 for x in v if x >= P.R_RISE), len(v)))
    W("")
    if LV and PA:
        W("  Hd1(电平域最大 ≥ 18 ⇒ 域错配成立):电平域最大 = %.2f ⇒ **%s**"
          % (max(LV), '成立' if max(LV) >= P.R_RISE else '不成立'))
        W("  Hd2(电平域也远达不到 ⇒ 单纯定高):%s"
          % ('成立' if max(LV) < P.R_RISE else '不成立'))
        W("  两域倍数(最大值之比 电平/PAPR)= %.2f×" % (max(LV)/max(PA) if max(PA)>0 else float('nan')))
    W("")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。")
    open('/home/it1234/processor/01_design/prototype_W1P/r66d_rise_domain_out.txt','w').write("\n".join(O)+"\n")

if __name__ == '__main__':
    main()
