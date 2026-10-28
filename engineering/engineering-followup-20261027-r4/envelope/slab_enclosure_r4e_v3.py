"""Exact outer coverings from complete boundary boxes, without Common.

For a compact S in R^3 and a fixed coordinate x_k=t, the compact section
S_t is contained in the convex hull of its relative boundary. Its relative
boundary is a subset of boundary(S) intersected with that plane. Thus every
point of S in an OPEN coordinate slab is bounded transversely by boundary
boxes meeting that open slab. Cut planes are retained as zero-volume sets.

Three such independently valid slab coverings can be intersected. Their
positive boxes have disjoint interiors in their own partition coordinate,
so triple intersections have disjoint interiors and exact volumes add.
This statement does not prove native boundary semantics or compiled errors.
"""
from fractions import Fraction as F
from itertools import product


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encode_box(box):
    return [[str(lo), str(hi)] for lo, hi in box]


def intersection(a, b):
    return [(max(x[0], y[0]), min(x[1], y[1])) for x, y in zip(a, b)]


def volume(box):
    if any(lo >= hi for lo, hi in box):
        return F(0)
    result = F(1)
    for lo, hi in box:
        result *= hi - lo
    return result


def material_boundary_boxes(source, displacement, inflated=False):
    axes = [(F(1),F(0),F(0)),(F(0),F(1),F(0)),(F(0),F(0),F(1))]
    supports = [source.support(n, detailed=True) for n in axes]
    keys = [(p['kind'],p['index']) for p in supports[0]['pieces']]
    require(all([(p['kind'],p['index']) for p in s['pieces']] == keys for s in supports), 'boundary-box support coverage differs across axes')
    epsilon = source.max_tolerance if inflated else F(0)
    pieces = []
    for i, key in enumerate(keys):
        box = []
        for axis in range(3):
            lo, hi = map(F,supports[axis]['pieces'][i]['support_exact'])
            box.append((lo+displacement[axis][0]-epsilon, hi+displacement[axis][1]+epsilon))
        pieces.append({'kind':key[0],'index':key[1],'box':box})
    require(pieces, 'empty complete boundary cover')
    whole = [(min(p['box'][k][0] for p in pieces), max(p['box'][k][1] for p in pieces)) for k in range(3)]
    return {'pieces':pieces,'whole':whole,'inflation':epsilon}


def coverage_axis(first, second, domain, axis):
    lo, hi = domain[axis]
    require(lo < hi, 'positive partition width required')
    cuts = sorted({lo,hi} | {value for source in (first,second) for p in source['pieces'] for value in p['box'][axis] if lo < value < hi})
    rows = []
    positive = []
    total = F(0)
    for index,(left,right) in enumerate(zip(cuts,cuts[1:])):
        require(left < right, 'strictly ordered partition cuts')
        active = [[i for i,p in enumerate(source['pieces']) if p['box'][axis][0] < right and p['box'][axis][1] > left] for source in (first,second)]
        row = {'index':index,'open_interval_exact':[str(left),str(right)],'active_piece_indices':active}
        if not active[0] or not active[1]:
            row.update(disposition='empty-material-section-boundary-cover',volume_exact='0')
        else:
            hulls = []
            for source,indices in zip((first,second),active):
                hull = [(min(source['pieces'][i]['box'][k][0] for i in indices), max(source['pieces'][i]['box'][k][1] for i in indices)) for k in range(3)]
                hull[axis] = left,right
                hulls.append(hull)
            bound = intersection(intersection(hulls[0],hulls[1]),domain)
            value = volume(bound)
            row.update(material_section_outer_boxes_exact=[encode_box(b) for b in hulls],intersection_outer_box_exact=encode_box(bound),volume_exact=str(value),
                       disposition='positive-volume-exact-box' if value > 0 else 'empty-or-zero-measure-coordinate-intersection')
            if value:
                positive.append({'axis':axis,'slab_index':index,'box':bound})
                total += value
        rows.append(row)
    require(len(rows) == len(cuts)-1 and rows[0]['open_interval_exact'][0] == str(lo) and rows[-1]['open_interval_exact'][1] == str(hi), 'complete partition interval coverage')
    return {'axis':axis,'cuts_exact':[str(x) for x in cuts],'all_open_slab_records':rows,'positive_boxes':positive,'sum_positive_volume_exact':str(total),
            'cut_planes_retained_as_zero_volume_closed_carriers':True,'cut_plane_transverse_bounds_exact':encode_box(domain),
            'cut_plane_carrier_count':len(cuts),'positive_boxes_have_pairwise_disjoint_interiors_by_partition_axis':True}


def validate_cell_topology(box):
    """Independent closed six-face box topology and directed divergence volume."""
    require(all(lo < hi for lo,hi in box), 'positive box required')
    bits = list(product((0,1),repeat=3))
    vertices = [tuple(box[k][bit[k]] for k in range(3)) for bit in bits]
    indices = {bit:i for i,bit in enumerate(bits)}
    def sub(a,b):return tuple(x-y for x,y in zip(a,b))
    def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
    def dot(a,b):return sum((x*y for x,y in zip(a,b)),F(0))
    faces=[]
    for k in range(3):
        remaining=[j for j in range(3) if j!=k]
        for side in (0,1):
            polygon=[]
            for pair in [(0,0),(1,0),(1,1),(0,1)]:
                bit=[0,0,0];bit[k]=side
                for j,value in zip(remaining,pair):bit[j]=value
                polygon.append(indices[tuple(bit)])
            a,b,c=(vertices[i] for i in polygon[:3]);normal=cross(sub(b,a),sub(c,a))
            if normal[k]*(1 if side else -1)<0:polygon.reverse()
            faces.append(polygon)
    triangles=[(f[0],f[1],f[2]) for f in faces]+[(f[0],f[2],f[3]) for f in faces]
    edges={}
    for triangle in triangles:
        for a,b in zip(triangle,(*triangle[1:],triangle[0])):edges[a,b]=edges.get((a,b),0)+1
    require(all(count==1 and edges.get((b,a))==1 for (a,b),count in edges.items()),'selected box oriented edge incidence')
    directed=sum((dot(vertices[i],cross(vertices[j],vertices[k])) for i,j,k in triangles),F(0))/6
    require(directed==volume(box)>0 and 8-len(edges)//2+12==2,'selected box topology or directed volume')
    return directed


def intersect_three_coverings(covers, maximum_pair_checks):
    order=sorted(range(3),key=lambda k:len(covers[k]['positive_boxes']))
    checks=0;cells=[];total=F(0)
    for a in covers[order[0]]['positive_boxes']:
        for b in covers[order[1]]['positive_boxes']:
            checks+=1
            require(checks<=maximum_pair_checks,'registered exact intersection enumeration capacity')
            pair=intersection(a['box'],b['box'])
            if not volume(pair):continue
            for c in covers[order[2]]['positive_boxes']:
                checks+=1
                require(checks<=maximum_pair_checks,'registered exact intersection enumeration capacity')
                box=intersection(pair,c['box']);value=volume(box)
                if value:
                    indices=[None]*3
                    for item in (a,b,c):indices[item['axis']]=item['slab_index']
                    directed=validate_cell_topology(box)
                    require(directed==value,'directed cell volume differs')
                    cells.append({'slab_index_xyz':indices,'box_exact':encode_box(box),'positive_directed_volume_exact':str(value),
                                  'closed_oriented_box_topology_verified':True})
                    total+=value
    keys=[tuple(x['slab_index_xyz']) for x in cells]
    require(len(keys)==len(set(keys)),'duplicate partition cell would double count volume')
    for cell in cells:
        box=[tuple(map(F,x)) for x in cell['box_exact']]
        for axis,index in enumerate(cell['slab_index_xyz']):
            cuts=list(map(F,covers[axis]['cuts_exact']))
            require(cuts[index]<=box[axis][0]<box[axis][1]<=cuts[index+1],'cell escapes unique axis partition interval')
    return {'enumeration_order':order,'actual_exact_box_intersection_checks':checks,'positive_cells':cells,
            'positive_cell_count':len(cells),'sum_directed_volume_exact':str(total),
            'pairwise_disjoint_interiors_proof':'Each cell is contained in its indexed X, Y and Z partition intervals; distinct triples differ in at least one disjoint open interval.',
            'all_partition_boundary_planes_retained':True,'zero_volume_boundary_planes_not_discarded':True}


def build_covering(first,second,maximum_pair_checks):
    domain=intersection(first['whole'],second['whole'])
    source_boxes=lambda source:[{'kind':p['kind'],'index':p['index'],'box_exact':encode_box(p['box'])} for p in source['pieces']]
    proof={'schema':'razr-r4e-compact-material-boundary-slab-cover-v1','first_complete_boundary_boxes':source_boxes(first),
           'second_complete_boundary_boxes':source_boxes(second),'first_whole_support_box_exact':encode_box(first['whole']),
           'second_whole_support_box_exact':encode_box(second['whole']),'global_intersection_box_exact':encode_box(domain),
           'declared_uncertainty_inflation_exact_mm':[str(first['inflation']),str(second['inflation'])],
           'native_Common_called_or_used':False,'bounded_complete_boundary_semantics_remains_a_premise':True}
    if not volume(domain):
        proof.update(axis_covers=[],combined={'positive_cells':[],'positive_cell_count':0,'sum_directed_volume_exact':'0','empty_or_lower_dimensional_global_support_intersection':True})
        return proof
    covers=[coverage_axis(first,second,domain,k) for k in range(3)]
    combined=intersect_three_coverings(covers,maximum_pair_checks)
    # Drop only internal Fraction objects; their exact decimal-free ranges and
    # indices already occur in every immutable open-slab record above.
    proof['axis_covers']=[{k:v for k,v in c.items() if k!='positive_boxes'} for c in covers]
    proof['combined']=combined
    require(F(combined['sum_directed_volume_exact'])<=min(F(c['sum_positive_volume_exact']) for c in covers),'intersection grew beyond a component cover volume')
    return proof


def independent_known_controls():
    """Exact boundary covers of two disjoint boxes with overlapping hulls."""
    def boundary_of_box(ranges):
        pieces=[]
        for axis in range(3):
            for side in (0,1):
                face=list(ranges);face[axis]=(ranges[axis][side],ranges[axis][side])
                pieces.append({'kind':'face','index':len(pieces),'box':face})
        return pieces
    def material(boxes):
        pieces=[]
        for box in boxes:
            for piece in boundary_of_box(box):piece['index']=len(pieces);pieces.append(piece)
        whole=[(min(p['box'][k][0] for p in pieces),max(p['box'][k][1] for p in pieces)) for k in range(3)]
        return {'pieces':pieces,'whole':whole,'inflation':F(0)}
    a=material([[(F(0),F(1)),(F(0),F(1)),(F(0),F(1))],[(F(3),F(4)),(F(0),F(1)),(F(0),F(1))]])
    b=material([[(F(3,2),F(5,2)),(F(0),F(1)),(F(0),F(1))]])
    separated=build_covering(a,b,10000)
    require(F(separated['combined']['sum_directed_volume_exact'])==0,'disconnected components must not be replaced by whole convex hull')
    self_case=build_covering(a,a,10000)
    require(F(self_case['combined']['sum_directed_volume_exact'])==2,'complete self intersection of two unit boxes')
    touching=material([[(F(1),F(3)),(F(0),F(1)),(F(0),F(1))]])
    boundary_case=build_covering(a,touching,10000)
    require(F(boundary_case['combined']['sum_directed_volume_exact'])==0,'measure-zero contact planes must not gain volume')
    thin=F(1,2**51)
    overlap=material([[(F(1)-thin,F(3)+thin),(F(0),F(1)),(F(0),F(1))]])
    thin_case=build_covering(a,overlap,10000)
    require(F(thin_case['combined']['sum_directed_volume_exact'])==2*thin,'both exact nonzero overlap strips must be retained')
    return [{'name':'disconnected-original-whole-hull-overlap','actual':separated,'passed':True},
            {'name':'two-components-whole-self-positive','actual':self_case,'passed':True},
            {'name':'retained-zero-measure-touching-planes','actual':boundary_case,'passed':True},
            {'name':'both-nonzero-2pow-51-overlap-strips','actual':thin_case,'passed':True}]
