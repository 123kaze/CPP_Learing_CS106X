"""Real-data figures,450dpi PNG and SVG; no fabricated or planning numbers."""
from pathlib import Path
import json,csv,collections
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'figures';DATA=OUT/'data';DATA.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','savefig.dpi':450})
COLORS=['#0077BB','#EE7733','#009988','#CC3311']
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def data(name,rows):
    with (DATA/f'{name}.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def save(fig,name):
    fig.savefig(OUT/f'{name}.png',dpi=450,bbox_inches='tight',facecolor='white');fig.savefig(OUT/f'{name}.svg',bbox_inches='tight',facecolor='white');plt.close(fig)
def run():
    assert read(ROOT/'results'/'verification.json')['status']=='passed'
    raw=[r for p in (ROOT/'results'/'main').glob('*/*.json') for r in read(p)['rows']]
    # No pseudoreplication: exactly one trace at each displayed point.
    flow=[dict(dataset=r['dataset'],budget_kib=r['budget_kib'],method=r['method'],fpr=r['fpr'],fp=r['fp_tail'],evaluation_queries=r['evaluation_queries']) for r in raw if r['dataset'].endswith('_flow') and r['method'] in ('Gama','StreamModel','LearnGrid')]
    data('causal_trace_fpr',flow);fig,axes=plt.subplots(1,3,figsize=(9,3),constrained_layout=True)
    for ax,ds,title in zip(axes,('caida_flow','mawi2021_flow','mawi2022_flow'),('Caida','MAWI2021','MAWI2022: frozen holdout')):
        for i,method in enumerate(('Gama','StreamModel','LearnGrid')):
            values=sorted((r for r in flow if r['dataset']==ds and r['method']==method),key=lambda r:r['budget_kib'])
            ax.plot([v['budget_kib'] for v in values],[100*v['fpr'] for v in values],marker=('o','s','^')[i],color=COLORS[i],label=method,linewidth=1.4,markersize=4)
        ax.set(title=title,xlabel='Filter state budget (KiB)',ylabel='Negative FPR (%)');ax.set_xticks([16,24,32]);ax.grid(axis='y',alpha=.2)
    axes[0].legend(frameon=False,fontsize=8);save(fig,'causal_trace_fpr')
    groups=collections.defaultdict(dict)
    for r in raw:
        if not r['dataset'].endswith('_flow'):groups[r['dataset'],r['budget_kib'],r['workload'],r['seed']][r['method']]=r
    pairs=[dict(dataset=k[0],budget_kib=k[1],workload=k[2],seed=k[3],grid_fp=v['LearnGrid']['fp_tail'],model_fp=v['StreamModel']['fp_tail']) for k,v in groups.items()]
    data('model_grid_fp',pairs);fig,ax=plt.subplots(figsize=(5.4,4.1),constrained_layout=True)
    for i,ds in enumerate(('cod','caida','shalla','url')):
        v=[r for r in pairs if r['dataset']==ds];ax.scatter([r['grid_fp']+1 for r in v],[r['model_fp']+1 for r in v],s=10,alpha=.45,color=COLORS[i],label=ds.upper(),rasterized=True)
    lim=max(max(r['grid_fp'],r['model_fp'])+1 for r in pairs)*1.3
    ax.plot([1,lim],[1,lim],color='#666666',linewidth=.9,linestyle='--');ax.set(xscale='log',yscale='log',xlim=(.8,lim),ylim=(.8,lim),xlabel='Learning-grid tail FP +1',ylabel='Stream-model tail FP +1')
    ax.text(.03,.97,'Above diagonal: model has more FP',transform=ax.transAxes,va='top',fontsize=8);ax.legend(frameon=False,loc='lower right');save(fig,'model_grid_fp')
    live=[r for p in (ROOT/'results'/'live').glob('*.json') for r in read(p)['rows']]
    lgr=collections.defaultdict(dict)
    for r in live:lgr[r['dataset'],r['budget_kib'],r['workload'],r['positive_fraction']][r['method'],r['placement']]=r
    rows=[]
    for key,methods in lgr.items():
        g=methods['Gama','before']
        for name,place in (('StreamModel','before'),('StreamModel','after'),('LearnGrid','before'),('LearnGrid','after')):
            r=methods[name,place]
            for gp,rp in zip(g['backend_projections'],r['backend_projections']):rows.append(dict(dataset=key[0],budget_kib=key[1],workload=key[2],positive_fraction=key[3],method=name,placement=place,backend_us=gp['backend_us'],speedup=gp['projected_ns']/rp['projected_ns']))
    data('projected_speedup',rows);fig,axes=plt.subplots(1,2,figsize=(9,3.5),constrained_layout=True)
    labels=['Model / before','Model / after','Grid / before','Grid / after'];variants=[('StreamModel','before'),('StreamModel','after'),('LearnGrid','before'),('LearnGrid','after')]
    for i,(method,place) in enumerate(variants):
        ys=[np.array([r['speedup'] for r in rows if r['method']==method and r['placement']==place and r['backend_us']==us]) for us in (1,10,100)]
        positions=np.arange(3)+(i-1.5)*.17
        bp=axes[0].boxplot(ys,positions=positions,widths=.14,patch_artist=True,showfliers=True,manage_ticks=False,medianprops={'color':'#333333'},flierprops={'markersize':2})
        for b in bp['boxes']:b.set(facecolor=COLORS[i],alpha=.7)
        axes[0].plot([],[],color=COLORS[i],label=labels[i],linewidth=4)
    axes[0].axhline(1,color='#666666',linestyle='--',linewidth=.8);axes[0].set_xticks([0,1,2],['1','10','100']);axes[0].set(xlabel='Assumed backend latency (us)',ylabel='Projected speedup over Gama',yscale='log',title='16 declared scenarios per variant');axes[0].legend(frameon=False,fontsize=7)
    sql=read(ROOT/'results'/'sqlite_backend.json')['rows'];sqlrows=[]
    for i,name in enumerate(('NoFilter','Gama','StreamModel','LearnGrid')):
        values=[r['mean_query_ns']/1000 for r in sql if r['method']==name];sqlrows.extend(dict(method=name,repeat=j,mean_query_us=x) for j,x in enumerate(values))
        axes[1].bar(i,np.median(values),color=COLORS[i],alpha=.8,width=.6);axes[1].scatter([i]*3,values,s=10,color='#333333',zorder=3)
    axes[1].set_xticks(range(4),['No filter','Gama','Model','Grid']);axes[1].set(ylabel='Actual SQLite path (us/query)',title='File-backed KV; OS cache not flushed');axes[1].grid(axis='y',alpha=.2);data('sqlite_latency',sqlrows);save(fig,'end_to_end')
    manifest='''# Figure data manifest

All plotted values are actual experiment outputs. Backend-latency panels are explicitly projections from measured CPU time and backend access counts, not measured disk latency. No mock data are used. PNG450dpi and SVG are exported; English labels avoid platform-dependent Chinese font substitution.

|Figure|Data|Source|Script|Outputs|
|---|---|---|---|---|
|Causal trace FPR|data/causal_trace_fpr.csv|results/main/*_flow/*.json; one trace, no confidence intervals|src/make_figures.py|causal_trace_fpr.png/.svg|
|Model vs grid FP|data/model_grid_fp.csv|results/main for four scalar/URL datasets; fixed workload seeds; +1 only for log display|src/make_figures.py|model_grid_fp.png/.svg|
|Measured CPU projections and actual KV|data/projected_speedup.csv; data/sqlite_latency.csv|results/live/*.json and results/sqlite_backend.json|src/make_figures.py|end_to_end.png/.svg|

The scatter and box distributions are descriptive across declared scenarios, not independent statistical replications. Inferential outputs are in tables/paired_comparisons.csv.
'''
    (OUT/'data-manifest.md').write_text(manifest,encoding='utf-8');print('FIGURES EXPORTED',flush=True)
if __name__=='__main__':run()
