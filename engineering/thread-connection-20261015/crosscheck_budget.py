"""Independent interval/corner diagnostics of PR21; all numbers are synthetic.

This is supplemental verification, not another counted suite, physical load,
thread grade, measured torque curve, installation instruction, or CAD change.
"""
from pathlib import Path
import hashlib,itertools,json,math,random,sys
import numpy as np
from scipy.optimize import linprog
R=Path('/home/qian-qi/RAZR-SLIDE-thread-validation-20261015')
O=Path('/tmp/razr-thread-validation-20261015')
sys.path.insert(0,str(R/'integration'))
import frame_thread_budget as m
rng=random.Random(210736)
mat=np.array([[1,0,0,-1,-1,0,0],[1,-1,0,0,-1,-1,0],[0,1,1,-1,0,0,-1],[0,0,1,0,0,-1,-1]],float)
eng=[]
for index in range(200):
    intervals=[]
    for lo,span in ((1,4),(0,5),(.1,1.5),(0,1),(0,1),(0,.7),(0,.7)):
        a=lo+rng.random()*span;intervals.append([a,a+rng.random()*span])
    inp=dict(zip(m.ENGAGEMENT_FIELDS,intervals));result=m.engagement_bounds(inp)
    # Analytic minimum of each affine form over the independent box, not corner enumeration.
    lows=[sum(coef*(pair[0] if coef>=0 else pair[1]) for coef,pair in zip(row,intervals)) for row in mat]
    lower=max(0.,min(lows))
    fit=linprog([0.]*7+[-1.],A_ub=np.column_stack((-mat,np.ones(4))),b_ub=np.zeros(4),bounds=intervals+[(None,None)],method='highs')
    assert fit.success
    upper=max(0.,-fit.fun)
    assert np.allclose(result['complete_form_overlap_mm'],[lower,upper],atol=1e-10,rtol=1e-10)
    eng.append({'inputs':inp,'computed':result['complete_form_overlap_mm'],'independent_affine_minimum_mm':lower,'independent_LP_maximum_mm':upper})
pre=[];tor=[]
for index in range(100):
    P=rng.uniform(0,20);c0=rng.uniform(0,.3);c1=rng.uniform(c0,.7);A=rng.uniform(3,60)
    scatter=rng.uniform(0,.35);loss=rng.uniform(0,3);gain=rng.uniform(0,2);clamp=rng.uniform(.01,2)
    inp={'separating_load_N':[0,P],'load_fraction':[c0,c1],'allowable_total_bolt_force_N':[A,A+1],
         'preload_fractional_scatter':scatter,'preload_loss_N':[0,loss],'preload_gain_N':[0,gain],'required_remaining_clamp_N':[clamp,clamp]}
    res=m.preload_window(inp);lo,hi=res['nominal_preload_lower_N'],res['nominal_preload_upper_N'];cases=[]
    if res['status']=='conditional_window_exists':
        for nominal in (lo,(lo+hi)/2,hi):
            margins=[]
            for fraction,c,l,g,p in itertools.product((-scatter,scatter),(c0,c1),(0,loss),(0,gain),(0,P)):
                remaining=nominal*(1+fraction)-l-(1-c)*p
                total=nominal*(1+fraction)+g+c*p
                margins.append([remaining-clamp,A-total])
            mins=np.min(margins,axis=0).tolist();assert min(mins)>-1e-10
            cases.append({'nominal_preload_N':nominal,'minimum_clamp_and_capacity_margins_N':mins})
    else:assert hi<lo
    pre.append({'inputs':inp,'result':res,'independent_corner_cases':cases})
    flo=rng.uniform(.5,10);fhi=flo+rng.uniform(0,30);klo=rng.uniform(.05,.15);khi=rng.uniform(klo,.4)
    diameter=rng.uniform(.5,2);error=rng.uniform(0,.2);t0=rng.uniform(0,.0005);t1=t0+rng.uniform(0,.0005);ceiling=.02
    result=m.torque_window(m.Span(flo,fhi),m.Span(klo,khi),diameter,error,m.Span(t0,t1),ceiling)
    cs=[]
    if result['status']=='conditional_window_exists':
        for cmd in (result['commanded_torque_lower_Nm'],result['commanded_torque_upper_Nm']):
            values=[]
            for delta,k,prev in itertools.product((-error,error),(klo,khi),(t0,t1)):
                actual=cmd*(1+delta);force=(actual-prev)/(k*diameter/1000)
                assert force>=flo-1e-10 and force<=fhi+1e-10 and actual<=ceiling+1e-12
                values.append({'actual_torque_Nm':actual,'preload_N':force})
            cs.append({'command_Nm':cmd,'forward_corner_values':values})
    else:assert result['commanded_torque_upper_Nm']<result['commanded_torque_lower_Nm']
    tor.append({'required_preload':[flo,fhi],'K':[klo,khi],'diameter_mm':diameter,'tool_error':error,'prevailing':[t0,t1],'result':result,'forward_checks':cs})
# Reverse a design question: maximum permitted tip incomplete zone for full coverage.
# These are the PREVIOUS HYPOTHETICAL dimensions, not newly obtained vendor limits.
scenarios=[]
for nominal in (3.,4.):
    vals=[[nominal-.05,nominal+.05],[1.96,2.04],[.75,.85],[0,.5],[0,.5],[0,.1],[0,.1]]
    inp=dict(zip(m.ENGAGEMENT_FIELDS,vals));base=m.engagement_bounds(inp)
    threshold=vals[0][0]-vals[1][1]-vals[2][1]+vals[6][0]
    tests=[]
    for offset in (-.001,.001):
        p={k:list(v) for k,v in inp.items()};p['male_tip_incomplete_mm']=[0,threshold+offset]
        r=m.engagement_bounds(p)
        assert r['all_female_complete_form_axial_interval_covered']==(offset<0)
        tests.append({'offset_from_threshold_mm':offset,'coverage_margin_mm':r['upper_end_coverage_margin_mm'],'covered':r['all_female_complete_form_axial_interval_covered']})
    scenarios.append({'hypothetical_nominal_length_mm':nominal,'prior_hypothetical_result':base,'hypothetical_tip_incomplete_upper_limit_for_full_coverage_mm':threshold,'neighbor_checks':tests,'actual_supplier_limit_available':False})
actual=m.evaluate(json.loads((R/'integration/frame_thread_actual_inputs.json').read_text()))
assert actual['engagement']['status']==actual['preload']['status']=='undetermined'
r={'source_sha256':hashlib.sha256((R/'integration/frame_thread_budget.py').read_bytes()).hexdigest(),'diagnostic_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
   'independent_engagement_boxes':eng,'preload_corner_boxes':pre,'torque_forward_boxes':tor,'hypothetical_design_thresholds':scenarios,'actual_result':actual,
   'all_diagnostics_passed':True,'included_in_736_test_count':False,'CAD_changed':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
(O/'crosscheck-budget.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'engagement_boxes':len(eng),'preload_boxes':len(pre),'torque_boxes':len(tor),'thresholds':[(s['hypothetical_nominal_length_mm'],s['hypothetical_tip_incomplete_upper_limit_for_full_coverage_mm']) for s in scenarios],'passed':True,'actual_inputs':'undetermined'}),flush=True)
