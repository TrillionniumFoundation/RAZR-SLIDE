"""Separate owned process: fresh BREP/STEP readback and original Common checks.

It uses the same pinned OCCT kernel, not an independent second CAD kernel.
Partial producer evidence is read before completion is required; counts never
claim that absent or invalid geometry was read successfully.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import resource
import signal
import time
from types import SimpleNamespace
from run_l5 import ROOT,HERE,S4,SOURCES,sha,require,identity,owned_process,signature,api,stage
import cylindrical_sweep_l5 as l5
import l5_science_contract as rules
from exact_xy_support_l5 import support_certificate


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--producer',type=Path,required=True);ap.add_argument('--inputs',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    owned_process.announce_worker_from_environment(Path(__file__).resolve())
    out=args.output.resolve();require(not out.exists() and not out.is_relative_to(ROOT),'fresh reader directory outside source required')
    out.mkdir(parents=True);science=out/'science';science.mkdir();begin=time.monotonic()
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(InterruptedError('owned SIGTERM')))
    r={'schema':'razr-L5-separate-native-reader-v1','execution_completed':False,'all_original_postguards_passed':False,
       'source_runtime_unchanged':False,'verified_export_file_hashes':0,'fresh_BREP_readbacks':0,'fresh_STEP_readbacks':0,
       'same_pinned_CAD_kernel':True,'independent_second_CAD_kernel':False,'case_readbacks':[],
       'native_controls_readbacks':[],**{k:False for k in rules.FALSE_FLAGS}}
    before=None;executed=[];budget=None;own={n:sha(HERE/n) for n in SOURCES};r['external_source_sha256']=own
    def save():
        r['elapsed_seconds']=time.monotonic()-begin;r['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        identity.atomic_json(science/'NATIVE_READBACK.json',r)
    save()
    try:
        require(identity.git('rev-parse','HEAD')==S4 and not identity.git('status','--porcelain'),'immutable S4 source required')
        before=identity.snapshot();executed=identity.record_executed_project_files();identity.atomic_json(out/'source-before-private.json',before)
        import verify_slide_native as original
        import cadquery as cq
        import product_assembly as p
        import validate_product_nominal_report as guard
        budget=stage.ForwardBudget(original.Budget(SimpleNamespace(output=science/'NATIVE_READBACK.json')),api);budget.check()
        folder=args.producer.resolve();report_path=folder/'report.json';producer=json.loads(report_path.read_text())
        r['original_producer_report_sha256']=sha(report_path);r['original_producer_report_bytes']=report_path.stat().st_size
        r['producer_execution_completed']=producer['execution_completed'];r['scope']=producer['scope']
        bodies={};seen=set()
        for item in producer.get('all_scientific_exports',[]):
            budget.check();name=item['path'];require(rules.scientific_filename(name) and name not in seen,'unsafe or repeated source geometry name')
            path=folder/name;require(path.parent==folder and path.is_file() and not path.is_symlink(),'absent or linked actual native output')
            require(path.stat().st_size==item['bytes'] and sha(path)==item['sha256'],'actual native output bytes changed')
            seen.add(name);r['verified_export_file_hashes']+=1;save()
            if path.suffix=='.brep':
                body=cq.Shape.importBrep(str(path));require(body.isValid(),'readback BREP invalid topology')
                if name=='control-original-extrusion-original-face.brep':
                    require(len(body.Faces())==1 and body.Faces()[0].geomType()=='EXTRUSION','saved original EXTRUSION face changed')
                else:
                    p.whole_material(body,empty=not item.get('positive_whole_material_required',False))
                sig=item.get('signature')
                if sig is not None:
                    require(body.ShapeType()==sig['shape_type'] and body.isValid()==sig['is_valid'],'readback shape topology signature changed')
                    require(abs(float(body.Volume())-sig['signed_volume_mm3'])<=1e-7,'readback whole signed volume changed')
                bodies[name]=body;r['fresh_BREP_readbacks']+=1
            elif name.endswith('-original-face.step'):
                roots=cq.importers.importStep(str(path)).vals();require(len(roots)==1 and roots[0].isValid(),'original face STEP root invalid')
                r['fresh_STEP_readbacks']+=1
            else:
                roots=cq.importers.importStep(str(path)).vals();require(len(roots)==1,'one complete STEP root required')
                body=p.single(roots[0]);bodies[name]=body;r['fresh_STEP_readbacks']+=1
            save()
        binding=json.loads((HERE/'L5_ORIGINAL_SEVEN_BINDING.json').read_text())
        original_by_id={c['case_id']:c for c in binding['original_cases']};inputs=args.inputs.resolve()
        def body_at(record):
            require(record['path'] in bodies,'saved BREP absent from fresh native imports')
            return bodies[record['path']]
        def original_body(item):
            path=(inputs/item['path']).resolve()
            require(path.is_relative_to(inputs) and not path.is_symlink() and path.stat().st_size==item['bytes'] and sha(path)==item['sha256'],'original readback input identity changed')
            return p.single(cq.Shape.importBrep(str(path)))
        for call in producer.get('calls',[]):
            budget.check();path=folder/(call['call_id']+'.json')
            require(sha(path)==call['case_json_sha256'] and path.stat().st_size==call['case_json_bytes'],'original call record changed')
            case=json.loads(path.read_text());row={'call_id':case['call_id'],'completed':False};r['case_readbacks'].append(row);save()
            if not case.get('execution_completed'):
                row['producer_incomplete_case_not_claimed_as_readback_complete']=True;continue
            target=case['target'];spec=target['specification'];result=case['new_result'];audit=result['audit']
            rules.validate_result(result,target,spec,ROOT,guard)
            old=original_by_id[case['original_case_id']];require(target==old['target'],'whole original q target changed')
            shell=bodies[case['call_id']+'-moving-input.brep'];moving=bodies[case['call_id']+'-fixed-input.brep']
            row['input_STEP_identities']=[];row['complete_original_material_correspondence']=[]
            for role,actual,original_member in zip(('moving-input','fixed-input'),(shell,moving),old['inputs']):
                step=bodies[case['call_id']+'-'+role+'.step'];row['input_STEP_identities'].append(l5.compare(p,actual,step))
                row['complete_original_material_correspondence'].append(l5.compare(p,actual,original_body(original_member['exports']['brep'])))
            layer_shapes=[body_at(x['reconstructed_layer_BREP']) for x in audit['layers']]
            rebuilt=body_at(audit['complete_reconstructed_BREP']);row['whole_layer_union_identity']=l5.compare(p,p.fuse(layer_shapes),rebuilt)
            row['complete_input_identity']=l5.compare(p,moving,rebuilt)
            missing=moving.cut(rebuilt);leaves,missing_volume=p.whole_material(missing,empty=True)
            row['whole_source_omission_mm3']=missing_volume
            require(abs(missing_volume-audit['whole_source_omission']['signed_volume_mm3'])<=1e-7,'readback whole-source omission changed')
            if audit['whole_source_omission']['actual_difference_has_no_solid_material']:
                require(not leaves and missing_volume==0.,'claimed native-empty source difference is not empty on readback')
            checks=[];row['layer_readbacks']=checks;component_omissions=[]
            for i,entry in enumerate(audit['carrier_checks']):
                budget.check();carrier=body_at(entry['carrier_BREP']);construction=entry['construction']
                fresh={'layer_index':i,'source_layer_identity':l5.compare(p,body_at(audit['layers'][i]['actual_layer_BREP']),layer_shapes[i])}
                checks.append(fresh)
                if construction['method']=='positive_disk_capsule_prism':
                    bridge=body_at(construction['bridge_BREP']);vertices=[tuple(v.Center().toTuple()) for v in bridge.Vertices()]
                    points=construction['XY_bridge_support']['native_bridge_XY_vertices']
                    require(len(vertices)==8 and len(bridge.Edges())==12 and len(bridge.Faces())==6 and all(f.geomType()=='PLANE' for f in bridge.Faces()),'fresh bridge topology differs')
                    require(set((v[0],v[1]) for v in vertices)==set(map(tuple,points)),'fresh bridge XY differs from exact certificate')
                    exact=support_certificate(audit['source_motion_and_sections']['centerline_endpoints_native'],
                        audit['source_motion_and_sections']['layers'][i]['outer_native_radius'],points)
                    require(exact['continuous_rectangle_contained'],'fresh rounded bridge does not contain continuous rectangle')
                    zlo,zhi=entry['carrier_z_native_with_actual_bound_union']
                    for point in points:
                        zs=sorted(v[2] for v in vertices if v[:2]==tuple(point))
                        require(len(zs)==2 and zs[0]<=zlo and zs[1]>=zhi,'fresh bridge loses full Z interval')
                    pieces=[bridge,*[body_at(x) for x in construction['endpoint_disk_BREPs']]]
                    fresh['component_omissions']=[]
                    for part,record in zip(pieces,construction['component_containment_checks']):
                        left,volume=p.whole_material(part.cut(carrier),empty=True)
                        require(abs(volume-record['outside_mm3'])<=1e-7,'fresh capsule Boolean component loss changed')
                        if record['difference_has_no_solid_material']:require(not left and volume==0.,'claimed empty component loss not empty on fresh readback')
                        component_omissions.append(volume);fresh['component_omissions'].append(volume)
                static=l5.static_common(p,guard,carrier,shell);fresh['fresh_static_Common']=static
                require(abs(static['strict_common']['common_mm3']-entry['static']['strict_common']['common_mm3'])<=1e-7,'fresh original carrier Common differs')
                save()
            from translation_regions import sum_common_upper_bound
            common=sum_common_upper_bound(x['fresh_static_Common']['strict_common']['common_mm3'] for x in checks)
            upper=sum_common_upper_bound([common,missing_volume,math.fsum(component_omissions)])
            require(abs(upper-result['common_upper_bound_mm3'])<=1e-7,'fresh complete pair upper bound differs')
            require(('clear' if upper<=1e-7 else 'unresolved_enclosure_overlap')==result['original_per_pose_volume_predicate_disposition'],
                'fresh complete-pair original gate disposition changed')
            row['fresh_total_per_pose_Common_upper_bound_mm3']=upper
            negative=body_at(audit['negative_control_BREP']);values=[l5.static_common(p,guard,body_at(x['carrier_BREP']),negative) for x in audit['carrier_checks']]
            negative_sum=sum_common_upper_bound(x['strict_common']['common_mm3'] for x in values)
            require(negative_sum>1e-7,'fresh whole-input intrusion negative control failed')
            row.update(negative_control_Common_sum_mm3=negative_sum,completed=True,
                fresh_native_readback=True,disposition=result['disposition']);save()
        controls=producer.get('L5_primitive_controls',{}).get('controls',[])
        for control in controls:
            budget.check();name=control['name'];carrier=body_at(control['carrier_BREP']);source=body_at(control['source_disk_BREP'])
            settings={'ordinary':((0.,0.),(2.,.25)),'reversed':((2.,.25),(0.,0.)),'zero':((0.,0.),(0.,0.)),'tiny':((0.,0.),(0.,4.440892098500626e-16))}
            a,b=settings[name];checks=[]
            for t in (0.,.25,.5,.75,1.):
                body=source.translate((t*(b[0]-a[0]),t*(b[1]-a[1]),0.));v=p.volume(body.cut(carrier))
                require(0<=v<=1e-7,'fresh primitive finite containment failed');checks.append(v)
            r['native_controls_readbacks'].append({'name':name,'passed':True,'finite_containment_mm3':checks,
                'finite_checks_not_continuous_argument':True});save()
        require(producer['execution_completed'] and producer['all_original_postguards_passed'] and producer['source_runtime_unchanged'] and producer['external_source_unchanged'],
            'partial producer cannot yield complete native reader pass')
        require(len(r['case_readbacks'])==7 and all(x['completed'] for x in r['case_readbacks']) and len(r['native_controls_readbacks'])==4,'complete original cases or primitive readback omitted')
        r.update(execution_completed=True,all_original_postguards_passed=True,
            disposition_counts=dict(Counter(x['disposition'] for x in r['case_readbacks'])),
            original_controls_and_same_saved_EXTRUSION_BREP_read_back=True)
    except (api.CapacityStop,InterruptedError) as exc:r['capacity_failure_type']=type(exc).__name__
    except BaseException as exc:r['failure_type']=type(exc).__name__
    finally:
        try:
            if before is not None:
                after=identity.finish(before,executed);identity.atomic_json(out/'source-after-private.json',after)
                r['source_runtime_unchanged']=after['source_bytes_and_locked_environment_unchanged']
                require(after['repository_head_at_finish']==S4 and not identity.git('status','--porcelain'),'reader source closure changed')
            require(own=={n:sha(HERE/n) for n in SOURCES},'reader frozen external source changed');r['external_source_unchanged']=True
        except Exception as exc:r['postflight_failure_type']=type(exc).__name__;r['source_runtime_unchanged']=False
        if budget is not None:r['original_resource_record']=budget.record()
        save()
    print(json.dumps({k:r.get(k) for k in ('execution_completed','all_original_postguards_passed','fresh_BREP_readbacks','fresh_STEP_readbacks','failure_type','capacity_failure_type','elapsed_seconds')}),flush=True)
    return 0 if (r['execution_completed'] and r['all_original_postguards_passed'] and r['source_runtime_unchanged'] and not r.get('failure_type') and not r.get('postflight_failure_type')) else 2

if __name__=='__main__':raise SystemExit(main())
