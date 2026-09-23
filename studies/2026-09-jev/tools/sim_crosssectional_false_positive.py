"""No-memory model with STABLE tilts; labels share sector x season shocks (drift-like).
Question: how often does analyze.delta_pre_post reject at the Holm floor (0.0125) / 0.05?"""
import sys, numpy as np
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))
from analyze import delta_pre_post

def world(seed, sd_sect=0.03, sd_size=0.01, sd_idio=0.09):
    rng = np.random.default_rng(seed)
    T, S = 812, 11
    sect = rng.integers(0, S, T); z = rng.normal(0, 1, T)
    tilt_s = rng.normal(0, 0.5, S)                 # stable sector hunch, NOT memory
    rows = []
    for grp, seasons in (("PRE", 8), ("POST", 2)):
        for q in range(seasons):
            f_s = rng.normal(0, sd_sect, S)         # common sector shock this season
            f_z = rng.normal(0, sd_size)            # size premium this season
            r = f_s[sect] + f_z * z + rng.normal(0, sd_idio, T)
            s = 1 / (1 + np.exp(-(tilt_s[sect] + 0.5 * z + rng.normal(0, 0.3, T))))
            for i in range(T):
                rows.append({"s": float(s[i]), "y": int(r[i] > 0), "ticker": f"T{i}", "grp": grp,
                             "sector": f"T{i}"})   # 'sector' key reused as ticker stratum for the fix
    return rows

if __name__ != "__main__": raise ImportError
N = int(sys.argv[1]) if len(sys.argv) > 1 else 120
est, sds, rej125, rej05, w_rej125, w_rej05, w_est = [], [], 0, 0, 0, 0, []
for k in range(N):
    rows = world(1000 + k)
    d = delta_pre_post(rows, B=300, seed=k)
    est.append(d["estimate"]); sds.append(d["boot_sd"])
    rej125 += d["p_one_sided"] <= 0.0125; rej05 += d["p_one_sided"] <= 0.05
print(f"pooled AUC  : SD of estimate across worlds {np.std(est):.4f} vs mean bootstrap SD {np.mean(sds):.4f}")
print(f"pooled AUC  : reject@0.0125 {rej125}/{N} = {rej125/N:.3f} ; reject@0.05 {rej05}/{N} = {rej05/N:.3f}")
