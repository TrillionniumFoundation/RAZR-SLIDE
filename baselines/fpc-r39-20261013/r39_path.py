"""R39 negative-screening candidate, NOT a supplier-qualified flex cable.

A and B end centres are the static BM28 *catalogue proxies* in R38.
A fixed, B moves on the R38 travel path (s, q). The mathematical three-
dimensional curves maintain a prescribed centreline arclength via a bounded
scalar root solve. This DOES NOT show an elastic equilibrium, clamp/flex fit,
controlled twist, impedance, strain, fatigue, or a buildable in-chassis route.
"""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import brentq
from r38_parts import A_FIXED_XYZ, B_LOCAL_XYZ, MATED_HEIGHT_MM, SLIDE_TRAVEL_MM, DOCK_Z_TRAVEL_MM

LENGTH_TARGET_MM = 125.0  # hypothetical; never supplier-qualified
FPC_WIDTH_MM=1.20
FPC_THICKNESS_MM=0.15
RADIUS_SCREENS_MM=(2.5,7.5,15.0)

@dataclass(frozen=True)
class Candidate:
    name:str
    x_bulge:float
    z_bulge:float
    y_sine_harmonic:int

CANDIDATES=(
 Candidate('INBOARD_SERPENTINE',-4.0,2.0,2),
 Candidate('INNER_SIDE_SERPENTINE',2.5,2.0,2),
 Candidate('OUTBOARD_SERPENTINE',17.0,4.0,2),
 Candidate('OUTBOARD_SINGLE_BOW',17.0,4.0,1),
)

def anchors(s,q):
    a=np.array(A_FIXED_XYZ,dtype=float)+np.array([0,0,MATED_HEIGHT_MM/2])
    b=np.array(B_LOCAL_XYZ,dtype=float)+np.array([0,float(s),float(q)-DOCK_Z_TRAVEL_MM+MATED_HEIGHT_MM/2])
    return a,b

def curve(candidate, s, q, n=401, target=LENGTH_TARGET_MM):
    a,b=anchors(s,q)
    u=np.linspace(0.,1.,n)
    h=candidate.y_sine_harmonic
    base=a[None,:]+(b-a)[None,:]*u[:,None]
    x=candidate.x_bulge*np.sin(np.pi*u)
    z=candidate.z_bulge*np.sin(2*np.pi*u)
    yshape=np.sin(h*np.pi*u)
    dx=candidate.x_bulge*np.pi*np.cos(np.pi*u)
    dz=candidate.z_bulge*2*np.pi*np.cos(2*np.pi*u)
    def velocity(amp):
        v=np.tile(b-a,(n,1))
        v[:,0]+=dx
        v[:,1]+=amp*h*np.pi*np.cos(h*np.pi*u)
        v[:,2]+=dz
        return v
    def arc(amp):
        return float(np.trapezoid(np.linalg.norm(velocity(amp),axis=1),u))
    if arc(0.)>target+1e-8:raise ValueError('fixed length shorter than base path')
    amp=brentq(lambda w:arc(w)-target,0.,150.,xtol=1e-12)
    points=base + np.stack([x,amp*yshape,z],axis=1)
    v=velocity(amp)
    dv=np.tile([0.,0.,0.],(n,1))
    dv[:,0]=-candidate.x_bulge*np.pi**2*np.sin(np.pi*u)
    dv[:,1]=-amp*(h*np.pi)**2*np.sin(h*np.pi*u)
    dv[:,2]=-candidate.z_bulge*(2*np.pi)**2*np.sin(2*np.pi*u)
    vv=np.linalg.norm(v,axis=1)
    curvature=np.linalg.norm(np.cross(v,dv),axis=1)/np.maximum(vv,1e-14)**3
    # For a real FPC, extra width twist curvature/warping must be tested separately.
    rmin=float(1/np.max(curvature)) if np.max(curvature)>0 else float('inf')
    sampled_length=float(np.linalg.norm(np.diff(points,axis=0),axis=1).sum())
    return dict(points=points, tangent=v/vv[:,None],target_length=target,
      numerical_length=arc(amp),polyline_length=sampled_length,amplitude=amp,
      min_centerline_radius_mm=rmin,
      approx_fiber_bending_strain=FPC_THICKNESS_MM/(2*rmin),
      point_bounds={'x':[float(points[:,0].min()),float(points[:,0].max())],
        'y':[float(points[:,1].min()),float(points[:,1].max())],
        'z':[float(points[:,2].min()),float(points[:,2].max())]},
      maximum_curvature_per_mm=float(curvature.max()))

if __name__=='__main__':
 for c in CANDIDATES:
  print('\n',c.name)
  for s,q in [(0,0),(39.875,0),(79.75,0),(79.75,4.1),(79.75,8.2)]:
   a=curve(c,s,q)
   print('pose',s,q,'amp',round(a['amplitude'],3),'Rmin',round(a['min_centerline_radius_mm'],3),'length',round(a['numerical_length'],9),'xbounds',a['point_bounds']['x'],'ybounds', [round(x,2) for x in a['point_bounds']['y']])
