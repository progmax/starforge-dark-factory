# REJECT — exact FIFO/generation repair revision

Product `4edb95b405225ab9f76b945ae06b1a341dd50b0f`.
Frozen audit `52b50da43a750452ed44fb9ab118c9576428a475`.
Organizer `803560d2a678ace1414465c098eb0ab5380ffade`.

The original reset type and bulk-reset/health contention defects now pass. A remaining §2/I-05 ordinary5s deadline defect reproduces under bounded repeated imports:25 valid logins plus25 unchanged imports spaced0.19s, exactly50 workload calls and at most26 in flight. On both independent B18080 and C19080 instances,23 logins timeout at5s,2 return200, and all25 imports return204. Both commands exit1. No credential values change across these imports; every login password is valid throughout.

Source diagnosis: credentials/generation are captured before FIFO hash admission, so queued attempts age before hashing. Current generation comparison restarts obsolete prepared work in the uncapped server loop; FIFO access alone does not bound total recapture time. Detailed original reproduction, source pointers and per-call reports are in `DEFECTS.md` and both `staggered-generation*-summary.json`/logs. No source/audit/organizer/assertion edits occurred. Builder owns correction.

| Fresh gate | Actual result |
|---|---|
| Exact clean checkout/build/delivery | PASS; both exact clones, genuine parent0655f50/author, scoped3file diff, no nested/link/untracked dependency, build exit0 |
| Full published Stage1 |147/147 passed, zero skipped/deselected/errors/xfails;45.35s pytest time |
| All frozen independent methods |32methods/198subtests passed;6051HTTPcalls;58.918810s; max1.250428s |
| Original6 + expanded52 +6 integral reset probes | PASS; atomic400 wrong types and retained422/numeric semantics, all5 retries/login unchanged |
| Both50 six-user reset loads | PASS;100/100204,max6.707893/6.602537s under10s |
|45reset+5health original failure regression | PASS; healthmax0.004561s, all control deadlines met |
| Eight expanded50-call batches across both origins | PASS;400calls covering imports/logins/40reset+10health-read/25reset+25login-signup; per-path deadlines preserved |
| Queued password changes/reused-ID burst import churn | PASS;49-overlap queued scenario and50-call burst current credentials/restored sessions |
| Source-aware gate/fence private instances | PASS; four exception/interruption/ABA/stale-wrong-password checks;2 counted recapture branches inside exact image |
| Mixed money/control and invalid-state recovery | PASS;50calls/11coherent snapshots,12 invalid states422 unchanged and all5 retries/login recover |
| Actual removed-source third-process import | PASS;7accounts/all5original retry responses/hash login/tokens/IDs/timestamps/operators/failed keys preserved;45calls |
| Required spaced generation churn | REJECT;23/25logins timeout on each of two origins under5s requirement |
| Higher-stage overshoot |35collected,one expected missing-login-UI failure with Chromium launched;11.07s, separate from Stage1 |

Safe machine report `VERDICT.json`; all85 normative rows `ledger-reconciliation.json` (S2-04 rejected); all12 inspections `INSPECTION-RESULTS.md` (I-05 rejected). Full commands/exits/timeouts/timings/logs and IDs are in paired command files, `identity.json`, `services.json`, `third-service.json`, `runner-current.json`, `startup-commands.json`, `third-commands.json`. Source-aware private-instance checks import the shipped class inside the exact image; synthetic fault injection affects only those private objects, not shipped source or the live HTTP server. Live recapture counters are not exported; source was inspected and private branch recaptures counted.

Product image `sha256:cf392094e37fd1c3a079e74cdead45fa407b799216804f819afb894d652689a5`.
Prepared runner current identity `sha256:022bfa4b97f6bfee83dfd8628e957dbca5ab65ab6768ad62bc3820138c287902`, retained under `starforge-clean-stage1-runner-verifier:20261005t214606`.
All service instances enforced2CPU/2GiB/no product mounts/internal no-default-route networking. Default/alternate startup ready0.591162/0.559985s; third19080 health0.484256s. Final inspections show noOOM/restarts. Post-load632.2/548.6MiB observations are not peak-memory/long-term claims.

Attempt2026-10-05 21:46:06–22:05:22UTC,19m16s through owned cleanup; every execution clock/cutoff reserve checked before04:30UTC. Source removed during portability; remaining owned B/C/runner/network removed at completion. Prepared runner references retained; no other attempt resource read/stopped/pruned. Raw exports/context remain private600 under700 directory, never in room summaries. Both earlier genuine REJECTs and counts remain unchanged, with no count relabeling.

All available published tests/plugins/fixtures ran unchanged in the named prepared isolated runner using official harness.plugin/count semantics, with lifecycle independently recorded to preserve immutable IDs and avoid shared mutable setup tags. Private judging suites are not in the participant package. Docker internal mode suppresses host port exposure, so HTTP checks use isolated origins per pinned harness; no outbound fallback. Stage1 has no earlier-stage upgrade/browser UI obligation; required import portability was fully exercised. No arbitrary throughput, peak-memory, indefinite-aging or future-revision acceptance claim is made.

Observed Codex/gpt-6.1-sol high effort per runtime briefing. Token usage/billing unavailable and unknown, not zero. No accepted pair. A changed revision needs a fresh complete attempt.
