# Physical inputs and the next useful engineering step

The nine accepted results are normalized equilibria in one fixed support and contact model. They complete original-case coverage at this scope, not a measured assembly.

## 1. Specify the actual load and assembly path
Resolve which real surfaces restrain the frame and which load locations/magnitudes represent service. Distinguish prescribed initial connector force/adjustment from the force in the equilibrated bolt. A genuine pretension step followed by fixed adjustment and applied service load needs an explicit physical definition; it is not reproduced merely by changing a constant force or comparing two independent equilibria. Do not assign a tightening torque using the catalogue maximum alone.

## 2. Replace assumed head/nut pressure with a justified interface
Current bolt springs use prescribed pressure-weighted displacement. Determine actual head/nut bearing geometry, effective thread bounds and material compliance. Where contact can open, retain single-sided compression and check the existing global load path. Do not convert point multipliers to contact stress by dividing by an invented area.

## 3. Use actual connection data in the existing budget
Keep the existing thread/preload budget and fill it only with attributable effective-thread, material, torque–tension and service-load data. Evaluate each bolt separately using the new transfer results, not a four-way average. Include plate/frame bending and load-path sensitivity before any claim of allowable service force. CAD, donor device, OLED/FPC and dual-battery packaging remain separate unresolved assembly workstreams.

Primary technical references consulted (not adopted as product data):
- SIMULIA Abaqus, Creating and editing bolt loads: https://docs.software.vt.edu/abaqusv2025/English/SIMACAECAERefMap/simacae-t-advboltloadscreate.htm
- SIMULIA Abaqus, Prescribed Assembly Loads: https://abaqus.uclouvain.be/English/SIMACAEPRCRefMap/simaprc-c-pretension.htm
- GetFEM, Small sliding contact with friction bricks: https://getfem.org/userdoc/model_contact_friction.html

These sources clarify load-step and nodal-force semantics. No Abaqus/GetFEM solver was installed or used by this experiment, and no material, preload or manufacturing capability was inferred from their examples.
