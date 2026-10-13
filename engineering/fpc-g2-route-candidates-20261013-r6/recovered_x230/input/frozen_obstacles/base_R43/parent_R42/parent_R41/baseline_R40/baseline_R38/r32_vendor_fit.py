"""R32 official TE catalogue envelope as a known *non-fit* witness.

A manufacturer's axis-aligned bounding envelope is not the STEP contact solid;
this enumerates six axis-aligned configurations only, not arbitrary rotations
or alternative parts. There is NO power or USB qualification from this test.
"""
from __future__ import annotations
import json,itertools
from r25_capture import ROOT
from r32_cartridge import CHANNEL

TE_MM={'length':2.4,'width':1.05,'uncompressed_height':1.2,
       'contact_working_low':.70,'contact_working_high':1.0,'max_A':1.5}
TE_URL='https://www.te.com/en/product-2199001-1.html'


def run(write=True):
    ch=dict(x=round(CHANNEL[1]-CHANNEL[0],6),y=round(CHANNEL[3]-CHANNEL[2],6),z=round(CHANNEL[5]-CHANNEL[4],6))
    orientations=[]
    sizes=(TE_MM['length'],TE_MM['width'],TE_MM['uncompressed_height'])
    for xyz in sorted(set(itertools.permutations(sizes))):
        orientations.append(dict(TE_axis_envelope_xyz_mm=xyz,
            three_axis_aligned_fit=all(a<=b for a,b in zip(xyz,(ch['x'],ch['y'],ch['z'])))))
    d=dict(revision='R32 vendor TE catalogue bounded packaging test, orthogonal only',
       source_official=TE_URL,
       source_dimension_kind='public nominal catalogue envelope; actual supplier STEP not imported',
       official_product_number='2199001-1',
       circuit_application='Signal',
       dimension_mm=TE_MM,
       R32_channel_internal_nominal_mm=ch,
       six_permutations=orientations,
       axis_aligned_envelope_fit_count=sum(p['three_axis_aligned_fit'] for p in orientations),
       requires_real_part_3D_mesh_and_assembly_fit=True,
       real_USB_and_battery_power_connectors_NOT_SELECTED=True,
       cannot_use_1p5A_signal_rating_for_main_battery=True,
       exact_mating_contact_onset_mm_not_known=True,
       manufacturing_go=False)
    if write:(ROOT/'verification'/'R32_vendor_fit.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    return d
if __name__=='__main__':
    d=run();print('R32 TE BOUNDING FIT',d['axis_aligned_envelope_fit_count'],'/',len(d['six_permutations']),flush=True)
