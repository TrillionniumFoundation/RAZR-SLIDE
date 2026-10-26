"""Flat 26-channel research artwork bound to the current EP5 material identity.

This is not an OEM display/USB/power interconnect.  The 188 mm outline follows
the EP5 material width law; bare copper is independently read back from the
generated KiCad S-expressions.  Supplier stackup, electrical loading, impedance,
dynamic strain and manufacturing acceptance remain unknown.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path

from product_interfaces import sexp, children

ROOT = Path(__file__).resolve().parents[1]
ROUTE = ROOT / 'design/product_routing_ep5.json'
RULES = {'track_width_mm': .15, 'end_pitch_mm': .4,
         'middle_pitch_mm': .37, 'pad_width_mm': .25,
         'pad_length_mm': 4., 'pad_center_y_mm': 3.,
         'minimum_clearance_mm': .1, 'minimum_copper_edge_mm': .5,
         'channels': 26, 'taper_segments': 32}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def route_input(path=ROUTE):
    data = json.loads(Path(path).read_text())
    if data.get('schema') != 'razr-product-routing-ep5-v1':
        raise ValueError('EP5 material configuration required')
    expected = {'free_length_mm': 164, 'total_material_length_mm': 188,
                'stiffened_length_each_end_mm': 12, 'middle_width_mm': 10.8,
                'endpoint_width_mm': 12, 'taper_length_each_end_mm': 4,
                'thickness_assumption_mm': .1}
    if any(data.get('route', {}).get(k) != v for k, v in expected.items()):
        raise ValueError('EP5 material dimensions changed; rederive the artwork')
    if not isinstance(data.get('candidate_id'), str) or not data['candidate_id']:
        raise ValueError('named EP5 candidate required')
    if any(data.get(k) is not False for k in ('candidate_go', 'fixture_fabrication_go',
                                              'manufacturing_go', 'supplier_dynamic_qualified')):
        raise ValueError('research input cannot claim release or supplier qualification')
    return data


def width(y, config):
    r = config['route']; length = r['total_material_length_mm']
    if not 0 <= y <= length:
        raise ValueError('material station outside EP5')
    edge = min(y, length-y)-r['stiffened_length_each_end_mm']
    u = min(1., max(0., edge/r['taper_length_each_end_mm']))
    q = u*u*u*(10.-15.*u+6.*u*u)
    return r['endpoint_width_mm']+(r['middle_width_mm']-r['endpoint_width_mm'])*q


def outline(config):
    r = config['route']; end = r['stiffened_length_each_end_mm']
    length = r['total_material_length_mm']; taper = r['taper_length_each_end_mm']
    stations = sorted({0., end, length-end, length} |
        {end+taper*i/RULES['taper_segments'] for i in range(RULES['taper_segments']+1)} |
        {length-end-taper*i/RULES['taper_segments'] for i in range(RULES['taper_segments']+1)})
    # Explicit polygon approximation of the same smooth quintic width law.
    right = [(round(width(y, config)/2, 9), round(y, 9)) for y in stations]
    return right + [(-x, y) for x, y in reversed(right)]


def channels(config):
    r = config['route']; length = r['total_material_length_mm']; end = r['stiffened_length_each_end_mm']
    result = []
    for i in range(RULES['channels']):
        n = i-(RULES['channels']-1)/2
        xe, xm = round(n*RULES['end_pitch_mm'], 9), round(n*RULES['middle_pitch_mm'], 9)
        points = [(xe, 3.), (xe, 6.), (xm, end), (xm, length-end),
                  (xe, length-6.), (xe, length-3.)]
        result.append({'net': f'C{i+1:02}', 'pin': str(i+1), 'points': points})
    return result


def pcb(config):
    r = config['route']; rows = channels(config)
    lines = ['(kicad_pcb (version 20221018) (generator "razr_ep5_research")',
        '(general (thickness 0.1)) (paper "A4")',
        '(layers (0 "F.Cu" signal) (31 "B.Cu" signal) (36 "B.SilkS" user) (37 "F.SilkS" user) (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user) (48 "B.Fab" user) (49 "F.Fab" user))',
        '(setup (stackup (layer "F.Mask" (type "Top Solder Mask") (thickness .010)) (layer "F.Cu" (type "copper") (thickness .018)) (layer "dielectric 1" (type "core") (thickness .062) (material "UNSELECTED_RESEARCH_STACK")) (layer "B.Cu" (type "copper") (thickness 0)) (layer "B.Mask" (type "Bottom Solder Mask") (thickness .010)) (copper_finish "None") (dielectric_constraints no)) (pad_to_mask_clearance 0))',
        '(net 0 "")']
    for i, row in enumerate(rows, 1):
        lines.append(f'(net {i} "{row["net"]}")')
    for end, index in (('A', 0), ('B', -1)):
        lines.append(f'(footprint "RAZR_EP5:END26_{end}" (layer "F.Cu") (at 0 0) (attr smd)')
        y = 8 if end == 'A' else r['total_material_length_mm']-8
        lines.append(f'(fp_text reference "J{end}" (at 0 {y}) (layer "F.Fab") (effects (font (size .8 .8) (thickness .1))))')
        lines.append('(fp_text value "OWNED_CONTINUITY_ONLY" (at 0 0) (layer "F.Fab") hide (effects (font (size .8 .8) (thickness .1))))')
        for i, row in enumerate(rows, 1):
            x, y = row['points'][index]
            lines.append(f'(pad "{i}" smd rect (at {x} {y}) (size .25 4) (layers "F.Cu" "F.Mask") (net {i} "{row["net"]}"))')
        lines.append(')')
    for i, row in enumerate(rows, 1):
        for a, b in zip(row['points'], row['points'][1:]):
            lines.append(f'(segment (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (width .15) (layer "F.Cu") (net {i}))')
    points = outline(config)
    for a, b in zip(points, points[1:]+points[:1]):
        lines.append(f'(gr_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (layer "Edge.Cuts") (width .05))')
    return '\n'.join(lines+[')'])+'\n'


def _item(node, kind):
    found = children(node, kind)
    if len(found) != 1:
        raise ValueError('expected one '+kind)
    return found[0]


def _xy(node, kind):
    item = _item(node, kind)
    if len(item) != 3:
        raise ValueError('two coordinates required')
    values = tuple(float(x) for x in item[1:])
    if not all(math.isfinite(x) for x in values):
        raise ValueError('nonfinite native coordinate')
    return values


def _point_segment(p, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    length = dx*dx+dy*dy
    t = 0. if length == 0 else max(0., min(1., ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length))
    return math.hypot(p[0]-a[0]-t*dx, p[1]-a[1]-t*dy)


def _segments(a, b, c, d):
    def cross(p, q, r):
        return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    ab1, ab2, cd1, cd2 = cross(a,b,c), cross(a,b,d), cross(c,d,a), cross(c,d,b)
    if ab1*ab2 <= 0 and cd1*cd2 <= 0:
        if max(min(a[0],b[0]),min(c[0],d[0])) <= min(max(a[0],b[0]),max(c[0],d[0])) and max(min(a[1],b[1]),min(c[1],d[1])) <= min(max(a[1],b[1]),max(c[1],d[1])):
            return 0.
    return min(_point_segment(a,c,d), _point_segment(b,c,d), _point_segment(c,a,b), _point_segment(d,a,b))


def verify_artwork(payload, config):
    """Read actual emitted pads, tracks, outline and stack; never trust counts."""
    parsed = sexp(payload)
    tree = parsed[0] if len(parsed) == 1 and isinstance(parsed[0], list) else parsed
    if not tree or tree[0] != 'kicad_pcb':
        raise ValueError('native KiCad board required')
    allowed = {'version','generator','general','paper','layers','setup','net','footprint','segment','gr_line'}
    if any(not isinstance(x,list) or not x or x[0] not in allowed for x in tree[1:]):
        raise ValueError('unreviewed board material or copper object')
    if float(_item(_item(tree,'general'),'thickness')[1]) != config['route']['thickness_assumption_mm']:
        raise ValueError('board thickness differs from EP5 assumption')
    stack = _item(_item(tree,'setup'),'stackup')
    layer_thickness = [float(_item(x,'thickness')[1]) for x in children(stack,'layer')]
    if not math.isclose(sum(layer_thickness), .1, abs_tol=1e-12):
        raise ValueError('requested stack sum differs from geometric thickness')
    nets = {int(x[1]): x[2] for x in children(tree,'net')}
    if len(children(tree,'net')) != 27 or nets != {0:''}|{i:f'C{i:02}' for i in range(1,27)}:
        raise ValueError('all 26 owned continuity identities required')
    pads = {}
    for footprint in children(tree,'footprint'):
        if any(not isinstance(x,list) or not x or x[0] not in {'layer','at','attr','fp_text','pad'} for x in footprint[2:]):
            raise ValueError('unreviewed footprint material')
        if _xy(footprint,'at') != (0.,0.):
            raise ValueError('unexpected endpoint placement')
        refs = [x for x in children(footprint,'fp_text') if x[1] == 'reference']
        if len(refs) != 1 or refs[0][2] not in ('JA','JB'):
            raise ValueError('unknown endpoint')
        ref = refs[0][2]
        for pad in children(footprint,'pad'):
            key = (ref,pad[1]); n = _item(pad,'net')
            if key in pads or pad[2:4] != ['smd','rect'] or _xy(pad,'size') != (.25,4.):
                raise ValueError('duplicate or changed pad geometry')
            if _item(pad,'layers')[1:] != ['F.Cu','F.Mask']:
                raise ValueError('unexpected pad copper layer')
            if int(n[1]) not in nets or n[2] != nets[int(n[1])]:
                raise ValueError('pad net identity differs')
            pads[key] = {'xy':_xy(pad,'at'), 'net':int(n[1])}
    expected = channels(config)
    if set(pads) != {(end,str(i)) for end in ('JA','JB') for i in range(1,27)}:
        raise ValueError('endpoint inventory incomplete')
    for i, row in enumerate(expected,1):
        for ref,index in (('JA',0),('JB',-1)):
            if pads[(ref,str(i))] != {'xy':row['points'][index], 'net':i}:
                raise ValueError('pad location or continuity identity differs')
    tracks = []
    for segment in children(tree,'segment'):
        a,b = _xy(segment,'start'),_xy(segment,'end'); n = int(_item(segment,'net')[1])
        w = float(_item(segment,'width')[1])
        if n not in range(1,27) or w != .15 or _item(segment,'layer')[1] != 'F.Cu' or a == b:
            raise ValueError('invalid research copper segment')
        tracks.append((n,a,b,w))
    expected_tracks = [(i,a,b,.15) for i,row in enumerate(expected,1) for a,b in zip(row['points'],row['points'][1:])]
    if len(tracks) != len(set(tracks)) or set(tracks) != set(expected_tracks):
        raise ValueError('missing, extra, disconnected or changed copper path')
    edges = []
    for line in children(tree,'gr_line'):
        if _item(line,'layer')[1] != 'Edge.Cuts':
            raise ValueError('unreviewed graphic material')
        edges.append((_xy(line,'start'),_xy(line,'end')))
    points = outline(config); expected_edges = list(zip(points,points[1:]+points[:1]))
    if len(edges) != len(set(edges)) or set(edges) != set(expected_edges):
        raise ValueError('flat material outline differs from EP5 width law')
    # Conservative capsule distance for all different-net copper tracks.
    clearance = min(_segments(a,b,c,d)-(w+v)/2 for j,(n,a,b,w) in enumerate(tracks)
                    for m,c,d,v in tracks[j+1:] if n != m)
    track_edge = min(_segments(a,b,c,d)-w/2 for _,a,b,w in tracks for c,d in edges)
    pad_edge = min(config['route']['endpoint_width_mm']/2-abs(p['xy'][0])-.125 for p in pads.values())
    pad_clearance = RULES['end_pitch_mm']-RULES['pad_width_mm']
    # Fan-in starts beyond the complete rectangular pad (Y=5), so no other
    # pad is reached by a different-net fan.  Explicitly check all pad edges.
    pad_track = math.inf
    for (_,pin),p in pads.items():
        x,y = p['xy']; rect = [(x-.125,y-2),(x+.125,y-2),(x+.125,y+2),(x-.125,y+2)]
        for n,a,b,w in tracks:
            if n == p['net']:
                continue
            if any(x-.125 <= q[0] <= x+.125 and y-2 <= q[1] <= y+2 for q in (a,b)):
                pad_track = min(pad_track,-w/2)
            else:
                pad_track = min(pad_track,min(_segments(a,b,c,d) for c,d in zip(rect,rect[1:]+rect[:1]))-w/2)
    if min(clearance,pad_clearance,pad_track) < RULES['minimum_clearance_mm']-1e-9 or min(track_edge,pad_edge) < RULES['minimum_copper_edge_mm']-1e-9:
        raise ValueError('research copper/edge rule failed')
    return {'unique_owned_nets':26,'pads':len(pads),'tracks':len(tracks),
            'closed_outline_edges':len(edges),'complete_copper_paths_verified':True,
            'track_clearance_mm':clearance,'pad_clearance_mm':pad_clearance,
            'pad_to_other_track_clearance_mm':pad_track,
            'minimum_copper_edge_clearance_mm':min(track_edge,pad_edge),
            'thickness_and_stack_sum_match_EP5':True,
            'native_KiCad_DRC_executed':False,'supplier_rules_confirmed':False}


def export(output, route_path=ROUTE):
    output = Path(output); config = route_input(route_path)
    source_before = sha(__file__); route_before = sha(route_path)
    if output.exists():
        raise ValueError('use a new output directory')
    board = pcb(config); verified = verify_artwork(board,config)
    output.mkdir(parents=True)
    (output/'ep5_continuity26.kicad_pcb').write_text(board)
    project = {'board':{'design_settings':{'rules':{'min_clearance':.1,'min_track_width':.1,'min_copper_edge_clearance':.5}}},
               'meta':{'filename':'ep5_continuity26.kicad_pro','version':1},
               'net_settings':{'classes':[{'name':'Default','clearance':.1,'track_width':.15,'via_diameter':.6,'via_drill':.3,'diff_pair_width':.15,'diff_pair_gap':.1,'diff_pair_via_gap':.25}],'meta':{'version':3}}}
    (output/'ep5_continuity26.kicad_pro').write_text(json.dumps(project,indent=2)+'\n')
    rows = channels(config)
    with (output/'conductor-schedule.csv').open('w',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=('net','A_owned_pin','B_owned_pin','end_x_mm','middle_x_mm','OEM_assignment'))
        writer.writeheader()
        for row in rows:
            writer.writerow({'net':row['net'],'A_owned_pin':row['pin'],'B_owned_pin':row['pin'],
                'end_x_mm':row['points'][0][0],'middle_x_mm':row['points'][2][0],'OEM_assignment':''})
    outline_rows = [{'x_mm':x,'material_y_mm':y} for x,y in outline(config)]
    (output/'flat-material-outline.json').write_text(json.dumps(outline_rows,indent=2)+'\n')
    result = {'schema':'razr-ep5-flat-research-ecad-v1','candidate_id':config['candidate_id'],
        'EP5_route_sha256':route_before,'generator_sha256':source_before,
        'source_scope':'same EP5 188 mm flat material outline and owned continuity copper; no OEM assignments',
        'material':{k:config['route'][k] for k in ('total_material_length_mm','free_length_mm','stiffened_length_each_end_mm','middle_width_mm','endpoint_width_mm','taper_length_each_end_mm','thickness_assumption_mm')},
        'research_rules':RULES,'parsed_artwork_verification':verified,
        'verification_scope':'same-program parser and analytic geometry checks; not independent CAD-kernel or KiCad DRC',
        'legacy_164mm_coupon_reused':False,'research_26_conductors_routed_in_flat_artwork':True,
        'three_dimensional_copper_strain_or_contact_checked':False,
        'OEM_pinmap':None,'USB_impedance_qualified':False,'power_current_rating_A':None,
        'supplier_finished_stackup_selected':False,'supplier_dynamic_qualified':False,
        'physical_sample_manufactured_or_tested':False,'candidate_go':False,
        'fixture_fabrication_go':False,'manufacturing_go':False,
        'files_sha256':{p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()}}
    if sha(__file__) != source_before or sha(route_path) != route_before:
        raise ValueError('source changed during research export')
    (output/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args()
    print(json.dumps(export(args.output),indent=2))
