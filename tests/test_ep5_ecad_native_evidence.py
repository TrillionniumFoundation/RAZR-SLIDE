"""Reject incomplete native evidence without requiring KiCad for these tests."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'),str(ROOT/'integration')]
import verify_ep5_ecad_native as v


class NativeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.config = v.artwork.route_input()
        self.hashes = {'board':'a'*64,'project':'b'*64}
        self.report = {'inputs_sha256':self.hashes,'input_bytes_unchanged':True,
                       'project_loaded':True,'tracks':130,'footprints':2,
                       'declared_board_thickness_mm':.1,'native_pad_readback':[],
                       'drc_zero_reported_items':True,'drc_violation_types':{},
                       'drc_sections':[{'count':0,'kind':'DRC violations'}]}
        self.drc_identity = {'source':'board.kicad_pcb','coordinate_units':'mm','kicad_version':'8.0.9'}
        for row in v.artwork.channels(self.config):
            for reference,index in (('JA',0),('JB',-1)):
                self.report['native_pad_readback'].append({'reference':reference,'pad':row['pin'],
                    'net':row['net'],'size_mm':[.25,4.],'position_mm':list(row['points'][index])})

    def reject(self, report):
        with self.assertRaises(ValueError): v.validate_readback(report,self.config,self.hashes)

    def drc(self, document, code=0):
        return v.validate_drc(self.drc_identity | document,code,'board.kicad_pcb','8.0.9')

    def test_native_complete_terminal_inventory(self):
        self.assertEqual(v.validate_readback(self.report,self.config,self.hashes)['terminals'],52)

    def test_legacy_length_readback_cannot_qualify_EP5(self):
        self.report['native_pad_readback'][1]['position_mm'][1] -= 24
        self.reject(self.report)

    def test_native_wrong_net_and_duplicate_terminal_rejected(self):
        wrong = copy.deepcopy(self.report)
        wrong['native_pad_readback'][0]['net'] = 'C02'
        self.reject(wrong)
        self.report['native_pad_readback'][-1] = self.report['native_pad_readback'][0]
        self.reject(self.report)

    def test_native_nonfinite_position_or_thickness_rejected(self):
        bad = copy.deepcopy(self.report); bad['declared_board_thickness_mm'] = float('nan')
        self.reject(bad)
        self.report['native_pad_readback'][0]['position_mm'][0] = float('nan')
        self.reject(self.report)

    def test_zero_exit_does_not_erase_DRC_warning_or_exclusion(self):
        for severity in ('warning','error','exclusion'):
            with self.subTest(severity=severity), self.assertRaises(ValueError):
                self.drc({'violations':[{'severity':severity}],'unconnected_items':[]})

    def test_missing_disconnected_and_nonzero_native_results_rejected(self):
        for document, code in (({'violations':[]},0),
                               ({'violations':[],'unconnected_items':[{}]},0),
                               ({'violations':[],'unconnected_items':[]},5)):
            with self.subTest(document=document,code=code), self.assertRaises(ValueError):
                self.drc(document,code)

    def test_complete_empty_native_DRC_result(self):
        self.assertEqual(self.drc({'violations':[],'unconnected_items':[],'schematic_parity':[]}),
                         {'violations':0,'unconnected_items':0,'schematic_parity':0})

    def test_readback_DRC_rejection_survives_clean_cli_result(self):
        self.report['drc_sections'] = [{'count':17,'kind':'DRC violations'}]
        self.report['drc_violation_types'] = {'clearance':17}
        self.reject(self.report)

    def test_missing_readback_DRC_cannot_be_a_pass(self):
        self.report.pop('drc_sections')
        self.reject(self.report)

    def test_wrong_board_version_or_unit_receipt_rejected(self):
        for key,value in (('source','another-board.kicad_pcb'),('coordinate_units','in'),('kicad_version','foreign')):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.drc({'violations':[],'unconnected_items':[],key:value})


if __name__ == '__main__': unittest.main()
