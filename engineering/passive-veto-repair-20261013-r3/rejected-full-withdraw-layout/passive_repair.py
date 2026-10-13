#!/usr/bin/env python3
"""r3 derived bench: two trapped-pin cam tracks positively drive independent stops.

Research dimensions only. No material, force, spring or OEM fit qualification.
The contact offset/free withdrawal are explicit new bench hypotheses.
"""
from __future__ import annotations
import functools,hashlib,itertools,json,math,platform,sys
from pathlib import Path
import cadquery as cq
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
OLD=REPO/'engineering/passive-veto-design-20261013-r2'
sys.dont_write_bytecode=True;sys.path.insert(0,str(OLD))
import passive_veto as old
from occ_signed_volume import common,validated_solid_volume
EPS=1e-7;CAPTURE_Q_SHIFT=.15;CAM_SEAT_PLATEAU=.10;PIN_R=.10;SLOT_R=.16;LEVELS=(0.,5.)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cv(a,b):return common(a,b)['checked_volume_mm3']
def box(*args):return old.blk(*args)
def fuse(parts):
 s=parts[0]
 for p in parts[1:]:s=s.fuse(p)
 s=s.clean();validated_solid_volume(s);return s
def world(s,port,side):return old.world(s,port,side)
def delta_q(port,d):return (0,-d,0) if port=='STOW' else (0,0,d)
def delta_r(port,d):return (0,0,d) if port=='STOW' else (0,d,0)
def qleaf(port):return 1.3 if port=='STOW' else 6.2
def lift(q):return max(0.,min(1.2,1.2-2*(q-CAM_SEAT_PLATEAU)))
def capsule(a,b,r):
 dq,dr=b[0]-a[0],b[1]-a[1];length=math.hypot(dq,dr);nq,nr=-dr*r/length,dq*r/length
 pts=[(a[0]+nq,a[1]+nr),(b[0]+nq,b[1]+nr),(b[0]-nq,b[1]-nr),(a[0]-nq,a[1]-nr)]
 prism=cq.Workplane('YZ',origin=(-.65,0,0)).polyline(pts).close().extrude(.5).val()
 disks=[cq.Solid.makeCylinder(r,.5,cq.Vector(-.65,*p),cq.Vector(1,0,0)) for p in (a,b)]
 return fuse([prism,*disks])
def track():
 nodes=[(-1.3,0.),(-.7,0.),(-.1,1.2),(.3,1.2)]
 hole=fuse([capsule(a,b,SLOT_R) for a,b in zip(nodes,nodes[1:])])
 body=box(-.6,-.2,-1.1,.5,-.28,1.48).cut(hole).clean()
 validated_solid_volume(body);return body
def raw_stop(port):
 Q=qleaf(port)
 pin=cq.Solid.makeCylinder(PIN_R,.67,cq.Vector(-.85,0,0),cq.Vector(1,0,0))
 return fuse([pin,box(-.85,-.65,-.05,.05,0,1.8),box(-.85,.4,0,Q+.05,1.5,1.8),box(.2,.4,Q-.05,Q+.05,0,1.8)])

@functools.lru_cache(maxsize=4)
def static(port,side):
 previous,dx=old.fixture_parts(port,side);Q=qleaf(port)
 # Derived research body; original key/pawl contact shape stays an archived
 # comparison, while pawn/contact/guide are displaced by q+.15 in this bench.
 min_e=-.6 if port=='STOW' else -.3
 pawn=previous['PAWL_SLIDER'].intersect(world(box(min_e,5.,-20,20,-20,20),port,side)).clean()
 pawn=pawn.translate(delta_q(port,CAPTURE_Q_SHIFT))
 origroot=previous['GUIDE_CARTRIDGE'].translate(delta_q(port,CAPTURE_Q_SHIFT))
 cover=previous['REMOVABLE_COVER_UNFASTENED'].translate(delta_q(port,CAPTURE_Q_SHIFT))
 # Gate/stalk joins the moved original stem, but remains on a separate q plane
 # from both interposer crosspieces, permitting stop return after full retreat.
 stalk_q=Q+.5
 if port=='STOW':
  stalk=box(-.1,0,stalk_q-.05,stalk_q+.05,-9.8,6.1)
  link=box(-.1,0,Q-.05,stalk_q+.05,-9.85,-9.77)
 else:
  stalk=box(-.1,0,stalk_q-.05,stalk_q+.05,1.0,9.9)
  link=box(-.1,0,stalk_q-.05,stalk_q+.05,9.87,9.97)
 tabs=[stalk,link]
 for off in LEVELS:
  tabs.extend([box(-.1,0,Q-.05,Q+.05,off+.1,off+1.1),box(-.1,0,Q+.04,stalk_q+.05,off+1.,off+1.1)])
 pawn=fuse([pawn,world(fuse(tabs),port,side)])
 roots=[origroot];cams=[];caps=[];stops={}
 rootq=(3.,3.2) if port=='STOW' else (8.,8.2)
 for index,off in enumerate(LEVELS):
  outer=box(-1.1,.9,-1.45,Q+.25,-.8,3.02)
  cavity=box(-.87,.42,-.12,Q+.07,-.12,3.03)
  outer=outer.cut(cavity)
  cam_window=box(-1.52,-.18,-1.105,1.81,-.51,1.50)
  gate_window=box(-.12,abs(dx)+.12,Q-.07,Q+.57,.08,1.12)
  outer=outer.cut(cam_window).cut(gate_window).clean()
  base=box(-2.9,.9,-1.45,rootq[1],-1.,-.8)
  root_r=(-11.06-off,-.8) if port=='STOW' else (-.8,13.-off)
  stem=box(-2.9,-2.7,*rootq,*root_r)
  # Actual lower stop bears underneath bridge, not an absent floating flag.
  bottom=box(.1,.9,.7,.9,1.12,1.48)
  fixed=fuse([outer,base,stem,bottom])
  # Full-travel key-adapter and pawn-stalk passages through actual material.
  adapter_pass=box(-1.52,-1.08,-.07,rootq[1]+.02,-20,20)
  stalk_pass=box(-.12,abs(dx)+.12,stalk_q-.07,stalk_q+.07,-20,20)
  fixed=fixed.cut(adapter_pass).cut(stalk_pass).clean()
  cap=box(-2.,2.,-1.45,Q+.25,3.02,3.32).cut(adapter_pass).clean()
  # Physical insertion datum prevents using negative-q over-insertion to
  # invent a larger phone seating window. Nominal gap .01, still hypothesis.
  datum=box(-.7,-.1,-1.40,-1.11,-.5,1.48)
  fixed=fuse([fixed,datum])
  fixed=fixed.translate((0,0,off));cap=cap.translate((0,0,off))
  roots.append(world(fixed,port,side));caps.append(world(cap,port,side))
  stop=raw_stop(port).translate((0,0,off))
  stops['STOP_'+str(index)]=world(stop,port,side)
  connector_r=(-3.2-off,-.23) if port=='STOW' else (-.5,9.7-off)
  keycam=fuse([track(),box(-1.5,-1.1,-.05,.05,*connector_r),box(-1.5,-.2,-.05,.05,-.5,-.23)])
  cams.append(world(keycam.translate((0,0,off)),port,side))
 root=fuse(roots)
 xc=-34.75 if side=='L' else 34.75
 if port=='STOW':
  keyaccess=box(xc-.22,xc+.22,-12,2.5,-.72,7.02)
  root=root.cut(keyaccess).clean();cover=cover.cut(keyaccess).clean()
  root_slot=world(box(-2.92,-2.68,2.98,3.22,-8.,-6.),port,side)
  cover=cover.cut(root_slot).clean()
  # Route moved stem/stalk through a new opening in the copied end guide.
  stalkaccess=world(box(-.12,abs(dx)+.12,Q+.43,Q+.57,-11.08,-6.3),port,side)
  root=root.cut(stalkaccess).clean();cover=cover.cut(stalkaccess).clean()
  # Full extraction opens the center of the old research cover. A true upper
  # arch reconnects its two sides above the entire key-grip swept envelope.
  cover=fuse([cover,box(xc-2.7,xc-2.4,-4.,-3.7,3.4,7.5),
               box(xc+2.4,xc+2.7,-4.,-3.7,3.4,7.5),
               box(xc-2.7,xc+2.7,-4.,-3.7,7.1,7.5)])
  key=old.normalized_originals(port,side)[0]
  grip=box(xc-.18,xc+.18,.5,2.,2.95,7.)
  top=world(box(-1.5,.18,-.3,.4,-3.2,-3.),port,side)
  key=fuse([key,grip,top,*cams])
 else:
  key=old.normalized_originals(port,side)[0]
  grip=world(box(-1.3,.18,-2.,1.3,9.4,10.6),port,side)
  key=fuse([key,grip,*cams])
 for s in [pawn,root,cover,key,*caps,*stops.values()]:validated_solid_volume(s)
 return {'PAWL':pawn,'ROOT':root,'OLD_COVER_UNFASTENED':cover,'KEY':key,
         'CAP_0_UNFASTENED':caps[0],'CAP_1_UNFASTENED':caps[1],**stops},dx

def scene(port,side,q=0.,retreat=0.,present=True,jam=None):
 base,dx=static(port,side);out={n:s for n,s in base.items() if n!='KEY'}
 out['PAWL']=base['PAWL'].translate((dx*retreat,0,0))
 for i in range(2):out['STOP_'+str(i)]=base['STOP_'+str(i)].translate(delta_r(port,(jam or {}).get(i,lift(q) if present else 0.)))
 if present:out['KEY']=base['KEY'].translate(delta_q(port,q))
 return out
def pairs(p):return [{'parts':[a,b],'common_mm3':cv(p[a],p[b])} for a,b in itertools.combinations(p,2)]
def save(p,name):
 a=cq.Assembly(name=name)
 for n,s in p.items():validated_solid_volume(s);a.add(s,name=n)
 path=HERE/'cad'/f'{name}.step';a.save(str(path),exportType='STEP')
 solids=cq.importers.importStep(str(path)).solids().vals()
 if len(solids)!=len(p):raise ValueError('STEP solid count changed')
 actual=sorted(validated_solid_volume(s) for s in solids);expected=sorted(s.Volume() for s in p.values())
 if any(abs(a-b)>1e-6 for a,b in zip(actual,expected)):raise ValueError('STEP volume changed')
 return {'path':str(path.relative_to(HERE)),'sha256':sha(path),'valid_positive_solids':len(solids)}

def main():
 (HERE/'cad').mkdir(exist_ok=True)
 rows=[];withdraw=[];steps=[]
 for port in ('STOW','OPEN'):
  for side in 'LR':
   for name,q,pres,jam in [('FULL',0,True,None),('SEAT_0p10',.10,True,None),('PARTIAL_0p25',.25,True,None),('ABSENT',0,False,None),('PRIMARY_JAM_ABSENT',0,False,{0:1.2}),('SECONDARY_JAM_ABSENT',0,False,{1:1.2}),('DOUBLE_JAM_ABSENT',0,False,{0:1.2,1:1.2})]:
    rr=[]
    for i in range(23):
     p=scene(port,side,q,i/22,pres,jam)
     rr.append({'fraction':i/22,'pairs':pairs(p)})
    rows.append({'port':port,'side':side,'state':name,'samples':rr})
    print(json.dumps({'port':port,'side':side,'state':name,'path_stop_collision_max_mm3':max(x['common_mm3'] for r in rr for x in r['pairs'] if 'PAWL' in x['parts'] and any(n.startswith('STOP') for n in x['parts']))}),flush=True)
   for jamname,jam in [('NORMAL',None),('PRIMARY_HELD_CLEAR',{0:1.2}),('SECONDARY_HELD_CLEAR',{1:1.2})]:
    for q in (0.,.02,.05,.10,.15,.2,.25,.4,.7,.8,1.,1.2,1.4,2.,4.,8.,12.):
     p=scene(port,side,q,1.,True,jam)
     withdraw.append({'port':port,'side':side,'jam_state':jamname,'key_withdraw_mm':q,'pairs':pairs(p)})
  for name,q,pres,jam,fraction in [('SEATED',0,True,None,0),('RELEASED',0,True,None,1),('ABSENT_BLOCKED',0,False,None,.35/abs(static(port,'L')[1])),('PRIMARY_JAM_ABSENT_BLOCKED',0,False,{0:1.2},.35/abs(static(port,'L')[1])),('DOUBLE_JAM_ABSENT_ESCAPE',0,False,{0:1.2,1:1.2},1),('NORMAL_KEY_WITHDRAW_1p4',1.4,True,None,1),('PRIMARY_HELD_CLEAR_WITHDRAW_BLOCKED',.4,True,{0:1.2},1)]:
   combined={}
   for side in 'LR':combined.update({side+'_'+n:s for n,s in scene(port,side,q,fraction,pres,jam).items()})
   steps.append(save(combined,port+'_'+name))
 report={'revision':'r3 two independent trapped-pin cam stops and derived capture bench',
   'environment':{'host':platform.node(),'cadquery':cq.__version__},
   'source_r2_builder_sha256':sha(OLD/'passive_veto.py'),'original_capture_q_translation_mm':CAPTURE_Q_SHIFT,
   'derived_nominal_capture_free_withdrawal_mm':.18,'derived_capture_probe_mm':.25,
   'original_0p05_capture_probe_not_claimed':True,'cam_full_seat_plateau_nonnegative_mm':CAM_SEAT_PLATEAU,
   'all_dimensions_research_hypotheses':True,'pin_radius_mm':PIN_R,'slot_radius_mm':SLOT_R,
   'motion_rows':rows,'actual_normal_and_jammed_key_withdrawal_rows':withdraw,'STEP_exports':steps,
   'return_is_positive_cam_geometry_not_a_spring_flag':True,'friction_force_strength_or_actual_jam_qualification':False,
   'double_jam_escape_retained':True,'physical_max_safe_freewithdrawal_for_BM28_OLED_FPC_mm':None,
   'fixture_fabrication_go':False,'manufacturing_go':False}
 (HERE/'r3-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'motion_samples':sum(len(r['samples']) for r in rows),'withdrawal_samples':len(withdraw),'STEPs':len(steps),'manufacturing_go':False},indent=2))
if __name__=='__main__':main()
