"""Compare three nested volume spaces under identical frozen traction vectors.

This script audits rather than repairs contact: it never labels a frozen-force
field a newly solved unilateral contact solution. Three levels with unchanged
trace mesh are not a continuum convergence certificate.
"""
from pathlib import Path
import argparse,gzip,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
from contact_exchange import sha256,QuadraticGapBatch
from contact_patch_audit import triangle_coefficients,extrema


def main(a):
    a.output.mkdir(parents=True,exist_ok=False)
    rawpath=ROOT/'engineering/contact-field-20261015/common-cell-results.json.gz';metapath=ROOT/'engineering/contact-field-20261015/coupled-field-audit.json.gz'
    raw=json.loads(gzip.decompress(rawpath.read_bytes()));meta={m['patch']:m for m in json.loads(gzip.decompress(metapath.read_bytes()))['contact_patches']}
    ld={b:np.load(a.results/'volume-v3'/b/'level-0/loads.npz',allow_pickle=False) for b in ('panel','frame')}
    polygons=[];origins=[];tp=[];tf=[];dp=[];df=[];sign=[];initial=[]
    for group in raw:
        m=meta[group['patch']];tangent=[j for j in range(3) if j!=m['normal_axis']];origin=np.array(m['origin_tangent_mm'])
        for cell in group['cells']:
            ip=np.array(cell['panel_P2_dofs']);iff=np.array(cell['frame_P2_dofs']);dp.append(ip);df.append(iff)
            tp.append(triangle_coefficients(ld['panel']['xyz'][tangent][:,ip[:3]].T,np.eye(6),origin));tf.append(triangle_coefficients(ld['frame']['xyz'][tangent][:,iff[:3]].T,np.eye(6),origin))
            polygons.append(cell['polygon']);origins.append(origin);sign.append(m['normal_sign']);initial.append(m['initial_gap_mm'])
    tp=np.asarray(tp);tf=np.asarray(tf);dp=np.asarray(dp);df=np.asarray(df);sign=np.asarray(sign);initial=np.asarray(initial)
    assert len(polygons)==5255;batch=QuadraticGapBatch(polygons,origins);rows=[]
    for case in (4,5,6,7):
        olddir=ROOT/'engineering/preload-closure-20261017'/f'case-{case}';old=np.load(olddir/'full-fields.npz',allow_pickle=False)
        levels=[]
        for level in (0,1,2):
            fields={};energy=0.;body_metrics={}
            for b in ('panel','frame'):
                if level==0:u=old['up' if b=='panel' else 'uf'];f=old['load_'+b];item={'new_fTu':float(f@u),'old_fTu':float(f@u),'max_displacement_change_mm':0.}
                else:
                    folder=a.results/f'frozen-v2-{b}-L{level}';d=np.load(folder/f'case-{case}.npz',allow_pickle=False);u=d['u'];f=d['load'];item=json.loads((folder/f'case-{case}.json').read_text());assert np.array_equal(f,old['load_'+b])
                fields[b]=u;energy+=float(f@u);body_metrics[b]=item
            c=-sign[:,None]*(np.einsum('ijk,ik->ij',tp,fields['panel'][dp])-np.einsum('ijk,ik->ij',tf,fields['frame'][df]));c[:,0]+=initial
            audit=batch.extrema(c);negative=int(np.sum(audit['minimum'] < -1e-7))
            if level==0:assert negative==0,'historical accepted baseline must reproduce'
            # Independent unchanged scalar check on every cell, not just the worst.
            maximum=0.
            for i,poly in enumerate(polygons):
                ref=extrema(c[i],poly,origins[i]);maximum=max(maximum,abs(ref['minimum']-audit['minimum'][i]),abs(ref['maximum']-audit['maximum'][i]))
            assert maximum<1e-10
            np.savez_compressed(a.output/f'case-{case}-level-{level}-gaps.npz',**{k:v for k,v in audit.items() if isinstance(v,np.ndarray)})
            row={'case':case,'level':level,'total_fTu':energy,'minimum_gap_mm':float(np.min(audit['minimum'])),'negative_cells_beyond_tolerance':negative,'scalar_batch_max_error_mm':maximum,'body_metrics':body_metrics,
                 'same_old_traction_vectors':True,'new_unilateral_contact_solution':level==0}
            levels.append(row);print('FROZEN_GAP',case,level,negative,row['minimum_gap_mm'],flush=True)
        j0,j1,j2=[x['total_fTu'] for x in levels];assert j1>=j0-1e-10*abs(j0) and j2>=j1-1e-10*abs(j1)
        rows.append({'case':case,'levels':levels,'relative_compliance_change_L1_over_L0':j1/j0-1,'relative_compliance_change_L2_over_L1':j2/j1-1,'increment_ratio_not_error_estimate':(j2-j1)/(j1-j0),
                     'new_contact_solved_at_refined_levels':False,'volume_or_contact_convergence_certified':False})
    summary={'base_main':'85a86ce6e15e48186afcdf36ec665ebb7a902653','cases':rows,'original_common_cells':5255,'states_audited':12,'same_global_trace_space':True,'CAD_or_material_or_initial_loads_changed':False,
             'audit_complete':True,'refined_contact_resolve_required':True,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,
             'source_sha256':sha256(__file__),'common_cells_sha256':sha256(rawpath),'contact_metadata_sha256':sha256(metapath)}
    (a.output/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
