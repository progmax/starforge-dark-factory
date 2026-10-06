# Independent normative ledger

Authority: the complete Stage1 specification supplied directly in this room, pinned organizer source identity `803560d2a678ace1414465c098eb0ab5380ffade`. The auditor did not open organizer files, example tests, implementation, previous run artifacts or history. Source labels below name the supplied sections and endpoint clauses. Each row is a normative obligation or a delivery boundary, not a claim that a product passed. `test_*` names identify executable HTTP checks in `acceptance.py`; `I-*` names identify mandatory Verifier evidence in `INSPECTION.md`. Cross-cutting tests apply independently to all five idempotent paths. Related assertions within a row are inseparable parts of the cited clause.

| ID | Source | Obligation / observable oracle | Evidence |
|---|---|---|---|
| S1-01 | §1 scope; opening instruction | Only own synthetic Stage1 HTTP service; no domain product source/API/schema reuse, no later-stage work required. | I-01 |
| S1-02 | §1 invariant 1 | Sum of balances equals seed total after all writes, failures, retries and concurrent operations; import restores exported total. | test_concurrent_spending_and_reads; test_request_terminal_races; test_settlement_concurrency; test_export_import_portability; I-02 |
| S1-03 | §1 invariant 2 | Nonnegative balances including transiently, never partial debit/credit. | test_concurrent_spending_and_reads; test_control_atomic_races; I-02 |
| S1-04 | §1 invariant 3 | A request moves money at most once under same or different retry keys and terminal races. | test_request_terminal_races; test_cross_path_money_races; test_idempotency_after_state_change; I-02 |
| S1-05 | §1 amounts/scope | Exact integer minor units; transfers only among existing wallets; no external deposits or integrations required. | test_exact_high_balance; test_payment_errors_atomic; I-01 |
| S2-01 | §2 deliverables | HTTP service, Dockerfile and build/start RUN command without manual setup; Compose optional. | I-03 |
| S2-02 | §2 harness contract | Container runs independently; acceptance accesses HTTP, never imports product code on judge host. | I-03 |
| S2-03 | §2 image/runtime | Single container with PORT and mapping, all runtime dependencies/assets/init/seed included; no runtime outbound dependency, Compose unused. | I-04 |
| S2-04 | §2 resource table | Operates at 2 vCPU / 2 GiB, ready within 60 seconds, up to 50 in flight; request <=5 s and controls <=10 s. | test_concurrent_identical_all_paths; test_concurrent_spending_and_reads; I-05 |
| S2-05 | §2 disk | Ephemeral state allowed; abrupt restart durability not required. | I-06 |
| S3-01 | §3.1 | Listen 0.0.0.0, PORT environment and default 8080. | I-03 |
| S3-02 | §3.2 | Ready GET /health is 200 JSON {status:ok}; healthy only after store can serve; startup <=60 s. | test_health; I-05 |
| S3-03 | §3.3 | Unauthenticated enabled reset 204 empty; repeated replacement becomes visible when response completes. | test_reset_replacement_and_failure; test_control_atomic_races |
| S3-04 | §3.4 | JSON with UTF-8 charset on JSON responses; requests sent as specified. | test_health; test_common_validation; I-07 |
| S3-05 | §3.4 | Response timestamps RFC3339 explicit offset. | test_payment_values_and_receipts; test_splits_rounding; test_settlement_net_and_receipts; test_export_import_portability |
| S3-06 | §3.4 | Ignore unknown body fields and query parameters; never reject them. | test_common_validation; test_idempotency_scope_and_json; test_feed_and_pagination |
| S3-07 | §3.4 | IDs opaque strings <=64 chars; tests do not impose prefixes/encoding. | test_authentication; test_payment_values_and_receipts; test_splits_rounding; test_settlement_net_and_receipts |
| S4-01 | §4 currency/model | One fixture currency; minor units 0/2/3 for JPY/EUR/BHD; no rescaling API amounts. | test_reset_seed_and_currency |
| S4-02 | §4 numeric | Integral numeric values 1000,1000.0,1e3 accepted equivalently; strings/booleans invalid amounts. | test_payment_values_and_receipts; test_common_validation |
| S4-03 | §4 users | Handles unique, immutable, pattern a-z0-9_ length1..20; seeded handles retained. | test_authentication; test_concurrent_signup; test_reset_seed_and_currency; I-08 |
| S4-04 | §4 derived handle | Signup local part lowercase, replace each disallowed char with _, truncate20; collision fails atomically. | test_authentication |
| S4-05 | §4 new users | Signup balance0 and immediately receive payments and requests. | test_authentication |
| S4-06 | §4 payment/request | Direct/request payment immediate atomic; request pending -> one terminal state; correct requester/payer roles. | test_requests_and_insufficient_recovery; test_request_permissions_and_terminal_states; I-02 |
| S4-07 | §4 overbalance requests | Request may exceed payer balance; pay fails409 unchanged; later incoming funds allow same request. | test_requests_and_insufficient_recovery |
| S4-08 | §4 visibility/feed | Payment visible iff public or caller party; private receiver sees same visibility, no operator exception. | test_feed_and_pagination; test_settlement_validation_and_permissions |
| S4-09 | §4 requests/splits | Requests only in parties' request lists, never feed; split itself never feed item. | test_feed_and_pagination; test_splits_rounding |
| S4-10 | §4 arithmetic range | Per amount <=1e9; balances within ±2^53; exact arithmetic at high values. Overflow rejection code unspecified. | test_exact_high_balance; test_common_validation; I-02 |
| S4-11 | §4 fixture | Seed password usable immediately; balances already net, seeded payments not replayed. | test_reset_seed_and_currency |
| S4-12 | §4 negative fixture | Negative seeded balance422 validation_failed; prior state unchanged. | test_reset_replacement_and_failure |
| S5-01 | §5 errors | Every error has error.code and human-readable string message; no5xx even under load. | test_common_validation; test_concurrent_spending_and_reads; I-07 |
| S5-02 | §5 table | Unparseable JSON/wrong JSON field type400 malformed_request unless explicit exception. | test_common_validation; test_authentication |
| S5-03 | §5 table | Missing required fields422 validation_failed; correct-type invalid format/range422 unless endpoint-specific code. | test_common_validation; test_authentication |
| S5-04 | §5 exceptions | Invalid amount including strings/bools, note nonstring/null, visibility any non-public/private422. Only omission selects defaults. | test_common_validation |
| S5-05 | §5 query syntax/ranges | Decimal digits only; limit1..200 default50, offset>=0 default0; invalid numeric forms422. | test_feed_and_pagination; test_request_lists; test_sorting_and_default_pagination |
| S5-06 | §5 key range | Absent/empty key400 missing_idempotency_key; length1..255; over255422 validation_failed. | test_idempotency_all_paths |
| S5-07 | §5 permission/errors | Missing/malformed/unknown bearer401; forbidden403; unknown resource404; required status/code exact. | test_authenticated_routes; test_request_permissions_and_terminal_states; test_settlement_validation_and_permissions |
| S6-01 | §6 signup/login | Correct201 signup and200 login shapes with user_id, display_name, token. | test_authentication |
| S6-02 | §6 signup table | Duplicate email409 email_taken; password<8/email invalid422; bad login401; derived collision409 handle_taken creates no account. | test_authentication; test_concurrent_signup |
| S6-03 | §6 bearer | All business endpoints authenticated; health/reset/auth/export/import exempt by §10. | test_authenticated_routes; test_export_import_portability |
| S6-04 | §6 sessions | Multiple tokens remain valid concurrently, no expiry; tokens preserved after import. | test_authentication; test_export_import_portability; I-09 |
| S6-05 | §6 passwords | Password hashing function, no plaintext storage, including seeded/signup/export/import state. Encoding unspecified. | I-09 |
| S7-01 | §7 five paths | payments, requests, request-pay, splits, settlements each require key; first success201. | test_idempotency_all_paths |
| S7-02 | §7 replay | Same user/method/path/key/body replay200, identical original JSON response, no additional effect. | test_idempotency_all_paths; test_idempotency_after_state_change |
| S7-03 | §7 scope | Distinct users and paths independent for identical key; distinct request-pay IDs independent. | test_idempotency_scope_and_json |
| S7-04 | §7 equality | Same parsed JSON regardless object key order/whitespace/numeric representation; array order and absent-vs-explicit defaults differ. | test_idempotency_scope_and_json |
| S7-05 | §7 conflict | Different parsed body same claimed key409 idempotency_key_reuse, including otherwise invalid changed field body. | test_idempotency_all_paths; test_idempotency_scope_and_json; test_concurrent_conflicting_keys |
| S7-06 | §7 failed use | Every failed4xx leaves key reusable; corrected request is first use201. | test_idempotency_all_paths; test_settlement_validation_and_permissions |
| S7-07 | §7 concurrent | 50 simultaneous identical unused-key calls: exactly one201, all others200 same body; one effect. | test_concurrent_identical_all_paths |
| S7-08 | §7 changed resource | Original successful replay survives paid/declined/cancelled state; original body and no writes. | test_idempotency_after_state_change; test_export_import_portability |
| S7-09 | §7 precedence | Once object parsed and caller authenticated, claimed key resolved before field validation/current-resource checks. | test_idempotency_all_paths; test_idempotency_after_state_change |
| S8-01 | §8 /me | Caller user_id/display_name/handle/balance/currency/minor_units exact. | test_reset_seed_and_currency; test_authentication |
| S8-02 | §8 payments success | Receipt fields sender/recipient IDs/handles/amount/currency/note/visibility/request_id/created_at; defaults note empty/public; settlement_id null per §11. | test_payment_values_and_receipts |
| S8-03 | §8 payments errors | Short funds409; amount range/noninteger422; own handle422 self_payment; note>200/invalid visibility422; unknown handle404. | test_payment_errors_atomic; test_common_validation |
| S8-04 | §8 payment atomicity | Debit/credit single atomic step; failed payment no trace; verbatim note Unicode/emoji no normalization/trimming. | test_payment_values_and_receipts; test_payment_errors_atomic; test_concurrent_spending_and_reads; I-02 |
| S8-05 | §8 requests success | Caller requester; receipt party IDs/handles/amount/currency/note/pending/null payment/timestamp; optional note empty. | test_requests_and_insufficient_recovery |
| S8-06 | §8 requests errors | Invalid amount/note422; own payer422 self_request; unknown payer404; never funds check. | test_requests_and_insufficient_recovery; test_common_validation |
| S8-07 | §8 request-pay | Only payer; body optional visibility defaultpublic; returns payment201 linked request, sets paid/payment_id. | test_requests_and_insufficient_recovery |
| S8-08 | §8 request-pay errors | Nonpending409 request_not_pending; short funds409; wrong payer403; unknown404. | test_request_permissions_and_terminal_states; test_requests_and_insufficient_recovery |
| S8-09 | §8 decline | Only payer;200 declined; second decline200 current; paid/cancelled409; wrong party403; no key needed. | test_request_permissions_and_terminal_states |
| S8-10 | §8 cancel | Only requester;200 cancelled; second cancel200; paid/declined409; wrong party403; no key needed. | test_request_permissions_and_terminal_states |
| S8-11 | §8 GET requests | Only two parties; incoming/outgoing/both and four status filters; unknown filters422. | test_request_lists |
| S8-12 | §8 request pagination | Newest-first timestamp, correct defaults/ranges/offset/has_more. | test_request_lists; test_sorting_and_default_pagination |
| S8-13 | §8 split success | Listed order shares for all listed participants (caller optional), requests for every other listed party in order; caller requester; no funds checks. | test_splits_rounding |
| S8-14 | §8 split errors | Empty/duplicate participants422; unknown404; amount/note422; no partial requests/claimed key on failure. | test_split_validation_atomic; test_common_validation |
| S8-15 | §8 split self-only | Single caller valid one share zero requests. | test_splits_rounding |
| S8-16 | §8 activity | Only visible payments, newest first, same pagination/ranges; same-second relative order unspecified. | test_feed_and_pagination; test_sorting_and_default_pagination |
| S9-01 | §9 shares | Exact integer sum; max spread1; remainder given first listed, examples1000/3,1/3,10/3,999/3,5/5. | test_splits_rounding |
| S9-02 | §9 zero share | Zero share legal, creates request and can be paid; must not impose ordinary amount minimum on derived share. | test_splits_rounding |
| S9-03 | §9 independence | Different list order moves extra unit, independent previous splits; paying all retains seed total. | test_splits_rounding |
| S10-01 | §10 control endpoints | Export/import unauthenticated; export200 object track pocketful/version1/state object, import204 empty. | test_export_import_portability |
| S10-02 | §10 opaque portability | Unchanged export accepted in distinct process/port, no source files/volumes/network dependence; source removable. | test_export_import_portability; I-10 |
| S10-03 | §10 replacement | Import atomic replacement, not merge; repeat no duplication; removes destination accounts/credentials/tokens; reset clears imported state. | test_export_import_portability; test_control_atomic_races; test_reset_clears_all_idempotency_paths |
| S10-04 | §10 invalid imports | Unparseable400; missing fields/wrong track/version/invalid state422; destination unchanged. Wrong outer types follow §5; no invented state schema. | test_export_import_validation; I-11 |
| S10-05 | §10 snapshot | Atomic read-only export; subsequent source writes do not mutate prior snapshot. | test_export_import_portability; test_control_atomic_races; I-02 |
| S10-06 | §10 preservation | Accounts/hash login/tokens/currency/balances/payments/requests/permissions/IDs/timestamps retained, not reseeded/replayed. | test_export_import_portability; I-09 |
| S10-07 | §10 idempotency | All completed request bodies/original receipts including settlements preserved, failed keys reusable; preimport tokens and retries work. | test_export_import_portability |
| S10-08 | §10 timeout/privacy | Controls <=10 s; credentials/tokens private artifacts, no room leaks. | I-05; I-12 |
| S11-01 | §11 operators | Optional fixture operator IDs defaultempty; operator any wallets; no token401/nonoperator403; no private-feed/request privilege. | test_settlement_validation_and_permissions |
| S11-02 | §11 batch shape | transfers1..32 objects; malformed batch shape422; unknown fields ignored. | test_settlement_validation_and_permissions |
| S11-03 | §11 entry validation | Ordinary amount/note/visibility/defaults; unknown404/self422 self_payment; entry errors input order before funds. | test_settlement_validation_and_permissions |
| S11-04 | §11 affordability | Net all incoming/outgoing per wallet, nonnegative final; need not be sequentially affordable; short collective409. | test_settlement_net_and_receipts; test_settlement_concurrency |
| S11-05 | §11 atomicity | Entire batch or nothing; failed validation no key/payment/revision; no transient negative balance. Revision is not a public field. | test_settlement_validation_and_permissions; test_settlement_concurrency; I-02 |
| S11-06 | §11 response | settlement_id/committed_at/payments input order; each payment settlement_id batch/null request_id; equal created_at/committed_at. Nonmembers settlement_id null. | test_settlement_net_and_receipts; test_payment_values_and_receipts |
| S11-07 | §11 visibility/replay | Each constituent ordinary visibility; operator receipt includes all; replay200 original full response. | test_settlement_net_and_receipts; test_idempotency_all_paths |
| S11-08 | §11 state preservation | Reset installs fixture operator permissions; import preserves operators/membership/receipts/retries. | test_settlement_validation_and_permissions; test_export_import_portability |

No row grants runtime acceptance to the auditor. Tests and inspection obligations together cover the written contract; finite HTTP observations do not prove internal transient invariants, storage confidentiality, absence of time expiry, or absence of outbound dependencies. Those require the named inspection/runtime evidence before acceptance.
