"""d5-b2 · **B-2 分辨力**:能不能把「两个人」与「一个人被两只麦拾到」分开。
⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_d5_b2.txt(§3 判据跑前写死)。
⛔ 本文件不含结论性散文。"""
import sys, json, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_D5')
import numpy as np
from scipy.signal import fftconvolve
import clrig
from clrig import FS
import marks

DIR = '/home/it1234/processor/01_design/prototype_D5/'
T60, DUR, NTRIAL = 0.4, 3.0, 12
ENV_HOP = 256                      # 包络抽取(automixer 本来就有的量级)
OUT = []
def W(s=''):
    OUT.append(s); print(s); sys.stdout.flush()

def rir(seed):
    h, _ = clrig.make_F(T60=T60, prop_delay_ms=8., seed=seed)
    return h

def env(x, hop=ENV_HOP):
    n = (len(x)//hop)*hop
    return np.sqrt((x[:n]**2).reshape(-1, hop).mean(1) + 1e-30)

def norm_xcorr(a, b, maxlag=None):
    """最大归一化互相关(带 lag 搜索)。"""
    a = a - a.mean(); b = b - b.mean()
    d = np.sqrt((a@a)*(b@b)) + 1e-30
    if maxlag is None:
        maxlag = int(0.05*FS)                      # ±50 ms 足够覆盖麦间几何差
    c = fftconvolve(a, b[::-1], mode='full')/d
    mid = len(b)-1
    return float(np.max(np.abs(c[mid-maxlag:mid+maxlag+1])))

def scenario(kind, seed):
    rng = np.random.default_rng(1000+seed)
    n = int(DUR*FS)
    h1, h2 = rir(2*seed), rir(2*seed+1)
    if kind == 'S1':                               # 两个人:不同源
        s1 = rng.standard_normal(n); s2 = rng.standard_normal(n)
        x1 = fftconvolve(s1, h1)[:n]; x2 = fftconvolve(s2, h2)[:n]
    else:                                          # S2 一人两麦:同源不同 RIR
        s = rng.standard_normal(n)
        x1 = fftconvolve(s, h1)[:n]; x2 = fftconvolve(s, h2)[:n]
    # ⚠ 归一化到同一 RMS ⇒ 电平判据在构造上拿不到便宜(预注册 §1)
    x1 = x1/(np.sqrt((x1**2).mean())+1e-30); x2 = x2/(np.sqrt((x2**2).mean())+1e-30)
    L1, L2 = 20*np.log10(np.sqrt((x1**2).mean())), 20*np.log10(np.sqrt((x2**2).mean()))
    e1, e2 = env(x1), env(x2)
    return dict(D_lvl=abs(L1-L2),
                D_env=norm_xcorr(e1, e2, maxlag=int(0.05*FS/ENV_HOP)),
                D_xcorr=norm_xcorr(x1, x2))

def sep(a, b):
    """区间不重叠(⛔ 不取阈值)。"""
    return (max(a) < min(b)) or (max(b) < min(a))

def main():
    t0 = time.time()
    W("未经 critic 评审 —— d5-b2 · B-2 分辨力  [L2/宿主仿真]  预注册 = PREREG_d5_b2.txt")
    W("问:判据能否把【两个人 S1】与【一个人被两只麦拾到 S2】分开")
    W(f"构型:T60={T60} · {DUR:.0f}s · 白噪声源 · 每场景 {NTRIAL} 试次 · 两通道 RMS 已对齐")
    W("⛔ 源为白噪声 ⇒ **不得外推到语音**(相关性结构不同)")
    W("")
    res = {'S1': [], 'S2': []}
    for k in ('S1', 'S2'):
        for i in range(NTRIAL):
            res[k].append(scenario(k, i))
    W(f"{'量':>10}{'S1(两个人)区间':>28}{'S2(一人两麦)区间':>28}{'区间不重叠?':>14}")
    verdicts = {}
    for key in ('D_lvl', 'D_env', 'D_xcorr'):
        a = [r[key] for r in res['S1']]; b = [r[key] for r in res['S2']]
        s = sep(a, b); verdicts[key] = s
        W(f"{key:>10}{f'[{min(a):.4f}, {max(a):.4f}]':>28}{f'[{min(b):.4f}, {max(b):.4f}]':>28}"
          f"{('✅ **可分**' if s else '⛔ 重叠(无分辨力)'):>14}")
    W("")
    W("="*94); W("§H 预注册假设逐条对表(⛔ 判据取自 PREREG §3,跑后未改)"); W("="*94)
    W(f"  H1 电平判据无分辨力(**我预期的方向 ⇒ 举证门槛更高**):"
      f"sep(D_lvl) = {verdicts['D_lvl']} ⇒ "
      f"{'✅ 如预期(电平判据确实分不开)' if not verdicts['D_lvl'] else '⚠ **反预期 ⇒ 须先查构型,⛔ 不得直接下结论**'}")
    W(f"  H2 主问:sep(D_env) = {verdicts['D_env']} ｜ sep(D_xcorr) = {verdicts['D_xcorr']}")
    if verdicts['D_env']:
        W("     ⇒ ✅ **便宜的判据(包络互相关)够用** ⇒ §2 的算力界不受威胁")
    elif verdicts['D_xcorr']:
        W("     ⇒ ⚠ **能做,但要贵的**(原始信号 + lag 搜索)⇒ **§2 的界须重估**")
    else:
        W("     ⇒ ⛔⛔ **两者皆不可分 ⇒ 本构型下无可用判据 ⇒ 顶格报**")
    W("")
    W("  H3 有利侧的闸(⛔ 两个方向都报,只报 (a) 不算数):")
    for key in ('D_env', 'D_xcorr'):
        a = [r[key] for r in res['S1']]; b = [r[key] for r in res['S2']]
        mid = (max(a)+min(b))/2 if max(a) < min(b) else (np.median(a)+np.median(b))/2
        pa = sum(1 for v in b if v > mid)/len(b)      # S2 判为同源
        pb = sum(1 for v in a if v > mid)/len(a)      # ⛔ S1 被误判为同源
        W(f"    {key}: (a) S2 判为同源 **{pa*100:.0f}%** ｜ "
          f"(b) ⛔ **S1 被误判为同源 {pb*100:.0f}%**(真的两个人被合并)")
    W("    ⚠ 上面那个中点**仅为报这两个比例而临时取**,⛔ **不是本轮要定的门限**(预注册 §4)")
    W("")
    W(f"⚠ n = {NTRIAL} 试次/场景 ⇒ **{NTRIAL}/∞**,⛔ 不是全称;⛔ 白噪声源,不得外推到语音")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    open(DIR+'d5_b2_out.txt','w').write("\n".join(OUT)+"\n")
    json.dump(res, open(DIR+'d5_b2.json','w'))

if __name__ == '__main__':
    main()
