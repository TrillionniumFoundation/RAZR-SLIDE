"""Audit completed ring-boundary field checkpoints after report serialization failed.

This does NOT turn the original process exit1 into exit0 or assert the other
boundary was solved. Only the actually saved complete displacement/force/
reaction checkpoint is postprocessed, with its original source and log bound.
"""
from pathlib import Path
import hashlib,json
import numpy as np
O=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def recover(folder,mesh_folder,producer):
    source=O/folder/'four_bearing_rings_ideal_clamp.npz';z=np.load(source,allow_pickle=False)
    xyz=z['dof_xyz'];U=z['displacements'];F=z['forces'];R=z['reactions'];D=z['constrained_dofs'];axes=[z[f'axis{i}'] for i in range(3)]
    assert U.shape==F.shape==R.shape and U.shape[1]==4 and xyz.shape==(3,U.shape[0])
    assert all(np.isfinite(a).all() for a in (xyz,U,F,R))
    free=np.setdiff1d(np.arange(U.shape[0]),D);residual=float(np.max(np.abs(R[free])))
    C=F.T@U;energy=np.sum(U*(R+F),axis=0)/2;recip=float(np.max(np.abs(C-C.T))/np.max(np.abs(C)));eigs=np.linalg.eigvalsh(C)
    labels=['L_front','L_rear','R_front','R_rear'];loads=[]
    for j,label in enumerate(labels):
        force=np.array([F[i,j].sum() for i in axes]);reaction=np.array([R[i,j].sum() for i in axes]);fvec=np.zeros((U.shape[0],3));rvec=np.zeros_like(fvec)
        for d,i in enumerate(axes):fvec[i,d]=F[i,j];rvec[i,d]=R[i,j]
        moment=np.cross(xyz.T,fvec).sum(axis=0);reaction_moment=np.cross(xyz.T,rvec).sum(axis=0)
        fb=float(np.linalg.norm(force+reaction));mb=float(np.linalg.norm(moment+reaction_moment));workerr=float(abs(C[j,j]-2*energy[j])/abs(C[j,j]))
        assert np.linalg.norm(force-[(-1 if label[0]=='L' else 1),0,0])<1e-10
        assert fb<1e-5 and mb<1e-3 and workerr<1e-6
        loads.append({'label':label,'E_delta_over_F_per_mm':float(C[j,j]),'applied_resultant_N':force.tolist(),'applied_moment_Nmm':moment.tolist(),'reaction_N':reaction.tolist(),'reaction_moment_Nmm':reaction_moment.tolist(),'force_balance_norm_N':fb,'moment_balance_norm_Nmm':mb,'work_energy_relative_error':workerr})
    assert residual<1e-6 and recip<1e-6 and eigs.min()>0
    m=json.loads((O/mesh_folder/'mesh-report.json').read_text());mesh=O/mesh_folder/'mesh.npz';q=np.load(mesh,allow_pickle=False);pts=q['points'];tet=q['tetra'];J=np.stack([pts[tet[:,i]]-pts[tet[:,0]] for i in (1,2,3)],axis=2);det=np.linalg.det(J)
    assert np.min(np.abs(det))>1e-16 and np.isfinite(det).all()
    assert abs(abs(det).sum()/6-m['mesh_volume_mm3'])<1e-7 and m['mesh_sha256']==sha(mesh)
    report={'checkpoint':str(source),'checkpoint_sha256':sha(source),'original_solver_exit':int((O/(folder+'.exit')).read_text()),'original_log_sha256':sha(O/(folder+'.log')),'producer_source_sha256':sha(O/producer),'mesh':m,'mesh_path':str(mesh),'DOFs':int(U.shape[0]),'boundary':'four mounting bearing rings with all displacement components ideally fixed','only_this_completed_boundary_recovered':True,'other_requested_boundary_not_completed':True,'normalized_E_N_per_mm2':1.,'synthetic_nu':.3,'quadratic_displacements_linear_geometric_tets':True,'free_residual_max_N':residual,'reciprocity_relative_error':recip,'response_eigenvalues':eigs.tolist(),'response_matrix_E_scaled_per_mm':C.tolist(),'loads':loads,'min_abs_element_jacobian_mm3':float(np.min(np.abs(det))),'negative_orientation_elements':int((det<0).sum()),'no_nonpositive_element_volume':True,'passed_checkpoint_audit':True,'manufacturing_go':False}
    (O/(folder+'-recovered.json')).write_text(json.dumps(report,indent=2)+'\n');print('RECOVERED',folder,[x['E_delta_over_F_per_mm'] for x in loads],flush=True);return report


if __name__=='__main__':
    coarse=recover('solve3p2-fixed','mesh3web','field_producer_used.py');fine=recover('solve2p2-fixed','mesh2web','field_producer_used.py');other=recover('solve3p2','mesh3web','rejected-memory-solver.py')
    c=np.diag(coarse['response_matrix_E_scaled_per_mm']);f=np.diag(fine['response_matrix_E_scaled_per_mm']);a=np.diag(other['response_matrix_E_scaled_per_mm']);change=np.abs(c-f)/np.abs(f);ordering=np.max(np.abs(c-a)/np.abs(c))
    assert ordering<1e-7
    result={'coarse_fields':coarse['checkpoint_sha256'],'fine_fields':fine['checkpoint_sha256'],'same_mesh_independent_ordering_relative_difference':float(ordering),'two_mesh_diagonal_relative_difference':change.tolist(),'declared_mean_response_mesh_agreement_target':.05,'meets_target':bool(np.all(change<=.05)),'not_certified_global_FE_error_or_stress_convergence':True,'all_original_process_exit_codes_retained':True}
    (O/'ring-field-comparison.json').write_text(json.dumps(result,indent=2)+'\n');print('COMPARISON',json.dumps(result),flush=True)
