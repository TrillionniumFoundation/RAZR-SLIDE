"""Privacy and failure-classification checks; no KiCad/native qualification."""
import json
import unittest
from diagnose_ec1 import classify_version, project_ldd, commands_projection


class ProjectionChecks(unittest.TestCase):
    def test_loader_missing(self):
        value = classify_version(b'/private/Alice/kicad-cli: error while loading shared libraries: libexample.so.8: cannot open shared object file: No such file or directory\n', 127)
        self.assertEqual(value['classification'], 'loader_missing_library')
        self.assertEqual(value['missing_libraries'], ['libexample.so.8'])
        self.assertNotIn('Alice', json.dumps(value))
        self.assertNotIn('/private', json.dumps(value))

    def test_ldd_needed_names_only(self):
        value = project_ldd(b' linux-vdso.so.1 (0x7fff)\n libexample.so.8 => not found\n libother.so.1 => /private/Alice/libother.so.1 (0x123abc)\n /private/Alice/ld-linux-x86-64.so.2 (0x123abc)\n', 0)
        self.assertEqual([x for x in value['dependencies'] if x['state'] == 'missing'], [{'soname': 'libexample.so.8', 'state': 'missing'}])
        self.assertEqual(len(value['dependencies']), 4)
        self.assertTrue(value['complete_recognized_listing'])
        self.assertNotIn('Alice', json.dumps(value))
        self.assertNotIn('/private', json.dumps(value))

    def test_abi_and_symbol(self):
        value = classify_version(b"private: /private/Alice/libstdc++.so.6: version `GLIBCXX_3.4.33' not found (required by private)\n", 1)
        self.assertEqual(value['classification'], 'loader_missing_symbol_version')
        self.assertEqual(value['missing_ABI_versions'], ['GLIBCXX_3.4.33'])
        value = classify_version(b'private: symbol lookup error: secret_symbol\n', 127)
        self.assertEqual(value['classification'], 'loader_undefined_symbol')
        self.assertNotIn('secret_symbol', json.dumps(value))

    def test_version_does_not_invent_pass(self):
        self.assertEqual(classify_version(b'9.0.9\n', 0)['classification'], 'version_executed')
        self.assertEqual(classify_version(b'9.0.9\n', 1)['classification'], 'unclassified_version_failure')
        self.assertEqual(classify_version(b'/private/Alice 9.0.9\n', 0)['numeric_versions'], [])

    def test_unknown_stays_unknown(self):
        value = project_ldd(b'private@example.org runtime path /private/Alice\n', 1)
        self.assertEqual(value['unrecognized_line_count'], 1)
        self.assertFalse(value['complete_recognized_listing'])
        self.assertEqual(value['dependencies'], [])
        self.assertNotIn('private', json.dumps(value))

    def test_command_allowlist(self):
        value = commands_projection({'commands': [
            {'label': 'kicad-version', 'argv': ['/private/Alice/bin'], 'exit_code': 127, 'seconds': 0.1, 'log_sha256': '1' * 64},
            {'label': '/private/Alice', 'exit_code': 0},
            {'label': 'native-drc', 'seconds': float('nan'), 'log_sha256': '/private/Alice'}]})
        self.assertEqual(len(value), 2)
        self.assertEqual(value[1], {'label': 'native-drc'})
        self.assertNotIn('private', json.dumps(value))


if __name__ == '__main__':
    unittest.main()
