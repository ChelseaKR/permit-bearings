# Hosting the optional AI service on AWS Lambda

This directory deploys `permit_pathways.ai` as one arm64 Lambda behind a
Function URL, with a DynamoDB per-day counter as the hard cost ceiling.
It is a prototype showcase deployment: it has rate limiting, a daily cap,
CORS locked to the static site, least-privilege model access, 14-day logs
that carry no request content, and nothing else. It is **not** the
reviewed beta deployment ADR 0002 describes; see "What this does not do".

## Shape and cost

| Piece | Setting | Why |
|---|---|---|
| Lambda `permit-bearings-ai` | python3.12, arm64, 1024 MB, 120 s timeout, reserved concurrency 2 | one explanation call takes 20–40 s; two in flight is enough for a showcase and bounds burst cost |
| Function URL | auth NONE; resource policy grants `InvokeFunctionUrl` and `InvokeFunction` scoped by `lambda:InvokedViaFunctionUrl`; CORS answered by the app, not the edge | the static page calls it directly from the browser; there is no secret a public page could keep; two CORS layers would duplicate `Access-Control-Allow-Origin`, which browsers reject |
| DynamoDB `permit-bearings-ai-budget` | on-demand, TTL 3 days, one item per UTC day | atomic conditional update is the daily cap (`PERMIT_AI_DAILY_CAP`, default 100) |
| IAM | `bedrock:InvokeModel` on one model/profile, `dynamodb:UpdateItem` on one table, logs | nothing else |
| Model | `global.anthropic.claude-sonnet-4-6` via Bedrock | the model this account can invoke today; change `-var model=…` when Sonnet 5 is enabled |

Worst-case spend at the default cap: 100 model-backed requests/day at roughly
$0.02–$0.05 each on Sonnet 4.6 pricing, i.e. under $5/day and usually far
less; Lambda and DynamoDB are within free-tier scale. The per-client limit
(`PERMIT_AI_PER_CLIENT_PER_MINUTE`, default 6) slows a single abuser; the
daily cap stops everyone. A 429 `budget_exhausted` leaves the static page's
deterministic result untouched.

## Deploy

```sh
./deploy/ai-service/build.sh                     # package.zip (≈9 MB) from the locked deps + repo inputs
cd deploy/ai-service
terraform init
terraform plan  -var daily_cap=100
terraform apply -var daily_cap=100               # prints service_url
curl "$(terraform output -raw service_url)health"
```

Then put the URL on the page: append it to the `permit-ai-service` meta
tag's comma-separated list in `check.html` (local first, hosted second) and
add the origin to the page's `connect-src`, and to the same header in
`demo/app.py`. `tests/test_ai_static_wiring.py` pins both lists; update it in
the same change. Redeploy after any service change with `build.sh` and
`terraform apply` (the zip's hash triggers the update).

Terraform state is local to this directory and Git-ignored. A second
operator needs the state file or a remote backend. The `InvokeFunction`
statement is added through a `null_resource` running the AWS CLI because the
pinned provider has no argument for the `InvokedViaFunctionUrl` condition;
`terraform destroy` removes it.

Applied 2026-08-21 in account `014248889144`; the URL is the second
candidate in `check.html`'s `permit-ai-service` meta tag.

## Verify after deploy

- `GET /health` returns `stores_applicant_content: false` and the daily cap.
- From the static page, "Use AI assistance" connects (the local candidate
  fails fast, the hosted one answers) and a draft round-trip works.
- After the cap: `POST /explain` returns 429 `budget_exhausted`.
- CloudWatch log lines contain paths and status codes, never bodies.

## What this does not do

- It does not make the hosted service a reviewed beta. The privacy review of
  the free-text field, the subprocessor record's human sign-off, a threat
  model, incident rehearsal, and the role approvals ADR 0002 lists remain
  `not_run`. `docs/DATA-FLOW.md` records the subprocessor facts.
- It does not authenticate callers; anyone who can reach the URL can spend
  the daily budget. That is the accepted trade for a keyless static page.
- It does not retain applicant content anywhere: Lambda holds the request
  in memory; Bedrock does not retain prompts for training and logs nothing
  unless model-invocation logging is turned on (it is not).
- Removing everything is `terraform destroy`.
