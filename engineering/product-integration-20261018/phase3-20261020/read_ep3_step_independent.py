#!/usr/bin/env python3
"""Independently read EP3 STEP exports without calling the geometry generators.

The native report records all 41 candidate bodies in each complete assembly,
but not the external 113/120 bodies' individual metrics. This reader compares
all recorded candidates, and records the remaining readback metrics explicitly
as lacking a generator-report comparison. It never calls that full coverage.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback

POSES = ('STOW','PREDOCK','OPEN')
EXPECTED_TOTAL = {'STOW':154,'PREDOCK':154,'OPEN':161}
EXPECTED_EXTERNAL = {'STOW':113,'PREDOCK':113,'OPEN':120}
SCHEMA = 'razr-ep3-native-three-pose-v1'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_identity(path):
    path = Path(path)
    data = path.read_bytes()
    return {'path':str(path.resolve()),'bytes':len(data),
            'sha256':hashlib.sha256(data).hexdigest()}


def finite_number(value):
    return type(value) in (int,float) and math.isfinite(value)


def metrics_valid(value):
    b = value.get('bounds_mm')
    return (isinstance(b,list) and len(b)==6 and all(finite_number(v) for v in b)
            and all(b[2*i] < b[2*i+1] for i in range(3))
            and finite_number(value.get('volume_mm3')) and value['volume_mm3']>0)


def agreement(first, second, tolerance):
    if not metrics_valid(first) or not metrics_valid(second):
        return None
    bounds_error = max(abs(a-b) for a,b in zip(first['bounds_mm'],second['bounds_mm']))
    volume_error = abs(first['volume_mm3']-second['volume_mm3'])
    volume_limit = max(tolerance['absolute_volume_mm3'],
                       tolerance['relative_volume']*max(first['volume_mm3'],second['volume_mm3']))
    if bounds_error > tolerance['bounds_mm'] or volume_error > volume_limit:
        return None
    return {'max_bounds_error_mm':bounds_error,'absolute_volume_error_mm3':volume_error,
            'applied_volume_tolerance_mm3':volume_limit}


def match_recorded_metrics(expected, observed, tolerance):
    """Injective geometric multiset matching, including repeated screw shapes.

    STEP flattened-solid order is not an identity. A perfect matching must use
    separate observed solids for separate expected objects. Matching bounds and
    volume does not prove full material/topology equality or STEP label identity.
    """
    require(isinstance(expected,dict) and expected, 'missing expected object metrics')
    require(all(metrics_valid(v) for v in expected.values()), 'invalid generator object metrics')
    neighbors = {name:[i for i,metric in enumerate(observed)
                       if agreement(value,metric,tolerance) is not None]
                 for name,value in expected.items()}
    assigned = {}
    def augment(name, visited):
        for index in neighbors[name]:
            if index in visited:
                continue
            visited.add(index)
            if index not in assigned or augment(assigned[index],visited):
                assigned[index]=name
                return True
        return False
    unmatched=[]
    for name in sorted(expected,key=lambda k:(len(neighbors[k]),k)):
        if not augment(name,set()):
            unmatched.append(name)
    mappings=[{'native_report_part':name,'observed_flat_solid_index':index,
               **agreement(expected[name],observed[index],tolerance)}
              for index,name in sorted(assigned.items(),key=lambda row:row[1])]
    used=set(assigned)
    return {'expected_objects':len(expected),'observed_objects':len(observed),
            'recorded_objects_all_matched_injectively':not unmatched and len(assigned)==len(expected),
            'unmatched_expected_objects':unmatched,
            'matching':mappings,
            'unassigned_observed_indices':[i for i in range(len(observed)) if i not in used],
            'expected_objects_with_multiple_metric_matches':sorted(k for k,v in neighbors.items() if len(v)>1),
            'comparison':'anonymous finite-solid multiset using bounds and volume; no source-name/order assumption',
            'full_material_boolean_equivalence_proved':False,
            'STEP_assembly_label_identity_proved':False}


def native_metrics(solid, index):
    # Same exact underlying-geometry bounds convention as the generator, used
    # by this new process without importing product_assembly or any builder.
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    box=Bnd_Box()
    BRepBndLib.AddOptimal_s(solid.wrapped,box,False,False)
    xmin,ymin,zmin,xmax,ymax,zmax=box.Get()
    return {'flat_solid_index':index,'valid':bool(solid.isValid()),
            'positive_volume':solid.Volume()>0,
            'volume_mm3':solid.Volume(),
            'bounds_mm':[xmin,xmax,ymin,ymax,zmin,zmax]}


def compound_bounds(shape):
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    box=Bnd_Box(); BRepBndLib.AddOptimal_s(shape.wrapped,box,False,False)
    xmin,ymin,zmin,xmax,ymax,zmax=box.Get()
    return [xmin,xmax,ymin,ymax,zmin,zmax]


def endpoint_location(route, end):
    """Build a proper rigid frame from retained numeric metadata, not a builder."""
    import cadquery as cq
    from OCP.gp import gp_Trsf
    index=0 if end=='A' else 1
    w=route['end_width_axes'][index]; t=route['end_tangents'][index]
    origin=route[end+'_endpoint_world_mm']
    require(all(len(v)==3 and all(finite_number(x) for x in v) for v in (w,t,origin)),
            'invalid recorded endpoint axes/origin')
    dot=lambda u,v:sum(a*b for a,b in zip(u,v))
    n=[w[1]*t[2]-w[2]*t[1],w[2]*t[0]-w[0]*t[2],w[0]*t[1]-w[1]*t[0]]
    require(max(abs(dot(w,w)-1),abs(dot(t,t)-1),abs(dot(n,n)-1),abs(dot(w,t)),
                abs(dot(w,n)),abs(dot(t,n)))<1e-10, 'recorded frame is not orthonormal')
    transform=gp_Trsf()
    transform.SetValues(w[0],t[0],n[0],origin[0],
                        w[1],t[1],n[1],origin[1],
                        w[2],t[2],n[2],origin[2])
    return cq.Location(transform)


def versions():
    value={'python':sys.version,'python_executable':sys.executable}
    for name in ('cadquery','cadquery-ocp','numpy'):
        try: value[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: value[name]=None
    return value


def git_head(root):
    p=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],capture_output=True,text=True,timeout=15)
    return p.stdout.strip() if p.returncode==0 else None


def source_identity(manifest, root):
    rows={}
    for name,digest in manifest['input_sha256'].items():
        require(re.fullmatch(r'[a-f0-9]{64}',digest) is not None,'invalid retained source digest')
        rel=Path(name); require(not rel.is_absolute(),'source path must be repository-relative')
        path=(root/rel).resolve()
        require(root in path.parents and path.is_file(),'missing or escaped generator source: '+name)
        actual=file_identity(path)
        rows[name]={**actual,'native_report_sha256':digest,'matches_native_report':actual['sha256']==digest}
    return rows


def step_path(folder, relative):
    require(isinstance(relative,str) and Path(relative).name==relative and relative.endswith('.step'),
            'STEP reference must be a local basename')
    path=(folder/relative).resolve()
    require(path.parent==folder and path.is_file(),'missing or escaped STEP export')
    return path


def read_file(path, expected_count):
    import cadquery as cq
    start=time.monotonic()
    shape=cq.importers.importStep(str(path)).val()
    solids=list(shape.Solids())
    metrics=[native_metrics(solid,i) for i,solid in enumerate(solids)]
    return shape,solids,{'file_identity':file_identity(path),'read_seconds':time.monotonic()-start,
        'expected_flat_solids':expected_count,'observed_flat_solids':len(solids),
        'flat_solid_count_matches':len(solids)==expected_count,
        'all_flat_solids_valid_positive':all(v['valid'] and v['positive_volume'] and metrics_valid(v) for v in metrics),
        'bounds_mm':compound_bounds(shape),'sum_of_flat_solid_volumes_mm3':sum(v['volume_mm3'] for v in metrics),
        'flat_solids':metrics,
        'sum_is_not_boolean_union_volume':True}


def execute(manifest_path, root, output, tolerance):
    manifest_path=Path(manifest_path).resolve(); root=Path(root).resolve(); output=Path(output).resolve()
    require(not output.exists() and output!=root and root not in output.parents,
            'use a new output directory outside the repository')
    output.mkdir(parents=True)
    start=dt.datetime.now(dt.timezone.utc); clock=time.monotonic()
    report={'schema':'razr-ep3-independent-step-readback-v1',
        'started_utc':start.isoformat(),'command_line':sys.argv,
        'independent_process_from_generator':True,
        'geometry_generator_modules_imported':False,
        'reader_source':file_identity(__file__),'runtime':versions(),
        'reader_process':{'pid':os.getpid(),'parent_pid':os.getppid(),
            'entrypoint':str(Path(__file__).resolve()),
            'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()
                if Path('/proc/sys/kernel/random/boot_id').is_file() else None},
        'tolerance':tolerance,'files':{},'execution_completed':False,
        'declared_readback_checks_passed':False,
        'full_assembly_native_report_geometry_coverage_complete':False,
        'source_assembly_full_material_equivalence_proved':False,
        'interference_or_internal_motion_passed':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    tracked={Path(__file__).resolve():file_identity(__file__)}
    try:
        tracked[manifest_path]=file_identity(manifest_path)
        manifest=json.loads(manifest_path.read_text())
        require(manifest.get('schema')==SCHEMA,'wrong generator report schema')
        require(manifest.get('native_checks_executed') is True and manifest.get('source_bytes_unchanged') is True,
                'generator did not complete its source-bound native checks')
        require(re.fullmatch(r'[a-f0-9]{40}',manifest.get('source_commit','')) is not None,
                'native source commit missing')
        report['native_report']=tracked[manifest_path]
        report['native_source_commit']=manifest['source_commit']
        report['reader_observed_repository_head']=git_head(root)
        report['generator_source_inputs']=source_identity(manifest,root)
        require(all(v['matches_native_report'] for v in report['generator_source_inputs'].values()),
                'current source bytes differ from native report; do not silently relabel evidence')
        tracked.update({Path(v['path']):{'path':v['path'],'bytes':v['bytes'],'sha256':v['sha256']}
                        for v in report['generator_source_inputs'].values()})
        poses={row['pose']:row for row in manifest['poses']}
        require(set(poses)==set(POSES) and len(manifest['poses'])==3,'three unique native poses required')
        for label,row in poses.items():
            require(row['combined_participants']==EXPECTED_TOTAL[label]
                    and row['external_participants']==EXPECTED_EXTERNAL[label]
                    and row['candidate_participants']==41 and len(row['parts'])==41,
                    'generator pose participant contract differs')
            require(all(metrics_valid(value) for value in row['parts'].values()),'missing candidate metrics')
        require(set(manifest['endpoint_exports'])=={'A','B'},'both endpoint exports required')
        folder=manifest_path.parent
        for end in ('A','B'):
            meta=manifest['endpoint_exports'][end]; path=step_path(folder,meta['file'])
            require(meta['parts']==20,'complete endpoint expected to have 20 bodies')
            tracked[path]=file_identity(path)
            require(tracked[path]['sha256']==meta['sha256'],'endpoint export hash differs')
            shape,solids,row=read_file(path,20)
            expected_bounds=meta['bounds_mm']
            require(isinstance(expected_bounds,list) and len(expected_bounds)==6,'missing endpoint bounds')
            error=max(abs(a-b) for a,b in zip(row['bounds_mm'],expected_bounds))
            row['local_compound_bounds_comparison']={'native_report_bounds_mm':expected_bounds,
                'max_error_mm':error,'within_tolerance':error<=tolerance['bounds_mm']}
            row['placed_metric_comparisons']={}
            for label in POSES:
                native_pose=poses[label]
                expected={name:value for name,value in native_pose['parts'].items() if name.startswith(end+'_')}
                require(len(expected)==20,'native report must retain all 20 placed endpoint objects')
                location=endpoint_location(native_pose['route'],end)
                observed=[native_metrics(solid.moved(location),i) for i,solid in enumerate(solids)]
                row['placed_metric_comparisons'][label]=match_recorded_metrics(expected,observed,tolerance)
            row['all_declared_file_checks_passed']=(row['flat_solid_count_matches']
                and row['all_flat_solids_valid_positive'] and row['local_compound_bounds_comparison']['within_tolerance']
                and all(v['recorded_objects_all_matched_injectively'] for v in row['placed_metric_comparisons'].values()))
            row['metric_scope']='all 20 local endpoint solids: bounds directly; per-solid volume and placement via each native pose retained rigid frame'
            report['files']['endpoint_'+end]=row
            (output/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps({'file':path.name,'observed_solids':len(solids),
                'declared_checks_passed':row['all_declared_file_checks_passed']}),flush=True)
        for label in POSES:
            native_pose=poses[label]; meta=native_pose['combined_STEP']; path=step_path(folder,meta['file'])
            require(meta['expected_solids']==EXPECTED_TOTAL[label],'complete assembly count differs')
            tracked[path]=file_identity(path)
            require(tracked[path]['sha256']==meta['sha256'],'assembly export hash differs')
            shape,solids,row=read_file(path,EXPECTED_TOTAL[label])
            matching=match_recorded_metrics(native_pose['parts'],row['flat_solids'],tolerance)
            row['candidate_metric_comparison']=matching
            row['expected_metric_coverage']={'recorded_candidate_objects':41,
                'external_objects_without_per_object_generator_metrics':EXPECTED_EXTERNAL[label],
                'all_assembly_objects_have_generator_metrics':False,
                'unassigned_solids_are_not_asserted_named_or_individually_identical_external_parts':True}
            row['aggregate_volume_comparison']={'native_report_whole_assembly_volume_mm3':None,
                'whole_assembly_volume_compared':False,
                'recorded_candidate_volume_mm3':sum(v['volume_mm3'] for v in native_pose['parts'].values()),
                'matched_readback_candidate_volume_mm3':sum(row['flat_solids'][v['observed_flat_solid_index']]['volume_mm3'] for v in matching['matching']),
                'reason':'native report records per-object metrics only for the 41 candidate bodies; no whole-assembly numeric baseline exists'}
            row['all_declared_file_checks_passed']=(row['flat_solid_count_matches']
                and row['all_flat_solids_valid_positive'] and matching['recorded_objects_all_matched_injectively'])
            report['files']['assembly_'+label]=row
            (output/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps({'file':path.name,'observed_solids':len(solids),
                'recorded_candidates_matched':len(matching['matching']),
                'external_objects_without_generator_metric_baseline':EXPECTED_EXTERNAL[label],
                'declared_checks_passed':row['all_declared_file_checks_passed']}),flush=True)
        after={str(path):file_identity(path) for path in tracked}
        report['retained_input_files']={str(path):value for path,value in tracked.items()}
        report['input_files_unchanged_during_reader']=all(value['sha256']==after[str(path)]['sha256']
            and value['bytes']==after[str(path)]['bytes'] for path,value in tracked.items())
        report['execution_completed']=True
        report['declared_readback_checks_passed']=(len(report['files'])==5
            and all(v['all_declared_file_checks_passed'] for v in report['files'].values())
            and report['input_files_unchanged_during_reader'])
        report['readback_outcome']=('declared_comparisons_passed_with_explicit_unrecorded_external_geometry'
            if report['declared_readback_checks_passed'] else 'declared_readback_check_failed')
    except Exception as exc:
        report['failure']={'error_type':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc()}
        report['readback_outcome']='execution_failed_or_incomplete'
    finally:
        report['finished_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
        report['elapsed_seconds']=time.monotonic()-clock
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--repo-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    tolerance={'bounds_mm':1e-6,'absolute_volume_mm3':1e-6,'relative_volume':1e-9,
               'scope':'STEP numeric roundtrip comparison; not physical manufacturing tolerances'}
    result=execute(args.manifest,args.repo_root,args.output,tolerance)
    print(json.dumps({'execution_completed':result['execution_completed'],
        'declared_readback_checks_passed':result['declared_readback_checks_passed'],
        'full_assembly_native_report_geometry_coverage_complete':False,
        'interference_or_internal_motion_passed':False,'report':str(args.output/'report.json')}))
    raise SystemExit(0 if result['execution_completed'] and result['declared_readback_checks_passed'] else 2)


if __name__=='__main__': main()
