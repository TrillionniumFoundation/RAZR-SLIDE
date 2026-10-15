"""Independent native verification of fixed finite-wall counterbore webs.

Checks every old material identity and actual full scene/declared movement.
Meshability is checked separately with the supplemental pinned Gmsh runner;
no CAD-Boolean pass is relabeled as stiffness or manufacturing qualification.
"""
from pathlib import Path
import argparse,json,sys
import verify_frame_nut_anchor as n
v=n.v
e=n.e
ROOT=Path(__file__).resolve().parents[1]
BODY={s+'_'+r for s in 'LR' for r in ('PAWL','SHOULDER_PIN_NOMINAL','TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL','ROOF','ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL','GUIDE_REFERENCE','ROOT_OUTER','ROOT_INNER','OLD_COVER')}|{'A_BACK_PANEL'}


def additions():
    shapes={}
    for side,sign in [('L',-1),('R',1)]:
        x=sign*11.6
        for i,y in enumerate((14.5,29.6)):
            for j,(lo,hi) in enumerate(((x-1.1,x-.95),(x+.95,x+1.1))):
                shapes[f'{side}_{i}_{j}']=v.box((lo,y-1.1,.60),(hi,y+1.1,2.00))
    return shapes


def partition_certificate(before, after):
    """Exact four local boxes plus the complete complement, no tolerance relaxation.

    The original tangent counterbores made a whole-shape difference return
    inconsistent full-volume results. Reject that difference certificate;
    partition BOTH complete bodies, independently reconstruct each change,
    require unchanged complement, and close both original volume sums.
    """
    outside_a=before;outside_b=after;rows=[]
    for side,sign in [('L',-1),('R',1)]:
        for i,y in enumerate((14.5,29.6)):
            x=sign*11.6;window=v.box((x-1.2,y-1.2,.5),(x+1.2,y+1.2,2.1))
            a=before.intersect(window);b=after.intersect(window);expected=a
            for name,piece in additions().items():
                if name.startswith(f'{side}_{i}_'):expected=expected.fuse(piece).clean()
            same=v.equal(expected,b);av=v.vol(a);bv=v.vol(b)
            if bv<av-v.TOL:raise ValueError('local original material lost')
            rows.append({'side':side,'index':i,'before_mm3':av,'after_mm3':bv,'exact_union_difference_mm3':same})
            outside_a=outside_a.cut(window).clean();outside_b=outside_b.cut(window).clean()
    same=v.equal(outside_a,outside_b)
    va=v.vol(before);vb=v.vol(after);ca=v.vol(outside_a);cb=v.vol(outside_b)
    if abs(va-ca-sum(x['before_mm3'] for x in rows))>v.TOL or abs(vb-cb-sum(x['after_mm3'] for x in rows))>v.TOL:
        raise ValueError('partition omitted original or new material')
    return {'local_regions':rows,'complement_difference_mm3':same,'before_volume_mm3':va,'after_volume_mm3':vb,
            'before_complement_mm3':ca,'after_complement_mm3':cb,'gain_mm3':vb-va,'loss_mm3':0.,
            'whole_ambiguous_tangent_difference_not_accepted':True,'all_material_partitioned':True}


def verify(baseline,manifest,output,full=False):
    output=Path(output)
    if output.exists():raise ValueError('new output required')
    bm,before,h=n.load(baseline,BODY);meta,after,h2=n.load(manifest,BODY);h.update(h2)
    if meta['baseline_manifest_sha256']!=v.sha(baseline) or bm['source_sha256']!=v.sha(ROOT/'integration/frame_nut_anchor.py'):raise ValueError('wrong baseline')
    pieces=additions();expected=before['A_BACK_PANEL'];joins=[]
    for key,b in pieces.items():
        joint=v.common(before['A_BACK_PANEL'],b)
        if joint<=v.TOL:raise ValueError('web has no volumetric panel attachment')
        joins.append({'key':key,'overlap_mm3':joint});expected=v.single(expected.fuse(b).clean())
    v.equal(expected,after['A_BACK_PANEL'])
    changed={'A_BACK_PANEL'}
    for key in set(before)-changed:v.equal(before[key],after[key])
    material=partition_certificate(before['A_BACK_PANEL'],after['A_BACK_PANEL']);loss=material['loss_mm3'];gain=material['gain_mm3']
    parent,prior,old,profiles=e.v.parent_native(h);base={k:after[k] for k in BODY};slots={s:e.native_slot(after[s+'_TAB']) for s in 'LR'}
    cases=[(s,d,u,c,p) for s,d,u in ((0.,0.,0.),(0.,0.,3.),(40.,0.,3.),(79.75,8.2,3.)) for c,p in ((0.,0.),(.02,.07))]
    scenes=[];shifts=[];paths=[];assembly=[];failures=[]
    for idx,args in enumerate(cases if full else cases[:1]):
        whole,_,_=n.scene(after,base,parent,prior,old,profiles,slots,args)
        rows=e.v.w.pairs(whole,None if idx==0 else {'A_BACK_PANEL'});bad=n.check_rows(rows);failures+=bad
        scenes.append({'args':args,'participants':83,'pairs':rows,'bad':bad});print('SCENE',idx,len(rows),'BAD',bad,flush=True)
        if idx==0:home=whole
        if full:
            for dx in (-.02,.02):
                _,moving,fixed=n.scene(after,base,parent,prior,old,profiles,slots,args,dx)
                rows=n.p.cross_pairs(moving,fixed);bad=n.check_rows(rows);failures+=bad
                shifts.append({'state':idx,'dx':dx,'pairs':rows,'bad':bad})
    if full:
        for idx in (0,7):
            _,moving,fixed=n.scene(after,base,parent,prior,old,profiles,slots,cases[idx],-.02)
            nuts={k:b for k,b in fixed.items() if '_NUT_' in k}
            for key,body in moving.items():
                if key=='A_BACK_PANEL':
                    row=n.p.panel_motion_with_exact_screw_voids(body,(.04,0,0),{k:b for k,b in fixed.items() if k not in nuts})
                    for name,b in nuts.items():
                        bb=b.BoundingBox();cage=v.box((bb.xmin-.04,bb.ymin,bb.zmin),(bb.xmax,bb.ymax,bb.zmax));value=v.common(body,cage)
                        item={'fixed':name,'method':'inverse_nut_box','common_mm3':[value],'clear':value<=v.TOL};row['checks'].append(item)
                        if value>v.TOL:row['failed'].append(item)
                else:row=e.v.motion(key,body,(.04,0,0),fixed)
                paths.append(row);failures+=row['failed']
            print('DECK_PATH',idx,'FAILED',sum(len(x['failed']) for x in paths),flush=True)
        prior_service=e.frozen(h);detachable={s+'_'+r for s in 'LR' for r in e.v.INSERT_ROLES}
        installed={k:b for k,b in home.items() if k not in detachable|{'A_FRAME','B_SHELL'}}
        for side in 'LR':
            for key,move in e.v.plan(side):
                if key.endswith('_ROOF'):
                    kept=v.single(prior_service[key].cut(n.p.w.w.relief(side)).clean());row=e.roof_motion_partition(key,home[key],kept,move,installed)
                else:row=e.v.motion(key,home[key],move,installed)
                assembly.append(row);failures+=row['failed'];installed[key]=home[key]
                print('ASSEMBLY',key,'BAD',len(row['failed']),flush=True)
    outside=v.vol(after['A_BACK_PANEL'].cut(old['A_OUTER']))
    if outside>v.TOL:failures.append({'outside_original_A':outside})
    if any(v.sha(f)!=s for f,s in h.items()):raise ValueError('input changed')
    if 'panel_bearing_web' in sys.modules:raise ValueError('candidate generator imported')
    report={'source_sha256':meta['source_sha256'],'reader_sha256':v.sha(__file__),'input_sha256':h,'templates':34,'unchanged_templates':33,'physical_parts':83,
            'panel_added_mm3':gain,'panel_removed_mm3':loss,'material_partition':material,'web_joins':joins,'nominal_X_wall_mm':.15,'old_nominal_X_wall_mm':0.,
            'scenes':scenes,'shifted_decks':shifts,'whole_deck_X_paths':paths,'detached_control_insertions':assembly,'failure_pairs':failures,'passed':not failures,
            'all_prior_native_tasks_or_upstream_complete_assembly_rerun':False,'same_CAD_kernel':True,'candidate_builder_imported':False,
            'elasticity_qualification_is_not_this_geometric_check':True,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    with output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print('WEB_RESULT',report['passed'],flush=True);return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--full',action='store_true');a=p.parse_args()
    r=verify(a.baseline,a.manifest,a.output,a.full);raise SystemExit(0 if r['passed'] else 1)
