#!/usr/bin/env python3
"""One serialized board, one fresh native KiCad process, one actual DRC.

An in-memory multiple-board invocation omitted copper-clearance errors on a
real injected short. Reloading that exact board in a fresh native process
restored them. This helper requires the actual proposed project constraints;
no rule exclusions, severity edits or report-label normalization are applied.
"""
from pathlib import Path
import hashlib,json,re,sys
import pcbnew
source=Path(sys.argv[1]).resolve(); report=Path(sys.argv[2]).resolve()
b=pcbnew.LoadBoard(str(source));b.BuildConnectivity();s=b.GetDesignSettings()
rules={'min_clearance_mm':pcbnew.ToMM(s.m_MinClearance),'hole_clearance_mm':pcbnew.ToMM(s.m_HoleClearance),
       'netclass_clearance_mm':{k:pcbnew.ToMM(v.GetClearance()) for k,v in b.GetAllNetClasses().items()}}
assert rules['min_clearance_mm']==.1 and rules['hole_clearance_mm']==.25 and rules['netclass_clearance_mm']['Default']==.1,rules
assert pcbnew.WriteDRCReport(b,str(report),pcbnew.EDA_UNITS_MILLIMETRES,True)
text=report.read_text();counts={key:int(re.search(r'Found (\d+) '+key,text)[1]) for key in ('DRC violations','unconnected pads','Footprint errors')}
print(json.dumps({'engine':pcbnew.Version(),'serialized_board':source.name,'board_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'rules':rules,'counts':counts,'native_unconnected':b.GetConnectivity().GetUnconnectedCount(False),'fresh_native_process':True}))
