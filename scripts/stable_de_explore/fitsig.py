"""hier_binary.fit with a per-team ability SD (array sigma): scratch copy made by patching the source."""
import inspect, numpy as np
from arch_b import hier_binary as hb
src = inspect.getsource(hb.fit)
def rep(a, b):
    global src
    assert a in src, a
    src = src.replace(a, b)
rep("def fit(", "def fit_sig(")
rep("    has_mu, has_nu = tau > 0, tau_b > 0\n", "    has_mu, has_nu = tau > 0, tau_b > 0\n    sigma = np.broadcast_to(np.asarray(sigma, float), (n_t,))\n")
rep("f += np.sum((th - m) ** 2) / (2 * sigma ** 2) +", "f += np.sum((th - m) ** 2 / (2 * sigma ** 2)) +")
rep("(-wt(rt) / sigma ** 2 + (mu - MU0) / tau ** 2)", "(-wt(rt / sigma ** 2) + (mu - MU0) / tau ** 2)")
rep("(np.bincount(r_c, r_w ** 2, n_c) / sigma ** 2 + 1 / tau ** 2)", "(np.bincount(r_c, r_w ** 2 / sigma[r_t] ** 2, n_c) + 1 / tau ** 2)")
rep("(-wt(dt) / sigma ** 2 + vm / tau ** 2)", "(-wt(dt / sigma ** 2) + vm / tau ** 2)")
ns = dict(vars(hb)); exec(src, ns); fit_sig = ns["fit_sig"]

def board_sigma(ds, res, obs, rows, sigma_t, k=20.0, s0=300.0):
    """EB spread per board: mean over the board's rows of (theta-m)^2 + posterior var, shrunk by k pseudo-rows at s0."""
    team, prob, y = obs
    n_t, n_c = len(ds.teams), len(ds.contests)
    r_t, r_c = ds.team_of_row[rows], ds.contest_of_row[rows]
    n_rows = np.bincount(r_t, minlength=n_t).astype(float)
    m = np.bincount(r_t, res["mu"][r_c] / n_rows[r_t], n_t); m[n_rows == 0] = 2000.0
    pr = 1 / (1 + np.exp(-(res["theta"][team] - res["b"][prob]) / hb.S))
    var = 1 / (np.bincount(team, pr * (1 - pr), n_t) / hb.S ** 2 + 1 / sigma_t ** 2)
    e2 = (res["theta"] - m) ** 2 + var
    num = np.bincount(r_c, e2[r_t], n_c); cnt = np.bincount(r_c, None, n_c)
    return np.sqrt((num + k * s0 ** 2) / (cnt + k)), cnt

def team_sigma(ds, sig_c, rows):
    """per-team SD: root mean square of its boards' SDs"""
    n_t = len(ds.teams)
    r_t, r_c = ds.team_of_row[rows], ds.contest_of_row[rows]
    n_rows = np.bincount(r_t, minlength=n_t).astype(float)
    out = np.sqrt(np.bincount(r_t, sig_c[r_c] ** 2, n_t) / np.maximum(n_rows, 1)); out[n_rows == 0] = 300.0
    return out

def fit_eb(ds, obs=None, rows=None, iters=4, scale=None, **kw):
    """iterate fit <-> board spreads; `scale` rescales the spreads so their row-weighted RMS equals it"""
    if obs is None: obs = (ds.team_of_row[ds.obs_row], ds.obs_prob, ds.obs_y.astype(float))
    rows_m = np.ones(len(ds.team_of_row), bool) if rows is None else rows
    sig_t = np.full(len(ds.teams), 300.0); sig_c = None
    for _ in range(iters):
        res = fit_sig(ds, obs=obs, rows=rows, sigma=sig_t, **kw)
        sig_c, cnt = board_sigma(ds, res, obs, rows_m, sig_t)
        if scale: sig_c = sig_c * scale / np.sqrt(np.sum(cnt * sig_c ** 2) / cnt.sum())
        sig_t = team_sigma(ds, sig_c, rows_m)
    res = fit_sig(ds, obs=obs, rows=rows, sigma=sig_t, **kw)
    res["sig_c"] = sig_c
    return res
