"""Full prior-positive ledger reduction under explicit completed trim premises."""
import argparse,gzip,hashlib,json,math,os,resource,signal,sys,time,traceback
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def ident(p):
    p=Path(p);return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def readz(p):
    with gzip.open(p,'rt') as stream:return json.load(stream)
def writez(p,data):
    with gzip.open(p,'wt') as stream:json.dump(data,stream,separators=(',',':'))
def main():
    p=argparse.ArgumentParser();p.add_argument('--native-report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(805306368,805306368));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('120-second completion-corridor producer limit')));signal.alarm(120)
    report={'schema':'razr-r13-conditional-completion-corridor-ledger-v1','completed':False,'pairs':[],
        'source':ident(__file__),'capacity_basis':ident(ROOT/'ALGORITHM_AND_CAPACITY.md'),'model_definition':ident(ROOT/'COMPLETION_MODEL_DEFINITION.md'),
        'limits':{'seconds':120,'address_space_bytes':805306368,'cpus':1},'original_threshold_exact':str(F(1e-7)),
        'original_spatial_split_limit':4096,'original_depth_limit':24,'additional_spatial_splits':0,'additional_depth':0,
        'native_filled_domain_equals_completion_model_proved':False,'uniform_compiled_error_proved':False,
        'actual_collision_proved':False,'continuous_G2':False,'whole_15D_G2':False}
    try:
        import completion_model_r13 as model
        sys.path.insert(0,str(ROOT/'inputs'));import projected_boundary_r12 as support
        report['model_source']=ident(model.__file__);report['inherited_projection_source']=ident(support.__file__)
        manifest=json.loads((ROOT/'inputs/INPUT_MANIFEST.json').read_text())
        for row in manifest['files']:
            actual=ident(ROOT/'inputs'/row['path']);assert all(actual[k]==row[k] for k in ('bytes','sha256'))
        report['input_manifest']=ident(ROOT/'inputs/INPUT_MANIFEST.json')
        native=json.loads(a.native_report.read_text());assert native['completed'] and native['wire_count']==12 and native['complete_ordered_edge_count']==48
        report['native_report']=ident(a.native_report)
        certificates={f['face_index']:model.build_face(f) for f in native['faces']}
        assert sorted(certificates)==[104,109,110,115,118,121]
        certfile=a.output/'complete_trim_corridors.json';certfile.write_text(json.dumps({'schema':'razr-r13-six-guide-face-completion-corridors-v1',
            'native_report':ident(a.native_report),'model_source':ident(model.__file__),'model_definition':ident(ROOT/'COMPLETION_MODEL_DEFINITION.md'),
            'faces':[certificates[i] for i in sorted(certificates)],'actual_native_trim_model_membership_proved':False},indent=2)+'\n')
        report['complete_trim_corridors']=ident(certfile)
        projections=readz(ROOT/'inputs/R12_complete_projections.json.gz')['bodies']['A_BACK_PANEL'];assert len(projections)==298
        ymax=max(F(p[1][1]) for p in projections)
        for side in ('L','R'):
            key=side+'_KEY';priorpath=ROOT/f'inputs/R12_{key}_exterior.json.gz';prior=readz(priorpath)
            originals=prior['original_positive_boxes'];rows=[];prior_sum=F(0);current_sum=F(0);original_sum=F(0)
            counts={'inherited_KEY_exterior':0,'new_panel_completed_trim_exterior':0,'retained_positive_full_box':0};new_faces=set()
            for previous in originals:
                B=[tuple(map(F,p)) for p in previous['box_exact']];volume=math.prod(b-a for a,b in B);assert volume>0 and volume==F(previous['positive_full_box_volume_exact'])
                before=F(previous['upper_exact']);assert before in (0,volume)
                original_sum+=volume;prior_sum+=before
                item={'locator':previous['locator'],'box_exact':previous['box_exact'],'original_positive_full_box_volume_exact':str(volume),
                      'R12_upper_exact':str(before),'upper_under_B0_and_T_exact':str(before)}
                if before==0:
                    assert previous['kind']=='KEY_bent_negative_Y_then_outside_X'
                    item.update(kind='inherited_KEY_exterior',original_certificate=previous)
                else:
                    tube=(B[0],(B[1][0],ymax+1),B[2]);witnesses=[];failed=[]
                    assert all(a<=c<d<=b for (a,b),(c,d) in zip(tube,B))
                    for fi,face in enumerate(projections):
                        witness=None
                        for k,n in enumerate(support.NORMALS):
                            lo,hi=support.box_projection(tube,n);a0,b0=map(F,face[k])
                            if b0<=lo:witness={'face_index':fi,'method':'original_complete_support','normal':k,'relation':'at_or_below_open_tube'};break
                            if a0>=hi:witness={'face_index':fi,'method':'original_complete_support','normal':k,'relation':'at_or_above_open_tube'};break
                        if witness is None and fi in certificates:witness=model.exclude_query(tube,certificates[fi])
                        if witness is None:failed.append(fi)
                        else:witnesses.append(witness)
                    if not failed:
                        assert len(witnesses)==298 and sorted(w['face_index'] for w in witnesses)==list(range(298))
                        item.update(kind='new_panel_completed_trim_exterior',upper_under_B0_and_T_exact='0',
                            open_tube_exact=model.ser_box(tube),all_298_complete_face_witnesses=witnesses,
                            outside_global_Y_support_exact=str(ymax),new_trim_faces=[w['face_index'] for w in witnesses if w['method']!='original_complete_support'])
                        new_faces.update(item['new_trim_faces'])
                    else:item.update(kind='retained_positive_full_box',unresolved_full_support_faces=failed)
                counts[item['kind']]+=1;current_sum+=F(item['upper_under_B0_and_T_exact']);rows.append(item)
            assert len(rows)==len(originals) and original_sum==F(prior['original_full_bound_exact']) and prior_sum==F(prior['remaining_full_bound_exact'])
            payload={'schema':'razr-r13-all-original-positive-boxes-with-explicit-trim-premises-v1','key':key,'source_R12_ledger':ident(priorpath),
                'complete_trim_corridors':ident(certfile),'original_positive_boxes':rows,'counts':counts,
                'original_coarse_sum_exact':str(original_sum),'unchanged_R12_B0_only_sum_exact':str(prior_sum),
                'new_B0_and_T_sum_exact':str(current_sum),'new_B0_and_T_threshold_passes':current_sum<=F(1e-7),
                'all_original_positive_boxes_accounted':True,'actual_native_T_membership_proved':False,
                'actual_native_B0_membership_proved':False,'uniform_compiled_error_proved':False,'continuous_G2':False}
            path=a.output/f'{key}-completed-trim-ledger.json.gz';writez(path,payload)
            report['pairs'].append({'key':key,'all_original_positive_boxes':len(rows),'counts':counts,'trim_faces_used':sorted(new_faces),
                'R12_B0_only_upper_exact':str(prior_sum),'R12_B0_only_upper_approx_mm3':float(prior_sum),
                'B0_and_T_upper_exact':str(current_sum),'B0_and_T_upper_approx_mm3':float(current_sum),
                'original_1e_minus7_passes_only_under_B0_and_T':current_sum<=F(1e-7),'ledger':ident(path)})
        assert report['native_report']==ident(a.native_report);report['completed']=True
    except Exception as e:report['failure']={'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0);report['seconds']=time.monotonic()-start;report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report.get(k) for k in ('completed','pairs','seconds','peak_RSS_bytes','failure')}))
    if not report['completed']:raise SystemExit(1)

if __name__=='__main__':main()
