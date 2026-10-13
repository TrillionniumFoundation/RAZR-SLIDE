"""Nominal, conditional composite sections; never a finished laminate qualification."""
from dataclasses import dataclass
import json, math
from pathlib import Path

def positive(x, name):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<=0:
        raise ValueError(name+' must be finite and positive')
    return float(x)

@dataclass(frozen=True)
class Layer:
    name: str
    thickness_um: float
    modulus_GPa: float | None = None

def section(layers):
    if not layers:raise ValueError('empty section')
    z=0.;rows=[]
    for layer in layers:
        t=positive(layer.thickness_um,'thickness')
        e=None if layer.modulus_GPa is None else positive(layer.modulus_GPa,'modulus')
        rows.append(dict(name=layer.name,z0_um=z,z1_um=z+t,centroid_um=z+t/2,thickness_um=t,modulus_GPa=e));z+=t
    missing=any(r['modulus_GPa'] is None for r in rows)
    neutral=None if missing else sum(r['modulus_GPa']*r['thickness_um']*r['centroid_um'] for r in rows)/sum(r['modulus_GPa']*r['thickness_um'] for r in rows)
    copper=[r for r in rows if r['name']=='RA_COPPER']
    if len(copper)!=1:raise ValueError('this conditional section requires one copper layer')
    c=copper[0];lo=min(r['centroid_um'] for r in rows);hi=max(r['centroid_um'] for r in rows)
    furthest=None if neutral is None else max(abs(c['z0_um']-neutral),abs(c['z1_um']-neutral))
    # Positive constituent E weights imply NA is a convex combination of centroids.
    # This broad conditional bound contains extreme, unqualified modulus ratios.
    upper=max(abs(c['z0_um']-lo),abs(c['z1_um']-lo),abs(c['z0_um']-hi),abs(c['z1_um']-hi))
    return dict(layers=rows,nominal_unprocessed_thickness_um=z,neutral_axis_um=neutral,
      neutral_axis_missing_reason='layer_moduli_not_delivered' if missing else None,
      conditional_positive_modulus_centroid_interval_um=[lo,hi],
      conditional_max_copper_distance_upper_um=upper,copper_distance_um=furthest,
      finished_thickness_max_um=None,pressed_adhesive_thickness_um=None,
      project_material_batch_and_process_qualified=False,manufacturing_go=False)

def build_report():
    # Exact published product nominals. No guessed modulus or manufacturing tolerance.
    out=[]
    for code,adh,top in [('LF7001',13.,13.),('LF0110',25.,25.)]:
        for ac,base in [('AC181200RY',12.),('AC182500RY',25.)]:
            result=section([Layer('BASE_POLYIMIDE',base),Layer('RA_COPPER',18.),Layer('ACRYLIC_ADHESIVE',adh),Layer('COVER_POLYIMIDE',top)])
            result.update(base_part=ac,coverlay_part=code,nominal_radius_example_mm=16.5,
                conditional_max_copper_distance_index_upper=result['conditional_max_copper_distance_upper_um']/16500.,
                copper_at_neutral_axis_example_index=9/16500.,
                not_a_fatigue_or_actual_strain_result=True)
            out.append(result)
    return dict(schema='razr-slide-fpc-composite-nominal-r5',sections=out,
      nominal_thickness_is_not_finished_thickness=True,
      adhesive_flow_mm_is_not_through_thickness_collapse=True,
      LF0110_typical_Dk_and_peel_are_not_certified_LF7001_limits=True,
      source_table_mil_um_rounding_is_preserved=True,
      unknown=['pressed stackup and tolerance','each constituent modulus vs temperature','actual copper traces and density','grain direction and copper residual stress','actual neutral plane','lamination/coverlay process','continuous curvature and twist','dynamic fatigue and USB/power qualification'],
      system_capacity_goal_mAh=4700,manufacturing_go=False)

if __name__=='__main__':
    p=Path(__file__).resolve().parent/'conditional_sections.json';p.write_text(json.dumps(build_report(),indent=2)+'\n')
    print(json.dumps({'sections':4,'manufacturer_qualified_neutral_axes':0,'manufacturing_go':False}))
