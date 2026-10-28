"""Separate certificate checker: no producer import, CAD import, or Common.

Reconstructs channels, checks complete per-piece disjunction certificates and
all retained volumes using only exact Fraction arithmetic.
"""
import argparse
from fractions import Fraction as Q
import gzip
import hashlib
import json
from pathlib import Path
import resource
import time
import traceback


def need(ok, message):
    if not ok: raise ValueError(message)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def bound(item, parent=None):
    path = Path(item['path']) if parent is None else parent/item['path']
    need(path.stat().st_size == item['bytes'] and digest(path) == item['sha256'], 'input bytes or digest differ')
    return path


def box(strings):
    ranges = tuple(tuple(Q(x) for x in pair) for pair in strings)
    need(len(ranges) == 3 and all(len(p)==2 and p[0]<=p[1] for p in ranges), 'ordered 3D bounds')
    return ranges


def signed_measure(ranges):
    need(all(a < b for a,b in ranges), 'positive diagonal required')
    return (ranges[0][1]-ranges[0][0])*(ranges[1][1]-ranges[1][0])*(ranges[2][1]-ranges[2][0])


def reconstructed_sources(proof, stationary):
    d = box(proof['full_remaining_displacement_box_exact'])
    cover = proof['complete_raw_boundary_slab_cover']
    sources = []
    for s,name in enumerate(('first_complete_boundary_boxes','second_complete_boundary_boxes')):
        pieces = []
        for p in cover[name]:
            b = box(p['box_exact'])
            if stationary and s==0:
                b = tuple((v[0]-d[k][0],v[1]-d[k][1]) for k,v in enumerate(b))
            pieces.append(b)
        limits = tuple((min(p[k][0] for p in pieces),max(p[k][1] for p in pieces)) for k in range(3))
        sources.append((pieces,limits))
    return sources


def check_exclusion(item, target, sources):
    need(item['excluded_open_interior'] is True, 'exclusion marker')
    need(item['whole_closed_cell_disjoint_claimed'] is False and item['closed_cell_boundary_retained_as_zero_volume_carrier'] is True,
         'open-interior-only scope required')
    side,axis,end = item['material_side'],item['axis'],item['end']
    need(type(side) is int and 0<=side<len(sources) and type(axis) is int and 0<=axis<3 and end in (0,1), 'valid selected channel')
    pieces,whole = sources[side]
    channel = box(item['open_channel_exact'])
    need(all(a<b for a,b in channel), 'connected open channel')
    need(all(channel[k]==target[k] for k in range(3) if k!=axis), 'channel transverse footprint changed')
    if end==0:
        need(channel[axis][1]==target[axis][1] and channel[axis][0]<min(whole[axis][0],target[axis][0]), 'lower channel misses known exterior')
    else:
        need(channel[axis][0]==target[axis][0] and channel[axis][1]>max(whole[axis][1],target[axis][1]), 'upper channel misses known exterior')
    codes = item['complete_piece_separation_codes']
    need(type(codes) is str and len(codes)==len(pieces)==item['boundary_piece_count'], 'incomplete per-piece certificate')
    for piece,code in zip(pieces,codes):
        need(code in '012345', 'invalid separation code')
        k,t = divmod(int(code),2)
        need(piece[k][1]<=channel[k][0] if t==0 else piece[k][0]>=channel[k][1], 'boundary box is not separated from open channel')
    return len(pieces)


def check_blocked(item, target, sources):
    need(item['excluded_open_interior'] is False and item['actual_material_interference_claimed'] is False, 'unresolved channel cannot establish collision')
    rows = item['all_registered_channels_blocked']
    need(len(rows)==6*len(sources), 'complete registered blocked channels')
    seen = set()
    for row in rows:
        s,k,end,i = row['material_side'],row['axis'],row['end'],row['blocking_piece_index']
        need((s,k,end) not in seen, 'duplicate blocked direction');seen.add((s,k,end))
        pieces,whole = sources[s];piece=pieces[i]
        ranges = list(target)
        ranges[k] = (min(whole[k][0]-1,target[k][0]-1),target[k][1]) if end==0 else (target[k][0],max(whole[k][1]+1,target[k][1]+1))
        need(all(piece[j][1]>ranges[j][0] and piece[j][0]<ranges[j][1] for j in range(3)), 'recorded blocker misses channel')
    need(seen=={(s,k,e) for s in range(len(sources)) for k in range(3) for e in (0,1)}, 'blocked channel coverage differs')


def negative_controls(good, target, sources):
    # These mutate copies only; original scientific bytes never change.
    results = []
    def reject(name, item):
        error=None
        try: check_exclusion(item,target,sources)
        except (ValueError,IndexError,TypeError) as exc: error=str(exc)
        need(error is not None, 'corrupted certificate accepted: '+name)
        results.append({'name':name,'actual_rejected':True,'reason':error})
    changed=dict(good);changed['complete_piece_separation_codes']=good['complete_piece_separation_codes'][:-1]
    reject('omitted-complete-boundary-piece',changed)
    changed=dict(good);changed['whole_closed_cell_disjoint_claimed']=True
    reject('overclaim-closed-cell-disjointness',changed)
    changed=dict(good);channel=[list(p) for p in good['open_channel_exact']];k=good['axis'];e=good['end']
    channel[k][e]=str(target[k][e]);changed['open_channel_exact']=channel
    reject('channel-does-not-reach-known-exterior',changed)
    changed=dict(good);codes=list(good['complete_piece_separation_codes']);pieces,_=sources[good['material_side']];c=box(good['open_channel_exact'])
    done=False
    for i,piece in enumerate(pieces):
        for new in '012345':
            j,t=divmod(int(new),2)
            holds=piece[j][1]<=c[j][0] if t==0 else piece[j][0]>=c[j][1]
            if not holds:
                codes[i]=new;changed['complete_piece_separation_codes']=''.join(codes);done=True;break
        if done:break
    need(done,'no false separating inequality found for negative control')
    reject('false-separating-coordinate',changed)
    return results


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();c=json.loads(args.contract.read_text())
    need(digest(__file__)==c['verifier_sha256'],'registered verifier identity')
    args.output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    report={'schema':'razr-r5e-exterior-channel-independent-algorithm-verification-v2','execution_completed':False,
            'producer_code_imported':False,'native_Common_called':False,'frames':[],'negative_controls':[],
            'native_boundary_semantics_verified':False,'compiled_error_bound_verified':False,'full_continuous_G2':False}
    def save():
        report['seconds']=time.monotonic()-start;report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        producer_path=bound(c['producer_report']);producer=json.loads(producer_path.read_text())
        need(producer['execution_completed'] and producer['phase']!='preflight','completed actual certificate source required')
        baseline_path=bound(producer['source_report_identity']);baseline=json.loads(baseline_path.read_text())
        source_rows={(r['case_id'],r['frame']):r for r in baseline['frames']}
        stationary=producer['phase']=='single_stationary_witness'
        diagnosis=None
        if stationary:
            diagnosis=json.loads(bound(c['r4_stationary_diagnostic']).read_text())
        for row in producer['frames']:
            key=(row['case_id'],row['frame']);old=source_rows[key]
            need(row['source_proof']['sha256']==old['proof']['sha256'],'producer proof detached from original report')
            with gzip.open(bound(row['source_proof']),'rt') as stream: proof=json.load(stream)
            need(row['original_remaining_displacement_box_exact']==proof['full_remaining_displacement_box_exact']==old['full_remaining_displacement_box_exact'],'full original D differs')
            sources=reconstructed_sources(proof,stationary)
            with gzip.open(bound(row['certificate'],producer_path.parent),'rt') as stream: cert=json.load(stream)
            records=cert['cells']
            original_cells=proof['complete_raw_boundary_slab_cover']['combined']['positive_cells']
            if stationary:
                original=next(x for x in diagnosis['rows'] if (x['case_id'],x['frame'])==key)['zero_displacement_spatial_cover_witness']
                original_cells=[{'box_exact':original['stationary_enclosure_positive_cell_exact'],'positive_directed_volume_exact':original['stationary_enclosure_cell_volume_exact']}]
            need(len(records)==len(original_cells)==row['candidate_cell_count'],'complete cell coverage')
            excluded=Q(0);kept=Q(0);checked=0;excluded_count=0
            for i,(item,oldcell) in enumerate(zip(records,original_cells)):
                need(item['cell_index']==i and item['box_exact']==oldcell['box_exact'],'original positive cell changed or reordered')
                target=box(item['box_exact']);v=signed_measure(target)
                need(v==Q(item['positive_directed_volume_exact'])==Q(oldcell['positive_directed_volume_exact']),'cell directed determinant volume changed')
                if item['excluded_open_interior']:
                    checked+=check_exclusion(item,target,sources);excluded+=v;excluded_count+=1
                    if not report['negative_controls']:report['negative_controls']=negative_controls(item,target,sources)
                else:
                    check_blocked(item,target,sources);kept+=v
            need(excluded==Q(row['removed_open_cell_sum_exact']) and kept==Q(row['retained_cell_sum_exact']),'remaining upper volume differs')
            need(excluded+kept==Q(row['original_disjoint_cell_sum_exact']),'original full sum differs')
            need(row['all_cell_boundaries_retained_as_zero_volume_carriers'] is True,'omitted zero-volume carriers')
            chosen=kept
            if not stationary:
                need(kept+excluded==Q(proof['complete_raw_boundary_slab_cover']['combined']['sum_directed_volume_exact']),'original slab sum not conserved')
                chosen=min(kept,Q(old['coarse_whole_support_upper_exact_mm3']))
                need(chosen==Q(row['selected_conditional_raw_upper_exact_mm3']),'selected upper differs')
                need(chosen<=Q(old['conditional_complete_material_intersection_upper_exact_mm3']),'new upper exceeds inherited bound')
                need(old['original_min_volume_plus_TOL_gate_passed'] is True and row['original_min_volume_plus_TOL_gate_passed'] is True,'upper sanity gate inheritance failed')
            need(row['conditional_raw_clearance_gate_passed']==(chosen<=Q(1e-7)),'original float64 threshold gate differs')
            report['frames'].append({'case_id':key[0],'frame':key[1],'complete_cells':len(records),'excluded_cells':excluded_count,
                                     'independently_checked_boundary_piece_separations':checked,'retained_upper_exact':str(chosen),
                                     'original_clearance_gate_passed':chosen<=Q(1e-7)})
            save()
        need(report['negative_controls'],'no actual exclusion certificate for negative checks')
        report['conditional_clearance_passes']=sum(r['original_clearance_gate_passed'] for r in report['frames'])
        report['execution_completed']=True
    except BaseException as exc:
        report['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()};raise
    finally:
        save();print(json.dumps({k:report.get(k) for k in ('execution_completed','conditional_clearance_passes','seconds','peak_RSS_bytes','failure')}),flush=True)


if __name__=='__main__':main()
