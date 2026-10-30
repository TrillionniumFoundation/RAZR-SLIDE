"""Evidence-bound G4 powered-motion and G5 endurance/process decisions.

Plans retain missing OEM/supplier limits as null.  A complete observation matrix
is distinct from qualification; synthetic fixtures and incomplete records cannot
pass.  A definite observed failure survives missing data.  PASS is limited to
the declared measured protocol and never issues a manufacturing release.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATHS = ('design/product_geometry.json','design/product_interfaces.json','design/product_routing_ep5.json')
CURRENT_EXTRA_SOURCES = ('design/product_routing_ep4.json',
    'tools/verify_product_ep5_native.py','tools/check_environment.py',
    'engineering/product-integration-20261018/physical-test-followon-20261019/qualification_contract.py',
    'engineering/product-integration-20261018/phase5-20261022/read_ep5_step_independent.py')
PHASES = ('LOCKED_BASELINE','UNLOCK_LEFT','UNLOCK_RIGHT','SLIDE_OUT','SEAT',
          'HOLD_LEFT_INSTALL','HOLD_RIGHT_INSTALL','SUPPORT_INSTALL','HANDS_OFF_OPEN',
          'SUPPORT_REMOVE','HOLD_RIGHT_REMOVE','HOLD_LEFT_REMOVE','UNSEAT','SLIDE_IN',
          'RELOCK_RIGHT','RELOCK_LEFT','LOCKED_FINAL')
MODES = ('original_battery','original_charging')
FUNCTIONS = ('power','pack_A','pack_B','usb','display','touch','camera','rf','audio_sensors')
# Each code-owned metric must appear; plans may add multiple named rails/channels
# for the same metric. Actual limits and rail identities need cited evidence.
G4_METRICS = {
    'power_rail_voltage':('power','V','range'),
    'power_current':('power','A','range'),
    'unexpected_reset_count':('power','count','maximum'),
    'pack_A_current':('pack_A','A','range'),
    'pack_A_temperature':('pack_A','C','range'),
    'pack_B_current':('pack_B','A','range'),
    'pack_B_temperature':('pack_B','C','range'),
    'usb_error_count':('usb','count','maximum'),
    'usb_disconnect_count':('usb','count','maximum'),
    'display_error_count':('display','count','maximum'),
    'touch_position_error':('touch','mm','maximum'),
    'camera_error_count':('camera','count','maximum'),
    'rf_error_count':('rf','count','maximum'),
    'audio_sensor_error_count':('audio_sensors','count','maximum'),
}
G5_METRICS = {
    'operating_force':('N','maximum'), 'unlock_force':('N','maximum'),
    'left_right_skew':('mm','maximum'), 'relock_error':('mm','maximum'),
    'retention_drift':('mm','maximum'), 'fpc_resistance':('ohm','maximum'),
    'display_error_count':('count','maximum'), 'usb_error_count':('count','maximum'),
}
EXPOSURE = {'temperature':('C','temperature_min_C','temperature_max_C'),
            'humidity':('percent','humidity_min_percent','humidity_max_percent'),
            'motion_speed':('mm/s','speed_min_mm_s','speed_max_mm_s'),
            'applied_load':('N','load_min_N','load_max_N')}


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(data):
    def pairs(items):
        result = {}
        for key,value in items:
            if key in result: raise ValueError('duplicate JSON field could hide evidence: '+key)
            result[key] = value
        return result
    def constant(value): raise ValueError('nonfinite JSON number: '+value)
    return json.loads(data,object_pairs_hook=pairs,parse_constant=constant)


def number(value, name, *, minimum=None, integer=False):
    if type(value) not in (int,float) or not math.isfinite(value):
        raise ValueError(name+': finite non-boolean number required')
    if minimum is not None and value < minimum:
        raise ValueError(name+': value below allowed domain')
    if integer and type(value) is not int:
        raise ValueError(name+': integer required')
    return value


def stamp(value):
    if not isinstance(value,str): raise ValueError('timestamp required')
    parsed = dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None: raise ValueError('timestamp must include timezone')
    return parsed


def text(value):
    return isinstance(value,str) and bool(value.strip())


def combine(states):
    return 'fail' if 'fail' in states else 'unknown' if not states or 'unknown' in states else 'pass'


def interval_decision(value, error, criterion, direction):
    if value is None or error is None or criterion is None: return 'unknown'
    value = number(value,'measurement'); error = number(error,'uncertainty',minimum=0)
    lo,hi = value-error,value+error
    number(lo,'measurement lower interval'); number(hi,'measurement upper interval')
    keys = ('minimum','maximum') if direction == 'range' else (direction,)
    if any(criterion.get(k) is None for k in keys): return 'unknown'
    limits = {k:number(criterion[k],'criterion '+k) for k in keys}
    if direction == 'range' and limits['minimum'] > limits['maximum']:
        raise ValueError('reversed acceptance range')
    if ('minimum' in limits and hi < limits['minimum']) or ('maximum' in limits and lo > limits['maximum']):
        return 'fail'
    if ('minimum' in limits and lo < limits['minimum']) or ('maximum' in limits and hi > limits['maximum']):
        return 'unknown'
    return 'pass'


class Evidence:
    def __init__(self, root):
        self.root = Path(root).resolve(); self.checked = {}

    def read(self, reference):
        if not isinstance(reference,dict) or not text(reference.get('path')) or not re.fullmatch(r'[0-9a-f]{64}',str(reference.get('sha256',''))):
            raise ValueError('original evidence path and SHA256 required')
        rel = Path(reference['path'])
        if rel.is_absolute() or '..' in rel.parts: raise ValueError('relative evidence path required')
        path = self.root/rel
        for p in (path,*path.parents):
            if p == self.root: break
            if p.is_symlink(): raise ValueError('evidence symlinks are not accepted')
        if self.root not in path.resolve().parents or not path.is_file():
            raise ValueError('original evidence is absent or outside the evidence root')
        data = path.read_bytes()
        if sha_bytes(data) != reference['sha256']: raise ValueError('original evidence hash mismatch')
        self.checked[path] = reference['sha256']
        return data

    def recheck(self):
        if any(sha_bytes(p.read_bytes()) != h for p,h in self.checked.items()):
            raise ValueError('evidence changed during evaluation')


def binding(repository=ROOT):
    root = Path(repository)
    candidate = strict_json((root/DESIGN_PATHS[2]).read_text())
    head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    import ep5_input_closure
    payloads = ep5_input_closure.native_input_roles('full')
    return {'git_commit':head,'candidate_id':candidate['candidate_id'],
            'source_inventory':'all_top_level_integration_python_and_declared_current_sources_v1',
            'files_sha256':{p:sha_bytes((root/p).read_bytes()) for p in current_source_paths(root)},
            'native_payload_sha256':{p:sha_bytes((root/p).read_bytes()) if (root/p).is_file() else None for p in payloads}}


def current_source_paths(repository=ROOT):
    root = Path(repository)
    return sorted(set(DESIGN_PATHS)|set(CURRENT_EXTRA_SOURCES)|
                  {p.relative_to(root).as_posix() for p in (root/'integration').glob('*.py')})


def verify_binding(value, repository, physical=False):
    if not isinstance(value,dict) or not re.fullmatch(r'[0-9a-f]{40}',str(value.get('git_commit',''))):
        raise ValueError('exact design commit binding required')
    root = Path(repository); files = value.get('files_sha256',{})
    if not isinstance(files,dict) or not set(DESIGN_PATHS) <= set(files):
        raise ValueError('bind geometry, interfaces and current EP5 routing')
    reader = Evidence(root)
    current_head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    import ep5_input_closure
    required_payloads = ep5_input_closure.native_input_roles('full')
    payloads = value.get('native_payload_sha256',{})
    if not isinstance(payloads,dict): raise ValueError('native payload identity map required')
    reader.binding_status = {'bound_commit':value['git_commit'],'current_HEAD':current_head,
        'bound_commit_is_current_HEAD':value['git_commit'] == current_head,
        'physical_commit_bytes_verified':physical,
        'unbound_current_source_paths':sorted(set(current_source_paths(root))-set(files)),
        'unbound_native_payload_paths':sorted(p for p in required_payloads if payloads.get(p) is None)}
    for path,digest in files.items():
        raw = reader.read({'path':path,'sha256':digest})
        if physical:
            try:
                committed = subprocess.check_output(['git','show',value['git_commit']+':'+path],cwd=root,stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as exc:
                raise ValueError('physical design commit payload is unavailable') from exc
            if committed != raw: raise ValueError('physical design bytes differ from the bound commit')
    for path,digest in payloads.items():
        if path not in required_payloads: raise ValueError('unexpected native payload role')
        if digest is None: continue
        raw = reader.read({'path':path,'sha256':digest})
        if physical:
            try: committed = subprocess.check_output(['git','show',value['git_commit']+':'+path],cwd=root,stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as exc: raise ValueError('bound native payload commit is unavailable') from exc
            if committed != raw: raise ValueError('native payload differs from bound physical commit')
    candidate = strict_json((root/DESIGN_PATHS[2]).read_text())
    if value.get('candidate_id') != candidate.get('candidate_id'):
        raise ValueError('qualification belongs to another routing candidate')
    return reader


def prerequisite_decisions(plan, evidence, blockers, acquisition=None):
    expected_gates = ('G3',) if plan['gate'] == 'G4' else ('G3','G4')
    decisions = []
    intervals = {}
    decision_times = {}
    for gate in expected_gates:
        references = plan.get('prerequisites',{}).get(gate,{})
        for specimen in plan.get('specimen_ids',[]):
            initial_blockers = len(blockers)
            reference = references.get(specimen) if isinstance(references,dict) else None
            if reference is None:
                blockers.append('prerequisite_missing:'+gate+':'+specimen); continue
            prior = strict_json(evidence.read(reference))
            if not isinstance(prior,dict): raise ValueError('qualified prerequisite report required')
            if gate == 'G3':
                if prior.get('schema') != 'razr-unpowered-motion-qualification-decision-v1' or prior.get('current_EP5_candidate_bound') is not True or prior.get('execution_kind') != 'physical':
                    raise ValueError('physical current EP5 G3 prerequisite required')
                if prior.get('specimen_id') != specimen: raise ValueError('G3 prerequisite names another specimen')
                prior_binding = prior.get('design_binding',{})
            else:
                if prior.get('schema') != 'razr-product-qualification-decision-v1' or prior.get('gate') != 'G4' or prior.get('execution_kind') != 'physical':
                    raise ValueError('physical G4 prerequisite required')
                if prior.get('execution_binding',{}).get('physical_commit_bytes_verified') is not True:
                    raise ValueError('G4 prerequisite physical commit bytes were not verified')
                if specimen not in prior.get('specimen_ids',[]): raise ValueError('G4 prerequisite names another specimen')
                prior_binding = prior.get('design_binding',{})
            if prior_binding.get('git_commit') != plan['design_binding']['git_commit']:
                raise ValueError('prerequisite and tested design commits differ')
            if any(prior_binding.get('files_sha256',{}).get(p) != h for p,h in plan['design_binding']['files_sha256'].items()):
                raise ValueError('prerequisite source bytes differ from current test')
            # Predeclare a shared superset binding, including G3 artifact roles
            # and G4/G5 native payloads, before acquiring any of the stages.
            # Partial legacy bindings do not qualify an upgraded assembly.
            if prior_binding != plan['design_binding']:
                raise ValueError('prerequisite and current complete design bindings differ')
            status = prior.get('status')
            if status not in ('pass','fail','unknown'): raise ValueError('invalid prerequisite status')
            if status == 'pass' and any(prior.get(k) for k in
                    ('blockers','retained_failure_records','retained_maintenance_records','function_failure_witnesses')):
                raise ValueError('prerequisite pass contradicts its retained evidence')
            if status == 'pass':
                sampled = prior.get('sampled_criteria_status')
                criteria = prior.get('criteria')
                if sampled is None or not isinstance(criteria,list):
                    blockers.append('prerequisite_sampled_results_missing:'+gate+':'+specimen)
                elif sampled != 'pass' or any(not isinstance(c,dict) or c.get('status') != 'pass' for c in criteria):
                    raise ValueError('prerequisite pass contradicts its sampled criteria')
                elif gate == 'G3' and not criteria:
                    blockers.append('prerequisite_sampled_results_missing:'+gate+':'+specimen)
                # G3 retains all metric decisions; G4's criteria is an exception
                # list, so its successful empty list is meaningful only with
                # the actual nonempty, fully sampled observation coverage.
                if gate == 'G4':
                    coverage = prior.get('coverage')
                    observations = prior.get('observations')
                    if not isinstance(coverage,list) or not coverage or type(observations) is not int or observations <= 0:
                        blockers.append('prerequisite_observation_coverage_missing:'+gate+':'+specimen)
                    elif any(not isinstance(c,dict) or c.get('complete') is not True for c in coverage):
                        raise ValueError('prerequisite pass contradicts its observation coverage')
                for c in prior.get('process_decisions',[]):
                    if not isinstance(c,dict) or c.get('status') != 'pass':
                        raise ValueError('prerequisite pass contradicts its process decisions')
            if status != 'pass': blockers.append('prerequisite_not_passed:'+gate+':'+specimen)
            # A shared specimen name and source commit do not identify a repaired
            # or replaced assembly. Bind the retained as-built record itself.
            prior_specimen = (prior.get('as_built_specimen_record') if gate == 'G3'
                              else prior.get('as_built_specimen_records',{}).get(specimen))
            current_specimen = (acquisition or {}).get('as_built',{}).get(specimen,{}).get('specimen_record')
            if prior_specimen is None or current_specimen is None:
                blockers.append('prerequisite_as_built_missing:'+gate+':'+specimen)
            elif evidence.read(prior_specimen) != evidence.read(current_specimen):
                raise ValueError('prerequisite and current as-built specimen records differ')
            previous_start = prior.get('acquisition_started_at_utc')
            previous_end = prior.get('acquisition_ended_at_utc')
            current_start = (acquisition or {}).get('started_at_utc')
            if any(t is None for t in (previous_start,previous_end,current_start)):
                blockers.append('prerequisite_chronology_missing:'+gate+':'+specimen)
            else:
                a,b,c = stamp(previous_start),stamp(previous_end),stamp(current_start)
                if not a < b <= c:
                    raise ValueError('prerequisite acquisition chronology contradicts stage order')
                intervals[specimen,gate] = (a,b)
            # Finishing acquisition is insufficient: its qualifying review/pass
            # must exist before the next physical stage starts.
            reviewed = prior.get('qualification_reviewed_at_utc')
            legacy_reviewed = prior.get('preregistration_verification',{}).get('reviewed_at_utc')
            if reviewed is not None and legacy_reviewed is not None and stamp(reviewed) != stamp(legacy_reviewed):
                raise ValueError('prerequisite review chronology has conflicting declarations')
            reviewed = reviewed if reviewed is not None else legacy_reviewed
            if any(t is None for t in (previous_end,reviewed,current_start)):
                blockers.append('prerequisite_decision_time_missing:'+gate+':'+specimen)
            elif not stamp(previous_end) <= stamp(reviewed) <= stamp(current_start):
                raise ValueError('prerequisite review chronology contradicts stage order')
            else:
                decision_times[specimen,gate] = stamp(reviewed)
            local_blockers = blockers[initial_blockers:]
            admitted_status = 'unknown' if status == 'pass' and local_blockers else status
            decisions.append({'gate':gate,'specimen_id':specimen,'status':admitted_status,
                'reported_status':status,'validation_blockers':list(local_blockers),'source':reference})
    for specimen in plan.get('specimen_ids',[]):
        if (specimen,'G3') in intervals and (specimen,'G4') in intervals:
            if intervals[specimen,'G3'][1] > intervals[specimen,'G4'][0]:
                raise ValueError('prerequisite G3/G4 chronology contradicts stage order')
            if (specimen,'G3') in decision_times and decision_times[specimen,'G3'] > intervals[specimen,'G4'][0]:
                raise ValueError('prerequisite G3 review/G4 chronology contradicts stage order')
    return decisions


def retained_events(plan, record, evidence, blockers):
    """Retain reported failures separately from missing data and maintenance.

    The program checks attachment bytes, not the authenticity of an event.
    A reported failure remains a failure even if samples or its attachment
    are absent. Maintenance invalidates uninterrupted identity, not itself
    an observed failure. The same rules apply to both G4 and G5.
    """
    events = record.get('maintenance_or_replacement_events')
    if events is None:
        blockers.append('maintenance_history_undeclared'); events = []
    elif not isinstance(events,list):
        raise ValueError('maintenance/replacement event list required')
    if events:
        blockers.append('uninterrupted_specimen_identity_broken_by_maintenance_or_replacement')
    for event in events:
        if not isinstance(event,dict) or event.get('specimen_id') not in plan.get('specimen_ids',[]) or not text(event.get('description')):
            raise ValueError('identified maintenance/replacement event required')
        if event.get('source') is None: blockers.append('maintenance_original_missing')
        else: evidence.read(event['source'])
    failures = record.get('failures')
    if failures is None:
        blockers.append('failure_history_undeclared'); failures = []
    elif not isinstance(failures,list):
        raise ValueError('failure record list required')
    for failure in failures:
        if not isinstance(failure,dict) or failure.get('specimen_id') not in plan.get('specimen_ids',[]) or not text(failure.get('description')):
            raise ValueError('identified failure record required')
        if failure.get('source') is None: blockers.append('failure_original_missing')
        else: evidence.read(failure['source'])
    return list(events),list(failures)


def product_inputs(repository=ROOT):
    import product_interfaces as interfaces
    root = Path(repository); config = strict_json((root/'design/product_interfaces.json').read_text())
    interfaces.validate_config(config,root)
    required = list(interfaces.DONOR_FIELDS)
    missing = [k for k in required if not interfaces.identity_value_known(config['donor'].get(k))]
    bound = [x['id'] for x in config['interfaces'] if interfaces.terminal_evidence_bound(x,config,root)]
    identity = interfaces.evidence_record(config.get('donor_evidence',{}).get('identity_record'),'razr-observed-donor-identity-v2',root)
    return {'unknown_donor_identity_fields':missing,'physical_donor_identity_bound':interfaces.donor_identity_bound(config,root),
            'observed_donor_specimen_id':identity.get('specimen_id') if identity else None,
            'physically_bound_interfaces':bound,'missing_physical_interfaces':sorted(interfaces.INTERFACES-set(bound)),
            'actual_part_dimensions_or_supplier_limits_inferred':False}


def _criterion(item, unit, direction, evidence, blockers, label):
    if item is None:
        blockers.append('criterion_missing:'+label); return None
    if not isinstance(item,dict) or item.get('unit') != unit:
        raise ValueError('criterion unit differs: '+label)
    keys = ('minimum','maximum') if direction == 'range' else (direction,)
    if any(item.get(k) is None for k in keys):
        blockers.append('limit_unknown:'+label); return None
    for k in keys: number(item[k],label+'.'+k)
    if direction == 'range' and item['minimum'] > item['maximum']:
        raise ValueError('reversed criterion range')
    if item.get('source') is None or not text(item.get('source_locator')):
        blockers.append('limit_source_missing:'+label); return None
    evidence.read(item['source'])
    return item


def _requirement(plan, key, evidence, blockers, *, minimum=0, integer=False):
    item = plan.get('requirements',{}).get(key)
    if not isinstance(item,dict) or item.get('value') is None:
        blockers.append('requirement_unknown:'+key); return None
    value = number(item['value'],key,minimum=minimum,integer=integer)
    if item.get('source') is None or not text(item.get('source_locator')):
        blockers.append('requirement_source_missing:'+key); return None
    evidence.read(item['source'])
    return value


def _common(plan, record, repository, evidence_root, review):
    evidence = Evidence(evidence_root)
    result = {'schema':'razr-product-qualification-decision-v1','gate':plan.get('gate'),
        'status':'unknown','criteria':[],'blockers':[],
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,
        'physical_phone_verified':False,'unsampled_failure_absence_proved':False,
        'reviewer_identity_authenticated_by_program':False,
        'evaluator_sha256':sha_bytes(Path(__file__).read_bytes())}
    blockers = result['blockers']
    if plan.get('schema') != 'razr-product-qualification-plan-v1' or plan.get('gate') not in ('G4','G5'):
        raise ValueError('supported qualification plan required')
    if plan.get('is_template') is not False: blockers.append('plan_is_template')
    design = verify_binding(plan.get('design_binding'),repository)
    result['execution_binding'] = dict(design.binding_status)
    result['design_binding'] = plan['design_binding']
    if not design.binding_status['bound_commit_is_current_HEAD']:
        blockers.append('historical_commit_is_not_current_qualification')
    if design.binding_status['unbound_current_source_paths']:
        blockers.append('current_geometry_source_closure_incomplete')
    if design.binding_status['unbound_native_payload_paths']:
        blockers.append('current_native_payload_closure_incomplete')
    readiness = product_inputs(repository); result['product_inputs'] = readiness
    if not readiness['physical_donor_identity_bound'] or readiness['missing_physical_interfaces']:
        blockers.append('same_specimen_physical_inputs_incomplete')
    if not isinstance(record,dict):
        blockers.append('physical_acquisition_missing'); return result,evidence,design,None
    if record.get('schema') != 'razr-product-qualification-acquisition-v1' or record.get('gate') != plan['gate']:
        raise ValueError('acquisition schema/gate differs')
    if record.get('design_binding') != plan['design_binding']:
        raise ValueError('acquisition and plan design identities differ')
    if record.get('execution_kind') not in ('physical','synthetic_fixture'):
        raise ValueError('explicit physical/synthetic execution identity required')
    physical = record['execution_kind'] == 'physical'
    if not physical: blockers.append('synthetic_fixture_is_not_physical_qualification')
    else:
        design = verify_binding(plan['design_binding'],repository,physical=True)
        result['execution_binding'] = dict(design.binding_status)
    planned_ids = plan.get('specimen_ids')
    if not isinstance(planned_ids,list) or not planned_ids or len(planned_ids) != len(set(planned_ids)) or not all(text(x) for x in planned_ids):
        blockers.append('predeclared_specimen_inventory_missing')
        planned_ids = []
    if record.get('specimen_ids') != planned_ids:
        raise ValueError('acquisition specimen inventory differs from plan')
    result['specimen_ids'] = planned_ids
    result['retained_maintenance_records'],result['retained_failure_records'] = retained_events(plan,record,evidence,blockers)
    result['prerequisite_decisions'] = prerequisite_decisions(plan,evidence,blockers,record)
    if plan.get('same_donor_specimen_id') is None:
        blockers.append('same_donor_specimen_identity_missing')
    elif plan['same_donor_specimen_id'] != readiness['observed_donor_specimen_id']:
        raise ValueError('plan does not identify the observed donor specimen')
    starts,ends = record.get('started_at_utc'),record.get('ended_at_utc')
    result['acquisition_started_at_utc'] = starts
    result['acquisition_ended_at_utc'] = ends
    declared = plan.get('declared_at_utc')
    if any(x is None for x in (starts,ends,declared)):
        blockers.append('acquisition_or_predeclaration_time_missing'); start = None
    else:
        start,end,pre = stamp(starts),stamp(ends),stamp(declared)
        if not pre < start < end: raise ValueError('plan must precede ordered acquisition times')
    if not text(plan.get('approved_by')) or not plan.get('approval_evidence'):
        blockers.append('plan_approval_evidence_missing')
    for ref in plan.get('approval_evidence',[]): evidence.read(ref)
    plan_digest = sha_bytes(json.dumps(plan,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
    result['plan_semantic_sha256'] = plan_digest
    acquisition_digest = sha_bytes(json.dumps(record,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
    result['acquisition_semantic_sha256'] = acquisition_digest
    if review is None:
        blockers.append('independent_preregistration_attestation_missing')
    else:
        if review.get('plan_semantic_sha256') != plan_digest or review.get('acquisition_semantic_sha256') != acquisition_digest or review.get('specimen_ids') != planned_ids or review.get('gate') != plan['gate']:
            raise ValueError('review does not bind the exact plan and specimens')
        if review.get('conclusion') != 'verified_preregistered_exact_plan' or review.get('independent_of_acquisition') is not True or not text(review.get('reviewed_by')) or not review.get('original_evidence'):
            blockers.append('preregistration_not_attested')
        elif start is None or review.get('verified_registration_at_utc') is None:
            blockers.append('review_chronology_missing')
        elif not stamp(declared) <= stamp(review['verified_registration_at_utc']) < start:
            raise ValueError('preregistration review chronology differs')
        if review.get('reviewed_at_utc') is None:
            blockers.append('review_completion_time_missing')
        elif ends is not None and stamp(review['reviewed_at_utc']) < stamp(ends):
            raise ValueError('exact-acquisition review predates acquisition completion')
        else:
            result['qualification_reviewed_at_utc'] = review['reviewed_at_utc']
        for ref in review.get('original_evidence',[]): evidence.read(ref)
    specimens = record.get('as_built',{})
    result['as_built_specimen_records'] = {}
    result['as_built_donor_specimen_ids'] = {}
    for specimen in planned_ids:
        item = specimens.get(specimen,{})
        specimen_ref = item.get('specimen_record')
        if specimen_ref is None:
            blockers.append('as_built_specimen_record_missing:'+specimen)
        else:
            original = strict_json(evidence.read(specimen_ref))
            if not isinstance(original,dict) or original.get('specimen_id') != specimen:
                raise ValueError('as-built original names another specimen')
            if original.get('design_binding') != plan['design_binding']:
                raise ValueError('as-built original design binding differs')
            if original.get('execution_kind') != record['execution_kind']:
                raise ValueError('as-built original execution kind differs')
            if original.get('is_template') is not False:
                blockers.append('as_built_specimen_record_is_template:'+specimen)
            original_roles = original.get('qualification_assembly')
            if not isinstance(original_roles,dict) or any(role not in original_roles for role in
                    ('parts','material_lots','process','firmware','assembly')):
                blockers.append('as_built_role_binding_missing:'+specimen)
            else:
                for role in ('parts','material_lots','process','firmware','assembly'):
                    if original_roles[role] != item.get(role):
                        raise ValueError('as-built original and current '+role+' records differ')
            # A consistent mutable wrapper cannot relabel the donor recorded
            # in the SHA-bound original. Accept either explicit original
            # location, but require multiple declarations to agree.
            original_donors = [original.get('same_donor_specimen_id')]
            if isinstance(original_roles,dict):
                original_donors.append(original_roles.get('same_donor_specimen_id'))
            original_donors = [value for value in original_donors if value is not None]
            if not original_donors:
                blockers.append('as_built_original_donor_missing:'+specimen)
            elif any(not text(value) for value in original_donors):
                raise ValueError('as-built original donor identity must be nonempty text')
            elif any(value != original_donors[0] for value in original_donors):
                raise ValueError('as-built original has conflicting donor identities')
            else:
                donor = original_donors[0]
                for value in (plan.get('same_donor_specimen_id'),item.get('same_donor_specimen_id')):
                    if value is not None and value != donor:
                        raise ValueError('as-built original donor differs from the plan or current record')
                result['as_built_donor_specimen_ids'][specimen] = donor
            result['as_built_specimen_records'][specimen] = specimen_ref
        if item.get('design_binding') != plan['design_binding']:
            blockers.append('as_built_design_unbound:'+specimen)
        if item.get('same_donor_specimen_id') != plan.get('same_donor_specimen_id') or item.get('same_donor_specimen_id') is None:
            blockers.append('as_built_donor_unbound:'+specimen)
        for role in ('parts','material_lots','process','firmware','assembly'):
            row = item.get(role,{})
            if not text(row.get('identity')) or row.get('source') is None:
                blockers.append('as_built_role_missing:'+specimen+':'+role)
            else: evidence.read(row['source'])
    result['execution_kind'] = record['execution_kind']
    return result,evidence,design,start


def _calibration(item, unit, evidence, blockers, label, start):
    if not isinstance(item,dict) or item.get('absolute_error_bound') is None or item.get('source') is None:
        blockers.append('calibration_missing:'+label); return None
    if item.get('unit') != unit: raise ValueError('calibration unit differs: '+label)
    error = number(item['absolute_error_bound'],'calibration error',minimum=0)
    evidence.read(item['source'])
    if item.get('recorded_at_utc') is None: blockers.append('calibration_time_missing:'+label)
    elif start is not None and stamp(item['recorded_at_utc']) > start: raise ValueError('calibration postdates acquisition')
    return error


def _finish(result, evidence, design, states):
    states = list(states)+[x['status'] for x in result.get('prerequisite_decisions',[]) if x['status'] != 'pass']
    if result.get('retained_failure_records'): states.append('fail')
    result['sampled_criteria_status'] = combine(states)
    result['blockers'] = sorted(set(result['blockers']))
    result['status'] = combine(states+(['unknown'] if result['blockers'] else []))
    if result.get('execution_kind') == 'synthetic_fixture' and result['status'] == 'pass': result['status'] = 'unknown'
    result['scope'] = 'declared sampled protocol only; no independent attachment authenticity or manufacturing release'
    evidence.recheck(); design.recheck()
    if sha_bytes(Path(__file__).read_bytes()) != result['evaluator_sha256']:
        raise ValueError('qualification evaluator changed during execution')
    result['verified_original_evidence_files'] = len(evidence.checked)
    return result


def evaluate_g4(plan, record, repository=ROOT, evidence_root='.', review=None):
    result,evidence,design,start = _common(plan,record,repository,evidence_root,review)
    if plan['gate'] != 'G4': raise ValueError('G4 plan required')
    blockers = result['blockers']; states = []
    requirements = {k:_requirement(plan,k,evidence,blockers,minimum=m,integer=i) for k,m,i in (
        ('minimum_cycles_per_mode',1,True),('minimum_samples_per_phase',2,True),
        ('maximum_sampling_gap_s',0,False),('maximum_alignment_error_s',0,False))}
    if plan.get('phase_order') != list(PHASES) or plan.get('power_modes') != list(MODES):
        raise ValueError('complete current manual phase and original-power mode inventory required')
    for function in FUNCTIONS:
        protocol = plan.get('function_protocols',{}).get(function,{})
        if not text(protocol.get('identity')) or protocol.get('source') is None or not text(protocol.get('source_locator')):
            blockers.append('function_protocol_missing:'+function)
        else: evidence.read(protocol['source'])
    channels = plan.get('channels',{})
    if not isinstance(channels,dict): raise ValueError('named channel map required')
    seen = set(); limits = {}; errors = {}
    for channel,item in channels.items():
        metric = item.get('metric')
        if not text(channel) or metric not in G4_METRICS: raise ValueError('unknown G4 channel')
        function,unit,direction = G4_METRICS[metric]; seen.add(metric)
        if not text(item.get('measured_location')) or item.get('identity_source') is None:
            blockers.append('physical_channel_identity_missing:'+channel)
        else: evidence.read(item['identity_source'])
        limits[channel] = _criterion(item.get('criterion'),unit,direction,evidence,blockers,channel)
        errors[channel] = _calibration((record or {}).get('calibrations',{}).get(channel),unit,evidence,blockers,channel,start)
    for metric in set(G4_METRICS)-seen: blockers.append('mandatory_metric_missing:'+metric)
    if record is None: return _finish(result,evidence,design,['unknown'])
    for function in FUNCTIONS:
        attachment = record.get('function_evidence',{}).get(function,{})
        if attachment.get('source') is None or not text(attachment.get('source_locator')):
            blockers.append('function_original_evidence_missing:'+function)
        else: evidence.read(attachment['source'])
    if record.get('raw_observations') is None:
        blockers.append('raw_observations_missing'); return _finish(result,evidence,design,['unknown'])
    rows = strict_json(evidence.read(record['raw_observations']))
    if not isinstance(rows,list): raise ValueError('original observation list required')
    windows = record.get('phase_windows',[])
    if not isinstance(windows,list): raise ValueError('phase window list required')
    window_map = {}; by_run = {}; previous = {}
    for window in windows:
        specimen,mode,cycle,phase = (window.get(k) for k in ('specimen_id','mode','cycle','phase'))
        if specimen not in plan.get('specimen_ids',[]) or mode not in MODES or phase not in PHASES:
            raise ValueError('unexpected specimen/mode/phase')
        number(cycle,'cycle',minimum=1,integer=True)
        a,b = number(window.get('start_s'),'phase start',minimum=0),number(window.get('end_s'),'phase end',minimum=0)
        if a >= b: raise ValueError('positive phase duration required')
        key = (specimen,mode,cycle,phase)
        if key in window_map: raise ValueError('duplicate phase window')
        run = (specimen,mode,cycle); by_run.setdefault(run,[]).append(phase)
        if a < previous.get(specimen,-math.inf): raise ValueError('overlapping or reversed phase windows across runs')
        if start is not None and b > (stamp(record['ended_at_utc'])-start).total_seconds():
            raise ValueError('phase window exceeds acquisition duration')
        previous[specimen] = b; window_map[key] = {'window':window,'rows':[]}
    for run,phases in by_run.items():
        if phases != list(PHASES): blockers.append('incomplete_phase_program:'+str(run))
    for specimen in plan.get('specimen_ids',[]):
        for mode in MODES:
            cycles = sorted({c for s,m,c in by_run if s == specimen and m == mode})
            need = requirements['minimum_cycles_per_mode']
            if not cycles or cycles != list(range(1,max(cycles)+1)) or (need is not None and len(cycles) < need):
                blockers.append('insufficient_complete_cycles:'+specimen+':'+mode)
    alignment = record.get('alignment_error_bound_s')
    if alignment is None or record.get('synchronization_evidence') is None:
        blockers.append('time_alignment_evidence_missing'); alignment = None
    else:
        number(alignment,'alignment error',minimum=0); evidence.read(record['synchronization_evidence'])
        if requirements['maximum_alignment_error_s'] is not None and alignment > requirements['maximum_alignment_error_s']:
            blockers.append('time_alignment_exceeds_limit')
    prior_row = {}
    result['function_failure_witnesses'] = []
    result['function_unknown_cells'] = 0
    for row in rows:
        key = tuple(row.get(k) for k in ('specimen_id','mode','cycle','phase'))
        if key not in window_map: raise ValueError('observation has no declared phase window')
        t = number(row.get('time_s'),'observation time',minimum=0); window = window_map[key]['window']
        if not window['start_s'] <= t <= window['end_s'] or t <= prior_row.get(key,-math.inf):
            raise ValueError('observation timing inconsistent with its phase')
        prior_row[key] = t; window_map[key]['rows'].append(row)
        outcomes = row.get('function_outcomes',{})
        if not isinstance(outcomes,dict) or set(outcomes)-set(FUNCTIONS): raise ValueError('unknown function outcome')
        for function in FUNCTIONS:
            outcome = outcomes.get(function)
            if outcome not in (None,'observed_ok','observed_failure','not_observed'): raise ValueError('invalid function outcome')
            states.append('fail' if outcome == 'observed_failure' else 'pass' if outcome == 'observed_ok' else 'unknown')
            if outcome == 'observed_failure':
                result['function_failure_witnesses'].append({'specimen_id':key[0],'mode':key[1],'cycle':key[2],'phase':key[3],'time_s':t,'function':function,'raw_observations':record['raw_observations']})
            elif outcome != 'observed_ok': result['function_unknown_cells'] += 1
        values = row.get('values',{})
        if not isinstance(values,dict) or set(values)-set(channels): raise ValueError('unknown measured channel')
        for channel,item in channels.items():
            metric = item['metric']; _,unit,direction = G4_METRICS[metric]; value = values.get(channel)
            if value is not None:
                number(value,'channel '+channel)
                if unit == 'count': number(value,'event count',minimum=0,integer=True)
            decision = interval_decision(value,errors[channel],limits[channel],direction)
            states.append(decision)
            if decision != 'pass': result['criteria'].append({'specimen_id':key[0],'mode':key[1],'cycle':key[2],'phase':key[3],'time_s':t,'channel':channel,'status':decision})
    coverage = []; continuous_prior_sample = {}
    for key,item in window_map.items():
        samples = item['rows']; w = item['window']; n = requirements['minimum_samples_per_phase']
        gaps = ([samples[0]['time_s']-w['start_s']] + [b['time_s']-a['time_s'] for a,b in zip(samples,samples[1:])] + [w['end_s']-samples[-1]['time_s']]) if samples else [w['end_s']-w['start_s']]
        gap = max(gaps)+(2*alignment if alignment is not None else 0)
        sequence = key[:2]
        if samples:
            if sequence in continuous_prior_sample:
                gap = max(gap,samples[0]['time_s']-continuous_prior_sample[sequence]+(2*alignment if alignment is not None else 0))
            continuous_prior_sample[sequence] = samples[-1]['time_s']
        complete = bool(samples) and n is not None and len(samples) >= n and alignment is not None and requirements['maximum_sampling_gap_s'] is not None and gap <= requirements['maximum_sampling_gap_s']
        if not complete: blockers.append('sample_coverage_incomplete:'+str(key))
        coverage.append({'specimen_id':key[0],'mode':key[1],'cycle':key[2],'phase':key[3],'samples':len(samples),'maximum_gap_including_boundaries_s':gap,'complete':complete})
    result['coverage'] = coverage; result['observations'] = len(rows)
    result['required_function_phase_cells_per_cycle_and_mode'] = len(FUNCTIONS)*len(PHASES)
    return _finish(result,evidence,design,states or ['unknown'])


def rederive_g5_cycles(plan, record, evidence, blockers, start):
    """Recompute phase coverage, exposure extrema and cycle counts from samples.

    The CSV is a checked summary only. It cannot create exposure or a complete
    phase absent from the retained samples and synchronized phase windows.
    """
    minimum = _requirement(plan,'minimum_samples_per_exposure_phase',evidence,blockers,minimum=2,integer=True)
    alignment_limit = _requirement(plan,'maximum_alignment_error_s',evidence,blockers,minimum=0)
    required = ('raw_exposure_samples','exposure_phase_windows','phase_observation_evidence','synchronization_evidence')
    if any(record.get(k) is None for k in required):
        blockers.append('summary_only_G5_raw_exposure_or_phase_evidence_missing')
        return None,[]
    raw = strict_json(evidence.read(record['raw_exposure_samples']))
    windows = strict_json(evidence.read(record['exposure_phase_windows']))
    evidence.read(record['phase_observation_evidence']); evidence.read(record['synchronization_evidence'])
    if not isinstance(raw,list) or not isinstance(windows,list): raise ValueError('raw G5 sample/window lists required')
    alignment = record.get('alignment_error_bound_s')
    if alignment is None:
        blockers.append('G5_alignment_error_unknown')
    else:
        number(alignment,'G5 alignment error',minimum=0)
        if alignment_limit is None or alignment > alignment_limit: blockers.append('G5_alignment_error_exceeds_declared_limit')
    by_phase = {}; by_cycle = {}; prior = {}
    for window in windows:
        specimen,cycle,phase = (window.get(k) for k in ('specimen_id','cycle','phase'))
        if specimen not in plan.get('specimen_ids',[]) or phase not in PHASES: raise ValueError('unplanned raw G5 phase')
        number(cycle,'raw cycle',minimum=1,integer=True)
        a,b = number(window.get('start_s'),'raw phase start',minimum=0),number(window.get('end_s'),'raw phase end',minimum=0)
        if a >= b or a < prior.get(specimen,-math.inf): raise ValueError('raw G5 phase chronology overlaps or reverses')
        if start is not None and b > (stamp(record['ended_at_utc'])-start).total_seconds(): raise ValueError('raw exposure exceeds acquisition duration')
        prior[specimen] = b; key = (specimen,cycle,phase)
        if key in by_phase: raise ValueError('duplicate raw G5 phase')
        by_phase[key] = {'window':window,'samples':[]}
        by_cycle.setdefault((specimen,cycle),[]).append(key)
    last_sample = {}
    for sample in raw:
        key = tuple(sample.get(k) for k in ('specimen_id','cycle','phase'))
        if key not in by_phase: raise ValueError('raw exposure sample has no declared phase')
        t = number(sample.get('time_s'),'raw exposure time',minimum=0)
        w = by_phase[key]['window']
        if not w['start_s'] <= t <= w['end_s'] or t <= last_sample.get(key,-math.inf):
            raise ValueError('raw exposure sample chronology differs')
        last_sample[key] = t
        values = sample.get('values')
        if not isinstance(values,dict) or set(values)-set(EXPOSURE): raise ValueError('unknown raw exposure quantity')
        for name in EXPOSURE:
            if values.get(name) is not None: number(values[name],'raw '+name)
        by_phase[key]['samples'].append(sample)
    derived = []; coverage = []; continuous_prior_sample = {}
    for (specimen,cycle),keys in sorted(by_cycle.items()):
        actual_phases = [key[2] for key in keys if by_phase[key]['samples']]
        if [key[2] for key in keys] != list(PHASES) or actual_phases != list(PHASES):
            blockers.append('raw_G5_phase_program_incomplete:'+specimen+':'+str(cycle))
        maximum_gap = 0.; all_samples = []
        for key in keys:
            item = by_phase[key]; samples = item['samples']; w = item['window']
            gaps = ([samples[0]['time_s']-w['start_s']] + [b['time_s']-a['time_s'] for a,b in zip(samples,samples[1:])] + [w['end_s']-samples[-1]['time_s']]) if samples else [w['end_s']-w['start_s']]
            gap = max(gaps)+(2*alignment if alignment is not None else 0.)
            number(gap,'raw gap with synchronization uncertainty',minimum=0)
            maximum_gap = max(maximum_gap,gap); all_samples.extend(samples)
            complete = minimum is not None and len(samples) >= minimum and alignment is not None
            if not complete: blockers.append('raw_G5_phase_undersampled:'+str(key))
            for name in EXPOSURE:
                if not samples or any(x['values'].get(name) is None for x in samples):
                    blockers.append('raw_G5_quantity_incomplete:'+str(key)+':'+name)
            coverage.append({'specimen_id':specimen,'cycle':cycle,'phase':key[2],
                'samples':len(samples),'maximum_gap_including_boundaries_s':gap,'minimum_sample_and_alignment_coverage':complete})
        # Include intervals between named phases, too; phase-only gap checks
        # must not conceal an unobserved segment of the cycle.
        for first,second in zip(keys,keys[1:]):
            gap = by_phase[second]['window']['start_s']-by_phase[first]['window']['end_s']
            maximum_gap = max(maximum_gap,gap+(2*alignment if alignment is not None else 0.))
        # Actual adjacent samples cross phase and cycle boundaries. Separate
        # window-edge gaps cannot replace their sum across an unobserved span.
        if all_samples:
            times = [x['time_s'] for x in all_samples]
            if specimen in continuous_prior_sample:
                times.insert(0,continuous_prior_sample[specimen])
            maximum_gap = max(maximum_gap,max((b-a for a,b in zip(times,times[1:])),default=0.)+(2*alignment if alignment is not None else 0.))
            continuous_prior_sample[specimen] = all_samples[-1]['time_s']
        row = {'specimen_id':specimen,'cycle':str(cycle),
            'start_s':str(by_phase[keys[0]]['window']['start_s']),
            'end_s':str(by_phase[keys[-1]]['window']['end_s']),
            'maximum_sampling_gap_s':str(maximum_gap),'observed_phase_order':'|'.join(actual_phases)}
        for name,(_,low,high) in EXPOSURE.items():
            values = [x['values'][name] for x in all_samples if x['values'].get(name) is not None]
            row[low] = str(min(values)) if values else ''; row[high] = str(max(values)) if values else ''
        derived.append(row)
    return derived,coverage


def evaluate_g5(plan, record, repository=ROOT, evidence_root='.', review=None):
    result,evidence,design,start = _common(plan,record,repository,evidence_root,review)
    if plan['gate'] != 'G5': raise ValueError('G5 plan required')
    blockers = result['blockers']; states = []
    if plan.get('phase_order') != list(PHASES):
        raise ValueError('G5 must retain the current full manual cycle definition')
    protocol = plan.get('cycle_protocol',{})
    if not text(protocol.get('identity')) or protocol.get('source') is None or not text(protocol.get('source_locator')):
        blockers.append('cycle_protocol_missing')
    else: evidence.read(protocol['source'])
    need_cycles = _requirement(plan,'required_cycles',evidence,blockers,minimum=1,integer=True)
    min_samples = _requirement(plan,'minimum_specimens',evidence,blockers,minimum=1,integer=True)
    max_gap = _requirement(plan,'maximum_exposure_sampling_gap_s',evidence,blockers,minimum=0)
    if min_samples is not None and len(plan.get('specimen_ids',[])) < min_samples: blockers.append('insufficient_predeclared_specimens')
    checkpoints = plan.get('checkpoints_cycles')
    if not isinstance(checkpoints,list) or not checkpoints:
        blockers.append('predeclared_checkpoints_missing'); checkpoints = []
    else:
        for n in checkpoints: number(n,'checkpoint',minimum=0,integer=True)
        if checkpoints != sorted(set(checkpoints)) or checkpoints[0] != 0:
            raise ValueError('ordered unique checkpoints including zero required')
        if need_cycles is not None and checkpoints[-1] != need_cycles:
            raise ValueError('final checkpoint must equal required exposure')
    limits = {name:_criterion(plan.get('criteria',{}).get(name),unit,direction,evidence,blockers,name) for name,(unit,direction) in G5_METRICS.items()}
    exposure_limits = {name:_criterion(plan.get('exposure',{}).get(name),unit,'range',evidence,blockers,'exposure:'+name) for name,(unit,_,_) in EXPOSURE.items()}
    dimensions = plan.get('critical_dimensions',{})
    if not isinstance(dimensions,dict) or not dimensions: blockers.append('critical_dimension_inventory_missing'); dimensions = {}
    dimension_limits = {name:_criterion(item,'mm','range',evidence,blockers,'dimension:'+name) for name,item in dimensions.items()}
    if record is None: return _finish(result,evidence,design,['unknown'])
    if record.get('cycle_csv') is None:
        blockers.append('raw_cycle_log_missing'); cycle_rows = []
    else:
        reader = csv.DictReader(io.StringIO(evidence.read(record['cycle_csv']).decode('utf-8-sig')))
        fields = {'specimen_id','cycle','start_s','end_s','maximum_sampling_gap_s','observed_phase_order'} | {k for _,a,b in EXPOSURE.values() for k in (a,b)}
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)) or set(reader.fieldnames) != fields:
            raise ValueError('cycle log must retain the complete exposure columns')
        cycle_rows = list(reader)
    derived,raw_coverage = rederive_g5_cycles(plan,record,evidence,blockers,start)
    result['raw_phase_coverage'] = raw_coverage
    result['G5_cycle_evidence_scope'] = 'raw_samples_and_windows_rederived' if derived is not None else 'summary_only_not_qualifying'
    if derived is not None:
        if len(cycle_rows) != len(derived): raise ValueError('cycle summary row count differs from original raw samples')
        for declared,recomputed in zip(cycle_rows,derived):
            for key in ('specimen_id','cycle','observed_phase_order'):
                if declared[key] != recomputed[key]: raise ValueError('cycle summary identity/phase differs from raw exposure')
            for key in set(recomputed)-{'specimen_id','cycle','observed_phase_order'}:
                if declared[key] == recomputed[key] == '': continue
                if not declared[key] or not recomputed[key] or not math.isclose(number(float(declared[key]),'summary number'),number(float(recomputed[key]),'rederived number'),rel_tol=1e-12,abs_tol=1e-12):
                    raise ValueError('cycle summary statistic differs from original raw samples: '+key)
        cycle_rows = derived
    exposure_errors = {name:_calibration(record.get('calibrations',{}).get('exposure:'+name),unit,evidence,blockers,'exposure:'+name,start) for name,(unit,_,_) in EXPOSURE.items()}
    counts = {}; times = {}; result['exposure_deviations_or_unknowns'] = []
    for row in cycle_rows:
        specimen = row['specimen_id']
        if specimen not in plan.get('specimen_ids',[]): raise ValueError('unplanned cycle specimen')
        try: n = int(row['cycle'])
        except ValueError as exc: raise ValueError('integer cycle index required') from exc
        if str(n) != row['cycle'] or n != counts.get(specimen,0)+1: raise ValueError('complete consecutive original cycle inventory required')
        a,b = number(float(row['start_s']),'cycle start',minimum=0),number(float(row['end_s']),'cycle end',minimum=0)
        if a >= b or a < times.get(specimen,-math.inf): raise ValueError('invalid cycle chronology')
        if start is not None and b > (stamp(record['ended_at_utc'])-start).total_seconds():
            raise ValueError('cycle log exceeds acquisition duration')
        if row['observed_phase_order'].split('|') != list(PHASES):
            blockers.append('incomplete_original_cycle_program:'+specimen+':'+str(n))
        counts[specimen] = n; times[specimen] = b
        gap = number(float(row['maximum_sampling_gap_s']),'exposure gap',minimum=0)
        if max_gap is None or gap > max_gap: blockers.append('cycle_exposure_coverage_incomplete:'+specimen+':'+str(n))
        for name,(_,low,high) in EXPOSURE.items():
            if not row[low] or not row[high]: states.append('unknown'); continue
            lo,hi = number(float(row[low]),low),number(float(row[high]),high)
            if lo > hi: raise ValueError('reversed measured exposure interval')
            for label,value in (('minimum',lo),('maximum',hi)):
                decision = interval_decision(value,exposure_errors[name],exposure_limits[name],'range')
                states.append(decision)
                if decision != 'pass': result['exposure_deviations_or_unknowns'].append({'specimen_id':specimen,'cycle':n,'quantity':name,'bound':label,'status':decision,'scope':'protocol exposure condition'})
    for specimen in plan.get('specimen_ids',[]):
        if need_cycles is None or counts.get(specimen,0) != need_cycles:
            blockers.append('required_lifetime_exposure_incomplete:'+specimen)
    if record.get('checkpoint_observations') is None:
        blockers.append('raw_checkpoint_observations_missing'); observations = []
    else: observations = strict_json(evidence.read(record['checkpoint_observations']))
    observed = set()
    for row in observations:
        specimen,n,metric = row.get('specimen_id'),row.get('cycle'),row.get('metric')
        if specimen not in plan.get('specimen_ids',[]) or n not in checkpoints or metric not in G5_METRICS:
            raise ValueError('unplanned checkpoint observation')
        key = (specimen,n,metric)
        if key in observed: raise ValueError('duplicate checkpoint result')
        observed.add(key); unit,direction = G5_METRICS[metric]
        error = _calibration(record.get('calibrations',{}).get(metric),unit,evidence,blockers,metric,start)
        if row.get('value') is not None and unit == 'count': number(row['value'],'observed event count',minimum=0,integer=True)
        outcome = row.get('reported_outcome')
        if outcome not in (None,'observed_ok','observed_failure','not_observed'): raise ValueError('invalid checkpoint outcome')
        if outcome == 'observed_failure': states.append('fail')
        elif outcome != 'observed_ok': states.append('unknown')
        decision = interval_decision(row.get('value'),error,limits[metric],direction); states.append(decision)
        result['criteria'].append({'specimen_id':specimen,'cycle':n,'metric':metric,'status':decision,'reported_outcome':outcome})
    expected = {(s,n,m) for s in plan.get('specimen_ids',[]) for n in checkpoints for m in G5_METRICS}
    if observed != expected: blockers.append('checkpoint_metric_coverage_incomplete')
    process_seen = set(); result['process_decisions'] = []
    for row in record.get('process_measurements',[]):
        key = (row.get('specimen_id'),row.get('dimension'))
        if key[0] not in plan.get('specimen_ids',[]) or key[1] not in dimensions or key in process_seen:
            raise ValueError('duplicate or unplanned process measurement')
        process_seen.add(key)
        if row.get('source') is None: blockers.append('process_original_missing:'+str(key))
        else: evidence.read(row['source'])
        error = _calibration(record.get('calibrations',{}).get('dimension:'+key[1]),'mm',evidence,blockers,'dimension:'+key[1],start)
        decision = interval_decision(row.get('value'),error,dimension_limits[key[1]],'range')
        states.append(decision)
        result['process_decisions'].append({'specimen_id':key[0],'dimension':key[1],'status':decision})
    if process_seen != {(s,d) for s in plan.get('specimen_ids',[]) for d in dimensions}:
        blockers.append('process_dimension_coverage_incomplete')
    result['completed_cycles_by_specimen'] = counts
    result['expected_checkpoint_metric_cells'] = len(expected)
    result['observed_checkpoint_metric_cells'] = len(observed)
    return _finish(result,evidence,design,states or ['unknown'])


def templates(repository=ROOT):
    common = {'schema':'razr-product-qualification-plan-v1','is_template':True,
              'design_binding':binding(repository),'specimen_ids':[],
              'same_donor_specimen_id':None,
              'declared_at_utc':None,'approved_by':None,'approval_evidence':[],
              'prerequisites':{}}
    def requirement(): return {'value':None,'source':None,'source_locator':None}
    def criterion(unit,direction):
        return {'unit':unit,**{k:None for k in (('minimum','maximum') if direction == 'range' else (direction,))},'source':None,'source_locator':None}
    g4 = {**common,'gate':'G4','phase_order':list(PHASES),'power_modes':list(MODES),
          'function_protocols':{f:{'identity':None,'source':None,'source_locator':None} for f in FUNCTIONS},
          'requirements':{k:requirement() for k in ('minimum_cycles_per_mode','minimum_samples_per_phase','maximum_sampling_gap_s','maximum_alignment_error_s')},
          'channels':{m:{'metric':m,'measured_location':None,'identity_source':None,'criterion':criterion(u,d)} for m,(_,u,d) in G4_METRICS.items()}}
    g5 = {**common,'gate':'G5','requirements':{k:requirement() for k in ('required_cycles','minimum_specimens','maximum_exposure_sampling_gap_s','minimum_samples_per_exposure_phase','maximum_alignment_error_s')},
          'phase_order':list(PHASES),'cycle_protocol':{'identity':None,'source':None,'source_locator':None},
          'checkpoints_cycles':[],'criteria':{m:criterion(u,d) for m,(u,d) in G5_METRICS.items()},
          'exposure':{m:criterion(u,'range') for m,(u,_,_) in EXPOSURE.items()},'critical_dimensions':{}}
    return {'G4':g4,'G5':g5}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',type=Path,default=ROOT)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--plan',type=Path)
    parser.add_argument('--acquisition',type=Path)
    parser.add_argument('--review',type=Path)
    parser.add_argument('--templates',action='store_true')
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('new output required')
    if args.templates:
        args.output.mkdir(parents=True)
        plans = templates(args.repository)
        for gate,plan in plans.items():
            (args.output/(gate+'-plan.template.json')).write_text(json.dumps(plan,indent=2)+'\n')
            decision = (evaluate_g4 if gate == 'G4' else evaluate_g5)(plan,None,args.repository,args.output)
            (args.output/(gate+'-current-readiness.json')).write_text(json.dumps(decision,indent=2)+'\n')
        (args.output/'physical-input-inventory.json').write_text(json.dumps(product_inputs(args.repository),indent=2)+'\n')
    else:
        if args.plan is None: parser.error('--plan is required without --templates')
        plan = strict_json(args.plan.read_text()); record = strict_json(args.acquisition.read_text()) if args.acquisition else None
        review = strict_json(args.review.read_text()) if args.review else None
        result = (evaluate_g4 if plan['gate'] == 'G4' else evaluate_g5)(plan,record,args.repository,args.acquisition.parent if args.acquisition else args.plan.parent,review)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        print(json.dumps({'gate':result['gate'],'status':result['status'],'blockers':len(result['blockers'])}))


if __name__ == '__main__': main()
