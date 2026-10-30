"""Prefix-guided search; only complete channels can prove a volume bound.

The prefix is a heuristic. No absent piece or unscanned channel is excluded.
Every claimed cylinder/slab bound carries two complete source censuses.
"""
from fractions import Fraction as F
import cylinder_slab_r9 as base
from cylinder_slab_r9 import common,math,cached


def scan(observation,source,models,D,report,complete=False):
    """Resume a recorded prefix without counting its old tests twice."""
    side=observation['material_side'];shift=base.source_shift(side,D)
    channel=math.box(observation['channel_exact'])
    codes=list(observation['codes']);claims=observation['new_claims']
    unknown=observation['unresolved_piece_indices']
    for index in range(len(codes),len(source['pieces'])):
        piece=source['pieces'][index];report['counts']['pieces']+=1
        if report['counts']['pieces']>12000000:raise RuntimeError('original piece cap')
        code=cached.old_separate(piece,channel)
        if code is not None:codes.append(code);continue
        model=models.get((piece['kind'],piece['index']))
        claim=math.correlate(model,math.box(piece['box_exact']),channel,shift) if model else None
        if claim is None:
            codes.append('?');unknown.append(index)
            if not complete:break
            continue
        code={'plane':'P','line':'L','quadric':'Q','empty_closed_intersection':'E'}[claim['code']]
        claim.update(material_key=source['material_key'],piece_index=index,
                     original_kind=piece['kind'],original_index=piece['index'],channel_exact=math.encbox(channel))
        codes.append(code);claims.append(claim);report['counts']['new_'+claim['code']]+=1
    observation.update(codes=''.join(codes),scan_mode='complete' if len(codes)==len(source['pieces']) else 'prefix',
                       failure=None if not unknown else {'piece_index':unknown[0]})
    return observation


def evaluate(B,sources,models,D,report):
    observations=[]
    for side,source in enumerate(sources):
        for axis in range(3):
            for end in (0,1):
                channel=common.channel_for(B,math.box(source['known_whole_exact']),axis,end)
                observation={'material_side':side,'axis':axis,'end':end,'channel_exact':math.encbox(channel),
                             'codes':'','new_claims':[],'unresolved_piece_indices':[],'failure':None}
                report['counts']['channels']+=1
                scan(observation,source,models[side],D,report)
                observations.append(observation)
                if not observation['unresolved_piece_indices']:
                    return {'kind':'complete_exterior_channel','bound_exact':'0','observations':observations,
                            'selected_channel':len(observations)-1,'candidate_search_is_proof':False}
    # These provisional objects use only prefixes. They rank work; they never
    # enter a certificate as valid material restrictions.
    candidates=[]
    for ci,c in enumerate(observations):
        side=c['material_side'];cyl=base.cylinder_candidate(c,sources[side],models[side],D)
        if cyl is None:continue
        for si,s in enumerate(observations):
            other=s['material_side']
            if other==side:continue
            for slab in base.slab_candidates(s,sources[other],models[other],D):
                cheap=base.combine(B,cyl,slab,D)
                value=F(cheap['bound_exact'])
                if value<common.volume(B):candidates.append((value,ci,si))
    candidates=sorted(set(candidates))
    attempted=[]
    for _,ci,si in candidates[:2]:
        attempted.append([ci,si])
        for index in (ci,si):
            observation=observations[index];side=observation['material_side']
            scan(observation,sources[side],models[side],D,report,complete=True)
        c,s=observations[ci],observations[si];side,other=c['material_side'],s['material_side']
        cyl=base.cylinder_candidate(c,sources[side],models[side],D)
        if cyl is None:continue
        choices=[]
        for slab in base.slab_candidates(s,sources[other],models[other],D):
            bound=base.combine(B,cyl,slab,D);choices.append((F(bound['bound_exact']),slab,bound))
        if not choices:continue
        value,slab,bound=min(choices,key=lambda item:item[0])
        if value<common.volume(B):
            return {'kind':'cylinder_slab_upper_bound','bound_exact':str(value),'observations':observations,
                    'cylinder_channel':ci,'slab_channel':si,
                    'cylinder':{k:v for k,v in cyl.items() if k!='basis'},'slab':slab,'combination':bound,
                    'candidate_search_is_proof':False,'candidate_pairs_attempted':attempted}
    return {'kind':'unresolved_full_box','bound_exact':str(common.volume(B)),'observations':observations,
            'candidate_search_is_proof':False,'candidate_pairs_attempted':attempted}
