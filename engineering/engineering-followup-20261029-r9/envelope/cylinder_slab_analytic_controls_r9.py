"""Analytic boundary and degeneracy controls, separate from actual evidence."""
from fractions import Fraction as F
import json
from pathlib import Path
import cylinder_slab_r9 as candidate
import check_cylinder_slab_r9_v2 as independent


def main():
    zero=((F(0),F(0)),)*3
    base={'origin':(F(0),)*3,'X':(F(1),F(0),F(0)),'Y':(F(0),F(1),F(0)),
          'Z':(F(0),F(0),F(1)),'a':(F(1),F(0),F(0)),'b':(F(0),F(1),F(0)),
          'radius':F(1),'determinant':F(1)}
    basis={k:[str(x) for x in v] if isinstance(v,tuple) else str(v) for k,v in base.items() if k in ('origin','X','Y','Z','radius')}
    source={'pieces':[{'kind':'face','index':0}]};models={('face',0):{'type':'GeomAbs_Cylinder','basis':base}}
    records=[]
    def channel(box,end=1):
        return {'unresolved_piece_indices':[0],'channel_exact':[[str(x) for x in a] for a in box],
                'material_side':0,'axis':0,'end':end}
    tests=[('outward_increasing_radial_valid',((F(2),F(4)),(F(-1),F(1)),(F(0),F(1))),1,zero,True),
           ('opposite_channel_rejected',((F(2),F(4)),(F(-1),F(1)),(F(0),F(1))),0,zero,False),
           ('nonmonotone_crossing_axis_retained',((F(-2),F(2)),(F(-1),F(1)),(F(0),F(1))),1,zero,False),
           ('full_shift_changes_monotonicity',((F(2),F(4)),(F(-1),F(1)),(F(0),F(1))),1,((F(3),F(3)),zero[1],zero[2]),False)]
    for name,B,end,D,expected in tests:
        actual=candidate.cylinder_candidate(channel(B,end),source,models,D)
        assert (actual is not None)==expected
        records.append({'name':name,'accepted':actual is not None,'expected':expected,'passed':True})
    unsupported={('face',0):{'type':'GeomAbs_Plane','normal':(F(0),F(1),F(0))}}
    assert candidate.cylinder_candidate(channel(tests[0][1]),source,unsupported,zero) is None
    records.append({'name':'noncylinder_boundary_retained','passed':True})
    assert candidate.slab_candidates(channel(tests[0][1]),source,unsupported,zero)==[]
    records.append({'name':'projection_parallel_to_channel_retained','passed':True})
    B=((F(-1),F(1)),(F(-1),F(1)),(F(0),F(1)))
    for name,D,n,L,expected in [
        ('exact_closed_tangency_has_zero_3D_volume',zero,(F(1),F(0),F(0)),F(1),F(0)),
        ('strict_separation_zero',zero,(F(1),F(0),F(0)),F(2),F(0)),
        ('nonzero_shift_positive_slab',((F(0),F(1,10)),zero[1],zero[2]),(F(1),F(0),F(0)),F(1),F(1,5)),
        ('unnormalized_normal_same_physical_volume',((F(0),F(1,10)),zero[1],zero[2]),(F(7),F(0),F(0)),F(7),F(1,5)),
        ('wide_slab_capped_by_whole_box',zero,(F(1),F(0),F(0)),F(-10),F(4))]:
        cylinder={'basis':base,'source_shift_exact':[[str(x) for x in a] for a in D]}
        slab={'normal_exact':list(map(str,n)),'lower_exact':str(L)}
        result=candidate.combine(B,cylinder,slab,D)
        value=independent.verify_combination(result,B,basis,D,n,L)
        assert value==expected
        records.append({'name':name,'bound_exact':str(value),'expected_exact':str(expected),'passed':True})
    for value in (F(0),F(2),F(1,10**80),F(10**100,3)):
        upper=candidate.root_upper(value)
        assert upper>=0 and upper*upper>=value
        records.append({'name':'outward_rational_root','radicand':str(value),'upper':str(upper),'passed':True})
    try:independent.measure(((F(0),F(0)),(F(0),F(1)),(F(0),F(1))))
    except ValueError as exc:
        assert str(exc)=='positive_original_leaf'
        records.append({'name':'degenerate_positive_cell_rejected','reason':str(exc),'passed':True})
    else:raise AssertionError('degenerate cell admitted')
    p=Path(__file__).with_name('CYLINDER_SLAB_ANALYTIC_CONTROLS.json')
    r={'schema':'razr-r9-cylinder-slab-analytic-controls','completed':True,'controls':records,
       'producer':candidate.common.identity(candidate.__file__),'independent_checker':candidate.common.identity(independent.__file__),
       'source':candidate.common.identity(__file__),'synthetic_controls_not_new_physical_evidence':True}
    p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':len(records)}))


if __name__=='__main__':main()
