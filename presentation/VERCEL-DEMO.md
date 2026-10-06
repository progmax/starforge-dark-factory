# Vercel demo deployment

The root Dockerfile.vercel is operator deployment configuration only. It uses the original Builder Dockerfile with COPY paths adjusted for the repository root. No file in stage-1 is changed; its accepted Git tree remains8589e056f9cd3004fdb09ed61084d3d11f5d4fb1.

Set PORT=8080 in Vercel. The hosted API uses synthetic data, ephemeral in-memory state, and the unchanged Stage1 HTTP application. Vercel may scale or retire instances, so online state may reset or differ between instances; the Docker submission and its isolated acceptance remain authoritative. No new graded stage is claimed. Vercel Hobby is used without adding a card or upgrading a plan.

Live API base: https://vercel-stage1-theta.vercel.app
Browser health demo: https://vercel-stage1-theta.vercel.app/health

Hosted smoke check2026-10-06: health200, reset204, login200, payment201, identical retry200, balance10000→8500 with no additional debit. Safe results in evidence/VERCEL-DEMO-RESULT.json; no token or password is included. The deployment was made through official Vercel CLI62.4.0 using its temporary deployment flow. It is an online synthetic demonstration, not another autonomous graded run.
