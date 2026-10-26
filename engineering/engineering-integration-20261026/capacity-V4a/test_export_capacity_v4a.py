"""IO-only regression for actual frozen labels; synthetic bytes are not CAD."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
import export_capacity_v4 as exporter


class ExportRegression(unittest.TestCase):
    def test_real_followup_Common_name_was_rejected(self):
        for frame in ('initial','opposite'):
            name='call-000001-'+frame+'-region-0-Common.brep'
            self.assertIsNone(re.fullmatch(r'call-[0-9]{6}(?:\.json|-[a-z0-9_-]+\.brep)',name))
            self.assertTrue(exporter.scientific_filename(name))

    def test_exact_all_frozen_label_families(self):
        labels=['moving-input','fixed-input','contact-key','contact-stop',
            'decomposition-pin','decomposition-remainder','negative-contact-stop',
            'negative-stop','negative-spring']
        labels += [p+str(i) for p in ('carrier-','carrier-contact-') for i in range(4)]
        labels += ['sample-'+str(i)+'-'+s for i in range(3) for s in ('spring','stop','relative')]
        labels += [f+'-region-4095'+suffix for f in ('initial','opposite') for suffix in ('','-Common')]
        for label in labels:
            self.assertTrue(exporter.scientific_filename('call-000123-'+label+'.brep'),label)

    def test_names_outside_frozen_scope_stay_rejected(self):
        for name in ('../report.json','runtime.log','call-000001-runtime.brep',
            'call-000001-initial-region-0-COMMON.brep','call-000001-carrier-4.brep',
            'call-000001-sample-3-stop.brep','call-1.json'):
            self.assertFalse(exporter.scientific_filename(name),name)

    def test_export_keeps_science_and_finishes_red_on_unknown_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);science=root/'capacity/worker/science';science.mkdir(parents=True)
            sources=root/'sources';sources.mkdir();out=root/'publish'
            saved={'report.json':b'{"synthetic_export_test":true}\n',
                'call-000001.json':b'{"synthetic_export_test":true}\n',
                'call-000001-initial-region-0-Common.brep':b'SYNTHETIC IO BYTES; NOT A CAD RESULT\n'}
            for name,data in saved.items():(science/name).write_bytes(data)
            (science/'private-runtime.log').write_text('unreviewed runtime sentinel')
            (science/'call-000002.json').write_text('{"private":"/tmp/unreviewed-runtime"}')
            (science/'call-000003-fixed-input.brep').symlink_to(science/'private-runtime.log')
            proc=subprocess.run([sys.executable,'-B',str(Path(exporter.__file__)),'--case',str(root),
                '--sources',str(sources),'--output',str(out)],capture_output=True)
            self.assertEqual(proc.returncode,2)
            manifest=json.loads((out/'MANIFEST.json').read_text())
            self.assertEqual(set(manifest),set(saved)|{'EXPORT_SCOPE.json'})
            for name,data in saved.items():
                self.assertEqual((out/name).read_bytes(),data)
                self.assertEqual(manifest[name]['sha256'],hashlib.sha256(data).hexdigest())
            scope=json.loads((out/'EXPORT_SCOPE.json').read_text())
            self.assertEqual(len(scope['omitted_unreviewed_JSON']),3)
            self.assertNotIn('unreviewed runtime sentinel',json.dumps(scope))
            self.assertNotIn('private-runtime.log',json.dumps(scope))
            self.assertFalse(scope['raw_runtime_exported'])


if __name__=='__main__':unittest.main()
