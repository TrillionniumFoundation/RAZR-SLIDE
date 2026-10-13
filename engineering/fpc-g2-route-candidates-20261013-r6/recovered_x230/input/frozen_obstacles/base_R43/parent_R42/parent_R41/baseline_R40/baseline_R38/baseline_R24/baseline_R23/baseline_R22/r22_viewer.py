"""Create offline 2D R22 pose/safety logic viewer; explicitly NOT physical mechanism."""
import json
from pathlib import Path
from r22_mechanics import ROOT,P
from r17_model import draw_screen,draw_internal_fpc

def run():
 frames=[]
 for i in range(201):
  t=i/200
  if t<=.75:s=P.travel*t/.75;q=0;leaf=0
  elif t<=.90:s=P.travel;q=P.z_travel*(t-.75)/.15;leaf=0
  else:s=P.travel;q=P.z_travel;leaf=(t-.90)/.10
  s=max(0,min(P.travel,s));q=max(0,min(P.z_travel,q));leaf=max(0,min(1,leaf))
  a=draw_screen(P,s,q,18);b=draw_internal_fpc(P,s,q,18)
  frames.append(dict(stage=i/2,s=round(s,5),q=round(q,5),leaf=round(leaf,5),
   oled=[[round(y,3),round(z,3)] for y,z in a['path']],
   fpc=[[round(y+s,3),round(z-P.z_travel+q,3)] for y,z in b['path_local']]))
 html='''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"/><title>R22 机械三重硬止挡·离线动作与故障诊断</title>
 <style>body{background:#0c1423;color:#eaf0f7;font:15px system-ui,"Noto Sans CJK SC",sans-serif;max-width:980px;margin:auto;padding:20px} h1{font-size:21px} .dim{color:#aabbd0;font-size:13px} .warn{background:#382d25;border-left:4px solid #df9a5b;padding:10px} .row{display:flex;flex-wrap:wrap;gap:12px} label{background:#182638;border:1px solid #47566c;padding:10px;border-radius:8px;flex:1 1 180px} label input{margin-right:6px} #slider{width:100%;accent-color:#36ddd5} svg{width:100%;height:auto;background:#182638;border:1px solid #53667b;border-radius:12px} .status{padding:12px;background:#1c2939;border-radius:8px;font-weight:650} .bad{color:#ff9e9e} .ok{color:#95e7b8} .blocked{color:#ffd785} pre{white-space:pre-wrap}</style>
 <h1>R22｜单屏双等舱滑盖 · 双侧误开/第三止挡模型</h1><p class="dim">CadQuery 3D 布尔改型与选定态独立验证结果在 R22 工程包内；此 HTML 只展示 **2D 解析运动路径和理想的锁止条件逻辑**。虚拟场景不能证明弹簧、真实 A 侧机械键、触点耐久或 OEM OLED。</p>
 <p>滑行/就位/屏幕展开进度： <output id="pct">0%</output></p><input id="slider" type="range" min="0" max="200" value="0" step="1"/>
 <svg viewBox="-22 -25 280 195" id="scene"><g id="view"></g></svg>
 <p class="dim">A=灰色，B=蓝色，OLED=青色，B 内部 FPC=粉色。R3.4/OLED 路径为未经厂家批准的模型。</p>
 <div class="row"><label><input type="checkbox" id="legacy" checked> 原左右狗齿同时错误解除</label><label><input type="checkbox" id="force" checked> 尝试强制伸出接点</label><label><input type="checkbox" id="left"> 新增左侧止挡卡开</label><label><input type="checkbox" id="right"> 新增右侧止挡卡开</label><label><input type="checkbox" id="centre"> 独立中央止挡卡开</label></div>
 <p class="status" id="status"></p><p class="dim" id="details"></p><p class="warn">红色状态是明确的 **否决反例**：如果三只承力挡块共同被错误拉开，则旧锁也误开时仍可提前伸出。本项目禁止对此报“已消灭共因故障”。真实连接器/接收键/复位机构尚未建模，制造 NO-GO。</p>
 <script>const FRAMES=__FRAMES__;const P={travel:79.75,zTravel:8.2,height:94.25,thick:7.2};
 const elements=Object.fromEntries(['slider','pct','legacy','force','left','right','centre','view','status','details'].map(k=>[k,document.getElementById(k)]));
 const xScale=1.0,X=27,Y=140,xy=(y,z)=>[X+y*xScale,Y-z*xScale];
 function poly(ps,c,w){return `<polyline points="${ps.map(a=>xy(...a).join(',')).join(' ')}" fill="none" stroke="${c}" stroke-width="${w}"/>`}
 function rect(a,b,c,d,color){let [x,y]=xy(a,d);return `<rect x="${x}" y="${y}" width="${(b-a)*xScale}" height="${(d-c)*xScale}" fill="${color}" fill-opacity=".37" stroke="${color}"/>`}
 function run(){let f=FRAMES[+elements.slider.value],seatedStow=Math.abs(f.s)<=.02&&Math.abs(f.q)<=.02,
 seatedOpen=Math.abs(f.s-P.travel)<=.02&&Math.abs(f.q-P.zTravel)<=.02,
 seated=seatedStow||seatedOpen,port=seatedStow?'收纳':seatedOpen?'展开':'无合格坐实端',
 retractL=seated||elements.left.checked,retractR=seated||elements.right.checked,retractC=seated||elements.centre.checked,
 blocked=!(retractL&&retractR&&retractC),forced=elements.force.checked,
 fails=forced&&!blocked&&!seated;
 elements.view.innerHTML=rect(0,P.height,0,P.thick,'#acbbce')+rect(f.s,f.s+P.height,-P.zTravel+f.q,P.thick-P.zTravel+f.q,'#4b8aea')+poly(f.oled,'#5dfbe7',2.5)+poly(f.fpc,'#ef78c4',2)+`<circle cx="${xy(18.5,0)[0]}" cy="${xy(18.5,0)[1]}" r="3" fill="#ffcb69"/>`;
 elements.pct.textContent=f.stage.toFixed(1)+'%  /   B纵向 '+f.s.toFixed(2)+'mm   /   靠前 '+f.q.toFixed(2)+'mm';
 elements.status.className='status '+(fails?'bad':forced&&blocked?'blocked':'ok');
 elements.status.textContent=fails?'危险：三道硬止挡均误开，未坐实也可提前伸出（NO-GO）':
 forced&&blocked?'拦截：至少一道实体止挡仍处于锁定位置（理想代理）':
 forced&&seated?'理想坐实且挡块撤回：接点可以伸出（真实机构未证实）':'未请求伸出/已缩回';
 elements.details.textContent=`端面坐实：${port} | 旧左右狗齿假误开=${elements.legacy.checked}（不控制中央锁） | 理想挡块 L=${retractL?'开':'闭'}，R=${retractR?'开':'闭'}，中心=${retractC?'开':'闭'} | 仅供故障树逻辑审查。`;
 }
 for(const v of Object.values(elements))if(v&&['INPUT'].includes(v.tagName))v.addEventListener('input',run);run();</script>
 </html>'''
 out=ROOT/'viewer';out.mkdir(exist_ok=True)
 path=out/'R22_三止挡离线动作及故障诊断.html'
 path.write_text(html.replace('__FRAMES__',json.dumps(frames,separators=(',',':'))),encoding='utf-8')
 return path

if __name__=='__main__':print(run())
