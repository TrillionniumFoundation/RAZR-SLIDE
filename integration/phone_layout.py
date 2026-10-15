"""Project-owned equal-envelope cabin study, not measured OEM space or a phone release.

The rectangular baseline is retained as a negative control. Complementary end
steps reserve the overlap implied by the historical planform and current
motion. Only empty, closed-wall study shells are modeled: no electronics,
OLED, guide, seal, access lid, toleranced fit, strength or battery capacity.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import itertools
import json
import math
from pathlib import Path

import cadquery as cq
from straight_envelope import TOL, single, whole_material

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Dimensions:
    width_mm: float
    height_mm: float
    thickness_mm: float
    slide_mm: float
    normal_seating_mm: float
    study_clearance_mm: float
    study_wall_mm: float

    def __post_init__(self):
        for value in asdict(self).values():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError('dimensions must be finite positive numbers')
        if self.height_mm <= self.slide_mm:
            raise ValueError('this complementary-overlap study needs height > slide')
        if self.normal_seating_mm - self.thickness_mm < self.study_clearance_mm - TOL:
            raise ValueError('study shells collide or lack declared stowed clearance')
        if min(self.width_mm, self.full_depth_length, self.thickness_mm) <= 2 * self.study_wall_mm:
            raise ValueError('no positive full-depth study cavity')
        if self.lap_depth <= self.study_wall_mm:
            raise ValueError('lap depth is thinner than the assumed wall')

    @property
    def overlap(self):
        return self.height_mm - self.slide_mm

    @property
    def lap_length(self):
        return self.overlap + self.study_clearance_mm

    @property
    def full_depth_length(self):
        return self.height_mm - self.lap_length

    @property
    def lap_depth(self):
        return (self.thickness_mm - self.study_clearance_mm) / 2

    @property
    def cavity_size(self):
        w = self.study_wall_mm
        return (self.width_mm - 2*w, self.full_depth_length - 2*w, self.thickness_mm - 2*w)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def block(lo, hi):
    if any(not math.isfinite(v) for v in (*lo, *hi)) or any(b <= a for a, b in zip(lo, hi)):
        raise ValueError('invalid solid bounds')
    return single(cq.Solid.makeBox(*(b-a for a,b in zip(lo,hi)), cq.Vector(*lo)))


def volume(shape, *, empty=False):
    return whole_material(shape, empty=empty)[1]


def common(a, b):
    value = volume(a.intersect(b), empty=True)
    if value > min(volume(a), volume(b)) + TOL:
        raise ValueError('invalid common volume')
    return value


def outside(a, b):
    value = volume(a.cut(b), empty=True)
    if value > volume(a) + TOL:
        raise ValueError('invalid difference volume')
    return value


def bounds(shape):
    b = shape.BoundingBox()
    return [b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]


def build_cabin(d: Dimensions, cabin: str, *, stepped: bool):
    if cabin not in ('A','B') or type(stepped) is not bool:
        raise ValueError('unknown cabin or study variant')
    w,h,t,c = d.width_mm,d.height_mm,d.thickness_mm,d.study_wall_mm
    rectangular = block((-w/2,0,0),(w/2,h,t))
    if not stepped:
        outer = rectangular
        cavity = block((-w/2+c,c,c),(w/2-c,h-c,t-c))
    elif cabin == 'A':
        outer = single(block((-w/2,0,0),(w/2,d.full_depth_length,t)).fuse(
            block((-w/2,d.full_depth_length,0),(w/2,h,d.lap_depth))).clean())
        cavity = block((-w/2+c,c,c),(w/2-c,d.full_depth_length-c,t-c))
    else:
        outer = single(block((-w/2,d.lap_length,0),(w/2,h,t)).fuse(
            block((-w/2,0,d.lap_depth+d.study_clearance_mm),(w/2,d.lap_length,t))).clean())
        cavity = block((-w/2+c,d.lap_length+c,c),(w/2-c,h-c,t-c))
    if outside(cavity, outer) > TOL:
        raise ValueError('cavity is not contained in its project-owned outer shape')
    shell = single(outer.cut(cavity).clean())
    return {'outer':outer,'cavity':cavity,'shell':shell}


def operating_enclosures(d: Dimensions):
    """Full straight-motion supersets, derived from two rectangular B outer blocks.

    Translation of a box along a box axis is its exact lengthened box. Taking
    both B outer blocks includes all shell material, without filling a sampling
    gap. The two motion phases are sequential, not concurrent.
    """
    w,h,t,z = d.width_mm,d.height_mm,d.thickness_mm,d.normal_seating_mm
    slide = block((-w/2,0,z),(w/2,h+d.slide_mm,z+t))
    seat_lap = block((-w/2,d.slide_mm,d.lap_depth+d.study_clearance_mm),
                     (w/2,d.slide_mm+d.lap_length,t+z))
    seat_body = block((-w/2,d.slide_mm+d.lap_length,0),
                      (w/2,d.slide_mm+h,t+z))
    return {'slide_outer_superset':slide,'seat_lap_superset':seat_lap,'seat_body_superset':seat_body}


def proper_axis_rotations():
    """24 proper signed axis permutations, not a search over all rotations."""
    result=[]
    for p in itertools.permutations(range(3)):
        inversions=sum(p[i]>p[j] for i in range(3) for j in range(i+1,3))
        parity=(-1)**inversions
        for signs in itertools.product((-1,1),repeat=3):
            if parity*math.prod(signs)!=1:
                continue
            matrix=[[signs[row] if col==p[row] else 0 for col in range(3)] for row in range(3)]
            result.append(matrix)
    return result


def reservation_trials(cavity_size, moving_size):
    for values in (cavity_size,moving_size):
        if len(values)!=3 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<=0 for x in values):
            raise ValueError('invalid reservation dimensions')
    trials=[]
    for matrix in proper_axis_rotations():
        extent=[sum(abs(a)*b for a,b in zip(row,moving_size)) for row in matrix]
        margin=[a-b for a,b in zip(cavity_size,extent)]
        trials.append({'rotation':matrix,'rotated_reservation_mm':extent,'total_axis_margin_mm':margin,
                       'reservation_contained':all(x>=0 for x in margin)})
    return {'scope':'24 proper axis rotations of the entire conservative rectangular reservation; no selected mounting transform',
            'trials':trials,'accepted_count':sum(x['reservation_contained'] for x in trials),
            'not_a_proof_against_arbitrary_tilt_or_actual_nonrectangular_material':True,
            'not_a_positive_finished_phone_fit_test':True}


def generate(config_path: Path, output: Path):
    config_path=config_path.resolve();output=output.resolve()
    protected=[(ROOT/n).resolve() for n in ('archive','baselines','docs','engineering','integration','tests','tools','.git','.venv')]
    if output==ROOT or any(output==p or p in output.parents for p in protected):
        raise ValueError('use a new output directory outside source and frozen evidence')
    data=json.loads(config_path.read_text());d=Dimensions(**data['dimensions'])
    if data.get('input_kind')!='project_owned_parametric_study_not_measured':
        raise ValueError('unrecognized study provenance')
    source=ROOT/data['component_reservation_source']
    reservations=json.loads(source.read_text())
    output.mkdir(parents=True,exist_ok=False)
    models={kind:{side:build_cabin(d,side,stepped=(kind=='stepped')) for side in ('A','B')}
            for kind in ('rectangular_negative','stepped')}
    exports={}
    def export(name,body):
        path=output/(name+'.step');cq.exporters.export(body,str(path))
        exports[name]={'path':path.name,'sha256':digest(path),'volume_mm3':volume(body),'bounds_xyz_mm':bounds(body)}
    for kind,sides in models.items():
        for side,parts in sides.items():
            for name,body in parts.items():export(kind+'_'+side+'_'+name,body)
    moves={'STOW':(0,0,d.normal_seating_mm),'PREDOCK':(0,d.slide_mm,d.normal_seating_mm),'OPEN_SEATED':(0,d.slide_mm,0)}
    poses=[]
    for kind,sides in models.items():
        for pose,shift in moves.items():
            b=sides['B']['shell'].translate(shift)
            poses.append({'variant':kind,'pose':pose,'B_translation_mm':shift,'shell_common_mm3':common(sides['A']['shell'],b)})
            export(kind+'_'+pose+'_B_shell',b)
    cages=operating_enclosures(d)
    for name,body in cages.items():export(name,body)
    a=models['stepped']['A']['outer']
    proof={name:common(a,body) for name,body in cages.items()}
    sides=models['stepped']
    endpoint_containment={}
    seat=single(cages['seat_lap_superset'].fuse(cages['seat_body_superset']).clean())
    for name,shift in moves.items():
        cage=cages['slide_outer_superset'] if name=='STOW' else seat
        endpoint_containment[name]=outside(sides['B']['outer'].translate(shift),cage)
    trials={r['side']:reservation_trials(d.cavity_size,r['size_eqr_mm']) for r in reservations['full_operational_space_reservations']}
    negative=next(x['shell_common_mm3'] for x in poses if x['variant']=='rectangular_negative' and x['pose']=='OPEN_SEATED')
    if negative<=TOL or any(x['shell_common_mm3']>TOL for x in poses if x['variant']=='stepped') or any(v>TOL for v in (*proof.values(),*endpoint_containment.values())):
        raise ValueError('native geometry disagrees with declared overlap construction')
    old_cavity=volume(models['rectangular_negative']['A']['cavity'])
    report={'study':'equal-envelope complementary overlap empty-shell study','dimensions':asdict(d),
            'input_kind':data['input_kind'],'source_sha256':digest(Path(__file__)),
            'configuration_sha256':digest(config_path),'component_reservation_sha256':digest(source),
            'historical_planform_reference':data['historical_planform_reference'],
            'poses':poses,'exports':exports,'longitudinal_overlap_mm':d.overlap,'lap_length_with_study_clearance_mm':d.lap_length,
            'equal_finished_outer_bounds_in_each_local_frame':bounds(sides['A']['outer'])==bounds(sides['B']['outer']),
            'continuous_outer_enclosure_common_mm3':proof,'native_endpoint_containment_outside_mm3':endpoint_containment,
            'two_sequential_axis_translations_not_sample_union':True,
            'study_cavity_size_mm':d.cavity_size,'study_cavity_volume_mm3_per_cabin':volume(sides['A']['cavity']),
            'full_depth_cavity_volume_cost_mm3_per_cabin':old_cavity-volume(sides['A']['cavity']),
            'component_reservation_trials':trials,
            'selected_component_to_cabin_transform':None,'actual_components_installed':False,
            'finished_phone_fit':'unknown',
            'limited_reservation_result':'rejected' if all(x['accepted_count']==0 for x in trials.values()) else 'some conservative rotations fit; mounting still unknown',
            'not_modeled':['selected OLED and planar storage','populated boards and connectors','battery cells and swelling','guides and bridge','lid installation and seals','loads, deflection and process tolerances'],
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config',type=Path,default=ROOT/'integration/phone_layout_study.json')
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();r=generate(args.config,args.output)
    print(json.dumps({k:r[k] for k in ('longitudinal_overlap_mm','study_cavity_size_mm','study_cavity_volume_mm3_per_cabin','finished_phone_fit','manufacturing_go')}))
