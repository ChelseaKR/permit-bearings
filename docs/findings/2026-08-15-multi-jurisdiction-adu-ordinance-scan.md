# Multi-jurisdiction ADU ordinance scan (2026-08-15)

First run of the ordinance conformance scanner against more than one
jurisdiction. The corpus goes from 1 to 7 of the 541 registry entries.

**This is a presence-based screen, not a legal conclusion.** Every flag below is
a candidate provision for staff or counsel review. The scanner cannot detect
*missing* required language, it does not read the whole municipal code, and
silence is not a clean bill of health. Nothing here is an HCD finding, a
violation determination, or advice to any jurisdiction.

## Why these seven

The committed HCD Housing Accountability Unit dataset
(`data/jurisdictions/hcd-letters.json`, 1,314 letters retrieved 2026-08-03)
maps 470 of the 541 registry entries. Counting by authority and letter kind:

- 341 jurisdictions have received at least one letter under Accessory Dwelling
  Unit Law.
- 205 of those have received a **Technical Assistance Letter - Repeal
  Request** under ADU Law, most citing Gov. Code sections 66316 and 66326.
  That letter kind is HCD telling a jurisdiction its ADU ordinance is outdated.

That gives a 205-jurisdiction priority list derived entirely from data already
in the repository, with no fetching required. The seven scanned here are a
convenience sample from that list plus the existing San Diego entry, chosen
because their current ADU chapter is served as plain HTML by a publisher whose
robots.txt permits retrieval. They are not a random or representative sample,
and the counts below do not generalise to the other 534 entries.

## What was fetched, and how

| | |
| --- | --- |
| Host | `www.codepublishing.com` (Code Publishing Inc.), publisher-hosted current municipal code |
| Requests | 14 chapter URLs, one request each, plus 1 `robots.txt` and 7 directory probes |
| Rate | one request every 3 seconds, single-threaded, no retries |
| User agent | `permit-pathways-research/0.1 (+https://github.com/ChelseaKR/permit-pathways; ADU ordinance conformance screening)` |
| Result | 6 chapters retrieved; 8 cities have migrated to a different publisher and returned a redirect notice instead of code text |
| Conversion | tag-stripping to plain text; the retrieved page SHA-256 is recorded per entry in `corpus/ordinances/SOURCES.json` |

`robots.txt` for that host disallows `/search/`, `/dtSearch/`, `/cgi-bin/`,
`*.pdf`, and the `*NT.html` navigation trees. None of those were requested.
Chapter URLs were obtained from a search index rather than by crawling the
disallowed navigation tree. The host sets no `Content-Signal` directives.

Two other publishers that carry most of the remaining California codes,
`library.municode.com` and `codelibrary.amlegal.com`, both set
`Content-Signal: search=yes,ai-train=no,use=reference`. Nothing was fetched
from either. Whether this use is compatible with that signal is a call for
Chelsea, not for the scanner.

## Results

| Jurisdiction | Flags | definite | review | HCD ADU letters | repeal request |
| --- | --- | --- | --- | --- | --- |
| Angels | 4 | 4 | 0 | 1 | yes |
| Capitola | 12 | 5 | 7 | 0 | no |
| Folsom | 3 | 0 | 3 | 1 | yes |
| Foster City | 6 | 0 | 6 | 0 | no |
| San Diego | 1 | 0 | 1 | 4 | no |
| Trinidad | 5 | 1 | 4 | 0 | no |
| Watsonville | 2 | 0 | 2 | 1 | yes |
| **Total** | **33** | **10** | **23** | | |

Before this run the committed corpus produced 1 flag, of `review` severity.

## The finding

Ten of the 33 flags are `definite` severity, and all ten are the same check:
`stale-statutory-citation`, ordinance text citing Government Code sections that
SB 477 (Ch. 7, Stats. 2024) deleted when it relocated State ADU Law from
sections 65852.2 et seq. to sections 66310 through 66342, effective
March 25, 2024. That is the same failure mode as HCD's first ADU finding
against the County of Santa Clara, June 24, 2025.

Three jurisdictions carry it, and the interesting part is which:

**Angels** (`Ch. 17.61`, Ord. 554, 2026) regulates by incorporation and lists
both numbering schemes at once, citing sections 66310 through 66342 *and*
sections 65852.2, 65852.21, 65852.22, 65852.23, 65852.26. Only 65852.21 is
still current. This is the mildest of the three: the current sections are
present and the text closes with "as these provisions may be amended".

**Capitola** (`Ch. 17.74`) is the substantive one. Its purpose clause sets the
chapter's standards "consistent with Government Code Sections 65852.2 through
65852.22", and four further provisions hang off the deleted sections,
including a permit-denial ground at section 65852.2 and a JADU compliance
requirement at section 65852.22. The chapter's authority is written entirely
against a statute that no longer exists.

**Trinidad** (`Ch. 17.54`) defines "accessory dwelling unit" itself by
reference to section 65852.2(i)(4).

**Capitola and Trinidad have no HCD ADU letter at all.** The scanner reproduced
HCD's documented failure mode in two jurisdictions HCD's public enforcement
record has not reached. That is the argument for the corpus: the checks were
derived from HCD letters, and pointed at un-lettered jurisdictions they find
the same thing.

The other 23 flags are `review` severity and are exactly that: owner-occupancy
language, a 16-foot height cap, a side or rear setback figure above four feet,
size caps, and subjective design terms. Each needs a human to decide whether
the provision is an unlawful requirement or a lawful branch. None of them is
asserted here to be a violation.

## Known weaknesses this run exposed

1. **One provision can produce several flags.** Angels' four `definite` flags
   are four section numbers in a single sentence. The count overstates the
   number of distinct problems.
2. **Publisher pages carry no adopted-ordinance history note.** The San Diego
   entry records its enactment and effective dates from the city PDF's own
   history note. The six new entries cannot: the publisher page does not state
   them, so `SOURCES.json` records the retrieval date and page digest only, and
   the operative dates are unconfirmed.
3. **`scan_ordinances.py` re-dates every result on every run.** It takes one
   global `scanned_on` and rewrites all result files, including jurisdictions
   whose text was not re-retrieved. At 7 entries that is untidy; at 200 it is
   misleading.
4. **Text conversion is unreviewed.** Tag stripping is not the same as the
   `pdftotext` path used for San Diego, and no one has diffed the converted
   text against the rendered page.
