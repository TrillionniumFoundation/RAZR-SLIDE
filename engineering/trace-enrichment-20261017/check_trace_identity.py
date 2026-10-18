"""Bind the actual selected-face maps and parent DOFs to the frozen FE mesh."""
from pathlib import Path
import json,gzip,hashlib,sys
import numpy as np
from skfem import MeshTet,Basis,ElementTetP2,ElementVector
R=Path('/home/qian-qi/RAZR-SLIDE-trace-enrichment-20261017');O=Path('/tmp/razr-trace-enrichment-20261017');V=Path('/tmp/razr-volume-convergence-20261017/volume-v3')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
raw=json.loads(gzip.decompress((R/'engineering/contact-field-20261015/common-cell-results.json.gz').read_bytes()))
flat=[(g['patch'],c) for g in raw for c in g['cells']]
seedpath=R/'engineering/nested-contact-20261017/level-2/case-6/report.json.gz';seed=json.loads(gzip.decompress(seedpath.read_bytes()));h={str(seedpath):sha(seedpath)}
ref=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]]);edges=((0,1),(0,2),(0,3),(1,2),(1,3),(2,3));canonical=np.vstack((ref,[(ref[i]+ref[j])/2 for i,j in edges]));faces=tuple(tuple(j for j in range(4) if j!=i) for i in range(4))
rows=[];sets={}
for name in ('panel','frame'):
    mp=V/name/'level-2/mesh.npz';h[str(mp)]=sha(mp);d=np.load(mp,allow_pickle=False);mesh=MeshTet(d['points'].T,d['tetra'].T)
    bv=Basis(mesh,ElementVector(ElementTetP2()),intorder=2);refnodes=ElementTetP2().doflocs;perm=np.array([np.argmin(np.linalg.norm(refnodes-x,axis=1)) for x in canonical]);ids=bv.element_dofs[(3*perm[:,None]+np.arange(3)).ravel()].T
    facelookup={tuple(sorted(t)):i for i,t in enumerate(mesh.facets.T)}
    scores={g['patch']:{} for g in raw}
    for p,f in zip(seed['contact_points'][4:],seed['forces'][4:]):
        patch,c=flat[p['cell']];key=tuple(sorted(c[name+'_triangle']));scores[patch][key]=scores[patch].get(key,0.)+f
    for limit,label in [(2,'original-selected-v3'),(4,'original-selected64-v1')]:
        run=O/label;sp=run/name/'selection.json';rp=run/name/'local-records.json';reportpath=run/'report.json'
        for path in (sp,rp,reportpath):h[str(path)]=sha(path)
        chosen=json.loads(sp.read_text());expected=[]
        for patch in sorted(scores):
            for key in sorted(scores[patch],key=lambda key:(-scores[patch][key],key))[:limit]:expected.append((patch,key))
        expected.sort();actual=sorted((x['patch'],tuple(x['vertices'])) for x in chosen);assert actual==expected
        published=[x for x in json.loads(reportpath.read_text())['selected_faces'] if x['body']==name];assert chosen==published
        records=json.loads(rp.read_text());recordby={x['tet']:x for x in records};assert len(recordby)==len(records)
        visited=set()
        for i,x in enumerate(chosen):
            fi=facelookup[tuple(x['vertices'])];adj=mesh.f2t[:,fi];adj=adj[adj>=0];assert len(adj)==1
            ti=int(adj[0]);assert x['tet']==ti and set(mesh.t[list(faces[x['local_face']]),ti])==set(x['vertices'])
            assert x['coefficient_indices']==[3*i,3*i+1,3*i+2]
            assert [x['local_face'],i] in recordby[ti]['roles']
            np.testing.assert_array_equal(recordby[ti]['retained_dofs'],ids[ti])
            np.testing.assert_array_equal(recordby[ti]['vertices'],mesh.p.T[mesh.t[:,ti]])
            visited.add(ti)
        assert visited==set(recordby)
        sets[(name,limit)]={x[1] for x in actual}
        rows.append({'body':name,'per_patch_cap':limit,'actual_selected_faces':len(chosen),'actual_parent_tetrahedra':len(visited),'library_DOF_maps_equal':True,'ranking_recomputed_from_original_case6':True,'all_faces_exterior':True})
for name in ('panel','frame'):assert sets[(name,2)]<sets[(name,4)]
for path,value in h.items():assert sha(path)==value
result={'passed':True,'rows':rows,'input_sha256':h,'actual_nested_sets_checked':True,'does_not_change_source_or_fields':True,'source_sha256':sha(__file__)}
(O/'selection-and-DOF-identity.json').write_text(json.dumps(result,indent=2)+'\n');print('ACTUAL_TRACE_IDENTITY_PASSED',rows,flush=True)
