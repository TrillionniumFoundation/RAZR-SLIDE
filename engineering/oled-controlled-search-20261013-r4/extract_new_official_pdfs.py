#!/usr/bin/env python3
"""Read two exact public PDF inputs without redistributing their text or images."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

INPUTS = {
    'environment.pdf': ('6a3c2afda91bde4872013f24266c30c2e258afa5536bd335c404294bb93aa4fd', 591375, 10),
    'eprel_fiche.pdf': ('a00256725edebc70c14a43c70a17788b9f23b2a1bca0c1d78e81f777dd3b0687', 60330, 2),
}

def get_pages(cache, name):
    raw = (cache / name).read_bytes()
    expected, size, count = INPUTS[name]
    assert len(raw) == size and hashlib.sha256(raw).hexdigest() == expected, name
    result = subprocess.run(['pdftotext', '-layout', str(cache / name), '-'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    pages = result.stdout.split('\f')
    if not pages[-1].strip():
        pages.pop()
    assert len(pages) == count, (name, len(pages))
    info = subprocess.run(['pdfinfo', str(cache / name)], capture_output=True, text=True)
    assert info.returncode == 0, info.stderr
    selected_info = {}
    for line in info.stdout.splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            if key in ('CreationDate', 'ModDate', 'Pages', 'PDF version', 'Encrypted'):
                selected_info[key] = value.strip()
    return pages, {'name': name, 'bytes': size, 'sha256': expected, 'pages': count,
                   'pdftotext_exit_code': result.returncode, 'pdfinfo_exit_code': info.returncode,
                   'pdf_metadata': selected_info}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache-root', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    environment, env_receipt = get_pages(args.cache_root, 'environment.pdf')
    fiche, fiche_receipt = get_pages(args.cache_root, 'eprel_fiche.pdf')
    assert 'April 2025' in environment[0]
    assert 'MobileSentrix' in environment[6] and 'iFixit' in environment[6] and 'Replace Base' in environment[6]
    assert '1224*2992' in environment[8]
    assert '500 nits' in environment[8] and '13%' in environment[8]
    assert 'XT2551-6' in fiche[0]
    assert re.search(r'Rated battery capacity.*?4\s*540', fiche[0], re.S)
    assert '22/03/2025' in fiche[1]
    assert '2250774' in fiche[1]
    assert 'https://www.replacebase.eu/motorola-guide' in fiche[1]
    report = {
        'schema': 'razr-slide-new-public-oled-source-extraction-r4-v1',
        'inputs': [env_receipt, fiche_receipt],
        'functional_facts': {
            'environment_report_edition': 'April 2025',
            'environment_report_real_pdf_pages': 10,
            'oem_repair_channel_declaration_pdf_page': 7,
            'oem_repair_channels': ['iFixit (US)', 'MobileSentrix (US)', 'Replace Base (EU)'],
            'oem_main_resolution_source_pdf_page': 9,
            'oem_main_resolution_px': [1224, 2992],
            'reported_oem_relative_display_power_test_luminance_nit': 500,
            'reported_oem_relative_power_reduction_percent': 13,
            'absolute_display_current_or_power_provided': False,
            'eprel_registration': '2250774',
            'eprel_model': 'razr 60 ultra (XT2551-6)',
            'eprel_rated_device_battery_capacity_mAh': 4540,
            'eprel_market_start': '2025-03-22',
            'eprel_repair_instructions_url': 'https://www.replacebase.eu/motorola-guide',
        },
        'selected_donor_identity': None,
        'controlled_module_model': None,
        'full_module_MCAD': None,
        'controlled_FPC_COF_pinout': None,
        'qualified_moving_bend_region': None,
        'minimum_dynamic_bend_radius_mm': None,
        'absolute_power_ratings': None,
        'physical_RAZR_SLIDE_qualification': False,
        'manufacturing_go': False,
    }
    # The output contains own facts, provenance and null missing fields; no copied PDF text.
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'inputs_verified': 2, 'pages_verified': 12, 'report': str(args.report), 'manufacturing_go': False}))

if __name__ == '__main__':
    main()
