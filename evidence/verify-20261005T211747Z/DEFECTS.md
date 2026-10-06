# Required request deadline failure — repaired exact revision

Product `0655f50e9d66b5a5679ec98e6ef3b3977ed5220a`; audit `52b50da43a750452ed44fb9ab118c9576428a475`; organizer `803560d2a678ace1414465c098eb0ab5380ffade`.

Stage1 §2 resource table requires up to50 requests in flight, ordinary request timeout5s and reset10s. §10 gives test controls10s. The specification does not exempt concurrent control calls from these deadlines.

Reproduction executes `control-load.py` in the immutable prepared runner on this attempt's internal network. It releases50 clients at a threading barrier. Each client sends one unauthenticated valid reset with the six-user frozen-audit fixture (`acceptance.fixture([100]*6)`). Service limits are2CPU/2GiB, no mounts, no outbound route. The HTTP wrapper uses10s for reset. No external service/load generator is contacted.

| Probe | Actual result |
|---|---|
| First origin8080,50 valid resets |38 returned204;12 timed out. Longest measured client10.019971s. |
| Second independent origin18080, same50 resets |39 returned204;11 timed out. Longest measured client10.024501s. |
| Second origin,45 reset workers then5 health workers after1s, maximum50workers |38 resets returned204;7 reset timeouts. All5 health calls timed out at their5s budget. Reset max10.031167s; health max5.006423s. |

Every probe exited1 and preserved its full per-call report, commands and timings. Existing successful type-error repair remained successful; no assertion or source was changed to produce this result.

Source diagnosis: server.py:68 acquires the one Service.lock before routing reset. domain.py:686 route calls build_fixture:166 within that lock; every fixture user requires password_hash:130, which synchronously runs scrypt. Measured completion times progress approximately0.25–0.26s per six-user reset, so50 reset operations exceed the10s window. Ordinary health also waits for this same lock. Repeat across two origins supports a product serialization bottleneck rather than a one-off transport fault. Inspection shows both services running, no OOM/restarts, and unchanged CPU/memory limits. Memory resource observation after repeat544.7MiB/2GiB is an idle point observation, not a peak/throughput claim.

Evidence: `control-load.py`, `control-load-summary.json`, `control-load.log`, `control-load-repeat.py`, `control-load-repeat-summary.json`, `control-load-repeat.log`, `mixed-control-health.py`, `mixed-control-health-summary.json`, `mixed-control-health.log`, `loaded-service-state.log`, `final-service-state.log`.

Required result: all valid bounded calls finish within their specified budgets while preserving atomic state and real hashed-password storage. Repair belongs to Builder; Auditor assertions remain frozen. Do not replace password hashing with plaintext or weaken stated resource limits, HTTP timeouts, concurrency or coverage to relabel the failures. Hash algorithm/encoding/parameters are implementation choices within the stated hashing requirement. A new full revision needs fresh complete verification.

Original revision's malformed-reset rejection stays separate in `checks/verify-20261005T210331Z`. This repaired revision passed all six original cases,52 expanded malformed/boundary probes and6 valid numeric representations; its new rejection is the deadline requirement.
