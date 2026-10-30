"""Read-only exact directed trim-loop area and world boundary-flux audit.

No OCP import, native construction, Common or producer geometry-function reuse.
This adds an explicit bounded rectangular face realization/orientation check to
the already complete native inventories. Existing executed sources are unchanged.
"""
import argparse
import copy
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import resource
import time
import traceback


def need(value,message):
    if not value:raise ValueError(message)


def identity(path):
    path=Path(path)
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'path':str(path.resolve()),'bytes':path.stat().st_size,'sha256':digest}


def face_area(face):
    need(face['type']=='GeomAbs_Plane' and len(face['edge_uses'])==4,'complete four-trim plane required')
    need(face['orientation'] in ('TopAbs_FORWARD','TopAbs_REVERSED'),'oriented face required')
    area=F(0);segments=[]
    for edge in face['edge_uses']:
        need(edge['type']=='GeomAbs_Line','whole affine trim required')
        p,d=tuple(map(F,edge['origin_exact'])),tuple(map(F,edge['direction_exact']))
        a,b=map(F,edge['interval_exact']);need(a<b,'positive complete trim interval')
        need(edge['orientation'] in ('TopAbs_FORWARD','TopAbs_REVERSED'),'oriented trim required')
        x=tuple(p[i]+a*d[i] for i in range(2));y=tuple(p[i]+b*d[i] for i in range(2))
        if edge['orientation']=='TopAbs_REVERSED':x,y=y,x
        area+=(x[0]*y[1]-x[1]*y[0])/2
        segments.append((x,y))
    # Four straight edges must form one complete directed cycle. A signed-area
    # match without connectivity would not certify the bounded rectangular face.
    starts=[a for a,b in segments];ends=[b for a,b in segments]
    need(len(set(starts))==len(set(ends))==4 and set(starts)==set(ends),'single-degree directed rectangle graph')
    successors=dict(segments);point=starts[0];seen=set()
    while point not in seen:seen.add(point);point=successors[point]
    need(point==starts[0] and len(seen)==4,'one complete directed trim cycle')
    u0,u1,v0,v1=map(F,face['UV_exact'])
    need(u0<u1 and v0<v1,'positive full UV rectangle')
    expected=(u1-u0)*(v1-v0)*(1 if face['orientation']=='TopAbs_FORWARD' else -1)
    need(area==expected,'directed trim loop must bound finite rectangle with native face orientation')
    origin=tuple(map(F,face['origin_exact']));normal=tuple(map(F,face['normal_exact']))
    return {'face_id':face['id'],'signed_UV_area_exact':str(area),
            'exact_world_volume_flux_contribution':str(sum(a*b for a,b in zip(origin,normal))*area/3)}


def audit(item):
    inv=item['inventory'];need(len(inv['faces'])==6,'all six native faces required')
    faces=[face_area(face) for face in inv['faces']]
    flux=sum(F(row['exact_world_volume_flux_contribution']) for row in faces)
    expected=F(1)
    for a,b in item['bounds_exact']:expected*=F(b)-F(a)
    need(flux==expected>0,'exact outward boundary flux equals positive full box volume')
    return {'label':item['label'],'native_file':item['native_file'],'faces':faces,
            'exact_native_world_boundary_flux_volume':str(flux),'positive_directed_volume_retained':True,
            'finite_rectangle_trim_realization_verified':True}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    here=Path(__file__).resolve().parent
    result={'schema':'razr-r11-native-trim-orientation-and-flux-supplement-v1','completed':False,
            'source':identity(__file__),'native_or_CAD_calls':0,'items':[],'negative_controls':[],
            'original_product_source_filling_qualified':False,'full16_search_qualified':False}
    try:
        paths=[here/'hybrid-controls-attempt1/report.json',here/'independent-hybrid-controls-v2-attempt1/report.json',
               here/'original-root-masks-attempt1/report.json',here/'independent-original-root-masks-attempt1/report.json']
        docs=[json.loads(p.read_text()) for p in paths]
        need(docs[0]['execution_completed'] and all(doc['completed'] for doc in docs[1:]),'all actual prerequisite producer/reader reports completed')
        result['actual_prerequisites']=[identity(p) for p in paths];items=[]
        for case in docs[0]['cases']:
            inputs=[('source',case['source']),('carrier',case['carrier'])]+[(c['kind']+'-other',c['other']) for c in case['Commons']]
            for label,value in inputs:
                items.append({'label':f'control-case-{case["index"]}:{label}','native_file':value['native_file'],
                              'inventory':value['complete_boundary_inventory'],'bounds_exact':value['bounds_exact']})
        result['original_root_proof_bindings']=[]
        for frame in docs[2]['frames']:
            path=here/'original-root-masks-attempt1'/Path(frame['proof']['path']).name
            actual=identity(path);need(all(actual[k]==frame['proof'][k] for k in ('bytes','sha256')),'actual complete root proof unchanged')
            with gzip.open(path,'rt') as stream:proof=json.load(stream)
            value=proof['native_carrier'];items.append(dict(value,label=f'{frame["case_id"]}-frame-{frame["frame"]}'))
            result['original_root_proof_bindings'].append(actual)
        for item in items:
            actual=identity(item['native_file']['path']);need(actual==item['native_file'],'actual native object unchanged')
            result['items'].append(audit(item))
        for name,kind in [('reverse_one_whole_trim_loop','reverse'),('omit_one_trim_segment','omit')]:
            bad=copy.deepcopy(items[0]['inventory']['faces'][0])
            if kind=='reverse':
                for edge in bad['edge_uses']:
                    edge['orientation']='TopAbs_REVERSED' if edge['orientation']=='TopAbs_FORWARD' else 'TopAbs_FORWARD'
            else:bad['edge_uses'].pop()
            path=args.output/(name+'.json');path.write_text(json.dumps(bad,indent=2)+'\n')
            try:face_area(bad)
            except ValueError as exc:result['negative_controls'].append({'name':name,'rejected':True,'reason':str(exc),'input':identity(path)})
            else:raise ValueError('actual trim negative control accepted')
        result['totals']={'native_object_bindings':len(items),
                          'distinct_native_byte_identities':len({v['native_file']['sha256'] for v in items}),
                          'full_directed_trim_loops':sum(len(v['faces']) for v in result['items']),
                          'original_frame_native_carriers':len(docs[2]['frames']),
                          'negative_controls_rejected':len(result['negative_controls'])}
        result['completed']=True
    except Exception as exc:result['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    result['seconds']=time.monotonic()-start;result['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result.get(k) for k in ('completed','totals','seconds','peak_RSS_bytes','failure')}))
    if not result['completed']:raise SystemExit(1)


if __name__=='__main__':main()
