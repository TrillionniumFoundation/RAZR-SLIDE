from pathlib import Path
import hashlib,ast
R=Path('/home/qian-qi/RAZR-SLIDE-consistent-load-20261017');p=R/'engineering/trace-enrichment-20261017/solve_trace_probe.py'
s=p.read_text();assert hashlib.sha256(p.read_bytes()).hexdigest()=='948837c9443394ab77f185bdbbb3c7d763130dcd1e9adf0db5fd9a16c9d2178b'
def replace(a,b):
 global s
 assert s.count(a)==1,(a[:80],s.count(a));s=s.replace(a,b)
replace("BASE='faee1e95e5e3b86baa9b21fe6a9d4a205aa5d752'","BASE='2886fa11421d675222df443251be43145f322bbf'")
replace("    oldforce=np.asarray(seed['forces']);bodies={};selection=[]",'''    surface=None;load_mode=getattr(a,'surface_load_mode','discrete')
    if getattr(a,'surface_loads',None) is not None:
        sys.path.insert(0,str(ROOT/'engineering/consistent-load-20261017'))
        from surface_archive import SurfaceArchive
        surface=SurfaceArchive(a.surface_loads);hashes.update(surface.hashes)
    elif load_mode!='discrete':raise ValueError('consistent loading requires a verified surface archive')
    oldforce=np.asarray(seed['forces']);bodies={};selection=[]''')
replace("        chosen.sort(key=lambda x:(x['patch'],x['vertices']));lookup={tuple(x['vertices']):i for i,x in enumerate(chosen)}",'''        if surface is not None:chosen=surface.extend_selection(name,chosen,a.load_face_cap)
        chosen.sort(key=lambda x:(x['patch'],x['vertices']));lookup={tuple(x['vertices']):i for i,x in enumerate(chosen)}''')
replace("        bodies[name]={'K':K,'A':A,'B':B,'Z':Z,'sf':sf,'data':data,'free':free,'D':D,'factor':factor,",'''        if surface is None:
            lc=data['C'][:,:4].copy();lf=data['F'].copy();lcb=np.zeros((nb,4));lfb=np.zeros((nb,lf.shape[1]))
        else:lc,lcb,lf,lfb=surface.vectors(name,chosen,data,load_mode)
        np.savez_compressed(bodyout/'effective-loads.npz',C=lc,Cb=lcb,F=lf,Fb=lfb)
        bodies[name]={'K':K,'A':A,'B':B,'Z':Z,'sf':sf,'data':data,'free':free,'D':D,'factor':factor,
            'C':lc,'Cb':lcb,'F':lf,'Fb':lfb,''')
replace("            c0=np.r_[P['data']['C'][:,idx],np.zeros(P['nb']),F['data']['C'][:,idx],np.zeros(F['nb'])]","            c0=np.r_[P['C'][:,idx],P['Cb'][:,idx],F['C'][:,idx],F['Cb'][:,idx]]")
replace("    check0=original.restore(oldC,oldH,original.identity,probes=5);print('BASE_RESPONSE_VERIFIED',check0,flush=True)\n    H=oldH.copy()",'''    referenceC=oldC.tolil(copy=True)
    referenceC[:,:4]=csc_matrix(np.vstack([P['data']['C'][:,:4],F['data']['C'][:,:4]]))
    referenceC=referenceC.tocsc()
    check0=original.restore(referenceC,oldH,original.identity,probes=5);print('BASE_RESPONSE_VERIFIED',check0,flush=True)
    H=oldH.copy()
    # Only four base force functionals changed. Recompute their COMPLETE
    # operator columns; old contact/contact entries still have the same K/maps.
    if surface is not None and load_mode=='consistent':
        responses=base_response(oldC[:,:4].toarray(order='F'))
        columns=np.asarray(oldC.T@responses);H[:,:4]=columns;H[:4,:]=columns.T
        H[:4,:4]=(H[:4,:4]+H[:4,:4].T)/2''')
replace("    external=np.r_[P['data']['F'][:,2]*1e-5,np.zeros(P['nb']+nF)]","    external=np.r_[P['F'][:,2]*1e-5,P['Fb'][:,2]*1e-5,np.zeros(nF)]")
replace("    loadG=P['data']['R'].T@P['data']['F'][:,2]*1e-5","    loadG=R.T@external")
replace("        'not_full_P3_or_all_interface_refinement':True,'old_discrete_nodal_load_functionals_preserved':True,'continuous_load_projection_not_claimed':True,",'''        'not_full_P3_or_all_interface_refinement':True,'old_discrete_nodal_load_functionals_preserved':load_mode=='discrete',
        'continuous_load_projection_not_claimed':load_mode=='discrete',
        'surface_load_archive':str(surface.root) if surface is not None else None,'surface_load_mode':load_mode,
        'load_face_cap':getattr(a,'load_face_cap',0),'surface_integration_scope':'declared planar polygon and affine research density; not actual measured traction',
        'load_map_change_not_mesh_convergence':surface is not None,''')
replace("    a=p.parse_args();assert 1<=a.faces_per_patch<=4 and a.max_exchanges>0 and a.max_points>=4000",'''    p.add_argument('--surface-loads',type=Path);p.add_argument('--surface-load-mode',choices=('discrete','consistent'),default='discrete');p.add_argument('--load-face-cap',type=int,default=0)
    a=p.parse_args();assert 1<=a.faces_per_patch<=4 and a.max_exchanges>0 and a.max_points>=4000 and 0<=a.load_face_cap<=4''')
ast.parse(s);p.write_text(s)
print('PATCHED_PROBE',hashlib.sha256(p.read_bytes()).hexdigest())
