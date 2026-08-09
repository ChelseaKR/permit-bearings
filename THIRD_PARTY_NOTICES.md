# Third-party notices

The repository `LICENSE` applies to original Permit Bearings software and
project-authored material. It does not relicense source documents, government
records, transit feeds, datasets, or other third-party material retained for
evidence and testing. Those items remain subject to their publishers' terms.

## California Design System references

The local version-0 preview compatibility layer is informed by the successor
[California Design
System](https://github.com/Office-of-Digital-Services/California-Design-System)
at commit `f8775cfac090de08b9e0083eb3008bd585f33e91`, dated 2026-01-27. That
project describes itself as pre-Alpha and not production-ready. Its repository
and package metadata do not currently provide one unambiguous redistribution
license, so this repository copies no successor package, source file, or
compiled bundle. The local `ca-*` compatibility CSS and markup are
project-authored implementations; the commit is a pinned design reference, not
a redistributed dependency.

Published color, type, spacing, and width token values are adapted from the
`cagov` theme in `@cagov/ds-base-css` from the archived
[California Design System](https://github.com/cagov/design-system), pinned at
commit `4a2ba27967580cbfb10b94b0e1b3193dbcea7c22`. That repository's root license
is the MIT License reproduced below.

The static site also redistributes three unmodified Public Sans WOFF2 files
from that exact archived snapshot:

- `fonts/publicsans-regular-webfont.woff2` as
  `assets/fonts/publicsans-regular-webfont.woff2`;
- `fonts/publicsans-semibold-webfont.woff2` as
  `assets/fonts/publicsans-semibold-webfont.woff2`; and
- `fonts/publicsans-bold-webfont.woff2` as
  `assets/fonts/publicsans-bold-webfont.woff2`.

Public Sans combines the SIL Open Font License 1.1 Libre Franklin base with
U.S. General Services Administration modifications released through CC0; the
Public Sans project directs users of the combined font to follow the SIL Open
Font License 1.1 reproduced below. No State logo, official-site banner,
branding, affiliation, or endorsement is copied or claimed.

### MIT License for archived California Design System material

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

### SIL Open Font License 1.1 for Public Sans

Copyright 2015 The Public Sans Project Authors
(https://github.com/uswds/public-sans)

This Font Software is licensed under the SIL Open Font License, Version 1.1.

```text
-----------------------------------------------------------
SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007
-----------------------------------------------------------

PREAMBLE
The goals of the Open Font License (OFL) are to stimulate worldwide
development of collaborative font projects, to support the font creation
efforts of academic and linguistic communities, and to provide a free and
open framework in which fonts may be shared and improved in partnership with
others.

The OFL allows the licensed fonts to be used, studied, modified and
redistributed freely as long as they are not sold by themselves. The fonts,
including any derivative works, can be bundled, embedded, redistributed
and/or sold with any software provided that any reserved names are not used
by derivative works. The fonts and derivatives, however, cannot be released
under any other type of license. The requirement for fonts to remain under
this license does not apply to any document created using the fonts or their
derivatives.

DEFINITIONS
"Font Software" refers to the set of files released by the Copyright
Holder(s) under this license and clearly marked as such. This may include
source files, build scripts and documentation.

"Reserved Font Name" refers to any names specified as such after the
copyright statement(s).

"Original Version" refers to the collection of Font Software components as
distributed by the Copyright Holder(s).

"Modified Version" refers to any derivative made by adding to, deleting, or
substituting -- in part or in whole -- any of the components of the Original
Version, by changing formats or by porting the Font Software to a new
environment.

"Author" refers to any designer, engineer, programmer, technical writer or
other person who contributed to the Font Software.

PERMISSION & CONDITIONS
Permission is hereby granted, free of charge, to any person obtaining a copy
of the Font Software, to use, study, copy, merge, embed, modify, redistribute,
and sell modified and unmodified copies of the Font Software, subject to the
following conditions:

1) Neither the Font Software nor any of its individual components, in Original
or Modified Versions, may be sold by itself.

2) Original or Modified Versions of the Font Software may be bundled,
redistributed and/or sold with any software, provided that each copy contains
the above copyright notice and this license. These can be included either as
stand-alone text files, human-readable headers or in the appropriate
machine-readable metadata fields within text or binary files as long as those
fields can be easily viewed by the user.

3) No Modified Version of the Font Software may use the Reserved Font Name(s)
unless explicit written permission is granted by the corresponding Copyright
Holder. This restriction only applies to the primary font name as presented
to the users.

4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font
Software shall not be used to promote, endorse or advertise any Modified
Version, except to acknowledge the contribution(s) of the Copyright Holder(s)
and the Author(s) or with their explicit written permission.

5) The Font Software, modified or unmodified, in part or in whole, must be
distributed entirely under this license, and must not be distributed under
any other license. The requirement for fonts to remain under this license
does not apply to any document created using the Font Software.

TERMINATION
This license becomes null and void if any of the above conditions are not met.

DISCLAIMER
THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT OF COPYRIGHT, PATENT,
TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR
ANY CLAIM, DAMAGES OR OTHER LIABILITY, INCLUDING ANY GENERAL, SPECIAL,
INDIRECT, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF THE USE OR INABILITY TO USE
THE FONT SOFTWARE OR FROM OTHER DEALINGS IN THE FONT SOFTWARE.
```

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
- `corpus/yolo/` contains metadata for Yolo County's public parcel feature
  layer, not a parcel query or parcel record. Its canonical URL, retrieval
  date, and content hash are recorded in `data/sources.json`. Yolo County does
  not endorse this project.
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
