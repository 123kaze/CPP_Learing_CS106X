"""Post-run verifier and monochrome, shape-coded mechanism figures; no experiment changes."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
from pathlib import Path
import sys
import hashlib
import json
import csv
import math
import numpy as np
from scipy.stats import spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def collect():
    manifest=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in manifest['sources'].items():assert sha(BLOOM/p)==h,p
    done=json.loads((ROOT/'results/completion.json').read_text());assert done['status']=='complete' and done['paired_cases']==168
    rows=[];inputs={}
    for ds in ('url','caida_tcp_flow'):
        path=ROOT/f'results/{ds}.json';d=json.loads(path.read_text());inputs[str(path.relative_to(ROOT))]=sha(path)
        assert d['status']=='complete' and len(d['cases'])==84 and d['freeze_sha256']==sha(ROOT/'plan/freeze.json')
        for name,h in d['input_hashes'].items():assert manifest['inputs'][f'windows_research/round2_backlog/cache/{ds}/{name}']==h
        seen=set()
        for r in d['cases']:
            key=tuple(r[k] for k in ('amplitude','seed','ttl','bf_bits_per_member'));assert key not in seen;seen.add(key)
            for name,field in (('paper_M','paper_identity'),('exact_M','exact_identity')):
                p=np.array(r[field]['p']);h=np.array(r[field]['h']);M=np.array(r[field]['M']);active=p>0
                rho=M[active]/h[active];factor=float(p[active]@rho/math.exp(float(p[active]@np.log(rho))))
                assert math.isclose(factor,r[field]['arithmetic_geometric_factor'],rel_tol=1e-10)
                eh=np.array(r[field]['baseline_epsilon']);em=np.array(r[field]['reweighted_epsilon'])
                assert math.isclose(float(M@eh),r[field]['conditional_baseline_fp'],rel_tol=1e-12)
                assert math.isclose(float(M@em),r[field]['conditional_reweighted_fp'],rel_tol=1e-12)
                if r[field]['interior']:assert math.isclose(float((M@eh)/(M@em)),factor,rel_tol=1e-9)
                for arm in r['arms'].values():
                    assert arm['member_fn']==0 and arm['clock']['processed']==300000 and arm['clock']['cutoff']==0
                    assert arm['payload_bytes']*8<=r['budget_bits'] and arm['cache_physical_bytes']<=2048
                    assert arm['used_bits']+arm['unused_budget_bits']==r['budget_bits']
                for cache in ('ttl','clock'):
                    c=r['comparisons'][name][cache];expected=None if c['baseline_fp']==0 else 1-c['reweighted_fp']/c['baseline_fp']
                    assert c['raw_gain']==expected
                rows.append(dict(dataset=ds,arm=name,**{k:r[k] for k in ('amplitude','seed','ttl','bf_bits_per_member')},interior=r[field]['interior'],
                                 predicted_gain=r[field]['predicted_gain'],conditional_gain=r[field]['conditional_gain'],
                                 ttl_gain=r['comparisons'][name]['ttl']['raw_gain'],clock_gain=r['comparisons'][name]['clock']['raw_gain'],
                                 ttl_baseline_fp=r['comparisons'][name]['ttl']['baseline_fp'],ttl_reweighted_fp=r['comparisons'][name]['ttl']['reweighted_fp'],
                                 clock_baseline_fp=r['comparisons'][name]['clock']['baseline_fp'],clock_reweighted_fp=r['comparisons'][name]['clock']['reweighted_fp']))
        assert len(seen)==84
    assert len(rows)==336
    return rows,inputs


def summaries(rows):
    out=[]
    for arm in ('paper_M','exact_M'):
        for ds in ('url','caida_tcp_flow'):
            for scope in ('interior','clipped','all'):
                rr=[r for r in rows if r['arm']==arm and r['dataset']==ds and (scope=='all' or r['interior']==(scope=='interior'))]
                for cache in ('ttl','clock'):
                    points=[r for r in rr if r[cache+'_gain'] is not None]
                    x=np.array([r['predicted_gain'] for r in points]);y=np.array([r[cache+'_gain'] for r in points])
                    corr=float(spearmanr(x,y).statistic) if len(points)>2 and np.ptp(x)>0 and np.ptp(y)>0 else None
                    out.append(dict(arm=arm,dataset=ds,scope=scope,cache=cache,cases=len(rr),plotted=len(points),
                                    wins=sum(r[cache+'_reweighted_fp']<r[cache+'_baseline_fp'] for r in rr),
                                    ties=sum(r[cache+'_reweighted_fp']==r[cache+'_baseline_fp'] for r in rr),
                                    losses=sum(r[cache+'_reweighted_fp']>r[cache+'_baseline_fp'] for r in rr),
                                    median_actual_gain=float(np.median(y)) if len(y) else None,spearman_descriptive=corr))
    return out


def plots(rows):
    folder=ROOT/'results/figures';folder.mkdir(exist_ok=True)
    for arm in ('paper_M','exact_M'):
        rr=[r for r in rows if r['arm']==arm]
        for mode,bg,ink,grid in (('light','#ffffff','#202020','#d6d6d6'),('dark','#151515','#eeeeee','#444444')):
            fig,axes=plt.subplots(1,3,figsize=(15,5.3),layout='constrained',facecolor=bg)
            yall=[100*r[c+'_gain'] for r in rr for c in ('ttl','clock') if r[c+'_gain'] is not None]
            yrange=(min(-5,min(yall)-8),max(50,max(yall)+8));xmax=max(r['predicted_gain'] for r in rr)*100+3
            specs=[('ttl',True,'Fixed TTL: both allocations interior'),('ttl',False,'Fixed TTL: clipping (outside identity)'),('clock',None,'Fixed-memory CLOCK (outside fixed T)')]
            for ax,(cache,interior,title) in zip(axes,specs):
                ax.set_facecolor(bg);ax.grid(color=grid,lw=.6,zorder=0);ax.set_axisbelow(True)
                for ds,marker,label in (('url','o','URL'),('caida_tcp_flow','^','TCP-only')):
                    points=[r for r in rr if r['dataset']==ds and (interior is None or r['interior']==interior) and r[cache+'_gain'] is not None]
                    ax.scatter([100*r['predicted_gain'] for r in points],[100*r[cache+'_gain'] for r in points],s=64,marker=marker,
                               facecolors='none' if ds=='url' else ink,edgecolors=ink,linewidths=1,alpha=.68,label=f'{label} (n={len(points)})',zorder=3)
                    if points:
                        end=max(points,key=lambda r:(r['predicted_gain'],r[cache+'_gain']))
                        ax.annotate(label,(100*end['predicted_gain'],100*end[cache+'_gain']),xytext=(-5,10),textcoords='offset points',ha='right',color=ink,fontsize=8)
                ax.plot([0,xmax],[0,xmax],color=ink,ls='--',lw=1.5,label='y=x',zorder=1)
                ax.axhline(0,color=ink,lw=.8);ax.set_xlim(-1,xmax);ax.set_ylim(*yrange)
                ax.set_title(title,color=ink,fontsize=10);ax.set_xlabel('AM/GM predicted FP improvement (%)',color=ink)
                ax.tick_params(colors=ink);ax.spines[['top','right']].set_visible(False)
                for spine in ax.spines.values():spine.set_color(grid)
                ax.legend(loc='lower right',fontsize=8,facecolor=bg,edgecolor=grid,labelcolor=ink)
            axes[0].set_ylabel('Measured physical-BF FP improvement (%)',color=ink)
            title='Paper Che weights' if arm=='paper_M' else 'Exact finite-horizon TTL weights'
            fig.suptitle(title+' | fixed scorer, regions and paired queries',color=ink,fontsize=13)
            fig.supxlabel('Synthetic popularity on real feature pools. 3 paired seeds, not independent cases. Negative gains and low-count noise retained.',color=ink,fontsize=9)
            for ext in ('png','pdf'):fig.savefig(folder/f'{arm}_{mode}.{ext}',dpi=170,facecolor=bg)
            plt.close(fig)


def interactive(rows):
    # One neutral ink, shape-coded identities: no categorical hues/CVD color distinctions.
    template='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Reweighting mechanism — all outcomes</title>
<style>:root{--bg:#fff;--ink:#202020;--grid:#d6d6d6}body.dark{--bg:#151515;--ink:#eee;--grid:#444}body{background:var(--bg);color:var(--ink);font:15px system-ui;margin:24px}button,select{background:var(--bg);color:var(--ink);border:1px solid var(--grid);padding:7px}#plots{display:grid;grid-template-columns:repeat(auto-fit,minmax(350px,1fr));gap:16px}svg{width:100%;height:auto}table{border-collapse:collapse;font-size:12px}td,th{padding:5px;border-bottom:1px solid var(--grid)}#tip{position:fixed;display:none;pointer-events:none;background:var(--bg);border:1px solid var(--ink);padding:10px;white-space:pre;z-index:2}a{color:var(--ink)}</style>
<h1>Conditional reweighting mechanism</h1><p>Synthetic popularity on real feature pools. Fixed scorer/regions; three paired seeds, not independent cases. All negative outcomes retained.</p>
<div><label>Weights <select id="arm"><option value="paper_M">Paper Che M(T)</option><option value="exact_M">Exact finite-horizon TTL M(T)</option></select></label> <button id="theme">Toggle light/dark</button> <a href="scatter_rows.csv">All data (CSV)</a></div>
<p>○ URL　▲ TCP-only　— — y=x. Color is not used to encode dataset. Hover or focus a point for raw FP counts. Fractional gain is undefined when baseline FP is zero.</p><div id="plots"></div><div id="tip" role="tooltip"></div><details><summary>Accessible data table</summary><div id="table"></div></details>
<script>const rows=__DATA__;const NS='http://www.w3.org/2000/svg';const tip=document.querySelector('#tip');
function el(tag,attrs,parent,text){let e=document.createElementNS(NS,tag);for(let[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;parent.appendChild(e);return e}
function render(){let data=rows.filter(r=>r.arm===document.querySelector('#arm').value);let host=document.querySelector('#plots');host.replaceChildren();let yy=data.flatMap(r=>[r.ttl_gain,r.clock_gain]).filter(x=>x!==null).map(x=>100*x),ymin=Math.min(-5,...yy)-8,ymax=Math.max(50,...yy)+8,xmax=Math.max(...data.map(r=>r.predicted_gain*100))+3;
for(let[cache,cond,title]of [['ttl',true,'TTL: both interior'],['ttl',false,'TTL: clipped / outside identity'],['clock',null,'CLOCK: outside fixed T']]){let box=document.createElement('div');host.appendChild(box);let s=el('svg',{viewBox:'0 0 440 400',role:'img','aria-label':title},box);el('text',{x:220,y:20,'text-anchor':'middle',fill:'var(--ink)'},s,title);let x=v=>60+v/xmax*350,y=v=>340-(v-ymin)/(ymax-ymin)*280;
for(let i=0;i<=5;i++){let v=ymin+(ymax-ymin)*i/5;el('line',{x1:60,x2:410,y1:y(v),y2:y(v),stroke:'var(--grid)'},s);el('text',{x:54,y:y(v)+4,'text-anchor':'end',fill:'var(--ink)','font-size':11},s,v.toFixed(0)+'%')}
for(let i=0;i<=4;i++){let v=xmax*i/4;el('text',{x:x(v),y:357,'text-anchor':'middle',fill:'var(--ink)','font-size':11},s,v.toFixed(0)+'%')}
el('line',{x1:x(0),x2:x(xmax),y1:y(0),y2:y(xmax),stroke:'var(--ink)','stroke-dasharray':'6 4'},s);el('text',{x:230,y:380,'text-anchor':'middle',fill:'var(--ink)','font-size':12},s,'Predicted FP improvement');el('text',{x:14,y:205,transform:'rotate(-90 14 205)','text-anchor':'middle',fill:'var(--ink)','font-size':12},s,'Measured FP improvement');
for(let r of data.filter(r=>(cond===null||r.interior===cond)&&r[cache+'_gain']!==null)){let px=x(r.predicted_gain*100),py=y(r[cache+'_gain']*100);if(r.dataset==='url')el('circle',{cx:px,cy:py,r:4,fill:'var(--bg)',stroke:'var(--ink)'},s);else el('path',{d:`M${px} ${py-5}L${px+5} ${py+4}L${px-5} ${py+4}Z`,fill:'var(--ink)',stroke:'var(--bg)'},s);let hit=el('circle',{cx:px,cy:py,r:9,fill:'transparent',tabindex:0,role:'graphics-symbol'},s);let text=`${r.dataset}, seed ${r.seed}, a=${r.amplitude}, T=${r.ttl}\nbits/member=${r.bf_bits_per_member}, interior=${r.interior}\npredicted=${(100*r.predicted_gain).toFixed(2)}%, measured=${(100*r[cache+'_gain']).toFixed(2)}%\nFP: ${r[cache+'_baseline_fp']} → ${r[cache+'_reweighted_fp']}`;hit.setAttribute('aria-label',text);el('title',{},hit,text);let show=e=>{tip.textContent=text;tip.style.display='block';let rect=hit.getBoundingClientRect();tip.style.left=Math.min(innerWidth-330,e.clientX||rect.x)+'px';tip.style.top=Math.min(innerHeight-140,(e.clientY||rect.y)+12)+'px'};hit.onpointerenter=show;hit.onfocus=show;hit.onpointerleave=hit.onblur=()=>tip.style.display='none'} }
let cols=['dataset','amplitude','seed','ttl','bf_bits_per_member','interior','predicted_gain','ttl_baseline_fp','ttl_reweighted_fp','ttl_gain','clock_baseline_fp','clock_reweighted_fp','clock_gain'];let table=document.createElement('table');let tr=table.insertRow();for(let c of cols){let th=document.createElement('th');th.textContent=c;tr.appendChild(th)}for(let r of data){let row=table.insertRow();for(let c of cols)row.insertCell().textContent=r[c]===null?'undefined':r[c]}document.querySelector('#table').replaceChildren(table)}
document.querySelector('#arm').onchange=render;document.querySelector('#theme').onclick=()=>document.body.classList.toggle('dark');render();</script></html>'''
    (ROOT/'results/interactive.html').write_text(template.replace('__DATA__',json.dumps(rows,allow_nan=False)))


def main():
    rows,inputs=collect();summary=summaries(rows)
    with (ROOT/'results/scatter_rows.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (ROOT/'results/verification.json').write_text(json.dumps(dict(status='verified',paired_cases=168,physical_builds=504,comparison_rows=336,inputs=inputs),indent=2)+'\n')
    (ROOT/'results/summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    text=['# Proposition5.3: controlled mechanism experiment','',
          'Paper reference:e256658:vldb/sections/analysis.tex, prop:gain. Two real feature pools with controlled synthetic popularity; not a new real trace.168paired settings,504physicalBFbuilds, three shared seeds. Model and regions fixed; no score/partition/cache search.','',
          '## Applicability','',
          '- Both allocations interior:117/168settings; clipping:51/168 (for both paper and exact-TTL weight definitions). Formula is evaluated only over positive-member regions; URL has4 and TCP has3 such regions in the frozen5-region layout. Empty regions are not positive-weight AM/GM terms.',
          '- Continuous interior ratios match the AM/GM factor within1e-9relative tolerance. This verifies the implementation/algebra, not empirical CLOCK optimality.',
          '- PhysicalBFqueries additionally have integer probe/bit allocation and finite-key/stream variability. Even in the interior panel these are not literally continuous ideal BFs. Exact-TTL M isolates finite-horizon cache approximation; paper-Che M is separately plotted.',
          '- Fixed TTL has unconstrained occupancy, so equalT is NOT equal cache memory. The CLOCK panel instead has2048bytes per filter and therefore violates exogenousT; no theorem guarantee is claimed there.',
          '- Regional total traffic is held constant across correlation strength; only within-region concentration changes. Empty query regions are renormalized and disclosed in raw JSON. At amplitude0, unequal region pool sizes can still make M/h nonconstant; amplitude is a controlled input, NOT the predicted gain axis.','',
          '## All paired outcomes (wins/ties/losses, no filtering)','',
          '| Weights | Dataset | Cache | Cases | Win/tie/loss | Median measured improvement |','|---|---|---|---:|---|---:|']
    for s in summary:
        if s['scope']=='all':text.append(f'| {s["arm"]} | {s["dataset"]} | {s["cache"]} | {s["cases"]} | {s["wins"]}/{s["ties"]}/{s["losses"]} | {s["median_actual_gain"]:.2%} |')
    text+=['','## Interior-only association (descriptive; no independent-case p-values)','',
           '| Weights | Dataset | Cache | Cases | Spearman correlation of predicted/actual gain |','|---|---|---|---:|---:|']
    for s in summary:
        if s['scope']=='interior':text.append(f'| {s["arm"]} | {s["dataset"]} | {s["cache"]} | {s["cases"]} | {s["spearman_descriptive"]:.4f} |')
    text+=['','## Reading the figures','',
           '[Interactive, keyboard-accessible scatter and table](interactive.html) · [All plotted rows](scatter_rows.csv)','',
           '![Paper weights, all conditions separated](figures/paper_M_light.png)','',
           '![Exact TTL weights, all conditions separated](figures/exact_M_light.png)','',
           'Dark versions and vector PDFs accompany both figures. Monochrome ink with circle/triangle shapes avoids categorical-color ambiguity; both modes use separately chosen high-contrast ink/surface. No data points cropped to hide regressions.','',
           'The result supports a conditional mechanism and its boundaries, not a claim that higher arbitrary variance always improves deployment, nor that the learning estimator accurately recovers the oracle M. Some URL low-FP cases are noisy and regress sharply. These losses remain in the figures and tables. New real-workload evidence is a separate round27 task.']
    (ROOT/'results/report.md').write_text('\n'.join(text)+'\n')
    plots(rows);interactive(rows)
    print('PASS:168paired settings504builds; independent result checks; figures and complete table generated',flush=True)


if __name__=='__main__':main()
