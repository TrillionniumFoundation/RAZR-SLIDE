"""Export separate 3D ribbon BRep for geometry inspection, all rejected GHOSTs."""
import json,hashlib,cadquery as cq
from r25_capture import ROOT
from r39_export import CHOSEN,SCENES,loft_ribbon
from r39_screen import CANDIDATES
from r39_path import curve

def run():
    rec=[]
    for i,(which,tag) in enumerate(CHOSEN,1):
        _,s,q=next(a for a in SCENES if a[0]==tag)
        _,c,L=next(a for a in CANDIDATES if a[0]==which)
        rib=loft_ribbon(curve(c,s,q,n=81,target=L))
        f=ROOT/'cad'/f'R39_RIBBON_{i:02d}_GHOST_{which}_{tag}.brep'
        cq.exporters.export(rib,str(f))
        loaded=cq.importers.importBrep(str(f)).val()
        assert loaded.isValid() and len(loaded.Solids())==1
        rec.append(dict(file=f.name,sha256=hashlib.sha256(f.read_bytes()).hexdigest(),solids=len(loaded.Solids()),
            volume_mm3=round(loaded.Volume(),7),physical_OEM_cable=False))
    data=dict(note='R39 negative-only 3D ribbon research BReps, not functional cable',count=len(rec),records=rec,
         all_unsafe_ghost=True,manufacturing_go=False)
    (ROOT/'verification/R39_ribbon_BREP_manifest.json').write_text(json.dumps(data,indent=2)+'\n')
    print('R39 RIBBON BREP',len(rec),flush=True)
if __name__=='__main__':run()
