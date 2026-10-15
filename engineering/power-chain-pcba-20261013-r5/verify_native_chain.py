"""Read actual PCB/native XML/STEP; do not import the CAD builder."""
from pathlib import Path
import sys,hashlib,json,re,math,csv,xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
from shapely.geometry import Point,box,LineString
from shapely.ops import unary_union
import cadquery as cq
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'strict-motion-audit-20261013'))
from verify_step_payload import full_solid_payload
def parse(src):
 toks=re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+',src);stack=[];cur=[]
 for t in toks:
  if t=='(':stack.append(cur);cur=[]
  elif t==')':old=cur;cur=stack.pop();cur.append(old)
  else:cur.append(json.loads(t) if t.startswith('"') else t)
 assert not stack and len(cur)==1
 return cur[0]
def kids(a,k):return [v for v in a if isinstance(v,list) and v and v[0]==k]
def one(a,k):return kids(a,k)[0]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for stage in ['A1','A2','B1','B2']:
 r=HERE/'modules'/stage;pcb=r/'cut_reference.kicad_pcb';before=sha(pcb)
 b=parse(pcb.read_text());netnames={int(n[1]):n[2] for n in kids(b,'net')};pmap={};iso=[];main=[];padn=0;vias=0
 def addgeom(net,g):
  if not net:return
  (iso if '_ISO_LED_' in net else main).append(g)
 for fp in kids(b,'footprint'):
  ref=next(v[2] for v in kids(fp,'fp_text') if v[1]=='reference');at=one(fp,'at');px,py=map(float,at[1:3])
  for p in kids(fp,'pad'):
   pn=p[1];ns=kids(p,'net');net=ns[0][2] if ns else None;key=(ref,pn)
   assert key not in pmap or pmap[key]==net
   pmap[key]=net;xy=one(p,'at');sz=one(p,'size');x=px+float(xy[1]);y=py+float(xy[2]);sx,sy=map(float,sz[1:3]);padn+=1
   # Rectangular envelopes conservatively include oval/circle pad extents.
   addgeom(net,box(x-sx/2,y-sy/2,x+sx/2,y+sy/2))
 for t in kids(b,'segment'):
  a=list(map(float,one(t,'start')[1:3]));z=list(map(float,one(t,'end')[1:3]));w=float(one(t,'width')[1]);addgeom(netnames[int(one(t,'net')[1])],LineString([a,z]).buffer(w/2))
 for v in kids(b,'via'):
  xy=list(map(float,one(v,'at')[1:3]));radius=float(one(v,'size')[1])/2;addgeom(netnames[int(one(v,'net')[1])],Point(xy).buffer(radius));vias+=1
 gap=unary_union(iso).distance(unary_union(main));assert gap>=5-1e-9,(stage,gap)
 nr=HERE/'native_pocket_v2/modules'/stage
 xm=ET.parse(nr/'native.xml').getroot();xmap={}
 for net in xm.findall('./nets/net'):
  name=net.attrib['name'].removeprefix('/')
  for n in net.findall('node'):xmap[(n.attrib['ref'],n.attrib['pin'])]=name
 facts=json.loads((r/'reference_terminal_map.json').read_text());count=0
 for c in facts['components']:
  for i,net in enumerate(c['nets'],1):
   key=(c['ref'],str(i));assert pmap[key]==net,(stage,key,pmap.get(key),net)
   if net is not None:assert xmap[key]==net,(stage,key,xmap.get(key),net)
   else:assert key not in xmap or xmap[key].startswith('unconnected-')
   count+=1
 assert count==42 and padn==46 and vias==13
 assert pmap['J1','2']==pmap['J2','2']
 assert pmap['J3','1'].endswith('_ISO_LED_P') and pmap['J3','2'].endswith('_ISO_LED_N')
 assert pmap['U2','4']==pmap['U1','5'] and pmap['U2','3']==pmap['U1','1']
 lib=parse((r/'OwnedCut.kicad_sym').read_text())
 official={'TPS259470LRPW':{1:'EN/UVLO',2:'OVLO',3:'AUXOFF',4:'FLT',5:'IN',6:'OUT',7:'DVDT',8:'GND',9:'ILM',10:'ITIMER'},'VOS618A-8X001T':{1:'A',2:'K',3:'E',4:'C'},'PMEG3050EP':{1:'K',2:'A'}}
 for part,expected_pins in official.items():
  symbol=next(z for z in kids(lib,'symbol') if z[1]==part)
  unit=next(z for z in kids(symbol,'symbol') if z[1]==part+'_1_1')
  actual={int(one(pin,'number')[1]):one(pin,'name')[1] for pin in kids(unit,'pin')}
  assert actual==expected_pins,(stage,part,actual)
 final_source=next(z for z in json.loads((HERE/'native_pocket_v2/native_pocket_ERC_v2.json').read_text()) if z.get('stage')==stage and 'frozen_SCH_sha256' in z)
 assert sha(r/'cut_reference.kicad_sch')==final_source['frozen_SCH_sha256'] and sha(r/'OwnedCut.kicad_sym')==final_source['frozen_SYM_sha256']
 erc=json.loads((nr/'ERC.json').read_text());assert all(not s['violations'] for s in erc['sheets'])
 drec=next(x for x in json.loads((HERE/'native_main/native_main_DRC_v1.json').read_text()) if x['stage']==stage)
 assert drec['exit']==0 and all(v==0 for v in json.loads(drec['stdout'])['counts'].values())
 ex=HERE/'native_main/modules'/stage/'exports';step=ex/'BOARD_ONLY.step';stepbefore=sha(step)
 leaves,typ=full_solid_payload(cq.importers.importStep(str(step)).vals());assert len(leaves)==1
 volume=leaves[0].Volume();expected=45*24*1.6-8*math.pi*.375**2*1.6;assert abs(volume-expected)<1e-7
 bb=leaves[0].BoundingBox();assert [bb.xlen,bb.ylen,bb.zlen]==[45.,24.,1.6]
 pos=list(csv.DictReader((ex/'placement.csv').open()));assert len(pos)==12
 gerbers=[p for p in ex.iterdir() if p.suffix in ['.gtl','.gbl','.gtp','.gto','.gts','.gbs','.gm1']];assert len(gerbers)==7
 assert sha(pcb)==before and sha(step)==stepbefore
 rows.append({'stage':stage,'unique_pin_parity':count,'copper_pads':padn,'actual_vias':vias,'conservative_nominal_XY_cross_domain_copper_gap_mm':gap,'domain_gap_is_not_dielectric_or_creepage_qualification':True,'source_PCB_sha256':before,'all_ERC_severities':0,'native_fresh_DRC':json.loads(drec['stdout'])['counts'],'STEP_sha256':stepbefore,'STEP_positive_solids':1,'STEP_shape_types':typ,'STEP_volume_mm3':volume,'STEP_bbox_mm':[bb.xlen,bb.ylen,bb.zlen],'STEP_component_models_absent':True,'STEP_omits_13_via_bores':True,'SMD_positions':len(pos),'Gerber_layers':len(gerbers),'export_SHA256':{str(p.relative_to(ex)):sha(p) for p in ex.rglob('*') if p.is_file()}})
receipt={'schema':'four-cut-native-independent-r5','rows':rows,'unique_pin_parity_total':168,'nominal_copper_isolation_gap_mm':5,'Gerber_layers_total':28,'SMD_positions_total':48,'STEP_positive_solids_total':4,'source_bytes_unchanged':True,'native_physical_board_electrical_tests':False,'PCB_group_is_complete_phone':False,'manufacturing_go':False,'verifier_sha256':sha(Path(__file__))}
(HERE/'independent_chain_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:receipt[k] for k in ['unique_pin_parity_total','nominal_copper_isolation_gap_mm','Gerber_layers_total','SMD_positions_total','STEP_positive_solids_total','manufacturing_go']}))
