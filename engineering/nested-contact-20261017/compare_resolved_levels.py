"""Compare re-equilibrated levels, never fixed old tractions or point counts.

The boundary trace remains unchanged; this is interior-space sensitivity,
not global h/trace convergence. For nested volume spaces with recovered free
interiors, <u_coarse,u_fine>_Kfine equals the retained coarse vector paired
with condensed Kfine*u_fine, because the fine interior residual vanishes.
Thus E_fine+E_coarse-2*cross measures the elastic distance between the two
full fields without pretending their condensed matrices are identical.
It is a difference of two discrete solutions, not a continuum error bound.
"""
from pathlib import Path
import argparse,gzip,hashlib,json
import numpy as np
from scipy.sparse import load_npz

P=argparse.ArgumentParser(description=__doc__)
P.add_argument('--repo',type=Path,required=True);P.add_argument('--level1',type=Path,required=True);P.add_argument('--level2',type=Path,required=True);P.add_argument('--volume',type=Path,required=True);P.add_argument('--original',type=Path,required=True);P.add_argument('--output',type=Path,required=True)
P.add_argument('--levels',type=int,nargs='+',default=[0,1,2]);P.add_argument('--level2-audit',type=Path)
a=P.parse_args();assert a.levels in ([0,1],[1,2],[0,1,2]);assert not a.output.exists();a.output.mkdir(parents=True)
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
inputs={};reportrows={};displacements={};applied={};energy={};kfields={}
metafile=a.repo/'engineering/contact-field-20261015/coupled-field-audit.json.gz'
metas={m['patch']:m for m in json.loads(gzip.decompress(metafile.read_bytes()))['contact_patches']};inputs[str(metafile)]=sha(metafile)
for level in a.levels:
    base={0:a.repo/'engineering/preload-closure-20261017',1:a.level1,2:a.level2}[level]
    for case in (4,5,6,7):
        d=base/f'case-{case}';rf=d/('report.json.gz' if level==0 else 'report.json');ff=d/'full-fields.npz'
        r=json.loads(gzip.decompress(rf.read_bytes()) if level==0 else rf.read_text())
        vf=d/('independent-verification.json.gz' if level==0 else 'independent.json')
        if level==2 and a.level2_audit is not None:vf=a.level2_audit/f'case-{case}'/'independent.json'
        v=json.loads(gzip.decompress(vf.read_bytes()) if level==0 else vf.read_text())
        assert r['passed'] and v['discrete_solution_passed'] and v['original_common_cells']==5255
        assert v['minimum_gap_mm']>=-1e-7
        assert r['case']==case and r['load_index']==case%4 and r['spring_initial_over_Epanel_mm2']==.0002
        assert r['force_over_Epanel_mm2']==1e-5 and r['spring_compliance_times_Epanel_per_mm']==5. and r['nu']==.3 and r['Epanel_over_Eframe']==1.
        if level:assert r['volume_level']==v['nested_volume_level']==level
        for path in (rf,ff,vf):inputs[str(path)]=sha(path)
        z=np.load(ff,allow_pickle=False);lam=np.asarray(r['forces']);np.testing.assert_array_equal(z['lambda_forces'],lam)
        for body,key in (('panel','up'),('frame','uf')):
            displacements[level,case,body]=z[key];applied[level,case,body]=z['load_'+body]
        totals={name:{'normal_reaction_sum':0.,'panel_force':np.zeros(3),'panel_moment_about_origin':np.zeros(3)} for name in metas}
        for force,p in zip(lam[4:],r['contact_points'][4:]):
            m=metas[p['patch']];axis=m['normal_axis'];sgn=m['normal_sign'];tan=[i for i in range(3) if i!=axis]
            xyz=np.zeros(3);xyz[tan]=p['xy'];xyz[axis]=1.2 if axis==2 else sgn*36.325
            f=np.zeros(3);f[axis]=-sgn*force
            t=totals[p['patch']];t['normal_reaction_sum']+=float(force);t['panel_force']+=f;t['panel_moment_about_origin']+=np.cross(xyz,f)
        reportrows[level,case]={'level':level,'case':case,'minimum_gap_mm':v['minimum_gap_mm'],'contact_points':len(lam)-4,'bolt_tension_over_Epanel_mm2':lam[:4].tolist(),'patch_resultants':totals,'full_field_independent_audit_passed':True}

bodyinputs={}
for level in a.levels:
    for body in ('panel','frame'):
        folder=a.original/body if level==0 else a.volume/body/f'level-{level}'
        f=folder/'K.npz';K=load_npz(f).tocsc();inputs[str(f)]=sha(f)
        registered=json.loads((folder/'report.json').read_text());assert registered['K_sha256']==sha(f)
        inputs[str(folder/'report.json')]=sha(folder/'report.json')
        if level:
            assert registered['level']==level and registered['body_loads_on_added_internal_DOFs'] is False
        loadfile=folder/'loads.npz';inputs[str(loadfile)]=sha(loadfile)
        z=np.load(loadfile,allow_pickle=False);data={k:z[k] for k in z.files};bodyinputs[level,body]=data
        for case in (4,5,6,7):
            u=displacements[level,case,body];Ku=K@u;energy[level,case,body]=float(u@Ku);kfields[level,case,body]=Ku
            np.testing.assert_allclose(float(u@applied[level,case,body]),energy[level,case,body],rtol=1e-5,atol=1e-17)
        del K
# Logical load, coordinate and gauge identities are fixed across levels.
for body in ('panel','frame'):
    for level in a.levels[1:]:
        for key in ('F','C','D','R','xyz'):
            np.testing.assert_array_equal(bodyinputs[a.levels[0],body][key],bodyinputs[level,body][key])

for (level,case),row in reportrows.items():
    u=displacements[level,case,'panel'];j=case%4;F=bodyinputs[level,'panel']['F'][:,j]
    q=sum(bodyinputs[level,b]['C'].T@displacements[level,case,b] for b in ('panel','frame'))
    lam=np.asarray(row['bolt_tension_over_Epanel_mm2']);np.testing.assert_allclose(lam,.0002+q/5.,atol=1e-10,rtol=1e-8)
    E=sum(energy[level,case,b] for b in ('panel','frame'))
    row.update({'elastic_twice_energy_over_Epanel':E,'load_shape_weighted_displacement_mm':float(F@u),'external_work_over_Epanel':float(1e-5*F@u),'bolt_relative_displacement_mm':q.tolist(),'coupled_potential_over_Epanel':.5*E-float(1e-5*F@u)+.0002*float(q.sum())+.1*float(q@q)})

comparisons=[]
for coarse,fine in zip(a.levels[:-1],a.levels[1:]):
    for case in (4,5,6,7):
        c=reportrows[coarse,case];f=reportrows[fine,case]
        elastic_distance=0.
        components={}
        for body in ('panel','frame'):
            cross=float(displacements[coarse,case,body]@kfields[fine,case,body])
            val=energy[coarse,case,body]+energy[fine,case,body]-2*cross
            assert val>=-1e-5*max(energy[coarse,case,body],energy[fine,case,body])
            components[body]={'coarse_twice_energy':energy[coarse,case,body],'fine_twice_energy':energy[fine,case,body],'nested_cross_energy':cross,'signed_elastic_difference_energy':val}
            elastic_distance+=val
        qc=np.asarray(c['bolt_relative_displacement_mm']);qf=np.asarray(f['bolt_relative_displacement_mm'])
        pchanges={name: f['patch_resultants'][name]['normal_reaction_sum']-c['patch_resultants'][name]['normal_reaction_sum'] for name in metas}
        def relative(key):return (f[key]-c[key])/max(abs(c[key]),1e-300)
        comparisons.append({'case':case,'coarse_level':coarse,'fine_level':fine,'relative_load_displacement_change':relative('load_shape_weighted_displacement_mm'),'relative_elastic_twice_energy_change':relative('elastic_twice_energy_over_Epanel'),'coupled_potential_change':f['coupled_potential_over_Epanel']-c['coupled_potential_over_Epanel'],'nested_full_elastic_difference_energy':elastic_distance,'relative_nested_energy_distance_squared':elastic_distance/max(f['elastic_twice_energy_over_Epanel'],1e-300),'spring_difference_energy':float((qf-qc)@(qf-qc)/5.),'maximum_bolt_tension_change':float(np.max(abs(np.asarray(f['bolt_tension_over_Epanel_mm2'])-c['bolt_tension_over_Epanel_mm2']))),'patch_normal_force_changes':pchanges,'nested_energy_components':components})
        print('COMPARISON',coarse,fine,case,'LOAD_DISP_REL',comparisons[-1]['relative_load_displacement_change'],'ELASTIC_REL',comparisons[-1]['relative_elastic_twice_energy_change'],'ENERGY_DISTANCE2_REL',comparisons[-1]['relative_nested_energy_distance_squared'],flush=True)

result={'completed_levels':a.levels,'cases':list(reportrows.values()),'comparisons':comparisons,'input_sha256':inputs,'source_sha256':sha(__file__),'same_contact_tolerance_mm':1e-7,'all_re_equilibrated_not_frozen_old_tractions':True,'nested_volume_sensitivity_only':True,'same_original_surface_trace':True,'trace_refinement_performed':False,'continuum_error_bound_or_convergence_certified':False,'residual_contact_tolerance_not_separated_from_volume_effects':True,'point_reactions_not_area_pressure':True,'initial_spring_force_not_installed_preload':True,'all_reference_fixture_and_physical_unknowns_retained':True,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
for p,h in inputs.items():assert sha(p)==h
(a.output/'comparison.json').write_text(json.dumps(result,indent=2,default=lambda v:v.tolist(),allow_nan=False)+'\n')
print('COMPARISON_COMPLETED',len(comparisons),flush=True)
