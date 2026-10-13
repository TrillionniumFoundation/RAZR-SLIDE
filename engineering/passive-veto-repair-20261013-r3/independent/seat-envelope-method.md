The original R25/R26 A-key, engaged pawl and parked pawl were instantiated as
actual CadQuery/OCC bodies from the unchanged historical contact sources.
Each input body was validated as one connected, positive signed-volume solid.
No r2/r3 builder main routine was executed and no historical CAD was edited.

The native scan exited 0 after 318.467 seconds. It covered 41 q positions from
−0.100 to +0.100 mm in 0.005 mm increments, both ports and both sides, and all
27 XYZ combinations at each deliberately injected ±0.01, ±0.02 and ±0.05 mm
level. Shared zero offsets and identical actual key translations were reused:
12,956 logical states correspond to 5,204 unique actual geometry profiles.
There were 26,383 signed OCC common calculations and 98,513 proven-zero AABB
comparisons after the actual participating solids were validated. AABB touch
only proves zero material-intersection volume; it does not prove positive gap.

For each profile, the actual original pawl traversed 23 positions from engaged
to its original parked location. A viable research sample requires zero
positive material intersection at every release position and a positive
key/pawl common when the key is withdrawn another 0.05 mm. This last condition
is the original rigid capture witness. Zero common at its touch boundary does
not prove that real hardware escapes or lacks retention.

All four actual port/side combinations returned the same sampled q bands:

| Deliberately injected XYZ error | Full sampled q band (mm) | Nonnegative withdrawal domain (mm) |
|---|---:|---:|
| Nominal | −0.015 to +0.030 | 0 to +0.030 |
| ±0.010, all 27 combinations | −0.005 to +0.020 | 0 to +0.020 |
| ±0.020, all 27 combinations | +0.005 to +0.010 | +0.005 to +0.010 |
| ±0.050, all 27 combinations | No passing sample | No passing sample |

Negative q represents deliberate over-insertion in this contact model. The
phone chassis has not been shown to permit that motion, so negative q cannot
be used to enlarge the usable phone seat window. For the nonnegative domain,
the nominal sampled original-contact window spans 0.030 mm. A proposed r3
research plateau from 0 to +0.015 mm fits inside the injected ±0.010 mm band,
with at least 0.005 mm of nominal geometric margin to its upper limit. This
proposal does not resolve the ±0.020 or ±0.050 mm counterexamples.

The error values are research perturbations, not supplier GD&T. The scan does
not validate the complete r3 guide/chassis, materials, springs, friction,
fasteners, load paths, OLED or production assembly. Actual imported source
bytes remained unchanged. `manufacturing_go=false` remains mandatory.
