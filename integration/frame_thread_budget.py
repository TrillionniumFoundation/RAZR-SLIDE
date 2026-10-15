"""Finite-engagement and preload screens for ONE frame screw.

A selected nominal thread is not a measured fit, a material allowable, or a
fixed CAD bond. Missing physical limits remain undetermined. All dimensions
are mm, angles degrees, forces N and torques N m. No hardware is actuated.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
import argparse
import json
import math
from pathlib import Path


def real(x: object, name: str, *, minimum: float | None = None) -> float:
    if type(x) not in (float, int) or not math.isfinite(x):
        raise ValueError(f'{name}: finite non-boolean real required')
    v = float(x)
    if minimum is not None and v < minimum:
        raise ValueError(f'{name}: must be at least {minimum}')
    return v


@dataclass(frozen=True)
class Span:
    lo: float
    hi: float

    def __post_init__(self):
        object.__setattr__(self, 'lo', real(self.lo, 'lower bound'))
        object.__setattr__(self, 'hi', real(self.hi, 'upper bound'))
        if self.lo > self.hi:
            raise ValueError('reversed interval')

    @classmethod
    def read(cls, value, name, nonnegative=True):
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError(name + ': explicit [minimum, maximum] required')
        r = cls(*value)
        if nonnegative and r.lo < 0:
            raise ValueError(name + ': negative dimension')
        return r

    def endpoints(self):
        return (self.lo, self.hi)


ENGAGEMENT_FIELDS = ('underhead_length_mm', 'nut_seat_from_screw_seat_mm',
                     'nut_height_mm', 'male_underhead_incomplete_mm',
                     'male_tip_incomplete_mm', 'female_entry_incomplete_mm',
                     'female_exit_incomplete_mm')


def overlap(length, grip, height, underhead, tip, entry, exit_loss):
    a, b = underhead, length - tip
    c, d = grip + entry, grip + height - exit_loss
    return max(0., min(b, d) - max(a, c))


def engagement_bounds(values: dict) -> dict:
    if not isinstance(values, dict):
        raise ValueError('named dimension intervals required')
    supplied = {k: Span.read(values[k], k) for k in ENGAGEMENT_FIELDS
                if values.get(k) is not None}
    missing = [k for k in ENGAGEMENT_FIELDS if k not in supplied]
    if missing:
        return {'status': 'undetermined', 'missing_inputs': missing,
                'actual_complete_thread_count': None, 'candidate_go': False}
    b = [supplied[k] for k in ENGAGEMENT_FIELDS]
    if b[0].lo <= 0 or b[2].lo <= 0:
        raise ValueError('positive screw length and nut height required')
    # overlap = max(0, min of four affine differences); its minimum on the
    # independent interval box occurs at a vertex. Shared grip is used ONCE.
    vertices = list(product(*(x.endpoints() for x in b)))
    vals = [overlap(*x) for x in vertices]
    lower = min(vals)
    # Largest possible intervals use longest screw/nut and smallest end losses.
    # Their relative shift can attain the maximum at a bound or aligned end.
    L,g,H,u,t,c,d = b
    candidates = {g.lo, g.hi,
                  min(g.hi, max(g.lo, u.lo-c.lo)),
                  min(g.hi, max(g.lo, L.hi-t.lo-H.hi+d.lo))}
    upper = max(overlap(L.hi, x, H.hi, u.lo, t.lo, c.lo, d.lo)
                for x in candidates)
    lower_coverage = g.lo+c.lo-u.hi
    upper_coverage = L.lo-t.hi-(g.hi+H.hi-d.lo)
    return {'status': 'bounded_geometric_screen',
            'complete_form_overlap_mm': [lower, upper],
            'worst_corner': dict(zip(ENGAGEMENT_FIELDS, vertices[vals.index(lower)])),
            'nominal_solid_overlap_not_used_as_effective_engagement': True,
            'lower_end_coverage_margin_mm': lower_coverage,
            'upper_end_coverage_margin_mm': upper_coverage,
            'all_female_complete_form_axial_interval_covered':
                lower_coverage >= 0 and upper_coverage >= 0 and lower > 0,
            'tip_protrusion_mm': [L.lo-g.hi-H.hi, L.hi-g.lo-H.lo],
            'independent_bound_box_not_supplier_tolerance': True,
            'radial_fit_lead_pitch_error_and_strength_not_checked': True,
            'actual_complete_thread_count': None, 'candidate_go': False}


def lead_branch(axial_mm, screw_deg, nut_deg, pitch_mm, backlash_mm,
                complete_overlap_mm):
    dz, a, b = [real(v,n) for v,n in zip((axial_mm,screw_deg,nut_deg),
                                        ('axial displacement','screw angle','nut angle'))]
    pitch=real(pitch_mm,'pitch',minimum=0.)
    play=real(backlash_mm,'axial backlash',minimum=0.)
    length=real(complete_overlap_mm,'complete overlap',minimum=0.)
    if pitch <= 0:
        raise ValueError('positive lead required')
    residual=dz-pitch*(a-b)/360.
    return {'engaged': length > 0,
            'local_unwrapped_lead_residual_mm': residual,
            'on_selected_engaged_branch': None if length==0 else abs(residual)<=play/2+1e-12,
            'disengaged_motion_unconstrained_by_this_law': length==0,
            'conditional_ideal_lead_law_not_native_collision_or_retention_capacity': True,
            'screw_rotation_not_automatically_locked': True}


PRELOAD_FIELDS = ('separating_load_N', 'load_fraction', 'allowable_total_bolt_force_N',
                  'preload_fractional_scatter', 'preload_loss_N', 'preload_gain_N',
                  'required_remaining_clamp_N')


def preload_window(values: dict) -> dict:
    """Invert the same closed two-spring model as roof_joint_budget.screen.

    One screw's load must already include its actual introduction/prying model;
    a minimum reaction from a normal-only LP is NOT a physical upper load.
    """
    if not isinstance(values, dict):
        raise ValueError('named preload inputs required')
    spans = {k: Span.read(values[k],k) for k in PRELOAD_FIELDS
             if k != 'preload_fractional_scatter' and values.get(k) is not None}
    f=values.get('preload_fractional_scatter')
    if f is not None:
        f=real(f,'preload scatter',minimum=0.)
        if f>=1:raise ValueError('fractional scatter must be less than one')
    missing=[k for k in PRELOAD_FIELDS if values.get(k) is None]
    if missing:
        return {'status':'undetermined','missing_inputs':missing,'candidate_go':False}
    P,C,A,loss,gain,clamp=[spans[k] for k in ('separating_load_N','load_fraction',
        'allowable_total_bolt_force_N','preload_loss_N','preload_gain_N','required_remaining_clamp_N')]
    if C.hi>=1 or A.lo<=0 or clamp.lo<=0:
        raise ValueError('load fraction below one, positive allowable and clamp reserve required')
    # The limiting cases differ: low C unloads the joint, high C loads the bolt.
    low=((1-C.lo)*P.hi+loss.hi+clamp.hi)/(1-f)
    high=(A.lo-C.hi*P.hi-gain.hi)/(1+f)
    return {'status':'conditional_window_exists' if high>=low else 'no_robust_window',
            'nominal_preload_lower_N':low,'nominal_preload_upper_N':high,
            'not_an_installation_instruction':True,'not_a_load_sharing_solver':True,
            'closed_joint_model_only':True,'candidate_go':False}


def torque_window(required_preload: Span, nut_factor: Span, diameter_mm,
                  tool_fraction_error, prevailing_torque_Nm: Span,
                  max_actual_torque_Nm):
    """Optional inverse T=K*F*d + prevailing torque, without a default K.

    Preload here is the required as-installed preload interval; service loss,
    gain, load, and strength must first be included in that interval.
    """
    d=real(diameter_mm,'diameter',minimum=0.)/1000.
    error=real(tool_fraction_error,'tool error',minimum=0.)
    maximum=real(max_actual_torque_Nm,'maximum actual torque',minimum=0.)
    if d<=0 or error>=1 or nut_factor.lo<=0 or required_preload.lo<0 or prevailing_torque_Nm.lo<0:
        raise ValueError('invalid torque/preload bounds')
    low=(nut_factor.hi*d*required_preload.lo+prevailing_torque_Nm.hi)/(1-error)
    high=min((nut_factor.lo*d*required_preload.hi+prevailing_torque_Nm.lo)/(1+error),
             maximum/(1+error))
    return {'status':'conditional_window_exists' if high>=low else 'no_robust_torque_window',
            'commanded_torque_lower_Nm':low,'commanded_torque_upper_Nm':high,
            'catalogue_maximum_not_selected_as_setpoint':True,
            'requires_same_hardware_and_surface_torque_tension_data':True,
            'not_an_installation_instruction':True}


def evaluate(document):
    return {'scope':document['scope'],
            'engagement':engagement_bounds(document['engagement_inputs']),
            'preload':preload_window(document['preload_inputs']),
            'lead_model_is_conditional_not_material_proof':True,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=evaluate(json.loads(a.inputs.read_text()))
    with a.output.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps(r))
