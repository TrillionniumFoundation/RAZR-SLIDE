"""Independent inequalities for original affine patches and coaxial material profiles.

Does not import producer or local_geometry_r11. Bounded source-filling semantics
remain a separate obligation; this verifies all declared representation supports.
"""
from fractions import Fraction as F
from itertools import product

def need(value,message):
    if not value:raise ValueError(message)
def V(x):return tuple(map(F,x))
def dot(x,y):return sum(a*b for a,b in zip(x,y))
def bounds(items):return tuple(tuple(map(F,x)) for x in items)
def project(points,n):
    q=[dot(p,n) for p in points];return min(q),max(q)
def line_points(curve):
    need(curve['type']=='GeomAbs_Line','complete line support required')
    p,d=V(curve['origin_exact']),V(curve['direction_exact']);t=V(curve['range_exact'])
    need(t[0]<=t[1],'complete ordered curve interval')
    return [tuple(a+s*b for a,b in zip(p,d)) for s in t]
def face_domain(face):
    u0,u1,v0,v1=map(F,face['surface']['UV_exact']);uv=[[u0,u1],[v0,v1]]
    for use in face['pcurves']:
        for point in line_points(use['curve']):
            for k in range(2):uv[k]=[min(uv[k][0],point[k]),max(uv[k][1],point[k])]
    return tuple(map(tuple,uv))

def original_motion(case,result):
    spec=result['target']['specification'];co=spec['coefficients'];domain=spec['parameter_intervals']
    need(len(co)==len(domain) and co[0][0]==(1. if case<=15 else -1.) and co[0][1]==float(F(319,48)),'original full q law')
    begin=0 if case<=15 else 1 if case==16 else len(co)
    saved=[];uncertainty=[F(0)]*3
    for coefficients,iv in zip(co[begin:],domain[begin:]):
        native_width=float(iv[1])-float(iv[0]);exact_width=F(float(iv[1]))-F(float(iv[0]))
        v=tuple(F(float(x)*native_width) for x in coefficients);saved.append(v)
        for k,c in enumerate(coefficients):uncertainty[k]+=abs(v[k]-F(float(c))*exact_width)
    return saved,tuple(uncertainty),(F(48,319) if case<=15 else F(-48,319))

def check_source(case,source,result,certificate):
    vectors,error,r=original_motion(case,result)
    need(F(certificate['ratio_exact'])==r,'original q-perpendicular coordinate')
    need([V(v) for v in certificate['remaining_vectors_exact']]==vectors,'complete original remaining displacement vectors')
    need(V(certificate['coefficient_domain_error_halfwidth_exact'])==error,'complete exact coefficient/domain residual retained')
    need(certificate['whole_source_face_edge_vertex_counts']=={p:len(source[p]) for p in ('faces','edges','vertices')},'whole source boundary census')
    tol=max(F(row['tolerance_exact']) for plural in ('faces','edges','vertices') for row in source[plural])
    need(F(certificate['native_tolerance_pad_exact'])==tol,'original native tolerance preserved as carrier padding')
    normals=((F(1),-r,F(0)),(F(0),F(1),F(0)),(F(0),F(0),F(1)))
    points=[]
    for face in source['faces']:
        s=face['surface'];need(s['type']=='GeomAbs_Plane' or s.get('affine_line_basis'),'complete affine face source type')
        uv=face_domain(face);o,X,Y=V(s['origin_exact']),V(s['X_exact']),V(s['Y_exact'])
        points.extend(tuple(o[k]+u*X[k]+v*Y[k] for k in range(3)) for u,v in product(*uv))
    for edge in source['edges']:points.extend(line_points(edge['curve']))
    points.extend(V(row['point_exact']) for row in source['vertices'])
    need(points,'nonempty whole source')
    claimed=bounds(certificate['support_exact'])
    for axis,n in enumerate(normals):
        lo,hi=project(points,n)
        for v in vectors:
            x=dot(v,n);lo+=min(0,x);hi+=max(0,x)
        delta=tol*sum(map(abs,n))+sum(abs(n[k])*error[k] for k in range(3))
        need(claimed[axis][0]<=lo-delta<=hi+delta<=claimed[axis][1],'entire affine patch/edge/vertex and continuous D support included')
    return claimed

def circular_support(curve,center,R):
    need(V(curve['origin_exact'])[:2]==center,'same original fixed coaxial axis')
    X,Y=V(curve['X_exact']),V(curve['Y_exact']);need(X[2]==Y[2]==0,'horizontal circular basis')
    radius=F(curve['radius_exact']);need(radius>=0 and R>=0,'nonnegative radii')
    a=R*R-radius*radius*dot(X,X);d=R*R-radius*radius*dot(Y,Y);b=-radius*radius*dot(X,Y)
    need(a>=0 and d>=0 and a*d-b*b>=0,'exact PSD circular radius support for every angle')

def check_fixed(fixed,certificate):
    C=V(certificate['center_xy_exact']);need(len(C)==2,'complete fixed axis center')
    profiles=certificate['faces'];need(len(profiles)==len(fixed['faces']),'all fixed faces retained')
    edge={e['index']:e for e in fixed['edges']};vertex={v['index']:v for v in fixed['vertices']}
    for face,row in zip(fixed['faces'],profiles):
        need(row['face_index']==face['index'],'full original fixed face order')
        R=F(row['radius_upper_exact']);need(F(row['radius_square_upper_exact'])==R*R,'exact radial square')
        tol=max([F(face['tolerance_exact'])]+[F(edge[i]['tolerance_exact']) for i in face['edge_indices']]+[F(vertex[i]['tolerance_exact']) for i in face['vertex_indices']])
        need(F(row['tolerance_exact'])==tol and R>=2*tol,'all recorded fixed tolerances retained')
        inner_radius=R-2*tol;support_z=[];s=face['surface']
        if s['type']=='GeomAbs_Cylinder':
            axis=V(s['axis_exact']);need(axis[:2]==(0,0) and abs(axis[2])==1,'actual fixed cylinder vertical')
            circular_support(s,C,inner_radius);uv=face_domain(face)
            support_z.extend(F(s['origin_exact'][2])+axis[2]*v for v in uv[1])
        else:
            need(s['type']=='GeomAbs_Plane' and F(s['X_exact'][2])==F(s['Y_exact'][2])==0,'complete horizontal fixed cap')
            support_z.append(F(s['origin_exact'][2]))
        circle_count=0
        for ei in set(face['edge_indices']):
            q=edge[ei]['curve']
            if q['type']=='GeomAbs_Line':support_z.extend(p[2] for p in line_points(q))
            else:
                need(q['type']=='GeomAbs_Circle','all spatial fixed cap edges represented')
                circular_support(q,C,inner_radius);support_z.append(F(q['origin_exact'][2]));circle_count+=1
        need(circle_count>0,'bounded radial cap/cylinder boundary circles retained')
        support_z.extend(F(vertex[i]['point_exact'][2]) for i in face['vertex_indices'])
        z0,z1=map(F,row['z_exact']);need(z0<=min(support_z)-tol<=max(support_z)+tol<=z1,'complete trim/curve/vertex axial support')
    return True

def verify_tree(row,result):
    case=int(row['case_id'][-3:]);support=check_source(case,row['source_inventory'],result,row['source_support'])
    check_fixed(row['fixed_inventory'],row['fixed_profile']);r=F(row['source_support']['ratio_exact'])
    nodes=row['nodes'];seen=set();pending=[(0,support[1],0)];leaves=[];splits=0
    while pending:
        index,Y,depth=pending.pop();need(type(index) is int and 0<=index<len(nodes) and index not in seen,'complete unique cover tree')
        seen.add(index);node=nodes[index];need(node['id']==index and node['depth']==depth<=24,'original depth bound')
        need(V(node['y_exact'])==Y,'full reconstructed Y subdomain')
        B=bounds(node['box_exact']);need(all(a<b for a,b in B),'positive complete native carrier coordinates')
        X=(min(s+r*y for s,y in product(support[0],Y)),max(s+r*y for s,y in product(support[0],Y)))
        true=(X,Y,support[2]);need(all(ca<=a<=b<=cb for (a,b),(ca,cb) in zip(true,B)),'complete swept source strip subset of carrier')
        need(all((v*65536).denominator==1 and F(float(v))==v for interval in B for v in interval),'exact nondegenerate world dyadic carrier grid')
        if node['kind']=='split':
            cut=F(node['cut_exact']);need(cut==(Y[0]+Y[1])/2 and len(node['children'])==2 and node['children'][0]!=node['children'][1],'complete original midpoint partition')
            pending.extend([(node['children'][1],(cut,Y[1]),depth+1),(node['children'][0],(Y[0],cut),depth+1)]);splits+=1
        else:
            need(node['kind']=='leaf','no unevaluated node may pass')
            active=[p for p in row['fixed_profile']['faces'] if F(p['z_exact'][1])>=B[2][0] and F(p['z_exact'][0])<=B[2][1]]
            sep=node['separation'];need(sep['strict'] and sep['active_faces']==[p['face_index'] for p in active],'all active fixed faces included')
            if active:
                C=V(row['fixed_profile']['center_xy_exact']);ds=sum(max(a-c,c-b,F(0))**2 for (a,b),c in zip(B[:2],C))
                radius=max(F(p['radius_square_upper_exact']) for p in active)
                need(F(sep['squared_axis_distance_exact'])==ds and F(sep['radius_square_upper_exact'])==radius and ds>radius,'strict exact whole-profile radial separation')
            else:need(sep['squared_axis_distance_exact'] is None and sep['radius_square_upper_exact'] is None,'empty axial support explicit')
            leaves.append(index)
    need(len(seen)==len(nodes),'no hidden or unreachable cover records')
    need({p['node_id'] for p in row['native_leaves']}==set(leaves) and len(row['native_leaves'])==len(leaves),'all complete native carrier leaves')
    return {'roots':1,'splits':splits,'native_carriers':len(leaves),'maximum_depth':max(n['depth'] for n in nodes),
            'complete_original_representation_and_remaining_domain_included':True,'strict_profile_separation_verified':True,
            'original_native_source_filling_formally_proved':False}
