"""D6 external harness: real readonly service view and owned subreaper lifecycle.
No S4/original source edits; all task-owned evidence stays outside the checkout.
"""
import ctypes, errno, hashlib, importlib.util, json, os, pathlib, re, select, secrets, shutil, signal, subprocess, sys, time
P = pathlib.Path
SCRIPT = P(__file__).resolve()
INTERNAL = len(sys.argv) > 1 and sys.argv[1] in ('--private-root', '--inside', '--signal-check')
if INTERNAL:
    MODE = sys.argv[1][2:]
    OUT = P(sys.argv[2]).resolve()
    REPO = P(sys.argv[3]).resolve() if len(sys.argv) > 3 else P(os.environ['GITHUB_WORKSPACE']).resolve()
    TARGET = None; COMMAND = []
else:
    MODE = 'outside'; TARGET = P(sys.argv[1]).resolve(); COMMAND = sys.argv[2:]
    OUT = TARGET.with_name(TARGET.name+'.namespace'); REPO = P(os.environ['GITHUB_WORKSPACE']).resolve()
if MODE in ('outside', 'signal-check'):
    OUT.mkdir(parents=True, exist_ok=False)
RAW = OUT/'raw'; RAW.mkdir(exist_ok=True)
S4 = 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
SUP_REL = 'engineering/engineering-integration-20261025/numerics/run_bounded.py'
SUP_SHA = '901654cdb718a988471a700b01bfbb2e8979a98248c9211fa69d42b25279e56e'
ARCH_REL = 'engineering/gate-closure-20261023/geometry-followon-042b7689/key-v4-readback-algebra/results.tar.gz'
ARCH_SHA = 'beef1cf45fb49417c6af092fec51fb266fd6e89f238410c8cf137af4c20ce442'
V4_MEMBER = 'gates_audit/dev/key-endpoint-v4/run_key_endpoint_trials.py'
V4_SHA = 'ecd57df70e7df83e42083b6019e3b84da261c486c8c9681909a4b192b4505dad'
CONTROL_KEYS = ('anon', 'shmem', 'kernel_stack', 'pagetables', 'sock', 'slab_unreclaimable')
V4_KEYS = ('inactive_file', 'file_dirty', 'file_writeback', 'file', 'shmem')
FINITE_KEYS = ('anon', 'shmem', 'kernel', 'slab_reclaimable', 'unevictable')
NS_KEYS = ('mnt', 'pid', 'pid_for_children', 'user', 'cgroup')
def require(value, message):
    if not value: raise RuntimeError(message)
def sha(path): return hashlib.sha256(P(path).read_bytes()).hexdigest()
def save(name, value):
    final=OUT/name; temporary=final.with_name(final.name+'.tmp-'+str(os.getpid()))
    temporary.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');os.replace(temporary,final)
def ident(path):
    path = P(path); s = path.stat()
    return {'path': str(path), 'device': s.st_dev, 'inode': s.st_ino, 'mode': s.st_mode, 'symlink': path.is_symlink()}
def same_inode(a, b): return (a['device'], a['inode']) == (b['device'], b['inode'])
def capture(label, path):
    r = {'path': str(path), 'epoch': time.time(), 'readable': False}
    try:
        r['identity'] = ident(path)
        data = P(path).read_bytes(); r.update(readable=True, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        (RAW/(label+'.txt')).write_bytes(data)
        r['text'] = data.decode('utf-8', errors='strict')
    except (OSError, UnicodeError) as e: r['error'] = type(e).__name__+': '+str(e)
    return r
def require_text(r):
    require(r['readable'], 'required real interface unavailable: '+r['path']+' '+r.get('error', ''))
    require(not r['identity']['symlink'], 'interface symlink rejected')
    return r['text']
def proc(label, pid='self'):
    base = P('/proc')/str(pid)
    records = {k: capture(label+'-'+k, base/k) for k in ('cgroup', 'mountinfo', 'status', 'stat')}
    status = dict(line.split(':', 1) for line in require_text(records['status']).splitlines() if ':' in line)
    ns = {k: os.readlink(base/'ns'/k) for k in NS_KEYS}
    return {'epoch': time.time(), 'pid': os.getpid() if pid == 'self' else int(pid), 'records': records, 'status': status, 'namespaces': ns}
def unescape(s): return re.sub(r'\\([0-7]{3})', lambda m: chr(int(m.group(1), 8)), s)
def mounts(text):
    result = []
    for line in text.splitlines():
        a, b = line.split(' - ', 1); left, right = a.split(), b.split()
        result.append({'id': int(left[0]), 'root': unescape(left[3]), 'mountpoint': unescape(left[4]), 'options': left[5].split(','), 'optional': left[6:], 'fstype': right[0], 'source': unescape(right[1]), 'super_options': right[2].split(',')})
    return result
def group_path(text):
    rows = [line.split(':', 2) for line in text.splitlines() if line.startswith('0::')]
    require(len(rows) == 1, 'one real unified cgroup membership required')
    path = P(rows[0][2]); require(path.is_absolute() and '..' not in path.parts and str(path) != '/', 'non-root current service cgroup required')
    return path
def measured(label, base):
    r = {'directory': ident(base), 'epoch': time.time(), 'files': {k: capture(label+'-'+k, P(base)/k) for k in ('memory.stat', 'memory.current', 'memory.max', 'cgroup.type')}}
    save(label+'.json', r)
    values = dict((k, int(v)) for k, v in (line.split() for line in require_text(r['files']['memory.stat']).splitlines()))
    require(all(k in values for k in set(CONTROL_KEYS+V4_KEYS+FINITE_KEYS)), 'real memory.stat missing required counters')
    require(all(v >= 0 for v in values.values()), 'negative memory.stat counter')
    current = int(require_text(r['files']['memory.current']).strip()); require(current >= 0, 'negative current')
    cap = require_text(r['files']['memory.max']).strip(); require(cap == 'max' or (cap.isdecimal() and int(cap) >= 0), 'invalid maximum')
    r.update(values=values, current=current, maximum=cap)
    save(label+'.json', r)
    return r
def member_identity_matches(old, new):
    require(same_inode(old['directory'], new['directory']), 'bound directory inode differs from actual service')
    for k in ('memory.stat', 'memory.current', 'memory.max'):
        require(same_inode(old['files'][k]['identity'], new['files'][k]['identity']), 'counter inode changed: '+k)
    require(old['maximum'] == new['maximum'], 'service memory.max changed')
def namespace_checks(snapshot, before, *, private):
    require((snapshot['namespaces']['mnt'] != before['namespaces']['mnt']) == private, 'unexpected mount namespace identity')
    require(all(snapshot['namespaces'][k] == before['namespaces'][k] for k in NS_KEYS if k != 'mnt'), 'PID/user/cgroup namespace changed')
    require(snapshot['records']['cgroup']['text'] == before['records']['cgroup']['text'], 'process moved to a different cgroup')
def run_record(label, argv, **kwargs):
    start = time.time()
    with (OUT/(label+'.stdout')).open('wb') as stdout, (OUT/(label+'.stderr')).open('wb') as stderr:
        r = subprocess.run(argv, stdout=stdout, stderr=stderr, **kwargs)
    rec = {'argv': argv, 'exit_code': r.returncode, 'seconds': time.time()-start, 'stdout_sha256': sha(OUT/(label+'.stdout')), 'stderr_sha256': sha(OUT/(label+'.stderr'))}
    save(label+'.json', rec)
    return r.returncode

EXPECTED_FIVE = {
 'integration/probe_key_endpoint_extension.py': 'a2f15dd4c9f41a9235e4c7625da52c9bf81add0260556d841e65c6261123408e',
 'tools/key_endpoint_resume.py': 'f9fa0e36cfdae30a24eab771c015b260d004573d60a23351bf266d1cb28cfb49',
 'run_key_endpoint_trials.py': V4_SHA,
 'tests/test_key_endpoint_extension.py': '3fe949b3a0036875946263bc5d6f97fce4d8555cc2c0b7d0686f263bbe99e60b',
 'tests/test_key_endpoint_resume.py': '6038b8ea4659bb3095f766d75ef54b1d607e1f3096ece816cb887fbaec3d0188',
}
SAFE_ENV_NAMES = ('PATH', 'HOME', 'USER', 'LOGNAME', 'SHELL', 'LANG', 'LC_ALL', 'LC_CTYPE', 'TZ',
 'TMPDIR', 'TMP', 'TEMP', 'LD_LIBRARY_PATH', 'SSL_CERT_FILE', 'SSL_CERT_DIR', 'REQUESTS_CA_BUNDLE',
 'CI', 'GITHUB_ACTIONS', 'GITHUB_WORKSPACE', 'GITHUB_SHA', 'GITHUB_JOB', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT',
 'RUNNER_TEMP', 'HOST_ROOT', 'HOST_JOB_START', 'CASE_DIR', 'CASE_KIND', 'CASE_KEY', 'S4',
 'PYTHONDONTWRITEBYTECODE', 'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS',
 'UV_PYTHON', 'UV_PYTHON_INSTALL_DIR', 'UV_PYTHON_PREFERENCE', 'UV_PYTHON_DOWNLOADS',
 'UV_PYTHON_DOWNLOADS_JSON_URL', 'UV_CACHE_DIR', 'UV_NO_SYNC', 'UV_PROJECT_ENVIRONMENT', 'UV_LINK_MODE',
 'UV_NO_CACHE', 'UV_COMPILE_BYTECODE', 'UV_NO_PROGRESS', 'UV_COLOR', 'UV_HTTP_TIMEOUT', 'UV_HTTP_RETRIES',
 'UV_MANAGED_PYTHON', 'RAZR_EXPECTED_SIGNAL_PROBE')
def proc_identity(pid, full=True):
    path=P('/proc')/str(pid); text=(path/'stat').read_text(); rest=text[text.rfind(')')+2:].split()
    status=dict(line.split(':',1) for line in (path/'status').read_text().splitlines() if ':' in line)
    result={'pid':int(pid),'ppid':int(rest[1]),'pgid':int(rest[2]),'sid':int(rest[3]),'state':rest[0],'start_ticks':int(rest[19]),'uid':int(status['Uid'].split()[0])}
    if full:
        result.update(cgroup=(path/'cgroup').read_text(),mnt_namespace=os.readlink(path/'ns/mnt'))
    return result
def bound_pidfd(identity, parent=None):
    require(hasattr(os,'pidfd_open') and hasattr(signal,'pidfd_send_signal'), 'real pidfd signal API unavailable')
    before=proc_identity(identity['pid'],full=False); require(before['start_ticks']==identity['start_ticks'], 'PID identity changed before pidfd binding')
    if parent is not None: require(before['ppid']==parent, 'process is not an actual owned child')
    fd=os.pidfd_open(identity['pid'],0)
    try:
        after=proc_identity(identity['pid'],full=False); require(after['start_ticks']==identity['start_ticks'] and after['uid']==os.getuid(), 'PID/UID changed while binding pidfd')
        if parent is not None: require(after['ppid']==parent, 'child lineage changed while binding pidfd')
        return fd
    except BaseException:
        os.close(fd); raise
def exited(fd): return bool(select.select([fd],[],[],0)[0])
def lineage_reaches(pid, ancestor):
    rows=[]; seen=set()
    while pid>1 and pid not in seen and len(rows)<64:
        seen.add(pid); r=proc_identity(pid,full=False); rows.append(r)
        if pid==ancestor['pid']:
            require(r['start_ticks']==ancestor['start_ticks'], 'owned launcher PID reused')
            return rows
        pid=r['ppid']
    raise RuntimeError('ready process is not a descendant of the actual owned launcher')
def children():
    path=P('/proc/self/task')/str(os.getpid())/'children'
    result=[]
    for value in path.read_text().split():
        try:
            r=proc_identity(int(value),full=False); require(r['ppid']==os.getpid(), 'kernel child list parent mismatch'); result.append(r)
        except FileNotFoundError:
            require(value not in path.read_text().split(), 'kernel still lists a child whose identity cannot be read; cleanup unknown')
    return result
def original_sources(state):
    require(subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()==S4, 'functional HEAD is not S4')
    require(subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--untracked-files=all'],text=True)=='', 'S4 checkout is dirty')
    require(sha(REPO/SUP_REL)==SUP_SHA, 'S4 original supervisor changed')
    study=P(state['environment']['HOST_ROOT'])/'original-v4'
    for name,digest in EXPECTED_FIVE.items(): require(sha(study/name)==digest, 'original five-source bytes differ: '+name)
    require(sha(SCRIPT)==state['harness_sha256'] and sha(state['host_cap'])==state['host_cap_sha256'], 'external harness source changed')
    metadata=P(state['environment'].get('UV_PYTHON_DOWNLOADS_JSON_URL',''))
    require(metadata==P(state['environment']['HOST_ROOT'])/'python-downloads.json' and metadata.is_file() and metadata.stat().st_size==552 and sha(metadata)=='a23c006d96b05012706707a5c0fc0bca87c17b4e362d5992a83795db914a5c56', 'official selected Python metadata bytes/path differ')
def validate_view(state, label):
    here=proc(label); save(label+'-process.json',here); namespace_checks(here,state['before'],private=True)
    require(os.getuid()==state['uid'] and os.geteuid()==state['uid'] and os.getgid()==state['gid'] and sorted(os.getgroups())==state['groups'],'original caller credentials not restored')
    require(here['status']['NoNewPrivs'].strip()=='1','no_new_privs missing')
    require(int(here['status']['CapEff'].strip(),16)&~int(state['before']['status']['CapEff'].strip(),16)==0,'capabilities increased')
    current=measured(label+'-service','/sys/fs/cgroup');member_identity_matches(state['service'],current)
    entries=mounts(here['records']['mountinfo']['text']); target=[m for m in entries if m['mountpoint']=='/sys/fs/cgroup'][-1]
    require(target['fstype']=='cgroup2' and target['root']==state['hierarchy_path'] and 'ro' in target['options'],'actual readonly service cgroup2 mount missing')
    require(not any(v.startswith(('shared:','master:','propagate_from:')) for m in entries for v in m['optional']),'mount propagation is not private')
    require(all(os.environ.get(k)==v for k,v in state['environment'].items()),'allowlisted original caller environment was not restored')
    actual_uv=shutil.which('uv')
    require(actual_uv==state['observed_uv_path'],'uv PATH changed across privilege transition')
    original_sources(state)
    return here,current

def private_root():
    state=json.loads((OUT/'prepared.json').read_text());require(os.geteuid()==0,'passwordless sudo root authority unavailable')
    here=proc('private-root-before-bind');save('private-root-before-bind.json',here);namespace_checks(here,state['before'],private=True)
    require(same_inode(ident(state['service_path']),state['service']['directory']),'real source service inode changed')
    for label,argv in [('make-rprivate',[state['tools']['mount'],'--make-rprivate','/']),('real-service-bind',[state['tools']['mount'],'--bind',state['service_path'],'/sys/fs/cgroup']),('readonly-bind',[state['tools']['mount'],'-o','remount,bind,ro','/sys/fs/cgroup'])]:
        require(run_record(label,argv,timeout=15)==0,'private mount failed: '+label)
    args=[state['tools']['setpriv'],'--reuid',str(state['uid']),'--regid',str(state['gid']),'--no-new-privs']
    args+=['--groups',','.join(map(str,state['groups']))] if state['groups'] else ['--clear-groups']
    args+=['/usr/bin/python3','-B',str(SCRIPT),'--inside',str(OUT),str(REPO)]
    # exec removes the privileged launcher; no root wait/timeout surrounds long CAD.
    os.execve(state['tools']['setpriv'],args,state['environment'])

def inside():
    state=json.loads((OUT/'prepared.json').read_text());os.chdir(state['cwd'])
    here,view=validate_view(state,'inside-before')
    spec=importlib.util.spec_from_file_location('original_v4_resources',P(state['environment']['HOST_ROOT'])/'original-v4/run_key_endpoint_trials.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);res=module.resources(P(state['target']).parent)
    values=view['values']; finite=values['anon']+values['shmem']+max(0,values['kernel']-values['slab_reclaimable'])+values['unevictable']
    save('original-resource-preflight.json',{'original_v4_resources':res,'control_nonreclaimable_bytes':sum(values[k] for k in CONTROL_KEYS),'finite_shared_bytes':finite,'observed_uv_path':shutil.which('uv'),'manager_python_executable':sys.executable,'scope':state['hierarchy_path']+' and descendants; not whole VM root','CAD_executed_by_preflight':False})
    require(res['writeable_disk_bytes']>=500*1024**2 and res['effective_memory_headroom_bytes']>=2*1024**3,'original measured disk/headroom prerequisites unavailable')
    require(res['shared_unreclaimable_memory_bytes']<=int(6.8*1024**3) and sum(values[k] for k in CONTROL_KEYS)<=6.8*1024**3,'original memory budget unavailable')
    if state['environment'].get('CASE_KIND')=='orthogonal': require(finite+2*1024**3<=6.8*1024**3,'original finite startup memory prerequisite unavailable')
    for a in state['ancestors']:
        if a['is_cgroup_root'] or a['path']==state['service_path']:continue
        maximum=require_text(a['maximum']).strip();current=int(require_text(a['current']).strip())
        require(current>=0 and (maximum=='max' or maximum.isdecimal()),'unknown ancestor measurement')
        if maximum!='max':require(int(maximum)-current>=res['effective_memory_headroom_bytes'],'a proper ancestor has tighter finite headroom; blocked')
    libc=ctypes.CDLL(None,use_errno=True)
    require(libc.prctl(36,1,0,0,0)==0,'PR_SET_CHILD_SUBREAPER failed')
    flag=ctypes.c_int();require(libc.prctl(37,ctypes.byref(flag),0,0,0)==0 and flag.value==1,'subreaper flag did not become effective')
    require(not children(),'manager already owns unexpected children before launch')
    got=[]
    def received(signum,frame):got.append({'signal':signum,'epoch':time.time()})
    signal.signal(signal.SIGINT,received);signal.signal(signal.SIGTERM,received)
    me=proc_identity(os.getpid());ready={'nonce':state['nonce'],'identity':me,'namespace':here['namespaces'],'uid':os.getuid(),'subreaper':True,'harness_sha256':sha(SCRIPT),'epoch':time.time()}
    save('manager-ready.json',ready)
    wait_end=time.monotonic()+15
    while not (OUT/'manager-authorized.json').is_file():
        require(not got,'interrupted before owned pidfd authorization');require(time.monotonic()<wait_end,'outer owned pidfd authorization missing');time.sleep(.05)
    authorized=json.loads((OUT/'manager-authorized.json').read_text());require(authorized['nonce']==state['nonce'] and authorized['manager_start_ticks']==me['start_ticks'],'authorization identity mismatch')
    receipt={'scope':state['hierarchy_path']+' and descendants; not whole VM root','manager_identity':me,'subreaper':True,'received_signals':got,'owned_signals':[],'reaped_children':[],'adopted_descendant_cleanup_required':False,'forced_cleanup':False,'cleanup_verified':False,'normal_command_completed':False,'expected_signal_probe':state['expected_signal_probe'],'started_epoch':time.time()}
    cap=None;cap_fd=None;exit_code=2;signal_sent=False;stop_started=None
    def send_owned(identity,sig,reason):
        fd=bound_pidfd(identity,parent=os.getpid())
        try:
            if not exited(fd):signal.pidfd_send_signal(fd,sig)
            receipt['owned_signals'].append({'identity':identity,'signal':sig,'reason':reason,'epoch':time.time(),'method':'kernel pidfd, actual direct PPid and start_ticks checked'})
        finally:os.close(fd)
    def reap_adopted():
        remaining=[]
        for r in children():
            if cap is not None and r['pid']==cap.pid:continue
            try:
                pid,status=os.waitpid(r['pid'],os.WNOHANG)
                if pid:receipt['reaped_children'].append({'identity':r,'wait_status':status,'epoch':time.time()})
                else:remaining.append(r)
            except ChildProcessError:pass
        return remaining
    try:
        args=['/usr/bin/python3','-B',state['host_cap'],state['target'],*state['command']]
        cap=subprocess.Popen(args,start_new_session=True)
        owned=proc_identity(cap.pid);require(owned['ppid']==os.getpid() and owned['uid']==state['uid'] and owned['mnt_namespace']==me['mnt_namespace'] and owned['cgroup']==me['cgroup'],'host-cap identity did not inherit exact service/UID namespace')
        cap_fd=bound_pidfd(owned,parent=os.getpid());receipt['host_cap_identity']=owned;receipt['host_cap_argv']=args
        final_manager_deadline=float(state['environment']['HOST_JOB_START'])+3270
        while cap.poll() is None:
            if got or time.time()>=final_manager_deadline:
                if not signal_sent:
                    signal.pidfd_send_signal(cap_fd,signal.SIGINT);signal_sent=True;stop_started=time.monotonic()
                    receipt['owned_signals'].append({'identity':owned,'signal':signal.SIGINT,'reason':'external INT/TERM or manager deadline mapped to host-cap cleanup','epoch':time.time(),'method':'bound owned Popen pidfd'})
                elif time.monotonic()-stop_started>30:
                    receipt['forced_cleanup']=True;signal.pidfd_send_signal(cap_fd,signal.SIGKILL)
                    break
            time.sleep(.1)
        if cap.poll() is None:
            try:cap.wait(timeout=5)
            except subprocess.TimeoutExpired:receipt['host_cap_exit_unknown']=True
        else:cap.wait()
        receipt['host_cap_exit_code']=cap.returncode
        adopted=reap_adopted()
        if adopted:
            receipt['adopted_descendant_cleanup_required']=True
            # Only actual children adopted by THIS subreaper may be signalled.
            deadline=time.monotonic()+10;sent={}
            while adopted and time.monotonic()<deadline:
                for r in adopted:
                    key=(r['pid'],r['start_ticks']);first=sent.get(key)
                    if first is None:
                        send_owned(r,signal.SIGINT,'adopted residual after original cleanup; run fails');sent[key]=time.monotonic()
                    elif time.monotonic()-first>2:
                        receipt['forced_cleanup']=True;send_owned(r,signal.SIGKILL,'adopted residual did not exit after SIGINT')
                time.sleep(.1);adopted=reap_adopted()
            receipt['unexited_owned_children']=adopted
        remaining=children();receipt['remaining_actual_children']=remaining
        receipt['cleanup_verified']=cap.returncode is not None and exited(cap_fd) and not remaining
        require(receipt['cleanup_verified'],'owned process cleanup is unknown/incomplete')
        require(not receipt['adopted_descendant_cleanup_required'] and not receipt['forced_cleanup'],'residual/forced cleanup means failed command, never pass')
        validate_view(state,'inside-after');original_sources(state)
        receipt['normal_command_completed']=cap.returncode==0 and not got and not signal_sent
        exit_code=cap.returncode if receipt['normal_command_completed'] else 2
        if exit_code<0:exit_code=128-exit_code
    except BaseException as exc:
        receipt['failure']=type(exc).__name__+': '+str(exc)
        if cap is not None and cap.poll() is None:
            try:
                if cap_fd is not None:signal.pidfd_send_signal(cap_fd,signal.SIGINT)
                else:cap.send_signal(signal.SIGINT)
                cap.wait(timeout=25)
            except BaseException as cleanup:receipt['exception_cleanup_error']=type(cleanup).__name__+': '+str(cleanup)
        # Do not claim cleanup from a parent exit. Reap/signals are limited to actual direct children.
        end=time.monotonic()+10
        while children() and time.monotonic()<end:
            for r in children():
                if cap is not None and r['pid']==cap.pid:
                    if cap.poll() is None:
                        receipt['forced_cleanup']=True
                        try:send_owned(r,signal.SIGKILL,'exception cleanup of owned host-cap')
                        except ProcessLookupError:pass
                    continue
                receipt['adopted_descendant_cleanup_required']=True;receipt['forced_cleanup']=True
                try:send_owned(r,signal.SIGKILL,'exception cleanup of actual adopted descendant')
                except ProcessLookupError:pass
            if cap is not None:cap.poll()
            reap_adopted();time.sleep(.1)
        receipt['remaining_actual_children']=children();receipt['cleanup_verified']=not receipt['remaining_actual_children'] and (cap is None or cap.poll() is not None)
    finally:
        if cap_fd is not None:os.close(cap_fd)
        receipt.update(exit_code=exit_code,finished_epoch=time.time())
        save('manager-result.json',receipt)
        unsafe=not receipt['cleanup_verified'] or receipt['forced_cleanup'] or receipt['adopted_descendant_cleanup_required']
        if unsafe or (got and not state['expected_signal_probe']):
            P(state['environment']['CASE_DIR'],'namespace-lifecycle-block.json').write_text(json.dumps({'blocked':True,'receipt':str(OUT/'manager-result.json'),'reason':'interrupted production command or incomplete/forced/adopted cleanup; later native commands forbidden'},indent=2)+'\n')
    return exit_code

def outside():
    before=proc('host-before');save('host-before.json',before)
    summary={'schema':'razr-D6-private-service-launch','functional_candidate':S4,'command':COMMAND,'compatibility_verified':False,'cleanup_verified':False,'command_exit_code':None,'private_root_Python_launcher_execs_original_UID_manager':True,'started_epoch':time.time()}
    child=None;manager_fd=None;requested=[]
    def handler(signum,frame):requested.append({'signal':signum,'epoch':time.time()})
    signal.signal(signal.SIGINT,handler);signal.signal(signal.SIGTERM,handler)
    try:
        require(COMMAND,'command required')
        env={k:os.environ[k] for k in SAFE_ENV_NAMES if k in os.environ};require(all(k in env for k in ('PATH','HOME','HOST_JOB_START','HOST_ROOT','CASE_DIR','S4')),'required allowlisted caller environment missing')
        require(not (P(env['CASE_DIR'])/'namespace-lifecycle-block.json').exists(),'previous lifecycle failure blocks this job')
        expected_signal=env.get('RAZR_EXPECTED_SIGNAL_PROBE')
        require(expected_signal in (None,'SIGINT','SIGTERM'),'unknown lifecycle probe marker')
        if expected_signal:
            require(str(REPO/SUP_REL) in COMMAND and '--seconds' in COMMAND and COMMAND[COMMAND.index('--seconds')+1]=='30','signal probe exception only applies to short original supervisor')
        command=list(COMMAND)
        if '/' not in command[0]:
            command[0]=shutil.which(command[0],path=env['PATH']);require(command[0],'executable unavailable on original caller PATH')
        membership=group_path(before['records']['cgroup']['text']);candidates=[m for m in mounts(before['records']['mountinfo']['text']) if m['fstype']=='cgroup2' and membership.is_relative_to(P(m['root']))]
        require(candidates,'no genuine cgroup2 mount covers this job');mount=max(candidates,key=lambda m:len(P(m['root']).parts))
        service=P(mount['mountpoint'])/membership.relative_to(P(mount['root']));require(service.resolve()==service and not service.is_symlink(),'service path resolution changed')
        measured_before=measured('host-service-before',service);ancestors=[];current=service
        while True:
            item={'path':str(current),'identity':ident(current),'is_cgroup_root':current==P(mount['mountpoint']),'maximum':capture('ancestor-'+str(len(ancestors))+'-memory.max',current/'memory.max'),'current':capture('ancestor-'+str(len(ancestors))+'-memory.current',current/'memory.current')};ancestors.append(item)
            if item['is_cgroup_root']:break
            require(current.parent!=current and current.parent.is_relative_to(P(mount['mountpoint'])),'invalid real ancestry');current=current.parent
        tools={k:shutil.which(k) for k in ('sudo','unshare','mount','setpriv')};require(all(tools.values()),'existing namespace/drop tools unavailable; no fallback')
        state={'nonce':secrets.token_hex(32),'before':before,'uid':os.getuid(),'gid':os.getgid(),'groups':sorted(os.getgroups()),'cwd':os.getcwd(),'hierarchy_path':str(membership),'service_path':str(service),'service':measured_before,'ancestors':ancestors,'root_directory':ident('/sys/fs/cgroup'),'root_memory_stat':capture('host-root-memory.stat','/sys/fs/cgroup/memory.stat'),'host_meminfo':capture('host-meminfo','/proc/meminfo'),'tools':tools,'environment':env,'harness_sha256':sha(SCRIPT),'host_cap':str(P(env['HOST_ROOT'])/'host-cap.py'),'host_cap_sha256':sha(P(env['HOST_ROOT'])/'host-cap.py'),'target':str(TARGET),'command':command,'expected_signal_probe':expected_signal,'observed_uv_path':shutil.which('uv',path=env['PATH'])}
        require(state['uid']!=0,'launcher must begin as original unprivileged runner');original_sources(state);save('prepared.json',state)
        args=[tools['sudo'],'-n',tools['unshare'],'--mount','--propagation','private','--','/usr/bin/python3','-B',str(SCRIPT),'--private-root',str(OUT),str(REPO)]
        with (OUT/'namespace.stdout').open('wb') as log,(OUT/'namespace.stderr').open('wb') as err:
            child=subprocess.Popen(args,stdout=log,stderr=err,start_new_session=True);owned=proc_identity(child.pid,full=False);save('owned-namespace-launcher.json',{'argv':args,'identity':owned})
            sent_count=0;early_sent=False
            while child.poll() is None:
                ready=OUT/'manager-ready.json'
                if manager_fd is None and ready.is_file():
                    r=json.loads(ready.read_text());require(r['nonce']==state['nonce'] and r['harness_sha256']==state['harness_sha256'] and r['subreaper'] is True,'manager readiness provenance mismatch')
                    rows=lineage_reaches(r['identity']['pid'],owned);require(r['uid']==state['uid'],'manager UID mismatch')
                    manager_fd=bound_pidfd(r['identity']);save('verified-owned-manager-lineage.json',{'lineage':rows,'identity':r['identity'],'signal_method':'pidfd','nonce':state['nonce']})
                    save('manager-authorized.json',{'nonce':state['nonce'],'manager_start_ticks':r['identity']['start_ticks'],'outer_pid':os.getpid(),'epoch':time.time()})
                if requested:
                    if manager_fd is not None and len(requested)>sent_count:
                        if not exited(manager_fd):signal.pidfd_send_signal(manager_fd,signal.SIGINT)
                        sent_count=len(requested)
                    elif manager_fd is None and not early_sent:
                        # No heavy command can start before pidfd authorization. This is only setup cancellation.
                        child.send_signal(signal.SIGINT);early_sent=True
                time.sleep(.1)
            code=child.wait();summary['namespace_launcher_exit_code']=code
        require(manager_fd is not None,'manager never reached owned pidfd authorization')
        require(exited(manager_fd),'manager identity still alive after launcher exit')
        result=json.loads((OUT/'manager-result.json').read_text());summary['manager_result']=result;summary['cleanup_verified']=result['cleanup_verified'];summary['command_exit_code']=result['host_cap_exit_code'] if 'host_cap_exit_code' in result else None
        after=proc('host-after');save('host-after.json',after);namespace_checks(after,before,private=False)
        require(after['records']['mountinfo']['text']==before['records']['mountinfo']['text'],'host global mount view changed')
        require(same_inode(ident('/sys/fs/cgroup'),state['root_directory']),'host root inode changed')
        measured_after=measured('host-service-after',service);member_identity_matches(measured_before,measured_after)
        for i,a in enumerate(ancestors):
            post=capture('ancestor-'+str(i)+'-memory.max-after',P(a['path'])/'memory.max');save('ancestor-'+str(i)+'-after.json',post)
            require(a['maximum']['readable']==post['readable'],'ancestor maximum availability changed')
            if post['readable']:require(post['text']==a['maximum']['text'] and same_inode(post['identity'],a['maximum']['identity']),'ancestor maximum changed')
        original_sources(state);summary['compatibility_verified']=True
        require(result['cleanup_verified'] and not result['forced_cleanup'] and not result['adopted_descendant_cleanup_required'],'owned cleanup did not finish through normal original path')
        summary['normal_command_completed']=result['normal_command_completed'];summary['exit_code']=code if code>=0 else 128-code
    except BaseException as exc:
        summary['failure']=type(exc).__name__+': '+str(exc);summary['exit_code']=2
        if child is not None and child.poll() is None:
            # Never kill only sudo/namespace parent and claim descendants are gone.
            if manager_fd is not None and not exited(manager_fd):signal.pidfd_send_signal(manager_fd,signal.SIGINT)
            else:child.send_signal(signal.SIGINT)
            try:child.wait(timeout=60)
            except subprocess.TimeoutExpired:summary['cleanup_unknown']=True
        if not summary.get('cleanup_verified'):
            P(os.environ['CASE_DIR'],'namespace-lifecycle-block.json').write_text(json.dumps({'blocked':True,'receipt':str(OUT/'SUMMARY.json'),'reason':'outer failure or cleanup unknown; later native commands forbidden'},indent=2)+'\n')
    finally:
        if manager_fd is not None:os.close(manager_fd)
        summary.update(external_signals=requested,finished_epoch=time.time());save('SUMMARY.json',summary)
    return summary['exit_code']

def signal_check():
    result={'schema':'razr-D6-nonCAD-signal-chain-check','passed':False,'native_CAD_executed':False,'original_source_sha256':SUP_SHA,'tests':[]}
    sentinel=None;sentinel_fd=None
    try:
        require(sha(REPO/SUP_REL)==SUP_SHA,'original supervisor source mismatch')
        sentinel=subprocess.Popen(['/usr/bin/python3','-B','-c','import time; time.sleep(120)'],start_new_session=True)
        sentinel_identity=proc_identity(sentinel.pid);sentinel_fd=bound_pidfd(sentinel_identity,parent=os.getpid());result['unrelated_to_namespace_branch_sentinel']=sentinel_identity
        worker=OUT/'stdlib-worker.py'
        worker.write_text("import json,os,pathlib,sys,time\np=pathlib.Path('/proc/self');t=(p/'stat').read_text();r=t[t.rfind(')')+2:].split();record={'pid':os.getpid(),'ppid':os.getppid(),'pgid':os.getpgid(0),'sid':os.getsid(0),'uid':os.getuid(),'start_ticks':int(r[19]),'cgroup':(p/'cgroup').read_text(),'mnt_namespace':os.readlink(p/'ns/mnt')}\ntarget=pathlib.Path(sys.argv[1]);temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(record,indent=2)+'\\n');os.replace(temporary,target)\ntime.sleep(60)\n")
        for sig in (signal.SIGINT,signal.SIGTERM):
            name=signal.Signals(sig).name;folder=OUT/name;folder.mkdir();task=folder/'task';task.mkdir();identity_file=folder/'worker-ready.json'
            target=folder/'host-cap';cmd=['/usr/bin/python3','-B',str(SCRIPT),str(target),'/usr/bin/python3','-B',str(REPO/SUP_REL),'--task-directory',str(task),'--seconds','30','--log',str(folder/'original-child.log'),'--report',str(folder/'original-supervisor-report.json'),'--','/usr/bin/python3','-B',str(worker),str(identity_file)]
            env=os.environ.copy();env['RAZR_EXPECTED_SIGNAL_PROBE']=name
            launch=None;worker_fd=None;sup_fd=None;row={'signal_to_outer':name,'passed':False,'cleanup_unknown':False}
            try:
                with (folder/'outer.stdout').open('wb') as log,(folder/'outer.stderr').open('wb') as err:
                    launch=subprocess.Popen(cmd,env=env,stdout=log,stderr=err,start_new_session=True);launch_identity=proc_identity(launch.pid,full=False);row['owned_outer_identity']=launch_identity;deadline=time.monotonic()+20
                    while not identity_file.is_file() and launch.poll() is None and time.monotonic()<deadline:time.sleep(.05)
                    require(identity_file.is_file(),'short real signal worker did not start')
                    wi=json.loads(identity_file.read_text());lineage=lineage_reaches(wi['pid'],launch_identity);worker_fd=bound_pidfd(wi);sup_identity=proc_identity(wi['ppid']);sup_fd=bound_pidfd(sup_identity)
                    require(wi['sid']==wi['pid'] and wi['pgid']==wi['pid'],'original supervisor child is not an independent session')
                    time.sleep(.25);launch.send_signal(sig)
                    try:code=launch.wait(timeout=45)
                    except subprocess.TimeoutExpired:raise RuntimeError('owned signal chain did not finish; no install/CAD permitted')
                    require(exited(worker_fd) and exited(sup_fd),'actual original controller/independent-session worker did not exit')
                    require(not exited(sentinel_fd),'signal affected the separate non-namespace branch sentinel')
                    ns=target.with_name(target.name+'.namespace');summ=json.loads((ns/'SUMMARY.json').read_text());mr=json.loads((ns/'manager-result.json').read_text());original=json.loads((folder/'original-supervisor-report.json').read_text());host=json.loads(target.with_suffix('.json').read_text())
                    require(code!=0 and summ['compatibility_verified'] and summ['cleanup_verified'] and mr['cleanup_verified'] and not mr['forced_cleanup'] and not mr['adopted_descendant_cleanup_required'],'expected signal did not take the clean original path')
                    require(mr['received_signals'] and original['resource_stop_reason']=='supervisor_failure' and original['supervisor_error']['type']=='KeyboardInterrupt' and original['supervisor_source_unchanged'] and original['supervisor_source_sha256']==SUP_SHA,'original supervisor INT/finally receipt is missing')
                    require(host['failure'].startswith('KeyboardInterrupt'),'host-cap did not enter its original cleanup exception path')
                    row.update(passed=True,exit_code=code,worker_identity=wi,supervisor_identity=sup_identity,lineage=lineage,both_bound_pidfds_exited=True,unrelated_sentinel_unaffected=True,forced_or_adopted_cleanup=False,original_supervisor_report_sha256=sha(folder/'original-supervisor-report.json'),namespace_summary_sha256=sha(ns/'SUMMARY.json'))
                    result['tests'].append(dict(row))
            except BaseException as exc:
                row['failure']=type(exc).__name__+': '+str(exc)
                raise
            finally:
                # Every early failure keeps ownership and requests the same cleanup route.
                if launch is not None and launch.poll() is None:
                    row['early_failure_cleanup_requested']=True
                    try:
                        launch.send_signal(signal.SIGINT);launch.wait(timeout=45)
                    except BaseException as cleanup:
                        row['cleanup_unknown']=True;row['cleanup_error']=type(cleanup).__name__+': '+str(cleanup)
                if launch is not None:row['actual_outer_exit_code']=launch.poll()
                for label,fd in (('worker',worker_fd),('original_supervisor',sup_fd)):
                    if fd is not None:
                        row[label+'_pidfd_exited_at_finally']=exited(fd)
                        if not row[label+'_pidfd_exited_at_finally']:row['cleanup_unknown']=True
                        os.close(fd)
                save('signal-'+name+'-final.json',row)
                if row['cleanup_unknown']:
                    P(os.environ['CASE_DIR'],'namespace-lifecycle-block.json').write_text(json.dumps({'blocked':True,'reason':'signal probe owned branch cleanup unknown; install/CAD forbidden'},indent=2)+'\n')
        require(len(result['tests'])==2,'both INT and TERM chain tests required');result['passed']=True
    except BaseException as exc:
        result['failure']=type(exc).__name__+': '+str(exc)
        P(os.environ['CASE_DIR'],'namespace-lifecycle-block.json').write_text(json.dumps({'blocked':True,'reason':'nonCAD real signal-chain self-check failed; no install/CAD'},indent=2)+'\n')
    finally:
        if sentinel is not None:
            if sentinel.poll() is None:sentinel.terminate()
            try:sentinel.wait(timeout=5)
            except subprocess.TimeoutExpired:sentinel.kill();sentinel.wait()
        if sentinel_fd is not None:os.close(sentinel_fd)
        result['finished_epoch']=time.time();save('SIGNAL_CHECK.json',result)
    return 0 if result['passed'] else 2
try:
    if MODE=='outside':code=outside()
    elif MODE=='private-root':private_root();code=2
    elif MODE=='inside':code=inside()
    elif MODE=='signal-check':code=signal_check()
    else:raise RuntimeError('unknown mode')
except BaseException as exc:
    save(MODE+'-ERROR.json',{'error':type(exc).__name__+': '+str(exc),'epoch':time.time()});raise
raise SystemExit(code)
