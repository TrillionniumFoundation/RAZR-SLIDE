"""Nominal cover-first sequence with finite jaw and driver keep-out bodies.
Only a bench geometry/handling study. Jaw actuator, fixture stiffness, friction,
part support during handling, screw threads/preload and phone fit unqualified.
"""
from pathlib import Path
import argparse,json,hashlib,time,platform
import cover_admission as s
import cam_contact_native as n
from translation_regions import regions,checks


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def path_check(moving,vector,fixed,moving_name):
    own,method=regions(moving,vector);rows={}
    for name,shape in fixed.items():
        # For concave roots, sweep the obstacle relatively. This avoids filling
        # moving-root guide bores with conservative cylindrical carriers.
        if moving_name.startswith('ROOT_') and name not in ('OLD_COVER','JAW_LOWER','JAW_UPPER'):
            relative,rm=regions(shape,tuple(-v for v in vector));row=checks(relative,moving);row['method']='fixed_relative';row['construction']=rm
        else:
            row=checks(own,shape);row['method']='moving_regions';row['construction']=method
        rows[name]=row
    return rows


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();out=a.output.resolve()
    if out==s.ROOT or s.ROOT in out.parents:raise ValueError('new external output directory required')
    out.mkdir(parents=True,exist_ok=False);start=time.monotonic();allrows=[];exports={};cover_reports=[]
    sources={str(p.relative_to(s.ROOT)):sha(p) for p in [Path(__file__),Path(s.__file__),Path(__file__).with_name('translation_regions.py'),Path(s.prior.__file__)]}
    def export(name,body):
        n.single(body);p=out/(name+'.step');n.cq.exporters.export(body,str(p));b=body.BoundingBox()
        exports[name]={'path':p.name,'sha256':sha(p),'volume_mm3':body.Volume(),'bounds_mm':{k:getattr(b,k) for k in ('xmin','xmax','ymin','ymax','zmin','zmax')}}
    for side in 'LR':
        parts,raw=s.scene('STOW',side);original,root,cover,relative,report,_,_=s.design(side);cover_reports.append(report)
        ex=-1 if side=='L' else 1
        park=parts['PAWL'].translate((ex*1.1,0,0));parts['PARKED_PAWL']=park
        # Two opposed jaw TIP envelopes grip the new far tie; actuators and
        # full clamp mechanisms are not modeled or claimed physically built.
        jawlow=n.box(side,-.8,.8,12.15,12.55,-3.4,-2.9)
        jawup=n.box(side,-.8,.8,12.15,12.55,-2.5,-2.0)
        installed={'JAW_LOWER':jawlow}
        export(side+'_JAW_LOWER',jawlow);export(side+'_JAW_UPPER',jawup)
        for name,shape in parts.items():export(side+'_'+name,shape)
        stages=[('PLACE_COVER','OLD_COVER',(0,0,5.)),('CLAMP_UPPER','JAW_UPPER',(0,0,3.)),
                ('INSERT_INNER','ROOT_INNER',(-ex*10.,0,0)),('INSERT_PAWL_FROM_BELOW','PARKED_PAWL',(0,0,-25.)),
                ('INSERT_STOP0','STOP_0',(ex*10.,0,0)),('INSERT_STOP1','STOP_1',(ex*10.,0,0)),
                ('CLOSE_OUTER','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS',(ex*10.,0,0)),
                ('INSERT_JOIN_SCREW0','ROOT_JOIN_SCREW_0_M1x3_NOMINAL',(ex*10.,0,0)),
                ('INSERT_JOIN_SCREW1','ROOT_JOIN_SCREW_1_M1x3_NOMINAL',(ex*10.,0,0))]
        for stage,name,displacement in stages:
            body=jawup if name=='JAW_UPPER' else parts[name]
            rows=path_check(body,displacement,installed,name)
            record={'side':side,'stage':stage,'moving':name,'start_translation_world_mm':displacement,'end_translation_world_mm':[0.,0.,0.],
                    'fixed_names':list(installed),'checks':rows,'all_pairs_clear':all(r['all_regions_clear'] for r in rows.values())}
            allrows.append(record);installed[name]=body
            print(side,stage,'pairs',len(rows),'blocked',[k for k,v in rows.items() if not v['all_regions_clear']],flush=True)
            (out/'progress.json').write_text(json.dumps({'stages':allrows,'manufacturing_go':False},indent=2))
        for i in range(2):
            tool=n.single(n.cq.Solid.makeCylinder(1.5,60.,n.world(side,2.2,-2.4,-1.3+5*i),n.cq.Vector(ex,0,0)))
            name='JOIN_DRIVER_'+str(i);export(side+'_'+name,tool)
            rows={key:{'region_common_mm3':[n.common(tool,shape)],'all_regions_clear':n.common(tool,shape)<=1e-7,'method':'full_tool_occupancy'} for key,shape in installed.items()}
            allrows.append({'side':side,'stage':'JOIN_DRIVER_'+str(i),'moving':name,'fixed_names':list(installed),'checks':rows,'all_pairs_clear':all(r['all_regions_clear'] for r in rows.values()),'driver_nominal_diameter_mm':3.,'driver_visible_length_plus_travel_mm':60.,'socket_or_torque_qualification':False})
            print(side,name,'blocked',[k for k,v in rows.items() if not v['all_regions_clear']],flush=True)
    if sources!={p:sha(s.ROOT/p) for p in sources}:raise ValueError('source changed during execution')
    positives=[{'side':r['side'],'stage':r['stage'],'fixed':name,'regions':v['region_common_mm3']} for r in allrows for name,v in r['checks'].items() if not v['all_regions_clear']]
    result={'host':platform.node(),'source_SHA256':sources,'source_bytes_unchanged':True,'cover_designs':cover_reports,'stages':allrows,'exports':exports,
        'stage_count':len(allrows),'pair_count':sum(len(r['checks']) for r in allrows),'positive_pairs':positives,
        'nominal_declared_cover_first_sequence_clear':not positives,'native_part_geometry_changed_except_cover':False,
        'jaw_tip_geometry_included':True,'complete_clamp_actuator_and_grasp_force_qualified':False,
        'temporary_handling_of_parts_assumed':True,'screw_threads_preload_strength_friction_tolerance_qualified':False,
        'remaining_spring_cap_installation_not_newly_qualified':True,'research_bench_q_growth_mm':3.5,
        'phone_cavity_fit_unknown':True,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,
        'elapsed_seconds':time.monotonic()-start}
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print('RESULT',result['pair_count'],'positive',len(positives),flush=True)
    if positives:raise SystemExit(1)

if __name__=='__main__':main()
