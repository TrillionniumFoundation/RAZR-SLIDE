from pathlib import Path
import ast
R=Path('/home/qian-qi/RAZR-SLIDE-nested-contact-20261017')
p=R/'engineering/volume-convergence-20261017/solve_enriched_contact.py'
s=p.read_text()
s=s.replace('NOT reused. Original case6 point locations/forces are optimizer seeds only.','NOT reused across energies. A same-energy, hash-bound checkpoint may resume.\nOriginal case6 point locations/forces are optimizer seeds only on fresh runs.')
anchor='def main(a):'
helper='''def read_same_energy_state(state, inputs, level, repo, output):
    """Resume only the exact energy/loads/domains; a level label alone is insufficient.

    Older PR28 manifests have no explicit level field, so their immutable
    per-body level/K identities are also required. No old contact pass is
    inherited: each requested case is solved and audited again.
    """
    if type(level) is not int or level not in (1, 2):
        raise ValueError('invalid volume level')
    state, inputs, repo, output = map(lambda x: Path(x).resolve(), (state, inputs, repo, output))
    if state == output or state in output.parents or output in state.parents:
        raise ValueError('checkpoint and output overlap')
    manifest = state/'manifest.json'
    saved = json.loads(manifest.read_text())
    if (saved.get('gap_tolerance_mm') != GAP_TOLERANCE
            or saved.get('state_is_finite_QP_not_gap_qualification') is not True
            or type(saved.get('case')) is not int or saved['case'] not in range(8)):
        raise ValueError('invalid finite state identity')
    if 'volume_level' in saved and saved['volume_level'] != level:
        raise ValueError('checkpoint volume level differs')
    prior = saved.get('input_sha256')
    if not isinstance(prior, dict) or not prior:
        raise ValueError('missing checkpoint provenance')
    # Validate recorded dependencies before trusting any stored matrix/map.
    for name, digest in prior.items():
        if not isinstance(digest, str) or len(digest) != 64 or sha256(Path(name)) != digest:
            raise ValueError('changed checkpoint dependency: '+str(name))
    required = {}
    for body in ('panel', 'frame'):
        for filename in ('K.npz', 'loads.npz', 'mesh.npz', 'report.json'):
            suffix = f'/{body}/level-{level}/{filename}'
            current = inputs/body/f'level-{level}'/filename
            required[suffix] = sha256(current)
    for filename in ('common-cell-results.json.gz', 'coupled-field-audit.json.gz'):
        required['/engineering/contact-field-20261015/'+filename] = sha256(repo/'engineering/contact-field-20261015'/filename)
    for filename in ('assembly_inputs.json','roof_joint_load_inputs.json','frame_thread_actual_inputs.json'):
        required['/integration/'+filename] = sha256(repo/'integration'/filename)
    for suffix, digest in required.items():
        matching = [h for name,h in prior.items() if str(Path(name)).endswith(suffix)]
        if not matching or any(h != digest for h in matching):
            raise ValueError('checkpoint energy, domain or physical-input identity differs: '+suffix)
    for name,key in (('response.npz','response_sha256'),('points.json','points_sha256')):
        if sha256(state/name) != saved.get(key):
            raise ValueError('checkpoint payload changed: '+name)
    return saved


'''
assert anchor in s and 'def read_same_energy_state' not in s;s=s.replace(anchor,helper+anchor,1)
old="    resumed=None\n    if a.resume_state is not None:raise ValueError('old energy checkpoints cannot be restored into an enriched K')"
new="""    resumed=None
    if a.resume_state is not None:
        a.resume_state=a.resume_state.resolve()
        resumed=read_same_energy_state(a.resume_state,a.inputs,a.volume_level,a.repo,a.output)
        response_file=a.resume_state/'response.npz';point_file=a.resume_state/'points.json'
        with np.load(response_file,allow_pickle=False) as data:
            checkpoint={k:data[k] for k in data.files}
        seed={'contact_points':json.loads(point_file.read_text()),'forces':checkpoint['forces']}
""".rstrip()
assert old in s;s=s.replace(old,new,1)
start="    before=time.monotonic();print('NEW_ENERGY_RESPONSES',len(points),flush=True)"
end="    # Recompute low-dimensional maps from the unchanged full force maps. Never"
a=s.index(start);b=s.index(end,a);block=s[a:b]
s=s[:a]+"    if resumed is None:\n"+''.join('    '+line if line.strip() else line for line in block.splitlines(True))+"    else:\n        checked=cache.restore(C,checkpoint['H'],cache.identity,probes=5)\n        print('SAME_ENERGY_CHECKPOINT_RESTORED',len(points)-4,checked,flush=True)\n"+s[b:]
anchor="    print('ALL_POINT_RESPONSES_RECOMPUTED_FOR_CHANGED_ENERGY',len(points)-4,flush=True)"
replacement="""    if resumed is not None:
        np.testing.assert_allclose(G,checkpoint['G'],rtol=1e-8,atol=2e-8)
        np.testing.assert_allclose(qfree,checkpoint['qfree'],rtol=2e-7,atol=1e-8)
        np.testing.assert_array_equal(initialgap,checkpoint['initialgap'])
        np.testing.assert_allclose(loadG,checkpoint['loadG'],rtol=1e-10,atol=1e-10)
    print('POINT_RESPONSE_IDENTITY_READY',len(points)-4,'same_energy_resume',resumed is not None,flush=True)"""
assert anchor in s;s=s.replace(anchor,replacement,1)
s=s.replace("{'old_response_reused':False,'old_locations_and_forces_are_initialization_only':True,'input_sha256':hashes}","{'old_response_reused_across_energies':False,'same_energy_response_restored':resumed is not None,'old_locations_and_forces_are_initialization_only':True,'input_sha256':hashes}")
s=s.replace("dump(snap/'manifest.json',{'case':case,'exchange':exchange,'input_sha256':hashes,","dump(snap/'manifest.json',{'case':case,'exchange':exchange,'volume_level':a.volume_level,'input_sha256':hashes,")
s=s.replace("'whole_field_reconstructed_by_one_exact_response':True,'volume_level':enriched['level']", "'whole_field_reconstructed_by_one_exact_response':True,'same_energy_checkpoint_restored':resumed is not None,'volume_level':enriched['level']")
ast.parse(s);p.write_text(s)
print('PATCHED',p,'same-energy resume only; fresh solve and physics unchanged')
