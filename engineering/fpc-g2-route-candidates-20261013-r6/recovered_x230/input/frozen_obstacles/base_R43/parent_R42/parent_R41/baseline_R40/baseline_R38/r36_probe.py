import cadquery as cq
from r25_capture import blk,intersection,P
from r30_mechanics import mirrored
from r35_parts import *
from r25_dynamic import POSES
from r24_mechanics import r21
A=cq.importers.importBrep('cad/R35_A_R34_UNCHANGED.brep').val();B=cq.importers.importBrep('cad/R35_B_INBOARD_RAILS_AND_GUIDES.brep').val()
anchor=blk(32.76,34.48,5.28,7.25,1.83,3.40)
plate=blk(32.20,32.44,4.5,6.96,2.055,3.015)
shank=cq.Solid.makeCylinder(.4,2.,cq.Vector(32.20,6.18,2.53),cq.Vector(1,0,0))
head=cq.Solid.makeCylinder(.65,.30,cq.Vector(31.90,6.18,2.53),cq.Vector(1,0,0))
screw=head.fuse(shank).clean()
plate=plate.cut(cq.Solid.makeCylinder(.43,.28,cq.Vector(32.18,6.18,2.53),cq.Vector(1,0,0))).clean()
for name,shape in [('anchor',anchor),('plate',plate),('screw',screw)]:
 print(name,'V',shape.Volume(),'valid',shape.isValid(),'B',intersection(shape,B),'A',intersection(shape,A))
print('plate screw',intersection(plate,screw),'plate pin',intersection(plate,pin('R')),'anchor cap',intersection(anchor,bored_cap('R')),'anchor pin',intersection(anchor,pin('R')),'anchor gauge',intersection(anchor,te_signal_envelope('R')),'anchor plate',intersection(anchor,plate))
B2=B.fuse(anchor).clean()
print('B2',B2.isValid(),len(B2.Solids()),B2.Volume()-B.Volume())
for mode,ss in [('installed',pin('R')),('withdraw',pin('R').translate((-.05,0,0)))]:print(mode,'plate pin overlap',intersection(plate,ss))
for tag,s,q in POSES:
 ref=r21.r17_assembly(P,s,q,1 if tag=='OPEN_SEATED' else 0)
 t=(0,s,q-P.z_travel)
 print('POSE',tag,[(n,round(intersection(sh.translate(t),A),8),round(intersection(sh.translate(t),ref['OLED']),8),round(intersection(sh.translate(t),ref['FPC']),8)) for n,sh in [('anchor',anchor),('plate',plate),('screw',screw)]])
