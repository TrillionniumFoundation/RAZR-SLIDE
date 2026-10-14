"""Pinned, already independently checked native STEP participants for admission.
No scene regeneration or STEP healing is performed. Only the explicit locator
window changes; all other serialized product-part payloads remain exact.
"""
from pathlib import Path
from functools import lru_cache
import hashlib,json,tarfile,tempfile
import cam_contact_native as n
from verify_contact_motion import PARTS
ROOT=Path(__file__).resolve().parents[1]
BASE_COMMIT='25a33b90a781f35aa47f15c6b319ac48e18f0b9c'
EXPECTED_ARCHIVE_SHA256='29567f531d7b81727fa1d4aa25df2d1ef913858137fb5719406ac65bcf786cef'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

@lru_cache(maxsize=2)
def _load(side):
    if side not in ('L','R'):raise ValueError('invalid side')
    base=ROOT/'engineering/keycover-geometry-20261014';archive=base/'project-owned-geometry.tar.gz';manifest=json.loads((base/'geometry-manifest.json').read_text())
    if sha(archive)!=EXPECTED_ARCHIVE_SHA256 or manifest['archive_sha256']!=EXPECTED_ARCHIVE_SHA256:raise ValueError('pinned STEP archive differs')
    entries={x['path']:x for x in manifest['files']};parts={};identity={}
    with tempfile.TemporaryDirectory() as tmp,tarfile.open(archive,'r:gz') as tar:
        for name in sorted(PARTS):
            member='motion/'+side+'_'+name+'.step';item=tar.getmember(member)
            if not item.isfile():raise ValueError('not a regular native file')
            b=tar.extractfile(item).read();reference=entries[member]
            if len(b)!=reference['bytes'] or hashlib.sha256(b).hexdigest()!=reference['sha256']:raise ValueError('native participant identity differs')
            p=Path(tmp)/(name+'.step');p.write_bytes(b);roots=n.cq.importers.importStep(str(p)).vals()
            if len(roots)!=1:raise ValueError('unaccounted native roots')
            parts[name]=n.single(roots[0]);identity[name]={'archive_member':member,'sha256':reference['sha256']}
    if len(parts)!=23:raise ValueError('incomplete native participant set')
    return parts,identity

def load_parts(side,*,original_closed_locator=False):
    if type(original_closed_locator) is not bool:raise ValueError('explicit boolean control required')
    source,identity=_load(side);parts=dict(source)
    if not original_closed_locator:
        cover=parts['OLD_COVER'];window=n.box(side,-3.16,-2.68,2.98,3.22,-7.25,-6.43);new=n.single(cover.cut(window).clean())
        delta=n.whole_material(cover.cut(new),empty=True)[1]
        if abs(delta-.04416)>1e-7 or n.whole_material(new.cut(cover),empty=True)[1]>1e-7:raise ValueError('locator subtraction differs')
        parts['OLD_COVER']=new
    return parts,{'base_commit':BASE_COMMIT,'archive_sha256':EXPECTED_ARCHIVE_SHA256,'native_part_identity':identity,'scene_builder_imported':False,'native_files_healed_or_rewritten':False,'only_changed_part':None if original_closed_locator else 'OLD_COVER','locator_capture_qualified':False}

def at(shape,offset):
    # A zero transform must not unnecessarily reconstruct native wire topology.
    return shape if all(x==0 for x in offset) else shape.translate(offset)
