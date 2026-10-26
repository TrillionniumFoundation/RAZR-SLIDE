"""Regression guards for empty evidence, incomplete native checks and exact members."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ep5_input_closure as closure
import product_routing_ep5 as ep5

import product_routing_ep4 as ep4
from verified_native_members import verify_member_directory

HERE=Path(__file__).resolve().parents[2]
reader_path=HERE/'engineering/product-integration-20261018/phase5-20261022/read_ep5_step_independent.py'
spec=importlib.util.spec_from_file_location('ep5_independent_reader_test_subject',reader_path)
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)

class EvidenceGuardTests(unittest.TestCase):
    def continuous_fixture(self):
        metric={'volume_mm3':1.,'bounds_mm':[0.,1.,0.,1.,0.,1.],'positive_valid_solids':1}
        endpoints={end:{end+'_'+name:copy.deepcopy(metric) for name in reader.ENDPOINT_PART_NAMES}
                   for end in ('A','B')}
        rows=[{'a':'U1_ALL_POSES_SMOOTH_ENCLOSURE','b':name,
               'a_bounds_mm':metric['bounds_mm'],'b_bounds_mm':metric['bounds_mm'],
               'method':'native_Common','common_mm3':0.,'common_positive_solids':0,'rejected':False}
              for name in endpoints['B']]
        return {'schema':'razr-ep5-continuous-complete-endpoint-geometry-v1',
                'endpoint_metrics':endpoints,'U1_cage':copy.deepcopy(metric),
                'U1_to_all_20_B_endpoint_parts':{'rows':rows,'failures':[],'pair_count':20,
                    'native_Common_calls':20,'cached_axis_gap_rejections_of_intersection':0,
                    'positive_Common_count_including_below_tolerance':0,'rejection_volume_tolerance_mm3':1e-7,
                    'no_Common_above_tolerance_or_evaluation_error':True},
                'other_segment_axis_separation_margins':{name:1. for name in reader.ENDPOINT_MARGIN_NAMES},
                'all_declared_continuous_endpoint_geometric_checks_clear':True,
                'current_PAWL_or_full_external_field_checked':False,
                'friction_strain_tolerance_and_physical_qualification_proved':False,
                'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}

    def test_full_reader_recomputes_pose_and_report_rejection_from_raw_volumes(self):
        for scope in ('pair','containment'):
            pose={'complete_pair_matrix':{'rows':[{'common_mm3':.25 if scope=='pair' else 0.,
                                                  'rejected':scope=='pair'}]},
                  'containment':{'rows':[{'outside_outer_union_mm3':.25 if scope=='containment' else 0.,
                                          'rejected':scope=='containment'}]},
                  'decisive_geometric_rejection_or_evaluation_failure':True,
                  'all_declared_finite_pose_checks_clear':False}
            report={'poses':[pose],'geometric_rejection_found':True}
            self.assertTrue(reader.validate_disposition(report,False))
            report['geometric_rejection_found']=False
            with self.subTest(scope=scope),self.assertRaisesRegex(ValueError,'full disposition'):
                reader.validate_disposition(report,False)
            report['geometric_rejection_found']=True
            pose['all_declared_finite_pose_checks_clear']=True
            with self.assertRaisesRegex(ValueError,'finite-pose disposition'):
                reader.validate_disposition(report,False)

    def test_continuous_pair_failure_cannot_hide_in_local_clear_claim(self):
        continuous=self.continuous_fixture()
        self.assertFalse(reader.validate_continuous_endpoints(continuous))
        pair=continuous['U1_to_all_20_B_endpoint_parts'];row=pair['rows'][0]
        row.update(common_mm3=.25,common_positive_solids=1,rejected=True)
        pair.update(failures=[row],positive_Common_count_including_below_tolerance=1,
                    no_Common_above_tolerance_or_evaluation_error=False)
        continuous['all_declared_continuous_endpoint_geometric_checks_clear']=False
        report={'poses':[{'complete_pair_matrix':{'rows':[{'common_mm3':0.,'rejected':False}]}}],
                'continuous_complete_endpoints':continuous,'all_declared_local_geometry_checks_clear':False}
        self.assertTrue(reader.validate_disposition(report,True))
        report['all_declared_local_geometry_checks_clear']=True
        with self.assertRaisesRegex(ValueError,'local disposition'):
            reader.validate_disposition(report,True)
        continuous['all_declared_continuous_endpoint_geometric_checks_clear']=True
        with self.assertRaisesRegex(ValueError,'continuous endpoint disposition'):
            reader.validate_disposition(report,True)

    def test_continuous_endpoint_inventory_margins_and_pair_coverage_are_required(self):
        for change in ('missing_part','missing_pair','duplicate_pair','missing_margin','nonpositive_margin','false_release'):
            continuous=self.continuous_fixture()
            if change=='missing_part':continuous['endpoint_metrics']['B'].pop(next(iter(continuous['endpoint_metrics']['B'])))
            elif change=='missing_pair':continuous['U1_to_all_20_B_endpoint_parts']['rows'].pop()
            elif change=='duplicate_pair':continuous['U1_to_all_20_B_endpoint_parts']['rows'][-1]=copy.deepcopy(continuous['U1_to_all_20_B_endpoint_parts']['rows'][0])
            elif change=='missing_margin':continuous['other_segment_axis_separation_margins'].pop(next(iter(reader.ENDPOINT_MARGIN_NAMES)))
            elif change=='nonpositive_margin':continuous['other_segment_axis_separation_margins'][next(iter(reader.ENDPOINT_MARGIN_NAMES))]=0.
            else:continuous['manufacturing_go']=True
            with self.subTest(change=change),self.assertRaises(ValueError):
                reader.validate_continuous_endpoints(continuous)

    def test_empty_manifest_is_rejected_by_actual_reader_execute(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);manifest=root/'empty.json'
            manifest.write_text(json.dumps({'schema':'razr-ep5-full-pair-native-v1',
                'native_checks_executed':False,'source_bytes_unchanged':True,
                'source_sha256':{},'selected_poses':[],'poses':[],
                'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}))
            result=reader.execute(manifest,ep4.ROOT,root/'out')
            self.assertFalse(result['declared_readback_checks_passed'])
            self.assertFalse(result['execution_completed'])
            self.assertTrue(result['failures'])

    def test_header_requires_actual_nonempty_unique_executed_pose_set(self):
        base={'schema':'razr-ep5-local-motion-native-v1','native_checks_executed':True,
              'source_bytes_unchanged':True,'source_sha256':{'/some/input':'a'*64},
              'selected_poses':['STOW'],'poses':[{'pose':'STOW'}],
              'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
        self.assertTrue(reader.validate_native_header(base))
        cases=[('selected_poses',[]),('selected_poses',['STOW','STOW']),
               ('selected_poses',['NOT_A_POSE']),('source_sha256',{}),
               ('native_checks_executed',False),('source_bytes_unchanged',False),
               ('candidate_go',True),('poses',[])]
        for key,value in cases:
            with self.subTest(key=key,value=value):
                changed=copy.deepcopy(base);changed[key]=value
                with self.assertRaises(ValueError):reader.validate_native_header(changed)

    def test_common_requires_finite_nonnegative_evaluated_material(self):
        parts={'A':{'volume_mm3':1.,'bounds_mm':[0.,1.,0.,1.,0.,1.]},
               'B':{'volume_mm3':1.,'bounds_mm':[2.,3.,0.,1.,0.,1.]}}
        row={'a':'A','b':'B','a_bounds_mm':parts['A']['bounds_mm'],'b_bounds_mm':parts['B']['bounds_mm'],
             'method':'native_Common','common_mm3':0.,'common_positive_solids':0,'rejected':False}
        matrix={'rows':[row],'failures':[],'native_Common_calls':1,
                'cached_axis_gap_rejections_of_intersection':0,
                'positive_Common_count_including_below_tolerance':0,
                'rejection_volume_tolerance_mm3':1e-7,'no_Common_above_tolerance_or_evaluation_error':True}
        reader.validate_pair_rows(matrix,parts)
        for value in (None,-.1,float('nan'),float('inf'),True,'0'):
            with self.subTest(value=value):
                bad=copy.deepcopy(matrix);bad['rows'][0]['common_mm3']=value
                with self.assertRaises(ValueError):reader.validate_pair_rows(bad,parts)
        bad=copy.deepcopy(matrix);del bad['rows'][0]['common_mm3']
        with self.assertRaises(ValueError):reader.validate_pair_rows(bad,parts)

    def test_full_containment_cannot_be_empty_but_local_explicitly_is(self):
        reader.validate_containment({'rows':[],'executed':False},{},True)
        with self.assertRaises(ValueError):reader.validate_containment({'rows':[],'parts':41},{},False)
        with self.assertRaises(ValueError):reader.validate_containment({'rows':[],'executed':True},{},True)

    def test_axis_gap_omission_must_follow_actual_pair_bounds(self):
        parts={name:{'volume_mm3':1.,'bounds_mm':[0.,1.,0.,1.,0.,1.]} for name in ('A','B')}
        row={'a':'A','b':'B','a_bounds_mm':parts['A']['bounds_mm'],'b_bounds_mm':parts['B']['bounds_mm'],
             'method':'cached_native_geometry_bounds_positive_axis_gap','axis_gap_lower_mm':3.,
             'common_mm3':0.,'rejected':False}
        with self.assertRaises(ValueError):reader.validate_pair_rows({'rows':[row]},parts)

class OriginalMemberGuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name);self.members=self.root/'members';self.members.mkdir()
        self.records=[]
        for index in range(64):
            name=f'part_{index:02}.step';raw=('controlled original '+str(index)).encode()
            (self.members/name).write_bytes(raw)
            self.records.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        self.manifest=self.root/'manifest.json';self.save()
    def save(self):
        self.manifest.write_text(json.dumps({'files':self.records}))
    def check(self):
        return verify_member_directory(self.members,self.manifest,64)
    def test_all_original_members_are_required_and_hashed(self):
        result=self.check();self.assertEqual(result['actual_member_count'],64)
        self.assertTrue(result['all_original_member_bytes_verified'])
        self.assertFalse(result['original_archive_sha256_claimed_recovered'])
    def test_mutated_missing_and_extra_members_are_rejected(self):
        path=self.members/'part_00.step';original=path.read_bytes();path.write_bytes(b'X'+original[1:])
        with self.assertRaises(ValueError):self.check()
        path.unlink()
        with self.assertRaises(ValueError):self.check()
        path.write_bytes(original);(self.members/'extra.step').write_bytes(b'extra')
        with self.assertRaises(ValueError):self.check()
    def test_symbolic_member_and_symbolic_directory_are_rejected(self):
        path=self.members/'part_00.step';outside=self.root/'original.step'
        outside.write_bytes(path.read_bytes());path.unlink();path.symlink_to(outside)
        with self.assertRaises(ValueError):self.check()
        path.unlink();path.write_bytes(outside.read_bytes())
        alias=self.root/'alias';alias.symlink_to(self.members,target_is_directory=True)
        with self.assertRaises(ValueError):verify_member_directory(alias,self.manifest,64)
    def test_unsafe_or_duplicate_manifest_member_is_rejected(self):
        self.records[0]['path']='../original.step';self.save()
        with self.assertRaises(ValueError):self.check()
        self.records[0]=dict(self.records[1]);self.save()
        with self.assertRaises(ValueError):self.check()


class InputClosureGuardTests(unittest.TestCase):
    # Independently reviewed native reader chain: configurations plus panel,
    # pawl, cam-v5, mounted and compressed stop/spring profile payload roles.
    CONFIGS={'design/product_routing_ep5.json','design/product_geometry.json','design/product_routing_ep4.json'}
    ENGINEERING={
        'engineering/panel-bearing-web-20261015/native-templates.tar.gz',
        'engineering/pawl-actuation-20261015/geometry-manifest.json',
        'engineering/pawl-actuation-20261015/native-geometry.tar.gz',
        'engineering/pawl-actuation-20261015/NATIVE_MANIFEST.json',
        'engineering/cam-coupling-20261015/geometry-v5-manifest.json',
        'engineering/cam-coupling-20261015/native-v5-geometry.tar.gz',
        'engineering/cam-coupling-20261015/V5_NATIVE_MANIFEST.json',
        'engineering/mounted-mechanism-20261015/geometry-manifest.json',
        'engineering/thin-mechanism-20261015/native-verification.json.gz'}
    MOUNTED='engineering/mounted-mechanism-20261015/native-geometry.tar.gz'
    THIN='engineering/thin-mechanism-20261015/native-verification.json.gz'

    def test_modes_match_independently_enumerated_actual_data_closure(self):
        self.assertEqual(set(closure.native_input_roles('local')),self.CONFIGS)
        self.assertEqual(set(closure.native_input_roles('full',True)),self.CONFIGS|self.ENGINEERING)
        self.assertEqual(set(closure.native_input_roles('full')),self.CONFIGS|self.ENGINEERING|{self.MOUNTED})
        for mode,verified in [('all',False),('local',True),('full',1),([],False)]:
            with self.subTest(mode=mode,verified=verified):
                with self.assertRaises(ValueError):closure.native_input_roles(mode,verified)

    def test_every_declared_role_is_required_even_if_historical_payloads_are_absent(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for name in self.CONFIGS|self.ENGINEERING|{self.MOUNTED}:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(name.encode())
            with patch.object(ep5,'ROOT',root),patch.object(ep5.ep4,'ROOT',root):
                before=ep5._snapshot_sources('full')
                self.assertTrue({str(root/name) for name in self.CONFIGS|self.ENGINEERING|{self.MOUNTED}}<=set(before))
                for name in self.CONFIGS|self.ENGINEERING|{self.MOUNTED}:
                    path=root/name;original=path.read_bytes();path.unlink()
                    with self.subTest(name=name):
                        with self.assertRaises(ValueError):ep5._snapshot_sources('full')
                    path.write_bytes(original)
                (root/self.MOUNTED).unlink()
                self.assertEqual(len(ep5._snapshot_sources('full',True)),12)
                self.assertEqual(set(closure.native_input_roles('local')),self.CONFIGS)

    def test_consumed_compressed_profile_mutation_fails_source_completion(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for name in self.CONFIGS|self.ENGINEERING:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(name.encode())
            with patch.object(ep5,'ROOT',root),patch.object(ep5.ep4,'ROOT',root):
                before=ep5._snapshot_sources('full',True)
                self.assertTrue(ep5.source_completion_check(before)['source_bytes_unchanged'])
                (root/self.THIN).write_bytes(b'mutated profile bytes')
                result=ep5.source_completion_check(before)
                self.assertFalse(result['source_bytes_unchanged'])
                self.assertEqual([row['path'] for row in result['changed_or_missing_sources']],[str(root/self.THIN)])

    def test_factory_new_or_unpinned_payload_cannot_expand_declared_scope(self):
        archive='engineering/panel-bearing-web-20261015/native-templates.tar.gz'
        metadata={'archive':archive,'archive_sha256':'a'*64,'source_inputs':{self.THIN:'b'*64}}
        before={str((ep4.ROOT/archive).resolve()):'a'*64,str((ep4.ROOT/self.THIN).resolve()):'b'*64}
        ep5.validate_factory_input_coverage(metadata,before)
        before.pop(str((ep4.ROOT/self.THIN).resolve()))
        with self.assertRaises(ValueError):ep5.validate_factory_input_coverage(metadata,before)

    def test_reader_rejects_missing_extra_or_old_role_inventory(self):
        roles=closure.native_input_roles('full',True)
        report={'input_closure_schema':closure.SCHEMA,'declared_input_roles':roles,
                'input_closure_helper_sha256':'a'*64}
        reader.validate_declared_input_roles(report,roles)
        for change in ('missing_gzip','extra_history','old_report','bad_helper'):
            bad=copy.deepcopy(report)
            if change=='missing_gzip':bad['declared_input_roles'].pop(self.THIN)
            elif change=='extra_history':bad['declared_input_roles']['engineering/unused/native.tar.gz']='unused'
            elif change=='old_report':bad.pop('input_closure_schema')
            else:bad['input_closure_helper_sha256']='unknown'
            with self.subTest(change=change):
                with self.assertRaises(ValueError):reader.validate_declared_input_roles(bad,roles)

if __name__=='__main__':unittest.main()
