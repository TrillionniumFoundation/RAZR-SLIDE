"""Exact complete coordinate arrangements of each full modified source region.

The finite cells are an algebraic decomposition of box unions. They are not
finite sampling of an unknown CAD shape. CAD-to-model equality is a separate
native diagnostic with an explicitly open exact material-identity bridge.
"""
from fractions import Fraction as F
from pathlib import Path
import gzip
import hashlib
import itertools
import json
import time

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def encode(v):
    if isinstance(v,F):return str(v)
    if isinstance(v,dict):return {k:encode(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [encode(x) for x in v]
    return v
def volume(b):
    a,z=b;return (z[0]-a[0])*(z[1]-a[1])*(z[2]-a[2])
def intersection(bs):
    lo=tuple(max(b[0][i] for b in bs) for i in range(3));hi=tuple(min(b[1][i] for b in bs) for i in range(3))
    return (lo,hi) if all(a<z for a,z in zip(lo,hi)) else None
def interval_union(intervals):
    out=[]
    for lo,hi in sorted(intervals):
        if out and lo<=out[-1][1]:out[-1][1]=max(out[-1][1],hi)
        else:out.append([lo,hi])
    return out
def strata(axis):
    out=[]
    for i,p in enumerate(axis):
        out.append({'kind':'point','at':p,'representative':p})
        if i+1<len(axis):out.append({'kind':'open_interval','interval':[p,axis[i+1]],'representative':(p+axis[i+1])/2})
    return out
def section(boxes,axis,t,axes):
    other=[j for j in range(3) if j!=axis];cells=[]
    A=Fu=Fv=Qu=Qv=Qcross=F(0)
    for j,k in itertools.product(range(len(axes[other[0]])-1),range(len(axes[other[1]])-1)):
        u0,u1=axes[other[0]][j:j+2];v0,v1=axes[other[1]][k:k+2]
        owners=[n for n,(lo,hi) in boxes.items() if lo[axis]<=t<=hi[axis] and lo[other[0]]<(u0+u1)/2<hi[other[0]] and lo[other[1]]<(v0+v1)/2<hi[other[1]]]
        if not owners:continue
        ar=(u1-u0)*(v1-v0);fu=(u1*u1-u0*u0)*(v1-v0)/2;fv=(v1*v1-v0*v0)*(u1-u0)/2
        A+=ar;Fu+=fu;Fv+=fv;Qu+=(u1**3-u0**3)*(v1-v0)/3;Qv+=(v1**3-v0**3)*(u1-u0)/3;Qcross+=(u1*u1-u0*u0)*(v1*v1-v0*v0)/4
        cells.append({'transverse_cell_indices':[j,k],'owners':owners,'area_mm2':ar})
    rec={'area_mm2':A,'positive_cells':cells,'transverse_axes':['XYZ'[j] for j in other]}
    if A:
        rec.update(centroid_mm=[Fu/A,Fv/A],central_integral_u_squared_mm4=Qu-Fu*Fu/A,
                   central_integral_v_squared_mm4=Qv-Fv*Fv/A,central_integral_uv_mm4=Qcross-Fu*Fv/A)
    return rec
def partition(boxes,window):
    axes=[sorted({p[i] for b in boxes.values() for p in b}|{p[i] for p in window}) for i in range(3)]
    cells=[];total=F(0)
    for ids in itertools.product(*(range(len(x)-1) for x in axes)):
        lo=tuple(axes[i][j] for i,j in enumerate(ids));hi=tuple(axes[i][j+1] for i,j in enumerate(ids));mid=tuple((a+z)/2 for a,z in zip(lo,hi))
        owners=[name for name,(a,z) in boxes.items() if all(a[i]<mid[i]<z[i] for i in range(3))]
        if owners:
            vol=volume((lo,hi));total+=vol;cells.append({'coordinate_indices':ids,'owners':owners,'volume_mm3':vol})
    inc=F(0)
    for n in range(1,len(boxes)+1):
        for subset in itertools.combinations(boxes,n):
            v=intersection([boxes[k] for k in subset])
            if v:inc+=(-1)**(n+1)*volume(v)
    assert inc==total
    all_sections={};all_chords={}
    for axis in range(3):
        rows=[];integral=F(0)
        for st in strata(axes[axis]):
            sec=section(boxes,axis,st['representative'],axes);rows.append({k:v for k,v in st.items() if k!='representative'}|sec)
            if st['kind']=='open_interval':integral+=sec['area_mm2']*(st['interval'][1]-st['interval'][0])
        assert integral==total
        all_sections['XYZ'[axis]]={'every_axis_stratum':rows,'Cavalieri_volume_mm3':integral,
            'minimum_positive_area_mm2':min(r['area_mm2'] for r in rows if r['area_mm2']>0),
            'includes_artificial_window_sections_not_whole_part_cross_sections':True}
        other=[j for j in range(3) if j!=axis];runs=[];min_all=None;min_internal=None
        for sa,sb in itertools.product(strata(axes[other[0]]),strata(axes[other[1]])):
            vals=[sa['representative'],sb['representative']]
            intervals=[(lo[axis],hi[axis]) for lo,hi in boxes.values() if all(lo[j]<=v<=hi[j] for j,v in zip(other,vals))]
            united=interval_union(intervals)
            if not united:continue
            rec={'transverse_strata':[{k:v for k,v in s.items() if k!='representative'} for s in (sa,sb)],'connected_material_intervals':[]}
            for lo,hi in united:
                length=hi-lo;touch=lo==window[0][axis] or hi==window[1][axis]
                min_all=length if min_all is None else min(min_all,length)
                if not touch:min_internal=length if min_internal is None else min(min_internal,length)
                rec['connected_material_intervals'].append({'lo':lo,'hi':hi,'length_mm':length,'touches_window_boundary':touch})
            runs.append(rec)
        all_chords['XYZ'[axis]]={'every_transverse_stratum':runs,'minimum_positive_directional_chord_mm':min_all,
                               'minimum_when_neither_end_on_window_plane_mm':min_internal,
                               'not_arbitrary_direction_minimum_wall':True}
    joins=[];neighbors={k:set() for k in boxes}
    for left,right in itertools.combinations(boxes,2):
        b=intersection([boxes[left],boxes[right]])
        if b:
            joins.append({'features':[left,right],'complete_overlap_box':b,'volume_mm3':volume(b),
                          'normal_axis_rectangle_areas_mm2':{c:(b[1][(i+1)%3]-b[0][(i+1)%3])*(b[1][(i+2)%3]-b[0][(i+2)%3]) for i,c in enumerate('XYZ')}})
            neighbors[left].add(right);neighbors[right].add(left)
    seen=set();front=[next(iter(boxes))]
    while front:
        node=front.pop()
        if node in seen:continue
        seen.add(node);front.extend(neighbors[node]-seen)
    return {'axes':axes,'occupied_3D_cells':cells,'union_volume_mm3':total,'inclusion_exclusion_volume_mm3':inc,
            'complete_sections':all_sections,'complete_directional_chords':all_chords,
            'positive_volume_feature_overlap_graph':joins,'positive_overlap_graph_connected':len(seen)==len(boxes)}

def main():
    started=time.monotonic();decl=json.loads((HERE/'MODIFIED_REGION_DECLARATIONS.json').read_text())
    outdir=HERE/'exact-sections-attempt1';outdir.mkdir(exist_ok=False);summary=[]
    for mode,convert in [('declared_decimal',lambda v:F(str(v))),('exact_serialized_binary64_coordinates',F)]:
        for name,row in decl['regions'].items():
            boxes={n:tuple(tuple(convert(x) for x in p) for p in b) for n,b in row['boxes'].items()}
            window=tuple(tuple(convert(x) for x in p) for p in row['window'])
            for b in boxes.values():assert all(window[0][i]<=b[0][i]<b[1][i]<=window[1][i] for i in range(3))
            r=partition(boxes,window);r['coordinate_interpretation']=mode;r['region']=name
            if 'full_declared_cutter' in row:
                cutter=tuple(tuple(convert(x) for x in p) for p in row['full_declared_cutter'])
                assert all(window[0][i]<=cutter[0][i]<cutter[1][i]<=window[1][i] for i in range(3))
                assert all(intersection([b,cutter]) is None for b in boxes.values())
                r['entire_declared_cutter_has_zero_model_material']=True
            p=outdir/(name+'__'+mode+'.json.gz')
            with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write((json.dumps(encode(r),separators=(',',':'))+'\n').encode())
            summary.append({'region':name,'coordinate_interpretation':mode,'file':str(p.relative_to(HERE)),'sha256':sha(p),
                            'occupied_3D_cells':len(r['occupied_3D_cells']),'volume_mm3_exact':str(r['union_volume_mm3']),
                            'volume_mm3_display':float(r['union_volume_mm3']),'positive_overlap_graph_connected':r['positive_overlap_graph_connected'],
                            'directional_chord_minima_mm':{axis:float(v['minimum_positive_directional_chord_mm']) for axis,v in r['complete_directional_chords'].items()},
                            'directional_chord_minima_without_window_planes_mm':{axis:float(v['minimum_when_neither_end_on_window_plane_mm']) if v['minimum_when_neither_end_on_window_plane_mm'] is not None else None for axis,v in r['complete_directional_chords'].items()}})
    # Meaningful negative control: two full bodies agree at two axial cuts but
    # a missing middle slab is found by complete coordinate integration.
    full={'block':((F(0),F(0),F(0)),(F(1),F(3),F(1)))}
    split={'left':((F(0),F(0),F(0)),(F(1),F(1),F(1))), 'right':((F(0),F(2),F(0)),(F(1),F(3),F(1)))}
    f=partition(full,full['block']);s=partition(split,full['block'])
    assert f['union_volume_mm3']-s['union_volume_mm3']==1 and not s['positive_overlap_graph_connected']
    control={'finite_end_sections_equal':True,'end_sections_y':[F(1,2),F(5,2)],'undetected_by_two_end_cuts_missing_volume_mm3':F(1),
             'complete_partition_detected_missing_material_and_disconnection':True}
    report={'schema':'razr-r13-complete-modified-region-sections-v1','completed':True,'source_sha256':sha(__file__),
            'declarations_sha256':sha(HERE/'MODIFIED_REGION_DECLARATIONS.json'),'results':summary,
            'negative_control':control,'seconds':time.monotonic()-started,
            'scope':{'all_defined_box_regions_all_coordinate_strata_complete':True,'finite_unknown_shape_probe_method':False,
                     'native_material_identity_bridge_proved':False,'arbitrary_direction_global_minimum_wall':False,
                     'whole_KEY_or_panel_weakest_load_section':False,'structural_strength':False,'full_15D_G2':False}}
    p=outdir/'report.json';p.write_text(json.dumps(encode(report),indent=2)+'\n')
    print(json.dumps({'completed':True,'regions_modes':len(summary),'seconds':report['seconds'],'sha256':sha(p)}))

if __name__=='__main__':main()
