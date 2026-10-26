import datetime,json,os
from pathlib import Path
procs=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  if (p/'comm').read_text().strip()!='adb':continue
  args=(p/'cmdline').read_bytes().decode(errors='replace').strip('\0').split('\0')
  selected={}
  for pair in (p/'environ').read_bytes().split(b'\0'):
   k,_,v=pair.partition(b'=')
   if k.decode(errors='ignore') in ['ADB_SERVER_SOCKET','ANDROID_ADB_SERVER_PORT','ADB_SERVER_PORT','ADB_LIBUSB','ADB_VENDOR_KEYS']:
    selected[k.decode()]=v.decode(errors='replace')
  procs.append({'pid':int(p.name),'args':args,'selected_environment':selected,'executable':str((p/'exe').resolve())})
 except (OSError,PermissionError):pass
print(json.dumps({'host_alias':'pocket4','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'adb_servers':procs}))
