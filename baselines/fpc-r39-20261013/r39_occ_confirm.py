"""Exact OCC solid Boolean interference only at six representative GHOST scenes.
A positive intersection is definitive for this geometric proxy at this pose;
zero does not establish collision-free continuous motion or tolerance closure.
"""
import json,time
import cadquery as cq
from r25_capture import ROOT,P
from r24_mechanics import r21
from r39_export import CHOSEN,SCENES,loft_ribbon
from r39_screen import CANDIDATES
from r39_path import curve

def run():
    A=cq.importers.importBrep(str(ROOT/'cad/R38_A_R37_BYTE_IDENTICAL.brep')).val()
    B=cq.importers.importBrep(str(ROOT/'cad/R38_B_PROVISIONAL_STATIC_HEADER_CLEARANCE.brep')).val()
    out=[]
    for key,tag in CHOSEN:
        cn,L=next((c,l) for n,c,l in CANDIDATES if n==key)
        s,q=next((s,q) for n,s,q in SCENES if n==tag)
        body=loft_ribbon(curve(cn,s,q,n=81,target=L))
        ref=r21.r17_assembly(P,s,q,1 if tag=='OPEN' else 0)
        solid_map={'A_chassis':A,'B_chassis':B.translate((0,s,q-P.z_travel)),
          'OLED_study_proxy':ref['OLED'],'existing_display_FPC_proxy':ref['FPC']}
        collisions={}
        for name,solid in solid_map.items():
            t=time.monotonic()
            try:
                overlap=solid.intersect(body)
                vol=float(overlap.Volume())
                collisions[name]=dict(intersect_mm3=round(vol,8),boolean_success=True,seconds=round(time.monotonic()-t,3))
            except Exception as e:
                collisions[name]=dict(boolean_success=False,error=f'{type(e).__name__}: {e}')
        out.append(dict(candidate=key,pose=tag,slide_mm=s,dock_mm=q,
         full_3d_ribbon_study_volume_mm3=round(body.Volume(),7),
         intersection_details=collisions,
         any_confirmed_penetration=any(v.get('intersect_mm3',0)>1e-7 for v in collisions.values())))
        print('OCC BOOLEAN',key,tag,[(n,c.get('intersect_mm3')) for n,c in collisions.items()],flush=True)
    result=dict(revision='R39 full 3D OCC interferences for SIX SELECTED scenes (not continuous sweep)',
      count=len(out),scenes=out,all_scenes_have_positive_Occ_Boolean_penetration=all(x['any_confirmed_penetration'] for x in out),
      manufacturing_go=False)
    (ROOT/'verification/R39_selected_OCC_boolean.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result
if __name__=='__main__':run()
