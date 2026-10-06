# Running the independent Stage1 audit

Auditor author checks are pure/static. Only the Verifier executes HTTP against products, published organizer harnesses, Docker, resource/offline checks and source-aware inspection. No product acceptance is implied by author checks. There are no third-party dependencies; Python3.10+ standard library is sufficient.

From a fresh clone of the exact frozen audit commit:

```sh
python3 -m py_compile acceptance.py
python3 acceptance.py --self-check
python3 acceptance.py --list
git diff --check
git status --porcelain=v1
```

`--self-check` validates pure rounding/timestamp oracles and complete ledger-to-test/inspection links. `--list` never constructs an HTTP client or contacts a service. Running without `--run` lists tests. There are no skip decorators and no optional portability skip.

For acceptance, prepare two independent containers from the exact full product commit/image ID using the product's committed Dockerfile/RUN, distinct ports, separate ephemeral stores,2 vCPU/2 GiB and a unique runtime network with outbound blocked. No shared volumes, source/personal mounts, proxy or external datastore. Use the isolated prepared runner as needed to reach both services. Run this suite from the audit clone using a generic prepared Python installation; never import product source files on the host. Replace the example origins with the two actual isolated endpoints, and use a new evidence directory for every attempt:

```sh
python3 acceptance.py --run \
  --base-url http://127.0.0.1:18081 \
  --peer-url http://127.0.0.1:18082 \
  --report /absolute/path/to/checks/unique-attempt/independent-summary.json
```

The example localhost origins are only suitable if the independent containers are exposed through permitted host port mappings. When the suite runs in the prepared isolated runner, use that attempt's two service addresses on its isolated network. The prepared harness interpreter is `/Users/max/work/ai/hackops/participation/dark-factory/work/checks/verifier-readiness-venv/bin/python`; do not assume local `python3` is that interpreter. The browser path and runner identity belong to the published harness setup, not this HTTP-only suite. Resolve current runner identity as instructed by the owner; never reuse a previous run's digest or service-specific artifacts.

Exit0 requires all collected test methods to run successfully with no errors/failures/skips. The safe JSON summary records actual test/subtest counts, HTTP calls, maximum request duration, start/elapsed times and failed test names. It contains no credentials, tokens or exported state. Keep raw console output/private exports in the attempt directory under private access controls; share safe summaries only. A subtest failure makes the method/suite fail; no failure is silently converted to a pass. The expected method count is recorded by author checks, not a substituted runtime count.

The suite resets both supplied services repeatedly; they must belong exclusively to this attempt. It has50-call worker barriers, per-HTTP timeouts5s ordinary/10s test controls and bounded fixtures, so allow reasonable cumulative runtime. Check the absolute owner stop before starting, reserve time for cleanup/report, and terminate/report BLOCKED if it cannot finish by2026-10-06 04:30 UTC. Never prune shared resources or stop the earlier run. Record actual container/network/image IDs and cleanup only this attempt's resources.

Full acceptance additionally requires:

1. Fresh clones and identity confirmation for exact full product AND audit revisions. Preserve command-level exit statuses and original failures. Changed product or audit revision requires complete fresh verification; do not relabel old counts.
2. The complete applicable published organizer harness in isolated mode after this audit is frozen. Determine its exact documented invocation from pinned organizer source. The auditor intentionally did not inspect those tests, so this RUN does not invent harness flags. Report legitimate higher-stage overshoot separately, never silently skip any Stage1 obligation.
3. Every `I-01` through `I-12` in `INSPECTION.md`, including source atomicity/hashing, startup/default+alternatePORT, resource/offline controls, source-removal portability and source-justified malformed internal state. The audit's two-URL argument alone does not prove processes are independent.
4. A clause-by-clause evidence reconciliation against `LEDGER.md`, all ambiguities resolved within the band or concretely reported BLOCKED/REJECT. Only Verifier ACCEPT with no known required gap can advance the stage.

No audit command authorizes Builder implementation. Coordinator alone releases the Builder after receiving the clean frozen full audit revision.
