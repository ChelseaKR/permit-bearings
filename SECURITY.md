# Security policy

Permit Bearings is a pre-release public-sector prototype. The public static
demo has no accounts, uploads, telemetry, runtime model call, or applicant-data
store. The Python reference server accepts a request only long enough to render
a response and does not persist it.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability or exposed secret.
Use GitHub's private vulnerability-reporting flow under **Security → Report a
vulnerability**, or email `ckellyreif@gmail.com` with the subject
`SECURITY: permit-pathways`.

Include the affected commit, a minimal reproduction, likely impact, and any
suggested mitigation. Please avoid submitting real applicant records or other
personal information.

## Supported versions

No stable version has been released. Security fixes apply to the current
default branch only.

## Current boundary

In scope are the deterministic rule and readiness engines, source watcher,
static browser demo, Python reference server, generated-data pipeline, and CI
supply chain. An evidence-integrity bypass—such as action copy appearing from
a stale or fingerprint-mismatched source—is treated as a security-relevant
trust failure.

The made-up Woodland browser handoff accepts only a public journey ID and
version; it does not put project facts in the URL or browser storage. Both
entry pages validate the generated journey, linked route/readiness evidence,
fingerprints, and current source-review windows. Direct, malformed,
duplicated, mismatched, or stale packet entry must withhold findings. The URL
is an identifier for one public synthetic record, not authorization.

The demo is not approved for real applicant data. A deployment that adds
storage, identity, uploads, telemetry, external models, or permitting-system
integration requires a new threat model and privacy review before use.
