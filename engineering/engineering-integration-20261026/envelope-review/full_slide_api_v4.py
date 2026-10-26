"""Prospective full-SLIDE API; no S4 defaults or published L2/L3 bytes change.

No native module is imported here.  A supervised caller supplies the frozen
S4 contract, predicates, V2/V3 modules, actual factory bodies and evidence
callbacks.  This module has not yet been executed on native K1 material.
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
import itertools
import math
import time

TOL=1e-7
BOUND_PAD_MM=1e-5
MAX_REGIONS=4096
SCHEMA='razr-slide-specification-v4'


class CapacityStop(RuntimeError):
    """Owned caller must retain the full inventory and unfinished pair prefix."""


def require(ok,message):
    if not ok:raise ValueError(message)


def check_budget(callback):
    try:return callback()
    except Exception as exc:raise CapacityStop(type(exc).__name__+': '+str(exc)) from exc


def finite(value):
    return type(value) in (float,int) and math.isfinite(value)


def original_sum(values):
    values=list(values)
    require(values and all(finite(v) and v>=0 for v in values),'nonempty finite nonnegative original Common values required')
    total=math.fsum(values);require(math.isfinite(total),'nonfinite original Common sum')
    return total


def correlated_family(a,b):
    for side in 'LR':
        for index in (0,1):
            pair={a,b}
            if pair=={side+'_KEY',f'{side}_STOP_{index}'}:return 'KEY_STOP'
            if pair=={f'{side}_SPRING_{index}_OD_TOL_ENVELOPE',f'{side}_STOP_{index}'}:return 'SPRING_STOP'
    return None


def participant_pairs(names):
    names=list(names)
    require(names==sorted(set(names)) and len(names)==154,'exact complete ordered 154-material inventory required')
    pairs=list(itertools.combinations(names,2));require(len(pairs)==11781,'complete unordered pair count changed')
    return pairs


def initialize_inventory(names):
    return [{'a':a,'b':b,'disposition':'not_evaluated'} for a,b in participant_pairs(names)]


def inventory_status(rows,names):
    expected=participant_pairs(names)
    require([(r['a'],r['b']) for r in rows]==expected,'missing, duplicated, reordered or foreign full-pair slot')
    allowed={'not_evaluated','clear','unresolved_enclosure_overlap','unresolved_evaluation','unresolved_budget'}
    require(all(r['disposition'] in allowed for r in rows),'unknown pair result')
    counts=dict(Counter(r['disposition'] for r in rows))
    return {'expected_physical_pairs':11781,'all_original_pair_slots_present':True,'counts':counts,
            'all_pairs_evaluated':not any(counts.get(k,0) for k in ('not_evaluated','unresolved_budget')),
            'all_pairs_numerically_clear':all(r['disposition']=='clear' for r in rows),
            'complete_G2_qualification':False,'physical_qualification':False,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}


def require_closed_partition(low,high,intervals):
    low,high=Fraction(low),Fraction(high)
    parts=[(Fraction(a),Fraction(b)) for a,b in intervals]
    require(parts and 0<=low<high<=12 and parts[0][0]==low and parts[-1][1]==high,
            'closed partition must cover the complete original finite interval')
    require(all(a<b for a,b in parts) and all(x[1]==y[0] for x,y in zip(parts,parts[1:])),
            'empty, overlapping, gapped or collapsed exact q subinterval')
    return [[str(a),str(b)] for a,b in parts]


def outward_translation_bounds(coefficients,domain):
    """Directed binary64 operations for the affine coefficient box only.

    This does not certify OCCT native geometry bounds or transform error.
    """
    require(len(coefficients)==len(domain) and coefficients,'complete nonempty affine box required')
    require(all(len(c)==3 and all(finite(x) for x in c) for c in coefficients),'finite XYZ coefficients required')
    require(all(len(v)==2 and all(finite(x) for x in v) and v[0]<=v[1] for v in domain),'finite ordered intervals required')
    result=[]
    for axis in range(3):
        lower=upper=0.
        for c,(lo,hi) in zip(coefficients,domain):
            products=[c[axis]*lo,c[axis]*hi]
            require(all(math.isfinite(v) for v in products),'nonfinite affine product')
            lower=math.nextafter(lower+math.nextafter(min(products),-math.inf),-math.inf)
            upper=math.nextafter(upper+math.nextafter(max(products),math.inf),math.inf)
        result.extend((lower,upper))
    return result


def fresh_padded_axis_gap(a,b,coefficients,domain,v2):
    aa=v2.geometric_bounds(a);bb=v2.geometric_bounds(b)
    shift=outward_translation_bounds(coefficients,domain)
    lo=[];hi=[];blo=[];bhi=[]
    for axis in range(3):
        lo.append(math.nextafter(aa[2*axis]+shift[2*axis]-BOUND_PAD_MM,-math.inf))
        hi.append(math.nextafter(aa[2*axis+1]+shift[2*axis+1]+BOUND_PAD_MM,math.inf))
        blo.append(math.nextafter(bb[2*axis]-BOUND_PAD_MM,-math.inf))
        bhi.append(math.nextafter(bb[2*axis+1]+BOUND_PAD_MM,math.inf))
    gaps=[max(math.nextafter(lo[i]-bhi[i],-math.inf),math.nextafter(blo[i]-hi[i],-math.inf)) for i in range(3)]
    require(all(math.isfinite(v) for v in [*lo,*hi,*blo,*bhi,*gaps]),'nonfinite padded native bound')
    return max(gaps),{'complete_native_a_bounds_mm':aa,'complete_native_b_bounds_mm':bb,
        'outward_affine_shift_bounds_mm':shift,'moving_carrier_low_mm':lo,'moving_carrier_high_mm':hi,
        'fixed_carrier_low_mm':blo,'fixed_carrier_high_mm':bhi,'padding_each_body_mm':BOUND_PAD_MM,
        'axis_gap_lower_mm':gaps,'native_geometric_bounds_are_not_interval_certified':True,
        'fresh_candidate_material_bounds_used':True,'historical_clear_result_reused':False}


def _frame(a,b,coefficients,domain,*,name,p,v2,guard,budget_check,retain):
    check_budget(budget_check);started=time.monotonic();audit=[];checks=[];region=None;index=None
    timing={'region_construction_seconds':None,'region_checks_seconds':0.}
    try:
        p.whole_material(a);p.whole_material(b)
        gap,bound_record=fresh_padded_axis_gap(a,b,coefficients,domain,v2)
        if gap>0:
            result={'disposition':'clear','method':'continuous_relative_axis_gap','gap_lower_mm':gap,
                    'v4_fresh_padded_bounds':bound_record,'v4_timing':timing}
            guard.validate_frame(result);return result
        t=time.monotonic();pieces=v2.enclosure_regions(a,coefficients,domain,audit=audit)
        timing['region_construction_seconds']=time.monotonic()-t
        require(len(pieces)<=MAX_REGIONS,'original 4096-region cap exceeded')
        values=[]
        for index,region in enumerate(pieces):
            check_budget(budget_check);t=time.monotonic();common=p.strict_common(region,b)
            seconds=time.monotonic()-t;timing['region_checks_seconds']+=seconds
            values.append(common['common_mm3']);checks.append({'region_index':index,**common,'native_Common_seconds':seconds})
            upper=original_sum(values)
            if upper>TOL:
                retained=retain(region,b,{'frame':name,'region_index':index,'strict_common':common,
                    'recomputed_after_failure':False})
                result={'disposition':'unresolved_enclosure_overlap',
                    'method':'continuous_relative_affine_box_translation_enclosure',
                    'positive_enclosure_common_mm3':max(values),'examined_region_common_sum_mm3':upper,
                    'regions_examined':len(values),'total_region_count':len(pieces),'collision_proved':False,
                    'v2_carrier_audit':audit,'v4_region_checks':checks,'v4_retained_materials':retained,
                    'v4_timing':timing}
                guard.validate_frame(result);return result
        result={'disposition':'clear','method':'continuous_relative_affine_box_translation_enclosure',
            'region_count':len(pieces),'maximum_region_common_mm3':max(values),'common_upper_bound_mm3':upper,
            'common_upper_bound_is_sum_not_union_volume':True,'v2_carrier_audit':audit,
            'v4_region_checks':checks,'v4_timing':timing}
        guard.validate_frame(result);return result
    except (CapacityStop,InterruptedError):raise
    except Exception as exc:
        retained=None
        if region is not None:
            try:retained=retain(region,b,{'frame':name,'region_index':index,
                'error':type(exc).__name__+': '+str(exc),'recomputed_after_failure':True})
            except (CapacityStop,InterruptedError):raise
            except Exception as export_exc:retained={'retention_failed':type(export_exc).__name__+': '+str(export_exc)}
        return {'disposition':'unresolved_evaluation','error':type(exc).__name__+': '+str(exc),
                'collision_proved':False,'v2_carrier_audit':audit,'v4_region_checks':checks,
                'v4_retained_materials':retained,'v4_timing':timing}
    finally:
        timing['frame_elapsed_seconds']=time.monotonic()-started


def evaluate_specification(moving,fixed,spec,target,*,contract,source_root,p,v2,v3,
                           original_postguard,budget_check,emit,retain_v2,reference_frame='A'):
    """Return a tagged V4 record; never pass a V3 dynamic result as old raw.

    `emit` saves positive whole BREP operands before V3 checks. `retain_v2`
    saves a rejected carrier and, where possible, a distinctly named followup
    Common. The owning worker binds every output and the external sources.
    """
    started=time.monotonic();a,b=target['a'],target['b']
    require(a<b and a in contract.names and b in contract.names,'canonical complete material pair required')
    low,high=map(Fraction,target['q_interval_exact'])
    require(0<=low<=high<=12,'original finite q domain cannot be extended or clamped')
    require(spec in contract.specifications(a,b,low,high,reference_frame),'specification is not rebuilt from the frozen complete source law')
    check_budget(budget_check)
    result={'schema':SCHEMA,'pair':[a,b],'q_interval_exact':[str(low),str(high)],
            'source_specification':spec,'reference_frame':reference_frame,
            'original_volume_gate_mm3':TOL,'physical_qualification':False,
            'formal_directed_rounding_certificate':False,'factory_material_binding_supplied_by_owning_worker':True}
    if correlated_family(a,b) is not None:
        result['method_family']='v3_correlated_nominal_contact';audit={};result['method_audit']=audit
        def guarded_emit(label,body):
            check_budget(budget_check);exported=emit(label,body);check_budget(budget_check);return exported
        try:
            native=v3.evaluate(moving,fixed,spec,target,guarded_emit,source_root,audit)
            result.update(correlated_result=native,disposition=native['disposition'])
            require(native['common_upper_bound_is_sum_not_union_volume'] is True,'complete correlated body Common sum absent')
            result['common_upper_bound_mm3']=native['common_upper_bound_mm3']
            result['original_guard_scope']='static carrier/obstacle records only; correlated continuous construction has its own method identity'
        except (CapacityStop,InterruptedError):raise
        except Exception as exc:
            result.update(disposition='unresolved_evaluation',error=type(exc).__name__+': '+str(exc))
    else:
        result['method_family']='fresh_padded_gap_then_frozen_V2_affine_carriers'
        kw={'p':p,'v2':v2,'guard':original_postguard,'budget_check':budget_check,'retain':retain_v2}
        first=_frame(moving,fixed,spec['coefficients'],spec['parameter_intervals'],name='initial',**kw)
        raw=first
        if first['disposition']!='clear':
            reverse=_frame(fixed,moving,[[-x for x in v] for v in spec['coefficients']],spec['parameter_intervals'],name='opposite',**kw)
            raw=({**reverse,'relative_reference_frame_reversed':True,'initial_reference_frame_result':first}
                 if reverse['disposition']=='clear' else {**first,'opposite_reference_frame_result':reverse})
        result['affine_raw']=raw;result['disposition']=raw['disposition']
        try:original_postguard.validate_frame(raw)
        except Exception as exc:result.update(disposition='unresolved_evaluation',original_postguard_error=type(exc).__name__+': '+str(exc))
        if result['disposition']=='clear':result['common_upper_bound_mm3']=0. if raw['method']=='continuous_relative_axis_gap' else raw['common_upper_bound_mm3']
    check_budget(budget_check);result['specification_elapsed_seconds']=time.monotonic()-started
    return result


def aggregate_complete_pair(specifications,results):
    """One original 1e-7 budget across every complete-body/cage specification."""
    require(len(specifications)==len(results)>0,'all source specifications must be present')
    require(all(r['schema']==SCHEMA and r['source_specification']==s for s,r in zip(specifications,results)),
            'results omit/reorder/substitute a source specification')
    dispositions=[r['disposition'] for r in results]
    if any(d=='unresolved_evaluation' for d in dispositions):return {'disposition':'unresolved_evaluation','all_specifications_present':True}
    if any(d!='clear' for d in dispositions):return {'disposition':'unresolved_enclosure_overlap','all_specifications_present':True,'collision_proved':False}
    upper=original_sum(r['common_upper_bound_mm3'] for r in results)
    return {'disposition':'clear' if upper<=TOL else 'unresolved_enclosure_overlap',
            'all_specifications_present':True,'complete_body_common_upper_bound_mm3':upper,
            'common_upper_bound_is_sum_not_union_volume':True,'collision_proved':False}
