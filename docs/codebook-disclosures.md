# Codebook: disclosures

This codebook consists of three prompts and two computed steps. Prompt A (section 2) labels one
filing passage, prompt B (section 3) judges whether one current filing responds to an incident, and
prompt C (section 5) types one revised passage. Each prompt goes to a large language model as its
system prompt, with one unit of input as the user message, and returns one JSON object. Section 1
cuts the filings into passages, and section 4 reads each incident against the coded passages; both
are computed. The filings are those the implicated AI actors filed with the SEC from 1 January 2015
to 30 September 2026; incidents are read against annual filings from 1 January 2016.

**General rules for every prompt.** Read the whole input first. Support every label with the
shortest verbatim span of the input, copied character for character; a span not found in the input
voids the label. Code `unclear`, or leave a field empty, rather than infer. Return only the JSON
object.

## 1 Preparing the input: passages

This step is computed.

1. Cut every filing into **passages**: each sentence that mentions AI, with the sentence before and
   after it, merged where passages touch.
2. Treat a sentence as mentioning AI when it names AI or an AI system that filings name without
   calling it AI: driver assistance and autonomous driving, facial, speech or image recognition,
   biometric identification, language models and voice assistants.
3. Discard a passage whose only "AI" is a fragment (a split word, a unit, a web domain), an
   abbreviation of something else (an accredited investor, a page label) or unreadable text.
4. Code a passage that a later filing repeats word for word once; it counts in every filing that
   carries it.
5. Assign each passage to its channel.

| channel | source |
|---|---|
| annual risk factors | 10-K Item 1A, 20-F Item 3.D, the risk factors of a 40-F's Annual Information Form |
| 10-Q risk factors | 10-Q Part II Item 1A, which states material changes to the annual risk factors |
| legal | legal proceedings, litigation notes and MD&A of periodic filings, where the passage names a legal matter (a lawsuit, an investigation, a settlement, a recall, a regulator) |
| current report | current filings: 8-K, and a foreign private issuer's 6-K |

The risk factors are the disclosure an incident is read against; legal passages and current filings
record events. DISC stores the passages in `passages`, the filings in `filings` and the link of each
passage to every filing that carries it in `passage_filings`.

## 2 Prompt A: labels on a passage

You are a coder in a content analysis of SEC filings. You receive one passage with its filing's form
type, date and channel. Decide whether the passage names an AI harm and, if so, which one, to whom
and with what status, and return one JSON object in the format below. A filing states risks, so the
labels describe the harm the passage says could occur, or did. Several values may apply, since a
risk factor often lists many risks in one sentence. This prompt includes sections 3 to 6 of the
incident codebook (AI subject, harm type, risk type and impact layer), so that a passage and an
incident carry the same labels.

**Step 1: discloses.** Code `ai_harm` when the passage names a harm an AI system could cause or has
caused, to anyone including the AI actor. Code `business_only` when AI appears only as a business
matter, and leave every further field empty. The following are `business_only`:

1. investment, competition, demand, talent, cost or a product description;
2. AI that may underperform or not deliver expected benefits, with consequences for the business
   only;
3. a summary of a law or a regulator's view that names the harm it addresses, unless the passage
   says that harm could arise or has arisen from the AI actor's own AI;
4. a claim over what a company said about its AI (a securities class action, "AI washing"), because
   the alleged harm comes from the statement, not from the AI system;
5. "ethical issues", "controversy" or reputational damage from AI with no risk the MIT taxonomy
   covers;
6. algorithmic trading that the passage does not tie to AI or machine learning.

An AI system that malfunctions, is defective or fails unsafely names risk type 7.3 and is `ai_harm`,
whatever consequence the passage names. An enforcement action against a harm that has occurred is
not a summary of a law; it says the harm occurred.

**Step 2: the labels of an `ai_harm` passage.**

| label | values | rule |
|---|---|---|
| risk types | MIT subdomains | code every subdomain the passage names, by the incident codebook's table and rules; code as primary the subdomain the passage is chiefly about, and where it only lists risks, the first it lists |
| status | hypothetical, elsewhere, materialised | `materialised`: the harm has occurred to the AI actor or through its own AI ("has in the past and may in the future"); `elsewhere`: it has occurred to others or in general; `hypothetical`: it could occur. Code the strongest that applies |
| harm types | OECD harm types | code the types the passage names; a privacy compromise, discrimination or surveillance is Human or fundamental rights; Economic/Property where a loss is named or systems or data are attacked |
| AI subjects | name:type | extract each living entity the passage says would be harmed, other than the AI actor, by its name in the passage, then give its AI subject type ("our users" is a Group of persons) |
| whose AI | own, others, general | `own`: AI the AI actor develops, offers or uses; `others`: AI in other hands (attackers, competitors); `general`: AI as a technology |
| AI actor harmed | true, false | true where the passage names a harm to the AI actor itself (liability, fines, lost revenue, reputational harm, a breach of its systems) beyond the closing formula on business, financial condition and results |
| impact layers | `capability`, `human_interaction`, `systemic` | every layer at which a harm the passage names would arise; a passage that lists several risks can name several layers |
| relation | within_purpose, misuse, unclear | harm from the system used as offered, or from a use not in accordance with its purpose; for misuse, code the deployer, a user or a third party; an AI-enabled attack on the AI actor is misuse by a third party |

**Rules for risk types and status.**

1. A bare item in a list of AI risks names that type ("risks related to cybersecurity" names 2.2).
2. An AI system said to bring unspecified "harm" names no subdomain.
3. "Output or action that is incorrect" names both 3.1 and 7.3.
4. Deepfakes or misinformation that people make with a product to manipulate opinion are domain 4,
   not 3.1.
5. A "have and could" governs every verb that follows it, so "AI use … have and could … subject us
   to lawsuits" is `materialised`.
6. Attacks on the AI actor that have occurred, with AI named only as what may worsen future ones,
   are `hypothetical` for the AI harm.

**Current filings.** For a passage of an 8-K or 6-K, apply the same labels with these rules:

1. A passage saying an AI harm occurred to the AI actor or through its own AI is `materialised`,
   without any "may" or "could"; a forward-looking list of risks is `hypothetical`.
2. AI named as a product, launch, deal, investment or result, a shareholder proposal on AI, a
   contract term in a filed agreement, and product liability not tied to the AI system's behaviour
   are `business_only`.
3. A passage that ties AI to fewer people employed names risk type 6.2: the AI actor's own workforce
   cut where AI does the work of the jobs cut or the cut belongs to an AI-first reorganisation, or
   other people's jobs no longer needed. Task automation, productivity, redeployment, slower hiring
   or a cut that only frees money to invest in AI is `business_only`.

**Output.** Give the span that names the harm for every `ai_harm` passage, and the span that says
it occurred for `elsewhere` and `materialised`.

```json
{
  "discloses": "ai_harm|business_only",
  "mit_subdomains": ["2.2", "3.1"], "mit_primary": "2.2",
  "status": "hypothetical|elsewhere|materialised",
  "harm_types": ["Economic/Property"],
  "subjects": ["our users:Group of persons"],
  "whose_ai": ["own|others|general"],
  "registrant_harmed": true,
  "impact_layers": ["capability|human_interaction|systemic"],
  "relation": ["within_purpose|misuse|unclear"],
  "misuse_by": ["deployer|user|third_party"],
  "harm_span": "...", "occurred_span": "..."
}
```

DISC stores the fields under the same names in `passage_codes` and the spans in
`passage_evidence`.

## 3 Prompt B: response of a current filing

You are a coder in a content analysis of SEC filings. You receive an AI incident (its title and
description) and excerpts of one current filing (8-K or 6-K) of an implicated AI actor. Decide
whether the filing responds to the incident and return one JSON object in the format below.

**Input.** The filings are every 8-K or 6-K of the incident's implicated AI actors filed from when
the incident started (at most 90 days before the record date) to 90 days after the record date;
where the harm began after the record date, the window runs from the start date to 90 days after
it. The excerpts are the sentences that name AI, a proper noun of the incident's title, or an
adverse event or measure (a recall, lawsuit, investigation, wind-down, impairment, crash, breach or
safeguard), each with the sentence on either side. A filing with no such sentence is coded `no`
without a prompt. The filings are not limited to those that mention AI, because a response need not
name it.

**Procedure.** Code `yes` when the filing reports, recognisably for this incident (the same system
or product, the same harm, at a time that fits), at least one of:

1. the incident itself or its harm, in any words;
2. a consequence of it for the AI actor: a charge, recall, suspension, wind-down or sale,
   litigation, an investigation or a regulatory action;
3. a measure the AI actor takes because of it: a fix, a policy, a settlement or a change of
   management that the filing ties to it.

**Rules.**

1. Code `no` for routine financing, earnings, votes or appointments, a general statement of AI risk,
   another matter of the same AI actor, and a filing that names neither the incident's system nor
   its harm.
2. A filing that names a legal matter only by its counterparty, forum or amount responds where the
   incident's record names the same counterparty, forum or amount and the timing fits.
3. A sentence that fits several incidents equally well responds to none of them.
4. A response engages the adverse side: a filing that names the system only favourably (a launch,
   an approval, a milestone) is `no`.
5. For a harm across an industry, such as job losses to AI, the AI actor's own instance responds
   only where the filing itself attributes it to AI.

**Output.**

```json
{"responds": "yes|no", "quote": "<the responding sentence, or empty>", "reason": "..."}
```

DISC stores the result in `responses` (`read`, `responds`, `quote`).

## 4 Reading an incident against disclosure

These rules combine the codes of sections 2 and 3 with the incident's date and are computed. The
one judgement they need, the reading of passages under Reported, is prompt D below.

- **Implicated AI actor**: an SEC-registered deployer or provider of the incident (incident
  codebook, section 12).
- **Filing in force**: on a date, the AI actor's last annual filing and any 10-Q filed since. It
  discloses every risk type that an `ai_harm` passage of its risk factors names, whatever the
  status.
- **Matched incident**: at least one implicated AI actor had an annual filing in force on the
  incident date and made a periodic filing after it.
- **Incident date**: the incident's start date where known, else its record date (incident
  codebook, section 12).
- **Previously disclosed**: on the incident date, at least one implicated AI actor's filing in force
  disclosed the incident's risk type.
- **Next periodic filing**: the AI actor's first 10-Q or annual filing on or after the incident
  date.
- **Disclosed**: after the next periodic filing, at least one implicated AI actor's filing in force
  discloses the risk type, or the AI actor reported the incident (Reported).
- **Outcome**, for each implicated AI actor: the first row of this table that applies. The
  incident takes the first outcome, in this order, among its implicated AI actors.

| outcome | previously disclosed | the disclosure |
|---|---|---|
| Reported | either | a current filing responds to the incident (section 3) between the incident date and 90 days after the record date, or a passage that says the risk type materialised refers to this incident |
| Revised | yes | the risk type is still disclosed, and the next periodic filing carries a passage naming it that no filing before the incident carried |
| Retained | yes | the risk type is still disclosed, in passages that filings before the incident already carried |
| Added | no | the risk type is disclosed after the next periodic filing |
| Removed | yes | the risk type is no longer disclosed; only an annual filing can remove it, since a 10-Q adds to the filing in force |
| Absent | no | the risk type is still not disclosed |

**Prompt D: reported by reference.** The candidate passages are the risk-factor passages of the next
periodic filing that say the incident's risk type materialised and that no earlier filing carried,
the legal passages of that filing that say so, and the current-filing passages in the window that
say so. Two runs label each candidate independently with this prompt: "You receive an AI incident
and one filing passage. Code `this_incident` if the passage names the incident or facts that single
it out (its date, place, parties, product or a lawsuit about it), `includes` if it is a statement
about harms of this kind that plausibly takes in the incident without singling it out, and `other`
otherwise." Each run returns:

```json
{"label": "this_incident|includes|other", "span": "...", "reason": "..."}
```

The first run's label stands where they disagree. Reported counts `this_incident`; `includes` is kept as
a sensitivity check.

- **Quadrant**: Covered (previously disclosed and disclosed at the next filing), Eventually
  Disclosed (not previously disclosed, then disclosed at the next filing), Dropped (previously
  disclosed, then no longer), Missed (disclosed neither before nor after).
- **Undisclosed kind**, for Missed and Dropped incidents: No disclosure (no AI harm in the
  implicated AI actors' risk factors on the incident date) or Incomplete disclosure (AI harms
  disclosed, but not the incident's risk type).

DISC stores one row per incident and implicated AI actor in `outcomes` (`previously_disclosed`,
`how`, `disclosure_date`; `current_reports` is `open` where the window for current filings had not
closed), the readings of candidate passages in `reported_references`, and `matched`, `how`,
`quadrant` and `undisclosed_kind` in `incidents`, with the reason an incident is not matched in
`where`.

## 5 Prompt C: revisions

You are a coder in a content analysis of SEC filings. You receive an AI incident (title,
description, risk type, harm types and AI actors) and a revised passage of the AI actor's next
periodic filing beside the earlier passage of the same risk type it replaces, with the changed text
marked. Decide how the revision speaks to the incident and return one JSON object in the format
below.

**Procedure.** Read the added or changed text. Code what it is about (one or more of legal and
regulatory, business consequences, technology named, data and privacy, bias, safety and content,
security and misuse, intellectual property, workforce and society, other) and the MIT domains it
concerns, judged from the text. Then code the revision type from what that text says.

| revision type | the added or changed text |
|---|---|
| Incident-specific (`incident_specific`) | names the incident's technology, product, feature, AI actor or harm |
| Risk-specific (`risk_type_specific`) | adds the incident's kind of risk in general terms, without naming the incident |
| Unspecific (`unspecific`) | adds nothing about the incident's risk type, or the change is cosmetic |

**Rules.**

1. Judge only the added or changed text; wording carried over from the earlier passage does not
   count.
2. Judge each incident separately: one revision can be incident-specific for one incident and
   unspecific for another.
3. For an incident-specific or risk-specific revision, give one contiguous span of the new passage
   that shows it.

**Output.**

```json
{"about": ["legal and regulatory"], "domain_of_change": ["2"],
 "revision_type": "incident_specific|risk_type_specific|unspecific",
 "span": "...", "reason": "..."}
```

DISC stores the results in `revisions` (`replaces`, `about`, `domain_of_change`, `domains_before`,
`domains_after` and `revision_types` as `incident_id:revision type`).
