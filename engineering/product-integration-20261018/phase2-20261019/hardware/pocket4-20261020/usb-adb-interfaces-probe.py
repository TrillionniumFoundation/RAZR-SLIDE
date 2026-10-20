import json,os,shutil,stat,subprocess,datetime
from pathlib import Path
def read(p):
 try:return p.read_text().strip()
 except (OSError,UnicodeError):return None
def run(cmd):
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=12)
  return {'command':cmd,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
 except Exception as e:return {'command':cmd,'error':type(e).__name__}
details=[]
for p in Path('/sys/bus/usb/devices').glob('*'):
 if read(p/'idVendor')=='22b8':
  bus=read(p/'busnum');dev=read(p/'devnum');node=Path('/dev/bus/usb')/str(bus).zfill(3)/str(dev).zfill(3)
  rows=[]
  for q in p.glob(p.name+':*'):
   rows.append({'interface':q.name,**{k:read(q/k) for k in ['bInterfaceClass','bInterfaceSubClass','bInterfaceProtocol','interface']}})
  ns=node.stat() if node.exists() else None
  details.append({'sysfs':str(p),'configuration':read(p/'bConfigurationValue'),'interfaces':rows,'device_node':str(node),'mode':oct(stat.S_IMODE(ns.st_mode)) if ns else None,'uid':ns.st_uid if ns else None,'gid':ns.st_gid if ns else None,'readable':os.access(node,os.R_OK),'writable':os.access(node,os.W_OK)})
bins=[]
seen=set()
for item in [shutil.which('adb'),'/usr/bin/adb','/opt/android-sdk/platform-tools/adb',str(Path.home()/'Android/Sdk/platform-tools/adb')]:
 if item and Path(item).is_file() and item not in seen:
  seen.add(item);p=Path(item);header=p.open('rb').read(160)
  bins.append({'path':str(p),'resolved':str(p.resolve()),'kind':'ELF' if header.startswith(b'\x7fELF') else 'script_or_other','version':run([item,'version'])})
selected={k:os.environ.get(k) for k in ['ADB_SERVER_SOCKET','ANDROID_ADB_SERVER_PORT','ADB_VENDOR_KEYS'] if os.environ.get(k)}
procs=[]
for p in Path('/proc').glob('[0-9]*'):
 if read(p/'comm')=='adb':
  try:procs.append({'pid':int(p.name),'executable':str((p/'exe').resolve())})
  except OSError:pass
print(json.dumps({'host_alias':'pocket4','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'usb_interfaces':details,'adb_binaries':bins,'selected_adb_env':selected,'adb_processes':procs},ensure_ascii=False))
