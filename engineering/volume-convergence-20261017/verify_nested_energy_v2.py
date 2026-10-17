"""Independent nested-field energy differences, not continuum error estimates."""
from pathlib import Path
import numpy as np,json,sys,time
R=Path('/home/qian-qi/RAZR-SLIDE-volume-convergence-20261017');O=Path('/tmp/razr-volume-convergence-20261017')
sys.path[:0]=[str(R/'integration'),str(R/'engineering/volume-convergence-20261017')]
from tetra_bubble_refinement import REF,prolong_p2,CHILDREN,CHILD_VECTOR_MAPS
from frozen_load_response import strain_energy
from contact_exchange import sha256
T=prolong_p2(REF[None])[0];rows=[];inputs={}
for body in ('panel','frame'):
 path=O/'volume-v3'/body/'mapping.npz';mapping=np.load(path,allow_pickle=False);vertices=mapping['vertices'];ids=mapping['element_dofs'];inputs[str(path)]=sha256(path)
 for case in (4,5,6,7):
  paths=[R/'engineering/preload-closure-20261017'/f'case-{case}/full-fields.npz']+[O/f'frozen-v2-{body}-L{k}'/f'case-{case}.npz' for k in (1,2)]
  a,b,c=[np.load(p,allow_pickle=False) for p in paths]
  # Load compressed arrays once per field, not once per element chunk.
  bi=b['internal'];ci_full=c['internal']
  print('NESTED_START',body,case,flush=True)
  for p in paths:inputs[str(p)]=sha256(p)
  u0=a['up' if body=='panel' else 'uf'];u1=b['u'];u2=c['u'];f=b['load'];assert np.array_equal(f,c['load']) and np.array_equal(f,a['load_'+body])
  norm01=0.;norm12=0.
  for lo in range(0,len(ids),256):
   hi=min(lo+256,len(ids));v=vertices[lo:hi];ix=ids[lo:hi]
   star=np.concatenate((v,v.mean(axis=1)[:,None]),axis=1)
   one=np.concatenate((u1[ix],bi[lo:hi]),axis=1)
   two=np.concatenate((u2[ix],ci_full[lo:hi,:15]),axis=1)
   coarse=u0[ix]@T.T;diff=one-coarse
   for index,(child,ci) in enumerate(zip(CHILDREN,CHILD_VECTOR_MAPS)):
    vc=star[:,child];norm01+=float(strain_energy(vc,diff[:,ci]).sum())
    actual2=np.concatenate((two[:,ci],ci_full[lo:hi,15+15*index:30+15*index]),axis=1)
    diff2=actual2-one[:,ci]@T.T;ss=np.concatenate((vc,vc.mean(axis=1)[:,None]),axis=1)
    for cc,jj in zip(CHILDREN,CHILD_VECTOR_MAPS):norm12+=float(strain_energy(ss[:,cc],diff2[:,jj]).sum())
  j0,j1,j2=[float(f@u) for u in (u0,u1,u2)];d01=j1-j0;d12=j2-j1
  e01=abs(norm01-d01)/max(abs(d01),1e-20);e12=abs(norm12-d12)/max(abs(d12),1e-20)
  assert d01>0 and d12>0 and max(e01,e12)<2e-4
  row={'body':body,'case':case,'integrated_difference_energy_L01':norm01,'integrated_difference_energy_L12':norm12,
       'work_difference_L01':d01,'work_difference_L12':d12,'relative_identity_error_L01':e01,'relative_identity_error_L12':e12,
       'relative_energy_norm_increment_L01':float(np.sqrt(norm01/j1)),'relative_energy_norm_increment_L12':float(np.sqrt(norm12/j2)),
       'same_frozen_traction_only':True,'not_continuum_error_bound':True,'not_new_contact_solution':True}
  rows.append(row);print('NESTED_ENERGY',body,case,e01,e12,row['relative_energy_norm_increment_L12'],flush=True)
assert all(sha256(Path(p))==h for p,h in inputs.items())
(O/'nested-energy-checks.json').write_text(json.dumps({'passed':True,'rows':rows,'input_sha256':inputs,'source_sha256':sha256(__file__),'rigid_motion_not_counted_as_strain_error':True,'mesh_convergence_certified':False},indent=2)+'\n')
