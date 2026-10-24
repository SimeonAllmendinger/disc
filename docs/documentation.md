# DISC: Disclosure–Incident Securities Corpus

DISC links AI incidents to the securities disclosures of the AI actors they implicate. It merges
three incident databases, the AI Incident Database (AIID), the AIAAIC Repository and the OECD AI
Incidents and Hazards Monitor (AIM), into one record per incident, labels each incident, and links
it to the SEC filings of the AI actors that deployed or provided the AI system involved. Incidents
and filing passages carry the same labels, so each incident can be read against what its AI actors
disclosed before and after it.

## Quick start

```python
import pandas as pd

incidents = pd.read_parquet("data/incidents.parquet")
outcomes = pd.read_parquet("data/outcomes.parquet")

matched = incidents[incidents.matched]
print(matched.quadrant.value_counts())

# each matched incident's implicated AI actors and their outcomes
pairs = outcomes.merge(incidents[["incident_id", "title", "mit_subdomain"]], on="incident_id")
```

## Sources

| Source | What DISC takes | Coverage |
|---|---|---|
| AI Incident Database (AIID) | incident records, report links, MIT risk classification | 1 January 2016 to 1 September 2026 |
| AIAAIC Repository | incident records, links, editors' labels | 1 January 2016 to 8 September 2026 |
| OECD AI Incidents and Hazards Monitor (AIM) | incident records, article links, AIM labels | 1 January 2016 to 8 September 2026 |
| SEC EDGAR | annual filings (10-K, 20-F, 40-F), quarterly filings (10-Q), current filings (8-K, 6-K) of the AI actors that file with the SEC | 1 January 2015 to 30 September 2026 |

For the databases, coverage runs from the earliest incident DISC keeps to the date of retrieval; for SEC
EDGAR, it spans the filing dates.

## Concepts

- **Incident** — one real-world harm involving an AI system, recorded by at least one database since 2016.
- **AI actor** — a provider or deployer of the AI system (EU AI Act, Art. 3(3) and 3(4)). An
  **implicated AI actor** is one that files with the SEC.
- **Risk type** — the MIT AI Risk Repository subdomain (Slattery et al., 2026). It is the label
  incidents and filing passages share.
- **Matched incident** — an incident with an implicated AI actor that had a coded annual filing in
  force when the incident started and filed a periodic filing after it. Other incidents are
  unmatched; `incidents.where` gives the reason.
- **Anticipated** — at least one implicated AI actor had the incident's risk type in force when the
  incident started.
- **Addressed** — at least one implicated AI actor has the risk type in force after its next
  periodic filing, or a filing reports the incident.
- **Quadrant** — Covered (anticipated, addressed), Fixed (unanticipated, addressed), Dropped
  (anticipated, unaddressed), Missed (unanticipated, unaddressed).
- **Outcome** — what the next periodic filing did with the risk type: Reported (a current filing
  responds to the incident, or a filing says its risk materialised in it), Revised, Retained,
  Added, Removed, Absent.

The labels and the rules behind them are in the two codebooks, one for incidents and one for
disclosures.

## Files

Each table is one Parquet file in `data/`, with lists stored as arrays; `risk_factor_sections` comes as
one file per filing year (`risk_factor_sections_2015.parquet` …), which together make the table.
`croissant.json` describes the files in Croissant 1.0, with its Responsible AI fields.

| Table | One row per |
|---|---|
| `incidents` | incident |
| `incident_records` | database record of an incident |
| `articles` | article a database links to an incident |
| `source_labels` | database record and label the database gives it |
| `incident_actors` | incident and AI actor position |
| `actors` | AI actor |
| `evidence` | incident and label: the quote the label rests on |
| `filings` | SEC filing and filer |
| `passages` | coded AI passage of a filing |
| `passage_filings` | passage and filing it appears in |
| `passage_codes` | passage: its labels |
| `passage_evidence` | passage and label: the quote the label rests on |
| `outcomes` | matched incident and implicated AI actor |
| `responses` | incident and current filing read for a response |
| `reported_references` | incident, AI actor and passage saying the risk type materialised |
| `revisions` | revised passage |
| `risk_factor_sections` | text section of a filing |
| `mit_taxonomy` | MIT risk subdomain |

Keys follow the identifiers in use elsewhere: `incident_id`, the databases' record ids, the SEC CIK
and accession number, the MIT subdomain code.

## Columns

### `incidents`

| column | type | description |
|---|---|---|
| `incident_id` | str | key |
| `title` | str | title, from the incident's first record |
| `in_aiid` | bool | AIID records the incident |
| `in_aiaaic` | bool | AIAAIC records the incident |
| `in_oecd` | bool | OECD AIM records the incident |
| `record_date` | date | date of the earliest record |
| `record_date_basis` | str | source of the record date: aiid, aiaaic, oecd, corrected |
| `record_date_precision` | str | day, month, year |
| `started` | date | when the incident started |
| `started_precision` | str | day, month, year, unknown |
| `started_bound` | str | exact, or no_later_than (the incident had started by this date) |
| `deployer_status` | str | named, described, unknown, personal_use |
| `provider_status` | str | named, described, unknown |
| `upstream_provider_status` | str | named, described, unknown |
| `subject_status` | str | named, described, no_harm, unknown |
| `subject_type` | str | AI subject type: Individual, Group of persons, Society, Organization, Nature, Other |
| `subject_who` | str | who was harmed, in the coder's words |
| `autonomy_level` | str | action autonomy: human support, human-in-the-loop, human-on-the-loop, human-out-of-the-loop, unknown |
| `harm_types` | list | OECD harm types |
| `mit_domain` | str | MIT risk domain (1–7) |
| `mit_subdomain` | str | MIT risk subdomain: the risk type |
| `impact_layer` | str | capability, human_interaction, systemic |
| `intended_purpose` | str | what the AI system is for, in the coder's words |
| `relation` | str | within_purpose, misuse, unclear |
| `misuse_by` | str | deployer, user, third_party, where the use was misuse |
| `use_capability` | str | what the AI system does, as a capability verb (Herdel et al., 2024) |
| `use_technique` | str | the AI technique, as a class of the VAIR vocabulary (Golpayegani et al., 2023) |
| `use_domains` | list | the domain of the use, one or two (Herdel et al., 2024) |
| `answers_for` | str | who answers for the incident: SEC registrant (annual report in force, or none yet), private AI company, other company not SEC-registered, public body, person (personal use), no AI actor named |
| `matched` | bool | the incident is matched |
| `where` | str | for unmatched incidents, the reason |
| `quadrant` | str | Covered, Fixed, Dropped, Missed; empty if unmatched |
| `how` | str | outcome: Reported, Revised, Retained, Added, Removed, Absent |
| `unaddressed_kind` | str | for Missed and Dropped: No disclosure, Incomplete disclosure |

### `incident_records`

| column | type | description |
|---|---|---|
| `record_id` | str | AIID incident number, AIAAIC id or OECD AIM id |
| `incident_id` | str | the incident |
| `source` | str | aiid, aiaaic, oecd |
| `url` | str | the record's page |
| `record_title` | str | the record's title |
| `record_date` | date | the record's date |
| `description` | str | AIID description, AIAAIC summary or OECD AIM summary |
| `n_articles` | int | articles linked to the record |

### `articles`

| column | type | description |
|---|---|---|
| `incident_id` | str | the incident |
| `record_id` | str | the record that links the article; empty where found by search |
| `source` | str | aiid, aiaaic, oecd, search |
| `kind` | str | report, news, legal, other, article |
| `url` | str | the article |
| `article_title` | str | headline |
| `publisher` | str | outlet, else the URL's domain |
| `published` | date | publication date, where given |
| `ref` | str | `R1`, `R2` … where the coders read the article; the target of `evidence.ref` |

### `source_labels`

The databases' own labels, kept apart from DISC's: AIID's MIT AI Incident Tracker classification,
OECD AIM's labels (generated by a language model), AIAAIC's editors' labels.

| column | type | description |
|---|---|---|
| `incident_id` | str | the incident |
| `record_id` | str | the record |
| `source` | str | aiid, oecd, aiaaic |
| `label` | str | the database's label name |
| `value` | list | the database's value or values |

### `incident_actors`

| column | type | description |
|---|---|---|
| `incident_id` | str | the incident |
| `position` | str | deployer, provider, upstream_provider |
| `status` | str | named, described, unknown, personal_use |
| `party` | str | the party, as named or described |
| `acting_as` | str | what the party did, in the coder's words |
| `actor_id` | str | the AI actor in `actors`, where resolved |
| `cik` | int | SEC CIK, where the party files with the SEC |
| `link` | str | asserted (a database names it) or coded (the coders named it) |

### `actors`

| column | type | description |
|---|---|---|
| `actor_id` | str | key |
| `name` | str | name |
| `entity_type` | str | organisation, person |
| `aliases` | list | other names it appears under |
| `cik` | int | SEC CIK, where it files with the SEC |
| `sec_name` | str | its name at the SEC |
| `regime` | str | the annual form it files: 10-K, 20-F/40-F, none |
| `eu_ai_act_roles` | list | provider or deployer, in EU AI Act terms |
| `n_incidents` | int | incidents it is named in |
| `aiid_entity_ids` | list | AIID entity ids |

### `evidence`

| column | type | description |
|---|---|---|
| `incident_id` | str | the incident |
| `label` | str | the column of `incidents` the quote supports |
| `quote` | str | the span the label rests on, at most about 30 words |
| `ref` | str | `record` (the database record) or `R1`, `R2` … (`articles.ref`) |

### `filings`

| column | type | description |
|---|---|---|
| `accession` | str | SEC accession number; key with `cik` |
| `cik` | int | SEC CIK of the filer |
| `form` | str | 10-K, 20-F, 40-F, 10-Q, 8-K, 6-K, DEF 14A |
| `filing_date` | date | filing date |
| `report_date` | date | the period the filing covers |
| `url` | str | the primary document on EDGAR |
| `items` | str | 8-K items, where reported |
| `risk_factor_words` | int | words in the risk-factor section |

### `passages`

| column | type | description |
|---|---|---|
| `passage_id` | str | key: a hash of the text |
| `cik` | int | the filer |
| `channel` | str | annual risk factors, 10-Q risk factors, legal, current report |
| `first_filed` | date | the first filing that carries the text |
| `text` | str | the passage |

### `passage_filings`

| column | type | description |
|---|---|---|
| `passage_id` | str | the passage |
| `accession` | str | a filing that carries it |
| `form` | str | the filing's form |
| `filing_date` | date | the filing's date |

### `passage_codes`

| column | type | description |
|---|---|---|
| `passage_id` | str | the passage |
| `discloses` | str | ai_harm, business_only |
| `mit_subdomains` | list | every risk type the passage names |
| `mit_primary` | str | the risk type the passage is chiefly about |
| `status` | str | hypothetical, elsewhere, materialised |
| `harm_types` | list | OECD harm types |
| `subjects` | list | `name:type` for each AI subject the passage names |
| `registrant_harmed` | bool | the passage names a harm to the AI actor itself |
| `whose_ai` | list | own, others, general |
| `impact_layers` | list | capability, human_interaction, systemic |
| `relation` | list | within_purpose, misuse, unclear |
| `misuse_by` | list | deployer, user, third_party |

### `passage_evidence`

| column | type | description |
|---|---|---|
| `passage_id` | str | the passage |
| `label` | str | the label the quote supports, e.g. `mit:7.3`, `status` |
| `quote` | str | the span of the passage |

### `outcomes`

| column | type | description |
|---|---|---|
| `incident_id` | str | the matched incident |
| `cik` | int | the implicated AI actor |
| `started_used` | date | the date the outcome is read at |
| `anticipated` | bool | the risk type was in force when the incident started |
| `anticipating_passages` | list | the passages in force that name the risk type |
| `how` | str | Reported, Revised, Retained, Added, Removed, Absent |
| `decided_by` | str | accession of the deciding filing: the responding current filing or the next periodic filing |
| `decided_on` | date | its filing date |
| `days` | int | days from when the incident started to `decided_on` |
| `current_reports` | str | read, or open (the window for current filings had not closed) |

### `responses`

| column | type | description |
|---|---|---|
| `incident_id` | str | the incident |
| `cik` | int | the AI actor |
| `accession` | str | the current filing |
| `form` | str | 8-K, 6-K |
| `filing_date` | date | filing date |
| `items` | str | 8-K items |
| `days_from_record` | int | days from the record date to the filing |
| `read` | bool | the filing names AI, the incident or an adverse event and was read |
| `responds` | bool | the filing responds to the incident |
| `quote` | str | the responding sentence |

### `reported_references`

| column | type | description |
|---|---|---|
| `incident_id` | str | the incident |
| `cik` | int | the AI actor |
| `passage_id` | str | the passage saying the risk type materialised |
| `channel` | str | risk factors, legal, current report |
| `date` | date | filing date of the passage |
| `label_a` | str | first reader: this_incident, includes, other |
| `label_b` | str | second reader, same scale |
| `reported` | date | date the passage refers to this incident |
| `reported_incl` | date | the same, counting passages that include it among others |

### `revisions`

| column | type | description |
|---|---|---|
| `unit_id` | str | the revised passage (`passages.passage_id`) |
| `replaces` | str | the earlier passage of the same risk type it replaces |
| `cik` | int | the AI actor |
| `about` | list | what the revision is about |
| `domain_of_change` | list | MIT domains the revision touches |
| `revision_types` | list | `incident_id:revision_type` for each incident the revision is read against: incident_specific, risk_type_specific, unspecific |
| `domains_before` | list | MIT domains the passage named before |
| `domains_after` | list | MIT domains it names after |

### `risk_factor_sections`

Text sections of the implicated AI actors' filings: the risk factors of annual and quarterly filings
(10-K Item 1A, 20-F Item 3.D, the 40-F's Annual Information Form, 10-Q Part II Item 1A), the business
sections of annual filings, and the AI excerpts of current filings and proxy statements.

| column | type | description |
|---|---|---|
| `accession` | str | the filing |
| `cik` | int | the filer |
| `form` | str | form |
| `filing_date` | date | filing date |
| `report_date` | date | the period the filing covers |
| `section` | str | risk_factors, business, ai_excerpt |
| `method` | str | how it was extracted |
| `words` | int | words |
| `sentences` | int | sentences |
| `url` | str | the document on EDGAR |
| `text` | str | the section |

### `mit_taxonomy`

| column | type | description |
|---|---|---|
| `code` | str | MIT subdomain code, e.g. 7.3 |
| `name` | str | subdomain name |
| `domain` | str | domain number |
| `domain_name` | str | domain name |

## Personal data

Public figures named for a public role keep their names. The names of private individuals and
minors are replaced by `[private individual]` in every incident-side text field. Email addresses and
telephone numbers are replaced by `[email]` and `[phone]` in every text field, the SEC filing texts
included. URLs remain as published, except that query parameters granting access or identifying a reader
(share and gift tokens, guest keys, session and subscriber ids) are removed.

## Licence and attribution

The data are licensed under CC BY-SA 4.0 (`LICENSE`), as AIID's and AIAAIC's records require.
Cite the sources with DISC: the AI Incident Database, with per-incident links; the AIAAIC
Repository, with a link to each page; and the OECD AI Incidents and Hazards Monitor (OECD.AI, 2026).
SEC filing text is public information from SEC EDGAR, cited by accession number and URL, and is not
relicensed. Quotes from news articles are short excerpts that remain their publishers' copyright;
article texts are not included.

The explorer ships its fonts and scripts with their licence texts (`static/fonts/`, `static/vendor/`):
IBM Plex Sans, IBM Plex Mono and Libertinus Serif under the SIL Open Font License 1.1; d3 (ISC),
jsdiff (BSD-3-Clause) and marked (MIT).

## References

- Golpayegani, D., Pandit, H. J., & Lewis, D. (2023). To be high-risk, or not to be: Semantic
  specifications and implications of the AI Act's high-risk AI applications and harmonised standards.
  *Proceedings of the 2023 ACM Conference on Fairness, Accountability, and Transparency*, 905–915.
  https://doi.org/10.1145/3593013.3594050
- Herdel, V., Šćepanović, S., Bogucka, E., & Quercia, D. (2024). ExploreGen: Large language models
  for envisioning the uses and risks of AI technologies. *Proceedings of the AAAI/ACM Conference on
  AI, Ethics, and Society*, 7, 584–596. https://doi.org/10.1609/aies.v7i1.31660
- Regulation (EU) 2024/1689 laying down harmonised rules on artificial intelligence (AI Act).
  https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- Slattery, P., Saeri, A. K., Grundy, E. A. C., Graham, J., Noetel, M., Uuk, R., Dao, J., Pour, S.,
  Casper, S., & Thompson, N. (2026). The AI risk repository: A meta-review, database, and taxonomy of
  risks from artificial intelligence. *Patterns*, 7(5), 101517. https://doi.org/10.1016/j.patter.2026.101517

## Citation

Citation and DOI to follow.
