"""FastPLBF_M allocation (Sato & Matsui; github.com/atsukisato/FastPLBF, commit 9491e7e) in numba,
with arbitrary non-negative segment weights in place of the non-key histogram.

Semantics follow the original exactly:
  * N equal-width score segments on [0,1]; a score s falls in segment ceil(s*N) (s=0 -> 1);
  * g = (member counts + 1) normalised (prList adds one to every segment);
  * h = weights normalised (callers pass (validation counts + 1) for plain PLBF/Gama);
  * DPKL[n][q] = max over i of DPKL[i-1][q-1] + G(i..n)*ln(G/H)  (calc_DPKL);
  * for every j = k..N: first k-1 regions from DPPre[j-1][k-1], last region = segments j..N,
    FPRs from OptimalFPR_M, keep the minimum ExpectedFPR (find_best_t_and_f).
Region r covers segments (b[r-1], b[r]] in 1-based segment numbers.
"""
import math
import numpy as np
from numba import njit

N_SEG, K_REG = 1000, 5


def edges(N=N_SEG):
    return np.arange(N + 1) / N          # == [i / N for i in range(N + 1)] bit for bit


def segment_of(scores, N=N_SEG):
    """0-based segment index of each score in [0,1] (bisect_left on i/N, 0 -> first)."""
    i = np.searchsorted(edges(N), scores, side='left')
    return np.maximum(i, 1) - 1


@njit(cache=True)
def _dp(G, H, k):
    """G, H: prefix sums (length N+1). Returns DPPre (N+1, k+1), -1 = None."""
    N = len(G) - 1
    DPKL = np.full((N + 1, k + 1), -np.inf)
    DPPre = np.full((N + 1, k + 1), -1, np.int64)
    DPKL[0, 0] = 0.0
    for n in range(1, N + 1):
        for q in range(1, k + 1):
            best = -np.inf
            arg = -1
            for i in range(1, n + 1):
                prev = DPKL[i - 1, q - 1]
                if prev == -np.inf:
                    continue
                pos = G[n] - G[i - 1]
                neg = H[n] - H[i - 1]
                if neg == 0.0:
                    continue
                v = prev if pos == 0.0 else prev + pos * math.log(pos / neg)
                if best < v:
                    best = v
                    arg = i - 1
            DPKL[n, q] = best
            DPPre[n, q] = arg
    return DPPre


@njit(cache=True)
def _optimal_fpr(pos, neg, M, n):
    """OptimalFPR_M for one threshold vector; pos/neg = region probabilities (length k)."""
    k = len(pos)
    c = math.log2(math.e)
    order = np.empty(k, np.int64)
    ratio = np.empty(k)
    L = 0
    G_sum = 0.0
    for i in range(k):
        if neg[i] != 0.0:
            order[L] = i
            ratio[L] = pos[i] / neg[i]
            L += 1
        else:
            G_sum += pos[i]
    # descending by pos/neg; stable like Python's sort(reverse=True) on equal keys
    idx = np.argsort(-ratio[:L], kind='mergesort')
    order = order[:L][idx]
    suf = np.zeros(L + 1)
    for j in range(L - 1, -1, -1):
        i = order[j]
        term = 0.0
        if pos[i] != 0.0:
            term = pos[i] * math.log2(pos[i] / neg[i])
        suf[j] = suf[j + 1] + term
    m = 0
    beta = 0.0
    while m < L:
        beta = (M + c * n * suf[m]) / (c * n * (1 - G_sum))
        top = order[m]
        if math.pow(2.0, -beta) * pos[top] / neg[top] > 1:
            G_sum += pos[top]
            m += 1
            continue
        break
    f = np.ones(k)
    for j in range(m, L):
        i = order[j]
        f[i] = math.pow(2.0, -beta) * pos[i] / neg[i]
    return f


@njit(cache=True)
def _best(G, H, DPPre, k, M, n):
    N = len(G) - 1
    best = np.inf
    best_b = np.zeros(k + 1, np.int64)
    best_f = np.ones(k)
    b = np.zeros(k + 1, np.int64)
    pos = np.empty(k)
    neg = np.empty(k)
    for j in range(k, N + 1):
        if DPPre[j - 1, k - 1] < 0 and k > 1:
            continue
        b[k] = N
        b[k - 1] = j - 1
        now = j - 1
        ok = True
        for r in range(k - 1, 0, -1):
            now = DPPre[now, r]
            if now < 0:
                ok = False
                break
            b[r - 1] = now
        if not ok:
            continue
        for r in range(k):
            pos[r] = G[b[r + 1]] - G[b[r]]
            neg[r] = H[b[r + 1]] - H[b[r]]
        f = _optimal_fpr(pos, neg, M, n)
        e = 0.0
        for r in range(k):
            e += neg[r] * f[r]
        if best > e:
            best = e
            best_b[:] = b
            best_f[:] = f
    return best_b, best_f, best


def allocate(member_counts, weights, M_bits, k=K_REG):
    """FastPLBF_M with `weights` as the non-key mass per segment.

    member_counts: members per segment (raw counts; +1 smoothing applied here as in prList)
    weights:       non-negative per-segment weights (normalised here)
    Returns (bounds b[0..k] in segment numbers, region FPRs f[0..k-1], expected FPR under weights).
    """
    gc = np.asarray(member_counts, np.float64) + 1.0
    g = gc / gc.sum()
    w = np.asarray(weights, np.float64)
    h = w / w.sum()
    G = np.concatenate([[0.0], np.cumsum(g)])
    H = np.concatenate([[0.0], np.cumsum(h)])
    n = int(np.asarray(member_counts).sum())
    DPPre = _dp(G, H, k)
    b, f, e = _best(G, H, DPPre, k, float(M_bits), n)
    return b, f, e


def region_of_segment(b, N=N_SEG):
    """0-based region index for each 0-based segment."""
    seg = np.arange(1, N + 1)
    return np.searchsorted(b[1:], seg, side='left')


def smoothed(counts):
    """prList smoothing of a count histogram: (count + 1) per segment, normalised."""
    c = np.asarray(counts, np.float64) + 1.0
    return c / c.sum()
