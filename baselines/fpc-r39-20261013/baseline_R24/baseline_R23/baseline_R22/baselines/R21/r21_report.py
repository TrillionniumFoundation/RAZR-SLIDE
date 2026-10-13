"""R21 machine-data-driven CN engineering report. Render and visually verify PDF."""
from pathlib import Path
import json,csv,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.font_manager import fontManager
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.colors import HexColor
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle
from r21_geom import ROOT,P,STOW_Y
from r17_model import draw_screen,draw_internal_fpc
DATA=json.loads((ROOT/'verification'/'R21_results.json').read_text())
OUT=ROOT/'drawings';OUT.mkdir(exist_ok=True)
fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
plt.rcParams['font.family']='Noto Sans CJK JP'
plt.rcParams['axes.unicode_minus']=False
C={'A':'#64758a','B':'#367ab3','oled':'#02a8b1','fpc':'#c9589f','accent':'#e2a33e','dark':'#1b3148','red':'#bf4e5b'}
def save(fig,stem):
 fig.savefig(OUT/(stem+'.png'),dpi=165,bbox_inches='tight',pad_inches=.16)
 fig.savefig(OUT/(stem+'.svg'),bbox_inches='tight',pad_inches=.12)
 plt.close(fig)

def geometry_five():
 fig,ax=plt.subplots(1,5,figsize=(17.2,6.0),sharey=True)
 poses=[(0,0,0,'① 收起'),(P.travel/2,0,0,'② 上滑半程'),(P.travel,0,0,'③ 纵向到位'),(P.travel,P.z_travel/2,0,'④ 前后就位'),(P.travel,P.z_travel,1,'⑤ 齐平承托')]
 for pane,(s,q,leaf,label) in zip(ax,poses):
  # Both modules are envelope rectangles in Y/Z, not exact cross-section polygons.
  pane.add_patch(Rectangle((0,0),P.T,P.H,fill=True,facecolor=C['A'],alpha=.25,edgecolor=C['A'],lw=1.6))
  pane.add_patch(Rectangle((-P.z_travel+q,s),P.T,P.H,fill=True,facecolor=C['B'],alpha=.25,edgecolor=C['B'],lw=1.6))
  sd=draw_screen(P,s,q,20)
  pane.plot([z for y,z in sd['path']],[y for y,z in sd['path']],color=C['oled'],lw=2.5)
  fpc=draw_internal_fpc(P,s,q,16)
  pane.plot([z-P.z_travel+q for y,z in fpc['path_local']],[y+s for y,z in fpc['path_local']],color=C['fpc'],lw=1.2,ls='--')
  pane.set_xlim(-10,10);pane.set_ylim(-5,180);pane.set_title(label,fontsize=11);pane.grid(alpha=.13)
  pane.text(-9,156,f'Y={s:.2f}\nZ={q:.2f}',fontsize=8,color=C['dark'])
  pane.set_xlabel('Z (mm)',fontsize=9)
 ax[0].set_ylabel('Y (mm)')
 fig.suptitle('R21 / OLED 与 B舱本地FPC原路径不变；只重建接点仓与B舱局部结构',fontsize=15,weight='bold')
 fig.text(.5,.025,'灰色A固定，蓝色B向上滑后前后就位；青色OLED、紫色B舱内部FPC；显示为名义包络，不是OEM实物',ha='center',fontsize=9)
 fig.subplots_adjust(left=.055,right=.985,top=.83,bottom=.15,wspace=.12)
 save(fig,'R21_01_five_pose')

def pocket_layout():
 fig,axes=plt.subplots(1,2,figsize=(13.4,5.7))
 for a,loc,title in zip(axes,[30.,18.5],['R20旧：Y=30mm，侵入小电池包络','R21候选：Y=18.5mm，避开电池包络']):
  a.add_patch(Rectangle((-36.995,0),73.99,94.25,edgecolor=C['dark'],facecolor='#f4f7fa',lw=1.8))
  a.add_patch(Rectangle((-33,22),56,36,edgecolor='#3a855b',facecolor='#9bd0b6',alpha=.45,lw=1.5))
  a.add_patch(Rectangle((-23.6,loc-3.2),47.2,6.4,facecolor=C['accent'],edgecolor='#b07927',alpha=.63,lw=1.1))
  a.add_patch(Rectangle((-16,3.2),32,3.8,facecolor=C['B'],edgecolor='#20587b',alpha=.5))
  a.axhline(14.50,c='#657484',ls=':',lw=1)
  a.set(xlim=(-40,40),ylim=(0,95),xlabel='X / mm',ylabel='B舱局部Y / mm');a.set_aspect('equal',adjustable='box');a.grid(alpha=.12);a.set_title(title,fontsize=11)
  a.text(0,43,'B舱小电池代理\nY=22..58',ha='center',fontsize=9)
  a.text(0,6,'展开端触点仓',ha='center',color='white',fontsize=8)
  a.text(0,loc+0.1,'收纳触点仓',ha='center',fontsize=9)
 fig.suptitle('同尺寸双舱：仅移动收纳端信号仓，不改变B舱小电池的参考包络',fontsize=14,weight='bold')
 fig.subplots_adjust(top=.83,bottom=.12,wspace=.17)
 save(fig,'R21_02_contact_relief')

def oled_clearance():
 rows=DATA['oled_screening_mm'];fig,axes=plt.subplots(1,2,figsize=(13.1,5.0))
 x=[r['assumed_encapsulation_extension_each_edge_mm'] for r in rows]
 y=[r['min_clearance_mm'] for r in rows]
 axes[0].plot(x,y,marker='o',c=C['oled'],lw=2)
 axes[0].axhline(.30,color=C['red'],ls='--',label='筛查目标0.30mm')
 axes[0].fill_between(x,y,.30,where=[v<.3 for v in y],color=C['red'],alpha=.15)
 axes[0].set(xlabel='假设每侧增加的OLED封装宽度 / mm',ylabel='与B结构的最小名义间距 / mm',ylim=(0,.42));axes[0].grid(alpha=.15);axes[0].legend()
 axes[0].set_title('真实OLED宽度未知：只用有效区画图会高估余量',fontsize=11)
 vals=[DATA['altered_compared_to_R20']['battery_proxy_old_recess_intersection_mm3'],DATA['altered_compared_to_R20']['battery_proxy_new_recess_intersection_mm3']]
 axes[1].bar(['R20 Y=30','R21 Y=18.5'],vals,color=[C['red'],C['B']],width=.44)
 for i,v in enumerate(vals):axes[1].text(i,v+1,f'{v:.3f} mm³',ha='center',fontsize=10)
 axes[1].set(ylabel='切槽占用B电池包络 mm³',ylim=(0,34));axes[1].set_title('两端触点仓位置迁移带来的包络收益',fontsize=11)
 fig.suptitle('R21 正向优化与保留的OLED封装负向门槛',fontsize=14,weight='bold')
 fig.subplots_adjust(left=.08,right=.98,top=.81,bottom=.14,wspace=.31)
 save(fig,'R21_03_clearance_failures')

pdfmetrics.registerFont(TTFont('CN','/usr/share/fonts/truetype/arphic-gbsn00lp/gbsn00lp.ttf'))
REG=ParagraphStyle('c',fontName='CN',fontSize=9.7,leading=15,textColor=HexColor('#293c4b'))
SMALL=ParagraphStyle('s',parent=REG,fontSize=8.6,leading=13)
W,H=landscape(A4)
can=canvas.Canvas(str(ROOT/'R21_接点仓与屏幕装配工程审查.pdf'),pagesize=(W,H))
can.setTitle('R21 RAZR 双等高滑盖: 信号仓、OLED/FPC与公差失效工程审查')
can.setAuthor('RAZR-SLIDE parametric engineering study')
def head(n,title,sub):
 can.setFillColor(HexColor('#112538'));can.rect(0,H-81,W,81,stroke=0,fill=1)
 can.setFillColor(HexColor('#ffffff'));can.setFont('CN',19);can.drawString(35,H-40,title)
 can.setFont('CN',10);can.drawString(36,H-62,sub)
 can.setStrokeColor(HexColor('#e2e7ef'));can.line(36,30,W-36,30)
 can.setFillColor(HexColor('#66798a'));can.setFont('CN',8);can.drawString(36,16,'R21 / 工程代理几何 ≠ 厂家物料 ≠ 材料寿命验证 ≠ 制造放行')
 can.drawRightString(W-37,16,str(n))
def para(content,y,x=36,width=770,style=REG):
 t=Paragraph(content,style);_,hh=t.wrap(width,H);t.drawOn(can,x,y-hh);return y-hh

def chart(img,x,y,w,h):
 from PIL import Image
 im=Image.open(img);iw,ih=im.size;r=min(w/iw,h/ih);ww,hh=iw*r,ih*r
 can.drawImage(str(img),x+(w-ww)/2,y+(h-hh)/2,width=ww,height=hh,mask='auto')
def table(rows,y,widths,x=37):
 rr=[[Paragraph(str(t),SMALL) for t in row] for row in rows]
 tt=Table(rr,colWidths=widths,hAlign='LEFT')
 tt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#d9e8ee')),
 ('LINEBELOW',(0,0),(-1,0),.7,HexColor('#77aabb')),
 ('LINEBELOW',(0,1),(-1,-1),.3,HexColor('#cad5db')),
 ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
 ('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
 _,height=tt.wrap(sum(widths),H);tt.drawOn(can,x,y-height);return y-height

def build_pdf():
 geometry_five();pocket_layout();oled_clearance()
 head(1,'R21 | 双端信号仓重新布局与B舱局部一体化','从R17运动学、R19双端触点、R20失败接点仓的真实源码继续迭代')
 y=H-101
 y=para('<b>结论：</b>候选收纳触点中心从Y30改到Y18.5，B舱小电池代理被开槽的重叠体积由27.567mm³降至零；展开端加入托岛、侧导槽和背梁座。名义五态与OLED、本舱FPC不穿模，但<strong><font color="#ae3434">实际OLED封装宽度、公差、双挡块错误共因释放及跨舱电源均不合格</font></strong>。',y)
 chart(OUT/'R21_01_five_pose.png',36,148,770,307)
 y=134
 y=para('基本尺寸仍为两舱各94.25 × 73.99mm，纵向79.75mm、前后8.2mm；单块约7英寸OLED，B舱顶部假设R3.4单U平储，A舱优先大电池；4700mAh目标从未被真实电芯验证。',y,style=SMALL)
 can.showPage()
 head(2,'接点仓迁移：减少电池与可动零件冲突','旧固定导向肋虽然可与机身连接，但会在展开时与OLED相交：不能继续沿用')
 chart(OUT/'R21_02_contact_relief.png',35,185,770,307)
 y=172
 y=para('<b>变更：</b>沿B舱Y方向把收纳信号仓从30mm移动到18.5mm；保留R17的OLED平储通道。旧R20内侧导向肋在展开近端曾与OLED产生4.992mm³相交，R21废弃该肋，改由B舱本体中开出的滑动槽承担候选导向。',y,style=SMALL)
 y=para('<b>结果：</b>移位后B电池代理不被接点机构与切槽侵占；B外壳仍为一个连通实体。<b>限制：</b>盲槽的实际加工顺序、滑动副磨损、导向侧壁强度与装配公差未验证。A舱接收焊盘也必须同步移位。',y-8,style=SMALL)
 can.showPage()
 head(3,'展开端：载体不再无支撑地悬浮','二维算术和三维实体应分开：底板厚度通过的是假设尺寸筛查')
 y=H-105
 y=table([
 ('子结构','R20局部原状态','R21候选／当前门槛'),
 ('展开端信号岛','原厚度1.05mm，接点往内部缩回时接触托岛','补强0.80mm、加工额外运动槽；底板名义0.90mm'),
 ('B展开端狗齿','对应左右狗齿周围缺真实导向框','增加左右导向耳；预留横向1.4mm撤回通道'),
 ('载体后梁','此前没有稳定支持通道','在托岛下方增加局部托架及完整升程避让'),
 ('最坏厚度筛查','无可复算底板与公差链','按假设−0.15mm，底板保留0.75mm；实际强度未验证'),
 ('装配连通性','托岛与B舱功能核心分离','在两侧假设连接肋后，候选B壳合并为一个有效实体'),
 ('双端误释放','R20两侧全误开时接点可伸出','<font color="#a83232"><b>未修复；仍拒绝安全放行</b></font>')],y,[150,275,345])
 y-=23
 y=para('<b>补充：</b>R21并非已制造的安装机构。导槽里的轴承/导向衬套、弹簧、挡块真实止挡触发、锁闭复位、盲槽加工可行性、触点工作力与反复插拔耐久都尚无厂商数据。',y,style=REG)
 y=para('<b>供应商：</b>TE 2199001-1被标为Signal用途的弹片。其公开工作高度是0.70–1.00mm、未压高度1.20mm，最大1.5A。我们仍只使用明确标记的尺寸代理，官方STEP获取未成功；不能用于4700mAh双电池主供电确认。',y-8,style=SMALL)
 can.showPage()
 head(4,'OLED封装边界：名义有效区通过，真实面板仍失败','在同一R21 B实体上让柔性屏“每侧加宽”并重新测量三维最小距离')
 chart(OUT/'R21_03_clearance_failures.png',36,163,770,327)
 y=151
 y=para('<b>明确失效：</b>仅按OLED有效显示宽度建模时，最小距离0.3196mm，比暂定0.30mm要求仅多0.0196mm。每侧加宽0.15mm时最小距离约0.2895mm；每侧加宽0.20mm时约0.2395mm。<b>这不意味着真实模组必然超宽0.20mm，而意味着厂商封装尺寸缺失时无法放行。</b>',y,style=SMALL)
 y=para('同样，R3.4mm单U弯曲中性路径是假设，缺供应商OLED/OCA长期静置、展平力、摩擦和动态寿命许可。IEC 62715-6-42:2026只提供卷动显示展平力的测量方法，不提供本产品的合格证明。',y-7,style=SMALL)
 can.showPage()
 head(5,'复核范围、放行矩阵与最小实机试验','全部“通过”仅为名义几何或程序回归；负向测试识别失败仍应记录为测试通过')
 y=H-102
 y=table([
 ('工程门槛','R21证据/状态'),
 ('原R17/R19/R20代码基线','17 / 30 / 28项单位回归通过；R17为解析路径校核'),
 ('新R21可复算CAD','7个STEP，每态24个代理实体有效；另有3个DXF侧剖和离线HTML'),
 ('修正后B实体与OLED/内部FPC','五态CAD体积相交为0；未覆盖真实封装和全部公差'),
 ('B收纳端电池代理包络','新机构0mm³切槽重叠；仍非原厂电芯'),
 ('OLED实际宽度、寿命和真实R许可','<font color="#ab3030"><b>未通过/无厂家数据</b></font>'),
 ('双端常闭联锁、单侧故障、反向复位','<font color="#ab3030"><b>未通过：R20双挡块共同误开路径仍存在</b></font>'),
 ('触点公差、老化与主电流链路','<font color="#ab3030"><b>未通过：TE仅信号用途，R20老化公差也越界</b></font>'),
 ('整机4700mAh、热/跌落/振动/30万循环','无实物试验；不得宣称合格')],y,[225,545])
 y-=20
 y=para('<b>后续唯一合理优先级：</b>（1）取得OLED封装宽、层叠、动态R、展平力与OCA数据；（2）完成真正承力的双侧硬止挡联锁/机械回位，消灭共同误开；（3）把厂家真实信号接点CAD与经过额定认证的电源连接分开导入；（4）样机完成高低温、灰尘、偏载、静置恢复及循环验证。',y,style=SMALL)
 y=para('<b>权威公开参考：</b>TE https://www.te.com/en/product-2199001-1.html ；IEC https://webstore.iec.ch/en/publication/78233 ；本项目 R17/R19/R20 参数化源码与前轮负向报告（均随工程包提供）。',y-8,style=SMALL)
 can.showPage()
 can.save()
 print('REPORT',ROOT/'R21_接点仓与屏幕装配工程审查.pdf')

if __name__=='__main__':build_pdf()
