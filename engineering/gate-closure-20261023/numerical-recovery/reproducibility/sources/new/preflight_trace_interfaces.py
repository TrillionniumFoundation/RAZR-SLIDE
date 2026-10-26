"""Bounded original-data selected-trace interface preflight, without skfem.

This explicit standalone diagnostic builds only original selected-face local
energy/coupling blocks. It uses saved original mesh identities and the audited
new L2 global DOF map. It does not impersonate skfem, factor a global K, compute
a trace Schur inverse, run a contact QP, or qualify the current EP5 product.
"""
from pathlib import Path
import argparse
import gc
import importlib.util
import json
import resource
import sys
import time
import numpy as np
from scipy.sparse import coo_matrix, save_npz

BASE=Path(__file__).resolve().parent
ROOT=Path('/workspace/scratch/95cd2986fdf2/RAZR-SLIDE')
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'integration'))
sys.path.insert(0,str(ROOT/'engineering/consistent-load-20261017'))
from face_trace_space import trace_condense, FACES
from tetra_bubble_refinement import star_condense, p2_nodes
from surface_archive import SurfaceArchive, frozen_trace_selection
from installation_control import binding_digest, read_control
from rebuild_l2_only import sha, save_json, free_bytes


def main(args):
    start=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
    output=args.output.resolve()
    assert output!=ROOT and ROOT not in output.parents
    output.mkdir(parents=True,exist_ok=False)
    assert free_bytes(output)>500*1024**2
    frozen_path=ROOT/'engineering/joint-sensitivity-20261017/frozen-selection.json'
    surface_path=ROOT/'engineering/consistent-load-20261017/projection-512'
    control_path=ROOT/'engineering/installation-control-20261018/force-target-plan.json'
    frozen=json.loads(frozen_path.read_text())
    surface=SurfaceArchive(surface_path)
    hashes={str(frozen_path):sha(frozen_path),str(control_path):sha(control_path),**surface.hashes}
    sources={str(p):sha(p) for p in [Path(__file__),ROOT/'integration/face_trace_space.py',
              ROOT/'integration/tetra_bubble_refinement.py',ROOT/'integration/installation_control.py',
              ROOT/'engineering/consistent-load-20261017/surface_archive.py',
              ROOT/'engineering/bearing-continuation-20261022/reference/solve_trace_probe.py']}
    records=[];selection=[];body_inputs={}
    for body in ('panel','frame'):
        folder=args.volume/body/'level-2'
        report=json.loads((folder/'report.json').read_text())
        mapping=folder.parent/'mapping.npz'
        for name,key in [('mesh.npz','mesh_sha256'),('loads.npz','loads_sha256')]:
            path=folder/name;assert sha(path)==report[key];hashes[str(path)]=report[key]
        assert sha(mapping)==report['mapping_sha256']
        hashes[str(mapping)]=sha(mapping)
        hashes[str(folder/'report.json')]=sha(folder/'report.json')
        # Bind K identity without loading its large sparse arrays into memory.
        assert sha(folder/'K.npz')==report['K_sha256']
        hashes[str(folder/'K.npz')]=report['K_sha256']
        body_inputs[body]={name:report[key] for name,key in
                          [('K.npz','K_sha256'),('mesh.npz','mesh_sha256'),('loads.npz','loads_sha256')]}
        with np.load(folder/'mesh.npz',allow_pickle=False) as data:
            vertices=data['points'];tetra=data['tetra']
        with np.load(folder/'loads.npz',allow_pickle=False) as data:
            loads={name:data[name] for name in ('D','xyz','C','F')}
        with np.load(mapping,allow_pickle=False) as data:
            ids=data['element_dofs'];mapped_vertices=data['vertices']
        assert np.array_equal(mapped_vertices,vertices[tetra])
        chosen=frozen_trace_selection(frozen,body,report['mesh_sha256'])
        affected={};parent_checks=[]
        for i,desc in enumerate(chosen):
            key=desc['vertices']
            match=np.ones(len(tetra),dtype=bool)
            for vertex in key:match &= np.any(tetra==vertex,axis=1)
            adjacent=np.flatnonzero(match)
            assert len(adjacent)==1,'frozen selected face must be exterior'
            ti=int(adjacent[0]);tet=tetra[ti]
            local=next(f for f,ix in enumerate(FACES) if set(tet[list(ix)])==set(key))
            assert ti==desc['tet'] and local==desc['local_face']
            assert desc['coefficient_indices']==[3*i,3*i+1,3*i+2]
            face=vertices[key]
            area=float(np.linalg.norm(np.cross(face[1]-face[0],face[2]-face[0]))/2)
            assert abs(area-desc['area_mm2'])<1e-13
            expected=p2_nodes(vertices[tet][None])[0]
            mapped=loads['xyz'][:,ids[ti].reshape(10,3)[:,0]].T
            assert np.max(abs(expected-mapped))<1e-11
            affected.setdefault(ti,[]).append((local,i))
            parent_checks.append({'tet':ti,'local_face':local,'global_face_coefficient':i})
        n=loads['xyz'].shape[1];nb=3*len(chosen)
        rows=[];columns=[];values=[];B=np.zeros((nb,nb))
        old_absolute=0.;old_relative=0.;symmetry=0.;local_blocks=[]
        for ti,roles in sorted(affected.items()):
            geometry=vertices[tetra[ti]][None]
            enriched=trace_condense(geometry,E=1.,nu=.3,level=2).stiffness[0]
            original=star_condense(geometry,E=1.,nu=.3,level=2).stiffness[0]
            difference=float(np.max(abs(enriched[:30,:30]-original)))
            old_absolute=max(old_absolute,difference)
            old_relative=max(old_relative,difference/max(float(np.max(abs(original))),1e-300))
            symmetry=max(symmetry,float(np.max(abs(enriched-enriched.T))))
            localidx=np.array([30+3*f+j for f,_ in roles for j in range(3)])
            globalidx=np.array([3*i+j for _,i in roles for j in range(3)])
            rows.extend(np.repeat(ids[ti],len(globalidx)))
            columns.extend(np.tile(globalidx,30))
            values.extend(enriched[:30,localidx].ravel())
            B[np.ix_(globalidx,globalidx)]+=enriched[np.ix_(localidx,localidx)]
            local_blocks.append(enriched)
        assert old_relative<1e-10
        A=coo_matrix((values,(rows,columns)),shape=(n,nb)).tocsc()
        A.sum_duplicates();A.eliminate_zeros();A.sort_indices()
        held_cross=float(np.max(abs(A[loads['D']].data),initial=0.))
        assert held_cross<1e-11
        C,Cb,F,Fb=surface.vectors(body,chosen,loads,'consistent')
        directory=output/body;directory.mkdir()
        save_npz(directory/'coupling.npz',A)
        np.savez_compressed(directory/'local-blocks.npz',B=B,
                            selected_tetrahedra=np.array(sorted(affected)),
                            local_stiffness=np.stack(local_blocks))
        save_json(directory/'selection.json',chosen)
        # Keep only small trace load vectors; the complete original nodal
        # vectors are already immutable in the verified surface archive.
        np.savez_compressed(directory/'trace-loads.npz',Cb=Cb,Fb=Fb)
        record={'body':body,'original_vector_dofs':n,'selected_exterior_faces':len(chosen),
                'affected_parent_tetrahedra':len(affected),'new_trace_dofs':nb,
                'selected_parent_and_local_faces_match_original_record':True,
                'ordered_trace_indices_match_original_record':True,
                'original_global_DOF_coordinate_map_verified':True,
                'old_energy_block_absolute_error_max':old_absolute,
                'old_energy_block_relative_error_max':old_relative,
                'local_enriched_energy_symmetry_error_max':symmetry,
                'trace_interaction_with_original_fixed_coordinates_max':held_cross,
                'coupling_nnz':int(A.nnz),'full_Z_float64_bytes':n*nb*8,
                'consistent_C_shape':list(C.shape),'consistent_F_shape':list(F.shape),
                'trace_C_shape':list(Cb.shape),'trace_F_shape':list(Fb.shape),
                'trace_C_nonzero':int(np.count_nonzero(Cb)),
                'trace_F_nonzero':int(np.count_nonzero(Fb)),
                'new_files_sha256':{p.name:sha(p) for p in directory.iterdir()}}
        records.append(record);selection.extend(chosen)
        print(json.dumps(record),flush=True)
        del loads,ids,mapped_vertices,A,B,C,Cb,F,Fb,local_blocks
        gc.collect()
    cf=ROOT/'engineering/contact-field-20261015/common-cell-results.json.gz'
    mf=ROOT/'engineering/contact-field-20261015/coupled-field-audit.json.gz'
    payload={'bodies':body_inputs,'selection':selection,'common_regions':sha(cf),
             'contact_patches':sha(mf),'surface_mode':'consistent',
             'surface_manifest':sha(surface_path/'manifest.json')}
    identity=binding_digest(payload)
    control,control_hashes=read_control(control_path,model_identity=identity,external_scale=0.)
    hashes.update(control_hashes)
    assert control['mode']=='force_targets'
    for name,digest in {**hashes,**sources}.items():assert sha(name)==digest
    result={'schema':'razr-original-trace-interface-preflight-v1','completed':True,
            'explicit_new_diagnostic_no_skfem_impersonation':True,
            'locked_skfem_installed':importlib.util.find_spec('skfem') is not None,
            'original_selected_trace_interfaces_rebuilt':records,
            'new_model_identity':identity,'new_model_payload':payload,
            'force_control':{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in control.items()},
            'external_load_scale_over_Epanel_mm2':0.,'material_E_normalization':1.,'material_nu':.3,
            'input_sha256':hashes,'source_sha256':sources,
            'seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'global_K_factorization_executed':False,'trace_Schur_inverse_computed':False,
            'bearing_checkpoint_created':False,'new_QP_executed':False,
            'whole_contact_or_mesh_convergence_qualified':False,
            'physical_or_current_EP5_structural_qualification':False,
            'remaining_steps':['Complete both full base-H responses and original five inverse probes.',
                'For unchanged original driver: provide reviewed locked skfem dependency and memory for both LU factors plus trace Z.',
                'For bounded new adapter: explicitly review this DOF/topology path, then compute each body Z/Schur and independent full probes sequentially.',
                'Only after full updated operators are verified may original bearing continuation create an actual finite-QP/restart result.']}
    save_json(output/'report.json',result)
    print(json.dumps({'completed':True,'report':str(output/'report.json'),
                      'report_sha256':sha(output/'report.json'),'seconds':result['seconds'],
                      'peak_rss_kib':result['peak_rss_kib']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--volume',type=Path,default=Path('/tmp/razr-fe-20261023/volume-rebuild'))
    parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args())
