"""Read-only independent review of the frozen explicit ASCII BREP revision."""
import ast
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import resource
import signal
import tarfile
import time
import traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=ROOT/'r5-native/cloud-native-v1'
OLD=BASE/'publication-v3';NEW=BASE/'publication-v4'
SCIENCE=ROOT/'r5-native/trim-core-witness'
RECORD=HERE/'R5_NATIVE_CLOUD_V4_ASCII_INDEPENDENT_REVIEW.json'
LOCK='dbf70814f6933b98818338f0a342706161b0b47268ec6da7ddf36ef3d4be13b4'
HEADER=b'DBRep_DrawableShape\n\nCASCADE Topology V3, (c) Open Cascade\n'
started=time.monotonic();watched={};checks=[];hashed=0


def identity(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def need(ok,message):
    checks.append({'check':message,'passed':bool(ok)})
    if not ok:raise ValueError(message)


def read(path):
    global hashed
    path=Path(path);need(path.is_file()and not path.is_symlink()and path.stat().st_size<=8*2**20,'Bounded regular input: '+str(path.relative_to(ROOT)))
    data=path.read_bytes();hashed+=len(data);need(hashed<=64*2**20,'Read/hash budget')
    watched[str(path)]=identity(data);return data


def doc(path):return json.loads(read(path))


class UndoOnlySerializationDelta(ast.NodeTransformer):
    """Explicit whitelist of observed I/O-only differences, never geometry rewrites."""
    def visit_FunctionDef(self,node):
        if node.name in ('require_ascii_brep_v3','independent_ascii_brep_v3_header'):return None
        return self.generic_visit(node)
    def visit_ImportFrom(self,node):
        if node.module=='OCP.BRepTools':return ast.ImportFrom(module='OCP.BinTools',names=[ast.alias(name='BinTools')],level=0)
        if node.module=='OCP.BRep':node.names=[n for n in node.names if n.name!='BRep_Builder']
        return node
    def visit_Expr(self,node):
        if isinstance(node.value,ast.Call):
            call=node.value;name=call.func.id if isinstance(call.func,ast.Name)else ''
            if name in ('require_ascii_brep_v3','independent_ascii_brep_v3_header'):return None
            if name in ('need','require')and call.args:
                text=ast.unparse(call.args[0])
                if 'native_brep_serialization' in text or text in ('not native_shape.IsNull()','not raw.IsNull()'):return None
        return self.generic_visit(node)
    def visit_Assign(self,node):
        if any(isinstance(t,ast.Name)and t.id=='serialization' for t in node.targets):return None
        return self.generic_visit(node)
    def visit_Dict(self,node):
        keep=[i for i,k in enumerate(node.keys)if not(isinstance(k,ast.Constant)and k.value in ('serialization','native_brep_serialization'))]
        node.keys=[node.keys[i]for i in keep];node.values=[node.values[i]for i in keep]
        return self.generic_visit(node)
    def visit_Call(self,node):
        if isinstance(node.func,ast.Attribute)and isinstance(node.func.value,ast.Name)and node.func.value.id=='BRepTools':
            node.func.value.id='BinTools'
            if node.func.attr=='Read_s':node.args=node.args[:2]
        return self.generic_visit(node)
    def visit_Constant(self,node):
        mapping={'r5-finite-native-trim-core-witness-ascii-v2':'r5-finite-native-trim-core-witness-v1',
                 'r5-independent-native-trim-core-readback-ascii-v2':'r5-independent-native-trim-core-readback-v1',
                 'Native ASCII BREP export failed':'Native BREP export failed',
                 'Native ASCII BREP read failed':'Native BREP read failed',
                 'Independent ASCII BREP read failed':'Independent BREP read failed'}
        if isinstance(node.value,str)and node.value in mapping:node.value=mapping[node.value]
        return node


def main():
    global hashed
    need(not RECORD.exists(),'Preserve every actual review')
    resource.setrlimit(resource.RLIMIT_AS,(256*2**20,256*2**20))
    signal.signal(signal.SIGALRM,lambda signum,frame:(_ for _ in ()).throw(TimeoutError('90-second independent static review cap')));signal.alarm(90)
    report={'schema':'razr-r5-native-cloud-v4-independent-ASCII-delta-review','started_utc':datetime.now(timezone.utc).isoformat(),
            'completed':False,'reviewed_source_imported_or_executed':False,'actual_controls_rerun':False,'native_CAD_executed':False,
            'original_source_or_evidence_modified':False,'budget':{'wall_seconds':90,'address_space_bytes':268435456,
            'hash_read_bytes':67108864,'archive_decoded_bytes':8388608},'source_deltas':[],'original_input_headers':[],
            'native_runtime_or_geometry_pass_claimed':False,'full_continuous_G2':False}
    try:
        old=doc(OLD/'SOURCE_LOCK.json');lock=doc(NEW/'SOURCE_LOCK.json')
        need(identity(read(NEW/'SOURCE_LOCK.json'))['sha256']==LOCK,'Literal frozen v4 lock')
        need(lock['original_six_native_limits_unchanged']==old['original_six_native_limits_unchanged'],'All original six native limits byte-equivalent as JSON values')
        for name,wanted in lock['asset_files'].items():need(identity(read(NEW/name))==wanted,'V4 locked asset: '+name)
        for name in ('qualify_fresh_runtime_r5.py','run_fresh_runtime_script_r5.py','r5-native-fresh-hosted-v1.yml'):
            need(read(NEW/name)==read(OLD/name),'Previously reviewed entry/workflow unchanged: '+name)
        prior=doc(ROOT/'r5-integration/independent-native-cloud-v3-argv-review/R5_NATIVE_CLOUD_V3_ARGV_INDEPENDENT_REVIEW_V2.json')
        need(prior['completed']and prior['Actions_argv_gate_review_passed']and prior['actual_denial_control_counts']=={
            'explicit_unqualified_runtime_denial':2,'complete_raw_argv_equality_denial':13,'argparse_no_abbreviation_denial':2},'Completed independent original 17-control argv review retained')
        manifest=doc(NEW/'SCIENTIFIC_INPUT_MANIFEST.json');archive_path=NEW/'scientific-inputs.tar.gz'
        need(identity(read(archive_path))==manifest['archive_identity']and manifest['member_count']==len(manifest['members'])==155,'Complete v4 archive identity/census')
        total=0
        with tarfile.open(archive_path,'r:gz')as archive:
            rows=archive.getmembers();need(len(rows)==len({x.name for x in rows})==155 and {x.name for x in rows}==set(manifest['members']),'Exact unique v4 archive members')
            for row in rows:
                need(row.isfile()and not row.name.startswith('/')and'..'not in Path(row.name).parts,'Safe regular archive member: '+row.name)
                total+=row.size;need(total<=8*2**20,'Decoded archive budget')
                data=archive.extractfile(row).read();need(identity(data)==manifest['members'][row.name]and data==read(ROOT/row.name),'Frozen archive equals actual original: '+row.name)
        report['archive_members_verified']=155;report['archive_decoded_bytes']=total
        preparation=doc(BASE/'serialization-v1/R5_NATIVE_ASCII_BREP_REVISION_PREPARATION.json')
        need(len(preparation['original_six_inputs'])==6,'All six original inputs required')
        for row in preparation['original_six_inputs']:
            data=read(ROOT/row['path']);need(identity(data)==row['identity']and data.startswith(HEADER)and row['observed_exact_header_hex']==HEADER.hex(),'Actual complete input identity and exact ASCII V3 header: '+row['path'])
            report['original_input_headers'].append({'path':row['path'],'identity':row['identity'],'exact_ASCII_V3_header_verified':True})
        pairs=[('native_trim_core_witness_r5.py','native_trim_core_witness_r5_ascii_v2.py','require_ascii_brep_v3'),
               ('read_native_trim_core_witness_r5.py','read_native_trim_core_witness_r5_ascii_v2.py','independent_ascii_brep_v3_header')]
        for oldname,name,headerfn in pairs:
            oldtree=ast.parse(read(SCIENCE/oldname));newtree=ast.parse(read(SCIENCE/name))
            restored=UndoOnlySerializationDelta().visit(ast.parse(read(SCIENCE/name)))
            need(ast.dump(restored,include_attributes=False)==ast.dump(oldtree,include_attributes=False),'Entire source AST equal after explicit I/O-only delta whitelist: '+name)
            methods=[n for n in ast.walk(newtree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and isinstance(n.func.value,ast.Name)and n.func.value.id=='BRepTools']
            need(Counter(n.func.attr for n in methods)=={'Read_s':1,'Write_s':1},'One paired BRepTools read/write implementation: '+name)
            readfn=[n for n in ast.walk(newtree)if isinstance(n,ast.FunctionDef)and n.name=='read'];need(len(readfn)==1,'Single independent native reader: '+name)
            src=ast.unparse(readfn[0]);need(headerfn+'(' in src and 'BRep_Builder()'in src and '.IsNull()'in src,'Header/native status/nonNull read chain: '+name)
            need(src.index(headerfn+'(')<src.index('BRepTools.Read_s')<src.index('.IsNull()')<src.index('cq.Shape.cast'),'Read order before shape casting: '+name)
            header=[n for n in newtree.body if isinstance(n,ast.FunctionDef)and n.name==headerfn];need(len(header)==1,'Explicit independent header function: '+name)
            if name.startswith('native_'):need('stream.read(len(expected))'in ast.unparse(header[0]),'Producer reads bounded exact prefix')
            else:need(ast.unparse(header[0]).count('stream.readline(128)')==3,'Reader independently reads exactly three bounded lines')
            report['source_deltas'].append({'source':name,'identity':identity(read(SCIENCE/name)),'complete_geometry_control_flow_thresholds_preserved_after_whitelisted_IO_delta':True,
                'paired_ASCII_Read_Write':True,'native_Read_success_and_nonNull_required':True,'input_and_output_header_checked':True})
        before=read(OLD/'register_cloud_native_r5.py').decode();after=read(NEW/'register_cloud_native_r5.py').decode()
        expected=before.replace("script = science / 'r5-native/trim-core-witness/native_trim_core_witness_r5.py'","script = science / template['science_worker_paths']['producer']").replace("script = science / 'r5-native/trim-core-witness/read_native_trim_core_witness_r5.py'","script = science / template['science_worker_paths']['reader']")
        need(after==expected,'Registrar only replaces two science script path expressions')
        a=doc(OLD/'R5_CLOUD_NATIVE_SCIENCE_TEMPLATE.json');b=doc(NEW/'R5_CLOUD_NATIVE_SCIENCE_TEMPLATE.json')
        ca,cb=a['science_contract'],b['science_contract']
        need(a['original_resource_limits']==b['original_resource_limits']==lock['original_six_native_limits_unchanged'],'Template and lock original six gates identical')
        need({k:v for k,v in cb['capacity'].items()if k!='ASCII_output_capacity_basis'}==ca['capacity'],'Every prior capacity field unchanged; only explicit ASCII size basis added')
        for field in('scope','selection','mapping','projection','inventory_source','expected_43_package_versions'):
            need(ca[field]==cb[field],'Original scientific operand/domain/runtime field unchanged: '+field)
        need(cb['native_brep_serialization']=='OCCT_ASCII_BREP_V3'and b['science_worker_paths']=={
            'producer':'r5-native/trim-core-witness/native_trim_core_witness_r5_ascii_v2.py',
            'reader':'r5-native/trim-core-witness/read_native_trim_core_witness_r5_ascii_v2.py'},'New named ASCII source dispatch fixed in locked template')
        controls=doc(BASE/'serialization-v1/dispatch-controls/R5_ASCII_BREP_DISPATCH_CONTROLS_ACTUAL.json')
        need(controls['completed']and len(controls['controls'])==28 and controls['native_execution']is False and
             controls['native_topology_validity_claimed']is False and controls['blocked_native_import_attempts']==[]and controls['native_numeric_modules_loaded']==[],
             'Actual 28 controls completed with no native/numeric imports or topology claim')
        need(controls['control_source_identity']==identity(read(BASE/'check_ascii_brep_dispatch_r5.py')),'Actual format-control source byte identity')
        controltree=ast.parse(read(BASE/'check_ascii_brep_dispatch_r5.py'));controltext=ast.unparse(controltree)
        need('sys.meta_path.insert(0, NoNative())'in controltext and 'spec.loader.exec_module(module)'in controltext,'Actual controls call original header functions under no-native hook')
        cases=[x['path']for x in preparation['original_six_inputs']]+['empty','truncated_header','binary_format','other_ASCII_version','unknown_prefix','embedded_valid_header','wrong_line_endings','unsupported_declared_format_before_file_access']
        for oldname,name,headerfn in pairs:
            rows=[r for r in controls['controls']if r['source']==name];need([r['case']for r in rows]==cases,'Full actual14-case format control sequence: '+name)
            for row in rows:
                need(row['passed']is True,'Actual format control observed: '+name+'/'+row['case'])
                if row['case']in cases[:6]:need(row['observed']['header_hex']==HEADER.hex()and row['observed']['header_recognition_is_not_native_validity']is True,'Positive control claims format only')
                else:need(row['exception']['type']=='ValueError','Malformed/unsupported format actually denied')
            comparison=next(r for r in controls['source_comparisons']if r['source']==name)
            need(comparison['source_identity']==identity(read(SCIENCE/name))and comparison['predecessor_identity']==identity(read(SCIENCE/oldname)),'Actual controls bind exact old/new sources: '+name)
        for case in cases[6:-1]:
            data=read(BASE/'serialization-v1/dispatch-controls'/str(case+'.brep'));need(not data.startswith(HEADER),'Actual malformed fixture cannot satisfy exact ASCII V3 prefix: '+case)
        old_controls=doc(BASE/'argument-controls-v2/R5_CLOUD_ARGUMENT_CONTROLS_ACTUAL.json')
        need(old_controls['entry']==identity(read(NEW/'run_fresh_runtime_script_r5.py'))and old_controls['qualifier']==identity(read(NEW/'qualify_fresh_runtime_r5.py')),
             'Previous17 actual argv controls still bind unchanged v4 entry sources')
        report['actual_format_control_count']=28;report['actual_format_positive_count']=12;report['actual_format_negative_count']=16
        report['original_argv_actual_control_count_preserved']=17
        report['format_controls_are_not_native_topology_tests']=True
        report['allow_original_gate_Actions_for_exact_v4_revision']=True;report['completed']=True
    except BaseException as exc:
        report['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        report['allow_original_gate_Actions_for_exact_v4_revision']=False
    finally:
        signal.alarm(0);unchanged=True
        for path,wanted in watched.items():
            data=Path(path).read_bytes();hashed+=len(data);unchanged=unchanged and identity(data)==wanted
        report['all_watched_inputs_unchanged_after_review']=unchanged;report['completed']=report['completed']and unchanged
        report['seconds']=time.monotonic()-started;report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        report['total_hash_read_bytes']=hashed;report['watched_input_count']=len(watched);report['source_lock_sha256_literal']=LOCK
        report['budget_met']=report['seconds']<=90 and report['peak_RSS_bytes']<=268435456 and hashed<=67108864
        if not(report['completed']and report['budget_met']):report['completed']=False;report['allow_original_gate_Actions_for_exact_v4_revision']=False
        report['checks']=checks;report['check_count']=len(checks);report['watched_inputs']=[{'path':p,**v}for p,v in sorted(watched.items())]
        report['review_source']={'path':str(Path(__file__)),**identity(Path(__file__).read_bytes())}
        RECORD.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:report.get(k)for k in('completed','allow_original_gate_Actions_for_exact_v4_revision','seconds','peak_RSS_bytes','check_count','watched_input_count','total_hash_read_bytes','failure')}),flush=True)
    return 0 if report['completed']else 2


if __name__=='__main__':raise SystemExit(main())
