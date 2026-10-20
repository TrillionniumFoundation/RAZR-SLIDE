import datetime,hashlib,json,subprocess,re
ADB='/home/alex/.local/opt/razr-adb-37/adb';PORT='5061'
def run(args):
 try:
  p=subprocess.run([ADB,'-P',PORT,*args],capture_output=True,text=True,timeout=20)
  return {'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
 except Exception as e:return {'error':type(e).__name__}
raw=run(['devices','-l']);ids=[line.split()[0] for line in raw.get('stdout','').splitlines() if len(line.split())>=2 and line.split()[1]=='device']
assert len(ids)==1
serial=ids[0]
assert hashlib.sha256(serial.encode()).hexdigest()=='41ad305f8562a6c47710afe71fabf30cb8692a71d3de1a47ca9949b669bcc6c1'
results={}
for name in ['battery','main_battery','flip_battery','balance_master','balance_slave','usb']:
 q=run(['-s',serial,'shell','cat','/sys/class/power_supply/'+name+'/uevent'])
 if q.get('stdout'):
  q['stdout']='\n'.join((line.split('=',1)[0]+'=sha256:'+hashlib.sha256(line.split('=',1)[1].encode()).hexdigest()) if 'SERIAL' in line.split('=',1)[0].upper() and '=' in line else line for line in q['stdout'].splitlines())+'\n'
 results['power_supply_'+name]=q
for name,path in [('soc_model','/sys/devices/soc0/machine'),('soc_id','/sys/devices/soc0/soc_id'),('soc_revision','/sys/devices/soc0/revision'),('dt_model','/sys/firmware/devicetree/base/model'),('dt_compatible','/sys/firmware/devicetree/base/compatible')]:
 results[name]=run(['-s',serial,'shell','cat',path])
for name,args in [('shell_identity',['shell','id']),('drm_nodes',['shell','ls','-1','/sys/class/drm']),('graphics_nodes',['shell','ls','-1','/sys/class/graphics']),('touch_sysfs_names',['shell','ls','-1','/sys/class/input'])]:
 results[name]=run(['-s',serial,*args])
q=run(['-s',serial,'shell','dumpsys','input'])
if 'stdout' in q:
 q['stdout']='\n'.join(line for line in q['stdout'].splitlines() if re.match(r'^\s*(Device [0-9]+:|Name:|Path: /dev/input|Identifier:|Classes:|Sources:|IsExternal:|AssociatedDisplay)',line))+'\n'
 q['filter_scope']='Only hardware device summary lines retained; focused windows and event history excluded'
results['input_hardware_summary']=q
print(json.dumps({'host_alias':'pocket4','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'serial_sha256':hashlib.sha256(serial.encode()).hexdigest(),'adb_server_port':5061,'results':results,'read_only':True,'physical_phone_project_verified':False,'physical_part_labels_or_terminal_pinout_verified':False},ensure_ascii=False))
