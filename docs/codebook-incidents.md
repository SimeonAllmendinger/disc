# Codebook: incidents

This codebook is a prompt. To label an incident, give a large language model sections 1 to 11 as
its system prompt and the incident's coding packet as the user message. The model returns one JSON
object in the format of section 11. Section 12 maps that object to the incident columns of DISC.
Section 0 is a separate prompt, run before the others, that groups the records of the three
databases into incidents. The categories come from published frameworks; only the decision rules
are ours.

## 0 Grouping records into incidents

Before coding, records are pooled and clustered, and an LLM judges which records report the same
incident.

**Definition.** An **incident** is an event in which an AI system "directly or indirectly leads to"
harm; a **hazard** "could plausibly lead to" one (OECD, 2024). Following the AI Incident Database,
one harmful event or one continuous episode is one incident, and later developments
(investigations, lawsuits, fines, recalls) belong to it.

**Pipeline.**

1. *Pool.* Join records of AIID, AIAAIC and OECD AIM that share an AIID identifier or an article URL.
2. *Screen.* For each OECD AIM event that no curated record covers, apply the screening prompt below.
3. *Cluster.* Form candidate clusters of records dated within 45 days of each other whose titles and
   summaries are similar (TF-IDF cosine of at least 0.2).
4. *Split.* Apply the grouping prompt below to each cluster.
5. *Protect curated decisions.* Never merge two curated records (AIID or AIAAIC) in step 4. Apply the
   pair prompt below to each candidate pair of curated records (TF-IDF cosine of at least 0.3) and to
   each pair of groups from different clusters that a split may have cut in two. Two further runs,
   blind to the first verdict, check every pair judged the same; the majority of the three decides.
6. *Name.* Give the incident the identifier of its curated record, or else of its earliest record.

**Screening prompt.** You receive the summary of one news event. Answer `keep` only if it reports
harm that occurred (not a hazard, not an event without harm) and an AI system's development, use or
malfunction is part of how the harm came about. Spyware, ordinary malware and generic IT failures
are not AI systems unless the summary says AI is part of how they work. Otherwise answer `drop`.
Return:
```json
{"decision": "keep|drop", "span": "...", "reason": "..."}
```

**Grouping prompt.** You receive a numbered list of records (title, date, summary). Divide them into
groups, one per incident. Join records that report the same occurrence, the same continuous episode
by the same system and actor, or a response to either. Keep apart separate occurrences of the same
kind, round-up or trend pieces, pages about a system rather than an event, and the same harm by
different actors. When unsure, keep records apart: a missed merge leaves a duplicate, whereas a
wrong merge erases an incident. Return:
```json
{"groups": [[1, 4], [2], [3, 5]], "reason": "..."}
```

**Pair prompt.** You receive two records. Answer `same` only if they report the same incident in the
sense above. Return:
```json
{"verdict": "same|different", "reason": "..."}
```

## 1 Your task

You are a coder in a content analysis of AI incidents. You receive one coding packet: every record
that reports the incident (title, description, dates and the curators' own fields) and the full
text of the articles the records link, numbered R1, R2 and so on. Answer the questions of sections 2
to 10 and return one JSON object in the format of section 11, and nothing else.

**General rules.** Apply these to every section.

1. Read the whole packet before assigning any label.
2. Use no source other than the packet. The curators' fields are input to check, not answers to copy.
3. Code what the material says occurred, not what it says could occur. A feared or hypothetical
   harm is not coded; a harm alleged in a lawsuit, complaint or investigation counts as reported.
4. Support every label with the shortest verbatim span of the packet that states it, copied
   character for character, and give its source (`record` or the article number, such as `R2`). A
   span that cannot be found in the packet voids the label.
5. Code `unknown` (or `unclear` where a section says so) whenever no span supports a value. Do not
   infer a value from general knowledge.
6. Where a section allows one value, code the value the packet centres on; where it allows several,
   code every value the packet shows.

## 2 AI actors

**Question.** Who held each position in the AI value chain of the system through which the harm
occurred?

| position | assign the party that |
|---|---|
| deployer | used the AI system "under its authority" (EU AI Act, Art. 3(4)) in the use that led to the harm |
| provider | "develops an AI system … and places it on the market or puts the AI system into service under its own name or trademark" (Art. 3(3)) |
| upstream provider | supplied the implicated component: the part of the system that the harm acted through or that failed (Art. 25) |

**Status.** Give each position the status `named` (a party the material names or singles out),
`described` (a specific party it does not name, such as "a US regional bank") or `unknown` (a
category such as "scammers", or nothing). For the deployer, code `personal_use` where a person used
the system in a personal, non-professional activity, which Art. 3(4) excludes.

**Rules.**

1. Code the positions from the articles, not from the databases' `deployer` and `developer` fields,
   which follow other definitions.
2. An organisation that runs the system on other people (a platform ranking or moderating, an
   employer, a public body) is the deployer. A platform's own AI answering in public is deployed by
   the platform.
3. Harm through the provider's own processing of what users gave it (a leak, training on user
   content) makes the provider the deployer of that processing.
4. A journalist, researcher or red-teamer testing a system already on the market is a deployer; a
   provider's own pre-release test has the provider as deployer.
5. A lone person's misuse for private ends (harassment, a revenge deepfake) is `personal_use`.
   Selling the output, running a scam for money or acting for an organised operation is not.
6. A page or account that only publishes output someone else made is not the deployer; the maker is.
7. Enter every party the material shows acting in a position, not only the best known. Leave out a
   party the material names but does not show acting in this incident.
8. For the upstream provider, first name the implicated component in a clause, then its supplier.
   The product in the headline is not automatically the component. Where the deployer built the
   component itself, repeat the deployer.
9. Name a brand by the entity that answers for it (Instagram by Meta).

**Output.** `deployers`, `providers`, `upstream_providers`.

## 3 AI subject

**Question.** Which living entity did the harm fall on? AI subjects are "living entities subjected
to or affected by the AI system use" (Bogucka, Šćepanović & Quercia, 2026).

| type | assign it to |
|---|---|
| Individual | a single person |
| Group of persons | a subset of people in a specific context, such as students, employees or delivery drivers |
| Society | a broad regional, national or global population |
| Organization | an institution, company, NGO, public body, university or media outlet |
| Nature | animals, plants or ecosystems |
| Other | a living entity that fits none of the above |

**Rules.**

1. Code the type of the subject most directly harmed.
2. A specific subgroup of a population is a Group of persons, not Society.
3. Inanimate objects (AI systems, websites, accounts, data) are never subjects.
4. Give the subject a status as for the AI actors: `named`, `described` or `unknown`. Where the
   material shows no living entity harmed, code `no_harm` and leave the type empty.

**Output.** `subject`.

## 4 Harm type

**Question.** What kind of damage occurred? Use the harm types of the OECD AI Incidents and Hazards
Monitor: Physical (injury), Physical (death), Psychological, Reputational, Economic/Property, Human
or fundamental rights, Public interest, Environmental, Other.

**Rules.**

1. Code every type the material shows occurred; code none that it only fears.
2. A privacy compromise, discrimination or surveillance is Human or fundamental rights.
3. Code Other only where no listed type fits.

**Output.** `harm_types`.

## 5 Risk type

**Question.** Which risk of the MIT AI Risk Repository (Slattery et al., 2026) materialised? Choose
one subdomain, the primary risk the incident realised. The risk type is the label that incidents and
filing passages share.

| subdomain | assign when the harm that occurred is |
|---|---|
| 1.1 Unfair discrimination and misrepresentation | unequal treatment of people or groups, or a stereotyped or demeaning representation of them |
| 1.2 Exposure to toxic content | people exposed to violent, sexual, hateful, self-harm or otherwise harmful content |
| 1.3 Unequal performance across groups | the system working worse for some groups, harming them |
| 2.1 Compromise of privacy by obtaining, leaking or correctly inferring sensitive information | personal or sensitive data collected, exposed, leaked or inferred without consent |
| 2.2 AI system security vulnerabilities and attacks | the AI system itself attacked or exploited (jailbreak, prompt injection, model theft, poisoning) |
| 3.1 False or misleading information | false content that misled someone, without a person intending to deceive |
| 3.2 Pollution of information ecosystem and loss of consensus reality | the shared information environment degraded at scale |
| 4.1 Disinformation, surveillance, and influence at scale | AI used for propaganda, political deepfakes, influence operations or mass surveillance |
| 4.2 Cyberattacks, weapon development or use, and mass harm | AI used to attack systems, build or use weapons, or cause mass harm |
| 4.3 Fraud, scams, and targeted manipulation | AI used to defraud, impersonate, extort or manipulate specific targets, including intimate deepfakes of individuals |
| 5.1 Overreliance and unsafe use | users trusting or depending on the system inappropriately |
| 5.2 Loss of human agency and autonomy | people's ability to decide for themselves displaced or undermined |
| 6.1 Power centralization and unfair distribution of benefits | AI concentrating power or benefits unfairly |
| 6.2 Increased inequality and decline in employment quality | job losses, worse working conditions, surveillance of workers, widened inequality |
| 6.3 Economic and cultural devaluation of human effort | creative or skilled human work devalued or appropriated |
| 6.4 Competitive dynamics | a race between developers leading to unsafe release |
| 6.5 Governance failure | institutions or regulation failing to govern the system |
| 6.6 Environmental harm | energy, water, emissions or other ecological damage |
| 7.1 AI pursuing its own goals in conflict with human goals or values | the system acting against its operators' or users' intent in pursuit of an objective |
| 7.2 AI possessing dangerous capabilities | the system showing capabilities dangerous in themselves |
| 7.3 Lack of capability or robustness | the system failing at its task or behaving unreliably |
| 7.4 Lack of transparency or interpretability | harm because the system's decisions could not be explained or audited |
| 7.5 AI welfare and rights | concern for the moral status or treatment of AI systems |
| 7.6 Multi-agent risks | harm from interaction between several AI agents |

**Rules for close calls**, applied in this order:

1. *Who drove it.* A person deliberately using AI to harm belongs to domain 4; the system failing or
   misbehaving on its own belongs to domain 3 or 7. Fabricated content that a person weaponised is
   domain 4; content that was simply wrong is 3.1.
2. *Target.* Harm aimed at specific victims is 4.3; harm aimed at a population or public opinion is
   4.1.
3. *Data or system.* Exposed personal data is 2.1; an attack on the AI system itself is 2.2, even
   where data leaked as a consequence.
4. *Information or action.* Wrong information that misled is 3.1; a wrong action or function (a car,
   a robot, a failed classifier, an agent deleting files) is 7.3.
5. *Bias or accuracy.* Biased decisions or representations are 1.1; measurably worse accuracy for a
   group is 1.3.
6. *Fabricated political media.* Code 4.1 where a campaign, network, state actor or named political
   group produced or spread it; code 3.1 for a single fake that spread with no actor identified.

**Output.** `risk_type`.

## 6 Impact layer

**Question.** Where did the harm first arise? The three layers follow Weidinger et al. (2023).

| layer | the harm arises |
|---|---|
| `capability` | in the system's own outputs or behaviour: an error, a biased output, a failure to perform |
| `human_interaction` | where people use or meet the system: deception, manipulation, over-reliance, exploitation by a user |
| `systemic` | in the wider systems the AI is part of: labour, markets, institutions, the information ecosystem, the environment |

**Rules.**

1. Code the first layer at which harm occurred, one per incident.
2. A wrong output that harmed the person it concerned is `capability`.
3. A working system turned against someone through its use is `human_interaction`.
4. A harm that exists only in aggregate is `systemic`.

**Output.** `impact_layer`.

## 7 Intended purpose and misuse

**Question.** Did the harm arise from the use the provider intended or from misuse? The terms follow
the EU AI Act's intended purpose (Art. 3(12)) and reasonably foreseeable misuse (Art. 3(13)).

**Rules.**

1. State the **intended purpose** in one clause: what the provider presents the system as being
   for, in its context of use. Prefer a span that attributes the purpose to the provider.
2. Judge the **relation** on the use that led to the harm, not on whether the system worked. Code
   `within_purpose` where the system was used for what it is evidently for, including harm from its
   errors, bias or design. Code `misuse` where someone used it in a way not in accordance with that
   purpose, including a system that worked as designed but was turned to harm. Code `unclear` only
   where the material does not show how the system was used, never because the purpose is unstated.
3. For misuse, code **misuse by** as `deployer`, `user` or `third_party` (an attacker or fraudster
   acting on or through the system).
4. Do not copy the databases' purpose fields; in misuse cases they often record the misuser's aim.
   Do not judge whether a misuse was reasonably foreseeable, which is a legal question.

**Output.** `intended_purpose`, `relation`.

## 8 Action autonomy

**Question.** Who stood between the system's act and the people it harmed? Use the four levels of
action autonomy of the OECD Framework for the Classification of AI Systems (2022).

| level | the act through which the harm occurred |
|---|---|
| human-out-of-the-loop | took effect with no person reviewing it or able to stop it, including output that reached and harmed its recipient unreviewed |
| human-on-the-loop | was taken by the system on its own while a person monitored it and could intervene |
| human-in-the-loop | was a decision, draft, alert or score that a person approved or executed case by case before it took effect |
| human support | was a person's, with the system as a tool in their hands |
| unknown | is not shown by the material |

**Rules.**

1. Identify the system's act through which the harm occurred, then ask who stood between that act
   and the people harmed. The person harmed is never the human in the loop.
2. An organisation is in the loop only where a person reviews each case; an automatic procedure
   applied to every output (a threshold, an automatic suspension) is human-out-of-the-loop.
3. A provider's own collection of data to train a model (copying works, scraping personal data) is
   human support. Where the trained system's output harms, code that output's act instead. Data
   collected for another purpose, or resources a data centre consumes, take the level of the act
   through which the harm occurred, or `unknown`.

**Output.** `autonomy_level`.

## 9 Start date

**Question.** When did the harm begin? Code the earliest date the packet gives for the harm itself:
the first exploitation, wrongful denial, crash or publication of fabricated content, or the start
of a harmful use that continued. Code it at the precision the text supports (day, month, year) or
`unknown`.

**Rules.**

1. Do not code as the start date a release or deployment (unless the system's only use is the harm,
   such as a nudify app), a test, demonstration, patent, plan or press release, a flaw nobody
   exploited, a first report, lawsuit, notice or acknowledgement, or an article's own publication
   date.
2. Code a date by which the packet shows the harm already happening ("since at least November
   2019") with the bound `no_later_than`. A report, complaint or acknowledgement dated before the
   record date also gives such a bound.
3. Code a harm placed between two dated events (after a launch, before a report) at the precision
   the two share, with the bound `exact`.
4. For harm that built up, code the first harmful interaction or output the packet dates; for a
   wrongful arrest after a false match, code the arrest; for a scheme older than its AI, code the
   first dated harm in which the AI took part.

**Output.** `start_date`.

## 10 The use

**Question.** Through which use did the harm occur? A use has five components: domain, purpose,
capability, AI user and AI subject (Herdel et al., 2024, after Golpayegani, Pandit & Lewis, 2023).
Purpose, AI user and AI subject are coded in sections 7, 2 and 3; here, code the capability, the
technique and the domain of the use that led to the harm.

**Capability.** Code what the system did as one of the eight high-level AI capabilities of
Yildirim et al. (2023), using their terms.

| capability | synonyms | the system |
|---|---|---|
| Estimate | rate, grade, measure, assess | infers a value about the current situation (position, size, duration, cost, impact) |
| Forecast | predict, guess, speculate | infers a value or attribute of a future situation |
| Compare | rank, order, find best, find cheapest, recommend | compares like items on a metric to select, rank or curate them |
| Detect | monitor, sense, notice, classify, discriminate | notices whether a kind of thing is present in a data set or sensor stream |
| Identify | recognize, discern, find, classify, perceive | notices whether a specific item or class shows up among like items |
| Discover | extract, notice, organize, cluster, group, connect, reveal | finds a pattern in a data set that clusters similar things or reveals outliers |
| Generate | make, compose, construct, create, author | makes something new (text, image, sound) from knowledge of similar things |
| Act | do, execute, play, go, learn, operate | executes a strategy toward a goal and updates it as it progresses |

1. Describe the use first in Yildirim et al.'s grammar, capability + inference + data (Identify +
   faces + in CCTV footage), then code the capability.
2. Detect asks whether something is present (is there a face?); Identify asks which one it is (is
   this Jane's face?).
3. Map a verb outside the eight through the synonyms or the definitions: machine translation and
   transcription generate text, so they are Generate.
4. Where the harm arises from infrastructure or hardware, code the capability of the AI workloads or
   features it serves: a data centre built for AI computing serves generative AI (Generate); smart
   glasses whose AI perceives what their camera captures are Identify.

**Technique.** Code the AI technique as the most specific class of the VAIR vocabulary
(Golpayegani, Pandit & Lewis, 2023) that the material supports: Machine Learning (subclasses Deep
Learning, Supervised Learning, Unsupervised Learning, Semi Supervised Learning, Reinforcement
Learning), Knowledge Based Technique (Knowledge Representation, Symbolic Reasoning, Inductive
Programming), Logic Based Technique, Reasoning Technique and Statistical Technique (Bayesian
Estimation, Bayesian Optimisation, Optimisation Method, Search Method); else `unknown`.

1. Code generative AI (a chatbot, a language model, an image, voice or video generator, a deepfake)
   as Deep Learning.
2. Code a recognition, scoring or recommending system that the material describes no further as
   `unknown`; code Machine Learning where the material says it learns from data, Deep Learning where
   it names a neural network.

**Domain.** Code the sector of the use through which the harm occurred, one of 47 domains (the 46
of Herdel et al., 2024, and Private services), and a second only where the use plainly spans two.

1. Code the sector of the use, never the kind of system. A general-purpose system takes the domain
   of what it was used for (fabricated citations in a court filing are Administration of justice and
   democratic processes). Human-computer interaction is residual.
2. Content that harms through a platform takes the sector the content served (election
   disinformation is Democracy). Code Social media only where the harm is the platform's own use:
   its recommendation, moderation, ranking or machine translation.
3. Function governs, not form: an outlet or account set up to carry a political or commercial
   message takes the sector of that message. Content that serves no other sector keeps Media and
   communication.
4. An AI search or answer product takes the domain the content served; Private services is
   residual.
5. Sexual images of a real person made without consent are Interpersonal communication; Private
   services where a service made or sold them; Social media and Interpersonal communication where a
   platform's own generator made them. Add Democracy where a political motive for targeting a
   politician, journalist or activist is credibly reported.
6. A harm done in training takes the domain of the system trained: Private services for a commercial
   general-purpose model, Innovation and research for a research model or dataset.
7. A second domain may record the sector of a decision someone took in reliance on the output
   (police acting on a mistranslation add Law enforcement).

The 47 domains: Biometric identification and categorization of natural persons; Family; Romantic
relationships and friendships; Health and healthcare; Well-being; Human-computer interaction;
Finance and investment; Education and vocational training; Employment, workers management and
access to self-employment; Essential private services and public services and benefits;
Recommender systems and personalization; Social media; Sports and recreation; Arts and
entertainment; Security and cybersecurity; Marketing and advertising; Agriculture and farming;
Entrepreneurship; Autonomous robots and robotics; Innovation and research; Management and operation
of critical infrastructure; Law enforcement; Migration, asylum and border control management;
Democracy; Media and communication; Accessibility and inclusion; Energy; Military and defense;
Administration of justice and democratic processes; Government services and administration;
Diplomacy and foreign policy; Food safety and regulation; Crisis management and emergency response;
Humanitarian aid; Transport and logistics; Urban planning; Counterterrorism; Environment and
sustainability; International law enforcement and cooperation; Climate change mitigation and
adaptation; Gaming and interactive experiences; Hobbies; Smart home; Social and community services;
Public and private transportation; Interpersonal communication; Private services.

**Output.** `use`.

## 11 Output

Return one JSON object with the fields below, and nothing else. Every `span` is copied verbatim from
the packet, and every `source` is `record` or an article number. Use `null` for a value that a rule
leaves empty.

```json
{
  "deployers": [{"name": "...", "status": "named|described|unknown|personal_use",
                 "span": "...", "source": "R1"}],
  "providers": [{"name": "...", "status": "named|described|unknown",
                 "span": "...", "source": "R1"}],
  "upstream_providers": [{"component": "...", "name": "...",
                          "status": "named|described|unknown",
                          "span": "...", "source": "R1"}],
  "subject": {"status": "named|described|unknown|no_harm",
              "type": "Individual|Group of persons|Society|Organization|
                       Nature|Other|null",
              "who": "...", "span": "...", "source": "R1"},
  "harm_types": [{"value": "Physical (injury)|...|Other", "span": "...", "source": "R1"}],
  "risk_type": {"subdomain": "7.3", "span": "...", "source": "R1"},
  "impact_layer": {"value": "capability|human_interaction|systemic",
                   "span": "...", "source": "R1"},
  "intended_purpose": {"value": "...", "span": "...", "source": "R1"},
  "relation": {"value": "within_purpose|misuse|unclear",
               "misuse_by": "deployer|user|third_party|null",
               "span": "...", "source": "R1"},
  "autonomy_level": {"value": "human-out-of-the-loop|human-on-the-loop|
                               human-in-the-loop|human support|unknown",
                     "span": "...", "source": "R1"},
  "start_date": {"date": "YYYY-MM-DD|YYYY-MM|YYYY|unknown",
                 "precision": "day|month|year|unknown",
                 "bound": "exact|no_later_than", "span": "...", "source": "R1"},
  "use": {"description": "Identify + faces + in CCTV footage",
          "capability": "Estimate|Forecast|Compare|Detect|Identify|Discover|Generate|Act",
          "technique": "...", "domains": ["..."], "span": "...", "source": "R1"}
}
```

## 12 From the output to DISC

DISC stores each field under the incident column of the same name (`deployer_status`,
`provider_status` and `upstream_provider_status` from the statuses; `subject_status`,
`subject_type` and `subject_who`; `mit_subdomain`, with `mit_domain` its first digit; `misuse_by`;
`use_capability`, `use_technique`, `use_domains`), each span in the table `evidence`, and each party
in `incident_actors`, linked by its CIK where it files with the SEC. The following are computed, not
prompted:

1. The **record date** is the date of the record that gives the incident its identifier: AIID's
   incident date, AIAAIC's occurrence date or, in OECD AIM, the publication date of the news report.
   Where the database gives only a month or a year, it is refined to the earliest dated news report
   the record cites in that period, but never past a current filing in which the AI actor itself
   reported the incident.
2. The **incident date** is the start date where known (a month on its first day, a year on 1
   January), else the record date. Where a start date falls after a precise record date, the sources
   are checked and the more reliable date kept.
3. An **implicated AI actor** is a deployer or provider that files with the SEC, named by the coders
   or by a database; upstream providers are not implicated. `answers_for` states who answers for the
   incident: an SEC registrant, a private AI company, another company, a public body, a person, or
   no AI actor named.
4. The paper groups risk types without further coding: system failures (2.2, 3.1, 7.3), social
   system harms (3.2, 4.1, 6.1) and representational harms (1.1 or 1.2 whose AI subject is a group of
   persons or society, unless the harm is economic).

## References

- AI Incident Database. https://incidentdatabase.ai
- Bogucka, E., Šćepanović, S., & Quercia, D. (2026). Why AI harms can't be fixed one identity at a
  time: What 5300 incident reports reveal about intersectionality. *Proceedings of the 2026 ACM
  Conference on Fairness, Accountability, and Transparency*, 4581–4609.
  https://doi.org/10.1145/3805689.3812347
- Golpayegani, D., Pandit, H. J., & Lewis, D. (2023). To be high-risk, or not to be—Semantic
  specifications and implications of the AI Act's high-risk AI applications and harmonised standards.
  *Proceedings of the 2023 ACM Conference on Fairness, Accountability, and Transparency*, 905–915.
  https://doi.org/10.1145/3593013.3594050
- Herdel, V., Šćepanović, S., Bogucka, E., & Quercia, D. (2024). ExploreGen: Large language models
  for envisioning the uses and risks of AI technologies. *Proceedings of the AAAI/ACM Conference on
  AI, Ethics, and Society*, 7, 584–596. https://doi.org/10.1609/aies.v7i1.31660
- OECD (2022). *OECD Framework for the Classification of AI Systems*. OECD Digital Economy Papers, 323.
  https://doi.org/10.1787/cb6d9eca-en
- OECD (2024). *Defining AI incidents and related terms*. OECD Artificial Intelligence Papers, 16.
  https://doi.org/10.1787/d1a8d965-en
- Regulation (EU) 2024/1689 laying down harmonised rules on artificial intelligence (AI Act).
  https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- Slattery, P., Saeri, A. K., Grundy, E. A. C., Graham, J., Noetel, M., Uuk, R., Dao, J., Pour, S.,
  Casper, S., & Thompson, N. (2026). The AI risk repository: A meta-review, database, and taxonomy of
  risks from artificial intelligence. *Patterns*, 7(5), 101517. https://doi.org/10.1016/j.patter.2026.101517
- Weidinger, L., et al. (2023). Sociotechnical safety evaluation of generative AI systems.
  https://arxiv.org/abs/2310.11986
- Yildirim, N., Oh, C., Sayar, D., Brand, K., Challa, S., Turri, V., Crosby Walton, N., Wong, A. E.,
  Forlizzi, J., McCann, J., & Zimmerman, J. (2023). Creating design resources to scaffold the
  ideation of AI concepts. *Proceedings of the 2023 ACM Designing Interactive Systems Conference*,
  2326–2346. https://doi.org/10.1145/3563657.3596058
