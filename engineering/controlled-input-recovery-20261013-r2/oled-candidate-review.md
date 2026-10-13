# OLED module input recovery, 2026-10-13

Two official-linked module PDFs were downloaded and inspected. This is new module-level input, beyond the previously reviewed exhibition announcements. Neither module is released for RAZR SLIDE. `manufacturing_go=false`.

The product remains two equal finished compartment envelopes, one approximately 7-inch flexible display, B translation 79.75 mm followed by 8.2 mm normal seating, and A priority for the larger battery. Neither a smaller rigid screen nor a second display is introduced.

| Candidate | Retrieved module information | Manufacturing consequence |
| --- | --- | --- |
| DFRobot DFR1262 | Official product links a 27-page PDF, document DFX-TM667009 Rev A, effective 2024-08-26. ICNA3511A, four data pairs plus clock, 40-pin assignment, power/reset diagrams, 154.560 × 69.552 mm active area. Official kit includes an HDMI adapter and is specified without touch. | The PDF describes FT3658U touch, on-cell metal mesh, touch FPC, cover-glass outline, and a different apparent assembly scope. The vendor must identify which revision of the underlying module is actually shipped. No dynamic rolling approval was found in the retrieved PDF. |
| DisplayModule DMKDO06501DNA | 44-page vendor-branded PDF V1.0.0, 2025-07-01. RM692E5, four-lane MIPI, BK13C06-40DP/DS interface, dimensioned layer section and FPC tail. LP initialization example is present on PDF pages 23–24. | Pin assignments disagree between the drawing and electrical table. The timing page uses 2240 vertical pixels while general specification uses 2400. These conflicts must be resolved before routing or driving a physical module. No dynamic rolling qualification was found in this PDF. |

The original PDFs, extracted text, and review images stay outside the repository. Their URLs, exact byte lengths, and SHA-256 are in `oled-source-receipt.json`. Git receives original analysis and functional facts only. Supplier-approved project drawings, controlled redistribution permission, and project qualification reports have not been obtained.

The DFRobot PDF was also downloaded from immutable official Git commit `b968714c33210b76d8d2b269ac4a6c3cdcc7e3fd`. Its bytes match the current `main` download. This freezes which public document was reviewed; it does not make its unsigned customer-acceptance page an approval for RAZR SLIDE.

## Material electrical conflicts

The DisplayModule mechanical drawing is part `97065003A`, V1, 2024-11-25. The PDF cover has a later vendor document version. These identifiers are recorded separately; no equivalence between OEM and sales SKU is assumed.

| Location | Drawing, PDF p6 | Electrical table, PDF p7–8 | Effect |
| --- | --- | --- | --- |
| Pin 5/7 | Pin 5 burn-in; pin 7 AVDD | Two pin-5 rows, burn-in and AVDD; pin 7 burn-in | Analog power and special-purpose pads cannot be assigned safely. |
| Pin 8 | AVDD_EN | REST | Power enable versus reset is unresolved. |
| Pin 10 | AMOLED_VDDIO | AMOLED_VDDD | Logic rail naming and allowed voltage require confirmation. |
| Pin 12 | ID2 | GND | Connecting the wrong version could short an identification net to ground. |
| ELVDD side contacts | ELVDD | Description says negative power | Positive ELVDD in the DC rail table conflicts with the terminal description. |

Additional defects are preserved: its ELVSS absolute-rating table puts -1.0 in the minimum column and -5.0 in the maximum column; its touch section labels a voltage-valued row as operating current; and the touch controller is unnamed. None of these is silently repaired. The PDF pin-map conflict CSV contains factual comparisons, not a released netlist.

The DisplayModule nominal rail table provides VDDIO 1.65/1.8/1.95 V and VCI 2.6/3.0/3.6 V, with AVDD 7.6 V, ELVDD 4.6 V, and ELVSS -2.4 V typical. These are candidate study values, not complete tolerance/current/inrush specifications. The power-on page additionally states less than 150 mA for each of VDDIO, VCI, and AVDD, without a full module operating load table. The project must not substitute these values for measured worst-case OLED/touch loads.

The public initialization example ends with sleep-out, a 120 ms delay, and display-on. It is useful for a future sample bring-up. Its compatibility with the ordered revision, actual lane rate, mode totals, DSC status, and complete touch configuration remains unconfirmed. Generic D-PHY timing parameters do not establish the final link rate or full-motion eye/BER performance.

The DisplayModule PDF calls for a `(865)` connector suffix. The bounded current Hirose primary-source lookup returned `(800)` and `(895)` products. The mapping from `(865)` to an orderable exact mate, plating/reel variant, and drawing revision remains unresolved. No substitute is approved here, and BK13 is not treated as the project's separate BM28 static endpoint.

## Mechanical inputs that can be used conditionally

DisplayModule's drawing gives 71.452 ± 0.150 mm width, 156.640 ± 0.150 mm film length, 156.240 ± 0.150 mm OLED length, and a reference active area 69.552 × 154.560 mm. Its 112.386 ± 0.5 mm FPC tail and local component maxima of 1.01/0.95 mm require a separate fixed tail/driver keep-out. The film-region 0.291 ± 0.080 mm must not be used as the entire module thickness.

The drawing labels polarizer 0.105 mm, panel 0.038 mm, film 0.088 mm, and protective film 0.060 mm, summing to 0.291 mm. This is not a copper/material neutral-plane definition or a dynamic bending permit. The role and removal state of the protective film, adhesive properties, cover/touch additions, modulus and strain limits, bend side, sealing keep-outs, and DDIC/COF no-bend regions are still unknown.

The two documents both give 154.560 × 69.552 mm active area, whose calculated rectangle diagonal is 6.6727666093 inches. DisplayModule labels this 6.48 inches. Its 0.060 mm vertical pixel-pitch label multiplied by 2400 yields 144.000 mm, rather than the stated 154.560 mm active height. These discrepancies are retained for supplier resolution; no dimensions are rescaled to fit the label.

The DFRobot drawing includes a cover-glass assembly and a 2.51 mm minimum `CG-BPL Bending` clearance. That annotation is not an OLED dynamic bend radius and is not used as one. The kit's generic 3.3–5 V specification applies to its integration/adapter scope; the bare-module PDF also specifies independent low-voltage and OLED rails. Those two power domains are not collapsed into one.

## Remaining bounded external dependencies

There is no accepted module-specific evidence here for bidirectional rolling through the project's 79.75 mm travel and 8.2 mm seating, flat storage, tension/contact pressure/twist limits, supported material bend axis, full composite neutral plane, optical degradation after cycling, or seals after cycling. Public environmental test conditions are not serial/lot results for the intended assembly. The DisplayModule table points to Visionox reference results without providing such reports; the DFRobot sales page explicitly excludes humidity testing for the supplied bare kit. Neither establishes the final phone's qualification.

`oled-specific-requests.json` requests exact corrections and documents for these real candidates. No supplier contact, NDA acceptance, purchase, or sample receipt occurred. Production selection and physical qualification remain open.
