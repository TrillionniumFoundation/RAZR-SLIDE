"""Independent R20 gates and reproducible combined machine-readable results."""
import json,hashlib,unittest,io,sys
from pathlib import Path
from r20_model import ROOT,tolerance_budget,screen_oled_limit,model_report
from r20_cad import run as cad_run
from r20_packaging import run as pack_run
from test_r20 import TestR20
OUT=ROOT/'verification';OUT.mkdir(exist_ok=True)
def collect():
 cad=cad_run(write=True);pack=pack_run();bud=tolerance_budget();g=screen_oled_limit()
 stream=io.StringIO()
 tr=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TestR20))
 (OUT/'R20_tests.txt').write_text(stream.getvalue())
 assert tr.wasSuccessful(),stream.getvalue()
 assert len(cad['rows'])==9 and len(pack['results'])==2
 assert cad['rows'][4]['collisions']['L_block_mm3']>0
 assert cad['rows'][5]['collisions']['R_block_mm3']>0
 assert pack['results'][0]['crosstalk_intersect_mm3']['B_CORE_RECESSED_PROXY']>0
 assert pack['results'][1]['crosstalk_intersect_mm3']['B_OPEN_FLOATING_ISLAND_PROXY']>0
 data=dict(**model_report(),methodology={'unit_tests':tr.testsRun,'all_pass':tr.wasSuccessful(),
                 'CAD_poses':len(cad['rows']),'body_comparison_stages':len(pack['results']),
                 'R19_30_tests_rechecked_separately':True},
       local_CAD_summary=cad,assembly_negative=pack,
       safety_decision='REJECT: both-dog false opening; B core contact-housing overlaps; aged tolerance and OLED not approved')
 (OUT/'R20_results.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 return data
if __name__=='__main__':
 d=collect();print(json.dumps(dict(tests=d['methodology']['unit_tests'],poses=9,
     stow_body_clash_mm3=d['assembly_negative']['results'][0]['crosstalk_intersect_mm3']['B_CORE_RECESSED_PROXY'],
     open_island_clash_mm3=d['assembly_negative']['results'][1]['crosstalk_intersect_mm3']['B_OPEN_FLOATING_ISLAND_PROXY'],
     room_temp_window=d['tolerance']['preliminary_room_temp'],aging_window=d['tolerance']['thermal_wear'],
     release=False),ensure_ascii=False,indent=2))
