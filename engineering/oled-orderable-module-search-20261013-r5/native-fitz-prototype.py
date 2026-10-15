#!/usr/bin/env python3
"""Verify actual supplier PDF bytes and extract only original functional facts."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import fitz

EXPECTED_SHA256 = 'f5fb7cbfb229bd72d4df8e7f784d0da4514c75b045e90a5de295a45bf413d247'
EXPECTED_BYTES = 2982185

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    raw = args.pdf.read_bytes()
    assert len(raw) == EXPECTED_BYTES
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_SHA256
    result = subprocess.run(['pdftotext', '-layout', str(args.pdf), '-'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    pages = result.stdout.split('\f')
    if not pages[-1].strip():
        pages.pop()
    assert len(pages) == 18
    assert 'TA066FHV01-V2049A' in pages[0] and '2026-03-26' in pages[0]
    assert '■' in pages[0] and 'Pre' in pages[0]
    assert 'Final-Specification' in pages[0] and '□' in pages[0]
    assert 'Without TP' in pages[3] and 'RM692E5' in pages[3]
    assert '2240' in pages[3] and '2400' in pages[3]
    assert 'BK13C06-40DP/2-0.35V(865)' in pages[4]
    rows = []
    # PDF text order displaces three wrapped burn-in labels before their number.
    # Use the actual text coordinates, with bounds pinned to this exact PDF hash.
    # These coordinates associate table cells; they do not infer physical dimensions.
    doc = fitz.open(args.pdf)
    for page_number in (4, 5):
        words = doc[page_number].get_text('words')
        for word in words:
            x0, y0, x1, y1, token = word[:5]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if not token.isdigit() or not 1 <= int(token) <= 40 or not 70 <= cx <= 95:
                continue
            if page_number == 4 and cy < 185:
                continue
            symbols, types = [], []
            for entry in words:
                ex0, ey0, ex1, ey1, value = entry[:5]
                ecx, ecy = (ex0 + ex1) / 2, (ey0 + ey1) / 2
                if abs(ecy - cy) > 6:
                    continue
                if 105 <= ecx <= 200:
                    symbols.append((ex0, value))
                elif 205 <= ecx <= 235 and value in ('I/O', 'I', 'O', 'P'):
                    types.append(value)
            assert len(types) == 1, (token, types)
            rows.append((int(token), ' '.join(value for _, value in sorted(symbols)), types[0]))
    assert len(rows) == 40 and sorted(r[0] for r in rows) == list(range(1, 41)), rows
    pins = {r[0]: r[1] for r in rows}
    assert pins[7] == 'AVDD' and pins[8] == 'AVDD_EN'
    assert pins[10] == 'AMOLED_VDDD' and pins[12] == 'ID2'
    assert 'TP_MISO' in pages[4] and 'TP_MOSI' in pages[4]
    assert pages[6].count('TBD') >= 3
    assert '112.39' in pages[16] and 'Max1.01mm' in pages[16] and 'Max0.95mm' in pages[16]
    output = {
        'schema': 'razr-slide-preliminary-orderable-module-inputs-r5-v1',
        'source_sha256': EXPECTED_SHA256,
        'source_bytes': EXPECTED_BYTES,
        'source_pages': 18,
        'supplier_module': 'TA066FHV01-V2049A',
        'issued_date': '2026-03-26',
        'document_revision': '1.0',
        'document_scope': 'pre-specification for parameter checking',
        'customer_sample_approval': False,
        'display_driver': 'RM692E5',
        'nominal_cell_resolution_px': [1080, 2400],
        'specified_actual_display_resolution_px': [1080, 2240],
        'touch_fitted': False,
        '40_numbered_pin_rows_parsed_exactly_once': True,
        'pin_detail_scope': 'preliminary table; drawing assignment column empty',
        'pin_table_has_touch_SPI_despite_no_touch_module': True,
        'unused_touch_pin_disposition_explicitly_confirmed': False,
        'absolute_worst_case_operating_currents': None,
        'current_table_TBD_fields': 3,
        'dimension_inputs_for_research_only': {
            'general_table_nominal_W_H_D_mm': [71.452, 156.640, 0.231],
            'module_drawn_FPC_length_mm': 112.39,
            'local_component_height_limits_mm': [1.01, 0.95],
            'full_module_CAD_referenced_but_supplied': False,
            'drawing_dimension_tolerance_unless_specified_mm': 0.2,
            'CAD_based_unlisted_dimensions': None,
            'controlled_rolling_radius_mm': None,
            'permitted_moving_bend_region': None,
            'full_composite_neutral_axis': None,
        },
        'manufacturer_catalogue_vs_pdf_thickness_scope_resolved': False,
        'released_project_OLED_selection': False,
        'physical_project_qualification': False,
        'manufacturing_go': False,
    }
    args.report.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({'native_pdftotext_exit': result.returncode, 'actual_pages': len(pages),
                      'numbered_pin_rows': len(rows), 'sample_approved': False,
                      'manufacturing_go': False}))

if __name__ == '__main__':
    main()
