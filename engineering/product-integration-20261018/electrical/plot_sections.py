"""Plot the evaluated material vertices, not an illustrative invented route."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'integration'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle
import numpy as np
from product_fpc import load_config,route_pose

root=Path(__file__).resolve().parent
config=load_config();fig,axes=plt.subplots(2,1,figsize=(12,7.2),sharex=True,sharey=True)
for ax,(title,slide,descent) in zip(axes,[('STOW',0.,0.),('OPEN, SEATED',79.75,8.2)]):
    data,r=route_pose(config,slide,descent)
    # Left width-edge corners make the actual finite Y-Z section polygon.
    outline=np.r_[data['corners'][:,0,1:],data['corners'][::-1,3,1:]]
    ax.add_patch(Rectangle((0,0),94.25,8,fc='#e8edf4',ec='#8391a6',lw=.9))
    ax.add_patch(Rectangle((slide,8.2-descent),94.25,8,fc='#eef2f6',ec='#8391a6',lw=.9,alpha=.75))
    ax.add_patch(Polygon(outline,closed=True,color='#c53832'))
    ax.plot(data['center'][:,1],data['center'][:,2],color='#c53832',lw=1)
    ax.scatter(data['center'][[0,-1],1],data['center'][[0,-1],2],c='#152e4e',s=25,zorder=4)
    ax.set_title(f'{title}   |   fixed material: 140 mm   |   minimum radius: {r["analytic_minimum_centerline_radius_mm"]:.4f} mm',loc='left',fontsize=11,fontweight='bold')
    ax.set_ylabel('World Z (mm)');ax.set_ylim(-1,18);ax.set_xlim(-2,178);ax.grid(alpha=.2)
    ax.annotate('A end',data['center'][0,1:],xytext=(32,1.2),arrowprops={'arrowstyle':'-','color':'#152e4e'},fontsize=9)
    ax.annotate('B end',data['center'][-1,1:],xytext=(data['center'][-1,1]+6,data['center'][-1,2]+2),arrowprops={'arrowstyle':'-','color':'#152e4e'},fontsize=9)
axes[-1].set_xlabel('World Y (mm)')
fig.suptitle('FPC GEOMETRY STUDY — PHONE FIT REJECTED',fontsize=15,fontweight='bold',y=.98)
fig.text(.08,.025,'Red: actual finite 0.10 mm model section. Width is 12 mm along X. Gray: nominal cabin envelope, not empty free space.\nMinimum radius is geometric only; finished material stack and fatigue capability remain unqualified.',fontsize=9,color='#3f4a5a')
fig.tight_layout(rect=(.02,.08,.98,.94));fig.savefig(root/'FPC-route-sections.png',dpi=170);plt.close(fig)
