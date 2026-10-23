"""Builder-free, same-kernel verification of the fixed thin research mechanism.

Reimports every declared body, checks complete material, nominal relative
motion, stated assembly translations, capture and one rigid study placement.
Assembly paths assume held/preloaded parts; no real jig/grip/load claim.
Native failures remain failures. No candidate generator is imported.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import math
import sys

import cam_contact_native as n
from verify_contact_motion import PARTS
from translation_regions import regions, checks, sum_common_upper_bound

ROOT=Path(__file__).resolve().parents[1]
ROOT_NAMES=('ROOT_INNER','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def vol(shape):return n.whole_material(shape,empty=True)[1]


def equal(a,b):
    values=[vol(a.cut(b)),vol(b.cut(a))]
    if max(values)>1e-7:raise ValueError('complete native material mismatch')
    return values


def read_parts(manifest):
    manifest=Path(manifest).resolve();r=json.loads(manifest.read_text());parts={};inputs={str(manifest):sha(manifest)}
    expected={f'{side}_{state}_{name}' for side in 'LR' for state in ('old','candidate') for name in PARTS}
    expected|={f'{side}_{state}_PLACED_ASSEMBLY' for side in 'LR' for state in ('old','candidate')}
    if set(r['exports'])!=expected:raise ValueError('missing or extra declared participant')
    for role,rec in r['exports'].items():
        name=Path(rec['path'])
        if name.is_absolute() or len(name.parts)!=1 or name.name!=role+'.step':raise ValueError('bad native filename')
        path=manifest.parent/name
        if path.is_symlink() or sha(path)!=rec['sha256']:raise ValueError('native STEP bytes differ')
        if len(rec['bounds_xyz_mm'])!=6 or not all(math.isfinite(v) for v in rec['bounds_xyz_mm']):raise ValueError('invalid bounds certificate')
        roots=n.cq.importers.importStep(str(path)).vals()
        if len(roots)!=1:raise ValueError('extra native root')
        body=roots[0];leaves,total=n.whole_material(body)
        count=23 if role.endswith('_PLACED_ASSEMBLY') else 1
        if len(leaves)!=count:raise ValueError('native full solid count differs')
        if not math.isfinite(rec['volume_mm3']) or abs(total-rec['volume_mm3'])>1e-7:raise ValueError('native volume certificate differs')
        bb=body.BoundingBox();bounds=[bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax]
        if any(abs(x-y)>1e-7 for x,y in zip(bounds,rec['bounds_xyz_mm'])):raise ValueError('native bounds differ')
        if any(leaves[i].isSame(leaves[j]) for i in range(len(leaves)) for j in range(i)):raise ValueError('repeated native leaf')
        parts[role]=body;inputs[str(path)]=sha(path)
    return r,parts,inputs


def placement(body,side):
    if side not in ('L','R'):raise ValueError('invalid side')
    return body.rotate((0,0,0),(0,1,0),90 if side=='L' else -90).rotate((0,0,0),(0,0,1),180).translate((-13.85 if side=='L' else 13.85,10.,-30.55))


def motion_check(label,moving,vector,fixed,*,relative=False):
    all_regions=None if relative else regions(moving,vector)[0]
    rows=[]
    for name,body in sorted(fixed.items()):
        result=checks(regions(body,tuple(-v for v in vector))[0],moving) if relative else checks(all_regions,body)
        rows.append({'fixed':name,**result})
    return {'label':label,'vector_mm':vector,'relative_obstacle_sweep':relative,'pairs':len(rows),
            'checks':rows,'positive_pairs':[x for x in rows if not x['all_regions_clear']]}


def stage_plan(side):
    ex=-1 if side=='L' else 1
    result=[('OLD_COVER',(0,0,5.)),('JAW_UPPER',(0,0,3.)),('ROOT_INNER',(-ex*10.,0,0)),
            ('PARKED_PAWL',(0,0,-25.)),('STOP_0',(ex*10.,0,0)),('STOP_1',(ex*10.,0,0)),
            ('ROOT_OUTER_CONNECTED_ALL_FRAGMENTS',(ex*10.,0,0)),
            ('ROOT_JOIN_SCREW_0_M1x3_NOMINAL',(ex*10.,0,0)),('ROOT_JOIN_SCREW_1_M1x3_NOMINAL',(ex*10.,0,0))]
    for i in (0,1):
        result.extend([(f'CAP_{i}',(-ex*10.,0,0)),(f'SCREW_{i}_0',(0,0,25.)),(f'SCREW_{i}_1',(0,0,25.))])
    for i in (0,1):
        result.extend([(f'SPRING_GUIDE_{i}',(0,0,25.)),(f'SPRING_{i}_OD_TOL_ENVELOPE',(0,0,25.)),
                       (f'SPRING_CAP_{i}',(0,0,25.)),(f'SPRING_SCREW_{i}_M1x3_NOMINAL',(0,0,25.))])
    return result


def contact_rejections(contacts):
    """The pin and remainder cages cover one complete STOP core per KEY pair."""
    return [row for row in contacts if sum_common_upper_bound(
        [row['pin_complete_relative_path_common_mm3'],*row['core_remainder_cage_common_mm3']])>1e-7]


def side_checks(side,old,new):
    ex=-1 if side=='L' else 1
    result={'static':[],'motion':[],'assembly':[],'contacts':[],'retention':[],'material':{}}
    for name in sorted(PARTS):
        lost=vol(old[name].cut(new[name]));added=vol(new[name].cut(old[name]))
        if abs(old[name].Volume()-lost+added-new[name].Volume())>1e-7:raise ValueError('material balance differs')
        result['material'][name]={'old_mm3':old[name].Volume(),'removed_mm3':lost,'added_mm3':added,'new_mm3':new[name].Volume()}
    for name in ('KEY','PAWL','SCREW_1_0','SCREW_1_1','ROOT_JOIN_SCREW_0_M1x3_NOMINAL','ROOT_JOIN_SCREW_1_M1x3_NOMINAL'):
        equal(old[name],new[name])
    parked=new['PAWL'].translate((ex*1.1,0,0))
    for a,b in itertools.combinations(sorted(PARTS),2):
        result['static'].append({'parts':[a,b],'common_mm3':n.common(new[a],new[b])})
    for name,body in sorted(new.items()):
        if name!='PAWL':result['static'].append({'parts':['PARKED_PAWL',name],'common_mm3':n.common(parked,body)})
    fixed={k:v for k,v in new.items() if k not in ('KEY','PAWL','STOP_0','STOP_1','SPRING_0_OD_TOL_ENVELOPE','SPRING_1_OD_TOL_ENVELOPE')}
    fixed['PARKED_PAWL']=parked
    for i in (0,1):
        stop=new['STOP_'+str(i)]
        result['motion'].append(motion_check('STOP_'+str(i),stop,(0,0,-1.16),fixed))
        core=stop.intersect(n.box(side,-1.,.4,-40,40,-40,40)).clean()
        oldcore=old['STOP_'+str(i)].intersect(n.box(side,-1.,.4,-40,40,-40,40)).clean();equal(core,oldcore)
        profile,pin,rest,geo=n.extract_profile(new['KEY'],core,side)
        full_pin,_=n.pin_path_envelope(profile,side,*geo['pin_e_extent_mm'])
        pin_common=n.common(full_pin,new['KEY']);cages=n.remainder_cages(rest,profile,side)
        cage_common=[n.common(cage,new['KEY']) for cage,desc in cages]
        new_arm=stop.cut(core).clean();n.whole_material(new_arm)
        e_arm=n.bounds(side,new_arm)[0][0];key_max=n.bounds(side,new['KEY'])[0][1]
        if e_arm-key_max<=0:raise ValueError('new arm is not separated from full KEY by e')
        result['contacts'].append({'stop':i,'old_native_core_unchanged':True,'pin_complete_relative_path_common_mm3':pin_common,
                                   'core_remainder_cage_common_mm3':cage_common,'new_arm_to_KEY_axis_gap_mm':e_arm-key_max,
                                   'complete_STOP_core_to_KEY_common_upper_bound_mm3':sum_common_upper_bound([pin_common,*cage_common]),
                                   'common_upper_bound_is_sum_not_union_volume':True,
                                   'profile':profile.receipt(),'same_kinematic_branch_not_force_proof':True})
        # The maximum spring envelope bounds every selected compressed length.
        ec,qc=2.2,(16.5,10.5)[i];off=5*i
        maximum=n.single(n.cq.Solid.makeCylinder(.43,2.62,n.world(side,ec,qc,1.78+off),n.cq.Vector(0,0,1)))
        other={k:v for k,v in new.items() if k not in (f'SPRING_{i}_OD_TOL_ENVELOPE',f'STOP_{i}','PAWL')};other['PARKED_PAWL']=parked
        for name,body in other.items():
            result['static'].append({'parts':[f'SPRING_{i}_MAX_OCCUPANCY',name],'common_mm3':n.common(maximum,body)})
    result['motion'].append(motion_check('KEY',new['KEY'],(0,-12.,0),fixed))
    result['motion'].append(motion_check('PAWL',new['PAWL'],(ex*1.1,0,0),{k:v for k,v in new.items() if k!='PAWL'}))
    for distance in (.09,.12):
        for name in ROOT_NAMES:
            result['retention'].append({'root':name,'uplift_mm':distance,'common_mm3':n.common(new['OLD_COVER'].translate((0,0,distance)),new[name])})
    parts=dict(new);parts['PARKED_PAWL']=parked
    parts['JAW_LOWER']=n.box(side,-.8,.8,12.15,12.55,-3.4,-2.9)
    parts['JAW_UPPER']=n.box(side,-.8,.8,12.15,12.55,-2.5,-2.)
    installed={'JAW_LOWER':parts['JAW_LOWER']}
    for name,vector in stage_plan(side):
        row=motion_check(name,parts[name],vector,installed,relative=name in ROOT_NAMES)
        row['installed_before']=sorted(installed);result['assembly'].append(row);installed[name]=parts[name]
    # Release paths are geometric only. No actuator/grip-force claim.
    for name,vector in [('JAW_UPPER',(0,0,3.)),('JAW_LOWER',(0,0,-3.))]:
        fixed_release={k:v for k,v in installed.items() if k!=name}
        result['assembly'].append(motion_check('WITHDRAW_'+name,parts[name],vector,fixed_release))
        del installed[name]
    result['straight_installation_needs_held_upper_STOPS_and_part_handling']=True
    result['KEY_insertion_is_coupled_with_STOP_motion_not_an_independent_straight_stage']=True
    bad_static=[x for x in result['static'] if x['common_mm3']>1e-7]
    bad_motion=[x['label'] for x in result['motion'] if x['positive_pairs']]
    bad_assembly=[x['label'] for x in result['assembly'] if x['positive_pairs']]
    bad_contacts=contact_rejections(result['contacts'])
    bad_capture=[x for x in result['retention'] if (x['uplift_mm']==.09 and x['common_mm3']>1e-7) or (x['uplift_mm']==.12 and x['common_mm3']<=1e-7)]
    result['failures']={'static':bad_static,'motion':bad_motion,'assembly':bad_assembly,'contact':bad_contacts,'retention':bad_capture}
    result['passed']=not any(result['failures'].values())
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    if a.output.exists():raise ValueError('new result path required')
    sources={str(Path(f).resolve()):sha(f) for f in (__file__,sum_common_upper_bound.__code__.co_filename)}
    source,parts,inputs=read_parts(a.manifest);results={};fit=[];combined=[]
    inputs.update(sources)
    cavity_path=ROOT/'engineering/phone-layout-study-20261015/native/stepped_A_cavity.step'
    shell_path=cavity_path.with_name('stepped_A_shell.step')
    cavity=n.single(n.cq.importers.importStep(str(cavity_path)).val());shell=n.single(n.cq.importers.importStep(str(shell_path)).val())
    inputs[str(cavity_path)]=sha(cavity_path);inputs[str(shell_path)]=sha(shell_path)
    for side in 'LR':
        old={k:parts[f'{side}_old_{k}'] for k in PARTS};new={k:parts[f'{side}_candidate_{k}'] for k in PARTS}
        results[side]=side_checks(side,old,new)
        positioned=[]
        for name,body in new.items():
            moved=placement(body,side);positioned.append(moved);outside=vol(moved.cut(cavity));collision=n.common(moved,shell)
            fit.append({'side':side,'part':name,'outside_study_cavity_mm3':outside,'shell_common_mm3':collision})
        assembled=parts[side+'_candidate_PLACED_ASSEMBLY'];leaves=n.whole_material(assembled)[0];used=set()
        for body in positioned:
            matches=[i for i,s in enumerate(leaves) if i not in used and abs(s.Volume()-body.Volume())<1e-7 and max(vol(s.cut(body)),vol(body.cut(s)))<=1e-7]
            if len(matches)!=1:raise ValueError('placed assembly leaf not uniquely matched')
            used.add(matches[0])
        combined.append(assembled)
        old_rejection=sum(vol(placement(b,side).cut(cavity)) for b in old.values())
        if old_rejection<=1e-7:raise ValueError('old wide study-placement negative control disappeared')
        results[side]['old_placement_outside_mm3']=old_rejection
        # Whole-motion reservation: e includes the parked PAWL; q includes KEY withdrawal.
        b=n.bounds(side,n.cq.Compound.makeCompound(list(new.values())+[new['PAWL'].translate((-1.1 if side=='L' else 1.1,0,0)),new['KEY'].translate((0,-12.,0))]))
        reserve=placement(n.box(side,*b[0],*b[1],*b[2]),side)
        results[side]['whole_operating_reservation_eqr_mm']=b
        results[side]['whole_operating_reservation_outside_cavity_mm3']=vol(reserve.cut(cavity))
        print('VERIFIED',side,'PASS',results[side]['passed'],'FAILURES',results[side]['failures'],flush=True)
    between=vol(combined[0].intersect(combined[1]))
    if any(sha(p)!=h for p,h in inputs.items()):raise ValueError('native inputs changed during verification')
    if 'thin_mechanism' in sys.modules:raise ValueError('candidate builder imported')
    ok=all(x['passed'] and x['whole_operating_reservation_outside_cavity_mm3']<=1e-7 for x in results.values()) and all(x['outside_study_cavity_mm3']<=1e-7 and x['shell_common_mm3']<=1e-7 for x in fit) and between<=1e-7
    result={'source_commit':source['base_commit'],'verifier_sha256':sha(__file__),'manifest_sha256':sha(a.manifest),'source_input_sha256':inputs,
            'native_STEP_files':96,'individual_parts':92,'complete_placed_assemblies':4,'sides':results,'placement_checks':fit,'two_mechanism_common_mm3':between,
            'passed':ok,'candidate_builder_imported':False,'same_CAD_kernel':True,
            'nominal_study_placement_only':True,'actual_phone_kinematic_registration':False,'mechanism_to_shell_fasteners_not_designed':True,
            'fixture_hold_preload_tool_access_strength_tolerance_and_actual_components_unqualified':True,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('RESULT',ok,flush=True)
    raise SystemExit(0 if ok else 1)


if __name__=='__main__':main()
