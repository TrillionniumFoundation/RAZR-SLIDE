"""Selectively recover original H/restore inputs; retain failed frame history."""
import hashlib,json,pathlib,shutil,time,zipfile
from prepare_numeric_replay import ident,unpack_member


def main():
    p=pathlib.Path(__file__).resolve().parent;a=p/'original_archives';w=p/'original_inputs';e=p/'evidence'
    expected={
        'RAZR-SLIDE_N15_H_restore_four_load_science_20261027.zip':'c3cc04b9c577b8cc1d4c884e9e4334a9533148757473d32334db65a886e3f4be',
        'RAZR-SLIDE_N15_panel_H_columns_checkpoint_20261027.zip':'59d39d146c1f13c5f0b2d283e2eb973ee45f6048feebdf31954ed719943203ee',
        'RAZR-SLIDE_N15_frame_H_columns_checkpoint_20261027.zip':'f80e95c716c479999bbf9bf9fd3740849b5e7ea76ae2c64a561fd9458554f255',
        'RAZR-SLIDE_N15_original_linear_seed_20261027.zip':'98530c6a8c579d1d1858624c6659c4d6662abd77f365305a2324ddaf003fd4a1'}
    identities={}
    for name,digest in expected.items():
        value=ident(a/name);assert value['sha256']==digest;identities[name]=value
    basis=dict(schema='r12.original_H_restore_capacity_basis.v1',recorded_unix=time.time(),archives=identities,
        disk_free_bytes=shutil.disk_usage(p).free,selective_extraction_estimate_bytes=385000000,
        algorithm='Original H block roster; 7770 original basis RHS and saved projection SHA checks; five fresh-K-verified original saved full-field callbacks. No all-column K solve.',
        original_readback_source_SHA=ident(p/'read_saved_h_restore.py')['sha256'],historical_peak_RSS_KiB=581396,historical_seconds=77.3416191350002,
        address_space_limit_bytes=2*1024**3,wall_limit_seconds=180,threads=1,new_general_inverse_claimed=False)
    (e/'H_RESTORE_CAPACITY_BASIS.json').write_text(json.dumps(basis,indent=2)+'\n')
    assert basis['disk_free_bytes']>600000000
    for body in ['panel','frame']:
        z=zipfile.ZipFile(a/f'RAZR-SLIDE_N15_{body}_H_columns_checkpoint_20261027.zip')
        for i in z.infolist():
            if i.filename.startswith('runs/') and not i.is_dir():unpack_member(z,i.filename,w/(body+'-h')/i.filename)
    z=zipfile.ZipFile(a/'RAZR-SLIDE_N15_H_restore_four_load_science_20261027.zip')
    name='actual-results/combined-H-independent-readback/report.json';unpack_member(z,name,w/'n15'/name)
    z=zipfile.ZipFile(a/'RAZR-SLIDE_N15_original_linear_seed_20261027.zip')
    name='original-linear-response-seed/response.npz';unpack_member(z,name,w/'seed'/name)
    z=zipfile.ZipFile(a/'RAZR-SLIDE_N13_original_five_science_20261027.zip')
    with z.open('original/N12-engineering-40474654390.zip') as nested:
        inner=zipfile.ZipFile(nested)
        for short in ['contact_exchange.py','contact_patch_audit.py']:
            name='source/S4/integration/'+short;unpack_member(inner,name,w/'n12'/name)
    members=[ident(q) for root in ['panel-h','frame-h','n15','seed'] for q in sorted((w/root).rglob('*')) if q.is_file() and not q.name.startswith('.')]
    result=dict(schema='r12.original_H_restore_recovery.v1',completed=True,files=members,count=len(members),payload_bytes=sum(x['bytes'] for x in members),retained_failed_frame_8_520_attempt=True)
    (e/'H_RESTORE_RECOVERY.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['completed','count','payload_bytes']}))


if __name__=='__main__':main()
