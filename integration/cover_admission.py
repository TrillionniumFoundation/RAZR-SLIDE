"""Cover-first bench research candidate with explicitly redesigned interfaces.
Two closed capture features become lateral admission slots; the U runs past
q=12.2. A former disconnected locating tongue is removed by its declared full
feature box, never by largest-solid selection. Bench q grows 3.5mm. This is
not a drop-in design for the unverified finished phone cavities.
"""
from functools import lru_cache
from pathlib import Path
import json,gzip,hashlib,tarfile,tempfile
from verify_contact_motion import PARTS
import keycover_bypass as prior
import cam_contact_native as n
from translation_regions import regions,subtract_regions,checks
ROOT=prior.ROOT;GROUP=prior.GROUP;b=prior.b;parent=prior.parent
baseline=prior.baseline;previous=prior.previous
ROOT_NAME=prior.ROOT_NAME;check=prior.check;pairs=prior.pairs
volume_leaves=prior.volume_leaves


@lru_cache(maxsize=2)
def native_base(side):
    if side not in ('L','R'):raise ValueError('invalid side')
    phase=ROOT/'engineering/keycover-geometry-20261014'
    m=json.loads((phase/'geometry-manifest.json').read_text());archive=phase/'project-owned-geometry.tar.gz'
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=m['archive_sha256']:raise ValueError('canonical native archive changed')
    entries={x['path']:x for x in m['files']};parts={}
    with tempfile.TemporaryDirectory(prefix='native-cover-admission-') as td:
        with tarfile.open(archive,'r:gz') as t:
            for name in PARTS|{'KEY_COMPLETE_Q'}:
                member='motion/'+side+'_'+name+'.step';data=t.extractfile(member).read()
                if hashlib.sha256(data).hexdigest()!=entries[member]['sha256']:raise ValueError('canonical native member changed')
                f=Path(td)/(name+'.step');f.write_bytes(data);values=n.cq.importers.importStep(str(f)).vals()
                if len(values)!=1:raise ValueError('extra STEP roots')
                parts[name]=n.single(values[0])
        prior_phase=ROOT/'engineering/contact-motion-20261014'
        pm=json.loads((prior_phase/'geometry-manifest.json').read_text());pa=prior_phase/'project-owned-native-geometry.tar.gz'
        if hashlib.sha256(pa.read_bytes()).hexdigest()!=pm['archive_sha256']:raise ValueError('original cover archive changed')
        member='contact/'+side+'_OLD_COVER.step';item=next(x for x in pm['files'] if x['path']==member)
        with tarfile.open(pa,'r:gz') as t:data=t.extractfile(member).read()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('original cover changed')
        f=Path(td)/'original.step';f.write_bytes(data);original_cover=n.single(n.cq.importers.importStep(str(f)).val())
    raw=json.loads(gzip.decompress((phase/'native/motion130.json.gz').read_bytes()))
    record=next(x['repair'] for x in raw['rows'] if x['side']==side)
    return parts,original_cover,record

@lru_cache(maxsize=2)
def design(side):
    frozen,source,previous_report=native_base(side)
    original={k:v for k,v in frozen.items() if k in PARTS};root=original[ROOT_NAME];current_cover=original['OLD_COVER'];relative={};key=frozen['KEY_COMPLETE_Q']
    inside=1 if side=='L' else -1
    ir,im=regions(original['ROOT_INNER'],(inside*10.,0,0))
    er,em=regions(root,(-inside*10.,0,0))
    bridge=n.fuse([n.box(side,-2.7,-2.4,4.9,12.5,-2.9,-2.5),n.box(side,2.4,2.7,4.9,12.5,-2.9,-2.5),n.box(side,-2.7,2.7,12.2,12.5,-2.9,-2.5)])
    tongue=n.box(side,1.21,4.26,1.74,1.86,-7.25,-6.43)
    cut=subtract_regions(source.fuse(bridge).cut(key).clean(),ir+er)
    preleaves,_=n.whole_material(cut)
    if len(preleaves)!=2:raise ValueError('former-tongue counterexample changed')
    new=cut.cut(tongue).clean();n.single(new)
    removed=n.whole_material(source.cut(new),empty=True)[1];added=n.whole_material(new.cut(source),empty=True)[1]
    permitted=subtract_regions(source.cut(new).cut(key).cut(tongue),ir+er)
    if n.whole_material(permitted,empty=True)[1]>1e-7:raise ValueError('unaccounted original cover material removal')
    if abs(source.Volume()+added-removed-new.Volume())>1e-7:raise ValueError('cover material balance differs')
    if n.common(new,key)>1e-7 or not checks(ir,new)['all_regions_clear'] or not checks(er,new)['all_regions_clear']:raise ValueError('whole KEY/root admission intersects cover')
    report={'candidate':'far_bridge_cover_first_lateral_admission','side':side,
        'parent_contact_receipt':previous_report['parent_contact_receipt'],
        'previous_keycover_report':previous_report,'changed_parts':['OLD_COVER'],
        'native_roots_KEY_STOP_pawl_unchanged':True,
        'before_cover_bounds_eqr_mm':n.bounds(side,current_cover),'after_cover_bounds_eqr_mm':n.bounds(side,new),
        'qmax_bench_growth_mm':3.5,'phone_cavity_fit':'unknown','research_only_not_drop_in_phone_replacement':True,
        'source_cover_volume_mm3':source.Volume(),'new_cover_volume_mm3':new.Volume(),
        'source_original_removed_mm3':removed,'new_added_mm3':added,
        'new_lateral_locator_slots':True,'original_closed_locator_holes_preserved':False,
        'former_tongue_removal_box_eqr_mm':[1.21,4.26,1.74,1.86,-7.25,-6.43],
        'former_tongue_removal_mm3':n.whole_material(cut.cut(new),empty=True)[1],
        'pre_feature_removal_components':len(preleaves),'new_cover_single_positive_solid':True,'no_largest_fragment_selection':True,
        'inner_admission_method':im,'outer_admission_method':em,
        'capture_retention_strength_tolerance_and_phone_qualification':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    return original,root,new,relative,report,key,cut

def fixed_design(side):
    original,root,cover,relative,report,key,cut=design(side)
    return original,root,relative,report

def full_stop_envelopes(side):return prior.full_stop_envelopes(side)

def repair_parts(parts,port,side,*,enabled=True):
    if port not in ('STOW','OPEN') or side not in ('L','R') or type(enabled) is not bool:raise ValueError('invalid scene identity')
    if not enabled or port=='OPEN':return dict(parts),{'changed_parts':[],'manufacturing_go':False}
    original,root,cover,relative,report,key,cut=design(side)
    oldcover=native_base(side)[0]['OLD_COVER']
    if n.whole_material(parts['OLD_COVER'].cut(oldcover),empty=True)[1]>1e-7 or n.whole_material(oldcover.cut(parts['OLD_COVER']),empty=True)[1]>1e-7:raise ValueError('not the pinned previous cover')
    out=dict(parts);out['OLD_COVER']=cover
    if any(not out[k].wrapped.IsSame(v.wrapped) for k,v in parts.items() if k!='OLD_COVER'):raise ValueError('non-cover component changed')
    return out,report

def scene(port,side,lift=1.14,present=True,*,enabled=True):
    if port=='STOW' and lift==1.14 and present is True:
        parts={k:v for k,v in native_base(side)[0].items() if k in PARTS};raw={'canonical_native_STEP_source':True}
    else:parts,raw=prior.scene(port,side,lift,present)
    out,report=repair_parts(parts,port,side,enabled=enabled)
    return out,{**raw,'cover_first_admission':report}
