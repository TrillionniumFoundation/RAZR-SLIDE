"""Exact conditional overlap bounds from two complete exterior channels.

No native-BREP membership claim. The same boundary/exterior assumptions as the
retained serialized source model apply. Full displacements are never dropped.
"""
from fractions import Fraction as F
from math import isqrt
from pathlib import Path
import sys

R8=Path(__file__).resolve().parents[2]/'engineering-followup-20261029-r8/envelope'
sys.path.insert(0,str(R8))
import source_quadric_r8 as math
import run_original_depth24_r8 as common
import cached_predicates_r9 as cached


def root_upper(value, bits=128):
    if value < 0:
        raise ValueError('negative squared support')
    scale=1<<bits
    integer=isqrt((value.numerator*scale*scale)//value.denominator)
    q=F(integer,scale)
    if q*q<value:q+=F(1,scale)
    assert q>=0 and q*q>=value
    return q


def source_shift(side,D):
    return D if side==0 else ((F(0),F(0)),)*3


def project_piece(piece,model,normal,shift):
    if model and model['type']=='GeomAbs_Plane':
        d=model['record']['local_surface']
        X,Y=math.vec(d['X_exact']),math.vec(d['Y_exact'])
        if math.dot(normal,X)==math.dot(normal,Y)==0:
            value=math.dot(normal,math.vec(d['origin_exact']))
            lo,hi=math.interval_dot(normal,shift)
            return {'method':'exact_plane','lower_exact':str(value+lo),'upper_exact':str(value+hi)}
    if model and model['type']=='GeomAbs_Line':
        t0,t1=model['parameter_interval'];o=math.dot(normal,model['origin']);v=math.dot(normal,model['direction'])
        a,b=sorted((o+v*t0,o+v*t1));lo,hi=math.interval_dot(normal,shift)
        return {'method':'complete_original_line','lower_exact':str(a+lo),'upper_exact':str(b+hi)}
    # The old complete carrier is already displaced. Its whole projection is
    # a safe fallback; no native parameter or trim assertion is introduced.
    lo,hi=math.interval_dot(normal,math.box(piece['box_exact']))
    return {'method':'original_complete_carrier','lower_exact':str(lo),'upper_exact':str(hi)}


def cylinder_candidate(channel,source,models,D):
    unknown=channel['unresolved_piece_indices']
    if not unknown:return None
    first=source['pieces'][unknown[0]];model=models.get((first['kind'],first['index']))
    if not model or model['type']!='GeomAbs_Cylinder':return None
    basis=model['basis']
    for index in unknown:
        piece=source['pieces'][index];other=models.get((piece['kind'],piece['index']))
        if not other or other['type']!='GeomAbs_Cylinder' or other['basis']!=basis:return None
    C=math.box(channel['channel_exact']);shift=source_shift(channel['material_side'],D)
    stationary=tuple((C[k][0]-shift[k][1]-basis['origin'][k],C[k][1]-shift[k][0]-basis['origin'][k]) for k in range(3))
    axis=channel['axis'];a,b=basis['a'],basis['b']
    gradient=tuple(2*(a[axis]*a[k]+b[axis]*b[k]) for k in range(3))
    low,high=math.interval_dot(gradient,stationary)
    direction=1 if channel['end'] else -1
    if (low<0 if direction>0 else high>0):return None
    return {'piece_index':unknown[0],'basis':basis,'derivative_exact':[str(low),str(high)],
            'outward_direction':direction,'source_shift_exact':math.encbox(shift)}


def slab_candidates(channel,source,models,D):
    shift=source_shift(channel['material_side'],D)
    normals=[]
    for index in channel['unresolved_piece_indices']:
        piece=source['pieces'][index];m=models.get((piece['kind'],piece['index']))
        if not m or m['type']!='GeomAbs_Plane':continue
        n=m['normal'];direction=1 if channel['end'] else -1
        if not n[channel['axis']]:continue
        if n[channel['axis']]*direction>0:n=tuple(-v for v in n)
        if n not in normals:normals.append(n)
    candidates=[]
    for n in normals:
        records=[]
        for index in channel['unresolved_piece_indices']:
            piece=source['pieces'][index];model=models.get((piece['kind'],piece['index']))
            records.append(dict(project_piece(piece,model,n,shift),piece_index=index))
        lower=min(F(record['lower_exact']) for record in records)
        candidates.append({'normal_exact':list(map(str,n)),'lower_exact':str(lower),
                           'piece_projections':records,'source_shift_exact':math.encbox(shift)})
    return candidates


def combine(B,cylinder,slab,D):
    basis=cylinder['basis'];n=math.vec(slab['normal_exact']);shift=math.box(cylinder['source_shift_exact'])
    O,X,Y,Z=basis['origin'],basis['X'],basis['Y'],basis['Z']
    dual_w=tuple(x/basis['determinant'] for x in math.cross(X,Y))
    stationary=tuple((B[k][0]-shift[k][1]-O[k],B[k][1]-shift[k][0]-O[k]) for k in range(3))
    axial=math.interval_dot(dual_w,stationary)
    radial_squared=math.dot(n,X)**2+math.dot(n,Y)**2
    radial_upper=root_upper(radial_squared)
    axial_support=max(math.dot(n,Z)*x for x in axial)
    upper=math.dot(n,O)+basis['radius']*radial_upper+axial_support+math.interval_dot(n,shift)[1]
    lower=F(slab['lower_exact']);width=max(F(0),upper-lower)
    axis=max(range(3),key=lambda k:(abs(n[k]),-k))
    area=F(1)
    for k in range(3):
        if k!=axis:area*=B[k][1]-B[k][0]
    volume=min(common.volume(B),width*area/abs(n[axis]))
    return {'bound_exact':str(volume),'slab_lower_exact':str(lower),'cylinder_support_upper_exact':str(upper),
            'support_sqrt_radicand_exact':str(radial_squared),'support_sqrt_upper_exact':str(radial_upper),
            'axial_parameter_interval_exact':list(map(str,axial)),
            'axial_support_upper_exact':str(axial_support),'slice_axis':axis,
            'other_axes_area_exact':str(area),'positive_projection_width_exact':str(width)}


def evaluate(B,sources,models,D,report):
    observations=[];cylinders=[];slabs=[]
    for side,source in enumerate(sources):
        shift=source_shift(side,D)
        for axis in range(3):
            for end in (0,1):
                channel=common.channel_for(B,math.box(source['known_whole_exact']),axis,end)
                codes=[];claims=[];unknown=[]
                report['counts']['channels']+=1
                for index,piece in enumerate(source['pieces']):
                    report['counts']['pieces']+=1
                    if report['counts']['pieces']>12000000:raise RuntimeError('original piece cap')
                    code=cached.old_separate(piece,channel)
                    if code is not None:codes.append(code);continue
                    model=models[side].get((piece['kind'],piece['index']))
                    claim=math.correlate(model,math.box(piece['box_exact']),channel,shift) if model else None
                    if claim is None:codes.append('?');unknown.append(index);continue
                    code={'plane':'P','line':'L','quadric':'Q','empty_closed_intersection':'E'}[claim['code']]
                    claim.update(material_key=source['material_key'],piece_index=index,
                                 original_kind=piece['kind'],original_index=piece['index'],channel_exact=math.encbox(channel))
                    codes.append(code);claims.append(claim);report['counts']['new_'+claim['code']]+=1
                observation={'material_side':side,'axis':axis,'end':end,'channel_exact':math.encbox(channel),
                             'codes':''.join(codes),'new_claims':claims,'unresolved_piece_indices':unknown,
                             'failure':None if not unknown else {'piece_index':unknown[0]}}
                observations.append(observation);index=len(observations)-1
                if not unknown:
                    return {'kind':'complete_exterior_channel','bound_exact':'0',
                            'observations':observations,'selected_channel':index}
                cyl=cylinder_candidate(observation,source,models[side],D)
                if cyl is not None:cylinders.append((index,cyl))
                slabs.extend((index,slab) for slab in slab_candidates(observation,source,models[side],D))
    choices=[]
    for ci,cyl in cylinders:
        for si,slab in slabs:
            if observations[ci]['material_side']==observations[si]['material_side']:continue
            bound=combine(B,cyl,slab,D)
            choices.append((F(bound['bound_exact']),ci,si,cyl,slab,bound))
    if choices:
        value,ci,si,cyl,slab,bound=min(choices,key=lambda x:x[:3])
        if value<common.volume(B):
            return {'kind':'cylinder_slab_upper_bound','bound_exact':str(value),'observations':observations,
                    'cylinder_channel':ci,'slab_channel':si,
                    'cylinder':{k:v for k,v in cyl.items() if k!='basis'},'slab':slab,'combination':bound}
    return {'kind':'unresolved_full_box','bound_exact':str(common.volume(B)),'observations':observations}
