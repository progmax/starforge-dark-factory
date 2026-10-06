# Starforge — Pocketful Dark Factory

Solo team: **Starforge** (progmax). Track: **pocketful**. Event: WeAreDevelopers × BAND Dark Factory. [Team dashboard](https://lablab.ai/ai-hackathons/wearedevelopers-hackathon/starforge).

## Delivered result

This submission delivers **Stage 1 only**, an HTTP service for synthetic wallet balances, payments, money requests, bill splits and atomic net settlements. There is no browser application in Stage 1. No real funds or banking integration are involved.

Independent BAND Verifier accepted product `a8805bf4dc2297e0953ea4a5979fcd85c98b95b4` with audit `52b50da43a750452ed44fb9ab118c9576428a475`. The complete published Stage 1 suite passed 147/147; the independent suite passed 32 methods and 198 subtests. All 85 requirements-ledger rows and 12 inspection obligations were reconciled. These are participant checks, not a claim about unavailable private judging suites.

## Run

Follow [stage-1/RUN.md](stage-1/RUN.md) for the exact build and start command. Its [Dockerfile](stage-1/Dockerfile) builds a standalone service; runtime needs no outbound network or external datastore. Python standard library, threaded HTTP, exact monetary arithmetic and scrypt credential hashing are included in the container.

## Read the factory and evidence

- [FACTORY.md](FACTORY.md): role ownership, reproducible setup, costs, failure handling and limits.
- [mandates/](mandates/): the four generic mandates actually configured for this room.
- `room.json`: the genuine unchanged full BAND download for **Starforge clean Stage 1**, room `615b6e94-4717-404e-ba86-05015a1a0092`.
- [evidence/STAGE1-OUTCOME.md](evidence/STAGE1-OUTCOME.md): accepted revisions, measurements and preserved defects.
- [audit/LEDGER.md](audit/LEDGER.md) and [audit/RUN.md](audit/RUN.md): independent requirements, assertions and reproduction.
- [evidence/audit-history.bundle](evidence/audit-history.bundle): independent Auditor Git history, preserved without a nested repository.

The product history is the original agent history; operator packaging changes only root documentation and copied evidence. No stage source is written or altered by the operator. Three failed product revisions and their repairs remain in Git and the full room log. The earlier development run and supplementary OpenCode test room are excluded from this submission.

## Reproduce the organizer checks

Use the official [participant guide](https://github.com/band-ai/dark-factory-wearedevs/blob/803560d2a678ace1414465c098eb0ab5380ffade/docs/participant-guide.md) and organizer commit `803560d2a678ace1414465c098eb0ab5380ffade`.

```sh
python -m harness check /absolute/path/to/starforge-dark-factory --track pocketful
python -m harness run --track pocketful --repo /absolute/path/to/starforge-dark-factory --stage 1 --mode isolated --out /absolute/path/to/new-evidence-directory
```

The next-stage overshoot is expected to fail because no Stage 2 UI is shipped. Product acceptance applies only to the exact source and frozen audit revisions above. Each completed later stage will require its own folder and acceptance; no empty later-stage folders are included.
