"""Full source-modified regions, not point probes or a whole-part wall claim."""
from pathlib import Path
import ast
import hashlib
import json

HERE=Path(__file__).resolve().parent

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def literals(path):
    out={}
    for n in ast.parse(Path(path).read_text()).body:
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
            try: out[n.targets[0].id]=ast.literal_eval(n.value)
            except (ValueError,TypeError): pass
    return out

def mirrored(box,side):
    lo,hi=[list(x) for x in box]
    if side=='L': lo[0],hi[0]=-hi[0],-lo[0]
    return [lo,hi]

def build():
    k1=literals(HERE/'inputs/key_forward_loop_v1.py')
    c1=json.loads((HERE/'inputs/KEY_FORWARD_LOOP_V1_CONTRACT.json').read_text())
    c3=json.loads((HERE/'inputs/PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json').read_text())
    assert c1['candidate_source_sha256']==sha(HERE/'inputs/key_forward_loop_v1.py')
    assert c3['candidate_source_sha256']==sha(HERE/'inputs/panel_key_travel_stops_v1.py')
    assert c3['design_contract']['required_K1_contract_sha256']==sha(HERE/'inputs/KEY_FORWARD_LOOP_V1_CONTRACT.json')
    assert json.loads(json.dumps(k1['ADDITIONS']))==c1['design_contract']['added_boxes_R_local_q0_mm']
    regions={}
    R={
        'K1_entire_cut_loop_and_two_old_web_junctions':{
            'body':'KEY','window':[[16.9,4.9,3.9],[18.96,15.6,4.5]],
            'boxes':{**k1['ADDITIONS'],
                     'old_inboard_web_retained':[[16.9,14.,4.02],[17.38,15.5,4.38]],
                     'old_outboard_web_retained':[[18.48,14.,4.02],[18.96,15.5,4.38]]},
            'derived_from_named_source':['ADDITIONS','CUT'],
            'inherited_material_model_pending_native_readback':['old_inboard_web_retained','old_outboard_web_retained'],
            'full_declared_cutter':k1['CUT'],
            'source_lower_bound_on_added_prism_membership':True,
            'original_web_source_not_reconstructed_from_parent_CSG':True},
        'K3_lower_post_and_full_local_panel_thickness':{
            'body':'A_BACK_PANEL','window':[[17.38,4.3,0.],[18.48,5.1,4.5]],
            'boxes':{'local_panel_base':[[17.38,4.3,0.],[18.48,5.1,.65]],
                     'lower_post':c3['design_contract']['additive_boxes_R_mm']['lower_post']},
            'derived_from_named_source':['additive_boxes_R_mm.lower_post'],
            'inherited_material_model_pending_native_readback':['local_panel_base'],
            'original_panel_source_not_reconstructed_from_parent_CSG':True},
        'K3_upper_toe_entire_overlap_front_post_and_panel':{
            'body':'A_BACK_PANEL','window':[[17.38,17.28,0.],[18.48,19.6,7.1]],
            'boxes':{'local_panel_base':[[17.38,17.28,0.],[18.48,19.6,.65]],
                     'original_front_post':c3['design_contract']['original_front_post_R_mm'],
                     'upper_toe':c3['design_contract']['additive_boxes_R_mm']['upper_toe']},
            'derived_from_named_source':['additive_boxes_R_mm.upper_toe','original_front_post_R_mm'],
            'inherited_material_model_pending_native_readback':['local_panel_base','original_front_post'],
            'original_panel_source_not_reconstructed_from_parent_CSG':True}}
    for side in 'LR':
        for key,value in R.items():
            row=dict(value)
            row['side']=side
            row['body']=side+'_KEY' if row['body']=='KEY' else row['body']
            row['window']=mirrored(row['window'],side)
            row['boxes']={name:mirrored(box,side) for name,box in row['boxes'].items()}
            if 'full_declared_cutter' in row: row['full_declared_cutter']=mirrored(row['full_declared_cutter'],side)
            regions[side+'_'+key]=row
    return {'schema':'razr-r13-full-modified-region-declarations-v1','regions':regions,
            'every_K1_declared_cutter_and_all_three_added_prisms_covered':True,
            'every_K3_added_stop_box_and_entire_declared_front_post_overlap_covered':True,
            'covers_inherited_whole_part_all_previous_cuts':False,
            'native_material_identity':False,
            'whole_part_minimum_wall_or_weakest_section':False,
            'no_motion_or_shape_source_changed':True}

if __name__=='__main__':
    out=HERE/'MODIFIED_REGION_DECLARATIONS.json'
    assert not out.exists()
    r=build();out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'regions':len(r['regions']),'sha256':sha(out)}))
