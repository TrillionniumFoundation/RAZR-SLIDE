# Back-panel counterbore finite-wall candidate

Base42fc8149. Existing1.90mm counterbores are tangent to1.90mm guide width. Two independent volume-mesh attempts rejected the unmodified whole panel. New fixed straight strips add3.564mm3 only to A_BACK_PANEL; bore radius, screw, historical guide reference, PAWL/KEY/frame and all other33templates remain unchanged. Nominal sidewall becomes0.15mm, not a verified material/process allowance. The original ring-style candidate produced invalid boolean unions and is not used.

20new local geometry tests passed. Full756test coverage and current native full must be read from actual reports, not this configuration. Optional Gmsh/scikit-fem structural investigations are separate from the locked standard CAD checks; no actual material,preload or force is invented. All hardware go flags remainfalse.
