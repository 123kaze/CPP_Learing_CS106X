"""Scatter diagnostics from checked stored records, never measured-B claims."""
import math
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import NullLocator
from report22 import ROOT,collect,render
THEMES={
 'light':dict(surface='#fcfcfb',text='#0b0b0b',muted='#52514e',grid='#e1e0db',colors=('#2a78d6','#eb6834')),
 'dark':dict(surface='#1a1a19',text='#f0efec',muted='#c3c2b7',grid='#383835',colors=('#3987e5','#d95926'))}


def draw(rows,mode):
    t=THEMES[mode]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'text.usetex':False,'pdf.fonttype':42,
        'text.color':t['text'],'axes.labelcolor':t['muted'],'xtick.color':t['muted'],'ytick.color':t['muted'],
        'axes.edgecolor':t['grid'],'axes.facecolor':t['surface'],'figure.facecolor':t['surface']})
    fig,axes=plt.subplots(1,2,figsize=(11.6,5.3))
    fig.subplots_adjust(left=.078,right=.965,bottom=.24,top=.78,wspace=.35)
    fig.text(.078,.94,'Conditional KL formulas: what survives deployment?',fontsize=16,weight='bold')
    fig.text(.078,.875,'13 fixed non-holdout cases · 141 static candidates · final five-region partitions',fontsize=10,color=t['muted'])
    panels=[('predicted_capped_to_plain_ratio','actual_to_plain_ratio','interior_legal',
             'A: deployed FP comparison','Capped proxy / ideal plain BF (same W)','Measured static FP / measured plain-BF FP'),
            ('B_AM_GM','B_capped_loss','B_interior_legal',
             'B: conditional model check only','AM/GM mismatch expression','Exact capped continuous mismatch loss')]
    points=[]
    for ax,(xf,yf,legal,title,xlabel,ylabel) in zip(axes,panels):
        rr=[r for r in rows if r[xf] is not None and r[yf] is not None and r[xf]>0 and r[yf]>0]
        assert len(rr)==len(rows),'Do not silently omit zero/nonfinite points'
        mn=min(min(r[xf],r[yf]) for r in rr);mx=max(max(r[xf],r[yf]) for r in rr)
        lo=10**(math.log10(mn)-.12);hi=10**(math.log10(mx)+.14)
        ax.plot([lo,hi],[lo,hi],color=t['muted'],linewidth=.8,alpha=.65,zorder=1)
        for valid,color,marker,label in [(True,t['colors'][0],'o','Interior formula applicable'),(False,t['colors'][1],'^','Truncation needed')]:
            subset=[r for r in rr if bool(r[legal])==valid]
            ax.scatter([r[xf] for r in subset],[r[yf] for r in subset],s=46,marker=marker,
                color=color,alpha=.8,edgecolors=t['surface'],linewidths=.9,label=f'{label} (n={len(subset)})',zorder=3)
        ax.set_xscale('log');ax.set_yscale('log');ax.set_xlim(lo,hi);ax.set_ylim(lo,hi)
        ax.xaxis.set_minor_locator(NullLocator());ax.yaxis.set_minor_locator(NullLocator())
        ax.spines[['top','right']].set_visible(False);ax.grid(color=t['grid'],linewidth=.6)
        ax.set_xlabel(xlabel,labelpad=7);ax.set_ylabel(ylabel,labelpad=7)
        ax.set_title(title,loc='left',fontsize=11,pad=10)
        ax.legend(frameon=False,fontsize=7.5,loc='upper left')
        points.append(dict(panel=title,count=len(rr),x=xf,y=yf,legend_field=legal))
    a=axes[0]
    for case,tree,text,offset in [(5,48,'CAIDA fresh: selected EB',(.08,.62)),(8,48,'Shalla fresh: selected EB',(.08,.46))]:
        r=next(r for r in rows if r['case_index']==case and r['trees']==tree and r['family']=='GT19-EB')
        a.annotate(text,(r[panels[0][0]],r[panels[0][1]]),xytext=offset,textcoords='axes fraction',fontsize=7.5,
                   arrowprops=dict(arrowstyle='-',color=t['muted'],lw=.6),color=t['text'])
    b=axes[1]
    # Two series touch near unity; leader labels supplement the legend without color-only identification.
    legal=next(r for r in rows if r['B_interior_legal'] and r['B_AM_GM']>1.01)
    b.annotate('Interior: identity holds',(legal['B_AM_GM'],legal['B_capped_loss']),xytext=(.45,.18),textcoords='axes fraction',
               fontsize=8,arrowprops=dict(arrowstyle='-',color=t['muted'],lw=.6),color=t['text'])
    capped=max((r for r in rows if not r['B_interior_legal']),key=lambda r:abs(math.log(r['B_AM_GM']/r['B_capped_loss'])))
    b.annotate('Truncated: not the same formula',(capped['B_AM_GM'],capped['B_capped_loss']),xytext=(.22,.41),textcoords='axes fraction',
               fontsize=8,arrowprops=dict(arrowstyle='-',color=t['muted'],lw=.6),color=t['text'])
    fig.text(.078,.11,'Diagonal: equality. Both panels use log–log axes. Overlapping points are retained; full values: static_checks.csv.',fontsize=8.5,color=t['muted'])
    fig.text(.078,.061,'A includes estimation, DP and integer-deployment error. B is NOT an empirical q/r-filter comparison or a future guarantee.',fontsize=8.5,color=t['muted'])
    out=ROOT/'figures';out.mkdir(exist_ok=True);stem='kl_diagnostic'+('_dark' if mode=='dark' else '')
    fig.savefig(out/f'{stem}.png',dpi=180,facecolor=t['surface']);fig.savefig(out/f'{stem}.pdf',facecolor=t['surface']);plt.close(fig)
    return points


if __name__=='__main__':
    data=collect()
    for name,text in render(*data[:4]).items():assert (ROOT/'results'/name).read_bytes()==text.encode()
    points=draw(data[1],'light');draw(data[1],'dark')
    (ROOT/'figures/source.json').write_text(json.dumps(dict(points=points,source='../results/static_checks.csv',
        B_scope='conditional capped model, not measured deployments',themes=THEMES),indent=2)+'\n')
    print('Rendered verified A/B diagnostic scatter, light and dark PNG/PDF, no TeX')
