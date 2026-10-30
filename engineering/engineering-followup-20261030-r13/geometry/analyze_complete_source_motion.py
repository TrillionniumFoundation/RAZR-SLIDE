"""Full real lifting/projection and every STOP/SPRING source branch.

Frozen binary64 constants interpreted as exact reals are a separate model
from the complete binary64 execution acceptance set. No physical spring law
or force value is invented, and no profile is extrapolated or clamped.
"""
from fractions import Fraction as F
from pathlib import Path
import ast,hashlib,importlib.util,itertools,json,math,sys,time

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def encode(v):
    if isinstance(v,F):return {'exact':str(v),'display':float(v)}
    if isinstance(v,dict):return {k:encode(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [encode(x) for x in v]
    return v
def sqrt_interval(q):
    assert q>=0
    if not q:return F(0),F(0)
    e=q.numerator.bit_length()-q.denominator.bit_length()
    if q<F(2)**e:e-=1
    h=F(2)**(e//2-128);a=q/(h*h);n=math.isqrt(a.numerator//a.denominator);lo=n*h;hi=lo if lo*lo==q else (n+1)*h
    assert lo*lo<=q<=hi*hi
    return lo,hi
def feasible_witness(i,j,W):
    # Each interval is (lower,upper,include_lower,include_upper).
    lo=max(i[0],j[0]);hi=min(i[1],j[1])
    if lo<hi:return (lo+hi)/2,(lo+hi)/2
    if lo==hi and all((t[0]<lo or t[2]) and (lo<t[1] or t[3]) for t in (i,j)):return lo,lo
    if i[1]<=j[0]:
        gap=j[0]-i[1]
        if gap>2*W or (gap==2*W and not (i[3] and j[2])):return None
        eps=min((2*W-gap)/4,(i[1]-i[0])/4,(j[1]-j[0])/4)
        return i[1]-(F(0) if i[3] else eps),j[0]+(F(0) if j[2] else eps)
    w=feasible_witness(j,i,W);return None if w is None else w[::-1]
def inside(q,interval):
    lo,hi,lc,hc=interval;return (lo<q or (lo==q and lc)) and (q<hi or (q==hi and hc))
def lift(qL,qR,K,A,B):
    assert 0<=qL<=12 and 0<=qR<=12 and abs(qL-qR)<=2*(A+B)
    c=(qL+qR)/2;s=c/K;assert 0<=s<=F(79.75)
    out={}
    for side,q in zip('LR',(qL,qR)):
        dq=q-c;dx=min(A,max(-A,dq));assert abs(dx)<=A and abs(dx-dq)<=B and q==K*s+dq
        out[side]={'q_mm':q,'dq_mm':dq,'dx_mm':dx}
    return {'slide_mm':s,'center_q_mm':c,'sides':out}

def main():
    started=time.monotonic();raw=json.loads((HERE/'inputs/SOURCE_ALLOWED_DOMAIN_TEN_STATE_READBACK_V2.json').read_text())
    p=HERE/'inputs/cam_contact_profile.py';spec=importlib.util.spec_from_file_location('r13_frozen_contact_profile',p);mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
    assert sha(p)==raw['profile_source']['sha256']
    K=F(12/79.75);A=F((.425-.4)*math.hypot(1,float(K))+1e-7);B=F((.425-.4)*math.sqrt(2)+1e-7);W=A+B
    records={};original_profiles={}
    for side in 'LR':
        for i,row in enumerate(raw['profiles'][side]):
            vals=row['complete_original_values'];fields=('pin_radius','floor_height','floor_corner_q','ramp_slope','pin_q','lower_stop_height','q_max')
            profile=mod.ContactProfile(**{k:vals[k] for k in fields});original_profiles[side,i]=profile
            assert list(profile.breakpoints)==vals['breakpoints_q_mm']
            a,b,c=map(F,profile.breakpoints);r,h,corner,m,pinq,stop,qmax=(F(vals[k]) for k in fields)
            intercept=F(profile.intercept);h0=h+r;rootlo,roothi=sqrt_interval(r*r-(b-a)**2)
            assert 0<rootlo<=roothi
            ranges=[('plateau',(F(0),a,True,True),(F(0),F(0))),
                    ('rounded_corner',(a,b,False,False),(rootlo-r,F(0))),
                    ('ramp',(b,c,True,False),(intercept+m*(pinq-c)-h0,intercept+m*(pinq-b)-h0)),
                    ('lower_stop',(c,qmax,True,True),(stop-h0,stop-h0))]
            out=[];sign=-1 if side=='L' else 1
            for name,interval,delta in ranges:
                assert delta[0]<=delta[1];move=tuple(sorted(sign*t for t in delta))
                out.append({'branch':name,'q_interval':interval,'height_delta_from_exact_home_interval_mm':delta,
                            'STOP_X_translation_interval_mm':move,
                            'SPRING_lower_X_endpoint_delta_interval_mm':(min(F(0),move[0]),min(F(0),move[1])),
                            'SPRING_upper_X_endpoint_delta_interval_mm':(max(F(0),move[0]),max(F(0),move[1])),
                            'branch_open_endpoint_limits_enclosed':True})
            records[f'{side}_contact_{i}']={'original_profile_values':vals,'frozen_source_intercept_exact':intercept,
                'exact_home_height_from_parameter_sum_mm':h0,'original_binary64_home_height_mm':F(profile.evaluate(0)[0]),
                'binary64_home_rounding_difference_mm':F(profile.evaluate(0)[0])-h0,
                'branches':out,'full_q_delta_height_interval_mm':(min(v[2][0] for v in ranges),max(v[2][1] for v in ranges)),
                'corner_derivative_magnitude_upper':(b-a)/rootlo,'ramp_derivative_exact':-m,
                'plateau_to_corner_limit_delta_exact':F(0),
                'corner_to_ramp_jump_interval_mm':(intercept+m*(pinq-b)-h-rootlo,intercept+m*(pinq-b)-h-roothi)[::-1],
                'ramp_to_lower_stop_jump_exact_mm':stop-(intercept+m*(pinq-c)),
                'frozen_coefficient_real_model_exact_join_continuity_assumed':False,
                'actual_float64_full_evaluation_error_enclosed':False}
    # Complete shared-slide projection. Cmax is slightly above 12 in this
    # exact frozen-coefficient model, making the explicit midpoint lift valid.
    assert K*F(79.75)>=12
    p0=original_profiles['L',0];p1=original_profiles['L',1]
    a,b,c0=map(F,p0.breakpoints);a1,b1,c1=map(F,p1.breakpoints);assert a==a1 and b==b1 and c0<c1
    intervals=[('both_plateau',(F(0),a,True,True)),('both_rounded',(a,b,False,False)),
               ('both_ramp',(b,c0,True,False)),('STOP0_lower_STOP1_ramp',(c0,c1,True,False)),
               ('both_lower_stop',(c1,F(12),True,True))]
    pairs=[]
    for (ni,i),(nj,j) in itertools.product(intervals,repeat=2):
        witness=feasible_witness(i,j,W)
        item={'L_branch':ni,'R_branch':nj,'L_interval':i,'R_interval':j,'feasible_under_shared_slide_real_projection':witness is not None}
        if witness is not None:
            assert inside(witness[0],i) and inside(witness[1],j) and abs(witness[0]-witness[1])<=2*W
            item['exact_feasible_lift']=lift(*witness,K,A,B)
        else:item['separation_distance_infimum_mm']=max(i[0]-j[1],j[0]-i[1],F(0))
        pairs.append(item)
    assert sum(p['feasible_under_shared_slide_real_projection'] for p in pairs)==17
    # Failure controls actually execute the original finite source profile.
    controls=[]
    for side in 'LR':
        for i in (0,1):
            for q in (-.001,12.001):
                try:original_profiles[side,i].evaluate(q)
                except ValueError as e:controls.append({'side':side,'contact':i,'q':q,'rejected':True,'reason':str(e)})
                else:raise AssertionError('original out-of-domain profile unexpectedly accepted')
    assert abs(F(12)-F(0))>2*W
    controls.append({'control':'independent_full_square_corner_qL0_qR12','rejected_by_complete_shared_slide_projection':True,'required_q_difference':F(12),'maximum_permitted_q_difference':2*W})
    source_manifest=json.loads((HERE/'INPUT_MANIFEST.json').read_text())
    report={'schema':'razr-r13-complete-source-motion-real-projection-and-branches-v1','completed':True,'source_sha256':sha(__file__),
        'bound_motion_source_files':{k:v for k,v in source_manifest['files'].items() if k in ('product_assembly.py','product_split_assembly.py','cam_coupling.py','verify_cam_coupling.py','cam_contact_profile.py')},
        'coordinate_model':'exact real arithmetic on frozen binary64 thresholds/coefficients; separate from all binary64 execution acceptance',
        'coefficient_K':K,'crosshead_absolute_bound_A_mm':A,'crosshead_minus_KEY_bound_B_mm':B,'output_offset_bound_W_mm':W,
        'exact_center_at_full_slide_minus_12_mm':K*F(79.75)-12,
        'complete_qL_qR_projection':{'domain':'0<=qL,qR<=12 AND |qL-qR|<=2*(A+B)',
             'necessity':'qL-qR=dqL-dqR, with |dqs|<=A+B from the two inequalities',
             'sufficiency':'center=(qL+qR)/2; slide=center/K; dqs=qs-center; dxs=clamp(dqs,-A,A)',
             'lift_clamp_applies_to_auxiliary_dx_not_to_profile_q':True,
             'independent_qL_qR_full_square_is_only_an_overapproximation':True},
        'fixed_slide_q_interval':'[max(0,K*s-W), min(12,K*s+W)] independently for each side, with each side own feasible dx',
        'complete_profile_branches':records,'two_contact_merged_intervals':intervals,'lower_stop_breakpoint_difference_mm':c1-c0,
        'all_25_left_right_merged_branch_pairs':pairs,'feasible_pairs':17,'infeasible_pairs':8,
        'original_input_domain_constraints':raw['source_defined_independent_input_domain'],
        'telescope_constraints':{'three_joints_per_side':True,'independent_sides':True,
            'real_threshold_lower':F(.1-1e-7),'real_threshold_upper':F(2.9+1e-7),
            'sum_rule':'|j1+j2+j3-8.5+descent|<=binary64(1e-7), subject to actual source evaluation order',
            'equal_allocation_physically_enforced':False,'seating_requires_full_slide':True},
        'negative_controls':controls,
        'spring_representation':{'role_suffix':'SPRING_i_OD_TOL_ENVELOPE','declared_radius_mm':F(.43),
            'shape':'cylinder whose X endpoints extend by min/max of STOP translation; geometric maximum-material envelope',
            'actual_coil_geometry_known':False,'stiffness_free_length_solid_height_wire_diameter_coils_preload_material_and_end_fixity_known':False,
            'restoring_force_is_a_required_unverified_contact_branch_condition':True},
        'seconds':time.monotonic()-started,
        'scope':{'all_real_source_branch_intervals_covered':True,'profile_q_clamped_or_extended':False,
            'exact_float64_acceptance_set_equivalence_proved':False,'uniform_float64_profile_error_bound_proved':False,
            'actual_physical_allowed_domain_proved':False,'spring_force_preload_or_stop_strength_proved':False,
            'current_full_15D_collision_clear':False,'full_G2':False,'G3':False,'G4':False,'G5':False,'manufacturing_go':False}}
    path=HERE/'COMPLETE_SOURCE_MOTION_DOMAIN.json';assert not path.exists();path.write_text(json.dumps(encode(report),indent=2)+'\n')
    print(json.dumps({'completed':True,'feasible_branch_pairs':17,'original_profile_rejections':8,'seconds':report['seconds'],'sha256':sha(path)}))
if __name__=='__main__':main()
