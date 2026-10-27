"""Native K4 producer/reader API; called only by the owned hosted worker.

An owned hosted launcher must supply the unchanged original resource guard,
separate worker processes, exact S4/43-package environment checks and the
engineering allowlist exporter. This module never launches a process or CAD.
Its functions use the already verified cq/p modules supplied by that launcher.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import time

SPEC_SHA='a267cc50eeae4d59e96bfd1ebb61d8d14b81a856edb622e383565f2b722288dd'
P_SOURCE_SHA='fc5391d3be98810ada06ca27e65de9a77d2f599c4d1890bb31a4d87ef14791b4'
EPS=1e-7
FALSE_FLAGS={
    'global_minimum_wall_measured':False,'global_minimum_wall_qualified':False,
    'complete_continuous_motion_proved':False,'physical_allowed_domain_proved':False,
    'strength_qualified':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,
}


def require(ok,message):
    if not ok:raise ValueError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def identity(path):return {'bytes':Path(path).stat().st_size,'sha256':sha(path)}
def finite(x):
    require(type(x) in (float,int) and math.isfinite(x),'nonfinite native value')
    return x
def atomic(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(path)


def load_spec(spec_path):
    require(sha(spec_path)==SPEC_SHA,'frozen local-section spec differs')
    s=json.loads(Path(spec_path).read_text())
    require(s['schema']=='razr-K4-bounded-whole-body-local-section-native-pilot-v1','wrong K4 spec')
    require(len(s['probes'])==12 and len(s['negative_controls'])==2,'complete bounded probe inventory required')
    require(s['original_directed_positive_volume_gate_mm3']==EPS,'original geometry gate changed')
    require(len({x['probe_id'] for x in s['probes']})==12,'duplicate probe identifier')
    return s


def validate_external_context(p,context):
    require(sha(p.__file__)==P_SOURCE_SHA,'actual imported S4 material helper source differs')
    require(context.get('functional_source_commit')=='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560','immutable S4 checkout required')
    for k in ('owned_supervisor_active','source_bytes_before_verified','worktree_clean_before','locked_environment_before_verified'):
        require(context.get(k) is True,'owned launcher precondition missing: '+k)
    require(context.get('checked_locked_packages_before')==43,'all original locked packages required')
    require(context.get('original_resource_guard_unchanged') is True,'original owned resource limits required')
    require(callable(context.get('capture_error')),'raw failure preservation callback required')
    return {k:context[k] for k in ('functional_source_commit','owned_supervisor_active','source_bytes_before_verified',
        'worktree_clean_before','locked_environment_before_verified','checked_locked_packages_before','original_resource_guard_unchanged')}


def signature(p,shape,positive=False):
    solids,vol=p.whole_material(shape,empty=not positive)
    require(finite(vol)>=0,'negative signed whole material')
    if positive:require(len(solids)==1 and vol>0 and shape.isValid(),'one valid positive local material required')
    return {'valid_topology':bool(shape.isValid()),'solid_count':len(solids),
            'signed_volume_mm3':vol,'face_count':len(shape.Faces())}


def load_wholes(cq,p,step_dir,spec,budget_check):
    parts={};identities={};faces={}
    for name,expected in sorted(spec['input_three_whole_STEPs'].items()):
        budget_check();path=Path(step_dir)/name
        require(path.name==name and path.is_file() and not path.is_symlink(),'exact original whole STEP file required')
        require(identity(path)==expected,'whole STEP bytes differ from actual K3 science')
        roots=cq.importers.importStep(str(path)).vals();require(len(roots)==1,'one STEP root required')
        body=p.single(roots[0]);role=Path(name).stem
        identities[role]={'file':name,**expected,'native_signature':signature(p,body,True)}
        require(len(body.Faces())==spec['complete_face_inventory_required'][role],'current whole native face count differs')
        record=[]
        for index,face in enumerate(body.Faces()):
            budget_check()
            record.append({'native_face_index':index,'geometry_type':face.geomType(),'area_mm2':finite(face.Area()),
                           'actual_native_surface_bounds_mm':[finite(x) for x in p.bounds(face)],
                           'functional_role_assigned':False})
        parts[role]=body;faces[role]=record
    require(set(parts)=={'A_BACK_PANEL','L_KEY','R_KEY'},'all three original current participants required')
    return parts,identities,faces


class Output:
    def __init__(self,cq,p,output,budget_check,boolean_limit,error_recorder):
        self.cq,self.p,self.root,self.check=cq,p,Path(output),budget_check
        require(not self.root.exists(),'fresh output directory required; existing results never overwritten')
        self.root.mkdir(parents=True);self.exports=[];self.events=[];self.started=time.monotonic()
        self.boolean_limit=boolean_limit;self.boolean_calls=0;self.error_recorder=error_recorder
    def event(self,operation,phase,**record):
        row={'sequence':len(self.events),'elapsed_seconds':time.monotonic()-self.started,
             'operation':operation,'phase':phase,**record}
        self.events.append(row)
        with (self.root/'journal.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
    def failure(self,scope,error):
        self.event(scope,'diagnostic_error',diagnostic=self.error_recorder(scope,error))
    def operation(self,label,fn):
        require(self.boolean_calls<self.boolean_limit,'preregistered Boolean call bound reached')
        self.check();self.boolean_calls+=1
        begin=time.monotonic();self.event(label,'start')
        try:result=fn()
        except BaseException as error:
            self.failure(label,error)
            self.event(label,'error',exception_type=type(error).__name__,operation_seconds=time.monotonic()-begin)
            raise
        self.check();self.event(label,'finish',operation_seconds=time.monotonic()-begin)
        return result
    def difference(self,label,left,right):
        self.check()
        a,av=self.p.whole_material(left,empty=True);b,bv=self.p.whole_material(right,empty=True)
        left_empty=not a and av==0;right_empty=not b and bv==0
        if left_empty or right_empty:
            # Only an already validated empty material permits this exact set
            # identity. Unknown native errors and null shapes are never empty.
            self.event(label,'validated_empty_set_identity',
                rule='empty_left_minus_any_is_same_empty' if left_empty else 'any_minus_empty_is_same_left',
                left_signature=signature(self.p,left),right_signature=signature(self.p,right),
                result_is_exact_unchanged_left_operand=True,native_Boolean_called=False)
            return left
        return self.operation(label,lambda:left.cut(right))
    def shape(self,name,shape,positive=False):
        require(re.fullmatch(r'[A-Za-z0-9_-]+',name) is not None,'safe engineering basename required')
        self.check();sig=signature(self.p,shape,positive);brep=self.root/(name+'.brep')
        require(not brep.exists(),'scientific original may not be overwritten')
        require(shape.exportBrep(str(brep)) is True and 0<brep.stat().st_size<=16*2**20,'native BREP export failed or exceeded per-file bound')
        row={'name':brep.name,**identity(brep),'signature':sig,'positive_material_required':positive}
        self.exports.append(row)
        # STEP has no reliable empty-solid representation. Every positive local
        # shape has a complete STEP as well; every empty result retains BREP.
        if sig['signed_volume_mm3']>0:
            self.check();step=self.root/(name+'.step');require(not step.exists(),'scientific original may not be overwritten')
            status=shape.exportStep(str(step));expected=getattr(type(status),'IFSelect_RetDone',None)
            require(expected is not None and status==expected,'native STEP serializer did not report success')
            require(step.is_file() and 0<step.stat().st_size<=16*2**20,'native STEP export failed or exceeded per-file bound')
            self.exports.append({'name':step.name,**identity(step),'signature':sig,'positive_material_required':positive})
        require(signature(self.p,shape,positive)==sig,'serialization changed the in-memory material signature')
        return row
    def save(self,report):
        report['all_scientific_exports']=self.exports
        report['elapsed_seconds']=time.monotonic()-self.started
        report['journal_rows']=len(self.events)
        report['Boolean_calls_started']=self.boolean_calls
        report['preregistered_Boolean_call_limit']=self.boolean_limit
        report['journal']=identity(self.root/'journal.jsonl') if (self.root/'journal.jsonl').exists() else None
        atomic(self.root/'report.json',report)


def finish_external(context_after):
    result=context_after()
    for k in ('source_bytes_after_verified','locked_environment_after_verified','owned_child_identity_verified'):
        require(result.get(k) is True,'owned launcher postcondition missing: '+k)
    require(result.get('checked_locked_packages_after')==43,'complete locked package postcheck required')
    return {k:result[k] for k in ('source_bytes_after_verified','locked_environment_after_verified',
        'owned_child_identity_verified','checked_locked_packages_after')}


def run_producer(*,cq,p,spec_path,step_dir,output,budget_check,context_before,context_after):
    """Called only by the reviewed owned hosted worker after locked setup."""
    spec=load_spec(spec_path);before=validate_external_context(p,context_before)
    o=Output(cq,p,output,budget_check,38,context_before['capture_error'])
    report={'schema':'razr-K4-native-local-section-producer-v1','spec_sha256':SPEC_SHA,
        'API_source_sha256':sha(__file__),'execution_completed':False,'native_sections_qualified':False,
        'local_material_targets_all_matched':False,'context_before':before,
        'local_window_results':[],'negative_controls':[],'evaluation_failures':[],**FALSE_FLAGS}
    o.save(report);patches={}
    try:
        parts,inputs,faces=load_wholes(cq,p,step_dir,spec,budget_check)
        report['whole_inputs']=inputs;report['complete_native_face_inventory']=faces;o.save(report)
        for target in spec['probes']:
            budget_check()
            label=target['probe_id'];row={'probe_id':label,'whole_body':target['whole_body'],'evaluated':False,'status':'unresolved'}
            report['local_window_results'].append(row)
            try:
                window=p.box(*target['window_mm']);expected=p.box(*target['expected_local_material_box_mm'])
                o.shape(label+'-window',window,True);o.shape(label+'-expected',expected,True)
                actual=o.operation(label+'/whole_Common_window',lambda:parts[target['whole_body']].intersect(window))
                row['actual_export']=o.shape(label+'-actual',actual);patches[label]=actual
                extra=o.difference(label+'/actual_minus_expected',actual,expected)
                missing=o.difference(label+'/expected_minus_actual',expected,actual)
                o.shape(label+'-extra',extra);o.shape(label+'-missing',missing)
                values={'actual_mm3':p.volume(actual),'expected_mm3':p.volume(expected),
                        'actual_minus_expected_mm3':p.volume(extra),'expected_minus_actual_mm3':p.volume(missing)}
                require(all(finite(v)>=0 for v in values.values()),'invalid directed local material volume')
                require(values['actual_mm3']<=p.volume(window)+EPS,'Common exceeds complete window volume upper bound')
                matched=max(values['actual_minus_expected_mm3'],values['expected_minus_actual_mm3'],abs(values['actual_mm3']-values['expected_mm3']))<=EPS
                row.update({'evaluated':True,'status':'local_target_match' if matched else 'local_target_mismatch','passed':matched,**values})
            except BaseException as error:
                o.failure('native_or_preservation_exception',error)
                row.update({'status':'unresolved_native_or_preservation_error','exception_type':type(error).__name__})
                report['evaluation_failures'].append({'probe_id':label,'exception_type':type(error).__name__})
                if isinstance(error,(InterruptedError,TimeoutError,KeyboardInterrupt,SystemExit)):raise
            o.save(report)
        targets={x['probe_id']:x for x in spec['probes']}
        for control in spec['negative_controls']:
            budget_check()
            label=control['probe_id'];row={'probe_id':label,'evaluated':False,'expected':'positive oversized reference deficit'}
            report['negative_controls'].append(row)
            try:
                require(label in patches,'original local patch unavailable for negative control')
                bounds=[list(x) for x in targets[label]['expected_local_material_box_mm']]
                bounds[0][0]-=control['expected_reference_expand_each_X_side_mm'];bounds[1][0]+=control['expected_reference_expand_each_X_side_mm']
                expanded=p.box(*bounds);difference=o.difference(label+'/oversized_reference_minus_actual',expanded,patches[label])
                o.shape(label+'-negative-expanded',expanded,True);o.shape(label+'-negative-difference',difference)
                amount=p.volume(difference);require(finite(amount)>=0,'invalid negative-control volume')
                row.update({'evaluated':True,'positive_deficit_mm3':amount,'expected_rejection_observed':amount>EPS})
            except BaseException as error:
                o.failure('native_or_preservation_exception',error)
                row['exception_type']=type(error).__name__;report['evaluation_failures'].append({'negative_control':label,'exception_type':type(error).__name__})
                if isinstance(error,(InterruptedError,TimeoutError,KeyboardInterrupt,SystemExit)):raise
            o.save(report)
        report['execution_completed']=len(report['local_window_results'])==12 and len(report['negative_controls'])==2
        report['all_probes_evaluated']=all(x.get('evaluated') for x in report['local_window_results']+report['negative_controls'])
        report['local_material_targets_all_matched']=report['all_probes_evaluated'] and not report['evaluation_failures'] and all(x.get('passed') is True for x in report['local_window_results']) and all(x.get('expected_rejection_observed') is True for x in report['negative_controls'])
    except BaseException as error:
        o.failure('native_or_preservation_exception',error)
        report['evaluation_failures'].append({'scope':'worker','exception_type':type(error).__name__})
    finally:
        try:report['context_after']=finish_external(context_after)
        except BaseException as error:
            o.failure('native_or_preservation_exception',error)
            report['evaluation_failures'].append({'scope':'source_environment_postcheck','exception_type':type(error).__name__})
            report['local_material_targets_all_matched']=False
        o.save(report)
    return report


def run_reader(*,cq,p,spec_path,step_dir,producer,output,budget_check,context_before,context_after):
    """Separate process reimports original STEP and every saved scientific shape.

    Local masks/targets are freshly reconstructed. Saved actual local material
    is compared in both directions against a freshly intersected whole input.
    No producer clear flag substitutes for any of these computations.
    """
    spec=load_spec(spec_path);before=validate_external_context(p,context_before)
    require(context_before.get('separate_from_producer_process_verified') is True,'owned launcher must verify distinct producer/reader processes')
    prod_root=Path(producer);prod_path=prod_root/'report.json';original=json.loads(prod_path.read_text())
    require(original['schema']=='razr-K4-native-local-section-producer-v1' and original['spec_sha256']==SPEC_SHA,'bound original producer report required')
    require(original['API_source_sha256']==sha(__file__),'producer/reader exact API source bytes differ')
    o=Output(cq,p,output,budget_check,190,context_before['capture_error'])
    report={'schema':'razr-K4-separate-native-local-section-reader-v1','spec_sha256':SPEC_SHA,
        'API_source_sha256':sha(__file__),'producer_report':identity(prod_path),'execution_completed':False,
        'separate_process_verified_by_owned_launcher':True,'same_locked_kernel':True,'second_independent_kernel':False,
        'local_material_targets_all_matched':False,'context_before':before,'local_window_results':[],
        'negative_controls':[],'saved_geometry_readbacks':[],'STEP_BREP_whole_material_comparisons':[],
        'evaluation_failures':[],**FALSE_FLAGS}
    o.save(report);saved={};patches={}
    try:
        parts,inputs,faces=load_wholes(cq,p,step_dir,spec,budget_check)
        report['whole_inputs']=inputs;report['complete_native_face_inventory']=faces
        seen=set()
        require(len(original.get('all_scientific_exports',[]))<=128,'producer export count exceeds registered 64 BREP plus 64 STEP')
        for item in original.get('all_scientific_exports',[]):
            budget_check();name=item['name'];path=prod_root/name
            require(Path(name).name==name and name not in seen and path.is_file() and not path.is_symlink(),'saved original export absent or unsafe')
            require(identity(path)=={k:item[k] for k in ('bytes','sha256')},'saved native export bytes differ')
            seen.add(name)
            if name.endswith('.brep'):body=cq.Shape.importBrep(str(path))
            elif name.endswith('.step'):
                roots=cq.importers.importStep(str(path)).vals();require(len(roots)==1,'one saved STEP root required');body=roots[0]
            else:raise ValueError('unknown scientific shape format')
            sig=signature(p,body,item['positive_material_required'])
            require(sig['solid_count']==item['signature']['solid_count'] and abs(sig['signed_volume_mm3']-item['signature']['signed_volume_mm3'])<=EPS,'native export readback material signature differs')
            require(sig['valid_topology']==item['signature']['valid_topology'],'native export readback topology differs')
            saved[name]=body;report['saved_geometry_readbacks'].append({'name':name,**identity(path),'signature':sig});o.save(report)
        for name in sorted(saved):
            if not name.endswith('.step'):continue
            budget_check();stem=name[:-5];mate=stem+'.brep'
            require(mate in saved,'every positive original STEP needs its original BREP')
            a,b=saved[name],saved[mate]
            ab=o.difference(stem+'/STEP_minus_BREP',a,b)
            ba=o.difference(stem+'/BREP_minus_STEP',b,a)
            o.shape(stem+'-STEP-minus-BREP',ab);o.shape(stem+'-BREP-minus-STEP',ba)
            amounts=[p.volume(ab),p.volume(ba)]
            require(all(finite(v)>=0 for v in amounts),'invalid independent STEP/BREP directed volume')
            passed=max(amounts)<=EPS
            report['STEP_BREP_whole_material_comparisons'].append({'STEP':name,'BREP':mate,
                'STEP_minus_BREP_mm3':amounts[0],'BREP_minus_STEP_mm3':amounts[1],'evaluated':True,'passed':passed})
            if not passed:report['evaluation_failures'].append({'scope':'independent_STEP_BREP_material_mismatch','STEP':name})
            o.save(report)
        source_rows={x['probe_id']:x for x in original.get('local_window_results',[])}
        for target in spec['probes']:
            budget_check()
            label=target['probe_id'];row={'probe_id':label,'whole_body':target['whole_body'],'evaluated':False,'status':'unresolved'}
            report['local_window_results'].append(row)
            try:
                window=p.box(*target['window_mm']);expected=p.box(*target['expected_local_material_box_mm'])
                actual=o.operation(label+'/fresh_whole_Common_window',lambda:parts[target['whole_body']].intersect(window))
                signature(p,actual);patches[label]=actual;o.shape(label+'-readback-actual',actual)
                extra=o.difference(label+'/fresh_actual_minus_target',actual,expected)
                missing=o.difference(label+'/fresh_target_minus_actual',expected,actual)
                a=saved[label+'-actual.brep']
                old_extra=o.difference(label+'/saved_actual_minus_fresh',a,actual)
                old_missing=o.difference(label+'/fresh_actual_minus_saved',actual,a)
                for tag,shape in [('extra',extra),('missing',missing),('saved-extra',old_extra),('saved-missing',old_missing)]:o.shape(label+'-readback-'+tag,shape)
                values={'actual_mm3':p.volume(actual),'expected_mm3':p.volume(expected),
                    'actual_minus_expected_mm3':p.volume(extra),'expected_minus_actual_mm3':p.volume(missing),
                    'saved_actual_minus_fresh_mm3':p.volume(old_extra),'fresh_actual_minus_saved_mm3':p.volume(old_missing)}
                require(all(finite(v)>=0 for v in values.values()),'invalid independent directed volume')
                require(values['actual_mm3']<=p.volume(window)+EPS,'independent Common exceeds complete window upper bound')
                matched=max(values[k] for k in ('actual_minus_expected_mm3','expected_minus_actual_mm3','saved_actual_minus_fresh_mm3','fresh_actual_minus_saved_mm3'))<=EPS and abs(values['actual_mm3']-values['expected_mm3'])<=EPS
                declared=source_rows[label]
                agreement=declared.get('evaluated') is True and declared.get('passed')==matched and all(abs(values[k]-declared[k])<=EPS for k in ('actual_mm3','expected_mm3','actual_minus_expected_mm3','expected_minus_actual_mm3'))
                row.update({'evaluated':True,'passed':matched,'status':'local_target_match' if matched else 'local_target_mismatch',
                            'producer_numeric_and_classification_agreement':agreement,**values})
            except BaseException as error:
                o.failure('native_or_preservation_exception',error)
                row.update({'status':'unresolved_native_or_preservation_error','exception_type':type(error).__name__})
                report['evaluation_failures'].append({'probe_id':label,'exception_type':type(error).__name__})
                if isinstance(error,(InterruptedError,TimeoutError,KeyboardInterrupt,SystemExit)):raise
            o.save(report)
        targets={x['probe_id']:x for x in spec['probes']};old_controls={x['probe_id']:x for x in original.get('negative_controls',[])}
        for control in spec['negative_controls']:
            budget_check()
            label=control['probe_id'];row={'probe_id':label,'evaluated':False};report['negative_controls'].append(row)
            try:
                require(label in patches,'independent patch absent for control')
                bounds=[list(x) for x in targets[label]['expected_local_material_box_mm']]
                bounds[0][0]-=control['expected_reference_expand_each_X_side_mm'];bounds[1][0]+=control['expected_reference_expand_each_X_side_mm']
                expanded=p.box(*bounds);difference=o.difference(label+'/fresh_oversized_minus_actual',expanded,patches[label]);o.shape(label+'-readback-negative',difference)
                amount=p.volume(difference);require(finite(amount)>=0,'invalid independent negative volume')
                old=old_controls[label]
                row.update({'evaluated':True,'positive_deficit_mm3':amount,'expected_rejection_observed':amount>EPS,
                    'producer_agreement':old.get('evaluated') is True and abs(amount-old['positive_deficit_mm3'])<=EPS and old['expected_rejection_observed']==(amount>EPS)})
            except BaseException as error:
                o.failure('native_or_preservation_exception',error)
                row['exception_type']=type(error).__name__;report['evaluation_failures'].append({'negative_control':label,'exception_type':type(error).__name__})
                if isinstance(error,(InterruptedError,TimeoutError,KeyboardInterrupt,SystemExit)):raise
            o.save(report)
        report['execution_completed']=len(report['local_window_results'])==12 and len(report['negative_controls'])==2
        report['all_probes_evaluated']=all(x.get('evaluated') for x in report['local_window_results']+report['negative_controls'])
        report['local_material_targets_all_matched']=report['all_probes_evaluated'] and not report['evaluation_failures'] and all(x.get('passed') is True and x.get('producer_numeric_and_classification_agreement') is True for x in report['local_window_results']) and all(x.get('expected_rejection_observed') is True and x.get('producer_agreement') is True for x in report['negative_controls'])
    except BaseException as error:
        o.failure('native_or_preservation_exception',error)
        report['evaluation_failures'].append({'scope':'reader','exception_type':type(error).__name__})
    finally:
        try:report['context_after']=finish_external(context_after)
        except BaseException as error:
            o.failure('native_or_preservation_exception',error)
            report['evaluation_failures'].append({'scope':'source_environment_postcheck','exception_type':type(error).__name__})
            report['local_material_targets_all_matched']=False
        o.save(report)
    return report


if __name__=='__main__':
    raise SystemExit('Prepared API only: use the reviewed owned hosted launcher; no local or unguarded native entry point.')
