"""Independent R34 source and receipt attestation; PASS does not mean safe."""
from __future__ import annotations
import json,hashlib,re,platform,importlib.metadata
import cadquery as cq
from r25_capture import ROOT
from r32_attest import LABELS as HIST

NAMES=('integration','dynamic','tolerance','faults','STEP_manifest')
COUNTS={**HIST,'R33':40,'R34':36}

def run(write=True):
    freeze=json.loads((ROOT/'audit/R34_R33_immutable.json').read_text())
    assert freeze['ancestor_files_verified']==706 and freeze['all_ancestor_bytes_unchanged']
    for o in freeze['originals']:
        p=ROOT/o['path']
        assert p.is_file() and p.stat().st_size==o['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==o['sha256'],o['path']
    docs={n:json.loads((ROOT/f'verification/R34_{n}.json').read_text()) for n in NAMES}
    assert all(x['manufacturing_go'] is False for x in docs.values())
    i,d,t,f,st=(docs[k] for k in NAMES)
    assert i['B_is_valid_single_solid']
    assert i['final_orphan_solids']==0 and abs(i['interim_orphan_volume_removed_by_throat_mm3']-.1328)<1e-5
    assert len(d['unexpected_named_pose_collisions'])==0 and d['reference_poses']==10
    assert d['front_feed_cases']==28 and d['front_feed_interference_cases']==0
    assert d['top_feed_interference_cases']==10
    assert t['cases']==216 and t['offset_aggregation']['0.12']['hits']==42
    assert f['legacy_mechanical_combined_fault_escapes']==36
    assert f['electrical_single_fault_bypass_count']==3
    assert f['front_feed_reverse_escape_unopposed']
    assert st['count']==6 and st['ghost_count']==3
    for x in st['scenes']:
        assert x['parts']==x['valid_imported']
        assert hashlib.sha256((ROOT/'cad'/x['file']).read_bytes()).hexdigest()==x['sha256']
    for part in ['R34_A_R33_UNCHANGED.brep','R34_B_OPEN_SIGNAL_ENVELOPE_CRADLES.brep']:
        solid=cq.importers.importBrep(str(ROOT/'cad'/part)).val()
        assert solid.isValid() and len(solid.Solids())==1
    assert (ROOT/'verification/R34_inherited_exit.code').read_text().strip()=='0'
    assert (ROOT/'verification/R34_new_exit.code').read_text().strip()=='0'
    receipts={}
    for label,count in COUNTS.items():
        name='R34_new_36.log' if label=='R34' else f'R34_inherited_{label}.log'
        raw=(ROOT/'verification'/name).read_text(errors='replace')
        m=re.search(r'Ran\s+(\d+)\s+tests?',raw)
        assert m and int(m.group(1))==count and raw.rstrip().endswith('OK'),(label,raw[-250:])
        receipts[label]=dict(tests=count,file='verification/'+name,
                             sha256=hashlib.sha256((ROOT/'verification'/name).read_bytes()).hexdigest())
    out=dict(revision='R34 catalogue envelope bay research attestation: NO manufacturing release',
             date='2026-10-11',python=platform.python_version(),cadquery=importlib.metadata.version('cadquery'),
             ancestor_R33_zip_sha256=freeze['ancestor_zip_sha256'],
             original_R33_members_bytewise_unchanged=freeze['ancestor_files_verified'],
             historical_tests_reexecuted=sum(v for k,v in COUNTS.items() if k!='R34'),
             new_tests_reexecuted=COUNTS['R34'],all_tests_reexecuted=sum(COUNTS.values()),receipts=receipts,
             R34_B_valid_one_solid=i['B_is_valid_single_solid'],
             B_R34_net_volume_delta_mm3=i['B_R34_net_volume_delta_mm3'],
             real_front_feed_cut_mm3=i['front_throat_actual_added_cut_mm3'],
             nominal_TE_catalogue_box_2_sides_zero_B_overlap=all(z['TE_nominal_AABB_to_new_B_intersection_mm3']<1e-8 for z in i['TE_catalogue_box_fit_in_candidate_B']),
             reference_pose_count=d['reference_poses'],reference_abnormal_collisions=len(d['unexpected_named_pose_collisions']),
             front_feed_geometric_pose_samples=d['front_feed_cases'],front_feed_clash_count=d['front_feed_interference_cases'],
             top_feed_rejected_clash_count=d['top_feed_interference_cases'],
             hypothetical_offset_cases=t['cases'],hypothetical_0p12_jam_count=t['offset_aggregation']['0.12']['hits'],
             total_STEP_imported=st['count'],ghost_hazard_step_count=st['ghost_count'],
             old_mechanical_joint_escapes=f['legacy_mechanical_combined_fault_escapes'],
             electrical_single_point_bypass_count=f['electrical_single_fault_bypass_count'],
             vendor_native_STEP_imported=False,OEM_display_CAD_missing=True,
             electrical_cross_cabin_power_and_USB_not_designed=True,
             model_only_approval_does_not_count_as_product_safety=True,
             manufacturing_go=False)
    if write:(ROOT/'verification/R34_results.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print('R34 INDEPENDENT ATTEST',out['all_tests_reexecuted'],'original',out['original_R33_members_bytewise_unchanged'],'STEP',out['total_STEP_imported'],'NO-GO',flush=True)
    return out
if __name__=='__main__':run()
