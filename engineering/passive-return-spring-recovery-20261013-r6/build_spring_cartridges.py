#!/usr/bin/env python3
"""New R6 bench geometry from byte-pinned R4 STEP; never phone qualification."""
from pathlib import Path
import sys,math,json,hashlib,itertools,time,platform
sys.dont_write_bytecode=True
import cadquery as cq
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'inputs'))
import r4_identity as identity
from occ_signed_volume import validated_solid_volume
from strict_intersections import CheckedBody,Checker
from strict_signed_common import strict_common,participant
EPS=1e-7
EXPECTED={'STOW_SEATED.step':'38c7f5af67737c198c96d85c33a4fc4d9bd1acad34ce932039366c0a5242d118','OPEN_SEATED.step':'07f50a89195db27566c252b4c02619be716d4f3fd7be962ab795158745c203a0'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def box(e0,e1,q0,q1,r0,r1):return cq.Solid.makeBox(e1-e0,q1-q0,r1-r0,cq.Vector(e0,q0,r0))
def cyl(radius,height,e,q,r):return cq.Solid.makeCylinder(radius,height,cq.Vector(e,q,r),cq.Vector(0,0,1))
def fuse(ss):
 s=ss[0]
 for v in ss[1:]:s=s.fuse(v)
 s=s.clean();participant(s);return s
def world(s,port,side):
 xc=-34.75 if side=='L' else 34.75
 sign=(-1 if side=='L' else 1) if port=='STOW' else (1 if side=='L' else -1)
 if sign<0:s=s.mirror('YZ')
 if port=='STOW':return s.mirror('XZ').translate((xc,1.2,10))
 return s.mirror('XZ').rotate((0,0,0),(1,0,0),-90).translate((xc,-10,-6))
def rvec(port,d):return (0,0,d) if port=='STOW' else (0,d,0)
def source(port):
 p=HERE/'inputs'/(port+'_SEATED.step');assert sha(p)==EXPECTED[p.name]
 leaves,topology=identity.import_whole(p)
 return {side:{n:b.shape for n,b in identity.identify(leaves,port,side,True).items()} for side in 'LR'},topology
def derived(port,side,base,lift=1.14,present=True):
 p=dict(base);Q=1.3 if port=='STOW' else 6.2;qc=Q+.9
 root=p['ROOT'];new=[]
 for i in range(2):
  off=5*i;qc=Q+(.9 if i==0 else 3.0);ee=4. if port=="OPEN" else 0.;stop=p['STOP_'+str(i)].translate(rvec(port,-1.2))
  # Lateral shoulder joins the existing STOP below the existing cap plane.
  shoulder=fuse([box(.25,3.2+ee,Q-.04,Q+.08,1.5,1.8),box(2.5+ee,3.1+ee,Q+.02,qc+.15,1.5,1.8),cyl(.55,.3,2.8+ee,qc,1.5)]).translate((0,0,off))
  stop=fuse([stop,world(shoulder,port,side)])
  p['STOP_'+str(i)]=stop.translate(rvec(port,lift))
  link=fuse([box(.5,.9,Q+.15,qc+.55,-.98,-.82),box(.5,5.+ee,qc+.35,qc+.55,-.98,-.82)])
  post=box(4.+ee,5.+ee,qc-.55,qc+.55,-.90,4.4)
  post=post.cut(cyl(.5,3.0,4.5+ee,qc,1.7)).clean()
  added=fuse([link,post]).translate((0,0,off));new.append(world(added,port,side))
  # Removable C guide: actual OD upper .86 envelope, bore is proposed 1.20.
  guide=cyl(.8,3.,2.8+ee,qc,1.4).cut(cyl(.6,3.1,2.8+ee,qc,1.35)).cut(box(2.49+ee,3.11+ee,qc-1.,qc,1.35,3.21)).clean()
  p['SPRING_GUIDE_'+str(i)]=world(guide.translate((0,0,off)),port,side)
  cap=fuse([box(2.3+ee,5.4+ee,qc-.80,qc+.80,4.4,4.7),cyl(.7,.3,2.8+ee,qc,4.4)]).cut(cyl(.55,.7,4.5+ee,qc,4.3)).clean()
  p['SPRING_CAP_'+str(i)]=world(cap.translate((0,0,off)),port,side)
  screw=fuse([cyl(.5,3.,4.5+ee,qc,1.7),cyl(.9,.45,4.5+ee,qc,4.7)])
  p['SPRING_SCREW_'+str(i)+'_M1x3_NOMINAL']=world(screw.translate((0,0,off)),port,side)
  length=2.6-lift
  p['SPRING_'+str(i)+'_OD_TOL_ENVELOPE']=world(cyl(.43,length,2.8+ee,qc,1.8+lift).translate((0,0,off)),port,side)
 p['ROOT']=fuse([root,*new])
 for i in range(2):
  cut=world(box(.19,1.01,Q+.051,Q+.081,1.45+5*i,3.01+5*i),port,side)
  p['ROOT']=p['ROOT'].cut(cut).clean();participant(p['ROOT'])
  sidecut=world(box(.40,1.01,Q-.045,Q+.081,1.45+5*i,3.01+5*i),port,side)
  p['ROOT']=p['ROOT'].cut(sidecut).clean();participant(p['ROOT'])
 if not present:del p['KEY']
 for n,v in p.items():
  try:participant(v)
  except Exception as ex:
   print(json.dumps({"invalid_part":n,"solids":len(v.Solids()),"valid":v.isValid(),"error":str(ex)}),flush=True);raise
 return p
def checks(p):
 changed={n for n in p if n.startswith(('SPRING_','STOP_')) or n=='ROOT'}
 bb={n:CheckedBody(s) for n,s in p.items()};guard=Checker();rows=[]
 for a,b in itertools.combinations(p,2):
  if a not in changed and b not in changed:continue
  row=guard.common(bb[a],bb[b]);rows.append({'parts':[a,b],'checked_volume_mm3':row['checked_common_mm3'],'OCC_boolean_was_run':row['proof']=='actual_valid_signed_OCC_common_bounded_by_validated_inputs',**row})
 return rows
def export(parts,name):
 folder=HERE/'cad';folder.mkdir(exist_ok=True);a=cq.Assembly(name=name)
 for n,s in parts.items():a.add(s,name=n)
 path=folder/(name+'.step');a.save(str(path),exportType='STEP')
 leaves,topology=identity.import_whole(path)
 actual=sorted(b.volume for b in leaves);expected=sorted(participant(s)['signed_volume_mm3'] for s in parts.values())
 diagnostic={'actual_count':len(actual),'expected_count':len(expected),'actual_volumes':actual,'expected_volumes':expected,'max_volume_delta':max((abs(x-y) for x,y in zip(actual,expected)),default=0)}
 (HERE/(name+'_reimport_diagnostic.json')).write_text(json.dumps(diagnostic,indent=2)+'\n')
 assert len(actual)==len(expected) and all(abs(x-y)<1e-6 for x,y in zip(actual,expected))
 return {'path':str(path.relative_to(HERE)),'sha256':sha(path),'complete_payload':topology,'expected_solid_count':len(parts),'independent_reimport_count_and_volumes_match':True}
def main():
 start=time.monotonic();before={str(p.relative_to(HERE)):sha(p) for p in (HERE/'inputs').rglob('*') if p.is_file()};rows=[];exports=[]
 for port in ('STOW','OPEN'):
  sources,topology=source(port)
  for state,lift,present in [('CAM_SUPPORTED',1.14,True),('ABSENT_LOWER_STOP',-.02,False),('FORCED_UPPER',1.20,False)]:
   combined={}
   for side in 'LR':
    parts=derived(port,side,sources[side],lift,present);pairs=checks(parts)
    bad=[r for r in pairs if r['checked_volume_mm3']>EPS]
    rows.append({'port':port,'side':side,'state':state,'lift_mm':lift,'installed_nominal_spring_length_mm':2.6-lift,'source_whole_payload':topology,'pairs':pairs,'positive_intersections':bad})
    (HERE/'incremental-pairs.json').write_text(json.dumps(rows,indent=2)+'\n')
    combined.update({side+'_'+n:s for n,s in parts.items()})
    print(json.dumps({'port':port,'side':side,'state':state,'positive_intersections':len(bad),'max_mm3':max((r['checked_volume_mm3'] for r in bad),default=0)}),flush=True)
   if not any(r['positive_intersections'] for r in rows if r['port']==port and r['state']==state):exports.append(export(combined,port+'_'+state))
 after={str(p.relative_to(HERE)):sha(p) for p in (HERE/'inputs').rglob('*') if p.is_file()};assert before==after
 bad=[{'port':r['port'],'side':r['side'],'state':r['state'],'pairs':r['positive_intersections']} for r in rows if r['positive_intersections']]
 result={'revision':'new actual R6 recovery candidate; no R5 evidence reconstructed','host':platform.node(),'cadquery':cq.__version__,'source_sha256':sha(__file__),'input_sha256':before,'inputs_unchanged':True,'actual_rows':rows,'row_count':len(rows),'pair_count':sum(len(r['pairs']) for r in rows),'actual_OCC_common_count':sum(q['OCC_boolean_was_run'] for r in rows for q in r['pairs']),'unresolved_positive_intersections':bad,'STEP_exports':exports,'selected_spring':None,'spring_envelope_source':'Lee Spring CBM010A03E public nominal OD .81 +/- .05, free length 3, k .330 +/-10%, solid height upper 1.2537','spring_is_solid_occupancy_envelope_not_vendor_helical_STEP':True,'finite_force_retraction_limit_N':None,'physical_qualification':False,'phone_installation_validated':False,'fixture_fabrication_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
 (HERE/'build-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'rows':len(rows),'bad_rows':len(bad),'elapsed':result['elapsed_seconds']}),flush=True)
 if bad:raise ValueError('New candidate has real interference; all failures and STEP retained')
if __name__=='__main__':main()
