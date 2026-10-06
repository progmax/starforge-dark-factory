# Required residual defects, original exact revision

Product: `28b55ab6b17fb94a7d02f36b66e4d81b80339cc0`.
Audit: `52b50da43a750452ed44fb9ab118c9576428a475`.
Organizer: `803560d2a678ace1414465c098eb0ab5380ffade`.

Specification §5: wrong JSON field type is400 `malformed_request`; correct-type invalid values are422 unless endpoint-specific. §3.3/§4 fixture fields `payments` and `requests` are arrays, `minor_units` and wallet `balance` are numeric. The explicit422 amount/note/visibility exceptions do not exempt those fields.

The six cases in `residual.py:fixture_types` use an otherwise valid six-user fixture. Before each probe the destination is restored to an export with tokens, five original retry receipts, monetary records and operator rights. A subsequent export comparison checks atomic unchanged state without emitting credentials.

| Wrong field type | Expected | Observed | Previous state retained |
|---|---|---|---|
| `payments: {}` |400 malformed_request |204 |No |
| `requests: {}` |400 malformed_request |204 |No |
| `minor_units: true` |400 malformed_request |422 validation_failed |Yes |
| `minor_units: "2"` |400 malformed_request |422 validation_failed |Yes |
| first user `balance: true` |400 malformed_request |422 validation_failed |Yes |
| first user `balance: "100"` |400 malformed_request |422 validation_failed |Yes |

Source: `product/stage-1/domain.py` lines159,171,178,188. `field(..., list)` is used for users but not optional payments/requests; empty objects therefore iterate zero times and install an invalid replacement. Non-amount numeric fields use `integer` whose type errors are422.

Full evidence: `residual.log`, `residual.json`, `residual-summary.json`. The supplementary recorder completed with exit0 because `fixture_types` records discrepancies rather than raising; its `passed:true` field denotes successful observation execution, **not conformance**. These six observed required discrepancies prohibit ACCEPT. No frozen assertion has been changed. An interpretation question was sent to the Auditor; no test amendment was requested.

Required official suite:147 passed; frozen audit:32 methods/198 subtests passed. Those results do not cover this gap. Higher-stage probe collected35 and stopped after its first expected missing-UI failure, with a launched Chromium browser; this is separate from required Stage1 behavior.
