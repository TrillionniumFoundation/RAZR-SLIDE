"""Independent full-grid audit using paired monotone box extensions.

The producer uses per-ray minimum and maximum arrays. This verifier instead
builds full 3-D unions of upward and downward extended boxes, intersects those
unions, and compares every positive-width cell to the compressed ledger. No
producer function is imported; no native Boolean is used.
"""
from pathlib import Path
from fractions import Fraction as F
import os,resource,signal,time,json,gzip,hashlib,datetime,traceback
resource.setrlimit(resource.RLIMIT_AS,(805306368,805306368))
resource.setrlimit(resource.RLIMIT_CPU,(120,120))
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
signal.alarm(120)
import numpy as np

ROOT=Path(__file__).resolve().parent
PANEL=ROOT.parent/'panel_fill_work'
INPUT=PANEL/'fibre-intersection-attempt1/report.json'
NATIVE=PANEL/'native-boundaries-attempt4/report.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ident(p):return {'path':str(p),'bytes':Path(p).stat().st_size,'sha256':sha(p)}

start=time.monotonic()
report={'schema':'razr-r12-independent-full-cell-fibre-audit-v1',
    'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source':ident(__file__),'producer_source':ident(PANEL/'compute_fibre_intersection_r12.py'),
    'input_report':ident(INPUT),'native_boundary_source':ident(NATIVE),
    'completed':False,'pairs':[],'failures':[]}

def material_cover(indexed,shape):
    combined=np.ones(shape,dtype=bool)
    zonly=None
    for axis in range(3):
        negative=np.zeros(shape,dtype=bool);positive=np.zeros(shape,dtype=bool)
        for box in indexed:
            # Two monotone extensions, with exact coordinate-grid endpoints.
            low=[slice(a,b) for a,b in box];high=list(low)
            low[axis]=slice(0,box[axis][1])
            high[axis]=slice(box[axis][0],shape[axis])
            negative[tuple(low)]=True;positive[tuple(high)]=True
        hull=negative&positive
        if axis==2:zonly=hull.copy()
        combined &= hull
    return zonly,combined

try:
    entry=json.loads(INPUT.read_text());native=json.loads(NATIVE.read_text())
    assert entry['completed'] and native['completed']
    assert sha(NATIVE)==entry['native_boundary_report']['sha256']
    for pair in entry['pairs']:
        key=pair['label'];proof_paths={mode:Path(row['proof']['path']) for mode,row in pair['results'].items()}
        decoded={}
        for mode,path in proof_paths.items():
            assert sha(path)==pair['results'][mode]['proof']['sha256']
            with gzip.open(path,'rt') as stream:decoded[mode]=json.load(stream)
        base=decoded['Z_only'];grid=[list(map(F,a)) for a in base['grid_exact']]
        assert all(all(a<b for a,b in zip(g,g[1:])) for g in grid)
        shape=tuple(len(a)-1 for a in grid)
        assert shape==tuple(pair['grid']['grid_intervals'])
        all_boxes=[]
        for name in ('A_BACK_PANEL',key):
            boxes=[[[F(a),F(b)] for a,b in face['complete_swept_support']] for face in native['bodies'][name]['faces']]
            assert len(boxes)==(298 if name=='A_BACK_PANEL' else 92)
            all_boxes.append(boxes)
        for axis in range(3):
            assert set(grid[axis])=={v for boxes in all_boxes for box in boxes for v in box[axis]}
        for b,boxes in enumerate(all_boxes):
            indexed=base['indexed_boundary_boxes'][b]
            assert len(indexed)==len(boxes)
            for expected,indices in zip(boxes,indexed):
                assert [[grid[k][a],grid[k][c]] for k,(a,c) in enumerate(indices)]==expected
        first=material_cover(base['indexed_boundary_boxes'][0],shape)
        second=material_cover(base['indexed_boundary_boxes'][1],shape)
        item={'key':key,'positive_width_cells_verified':int(np.prod(shape)),'modes':{},
              'all_native_boundary_boxes_bound_exactly_to_grid':True}
        for mode,index in [('Z_only',0),('XYZ_intersection',1)]:
            ledger=decoded[mode]
            assert ledger['grid_exact']==base['grid_exact'] and ledger['indexed_boundary_boxes']==base['indexed_boundary_boxes']
            actual=first[index]&second[index]
            declared=np.zeros(shape,dtype=bool);cursor=0;volume=F(0)
            for piece in ledger['x_pieces']:
                a,b=piece['x_grid_interval'];assert a==cursor and a<b<=shape[0];cursor=b
                area=F(0);seen_y=[]
                for j,runs in piece['occupied_y_rows']:
                    assert 0<=j<shape[1] and j not in seen_y;seen_y.append(j)
                    previous=-1;length=F(0)
                    for c,d in runs:
                        assert 0<=c<d<=shape[2] and c>previous;previous=d
                        declared[a:b,j,c:d]=True;length+=grid[2][d]-grid[2][c]
                    area+=(grid[1][j+1]-grid[1][j])*length
                local=(grid[0][b]-grid[0][a])*area
                assert local==F(piece['exact_volume']);volume+=local
            assert cursor==shape[0] and np.array_equal(actual,declared)
            hashed=hashlib.sha256()
            for slab in actual:hashed.update(np.packbits(slab,axis=None).tobytes())
            assert hashed.hexdigest()==ledger['packed_complete_intersection_mask_sha256']
            assert int(actual.sum())==ledger['occupied_open_cells']
            assert volume==F(ledger['exact_intersection_upper_volume'])==F(pair['results'][mode]['exact_upper_mm3'])
            gate=volume<=F(1e-7);assert gate==pair['results'][mode]['original_1e_minus7_gate_passes']
            item['modes'][mode]={'all_open_cells_match_independent_monotone_extension_construction':True,
                'exact_volume':str(volume),'volume_approx_mm3':float(volume),'original_gate_passes':gate,
                'positive_tiny_cells_preserved':True,'packed_mask_sha256':hashed.hexdigest()}
        report['pairs'].append(item)
        del first,second,actual,declared
    report['completed']=True
    report['scientific_scope']={'numeric_ledger_and_entire_cell_masks_independently_verified':True,
        'conditional_fibre_cover_proof_valid':True,
        'fibre_proof':'For each material point and fixed transverse coordinates, compactness supplies boundary exits in both axis directions. If every boundary point is covered by recorded boxes, the point lies between the lowest and highest covered boundary ordinates. Intersecting the X/Y/Z fibre covers preserves inclusion. Grid endpoints partition the closed boxes exactly; omitted grid-plane cells have zero 3-D volume.',
        'complete_source_boundary_to_actual_native_filling_bridge_fully_proved':False,
        'uniform_compiled_evaluator_error_fully_bounded':False,
        'positive_upper_bound_proves_actual_collision':False,
        'current_key_panel_conservative_1e_7_gate_passes':False,
        'whole_15D_G2':False,'G3':False,'G4':False,'G5':False,'manufacturing_go':False}
except BaseException as exc:
    report['failures'].append({'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()})
finally:
    signal.alarm(0);report['seconds']=time.monotonic()-start
    report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    (ROOT/'FIBRE_COMPLETE_GRID_INDEPENDENT_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'completed':report['completed'],'seconds':report['seconds'],'peak_RSS_bytes':report['peak_RSS_bytes'],'failures':report['failures']}))
raise SystemExit(0 if report['completed'] else 1)
