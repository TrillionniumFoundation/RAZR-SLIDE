"""Owned K4 worker: exact locked S4 plus bounded imported-whole local sections.

This entry point must be started by supervise_k4 through the original owned
ready/release channel. It performs no work without that verified handshake.
Raw process/source/environment observations stay outside the scientific report.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
from f1_common import Budget, identity, owned_process, S4
from k4_local_section_native_api import run_producer,run_reader,FALSE_FLAGS


def require(ok,message):
    if not ok:raise ValueError(message)


def directory_bytes(path):
    return sum(p.stat().st_size for p in Path(path).rglob('*') if p.is_file())


def verify_bundle(path,expected):
    require(identity.sha(path)==expected,'frozen external source manifest differs')
    record=json.loads(Path(path).read_text())
    require(record['schema']=='razr-K4-frozen-hosted-source-bundle-v1' and record['functional_source_commit']==S4,'wrong frozen source bundle')
    for name,ref in record['runtime_sources'].items():
        p=HERE/name
        require(Path(name).name==name and p.is_file() and not p.is_symlink(),'frozen runtime source missing or linked')
        require(p.stat().st_size==ref['bytes'] and identity.sha(p)==ref['sha256'],'frozen runtime source bytes differ')
    for name,expected_sha in record['immutable_S4_helpers'].items():
        require(identity.sha(identity.ROOT/name)==expected_sha,'immutable S4 helper bytes differ')
    for name in ('service-launch.py','host-cap.py','python-downloads.json'):
        require(identity.sha(HERE.parent/name)==record['runtime_sources'][name]['sha256'],'actual lifecycle launcher source differs from frozen original')
    return record


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode',choices=('producer','readback'),required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--inputs',type=Path,required=True)
    ap.add_argument('--sources',type=Path,required=True)
    ap.add_argument('--sources-sha256',required=True)
    ap.add_argument('--producer',type=Path)
    args=ap.parse_args()
    owned_process.announce_worker_from_environment(Path(__file__).resolve())
    # The parent verified this exact worker source and released this Popen child.
    signal.signal(signal.SIGTERM,lambda s,f:(_ for _ in ()).throw(InterruptedError('owned supervisor SIGTERM')))
    out=args.output.resolve();parent=out.parent
    require(not out.exists() and parent.is_dir() and not out.is_relative_to(identity.ROOT),'fresh scientific output outside immutable checkout required')
    resource.setrlimit(resource.RLIMIT_FSIZE,(16*2**20,16*2**20))
    budget=Budget(parent);runtime={'mode':args.mode,'handshake_returned_after_parent_verification':True,
        'self_identity':owned_process.own_identity(),'worker_source_sha256':identity.sha(__file__),
        'API_source_sha256':identity.sha(HERE/'k4_local_section_native_api.py')}
    raw_path=parent/'worker-runtime.json';identity.atomic_json(raw_path,runtime)
    before=None;executed=set();report=None
    try:
        verify_bundle(args.sources,args.sources_sha256)
        require(identity.git('rev-parse','HEAD')==S4 and not identity.git('status','--porcelain','--untracked-files=all'),'clean immutable S4 checkout required')
        before=identity.snapshot();runtime['identity_before']=before;identity.atomic_json(raw_path,runtime)
        require(before['repository_head_at_start']==S4 and not before['worktree_status_at_start'],'source snapshot differs from immutable S4')
        require(before['environment']['passed'] is True and before['environment']['checked_package_count']==43,'all 43 locked packages must match')
        inputs=args.inputs.resolve();proof=json.loads((inputs/'K4-input-verification.json').read_text())
        binding=json.loads((HERE/'K4_INPUT_BINDING.json').read_text())
        require(proof['all_original_manifest_members_SHA_bytes_CRC_verified'] is True and proof['ZIP']==binding['ZIP'],'exact original scientific ZIP must be verified first')
        require(proof['selected_whole_STEP_members']==binding['selected_original_members'],'wrong complete STEP inputs')
        tracked_inputs={p:identity.sha(p) for p in inputs.rglob('*') if p.is_file()}
        require(all(not p.is_symlink() for p in tracked_inputs),'linked inputs prohibited')
        distinct=False
        if args.mode=='readback':
            require(args.producer is not None,'reader requires actual prior producer directory')
            old_dir=args.producer.resolve();old=json.loads((old_dir.parent/'worker-runtime.json').read_text())
            controller=json.loads((old_dir.parent/'controller.json').read_text())
            require(controller['owned_child_identity_verified'] is True and controller['owned_channel_descriptors_closed'] is True,'producer must be a verified terminated owned child')
            require('worker_exit_code' in controller and controller['result_sha256']==identity.sha(old_dir/'report.json'),'producer report must match its actual completed controller record')
            require(old['worker_source_sha256']==runtime['worker_source_sha256'] and old['API_source_sha256']==runtime['API_source_sha256'],'producer/reader source bytes differ')
            a,b=old['self_identity'],runtime['self_identity']
            distinct=(a['pid_namespace'],a['stat']['pid'],a['stat']['starttime_ticks'])!=(b['pid_namespace'],b['stat']['pid'],b['stat']['starttime_ticks'])
            require(distinct,'producer and reader process identity must differ')
            runtime['producer_runtime_sha256']=identity.sha(old_dir.parent/'worker-runtime.json')
            runtime['producer_controller_sha256']=identity.sha(old_dir.parent/'controller.json')
            runtime['separate_from_producer_process_verified']=distinct
            identity.atomic_json(raw_path,runtime)
        def capture_error(scope,error):
            text=str(error);raw=text.encode('utf-8',errors='replace');frames=[]
            for frame in traceback.extract_tb(error.__traceback__):
                path=Path(frame.filename).resolve()
                if path.is_relative_to(identity.ROOT/'.venv') and path.is_file():
                    frames.append({'source_family':'locked_environment_dependency_observation',
                        'relative_environment_path':str(path.relative_to(identity.ROOT/'.venv')),
                        'function':frame.name,'line':frame.lineno,'actual_file_sha256':identity.sha(path),
                        'immutable_Git_source_claimed':False})
                elif path.is_relative_to(identity.ROOT) and path.is_file() and before['available_source_sha256'].get(str(path))==identity.sha(path):
                    frames.append({'source_family':'immutable_S4','repository_path':str(path.relative_to(identity.ROOT)),
                        'function':frame.name,'line':frame.lineno,'sha256':identity.sha(path)})
                elif path.parent==HERE and path.is_file():
                    frames.append({'source_family':'frozen_external_K4','source_name':path.name,
                        'function':frame.name,'line':frame.lineno,'sha256':identity.sha(path)})
            record={'scope':scope,'exception_type':type(error).__name__,'message':text,'traceback':traceback.format_exc()}
            with (parent/'native-errors-private.jsonl').open('a') as stream:stream.write(json.dumps(record)+'\n')
            return {'exception_type':type(error).__name__,'exception_message_UTF8_bytes':len(raw),
                'exception_message_UTF8_sha256':hashlib.sha256(raw).hexdigest(),'raw_exception_message_exported':False,
                'controlled_source_traceback':frames}
        ctx={'functional_source_commit':S4,'owned_supervisor_active':True,'source_bytes_before_verified':True,
            'worktree_clean_before':True,'locked_environment_before_verified':True,'checked_locked_packages_before':43,
            'original_resource_guard_unchanged':True,'separate_from_producer_process_verified':distinct,'capture_error':capture_error}
        def check():
            row=budget.check()
            # Reserve a full next permitted 16 MiB file before any operation or
            # serialization. The unchanged ordinary-disk guard is also enforced.
            require(directory_bytes(out)+16*2**20<=128*2**20,'bounded scientific output reserve reached')
            require(directory_bytes(parent)<=160*2**20,'bounded total worker output reached')
            return row
        def after():
            finish=identity.finish(before,executed)
            verify_bundle(args.sources,args.sources_sha256)
            same_inputs=all(p.is_file() and identity.sha(p)==sha for p,sha in tracked_inputs.items())
            clean=identity.git('rev-parse','HEAD')==S4 and not identity.git('status','--porcelain','--untracked-files=all')
            current_identity=owned_process.own_identity()
            same_process=current_identity==runtime['self_identity']
            runtime.update(identity_after=finish,input_bytes_unchanged=same_inputs,source_checkout_still_clean=clean,
                own_process_identity_unchanged=same_process,resource_after=check())
            identity.atomic_json(raw_path,runtime)
            return {'source_bytes_after_verified':finish['source_bytes_and_locked_environment_unchanged'] and clean and same_inputs,
                'locked_environment_after_verified':finish['environment_after']==before['environment'],
                'checked_locked_packages_after':finish['environment_after']['checked_package_count'],
                'owned_child_identity_verified':same_process}
        executed=identity.record_executed_project_files()
        check()
        import cadquery as cq
        import product_assembly as p
        check()
        kwargs={'cq':cq,'p':p,'spec_path':HERE/'K4_LOCAL_SECTION_PILOT_SPEC.json','step_dir':inputs/'whole_STEP',
            'output':out,'budget_check':check,'context_before':ctx,'context_after':after}
        if args.mode=='producer':report=run_producer(**kwargs)
        else:report=run_reader(**kwargs,producer=args.producer)
        # Diagnostic completion is deliberately separate from local target match.
        return 0 if report.get('execution_completed') is True and report.get('context_after') is not None else 2
    except BaseException as error:
        runtime['failure']={'exception_type':type(error).__name__,'message':str(error)}
        if not (out/'report.json').exists():
            out.mkdir(parents=True,exist_ok=True)
            identity.atomic_json(out/'report.json',{'schema':'razr-K4-worker-entry-failure-v1','mode':args.mode,
                'execution_completed':False,'local_material_targets_all_matched':False,
                'evaluation_failures':[{'scope':'worker_entry','exception_type':type(error).__name__}],**FALSE_FLAGS})
        return 2
    finally:
        if before is not None and 'identity_after' not in runtime:
            try:runtime['identity_after']=identity.finish(before,executed)
            except BaseException as error:runtime['postcheck_failure_type']=type(error).__name__
        runtime['elapsed_seconds']=time.monotonic()-budget.start
        identity.atomic_json(raw_path,runtime)


if __name__=='__main__':raise SystemExit(main())
