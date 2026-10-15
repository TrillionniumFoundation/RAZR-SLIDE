"""Export inspectable, non-OEM R21 STEP assemblies and YZ motion sections."""
from __future__ import annotations
import cadquery as cq, hashlib,json,sys,html
from pathlib import Path
import ezdxf
from r21_geom import (ROOT,P,STOW_Y,STOW_PAD_Z,OPEN_PAD_Z,run_dock_integration,
  r17_assembly,local_assembly)
from r17_model import draw_screen,draw_internal_fpc
CAD=ROOT/'cad';CAD.mkdir(exist_ok=True)
VIEWER=ROOT/'viewer';VIEWER.mkdir(exist_ok=True)

POSES=[('01_STOWED_RETRACTED',0.,0.,0.,None),('02_50PCT_SLIDE',39.875,0.,0.,None),
 ('03_Y_COMPLETE_NOT_DOCKED',P.travel,0.,0.,None),('04_Z_HALF_DOCKING',P.travel,P.z_travel/2,0.,None),
 ('05_DOCKED_BRIDGE_EXTENDED',P.travel,P.z_travel,1.,None),
 ('06_STOW_CONTACT_FORCED_OPEN_UNQUALIFIED',0.,0.,0.,'STOW'),
 ('07_OPEN_CONTACT_FORCED_OPEN_UNQUALIFIED',P.travel,P.z_travel,1.,'OPEN')]
COLS=dict(A=cq.Color(.43,.48,.54),A_fixed_skin=cq.Color(.27,.61,.48),A_moving_leaf=cq.Color(.97,.67,.29),
 OLED=cq.Color(.10,.78,.85),FPC=cq.Color(.96,.24,.61),B_REBUILT=cq.Color(.22,.47,.82),
 STOW_CONTACT=cq.Color(.91,.72,.31),OPEN_CONTACT=cq.Color(.91,.72,.31))

def proxy_parts(pos,model):
 _,s,q,leaf,engaged=pos
 assembly=r17_assembly(P,s,q,leaf)
 pieces={k:v for k,v in assembly.items() if k!='B'}
 pieces['B_REBUILT']=model['built_b_core'].translate(cq.Vector(0,s,-P.z_travel+q))
 for port,local_y,padface in [('STOW',STOW_Y,STOW_PAD_Z+P.z_travel),('OPEN',5.,OPEN_PAD_Z)]:
  act=local_assembly(retract=(engaged!=port),left_open=engaged==port,right_open=engaged==port)
  for tag,val in act.items():
   if tag.startswith(('B_DOG','B_CARRIER_LUG','B_BOTTOM_CARRIER','B_TE_CONTACT')):
    # These are BODY frames, not permitted electrically connected in transit.
    pieces[port+'_'+tag]=val.translate(cq.Vector(0,local_y+s,padface-P.z_travel+q))
 return pieces

def draw_dxf(pose):
 tag,s,q,leaf,_=pose
 doc=ezdxf.new('R2010');doc.header['$INSUNITS']=4
 m=doc.modelspace()
 for layer,color in [('A',8),('B',5),('OLED',4),('LOCAL_FPC',6),('ANNOTATIONS',7)]:
  doc.layers.new(layer,dxfattribs={'color':color})
 # The following are SIDE-VIEW ENVELOPES ONLY, not projected CAD body walls.
 m.add_lwpolyline([(0,0),(P.H,0),(P.H,P.T),(0,P.T),(0,0)],dxfattribs={'layer':'A'})
 m.add_lwpolyline([(s,-P.z_travel+q),(s+P.H,-P.z_travel+q),(s+P.H,P.T-P.z_travel+q),
                   (s,P.T-P.z_travel+q),(s,-P.z_travel+q)],dxfattribs={'layer':'B'})
 dp=draw_screen(P,s,q,24)
 m.add_lwpolyline(dp['path'],dxfattribs={'layer':'OLED'})
 fp=draw_internal_fpc(P,s,q,24)
 m.add_lwpolyline([(y+s,z-P.z_travel+q) for y,z in fp['path_local']],dxfattribs={'layer':'LOCAL_FPC'})
 m.add_text(f'R21 {tag} / YZ envelope / mm / OLED R3.4 UNQUALIFIED',dxfattribs={'height':2.4,'layer':'ANNOTATIONS'}).set_placement((2,30))
 path=CAD/(tag+'.dxf');doc.saveas(path)
 return path

def html_viewer():
 states=[]
 for i in range(201):
  t=i/200
  if t<=.75:s=P.travel*t/.75;q=0;leaf=0
  elif t<=.90:s=P.travel;q=P.z_travel*(t-.75)/.15;leaf=0
  else:s=P.travel;q=P.z_travel;leaf=(t-.90)/.10
  s=max(0.,min(P.travel,s));q=max(0.,min(P.z_travel,q));leaf=max(0.,min(1.,leaf))
  dp=draw_screen(P,s,q,16)
  ff=draw_internal_fpc(P,s,q,16)
  states.append(dict(progress=round(t*100,2),s=round(s,4),q=round(q,4),leaf=round(leaf,4),
          oled=[[round(y,3),round(z,3)] for y,z in dp['path']],
          fpc=[[round(y+s,3),round(z-P.z_travel+q,3)] for y,z in ff['path_local']]))
 js=json.dumps(states,separators=(',',':'))
 content='''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
 <title>R21 双等高滑盖 / OLED-FPC 工程运动学</title><style>
 body{font-family:system-ui,"Noto Sans CJK SC",sans-serif;background:#0b1420;color:#e5e9ef;padding:22px;margin:auto;max-width:1150px}
 h1{font-size:22px} .light{color:#aebed0;font-size:13px} svg{background:#152338;max-width:100%;width:100%;height:auto;border:1px solid #4e6884;border-radius:12px}
 input{width:98%;accent-color:#48ddeb} .info{font-family:monospace;color:#79dfef}
 .warning{border-left:3px solid #f2ab6f;padding:10px;background:#25323c}</style>
 <h1>R21 双等高模块｜工程剖面</h1><p class="light">真实运动约束：B模块从后下向上滑、终点向前就位；仅一块OLED，B舱单U平储；信号触点为可缩回代理。页面无网络依赖。</p>
 <p><input id="slider" type="range" min="0" max="200" step="1" value="0"></p><p class="info" id="status"></p>
 <svg id="view" viewBox="-28 -28 300 230"><g id="layer"></g></svg>
 <p class="warning">本视图来自解析运动学；它不演示 R21 新增接点仓全部三维干涉、真实触点压缩或OLED供应商寿命。橙色端点表示收纳 Y=18.5 与展开 Y=84.75 的两座独立信号仓。跨舱电源/USB 尚未放行。</p>
 <script>const frames=__DATA__;const slider=document.getElementById('slider');const layer=document.getElementById('layer');const status=document.getElementById('status');
 const scale=1.22,X=20,Y=198;
 function py(y,z){return [X+y*scale,Y-z*scale];}
 function line(pts,col,width){return `<polyline points="${pts.map(a=>py(...a).join(',')).join(' ')}" stroke="${col}" stroke-width="${width}" fill="none" stroke-linejoin="round" stroke-linecap="round"/>`;}
 function rect(y0,y1,z0,z1,col){let [xx,yy]=py(y0,z1);return `<rect x="${xx}" y="${yy}" width="${(y1-y0)*scale}" height="${(z1-z0)*scale}" fill="${col}" fill-opacity=".37" stroke="${col}" stroke-width="1"/>`;}
 function render(){let f=frames[+slider.value],s=f.s,q=f.q;layer.innerHTML=rect(0,94.25,0,7.2,'#97a7b6')+rect(s,s+94.25,-8.2+q,-1+q,'#5b9eff')+line(f.oled,'#45ebf2',3)+line(f.fpc,'#e8a4cd',2)+
  `<circle cx="${py(18.5,0)[0]}" cy="${py(18.5,0)[1]}" r="4" fill="#f8b55a"/><circle cx="${py(84.75,6.25)[0]}" cy="${py(84.75,6.25)[1]}" r="4" fill="#f8b55a"/>`;
 status.textContent=`阶段 ${f.progress}%  | B纵向 ${s.toFixed(2)}mm /79.75  | 就位 ${q.toFixed(2)}mm /8.2  | 桥片 ${f.leaf.toFixed(2)}`;}
 slider.addEventListener('input',render);render();</script></html>'''.replace('__DATA__',js)
 path=VIEWER/'R21_motion_offline.html';path.write_text(content,encoding='utf8')
 return path

def run():
 model=run_dock_integration();records=[]
 for pose in POSES:
  name,s,q,k,engaged=pose
  pieces=proxy_parts(pose,model)
  group=cq.Assembly(name='R21_'+name)
  for label,shape in pieces.items():
   col=COLS.get(label.split('_')[0]+'_CONTACT',COLS.get(label,cq.Color(.79,.55,.21)))
   group.add(shape,name=label+'_RESEARCH_PROXY',color=col)
  path=CAD/(name+'.step');group.save(str(path),exportType='STEP')
  reopened=cq.importers.importStep(str(path)).solids().vals()
  assert len(reopened)==len(pieces) and all(x.isValid() for x in reopened),name
  dxf=draw_dxf(pose) if name.startswith(('01','03','05')) else None
  records.append(dict(state=name,STEP=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
     imported_valid_solids=len(reopened),CAD_size_bytes=path.stat().st_size,dxf_section=dxf.name if dxf else None,
     OLED_and_B_full_supplier_verified=False))
  print('CAD',name,len(reopened),'valid',flush=True)
 view=html_viewer()
 result=dict(revision='R21 export research proxies',pose_records=records,interactive_viewer=view.name,
   all_selected_proxies_valid=True,OEM_parts_included=False,real_hardstop_release=False,production_approval=False)
 (ROOT/'verification'/'R21_step_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 return result
if __name__=='__main__':run()
