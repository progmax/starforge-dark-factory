# REJECT — clean Stage1 initial product revision

Exact product: `28b55ab6b17fb94a7d02f36b66e4d81b80339cc0`.
Exact frozen audit: `52b50da43a750452ed44fb9ab118c9576428a475`.
Pinned organizer: `803560d2a678ace1414465c098eb0ab5380ffade`.

Acceptance attempt began2026-10-05 21:03:31UTC; owned-resource cleanup completed21:16:07UTC, approximately12minutes36seconds elapsed. No accepted product/audit pair exists from this attempt.

Required defect: §5 wrong JSON field types must produce400 `malformed_request`. An otherwise valid reset with `payments:{}` or `requests:{}` returns204 and replaces destination state. Wrong-type `minor_units` and user `balance` return422 instead of400. See `DEFECTS.md`, `residual.py:fixture_types`, `residual-summary.json` and original `residual.log`. Product source root cause: `domain.py:159,171,178,188`. The Builder owns the repair. Auditor owns any independently justified audit amendment; no assertion has been amended here.

| Gate | Actual result |
|---|---|
| Exact clean clone/build | PASS; independent identity/tree checks, no nested repos/symlinks/submodules, build exit0 |
| Complete published Stage1 |147 collected and147 passed,0 failures/errors/skips/deselection/xfails;45.54s pytest time |
| All frozen independent methods |32 methods,198 subtests passed;6051 HTTP calls;57.966590s suite time; longest request2.571205s |
| Stage2 overshoot |35 collected, stopped at first missing-login-UI failure; Chromium launched;11.24s; expected higher-stage result, separate from required Stage1 |
| Offline/resource/startup | Unique internal network/no default route/no product mounts;2CPU/2GiB; default8080 and alternate18080 health+reset in0.537/0.475s; third19080 health in0.495s; no OOM/restarts observed |
| Supplemental mixed races |50 simultaneous money/control/export jobs;11 coherent snapshots restored and checked |
| Source-aware invalid-state recovery |12 invalid states rejected422 with entire destination export unchanged; all5 original retries/login preserved and valid import recovered each time |
| Source removal portability | Source container removed before third-process import;7 accounts,5 original path responses, tokens/IDs/timestamps/operator rights/failed-key reuse preserved;45 HTTP calls |
| Required residual type handling | REJECT; six discrepancies, including two state-changing malformed resets |

Actual product image: `sha256:8aa85e9ea7698ffd222f3fd253752da197a6bea161943553fe035711aa545301`.
Actual prepared runner: `sha256:022bfa4b97f6bfee83dfd8628e957dbca5ab65ab6768ad62bc3820138c287902`; retained reference `starforge-clean-stage1-runner-verifier:20261005t2028` remains alive.
Full image/container/network identities, command arrays/exit codes/timeouts/timings and logs are in `identity.json`, `services.json`, `third-service.json`, `startup-v2-commands.json`, `third-commands.json` and each command's paired JSON/log.

Reconciliation: all85 ledger rows in `ledger-reconciliation-final.json`; all12 inspections in `INSPECTION-RESULTS.md`, with I-07 rejected. Full safe machine report `VERDICT-final.json`. Preliminary `VERDICT.json`/`ledger-reconciliation.json` are retained; final reconciliation corrects two cross-linked convention rows which independently passed, leaving the specific S5-02 wrong-type row rejected. Original test counts and failures are unchanged.

The supplementary recorder's exit0/`passed:true` for the fixture-type observer denotes successful observation execution, not a passing conformance assertion. Its six discrepancy records govern the rejection. No provided test is skipped/edited and no organizer/product source is patched. The first immediate health refusal before readiness is also retained, followed by fresh bounded successful startup.

The complete published tests ran through the exact pinned pytest/harness.plugin/summary command inside the prepared named isolated runner. Lifecycle was independently managed to preserve immutable image IDs and avoid the official CLI setup's shared mutable runner tag. The organizer source and all test bodies/fixtures/plugins remained unchanged. Its participant package publishes only part of judging tests; acceptance here additionally reconciles the written normative contract. Stage1 has no previous-stage upgrade requirement or browser UI requirement. Docker's internal mode does not expose host mappings on this platform; isolated origins verified binding/PORT behavior as the pinned harness prescribes.

Exports and credential contexts stay private local mode600 artifacts inside a mode700 directory; none are posted to the room. Owned services/runner/network were removed; no parallel earlier-run resources were read, stopped or pruned. Prepared runner reference is retained. A changed revision needs a fresh complete checkout and verdict, not relabeled counts.

Observed model/runtime: Codex/gpt-6.1-sol; high effort per owner briefing. Independent token usage and billing are unavailable and remain unknown. No human decision or permission change was requested.
