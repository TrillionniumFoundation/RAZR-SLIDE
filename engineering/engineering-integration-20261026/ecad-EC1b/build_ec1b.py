"""Prepare EC1b: append only three observed missing-SONAME provider packages."""
from pathlib import Path
import argparse,ast,copy,hashlib,json,subprocess
import yaml
S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
TREE='cdd9e2c41216201b6cd04dd610d45fde80499045'
HERE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def put(name,value):
 p=HERE/name;p.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n');return p
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--original-ec1',type=Path,required=True)
 ap.add_argument('--original-ec1a',type=Path,required=True)
 ap.add_argument('--source-root',type=Path,required=True)
 ap.add_argument('--emit-request-only',action='store_true')
 args=ap.parse_args()
 original=args.original_ec1;prior=args.original_ec1a
 oldnames=('run_ec1.py','export_ec1.py','EC1_PINNED_PACKAGES.json')
 preserved={n:original/n for n in oldnames}
 preserved.update({n:prior/n for n in ('diagnose_ec1.py','test_diagnose_ec1.py','EC1_FIRST_RUN_ENVIRONMENT_FAILURE.json')})
 names=('EC1B_PINNED_PACKAGES.json','OFFICIAL_PACKAGE_SOURCE_RECORD.json','NEW_PACKAGE_ELF_AND_DEPENDENCY_READBACK.json',
        'EC1B_PACKAGE_REPAIR_BINDING.json','EC1A_ACTUAL_ENVIRONMENT_FAILURE.json','EC1B_STATIC_CHECK.json','README.md','build_ec1b.py')
 if not args.emit_request_only:
  prior_check=json.loads((prior/'EC1A_STATIC_CHECK.json').read_text())
  for n,p in preserved.items():
   if n=='EC1_FIRST_RUN_ENVIRONMENT_FAILURE.json':continue
   r=prior_check['all_embedded_files_byte_identical'][n]
   b=p.read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
   if n.endswith('.py'):ast.parse(b,feature_version=(3,10))
  assert subprocess.check_output(['git','rev-parse',S4+'^{tree}'],cwd=args.source_root,text=True).strip()==TREE
  for n,h in prior_check['source_sha256'].items():
   b=subprocess.check_output(['git','show',S4+':'+n],cwd=args.source_root)
   assert sha(b)==h
  official=json.loads((HERE/'OFFICIAL_PACKAGE_SOURCE_RECORD.json').read_text())
  elf=json.loads((HERE/'NEW_PACKAGE_ELF_AND_DEPENDENCY_READBACK.json').read_text())
  assert sha((HERE/'OFFICIAL_PACKAGE_SOURCE_RECORD.json').read_bytes())==elf['source_index_record_sha256']
  assert official['InRelease_signature']['verified'] and official['full_index_bytes_verified']
  assert elf['new_package_bytes_match_official_signed_index']
  assert elf['every_new_NEEDED_resolved_by_pinned_new_provider_or_observed_prior_resolved_provider']
  assert elf['actual_EC1b_linker_closure_not_yet_executed']
  assert len(official['packages'])==3 and len(elf['packages'])==3
  pins=json.loads(preserved['EC1_PINNED_PACKAGES.json'].read_text())
  assert len(pins['packages'])==34
  additions=[]
  for index,row in enumerate(official['packages']):
   e=elf['packages'][index]
   assert e['package']==row['Package'] and e['version']==row['Version'] and e['architecture']==row['Architecture']=='amd64'
   assert e['bytes']==int(row['Size']) and e['sha256']==row['SHA256']
   assert e['url']=='https://archive.ubuntu.com/ubuntu/'+row['Filename']
   additions.append({'name':Path(row['Filename']).name,'bytes':int(row['Size']),'sha256':row['SHA256'],'url':e['url']})
  assert [p['Package'] for p in official['packages']]==['libglew2.2','libjxr0t64','libmbedcrypto7t64']
  newpins={'schema':'razr-EC1b-original-pins-plus-observed-SONAME-providers-v1',
   'scope':'Original 34 pinned package rows unchanged; append only three officially authenticated providers observed missing in EC1a.',
   'original_package_manifest_sha256':sha(preserved['EC1_PINNED_PACKAGES.json'].read_bytes()),
   'original_package_count':34,'additional_package_count':3,'packages':pins['packages']+additions}
  pinpath=put('EC1B_PINNED_PACKAGES.json',newpins)
  oldwf=(prior/'s4-ecad-ec1a-hosted.yml').read_bytes()
  assert sha(oldwf)==prior_check['workflow_sha256']
  old=yaml.safe_load(oldwf);wf=copy.deepcopy(old)
  wf['name']='EC1b original S4 KiCad checks with three authenticated missing-library providers'
  wf['on']['push']['branches']=['diagnostic/s4-ecad-ec1b-20261026']
  wf['concurrency']['group']='ec1b-'+'$'+'{{ github.ref }}'
  steps=wf['jobs']['ecad']['steps']
  prepare=steps[1]
  extra='\ncat > "$RUNNER_TEMP/razr-ec1-source/EC1B_PINNED_PACKAGES.json" <<\'RAZR_EC1B_PACKAGES\'\n'+pinpath.read_text()+'RAZR_EC1B_PACKAGES\n'
  check="""from pathlib import Path
import hashlib,json,os
source=Path(os.environ['RUNNER_TEMP'])/'razr-ec1-source'
old=source/'EC1_PINNED_PACKAGES.json'
new=source/'EC1B_PINNED_PACKAGES.json'
assert hashlib.sha256(old.read_bytes()).hexdigest()=='OLD_SHA'
assert hashlib.sha256(new.read_bytes()).hexdigest()=='NEW_SHA'
original=json.loads(old.read_text())['packages']
extended=json.loads(new.read_text())['packages']
assert len(original)==34 and len(extended)==37 and extended[:34]==original
assert extended[34:]==ADDITIONS
assert sum(r['bytes'] for r in extended[34:])==578006
assert len({r['name'] for r in extended})==37
""".replace('OLD_SHA',sha(preserved['EC1_PINNED_PACKAGES.json'].read_bytes())).replace('NEW_SHA',sha(pinpath.read_bytes())).replace('ADDITIONS',repr(additions))
  extra+="python3 -B - <<'EC1B_PACKAGE_CHECK'\n"+check+'EC1B_PACKAGE_CHECK\n'
  prepare['run']+=extra
  assert prepare['run'][:-len(extra)]==old['jobs']['ecad']['steps'][1]['run']
  steps[3]['run']=steps[3]['run'].replace('"$RUNNER_TEMP/razr-ec1-source/EC1_PINNED_PACKAGES.json"','"$RUNNER_TEMP/razr-ec1-source/EC1B_PINNED_PACKAGES.json"')
  steps[-1]['with']['name']='s4-ec1b-engineering'
  for i in (0,2,4,5):assert steps[i]==old['jobs']['ecad']['steps'][i]
  assert steps[3]['run'].replace('/EC1B_PINNED_PACKAGES.json','/EC1_PINNED_PACKAGES.json')==old['jobs']['ecad']['steps'][3]['run']
  assert wf['jobs']['ecad']['runs-on']=='ubuntu-24.04'
  assert wf['permissions']=={'contents':'read'} and wf['jobs']['ecad']['timeout-minutes']==25
  assert steps[-1]['with']['path']==old['jobs']['ecad']['steps'][-1]['with']['path']
  bash_count=0;inline_count=0
  for step in steps:
   if 'run' not in step:continue
   subprocess.run(['bash','-n'],input=step['run'].encode(),check=True);bash_count+=1
   lines=step['run'].splitlines()
   for i,line in enumerate(lines):
    if "python3 -B - <<'" not in line:continue
    tag=line.split("<<'",1)[1].split("'",1)[0]
    end=next(j for j in range(i+1,len(lines)) if lines[j]==tag)
    ast.parse('\n'.join(lines[i+1:end])+'\n',feature_version=(3,10));inline_count+=1
  for name,path in preserved.items():
   if name=='EC1_FIRST_RUN_ENVIRONMENT_FAILURE.json':continue
   tag='RAZR_EC1_SOURCE' if name in oldnames else 'RAZR_EC1A_SOURCE'
   marker='cat > "$RUNNER_TEMP/razr-ec1-source/'+name+'" <<\''+tag+"'\n"
   embedded=prepare['run'].split(marker,1)[1].split('\n'+tag+'\n',1)[0]+'\n'
   assert embedded.encode()==path.read_bytes()
  assert prepare['run'].split('RAZR_EC1B_PACKAGES\'\n',1)[1].split('\nRAZR_EC1B_PACKAGES\n',1)[0]+'\n'==pinpath.read_text()
  test=subprocess.run(['python3','-B',str(prior/'test_diagnose_ec1.py')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True)
  workflow=yaml.safe_dump(wf,sort_keys=False,width=110).encode();assert len(workflow)<500000
  (HERE/'s4-ecad-ec1b-hosted.yml').write_bytes(workflow)
  actual=prior/'EC1A-actual'
  review=json.loads((actual/'EC1A_ACTUAL_DIAGNOSTIC_REVIEW.json').read_text())
  diag=json.loads((actual/'isolated-linkage.engineering.json').read_text())
  execution=json.loads((actual/'execution.engineering.json').read_text())
  assert review['run_id']==40277280890 and review['artifact_id']==12634192069
  assert review['ZIP_sha256']=='f63d10da2aebd49cbbb7d8ca2c9a7986244ef7d00407dfb0da795d5f39b34353'
  missing=sorted({d['soname'] for r in diag['ldd'] for d in r['dependencies'] if d['state']=='missing'})
  assert missing==['libGLEW.so.2.2','libjxrglue.so.0','libmbedcrypto.so.7']
  failure={'schema':'razr-EC1a-observed-missing-provider-failure-v1','run_id':40277280890,
   'head_sha':'e64b64f8f4ab8de253a29ff16388be3aa474a8ee','job_id':121422599126,'artifact_id':12634192069,
   'engineering_ZIP_bytes':13081,'engineering_ZIP_sha256':review['ZIP_sha256'],
   'MANIFEST_sha256':review['manifest_sha256'],'manifest_entries':7,'exact_member_set_and_full_CRC_SHA_verified':True,
   'diagnostic_record_sha256':sha((actual/'isolated-linkage.engineering.json').read_bytes()),
   'version_exit_code':127,'original_and_repeat_version_log_sha256':'85000b4e91ae8e4d3f69dc76c9f269f76d15f4080fde29f669686cc55db0565e',
   'classification':'loader_missing_library','observed_missing_SONAMEs':missing,'native_DRC_executed':False,
   'source_bytes_unchanged':True,'CAD_or_DRC_rejection_claimed':False,'original_EC1_failure_rewritten':False}
  put('EC1A_ACTUAL_ENVIRONMENT_FAILURE.json',failure)
  binding={'schema':'razr-EC1b-package-only-repair-binding-v1','source_commit':S4,'source_tree':TREE,
   'source_sha256':prior_check['source_sha256'],'source_files_byte_identical_to_original_S4':True,
   'original_34_package_rows_preserved_exactly':True,'original_34_package_manifest_sha256':sha(preserved['EC1_PINNED_PACKAGES.json'].read_bytes()),
   'extended_package_manifest_sha256':sha(pinpath.read_bytes()),'additional_packages':additions,
   'official_source_record_sha256':sha((HERE/'OFFICIAL_PACKAGE_SOURCE_RECORD.json').read_bytes()),
   'new_ELF_dependency_readback_sha256':sha((HERE/'NEW_PACKAGE_ELF_AND_DEPENDENCY_READBACK.json').read_bytes()),
   'capacity_basis':{'actual_EC1a_download_extract_and_failed_version_elapsed_seconds':execution['engineering_record']['elapsed_seconds'],
    'actual_EC1a_complete_package_download_bytes':90574234,'new_download_bytes':578006,
    'new_data_tar_bytes':1699840,'official_new_package_installed_size_KiB':1886,
    'planning_incremental_disk_headroom_bytes':4*1024*1024,
    'exact_total_package_download_bytes':91152240,
    'original_package_download_socket_timeout_seconds':90,'original_download_threads':4,
    'original_each_package_extraction_timeout_seconds':60,'original_verifier_timeout_seconds':930,
    'original_job_timeout_minutes':25,'all_original_native_resource_guards_unchanged':True,
    'new_native_wall_time_not_yet_observed':True},
   'dependency_scope':{'new_ELF_NEEDED_all_resolved_by_package_internal_or_observed_prior_resolved_SONAME':True,
    'package_internal_additional_provider':'libjpegxr.so.0','unchanged_platform_provider_SONAMEs':['libGL.so.1','libc.so.6','libm.so.6'],
    'actual_new_runner_symbol_version_and_import_closure_not_yet_executed':True,
    'same_ubuntu_24_04_amd64_platform_and_original_apt_step':True},
   'original_version_and_DRC_checks_bypassed':False,'original_driver_exporter_and_diagnostic_modified':False,
   'new_dependency_packages_executed_locally':False,'raw_runtime_exported':False,
   'existing_E3_S4_native_pass_replaced':False,'new_native_pass_claimed':False,
   'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
  put('EC1B_PACKAGE_REPAIR_BINDING.json',binding)
  static={'schema':'razr-EC1b-static-source-and-workflow-check-v1','source_commit':S4,'source_tree':TREE,
   'prior_EC1a_workflow_sha256':sha(oldwf),'workflow_sha256':sha(workflow),'workflow_bytes':len(workflow),
   'preserved_driver_exporter_original_manifest_diagnostic_test':{n:{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for n,p in preserved.items()},
   'original_34_rows_byte_equivalent_objects':True,'exact_new_row_count':3,
   'all_six_embedding_payloads_byte_identical':True,'original_checkout_apt_export_diagnostic_steps_unchanged':True,
   'launch_command_only_package_argument_changes':True,'source_check_sha256':prior_check['source_sha256'],
   'bash_blocks_parsed':bash_count,'inline_python_3_10_blocks_parsed':inline_count,
   'original_six_projection_tests_exit_code':test.returncode,'original_six_projection_tests_log_sha256':sha(test.stdout),
   'native_CAD_or_ECAD_executed':False,'raw_runtime_added_to_artifact':False}
  put('EC1B_STATIC_CHECK.json',static)
  (HERE/'README.md').write_text("""# EC1b：按实际 SONAME 补齐三个固定官方依赖

EC1 首轮与 EC1a 均在原 kicad-version 先决失败，未执行 native DRC。EC1a 已实际读取两个目标的完整 ldd 分类：kicad-cli 缺 libmbedcrypto.so.7；_pcbnew 缺该库、libGLEW.so.2.2、libjxrglue.so.0。原失败分别保留，既有 E3 中同 S4 源的 native 真 pass 不被这些环境失败覆盖。

本次仅向原 34 条固定包记录后追加三项，不替换任何旧条目：Ubuntu noble amd64 的 libglew2.2 2.2.0-4build1、libjxr0t64 1.2~git20170615.f752187-5.1ubuntu2、libmbedcrypto7t64 2.28.8-1。Ubuntu 官方 InRelease 的 GPG 签名、其绑定的完整 Packages.xz SHA、三个完整 DEB 的 bytes/SHA 均已实际核验。通过标准 dpkg-deb/readelf 在内存中读取控制记录、ELF64 AMD64、SONAME、NEEDED 和所需 ABI 版本；未执行这些库，也未保存或公开 runtime 原包。具体原始来源 URL 与认证摘要见 OFFICIAL_PACKAGE_SOURCE_RECORD.json，逐 ELF 结果见 NEW_PACKAGE_ELF_AND_DEPENDENCY_READBACK.json。这里的 member 字段是官方包内相对成员名，不是现场运行路径。

新增直接依赖中的 libjpegxr.so.0 由同一固定 JXR 包提供；libGL.so.1、libc.so.6、libm.so.6 已在 EC1a 的实际 ldd 中解析。该证据只支持 SONAME 依赖闭包与选包，尚不证明新 worker 的全部版本符号解析或 KiCad 导入成功；仍由原 version/native-readback/native-drc 检查实际决定。

原 34 包共 90,574,234 B，EC1a 已完成下载、解包及失败版本调用，共 12.3324 s；新增下载 578,006 B，三份 data.tar 合计 1,699,840 B，官方 Installed-Size 合计 1,886 KiB，规划增加 4 MiB 磁盘余量。原 4 下载线程、90 s socket、单包 60 s 解包、930 s verifier 与 25 min job 上限不变，不能由此前版本失败阶段时钟预测后续 DRC 时钟。

run_ec1.py、export_ec1.py、diagnose_ec1.py、其六项纯投影测试、原 34 包 JSON 均逐字节保留。五个 S4 原检查/设计源和原参数、版本门、DRC、资源守卫不改；workflow 只新增固定包 JSON 与精确 preflight，原 launcher 仅改为读取扩展包清单。Ubuntu runner、原 apt 步骤、导出/诊断流程、always-upload 科学白名单不变。原包仅留 SHA/核验过程；没有新增任何 raw runtime 公共投影。

本次准备阶段未执行 native ECAD；所有资格仍由实际原检查及可读回原件决定。软件 continuity/DRC 也不等于 OEM 端子、真实 OLED/COF/FPC、动态弯折或物理 G3–G5 资格。
""")
  print(json.dumps({'prepared_only':True,'workflow_bytes':len(workflow),'workflow_sha256':sha(workflow),'new_pin_sha256':sha(pinpath.read_bytes()),'local_native_executed':False,'own_RAM_text_bytes':sum(p.stat().st_size for p in HERE.parent.rglob('*') if p.is_file())}))
  return
 files={**preserved,**{n:HERE/n for n in names}}
 static=json.loads((HERE/'EC1B_STATIC_CHECK.json').read_text())
 for n,r in static['preserved_driver_exporter_original_manifest_diagnostic_test'].items():
  b=files[n].read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
 wfpath=HERE/'s4-ecad-ec1b-hosted.yml';workflow=wfpath.read_bytes();assert sha(workflow)==static['workflow_sha256']
 target='engineering/engineering-integration-20261026/ecad-EC1b/'
 elements=[{'path':target+n,'mode':'100644','type':'blob','content':p.read_text()} for n,p in files.items()]
 elements.append({'path':'.github/workflows/s4-ecad-ec1b-hosted.yml','mode':'100644','type':'blob','content':workflow.decode()})
 request={'repository_full_name':'TrillionniumFoundation/RAZR-SLIDE','base_tree_sha':TREE,'tree_elements':elements}
 raw=(json.dumps(request,indent=2,ensure_ascii=False)+'\n').encode()
 own=sum(p.stat().st_size for p in HERE.parent.rglob('*') if p.is_file())
 assert own+len(raw)+12000<500000,(own,len(raw))
 req=HERE/'EC1B_PUBLIC_TREE_REQUEST.json';req.write_bytes(raw)
 mapping={'entries':[{'local_path':str(wfpath if e['path'].startswith('.github/') else files[e['path'].removeprefix(target)]),'repository_path':e['path'],'sha256':sha(e['content'].encode()),'bytes':len(e['content'].encode())} for e in elements]}
 mp=put('EC1B_SAFE_INTEGRATION_MAPPING.json',mapping)
 plan={'branch':'diagnostic/s4-ecad-ec1b-20261026','base_commit':S4,'base_tree':TREE,'request_sha256':sha(raw),'workflow_sha256':sha(workflow),'mapping_sha256':sha(mp.read_bytes()),'tree_paths':len(elements),'published':False}
 put('EC1B_PUBLICATION_PLAN.json',plan);print(json.dumps(plan))
if __name__=='__main__':main()
