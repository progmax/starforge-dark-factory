# REJECT — repaired exact Stage1 revision

Product: `0655f50e9d66b5a5679ec98e6ef3b3977ed5220a`.
Frozen audit: `52b50da43a750452ed44fb9ab118c9576428a475`.
Pinned organizer: `803560d2a678ace1414465c098eb0ab5380ffade`.

The original reset type defect is repaired, but §2/§10 request deadlines fail under permitted concurrent control load.50 valid simultaneous six-user resets at2CPU/2GiB yielded12 timeouts on origin8080 and11 on a second independent origin18080, each at the10s budget. A subsequent45-reset/5-health workload at maximum50workers timed out7 reset calls and all5 health calls at their5s budget. All three probes exited1; full per-call failures remain preserved.

Source: server.py:68 holds Service.lock while domain.py:686 route calls build_fixture:166; password_hash:130 runs six sequential scrypt derivations per reset while readers and all other routes wait. Completion times progress about0.25–0.26s per reset. Two-origin reproduction plus no OOM/restarts supports a product serialization bottleneck. Builder owns repair; no product, frozen audit or organizer assertion was changed by Verifier.

| Gate | Fresh exact-revision result |
|---|---|
| Clean checkout/build | Exact product and audit cloned anew, clean trees, genuine parent/author/committer, no untracked delivery dependencies/links/submodules/nested repos; build exit0 |
| Published required Stage1 |147/147 passed; zero failures/errors/skips/deselection/xfails;45.19s pytest time |
| All frozen independent tests |32 methods /198 subtests passed;6051 HTTP calls;56.897188s; max frozen-suite request2.515396s |
| Original six malformed resets | All400 malformed_request, full state unchanged; original tokens/login and all5 path retries retained after each |
| Extended repaired-reset regression |52 malformed/missing/range cases plus6 valid decimal/exponent currency fixtures passed;288 calls |
| Mixed money/control concurrency |50 calls,11 coherent snapshots importable with conserved balances/no duplicate request payment |
| Invalid opaque-state recovery |12 source-justified cases422 unchanged, all5 original responses and login retained, valid import restores state |
| Removed-source portability | Source actually removed; third process preserves7 accounts, tokens/IDs/timestamps/all5 original retry responses/operator rights/failed-key reuse;45 calls |
| Delivery/isolation/startup | Default8080/alternate18080 reset-ready0.604434/0.564776s; third19080 health0.528188s; unique internal network/no default route/no product mounts;2CPU/2GiB enforced |
| Required deadline/load gate | REJECT:50-reset deadlines fail on both origins;45reset+5health workload also fails ordinary5s deadline |
| Higher-stage overshoot |35 Stage2 cases collected; first missing-login-UI failure after Chromium launch;11.06s; expected probe failure, separate from Stage1 |

Full safe report: `VERDICT.json`. All85 normative rows: `ledger-reconciliation.json` (S2-04 and S10-08 rejected). All12 inspections: `INSPECTION-RESULTS.md` (I-05 rejected). Defect/reproduction: `DEFECTS.md`, `control-load.py`, `control-load-repeat.py`, `mixed-control-health.py` and their JSON/logs. Other reports: `official-stage1.counts.json`, `independent-summary.json`, `residual-summary.json`, `reset-regression-summary.json`, `source-removal-portability-summary.json`.

Product image: `sha256:074d62141bb5ec740d9b3ebbce22e52afe531ae60f3a02bd491b8931eb403a15`.
Current prepared runner: `sha256:022bfa4b97f6bfee83dfd8628e957dbca5ab65ab6768ad62bc3820138c287902`, re-resolved for this attempt and retained under `starforge-clean-stage1-runner-verifier:20261005t211747`.
Container/network identities and lifecycle: `services.json`, `third-service.json`, `runner-current.json`, `startup-commands.json`, `third-commands.json`, paired command JSON/log files. No OOM/restart observed; a post-repeat544.7MiB observation is not a peak-capacity claim.

Attempt began2026-10-05 21:17:47UTC; complete handoff recovered21:23:48UTC; build resumed21:23:49UTC; owned-resource cleanup finished21:34:39UTC. Approximately16m52s total, including6m01s of handoff recovery/preparation;10m50s from fresh build to cleanup. All execution began before the supplied04:30UTC cutoff with timeout/cleanup reserve checked. No human request or permission/model/security change occurred.

Raw exports/context stay private local600 files under700 directory; reports contain no credential values. Source/peer/third containers, named runner and unique network are removed; current prepared runner reference remains alive. Original rejected commit and its evidence under `checks/verify-20261005T210331Z` remain unchanged. No earlier parallel-run artifacts/resources were read or modified.

All applicable published tests ran unchanged using pinned harness.plugin/summary pytest semantics in the prepared named isolated runner. Container lifecycle is recorded separately to avoid shared mutable setup tags and preserve actual IDs. On this platform Docker internal mode does not expose host mappings, so HTTP acceptance uses isolated origins as the pinned harness describes. Private judging suites are unavailable in the participant package; every available required case plus normative residual checks was executed. Stage1 has no earlier-stage upgrade or browser UI obligation; its required import portability was executed fully. No arbitrary throughput, peak-memory or indefinite token-aging claim is made.

Observed model/runtime: Codex/gpt-6.1-sol per runtime briefing, high effort. Independent billing and token usage unknown, not zero. No accepted pair exists. A further revision needs a fresh complete attempt and verdict.
