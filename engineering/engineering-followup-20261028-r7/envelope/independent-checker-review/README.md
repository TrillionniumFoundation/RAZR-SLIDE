# V9 independent checker: cross-author source review

Root authored the new independent checker. The envelope producer author
reviewed that checker without importing or executing it. The final V2
review records 79 static and semantic checks, including the 60 unchanged
original independent functions, the two explicitly renamed old functions,
the nine unchanged core proof/control functions, exact source bindings,
independent full-Line endpoint and four-corner arithmetic, the strict
whole-D forward equality, and the new actual-control applicability rules.

The final checker is 141983 bytes with SHA-256
`d79fa404ce3311ecb9c8ab0f89791bde7bc33c738d4f791a09d1376081d89435`.
The final review is `R7E_V9_CROSS_AUTHOR_CHECKER_STATIC_REVIEW_V2.json`.
Its actual source review took 0.14439372800006822 seconds and reported
41041920 bytes peak RSS. No checker, producer, native geometry or channel
search ran as part of this review. Static eligibility does not establish
mathematical or physical qualification.

The earlier V1 review passed the same 79 semantic/static checks but had
a metadata counting error: the output-path uniqueness check appended to
the stored check list after its count had already been captured. Thus
V1 recorded count 79 and a list of 80 entries. V1 is preserved, with an
explicit correction record. V2 keeps that output-path gate separate and
asserts exact count/list agreement. The checker source did not change.

`MANIFEST.json` enumerates all regular members other than itself with
full byte sizes and SHA-256 digests. The frozen source package and actual
mathematical execution are separate evidence.
