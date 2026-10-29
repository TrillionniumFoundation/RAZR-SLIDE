"""Make byte-exact complete inputs available to unchanged full-case exporters."""
from pathlib import Path
import argparse
import datetime as dt
import importlib.util
import json
import os
import resource
import shutil
import time

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('r7_core_bindings',ROOT/'register_and_run_native_local_r7_v4.py')
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
K3=ROOT.parent/'r7-recovery/k3'

def main():
    ap=argparse.ArgumentParser(allow_abbrev=False);ap.add_argument('--pose',choices=['near','far'],required=True);a=ap.parse_args()
    source_receipt=ROOT/'R7_FULL_FACTORY_INPUTS_ACTUAL_READBACK_V1.json';inputs=json.loads(source_receipt.read_text())
    core.require(inputs['completed'] and inputs['total_prerequisite_bytes']==408408534,'Original complete prerequisite readback required')
    case=ROOT/('full-'+a.pose+'-attempt1');core.require(not case.exists(),'Fresh full case evidence directory required')
    s=os.statvfs(ROOT);available=s.f_bavail*s.f_frsize;core.require(available>=1536*2**20,'Original1536MiB extra input/export reserve unavailable')
    contract={'schema':'RAZR_R7_COMPLETE_INPUT_COPY_CONTRACT_V1','pose':a.pose,'source_identity':core.bind(__file__),
              'input_readback':core.bind(source_receipt),'maximum_seconds':60,'maximum_copied_regular_bytes':420000000,
              'maximum_RSS_bytes':268435456,
              'original_extra_input_export_reserve_bytes':1536*2**20,'ordinary_available_before':available,
              'native_or_qualification_execution_allowed':False,'all_copies_verified_before_native_registration':True}
    cp=ROOT/('R7_'+a.pose.upper()+'_COMPLETE_INPUT_COPY_CONTRACT_V1.json');core.save(cp,contract)
    case.mkdir();start=time.monotonic();copied={};byte_count=0
    def copy(src,relative,expected):
        nonlocal byte_count
        core.require(time.monotonic()-start<=60,'Input copy wall budget exceeded')
        core.require(not src.is_symlink() and core.identity(src)==expected,'Source original differs before copy')
        byte_count+=expected['bytes'];core.require(byte_count<=420000000,'Input copy registered total exceeded')
        target=case/relative;target.parent.mkdir(parents=True,exist_ok=True);core.require(not target.exists(),'No input-copy overwrite allowed')
        with src.open('rb') as f,target.open('xb') as out:shutil.copyfileobj(f,out,1024*1024)
        core.require(core.identity(target)==expected,'Byte-exact input copy failed');copied[relative]=expected
    for relative,expected in inputs['original_drivers'].items():copy(K3/'source/k3full'/relative,'source/k3full/'+relative,expected)
    for pose,record in inputs['poses'].items():
        src=K3/('prerequisite-'+pose)
        core.require(core.strict_inventory(src)==record['members'],'Complete prerequisite source set changed')
        for relative,expected in record['members'].items():copy(src/relative,'prerequisite-'+pose+'/'+relative,expected)
    driver=K3/'K3FULL-driver-source.json';copy(driver,driver.name,core.identity(driver))
    for pose,record in inputs['poses'].items():
        core.require(core.strict_inventory(case/('prerequisite-'+pose))==record['members'],'Actual complete copied prerequisite set differs')
    setup_path,_=core.verify_sources()
    expected=json.loads((ROOT/'R7_SETUP_INSTALL_ONLY_CONTRACT_V3.json').read_text())['expected_sources']
    core.save(case/'S4-source-before.json',{'schema':'razr-r7-actual-sparse-S4-source-before-v1','source_commit':core.S4,
        'source_tree':'cdd9e2c41216201b6cd04dd610d45fde80499045','present_source_sha256':{k:v['sha256'] for k,v in expected.items()},
        'all_present_tracked_bytes_match_HEAD':True,'full_checkout_claimed':False,'tracked_present_source_count':973,
        'fresh_local_setup_receipt_sha256':core.identity(setup_path)['sha256'],'hosted_run_identity_claimed':False})
    core.save(case/'K3FULL-input-capacity.json',{'ordinary_available_bytes_before_second_copy':available,
        'additional_input_and_export_reserve_bytes':1536*2**20,'observed_actual_two_input_unpacked_bytes':408408534,
        'original_native_startup_256MiB_runtime_100MiB_guards_unchanged':True})
    core.save(case/'K3FULL-prerequisite-verification.json',{pose:{'manifest_sha256':record['manifest_identity']['sha256'],
        'all_engineering_members_verified':record['actual_regular_files']-1,'actual_complete_clear_pilot_verified':True} for pose,record in inputs['poses'].items()})
    core.require(core.strict_inventory(K3/'source/k3full')==inputs['original_drivers'],'Original drivers changed during input copy')
    for pose,record in inputs['poses'].items():
        core.require(core.strict_inventory(K3/('prerequisite-'+pose))==record['members'],'Original prerequisite changed during input copy')
    core.require(time.monotonic()-start<=60 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=268435456,'Input-copy registered wall/RSS bound exceeded')
    receipt={'schema':'RAZR_R7_COMPLETE_INPUT_COPY_ACTUAL_V1','completed':True,'contract':core.bind(cp),
        'seconds':time.monotonic()-start,'copied_member_count':len(copied),'copied_bytes':byte_count,'members':copied,
        'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'all_actual_input_copy_sets_equal':True,'all_original_source_bytes_unchanged':True,'native_execution_claimed':False}
    core.save(case/'R7_COMPLETE_INPUT_COPY_RECEIPT.json',receipt)
    print(json.dumps({k:receipt[k] for k in ('completed','seconds','copied_member_count','copied_bytes')}))

if __name__=='__main__':main()
