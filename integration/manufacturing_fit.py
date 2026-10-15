"""Dimensional admission for a named catalogue candidate; never a strength release.

Signed chains retain correlation for a shared error source. A negative
clearance lower bound means the scenario is not certified; it is not itself a
native interference witness. Vendor nominal dimensions are not max-material
limits. Torque ceilings do not determine the joint's preload.
"""
from dataclasses import dataclass
import math


def real(x, name='value', *, positive=False):
    if type(x) not in (int, float) or not math.isfinite(x):
        raise ValueError('finite real required: '+name)
    if x < 0 or (positive and x == 0):
        raise ValueError('nonnegative/positive value required: '+name)
    return float(x)


@dataclass(frozen=True)
class CatalogueScrew:
    part_number: str = 'NBK SNZS-M1-5'
    diameter_mm: float = 1.0
    pitch_mm: float = .25
    length_under_head_mm: float = 5.0
    head_diameter_mm: float = 1.8
    head_height_mm: float = .45
    published_max_torque_Nm: float = .02

    def __post_init__(self):
        if not self.part_number: raise ValueError('named catalogue part required')
        for name in ('diameter_mm','pitch_mm','length_under_head_mm',
                     'head_diameter_mm','head_height_mm','published_max_torque_Nm'):
            real(getattr(self,name),name,positive=True)
        if self.head_diameter_mm <= self.diameter_mm: raise ValueError('head must bear on seat')


def axial_fit(seat_mm, *, female_start_mm=5.70, blind_end_mm=7.00,
              screw=CatalogueScrew()):
    seat_mm=real(seat_mm,'seat');real(female_start_mm);real(blind_end_mm)
    if blind_end_mm <= female_start_mm: raise ValueError('invalid blind bore')
    tip=seat_mm+screw.length_under_head_mm
    overlap=max(0.,min(tip,blind_end_mm)-max(seat_mm,female_start_mm))
    gap=blind_end_mm-tip
    return {'part_number':screw.part_number,'seat_mm':seat_mm,'tip_mm':tip,
            'head_back_mm':seat_mm-screw.head_height_mm,
            'nominal_axial_overlap_mm':overlap,'nominal_blind_gap_mm':gap,
            'nominal_axial_fit':overlap>0 and gap>0,
            'effective_threads_qualified':False,'tightening_torque_prescribed_Nm':None,
            'candidate_go':False}


def signed_error_bound(terms):
    """[(source_id, signed_sensitivity, symmetric_error_bound)] -> sum abs.

    Same source_id means the SAME random/unknown error, not merely two parts
    made from the same alloy. Differing bounds for one source are an error.
    """
    grouped={}
    for identity,coefficient,bound in terms:
        if not isinstance(identity,str) or not identity: raise ValueError('source id required')
        if type(coefficient) not in (int,float) or not math.isfinite(coefficient):
            raise ValueError('finite signed sensitivity required')
        bound=real(bound,identity)
        if identity in grouped:
            old,limit=grouped[identity]
            if limit != bound: raise ValueError('inconsistent bound for shared source')
            grouped[identity]=(old+coefficient,limit)
        else: grouped[identity]=(coefficient,bound)
    total=math.fsum(abs(c)*b for c,b in grouped.values())
    if not math.isfinite(total): raise ValueError('overflow in tolerance chain')
    return total


def clearance_screen(nominal_gap_mm, terms, reserve_mm=0.):
    gap=real(nominal_gap_mm,'nominal gap');reserve=real(reserve_mm,'reserve')
    total=signed_error_bound(terms);lower=gap-total-reserve
    if not math.isfinite(lower): raise ValueError('invalid clearance result')
    return {'nominal_gap_mm':gap,'relative_error_bound_mm':total,'additional_reserve_mm':reserve,
            'lower_bound_mm':lower,
            'status':'certified_for_this_bounded_chain' if lower>0 else 'not_certified_for_this_bounded_chain',
            'not_a_collision_proof':True,'actual_process_qualification':False,'candidate_go':False}


def thermal_chain(length_a_mm,cte_a_per_K,length_b_mm,cte_b_per_K,delta_K,
                  *,shared_temperature=True):
    for x in (length_a_mm,cte_a_per_K,length_b_mm,cte_b_per_K,delta_K): real(x)
    if type(shared_temperature) is not bool: raise ValueError('explicit correlation required')
    return signed_error_bound([('T',length_a_mm*cte_a_per_K,delta_K),
        ('T' if shared_temperature else 'T_B',-length_b_mm*cte_b_per_K,delta_K)])
