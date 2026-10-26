"""Post-K1 factory adapter. No adoption before two actual complete clear witnesses.

The caller must retain the immutable-S4 source/environment audit and original
owned capacity supervision. This module does not extend ContactProfile or
reinterpret an unsupported physical motion as admissible.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import itertools
import json
from pathlib import Path

S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
NAME='key_forward_loop_v1'
TOL=1e-7


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def compare(a,b,p):
    values=(p.volume(a.cut(b)),p.volume(b.cut(a)))
    require(all(0<=v<=TOL for v in values),'complete material difference exceeds original predicate')
    return {'a_minus_b_mm3':values[0],'b_minus_a_mm3':values[1]}


@dataclass(frozen=True)
class VerifiedKeys:
    original_q0:dict
    candidate_q0:dict
    receipt:dict


def load_keys(artifact_roots,binding,p,cq,budget):
    """Load only after externally frozen K1 artifact identities are supplied.

    binding: actual run/source IDs, candidate_source_sha256, contract_sha256 and
    poses[near/far].engineering_manifest_sha256. No prepared plan is a binding.
    """
    require(binding.get('actual_two_clear_witnesses_reviewed') is True,'actual dual-pose K1 clearance required')
    require(set(artifact_roots)==set(binding['poses'])=={'near','far'},'both exact K1 poses required')
    readback_keys={};receipts={}
    for pose in ('near','far'):
        root=Path(artifact_roots[pose]).resolve();manifest=root/'ENGINEERING_MANIFEST.json'
        require(sha(manifest)==binding['poses'][pose]['engineering_manifest_sha256'],'frozen K1 engineering manifest differs')
        members=json.loads(manifest.read_text())['members']
        for rel,entry in members.items():
            path=(root/rel).resolve()
            require(path.is_relative_to(root) and path.is_file() and not path.is_symlink(),'unsafe or absent K1 engineering member')
            require(sha(path)==entry['sha256'] and path.stat().st_size==entry['bytes'],'K1 engineering byte identity differs')
        reports={}
        for kind in ('factory','readback'):
            wrapper=json.loads((root/kind/'worker/report.engineering.json').read_text())
            require(wrapper.get('derived_projection_not_raw_original') is True,'explicit original-report projection required')
            r=wrapper['engineering_record'];reports[kind]=(wrapper,r)
            require(r.get('pose')==pose and r.get('functional_source_commit')==S4 and r.get('candidate_name')==NAME,
                    'K1 source, pose or named candidate differs')
            require(r.get('execution_completed') is True and r.get('finite_pose_clear') is True
                    and r.get('all_unordered_pairs_present_once') is True
                    and not r.get('evaluation_failures') and not r.get('mismatches_to_factory'),
                    'actual complete clear K1 producer and reader required')
            names=r['participant_names'];actual=[(x['a'],x['b']) for x in r['pairs']]
            require(len(set(names))==154 and len(actual)==11781 and actual==list(itertools.combinations(sorted(names),2)),
                    'complete K1 body-pair inventory differs')
            require(not any(x.get('rejected') or x['common_mm3']>TOL for x in r['pairs']),'K1 has a real rejected pair')
            ident=r['source_identity_projection']
            require(ident['source_commit_before']==ident['source_commit_after']==S4
                    and ident['worktree_clean_before'] is True
                    and ident['source_bytes_and_locked_environment_unchanged'] is True
                    and ident['locked_environment_before_passed'] is True
                    and ident['locked_environment_after_passed'] is True
                    and ident['checked_package_count_before']==ident['checked_package_count_after']==43,
                    'K1 original source/environment projection incomplete')
        fw,f=reports['factory'];rw,r=reports['readback']
        require(r['factory_report_sha256']==fw['original']['sha256'],'independent reader bound to different K1 producer')
        require(f['candidate_application']['source_sha256']==binding['candidate_source_sha256']
                and r['candidate_contract_sha256']==binding['contract_sha256'],'frozen named source/contract differs')
        require(r['native_STEP_readback_executed'] is True and len(r['body_readbacks'])==154
                and all(x['passed'] for x in r['body_readbacks'].values())
                and set(r['material_reconstruction'])=={'L_KEY','R_KEY'}
                and all(x['passed'] for x in r['material_reconstruction'].values()),'whole candidate material readback incomplete')
        shapes={}
        for side in 'LR':
            name=side+'_KEY';shapes[side]={}
            for role in ('original_q0','candidate_q0'):
                budget.check();entry=f['candidate_material_exports'][name][role]['files']['step']
                path=(root/'factory/worker'/entry['path']).resolve()
                require(path.is_relative_to(root) and sha(path)==entry['sha256'],'frozen KEY material STEP differs')
                roots=cq.importers.importStep(str(path)).vals();require(len(roots)==1,'one complete KEY STEP root required')
                shapes[side][role]=p.single(roots[0])
        readback_keys[pose]=shapes
        receipts[pose]={'engineering_manifest_sha256':sha(manifest),
            'factory_original_report_sha256':fw['original']['sha256'],
            'reader_original_report_sha256':rw['original']['sha256']}
    equality={side:{role:compare(readback_keys['near'][side][role],readback_keys['far'][side][role],p)
        for role in ('original_q0','candidate_q0')} for side in 'LR'}
    return VerifiedKeys({s:readback_keys['near'][s]['original_q0'] for s in 'LR'},
                        {s:readback_keys['near'][s]['candidate_q0'] for s in 'LR'},
                        {'candidate_name':NAME,'functional_source_commit':S4,
                         'candidate_source_sha256':binding['candidate_source_sha256'],
                         'actual_K1_run_id':binding['run_id'],'actual_K1_head_sha':binding['head_sha'],
                         'pose_originals':receipts,'near_far_complete_q0_material_agreement':equality,
                         'raw_runtime_report_reconstructed':False})


def full_scene(keys,nominal,cam,p,slide=0.,descent=0.,left_tab=0.,right_tab=0.,**kwargs):
    """Preserve every S4 independent input and replace only verified whole KEYs.

    Invalid original input remains invalid. In particular q is never clamped.
    This is a material factory adapter, not a proof of all resulting motions.
    """
    require(isinstance(keys,VerifiedKeys),'verified whole material bundle required')
    parts,metadata=nominal.full_scene(slide,descent,left_tab,right_tab,**kwargs)
    actual=metadata['scene'];offsets=actual['KEY_offsets_mm']
    comparisons={};out=dict(parts)
    for side,dq in zip('LR',offsets):
        q=cam.K*actual['slide_mm']+dq
        require(0<=q<=12,'no extension of finite native contact law')
        name=side+'_KEY'
        comparisons[name]={'actual_q_mm':q,'actual_q_binary64_hex':q.hex(),
            'fresh_original_KEY_to_verified_original_q0':compare(parts[name].translate((0,-q,0)),keys.original_q0[side],p)}
        out[name]=p.single(keys.candidate_q0[side].translate((0,q,0)))
    require(set(out)==set(parts),'full factory body inventory changed')
    return out,{**metadata,'named_KEY_candidate':{**keys.receipt,'current_factory_KEY_material_comparisons':comparisons,
        'all_other_factory_participants_retained':sorted(set(parts)-{'L_KEY','R_KEY'}),
        'independent_controls_or_offsets_reduced':False,'physical_allowed_domain_proved':False,
        'all_pairs_or_continuous_motion_proved_by_adapter':False,'strength_qualified':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}}
