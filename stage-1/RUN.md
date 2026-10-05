# Pocketful Stage1

Run the following complete command from this directory (`submission/stage-1`).
Docker is the only host prerequisite. It builds this directory, records the actual
image ID, creates a unique internal network and starts that immutable image in one
independent container. It needs no Compose, host Python, source mounts, datastore,
credentials or runtime downloads. The host port defaults to18081 to reduce collisions;
set `HOST_PORT` to another available host port for an additional instance.

```sh
sh -eu <<'RUN'
attempt_dir=$(mktemp -d "${TMPDIR:-/tmp}/pocketful-clean-stage1.XXXXXXXX")
attempt_name=$(basename "$attempt_dir" | tr '[:upper:]' '[:lower:]')
service_port=${PORT:-8080}
host_port=${HOST_PORT:-18081}
docker build --iidfile "$attempt_dir/image.id" .
image_id=$(cat "$attempt_dir/image.id")
network_id=$(docker network create --internal "$attempt_name-net")
docker run --detach --name "$attempt_name-service" \
  --cidfile "$attempt_dir/container.id" --network "$network_id" \
  --cpus=2 --memory=2g --memory-swap=2g \
  -e PORT="$service_port" -p "127.0.0.1:$host_port:$service_port" "$image_id"
printf 'Image: %s\nNetwork: %s\nEvidence directory: %s\nHealth: http://127.0.0.1:%s/health\n' \
  "$image_id" "$network_id" "$attempt_dir" "$host_port"
printf 'Cleanup only this instance: docker rm -f %s-service && docker network rm %s-net\n' \
  "$attempt_name" "$attempt_name"
RUN
```

The image listens on `0.0.0.0`, defaults to8080 and honors `-e PORT=<port>`.
An internal Docker network blocks external routing. The verifier must independently
confirm its platform's network isolation and port exposure; a generic prepared runner
may join that same isolated network to access the service directly. No outbound client
exists in the application. Both runtime modules and the Python/OpenSSL standard library
are inside the image. The initial store is empty and healthy; `POST /_test/reset`
installs the fixture. State is in memory and may disappear on container restart.

For a second independent instance, run the same command with a distinct host port.
Each invocation generates distinct network/container/evidence names and no product
image tag is reused. Save actual IDs for acceptance, and clean up only those instances.
Do not prune shared Docker resources. Docker build may resolve the generic base image
tag; the built product is always started by its actual image ID.

All business HTTP routes require bearer authentication. Health, signup/login and
reset/export/import are unauthenticated as specified. Control endpoints remain enabled
in the image. JSON responses carry UTF-8 media type, including error envelopes;204
has zero content bytes. Successful idempotent writes return201 and exact retries200.

## Representation and atomicity

`domain.py` implements only the supplied Stage1 requirements and the frozen independent
audit `52b50da43a750452ed44fb9ab118c9576428a475`. `server.py` handles HTTP parsing,
routing and response encoding. No organizer example tests, earlier-run artifacts,
existing domain product source, API documentation or schemas were consulted.

One process-wide reentrant lock covers every route, including login/signup, readers,
mutations, export, reset/import and retry resolution. Request bytes are parsed before
the lock; authentication and all live-state work occur inside it. Responses are encoded
under that same lock before sending bytes, so concurrent changes cannot mutate a
receipt or snapshot being returned. A disconnected client retains its committed result
and can retry normally. Request transitions and receipt/idempotency storage share the
same critical section. Failed domain validation precedes mutations and key claims.

Python integers preserve exact wallet arithmetic. JSON numbers are parsed as Decimal,
validated for integral value and converted to integers only after range checks. Split
shares use quotient/remainder in the supplied participant order; derived zero shares
are allowed through request payment. Settlements validate entries in order, then compute
every wallet's complete net change and validate all final balances before applying any
movement. No intermediate settlement debit can create a negative wallet.

Retry scope is user, method, exact path and key. The full parsed body uses a typed
canonical JSON representation: object keys sorted, array order retained, booleans
distinct from numbers, exact numeric digits/exponents normalized without floating point
or Decimal context rounding. Ignored fields are retained in retry identity. Original
response copies survive subsequent request transitions. Key conflicts/replays resolve
before current endpoint field/resource validation. Failures never claim a key.

Passwords use scrypt (`N=16384, r=8, p=1`, random16-byte salt,32-byte digest).
Only hash records enter state; login compares derived digests in constant time. Random
opaque bearer tokens never expire and are independently stored for concurrent sessions.
Replacement controls clear all destination credentials and token records.

## Portable snapshot format

Exports contain `track: "pocketful"`, `format_version: 1` and an opaque JSON `state`.
They are private test artifacts and must not be posted to the room: they include hashes,
session tokens and original retry bodies, which may contain arbitrary caller content.
The application does not log request/response bodies or authorization headers.

The state contains users with hashed credentials and balances, currency/minor units,
tokens, operator IDs, payment/request/settlement records and successful retry body
identities with independent original responses. Opening net balances and historical
seed record IDs distinguish already-applied seeded receipts from later transfers.
Signup appends a zero opening balance. This lets import reconcile recorded post-seed
movements with current balances without replaying them into wallets.

Import constructs and validates a detached snapshot before replacing the live store:
required schema/types, integer ranges, unique handles/emails/IDs, nonnegative balances,
seed total, movement-derived balances, credential encoding, references, request terminal
linkage/at-most-one payment, settlement membership/timestamps, operator/token references
and original retry receipt relationships. Existing pending creation receipts remain
pending in their retry copies even when their current request is terminal. Seeded
historical paid requests may lack a link only when supplied that way in a consistent
fixture; no new paid request omits its payment link. Invalid state returns422 without
any destination effect. No source process, port, file, volume or address is embedded.

## Author checks and acceptance boundary

Static checks only, from this directory:

```sh
python3 -m py_compile domain.py server.py
git -C .. diff --check
git -C .. -c user.name='Clean Builder' -c user.email='clean-builder@pocketful.local' var GIT_AUTHOR_IDENT
```

Builder authoring started2026-10-05 20:51 UTC after explicit Coordinator authorization
and clean audit identity confirmation. The complete direct specification and frozen audit
are the sole domain provenance. The initial product revision is
`24a141b18d0dcba2277b900aef1dd1c8ee3fac47`. Product commits use per-command author
and committer identity `Clean Builder <clean-builder@pocketful.local>`; no shared Git
config or prior commits are rewritten. No source runtime, HTTP, browser or Docker
was executed by Builder. Compilation is a syntax check, not runtime acceptance.

Author checks before handoff: both Python modules compiled with exit0; AST inspection
found only standard-library dependencies and the local domain module. The complete
RUN shell block passed `sh -n` with exit0. Source review traced all live-state mutation
and reader paths through the shared HTTP lock. Staged whitespace, scope, full revision,
clean-tree and author/committer checks are reported in the room after the actual commit.
One native patch attempt failed its RUN text-context match and applied no edits; the
corrected patch was applied normally. No failed product runtime result exists yet.

Verifier must fresh-clone the exact full product and audit revisions and execute all
published applicable harness tests, frozen HTTP tests and audit inspectionsI-01..I-12,
including50-in-flight races, resource/offline/default+alternatePORT checks, invalid state
recovery and portability after removing the source process. Only Verifier can ACCEPT.
Observed authoring runtime/model: Codex/gpt-6.1-sol, high effort per owner briefing;
token usage and billing are not independently measurable here and remain unknown.
