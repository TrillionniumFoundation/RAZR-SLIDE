from pathlib import Path
import ast
R=Path('/home/qian-qi/RAZR-SLIDE-consistent-load-20261017');O=Path('/tmp/razr-consistent-load-20261017')
s=(R/'engineering/trace-enrichment-20261017/verify_trace_field.py').read_text()
def rep(old,new):
 global s
 assert s.count(old)==1,(old[:100],s.count(old));s=s.replace(old,new)
rep("R=Path('/home/qian-qi/RAZR-SLIDE-trace-enrichment-20261017')","R=Path('/home/qian-qi/RAZR-SLIDE-consistent-load-20261017')")
rep("a=p.parse_args()","p.add_argument('--force-check',type=Path,required=True);a=p.parse_args()")
rep("model['panel']['expected'][:len(x['up'])]+=model['panel']['loads']['F'][:,2]*1e-5",'''fr=json.loads((a.force_check/'report.json').read_text());assert fr['passed'] and fr['candidate_integration_not_imported']
inputhash[str(a.force_check/'report.json')]=sha(a.force_check/'report.json')
for file,h in fr['input_sha256'].items():assert sha(file)==h;inputhash[file]=h
for file,h in fr['files_sha256'].items():assert sha(a.force_check/file)==h;inputhash[str(a.force_check/file)]=h
for name,m in model.items():
    C=m['loads']['C'][:,:4].copy();F=m['loads']['F'].copy();Cb=np.zeros((len(m['b']),4));Fb=np.zeros((len(m['b']),F.shape[1]))
    if r['surface_load_mode']=='consistent':
        z=np.load(a.force_check/(name+'.npz'),allow_pickle=False);C=z['C'];F=z['F']
        for rec in json.loads((a.force_check/(name+'-bubble-loads.json')).read_text()):
            fi=m['lookup'].get(tuple(sorted(rec['vertices'])))
            if fi is not None:(Cb if rec['kind']=='C' else Fb)[3*fi:3*fi+3,rec['index']]+=np.asarray(rec['bubble_load'])
    elif r['surface_load_mode']!='discrete':raise ValueError('unknown load mode')
    m['effective_C']=C;m['effective_Cb']=Cb;m['effective_F']=F;m['effective_Fb']=Fb
    m['expected']=-np.r_[C,Cb]@x['forces'][:4]
model['panel']['expected']+=np.r_[model['panel']['effective_F'][:,2],model['panel']['effective_Fb'][:,2]]*1e-5''')
rep("qbolt=sum(m['loads']['C'].T@m['u'] for m in model.values());assert np.max(abs(x['forces'][:4]-2e-4-qbolt/5))<1e-10", "qbolt=sum(m['effective_C'].T@m['u']+m['effective_Cb'].T@m['b'] for m in model.values());assert np.max(abs(x['forces'][:4]-2e-4-qbolt/5))<1e-10")
rep("newenergy=sum(z['twice_strain_energy'] for z in checks.values());F=model['panel']['loads']['F'][:,2]\noldresponse=float(F@oldx['up']);newresponse=float(F@x['up'])", "newenergy=sum(z['twice_strain_energy'] for z in checks.values());F=model['panel']['effective_F'][:,2];Fb=model['panel']['effective_Fb'][:,2]\noldresponse=float(F@oldx['up']);newresponse=float(F@x['up']+Fb@x['bp'])")
rep("'frozen_discrete_nodal_loads_not_new_continuous_traction':True,", "'surface_load_mode':r['surface_load_mode'],'surface_projection_independently_rebuilt':True,\n    'load_weighted_response':newresponse,'twice_elastic_energy':newenergy,\n    'frozen_discrete_nodal_loads_not_new_continuous_traction':r['surface_load_mode']=='discrete',\n    'different_load_functionals_not_discretization_only_comparison':True,")
rep("'frozen_discrete_nodal_loads_not_new_continuous_traction':True,", "'frozen_discrete_nodal_loads_not_new_continuous_traction':r['surface_load_mode']=='discrete',") if "'frozen_discrete_nodal_loads_not_new_continuous_traction':True," in s else None
ast.parse(s);(O/'verify_consistent_field.py').write_text(s);print('INDEPENDENT_FIELD_SOURCE_READY')
