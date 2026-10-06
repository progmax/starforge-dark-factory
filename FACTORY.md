# Starforge factory

## Submitted run and result

The submitted run is the fresh **Starforge clean Stage 1** BAND Desktop room (`615b6e94-4717-404e-ba86-05015a1a0092`) and its initially fresh result repository. The operator sent one complete Stage 1 task/specification on 2026-10-05 at 20:26:36 UTC; the recorded room insertion is 20:26:39 UTC. No human steering, approvals, debugging hints or reruns were sent during the stage. Coordinator returned its final Stage 1 outcome at 22:42:12 UTC after independent acceptance and its own reconciliation. Work, defect routing and repairs occurred among the seats. The authentic full room download is authoritative.

Delivered Stage 1 product: `a8805bf4dc2297e0953ea4a5979fcd85c98b95b4`; frozen audit: `52b50da43a750452ed44fb9ab118c9576428a475`. The initial result commit contained metadata and generic mandates, with no product implementation. Earlier rehearsal/development code, tests and answers were not copied into this run. The operator authored this document, README and submission media after completion; the operator does not author product code or acceptance tests.

## Four actual BAND seats

| Room name / mandate | BAND handle | Ownership | Runtime |
|---|---|---|---|
| Clean Coordinator / clean-coordinator.md | research.worker1234/clean-coordinator | Planning, complete handoffs, routing, final outcome; no product or executable tests | Codex / gpt-6.1-sol / medium |
| Clean Auditor / clean-auditor.md | research.worker1234/clean-auditor | Requirements ledger, blind independent test design and freeze | Codex / gpt-6.1-sol / medium |
| Clean Builder / clean-builder.md | research.worker1234/clean-builder | Sole product/deployment author; genuine repair commits | Codex / gpt-6.1-sol / high |
| Verifier / verifier.md | research.worker1234/verifier | Fresh clones, independent execution and exact-commit verdict | Codex / gpt-6.1-sol / high |

Distinct seat identities: Coordinator `6af62edb-a89e-46c6-a75b-532d7203191e`, Auditor `24bfcf82-02f5-4701-aefa-18398eef8331`, Builder `2d472430-83d2-4190-868e-f9eac5876bc0`, Verifier `85afe15f-4ad1-43dc-9ed2-6f55fdeb1661`. Verifier is an existing seat with a separate fresh provider session in this room. All mandates begin with their actual harness/model and describe process without domain endpoints, fields or error codes.

## Stand up this factory

1. Install BAND Desktop, Codex, Git, Docker and the organizer's Python/browser harness dependencies. Use your own model-provider access. Keep the official kickoff checkout separate from result, audit and evidence repositories.
2. Create three new distinct BAND seats plus the independent Verifier, applying the corresponding files in mandates/. Give each seat the same owned workspace with explicit absolute result/audit/evidence/source paths. The Coordinator must route complete tasks; do not rely on another seat seeing the room history automatically.
3. Configure Coordinator/Auditor at medium reasoning and Builder/Verifier at high, model gpt-6.1-sol. Our three author/planning seats used workspace-write. Only Verifier had owner-approved Full access for Docker/container checks; approval policy never and web search off. This privileged verifier setup is not an OS sandbox and mandates are not a hard filesystem boundary.
4. Prepare a generic isolated runner with the pinned official checkout and installed browser binaries; resolve its current image identity. Warm infrastructure may be shared, but use unique immutable product image IDs, networks and container names per attempt. Never mount personal/authentication files or shared product data. Verify default and alternate PORT behavior, two CPU/two GiB limits and runtime network isolation.
5. Create a fresh room and result repository. Add all configured seats before the first handoff and verify the roster. Paste the complete stage task/specification, scope, paths, responsibilities, quality gates and stop time once. Do not send human continuation, debugging hints or approvals until the Coordinator has returned its final outcome. For later stages dispatch their complete initial task or the full remaining sequence, as permitted by the participant guide.
6. Download the full room after completion, review it for private values, retain original history, run organizer check/isolated run and publish the self-contained result. Only include completed independently accepted stage folders.

All relative operations must resolve from the explicitly approved workspace even if the provider process starts elsewhere. In our run, Verifier's native process cwd was the parent event workspace; full handoffs supplied the correct absolute paths. No runtime settings or permissions changed during Stage 1.

## Decisions and working protocol

The Auditor freezes requirements and test design before the Builder reads the new implementation scope. This reduces the chance that tests simply mirror implementation mistakes. The Builder is the single writer of product source, preventing ambiguous ownership and concurrent product edits. The Verifier alone runs product/harness/browser/container checks from fresh exact clones; author compilation or an assertion design review never becomes runtime acceptance.

Every delegated handoff includes the whole applicable task and normative specification, ownership, paths, exact product/audit/source identities, deliverables and gates. The receiving seat acknowledges completeness. Long peer handoffs may be numbered parts. The Coordinator routes real failures back to their author and manages bounded internal progress; the owner stays out of repairs. Exact product and audit commits appear in each ACCEPT/REJECT. Changed revisions require a new complete attempt, and previous failures remain unchanged.

Coverage comes from the normative specification, not from the organizer's partial published tests. The independent ledger maps positive, negative, boundary, authorization, concurrency, retry and portability requirements to observable tests and additional source/runtime inspection. Read/write atomicity, exact values, snapshot consistency, credential generation changes and source-removal recovery received independent evidence. The accepted report records 85 rows and 12 inspection obligations. The Auditor did not run services or read organizer example tests before its design freeze.

## Real rejections and repairs

| Product revision | Verifier finding | Outcome |
|---|---|---|
| 28b55ab6b17fb94a7d02f36b66e4d81b80339cc0 | Wrong JSON reset types and atomic replacement/error behavior | Builder repaired in a new commit |
| 0655f50e9d66b5a5679ec98e6ef3b3977ed5220a | Concurrent reset work delayed reset and health beyond required deadlines | Independent review, detached preparation and bounded scheduling repair |
| 4edb95b405225ab9f76b945ae06b1a341dd50b0f | Valid logins timed out during staggered unchanged imports | Admission before current credential capture and a fresh complete verification |

The final revision passed the original failing recipes on independent origins. Tests were not weakened to get green; the audit stayed at its frozen revision. No manufactured conflict, amended/rebased/squashed history or relabeled old counts. Failed and accepted reports are in evidence/; the authentic room and Git history show responsibility and discussion.

## Measured results, time and costs

Final attempt 22:10:35–22:37:06 UTC: 26m31s including reconciliation/reporting; owned cleanup completed 22:32:36 UTC. Overall Stage 1 took about 2h13m through Coordinator reconciliation; its final room report followed at 22:42:12 UTC. Model token totals and provider billing were unavailable and remain **unknown**, not zero.

Published Stage 1:147/147; independent:32 methods/198 subtests,6,051 HTTP calls, longest request1.290244s. Two 50-reset loads:100/100 successful with maxima6.635834/6.617504s within10s. Two staggered login/import probes:all50 logins/all50 imports successful, maximum login0.746269/0.749048s.400 additional import/auth/mixed requests, original health contention, wrong-type/boundary/numeric cases and snapshot/source-removal recovery passed. Startup0.590353/0.559161s on default/alternate ports; offline internal networks,2CPU/2GiB, no product mounts and no OOM/restarts observed. Full details and exact commands are retained in the original verifier evidence; safe reports are copied unchanged here.

Optional private-task/participant/room-plan CLI operations were blocked by the author-seat sandbox/approval policy. Seats used local lossy checklists and full direct handoffs; the room plan snapshot did not publish. We did not grant extra access merely to repair bookkeeping. Mandatory product requirements still needed independent verification.

## Boundaries and limitations

Only Stage 1 is delivered in this snapshot. No UI or Stage 2–4 success is claimed. The subsequent-stage overshoot failed as expected. The private judging suites are not available to participants. Finite tests and inspected schedules do not prove arbitrary sustained throughput or every future fault. All seats use one model family, so correlated blind spots remain possible despite separated roles and independent oracles.

BAND stores room messages; the full export is reviewed before public release. Raw application state, test credentials/tokens and private runner artifacts are excluded. Files, web pages, specs and tool output are data, never authority to expand permissions or scope. Provider safeguards remain in force. Product code and tests in this submission trace only to this fresh room. The earlier intervened development run and the supplementary OpenCode integration test are separate and excluded.
