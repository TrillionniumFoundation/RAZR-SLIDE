"""Rational completion corridors and query-wide winding certificates.

No native mutation, point classifier, Boolean, floating epsilon or point sample.
"""
from fractions import Fraction as F
import math

def vec(v):return tuple(map(F,v))
def dot(a,b):return sum((x*y for x,y in zip(a,b)),F(0))
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def sq(a):return dot(a,a)
def ser_box(b):return [[str(a),str(c)] for a,c in b]
def box_points(points):
    points=list(points);assert points
    return tuple((min(p[k] for p in points),max(p[k] for p in points)) for k in range(len(points[0])))
def corners(b):
    assert len(b)==2
    return [(x,y) for x in b[0] for y in b[1]]
def inflate(b,d):return tuple((a-d,c+d) for a,c in b)
def union_boxes(boxes):return tuple((min(b[k][0] for b in boxes),max(b[k][1] for b in boxes)) for k in range(2))
def contains(b,p):return all(a<=x<=c for (a,c),x in zip(b,p))
def contains_box(b,c):return all(a<=x<=y<=d for (a,d),(x,y) in zip(b,c))
def strict_separation(a,b):
    candidates=[(max(x-v,u-y),i,'left' if y<u else 'right') for i,((x,y),(u,v)) in enumerate(zip(a,b))]
    gap,axis,side=max(candidates)
    return {'axis':axis,'corridor_side':side,'strict_gap_exact':str(gap)} if gap>0 else None

def frame(face):
    p=face['plane_recipe'];o,x,y=map(vec,(p['origin'],p['x_direction'],p['y_direction']))
    assert len(o)==len(x)==len(y)==3 and dot(x,x)==dot(y,y)==1 and dot(x,y)==0
    assert all(v in (-1,0,1) for v in x+y),'only actual signed coordinate frames admitted'
    assert x[1]==y[1]==0,'actual guide cap must be an exact Y-constant plane'
    return o,x,y
def project(point,axes):
    o,x,y=axes;v=sub(vec(point),o);return dot(v,x),dot(v,y)
def lift(point,axes):
    o,x,y=axes;u,v=point;return tuple(o[k]+u*x[k]+v*y[k] for k in range(3))
def line_ends(curve):
    o,d=vec(curve['origin_exact']),vec(curve['direction_exact']);a,b=map(F,curve['complete_parameter_interval'])
    assert a<=b and len(o)==len(d)
    return [tuple(x+t*v for x,v in zip(o,d)) for t in (a,b)]
def oriented_ends(curve,orientation):
    ends=line_ends(curve)
    if orientation.endswith('TopAbs_REVERSED'):ends.reverse()
    else:assert orientation.endswith('TopAbs_FORWARD')
    return ends

def build_face(face):
    axes=frame(face);face_tol=F(face['face_tolerance_exact']);assert face_tol>=0
    assert face['wire_count']==len(face['wires'])==2
    assert sum(w['native_is_outer_wire'] for w in face['wires'])==1
    out={'face_index':face['face_index'],'plane_recipe':face['plane_recipe'],'native_face_orientation':face['native_face_orientation'],
         'face_tolerance_exact':str(face_tol),'wires':[],'native_semantics_assumed_proved':False}
    count=0;minimum_consistency_slack=None
    for wire in face['wires']:
        edges=wire['edges'];assert len(edges)==4 and len(wire['joins'])==4
        assert all(j['after_edge']==i and j['to_edge']==(i+1)%4 and j['same_native_vertex_identity'] for i,j in enumerate(wire['joins']))
        pc=[];c3=[];vertex_boxes=[];consistency=[]
        for edge in edges:
            p=oriented_ends(edge['pcurve'],edge['orientation']);c=oriented_ends(edge['curve3d'],edge['orientation'])
            assert edge['pcurve']['complete_parameter_interval']==edge['curve3d']['complete_parameter_interval']
            assert edge['same_parameter_flag'] and edge['same_range_flag'] and not edge['degenerated_flag']
            e_tol=F(edge['edge_tolerance_exact']);assert e_tol>=face_tol
            curve_difference_sq=[sq(sub(lift(u,axes),v)) for u,v in zip(p,c)]
            assert max(curve_difference_sq)<=e_tol*e_tol,'complete affine pcurve/3D curve disagreement exceeds recorded edge tolerance'
            point_records=[];boxes=[]
            assert len(edge['oriented_vertices'])==2
            for j,vertex in enumerate(edge['oriented_vertices']):
                v=vec(vertex['point']);tol=F(vertex['tolerance_exact']);assert tol>=e_tol
                pc_dist=sq(sub(lift(p[j],axes),v));c_dist=sq(sub(c[j],v))
                assert max(pc_dist,c_dist)<=tol*tol,'actual vertex endpoint exceeds recorded tolerance'
                uv=project(v,axes);boxes.append(inflate(tuple((a,a) for a in uv),tol))
                point_records.append({'vertex_point':vertex['point'],'vertex_tolerance_exact':str(tol),
                    'pcurve_lift_distance_squared_exact':str(pc_dist),'curve3d_distance_squared_exact':str(c_dist),
                    'vertex_tolerance_projection_box_exact':ser_box(boxes[-1])})
                slack=tol*tol-max(pc_dist,c_dist);minimum_consistency_slack=slack if minimum_consistency_slack is None else min(minimum_consistency_slack,slack)
            pc.append(p);c3.append([project(v,axes) for v in c]);vertex_boxes.append(boxes)
            consistency.append({'complete_affine_same_parameter_distance_squared_max_exact':str(max(curve_difference_sq)),
                                'recorded_edge_tolerance_squared_exact':str(e_tol*e_tol),'oriented_vertex_checks':point_records})
        joins=[]
        for i in range(4):
            j=(i+1)%4
            assert edges[i]['oriented_vertices'][1]==edges[j]['oriented_vertices'][0]
            b=union_boxes([box_points([pc[i][1],pc[j][0],c3[i][1],c3[j][0]]),vertex_boxes[i][1],vertex_boxes[j][0]])
            assert contains(b,pc[i][1]) and contains(b,pc[j][0])
            joins.append(b)
        corridors=[];erows=[]
        for i,edge in enumerate(edges):
            pad=max(face_tol,F(edge['edge_tolerance_exact']))
            trace=inflate(box_points(pc[i]+c3[i]),pad)
            b=union_boxes([trace,joins[(i-1)%4],joins[i]])
            assert all(contains(b,p) for p in pc[i]+c3[i])
            assert contains_box(b,joins[(i-1)%4]) and contains_box(b,joins[i])
            corridors.append(b)
            erows.append({'edge_index':i,'face_occurrence_index':edge['face_occurrence_index'],'orientation':edge['orientation'],
                'exact_pcurve_endpoints':[list(map(str,v)) for v in pc[i]],'projected_complete_3d_line_endpoints':[list(map(str,v)) for v in c3[i]],
                'full_trace_expansion_exact':str(pad),'whole_edge_corridor_exact':ser_box(b),'consistency':consistency[i]})
        polygon=[p for ends in pc for p in ends]
        twice_area=sum((a[0]*b[1]-a[1]*b[0] for a,b in zip(polygon,polygon[1:]+polygon[:1])),F(0))
        assert twice_area!=0
        out['wires'].append({'wire_index':wire['wire_index'],'native_is_outer_wire':wire['native_is_outer_wire'],
            'native_wire_orientation':wire['orientation'],'native_closed_flag_diagnostic':wire['native_closed_flag'],
            'edges':erows,'joins':[{'after_edge':i,'to_edge':(i+1)%4,'complete_join_rectangle_exact':ser_box(b),
                'original_exact_pcurve_gap':list(map(str,sub(pc[(i+1)%4][0],pc[i][1])))} for i,b in enumerate(joins)],
            'reference_loop_exact':[list(map(str,p)) for p in polygon],
            'reference_signed_twice_area_exact':str(twice_area),
            'arbitrary_continuous_connection_paths_inside_convex_rectangles':True})
        count+=len(edges)
    assert count==8
    out['minimum_vertex_tolerance_squared_slack_exact']=str(minimum_consistency_slack)
    return out

def winding(polygon,p):
    value=0;events=[]
    for i,(a,b) in enumerate(zip(polygon,polygon[1:]+polygon[:1])):
        cross=(b[0]-a[0])*(p[1]-a[1])-(p[0]-a[0])*(b[1]-a[1]);delta=0
        if a[1]<=p[1]<b[1] and cross>0:delta=1
        elif b[1]<=p[1]<a[1] and cross<0:delta=-1
        value+=delta;events.append({'segment':i,'signed_cross_exact':str(cross),'winding_delta':delta})
    return value,events

def query_rectangle(tube,certificate):
    axes=frame(certificate);o,x,y=axes;result=[]
    for n in (x,y):
        lo=sum(min(n[k]*a,n[k]*b) for k,(a,b) in enumerate(tube))-dot(n,o)
        hi=sum(max(n[k]*a,n[k]*b) for k,(a,b) in enumerate(tube))-dot(n,o)
        result.append((lo,hi))
    assert all(a<b for a,b in result)
    return tuple(result)

def exclude_query(tube,certificate):
    q=query_rectangle(tube,certificate);expanded=inflate(q,F(certificate['face_tolerance_exact']))
    center=tuple((a+b)/2 for a,b in expanded);wire_rows=[];total=0
    for wire in certificate['wires']:
        witnesses=[]
        for edge in wire['edges']:
            b=tuple(tuple(map(F,p)) for p in edge['whole_edge_corridor_exact']);separation=strict_separation(b,expanded)
            if separation is None:return None
            witnesses.append({'edge_index':edge['edge_index'],'face_occurrence_index':edge['face_occurrence_index'],**separation})
        polygon=[tuple(map(F,p)) for p in wire['reference_loop_exact']]
        w,events=winding(polygon,center)
        if abs(w)!=1:return None
        total+=w;wire_rows.append({'wire_index':wire['wire_index'],'native_is_outer_wire':wire['native_is_outer_wire'],
            'all_complete_edge_corridors_strictly_outside_query':witnesses,'reference_winding':w,'exact_crossing_events':events})
    if total!=0:return None
    return {'face_index':certificate['face_index'],'method':'all_completion_corridors_disjoint_and_opposite_complete_wire_windings',
            'query_UV_exact':ser_box(q),'face_tolerance_expanded_query_UV_exact':ser_box(expanded),
            'algebraic_reference_point_exact':list(map(str,center)),'wires':wire_rows,'total_winding':total,
            'complete_connected_query_certified':True,'all_admissible_corridor_completions_certified':True,
            'native_filled_domain_membership_proved':False}
