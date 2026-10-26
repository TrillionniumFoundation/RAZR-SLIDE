"""Identify L1 Common's source role from preserved STEP coordinates without CAD.
This is an explicitly limited STEP text/topology observation, not native readback.
"""
from pathlib import Path
import argparse,ast,hashlib,io,itertools,json,math,re,subprocess,tarfile,zipfile
S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'

def points(text):
 records={int(k):v.strip() for k,v in re.findall(r'#(\d+)\s*=\s*(.*?);',text,re.S)}
 result=[]
 for key,s in records.items():
  m=re.fullmatch(r"VERTEX_POINT\s*\(\s*'[^']*'\s*,\s*#(\d+)\s*\)",s)
  if m:
   c=re.fullmatch(r"CARTESIAN_POINT\s*\(\s*'[^']*'\s*,\s*\((.*?)\)\s*\)",records[int(m[1])],re.S)
   if not c:raise ValueError('unrepresented vertex point type')
   p=[float(v.strip()) for v in c[1].split(',')]
   if len(p)!=3 or not all(math.isfinite(v) for v in p):raise ValueError('bad point')
   result.append(p)
 return result,{kind:sum(v.startswith(kind+'(') or v.startswith(kind+' (') for v in records.values()) for kind in ('ADVANCED_FACE','PLANE','LINE','EDGE_CURVE','VERTEX_POINT','CLOSED_SHELL','MANIFOLD_SOLID_BREP')}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repository',type=Path,required=True);ap.add_argument('--l1-archive',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 if a.output.exists():raise ValueError('fresh output required')
 sources={}
 def source(path):
  data=subprocess.check_output(['git','-C',str(a.repository),'show',S4+':'+path]);sources[path]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)};return data
 raw=source('integration/cover_backing.py');tree=ast.parse(raw);posts=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='POSTS' for t in n.targets))
 for n in ('integration/verify_cover_backing.py','integration/product_assembly.py','integration/product_routing_ep5.py','engineering/panel-bearing-web-20261015/structural-analysis/mesh_panel_probe.py'):source(n)
 rows=[]
 with tarfile.open(a.l1_archive) as t:
  zipped=t.extractfile('c2-slide-L1-O72-40210275856-1.zip').read()
  with zipfile.ZipFile(io.BytesIO(zipped)) as z:
   for case,q,side,post_name in ((2,3.4821884705062427,'L','front'),(4,9.160729490168748,'L','rear'),(7,3.4821884705062427,'R','front'),(9,9.160729490168748,'R','rear')):
    rbytes=z.read(f'run/case-{case:03d}/result.json');r=json.loads(rbytes)
    material=next(m for m in r['material_exports'] if m['id']==3);entry=material['exports']['step']
    b=z.read(f'run/case-{case:03d}/'+entry['path']);assert hashlib.sha256(b).hexdigest()==entry['sha256'] and len(b)==entry['bytes']
    pts,types=points(b.decode());assert len(pts)==8 and types['PLANE']==6 and types['EDGE_CURVE']==12
    pts=[[x,y+q,zz] for x,y,zz in pts];axes=[sorted(set(p[i] for p in pts)) for i in range(3)]
    assert all(len(v)==2 for v in axes) and set(map(tuple,pts))==set(itertools.product(*axes))
    sizes=[v[1]-v[0] for v in axes];volume=math.prod(sizes);native=material['original_in_memory_signature']['signed_volume_mm3'];assert abs(volume-native)<1e-10
    _,postlo,posthi=next(p for p in posts if p[0]==post_name);sign=-1 if side=='L' else 1
    posted=[sorted([sign*postlo[0],sign*posthi[0]]),[postlo[1],posthi[1]],[postlo[2],posthi[2]]]
    assert all(posted[i][0]-1e-9<=v<=posted[i][1]+1e-9 for i in range(3) for v in axes[i])
    assert max(abs(axes[0][j]-posted[0][j]) for j in (0,1))<1e-10
    rows.append({'case_id':f'case-{case:03d}','side':side,'panel_source_feature':side+'_BACKING_'+post_name,
      'original_result_sha256':hashlib.sha256(rbytes).hexdigest(),'Common_STEP':entry,'original_native_validity':material['original_in_memory_signature'],
      'STEP_text_entity_counts':types,'Common_vertex_coordinates_transformed_to_factory_frame':pts,
      'eight_vertices_equal_cartesian_box_corners':True,'vertex_coordinate_box_axes_mm':axes,'box_volume_mm3':volume,'original_native_Common_mm3':native,'difference_mm3':volume-native,
      'actual_source_post_axes_mm':posted,'Common_spans_full_post_X_width':True,
      'reference_frame_translation_to_factory':[0,q,0],'CAD_reader_executed':False})
 result={'schema':'razr-L1-panel-KEY-source-feature-identification-v1','functional_source_for_role_mapping':S4,
  'historical_geometry_execution_source':'bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb','source_identities':sources,
  'L1_original_O72_zip_sha256':hashlib.sha256(zipped).hexdigest(),'states':rows,
  'source_feature_function':{'name':'panel monolithic cover backing posts','nominal_OLD_COVER_outward_takeup_mm':.02,'source_contact_plane_abs_X_mm':17.43,'selected_unit_wrench_point_Z_mm':5.5,'unit_wrench_is_geometry_diagnostic_not_load_rating':True},
  'repair_implications':['Removing the complete post X cross-section through Z 4.02..4.38 removes the isolated rectangular post connection between its lower and upper portions; complete panel topology must be checked before claiming any replacement geometry.',
   'The existing normalized panel FE load patches use the same X=+/-17.43 post faces. Their old compliance is not current qualification after a cut or replacement.',
   'A replacement must preserve or explicitly replace cover contact faces and support load path. Simple collision material subtraction is not sufficient evidence.',
   'A named KEY bypass may avoid modifying the backing-post function, but full-domain interference, retained functional contact, actual remaining sections and stiffness still require execution.'],
  'new_native_CAD_executed':False,'complete_factory_reproduction_claimed':False,'material_repair_applied':False,'strength_qualified':False,'candidate_go':False,'manufacturing_go':False}
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'four_source_features_identified':True,'Common_spans_full_source_post_width':True,'native_readback_executed':False,'maximum_volume_reconstruction_error':max(abs(x['difference_mm3']) for x in rows)}))
if __name__=='__main__':main()
