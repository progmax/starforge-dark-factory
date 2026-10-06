# REJECT — ordinary login deadline under repeated valid replacement

Product `4edb95b405225ab9f76b945ae06b1a341dd50b0f`; frozen audit `52b50da43a750452ed44fb9ab118c9576428a475`; organizer `803560d2a678ace1414465c098eb0ab5380ffade`.

Stage1 §2 requires ordinary requests within5s with up to50 in flight. The expanded repair handoff explicitly requires repeated-generation/auth churn deadlines end to end, including FIFO admission, hashing, revalidation and publication. All inputs in this reproduction are valid and bounded.

`staggered-generation.py` resets a six-user synthetic fixture and exports it. It releases25 valid logins together. A single separate worker imports that exact unchanged export25times, first0.06s after release and then every0.19s. There are exactly50 exercised workload requests and at most26 simultaneously in flight (setup is completed before the workload). Identity, email, password hash and balances in every replacement are unchanged. Login passwords remain correct throughout. No external destinations, source modifications, fault injection or test weakening occur in this HTTP probe.

| Independent origin | Logins | Imports | Actual command result |
|---|---|---|---|
| B18080 |2 returned200;23 timed out5s |25 returned204 |exit1 |
| C19080 |2 returned200;23 timed out5s |25 returned204 |exit1 |

First longest login5.014894s; repeat longest login is recorded in its full per-call JSON. Source/third containers enforce2CPU/2GiB, no mounts/outbound; final inspections show running/noOOM/restarts. The repeat used a third process independently of B. Source-removal portability had completed on that third process before its owned store was reset for this reproduction.

Source: domain.py `prepare` captures generation/email/user ID/hash under the live lock, **then** calls `password_matches`, which waits for FIFO KDF admission. Queued snapshots therefore age while waiting. `auth` compares generation before success/failure and raises `CredentialChanged` on any replacement; server.py retries capture/admission/KDF without a cap.25 simultaneous valid logins plus valid spaced imports repeatedly invalidate those queued attempts until their5s budget is exceeded. FIFO admission itself works; it does not establish end-to-end liveness. No stale token/wrong-password result was observed or required to provoke this failure.

Evidence: `staggered-generation.py`, `staggered-generation-repeat.py`, both `*-summary.json`, both paired command JSON/logs, `loaded-service-state.log`, `final-service-state.log`. Original reports remain intact. Correct result requires all valid calls within stated budgets while preserving current credential fencing, password hashing, imported sessions and atomic replacement; no fixed retry cap/stale fallback/new response may replace compliance. Product author owns repair; audit assertions remain unchanged.

Other fresh gates pass, including147 published tests,32methods/198subtests, both50-reset loads, eight50-call expanded batches, original6+52boundary/6integral reset checks, two burst/queued credential replacement scenarios, source-aware gate interruption/ABA/failed-password recapture private-instance checks,12invalid-state recoveries and removed-source all-five-retry portability. These passes do not waive this ordinary deadline gap.
