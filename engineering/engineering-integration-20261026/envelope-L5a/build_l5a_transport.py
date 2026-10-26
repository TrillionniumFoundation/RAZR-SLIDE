"""L5a transport-only repair for the actual 500 KB workflow rejection."""
from pathlib import Path
import ast,copy,hashlib,json,re,subprocess,sys,time,urllib.request
import yaml
HERE=Path(__file__).resolve().parent
OLD=Path(sys.argv[1]).resolve()
COMMIT='b3c9bef2abe0d7065063bc966ec2083616286bd5'
TREE='fd7b1c070a2eb9369f0c870a71be467bbcdd7255'
TARGET='engineering/engineering-integration-20261026/envelope-L5/'
S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
sha=lambda b:hashlib.sha256(b).hexdigest()
def write_json(name,obj):
 p=HERE/name;p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n');return p
old_bytes=(OLD/'s4-k1-l5-cylindrical-hosted.yml').read_bytes()
assert len(old_bytes)==660075 and sha(old_bytes)=='c751f9d7fc6088dcb788ccf4a1bd9e0dcc35d8bf3b3c1a53e27ecd55d16743a1'
old=yaml.safe_load(old_bytes);wf=copy.deepcopy(old)
oldrun=old['jobs']['original']['steps'][2]['run']
assert oldrun==old['jobs']['current']['steps'][2]['run']
check=oldrun.split("python3 -B - <<'L5_SOURCE_CHECK'\n",1)[1].split('\nL5_SOURCE_CHECK\n',1)[0]
expected=next(ast.literal_eval(node.value) for node in ast.parse(check).body if isinstance(node,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='expected' for x in node.targets))
assert len(expected)==21
for n,r in expected.items():
 raw=(OLD/n).read_bytes();assert len(raw)==r['bytes'] and sha(raw)==r['sha256']
 if n.endswith('.py'):ast.parse(raw,feature_version=(3,10))
prefix,rest=oldrun.split('mkdir -p "$HOST_ROOT/l5" "$CASE_DIR/source/l5"\n',1)
removed=''
for name in expected:
 marker='L5_'+re.sub('[^A-Z0-9]','_',name.upper())
 section='cat > "$HOST_ROOT/l5/'+name+'" <<\''+marker+"'\n"+(OLD/name).read_text()+marker+'\n'
 section+='cp "$HOST_ROOT/l5/'+name+'" "$CASE_DIR/source/l5/'+name+'"\n'
 assert rest.startswith(section);rest=rest[len(section):];removed+=section
assert rest.startswith("python3 -B - <<'L5_SOURCE_CHECK'\n")
assert prefix+'mkdir -p "$HOST_ROOT/l5" "$CASE_DIR/source/l5"\n'+removed+rest==oldrun
download="""import hashlib,json,os,pathlib,time,urllib.request
root=pathlib.Path(os.environ['HOST_ROOT'])/'l5'
copy=pathlib.Path(os.environ['CASE_DIR'])/'source'/'l5'
expected=RECORDS
prefix='https://raw.githubusercontent.com/TrillionniumFoundation/RAZR-SLIDE/COMMIT/TARGET'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise ValueError('unexpected_public_source_redirect')
opener=urllib.request.build_opener(NoRedirect)
started=time.monotonic()
total=0
for name,row in expected.items():
    if pathlib.Path(name).name!=name:
        raise ValueError('invalid_fixed_source_basename')
    req=urllib.request.Request(prefix+name,headers={'User-Agent':'RAZR-L5a-source-readback'})
    with opener.open(req,timeout=15) as response:
        if response.status!=200 or response.geturl()!=prefix+name:
            raise ValueError('unexpected_public_source_response')
        raw=response.read(row['bytes']+1)
    if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
        raise ValueError('published_source_bytes_differ')
    for parent in (root,copy):
        with (parent/name).open('xb') as stream:
            stream.write(raw)
    total+=len(raw)
print(json.dumps({'source_commit':'COMMIT','verified_source_count':len(expected),'verified_source_bytes':total,'elapsed_seconds':time.monotonic()-started,'credentials_sent':False}))
""".replace('RECORDS',repr(expected)).replace('COMMIT',COMMIT).replace('TARGET',TARGET)
block="timeout --signal=TERM --kill-after=5s 90s python3 -B - <<'L5A_PINNED_PUBLIC_SOURCE'\n"+download+"L5A_PINNED_PUBLIC_SOURCE\n"
newrun=prefix+'mkdir -p "$HOST_ROOT/l5" "$CASE_DIR/source/l5"\n'+block+rest
assert newrun.replace(block,removed,1)==oldrun
for key in wf['jobs']:
 wf['jobs'][key]['steps'][2]['run']=newrun
 wf['jobs'][key]['steps'][2]['name']='Bind S4 and byte-exact published L5 sources under original guards'
wf['name']='L5a same whole-section diagnostic with bounded immutable public source loading'
wf['on']['push']['branches']=['diagnostic/s4-k1-l5a-cylindrical-20261026']
wf['concurrency']['group']='l5a-whole-sections-'+'$'+'{{ github.ref }}'
workflow=yaml.safe_dump(wf,sort_keys=False,width=110).encode();assert len(workflow)<500000
for key in old['jobs']:
 a=copy.deepcopy(wf['jobs'][key]);a['steps'][2]=old['jobs'][key]['steps'][2];assert a==old['jobs'][key]
assert wf['permissions']==old['permissions'] and wf['env']==old['env']
assert wf['jobs']['current']['needs']==old['jobs']['current']['needs']
assert all(j['timeout-minutes']==40 for j in wf['jobs'].values())
bash_count=0;inline_count=0
for job in wf['jobs'].values():
 for step in job['steps']:
  if 'run' not in step:continue
  s=step['run'];subprocess.run(['bash','-n'],input=s.encode(),check=True);bash_count+=1
  lines=s.splitlines()
  for i,line in enumerate(lines):
   m=re.search(r"\bpython(?:3)?(?: -B)? - <<'([A-Za-z0-9_]+)'$",line)
   if not m:continue
   end=next(j for j in range(i+1,len(lines)) if lines[j]==m.group(1))
   ast.parse('\n'.join(lines[i+1:end])+'\n',feature_version=(3,10));inline_count+=1
wfpath=HERE/'s4-k1-l5a-cylindrical-hosted.yml';wfpath.write_bytes(workflow)
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  raise ValueError('unexpected_public_source_redirect')
opener=urllib.request.build_opener(NoRedirect);readback=[];started=time.monotonic()
for name,row in expected.items():
 url='https://raw.githubusercontent.com/TrillionniumFoundation/RAZR-SLIDE/'+COMMIT+'/'+TARGET+name
 before=time.monotonic()
 with opener.open(urllib.request.Request(url,headers={'User-Agent':'RAZR-L5a-source-readback'}),timeout=15) as response:
  assert response.status==200 and response.geturl()==url;data=response.read(row['bytes']+1)
 assert len(data)==row['bytes'] and sha(data)==row['sha256']
 readback.append({'name':name,**row,'exact_public_readback_passed':True,'seconds':time.monotonic()-before})
elapsed=time.monotonic()-started
binding={'schema':'razr-L5a-bounded-public-source-transport-v1','source_commit':COMMIT,'source_tree':TREE,
 'repository_prefix':TARGET,'functional_source_commit':S4,'source_count':21,'total_verified_download_bytes':sum(r['bytes'] for r in expected.values()),
 'exact_source_bytes_unchanged':True,'source_files':readback,'local_actual_public_readback_seconds':elapsed,
 'raw_runtime_downloaded_or_exported':False,'credentials_sent':False,'redirects_permitted':False,
 'per_request_socket_timeout_seconds':15,'hard_source_install_process_timeout_seconds':90,
 'hard_source_install_termination_grace_seconds':5,'existing_external_host_deadline_seconds':2220,
 'existing_per_job_timeout_minutes':40,'new_download_does_not_extend_either_existing_deadline':True,
 'native_executed_by_static_or_transport_check':False}
write_json('L5A_SOURCE_TRANSPORT_BINDING.json',binding)
checks={'schema':'razr-L5a-transport-only-static-check-v1','original_workflow_sha256':sha(old_bytes),'original_workflow_bytes':len(old_bytes),
 'new_workflow_sha256':sha(workflow),'new_workflow_bytes':len(workflow),'under_500000_bytes':True,
 'source_files_exactly_original_21':True,'all_other_job_fields_and_steps_unchanged':True,
 'original_source_identity_check_unchanged':True,'original_hosted_bootstrap_and_owned_harness_unchanged':True,
 'original_two_jobs_and_original_to_current_dependency_unchanged':True,'original_permissions_unchanged':True,
 'original_native_source_and_resources_unchanged':True,'bash_blocks_parsed':bash_count,'inline_python_3_10_blocks_parsed':inline_count,
 'native_or_geometry_pass_claimed':False}
write_json('L5A_STATIC_CHECK.json',checks)
readme="""# L5a：首轮 workflow 大小先决失败后的源码装载窄修

首轮 L5 run 40287815678 在 GitHub 解析阶段拒绝 660,075 B 的 workflow；实际提示为 500 KB 上限，0 job、0 check run、0 artifact、0 native CAD。原始失败单独保存在 L5_FIRST_RUN_WORKFLOW_VALIDATION_FAILURE.json。该失败没有产生任何原七例或当前七例的几何结果。

本次仅替换两份 prepare 块中重复的 21 个源码 heredoc。下载固定已发表 commit b3c9bef2abe0d7065063bc966ec2083616286bd5 下同仓库的 21 个公开源码/绑定/说明文件；每项精确 bytes 与 SHA-256 匹配后写入原外部 HOST_ROOT/l5 和 CASE_DIR/source/l5。无凭据、拒绝重定向、单请求 15 s、整段 90 s 加 5 s TERM 清理；原 2220 s 外部期限和 40 min job 期限仍包含这段时间，不增加任何预算。完整下载总字节和本地实际公开源读回时钟在 L5A_SOURCE_TRANSPORT_BINDING.json。

原 21 文件逐字节保留，S4 checkout、owned supervisor、host-cap/service-launch、native producer、两个 reader、所有控制、原 1e-7 整对和门、1800 s / 1536 MiB 及磁盘/共享内存/安装守卫全部不变。original → current 两 job 顺序与先决不变。源码下载失败仍是准备失败，不能成为几何通过。

本次仍只处理原七个名义 [0,12] 区间及其原 spec 的独立 Z 范围。不覆盖完整 factory 的浮点容差薄层、真正左右独立域、K3 新 panel、完整 11,781 对或物理 G3–G5。

原算法说明和原科学源码位于 ../envelope-L5/。本修复没有重写任何原失败或产生新的 native 结果。GitHub 官方 workflow 上限依据：https://docs.github.com/en/actions/reference/limits#workflow-file-size
"""
(HERE/'README.md').write_text(readme)
paths=['L5_FIRST_RUN_WORKFLOW_VALIDATION_FAILURE.json','L5A_SOURCE_TRANSPORT_BINDING.json','L5A_STATIC_CHECK.json','README.md','build_l5a_transport.py']
target='engineering/engineering-integration-20261026/envelope-L5a/'
elements=[{'path':target+n,'mode':'100644','type':'blob','content':(HERE/n).read_text()} for n in paths]
elements.append({'path':'.github/workflows/s4-k1-l5-cylindrical.yml','mode':'100644','type':'blob','content':workflow.decode()})
request={'repository_full_name':'TrillionniumFoundation/RAZR-SLIDE','base_tree_sha':TREE,'tree_elements':elements}
req=write_json('L5A_PUBLIC_TREE_REQUEST.json',request)
mp=write_json('L5A_SAFE_INTEGRATION_MAPPING.json',{'entries':[{'local_path':str(wfpath if e['path'].startswith('.github/') else HERE/e['path'].rsplit('/',1)[1]),'repository_path':e['path'],'sha256':sha(e['content'].encode()),'bytes':len(e['content'].encode())} for e in elements]})
plan={'branch':'diagnostic/s4-k1-l5a-cylindrical-20261026','base_commit':COMMIT,'base_tree':TREE,'request_sha256':sha(req.read_bytes()),'workflow_sha256':sha(workflow),'mapping_sha256':sha(mp.read_bytes()),'changed_native_source_count':0,'source_count_reused_from_base_commit':21,'published':False}
write_json('L5A_PUBLICATION_PLAN.json',plan)
size=sum(p.stat().st_size for p in HERE.parent.rglob('*') if p.is_file());assert size<=500000,size
print(json.dumps({**plan,'workflow_bytes':len(workflow),'request_bytes':req.stat().st_size,'own_total_RAM_text_bytes':size,'bash_blocks':bash_count,'inline_python_blocks':inline_count,'actual_download_seconds':elapsed}))
