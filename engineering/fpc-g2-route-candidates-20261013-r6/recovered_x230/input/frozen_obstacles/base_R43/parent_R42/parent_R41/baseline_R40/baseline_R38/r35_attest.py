"""Independent R35 receipt evaluation: research CAD qualification only, never manufacturing."""
import json,hashlib,re,platform,importlib.metadata
import cadquery as cq
from r25_capture import ROOT
from r34_attest import COUNTS as PRIOR

DOCS=('integration','dynamic','tolerance','faults','STEP_manifest')
COUNTS={**PRIOR,'R35':50}

def run(write=True):
    freeze=json.loads((ROOT/'audit/R35_R34_immutable.json').read_text())
    assert freeze['all_ancestor_bytes_unchanged'] and freeze['original_member_count']==783
    for x in freeze['entries']:
        p=ROOT/x['path'];assert p.is_file() and p.stat().st_size==x['size_bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256'],x['path']
    docs={x:json.loads((ROOT/f'verification/R35_{x}.json').read_text()) for x in DOCS}
    assert all(d['manufacturing_go'] is False for d in docs.values())
    i,d,t,f,st=(docs[x] for x in DOCS)
    assert i['B_is_valid'] and i['B_solid_count']==1
    assert all(x['cap_B_intersection_mm3']<1e-8 and x['pin_B_intersection_mm3']<1e-8 for x in i['cap_and_pin'])
    assert d['reference_poses']==10 and all(not p['penetrations_mm3'] for p in d['pose_rows'])
    assert len(d['cap_front_feed_samples'])==22 and all(x['cap_B']<1e-8 for x in d['cap_front_feed_samples'])
    assert t['configurations']==216 and t['aggregation']['0.05']['pin_cap_jams']==0
    assert f['original_R34_unsafe_joint_modes']==36 and f['electrical_single_point_bypass_count']==3
    assert f['pin_no_axial_clip_or_thread_or_locknut'] and f['axial_pin_extraction_unopposed_by_B_and_bridge']
    assert st['count']==7 and st['ghosts']==4
    for s in st['scenes']:
        assert s['parts']==s['valid_imported'] and hashlib.sha256((ROOT/'cad'/s['file']).read_bytes()).hexdigest()==s['sha256']
    for name in ('R35_A_R34_UNCHANGED.brep','R35_B_INBOARD_RAILS_AND_GUIDES.brep'):
        shape=cq.importers.importBrep(str(ROOT/'cad'/name)).val();assert shape.isValid() and len(shape.Solids())==1
    for exit_name in ('R35_inherited_exit.code','R35_new_exit.code','R35_faults_exit.code','R35_export_exit.code'):
        assert (ROOT/'verification'/exit_name).read_text().strip()=='0',exit_name
    receipts={}
    for label,count in COUNTS.items():
        name=('R35_new_50.log' if label=='R35' else f'R35_inherited_{label}.log')
        p=ROOT/'verification'/name;log=p.read_text(errors='replace')
        m=re.search(r'Ran\s+(\d+)\s+tests?',log)
        assert m and int(m.group(1))==count and log.rstrip().endswith('OK'),(label,log[-300:])
        receipts[label]=dict(tests=count,file='verification/'+name,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    out=dict(revision='R35 mechanical front capture surrogate, NO manufacturer release',
          environment=dict(python=platform.python_version(),cadquery=importlib.metadata.version('cadquery')),
          R34_zip_sha256=freeze['R34_original_zip_sha256'],ancestor_members_bytewise_same=783,
          history_tests_reexecuted=sum(PRIOR.values()),new_research_tests_reexecuted=50,
          total_research_tests_reexecuted=sum(COUNTS.values()),test_receipts=receipts,
          R35_B_valid_single_solid=True,B_net_volume_change_mm3=i['B_volume_delta_mm3'],
          named_reference_poses=10,nominal_unexpected_pose_intersections=0,
          cap_front_insertion_samples=22,cap_front_nominal_intersections=0,
          hypothesis_tolerance_configurations=t['configurations'],
          tolerance_0p05_report=t['aggregation']['0.05'],
          pin_nominal_hole_radial_play_mm=f['radial_nominal_pin_hole_play_mm'],
          nominal_gauge_plus_pin_slack_mm=f['simple_sum_nominal_two_slack_mm'],
          old_mechanical_joint_fault_escape_count=f['original_R34_unsafe_joint_modes'],
          single_point_electrical_bypass_witnesses=f['electrical_single_point_bypass_count'],
          pin_axially_withdrawable=f['axial_pin_extraction_unopposed_by_B_and_bridge'],
          step_scenes=len(st['scenes']),intentional_ghost_scenes=st['ghosts'],
          TE_native_STEP_not_received=True,A_mating_contact_not_implemented=True,
          independent_power_USB_and_OLED_qualification_missing=True,
          end_to_end_safety_and_reliability_not_proven=True,
          manufacturing_go=False)
    if write:(ROOT/'verification/R35_results.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print('R35 ATTEST',out['total_research_tests_reexecuted'],'R34 783 exact inherited; GHOST',out['intentional_ghost_scenes'],'NO-GO',flush=True)
    return out
if __name__=='__main__':run()
