# Codebook: disclosures

This codebook defines the labels DISC gives the filings of implicated AI actors, and how an incident
is read against them. Filings are those the AI actors filed with the SEC from 1 January 2015 to 30
September 2026.

## 1 Unit

The unit is a **passage**: a sentence that mentions AI, with the sentence before and after it,
merged where passages touch. A sentence mentions AI when it names AI or an AI system a filing names
without calling it AI, such as driver assistance and autonomous driving, facial, speech or image
recognition, biometric identification, language models and voice assistants. A passage repeated word
for word in later filings is coded once and counts in every filing that carries it.

| channel | source |
|---|---|
| annual risk factors | 10-K Item 1A, 20-F Item 3.D, the risk factors of a 40-F's Annual Information Form |
| 10-Q risk factors | 10-Q Part II Item 1A, which states material changes to the annual risk factors |
| legal | legal proceedings and litigation notes, where the passage names a legal matter |
| current report | 8-K, and a foreign private issuer's 6-K |

The risk factors are the disclosure an incident is read against; legal passages and current filings
record events.

## 2 Labels on a passage

A filing states risks, so the labels describe the harm the passage says could occur, or did. Several
values may apply, since a risk factor often lists many risks in one sentence. Every label of an
`ai_harm` passage rests on a verbatim span of the passage (table `passage_evidence`).

**Discloses.** `ai_harm` when the passage names a harm an AI system could cause or has caused, to
anyone including the AI actor. `business_only` when AI appears only as a business matter: investment,
competition, demand, talent, cost, a product description, a regulation named without the harm it
addresses, AI that may underperform with consequences for the business only, or a claim over what a
company said about its AI. All further labels are empty for `business_only`.

| label | values | rule |
|---|---|---|
| risk types | MIT subdomains | every subdomain the passage names, by the incident codebook's table; the primary one is the subdomain the passage is chiefly about |
| status | hypothetical, elsewhere, materialised | `materialised`: the harm has occurred to the AI actor or through its own AI; `elsewhere`: it has occurred to others or in general; `hypothetical`: it could occur. The strongest applies. |
| harm types | OECD harm types | the types the passage names; a privacy compromise, discrimination or surveillance is Human or fundamental rights; Economic/Property where a loss is named or systems or data are attacked |
| AI subjects | name and type | each living entity the passage says would be harmed, other than the AI actor, with its AI subject type |
| whose AI | own, others, general | the AI actor's own AI (developed, offered or used); AI in other hands; AI as a technology |
| AI actor harmed | true, false | the passage names a harm to the AI actor itself (liability, fines, lost revenue, reputational harm, a breach of its systems) beyond the closing formula on business, financial condition and results |
| impact layers | capability, human interaction, systemic | where the harm named would arise |
| relation | within_purpose, misuse, unclear | harm from the system used as offered, or from a use not in accordance with its purpose; for misuse, by the deployer, a user or a third party |

**Current filings.** An 8-K or 6-K reports events: a passage saying an AI harm occurred to the AI
actor or through its own AI is `materialised`; a forward-looking list of risks is `hypothetical`; AI
named as a product, launch, deal, investment or result, a shareholder proposal on AI, and a contract
term are `business_only`. A passage that ties AI to fewer people employed names risk type 6.2.

## 3 Response of a current filing

For an incident and each current filing of its implicated AI actors, from when the incident started (at
most 90 days before the record date) to 90 days after the record date: does the filing respond to the
incident? It responds when it reports, recognisably for this incident (the same system or product,
the same harm, at a time that fits), the incident or its harm; a consequence of it for the AI actor
(a charge, recall, suspension, wind-down, litigation, investigation or regulatory action); or a
measure taken because of it. It does not respond with routine financing, earnings, votes or
appointments, a general statement of AI risk, another matter, or a sentence that fits several
incidents equally well. A response engages the adverse side: a filing that names the system only
favourably does not respond. A current filing without a sentence naming AI, the incident or an
adverse event is not read.

## 4 An incident read against disclosure

- **Anticipated**: when the incident started, at least one implicated AI actor's annual risk factors in
  force, with any 10-Q since, carried a passage naming the incident's risk type as an AI harm.
- **Addressed**: after the next periodic filing (the next 10-Q, or the annual filing if it comes
  first), at least one implicated AI actor has the risk type in force, or a filing reports the
  incident.
- **Outcome** at the next periodic filing, the first of the implicated AI actors' outcomes in this
  order:

| outcome | anticipated | the disclosure |
|---|---|---|
| Reported | either | a current filing responds to the incident, or a passage saying the risk type materialised refers to this incident, as two readers judge |
| Revised | yes | the next filing carries a new text of the risk type |
| Retained | yes | the risk type stays in unchanged text |
| Added | no | the risk type appears after the next filing |
| Removed | yes | the risk type is no longer disclosed |
| Absent | no | it is still not disclosed |

- **Quadrant**: Covered (anticipated and addressed), Fixed (unanticipated, then addressed), Dropped
  (anticipated, then unaddressed), Missed (unanticipated and unaddressed).
- **Unaddressed kind**, for Missed and Dropped incidents: No disclosure (no AI harm in the implicated
  AI actors' risk factors when the incident started); Incomplete disclosure (AI harms disclosed, but not the
  incident's risk type).

## 5 Revisions

A revised passage replaces an earlier passage of the same risk type. Its **revision type**, for an
incident, is how the new text speaks to the incident:

| revision type | the new text |
|---|---|
| Incident-specific | names the incident's technology, product, AI actor or harm |
| Risk-type specific | adds the incident's kind of risk in general terms |
| Unspecific | says nothing on the incident's risk type, or the change is cosmetic |
