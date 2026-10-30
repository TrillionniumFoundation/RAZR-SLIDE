"""Freeze only named sources and exact complete current originals for R13."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
OLD = Path('/workspace/scratch/f11ac2a81fe4/RAZR-SLIDE')
R9 = OLD / 'engineering/engineering-followup-20261029-r9/geometry'
R12 = HERE.parent / 'geometry_work'
RAW = Path('/workspace/scratch/f11ac2a81fe4/recovery/R9_geometry_originals/payload/producer-v3-attempt1/stow_tabs_0')
OUT = HERE / 'inputs'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

assert (HERE / 'PLAN_AND_RESOURCE_BASIS.json').is_file()
assert not OUT.exists(), 'Do not overwrite an input freeze.'
OUT.mkdir()
paths = {}
for name in ('key_forward_loop_v1.py','panel_key_travel_stops_v1.py','report.json'):
    paths[name] = R12 / 'inputs' / name
for name in ('KEY_FORWARD_LOOP_V1_CONTRACT.json','PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json','full_stop_states.py'):
    paths[name] = R9 / 'source-originals' / name
for name in ('cam_coupling.py','cam_contact_profile.py','product_assembly.py','product_nominal_motion.py','verify_cam_coupling.py','product_split_assembly.py'):
    paths[name] = OLD / 'integration' / name
paths['SOURCE_ALLOWED_DOMAIN_TEN_STATE_READBACK_V2.json'] = R9 / 'SOURCE_ALLOWED_DOMAIN_TEN_STATE_READBACK_V2.json'
for body in ('A_BACK_PANEL','L_KEY','R_KEY'):
    for fmt in ('brep','step'):
        paths[body+'.'+fmt] = R12 / 'inputs' / (body+'.'+fmt)
factory = json.loads(paths['report.json'].read_text())
for side in 'LR':
    for i in (0,1):
        for role in (f'{side}_STOP_{i}', f'{side}_SPRING_{i}_OD_TOL_ENVELOPE'):
            for fmt in ('brep','step'):
                rec = factory['body_exports'][role]['files'][fmt]
                path = RAW / rec['path']
                assert path.stat().st_size == rec['bytes'] and sha(path) == rec['sha256']
                paths[role+'.'+fmt] = path
files = {}
for name, src in paths.items():
    dst = OUT / name
    shutil.copyfile(src,dst)
    files[name] = {'source_path':str(src),'copy_path':'inputs/'+name,'bytes':dst.stat().st_size,'sha256':sha(dst)}
    assert sha(src)==files[name]['sha256']
for body in ('A_BACK_PANEL','L_KEY','R_KEY'):
    for fmt in ('brep','step'):
        rec = factory['body_exports'][body]['files'][fmt]
        assert files[body+'.'+fmt]['bytes']==rec['bytes'] and files[body+'.'+fmt]['sha256']==rec['sha256']
domain=json.loads((OUT/'SOURCE_ALLOWED_DOMAIN_TEN_STATE_READBACK_V2.json').read_text())
for name, row in domain['domain_source_files'].items():
    assert files[name]['sha256']==row['sha256'] and files[name]['bytes']==row['bytes'], name
assert files['cam_contact_profile.py']['sha256']==domain['profile_source']['sha256']
result={'schema':'razr-r13-exact-current-input-freeze-v1','files':files,'file_count':len(files),
        'total_bytes':sum(x['bytes'] for x in files.values()),'full_factory_original_report_state':factory['state'],
        'full_current_body_bytes_match_original_factory_report':True,
        'motion_sources_match_original_R9_S4_domain_readback':True,
        'original_source_modified':False}
(HERE/'INPUT_MANIFEST.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'files':result['file_count'],'bytes':result['total_bytes'],'manifest_sha256':sha(HERE/'INPUT_MANIFEST.json')}))
