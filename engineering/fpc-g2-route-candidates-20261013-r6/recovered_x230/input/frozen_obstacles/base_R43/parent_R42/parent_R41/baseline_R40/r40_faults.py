"""R40 negative safety and integration gate matrix. Not physical qualification."""
import json,hashlib
from r40_motion import ROOT,solve

def run(write=True):
    st=solve(0,0,16.5,119.);dock=solve(79.75,8.2,16.5,119.)
    pre=solve(79.75,0,16.5,119.)
    source=json.loads((ROOT/'baseline_R38/verification/R38_faults.json').read_text())
    R39_original=hashlib.file_digest(open(ROOT/'baseline/RAZR_SLIDE_R39_FPC_motion_hardgate_20261012.zip','rb'),'sha256').hexdigest()
    faults=[
      {'id':'F-FPC-PROTECTED-CORE','severity':'HOLD','observation':'5/5 OCC research sweeps intrude into original B-protected chassis'},
      {'id':'F-FPC-OLED','severity':'HOLD','observation':'4/5 named OCC sweeps intersect unapproved OLED proxy'},
      {'id':'F-RELOCATED-B-HEADER','severity':'HOLD','observation':'B terminal displaced -32.7mm in X; original B core occupied by catalogue proxy'},
      {'id':'F-HALF-SPEED-GUIDE','severity':'HOLD','observation':'Ideal U reversal must move approximately half the slide distance and also shift under Z docking; no mechanism exists'},
      {'id':'F-UNQUALIFIED-STRIP','severity':'HOLD','observation':'1.2mm width, 0.15mm thickness, R15 screening unlicensed; no OEM stack or supplier lifetime data'},
      {'id':'F-NO-POWER-BOARD','severity':'HOLD','observation':'Old 3 single-point PCB cross-bypasses and dual battery hot-plug/isolation unresolved'},
      {'id':'F-USB-SI','severity':'HOLD','observation':'Static Hirose header envelope does not prove connector pair, FPC impedance, eye/BER/EMI'},
      {'id':'F-LOCK','severity':'HOLD','observation':'36 of 64 old combined mechanical escape conditions retained, physical capture unverified'},
    ]
    for a in faults:assert a['severity']=='HOLD'
    out={'revision':'R40 rolling-U FPC screen, no manufacture release',
      'original_R39_zip_sha256':R39_original,
      'guide_U_top_y_stow_mm':round(st['U_top_y_mm'],8),
      'guide_U_top_y_predock_mm':round(pre['U_top_y_mm'],8),
      'guide_U_top_y_docked_mm':round(dock['U_top_y_mm'],8),
      'guide_required_y_travel_slide_mm':round(pre['U_top_y_mm']-st['U_top_y_mm'],8),
      'guide_required_y_shift_dock_mm':round(dock['U_top_y_mm']-pre['U_top_y_mm'],8),
      'guide_requires_unbuilt_separate_position_control':True,
      'R38_parent_power_hazard_modes':source['R37_original_power_single_bypass'],
      'fault_gates':faults,'all_gates_hold':all(f['severity']=='HOLD' for f in faults),
      'production_safety_circuit_built':False,'live_connection_tested':False,
      'FPC_vendor_approved':False,'manufacturing_go':False}
    if write:(ROOT/'verification/R40_faults.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    return out
if __name__=='__main__':run()
