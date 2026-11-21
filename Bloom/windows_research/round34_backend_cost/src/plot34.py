"""Monochrome dose-response plots: observations, prior forecast and0uscalibration."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
ROOT=Path(__file__).resolve().parents[1]


def luminance(code):
    rgb=[int(code[i:i+2],16)/255 for i in (1,3,5)]
    v=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb]
    return .2126*v[0]+.7152*v[1]+.0722*v[2]


def main():
    verified=json.loads((ROOT/'results/verification.json').read_text());assert verified['status']=='verified' and verified['timing_records']==288
    with (ROOT/'results/curve_points.csv').open() as f:rows=list(csv.DictReader(f))
    forecast=json.loads((ROOT/'results/pretrial_forecast.json').read_text());old={r['dataset']:r for r in forecast['thresholds']}
    datasets=list(old);folder=ROOT/'results/figures';folder.mkdir(exist_ok=True)
    paired={}
    for ds in datasets:
        d=json.loads((ROOT/f'results/{ds}.json').read_text())
        for delta in (0,5,10,25,50,100):
            a={r['rep']:r['ns_per_query'] for r in d['timings'] if r['delay_us']==delta and r['method']=='RA6'}
            b={r['rep']:r['ns_per_query'] for r in d['timings'] if r['delay_us']==delta and r['method']=='BF+Cache'}
            paired[ds,delta]=[a[i]/b[i] for i in range(3)]
    ymax=max(max(v) for v in paired.values())*1.12; ymin=.25
    palette_checks=[]
    for mode,bg,ink,grid in (('light','#ffffff','#202020','#d8d8d8'),('dark','#151515','#eeeeee','#444444')):
        contrast=(max(luminance(bg),luminance(ink))+.05)/(min(luminance(bg),luminance(ink))+.05);assert contrast>=7
        palette_checks.append(dict(mode=mode,surface=bg,ink=ink,contrast=contrast,categorical_hues=False,identity='line pattern and marker; no color-only distinction'))
        fig,axes=plt.subplots(4,2,figsize=(13,13.5),facecolor=bg)
        for ax,ds in zip(axes.ravel(),datasets):
            pp=sorted((r for r in rows if r['dataset']==ds),key=lambda r:float(r['delay_us']))
            x=np.array([float(r['delay_us']) for r in pp]);y=np.array([float(r['measured_ratio']) for r in pp])
            lo=np.array([min(paired[ds,int(v)]) for v in x]);hi=np.array([max(paired[ds,int(v)]) for v in x])
            f=old[ds];ar=f['RA_backend_calls']/f['queries'];ab=f['BF_backend_calls']/f['queries'];xx=np.linspace(0,100,201)
            previous=(f['RA_us']+ar*xx)/(f['BF_us']+ab*xx)
            current=(float(pp[0]['RA_us'])+ar*xx)/(float(pp[0]['BF_us'])+ab*xx)
            ax.set_facecolor(bg);ax.grid(color=grid,lw=.6);ax.set_axisbelow(True)
            ax.plot(xx,previous,':',color=ink,lw=1.5)
            ax.plot(xx,current,'--',color=ink,lw=1.5)
            ax.errorbar(x,y,yerr=[np.maximum(0,y-lo),np.maximum(0,hi-y)],fmt='o-',color=ink,lw=1.5,ms=6.5,mfc=bg,mec=ink,mew=1.2,capsize=3,zorder=4)
            ax.axhline(1,color=ink,lw=.8,alpha=.5);ax.set_xlim(-3,155);ax.set_ylim(ymin,ymax)
            ax.set_xticks([0,10,25,50,100]);ax.tick_params(colors=ink,labelsize=8);ax.spines[['top','right']].set_visible(False)
            for spine in ax.spines.values():spine.set_color(grid)
            ax.set_title(ds.replace('_flow','-flow')+f' | {pp[0]["budget_kib"]} KiB',color=ink,fontsize=11)
            ax.set_xlabel('Artificial added cost per SQL call (us)',color=ink,fontsize=9)
            ax.set_ylabel('RA / BF+Cache total query time',color=ink,fontsize=9)
            end=sorted([(float(previous[-1]),'R31 forecast'),(float(current[-1]),'0us-calibrated'),(float(y[-1]),'Measured')])
            gap=.055*(ymax-ymin);center=sum(v for v,_ in end)/3
            labels=np.array([center-gap,center,center+gap]);labels+=max(0,ymin+.08-labels[0]);labels-=max(0,labels[-1]-(ymax-.08))
            for (value,label),labely in zip(end,labels):
                ax.annotate(label,xy=(100,value),xytext=(107,labely),color=ink,fontsize=7.5,va='center',arrowprops=dict(arrowstyle='-',color=ink,lw=.6),bbox=dict(facecolor=bg,edgecolor='none',pad=.5))
        handles=[Line2D([0],[0],color=ink,marker='o',mfc=bg,lw=1.5,label='Measured at six levels'),Line2D([0],[0],color=ink,ls=':',lw=1.5,label='Prior round31 forecast'),Line2D([0],[0],color=ink,ls='--',lw=1.5,label='Contemporary0us calibration')]
        fig.suptitle('Backend-cost sensitivity: controlled extra CPU wait, not a remote database',color=ink,fontsize=13,y=.996)
        fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.5,.978),ncol=3,frameon=False,labelcolor=ink,fontsize=9)
        fig.text(.5,.009,'Below1: RA faster. Whiskers: paired min/max of3repetitions, NOT confidence intervals. Same200Krequests and fixed filters.',ha='center',color=ink,fontsize=9)
        fig.tight_layout(rect=(0,.025,1,.945))
        for ext in ('png','pdf'):fig.savefig(folder/f'cost_ratios_{mode}.{ext}',dpi=170,facecolor=bg)
        plt.close(fig)
    (ROOT/'results/plot_checks.json').write_text(json.dumps(dict(series='three monochrome line patterns, complete48points, no data exclusions',colors=palette_checks),indent=2)+'\n')
    print('PLOTS GENERATED:48observed points; light/dark PNG and PDF; CSV and full table retained')


if __name__=='__main__':main()
