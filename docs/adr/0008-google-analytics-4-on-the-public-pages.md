# ADR-0008: Google Analytics 4 on the public pages

**Status:** Accepted
**Date:** 2026-09-17
**Deciders:** Repository owner
**Amends:** ADR-0002 (its description of the current public prototype only;
the proposed beta boundary is unchanged). ADR-0002 and
`docs/BETA-OPERATIONS-RUNBOOK.md` are hash-bound by the beta operations ledger
(`beta_operations.DOCUMENT_BINDINGS`), so this record amends them rather than
editing their bytes.

## Context

The owner decided on 2026-09-17 to run Google Analytics 4 on every public site
in the portfolio and to update privacy pages and claims to match. Until now this
site said it had "no tracking", the repository description said "no tracking",
and `docs/DATA-FLOW.md`, `SECURITY.md` and the README described a public site
with no telemetry. ADR-0002's context paragraph said the same of the prototype.
AGENTS.md requires the fields, purpose, data flow, subprocessors, access,
retention and review needs to be written down before telemetry is added. This
record is that write-up.

## Decision

The six public pages (`index.html`, `check.html`, `prepare.html`,
`review.html`, `evidence.html` and the new `privacy.html`) load one first-party
script, `assets/analytics.js`. It loads Google's `gtag.js` for GA4 property
554878769 (web stream `G-9FJBLEN2ZJ`) only when all of these hold:

- the measurement ID in `assets/analytics.js` is set and well formed (`""`
  turns GA off everywhere);
- the page is served over HTTPS from `chelseakr.github.io` under
  `/permit-bearings/`, so local previews, the test and Lighthouse servers on
  127.0.0.1, CI, and any other host (including a future partner beta) load
  nothing from Google;
- the browser does not send Global Privacy Control, and Do Not Track is off;
  and
- the visitor has not used the footer's "Opt out of analytics" control.

When it does load:

- **Consent Mode v2 defaults.** `ad_storage`, `ad_user_data` and
  `ad_personalization` are denied everywhere. `analytics_storage` is denied
  through `region` for the EEA (the EU-27 plus Iceland, Liechtenstein and
  Norway), the United Kingdom and Switzerland, and granted elsewhere. There is
  no consent banner, so nothing updates these defaults. Visitors in those
  regions get no GA cookie, and Google receives cookieless pings from them.
- **Config.** `allow_google_signals: false` and
  `allow_ad_personalization_signals: false`. The property itself has Google
  signals disabled and 14-month event retention.
- **Addresses are stripped.** `page_location` is the origin and path only, so
  no query string (`?sample=`, `?journey=`, `?changed=`) and no fragment reaches
  Google. `page_referrer` is the referring site's origin only. The pages also
  keep `<meta name="referrer" content="no-referrer">`.
- **No applicant content.** The loader never reads a form, the intake answers,
  pasted ordinance text, or the AI assistance region. It sends no custom
  events.

The footer control on every page stores `"1"` under the localStorage key
`permit-bearings:analytics-opt-out` and sets Google's
`window["ga-disable-G-9FJBLEN2ZJ"]`. "Opt back in" removes the key. The control
is hidden without JavaScript, and it is hidden with an explanation under
GPC/DNT or when storage is blocked. `privacy.html` describes all of this.

The CSP meta tag on each page adds the minimum GA origins: `script-src
https://www.googletagmanager.com`; `connect-src https://*.google-analytics.com
https://*.analytics.google.com https://www.googletagmanager.com`; and `img-src
https://*.google-analytics.com https://www.googletagmanager.com`. Inline script
stays forbidden.

## The AGENTS.md inventory

| Item | Record |
|---|---|
| Collected fields | Page address (origin and path), page title, referring origin, browser, device type, screen size, language, and an approximate location Google derives from the IP address (GA4 does not log or store IP addresses). With the stream's default enhanced measurement, also scroll depth, outbound link clicks and file downloads. |
| Purpose | Counting which public pages are used. Nothing in GA is used to screen, route or evaluate a project. |
| Not collected | Project answers, jurisdiction or facts entered, pasted text, AI assistance input or output, query strings, fragments. |
| Data flow and subprocessors | Browser to Google LLC (US) through `gtag.js`. GitHub Pages hosting is unchanged. |
| Access and security boundary | The GA4 property belongs to the repository owner. No jurisdiction, partner or applicant system receives GA data. The loader is a first-party file under the existing CSP. |
| Retention and deletion | 14 months of event data in the property. Visitors can clear GA cookies and the opt-out key in their browser. |
| Jurisdiction ownership and export | Not applicable: GA holds no applicant or jurisdiction record, and the prototype is not a jurisdiction system. |
| CPRA records search | Not applicable to the prototype. A jurisdiction deployment would be on another host, where the loader does not run. |
| Deployment review | A partner beta must record GA in its inventory if it ever serves these pages from `chelseakr.github.io`, or set the ID to `""`. |

## Consequences

- The site now uses a third party and sets cookies for some visitors, so the
  "no tracking" claims are removed or corrected in the README, `SECURITY.md`,
  `docs/DATA-FLOW.md`, `docs/DESIGN.md`, `docs/SHOWCASE-VALIDATION-PLAN.md`,
  and the repository description.
- ADR-0002's proposed beta boundary ("no application telemetry or behavioral
  analytics") still stands for a beta deployment. The loader's host binding is
  what keeps a beta on another host inside it. The runbook's table row
  "Application telemetry/analytics: None" and its step-2 source screen are
  about a beta host and stay true there. When the ledger is next re-bound, the
  runbook should name `assets/analytics.js` in step 2 and say that its host
  binding has to be confirmed for the beta host.
- The accessibility, Lighthouse and pytest runs never contact Google, because
  they serve the pages from 127.0.0.1.
- Owner steps in the GA4 web stream settings: under Enhanced measurement, turn
  off "Page changes based on browser history events" (`check.html` calls
  `history.replaceState`, and GA would send the full address with it), "Site
  search" and "Form interactions".
- `tests/test_analytics.py` runs the loader in Node against each guard and
  includes negative controls that remove each guard and confirm the harness
  notices.
