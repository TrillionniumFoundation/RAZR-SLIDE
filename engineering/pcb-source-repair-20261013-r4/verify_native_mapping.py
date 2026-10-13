"""Read the real native XML and PCB payload independently of their builder."""
import hashlib,json,re,sys,xml.etree.ElementTree as ET
from pathlib import Path
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent

def sexpr(src):
 toks=re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+',src); stack=[];cur=[]
 for t in toks:
  if t=='(':stack.append(cur);cur=[]
  elif t==')':old=cur;cur=stack.pop();cur.append(old)
  else:cur.append(json.loads(t) if t.startswith('"') else t)
 assert not stack and len(cur)==1
 return cur[0]
def kids(a,k):return [v for v in a if isinstance(v,list) and v and v[0]==k]
def one(a,k):return kids(a,k)[0]
board=sexpr((root/'cut_reference.kicad_pcb').read_text())
bmap={};duplicates=0
for fp in kids(board,'footprint'):
 ref=next(v[2] for v in kids(fp,'fp_text') if v[1]=='reference')
 for pad in kids(fp,'pad'):
  pn=pad[1];net=kids(pad,'net');net=net[0][2] if net else None
  key=(ref,pn)
  if key in bmap:assert bmap[key]==net;duplicates+=1
  bmap[key]=net
xml=ET.parse(root/'native.xml').getroot();xmap={}
for net in xml.findall('./nets/net'):
 name=net.attrib['name'].removeprefix('/')
 for node in net.findall('node'):xmap[(node.attrib['ref'],node.attrib['pin'])]=name
facts=json.loads((root/'reference_terminal_map.json').read_text())
count=0
for c in facts['components']:
 for i,net in enumerate(c['nets'],1):
  key=(c['ref'],str(i));assert key in bmap,(key,'missing PCB pad')
  assert bmap[key]==net,(key,'PCB',bmap[key],net)
  if net is not None:assert xmap[key]==net,(key,'XML',xmap.get(key),net)
  else:assert key not in xmap or xmap[key].startswith('unconnected-'),(key,xmap.get(key))
  count+=1
# Official exact-variant pin functions, independently transcribed from table 5-1.
pin_functions={1:'EN/UVLO',2:'OVLO',3:'AUXOFF',4:'FLT',5:'IN',6:'OUT',7:'DVDT',8:'GND',9:'ILM',10:'ITIMER'}
lib=sexpr((root/'OwnedCut.kicad_sym').read_text());u=next(s for s in kids(lib,'symbol') if s[1]=='TPS259470LRPW')
pins=kids(next(s for s in kids(u,'symbol') if s[1]=='TPS259470LRPW_1_1'),'pin')
for p in pins:
 n=int(one(p,'number')[1]);assert one(p,'name')[1]==pin_functions[n]
 if n in (3,4):assert p[1]=='open_collector'
assert len(pins)==10 and count==30
erc=json.loads((root/'ERC.json').read_text())
assert all(not sheet.get('violations') for sheet in erc.get('sheets',[])), 'ERC actual violations'
receipt={'native_XML_PCB_unique_pin_matches':count,'extra_same_number_L_land_rectangles':duplicates,'official_exact_variant_pin_functions_matched':10,'AUXOFF_and_FLT_types':'open_collector','raw_CELLP_CELLN_not_present':not any('CELL' in n for n in bmap.values() if n),'phone_complete_PCB':False,'manufacturing_go':False,'frozen_inputs':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ['cut_reference.kicad_sch','cut_reference.kicad_pcb','OwnedCut.kicad_sym','reference_terminal_map.json']}}
(root/'independent_native_mapping.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
