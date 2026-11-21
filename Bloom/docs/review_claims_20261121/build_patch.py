"""Read four pinned manuscript files and WRITE ONLY a review patch in this directory.

There is deliberately no apply mode and no write to the paper repository.
"""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent
BASE='e256658'
FILES=('abstract.tex','introduction.tex','experiments.tex','conclusion.tex')


def replace_once(text,old,new):
    assert text.count(old)==1,('Expected exactly one source match',old[:100])
    return text.replace(old,new,1)


def transform(name,text):
    swaps=[]
    if name=='abstract.tex':
        swaps=[(
            r'On four datasets and four packet traces, RA-PLBF matches exhaustive replay of the learning prefix in quality, has 2--16\% fewer FPs on a trace held out until after the code freeze, and selects 2--5$\times$ faster, up to 49$\times$ at 100 million learning queries.',
            r'On four datasets and four packet traces, RA-PLBF has similar observed FP counts to exhaustive learning-period replay while reducing candidate-selection cost by 1.7--5.4$\times$ at the default settings, and by up to 49$\times$ at 100 million learning queries. FP improvements are workload-dependent: it has 2--16\% fewer FPs on a trace held out until after the code freeze, but its aggregate advantage over Replay is not statistically significant in the clustered test.')]
    elif name=='introduction.tex':
        swaps=[(
            r'\emph{Selection.} Against exhaustive learning-period replay, the strongest baseline, \ra has no more total FPs in 24 of 30 settings; across 21 clusters its geometric mean is 0.975 of replay\'s.',
            r'\emph{Selection.} Against exhaustive learning-period replay, the strongest baseline, \ra has no more total FPs in 24 of 30 settings; across 21 clusters its geometric mean is 0.975 of replay\'s. This aggregate FP advantage is not significant in the two-sided clustered test ($p=0.096$); the main result against Replay is lower selection cost with similar observed FP counts, not universal FP superiority.'),(
            r'  \item \emph{Evaluation.} On 1,146 cases and a pre-declared holdout trace, re-weighting beats tuning only the cache share on real traces, and \ra matches or beats exhaustive replay at a fraction of its selection cost, up to 49$\times$ less at 100M learning queries, and beats Gama, the official Gama code on its own data and a plain BF with a cache (\S\ref{sec:exp}).',
            r'  \item \emph{Evaluation.} On 1,146 cases and a pre-declared holdout trace, we separately measure workload-dependent FP gains from re-weighting and lower candidate-selection cost than exhaustive replay, up to 49$\times$ faster at 100M learning queries with similar observed FP counts. Comparisons with Gama, its official implementation and a plain BF with a cache expose both improvements and limitations (\S\ref{sec:exp}).')]
    elif name=='experiments.tex':
        swaps=[(
            r'In this section, we evaluate \ra on four datasets and four packet traces. When absent keys repeat, the results show that re-weighting by cache misses pays where regions differ in repetition, that \ra matches or beats exhaustive replay at a fraction of its selection cost, and that it beats Gama, a fixed cache and a plain BF with a cache.',
            r'In this section, we evaluate \ra on four datasets and four packet traces. We separate two empirical contributions: lower candidate-selection cost than exhaustive learning-period replay with similar observed FP counts, and further FP reductions from re-weighting on some workloads. The FP gains are workload-dependent; comparisons with cached baselines and a plain BF with a cache identify where the learned allocation helps and where it does not.'),(
            r'When queries repeat, Gama has up to 54$\times$ more FPs on the real traces and 11$\times$ more per case at the median (Table~\ref{tab:cases}).',
            r'Gama has up to 54$\times$ more FPs on the repeating real traces. Across all 748 eligible cases, including no-repeat workloads, its per-case FP ratio to \ra is about 11$\times$ at the median (Table~\ref{tab:cases}).'),(
            r'\ra reaches the same quality without building the candidates.',
            r'\ra obtains similar observed FP counts while building only a short list of candidates.'),(
            r'\paragraph{Statistical significance.} Cases that share a dataset share its model and query pool, so we test on 21 (dataset $\times$ workload group) clusters: \ra is better in 15, with a geometric mean of 0.975 (two-sided Wilcoxon signed-rank $p=0.096$).',
            r'\paragraph{Uncertainty and interpretation.} Cases that share a dataset share its model and query pool. We retain the original 21 (dataset $\times$ workload group) clusters: \ra is better in 15, with a geometric mean ratio of 0.975 to Replay (two-sided Wilcoxon signed-rank $p=0.096$). As an additional, post-hoc uncertainty analysis, we resample the eight complete datasets with replacement 50,000 times (seed 2901), carrying all clusters within each sampled dataset together. We keep the original 748-case eligibility rule and the equal-cluster mean of log paired ratios; no grouping is changed to obtain a smaller $p$-value. With the count-gap repair, the effect ratio is 0.9751 and the percentile 95\% interval is $[0.9473,1.0012]$. It includes 1. With only eight named datasets, this interval is a sensitivity estimate, not a guarantee for a new workload. Neither the test nor the interval establishes statistical equivalence or non-inferiority. We therefore describe similar observed FP counts at lower selection cost, with additional FP reductions on some workloads, rather than a general FP advantage over Replay.'),(
            r'At that length Replay keeps a 931\,MB trace and \ra 121\,MB of key statistics.',
            r'At that length Replay keeps 931\,MB of learning state, including an 800\,MB raw trace, and \ra keeps 121\,MB of key statistics; these state sizes are distinct from peak process memory.'),(
            r'On COD and CAIDA all methods choose 160 trees,',
            r'On COD and CAIDA the selected Gama and RA-family structures use 160 trees,'),(
            r'With a file-backed SQLite point lookup as the backend (about 3--4\,$\mu$s per access), where every FP issues a real lookup and only a lookup that returns no row inserts into the cache, the FPs saved outweigh the extra query work on the traces: \ra needs 39--65\% fewer backend accesses and 0.47--0.72$\times$ Gama\'s total time at 24\,KiB, and 0.77$\times$ on Shalla. On URL 128\,KiB it is 1.7$\times$ slower (2.1$\times$ with an in-memory backend), because it saves only 52 backend accesses per 200,000 queries while its model is three times larger. On COD and CAIDA a 160-tree model costs about as much as one SQLite lookup, and no learned filter is faster than using no filter. The time saved grows with the cost of a backend access. ',
            r'The SQLite experiment uses a batched timing protocol: the native filter/cache loop first processes the query batch using known membership labels for negative-cache feedback, and real SQL point lookups are then executed for the accepted queries. The timer covers both phases, but this is not a strictly interleaved online implementation in which SQL results drive each subsequent insertion. Under this batched metric, with file-backed SQLite (about 3--4\,$\mu$s per unfiltered access), \ra uses 39--65\% fewer backend accesses and 0.47--0.72$\times$ Gama\'s combined time on the traces at 24\,KiB, and 0.77$\times$ on Shalla. On URL 128\,KiB it is 1.7$\times$ slower (2.1$\times$ with an in-memory backend), saving only 52 backend accesses per 200,000 queries while using three times as many trees. On CAIDA 256\,KiB, its measured time is 3.165\,$\mu$s per query versus 4.004\,$\mu$s without a filter; on COD 1024\,KiB it is 4.181 versus 4.096\,$\mu$s. The fixed 48-tree FastPLBF baseline is faster than the unfiltered path on both. These measurements must not be interpreted as strictly interleaved backend-feedback latency; that experiment remains to be performed.'),(
            r'(at most 1 in 14 of 16 points)',r'(at most 1 in 13 of 16 points)'),(
            r'\ra pays off when absent keys repeat and the model separates members from negatives. Three conditions shape its use.',
            r'The evidence supports two distinct benefits: cheaper candidate selection with similar observed FP counts to Replay, and workload-dependent FP improvements from cache-aware allocation. It does not establish universal FP superiority, statistical equivalence, or lower end-to-end query latency. Three conditions shape its use.')]
    elif name=='conclusion.tex':
        swaps=[(
            r'On four datasets and four packet traces it matches exhaustive replay in quality, wins on a trace held out until after the code freeze, and selects up to 49$\times$ faster.',
            r'On four datasets and four packet traces it has similar observed FP counts to exhaustive learning-period replay while selecting up to 49$\times$ faster. Re-weighting yields additional FP reductions on some workloads, including a trace held out until after the code freeze, but the aggregate FP advantage is not significant in the clustered test and does not establish statistical equivalence.')]
    # Raw single-quoted Python literals above escape an apostrophe for syntax only.
    for old,new in swaps:
        old=old.replace("\\'", "'");new=new.replace("\\'", "'")
        text=replace_once(text,old,new)
    return text,len(swaps)


def main():
    p=argparse.ArgumentParser();p.add_argument('--paper',type=Path,required=True);a=p.parse_args()
    run=lambda *args:subprocess.check_output(['git','-C',str(a.paper),*args],text=True)
    commit=run('rev-parse',BASE).strip();parts=[];manifest={}
    for name in FILES:
        rel='vldb/sections/'+name;old=run('show',commit+':'+rel);new,changes=transform(name,old)
        assert old!=new
        # Text-only sanity checks; these do NOT substitute for TeX compilation or layout checks.
        assert new.count('{')==new.count('}'),name
        assert new.count('\\begin{')==new.count('\\end{'),name
        parts.extend(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/'+rel,tofile='b/'+rel))
        manifest[rel]=dict(before_sha256=hashlib.sha256(old.encode()).hexdigest(),after_sha256=hashlib.sha256(new.encode()).hexdigest(),exact_replacements=changes)
    patch=''.join(parts);dest=HERE/'performance-claims.patch'
    assert not dest.exists(),'Refuse patch overwrite'
    dest.write_text(patch)
    info=dict(status='draft_patch_only_NOT_APPLIED',base_commit=commit,files=manifest,patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
              compiled=False,pdf_updated=False,page_count_verified=False,committed=False,pushed=False,
              scope='Four VLDB sections; observed FP vs selection-cost claims, dataset-cluster CI, verified existing performance-reporting corrections. No algorithm, Proposition5.2 or MAWI24 result modification.')
    (HERE/'verification.json').write_text(json.dumps(info,indent=2)+'\n')
    print(json.dumps(info,indent=2))


if __name__=='__main__':main()
