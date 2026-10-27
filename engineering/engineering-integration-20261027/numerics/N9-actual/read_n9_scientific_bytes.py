"""Recover exact original N9 scientific bytes; no native matrix or CAD execution."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,os,resource,stat,time,urllib.request,urllib.error,zipfile
ZIP_BYTES=232205318
ZIP_SHA="13fcea5602f25efc827ebb717b1b38c76541c95d78addd78374f69dc359a6e27"
MANIFEST_BYTES=154607
MANIFEST_SHA="d99a52d2cd808787437dc77d251474ac6b6fca9ed4e269f3b55cf73226036ca7"
UNCOMPRESSED=433013118
CHUNK=1024**2
def check(ok,label):
    if not ok:raise ValueError(label)
def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(CHUNK),b""):h.update(b)
    return h.hexdigest()
def recover(a):
    start=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
    team_roots=(Path("/tmp/razr-recovery-20261026"),Path("/tmp/razr-next-20261027"))
    r={"schema":"razr-N9-original-scientific-complete-byte-readback-v1","completed":False,
       "source_run_id":40465150731,"source_head_sha":"44d5abca7b4000358d1e8275b1d9266713044019",
       "source_artifact_id":12715569236,"source_ZIP_bytes":ZIP_BYTES,"source_ZIP_sha256":ZIP_SHA,
       "original_manifest_bytes":MANIFEST_BYTES,"original_manifest_sha256":MANIFEST_SHA,
       "local_native_N9_execution":False,"native_CAD_or_numeric_execution":False,
       "source":"original immutable Actions scientific artifact",
       "team_download_and_extracted_file_ceiling_bytes":3*1024**3,"filesystem_reserve_bytes":2*1024**3,
       "byte_worker_AS_ceiling_bytes":256*1024**2,"byte_worker_wall_seconds":180,
       "original_numeric_resource_contract_changed":False,"raw_URL_or_credentials_saved":False,
       "phase":"preflight","members":{}}
    receipt=a.root/"N9_RECOVERED_ORIGINAL_SCIENTIFIC_READBACK.json"
    def save():
        r["elapsed_seconds"]=time.monotonic()-start
        r["peak_rss_KiB"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        receipt.write_text(json.dumps(r,indent=2)+"\n")
    def guard(additional=0):
        check(time.monotonic()-start<180,"byte_worker_wall_cap")
        fs=os.statvfs(a.root);available=fs.f_bavail*fs.f_frsize
        seen=set();used=0
        for team in team_roots:
            for p in team.rglob("*"):
                if p.is_file() and not p.is_symlink():
                    st=p.stat();key=(st.st_dev,st.st_ino)
                    if key not in seen:used+=st.st_size;seen.add(key)
        check(available>=2*1024**3+additional,"shared_disk_reserve")
        check(used+additional<=3*1024**3,"shared_team_file_cap")
        r["minimum_observed_filesystem_available_bytes"]=min(r.get("minimum_observed_filesystem_available_bytes",available),available)
        r["maximum_observed_team_file_bytes"]=max(r.get("maximum_observed_team_file_bytes",0),used)
    try:
        guard(ZIP_BYTES+UNCOMPRESSED+8*CHUNK);save()
        archive=a.root/"N9-original-scientific.zip";part=archive.with_suffix(".zip.writing")
        check(not archive.exists() and not part.exists(),"fresh_original_byte_destination")
        r["phase"]="download_original_zip";save()
        h=hashlib.sha256();count=0
        with urllib.request.urlopen(a.url,timeout=60) as response,part.open("xb") as out:
            r["download_HTTP_status"]=response.status
            for b in iter(lambda:response.read(CHUNK),b""):
                count+=len(b);check(count<=ZIP_BYTES,"original_zip_size_bound")
                out.write(b);h.update(b)
                if count%(16*CHUNK)<CHUNK:guard()
        check(count==ZIP_BYTES and h.hexdigest()==ZIP_SHA,"original_zip_actual_bytes_sha")
        os.replace(part,archive)
        r["whole_ZIP_actual_bytes_and_SHA_checked"]=True
        r["phase"]="original_manifest_and_all_members";save()
        outroot=a.root/"N9-original-scientific";outroot.mkdir(exist_ok=False)
        with zipfile.ZipFile(archive) as z:
            names=z.namelist();raw=z.read("EXPORT_MANIFEST.json")
            check(len(raw)==MANIFEST_BYTES and hashlib.sha256(raw).hexdigest()==MANIFEST_SHA,"original_manifest_bytes_sha")
            manifest=json.loads(raw);entries=manifest["exported_files"]
            check(len(entries)==79 and len(names)==len(set(names))==80 and set(names)==set(entries)|{"EXPORT_MANIFEST.json"},"exact_original_member_set")
            check(sum(i.file_size for i in z.infolist())==UNCOMPRESSED,"original_uncompressed_count")
            check(manifest["raw_runtime_records_exported"] is False and manifest["producer_records_modified"] is False,"original_scientific_scope")
            expected={**entries,"EXPORT_MANIFEST.json":{"bytes":MANIFEST_BYTES,"sha256":MANIFEST_SHA}}
            for info in z.infolist():
                name=info.filename;pp=PurePosixPath(name)
                check(not pp.is_absolute() and ".." not in pp.parts and chr(92) not in name and not info.is_dir(),"regular_scientific_relative_member")
                check(not stat.S_ISLNK(info.external_attr>>16),"no_symlink_members")
                check(info.file_size==expected[name]["bytes"],"original_member_declared_size")
                target=outroot/name;target.parent.mkdir(parents=True,exist_ok=True)
                h=hashlib.sha256();count=0
                with z.open(info) as inp,target.open("xb") as out:
                    for b in iter(lambda:inp.read(CHUNK),b""):
                        count+=len(b);check(count<=expected[name]["bytes"],"original_member_size_bound")
                        out.write(b);h.update(b)
                        if count%(16*CHUNK)<CHUNK:guard()
                actual={"bytes":count,"sha256":h.hexdigest()}
                check(actual==expected[name],"original_member_actual_sha_bytes")
                check(digest(target)==expected[name]["sha256"],"persisted_original_member_readback_sha")
                r["members"][name]={**actual,"CRC_checked":True,"persisted_byte_readback_checked":True}
                save()
        guard()
        r.update(completed=True,phase="complete",member_count=80,total_uncompressed_bytes=UNCOMPRESSED,
          every_original_member_actual_SHA_bytes_CRC_and_persisted_bytes_checked=True,
          source_ZIP_persisted_and_read_back=True,
          recovered_scientific_directory="N9-original-scientific",recovered_ZIP="N9-original-scientific.zip")
        check(digest(archive)==ZIP_SHA,"persisted_whole_zip_readback_sha")
        save();print(json.dumps({k:r[k] for k in ["completed","member_count","source_ZIP_bytes","source_ZIP_sha256","elapsed_seconds","peak_rss_KiB","native_CAD_or_numeric_execution"]}))
        return 0
    except BaseException as e:
        r.update(completed=False,failure_type=type(e).__name__)
        if isinstance(e,ValueError):r["failure_gate"]=str(e)
        if isinstance(e,urllib.error.HTTPError):r["failure_HTTP_status"]=int(e.code)
        save();print(json.dumps({k:r[k] for k in ["completed","phase","failure_type"]}|{k:r[k] for k in ["failure_gate","failure_HTTP_status"] if k in r}))
        return 2
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--url",required=True);p.add_argument("--root",type=Path,required=True)
    raise SystemExit(recover(p.parse_args()))
