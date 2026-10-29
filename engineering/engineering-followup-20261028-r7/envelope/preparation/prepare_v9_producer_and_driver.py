"""Create new named V9 producer/driver from recovered immutable V7 sources."""
from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parent
HERE = ROOT / 'source-v9'


def replace_once(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


def write_new(name, text):
    path = HERE / name
    assert not path.exists(), 'preserve existing new-version source'
    ast.parse(text)
    path.write_text(text)
    return {'path': str(path), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


old_producer = (HERE / 'planar_exterior_refinement_r5e_v7.py').read_text()
p = old_producer
p = replace_once(p, "'real_retained_leaf_selection','static_source_capacity']",
                 "'real_retained_leaf_selection','static_source_capacity','extra_line_plane_source']")
p = p.replace("'razr-r5e-planar-exterior-refinement-v7'", "'razr-r7e-planar-exterior-refinement-v9'")
p = p.replace("'razr-r5e-planar-exterior-tree-v7'", "'razr-r7e-planar-exterior-tree-v9'")
p = p.replace('registered V7 producer differs', 'registered new V9 producer differs')
p = p.replace('registered V7 phase required', 'registered new V9 phase required')
p = p.replace('r5e_v7_frozen_base_channels', 'r7e_v9_frozen_base_channels')
p = p.replace('r5e_v7_planar_source_helpers', 'r7e_v9_planar_source_helpers')
p = replace_once(p, "limits['maximum_total_UV_pieces']==4064", "limits['maximum_total_UV_pieces']==4100 and limits['maximum_planar_models']==50")
p = replace_once(p, "        expected=[(c,f) for c in ['case-001'", "        extra_projection=read(contract['extra_line_plane_source'])\n        expected=[(c,f) for c in ['case-001'")
p = replace_once(p, 'model.build_models(boundary,old,projection,limits)', 'model.build_models(boundary,old,projection,limits,extra_projection)')
p = replace_once(p, "                 'UV_boundary_piece_count':models['total_UV_boundary_piece_count'],",
                 "                 'UV_boundary_piece_count':models['total_UV_boundary_piece_count'],\n                 'additional_original_plane_count':models['additional_original_plane_count'],\n                 'additional_applied_plane_count':models['additional_applied_plane_count'],\n                 'additional_rejected_plane_count':models['additional_rejected_plane_count'],")
p = replace_once(p, "total_uv<=4064 and max_uv<=225 and max_piece<=4096 and total_models+rejected<=(6 if phase=='single_planar_exterior_leaf' else 48)",
                 "total_uv<=4100 and max_uv<=225 and max_piece<=4096 and total_models+rejected<=(8 if phase=='single_planar_exterior_leaf' else 50)")
p = replace_once(p, "            'original_V4_failure_preserved':True,'V5_producer_rerun':False,'V6_producer_rerun':False,'frames':[],",
                 "            'original_V4_failure_preserved':True,'original_V7_failure_preserved':True,\n            'missing_V8_archived_bytes_not_reconstructed':True,\n            'V5_producer_rerun':False,'V6_producer_rerun':False,'frames':[],")

old_driver = (HERE / 'run_portable_planar_r5e_v7.py').read_text()
d = old_driver
for before, after in [
    ('verify_planar_exterior_r5e_v7.py', 'verify_planar_exterior_r7e_v9.py'),
    ('planar_exterior_refinement_r5e_v7.py', 'planar_exterior_refinement_r7e_v9.py'),
    ('planar_exterior_model_r5e_v7.py', 'planar_exterior_model_r7e_v9.py'),
    ('R5E_PORTABLE_SOURCE_LOCK_V7.json', 'R7E_PORTABLE_SOURCE_LOCK_V9.json'),
    ('R5E_PLANAR_EXTERIOR_V7_BASIS.md', 'R7E_ORIGINAL_LINE_PLANE_V9_BASIS.md'),
    ('R5E_V7_STATIC_SOURCE_CAPACITY.json', 'R7E_V9_STATIC_SOURCE_CAPACITY.json'),
    ('razr-r5e-portable-planar-exterior-pipeline-v7', 'razr-r7e-portable-planar-exterior-pipeline-v9'),
    ('razr-r5e-portable-source-lock-v7-planar-exterior-conditioned', 'razr-r7e-portable-source-lock-v9-original-Line-plane-hulls'),
    ('razr-r5e-portable-planar-exterior-contract-v7', 'razr-r7e-portable-planar-exterior-contract-v9'),
    ('razr-r5e-portable-owned-planar-exterior-supervision-v7', 'razr-r7e-portable-owned-planar-exterior-supervision-v9'),
    ("'maximum_total_UV_pieces':4064,'maximum_planar_models':48", "'maximum_total_UV_pieces':4100,'maximum_planar_models':50"),
    ("capacity['actual_total_UV_boundary_pieces']<=4064", "capacity['actual_total_UV_boundary_pieces']<=4100"),
    ('Fixed64 patches/24 terms/4064 totalUV pieces.', 'Fixed64 patches/24 terms/4100 totalUV source pieces, including only the two original Line-plane additions; original48plane census unchanged.')]:
    assert before in d, before
    d = d.replace(before, after)
d = replace_once(d, "                      'planar_model_source':identity(src/'planar_exterior_model_r7e_v9.py'),",
                 "                      'planar_model_source':identity(src/'planar_exterior_model_r7e_v9.py'),\n                      'extra_line_plane_source':identity(src/'R7E_V9_ORIGINAL_LINE_PLANE_PROJECTION.json'),")
d = replace_once(d, '"""Five original owned stages for new V7 planar exterior certificates.',
                 '"""Five original owned stages for new V9 original Line-plane source hulls.')
d = replace_once(d, "         'original_V3_raw_clearance_passes_unchanged':4,'original_V4_selected_cell_bound_and_control_failure_unchanged':True,",
                 "         'original_V3_raw_clearance_passes_unchanged':4,'original_V4_selected_cell_bound_and_control_failure_unchanged':True,\n         'original_V7_failure_preserved':True,'missing_V8_archived_bytes_not_reconstructed':True,")

rows = [write_new('planar_exterior_refinement_r7e_v9.py', p), write_new('run_portable_planar_r7e_v9.py', d)]
assert (HERE / 'planar_exterior_refinement_r5e_v7.py').read_text() == old_producer
assert (HERE / 'run_portable_planar_r5e_v7.py').read_text() == old_driver
print(json.dumps({'created': rows, 'old_V7_sources_unchanged': True, 'workers_executed': False}))
