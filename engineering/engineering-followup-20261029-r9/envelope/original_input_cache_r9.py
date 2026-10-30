"""One complete producer/reader inventory read per fresh all-frame attempt.

Only immutable original materials and their parsed models are cached. No prior
refinement tree, node result or timed computation is reused.
"""
import gc
import gzip
import json
from pathlib import Path
from cylinder_slab_r9 import common,math


class Inputs:
    def __init__(self,root):
        self.root=Path(root)
        self.base=self.root/'r7-recovery/v7/r5-local-v7/input-snapshot-v1/base-v6/all-primitive-support-frames'
        self.report_path=self.base/'report.json'
        self.original=json.loads(self.report_path.read_text())
        self.report_identity=common.identity(self.report_path)
        required=set()
        for row in self.original['frames']:
            path=self.base/Path(row['certificate']['path']).name
            with gzip.open(path,'rt') as stream:certificate=json.load(stream)
            required.update(tuple(source['material_key']) for source in certificate['boundary_refinement']['sources'])
        contract=json.loads((self.root/'r7-envelope/edge189-source-diagnostic-v1/R7E_EDGE189_LINE_SUPPORT_DIAGNOSTIC_CONTRACT_V1.json').read_text())
        selected=[];self.native_identities=[]
        for kind in ('producer','reader'):
            path=self.root/'r7-recovery/r3e/native-and-math'/kind/'worker/report.json'
            ident=common.identity(path);ref=contract['inputs']['native_original_'+kind]
            common.need(all(ident[k]==ref[k] for k in ('bytes','sha256')),'native original inventory identity changed')
            doc=json.loads(path.read_text())
            common.need(doc['execution_completed'] and len(doc['operands'])==53,'complete native inventory required')
            materials={(row['input']['case_id'],row['input']['material_id']):row for row in doc['operands']
                       if (row['input']['case_id'],row['input']['material_id']) in required}
            common.need(set(materials)==required,'all required original materials present')
            selected.append(materials);self.native_identities.append(ident)
            del doc;gc.collect()
        common.need(selected[0]==selected[1],'complete selected producer/reader material mismatch')
        self.materials=selected[0];self.models={}
        for key,material in self.materials.items():
            boundary=material['boundary'];common.need(not boundary['incomplete_inventory'],'complete original boundary')
            for plural in ('faces','edges','vertices'):
                common.need(len(boundary[plural])==boundary['counts'][plural],'whole boundary census differs')
            mapping={}
            for kind,plural in (('face','faces'),('edge','edges')):
                for record in boundary[plural]:mapping[(kind,record['index'])]=math.source_model(record,kind)
            self.models[key]=mapping

    def load(self,case,frame):
        row=next(r for r in self.original['frames'] if r['case_id']==case and r['frame']==frame)
        path=self.base/Path(row['certificate']['path']).name;ident=common.identity(path)
        common.need(all(ident[k]==row['certificate'][k] for k in ('bytes','sha256')),'original V6 certificate identity changed')
        with gzip.open(path,'rt') as stream:certificate=json.load(stream)
        common.need(certificate['frame']=={k:v for k,v in row.items() if k!='certificate'},'certificate/report frame differs')
        keys=[tuple(s['material_key']) for s in certificate['boundary_refinement']['sources']]
        return row,certificate,[self.models[k] for k in keys],self.native_identities+[self.report_identity,ident],{k:self.materials[k] for k in keys}
