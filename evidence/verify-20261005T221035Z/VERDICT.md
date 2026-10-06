# ACCEPT — exact clean Stage1 product and audit

Accepted product: `a8805bf4dc2297e0953ea4a5979fcd85c98b95b4`.
Frozen audit: `52b50da43a750452ed44fb9ab118c9576428a475`.
Organizer: `803560d2a678ace1414465c098eb0ab5380ffade`.

All applicable published Stage1 tests, all frozen independent tests, all85 normative rows and I-01..I-12 passed fresh for this exact pair. No known required gap remains. This acceptance does not apply to any changed product or audit revision.

| Gate | Actual fresh evidence |
|---|---|
| Exact checkout/build/source | Both repositories freshly cloned at full SHAs, clean tracked trees, genuine independent authors/history; no nested/link/untracked dependency. Dockerfile built without setup/Compose/host product execution. Current source locks/hash/current-generation/typed replay/monetary/import paths inspected. |
| Complete published Stage1 |147collected/147passed;0failed/errors/skipped/deselected/xfails;45.28s pytest time. |
| Complete frozen independent suite |32methods/198subtests pass;0failures/errors/skips;6051HTTPcalls;58.517178s; longest request1.290244s. |
| Original malformed resets and boundaries | All6original cases400 atomic unchanged with credentials/tokens/records/all5retries/login retained;52extended malformed/missing/range probes +6valid decimal/exponent currency fixtures pass. |
| Original50reset deadlines |100/100204 across both origins; longest6.635834/6.617504s, within10s. |
| Original spaced generation/auth deadline | Both origins25/25logins200 +25/25unchangedimports204; exactly50calls/max26inflight each. Longest login0.746269/0.749048s, within5s. Original recipe/input/timing retained, only endpoint/attempt changed. |
| Expanded resource/auth/mixed loads | Eight50-call batches/400calls pass across both origins:50imports,50auth,40reset+10health-read,25reset+25login-signup.45reset+5health regression passes; healthmax0.004771s. Separate per-path5/10s budgets enforced. |
| Credential/gate/fence correctness | Queued changed-password49-overlap and reused-ID/hash25import+25login scenarios pass, positive and negative/current credentials/restored tokens checked. Seven exact-image private-instance checks pass, including error/interruption/missing-user release, post-admission capture and2counted recapture branches. No live/source/assertion modifications. |
| Monetary/control/recovery |50mixedmoney/control/write/export jobs,11coherent restored snapshots;12source-justified invalid opaque states422 unchanged, all5original retries/login recover. Complete frozen permission/feed/terminal/zero-share/net-settlement/race/exactness checks pass. |
| Removed-source portability | Actual source container removed and absence confirmed before unchanged import into third fresh19080 process.7accounts/hash login/tokens/IDs/timestamps/all5original receipts/retries/operator rights/failed-key reuse retained; destination credentials removed, repeat import restores state.45calls,max0.252453s. |
| Runtime isolation/resources/start | Single product process/container, no product mounts/shared store/outbound route; actual Internal network;2CPU/2GiB/swap caps, noOOM/restarts. Default8080/alternate18080 ready0.590353/0.559161s; third19080 health0.502067s.0.0.0.0 wildcard listener/PORT behavior verified. |
| Stage2 overshoot |35collected,first missing-login-UI failure after Chromium launched;11.10s. This is the expected higher-stage probe, separate from required Stage1. |

The corrected implementation admits a login KDF first, captures current generation/email/ID/hash briefly under the live lock, hashes outside it with that single admitted slot, then releases the slot before final live publication/fence. The helper does not recursively admit. The final generation/current-credential check still protects success and wrong-password failure; true changes recapture without caps/stale fallback/new errors. Password hashing strength, imported sessions, atomic full replacement, monetary/read/retry/export boundaries and original400/422 distinctions remain intact. `SOURCE-INSPECTION.md` records exact current function/line reasoning.

Evidence in this new attempt:

- `VERDICT.json`: full safe machine report, exact pair, actual counts/timings/limits/maxima and limitations.
- `ledger-reconciliation.json`: all85 stable normative rows PASS with test/inspection evidence links.
- `INSPECTION-RESULTS.md` and `SOURCE-INSPECTION.md`: all12 required inspections PASS and source rationale.
- `official-stage1.counts.json`, `independent-summary.json`, all supplemental `*-summary.json`, paired per-command JSON/log files: original actual outputs/counts/exits/timeouts/timings.
- `identity.json`, `services.json`, `third-service.json`, `runner-current.json`, startup/third command reports: actual full image/container/network identities and lifecycle.

Product image: `sha256:b23fd70d677488020ab3634d8090a425a973cdd4e1ac5ee2df70297b57571218`.
Prepared runner: `sha256:022bfa4b97f6bfee83dfd8628e957dbca5ab65ab6768ad62bc3820138c287902`, current identity re-resolved and retained under `starforge-clean-stage1-runner-verifier:20261005t221035`.
Main network: `4b8457be768e59c8a87a73ea180721be16a4c32599e0f9e85194e61e44ad29fb`.
Initial source: `242e9feca8dd67e7b8f5b9e5df87a7faf94ae6ebdf481829cd3b6207794a0dd4`.
Peer: `76f19cd60fc0759f6cd365c28e9aa5a326679a3d19a92c6be309277fcc1a3372`.
Third process: `23633a5bc870d7638448b6bebb8fd30ef9cdc2039402c9e883bb34a51ed70b74`.
Runner container: `91b94124d50bc7e7a1df641c066ea2c88d8ea2fefb2f9df0af9133c84f239841`.

Attempt started2026-10-05 22:10:35UTC. Runtime/portability checks completed22:26:05UTC; owned cleanup completed22:32:36UTC (22m01s from start). Final evidence reconciliation/acceptance completed22:37:06UTC (26m31s from start). All bounded commands began with actual-clock timeout/cleanup reserve before the2026-10-06 04:30UTC cutoff. No required work remains for this exact acceptance. Report-writing time is included honestly; no old counts substituted.

Owned source/peer/third/runner containers and unique network are removed; prepared runner references remain alive. No unrelated/parallel earlier-run resource read/stopped/pruned. Raw exports/context remain private600 under700 directory and were never posted to the room. Three genuine failed product revisions/reports (`28b55ab6`, `0655f50e`, `4edb95b4`) stay preserved in their separate attempts; fixes use genuine new commits, no amend/rebase/squash or manufactured failures. The frozen audit did not change.

Limits of this evidence: the participant package publishes only part of judging tests; every available applicable case plus required normative independent/source/runtime obligations was executed. Official tests/plugins/fixtures are unchanged, using official harness.plugin/count pytest semantics inside the named isolated prepared runner; lifecycle is separately recorded to preserve actual immutable IDs and avoid shared mutable setup tags. Docker internal mode suppresses host port exposure, so HTTP checks used isolated container origins as the pinned harness specifies. Stage1 requires no previous-stage upgrade/browser UI; its mandatory §10 state portability was executed fully. Private source-aware fault checks affected only test instances inside the exact image, never shipped files or live server. Live recapture counters are not exported; source and2counted private branches inspected. Bounded runtime/source acceptance does not claim arbitrary sustained throughput, peak-memory/infinite-fault/indefinite-aging proof or future-revision acceptance.

Observed runtime/model: Codex/gpt-6.1-sol, high effort per owner briefing. Independent token usage and billing unavailable/unknown, not zero. Coordinator owns the overall Stage1 outcome and operator submission workflow.
