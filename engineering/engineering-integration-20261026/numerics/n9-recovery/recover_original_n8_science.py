"""Recover exact original N8 scientific bytes; no native matrix or CAD execution."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,os,resource,stat,time,urllib.request,urllib.error,zipfile
ZIP_BYTES=238609175
ZIP_SHA="ac747737b52960596c6a35be47ba3d924f6276227d22a98be8fd3b1fde0d9d0e"
MANIFEST_BYTES=166609
MANIFEST_SHA="aa84d34b26847f308296809ff83002d32535a56a92eb09adcc7e42b571e88ee7"
UNCOMPRESSED=455274920
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
    team=a.root.parent
    r={"schema":"razr-N8-original-scientific-runtime-recovery-readback-v1","completed":False,
       "source_run_id":40288924586,"source_head_sha":"0f86820367a4444796d9fe9f72b63d324ee5c3c5",
       "source_artifact_id":12634369890,"source_ZIP_bytes":ZIP_BYTES,"source_ZIP_sha256":ZIP_SHA,
       "original_manifest_bytes":MANIFEST_BYTES,"original_manifest_sha256":MANIFEST_SHA,
       "original_native_N8_rerun":False,"native_CAD_or_numeric_execution":False,
       "old_RAM_or_store_files_recovered":False,"source":"original immutable Actions scientific artifact",
       "team_download_and_extracted_file_ceiling_bytes":3*1024**3,"filesystem_reserve_bytes":2*1024**3,
       "byte_worker_AS_ceiling_bytes":256*1024**2,"byte_worker_wall_seconds":180,
       "original_numeric_resource_contract_changed":False,"raw_URL_or_credentials_saved":False,
       "phase":"preflight","members":{}}
    receipt=a.root/"N8_RECOVERED_ORIGINAL_SCIENTIFIC_READBACK.json"
    def save():
        r["elapsed_seconds"]=time.monotonic()-start
        r["peak_rss_KiB"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        receipt.write_text(json.dumps(r,indent=2)+"\n")
    def guard(additional=0):
        check(time.monotonic()-start<180,"byte_worker_wall_cap")
        fs=os.statvfs(a.root);available=fs.f_bavail*fs.f_frsize
        used=sum(p.stat().st_size for p in team.rglob("*") if p.is_file())
        check(available>=2*1024**3+additional,"shared_disk_reserve")
        check(used+additional<=3*1024**3,"shared_team_file_cap")
        r["minimum_observed_filesystem_available_bytes"]=min(r.get("minimum_observed_filesystem_available_bytes",available),available)
        r["maximum_observed_team_file_bytes"]=max(r.get("maximum_observed_team_file_bytes",0),used)
    try:
        guard(ZIP_BYTES+UNCOMPRESSED+8*CHUNK);save()
        archive=a.root/"N8-original-scientific.zip";part=archive.with_suffix(".zip.writing")
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
        outroot=a.root/"N8-original-scientific";outroot.mkdir(exist_ok=False)
        with zipfile.ZipFile(archive) as z:
            names=z.namelist();raw=z.read("EXPORT_MANIFEST.json")
            check(len(raw)==MANIFEST_BYTES and hashlib.sha256(raw).hexdigest()==MANIFEST_SHA,"original_manifest_bytes_sha")
            manifest=json.loads(raw);entries=manifest["exported_files"]
            check(len(entries)==86 and len(names)==len(set(names))==87 and set(names)==set(entries)|{"EXPORT_MANIFEST.json"},"exact_original_member_set")
            check(sum(i.file_size for i in z.infolist())==UNCOMPRESSED,"original_uncompressed_count")
            check(manifest["raw_runtime_records_exported"] is False and manifest["producer_records_modified"] is False,"original_scientific_scope")
            expected={**entries,"EXPORT_MANIFEST.json":{"bytes":MANIFEST_BYTES,"sha256":MANIFEST_SHA}}
            for info in z.infolist():
                name=info.filename;pp=PurePosixPath(name)
                check(not pp.is_absolute() and ".." not in pp.parts and not info.is_dir(),"regular_scientific_relative_member")
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
        r.update(completed=True,phase="complete",member_count=87,total_uncompressed_bytes=UNCOMPRESSED,
          every_original_member_actual_SHA_bytes_CRC_and_persisted_bytes_checked=True,
          source_ZIP_persisted_and_read_back=True,
          recovered_scientific_directory="N8-original-scientific",recovered_ZIP="N8-original-scientific.zip")
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
