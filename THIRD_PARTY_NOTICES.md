# Third-party notices

The repository `LICENSE` applies to original Permit Bearings software and
project-authored material. It does not relicense source documents, government
records, transit feeds, datasets, or other third-party material retained for
evidence and testing. Those items remain subject to their publishers' terms.

## California Design System

The interface locally implements published color, type, spacing, and width
tokens from the `cagov` theme in `@cagov/ds-base-css`, part of the
[California Design System](https://github.com/cagov/design-system), and follows
the [California Web Standards design
principles](https://webstandards.ca.gov/web-policies/design-and-ux/design-principles/).
The repository does not redistribute the component package. No State branding,
affiliation, or endorsement is claimed.

MIT License

Copyright (c) 2022 CAdotGov

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Government and public-source evidence

- `corpus/hcd/` and `data/jurisdictions/hcd-letters.json` contain or describe
  material published by the California Department of Housing and Community
  Development. The project records source URLs and retrieval metadata; HCD
  does not endorse this project.
- `corpus/leginfo/` contains retrieved copies of official California
  legislative text. The canonical source is the California Legislative
  Information website.
- `corpus/ceqa/` contains a retrieved official CEQAnet project page.
- `corpus/woodland/` contains a retrieved City of Woodland preapproved ADU
  permit checklist. Its canonical URL, retrieval date, and content hash are
  recorded in `data/sources.json`. The broader City workflow webpage is not
  redistributed because its published HTML embeds third-party browser
  credentials. The City does not endorse this project.
- `corpus/ordinances/` contains text derived from official municipal material.
  Exact title, URL, and retrieval metadata are in
  `corpus/ordinances/SOURCES.json`.
- `data/jurisdictions/registry.json` includes U.S. Census Bureau 2020 FIPS
  place and county data, supplemented with an official City of Mountain House
  source recorded in that file.

The repository's derived rule records, fingerprints, tests, and annotations
are not statements by those publishers.

## Transit data

- `corpus/transit/ca-hq-transit-stops.json` is a derived snapshot of the
  California Department of Transportation's
  [High Quality Transit Stops](https://lab.data.ca.gov/dataset/high-quality-transit-stops)
  dataset. California Open Data identifies that dataset's license as
  Creative Commons Attribution. The local file records the retrieval date and
  selected source fields.
- `corpus/gtfs/unitrans.zip` is an official Unitrans GTFS schedule feed
  published at <https://unitrans.ucdavis.edu/gtfs>. Its embedded metadata
  identifies Unitrans as publisher. The publisher page does not state a
  specific reusable-content license, so inclusion here should not be read as
  a license grant; confirm redistribution terms before republishing the
  archive.

Source material is included for auditable prototype evidence and regression
testing. If a source publisher's current terms conflict with redistribution,
remove the bundled copy and retain only permitted metadata or a retrieval
workflow.
