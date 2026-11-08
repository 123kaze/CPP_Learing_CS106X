"""Plot stored total construction times and RA6's measured component groups.

Static PDF/PNG; no TeX required. Data table: results/construction_rows.csv.
Component medians are separate bars, never summed into a synthetic median total.
"""
import argparse
import csv
from pathlib import Path
from statistics import median
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
PALETTES={
    'light':dict(surface='#fcfcfb',ink='#0b0b0b',secondary='#52514e',grid='#e1e0d9',series='#2a78d6'),
    'dark':dict(surface='#1a1a19',ink='#f0efec',secondary='#c3c2b7',grid='#2c2c2a',series='#3987e5'),
}


def main(theme):
    with (ROOT/'results/construction_rows.csv').open() as f:rows=list(csv.DictReader(f))
    p=PALETTES[theme]
    plt.rcParams.update({'font.size':10,'text.color':p['ink'],'axes.labelcolor':p['secondary'],
                         'xtick.color':p['secondary'],'ytick.color':p['secondary'],
                         'figure.facecolor':p['surface'],'axes.facecolor':p['surface'],
                         'axes.edgecolor':p['grid'],'pdf.fonttype':42,'text.usetex':False})
    fig,axes=plt.subplots(2,2,figsize=(11,6.8))
    for i,(ds,kib,limit) in enumerate((('paper_url',128,36),('paper_cod',256,260))):
        data=[r for r in rows if r['dataset']==ds and int(r['budget_kib'])==kib and r['workload']=='once']
        assert len(data)==9
        left,right=axes[i]
        for y,code in enumerate(('RA6','PLBF','LBF')):
            values=[float(r['train_to_ready_s']) for r in data if r['method']==code]
            left.plot([min(values),max(values)],[y,y],color=p['series'],linewidth=2)
            left.scatter(values,[y-.09,y,y+.09],s=24,color=p['series'],alpha=.4,edgecolor=p['surface'],linewidth=.8)
            med=median(values)
            left.scatter([med],[y],s=48,marker='D',color=p['series'],edgecolor=p['surface'],linewidth=1,zorder=4)
            left.annotate(f'{med:.1f} s',(med,y),xytext=(9,0),textcoords='offset points',va='center',color=p['ink'])
        left.set_yticks([0,1,2],['RA6','Original G-PLBF','Original G-LBF'])
        left.set_title(f"{ds.removeprefix('paper_').upper()} {kib} KiB: total",loc='left',fontweight='bold')
        ra=[r for r in data if r['method']=='RA6']
        phases=('select_executable_s','score_input_prepare_s','train_s')
        labels=('Selection + executable build','Scoring + input preparation','Model training')
        for y,key in enumerate(phases):
            v=median(float(r[key]) for r in ra)
            right.barh(y,v,height=.32,color=p['series'],linewidth=0)
            right.annotate(f'{v:.1f} s',(v,y),xytext=(6,0),textcoords='offset points',va='center',color=p['ink'])
        right.set_yticks([0,1,2],labels)
        right.set_title('RA6: recorded component groups',loc='left',fontweight='bold')
        for ax in (left,right):
            ax.set_xlim(0,limit)
            ax.set_ylim(-.55,2.65)
            ax.set_xlabel('Seconds')
            ax.grid(axis='x',color=p['grid'],linewidth=.6)
            ax.set_axisbelow(True)
            ax.tick_params(axis='y',length=0)
            for side in ('top','right','left'):ax.spines[side].set_visible(False)
    fig.suptitle('Faster selection is not faster full construction',x=.08,ha='left',fontsize=15,fontweight='bold')
    fig.subplots_adjust(left=.16,right=.97,top=.86,bottom=.18,wspace=.95,hspace=.65)
    fig.text(.08,.055,'Stored round-8 once-workload runs. Left: 3 runs, diamond = median. Right: per-stage medians, not additive.\n'
             'Totals exclude data read and JIT warm-up. Source / stage boundaries differ across implementations; not an algorithm-only speed comparison.\n'
             'Full values and all budgets: construction_rows.csv and construction_cost.md.',fontsize=8,color=p['secondary'])
    out=ROOT/'figures';out.mkdir(exist_ok=True)
    stem='construction_cost'+('_dark' if theme=='dark' else '')
    fig.savefig(out/(stem+'.png'),dpi=180,facecolor=p['surface'])
    fig.savefig(out/(stem+'.pdf'),facecolor=p['surface'],metadata={'Author':'','Creator':'Matplotlib'})
    plt.close(fig)
    print(out/stem)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--theme',choices=tuple(PALETTES),default='light')
    main(p.parse_args().theme)
