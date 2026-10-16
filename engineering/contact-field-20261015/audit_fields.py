"""Reconstruct saved coupled P2 fields; audit gauge reactions and local gaps.

Quadratic gap extrema are computed on every common planar triangle polygon,
not inferred from average-port complementarity. Reference-coordinate,
small-displacement pairing only. No contact repair or geometry modification.
"""
from pathlib import Path
import argparse,hashlib,json,sys,time
import numpy as np
from shapely.geometry import Polygon,box,Point
from shapely.strtree import STRtree
from skfem import MeshTet,Basis,ElementVector,ElementTetP2

ROOT=Path('/home/qian-qi/RAZR-SLIDE-contact-field-20261015')
BASE=Path('/tmp/razr-support-coupling-20261015')
sys.path.insert(0,str(ROOT/'integration'))
from contact_support_budget import solve_support
from contact_patch_audit import triangle_coefficients,extrema,gap_status,evaluate
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();OUT=a.output;OUT.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False,default=lambda x:x.item() if hasattr(x,'item') else x.tolist())+'\n')
inputs={};data={};fields={};reports={};meshes={};bases={}
for b in ('panel','frame'):
 d=BASE/(b+'-final3');r=json.loads((d/'report.json').read_text());reports[b]=r
 for name,key in [('fields.npz','fields_sha256'),('reduced.npz','reduced_sha256')]:
  f=d/name;assert sha(f)==r[key];inputs[str(f)]=sha(f)
  loaded={k:v for k,v in np.load(f,allow_pickle=False).items()}
  if name=='fields.npz':fields[b]=loaded
  else:data[b]=loaded
 mf=BASE/('input/mesh.npz' if b=='panel' else 'frame-mesh3/mesh.npz');assert sha(mf)==r['mesh_sha256'];inputs[str(mf)]=sha(mf)
 m=np.load(mf,allow_pickle=False);mesh=MeshTet(m['points'].T,m['tetra'].T);basis=Basis(mesh,ElementVector(ElementTetP2()),intorder=4)
 assert basis.N==r['dofs'] and np.array_equal(basis.doflocs,fields[b]['dof_xyz'])
 meshes[b]=mesh;bases[b]=basis
 print('LOADED',b,basis.N,flush=True)
pp,ff=data['panel'],data['frame'];assert np.max(abs(pp['G']+ff['G']))<1e-8
cases=[];panel_u=[];frame_u=[];panel_load=[];frame_load=[];panel_reac=[];frame_reac=[]
for pre0 in (0.,2e-4):
 for j in range(4):
  F=1e-5;ratio=1.;pre=np.full(4,pre0);r=solve_support(pp['H']+ratio*ff['H'],pp['G'],pp['q0'][:,j]*F,pp['external_rigid_resultants'][:,j]*F,np.full(4,5.),pre,np.r_[np.zeros(4),np.full(4,.02)])
  assert r['passed'];lam=np.array(r['forces']);rigid=np.array(r['rigid_mode_coordinates']);weights=np.r_[-lam,np.eye(4)[j]*F]
  P=fields['panel'];Q=fields['frame'];up=P['solutions']@weights+P['rigid_modes']@rigid;uf=-ratio*Q['solutions']@lam
  lp=np.column_stack([P['port_forces'],P['external_forces']])@weights;lf=-Q['port_forces']@lam
  rp=P['reactions']@weights;rf=-Q['reactions']@lam
  gauge=float(np.max(abs(rp[P['D']])));assert gauge<1e-9
  residual=float(np.max(abs(np.delete(rp,P['D']))));assert residual<1e-9
  # Frame support reactions plus BOTH bodies' applied loads balance globally.
  def resultant(b,f):
   q=fields[b];axes=[q['axis'+str(k)] for k in range(3)];nodal=np.stack([f[ix] for ix in axes],axis=1);xyz=q['dof_xyz'][:,axes[0]].T
   return np.r_[nodal.sum(axis=0),np.cross(xyz,nodal).sum(axis=0)]
  balance=resultant('panel',lp)+resultant('frame',lf)+resultant('frame',rf)
  assert np.max(abs(balance))<1e-8
  q=P['port_forces'].T@up+Q['port_forces'].T@uf
  assert np.max(abs(q-np.array(r['relative_port_displacements'])))<1e-8
  # The symmetric reduced energy must match full nodal load/displacement work.
  ep=.5*up@lp;ef=.5*uf@lf
  expected=.5*(F*F*pp['external_compliance'][j,j]-2*F*pp['q0'][:,j]@lam+lam@pp['H']@lam)+.5*ratio*lam@ff['H']@lam
  assert abs(ep+ef-expected)<1e-10*max(1,abs(expected))
  cases.append({'case':len(cases),'spring_initial_over_Epanel_mm2':pre0,'force_over_Epanel_mm2':F,'load_index':j,'frame_compliance_ratio':ratio,'average_model':r,'combined_panel_gauge_max':gauge,'combined_panel_free_residual_max':residual,'global_force_moment_balance':balance.tolist(),'full_field_work_over2':[float(ep),float(ef)],'fields_checked_independently_of_small_matrix_observation':True})
  panel_u.append(up);frame_u.append(uf);panel_load.append(lp);frame_load.append(lf);panel_reac.append(rp);frame_reac.append(rf)
  print('RECONSTRUCT',len(cases)-1,'GAUGE',gauge,'BALANCE',float(np.max(abs(balance))),flush=True)
# Complete reconstructed fields and actual loads for a separate fresh K audit.
for b,uu,ll,rr in [('panel',panel_u,panel_load,panel_reac),('frame',frame_u,frame_load,frame_reac)]:
 np.savez_compressed(OUT/(b+'-coupled.npz'),displacement=np.stack(uu,axis=1),load=np.stack(ll,axis=1),saved_residual=np.stack(rr,axis=1),D=fields[b]['D'])
U={'panel':np.stack(panel_u,axis=1),'frame':np.stack(frame_u,axis=1)}
del panel_u,frame_u,panel_load,frame_load,panel_reac,frame_reac
# Construct P2 interpolation from actual surface vertices/edge nodes, not nearest-node values.
edge_maps={b:{tuple(e):i for i,e in enumerate(mesh.edges.T)} for b,mesh in meshes.items()}
def surface(b,axis,plane,tangent,region,origin):
 mesh=meshes[b];basis=bases[b];ids=mesh.boundary_facets();tris=mesh.facets[:,ids].T;xyz=mesh.p.T
 good=np.max(abs(xyz[tris,axis]-plane),axis=1)<1e-7;records=[]
 for tri in tris[good]:
  xy=xyz[tri][:,tangent];poly=Polygon(xy).intersection(region)
  if poly.is_empty or poly.area<=1e-14:continue
  if poly.geom_type!='Polygon' or poly.interiors:raise ValueError('unexpected nonconvex/holed cell')
  ei=[edge_maps[b][tuple(sorted((int(tri[i]),int(tri[j]))))] for i,j in ((0,1),(1,2),(2,0))]
  dofs=np.r_[basis.nodal_dofs[axis,tri],basis.edge_dofs[axis,ei]]
  pts=np.vstack([xy,(xy[0]+xy[1])/2,(xy[1]+xy[2])/2,(xy[2]+xy[0])/2])
  coeff=triangle_coefficients(xy,U[b][dofs],origin)
  assert np.max(abs(evaluate(coeff,pts,origin)-U[b][dofs]))<1e-8
  records.append((poly,coeff,tri.tolist(),dofs.tolist()))
 if not records:raise ValueError('empty surface')
 return records
patches=[];summaries=[];all_cells=[]
centers=[(-34.8,50.),(34.8,50.),(-34.8,70.),(34.8,70.)]
for i,(x,y) in enumerate(centers):patches.append((f'pad{i}',4+i,2,1.2,1.2,1.,0.,[0,1],Point(x,y).buffer(1.8,quad_segs=64),[x,y]))
for side,sign in [('L',-1),('R',1)]:
 for seg,y0,y1 in [('front',16.5,20.5),('rear',22.5,24.)]:
  idx=8+(0 if side=='L' else 2)+(0 if seg=='front' else 1)
  patches.append((f'key_{side}_{seg}',idx,0,sign*36.325,sign*36.345,float(sign),.02,[1,2],box(y0,.65,y1,2.),[(y0+y1)/2,1.325]))
for label,idx,axis,plane_p,plane_f,n,g,tan,region,origin in patches:
 A=surface('panel',axis,plane_p,tan,region,origin);B=surface('frame',axis,plane_f,tan,region,origin)
 tree=STRtree([x[0] for x in B]);cells=[]
 for ia,(pa,ca,ta,da) in enumerate(A):
  for ib in tree.query(pa,predicate='intersects'):
   pb,cb,tb,db=B[int(ib)];poly=pa.intersection(pb)
   if poly.is_empty or poly.area<=1e-12:continue
   if poly.geom_type!='Polygon' or poly.interiors:raise ValueError('invalid common cell')
   vertices=np.array(poly.exterior.coords)[:-1];coeff=-n*(ca-cb);coeff[0,:]+=g
   rec={'polygon':vertices.tolist(),'area_mm2':float(poly.area),'panel_triangle':ta,'frame_triangle':tb,'panel_P2_dofs':da,'frame_P2_dofs':db,'quadratic_gap_coefficients':coeff.tolist(),'cases':[]}
   for j in range(len(cases)):
    ex=extrema(coeff[:,j],vertices,origin);rec['cases'].append(ex)
   cells.append(rec)
 if not cells:raise ValueError('no actual mesh common region')
 area=sum(c['area_mm2'] for c in cells);a_area=sum(v[0].area for v in A)
 assert area<=a_area*(1+1e-7)
 rows=[]
 for j,case in enumerate(cases):
  low=min(cells,key=lambda c:c['cases'][j]['minimum']);high=max(cells,key=lambda c:c['cases'][j]['maximum']);mn=low['cases'][j]['minimum'];mx=high['cases'][j]['maximum'];force=case['average_model']['forces'][idx]
  status=gap_status(mn,mx,tolerance_mm=1e-7,compressive_force=force,force_tolerance=1e-11)
  rows.append({'case':j,'minimum_gap_mm':mn,'maximum_gap_mm':mx,'minimum_location_tangent_mm':low['cases'][j]['minimum_at'],'maximum_location_tangent_mm':high['cases'][j]['maximum_at'],'minimum_type':low['cases'][j]['minimum_kind'],'minimum_cell_vertices':low['polygon'],'minimum_cell_gap_polynomial':np.array(low['quadratic_gap_coefficients'])[:,j].tolist(),'origin_tangent_mm':origin,'mean_model_gap_mm':case['average_model']['remaining_contact_gaps'][idx-4],'compressive_force_over_Epanel_mm2':force,**status})
 summaries.append({'patch':label,'normal_axis':axis,'normal_sign':n,'initial_gap_mm':g,'origin_tangent_mm':origin,'common_cells':len(cells),'panel_selected_area_mm2':a_area,'common_area_mm2':area,'panel_uncovered_area_mm2':a_area-area,'circular_region_inscribed_256gon_if_pad':label.startswith('pad'),'polynomial_extrema_not_point_sampling':True,'results':rows})
 all_cells.append({'patch':label,'cells':cells});print('GAPS',label,'CELLS',len(cells),'RANGE',min(x['minimum_gap_mm'] for x in rows),max(x['maximum_gap_mm'] for x in rows),'COMPATIBLE',sum(x['resolved_contact_compatible_on_audited_domain'] for x in rows),flush=True)
import gzip
(OUT/'common-cell-results.json.gz').write_bytes(gzip.compress(json.dumps(all_cells,allow_nan=False).encode(),mtime=0))
for p,h in inputs.items():assert sha(p)==h
report={'input_sha256':inputs,'auditor_source_sha256':sha(__file__),'quadratic_core_sha256':sha(ROOT/'integration/contact_patch_audit.py'),'base_main':'5cfa8a86cf7648ac0add84898eeeb5b365440016','cases':cases,'contact_patches':summaries,'coupled_field_gauge_and_force_moment_work_audit_passed':True,'polynomial_piecewise_gap_reconstruction_complete':True,'local_nonpenetration_all_cases':all(x['nonpenetration_satisfied'] for p in summaries for x in p['results']),'resolved_contact_all_cases':all(x['resolved_contact_compatible_on_audited_domain'] for p in summaries for x in p['results']),'common_cell_file_sha256':sha(OUT/'common-cell-results.json.gz'),'fresh_stiffness_matrix_reassembly_done_here':False,'independent_fresh_K_audit_separate':True,'scope':'P2 fields on common planar mesh triangles inside declared reference footprints, linear geometry and small-sliding projection; not continuum interval certificate or full finite-rotation contact','same_previous_mesh_no_new_mesh_convergence_claim':True,'new_equilibrium_or_geometry_repair_performed':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
dump(OUT/'report.json',report);print('DONE',report['local_nonpenetration_all_cases'],report['resolved_contact_all_cases'],flush=True)
