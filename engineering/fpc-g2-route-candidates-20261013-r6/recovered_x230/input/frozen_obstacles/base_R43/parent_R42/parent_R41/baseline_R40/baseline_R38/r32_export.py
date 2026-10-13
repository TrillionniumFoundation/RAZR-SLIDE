"""R32 research STEP scenes with explicit known-unsafe GHOST witnesses.

All gauges are non-energized packaging solids; STEP export and import are NOT
an electrical interface, continuous operation, assembly-strength or OEM proof.
"""
from __future__ import annotations
import json,hashlib
import cadquery as cq
from r25_capture import ROOT,P
from r24_mechanics import r21
from r30_mechanics import gate,carrier
from r31_presence import interposer,pawl_position
from r22_mechanics import to_global
from r32_cartridge import gauge

SCENES=[
 dict(label='01_STOW_EMPTY_BAY_GAUGES_PRESENT',s=0.,q=0.,A=True),
 dict(label='02_OPEN_FINAL_0p05_BEFORE_SEATED',s=P.travel,q=8.15,A=True),
 dict(label='03_OPEN_SEATED_WITH_INSULATOR_GAUGES',s=P.travel,q=8.2,A=True),
 dict(label='04_GAUGE_LEFT_PARTLY_WITHDRAWN_UNRETAINED_GHOST',s=P.travel,q=8.2,A=False,ly=-1.,ghost=True),
 dict(label='05_GAUGE_WITHDRAWS_UNOPPOSED_GHOST',s=P.travel,q=8.2,A=False,ly=-2.5,ghost=True),
 dict(label='06_GAUGE_RIGHT_HARD_STOP_OVERRUN_GHOST',s=P.travel,q=8.2,A=True,ry=.2,ghost=True),
 dict(label='07_LEGACY_CARRIER_STUCK_EXTENDED_GHOST',s=P.travel,q=8.2,A=True,carrier=.8,ghost=True),
]

def run(write=True):
    A=cq.importers.importBrep(str(ROOT/'cad'/'R32_A_R31_UNMODIFIED.brep')).val()
    B=cq.importers.importBrep(str(ROOT/'cad'/'R32_B_REAR_CASSETTE_BAYS.brep')).val()
    out=[]
    for r in SCENES:
        s,q=r['s'],r['q']
        bg=B.translate((0,s,q-P.z_travel))
        ref=r21.r17_assembly(P,s,q,1. if s==P.travel and q==P.z_travel else 0.)
        parts={'B_R32_BACKED_CASSETTE_CHANNELS':bg,
               'OLED_REFERENCE_NON_OEM':ref['OLED'],
               'FPC_REFERENCE_NON_OEM':ref['FPC']}
        if r['A']:parts['A_R31_UNCHANGED']=A
        for side in 'LR':
            dy=r.get('ly',0.) if side=='L' else r.get('ry',0.)
            parts[f'{side}_NON_ENERGIZED_CASSETTE_GAUGE']=gauge(side,dy).translate((0,s,q-P.z_travel))
            parts[f'{side}_R31_INTERPOSER_UNQUALIFIED']=to_global(interposer(side,0.),'OPEN',s,q)
            parts[f'{side}_OLD_CAPTURE_PAWL_UNQUALIFIED']=to_global(pawl_position(side,0.),'OPEN',s,q)
            parts[f'{side}_OLD_GATE_UNQUALIFIED']=to_global(gate(side,0.),'OPEN',s,q)
            parts[f'{side}_OLD_CARRIER_UNQUALIFIED']=to_global(carrier(side,r.get('carrier',0.)),'OPEN',s,q)
        assembly=cq.Assembly(name='R32_'+r['label'])
        for name,sh in parts.items():
            color=(cq.Color(.86,.29,.26) if 'GHOST' in r['label'] and 'GAUGE' in name else
                cq.Color(.98,.76,.27) if 'GAUGE' in name else
                cq.Color(.29,.72,.72) if 'OLED' in name else
                cq.Color(.72,.32,.48) if 'FPC' in name else
                cq.Color(.24,.46,.75) if name.startswith('B') else cq.Color(.62,.66,.69))
            assembly.add(sh,name=name+'_NOT_MANUFACTURING_RELEASED',color=color)
        dest=ROOT/'cad'/f'R32_{r["label"]}.step'
        assembly.save(str(dest),exportType='STEP')
        reread=cq.importers.importStep(str(dest)).solids().vals()
        if len(reread)!=len(parts) or not all(p.isValid() for p in reread):
            raise RuntimeError(f'STEP reimport error {dest}: {len(reread)} != {len(parts)}')
        rr=dict(name=r['label'],filename=dest.name,parts=len(parts),
                imported_valid_solids=len(reread),ghost_known_unsafe=r.get('ghost',False),
                A_present=r['A'],s_mm=s,q_mm=q,
                size_bytes=dest.stat().st_size,
                sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
        out.append(rr)
        print('R32 STEP',r['label'],'valid',len(reread), 'ghost',rr['ghost_known_unsafe'],flush=True)
    report=dict(revision='R32 packaging-model only with 7 STEP scenes',
      scene_count=len(out),scenes=out,
      no_actual_electrical_contact_or_OEM_OLED_CAD=True,
      contact_carrier_old_failure_must_not_be_counted_as_closed=True,
      manufacturing_go=False)
    if write:(ROOT/'verification'/'R32_STEP_manifest.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    return report
if __name__=='__main__':run()
