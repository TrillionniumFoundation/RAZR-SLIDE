"""Export one explicit, unconnected 180 deg sidewall U GHOST and dimensional
counterexample to a simple transverse planar return loop with hypothetical R15.
This is *not* a full routed FPC and does not prove other 3-D topologies impossible.
"""
import cadquery as cq,math,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def run():
 R=15.; x=35.2;y0=25.; yc=50.;z0=0.
 p0=cq.Vector(x,y0,-R);p1=cq.Vector(x,yc,-R)
 pm=cq.Vector(x,yc+R,0.);p2=cq.Vector(x,yc,R);p3=cq.Vector(x,y0,R)
 wire=cq.Wire.assembleEdges([cq.Edge.makeLine(p0,p1),cq.Edge.makeThreePointArc(p1,pm,p2),cq.Edge.makeLine(p2,p3)])
 plane=cq.Plane(origin=p0,xDir=(1,0,0),normal=(0,1,0))
 sh=cq.Workplane(plane).rect(1.2,.15).sweep(cq.Workplane().newObject([wire]),isFrenet=False).val()
 assert sh.isValid() and len(sh.Solids())==1
 b=sh.BoundingBox()
 xstrip=(33.66,36.995); zlim=(-8.2,7.68)
 overlap_x=min(b.xmax,xstrip[1])-max(b.xmin,xstrip[0])
 r={ 'hypothetical_R_mm':R,'not_connected_to_anchors':True,
 'description':'R15 YZ transverse U installed in side strip; full OCC ribbon physically over-thick',
 'valid_sweep':True,'volume_mm3':round(sh.Volume(),8),
 'bounds':{k:round(getattr(b,k),7) for k in ('xmin','xmax','ymin','ymax','zmin','zmax')},
 'side_strip_x_intersection_positive_mm':round(overlap_x,7),
 'side_strip_X_fits':b.xmin>=xstrip[0] and b.xmax<=xstrip[1],
 'research_Z_bounds_fits':b.zmin>=zlim[0] and b.zmax<=zlim[1],
 'excess_above_research_Z_max_mm':round(max(0,b.zmax-zlim[1]),7),
 'excess_below_research_Z_min_mm':round(max(0,zlim[0]-b.zmin),7),
 'no_real_FPC_or_supplier_approval':True,'manufacturing_go':False}
 target=ROOT/'cad/R41_GHOST_SIDEWALL_YZ_RETURN_R15_NOT_ROUTED.step'
 target.parent.mkdir(exist_ok=True)
 cq.exporters.export(sh,str(target),exportType='STEP')
 imported=cq.importers.importStep(str(target)).solids().vals()
 assert len(imported)==1 and imported[0].isValid()
 r['STEP']={'name':target.name,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'reimport_valid_solids':len(imported)}
 (ROOT/'verification/R41_sidewall_budget.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(r,indent=2));return r
if __name__=='__main__':run()
