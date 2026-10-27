"""Actual L5 primitive controls and direct original saved EXTRUSION replay.

This file has no local CAD result. execute() is called only in the budgeted
hosted worker. Original method failures are retained separately from new-route
construction; neither a new route nor finite samples repair the old source.
"""
import math
import time
import cylindrical_sweep_l5 as l5


def execute(*,cq,p,emit,budget_check,checkpoint):
    rows=[]
    settings=[('ordinary',[(0.,0.),(2.,.25)]),('reversed',[(2.,.25),(0.,0.)]),
              ('zero',[(0.,0.),(0.,0.)]),('tiny',[(0.,0.),(0.,4.440892098500626e-16)])]
    for name,ends in settings:
        row={'name':name,'native_executed':False,'passed':False};rows.append(row);checkpoint(rows)
        budget_check();start=time.monotonic()
        def retain(label,body,positive=True):return emit('control-'+name,label,body,positive)
        row['construction']={}
        carrier,construction=l5.capsule(cq,p,ends,.5,1.,2.,emit=retain,label_prefix='capsule',audit=row['construction'])
        row['construction']=construction;row['carrier_BREP']=retain('whole-carrier',carrier)
        row['signed_volume_mm3']=p.volume(carrier);p.whole_material(carrier)
        row['source_disk_BREP']=retain('source-disk',p.single(cq.Solid.makeCylinder(.5,1.,cq.Vector(*ends[0],1.),cq.Vector(0,0,1))))
        row['finite_containment_crosschecks']=[]
        for i,t in enumerate((0.,.25,.5,.75,1.)):
            budget_check()
            point=[ends[0][j]+t*(ends[1][j]-ends[0][j]) for j in range(2)]
            sample=p.single(cq.Solid.makeCylinder(.5,1.,cq.Vector(*point,1.),cq.Vector(0,0,1)))
            outside=p.volume(sample.cut(carrier))
            row['finite_containment_crosschecks'].append({'parameter':t,'outside_mm3':outside})
            if not 0<=outside<=l5.TOL:
                row['failed_sample_BREP']=retain('sample-'+str(i),sample)
                raise ValueError('native primitive escaped certified source capsule')
        row.update(native_executed=True,passed=True,elapsed_seconds=time.monotonic()-start,
            finite_samples_do_not_establish_continuous_cover=True,formal_interval_CAD_certificate=False)
        checkpoint(rows)
    return {'native_controls_completed':True,'controls':rows,'original_seven_included_in_count':False}


def extrusion(*,source_shape,source_face,vector,cq,p,v2,emit,budget_check,checkpoint):
    import translation_regions as original
    report={'schema':'razr-L5-direct-original-EXTRUSION-control-v1','native_executed':False,
        'original_method_repaired':False,'complete_product_qualification':False}
    checkpoint(report);budget_check();p.whole_material(source_shape)
    faces=source_face.Faces()
    l5.require(len(faces)==1 and faces[0].geomType()=='EXTRUSION','saved original EXTRUSION face identity absent')
    kinds=[f.geomType() for f in source_shape.Faces()]
    l5.require('EXTRUSION' in kinds,'saved original temporary whole solid lost EXTRUSION surface')
    report['original_saved_whole_surface_types']=kinds
    report['original_vector_xyz']=vector
    start=time.monotonic()
    try:
        pieces,metadata=original.regions(source_shape,vector)
        for piece in pieces:p.whole_material(piece)
        report['unchanged_original_branch']={'executed':True,'outcome':'returned_without_original_failure',
            'region_count':len(pieces),'original_method_repaired':False}
    except Exception as exc:
        report['unchanged_original_branch']={'executed':True,'outcome':'original_failure_retained',
            'failure_type':type(exc).__name__,
            'same_unsupported_EXTRUSION_failure':type(exc) is ValueError and str(exc)=='unsupported advancing surface EXTRUSION',
            'original_method_repaired':False}
    report['unchanged_original_seconds']=time.monotonic()-start;checkpoint(report);budget_check()
    l5.require(report['unchanged_original_branch'].get('same_unsupported_EXTRUSION_failure') is True,
        'unchanged original EXTRUSION rejection classification changed')
    audit=[];regions,metadata=v2.regions(source_shape,vector,audit=audit)
    l5.require(0<len(regions)<=4096,'direct original EXTRUSION V2 region cap exceeded')
    report['new_V2_direct_EXTRUSION_route']={'native_executed':True,'metadata':metadata,'audit':audit,'regions':[]}
    for i,body in enumerate(regions):
        budget_check();p.whole_material(body)
        report['new_V2_direct_EXTRUSION_route']['regions'].append(emit('control-original-extrusion','v2-region-'+str(i),body,True))
    from translation_regions import subtract_regions
    report['finite_containment_checks']=[]
    for t in (0.,.25,.5,.75,1.):
        body=source_shape.translate(tuple(t*v for v in vector))
        outside=p.volume(subtract_regions(body,regions))
        report['finite_containment_checks'].append({'parameter':t,'outside_mm3':outside})
        l5.require(0<=outside<=l5.TOL,'direct EXTRUSION new region material escape')
    report.update(native_executed=True,new_V2_original_EXTRUSION_material_processed=True,
        new_V2_native_checks_passed=True,formal_interval_CAD_certificate=False,
        finite_samples_not_continuous_proof=True,old_original_failure_not_erased=True)
    checkpoint(report)
    return report
