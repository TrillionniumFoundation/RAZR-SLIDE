"""Force-controlled assembly followed by fixed installation adjustment.

Units: force/Epanel in mm^2, compliance Epanel/k in 1/mm, q and adjustment
in mm. Keeping adjustment fixed does NOT freeze the elastic bolt length or
keep its force constant. This is a prescribed pressure-weighted connector,
not resolved head/nut contact, a torque law, or physical qualification.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np

N_BOLTS = 4
SCHEMA = 'razr-installation-control-v1'

def vector(value, name, *, nonnegative=False, positive=False):
    if isinstance(value,(list,tuple)) and any(isinstance(v,(bool,np.bool_)) for v in value):
        raise ValueError(name+': boolean entries are not forces')
    x=np.asarray(value)
    if x.shape!=(N_BOLTS,) or x.dtype.kind not in 'fiu' or not np.isfinite(x).all():
        raise ValueError(name+': four finite real non-boolean entries required')
    x=x.astype(float,copy=True)
    if (nonnegative and (x<0).any()) or (positive and (x<=0).any()):
        raise ValueError(name+': invalid sign')
    return x

def binding_digest(payload):
    try:raw=json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    except (TypeError,ValueError) as exc:raise ValueError('finite JSON model identity required') from exc
    return hashlib.sha256(raw).hexdigest()

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def force_equalities(G, load, targets):
    """Add four actuator force equalities, not physical displacement supports."""
    G=np.asarray(G);load=np.asarray(load);t=vector(targets,'targets',nonnegative=True)
    if G.ndim!=2 or load.shape!=(G.shape[1],) or G.shape[0]<4:
        raise ValueError('incompatible physical equilibrium maps')
    if any(a.dtype.kind not in 'fiu' or not np.isfinite(a).all() for a in (G,load)):
        raise ValueError('finite real physical maps required')
    selector=np.zeros((G.shape[0],4));selector[:4]=np.eye(4)
    return np.column_stack((G,selector)), np.r_[load,t]

def split_coordinates(coordinates, physical_modes, *, force_control):
    x=np.asarray(coordinates)
    if type(physical_modes) is not int or physical_modes<0 or type(force_control) is not bool:
        raise ValueError('invalid coordinate mode count')
    if x.shape!=(physical_modes+(4 if force_control else 0),) or x.dtype.kind not in 'fiu' or not np.isfinite(x).all():
        raise ValueError('coordinate dimension differs')
    # Actuator multipliers are installation adjustments, never rigid support motion.
    return x[:physical_modes].copy(),x[physical_modes:].copy()

def adjustment_from_state(force, separation, compliance):
    f=vector(force,'force',nonnegative=True);q=vector(separation,'separation');c=vector(compliance,'compliance',positive=True)
    return c*f-q

def locked_force(separation, compliance, adjustment):
    return (vector(separation,'separation')+vector(adjustment,'adjustment'))/vector(compliance,'compliance',positive=True)

def decode_control(document, *, model_identity, external_scale):
    if not isinstance(document,dict) or document.get('schema')!=SCHEMA:
        raise ValueError('unsupported installation-control schema')
    if document.get('bolt_ids')!=['bolt0','bolt1','bolt2','bolt3']:
        raise ValueError('exact ordered bolt identities required')
    if document.get('units')!='force/Epanel:mm2;Epanel/k:1/mm;adjustment:mm':
        raise ValueError('explicit normalized units required')
    if document.get('physical_measurement') is not False:
        raise ValueError('this research control is not an installed-preload measurement')
    if type(external_scale) not in (int,float) or not np.isfinite(external_scale):
        raise ValueError('finite external scale required')
    c=vector(document.get('compliance_Epanel_over_k_per_mm'),'compliance',positive=True)
    mode=document.get('mode')
    if mode=='force_targets':
        if external_scale!=0:raise ValueError('assembly force control requires zero external service load')
        return {'mode':mode,'compliance':c,'targets':vector(document.get('target_force_over_Epanel_mm2'),'target',nonnegative=True),'adjustment':np.zeros(4)}
    if mode!='locked_adjustment':raise ValueError('unknown installation control mode')
    if document.get('model_identity')!=model_identity:raise ValueError('locked state belongs to different energy/load/support/trace maps')
    force=vector(document.get('assembly_force_over_Epanel_mm2'),'assembly_force',nonnegative=True)
    q=vector(document.get('assembly_separation_mm'),'assembly_separation')
    delta=vector(document.get('adjustment_mm'),'adjustment')
    if not np.array_equal(delta,adjustment_from_state(force,q,c)):
        raise ValueError('altered adjustment or assembly state')
    return {'mode':mode,'compliance':c,'targets':None,'adjustment':delta}

def read_control(path, *, model_identity, external_scale):
    p=Path(path).resolve();doc=json.loads(p.read_text());hashes={str(p):sha256(p)}
    control=decode_control(doc,model_identity=model_identity,external_scale=external_scale)
    if control['mode']=='locked_adjustment':
        sources=doc.get('source_files',{})
        if set(sources)!={'solver_report','field','independent_report'}:
            raise ValueError('locked adjustment lacks verified installation sources')
        sourcepaths={}
        for label,rec in sources.items():
            q=Path(rec['path']).resolve()
            if sha256(q)!=rec['sha256']:raise ValueError('installation evidence bytes changed')
            hashes[str(q)]=rec['sha256'];sourcepaths[label]=q
        report=json.loads(sourcepaths['solver_report'].read_text());audit=json.loads(sourcepaths['independent_report'].read_text())
        if report.get('passed') is not True or audit.get('passed') is not True:
            raise ValueError('installation source is not independently passed')
        state=report['installation_control']
        if state['mode']!='force_targets' or state['model_identity']!=model_identity or report['external_load_scale_over_Epanel_mm2']!=0:
            raise ValueError('source is not same-model unloaded force installation')
        for key in ['assembly_force_over_Epanel_mm2','assembly_separation_mm','compliance_Epanel_over_k_per_mm','adjustment_mm']:
            if state[key]!=doc[key]:raise ValueError('locked state differs from verified installation')
        for label in ['solver_report','field']:
            sp=sourcepaths[label]
            if audit.get('input_sha256',{}).get(str(sp))!=sha256(sp):
                raise ValueError('independent audit not bound to installation field')
    return control,hashes

def seal_locked_state(run_directory, independent_report, output):
    root=Path(run_directory).resolve();auditpath=Path(independent_report).resolve();out=Path(output)
    reportpath=root/'report.json';fieldpath=root/'full-fields.npz'
    report=json.loads(reportpath.read_text());audit=json.loads(auditpath.read_text())
    if report.get('passed') is not True or audit.get('passed') is not True:
        raise ValueError('solver and independent audit must both pass')
    state=report['installation_control']
    if state['mode']!='force_targets' or report['external_load_scale_over_Epanel_mm2']!=0:
        raise ValueError('only unloaded force installation can create fixed adjustment')
    for p in (reportpath,fieldpath):
        if audit.get('input_sha256',{}).get(str(p))!=sha256(p):raise ValueError('audit field identity mismatch')
    payload={'schema':SCHEMA,'mode':'locked_adjustment','bolt_ids':['bolt0','bolt1','bolt2','bolt3'],
        'units':'force/Epanel:mm2;Epanel/k:1/mm;adjustment:mm','physical_measurement':False,
        'model_identity':state['model_identity'],
        **{k:state[k] for k in ['assembly_force_over_Epanel_mm2','assembly_separation_mm','compliance_Epanel_over_k_per_mm','adjustment_mm']},
        'source_files':{k:{'path':str(p),'sha256':sha256(p)} for k,p in [('solver_report',reportpath),('field',fieldpath),('independent_report',auditpath)]}}
    decode_control(payload,model_identity=state['model_identity'],external_scale=0.)
    # Exclusive create avoids replacing a prior installed state or changing its meaning.
    with out.open('x') as stream:json.dump(payload,stream,indent=2,allow_nan=False);stream.write('\n')
    return payload
