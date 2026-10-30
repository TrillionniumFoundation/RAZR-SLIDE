# Official OCCT guidance and the remaining formal boundary

The official Open-Cascade-SAS documentation repository describes vertex tolerance as an allowed distance from the vertex point to its representations. Edge tolerance describes consistency of edge representations. The modeling-data guide defines material-side orientation, including the left side of an oriented surface edge. The modeling-algorithms guide describes topological wire connection using shared vertices or compatible vertex tolerances. These descriptions support retaining both topology and geometric tolerances, rather than equating `Closed()` with exact endpoint equality.

They do not establish that a particular compiled face classifier fills exactly the winding domain of arbitrary connector paths inside the proposed rectangles. They also do not bound all compiled arithmetic errors or make Common volume a certified measure. This R13 certificate therefore states its completion-corridor and oriented-filled-domain premises explicitly. No source input is healed or snapped.

Primary references retrieved through web search on 2026-10-30:

- Official BREP format guide: https://github.com/Open-Cascade-SAS/OCCT/wiki/brep_format
- Official modeling-data orientation guide: https://github.com/Open-Cascade-SAS/OCCT/wiki/modeling_data
- Official modeling-algorithms guide: https://github.com/Open-Cascade-SAS/OCCT/blob/master/dox/user_guides/modeling_algos/modeling_algos.md
- Official wire analysis API, describing separate 2-D/3-D/vertex gap checks: https://dev.opencascade.org/doc/occt-7.6.0/refman/html/class_shape_analysis___wire.html

The first three retrieved pages are current official documentation, not pinned copies of the installed OCCT 7.8.1 source. Attempts to retrieve `V7_8_1` versions of the BREP format guide, `BRepClass_FaceClassifier.cxx`, `BRepClass_FaceExplorer.cxx`, and `BRepTopAdaptor_FClass2d.cxx` from both GitHub blob and raw URLs returned fetch errors (`DisabledError`). The 7.8.0 BREP guide URL was also unavailable to the retrieval tool. No unavailable source bytes or formal runtime/source equivalence are claimed. The retained acquisition metadata distinguishes those failures from the accessible documentation.
