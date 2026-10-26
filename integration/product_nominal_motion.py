"""Complete finite-material checks for a bounded, nominal EP5 control domain.

The STOW study allows both manual tabs independently throughout [0, 3] mm
and both native slot flanks throughout [-1, 1]. It includes every current
EP5 participant. Relative rigid translations are enclosed continuously;
overlap of an enclosure is unresolved, never a collision witness by itself.
PREDOCK and OPEN retain released tabs at 3 mm while covering both continuous
slot flank ranges; OPEN includes all seven installed accessories. Every
feasible independent left/right telescope allocation at each fixed pose is
included through its exact linear relative-translation projection.
This does not cover slide/seating, KEY backlash, accessory assembly,
manufacturing tolerances, forces or physical operation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from functools import lru_cache
from fractions import Fraction
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import time

import product_assembly as p
from translation_regions import sum_common_upper_bound

TOL = 1e-7
CONTROL_ROLES = ('TAB', 'THUMB_PAD', 'PAD_SCREW_M06_NOMINAL',
                 'PAWL', 'SHOULDER_PIN_NOMINAL')
TELESCOPE_ROLES = ('TELESCOPE_1', 'TELESCOPE_1_BOTTOM_CAP',
                   'TELESCOPE_2', 'TELESCOPE_2_BOTTOM_CAP')
DOMAIN = ((0., 3.), (0., 3.), (-1., 1.), (-1., 1.))


@lru_cache(maxsize=8)
def fixed_route_parts(slide, descent):
    """Actual unchanged bodies are shared for the same fixed phone pose."""
    import product_routing_ep5 as ep5
    import product_fpc as f
    import oled_storage as oled
    c=ep5.load_config()
    fixed=p.registered_components(p.load_config(),slide,descent)
    fixed['OLED_GEOMETRIC_TRIAL']=oled.geometry(slide,descent)[0]
    sections,_=ep5.route_sections(slide,descent,c)
    material,_=ep5.finite_material_solid(sections,c)
    candidate={'EP5_finite_material':material}
    for end in ('A','B'):
        endpoint,_=ep5.endpoint_parts(end,c)
        candidate.update(f.place_endpoint(endpoint,sections,end))
    if len(candidate)!=41 or len(fixed)!=5:
        raise ValueError('complete route/allocation/OLED material required')
    return {**fixed,**candidate}


def full_scene(slide=0., descent=0., left_tab=0., right_tab=0., **kwargs):
    """Construct the same full EP5 inventory, with explicit mechanism inputs."""
    import product_split_assembly as split
    import product_routing_ep5 as ep5
    c=ep5.load_config()
    baseline,meta=split.split_scene(slide,descent,left_tab,right_tab,**kwargs)
    scene,relief=ep5.apply_scene_relief(baseline,slide,descent,c)
    all_parts={**scene,**fixed_route_parts(slide,descent)}
    if len(all_parts)!=len(baseline)+46:
        raise ValueError('complete EP5 material inventory changed')
    return all_parts, {'scene':meta,'research_relief':relief,
                       'mechanical_participants':len(baseline),
                       'candidate_participants':41,'combined_participants':len(all_parts)}


def controls_coefficients(names, slots):
    """Per-body affine translations in (uL, uR, flankL, flankR)."""
    expected = {side+'_'+role for side in 'LR' for role in CONTROL_ROLES}
    if not expected <= set(names):
        raise ValueError('a complete independent control body was omitted')
    result = {name: [[0., 0., 0.] for _ in DOMAIN] for name in names}
    for index, side in enumerate('LR'):
        for role in CONTROL_ROLES[:3]:
            result[side+'_'+role][index][1] = 1.
        for role in CONTROL_ROLES[3:]:
            result[side+'_'+role][index][2] = slots[side]['slope']
            result[side+'_'+role][index+2][2] = slots[side]['halfwidth']
    return result


def telescope_domain(descent):
    """Vertices of the actual bounded three-joint fixed-sum allocation.

    A vertex of this two-dimensional polytope has at least two joints at
    a bound. Exact rational arithmetic on the declared decimal dimensions
    avoids dropping boundary vertices while constructing this inventory.
    Native geometry and its numerical Common still use ordinary floats.
    """
    import cam_coupling as coupling
    pose = coupling.pose(coupling.STROKE, descent)
    lower = Fraction(str(coupling.STAGE_MIN))
    upper = Fraction(str(coupling.STAGE_MAX))
    extent = Fraction(str(coupling.SEATING))-Fraction(str(p.finite(descent)))
    total = 3*lower+extent
    vertices = set()
    for free in range(3):
        bound_indices = [index for index in range(3) if index != free]
        for ends in itertools.product((lower, upper), repeat=2):
            point = [None]*3
            for index, value in zip(bound_indices, ends):
                point[index] = value
            point[free] = total-sum(ends)
            if lower <= point[free] <= upper:
                vertices.add(tuple(point))
    if not vertices:
        raise ValueError('empty captured telescope allocation domain')
    vertices = [list(map(float, point)) for point in sorted(vertices)]
    nominal = pose['nominal_joint_offsets_mm'][0]
    joint_bounds = [[min(v[i] for v in vertices), max(v[i] for v in vertices)] for i in range(3)]
    parameter_bounds = [(lo-nominal, hi-nominal) for lo, hi in joint_bounds[:2]]
    return {'joint_limits_mm': [float(lower), float(upper)],
            'joint_sum_mm': float(total), 'nominal_joint_mm': nominal,
            'vertices_joint_mm': vertices, 'joint_projection_bounds_mm': joint_bounds,
            'parameter_bounds_delta_j1_delta_j2_mm': parameter_bounds,
            'left_right_allocations_independent': True,
            'third_joint_is_fixed_sum_remainder': True,
            'full_feasible_fixed_pose_allocation_covered': True}


def fixed_pose_coefficients(names, slots):
    """Actual split-material laws for controls plus four telescope deltas."""
    expected = {side+'_'+role for side in 'LR' for role in TELESCOPE_ROLES}
    if not expected <= set(names):
        raise ValueError('a complete telescope body or removable cap was omitted')
    result = controls_coefficients(names, slots)
    for vectors in result.values():
        vectors.extend([[0., 0., 0.] for _ in range(4)])
    for index, side in enumerate('LR'):
        first = 4+2*index
        for role in TELESCOPE_ROLES:
            result[side+'_'+role][first][2] = 1.
        for role in TELESCOPE_ROLES[2:]:
            result[side+'_'+role][first+1][2] = 1.
    return result


def relative_telescope_projection(coefficients, domain, telescope):
    """Project the complete feasible telescope polytope into relative Z.

    Every telescope-dependent material displacement is along the same Z
    axis. A linear map of each connected convex polytope is the closed
    interval between its vertex extrema. Independent sides add intervals.
    The remaining controls are independent, so this reduction preserves
    the complete relative-motion image rather than using a joint box.
    """
    if len(coefficients) != 8 or len(domain) != 8:
        raise ValueError('eight fixed-pose parameters required')
    if any(len(c) != 3 or any(c[:2]) for c in coefficients[4:]):
        raise ValueError('unrepresented non-Z telescope displacement')
    nominal = telescope['nominal_joint_mm']
    extrema = []
    for start in (4, 6):
        first, second = (p.finite(coefficients[start+i][2]) for i in (0, 1))
        values = [math.fsum((first*(v[0]-nominal), second*(v[1]-nominal)))
                  for v in telescope['vertices_joint_mm']]
        extrema.append((min(values), max(values)))
    interval = (math.fsum(v[0] for v in extrema), math.fsum(v[1] for v in extrema))
    vector = [0., 0., 0.] if interval == (0., 0.) else [0., 0., 1.]
    return coefficients[:4]+[vector], tuple(domain[:4])+(interval,)


def telescope_allocations(values, telescope):
    """Reconstruct feasible actual joints, never a witness outside the domain."""
    if len(values) != 8:
        raise ValueError('eight fixed-pose parameters required')
    values = [p.finite(value) for value in values]
    nominal = telescope['nominal_joint_mm']
    lower, upper = telescope['joint_limits_mm']
    allocations = {}
    for side, start in (('L', 4), ('R', 6)):
        first, second = values[start:start+2]
        joints = [nominal+first, nominal+second, nominal-first-second]
        # The native constructor uses this same 1e-9 mm boundary tolerance.
        # An infeasible outer-box point must not become an actual witness.
        if any(joint < lower-1e-9 or joint > upper+1e-9 for joint in joints):
            return None
        allocations[side] = joints
    return allocations


def translation(coefficients, values):
    if len(coefficients) != len(values):
        raise ValueError('coefficient/value dimension mismatch')
    return tuple(sum(c[axis]*value for c, value in zip(coefficients, values)) for axis in range(3))


def relative_coefficients(a, b):
    if len(a) != len(b):
        raise ValueError('relative coefficient dimension mismatch')
    return [[x-y for x, y in zip(ca, cb)] for ca, cb in zip(a, b)]


def translation_bounds(coefficients, domain=DOMAIN):
    if len(coefficients) != len(domain):
        raise ValueError('coefficient/domain dimension mismatch')
    bounds = []
    for axis in range(3):
        lo = hi = 0.
        for coefficient, interval in zip(coefficients, domain):
            if len(coefficient) != 3 or len(interval) != 2:
                raise ValueError('three-axis coefficients and closed intervals required')
            a, b = (p.finite(x) for x in interval)
            c = p.finite(coefficient[axis])
            if b < a:
                raise ValueError('reversed parameter interval')
            lo += min(c*a, c*b); hi += max(c*a, c*b)
        bounds.extend((lo, hi))
    return bounds


def enclosure_regions(body, coefficients, domain=DOMAIN, maximum_regions=4096):
    from translation_regions import regions
    active = [axis for axis in range(3) if any(c[axis] for c in coefficients)]
    bounds = translation_bounds(coefficients, domain)
    if not active:
        return [body], 'identical_relative_pose'
    if len(active) == 1:
        axis = active[0]; start = [0., 0., 0.]; vector = [0., 0., 0.]
        start[axis] = bounds[2*axis]; vector[axis] = bounds[2*axis+1]-bounds[2*axis]
        moved = body.translate(tuple(start))
        return regions(moved, vector)[0] if vector[axis] else [moved], 'continuous_relative_axis_translation'
    # A sequence of whole translation enclosures is a Minkowski-sum
    # superset of the affine image of the full parameter box. Material is
    # never removed, and positive conservative overlap is not accepted.
    pieces = [body.translate(translation(coefficients, [v[0] for v in domain]))]
    for coefficient, (lo, hi) in zip(coefficients, domain):
        vector = tuple(c*(hi-lo) for c in coefficient)
        if not any(vector):
            continue
        expanded = []
        for piece in pieces:
            expanded.extend(regions(piece, vector)[0])
            if len(expanded) > maximum_regions:
                raise ValueError('relative enclosure region budget exhausted')
        pieces = expanded
    return pieces, 'continuous_relative_affine_box_translation_enclosure'


def _continuous_pair_in_frame(a, b, coefficients, *, a_bounds=None, b_bounds=None, cache=None, cache_key=None, domain=DOMAIN):
    try:
        aa = a_bounds or p.bounds(a); bb = b_bounds or p.bounds(b)
        shift = translation_bounds(coefficients, domain)
        swept = [aa[2*i]+shift[2*i] for i in range(3)]
        high = [aa[2*i+1]+shift[2*i+1] for i in range(3)]
        gap = max(max(swept[i]-bb[2*i+1], bb[2*i]-high[i]) for i in range(3))
        if gap > 0:
            return {'disposition': 'clear', 'method': 'continuous_relative_axis_gap', 'gap_lower_mm': gap}
        # A caller label, including None, cannot identify actual native material.
        # Retain both object identity and OCCT topology/location identity so a
        # reused label or a changed placement cannot reuse another enclosure.
        key = (id(a), a.hashCode(), tuple(tuple(c) for c in coefficients), tuple(domain))
        if cache is None or key not in cache:
            value = enclosure_regions(a, coefficients, domain)
            if cache is not None:
                cache[key] = (a, value)  # retain the object whose id is in the key
        else:
            value = cache[key][1]
        regions, method = value
        maximum = 0.;values=[]
        for region in regions:
            common=p.strict_common(region,b)['common_mm3']
            values.append(common);maximum=max(maximum,common)
            upper=sum_common_upper_bound(values)
            if upper > TOL:
                return {'disposition': 'unresolved_enclosure_overlap', 'method': method,
                        'positive_enclosure_common_mm3': maximum,
                        'examined_region_common_sum_mm3':upper,'regions_examined':len(values),
                        'total_region_count':len(regions),'collision_proved':False}
        return {'disposition': 'clear', 'method': method, 'region_count': len(regions),
                'maximum_region_common_mm3': maximum,'common_upper_bound_mm3':upper,
                'common_upper_bound_is_sum_not_union_volume':True}
    except Exception as exc:
        return {'disposition': 'unresolved_evaluation', 'error': type(exc).__name__+': '+str(exc),
                'collision_proved': False}


def continuous_pair(a,b,coefficients,*,a_bounds=None,b_bounds=None,cache=None,cache_key=None,domain=DOMAIN):
    result=_continuous_pair_in_frame(a,b,coefficients,a_bounds=a_bounds,b_bounds=b_bounds,
                                    cache=cache,cache_key=cache_key,domain=domain)
    if result['disposition']=='clear':return result
    opposite=[[-value for value in vector] for vector in coefficients]
    reverse=_continuous_pair_in_frame(b,a,opposite,a_bounds=b_bounds,b_bounds=a_bounds,
                                     cache=cache,cache_key=('reverse-shape',id(b)),domain=domain)
    if reverse['disposition']=='clear':
        return {**reverse,'relative_reference_frame_reversed':True,
                'initial_reference_frame_result':result}
    return {**result,'opposite_reference_frame_result':reverse}


def evaluation_errors(row, frame='initial'):
    """Retain every failed evaluation even when the other frame proves clear."""
    result=[]
    if row.get('disposition')=='unresolved_evaluation':
        result.append({'frame':frame,'error':row.get('error','missing evaluation error detail')})
    for name in ('initial_reference_frame_result','opposite_reference_frame_result'):
        if name in row:
            result.extend(evaluation_errors(row[name],name))
    return result


def verify_affine_construction(base, coefficients, slide=0., descent=0., accessories=False, *, telescope=None):
    # This is a material check on complete actual factory participants, in
    # addition to the explicit affine construction in product_assembly.
    values = [1.125, 2.375, -.4, .65] if not slide and not descent else [3., 3., -.4, .65]
    extra = {}
    if telescope is not None:
        nominal = telescope['nominal_joint_mm']
        for vertex in (telescope['vertices_joint_mm'][0], telescope['vertices_joint_mm'][-1]):
            values.extend([vertex[0]-nominal, vertex[1]-nominal])
        extra['telescope_offsets'] = telescope_allocations(values, telescope)
        if extra['telescope_offsets'] is None:
            raise ValueError('construction probe is outside the feasible telescope domain')
    actual, _ = full_scene(slide, descent, left_tab=values[0], right_tab=values[1], flanks=values[2:4],
                           open_hold=accessories, open_support=accessories, **extra)
    if set(actual) != set(base):
        raise ValueError('control action changed the complete body inventory')
    worst = 0.
    for name, body in actual.items():
        shift=translation(coefficients[name],values)
        expected=base[name].translate(shift) if any(shift) else base[name]
        # Unchanged participants share exact construction; the geometry check
        # is still performed so a new hidden moving participant fails closed.
        difference = 0. if body.isSame(expected) else max(p.volume(body.cut(expected)), p.volume(expected.cut(body)))
        worst = max(worst, difference)
        if difference > TOL:
            raise ValueError('unrepresented control-dependent native material: '+name)
    return {'probe_controls': list(values[:4]), 'probe_parameters': list(values),
            'probe_telescope_offsets_by_side_mm': extra.get('telescope_offsets'), 'participants': len(actual),
            'maximum_bidirectional_material_difference_mm3': worst,
            'affine_law_is_code_owned_not_inferred_from_samples': True}


def witness_parameter_candidates(relative, domain, telescope=None):
    if len(relative) != len(domain):
        raise ValueError('relative witness/domain dimension mismatch')
    count = 4 if telescope is not None else len(domain)
    choices = [sorted({lo, (lo+hi)/2, hi}) if any(relative[i]) else [(lo+hi)/2]
               for i, (lo, hi) in enumerate(domain[:count])]
    if telescope is not None:
        if len(relative) != 8:
            raise ValueError('eight fixed-pose witness parameters required')
        nominal = telescope['nominal_joint_mm']
        for start in (4, 6):
            vertices = telescope['vertices_joint_mm'] if any(any(c) for c in relative[start:start+2]) else []
            choices.append(sorted({tuple(v) for v in [*vertices, [nominal]*3]}))
    for values in itertools.product(*choices):
        parameters = list(values[:count])
        if telescope is not None:
            for joints in values[count:]:
                parameters.extend([joints[0]-nominal, joints[1]-nominal])
            if telescope_allocations(parameters, telescope) is None:
                continue
        yield parameters


def confirmed_witnesses(base, coefficients, unresolved, maximum=5, *, domain=DOMAIN, slide=0., descent=0., accessories=False, telescope=None):
    witnesses = []
    full_scenes = {}
    for row in unresolved:
        a, b = row['a'], row['b']
        relative = relative_coefficients(coefficients[a], coefficients[b])
        for controls in witness_parameter_candidates(relative, domain, telescope):
            av = base[a].translate(translation(coefficients[a], controls))
            bv = base[b].translate(translation(coefficients[b], controls))
            first = p.strict_common(av, bv)['common_mm3']
            if first <= TOL:
                continue
            key = tuple(controls)
            if key not in full_scenes:
                extra = {'telescope_offsets': telescope_allocations(controls, telescope)} if telescope is not None else {}
                full_scenes[key] = full_scene(slide, descent, left_tab=key[0], right_tab=key[1], flanks=key[2:4],
                                              open_hold=accessories, open_support=accessories, **extra)[0]
            actual = full_scenes[key]
            common = p.strict_common(actual[a], actual[b])['common_mm3']
            if common <= TOL:
                raise ValueError('affine witness did not reproduce in the actual complete factory')
            witnesses.append({'a': a, 'b': b, 'controls_uL_uR_flankL_flankR': controls[:4],
                              'parameters': controls,
                              'telescope_offsets_by_side_mm': telescope_allocations(controls, telescope) if telescope is not None else None,
                              'common_mm3': common, 'actual_full_scene_participants': len(actual),
                              'real_pose_native_common_confirmed': True})
            break
        if len(witnesses) >= maximum:
            break
    return witnesses


def verify_controls(pose='STOW'):
    poses={'STOW':(0.,0.),'PREDOCK':(79.75,0.),'OPEN':(79.75,8.2)}
    if pose not in poses:raise ValueError('named finite pose required')
    slide,descent=poses[pose];accessories=pose=='OPEN'
    telescope=telescope_domain(descent)
    control_domain=DOMAIN if pose=='STOW' else ((3.,3.),(3.,3.),(-1.,1.),(-1.,1.))
    domain=control_domain+tuple(telescope['parameter_bounds_delta_j1_delta_j2_mm'])*2
    started = time.perf_counter()
    parts, meta = full_scene(slide, descent, open_hold=accessories, open_support=accessories)
    if len(parts) != (161 if accessories else 154):
        raise ValueError('complete current EP5 pose inventory required')
    print(json.dumps({'pose':pose,'stage':'full_scene_constructed','participants':len(parts),'seconds':time.perf_counter()-started}),flush=True)
    slots = p.native_inputs()[5]
    coefficients = fixed_pose_coefficients(parts, slots)
    construction = verify_affine_construction(parts, coefficients, slide, descent, accessories, telescope=telescope)
    print(json.dumps({'pose':pose,'stage':'whole_material_affine_check_complete','seconds':time.perf_counter()-started}),flush=True)
    bounds = {name: p.bounds(body) for name, body in parts.items()}
    rows, cache = [], {}
    for number, (a, b) in enumerate(itertools.combinations(sorted(parts), 2), 1):
        relative = relative_coefficients(coefficients[a], coefficients[b])
        projected, pair_domain = relative_telescope_projection(relative, domain, telescope)
        row = continuous_pair(parts[a], parts[b], projected, a_bounds=bounds[a], b_bounds=bounds[b],
                              cache=cache, cache_key=a, domain=pair_domain)
        rows.append({'a': a, 'b': b, 'relative_telescope_z_projection_mm': list(pair_domain[-1]), **row})
        if number % 2000 == 0:
            print(json.dumps({'checked_pairs': number, 'seconds': time.perf_counter()-started}), flush=True)
    unresolved = [row for row in rows if row['disposition'] != 'clear']
    failures=[{'a':row['a'],'b':row['b'],**error} for row in rows for error in evaluation_errors(row)]
    witnesses = confirmed_witnesses(parts, coefficients, unresolved, domain=domain, slide=slide, descent=descent,
                                    accessories=accessories, telescope=telescope)
    return {'schema': 'razr-ep5-independent-control-domain-v2', 'pose': pose,
            'domain': {'slide_mm': slide, 'descent_mm': descent, 'left_tab_mm': list(domain[0]),
                       'right_tab_mm': list(domain[1]), 'slot_flanks': [[-1., 1.], [-1., 1.]],
                       'KEY_offsets_mm': [0., 0.], 'crosshead_offsets_mm': [0., 0.],
                       'telescope_allocation': telescope,
                       'parameter_order': ['uL','uR','flankL','flankR','delta_j1L','delta_j2L','delta_j1R','delta_j2R'],
                       'relative_telescope_domain_reduction': 'complete independent polytope linear Z projection'},
            'complete_participant_names': sorted(parts), 'participant_count': len(parts),
            'pair_count': len(rows), 'expected_pair_count': len(parts)*(len(parts)-1)//2,
            'all_unordered_pairs_present_once': len(rows) == len(parts)*(len(parts)-1)//2,
            'construction_check': construction, 'native_scene_metadata': meta,
            'counts': dict(Counter(row['disposition'] for row in rows)),
            'methods': dict(Counter(row['method'] for row in rows if 'method' in row)),
            'pairs': rows, 'unresolved_pairs': unresolved, 'confirmed_collision_witnesses': witnesses,
            'evaluation_failures': failures, 'evaluation_failure_count': len(failures),
            'whole_declared_control_domain_clear': not unresolved,
            'unresolved_enclosure_overlap_is_not_collision': True,
            'sampled_clear_witnesses_cannot_discharge_an_unresolved_domain': True,
            'seconds': time.perf_counter()-started,
            'tab_motion_allowed_only_at_STOW': True,
            'complete_product_motion_proved': False, 'physical_qualification': False,
            'geometry_generator_imported': True, 'same_CAD_kernel': True,
            'formal_directed_rounding_certificate': False,
            'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False}


def bind_executed_files(root, snapshot, files):
    """Require HEAD bytes for every executed repository file, including this CLI."""
    root=Path(root).resolve();observed={};outside=[]
    for item in sorted(set(map(Path,files))):
        path=item.resolve()
        if item.is_symlink() or not path.is_file():
            raise ValueError('missing or linked executed source: '+str(item))
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if path.is_relative_to(root):
            relative=path.relative_to(root).as_posix()
            if snapshot.get(relative)!=digest:
                raise ValueError('executed source differs from HEAD blob or is untracked: '+relative)
        else:
            outside.append(str(path))
        observed[str(path)]=digest
    return observed,outside


def execution_identity(expected_head=None):
    """Use the existing exact-blob and complete EP5 input-closure validators."""
    import product_routing_ep5 as ep5
    tools_dir=str(p.ROOT/'tools')
    if tools_dir not in sys.path:sys.path.insert(0,tools_dir)
    import verify_product_ep5_native as native
    import check_environment as environment
    for module,name in ((native,'verify_product_ep5_native.py'),
                        (native.identity,'verify_product_native.py'),
                        (environment,'check_environment.py')):
        if Path(module.__file__).resolve()!=(p.ROOT/'tools'/name).resolve():
            raise ValueError('executed identity validator is outside the repository: '+name)
    head=native.identity.git(p.ROOT,'rev-parse','HEAD')
    if expected_head is not None and (len(expected_head)!=40 or expected_head!=head):
        raise ValueError('repository HEAD differs from the explicitly expected full commit')
    snapshot=native.source_snapshot(p.ROOT)
    raw_sources=ep5._snapshot_sources('full')
    # The generator's broader import inventory cannot silently add untracked
    # project code beyond the existing HEAD-bound source/input closure.
    sources,_=bind_executed_files(p.ROOT,snapshot,raw_sources)
    source_directories={Path(__file__).resolve().parent,Path(p.__file__).resolve().parent,
        Path(sum_common_upper_bound.__code__.co_filename).resolve().parent}
    executed,outside=bind_executed_files(p.ROOT,snapshot,
        [*(file for folder in source_directories for file in folder.glob('*.py')),Path(native.__file__),
         Path(native.identity.__file__),Path(environment.__file__)])
    sources.update(executed)
    locked=environment.inspect_environment(p.ROOT)
    if not locked['passed']:raise ValueError('locked runtime environment mismatch: '+repr(locked['errors']))
    return {'repository_head':head,'head_bound_source_sha256':snapshot,
            'executed_source_sha256':sources,'executed_source_overlay':bool(outside),
            'outside_repository_executed_files':outside,'environment':locked}


def execution_result_checks(report,before,after):
    """Derive completion from raw inventory and errors, including reverse tries."""
    names=report['complete_participant_names'];rows=report['pairs']
    expected=set(itertools.combinations(sorted(names),2))
    actual=[(row['a'],row['b']) for row in rows]
    inventory=(len(set(names))==len(names) and report['participant_count']==len(names)
        and len(actual)==len(set(actual))==len(expected) and set(actual)==expected
        and report['pair_count']==report['expected_pair_count']==len(expected))
    failures=[{'a':row['a'],'b':row['b'],**error} for row in rows for error in evaluation_errors(row)]
    source_unchanged=(before['repository_head']==after['repository_head']
        and before['head_bound_source_sha256']==after['head_bound_source_sha256']
        and before['executed_source_sha256']==after['executed_source_sha256'])
    completed=(inventory and source_unchanged and not failures
        and before['environment']['passed'] is True and after['environment']['passed'] is True)
    overlay=before['executed_source_overlay'] or after['executed_source_overlay']
    return {'all_unordered_pairs_present_once':inventory,'source_bytes_unchanged':source_unchanged,
        'evaluation_failures':failures,'evaluation_failure_count':len(failures),
        'diagnostic_execution_checks_passed':completed,
        'executed_source_overlay':overlay,'execution_checks_passed':completed and not overlay}


def main(argv=None):
    import product_routing_ep5 as ep5
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose', choices=('STOW','PREDOCK','OPEN'), default='STOW')
    parser.add_argument('--expected-head')
    parser.add_argument('--diagnostic-overlay',action='store_true',
        help='allow scratch sources; canonical execution_checks_passed remains false')
    args = parser.parse_args(argv)
    args.output=args.output.resolve()
    if args.output.exists() or args.output.is_relative_to(p.ROOT.resolve()):
        raise ValueError('new evidence output outside the repository required')
    report={'schema':'razr-ep5-independent-control-domain-v2','pose':args.pose,
        'execution_completed':False,'execution_checks_passed':False,
        'diagnostic_execution_checks_passed':False,'expected_head':args.expected_head,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    try:
        before=execution_identity(args.expected_head)
        report['identity_before']=before
        if before['executed_source_overlay'] and not args.diagnostic_overlay:
            raise ValueError('scratch sources require explicit diagnostic-overlay mode')
        report.update(verify_controls(args.pose))
        ep5.validate_factory_input_coverage(report['native_scene_metadata']['scene'],before['executed_source_sha256'])
        after=execution_identity(before['repository_head'])
        report['identity_after']=after
        report.update(execution_result_checks(report,before,after))
        report['execution_completed']=True
    except Exception as exc:
        report['execution_failure']=type(exc).__name__+': '+str(exc)
    with args.output.open('x') as stream:stream.write(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({key:report[key] for key in ('pose','pair_count','counts','whole_declared_control_domain_clear',
        'evaluation_failure_count','execution_checks_passed','diagnostic_execution_checks_passed','execution_failure','seconds') if key in report}))
    return 0 if (report['execution_checks_passed'] or
        args.diagnostic_overlay and report['diagnostic_execution_checks_passed']) else 2


if __name__=='__main__':
    raise SystemExit(main())
