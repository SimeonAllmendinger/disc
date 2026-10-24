# DISC — Disclosure–Incident Securities Corpus

DISC links 9,001 AI incidents, recorded by the AI Incident Database (AIID), the AIAAIC Repository and
the OECD AI Incidents and Hazards Monitor (AIM) since 2016, to the SEC filings of the AI actors they
implicate. It shows, incident by incident, whether disclosure had anticipated the incident's risk
before the incident started, and what the next report did about it: reported it, revised or retained the
risk, added it, removed it, or stayed silent.

Version 0.1.0, draft, not yet published. Built 16 October 2026.

## What is in it

Eighteen tables as Parquet in `data/`, the filing texts (`risk_factor_sections`) in one file per filing
year, described by [`croissant.json`](croissant.json) (Croissant 1.0 with its Responsible AI fields). Every column is defined in
[`docs/documentation.md`](docs/documentation.md); the labels follow two codebooks,
[`docs/codebook-incidents.md`](docs/codebook-incidents.md) and
[`docs/codebook-disclosures.md`](docs/codebook-disclosures.md).

| Side | Table | One row per |
|---|---|---|
| Incidents | `incidents` | incident (9,001): dates, coded labels, quadrant and outcome |
| | `incident_records` | record in AIID, AIAAIC or OECD AIM (12,036) |
| | `articles` | article the databases link to an incident (239,743); `ref` marks those the coders read |
| | `source_labels` | record × label: the databases' own labels (AIID's MIT classification, OECD AIM's, AIAAIC's), kept apart from ours |
| | `incident_actors` | incident × AI actor position (deployer, provider, upstream provider) |
| | `actors` | AI actor (7,572), with its SEC CIK where it files |
| | `evidence` | incident × label: the quote the label rests on, and its source |
| Disclosure | `filings` | SEC filing × registrant |
| | `passages` | coded passage: an AI sentence of a filing with its neighbours (17,578) |
| | `passage_filings` | passage × filing it appears in |
| | `passage_codes` | passage: the same labels as the incidents, plus status |
| | `passage_evidence` | passage × label: the quote |
| | `risk_factor_sections` | text section of a filing: risk factors, business section, or AI excerpt (24,797) |
| The link | `outcomes` | matched incident × implicated AI actor (2,280): anticipated? how addressed? |
| | `responses` | incident × 8-K or 6-K in its window (10,866): does it respond? |
| | `reported_references` | passage saying the incident's risk materialised, read for whether it refers to the incident |
| | `revisions` | revised passage: what changed, and how it speaks to each incident |
| Lookup | `mit_taxonomy` | MIT AI Risk Repository subdomain (24) |

Of the 9,001 incidents, 2,000 are matched (column `matched`): an implicated AI actor files with the
SEC, had disclosure in force when the incident started, and filed a periodic report after it. They fall into
four quadrants: Covered 877, Fixed 104, Dropped 7, Missed 1,012.

## Quick start

```python
import glob
import pandas as pd

incidents = pd.read_parquet("data/incidents.parquet")
outcomes = pd.read_parquet("data/outcomes.parquet")
evidence = pd.read_parquet("data/evidence.parquet")

matched = incidents[incidents.matched]
print(matched.quadrant.value_counts())

# the outcome of each incident's implicated AI actors, with the incident's risk type
pairs = outcomes.merge(incidents[["incident_id", "title", "mit_subdomain"]], on="incident_id")

# the filing texts, one file per filing year, as one table
texts = pd.concat(pd.read_parquet(f) for f in sorted(glob.glob("data/risk_factor_sections_*.parquet")))
```

## Explorer

`explorer/` browses the release, one dot per incident, all 9,001, in three arrangements: a timeline of
when the incident started; the four quadrants of the 2,000 matched incidents (risk type disclosed or
not when the incident started, and in the next periodic report), with the 7,001 unmatched in a band
beside them by reason; and the impact layers as waves out from the AI system, sectored
by risk domain.
Any label colours the dots. A dot opens the incident: its labels with their quotes, its records and
every article the databases link, and its AI actors' disclosure over time, including a word-level
comparison of any two filings (their risk factors, or a current report's AI excerpt) and the edits of
each revised passage against the one it replaces. Its Download panel offers the tables, the filing
texts by year, the docs and the codebooks.

```bash
pip install pandas pyarrow
python explorer/serve.py          # http://localhost:8765, reading data/
```

At first start it copies the risk-factor sections into a local index (`explorer/.cache/`, a few
minutes); comparisons are available once that is done.

`docs/explorer/` is the same explorer as static files, for hosting without a server; its Download
panel links the files in `data/` and `docs/`. To rebuild and try it:

```bash
python explorer/export.py --out docs/explorer --repo-path docs/explorer
python -m http.server -d .        # then open http://localhost:8000/docs/explorer/
```

The page compares the two filings in the browser, from texts it loads on demand.

## How it was made

- **Incidents.** AIID (snapshot of 1 September 2026), AIAAIC and OECD AIM (8 September 2026),
  deduplicated into incidents. Each is coded against written codebooks by LLM coders (Claude Opus 5.5;
  Claude Sonnet 5.5 on a fixed tenth), every label with the quote it rests on.
- **Disclosure.** The SEC EDGAR filings, filed 1 January 2015 – 30 September 2026, of the 328 AI actors
  that file with the SEC: annual reports (10-K, 20-F, 40-F), 10-Qs and current reports (8-K, 6-K). AI
  passages are cut from their risk factors and legal sections and coded on the incidents' labels.
- **The link.** An incident meets an AI actor's disclosure through its MIT risk type, judged when the
  incident started (anticipated) and at the next report (addressed).

Reliability, limitations, biases and intended uses are in `croissant.json`'s `rai:` fields, written
from [`metadata.json`](metadata.json). In short: incidents are a lower bound of AI harm; annual-report
and 10-Q passages are coded by one coder; each incident carries one risk type; nothing here is a
finding that any filing is misleading.

## Licence and attribution

- **Data:** CC BY-SA 4.0, because AIID's and AIAAIC's records require ShareAlike.
- **Sources to cite:**
  - AIID: McGregor (2021), with the snapshot date and per-incident URLs;
  - the AIAAIC Repository, with a link to each page;
  - OECD AIM: "OECD.AI (2026), AI Incidents and Hazards Monitor", accessed 8 September 2026.
- **SEC filing text** (passages, quotes, risk-factor sections) is public information from SEC EDGAR, cited per filing by accession number and URL. It is not relicensed here.
- **Quotes from news articles** are short excerpts that each evidence one label, linked to their source. They remain their publishers' copyright. Article bodies are not included.

Licence: [`LICENSE`](LICENSE).

## Personal data and corrections

Incidents name people. Public figures named for a public role keep their names; the names of private
individuals and minors are replaced by `[private individual]` in every incident-side text field (3,017 names
in 1,641 incidents; see [`docs/documentation.md`](docs/documentation.md)). Email addresses and telephone
numbers are replaced by `[email]` and `[phone]` in every text field, the SEC filing texts included. URLs
stay as published, less the query parameters that grant access or identify a reader. To
ask for a correction or removal, contact the maintainers (contact to be added before release).

## Citation

To follow with the DOI.

## Repository

This repository holds the release: the documentation, `croissant.json`, `metadata.json` and the
explorer. The tables in `data/` are built by `src/disc.py` in the research repository and published
with each release, not kept in git.
