## Why this change

The equal-cabin sliding phone needs one traceable assembly for the mechanism, flat OLED storage in B, complete flexible-material ends, the larger A cell, and reversible manual operation. This PR implements the common research assembly, connects evidence to actual specimens and commits, and records the geometric failures that still prevent a physical build.

## Current identities

- Published PR head: `90b09f5ef7c25aafd812909101b3d7d80081ba05`.
- Formal donor acquisition source: `f4db100cb62c0ac492118bf605b0e9e7ac7cce32`.
- EP3 source and 109-test selection: `bdb1bc19fce49692fd49cd508031bfc456e15208`.
- Limited native API repair and completed three-pose CAD execution: `a33e58cd555b8d9aff1e3649f79cd0dba378a804`.
- The publication commit archives results, the independently executed reader/controllers, and current state. Its 14 native input files match the executed a33e58c source exactly.
- Accepted main remains `a1b3cc1e0773446f2e36d0a607edf61211dd9919`. PR #36 is open and unmerged; PR #35 remains a separate draft at `176df31ceb35bb3737d68030e60ba377665de210`; PR #25 is closed without merging its old driver.

## What changed and what actually ran

### Actual donor and interfaces

The formal collector used Pocket4's existing ADB server at `127.0.0.1:5061`. All 17 read-only commands succeeded; transport ID stayed 37 and the server boot/PID/start identity did not change. USB and ADB serial hashes identify the same XT2551-3 specimen. Source and design inputs match f4db100.

The immutable imported record confirms the model only: **10 identity fields, seven physical part roles and all 12 terminal interfaces remain unbound**. An empty hardware-revision property was retained as unknown. Collection/import success does not freeze physical board, OLED/COF, cell or connector versions. Earlier software battery values and OEM capacities keep their original source and time scopes.

### Complete EP3 ends, finite material and common assembly

EP3 retains **20 finite bodies per end**, four small PCBs in total, and **124 mm** of material: 100 mm free plus two 12 mm stiffened tails. The candidate uses a 0.35 mm outer stiffener jaw and a nominal 1.4 mm M2 shaft; both remain research dimensions without selected processes or qualified retention.

The completed native execution took **656.874 seconds**, used unchanged source bytes, and performed **15,906 pair checks** with **zero pair-evaluation and zero containment-evaluation errors**. Pair counts include AABB separations and are not a count of Boolean operations.

| Pose | Complete participants | External pairs | Positive external Common pairs | Positive material/end Common pairs | Candidate bodies outside both cabin prisms | Result |
|---|---:|---:|---:|---:|---:|---|
| STOW | 154 | 4,633 | 6 | 0 | 0 | Rejected |
| PREDOCK | 154 | 4,633 | 5 | 4 | 1 | Rejected |
| OPEN | 161 | 4,920 | 5 | 4 | 0 | Rejected |

Both endpoint self-checks clear all 190 pairs. The whole-phone candidate remains rejected:
- The A carrier jaw intersects the A battery allocation by **18 mm³** in every pose.
- PREDOCK finite material has **49.088288346 mm³** outside the two separate cabin prisms. Its independently isolated low-straight witness has volume, Common with the finite ribbon, and residual outside both prisms of **35.031250526 mm³**.
- PREDOCK material intersects the B carrier jaw, both B mini PCBs and the static 26-wire transfer reservation.
- OPEN material intersects two B M1 board shafts, the B carrier jaw and the B DP PCB.
- The fixed single-U family has incompatible B-anchor requirements of at most 11.5 mm and at least 21 mm. This 9.5 mm contradiction is scoped to that endpoint orientation, layer arrangement and path family.

Five STEP files were independently read in a separate process in **32.628 seconds**. Counts 20 / 20 / 154 / 154 / 161, valid positive solids, and injective bounds/volume matching for the **41 recorded candidate bodies per pose** passed. The other 113 / 113 / 120 objects have no per-object generator metric baseline in the report; full-assembly material/label equivalence is not claimed. Readback success does not remove the collisions or establish continuous motion.

### Preserved failure and limited repair

The first native run on bdb1bc1 stopped after **427.276 seconds** without a complete final report. It retained six actual STOW collisions, 20 errors from cutting an already valid empty residual a second time, and a PREDOCK NumPy-scalar rejection at the strict box boundary.

a33e58c changes only validated empty-residual handling and the local built-in-float conversion. Candidate configuration and endpoint construction are unchanged. Eight native API cases retain real outside material, a small positive residual and a free-Face error correctly. The six STOW collision names and volumes match the first run. Original failure, checkpoint, logs, diff, repair and fresh results are all archived.

### Earlier engineering results remain separate

Phase2 still retains the OLED 0.6 mm material-length window, approximately 0.131197 mm PREDOCK flat tail, the rejected EP2 complete-end geometry, and its original OPEN collisions. Twelve local insertion sweeps and local reassembly/readback results remain evidence of those local operations; thin joints, whole-device tool access, physical hold/release, skew and reverse relocking remain unqualified.

Measured part geometry, real OLED/COF dynamic conditions, complete fabricated samples, the modified protected electrical phone chain and measured structural loads are not yet available. PR35 has no new FE/QP execution; identified response/points/trace state is still required.

## Validation and its scope

| Source / action | Actual result | Scope |
|---|---|---|
| 3e6864c donor collector selection | 102 tests, 13 errors | Retained legacy mock-interface failure |
| f4db100 fixture-only repair | Same 102 test identities pass | Actual collector source unchanged by the fixture repair |
| bdb1bc1 product + EP3 selection | 109 tests / 2 suites pass; no failures, errors or skips | Source before/after unchanged |
| a33e58c bounded repair | 7 EP3 tests + 8 native API cases + 1 scalar witness pass | Neither 109 nor 1310 tests were rerun in full |
| a33e58c native study | All three poses completed; all candidates rejected | 15,906 pair checks, zero evaluation errors |
| Independent reader | Declared five-file checks pass | 41 candidate metrics per pose; limited external baseline coverage |
| Publication-input verification | Sync check + 5 existing state tests pass; 28 relative links valid | 108-file artifact index and 14 native inputs verified |

The configured **1310 tests / 34 suites are not a new complete PASS**. Prior phase2 full 1297-test failure, 14-test repair, and disjoint 32+1 suite selection retain their original two-execution scope.

## Hosted Actions on the published head

[Run 39378151409](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409), attempt 1, is tied to exact `90b09f5ef7c25aafd812909101b3d7d80081ba05`.

The retained observation from **2026-10-20 06:04:33–06:05:08 UTC** is a live snapshot: the run was still **queued**, with **11 visible new jobs and zero executed steps**. The `full-unit-suites` and `native-phone-layout` jobs had completed as failure with runner ID 0; both directly retrieved annotations state that recent account payments failed or the spending limit needs increasing. The other nine jobs were queued. No result was inherited from an earlier attempt. The provider annotation does not distinguish the two account conditions.

The read-only inspector received **13 HTTP 200 responses**, recorded no collection error, and returned exit 2 because no successful hosted report exists. Original report: **43,094 bytes**, SHA256 `2b28a67da7715815101c2e822c6fd9d7b601b5d4a22d023c8e9358f6c1b58e86`. The complete retained JSON is included below without triggering another source commit. This is not a claim that all jobs have reached their final status.

Earlier f4db100 run 39359899335 and 42679be run 39355931047 each retain their own 12-job, zero-step, directly annotated reports in the committed phase3 evidence. They are not substituted for the new-head observation. Hosted execution remains open; no account billing, repository visibility, workflow or branch-protection setting was changed.

## Reviewable evidence

- [Current execution and engineering conclusions](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5ef7c25aafd812909101b3d7d80081ba05/engineering/product-integration-20261018/phase3-20261020/README.md)
- [Machine-readable summary](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5ef7c25aafd812909101b3d7d80081ba05/engineering/product-integration-20261018/phase3-20261020/SUMMARY.json)
- [Exact native failures, containment and readback scope](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5ef7c25aafd812909101b3d7d80081ba05/engineering/product-integration-20261018/phase3-20261020/native-summary.json)
- [Formal donor import and remaining identity fields](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5ef7c25aafd812909101b3d7d80081ba05/engineering/product-integration-20261018/phase3-20261020/hardware/DONOR_IMPORT.md)
- [Immutable actual donor record](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5ef7c25aafd812909101b3d7d80081ba05/engineering/product-integration-20261018/hardware/records/xt2551-3-20261020-f4db100-identity/record.json)
- [Original native failure and its checkpoint](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5ef7c25aafd812909101b3d7d80081ba05/engineering/product-integration-20261018/phase3-20261020/native-first-failure/native-execution-failure.json)
- [Limited repair and actual regression](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5ef7c25aafd812909101b3d7d80081ba05/engineering/product-integration-20261018/phase3-20261020/validation/ep3-api-repair/native-api-regression.json)
- [Independent STEP readback](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5ef7c25aafd812909101b3d7d80081ba05/engineering/product-integration-20261018/phase3-20261020/validation/ep3-independent-readback/report.json.gz)
- [108-file byte index](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5ef7c25aafd812909101b3d7d80081ba05/engineering/product-integration-20261018/phase3-20261020/artifact-index.json)
- [Publication-input verification](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5ef7c25aafd812909101b3d7d80081ba05/engineering/product-integration-20261018/phase3-20261020/validation/publication-input-verification.json)
- [Next physical inputs and direct acceptance outputs](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5ef7c25aafd812909101b3d7d80081ba05/engineering/product-integration-20261018/phase3-20261020/NEXT_PHYSICAL_INPUTS.md)

## Remaining acceptance work

1. Match the identified specimen to physical board/module/COF/cell labels, measured geometry and connector terminals.
2. Replace allocations with those parts; resolve the already occupied B 12 mm bands, A battery/jaw interference, cell tabs/swelling, RF/thermal space and the 4700 mAh target.
3. Jointly change endpoint direction, layer-transfer opening and material-storage region; verify complete finite OLED/FPC material, support and forward/return travel with sourced dynamic conditions.
4. Select manufacturable thin sections and joints, fabricate unpowered parts, assemble in order and measure operation force, release/hold, skew and reverse motion.
5. Measure flexible specimens and end retention, then use the identified original protected electrical chain for staged display/touch/power/USB tests.
6. Introduce measured materials, spans and internal loads; resume PR35 only with the complete identified cache.
7. Resolve the account payment/budget condition, then obtain an actually executed hosted report on an explicit head.

`candidate_go`, `fixture_fabrication_go`, `manufacturing_go`, physical-platform freeze and powered-phone acceptance remain false.
## Concrete next geometry decisions

The next bounded study should address the observed geometry together:

- Keep the A anchor and PCBs fixed; investigate moving the carrier plate's material-Y front limit from 7 mm to at least 13.2 mm, with the connecting web relocated into that plate. This removes the current plate/battery overlap in the stated coordinate calculation, but connected solid validity and all other contacts still require native checking.
- Investigate placing the complete B PCB/carrier/static-transfer group behind the free endpoint. The current PREDOCK and OPEN collisions affect different parts, so changing only a clamp screw cannot solve both states.
- Separate the Z transition from length storage: investigate an S transition through the cabin-overlap region followed by a B-local return bend. A limited arc-length calculation leaves outer-envelope space under the present allocations, but it does not establish an actual opening, support, dynamic radius qualification or clearance against the complete assembly.
- Obtain the actual Common solids, bounds and neighboring wall sections at A_FRAME, B_SHELL and the KEYs before proposing openings. A collision volume alone does not locate a manufacturable cutout.

These are next design decisions, not an additional executed CAD candidate or a released manufacturing drawing.


<details>
<summary>Complete original published-head Actions inspection JSON — 43,094 bytes</summary>

```json
{
  "schema": "razr-actions-inspection-v1",
  "repository": "TrillionniumFoundation/RAZR-SLIDE",
  "observed_utc": "2026-10-20T06:04:33.495191+00:00",
  "collector_sha256": "de87e3a81ac2aa3df70121905c19b3f92aea9d5c9ae5e1fd79b8d08c157bb593",
  "read_only": true,
  "expected_head": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
  "requested_run_id": 39378151409,
  "responses": [
    {
      "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409",
      "status": 200,
      "data": {
        "id": 39378151409,
        "name": "Research validation",
        "node_id": "WFR_kwLOVGyQz88AAAAJKx7n8Q",
        "head_branch": "work/product-integration-20261018",
        "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
        "path": ".github/workflows/research-ci.yml",
        "display_title": "Integrate WP0\u2013WP8 research assembly, interfaces and verified evidence",
        "run_number": 124,
        "event": "pull_request",
        "status": "queued",
        "conclusion": null,
        "workflow_id": 385032350,
        "check_suite_id": 106706983717,
        "check_suite_node_id": "CS_kwDOVGyQz88AAAAY2DtbJQ",
        "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409",
        "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409",
        "pull_requests": [
          {
            "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/pulls/36",
            "id": 4914837333,
            "number": 36,
            "head": {
              "ref": "work/product-integration-20261018",
              "sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
              "repo": {
                "id": 1416401103,
                "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE",
                "name": "RAZR-SLIDE"
              }
            },
            "base": {
              "ref": "main",
              "sha": "a1b3cc1e0773446f2e36d0a607edf61211dd9919",
              "repo": {
                "id": 1416401103,
                "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE",
                "name": "RAZR-SLIDE"
              }
            }
          }
        ],
        "created_at": "2026-10-20T06:02:45Z",
        "updated_at": "2026-10-20T06:02:45Z",
        "actor": {
          "login": "ProfHepta",
          "id": 102159240,
          "node_id": "U_kgDOBhbTiA",
          "avatar_url": "https://avatars.githubusercontent.com/u/102159240?v=4",
          "gravatar_id": "",
          "url": "https://api.github.com/users/ProfHepta",
          "html_url": "https://github.com/ProfHepta",
          "followers_url": "https://api.github.com/users/ProfHepta/followers",
          "following_url": "https://api.github.com/users/ProfHepta/following{/other_user}",
          "gists_url": "https://api.github.com/users/ProfHepta/gists{/gist_id}",
          "starred_url": "https://api.github.com/users/ProfHepta/starred{/owner}{/repo}",
          "subscriptions_url": "https://api.github.com/users/ProfHepta/subscriptions",
          "organizations_url": "https://api.github.com/users/ProfHepta/orgs",
          "repos_url": "https://api.github.com/users/ProfHepta/repos",
          "events_url": "https://api.github.com/users/ProfHepta/events{/privacy}",
          "received_events_url": "https://api.github.com/users/ProfHepta/received_events",
          "type": "User",
          "user_view_type": "public",
          "site_admin": false
        },
        "run_attempt": 1,
        "referenced_workflows": [],
        "run_started_at": "2026-10-20T06:02:45Z",
        "triggering_actor": {
          "login": "ProfHepta",
          "id": 102159240,
          "node_id": "U_kgDOBhbTiA",
          "avatar_url": "https://avatars.githubusercontent.com/u/102159240?v=4",
          "gravatar_id": "",
          "url": "https://api.github.com/users/ProfHepta",
          "html_url": "https://github.com/ProfHepta",
          "followers_url": "https://api.github.com/users/ProfHepta/followers",
          "following_url": "https://api.github.com/users/ProfHepta/following{/other_user}",
          "gists_url": "https://api.github.com/users/ProfHepta/gists{/gist_id}",
          "starred_url": "https://api.github.com/users/ProfHepta/starred{/owner}{/repo}",
          "subscriptions_url": "https://api.github.com/users/ProfHepta/subscriptions",
          "organizations_url": "https://api.github.com/users/ProfHepta/orgs",
          "repos_url": "https://api.github.com/users/ProfHepta/repos",
          "events_url": "https://api.github.com/users/ProfHepta/events{/privacy}",
          "received_events_url": "https://api.github.com/users/ProfHepta/received_events",
          "type": "User",
          "user_view_type": "public",
          "site_admin": false
        },
        "jobs_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/jobs",
        "logs_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/logs",
        "check_suite_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-suites/106706983717",
        "artifacts_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/artifacts",
        "cancel_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/cancel",
        "rerun_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/rerun",
        "previous_attempt_url": null,
        "workflow_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/workflows/385032350",
        "head_commit": {
          "id": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
          "tree_id": "8ffd22e7a20dea669c32ed675fafdc79751743ed",
          "message": "Archive phase3 donor and rejected EP3 native evidence",
          "timestamp": "2026-10-20T06:02:27Z",
          "author": {
            "name": "Tomasrgbsf",
            "email": "tomasbraynt@gmail.com"
          },
          "committer": {
            "name": "Tomasrgbsf",
            "email": "tomasbraynt@gmail.com"
          }
        },
        "repository": {
          "id": 1416401103,
          "node_id": "R_kgDOVGyQzw",
          "name": "RAZR-SLIDE",
          "full_name": "TrillionniumFoundation/RAZR-SLIDE",
          "private": true,
          "owner": {
            "login": "TrillionniumFoundation",
            "id": 262513357,
            "node_id": "O_kgDOD6WizQ",
            "avatar_url": "https://avatars.githubusercontent.com/u/262513357?v=4",
            "gravatar_id": "",
            "url": "https://api.github.com/users/TrillionniumFoundation",
            "html_url": "https://github.com/TrillionniumFoundation",
            "followers_url": "https://api.github.com/users/TrillionniumFoundation/followers",
            "following_url": "https://api.github.com/users/TrillionniumFoundation/following{/other_user}",
            "gists_url": "https://api.github.com/users/TrillionniumFoundation/gists{/gist_id}",
            "starred_url": "https://api.github.com/users/TrillionniumFoundation/starred{/owner}{/repo}",
            "subscriptions_url": "https://api.github.com/users/TrillionniumFoundation/subscriptions",
            "organizations_url": "https://api.github.com/users/TrillionniumFoundation/orgs",
            "repos_url": "https://api.github.com/users/TrillionniumFoundation/repos",
            "events_url": "https://api.github.com/users/TrillionniumFoundation/events{/privacy}",
            "received_events_url": "https://api.github.com/users/TrillionniumFoundation/received_events",
            "type": "Organization",
            "user_view_type": "public",
            "site_admin": false
          },
          "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE",
          "description": "RAZR SLIDE: equal-sized dual-compartment, single flexible OLED sliding-phone engineering research. Manufacturing NO-GO until physical qualification.",
          "fork": false,
          "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE",
          "forks_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/forks",
          "keys_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/keys{/key_id}",
          "collaborators_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/collaborators{/collaborator}",
          "teams_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/teams",
          "hooks_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/hooks",
          "issue_events_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/issues/events{/number}",
          "events_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/events",
          "assignees_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/assignees{/user}",
          "branches_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/branches{/branch}",
          "tags_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/tags",
          "blobs_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/git/blobs{/sha}",
          "git_tags_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/git/tags{/sha}",
          "git_refs_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/git/refs{/sha}",
          "trees_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/git/trees{/sha}",
          "statuses_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/statuses/{sha}",
          "languages_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/languages",
          "stargazers_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/stargazers",
          "contributors_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/contributors",
          "subscribers_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/subscribers",
          "subscription_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/subscription",
          "commits_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/commits{/sha}",
          "git_commits_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/git/commits{/sha}",
          "comments_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/comments{/number}",
          "issue_comment_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/issues/comments{/number}",
          "contents_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/contents/{+path}",
          "compare_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/compare/{base}...{head}",
          "merges_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/merges",
          "archive_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/{archive_format}{/ref}",
          "downloads_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/downloads",
          "issues_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/issues{/number}",
          "pulls_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/pulls{/number}",
          "milestones_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/milestones{/number}",
          "notifications_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/notifications{?since,all,participating}",
          "labels_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/labels{/name}",
          "releases_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/releases{/id}",
          "deployments_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/deployments"
        },
        "head_repository": {
          "id": 1416401103,
          "node_id": "R_kgDOVGyQzw",
          "name": "RAZR-SLIDE",
          "full_name": "TrillionniumFoundation/RAZR-SLIDE",
          "private": true,
          "owner": {
            "login": "TrillionniumFoundation",
            "id": 262513357,
            "node_id": "O_kgDOD6WizQ",
            "avatar_url": "https://avatars.githubusercontent.com/u/262513357?v=4",
            "gravatar_id": "",
            "url": "https://api.github.com/users/TrillionniumFoundation",
            "html_url": "https://github.com/TrillionniumFoundation",
            "followers_url": "https://api.github.com/users/TrillionniumFoundation/followers",
            "following_url": "https://api.github.com/users/TrillionniumFoundation/following{/other_user}",
            "gists_url": "https://api.github.com/users/TrillionniumFoundation/gists{/gist_id}",
            "starred_url": "https://api.github.com/users/TrillionniumFoundation/starred{/owner}{/repo}",
            "subscriptions_url": "https://api.github.com/users/TrillionniumFoundation/subscriptions",
            "organizations_url": "https://api.github.com/users/TrillionniumFoundation/orgs",
            "repos_url": "https://api.github.com/users/TrillionniumFoundation/repos",
            "events_url": "https://api.github.com/users/TrillionniumFoundation/events{/privacy}",
            "received_events_url": "https://api.github.com/users/TrillionniumFoundation/received_events",
            "type": "Organization",
            "user_view_type": "public",
            "site_admin": false
          },
          "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE",
          "description": "RAZR SLIDE: equal-sized dual-compartment, single flexible OLED sliding-phone engineering research. Manufacturing NO-GO until physical qualification.",
          "fork": false,
          "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE",
          "forks_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/forks",
          "keys_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/keys{/key_id}",
          "collaborators_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/collaborators{/collaborator}",
          "teams_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/teams",
          "hooks_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/hooks",
          "issue_events_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/issues/events{/number}",
          "events_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/events",
          "assignees_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/assignees{/user}",
          "branches_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/branches{/branch}",
          "tags_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/tags",
          "blobs_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/git/blobs{/sha}",
          "git_tags_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/git/tags{/sha}",
          "git_refs_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/git/refs{/sha}",
          "trees_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/git/trees{/sha}",
          "statuses_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/statuses/{sha}",
          "languages_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/languages",
          "stargazers_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/stargazers",
          "contributors_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/contributors",
          "subscribers_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/subscribers",
          "subscription_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/subscription",
          "commits_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/commits{/sha}",
          "git_commits_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/git/commits{/sha}",
          "comments_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/comments{/number}",
          "issue_comment_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/issues/comments{/number}",
          "contents_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/contents/{+path}",
          "compare_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/compare/{base}...{head}",
          "merges_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/merges",
          "archive_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/{archive_format}{/ref}",
          "downloads_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/downloads",
          "issues_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/issues{/number}",
          "pulls_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/pulls{/number}",
          "milestones_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/milestones{/number}",
          "notifications_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/notifications{?since,all,participating}",
          "labels_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/labels{/name}",
          "releases_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/releases{/id}",
          "deployments_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/deployments"
        }
      }
    },
    {
      "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/attempts/1/jobs?per_page=100&page=1",
      "status": 200,
      "data": {
        "total_count": 11,
        "jobs": [
          {
            "id": 118480847195,
            "run_id": 39378151409,
            "workflow_name": "Research validation",
            "head_branch": "work/product-integration-20261018",
            "run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409",
            "run_attempt": 1,
            "node_id": "CR_kwDOVGyQz88AAAAblgJBWw",
            "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
            "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/jobs/118480847195",
            "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847195",
            "status": "completed",
            "conclusion": "failure",
            "created_at": "2026-10-20T06:02:46Z",
            "started_at": "2026-10-20T06:02:46Z",
            "completed_at": "2026-10-20T06:03:32Z",
            "name": "full-unit-suites",
            "steps": [],
            "check_run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847195",
            "labels": [
              "ubuntu-24.04"
            ],
            "runner_id": 0,
            "runner_name": "",
            "runner_group_id": 0,
            "runner_group_name": ""
          },
          {
            "id": 118480847357,
            "run_id": 39378151409,
            "workflow_name": "Research validation",
            "head_branch": "work/product-integration-20261018",
            "run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409",
            "run_attempt": 1,
            "node_id": "CR_kwDOVGyQz88AAAAblgJB_Q",
            "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
            "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/jobs/118480847357",
            "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847357",
            "status": "queued",
            "conclusion": null,
            "created_at": "2026-10-20T06:02:46Z",
            "started_at": "2026-10-20T06:02:46Z",
            "completed_at": null,
            "name": "native-lateral-guide",
            "steps": [],
            "check_run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847357",
            "labels": [
              "ubuntu-24.04"
            ],
            "runner_id": 0,
            "runner_name": "",
            "runner_group_id": 0,
            "runner_group_name": ""
          },
          {
            "id": 118480847370,
            "run_id": 39378151409,
            "workflow_name": "Research validation",
            "head_branch": "work/product-integration-20261018",
            "run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409",
            "run_attempt": 1,
            "node_id": "CR_kwDOVGyQz88AAAAblgJCCg",
            "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
            "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/jobs/118480847370",
            "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847370",
            "status": "queued",
            "conclusion": null,
            "created_at": "2026-10-20T06:02:46Z",
            "started_at": "2026-10-20T06:02:46Z",
            "completed_at": null,
            "name": "native-serviceable",
            "steps": [],
            "check_run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847370",
            "labels": [
              "ubuntu-24.04"
            ],
            "runner_id": null,
            "runner_name": null,
            "runner_group_id": null,
            "runner_group_name": null
          },
          {
            "id": 118480847386,
            "run_id": 39378151409,
            "workflow_name": "Research validation",
            "head_branch": "work/product-integration-20261018",
            "run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409",
            "run_attempt": 1,
            "node_id": "CR_kwDOVGyQz88AAAAblgJCGg",
            "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
            "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/jobs/118480847386",
            "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847386",
            "status": "completed",
            "conclusion": "failure",
            "created_at": "2026-10-20T06:02:46Z",
            "started_at": "2026-10-20T06:02:46Z",
            "completed_at": "2026-10-20T06:02:50Z",
            "name": "native-phone-layout",
            "steps": [],
            "check_run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847386",
            "labels": [
              "ubuntu-24.04"
            ],
            "runner_id": 0,
            "runner_name": "",
            "runner_group_id": 0,
            "runner_group_name": ""
          },
          {
            "id": 118480847388,
            "run_id": 39378151409,
            "workflow_name": "Research validation",
            "head_branch": "work/product-integration-20261018",
            "run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409",
            "run_attempt": 1,
            "node_id": "CR_kwDOVGyQz88AAAAblgJCHA",
            "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
            "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/jobs/118480847388",
            "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847388",
            "status": "queued",
            "conclusion": null,
            "created_at": "2026-10-20T06:02:46Z",
            "started_at": "2026-10-20T06:02:46Z",
            "completed_at": null,
            "name": "native-catalogue-joint",
            "steps": [],
            "check_run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847388",
            "labels": [
              "ubuntu-24.04"
            ],
            "runner_id": null,
            "runner_name": null,
            "runner_group_id": null,
            "runner_group_name": null
          },
          {
            "id": 118480847419,
            "run_id": 39378151409,
            "workflow_name": "Research validation",
            "head_branch": "work/product-integration-20261018",
            "run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409",
            "run_attempt": 1,
            "node_id": "CR_kwDOVGyQz88AAAAblgJCOw",
            "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
            "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/jobs/118480847419",
            "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847419",
            "status": "queued",
            "conclusion": null,
            "created_at": "2026-10-20T06:02:46Z",
            "started_at": "2026-10-20T06:02:46Z",
            "completed_at": null,
            "name": "native-coupling",
            "steps": [],
            "check_run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847419",
            "labels": [
              "ubuntu-24.04"
            ],
            "runner_id": 0,
            "runner_name": "",
            "runner_group_id": 0,
            "runner_group_name": ""
          },
          {
            "id": 118480847472,
            "run_id": 39378151409,
            "workflow_name": "Research validation",
            "head_branch": "work/product-integration-20261018",
            "run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409",
            "run_attempt": 1,
            "node_id": "CR_kwDOVGyQz88AAAAblgJCcA",
            "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
            "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/jobs/118480847472",
            "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847472",
            "status": "queued",
            "conclusion": null,
            "created_at": "2026-10-20T06:02:46Z",
            "started_at": "2026-10-20T06:02:46Z",
            "completed_at": null,
            "name": "native-endpoint-joint",
            "steps": [],
            "check_run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847472",
            "labels": [
              "ubuntu-24.04"
            ],
            "runner_id": null,
            "runner_name": null,
            "runner_group_id": null,
            "runner_group_name": null
          },
          {
            "id": 118480847512,
            "run_id": 39378151409,
            "workflow_name": "Research validation",
            "head_branch": "work/product-integration-20261018",
            "run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409",
            "run_attempt": 1,
            "node_id": "CR_kwDOVGyQz88AAAAblgJCmA",
            "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
            "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/jobs/118480847512",
            "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847512",
            "status": "queued",
            "conclusion": null,
            "created_at": "2026-10-20T06:02:46Z",
            "started_at": "2026-10-20T06:02:46Z",
            "completed_at": null,
            "name": "native-pawl",
            "steps": [],
            "check_run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847512",
            "labels": [
              "ubuntu-24.04"
            ],
            "runner_id": null,
            "runner_name": null,
            "runner_group_id": null,
            "runner_group_name": null
          },
          {
            "id": 118480847516,
            "run_id": 39378151409,
            "workflow_name": "Research validation",
            "head_branch": "work/product-integration-20261018",
            "run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409",
            "run_attempt": 1,
            "node_id": "CR_kwDOVGyQz88AAAAblgJCnA",
            "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
            "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/jobs/118480847516",
            "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847516",
            "status": "queued",
            "conclusion": null,
            "created_at": "2026-10-20T06:02:46Z",
            "started_at": "2026-10-20T06:02:46Z",
            "completed_at": null,
            "name": "native-thin",
            "steps": [],
            "check_run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847516",
            "labels": [
              "ubuntu-24.04"
            ],
            "runner_id": 0,
            "runner_name": "",
            "runner_group_id": 0,
            "runner_group_name": ""
          },
          {
            "id": 118480847556,
            "run_id": 39378151409,
            "workflow_name": "Research validation",
            "head_branch": "work/product-integration-20261018",
            "run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409",
            "run_attempt": 1,
            "node_id": "CR_kwDOVGyQz88AAAAblgJCxA",
            "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
            "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/jobs/118480847556",
            "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847556",
            "status": "queued",
            "conclusion": null,
            "created_at": "2026-10-20T06:02:46Z",
            "started_at": "2026-10-20T06:02:46Z",
            "completed_at": null,
            "name": "native-mounted",
            "steps": [],
            "check_run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847556",
            "labels": [
              "ubuntu-24.04"
            ],
            "runner_id": 0,
            "runner_name": "",
            "runner_group_id": 0,
            "runner_group_name": ""
          },
          {
            "id": 118480847565,
            "run_id": 39378151409,
            "workflow_name": "Research validation",
            "head_branch": "work/product-integration-20261018",
            "run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409",
            "run_attempt": 1,
            "node_id": "CR_kwDOVGyQz88AAAAblgJCzQ",
            "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
            "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/actions/jobs/118480847565",
            "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847565",
            "status": "queued",
            "conclusion": null,
            "created_at": "2026-10-20T06:02:46Z",
            "started_at": "2026-10-20T06:02:46Z",
            "completed_at": null,
            "name": "native-root-clearance",
            "steps": [],
            "check_run_url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847565",
            "labels": [
              "ubuntu-24.04"
            ],
            "runner_id": null,
            "runner_name": null,
            "runner_group_id": null,
            "runner_group_name": null
          }
        ]
      }
    },
    {
      "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847195/annotations?per_page=100&page=1",
      "status": 200,
      "data": [
        {
          "path": ".github",
          "blob_href": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5ef7c25aafd812909101b3d7d80081ba05/.github",
          "start_line": 1,
          "start_column": null,
          "end_line": 1,
          "end_column": null,
          "annotation_level": "failure",
          "title": "",
          "message": "The job was not started because recent account payments have failed or your spending limit needs to be increased. Please check the 'Billing & plans' section in your settings",
          "raw_details": ""
        }
      ]
    },
    {
      "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847357/annotations?per_page=100&page=1",
      "status": 200,
      "data": []
    },
    {
      "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847370/annotations?per_page=100&page=1",
      "status": 200,
      "data": []
    },
    {
      "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847386/annotations?per_page=100&page=1",
      "status": 200,
      "data": [
        {
          "path": ".github",
          "blob_href": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5ef7c25aafd812909101b3d7d80081ba05/.github",
          "start_line": 1,
          "start_column": null,
          "end_line": 1,
          "end_column": null,
          "annotation_level": "failure",
          "title": "",
          "message": "The job was not started because recent account payments have failed or your spending limit needs to be increased. Please check the 'Billing & plans' section in your settings",
          "raw_details": ""
        }
      ]
    },
    {
      "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847388/annotations?per_page=100&page=1",
      "status": 200,
      "data": []
    },
    {
      "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847419/annotations?per_page=100&page=1",
      "status": 200,
      "data": []
    },
    {
      "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847472/annotations?per_page=100&page=1",
      "status": 200,
      "data": []
    },
    {
      "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847512/annotations?per_page=100&page=1",
      "status": 200,
      "data": []
    },
    {
      "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847516/annotations?per_page=100&page=1",
      "status": 200,
      "data": []
    },
    {
      "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847556/annotations?per_page=100&page=1",
      "status": 200,
      "data": []
    },
    {
      "url": "https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/118480847565/annotations?per_page=100&page=1",
      "status": 200,
      "data": []
    }
  ],
  "summary": {
    "expected_head": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
    "run_id": 39378151409,
    "run_attempt": 1,
    "actual_run_head": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
    "head_identity_matches": true,
    "run_status": "queued",
    "run_conclusion": null,
    "jobs": [
      {
        "id": 118480847195,
        "name": "full-unit-suites",
        "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
        "run_attempt": 1,
        "status": "completed",
        "conclusion": "failure",
        "runner_id": 0,
        "step_records": 0,
        "executed_step_records": 0,
        "inherited_completion_precedes_attempt_creation": false,
        "billing_or_spend_block_annotation": true,
        "annotation_count": 1,
        "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847195"
      },
      {
        "id": 118480847357,
        "name": "native-lateral-guide",
        "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
        "run_attempt": 1,
        "status": "queued",
        "conclusion": null,
        "runner_id": 0,
        "step_records": 0,
        "executed_step_records": 0,
        "inherited_completion_precedes_attempt_creation": false,
        "billing_or_spend_block_annotation": false,
        "annotation_count": 0,
        "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847357"
      },
      {
        "id": 118480847370,
        "name": "native-serviceable",
        "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
        "run_attempt": 1,
        "status": "queued",
        "conclusion": null,
        "runner_id": null,
        "step_records": 0,
        "executed_step_records": 0,
        "inherited_completion_precedes_attempt_creation": false,
        "billing_or_spend_block_annotation": false,
        "annotation_count": 0,
        "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847370"
      },
      {
        "id": 118480847386,
        "name": "native-phone-layout",
        "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
        "run_attempt": 1,
        "status": "completed",
        "conclusion": "failure",
        "runner_id": 0,
        "step_records": 0,
        "executed_step_records": 0,
        "inherited_completion_precedes_attempt_creation": false,
        "billing_or_spend_block_annotation": true,
        "annotation_count": 1,
        "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847386"
      },
      {
        "id": 118480847388,
        "name": "native-catalogue-joint",
        "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
        "run_attempt": 1,
        "status": "queued",
        "conclusion": null,
        "runner_id": null,
        "step_records": 0,
        "executed_step_records": 0,
        "inherited_completion_precedes_attempt_creation": false,
        "billing_or_spend_block_annotation": false,
        "annotation_count": 0,
        "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847388"
      },
      {
        "id": 118480847419,
        "name": "native-coupling",
        "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
        "run_attempt": 1,
        "status": "queued",
        "conclusion": null,
        "runner_id": 0,
        "step_records": 0,
        "executed_step_records": 0,
        "inherited_completion_precedes_attempt_creation": false,
        "billing_or_spend_block_annotation": false,
        "annotation_count": 0,
        "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847419"
      },
      {
        "id": 118480847472,
        "name": "native-endpoint-joint",
        "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
        "run_attempt": 1,
        "status": "queued",
        "conclusion": null,
        "runner_id": null,
        "step_records": 0,
        "executed_step_records": 0,
        "inherited_completion_precedes_attempt_creation": false,
        "billing_or_spend_block_annotation": false,
        "annotation_count": 0,
        "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847472"
      },
      {
        "id": 118480847512,
        "name": "native-pawl",
        "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
        "run_attempt": 1,
        "status": "queued",
        "conclusion": null,
        "runner_id": null,
        "step_records": 0,
        "executed_step_records": 0,
        "inherited_completion_precedes_attempt_creation": false,
        "billing_or_spend_block_annotation": false,
        "annotation_count": 0,
        "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847512"
      },
      {
        "id": 118480847516,
        "name": "native-thin",
        "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
        "run_attempt": 1,
        "status": "queued",
        "conclusion": null,
        "runner_id": 0,
        "step_records": 0,
        "executed_step_records": 0,
        "inherited_completion_precedes_attempt_creation": false,
        "billing_or_spend_block_annotation": false,
        "annotation_count": 0,
        "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847516"
      },
      {
        "id": 118480847556,
        "name": "native-mounted",
        "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
        "run_attempt": 1,
        "status": "queued",
        "conclusion": null,
        "runner_id": 0,
        "step_records": 0,
        "executed_step_records": 0,
        "inherited_completion_precedes_attempt_creation": false,
        "billing_or_spend_block_annotation": false,
        "annotation_count": 0,
        "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847556"
      },
      {
        "id": 118480847565,
        "name": "native-root-clearance",
        "head_sha": "90b09f5ef7c25aafd812909101b3d7d80081ba05",
        "run_attempt": 1,
        "status": "queued",
        "conclusion": null,
        "runner_id": null,
        "step_records": 0,
        "executed_step_records": 0,
        "inherited_completion_precedes_attempt_creation": false,
        "billing_or_spend_block_annotation": false,
        "annotation_count": 0,
        "html_url": "https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409/job/118480847565"
      }
    ],
    "jobs_without_executed_steps": [
      118480847195,
      118480847357,
      118480847370,
      118480847386,
      118480847388,
      118480847419,
      118480847472,
      118480847512,
      118480847516,
      118480847556,
      118480847565
    ],
    "billing_block_job_ids": [
      118480847195,
      118480847386
    ],
    "inherited_job_result_ids": [],
    "all_jobs_have_executed_steps": false,
    "successful_hosted_report": false,
    "one_fresh_attempt_executed_all_jobs": false,
    "scope": "provider execution records; no test-count or hardware result inferred"
  },
  "completed_utc": "2026-10-20T06:05:08.431968+00:00"
}
```

</details>
