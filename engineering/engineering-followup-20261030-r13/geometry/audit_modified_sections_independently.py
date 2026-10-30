"""Recompute section integrals by inclusion-exclusion, without producer imports."""
from pathlib import Path
from fractions import Fraction as F
import copy,gzip,hashlib,itertools,json,math,time
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    with gzip.open(p,'rt') as f:return json.load(f)
def rf(v):return tuple(tuple(map(F,p)) for p in v)
def moments_2d(rectangles):
    # Sum exact rectangle integrals by the independent inclusion-exclusion law.
    vals=[F(0)]*6
    for number in range(1,len(rectangles)+1):
        for subset in itertools.combinations(rectangles,number):
            u0=max(r[0][0] for r in subset);u1=min(r[1][0] for r in subset)
            v0=max(r[0][1] for r in subset);v1=min(r[1][1] for r in subset)
            if u0>=u1 or v0>=v1:continue
            term=((u1-u0)*(v1-v0),(u1*u1-u0*u0)*(v1-v0)/2,(v1*v1-v0*v0)*(u1-u0)/2,
                  (u1**3-u0**3)*(v1-v0)/3,(v1**3-v0**3)*(u1-u0)/3,(u1*u1-u0*u0)*(v1*v1-v0*v0)/4)
            vals=[a+(-1)**(number+1)*b for a,b in zip(vals,term)]
    return vals
def source_strata(axis):
    rows=[]
    for i,t in enumerate(axis):
        rows.append(('point',t,t,t))
        if i+1<len(axis):rows.append(('open_interval',t,axis[i+1],(t+axis[i+1])/2))
    return rows
def audit(decl,data,conv):
    boxes={n:tuple(tuple(conv(x) for x in p) for p in b) for n,b in decl['boxes'].items()};window=tuple(tuple(conv(x) for x in p) for p in decl['window'])
    axes=[sorted({p[i] for b in boxes.values() for p in b}|{p[i] for p in window}) for i in range(3)]
    assert [list(map(F,p)) for p in data['axes']]==axes
    # Whole-volume accounting independently of the stored positive cell list.
    volume=F(0)
    for count in range(1,len(boxes)+1):
        for subset in itertools.combinations(boxes.values(),count):
            lengths=[max(F(0),min(b[1][i] for b in subset)-max(b[0][i] for b in subset)) for i in range(3)]
            volume+=(-1)**(count+1)*math.prod(lengths)
    assert F(data['union_volume_mm3'])==F(data['inclusion_exclusion_volume_mm3'])==volume
    expected_cells={}
    for ids in itertools.product(*(range(len(a)-1) for a in axes)):
        mid=tuple((axes[i][j]+axes[i][j+1])/2 for i,j in enumerate(ids));owners=[name for name,(lo,hi) in boxes.items() if all(lo[i]<mid[i]<hi[i] for i in range(3))]
        if owners:expected_cells[ids]=(owners,math.prod(axes[i][j+1]-axes[i][j] for i,j in enumerate(ids)))
    cells=data['occupied_3D_cells'];assert len(cells)==len(expected_cells),'missing positive coordinate cell'
    seen=set()
    for c in cells:
        ids=tuple(c['coordinate_indices']);assert ids not in seen;seen.add(ids)
        owners,v=expected_cells[ids];assert owners==c['owners'] and F(c['volume_mm3'])==v
    count_sections=0;count_chords=0
    for i,axis in enumerate('XYZ'):
        other=[j for j in range(3) if i!=j];rows=data['complete_sections'][axis]['every_axis_stratum'];sts=source_strata(axes[i]);assert len(rows)==len(sts),'incomplete axis strata'
        integral=F(0)
        for r,(kind,lo,hi,t) in zip(rows,sts):
            assert r['kind']==kind
            assert (F(r['at'])==t if kind=='point' else tuple(map(F,r['interval']))==(lo,hi))
            rectangles=[(tuple(b[0][j] for j in other),tuple(b[1][j] for j in other)) for b in boxes.values() if b[0][i]<=t<=b[1][i]]
            A,Pu,Pv,Qu,Qv,Quv=moments_2d(rectangles)
            assert A==F(r['area_mm2']),'section area understated or overstated'
            if A:
                assert tuple(map(F,r['centroid_mm']))==(Pu/A,Pv/A)
                assert F(r['central_integral_u_squared_mm4'])==Qu-Pu*Pu/A
                assert F(r['central_integral_v_squared_mm4'])==Qv-Pv*Pv/A
                assert F(r['central_integral_uv_mm4'])==Quv-Pu*Pv/A
            if kind=='open_interval':integral+=A*(hi-lo)
            count_sections+=1
        assert integral==volume==F(data['complete_sections'][axis]['Cavalieri_volume_mm3'])
        chordrows=data['complete_directional_chords'][axis]['every_transverse_stratum'];expected=[]
        for sa,sb in itertools.product(source_strata(axes[other[0]]),source_strata(axes[other[1]])):
            transversal=[sa[3],sb[3]];segments=[];start=None
            for k,(a,b) in enumerate(zip(axes[i],axes[i][1:])):
                mid=(a+b)/2
                yes=any(box[0][i]<mid<box[1][i] and all(box[0][j]<=t<=box[1][j] for j,t in zip(other,transversal)) for box in boxes.values())
                if yes and start is None:start=a
                if start is not None and (not yes or k==len(axes[i])-2):
                    end=a if not yes else b;segments.append((start,end));start=None
            if segments:expected.append((sa,sb,segments))
        assert len(expected)==len(chordrows),'incomplete transverse strata'
        all_lengths=[];internal=[]
        for row,(sa,sb,segs) in zip(chordrows,expected):
            assert len(row['connected_material_intervals'])==len(segs)
            for r,(lo,hi) in zip(row['connected_material_intervals'],segs):
                assert (F(r['lo']),F(r['hi']),F(r['length_mm']))==(lo,hi,hi-lo)
                touch=lo==window[0][i] or hi==window[1][i];assert r['touches_window_boundary']==touch
                all_lengths.append(hi-lo)
                if not touch:internal.append(hi-lo)
            count_chords+=1
        q=data['complete_directional_chords'][axis]
        assert F(q['minimum_positive_directional_chord_mm'])==min(all_lengths)
        assert (None if q['minimum_when_neither_end_on_window_plane_mm'] is None else F(q['minimum_when_neither_end_on_window_plane_mm']))==(min(internal) if internal else None)
        assert q['not_arbitrary_direction_minimum_wall'] is True
    # Every positive-volume feature overlap is present; no graph edge is inferred from mere point contact.
    joins={}
    for left,right in itertools.combinations(boxes,2):
        lo=tuple(max(boxes[left][0][i],boxes[right][0][i]) for i in range(3));hi=tuple(min(boxes[left][1][i],boxes[right][1][i]) for i in range(3))
        if all(a<b for a,b in zip(lo,hi)):joins[(left,right)]=(lo,hi)
    assert len(joins)==len(data['positive_volume_feature_overlap_graph'])
    for r in data['positive_volume_feature_overlap_graph']:
        lo,hi=joins[tuple(r['features'])];assert rf(r['complete_overlap_box'])==(lo,hi)
        assert F(r['volume_mm3'])==math.prod(b-a for a,b in zip(lo,hi))
    return {'volume_exact_mm3':str(volume),'complete_axis_strata':count_sections,'complete_transverse_chord_strata':count_chords,'complete_positive_cells':len(cells),'positive_feature_joins':len(joins)}
def rejected(label,fn):
    try:fn()
    except (AssertionError,KeyError,IndexError) as e:return {'control':label,'rejected':True,'reason':str(e)}
    raise AssertionError(label+' escaped')
def main():
    start=time.monotonic();decl=json.loads((HERE/'MODIFIED_REGION_DECLARATIONS.json').read_text());producer=json.loads((HERE/'exact-sections-attempt1/report.json').read_text());rows=[]
    for item in producer['results']:
        p=HERE/item['file'];assert sha(p)==item['sha256'];data=load(p);conv=(lambda v:F(str(v))) if item['coordinate_interpretation']=='declared_decimal' else F
        rows.append({'region':item['region'],'coordinate_interpretation':item['coordinate_interpretation'],'ledger_sha256':sha(p),**audit(decl['regions'][item['region']],data,conv)})
    controls=[];key='R_K1_entire_cut_loop_and_two_old_web_junctions';data=load(HERE/'exact-sections-attempt1'/(key+'__declared_decimal.json.gz'));conv=lambda v:F(str(v))
    bad=copy.deepcopy(data);bad['occupied_3D_cells'].pop();controls.append(rejected('omit_one_positive_source_coordinate_cell',lambda:audit(decl['regions'][key],bad,conv)))
    bad=copy.deepcopy(data);row=next(x for x in bad['complete_sections']['Y']['every_axis_stratum'] if F(x['area_mm2'])>0);row['area_mm2']=str(F(row['area_mm2'])-F(1,2**80));controls.append(rejected('understate_positive_section_by_2^-80',lambda:audit(decl['regions'][key],bad,conv)))
    bad=copy.deepcopy(data);bad['complete_sections']['Y']['every_axis_stratum'].pop();controls.append(rejected('omit_complete_axial_interval_or_plane',lambda:audit(decl['regions'][key],bad,conv)))
    bad=copy.deepcopy(data);bad['positive_volume_feature_overlap_graph'].pop();controls.append(rejected('omit_load_route_feature_join',lambda:audit(decl['regions'][key],bad,conv)))
    # Explicitly recompute the producer's finite-cut counterexample, including both claimed cuts.
    A=[((F(0),F(0)),(F(1),F(1)))]
    assert moments_2d(A)[0]==1
    full=[(F(0),F(3))];split=[(F(0),F(1)),(F(2),F(3))]
    endpoints=[]
    for y in (F(1,2),F(5,2)):
        v1=moments_2d(A if any(lo<=y<=hi for lo,hi in full) else [])[0];v2=moments_2d(A if any(lo<=y<=hi for lo,hi in split) else [])[0];assert v1==v2==1;endpoints.append({'y':str(y),'both_areas':str(v1)})
    assert sum(hi-lo for lo,hi in full)-sum(hi-lo for lo,hi in split)==1
    native=[]
    for fmt in ('brep','step'):
        p=HERE/('native-'+fmt+'-attempt1/report.json');r=json.loads(p.read_text());assert r['completed'] and not r['failures'] and set(r['regions'])==set(decl['regions'])
        assert r['native_zero_difference_is_not_exact_set_identity'] and r['global_minimum_wall'] is False
        for n,d in r['regions'].items():
            for k in ('actual_crop','expected_union','actual_minus_expected','expected_minus_actual'):
                f=HERE/d[k]['file'];assert sha(f)==d[k]['sha256'] and f.stat().st_size==d[k]['bytes']
            assert d['actual_minus_expected']['signed_volume_mm3']==d['expected_minus_actual']['signed_volume_mm3']==0
        native.append({'format':fmt,'report_sha256':sha(p),'all_six_regions_original_gate_pass':True})
    result={'schema':'razr-r13-independent-complete-section-arithmetic-review-v1','completed':True,'source_sha256':sha(__file__),
            'producer_source_imported':False,'section_method':'inclusion-exclusion of exact rectangular moment integrals',
            'results':rows,'negative_controls':controls,'finite_cut_counterexample':{'two_actual_cut_checks':endpoints,'missing_volume_exact_mm3':'1'},
            'native_original_raw_members_rehashed':native,'seconds':time.monotonic()-start,
            'scope':{'complete_declared_region_model_checked':True,'actual_native_filling_identity_proved':False,'whole_part_global_minimum_wall':False,
                     'physical_material_or_strength_qualification':False,'full_15D_G2':False}}
    p=HERE/'MODIFIED_SECTIONS_INDEPENDENT_REVIEW.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'completed':True,'region_models':len(rows),'negative_controls':len(controls),'seconds':result['seconds'],'sha256':sha(p)}))
if __name__=='__main__':main()
