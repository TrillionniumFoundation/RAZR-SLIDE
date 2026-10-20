import datetime,hashlib,json,shutil,subprocess
from pathlib import Path
def read(p):
 try:return p.read_text().strip()
 except (OSError,UnicodeError):return None
def run(cmd):
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
  return {'command':cmd,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
 except Exception as e:return {'command':cmd,'error':type(e).__name__}
usb=[]
for p in sorted(Path('/sys/bus/usb/devices').glob('*')):
 vid=read(p/'idVendor');pid=read(p/'idProduct')
 if vid and pid:usb.append({'vendor_id':vid,'product_id':pid,'manufacturer':read(p/'manufacturer'),'product':read(p/'product'),'serial_sha256':hashlib.sha256((read(p/'serial') or '').encode()).hexdigest() if read(p/'serial') else None})
candidates=[shutil.which('adb'),'/opt/android-sdk/platform-tools/adb','/usr/bin/adb',str(Path.home()/'Android/Sdk/platform-tools/adb')]
adb=next((x for x in candidates if x and Path(x).is_file()),None)
result={'host_alias':'pocket4','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'usb_devices':usb,'adb_executable':adb,'read_only_observation':True,'phone_function_verified':False}
if adb:
 raw=run([adb,'devices','-l']); inv=[]; readable=[]
 for line in raw.get('stdout','').splitlines():
  cols=line.split()
  if not cols or line.startswith('List of') or line.startswith('*'):continue
  if len(cols)<2:continue
  serial,state=cols[:2]
  row={'serial_sha256':hashlib.sha256(serial.encode()).hexdigest(),'state':state,'details':' '.join(cols[2:])}
  if state=='device':
   prop=run([adb,'-s',serial,'shell','getprop','ro.product.manufacturer'])
   row['manufacturer_result']={k:v for k,v in prop.items() if k!='command'}
   if prop.get('returncode')==0 and prop.get('stdout','').strip().lower()=='motorola':
    values={}
    for name in ['ro.product.model','ro.product.device','ro.product.board','ro.hardware','ro.boot.hardware.sku','ro.build.fingerprint','ro.build.version.release','ro.build.version.security_patch']:
     q=run([adb,'-s',serial,'shell','getprop',name]);values[name]={k:v for k,v in q.items() if k!='command'}
    row['motorola_identity_properties']=values
    readable.append(row['serial_sha256'])
  inv.append(row)
 result.update(adb_inventory=inv,adb_devices_returncode=raw.get('returncode'),adb_devices_error=raw.get('error'),adb_devices_stderr=raw.get('stderr'),authorized_motorola_count=len(readable))
print(json.dumps(result,ensure_ascii=False))
