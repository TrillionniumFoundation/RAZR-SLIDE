import math
import copy
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import product_assembly as p
import product_nominal_motion as motion


class NominalMechanismTests(unittest.TestCase):
    def test_continuous_independent_slot_flanks_reach_actual_pawl(self):
        baseline, _ = p.native_scene(left_tab_mm=1.125, right_tab_mm=2.375)
        actual, meta = p.native_scene(left_tab_mm=1.125, right_tab_mm=2.375, flanks=(-.4, .65))
        slots = p.native_inputs()[5]
        for side, flank in zip('LR', (-.4, .65)):
            for role in ('PAWL', 'SHOULDER_PIN_NOMINAL'):
                delta = p.bounds(actual[side+'_'+role])[4]-p.bounds(baseline[side+'_'+role])[4]
                self.assertAlmostEqual(delta, flank*slots[side]['halfwidth'], places=8)
        self.assertEqual(meta['slot_flanks'], [-.4, .65])
        self.assertEqual(len(actual), 83)

    def test_left_right_telescope_allocations_are_independent(self):
        actual, meta = p.native_scene(79.75, 4.1, 3., 3., telescope_offsets={'L': [.1, 1.4, 2.9], 'R': [2.9, 1.4, .1]})
        self.assertAlmostEqual(p.bounds(actual['R_TELESCOPE_1'])[4]-p.bounds(actual['L_TELESCOPE_1'])[4], 2.8, places=8)
        self.assertAlmostEqual(p.bounds(actual['R_TELESCOPE_3'])[4], p.bounds(actual['L_TELESCOPE_3'])[4], places=8)
        self.assertNotEqual(meta['telescope_offsets_by_side_mm']['L'], meta['telescope_offsets_by_side_mm']['R'])
        self.assertEqual(len(actual), 83)

    def test_key_and_crosshead_clearance_moves_actual_material(self):
        baseline, _ = p.native_scene(40., 0., 3., 3.)
        actual, meta = p.native_scene(40., 0., 3., 3., key_offsets=(.02, -.02), crosshead_offsets=(.01, -.01))
        for side, dq, dx in (('L', .02, .01), ('R', -.02, -.01)):
            self.assertAlmostEqual(p.bounds(actual[side+'_KEY'])[2]-p.bounds(baseline[side+'_KEY'])[2], dq, places=8)
            self.assertAlmostEqual(p.bounds(actual[side+'_CROSSHEAD'])[0]-p.bounds(baseline[side+'_CROSSHEAD'])[0], (-1 if side=='L' else 1)*dx, places=8)
        self.assertEqual(meta['KEY_offsets_mm'], [.02, -.02])

    def test_key_and_cam_offset_must_satisfy_both_grooves(self):
        for kwargs in ({'crosshead_offsets': (.1, 0.)}, {'key_offsets': (.06, 0.), 'crosshead_offsets': (0., 0.)},
                       {'key_offsets': (math.nan, 0.)}, {'flanks': (1.01, 0.)}, {'flanks': (False, 0.)}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                p.native_scene(40., 0., 3., 3., **kwargs)

    def test_unmodeled_key_endpoint_branch_is_not_clamped(self):
        with self.assertRaisesRegex(ValueError, 'outside the finite declared cam travel'):
            p.native_scene(key_offsets=(-.01, 0.))
        with self.assertRaisesRegex(ValueError, 'outside the finite declared cam travel'):
            p.native_scene(79.75, 0., 3., 3., key_offsets=(.01, 0.))

    def test_telescope_inventory_and_kinematic_sum_are_closed(self):
        for values in ({'L': [.1, 1.4, 2.9]}, {'L': [.1, 1.4, 2.9], 'R': [.1, 1.4, 2.9], 'X': [.1]*3},
                       {'L': [.1, 1.4, 2.9], 'R': [.1]*3}, {'L': [False, 1.5, 2.9], 'R': [2.9, 1.4, .1]},
                       {'L': [.1, 1.4, 2.9], 'R': [float('nan'), 1.4, .1]}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                p.native_scene(79.75, 4.1, 3., 3., telescope_offsets=values)

    def test_complete_ep5_inventory_retained_for_independent_clearance_and_allocations(self):
        parts, metadata = motion.full_scene(40., 0., 3., 3.,
            flanks=(-.35, .55), key_offsets=(.02, -.02), crosshead_offsets=(.01, -.01),
            telescope_offsets={'L':[2.9,2.9,2.7], 'R':[2.7,2.9,2.9]})
        self.assertEqual(len(parts),154)
        self.assertEqual(metadata['mechanical_participants'],108)
        self.assertEqual(metadata['candidate_participants'],41)
        self.assertTrue(metadata['scene']['whole_material_preserved_against_this_pose_native_parents'])
        self.assertTrue(metadata['research_relief']['all_mechanical_participants_retained'])


class ContinuousRelativeGeometryTests(unittest.TestCase):
    def split_region_volumes(self):
        import translation_regions as regions
        a=p.box((0.,0.,0.),(1.,1.,1.))
        b=p.box((1.495,1.495,.4),(1.505,1.505,.4018))
        pieces,_=regions.regions(a,(2.,2.,0.))
        return [p.strict_common(piece,b)['common_mm3'] for piece in pieces]

    def test_thin_stop_core_combines_pin_and_remainder_for_one_stop(self):
        import verify_thin_mechanism as thin
        values=[value for value in self.split_region_volumes() if value>0]
        self.assertEqual(len(values),2)
        self.assertLess(max(values),motion.TOL)
        rejected={'stop':0,'pin_complete_relative_path_common_mm3':values[0],
            'core_remainder_cage_common_mm3':values[1:],
            'complete_STOP_core_to_KEY_common_upper_bound_mm3':0.}
        clear={'stop':1,'pin_complete_relative_path_common_mm3':values[0],
               'core_remainder_cage_common_mm3':[0.]}
        self.assertEqual(thin.contact_rejections([rejected,clear]),[rejected])

    def test_box_guide_combines_complete_pieces_per_fixed_target(self):
        import verify_pawl_box_guide as guide
        names=[name for name,_,_ in guide.v.COVERS[:3]]+['round_carrier']
        values=self.split_region_volumes()
        self.assertEqual(len(values),len(names))
        rows=[{'side':'R','fixed':'target','piece':name,'common_mm3':value}
              for name,value in zip(names,values)]
        result=guide.whole_material_enclosure_checks(rows)
        self.assertEqual(len(result),1)
        self.assertGreater(result[0]['common_upper_bound_mm3'],motion.TOL)
        self.assertFalse(result[0]['whole_material_enclosure_clear'])
        with self.assertRaisesRegex(ValueError,'piece inventory'):
            guide.whole_material_enclosure_checks(rows[:-1])
        # Different fixed bodies are separate pairs, not one summed obstacle.
        one=next(value for value in values if value>0)
        separate=[{'side':'R','fixed':target,'piece':name,'common_mm3':one if index==0 else 0.}
                  for target in ('first','second') for index,name in enumerate(names)]
        self.assertTrue(all(row['whole_material_enclosure_clear']
                            for row in guide.whole_material_enclosure_checks(separate)))

    def test_exact_material_partition_cannot_drop_component_sum_rejection(self):
        import verify_endpoint_joint_pawl as endpoint
        a=p.box((0.,0.,0.),(1.,1.,1.))
        base=p.single(p.cq.Workplane('XY').polyline([(0.,0.),(.02,0.),(1.,.98),
            (1.,1.),(.98,1.),(0.,.02)]).close().extrude(1.).val())
        b=p.box((1.495,1.495,.4),(1.505,1.505,.4018))
        result=endpoint.roof_motion_partition('whole material split',a,base,(2.,2.,0.),{'obstacle':b})
        self.assertEqual(result['partition_components'],3)
        row=result['checks'][0]
        self.assertLess(max(row['common_mm3']),motion.TOL)
        self.assertGreater(row['common_upper_bound_mm3'],motion.TOL)
        self.assertFalse(row['clear'])
        self.assertEqual(len(result['failed']),1)
        self.assertGreater(p.strict_common(a.translate((1.,1.,0.)),b)['common_mm3'],motion.TOL)

    def test_subthreshold_region_intersections_cannot_mask_larger_actual_overlap(self):
        import translation_regions as regions
        import verify_serviceable_pawl as serviceable
        a=p.box((0.,0.,0.),(1.,1.,1.))
        b=p.box((1.495,1.495,.4),(1.505,1.505,.4018))
        coefficients=[[2/3,2/3,0.],[0.,0.,0.],[0.,0.,0.],[0.,0.,0.]]
        actual=p.strict_common(a.translate((1.,1.,0.)),b)['common_mm3']
        self.assertGreater(actual,motion.TOL)
        enclosure,_=regions.regions(a,(2.,2.,0.))
        result=regions.checks(enclosure,b)
        self.assertLess(max(result['region_common_mm3']),motion.TOL)
        self.assertGreater(result['common_upper_bound_mm3'],motion.TOL)
        self.assertFalse(result['all_regions_clear'])
        self.assertEqual(motion.continuous_pair(a,b,coefficients)['disposition'],'unresolved_enclosure_overlap')
        translated=serviceable.motion('real split-region counterexample',a,(2.,2.,0.),{'obstacle':b})
        self.assertFalse(translated['checks'][0]['clear'])
        self.assertGreater(translated['checks'][0]['common_upper_bound_mm3'],motion.TOL)
        self.assertEqual(len(translated['failed']),1)

    def test_shared_cache_cannot_reuse_ring_enclosure_for_solid_material(self):
        outer=p.box((0.,0.,0.),(4.,4.,1.))
        ring=outer.cut(p.box((1.,1.,-1.),(3.,3.,2.)))
        b=p.box((1.9,1.9,.4),(2.1,2.1,.6))
        coefficients=[[0.,0.,.1],[0.,0.,0.],[0.,0.,0.],[0.,0.,0.]]
        cache={}
        self.assertEqual(motion.continuous_pair(ring,b,coefficients,cache=cache)['disposition'],'clear')
        actual=motion.continuous_pair(outer,b,coefficients,cache=cache)
        self.assertEqual(actual['disposition'],'unresolved_enclosure_overlap')
        self.assertGreater(actual['positive_enclosure_common_mm3'],.0079)

    def test_off_diagonal_aabb_overlap_is_not_reported_as_collision(self):
        a=p.box((0.,0.,0.),(.1,.1,.1));b=p.box((.45,0.,0.),(.55,.1,.1))
        coefficients=[[1/3,1/3,0.],[0.,0.,0.],[0.,0.,0.],[0.,0.,0.]]
        result=motion.continuous_pair(a,b,coefficients)
        self.assertEqual(result['disposition'],'clear')
        self.assertEqual(result['method'],'continuous_relative_affine_box_translation_enclosure')

    def test_positive_enclosure_is_unresolved_even_when_collision_exists(self):
        a=p.box((0.,0.,0.),(.1,.1,.1));b=p.box((.45,.45,0.),(.55,.55,.1))
        coefficients=[[1/3,1/3,0.],[0.,0.,0.],[0.,0.,0.],[0.,0.,0.]]
        result=motion.continuous_pair(a,b,coefficients)
        self.assertEqual(result['disposition'],'unresolved_enclosure_overlap')
        self.assertFalse(result['collision_proved'])
        self.assertGreater(p.strict_common(a.translate((.45,.45,0.)),b)['common_mm3'],motion.TOL)

    def test_identical_motion_cancels_in_the_pair_frame(self):
        coefficients=[[0.,1.,0.],[0.,0.,0.],[0.,0.,.025],[0.,0.,0.]]
        relative=motion.relative_coefficients(coefficients,coefficients)
        self.assertEqual(motion.translation_bounds(relative),[0.]*6)

    def test_all_control_components_required(self):
        names={s+'_'+r for s in 'LR' for r in motion.CONTROL_ROLES}
        slots={s:{'slope':1.,'halfwidth':.1} for s in 'LR'}
        coefficients=motion.controls_coefficients(names,slots)
        self.assertEqual(len(coefficients),10)
        names.remove('R_SHOULDER_PIN_NOMINAL')
        with self.assertRaises(ValueError):motion.controls_coefficients(names,slots)

    def test_continuous_parameter_bounds_preserve_negative_coefficients(self):
        coefficients=[[0.,-1.,.5],[0.,0.,0.],[0.,0.,.1],[0.,0.,0.]]
        self.assertEqual(motion.translation_bounds(coefficients),[0.,0.,-3.,0.,-.1,1.6])


class CapturedTelescopeDomainTests(unittest.TestCase):
    def test_feasible_joint_polytope_has_complete_vertices_and_collapses_at_open(self):
        for descent,expected_count,expected_sum in ((0.,3,8.5),(4.1,6,4.4),(8.2,1,.3)):
            domain=motion.telescope_domain(descent)
            self.assertEqual(len(domain['vertices_joint_mm']),expected_count)
            for joints in domain['vertices_joint_mm']:
                self.assertAlmostEqual(sum(joints),expected_sum,places=12)
                self.assertTrue(all(.1<=joint<=2.9 for joint in joints))
                self.assertGreaterEqual(sum(joint in (.1,2.9) for joint in joints),2)
        self.assertEqual(motion.telescope_domain(8.2)['vertices_joint_mm'],[[.1,.1,.1]])
        for descent in (-.01,8.21,False,float('nan')):
            with self.subTest(descent=descent),self.assertRaises(ValueError):
                motion.telescope_domain(descent)

    def test_relative_projection_keeps_sum_constraint_and_independent_sides(self):
        telescope=motion.telescope_domain(0.)
        domain=motion.DOMAIN+tuple(telescope['parameter_bounds_delta_j1_delta_j2_mm'])*2
        coefficients=[[0.,0.,0.] for _ in range(8)]
        coefficients[4][2]=coefficients[5][2]=1.
        projected,pair_domain=motion.relative_telescope_projection(coefficients,domain,telescope)
        loose=motion.translation_bounds(coefficients,domain)
        self.assertAlmostEqual(pair_domain[-1][0],-1/15,places=12)
        self.assertAlmostEqual(pair_domain[-1][1],2/15,places=12)
        self.assertLess(loose[4],pair_domain[-1][0]-.19)
        self.assertEqual(projected[-1],[0.,0.,1.])
        coefficients[6][2]=coefficients[7][2]=-1.
        _,relative_domain=motion.relative_telescope_projection(coefficients,domain,telescope)
        self.assertAlmostEqual(relative_domain[-1][0],-.2,places=12)
        self.assertAlmostEqual(relative_domain[-1][1],.2,places=12)
        # With the telescope fully retracted there is no allocation motion.
        opened=motion.telescope_domain(8.2)
        opened_domain=motion.DOMAIN+tuple(opened['parameter_bounds_delta_j1_delta_j2_mm'])*2
        _,zero=motion.relative_telescope_projection(coefficients,opened_domain,opened)
        self.assertEqual(zero[-1],(0.,0.))

    def test_infeasible_outer_box_point_is_never_an_actual_witness(self):
        telescope=motion.telescope_domain(0.)
        nominal=telescope['nominal_joint_mm']
        invalid=[0.,0.,0.,0.,2.7-nominal,2.7-nominal,0.,0.]
        self.assertIsNone(motion.telescope_allocations(invalid,telescope))
        domain=motion.DOMAIN+tuple(telescope['parameter_bounds_delta_j1_delta_j2_mm'])*2
        relative=[[0.,0.,0.]]*4+[[0.,0.,1.]]*4
        candidates=list(motion.witness_parameter_candidates(relative,domain,telescope))
        self.assertGreater(len(candidates),1)
        for values in candidates:
            allocations=motion.telescope_allocations(values,telescope)
            self.assertIsNotNone(allocations)
            for joints in allocations.values():
                self.assertTrue(all(.1-1e-9<=joint<=2.9+1e-9 for joint in joints))
                self.assertAlmostEqual(sum(joints),8.5,places=12)

    def test_whole_split_material_obeys_independent_telescope_affine_law(self):
        import product_split_assembly as split
        baseline,_=split.split_scene(79.75,4.1)
        allocations={'L':[.1,2.9,1.4],'R':[2.9,1.4,.1]}
        actual,_=split.split_scene(79.75,4.1,3.,3.,flanks=(-.4,.65),telescope_offsets=allocations)
        coefficients=motion.fixed_pose_coefficients(baseline,p.native_inputs()[5])
        nominal=motion.telescope_domain(4.1)['nominal_joint_mm']
        values=[3.,3.,-.4,.65]+[joint-nominal for side in 'LR' for joint in allocations[side][:2]]
        self.assertEqual(len(actual),108)
        self.assertEqual(set(actual),set(baseline))
        for name,body in actual.items():
            with self.subTest(part=name):
                expected=baseline[name].translate(motion.translation(coefficients[name],values))
                self.assertLessEqual(max(p.volume(body.cut(expected)),p.volume(expected.cut(body))),motion.TOL)

    def test_missing_telescope_cap_and_truncated_parameter_vectors_fail_closed(self):
        names={side+'_'+role for side in 'LR' for role in (*motion.CONTROL_ROLES,*motion.TELESCOPE_ROLES)}
        slots={side:{'slope':1.,'halfwidth':.1} for side in 'LR'}
        coefficients=motion.fixed_pose_coefficients(names,slots)
        names.remove('R_TELESCOPE_2_BOTTOM_CAP')
        with self.assertRaisesRegex(ValueError,'telescope body or removable cap'):
            motion.fixed_pose_coefficients(names,slots)
        with self.assertRaisesRegex(ValueError,'dimension mismatch'):
            motion.translation(coefficients['L_TELESCOPE_1'],[0.]*4)
        with self.assertRaisesRegex(ValueError,'dimension mismatch'):
            motion.relative_coefficients([[0.,0.,0.]]*8,[[0.,0.,0.]]*4)
        telescope=motion.telescope_domain(0.)
        domain=motion.DOMAIN+tuple(telescope['parameter_bounds_delta_j1_delta_j2_mm'])*2
        coefficients['L_TELESCOPE_1'][4][0]=.1
        with self.assertRaisesRegex(ValueError,'non-Z telescope displacement'):
            motion.relative_telescope_projection(coefficients['L_TELESCOPE_1'],domain,telescope)


class ExecutionEvidenceTests(unittest.TestCase):
    def fixture(self):
        rows=[{'a':a,'b':b,'disposition':'clear','method':'continuous_relative_axis_gap',
               'gap_lower_mm':.1} for a,b in (('a','b'),('a','c'),('b','c'))]
        report={'complete_participant_names':['a','b','c'],'participant_count':3,
                'pairs':rows,'pair_count':3,'expected_pair_count':3}
        identity={'repository_head':'a'*40,'head_bound_source_sha256':{'code.py':'b'*64},
                  'executed_source_sha256':{'/repo/code.py':'b'*64},
                  'executed_source_overlay':False,'environment':{'passed':True}}
        return report,identity

    def test_reverse_proof_retains_initial_kernel_error_and_blocks_execution_pass(self):
        first={'disposition':'unresolved_evaluation','error':'RuntimeError: failed Common',
               'collision_proved':False}
        reverse={'disposition':'clear','method':'continuous_relative_axis_translation',
                 'maximum_region_common_mm3':0.,'region_count':2}
        with mock.patch.object(motion,'_continuous_pair_in_frame',side_effect=[first,reverse]):
            result=motion.continuous_pair(object(),object(),[[0.,0.,0.]]*4)
        self.assertEqual(result['initial_reference_frame_result'],first)
        report,before=self.fixture();report['pairs'][0].update(result)
        checks=motion.execution_result_checks(report,before,copy.deepcopy(before))
        self.assertEqual(checks['evaluation_failure_count'],1)
        self.assertEqual(checks['evaluation_failures'][0]['error'],first['error'])
        self.assertFalse(checks['execution_checks_passed'])
        self.assertFalse(checks['diagnostic_execution_checks_passed'])

    def test_scratch_overlay_is_never_canonical_execution_success(self):
        report,before=self.fixture();before['executed_source_overlay']=True
        result=motion.execution_result_checks(report,before,copy.deepcopy(before))
        self.assertTrue(result['diagnostic_execution_checks_passed'])
        self.assertFalse(result['execution_checks_passed'])

    def test_unchanged_head_cannot_bind_dirty_assume_unchanged_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'code.py';path.write_text('# exact original source\n')
            def git(*args):
                return subprocess.check_output(['git','-C',str(root),'-c','user.name=Synthetic identity fixture',
                    '-c','user.email=synthetic@example.invalid','-c','commit.gpgsign=false',*args],text=True).strip()
            git('init','-q');git('add','.');git('commit','-qm','Synthetic source fixture','--no-verify')
            head=git('rev-parse','HEAD')
            snapshot={'code.py':hashlib.sha256(path.read_bytes()).hexdigest()}
            motion.bind_executed_files(root,snapshot,[path])
            git('update-index','--assume-unchanged','code.py')
            path.write_text('# uncommitted changed execution source\n')
            self.assertEqual(git('status','--porcelain'),'')
            self.assertEqual(git('rev-parse','HEAD'),head)
            with self.assertRaisesRegex(ValueError,'differs from HEAD blob'):
                motion.bind_executed_files(root,snapshot,[path])

    def test_duplicate_pairs_do_not_pass_an_unchanged_total_count(self):
        report,before=self.fixture()
        report['pairs'][-1]=copy.deepcopy(report['pairs'][0])
        report['all_unordered_pairs_present_once']=True
        result=motion.execution_result_checks(report,before,copy.deepcopy(before))
        self.assertFalse(result['all_unordered_pairs_present_once'])
        self.assertFalse(result['execution_checks_passed'])

    def test_changed_sum_helper_during_computation_blocks_product_motion_report(self):
        import product_motion
        with tempfile.TemporaryDirectory() as folder:
            helper=Path(folder)/'helper.py';helper.write_text('def helper(values):\n    return sum(values)\n')
            namespace={};exec(compile(helper.read_text(),str(helper),'exec'),namespace)
            def corrupt_after_geometry():
                helper.write_text('# changed while geometry was running\n')
                return {'all_requested_geometry_checks_nonpenetrating':True}
            with mock.patch.object(product_motion,'sum_common_upper_bound',namespace['helper']):
                with mock.patch.object(product_motion,'_verify_geometry',return_value={}):
                    result=product_motion.verify()
                self.assertEqual(result['executed_verification_source_sha256'][str(helper)],hashlib.sha256(helper.read_bytes()).hexdigest())
                self.assertTrue(result['source_bytes_unchanged'])
                with mock.patch.object(product_motion,'_verify_geometry',side_effect=corrupt_after_geometry):
                    with self.assertRaisesRegex(ValueError,'source changed during computation'):
                        product_motion.verify()


if __name__=='__main__':unittest.main()
