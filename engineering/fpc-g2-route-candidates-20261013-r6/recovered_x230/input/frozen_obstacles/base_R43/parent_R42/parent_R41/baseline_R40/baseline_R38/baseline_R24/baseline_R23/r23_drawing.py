"""Dimensioned diagnostic section, NOT shop drawings/technical tolerances."""
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT=Path(__file__).resolve().parent

def run():
    fig,ax=plt.subplots(figsize=(12.4,5.6))
    for xc,lab in [(-14.2,'LEFT LANE'),(14.2,'RIGHT LANE')]:
        xr=xc-0.55
        def rect(a,b,face,hatch=None,edge='black',z=3):
            ax.add_patch(Rectangle((xr,a),1.1,b-a,facecolor=face,hatch=hatch,edgecolor=edge,zorder=z,linewidth=1.4))
        rect(-2.25,-2.05,'0.5',z=2)          # roof
        rect(-3.10,-2.25,'0.75',z=3)          # jaw
        rect(-3.64,-3.24,'0.93',z=4)         # lug parked
        rect(-2.84,-2.44,'none',hatch='///',edge='0.3',z=5) # failed extended ghost
        ax.plot([xr-.15,xr+1.25],[-3.10,-3.10],linewidth=.7,c='black')
        ax.text(xc,-1.99,lab,ha='center',fontsize=10,weight='bold')
        ax.text(xc,-4.05,'Nominal B-side carrier lug',ha='center',fontsize=8)
    ax.annotate('0.14 mm nominal parked gap\nNOT manufacturing tolerance',xy=(-14.2,-3.17),xytext=(-8.8,-4.0),
        arrowprops={'arrowstyle':'->'},fontsize=9)
    ax.annotate('Jaw & frame roof: solid reaction only\nMaterial / capture / screws UNPROVEN',xy=(14.2,-2.35),xytext=(1.2,-3.95),
        arrowprops={'arrowstyle':'->'},fontsize=9)
    ax.text(0,-2.20,'A-side keys + positive cams\nNOT BUILT; manual jaw translation only',
      ha='center',va='center',fontsize=10,weight='bold')
    ax.text(0,-3.18,'Hatched lugs = forced extended GHOST\nSolid white lugs = parked',ha='center',fontsize=9)
    ax.set_xlim(-20,20);ax.set_ylim(-4.45,-1.6)
    ax.set_xticks([-14.2,0,14.2]);ax.set_xticklabels(['L','CENTER','R'])
    ax.set_ylabel('Z in local cartridge coordinate (mm)')
    ax.set_title('R23 split-guard XZ diagnostic section — NOT AN OEM/MANUFACTURING DRAWING')
    ax.grid(axis='y',alpha=.17)
    fig.tight_layout();p=ROOT/'cad'/'R23_double_guard_cross_section.png'
    fig.savefig(p,dpi=170);plt.close(fig)
    return p
if __name__=='__main__':print(run())
