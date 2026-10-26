"""Describe actual full-scene bodies without inventing a material assignment."""
from __future__ import annotations


MISSING = ('material_grade', 'elastic_modulus_MPa', 'poisson_ratio',
           'density_kg_m3', 'yield_or_allowable_stress_MPa',
           'process_and_wall_tolerances', 'contact_friction',
           'joint_stiffness_and_fastener_preload')


def provenance(name, metadata):
    """Use actual partition/relief metadata; other role labels are descriptive."""
    scene = metadata['scene']
    partitions = [row for row in scene.get('partition_checks', [])
                  if name in row['replacement_parts']]
    reliefs = [row for row in metadata['research_relief']['changes'] if row['part'] == name]
    functions = ['integration/product_nominal_motion.py:full_scene']
    if name == 'EP5_finite_material':
        category = 'finite_FPC_geometric_material'
        functions += ['integration/product_routing_ep5.py:finite_material_solid']
    elif name == 'OLED_GEOMETRIC_TRIAL':
        category = 'finite_OLED_geometric_trial'
        functions += ['integration/oled_storage.py:geometry']
    elif name.endswith('_ALLOCATION'):
        category = 'design_allocation_box_not_actual_supplier_component'
        functions += ['integration/product_assembly.py:registered_components']
    elif name.startswith(('L_', 'R_', 'FRAME_', 'CARTRIDGE_')) or name in (
            'A_FRAME', 'A_BACK_PANEL', 'B_SHELL', 'A_DISPLAY_SUPPORT',
            'B_OPEN_DISPLAY_SUPPORT_ACCESSORY'):
        category = 'mechanical_geometry'
        functions += ['integration/product_assembly.py:product_scene',
                      'integration/product_split_assembly.py:split_scene']
        if 'NOMINAL' in name:
            category = 'nominal_fastener_geometry_without_thread_or_preload_qualification'
        elif 'SPRING' in name:
            category = 'spring_outer_diameter_tolerance_envelope_not_constitutive_spring'
        elif name in ('A_FRAME', 'A_BACK_PANEL', 'B_SHELL'):
            category = 'current_relieved_housing_geometry_requires_new_structural_model'
    else:
        category = 'EP5_endpoint_finite_geometry'
        functions += ['integration/product_routing_ep5.py:endpoint_parts',
                      'integration/product_fpc.py:place_endpoint']
    if reliefs:
        functions += ['integration/product_routing_ep5.py:apply_scene_relief']
    return {'descriptive_role': category, 'source_functions': functions,
            'actual_parent_partition_records': partitions,
            'actual_EP5_relief_records': reliefs,
            'material_assignment_present': False,
            'missing_structural_properties': list(MISSING),
            'old_PR34_structural_result_applicable': False}


def measure(parts, metadata, assembly):
    result = {}
    for name, body in sorted(parts.items()):
        solids, volume = assembly.whole_material(body)
        bounds = list(assembly.bounds(body))
        result[name] = {'volume_mm3': volume, 'bounds_mm': bounds,
                        'solid_count': len(solids),
                        'bbox_dimensions_mm': [bounds[i+1]-bounds[i] for i in (0, 2, 4)],
                        'bbox_dimensions_are_not_wall_thickness': True,
                        **provenance(name, metadata)}
    return result
