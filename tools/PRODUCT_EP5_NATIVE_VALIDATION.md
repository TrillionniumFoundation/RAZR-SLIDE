# EP5 native research CI

`native-product-ep5` is a required input to `current-suites`, alongside the
unchanged EP4 gate, all configured unit suites and the existing native jobs.
Run it from a clean committed checkout with the locked research environment:

```sh
uv run --locked python -B tools/verify_product_ep5_native.py \
  --expected-head "$(git rev-parse HEAD)" \
  --output "$RUNNER_TEMP/razr-product-ep5-native" \
  --timeout-seconds 3000
```

The driver executes the local 46-body study at STOW, PREDOCK and OPEN, reads
those STEP outputs in a separate process, then executes the complete
154/154/161-body scenes and separately reads their STEP outputs. The local
three-pose matrix has 3,105 unordered pairs. The complete three-pose matrix
has 36,442 unordered pairs, including external/external pairs. The independent
reader owns detailed inventory, finite-value, containment and export checks;
the driver additionally requires every pose, body count, pair count and source
identity expected by this CI job.

## Exact committed source and actual native input roles

The driver reuses the audited EP4 HEAD/tree/blob source binding. It then reads
`integration/ep5_input_closure.py` from the same verified commit and binds each
required native input to its actual HEAD blob before and after execution.
Missing required inputs fail; files are not omitted merely because they are
unavailable. The role table is shared with the generator and independent reader.
Every native report must retain exactly the requested role table and its hashes.

| Mode | Required data inputs |
| --- | --- |
| Local study | Three active design configurations |
| Complete study, default | Those configurations plus ten named engineering payloads |
| Complete study, explicit original members | Those configurations plus nine named engineering payloads and the complete verified member input |

The named engineering inputs include panel-bearing templates, the PAWL and
cam-v5 native archive/manifest sets, the original mounted geometry manifest,
and the thin-mechanism `native-verification.json.gz` motion recipe. The default
path additionally requires the original mounted tar. Historical contact,
bench, capture, KEY-cover and thin tar containers are not consumed by this
EP5 execution and are not substituted or labelled recovered by this driver.
The full repository verifier retains its own complete fixture requirements.

The driver verifies the actual running driver and identity helper, both
independently executed reader sources, and the report bytes read by each reader.
Index assume-unchanged or skip-worktree flags cannot make changed required
input bytes pass. Locked runtime dependencies inside `.venv` are recorded as
runtime dependencies rather than tracked project source. Child commands use
`sys.executable`, so they remain in the interpreter selected by `uv run --locked`.

## Explicit original-member input for a scoped local execution

The default CI command above requires the original tracked mounted tar. There
is no automatic fallback. When that original container is unavailable, the
following explicit option accepts only a previously retained complete directory
of the 64 byte-identical original STEP members and its sibling recovery receipt:

```sh
uv run --locked python -B tools/verify_product_ep5_native.py \
  --expected-head "$(git rev-parse HEAD)" \
  --verified-mounted-members /absolute/path/recovered-original-members \
  --output /absolute/path/new-ep5-validation \
  --timeout-seconds 3000
```

The current committed `verified_native_members.py` validator checks the original
manifest identity, all member names, bytes and SHA256 values, and the receipt.
The driver forwards this option only to the complete native mode. It requires
the complete verification object to agree before execution, in the native
report before and after generation, in the independent reader, and after the
whole validation. Any changed member or receipt fails the execution gate.
The output records `archive_available` separately from
`verified_original_members`; it never claims to have recovered the original tar.

This is a scoped native validation. Its report keeps `full_checkout_verified`
and `all_configured_unit_suites_executed` false. A successful scoped run does not
convert unavailable historical fixtures into a complete checkout or make the
separate full unit verifier pass.

## Results and CI operation

A successful research job means the declared executions and independent reads
completed. Positive Common or escaped material remains a geometric rejection
in `research_scopes`; it is not an execution failure when its complete
diagnostics can be read. Kernel failures, missing required inputs or poses,
stale or changed source bytes and failed readers fail the job. Neither
finite-pose clearance nor job success grants G2 acceptance, continuous
complete-phone clearance, physical qualification, fixture fabrication or
manufacturing release. All product release flags remain false.

Outputs and command logs are retained on success or failure in the job artifact.
The job has a 60-minute limit and a 3,000-second combined command budget. The
current execution branch `work/gate-closure-20261022` is explicitly included
in the push trigger; PR and manual workflow triggers remain available.
