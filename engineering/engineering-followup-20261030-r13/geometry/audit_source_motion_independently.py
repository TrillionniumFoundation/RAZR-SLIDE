"""Independent algebraic verification of the frozen-coefficient real domain."""
from pathlib import Path
from fractions import Fraction as F
import ast,copy,hashlib,itertools,json,math,time
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def exact(x):return F(x['exact'])
def interval(x):return [exact(q) if isinstance(q,dict) else q for q in x]
def constants(p):
    out={}
    for n in ast.parse(Path(p).read_text()).body:
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
            v=n.value
            if isinstance(v,ast.Constant) and type(v.value) in (int,float):out[n.targets[0].id]=v.value
            elif isinstance(v,ast.BinOp) and isinstance(v.op,ast.Div) and isinstance(v.left,ast.Constant) and isinstance(v.right,ast.Constant):out[n.targets[0].id]=v.left.value/v.right.value
    return out
def check(r):
    cam=constants(HERE/'inputs/verify_cam_coupling.py');prod=constants(HERE/'inputs/product_assembly.py')
    K=F(cam['K']);A=F((cam['G']-cam['R'])*math.hypot(1,cam['K'])+prod['TOL']);B=F((cam['G']-cam['R'])*math.sqrt(2)+prod['TOL']);W=A+B
    assert (exact(r['coefficient_K']),exact(r['crosshead_absolute_bound_A_mm']),exact(r['crosshead_minus_KEY_bound_B_mm']),exact(r['output_offset_bound_W_mm']))==(K,A,B,W)
    assert K>0 and K*F(79.75)>=12
    assert exact(r['exact_center_at_full_slide_minus_12_mm'])==K*F(79.75)-12
    assert r['scope']['exact_float64_acceptance_set_equivalence_proved'] is False and r['scope']['actual_physical_allowed_domain_proved'] is False
    branch_count=0
    for key,row in r['complete_profile_branches'].items():
        p=row['original_profile_values'];a,b,c=map(F,p['breakpoints_q_mm']);radius=F(p['pin_radius']);height=F(p['floor_height']);m=F(p['ramp_slope']);pin=F(p['pin_q']);stop=F(p['lower_stop_height']);intercept=exact(row['frozen_source_intercept_exact']);home=height+radius
        assert exact(row['exact_home_height_from_parameter_sum_mm'])==home
        assert len(row['branches'])==4
        qs=[(F(0),a,True,True),(a,b,False,False),(b,c,True,False),(c,F(12),True,True)]
        signs=-1 if key.startswith('L') else 1;all_ranges=[]
        for n,(branch,q) in enumerate(zip(row['branches'],qs)):
            assert tuple(interval(branch['q_interval']))==q
            lo,hi=map(exact,branch['height_delta_from_exact_home_interval_mm'])
            if n==0:assert lo==hi==0
            elif n==1:
                root=lo+radius;assert 0<root and root*root<=radius*radius-(b-a)**2 and hi==0
                assert b-a<radius
                # For all q in this branch, 0<=q-a<=b-a. Squaring gives
                # the complete lower/upper square-root range, without calling sqrt.
                assert exact(row['corner_derivative_magnitude_upper'])*root==b-a
            elif n==2:assert (lo,hi)==(intercept+m*(pin-c)-home,intercept+m*(pin-b)-home)
            else:assert lo==hi==stop-home
            assert lo<=hi;all_ranges.append((lo,hi));move=tuple(sorted((signs*lo,signs*hi)))
            assert tuple(map(exact,branch['STOP_X_translation_interval_mm']))==move
            assert tuple(map(exact,branch['SPRING_lower_X_endpoint_delta_interval_mm']))==(min(F(0),move[0]),min(F(0),move[1]))
            assert tuple(map(exact,branch['SPRING_upper_X_endpoint_delta_interval_mm']))==(max(F(0),move[0]),max(F(0),move[1]))
            branch_count+=1
        assert tuple(map(exact,row['full_q_delta_height_interval_mm']))==(min(a for a,b in all_ranges),max(b for a,b in all_ranges))
        assert row['actual_float64_full_evaluation_error_enclosed'] is False
    pair_count=0;yes=0
    assert len(r['all_25_left_right_merged_branch_pairs'])==25
    pair_labels=set()
    for p in r['all_25_left_right_merged_branch_pairs']:
        label=(p['L_branch'],p['R_branch']);assert label not in pair_labels;pair_labels.add(label)
        L=interval(p['L_interval']);R=interval(p['R_interval']);distance=max(F(0),L[0]-R[1],R[0]-L[1])
        if p['feasible_under_shared_slide_real_projection']:
            lift=p['exact_feasible_lift'];s=exact(lift['slide_mm']);assert 0<=s<=F(79.75)
            vals=[]
            for side,iv in zip('LR',(L,R)):
                v=lift['sides'][side];q,dq,dx=(exact(v[k]) for k in ('q_mm','dq_mm','dx_mm'))
                assert q==K*s+dq and abs(dx)<=A and abs(dx-dq)<=B and 0<=q<=12
                assert (iv[0]<q or iv[0]==q and iv[2]) and (q<iv[1] or q==iv[1] and iv[3]);vals.append(q)
            assert abs(vals[0]-vals[1])<=2*W;yes+=1
        else:assert distance>2*W or distance==2*W and not(L[3] and R[2] if L[1]<=R[0] else R[3] and L[2])
        pair_count+=1
    assert yes==r['feasible_pairs']==17 and pair_count-yes==r['infeasible_pairs']==8
    assert len({a for a,b in pair_labels})==len({b for a,b in pair_labels})==5
    return {'full_profile_branches':branch_count,'complete_branch_pairs':pair_count,'feasible':yes,'infeasible':pair_count-yes}
def main():
    start=time.monotonic();p=HERE/'COMPLETE_SOURCE_MOTION_DOMAIN.json';r=json.loads(p.read_text());counts=check(r);controls=[]
    def rejected(name,bad):
        try:check(bad)
        except AssertionError:controls.append({'control':name,'rejected':True});return
        raise AssertionError(name+' escaped')
    bad=copy.deepcopy(r);bad['output_offset_bound_W_mm']['exact']=str(exact(bad['output_offset_bound_W_mm'])-F(1,2**80));rejected('shrink_full_source_offset_projection_by_2^-80',bad)
    bad=copy.deepcopy(r);bad['all_25_left_right_merged_branch_pairs'].pop();rejected('omit_one_complete_left_right_branch_pair',bad)
    bad=copy.deepcopy(r);bad['scope']['exact_float64_acceptance_set_equivalence_proved']=True;rejected('promote_real_model_to_complete_float64_acceptance',bad)
    report={'schema':'razr-r13-independent-source-motion-domain-arithmetic-review-v1','completed':True,'source_sha256':sha(__file__),
        'source_motion_report_sha256':sha(p),'producer_or_profile_module_imported':False,
        'all_corner_square_root_range_bounds_checked_by_exact_squared_inequalities':True,
        'AST_constants_match_named_source':True,**counts,'negative_controls':controls,'seconds':time.monotonic()-start,
        'scope':{'complete_real_projection_and_branch_range_proof':True,'actual_float64_acceptance_set_proved':False,'uniform_compiled_error_proved':False,
                 'physical_allowed_domain_or_spring_force_proved':False,'full_15D_G2':False}}
    out=HERE/'SOURCE_MOTION_INDEPENDENT_REVIEW.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'completed':True,'counts':counts,'negative_controls':len(controls),'sha256':sha(out)}))
if __name__=='__main__':main()
