"""Cross-check worst common-cell gaps using library tetrahedral P2 shapes.

No face-polynomial interpolation is used for these direct displacement
samples. Convex-cell triangulation checks polynomial extrema stability; that
is NOT a finite-element mesh refinement or continuum convergence claim.
"""
from pathlib import Path
import sys,json,gzip,hashlib
import numpy as np
from skfem import MeshTet,Basis,ElementTetP2,ElementVector
O=Path('/tmp/razr-contact-field-20261015');B=Path('/tmp/razr-support-coupling-20261015');R=Path('/home/qian-qi/RAZR-SLIDE-contact-field-20261015')
sys.path.insert(0,str(R/'integration'));from contact_patch_audit import extrema
report=json.loads((O/'audit-v1/report.json').read_text());cells=json.loads(gzip.decompress((O/'audit-v1/common-cell-results.json.gz').read_bytes()))
models={}
for body in ('panel','frame'):
 mf=B/('input/mesh.npz' if body=='panel' else 'frame-mesh3/mesh.npz');m=np.load(mf,allow_pickle=False);mesh=MeshTet(m['points'].T,m['tetra'].T)
 bs=Basis(mesh,ElementTetP2(),intorder=2);bv=Basis(mesh,ElementVector(ElementTetP2()),intorder=2);axes=bv.split_indices()
 assert np.array_equal(bs.doflocs,bv.doflocs[:,axes[0]])
 fmap={tuple(sorted(t)):i for i,t in enumerate(mesh.facets.T)};u=np.load(O/('audit-v1/'+body+'-coupled.npz'),allow_pickle=False)['displacement']
 models[body]=(mesh,bs,axes,fmap,u)
def direct(body,tri,pt,case):
 mesh,bs,axes,fmap,u=models[body];facet=fmap[tuple(sorted(tri))];cell=int(mesh.f2t[0,facet]);assert cell>=0
 xyz=mesh.p[:,mesh.t[:,cell]];X=np.linalg.solve(xyz[:,1:]-xyz[:,0,None],np.array(pt)-xyz[:,0]);bar=np.r_[1-X.sum(),X]
 assert bar.min()>-1e-9 and bar.max()<1+1e-9
 shape=np.array([bs.elem.lbasis(X[:,None],i)[0][0] for i in range(10)]);assert abs(shape.sum()-1)<1e-12
 dofs=bs.element_dofs[:,cell];return np.array([shape@u[ix[dofs],case] for ix in axes])
rows=[]
for patch,cs in zip(report['contact_patches'],cells):
 axis=patch['normal_axis'];sign=patch['normal_sign'];tangent=[d for d in range(3) if d!=axis]
 for j in range(8):
  cell=min(cs['cells'],key=lambda c:c['cases'][j]['minimum']);ex=cell['cases'][j];pt=np.zeros(3);pt[tangent]=ex['minimum_at']
  pt[axis]=1.2 if axis==2 else sign*36.325;other=pt.copy();other[axis]=1.2 if axis==2 else sign*36.345
  gap=patch['initial_gap_mm']-sign*(direct('panel',cell['panel_triangle'],pt,j)[axis]-direct('frame',cell['frame_triangle'],other,j)[axis])
  err=abs(gap-ex['minimum']);assert err<1e-9
  vertices=np.array(cell['polygon']);center=vertices.mean(axis=0);c=np.array(cell['quadratic_gap_coefficients'])[:,j]
  sub=[extrema(c,np.array([center,a,b]),patch['origin_tangent_mm']) for a,b in zip(vertices,np.roll(vertices,-1,axis=0))]
  serr=abs(min(s['minimum'] for s in sub)-ex['minimum']);assert serr<1e-9
  rows.append({'patch':patch['patch'],'case':j,'point_panel_mm':pt.tolist(),'point_frame_mm':other.tolist(),'gap_from_tetra_P2_library_mm':float(gap),'gap_from_face_polynomial_mm':ex['minimum'],'absolute_difference_mm':err,'subdivided_polygon_extremum_difference_mm':serr,'gap_below_minus_1e_minus7_mm':bool(gap < -1e-7)})
print('INDEPENDENT_WITNESSES',len(rows),'NEGATIVE',sum(x['gap_below_minus_1e_minus7_mm'] for x in rows),'MAX_ERR',max(x['absolute_difference_mm'] for x in rows),flush=True)
result={'rows':rows,'count':len(rows),'all_agree':True,'negative_witness_count':sum(x['gap_below_minus_1e_minus7_mm'] for x in rows),'same_displacement_solution_different_interpolation_path':True,'polynomial_subdivision_not_FE_mesh_convergence':True,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'candidate_go':False,'manufacturing_go':False}
payload=json.dumps(result,indent=2,allow_nan=False,default=lambda x:x.item())+'\n'
with (O/'independent-gap-witnesses-v2.json').open('x') as f:f.write(payload)
