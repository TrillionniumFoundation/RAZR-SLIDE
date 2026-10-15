"""Independent direct-B/KEY rigid-motion negative witnesses from stored native STEP.

12 mm is the existing VERIFIED LOCAL DOMAIN, not a proven physical hard stop.
This reader deliberately checks beyond it: a native collision at slide=64 mm
and final envelope protrusion after 79.75 mm slide / 8.2 mm normal descent.
No assumption of permanent KEY guide engagement is needed for these failures.
Only the current fixed study geometry / direct rigid transform are rejected.
No trajectory acceptance, force, alternative transmission or product release.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import tarfile
import tempfile


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    a=ap.parse_args();root=a.repo.resolve();out=a.output.resolve()
    if out==root or root in out.parents:raise ValueError('new external output required')
    sys.path.insert(0,str(root/'integration'))
    import cadquery as cq
    import cam_contact_native as n
    folder=root/'engineering/mounted-mechanism-20261015'
    gm=json.loads((folder/'geometry-manifest.json').read_text());arc=folder/gm['archive']
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    if sha(arc)!=gm['archive_sha256']:raise ValueError('source archive differs')
    entries={e['path']:e for e in gm['files']};parts={};source_hashes={str(arc):sha(arc),str(folder/'geometry-manifest.json'):sha(folder/'geometry-manifest.json')}
    with tarfile.open(arc,'r:gz') as t,tempfile.TemporaryDirectory(prefix='rigid-key-reader-') as td:
        for name in ('L_KEY','R_KEY','A_FRAME','A_OUTER','B_OUTER'):
            member=name+'.step';data=t.extractfile(member).read();e=entries[member]
            if len(data)!=e['bytes'] or hashlib.sha256(data).hexdigest()!=e['sha256']:raise ValueError('source member differs')
            f=Path(td)/member;f.write_bytes(data);vals=cq.importers.importStep(str(f)).vals()
            if len(vals)!=1:raise ValueError('extra source root')
            parts[name]=n.single(vals[0])
    out.mkdir(parents=True,exist_ok=False);rows=[];exports={}
    for side in 'LR':
        key=parts[side+'_KEY']
        for label,slide,descent in [('LOCAL_12_CONTROL',12.,0.),('MID_64_FAILURE',64.,0.),('SEATED_FAILURE',79.75,8.2)]:
            moved=key.translate((0,slide,-descent))
            collision=n.common(moved,parts['A_FRAME'])
            outside=None
            if descent:
                b=parts['B_OUTER'].translate((0,slide,8.2-descent))
                remainder=moved.cut(parts['A_OUTER']);n.whole_material(remainder,empty=True)
                remainder=remainder.cut(b);outside=n.whole_material(remainder,empty=True)[1]
            if label=='LOCAL_12_CONTROL' and collision>1e-7:raise ValueError('old local shell-clear control changed')
            if label=='MID_64_FAILURE' and collision<=1e-7:raise ValueError('missing real mid-stroke collision')
            if label=='SEATED_FAILURE' and abs(outside-moved.Volume())>1e-7:raise ValueError('expected full end-pose protrusion not reproduced')
            name=side+'_'+label;path=out/(name+'.step');cq.exporters.export(moved,str(path));bb=moved.BoundingBox()
            exports[name]={'path':path.name,'sha256':sha(path),'volume_mm3':moved.Volume(),'bounds_xyz_mm':[bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax]}
            rows.append({'side':side,'case':label,'B_slide_mm':slide,'B_normal_descent_mm':descent,
                         'KEY_world_translation_mm':[0,slide,-descent],'native_A_frame_common_mm3':collision,
                         'outside_combined_final_A_B_outer_mm3':outside,'KEY_material_volume_mm3':moved.Volume()})
    if any(sha(p)!=h for p,h in source_hashes.items()):raise ValueError('source changed during diagnostic')
    if any(m in sys.modules for m in ('mounted_mechanism','thin_mechanism','phone_layout')):raise ValueError('candidate builder imported')
    result={'source_main_base':'287d37d035cf2497b69bfe6af0866b4531274e71','diagnosed_functional_commit':'e8640c4c8b745f721ba6c150141a439497c6164b',
            'source_archive_sha256':gm['archive_sha256'],'reader_sha256':sha(__file__),'source_input_sha256':source_hashes,
            'cases':rows,'exports':exports,'local_12mm_is_not_a_proven_physical_stop':True,
            'beyond_local_domain_explicitly_evaluated':True,'direct_rigid_coupling_rejected_by_native_geometry':True,
            'not_a_rejection_of_retractable_or_lost_motion_couplings':True,'not_full_trajectory_acceptance':True,
            'candidate_builder_imported':False,'same_CAD_kernel':True,'expected_negative_witnesses_reproduced':True,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'cases':rows,'direct_rigid_link_rejected':True,'alternative_coupling_still_open':True}),flush=True)


if __name__=='__main__':main()
