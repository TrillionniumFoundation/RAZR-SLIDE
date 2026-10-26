"""Materialize current product input gaps and new, unapproved G3-G5 templates."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'integration'))
import product_qualification as qualification


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(output):
    output = Path(output)
    if output.exists(): raise ValueError('new delivery directory required')
    output.mkdir(parents=True)
    plans = qualification.templates(ROOT)
    for gate,plan in plans.items():
        (output/(gate+'-plan.template.json')).write_text(json.dumps(plan,indent=2)+'\n')
        evaluator = qualification.evaluate_g4 if gate == 'G4' else qualification.evaluate_g5
        result = evaluator(plan,None,ROOT,output)
        (output/(gate+'-current-readiness.json')).write_text(json.dumps(result,indent=2)+'\n')
    legacy = ROOT/'engineering/product-integration-20261018/physical-test-followon-20261019'
    plan = json.loads((legacy/'qualification-plan.template.json').read_text())
    specimen = json.loads((legacy/'as-built-specimen.template.json').read_text())
    base = qualification.binding(ROOT)
    candidate_file = 'design/product_routing_ep5.json'; generator = 'integration/product_routing_ep5.py'
    assembly = 'integration/product_assembly.py'
    base['files_sha256'].update({p:digest(ROOT/p) for p in (generator,assembly)})
    base['artifact_roles'] = {'cad':['design/product_geometry.json',assembly],
        'routing':[candidate_file,generator],'bom':[],'drawings':[],
        'material':[],'process':[],'firmware':[]}
    base['routing_candidate'] = {'candidate_id':base.pop('candidate_id'),
        'configuration_path':candidate_file,'configuration_sha256':base['files_sha256'][candidate_file],
        'generator_path':generator,'generator_sha256':base['files_sha256'][generator]}
    plan.update(schema='razr-unpowered-motion-qualification-plan-v2',design_binding=base)
    specimen.update(schema='razr-as-built-qualification-specimen-v2',design_binding=copy.deepcopy(base))
    old = specimen.get('role_observations',{}); old['routing'] = old.pop('ep4',{})
    for role,item in old.items(): item['design_paths'] = base['artifact_roles'][role]
    (output/'G3-EP5-plan.template.json').write_text(json.dumps(plan,indent=2)+'\n')
    (output/'G3-EP5-as-built.template.json').write_text(json.dumps(specimen,indent=2)+'\n')
    records = []
    folder = ROOT/'engineering/product-integration-20261018/hardware/records'
    for path in sorted(folder.glob('*/record.json')):
        record = json.loads(path.read_text())
        records.append({'path':path.relative_to(ROOT).as_posix(),'sha256':digest(path),
            'schema':record.get('schema'),'specimen_id':record.get('specimen_id'),
            'measurement_method':record.get('measurement_method'),'summary':record.get('summary')})
    interfaces = json.loads((ROOT/'design/product_interfaces.json').read_text())
    source_paths = ['design/product_interfaces.json','design/product_geometry.json','design/product_routing_ep5.json',
        'engineering/controlled-inputs-web-20261013-r6/candidate_facts.json',
        'engineering/oled-orderable-module-search-20261013-r5/extracted-tdo-inputs.json',
        'engineering/fpc-felios-primary-search-20261013-r6/source_facts.json']
    result = {'schema':'razr-current-product-input-readiness-v1',
        'local_original_records':records,'current_physical_inputs':qualification.product_inputs(ROOT),
        'local_adb_binary_available':shutil.which('adb') is not None,
        'new_donor_or_hardware_measurement_executed':False,
        'original_remote_donor_host_probed':False,
        'supplier_contact_or_procurement_executed':False,
        'actual_OEM_interfaces_assigned':False,
        'product_cell_budget':interfaces['cell_budget'],
        'controlled_reference_source_sha256':{p:digest(ROOT/p) if (ROOT/p).is_file() else None for p in source_paths},
        'scope':'Existing repository originals inspected; no new physical observations inferred.',
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (output/'physical-input-inventory.json').write_text(json.dumps(result,indent=2)+'\n')
    return {'output':str(output),'original_hardware_record_count':len(records),
            'G4_status':'unknown','G5_status':'unknown','new_G3_candidate':base['routing_candidate']['candidate_id']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(build(parser.parse_args().output),indent=2))
