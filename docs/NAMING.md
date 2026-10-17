# Unspill: name selection and preliminary screening

Research date: **2026-10-17**. This is a limited naming screen, not a legal
opinion, trademark registration, worldwide clearance, or guarantee against claims.
Registry availability does not establish trademark rights.

## Decision and market fit

**Unspill**, command **`unspill`**, suggests recovering after a mistake: “Get your
work back.” It uses seven lowercase ASCII characters and an ordinary, pronounceable
word. The brand does not incorporate “Git”; the product is described as an
independent recovery tool for Git workspaces. No Git logo or third-party artwork
is used, and no affiliation or endorsement is claimed.

The market already includes [GitUp snapshots](https://gitup.co/) and
[Rewind's hosted GitHub backups](https://rewind.com/products/backups/github/).
Unspill's focus is local snapshots of uncommitted files and Git metadata before
operations, with readable recovery choices. We do not claim to have invented
recovery or promise that local data can never be lost.

## Candidate screening

| Candidate | Finding | Decision |
| --- | --- | --- |
| BGit | [bgit](https://bgitcli.com/docs/) is an existing Git identity CLI | Retire the former name |
| regit / rgit | Existing Git tools and command names, including [regit](https://github.com/woaitsAryan/regit) and [rgit](https://github.com/w4/rgit) | Avoid |
| bkgit / rvgit | Exact package lookups were absent, but both incorporate Git in a new brand | Avoid the added Git trademark-policy question |
| Backlet | [An existing software workspace](https://github.com/sejalpandey30/backlet) uses the name | Avoid |
| Keepoint | [Existing software](https://www.keepoint.app/) uses the name | Avoid |
| Unspill | No competing software brand identified in the limited searches; unrelated trademark results disclosed below | Selected |

The [Git trademark policy](https://git-scm.com/about/trademark) restricts product
names incorporating its mark into new words, while permitting specified descriptive
uses such as “Product Name for Git.” A trademark owner's policy is not itself a
court determination of infringement. This project uses a separate brand to reduce
that issue rather than claiming that every existing Git-containing name is unlawful.

## Search scope and results

- Web queries included `"Unspill" software backup trademark`, `"unspill" app OR
  software OR backup OR company`, and `"unspill" trademark`.
- GitHub repository-name search for `unspill` returned one substring match,
  `sudo-rsingh/unspilled_coffee`, and no exact project name at the time of checking.
- Exact endpoints returned HTTP 404 for [npm](https://registry.npmjs.org/unspill),
  [PyPI](https://pypi.org/pypi/unspill/json),
  [crates.io](https://crates.io/api/v1/crates/unspill), and
  [Homebrew](https://formulae.brew.sh/api/formula/unspill.json). These results do
  not reserve names or prove that registry administrators will allow publication.
- The official [USPTO Trademark Search](https://tmsearch.uspto.gov/) Wordmark
  query `unspill`, with live/dead statuses included and no class filter selected,
  returned two records:
  - **UNSPILL**, serial **76387118**: displayed DEAD / ABANDONED; class 001,
    chemical composition / solid powdered absorbent.
  - **UNSPILL-A-BOWL**, serial **90393331**: displayed LIVE / REGISTERED;
    class 021, pet feeding and drinking bowls.
  Neither displayed software goods/services. That observation is not a legal
  finding that the marks cannot conflict or that abandoned marks have no rights.
- “Unspill” also appears as descriptive terminology in software documentation,
  including [QNX's package utility](https://qdn.qnx.com/developers/docs/6.3.0SP3/neutrino/utilities/p/pkgctl.html)
  and audio-control workflows. No standalone competing recovery product brand was
  identified in the results reviewed; the word is not claimed to be newly invented.

No domain was purchased. EUIPO, WIPO, state registries, other national registers,
and a comprehensive phonetic/design/common-law search were not completed. Search
indexes are incomplete and findings can change. Before substantial commercial
investment, obtain qualified trademark counsel's clearance in intended markets.

## Copyright and licensing

The [U.S. Copyright Office](https://www.copyright.gov/help/faq/faq-protect.html)
explains that names and short phrases are not protected by copyright. Product
names raise trademark questions; code, documentation, and artwork have separate
copyright considerations. The [USPTO clearance guidance](https://www.uspto.gov/trademarks/search/comprehensive-clearance-search-similar-trademarks)
explains why exact-name searches alone are insufficient.

The project retains [Apache-2.0](../LICENSE), Robert Al-Malak's authorship notice,
and [third-party provenance and bundled runtime notices](../THIRD_PARTY.md).
The rename adds no third-party implementation or artwork. An open-source license
does not clear a product name or provide a guarantee against legal claims.
