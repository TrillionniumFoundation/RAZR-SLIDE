"""Prospective K1 capacity stage; injected native operations, no CAD imports.

The owned worker must load actual dual-clear K1 materials, retain the original
source/runtime checks, and impose the unchanged external 1800 s/1536 MiB
limits. This module does not create a prepared or imaginary K1 binding.
It is an orchestration interface, not a standalone qualified native runner.
"""
from fractions import Fraction as F
import time


def require(ok, message):
    if not ok:
        raise ValueError(message)


def priority_pairs(names):
    """The same seventeen physical pairs, each over the whole original q domain."""
    names = list(names)
    require(names == sorted(set(names)) and len(names) == 154, 'complete ordered material inventory required')
    telescopes = ('L_TELESCOPE_2', 'L_TELESCOPE_3', 'L_TELESCOPE_3_CAM_LOWER_FLANGE',
                  'L_TELESCOPE_3_CAM_UPPER_FLANGE', 'R_TELESCOPE_2',
                  'R_TELESCOPE_3_CAM_LOWER_FLANGE', 'R_TELESCOPE_3_CAM_UPPER_FLANGE')
    result = [tuple(sorted(('B_SHELL', name))) for name in telescopes]
    for side in 'LR':
        for index in (0, 1):
            stop = f'{side}_STOP_{index}'
            result.append(tuple(sorted((side + '_KEY', stop))))
            result.append(tuple(sorted((f'{side}_SPRING_{index}_OD_TOL_ENVELOPE', stop))))
    result.extend(tuple(sorted(('A_BACK_PANEL', side + '_KEY'))) for side in 'LR')
    require(len(result) == len(set(result)) == 17 and all(a in names and b in names for a,b in result),
            'capacity sample must contain all seven telescopes, eight contacts and two panel pairs')
    return result


class CandidateFactory:
    """Delegate actual S4 scene generation through the verified frozen KEY adapter."""
    def __init__(self, keys, adapter, nominal, cam, p):
        require(isinstance(keys, adapter.VerifiedKeys), 'actual K1 loader return required')
        self.keys, self.adapter, self.original = keys, adapter, nominal
        self.cam, self.p = cam, p

    def full_scene(self, *args, **kwargs):
        return self.adapter.full_scene(self.keys, self.original, self.cam, self.p, *args, **kwargs)

    @property
    def fixed_route_parts(self):
        # The unchanged five-probe helper explicitly releases this original cache.
        return self.original.fixed_route_parts


class ForwardBudget:
    """Keep every original threshold; normalize its stop type for V4 propagation."""
    def __init__(self, original, api):
        self.original, self.api = original, api
    def check(self, *args, **kwargs):
        return self.api.check_budget(lambda: self.original.check(*args, **kwargs))
    def record(self):
        return self.original.record()


def construct_and_probe(*, keys, adapter, nominal, cam, p, original_driver,
                        source_evidence, domain, identity_before, budget, checkpoint):
    """Call the unchanged S4 five-probe and whole-spring validators on the adapter.

    The caller freezes the real adapter source and the actual K1 artifacts before
    this entry. Actual q=0 and every probe are complete S4 factories with only the
    two already verified KEY materials replaced by the adapter.
    """
    proxy = CandidateFactory(keys, adapter, nominal, cam, p)
    names = source_evidence.expected_names()
    reference = {side: [float(domain.JOINT_NOMINAL)] * 3 for side in 'LR'}
    base, metadata = proxy.full_scene(0., 0., 3., 3., flanks=(0., 0.), telescope_offsets=reference,
        key_offsets=(0., 0.), crosshead_offsets=(0., 0.), open_hold=False, open_support=False)
    source_evidence.cages.ep5.validate_factory_input_coverage(metadata['scene'], identity_before['executed_source_sha256'])
    source_evidence.validate_metadata(metadata)
    require(sorted(base) == names, 'actual complete factory inventory differs')
    inputs = p.native_inputs()
    profiles = tuple(profile for side in 'LR' for profile in inputs[4][side])
    require(profiles == source_evidence.original_profiles(), 'native profile differs from original source')
    halfwidth = {side: inputs[5][side]['halfwidth'] for side in 'LR'}
    laws = domain.rigid_laws(base, halfwidth, names)
    for body in base.values():
        budget.check()
        p.whole_material(body)
    springs = {name: source_evidence.Spring(name, tuple(p.bounds(base[name]))) for name in domain.SPRINGS}
    contract = source_evidence.Contract(names, laws, profiles, springs)
    bodies = original_driver.BoundedBodies(base, contract, proxy, p, budget)
    construction = {'original_complete_spring_identity': [], 'probes': [],
                    'source_laws_not_inferred_from_samples': True}
    def save():
        checkpoint({'construction': construction, 'five_factory_probes_complete': False})
    original_driver.verify_factory_laws(base, metadata, contract, proxy, p, identity_before,
        budget, bodies, construction, save)
    passed = original_driver.validate_construction(construction, contract)
    require(passed is True, 'unchanged complete factory probe validator rejected')
    result = {'construction': construction, 'five_factory_probes_complete': True,
              'original_nominal_source_domain': source_evidence.recorded_domain(profiles),
              'native_slot_halfwidth_mm': halfwidth,
              'base_spring_bounds_mm': {name: list(spring.base_bounds) for name,spring in springs.items()},
              'current_candidate_factory_metadata': metadata,
              'original_factory_defaults_changed': False,
              'physical_independent_allowed_domain_proved': False}
    checkpoint(result)
    return contract, bodies, result


def validate_interval_record(row, a, b, low, high, *, contract, api, validate_specification, depth=0):
    """Rebuild source specs and the original closed partition from saved records."""
    require(row['q_interval_exact'] == [str(low), str(high)], 'saved exact interval differs')
    require(row['schema'] == 'razr-capacity-interval-v4', 'unknown interval record')
    require(row['subdivision_parameter'] == 2 and depth <= 3, 'original recursion limit changed')
    attempts = row['attempts']
    require(len(attempts) == 1 and attempts[0]['reference_frame'] == 'A', 'source frame incomplete')
    attempt = attempts[0]
    specs = contract.specifications(a,b,low,high,'A')
    require(len(attempt['records']) == len(specs), 'source specification omitted')
    for spec, result in zip(specs,attempt['records']):
        require(result['source_specification'] == spec, 'recorded source specification differs')
        validate_specification(result)
    aggregate = api.aggregate_complete_pair(specs,attempt['records'])
    require(all(attempt[k] == value for k,value in aggregate.items()), 'complete source sum differs')
    child_dispositions = []
    if 'children' in row:
        require(depth <= 2 and aggregate['disposition'] == 'unresolved_enclosure_overlap',
                'unexpected subdivision or suppression of an evaluation error')
        require(row['split'] == ('all_actual_profile_breakpoints' if depth == 0 else 'closed_midpoint_bisection'),
                'original subdivision strategy changed')
        parts = contract.child_intervals(low,high,row['split'])
        require(row['closed_partition_exact'] == api.require_closed_partition(low,high,parts),
                'closed source partition changed')
        require(len(row['children']) == len(parts), 'source subinterval omitted')
        for child,(lo,hi) in zip(row['children'],parts):
            validate_interval_record(child,a,b,lo,hi,contract=contract,api=api,
                                     validate_specification=validate_specification,depth=depth+1)
            child_dispositions.append(child['disposition'])
    elif aggregate['disposition'] == 'unresolved_enclosure_overlap':
        require(depth == 3 or low == high, 'original complete subdivision omitted')
    proven = aggregate['disposition'] == 'clear' or bool(child_dispositions) and all(x=='clear' for x in child_dispositions)
    error = aggregate['disposition'] == 'unresolved_evaluation' or 'unresolved_evaluation' in child_dispositions
    expected = 'unresolved_evaluation' if error else 'clear' if proven else 'unresolved_enclosure_overlap'
    require(row['disposition'] == expected, 'saved interval disposition differs from complete evidence')
    return True


def evaluate_interval(a, b, low, high, *, contract, bodies, api, evaluate_specification,
                      budget_check, checkpoint, depth=0, maximum_depth=2):
    """Original full profile split and midpoint depth, separately tagged V4 records.

    evaluate_specification receives actual bodies, a freshly rebuilt source spec
    and the exact interval target. It must invoke the frozen V4 API with native
    callbacks retaining actual carriers. No old clear is used as an input.
    """
    require(maximum_depth == 2, 'capacity stage preserves original subdivision parameter two')
    low, high = F(low), F(high)
    row = {'schema': 'razr-capacity-interval-v4', 'q_interval_exact': [str(low), str(high)],
           'disposition': 'unresolved_enclosure_overlap', 'attempts': [],
           'collision_proved': False, 'subdivision_parameter': maximum_depth}
    start = time.monotonic()
    # These seventeen physical pairs are all non-flexible. The original source
    # contract accordingly permits frame A only. Internal V2 reverse checks are
    # still performed by the frozen API and retained in its result.
    try:
        api.check_budget(budget_check)
        specifications = contract.specifications(a, b, low, high, 'A')
        attempt = {'reference_frame': 'A', 'records': []}
        row['attempts'].append(attempt)
        for spec in specifications:
            api.check_budget(budget_check)
            moving = bodies.material(spec['moving'], low, high)
            fixed = bodies.material(spec['fixed'], low, high)
            target = {'a': a, 'b': b, 'q_interval_exact': [str(low), str(high)]}
            record = evaluate_specification(moving, fixed, spec, target)
            attempt['records'].append(record)
            checkpoint(row)
        aggregate = api.aggregate_complete_pair(specifications, attempt['records'])
        attempt.update(aggregate)
        row['disposition'] = aggregate['disposition']
        if row['disposition'] == 'clear':
            row['method'] = 'complete_V4_source_specifications'
            return row
        if row['disposition'] == 'unresolved_evaluation':
            return row
        if depth <= maximum_depth and low < high:
            split = 'all_actual_profile_breakpoints' if depth == 0 else 'closed_midpoint_bisection'
            intervals = contract.child_intervals(low, high, split)
            row['closed_partition_exact'] = api.require_closed_partition(low, high, intervals)
            row.update(split=split, children=[])
            for child_low, child_high in intervals:
                try:
                    child = evaluate_interval(a, b, child_low, child_high, contract=contract,
                        bodies=bodies, api=api, evaluate_specification=evaluate_specification,
                        budget_check=budget_check, checkpoint=checkpoint, depth=depth+1,
                        maximum_depth=maximum_depth)
                except api.CapacityStop as exc:
                    if getattr(exc, 'partial', None) is not None:
                        row['children'].append(exc.partial)
                    raise
                row['children'].append(child)
                checkpoint(row)
            if any(c['disposition'] == 'unresolved_evaluation' for c in row['children']):
                row['disposition'] = 'unresolved_evaluation'
            elif all(c['disposition'] == 'clear' for c in row['children']):
                row.update(disposition='clear', method='complete_closed_V4_interval_partition')
        return row
    except api.CapacityStop as exc:
        row['disposition'] = 'unresolved_budget'
        row['capacity_failure_type'] = type(exc).__name__
        exc.partial = row
        raise
    except InterruptedError:
        row['disposition'] = 'unresolved_budget'
        row['capacity_failure_type'] = 'InterruptedError'
        raise
    except Exception as exc:
        row['disposition'] = 'unresolved_evaluation'
        row['evaluation_failure_type'] = type(exc).__name__
        # Arbitrary exception text is not promoted to engineering output.
        return row
    finally:
        row['interval_elapsed_seconds'] = time.monotonic()-start
        checkpoint(row)


def run_capacity_pairs(*, contract, bodies, api, evaluate_specification,
                       budget_check, checkpoint, construction_receipt):
    require(construction_receipt.get('five_factory_probes_complete') is True,
            'actual unchanged five-probe validator must pass before pair evaluation')
    inventory = api.initialize_inventory(contract.names)
    index = {(r['a'], r['b']): i for i,r in enumerate(inventory)}
    selected = priority_pairs(contract.names)
    report = {'schema': 'razr-K1-capacity-stage-v4', 'execution_completed': False,
        'scope': '17 difficult pairs over complete original nominal SLIDE q law; capacity measurement only',
        'selected_physical_pairs': [list(x) for x in selected], 'all_11781_pair_slots': inventory,
        'selected_pair_results': [], 'active_interval': None,
        'all_11781_native_pairs_executed': False, 'full_independent_physical_domain_proved': False,
        'complete_G2_qualification': False, 'candidate_go': False,
        'fixture_fabrication_go': False, 'manufacturing_go': False}
    current_index = None
    def save_interval(row):
        report['active_interval'] = row
        checkpoint(report)
    checkpoint(report)
    try:
        for a,b in selected:
            current_index = index[a,b]
            report['active_pair'] = [a,b]
            result = evaluate_interval(a,b,F(0),F(12),contract=contract,bodies=bodies,api=api,
                evaluate_specification=evaluate_specification,budget_check=budget_check,
                checkpoint=save_interval)
            inventory[current_index]['disposition'] = result['disposition']
            report['selected_pair_results'].append({'a':a,'b':b,**result})
            report['active_interval'] = None
            checkpoint(report)
        report['execution_completed'] = len(report['selected_pair_results']) == 17
    except api.CapacityStop as exc:
        if current_index is not None:
            inventory[current_index]['disposition'] = 'unresolved_budget'
        report['capacity_failure_type'] = type(exc).__name__
        report['active_interval'] = getattr(exc,'partial',report['active_interval'])
    except InterruptedError:
        if current_index is not None:
            inventory[current_index]['disposition'] = 'unresolved_budget'
        report['capacity_failure_type'] = 'InterruptedError'
    finally:
        report['full_inventory_status'] = api.inventory_status(inventory,contract.names)
        checkpoint(report)
    return report
