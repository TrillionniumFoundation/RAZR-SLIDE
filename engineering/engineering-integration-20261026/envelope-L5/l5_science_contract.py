"""Frozen L5 science names, total bounds and independent record validation."""
from fractions import Fraction as F
import math
import ast
import hashlib
import json
from pathlib import Path
import re
import cylindrical_sweep_l5 as l5
from exact_xy_support_l5 import support_certificate

CASE_NUMBERS=('011','012','013','014','016','017','018')
CONTROL_NAMES=('ordinary','reversed','zero','tiny')
FALSE_FLAGS=('full_11781_pair_execution','independent_5D_or_SEATING_domain_proved',
             'K3_candidate_qualification','physical_qualification','candidate_go','manufacturing_go')


def require(ok,message):
    if not ok:raise ValueError(message)


def scientific_filename(name):
    if name in ('report.json','NATIVE_READBACK.json','INDEPENDENT_RECORD_CHECK.json'):
        return True
    case=r'(?:original|current)-case-(?:011|012|013|014|016|017|018)'
    if re.fullmatch(case+r'\.json',name):return True
    labels=(r'(?:moving-input|fixed-input|layer-[0-2]|actual-layer-[0-2]|whole-reconstructed|'
        r'carrier-[0-2]|layer-[0-2]-(?:bridge(?:-difference)?|endpoint-[01](?:-difference)?|short-disk|assembled-union|Common)|inner-lens-[0-2]|'
        r'carrier-union|whole-source-omission|negative-intruding-complete-input)')
    if re.fullmatch(case+'-'+labels+r'\.brep',name):return True
    if re.fullmatch(case+r'-(?:moving-input|fixed-input)\.step',name):return True
    if re.fullmatch(r'control-(?:ordinary|reversed|zero|tiny)-(?:capsule-(?:bridge(?:-difference)?|endpoint-[01](?:-difference)?|short-disk|assembled-union)|whole-carrier|source-disk|sample-[0-4])\.brep',name):return True
    if re.fullmatch(r'control-original-extrusion-(?:original-shape|original-face)\.(?:brep|step)',name):return True
    return re.fullmatch(r'control-original-extrusion-v2-region-[0-9]+\.brep',name) is not None


def validate_result(result,target,spec,root,guard):
    require(result['schema']==l5.SCHEMA and result['original_volume_gate_mm3']==1e-7,'new schema or original total gate changed')
    require(all(result[k] is False for k in FALSE_FLAGS),'unsupported scope or physical qualification')
    require(result['formal_interval_CAD_certificate'] is False and result['sampled_checks_are_not_continuous_proof'] is True,'native interval/sample claim changed')
    geometry=l5.plan(target,spec,l5.source_sections(root));audit=result['audit']
    require(geometry==audit['source_motion_and_sections'],'complete original source plan changed')
    n=len(geometry['layers']);checks=audit['carrier_checks'];layers=audit['layers']
    require(len(checks)==len(layers)==result['complete_original_pair_all_layers_count']==n,'complete axial layer inventory omitted')
    for key in ('a_minus_b_mm3','b_minus_a_mm3'):
        values=[x['actual_layer_identity'][key] for x in layers]
        require(all(type(x) in (int,float) and math.isfinite(x) and x>=0 for x in values),'negative/invalid source layer difference')
        require(math.fsum(values)<=1e-7 and 0<=audit['complete_input_identity'][key]<=1e-7,'complete material reconstruction failed')
    common=[]
    for i,(row,source) in enumerate(zip(checks,geometry['layers'])):
        require(row['layer_index']==layers[i]['index']==i,'source layer order changed')
        c=row['construction'];require(c['annular_inner_hole_filled_for_conservative_cover'] is True,'unreviewed inner-lens route enabled')
        require(c['native_radius_mm']>=source['outer_native_radius'],'source radius shrank')
        low,high=map(F,row['carrier_z_native_with_actual_bound_union']);dzlo,dzhi=map(F,geometry['reverse_independent_Z_interval_exact'])
        bound=layers[i]['actual_layer_native_bounds_mm']
        require(low<=min(F(source['carrier_z_exact'][0]),F(bound[4])+dzlo) and high>=max(F(source['carrier_z_exact'][1]),F(bound[5])+dzhi),'source or native Z extent shrank')
        if c['method']=='positive_disk_capsule_prism':
            proof=c['XY_bridge_support'];points=proof['native_bridge_XY_vertices']
            actual=support_certificate(geometry['centerline_endpoints_native'],source['outer_native_radius'],points)
            require(actual['continuous_rectangle_contained'] and actual==proof['construction_attempts'][proof['accepted_attempt']]['support_certificate'],'actual rounded bridge support certificate mismatch')
            require(c['native_bridge_topology']['native_vertex_XY_equals_certified_quad'] is True,'uncertified actual native bridge')
            require(all(x['full_directed_Z_interval_contained'] is True for x in c['native_bridge_topology']['native_Z_vertex_checks']),'native Z extent omitted')
            values=[x['outside_mm3'] for x in c['component_containment_checks']]
            require(len(values)==3 and all(0<=x<=1e-7 for x in values) and math.fsum(values)<=1e-7,'native union omitted a component')
        else:
            require(c['method']=='short_segment_containing_disk' and c['nonzero_displacement_not_dropped'] is True,'unknown short carrier construction')
        static=row['static'];guard.validate_frame(static['original_static_carrier_postguard_record'])
        value=static['strict_common']['common_mm3'];common.append(value)
        record=static['original_static_carrier_postguard_record']
        require(value==record.get('common_upper_bound_mm3',record.get('examined_region_common_sum_mm3')),'static carrier Common bound differs')
    path=Path(root)/'integration/translation_regions.py';data=path.read_bytes()
    binding=json.loads((Path(__file__).resolve().parent/'L5_ORIGINAL_SEVEN_BINDING.json').read_text())
    require(hashlib.sha256(data).hexdigest()==binding['source_files']['integration/translation_regions.py']['sha256'],
        'original total-bound source differs')
    function=next(n for n in ast.parse(data).body if isinstance(n,ast.FunctionDef) and n.name=='sum_common_upper_bound')
    namespace={'math':math};exec(compile(ast.Module(body=[function],type_ignores=[]),'<unchanged original pure sum>','exec'),namespace)
    sum_common_upper_bound=namespace['sum_common_upper_bound']
    carrier_sum=sum_common_upper_bound(common)
    omission=audit['whole_source_omission'];component_losses=[x for row in checks for x in row['construction'].get('component_containment_checks',[])]
    omitted=omission['signed_volume_mm3'];component_sum=math.fsum(x['outside_mm3'] for x in component_losses)
    upper=sum_common_upper_bound([carrier_sum,omitted,component_sum])
    strict=bool(omission['actual_difference_has_no_solid_material'] and all(x['difference_has_no_solid_material'] for x in component_losses))
    require(not strict or omitted==component_sum==0.,'nonzero omission asserted as strict containment')
    volume=audit['whole_pair_volume_error_budget']
    require(volume['carrier_Common_sum_mm3']==carrier_sum and volume['whole_source_omission_once_mm3']==omitted
        and volume['capsule_component_omission_sum_mm3']==component_sum and volume['complete_per_pose_Common_upper_bound_mm3']==upper,
        'whole-source or capsule material omission budget missing')
    require(upper==result['common_upper_bound_mm3'],'whole pair sum altered')
    require(result['original_per_pose_volume_predicate_disposition']==('clear' if upper<=1e-7 else 'unresolved_enclosure_overlap'),'original complete-pair threshold changed')
    expected=('clear' if strict else 'unresolved_source_containment') if upper<=1e-7 else 'unresolved_enclosure_overlap'
    require(result['disposition']==expected,'strict inclusion or volume disposition changed')
    require(all(0<=x['outside_mm3']<=1e-7 for x in audit['finite_whole_material_containment_checks']),'finite implementation check failed')
    negative=audit['negative_control'];negative_values=[]
    for x in negative['checks']:
        guard.validate_frame(x['original_static_carrier_postguard_record']);negative_values.append(x['strict_common']['common_mm3'])
    require(len(negative_values)==n and sum_common_upper_bound(negative_values)==negative['sum_mm3']>1e-7,'whole-input penetration negative control did not reject')
    require(result['original_static_postguards_passed'] and result['negative_control_passed'] and result['actual_whole_source_reconstruction_passed'],'incomplete native material/postguard evidence')
    return True
