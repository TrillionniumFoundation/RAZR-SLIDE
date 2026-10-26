"""Ideal beam sensitivity for the new KEY yoke's nominal narrow tab.

The 23.8 mm CAD extent is not a measured unsupported span. Material, real
supports, loads and force path remain unknown. Euler loads and linear beam
deflections are scenario calculations, never hardware acceptance or allowables.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


CAM_SOURCE_SHA256 = '4a3bf1d2b86d31fa8e3d60d3412e15548bf42287ed95d756798f3d88c6c4e631'
KEY_YOKE_STEP_SHA256 = 'a819b786a0d7f2a406194b60908233b106af6ed11988b4216c5e4e4d101aab94'
NATIVE_V5_ARCHIVE_SHA256 = '249f50dae36b591df189e17ed8f46b1d1e793d481b1d0fb57f0ff1a553dfbd07'


def positive(value, label):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError(label+': positive finite real value required')
    return float(value)


def section_properties(width_x_mm, thickness_z_mm):
    """Uniform rectangular section normal to beam axis Y."""
    b, h = positive(width_x_mm, 'width'), positive(thickness_z_mm, 'thickness')
    area = b*h
    ix, iz = b*h**3/12, h*b**3/12
    return {'width_x_mm': b, 'thickness_z_mm': h, 'area_mm2': area,
            'I_about_x_mm4': ix, 'I_about_z_mm4': iz,
            'weak_I_mm4': min(ix, iz), 'weak_radius_of_gyration_mm': math.sqrt(min(ix, iz)/area)}


def cantilever_stiffness_N_per_mm(E_GPa, span_mm, I_mm4):
    """Hypothetical one-clamp beam with transverse load at its free end."""
    e, length, inertia = positive(E_GPa, 'E')*1000, positive(span_mm, 'span'), positive(I_mm4, 'I')
    return 3*e*inertia/length**3


def euler_load_N(E_GPa, span_mm, I_mm4, effective_length_factor):
    e, length, inertia = positive(E_GPa, 'E')*1000, positive(span_mm, 'span'), positive(I_mm4, 'I')
    k = positive(effective_length_factor, 'effective length factor')
    return math.pi**2*e*inertia/(k*length)**2


def build_study():
    section = section_properties(.25, .30)
    rows = []
    for e in (2., 70., 200.):
        for length in (23.8, 12., 8., 4.):
            kx = cantilever_stiffness_N_per_mm(e, length, section['I_about_z_mm4'])
            kz = cantilever_stiffness_N_per_mm(e, length, section['I_about_x_mm4'])
            rows.append({'assumed_E_GPa': e, 'assumed_unsupported_span_mm': length,
                'hypothetical_cantilever_end_stiffness_N_per_mm': {'x_deflection': kx, 'z_deflection': kz},
                'hypothetical_cantilever_end_displacements': [
                    {'assumed_transverse_force_N': force, 'x_deflection_mm': force/kx,
                     'z_deflection_mm': force/kz, 'x_deflection_over_span': force/kx/length}
                    for force in (1e-6, 1e-5, 1e-4)],
                'ideal_euler_axial_buckling': [
                    {'effective_length_factor': k,
                     'weak_axis_load_N': euler_load_N(e, length, section['weak_I_mm4'], k),
                     'about_x_load_N': euler_load_N(e, length, section['I_about_x_mm4'], k),
                     'about_z_load_N': euler_load_N(e, length, section['I_about_z_mm4'], k),
                     'effective_slenderness_weak_axis': k*length/section['weak_radius_of_gyration_mm']}
                    for k in (.5, 1., 2.)]})
    losses = []
    for label, loss in (('each_total_cross_section_dimension_reduced_by_0p02_mm', .02),
                        ('each_opposed_outer_face_moves_inward_0p02_mm', .04)):
        reduced = section_properties(.25-loss, .30-loss)
        losses.append({'hypothesis': label, 'total_dimension_reduction_mm': loss,
                       'section': reduced,
                       'relative_loss': {key: 1-reduced[key]/section[key] for key in
                                         ('area_mm2', 'I_about_x_mm4', 'I_about_z_mm4')},
                       'is_manufacturing_tolerance': False})
    improvements = []
    for b, h in ((.30, .30), (.35, .40), (.50, .60)):
        enlarged = section_properties(b, h)
        improvements.append({'assumed_section': enlarged,
                             'weak_I_ratio_to_nominal': enlarged['weak_I_mm4']/section['weak_I_mm4'],
                             'geometry_clearance_or_admission_verified': False})
    return {'scope': 'ideal_rectangular_beam_parameter_sensitivity_only',
        'nominal_geometry': {'beam_axis': 'Y', 'tab_lower_xyz_mm': [13.2, 15.8, 4.05],
                            'tab_upper_xyz_mm': [13.45, 39.6, 4.35],
                            'nominal_Y_extent_mm': 23.8, 'section': section},
        'geometry_provenance': {'construction_source': 'integration/cam_coupling.py',
            'construction_source_sha256': CAM_SOURCE_SHA256,
            'main_commit': 'a1b3cc1e0773446f2e36d0a607edf61211dd9919',
            'current_role': 'L_KEY_YOKE.step', 'current_role_expected_sha256': KEY_YOKE_STEP_SHA256,
            'native_v5_archive_expected_sha256': NATIVE_V5_ARCHIVE_SHA256,
            'original_L_ORIGINAL_KEY_does_not_represent_this_added_web': True,
            'step_or_brep_remeasured_by_this_script': False},
        'formulas': {'E_N_per_mm2': '1000 * E_GPa', 'A': 'b*h',
            'I_about_x': 'b*h^3/12', 'I_about_z': 'h*b^3/12',
            'hypothetical_cantilever_end_stiffness': '3*E*I/L^3',
            'hypothetical_cantilever_end_deflection': 'F*L^3/(3*E*I)',
            'ideal_euler_load': 'pi^2*E*I/(K*L)^2'},
        'effective_length_factor_idealizations': {'0.5': 'both ends fully fixed',
            '1.0': 'both ends pinned', '2.0': 'one end fixed, other end free'},
        'assumptions': ['homogeneous isotropic linearly elastic straight uniform section',
            'ideal end conditions; centered axial compression for Euler estimate',
            'small deflection required for the lateral beam formula',
            'Euler estimate may exceed yield or be inapplicable at low slenderness',
            'guide clearance, imperfect straightness, notches, torsion and local stresses omitted'],
        'unknown_actual_inputs': ['material and modulus', 'yield and fatigue data',
            'unsupported spans and guide stiffness/clearance', 'axial and lateral load histories',
            'load eccentricity and connection stiffness'],
        'parameter_cases': rows, 'hypothetical_dimension_loss': losses,
        'hypothetical_section_increases': improvements,
        'span_reduction_ratios': [{'assumed_span_mm': length,
            'lateral_stiffness_ratio_same_support_type': (23.8/length)**3,
            'euler_load_ratio_same_K': (23.8/length)**2} for length in (12., 8., 4.)],
        'actual_load_or_boundary_condition_known': False,
        'strength_qualified': False, 'physical_failure_inferred': False,
        'new_fe_solve': False, 'candidate_go': False,
        'fixture_fabrication_go': False, 'manufacturing_go': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).parent/'cam_coupling.py'
    if hashlib.sha256(source.read_bytes()).hexdigest() != CAM_SOURCE_SHA256:
        parser.error('nominal geometry source changed; rederive the dimensions')
    report = build_study()
    report['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'parameter_rows': len(report['parameter_cases']),
                      'nominal_section': report['nominal_geometry']['section'],
                      'strength_qualified': False}))


if __name__ == '__main__':
    main()
