"""Plot only a complete verified experiment; PNG/PDF without TeX or external fonts."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, NullLocator, MaxNLocator
from common15 import ROOT
from report15 import collect, render

# Categorical slots validated with dataviz in light and dark modes.
THEMES={
    'light':dict(surface='#fcfcfb',text='#0b0b0b',muted='#52514e',grid='#e1e0db',ra6='#2a78d6',replay='#eb6834'),
    'dark':dict(surface='#1a1a19',text='#f0efec',muted='#c3c2b7',grid='#383835',ra6='#3987e5',replay='#d95926'),
}


def plot(summary, output, mode='light', linear=False):
    c=THEMES[mode]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'text.color':c['text'],
                         'axes.labelcolor':c['muted'],'xtick.color':c['muted'],'ytick.color':c['muted'],
                         'axes.edgecolor':c['grid'],'axes.facecolor':c['surface'],'figure.facecolor':c['surface'],
                         'text.usetex':False,'pdf.fonttype':42})
    fig,axes=plt.subplots(1,2,figsize=(11.2,4.9),gridspec_kw={'width_ratios':[1.35,1]},layout=None)
    fig.subplots_adjust(left=.078,right=.97,bottom=.22,top=.73,wspace=.32)
    fig.text(.078,.94,'Selection cost as the learning window grows',fontsize=17,weight='bold')
    fig.text(.078,.865,'CAIDA · 256 KiB · 180 feasible candidates · fixed Zipf(1.0) stream',fontsize=10,color=c['muted'])
    xs=[s['L']/1e6 for s in summary]
    ax,ratio=axes
    names={'ra6':'RA-PLBF (RA6)','replay':'Replay (early stopping)'}
    for method,marker,style in (('ra6','o','-'),('replay','s','--')):
        vals=[s['methods'][method]['selection_s'] for s in summary]
        ys=[r['median'] for r in vals]
        err=[[r['median']-r['min'] for r in vals],[r['max']-r['median'] for r in vals]]
        ax.errorbar(xs,ys,yerr=err,color=c[method],linewidth=1.5,linestyle=style,marker=marker,
                    markersize=6.5,markeredgecolor=c['surface'],markeredgewidth=1.5,
                    capsize=3,elinewidth=1,label=names[method],zorder=3)
        ax.annotate('RA6' if method=='ra6' else 'Replay',xy=(xs[-1],ys[-1]),xytext=(8,0),
                    textcoords='offset points',va='center',fontsize=9,color=c['text'],annotation_clip=False)
    vals=[s['speedup_median'] for s in summary]
    err=[[s['speedup_median']-s['speedup_range'][0] for s in summary],
         [s['speedup_range'][1]-s['speedup_median'] for s in summary]]
    ratio.errorbar(xs,vals,yerr=err,color=c['ra6'],linewidth=1.5,marker='o',markersize=6.5,
                   markeredgecolor=c['surface'],markeredgewidth=1.5,capsize=3,elinewidth=1,zorder=3)
    ratio.axhline(1,color=c['grid'],linewidth=1)
    ratio.annotate(f'{vals[-1]:.1f}×',xy=(xs[-1],vals[-1]),xytext=(8,0),textcoords='offset points',
                   va='center',fontsize=9,color=c['text'],annotation_clip=False)
    for a in axes:
        a.spines[['top','right']].set_visible(False)
        a.set_axisbelow(True);a.grid(axis='y',color=c['grid'],linewidth=.7)
        a.set_xlabel('Learning-period queries (millions)',labelpad=9)
        if not linear:
            a.set_xscale('log');a.set_xticks(xs,labels=[f'{x:g}' for x in xs]);a.xaxis.set_minor_locator(NullLocator())
            a.set_xlim(.85,160)
        else:
            a.set_xlim(0,112);a.set_xticks([0,20,40,60,80,100])
        a.tick_params(length=3,width=.6)
    if not linear:
        ax.set_yscale('log');ax.yaxis.set_major_formatter(ScalarFormatter());ax.yaxis.set_minor_locator(NullLocator())
    else:ax.set_ylim(bottom=0)
    ax.set_ylabel('Inclusive selection time (seconds)')
    ratio.set_ylabel('Paired speedup: Replay / RA6')
    ratio.set_ylim(0,max(s['speedup_range'][1] for s in summary)*1.2)
    ratio.yaxis.set_major_locator(MaxNLocator(nbins=5))
    ax.set_title('Counting and mapping included',loc='left',fontsize=11,pad=12)
    ratio.set_title('Not just an absolute seconds gap',loc='left',fontsize=11,pad=12)
    legend=ax.legend(loc='upper left',frameon=False,fontsize=9,handlelength=2.5)
    for text in legend.get_texts():text.set_color(c['text'])
    fig.text(.078,.10,'Markers: three-run medians. Whiskers: min–max. Ratio: median of paired ratios.',fontsize=9,color=c['muted'])
    fig.text(.078,.052,('Linear-axis view. ' if linear else 'Left: log–log axes; right: log-x. ')+
             'Models/scores prepared beforehand; no training or extrapolated timings.',fontsize=8.5,color=c['muted'])
    output.mkdir(exist_ok=True)
    stem='learning_scaling'+('_linear' if linear else '')+('_dark' if mode=='dark' else '')
    fig.savefig(output/f'{stem}.png',dpi=180,facecolor=c['surface'])
    fig.savefig(output/f'{stem}.pdf',facecolor=c['surface'])
    plt.close(fig)


if __name__=='__main__':
    rows,summary,_=collect()
    for name,text in render(rows,summary).items():
        assert (ROOT/'results'/name).read_bytes()==text.encode(), 'Regenerate verified report before plotting'
    plot(summary,ROOT/'figures')
    plot(summary,ROOT/'figures',mode='dark')
    plot(summary,ROOT/'figures',linear=True)
    (ROOT/'figures/source.json').write_text(json.dumps(dict(source='../results/summary.json',
        points=7,repetitions=3,interval='min-max',ratios='median of paired ratios',
        themes=THEMES,main_axes='time: log-x/log-y; speedup: log-x/linear-y'),indent=2)+'\n')
    print('Rendered verified light/dark and linear-axis PNG/PDF figures')
