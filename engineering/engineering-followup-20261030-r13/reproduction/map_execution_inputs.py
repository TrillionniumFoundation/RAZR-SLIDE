"""Read-only size+SHA input locator. No CAD, numerical solver, or git mutation."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,datetime,hashlib,json,os,stat,subprocess,time

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(path,git_format='sha1'):
    path=Path(path);before=path.stat();h=hashlib.sha256();g=hashlib.new(git_format)
    g.update(b'blob '+str(before.st_size).encode()+b'\0')
    with path.open('rb') as stream:
        while True:
            block=stream.read(1024*1024)
            if not block:break
            h.update(block);g.update(block)
    after=path.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),f'file changed during hashing: {path}'
    return {'bytes':before.st_size,'sha256':h.hexdigest(),'git_blob_id_for_exact_worktree_bytes':g.hexdigest()}
def git(repo,*args):return subprocess.check_output(['git',*args],cwd=repo)
def ident(path):
    path=Path(path);d=digest(path);return {'path':str(path.resolve()),'bytes':d['bytes'],'sha256':d['sha256']}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();repo=a.repository.resolve();workspace=a.workspace.resolve();output=a.output.resolve()
    output.mkdir(parents=True,exist_ok=True);out=output/'R13_EXECUTION_INPUT_TO_REPOSITORY_MAP.json';assert not out.exists(),'use a new output snapshot'
    started=now();clock=time.monotonic();head=git(repo,'rev-parse','HEAD').decode().strip();branch=git(repo,'branch','--show-current').decode().strip()
    git_format=git(repo,'rev-parse','--show-object-format').decode().strip()
    head_files={}
    for raw in git(repo,'ls-tree','-r','-z',head).split(b'\0'):
        if not raw:continue
        meta,path=raw.split(b'\t',1);mode,kind,blob=meta.decode().split()
        if kind=='blob':head_files[os.fsdecode(path)]=blob
    index_files={}
    for raw in git(repo,'ls-files','--stage','-z').split(b'\0'):
        if not raw:continue
        meta,path=raw.split(b'\t',1);mode,blob,stage=meta.decode().split()
        if stage=='0':index_files[os.fsdecode(path)]=blob
    sources=[
        ('envelope.INPUT_MANIFEST',workspace/'r13_envelope_work/inputs/INPUT_MANIFEST.json','engineering/engineering-followup-20261030-r13/envelope/inputs/INPUT_MANIFEST.json'),
        ('geometry.INPUT_MANIFEST',workspace/'r13_geometry_work/INPUT_MANIFEST.json','engineering/engineering-followup-20261030-r13/geometry/INPUT_MANIFEST.json'),
        ('geometry.EXTERNAL_DEPENDENCIES',workspace/'r13_geometry_work/EXTERNAL_DEPENDENCIES.json','engineering/engineering-followup-20261030-r13/geometry/EXTERNAL_DEPENDENCIES.json')]
    manifest_rows=[];entries=[]
    for group,path,repo_path in sources:
        manifest=json.loads(path.read_text());source_id=ident(path)
        imported=ident(repo/repo_path) if (repo/repo_path).is_file() else None
        assert imported is not None and all(source_id[k]==imported[k] for k in ('bytes','sha256')),'imported manifest identity differs'
        manifest_rows.append({'group':group,'original_manifest':source_id,'repository_manifest_path':repo_path,'imported_manifest_byte_identical':True})
        items=list(manifest['files'].items()) if isinstance(manifest['files'],dict) else [(row['path'],row) for row in manifest['files']]
        for ordinal,(name,row) in enumerate(items):
            if group=='envelope.INPUT_MANIFEST':
                source_path=row['source_path'];local='inputs/'+row['path'];copied_repo='engineering/engineering-followup-20261030-r13/envelope/'+local
            elif group=='geometry.INPUT_MANIFEST':
                source_path=row['source_path'];local=row['copy_path'];copied_repo='engineering/engineering-followup-20261030-r13/geometry/'+local
            else:source_path=row['path'];local=None;copied_repo=None
            assert Path(source_path).is_absolute() and '..' not in Path(source_path).parts
            entries.append({'entry_id':group+':'+str(ordinal),'group':group,'manifest_item':name,'manifest_ordinal':ordinal,
                'record_use':'explicit_external_execution_dependency' if group.endswith('EXTERNAL_DEPENDENCIES') else 'original_source_of_already_frozen_package_copy',
                'original_absolute_path':source_path,'frozen_copy_path_within_package':local,'expected_frozen_copy_repository_path':copied_repo,
                'required_bytes':row['bytes'],'required_sha256':row['sha256']})
    assert len(entries)==60 and Counter(e['group'] for e in entries)=={'envelope.INPUT_MANIFEST':14,'geometry.INPUT_MANIFEST':35,'geometry.EXTERNAL_DEPENDENCIES':11}
    wanted_sizes={e['required_bytes'] for e in entries};wanted={(e['required_bytes'],e['required_sha256']) for e in entries}
    inventory=subprocess.check_output(['rg','--files','--hidden','--no-ignore','-0','-g','!.git','-g','!**/__pycache__/**'],cwd=repo).split(b'\0')
    matches=defaultdict(list);candidate_count=0;scanned_files=0;bytes_hashed=0;cache={};skipped_symlinks=[]
    for raw in inventory:
        if not raw:continue
        rel=os.fsdecode(raw);path=repo/rel
        try:st=path.lstat()
        except FileNotFoundError:continue
        if stat.S_ISLNK(st.st_mode):skipped_symlinks.append(rel);continue
        if not stat.S_ISREG(st.st_mode):continue
        scanned_files+=1
        if st.st_size not in wanted_sizes:continue
        candidate_count+=1;d=digest(path,git_format);bytes_hashed+=d['bytes'];cache[rel]=d
        key=(d['bytes'],d['sha256'])
        if key not in wanted:continue
        matches[key].append({'repository_path':rel,'bytes':d['bytes'],'sha256':d['sha256'],
            'exact_worktree_blob_id':d['git_blob_id_for_exact_worktree_bytes'],
            'path_present_at_observed_HEAD':rel in head_files,
            'exact_bytes_present_at_observed_HEAD':head_files.get(rel)==d['git_blob_id_for_exact_worktree_bytes'],
            'path_in_observed_index':rel in index_files,
            'exact_bytes_in_observed_index':index_files.get(rel)==d['git_blob_id_for_exact_worktree_bytes']})
    for entry in entries:
        source=Path(entry['original_absolute_path']);origin={'exists_in_original_local_workspace_now':source.is_file()}
        if origin['exists_in_original_local_workspace_now']:
            d=digest(source,git_format);origin.update(observed_bytes=d['bytes'],observed_sha256=d['sha256'],
                'matches_declared_identity':(d['bytes'],d['sha256'])==(entry['required_bytes'],entry['required_sha256']))
        entry['original_location_observation']=origin
        options=matches[(entry['required_bytes'],entry['required_sha256'])]
        old_relative=entry['original_absolute_path'].split('/RAZR-SLIDE/',1)[1] if '/RAZR-SLIDE/' in entry['original_absolute_path'] else None
        def rank(row):
            path=row['repository_path'];preferred_region=(('panel_fill_work/' in entry['original_absolute_path'] and 'engineering-followup-20261030-r12/panel-filling/' in path)
                or ('/geometry_work/' in entry['original_absolute_path'] and 'engineering-followup-20261030-r12/geometry/' in path))
            return (not row['exact_bytes_present_at_observed_HEAD'],path!=old_relative,not preferred_region,
                    path!=entry['expected_frozen_copy_repository_path'],len(path),path)
        options=sorted(options,key=rank);entry['repository_matches']=options
        entry['repository_match_status']=('present_at_observed_HEAD' if any(x['exact_bytes_present_at_observed_HEAD'] for x in options)
                                          else 'present_only_in_observed_worktree_or_index' if options else 'no_exact_regular_file_found_in_repository')
        entry['preferred_repository_path']=options[0]['repository_path'] if options else None
        if entry['expected_frozen_copy_repository_path'] is not None:
            entry['frozen_package_copy_found_with_exact_identity']=any(x['repository_path']==entry['expected_frozen_copy_repository_path'] for x in options)
            assert entry['frozen_package_copy_found_with_exact_identity'],'missing/mismatched imported frozen input'
        entry['path_adaptation']={
            'recorded_absolute_path_is_portable_to_an_arbitrary_checkout':False,
            'recorded_path_kind':'original_checkout_absolute_path' if old_relative is not None else 'external_workspace_absolute_path',
            'matching_original_repository_relative_suffix':old_relative if old_relative in {x['repository_path'] for x in options} else None,
            'input_copy_main_programs_can_use_package_relative_path':entry['record_use']=='original_source_of_already_frozen_package_copy',
            'historical_preparation_or_external_reader_needs_original_layout_or_explicit_path_adapter':True,
            'this_mapping_materializes_layout_or_executes_adapter':False,
            'original_execution_environment_reproduced':False}
    # Independent final byte re-read of every selected mapping, not a scientific replay.
    selected={e['preferred_repository_path'] for e in entries if e['preferred_repository_path']}
    for rel in selected:
        assert digest(repo/rel,git_format)==cache[rel],'selected repository input changed after scan'
    endhead=git(repo,'rev-parse','HEAD').decode().strip();assert endhead==head,'HEAD changed during mapping; rerun a new snapshot'
    groups={g:dict(Counter(e['repository_match_status'] for e in entries if e['group']==g)) for g,_,_ in sources}
    result={'schema':'razr-r13-original-execution-input-to-current-repository-content-map-v1',
        'started_at_utc':started,'completed_at_utc':now(),'seconds':time.monotonic()-clock,'mapper_source':ident(__file__),
        'repository':{'absolute_path_at_mapping':str(repo),'observed_branch':branch,'observed_HEAD':head,'observed_HEAD_tree':git(repo,'rev-parse',head+'^{tree}').decode().strip(),
                      'git_object_format':git_format,'HEAD_unchanged_during_mapping':True,'remote_state_verified_by_this_mapper':False},
        'manifest_sources':manifest_rows,'entries':entries,
        'summary':{'declared_input_records':len(entries),'unique_size_SHA256_identities':len(wanted),
            'records_by_group_and_status':groups,'records_with_exact_repository_match':sum(bool(e['repository_matches']) for e in entries),
            'records_with_exact_HEAD_match':sum(e['repository_match_status']=='present_at_observed_HEAD' for e in entries),
            'worktree_or_index_only_records':sum(e['repository_match_status']=='present_only_in_observed_worktree_or_index' for e in entries),
            'records_without_exact_repository_match':sum(not e['repository_matches'] for e in entries),
            'original_absolute_locations_currently_absent':sum(not e['original_location_observation']['exists_in_original_local_workspace_now'] for e in entries),
            'original_absolute_locations_identity_mismatch':sum(e['original_location_observation'].get('matches_declared_identity') is False for e in entries),
            'regular_repository_files_scanned':scanned_files,'size_filtered_candidate_files_hashed':candidate_count,'candidate_bytes_hashed':bytes_hashed,
            'selected_repository_paths_reread':len(selected),'repository_symlinks_not_followed':skipped_symlinks},
        'scope':{'size_and_SHA256_identity_mapping_only':True,'all_three_manifest_record_sets_accounted':True,
            'archives_extracted_or_member_paths_promoted_to_real_files':False,'CAD_or_arithmetic_or_numerical_tasks_rerun':False,
            'sealed_sources_or_reports_modified':False,'git_mutation_or_push_performed':False,
            'original_absolute_layout_recreated':False,'original_interpreter_native_libraries_and_environment_reproduced':False,
            'scientific_execution_reproduced':False,'native_material_or_physical_qualification_added':False}}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'json':str(out),'sha256':digest(out)['sha256'],'summary':result['summary']},ensure_ascii=False))

if __name__=='__main__':main()
