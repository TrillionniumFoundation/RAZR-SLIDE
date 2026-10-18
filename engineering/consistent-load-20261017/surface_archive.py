"""Hash-bound surface functionals for the existing selected-trace experiment."""
from pathlib import Path
import hashlib,json
import numpy as np

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
class SurfaceArchive:
    def __init__(self,path):
        self.root=Path(path).resolve();p=self.root/'manifest.json';self.manifest=json.loads(p.read_text());self.hashes={str(p):sha(p)}
        self.data={};self.faces={}
        for filename,want in self.manifest['files_sha256'].items():
            rel=Path(filename)
            if len(rel.parts)!=1 or rel.is_absolute():raise ValueError('unsafe archive member')
            f=self.root/rel
            if f.is_symlink() or sha(f)!=want:raise ValueError('surface archive changed')
            self.hashes[str(f)]=want
        for name in ('panel','frame'):
            with np.load(self.root/(name+'.npz'),allow_pickle=False) as z:self.data[name]={k:z[k] for k in ('C','F')}
            self.faces[name]=json.loads((self.root/(name+'-faces.json')).read_text())
            for x in self.faces[name]:
                if x['body']!=name or len(set(x['vertices']))!=3 or x['kind'] not in ('C','F') or type(x['index']) is not int or not 0<=x['index']<4:
                    raise ValueError('invalid force face identity')
        if not self.manifest['original_nodal_vectors_reproduced']:raise ValueError('unverified source force identity')

    def extend_selection(self,name,chosen,cap):
        if type(cap) is not int or not 0<=cap<=4:raise ValueError('0..4 added load faces per patch required')
        groups={};existing={tuple(x['vertices']) for x in chosen};out=list(chosen)
        for row in self.faces[name]:groups.setdefault(row['patch'],[]).append(row)
        for label,rows in sorted(groups.items()):
            ranked=sorted(rows,key=lambda x:(-abs(x['work_coefficients'][6]),tuple(sorted(x['vertices']))))
            for row in ranked[:cap]:
                key=tuple(sorted(row['vertices']))
                if key in existing:continue
                out.append({'body':name,'patch':'force_support:'+label,'vertices':list(key),
                    'prior_resultant':row['resultant_scalar'],'selection_criterion':'absolute consistent cubic work before solve'})
                existing.add(key)
        return out

    def vectors(self,name,chosen,original,mode):
        if mode not in ('discrete','consistent'):raise ValueError('explicit load mode required')
        n=len(original['C']);nb=3*len(chosen);nf=original['F'].shape[1]
        C=original['C'][:,:4].copy() if mode=='discrete' else self.data[name]['C'].copy()
        F=original['F'].copy() if mode=='discrete' else self.data[name]['F'].copy()
        if C.shape!=(n,4) or F.shape!=(n,nf) or not np.isfinite(C).all() or not np.isfinite(F).all():raise ValueError('surface load dimension or values differ')
        Cb=np.zeros((nb,4));Fb=np.zeros((nb,nf));lookup={tuple(x['vertices']):i for i,x in enumerate(chosen)}
        if mode=='consistent':
            for row in self.faces[name]:
                fi=lookup.get(tuple(sorted(row['vertices'])))
                if fi is not None:
                    v=np.asarray(row['bubble_load'],dtype=float)
                    if v.shape!=(3,) or not np.isfinite(v).all():raise ValueError('nonfinite face functional')
                    (Cb if row['kind']=='C' else Fb)[3*fi:3*fi+3,row['index']]+=v
        return C,Cb,F,Fb
