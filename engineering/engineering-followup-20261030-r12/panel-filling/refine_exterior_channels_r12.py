"""Bounded exact exterior-channel refinement of all positive coarse cells."""
import argparse
from fractions import Fraction as F
import gzip,hashlib,json,os,resource,signal,time,traceback
from pathlib import Path


def identity(p):
    p=Path(p);return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}


def main():
    p=argparse.ArgumentParser();p.add_argument('--native-report',type=Path,required=True);p.add_argument('--coarse',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(805306368,805306368));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('180-second exterior-channel budget')));signal.alarm(180)
    report={'schema':'razr-r12-complete-original-cell-exterior-channel-refinement-v1','completed':False,'pairs':[],
        'original_threshold_exact':str(F(1e-7)),'new_spatial_splits':0,'new_split_depth':0,
        'original_split_limit':4096,'original_depth_limit':24,
        'full_continuous_G2':False,'native_material_set_identity_proved':False,'uniform_compiled_error_proved':False,
        'limits':{'seconds':180,'address_space_bytes':805306368,'cpus':1},'source':identity(__file__)}
    try:
        import projected_boundary_r12 as support
        native=json.loads(a.native_report.read_text());assert native['completed']
        report['native_report']=identity(a.native_report);report['projection_source']=identity(support.__file__)
        report['capacity_basis']=identity(Path(__file__).parent/'EXTERIOR_CHANNEL_BASIS.md')
        projections={name:support.all_faces(body) for name,body in native['bodies'].items()}
        projection_path=a.output/'complete_face_projections.json.gz'
        with gzip.open(projection_path,'wt') as stream:json.dump({'normals':support.NORMALS,'bodies':projections},stream,separators=(',',':'))
        report['projections']=identity(projection_path)
        for key in ('L_KEY','R_KEY'):
            coarsepath=a.coarse/(key+'-XYZ_intersection.json.gz');coarse=json.load(gzip.open(coarsepath,'rt'))
            grids=[[F(x) for x in g] for g in coarse['grid_exact']]
            original_sum=F(0);remaining_sum=F(0);boxes=[];panel_ymax=max(F(p[1][1]) for p in projections['A_BACK_PANEL'])
            key_xmin=min(F(p[0][0]) for p in projections[key]);key_xmax=max(F(p[0][1]) for p in projections[key])
            counts={'panel_positive_Y_channel':0,'KEY_bent_negative_Y_then_outside_X':0,'retained_positive_full_box':0}
            for piece_index,piece in enumerate(coarse['x_pieces']):
                i0,i1=piece['x_grid_interval'];X=(grids[0][i0],grids[0][i1])
                for row_index,(j,runs) in enumerate(piece['occupied_y_rows']):
                    Y=(grids[1][j],grids[1][j+1])
                    for run_index,(k0,k1) in enumerate(runs):
                        Z=(grids[2][k0],grids[2][k1]);B=(X,Y,Z);volume=(X[1]-X[0])*(Y[1]-Y[0])*(Z[1]-Z[0]);assert volume>0
                        original_sum+=volume
                        item={'locator':[piece_index,row_index,run_index],'box_exact':[[str(x),str(y)] for x,y in B],
                              'positive_full_box_volume_exact':str(volume),'kind':'retained_positive_full_box','upper_exact':str(volume)}
                        tube=(X,(Y[0],panel_ymax+1),Z)
                        proof=support.channel_proof(tube,projections['A_BACK_PANEL']) if tube[1][1]>tube[1][0] else None
                        if proof:
                            item.update(kind='panel_positive_Y_channel',upper_exact='0',channels=[proof],
                                        outside_global_support_axis=1,outside_global_support_end=str(panel_ymax))
                        elif Y[0]>=53:
                            first=(X,(F(52),Y[1]),Z)
                            second=((key_xmin-1,X[1]) if key=='L_KEY' else (X[0],key_xmax+1),(F(52),F(53)),Z)
                            firstproof=support.channel_proof(first,projections[key]);secondproof=support.channel_proof(second,projections[key]) if firstproof else None
                            if firstproof and secondproof:
                                item.update(kind='KEY_bent_negative_Y_then_outside_X',upper_exact='0',channels=[firstproof,secondproof],
                                            outside_global_support_axis=0,outside_global_support_end=str(key_xmin if key=='L_KEY' else key_xmax))
                        remaining_sum+=F(item['upper_exact']);counts[item['kind']]+=1;boxes.append(item)
            assert original_sum==F(coarse['exact_intersection_upper_volume'])
            payload={'schema':'razr-r12-exact-exterior-refinement-complete-ledger-v1','key':key,'coarse':identity(coarsepath),
                     'native_report':identity(a.native_report),'projections':identity(projection_path),'original_positive_boxes':boxes,
                     'original_full_bound_exact':str(original_sum),'remaining_full_bound_exact':str(remaining_sum),
                     'counts':counts,'new_splits':0,'all_original_positive_contributions_accounted':True,
                     'gate_pass_under_complete_represented_boundary_compact_filling_model':remaining_sum<=F(1e-7),
                     'actual_native_set_identity_proved':False,'uniform_compiled_error_proved':False,'full_continuous_G2':False}
            path=a.output/(key+'-exterior-ledger.json.gz')
            with gzip.open(path,'wt') as stream:json.dump(payload,stream,separators=(',',':'))
            report['pairs'].append({'key':key,'counts':counts,'original_positive_boxes':len(boxes),'original_bound_approx':float(original_sum),
                                   'remaining_upper_exact':str(remaining_sum),'remaining_upper_mm3_approx':float(remaining_sum),
                                   'original_1e_minus7_gate_passes_under_stated_model':remaining_sum<=F(1e-7),'ledger':identity(path)})
        report['completed']=True
    except Exception as exc:report['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0);report['seconds']=time.monotonic()-start;report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report.get(k) for k in ('completed','pairs','seconds','peak_RSS_bytes','failure')}))
    if not report['completed']:raise SystemExit(1)

if __name__=='__main__':main()
