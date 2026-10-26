import datetime,hashlib,json,subprocess
ADB='/home/alex/.local/opt/razr-adb-37/adb'
PORT='5061'
def run(args):
 p=subprocess.run([ADB,'-P',PORT,*args],capture_output=True,text=True,timeout=20)
 return {'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
raw=run(['devices','-l']);inventory=[];devices=[]
for line in raw['stdout'].splitlines():
 c=line.split()
 if len(c)<2 or line.startswith('List of') or line.startswith('*'):continue
 serial,state=c[:2];row={'serial_sha256':hashlib.sha256(serial.encode()).hexdigest(),'state':state,'details':' '.join(c[2:])}
 if state=='device':
  q=run(['-s',serial,'shell','getprop','ro.product.manufacturer']);row['manufacturer']=q
  if q['returncode']==0 and q['stdout'].strip().lower()=='motorola':devices.append((serial,row))
 inventory.append(row)
observations=[]
props=['ro.product.manufacturer','ro.product.model','ro.product.device','ro.product.board','ro.product.name','ro.product.vendor.model','ro.product.vendor.device','ro.boot.hardware.sku','ro.boot.hardware.revision','ro.boot.hwrev','ro.boot.hwc','ro.hardware','ro.board.platform','ro.soc.model','ro.soc.manufacturer','ro.build.fingerprint','ro.build.version.release','ro.build.version.security_patch','ro.build.version.incremental']
if len(devices)==1:
 serial,row=devices[0]
 obs={'serial_sha256':row['serial_sha256'],'properties':{n:run(['-s',serial,'shell','getprop',n]) for n in props}}
 for label,args in [('display_size',['shell','wm','size']),('surface_display_ids',['shell','dumpsys','SurfaceFlinger','--display-id']),('battery',['shell','dumpsys','battery']),('power_supply_names',['shell','ls','-1','/sys/class/power_supply']),('input_devices',['shell','cat','/proc/bus/input/devices']),('soc_identity',['shell','sh','-c','for x in machine family soc_id revision; do echo "$x"; cat "/sys/devices/soc0/$x"; done'])]:
  obs[label]=run(['-s',serial,*args])
 observations.append(obs)
print(json.dumps({'host_alias':'pocket4','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'adb_executable':ADB,'adb_server_port':5061,'adb_inventory':inventory,'authorized_motorola_count':len(devices),'donor_observations':observations,'read_only':True,'physical_part_labels_measured':False,'physical_phone_project_verified':False},ensure_ascii=False))
