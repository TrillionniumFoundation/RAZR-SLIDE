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


def checked_study_controls(case=6, gap_tolerance=1e-7):
    """Explicit normalized historical case and a target no looser than baseline.

    This selects synthetic research inputs, never an installed preload or a
    service-load rating. A stricter target is not a mesh/continuum certificate.
    """
    if type(case) is not int or not 0 <= case <= 7:
        raise ValueError('integer historical case 0..7 required')
    if type(gap_tolerance) not in (int, float) or not np.isfinite(gap_tolerance) or not 0 < gap_tolerance <= 1e-7:
        raise ValueError('finite positive gap tolerance no looser than 1e-7mm required')
    return case, float(gap_tolerance), case % 4, 0. if case < 4 else 2e-4


def frozen_trace_selection(record, body, expected_mesh_sha256):
    """Reuse face identities, not old energies or contact solutions.

    The caller hashes the complete record and rechecks actual exterior-face,
    parent and DOF mappings against the current mesh before forming any K.
    """
    if body not in ('panel', 'frame') or not isinstance(record, dict) or record.get('schema') != 'razr-frozen-traces-v1':
        raise ValueError('invalid frozen trace selection schema or body')
    hashes = record.get('mesh_sha256')
    if not isinstance(hashes, dict) or set(hashes) != {'panel', 'frame'} or hashes.get(body) != expected_mesh_sha256:
        raise ValueError('frozen trace mesh identity differs')
    for value in [*hashes.values(), record.get('source_report_sha256'), record.get('source_selection_sha256')]:
        if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('invalid frozen trace source hash')
    entries = record.get('selected_faces')
    if not isinstance(entries, list) or not entries:
        raise ValueError('nonempty selected face list required')
    seen = set(); output = []
    for face in entries:
        if not isinstance(face, dict) or face.get('body') not in ('panel', 'frame'):
            raise ValueError('unknown body in selected face')
        vertices = face.get('vertices')
        if not isinstance(vertices, list) or len(vertices) != 3 or any(type(v) is not int or v < 0 for v in vertices) or len(set(vertices)) != 3:
            raise ValueError('three distinct nonnegative vertex identities required')
        if vertices != sorted(vertices) or not isinstance(face.get('patch'), str) or not face['patch']:
            raise ValueError('canonical face vertex order and patch identity required')
        identity = (face['body'], tuple(vertices))
        if identity in seen:
            raise ValueError('duplicate selected mesh face')
        seen.add(identity)
        if face['body'] == body:
            output.append(json.loads(json.dumps(face, allow_nan=False)))
    if not output:
        raise ValueError('requested body has no selected face')
    return sorted(output, key=lambda x: (x['patch'], x['vertices']))


def checked_external_load_scale(value=None):
    """Research load/Epanel amplitude; zero is an unloaded assembly reference.

    Does not convert the normalized problem to actual Newtons or set preload.
    Omitting this option preserves the historical 1e-5 value exactly.
    """
    if value is None:
        return 1e-5
    if type(value) not in (int, float) or not np.isfinite(value) or value < 0:
        raise ValueError('external normalized load scale must be nonnegative and finite')
    return float(value)
