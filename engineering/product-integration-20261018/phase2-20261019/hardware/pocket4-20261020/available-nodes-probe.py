import datetime,hashlib,json,subprocess
ADB='/home/alex/.local/opt/razr-adb-37/adb';PORT='5061'
def run(args):
 p=subprocess.run([ADB,'-P',PORT,*args],capture_output=True,text=True,timeout=20)
 return {'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
raw=run(['devices','-l']);ids=[line.split()[0] for line in raw['stdout'].splitlines() if len(line.split())>=2 and line.split()[1]=='device']
assert len(ids)==1
serial=ids[0];assert hashlib.sha256(serial.encode()).hexdigest()=='41ad305f8562a6c47710afe71fabf30cb8692a71d3de1a47ca9949b669bcc6c1'
dirs=['/sys/class/drm/card0-DSI-1','/sys/class/drm/card0-DSI-2','/sys/class/drm/sde-conn-2-DSI-1','/sys/class/drm/sde-conn-3-DSI-2','/sys/class/power_supply/main_battery','/sys/class/power_supply/flip_battery']
result={p:run(['-s',serial,'shell','ls','-1',p]) for p in dirs}
print(json.dumps({'host_alias':'pocket4','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'serial_sha256':hashlib.sha256(serial.encode()).hexdigest(),'adb_server_port':5061,'directories':result,'read_only':True}))
