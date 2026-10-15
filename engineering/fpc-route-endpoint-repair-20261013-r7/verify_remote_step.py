"""Read only our STEP exports using the authorized main host's FreeCAD.

No protected or supplier CAD is modified or exported. This checks payloads;
it does not certify fit, electrical behavior, fatigue, or manufacture.
"""
from pathlib import Path
import hashlib,json,math,platform,traceback
import FreeCAD,Part
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n):return json.loads((ROOT/n).read_text())
def run():
    inputs=[{'path':e['path'],'expected_solid_count':e['source_full_payload']['positive_solid_leaves']} for e in load('native_receipt.json')['exports']]
    for r in load('corner_bay_followup_receipt.json')['rows']:
        inputs.append({'path':r['finite_STEP']['path'],'expected_solid_count':1})
        inputs.append({'path':r['path_only_STEP']['path'],'expected_path_edge_count':9})
    inputs.append({'path':load('corner_bay_mount_report.json')['export']['path'],'expected_solid_count':5})
    inputs += [{'path':r['export']['path'],'expected_solid_count':5} for r in load('mini_mount_reposition_receipt.json')['rows']]
    rows=[]
    for ent in inputs:
        p=ROOT/ent['path'];before=sha(p);record={**ent,'sha256_before':before,'complete_payload_passed':False}
        try:
            shape=Part.read(str(p));types={};leafs=[]
            def visit(s):
                name=s.ShapeType;types[name]=types.get(name,0)+1
                if not s.isValid():raise ValueError('invalid raw FreeCAD topology '+name)
                if name=='Compound' or ('expected_path_edge_count' in ent and name=='Wire'):
                    children=s.childShapes()
                    if not children:raise ValueError('empty raw compound/wire')
                    for c in children:visit(c)
                elif name=='Solid' and 'expected_solid_count' in ent:
                    if not math.isfinite(s.Volume) or s.Volume<=0:raise ValueError('nonpositive signed raw volume')
                    leafs.append(s)
                elif name=='Edge' and 'expected_path_edge_count' in ent:leafs.append(s)
                else:raise ValueError('unexpected extra raw topology '+name)
            visit(shape)
            expected=ent.get('expected_solid_count',ent.get('expected_path_edge_count'))
            if len(leafs)!=expected:raise ValueError('complete raw leaf count differs')
            record['raw_hierarchy_counts']=types;record['complete_leaf_count']=len(leafs)
            record['actual_signed_volume_sum_mm3']=sum(s.Volume for s in leafs) if 'expected_solid_count' in ent else None
            record['actual_path_length_mm']=sum(s.Length for s in leafs) if 'expected_path_edge_count' in ent else None
            record['complete_payload_passed']=True
        except Exception as exc:record['actual_exception']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        record['sha256_after']=sha(p)
        if record['sha256_after']!=before:raise ValueError('STEP bytes changed after read-only native check')
        rows.append(record)
    result={'host':platform.node(),'FreeCAD_version':list(FreeCAD.Version()),'script_sha256':sha(Path(__file__)),
      'actual_STEP_count':len(rows),'actual_solid_STEP_count':sum('expected_solid_count' in r for r in rows),'actual_path_only_STEP_count':sum('expected_path_edge_count' in r for r in rows),
      'complete_positive_solid_leaf_count':sum(r.get('complete_leaf_count',0) for r in rows if r['complete_payload_passed'] and 'expected_solid_count' in r),
      'actual_complete_payload_rejected_count':sum(not r['complete_payload_passed'] for r in rows),'rows':rows,
      'original_invalid_common_BREP_and_route_rejections_not_repaired':True,'actual_moving_FPC_or_full_PCB_or_OLED_qualified':False,
      'native_zero_means_results_recorded_not_phone_accepted':True,'manufacturing_go':False}
    (ROOT/'main_FreeCAD_STEP_review.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['host','FreeCAD_version','actual_STEP_count','complete_positive_solid_leaf_count','actual_complete_payload_rejected_count','manufacturing_go']}),flush=True)
run()
