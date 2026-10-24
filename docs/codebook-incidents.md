# Codebook: incidents

This codebook defines the labels DISC gives each incident. The unit is the incident: one real-world
harm involving an AI system, merged from the records of the AI Incident Database, the AIAAIC
Repository and the OECD AI Incidents and Hazards Monitor. Each incident is coded from its records and
the articles they link. Every label carries the verbatim span it rests on (table `evidence`); a label
the material does not support is coded `unknown` or `unclear` rather than inferred. The coding follows
what the material says occurred, not what it says could occur.

## 1 AI actors

Three positions in the value chain, after the EU AI Act.

| position | definition |
|---|---|
| deployer | "a natural or legal person, public authority, agency or other body using an AI system under its authority" (Art. 3(4)) |
| provider | a body that "develops an AI system … and places it on the market or puts the AI system into service under its own name or trademark" (Art. 3(3)) |
| upstream provider | the party that supplied the implicated component: the part of the system the harm acted through or that failed (Art. 25) |

Each position takes a status: `named` (a party the material names or singles out), `described` (a
specific party it does not name), `unknown` (a category, or nothing), and for the deployer
`personal_use` (a person using the system in a personal, non-professional activity, which Art. 3(4)
excludes). A position holds every party the material shows acting in it. Brands are resolved to the
entity that answers for them. An AI actor that files with the SEC is linked by its CIK.

## 2 AI subject

AI subjects are "living entities subjected to or affected by the AI system use" (Bogucka,
Šćepanović & Quercia, 2026). The type of the subject most directly harmed is coded; inanimate objects
are not subjects.

| type | definition |
|---|---|
| Individual | a single person |
| Group of persons | a subset of people in a specific context, such as students, employees or delivery drivers |
| Society | a broad regional, national or global population |
| Organization | an institution, company, NGO, public body, university or media outlet |
| Nature | animals, plants or ecosystems |
| Other | a living entity that fits none of the above |

Where the material shows no living entity harmed, the status is `no_harm`.

## 3 Harm type

The harm types of the OECD AI Incidents and Hazards Monitor: Physical (injury), Physical (death),
Psychological, Reputational, Economic/Property, Human or fundamental rights, Public interest,
Environmental, Other. Every type the material shows occurred is coded; feared harms are not.

## 4 Risk type

The subdomain of the MIT AI Risk Repository (Slattery et al., 2026), one per incident. It is the
label incidents and filing passages share.

| subdomain | assigned when the harm that occurred is |
|---|---|
| 1.1 Unfair discrimination and misrepresentation | unequal treatment of people or groups, or a stereotyped or demeaning representation of them |
| 1.2 Exposure to toxic content | people exposed to violent, sexual, hateful, self-harm or otherwise harmful content |
| 1.3 Unequal performance across groups | the system working worse for some groups, harming them |
| 2.1 Compromise of privacy | personal or sensitive data collected, exposed, leaked or inferred without consent |
| 2.2 AI system security vulnerabilities and attacks | the AI system itself attacked or exploited |
| 3.1 False or misleading information | false content that misled someone, without intent to deceive |
| 3.2 Pollution of information ecosystem | the shared information environment degraded at scale |
| 4.1 Disinformation, surveillance, and influence at scale | AI used for propaganda, political deepfakes, influence operations or mass surveillance |
| 4.2 Cyberattacks, weapon development or use, and mass harm | AI used to attack systems, build or use weapons, or cause mass harm |
| 4.3 Fraud, scams, and targeted manipulation | AI used to defraud, impersonate, extort or manipulate specific targets |
| 5.1 Overreliance and unsafe use | users trusting or depending on the system inappropriately |
| 5.2 Loss of human agency and autonomy | people's ability to decide for themselves displaced or undermined |
| 6.1 Power centralization and unfair distribution of benefits | AI concentrating power or benefits unfairly |
| 6.2 Increased inequality and decline in employment quality | job losses, worse working conditions, surveillance of workers, widened inequality |
| 6.3 Economic and cultural devaluation of human effort | creative or skilled human work devalued or appropriated |
| 6.4 Competitive dynamics | a race between developers leading to unsafe release |
| 6.5 Governance failure | institutions or regulation failing to govern the system |
| 6.6 Environmental harm | energy, water, emissions or other ecological damage |
| 7.1 AI pursuing its own goals | the system acting against its operators' or users' intent in pursuit of an objective |
| 7.2 AI possessing dangerous capabilities | the system showing capabilities dangerous in themselves |
| 7.3 Lack of capability or robustness | the system failing at its task or behaving unreliably |
| 7.4 Lack of transparency or interpretability | harm because the system's decisions could not be explained or audited |
| 7.5 AI welfare and rights | concern for the moral status or treatment of AI systems |
| 7.6 Multi-agent risks | harm from interaction between several AI agents |

Decision rules: a person deliberately using AI to harm belongs to domain 4, the system failing or
misbehaving on its own to domains 3 or 7; wrong information that misled is 3.1, a wrong action or
function is 7.3; harm aimed at specific victims is 4.3, harm aimed at a population is 4.1; exposed
personal data is 2.1, a broken AI system is 2.2; biased decisions are 1.1, measurably worse accuracy
for a group is 1.3.

## 5 Impact layer

The three layers of Weidinger et al. (2023). The first layer at which harm occurred is coded.

| layer | the harm arises |
|---|---|
| capability | in the system's own outputs or behaviour: an error, a biased output, a failure to perform |
| human interaction | where people use or meet the system: deception, manipulation, over-reliance, exploitation by a user |
| systemic | in the wider systems the AI is part of: labour, markets, institutions, the information ecosystem, the environment |

## 6 Intended purpose and misuse

After the EU AI Act's intended purpose (Art. 3(12)) and reasonably foreseeable misuse (Art. 3(13)).

- **Intended purpose**: one clause stating what the provider presents the system as being for.
- **Relation**, judged on the use that led to the harm: `within_purpose` where the system was used
  for what it is evidently for, including harm from its errors, bias or design; `misuse` where it was
  used in a way not in accordance with that purpose; `unclear` where the material does not show how
  it was used.
- **Misuse by**, for misuse: `deployer`, `user` or `third_party` (an attacker or fraudster).

## 7 Action autonomy

The levels of the OECD Framework for the Classification of AI Systems (2022), with OECD AIM's fourth,
coded for the system's act through which the harm occurred.

| level | the act |
|---|---|
| human-out-of-the-loop | took effect with no person reviewing it or able to stop it, including output that reached and harmed its recipient unreviewed |
| human-on-the-loop | was taken by the system on its own while a person monitored it and could intervene |
| human-in-the-loop | was a decision, draft, alert or score that a person approved or executed case by case before it took effect |
| human support | was a person's, with the system as a tool, including a provider's use of data to train a model |
| unknown | is not shown by the material |

## 8 When the incident started

An incident starts with the harm itself: the earliest date the material gives for the first
exploitation, wrongful denial, crash or publication, or the start of a harmful use that continued. A
release, test, plan, report, lawsuit or acknowledgement does not start it. The date is coded at the
precision the material supports (day, month, year, or unknown). A date by which the incident had
already started is coded as a bound (`no_later_than`). The record date, when the incident became
public, is kept alongside.

## 9 The use

Three components of the use through which the harm occurred, after Herdel et al. (2024).

- **Capability**: what the system does, as one of eight verbs: Estimating, Forecasting, Comparing,
  Detecting, Identifying, Discovering, Generating, Acting. A verb outside these is marked with an
  asterisk.
- **Technique**: the AI technique as a class of the VAIR vocabulary (Golpayegani, Pandit & Lewis,
  2023): Machine Learning and its subclasses such as Deep Learning, Knowledge Based, Logic Based,
  Reasoning and Statistical Techniques; the most specific the material supports, else `unknown`.
  Generative systems are Deep Learning.
- **Domain**: the sector the system was used in when the harm occurred, one or two of 47 domains (the
  46 of Herdel et al., 2024, and Private services). A general-purpose system takes the domain of what
  it was used for; content takes the sector it served, not the platform it travelled on.

## References

- Bogucka, E., Šćepanović, S., & Quercia, D. (2026). Why AI harms can't be fixed one identity at a
  time: What 5300 incident reports reveal about intersectionality. *Proceedings of the 2026 ACM
  Conference on Fairness, Accountability, and Transparency*. https://doi.org/10.1145/3805689.3812347
- Golpayegani, D., Pandit, H. J., & Lewis, D. (2023). To be high-risk, or not to be: Semantic
  specifications and implications of the AI Act's high-risk AI applications and harmonised standards.
  *Proceedings of the 2023 ACM Conference on Fairness, Accountability, and Transparency*, 905–915.
  https://doi.org/10.1145/3593013.3594050
- Herdel, V., Šćepanović, S., Bogucka, E., & Quercia, D. (2024). ExploreGen: Large language models
  for envisioning the uses and risks of AI technologies. *Proceedings of the AAAI/ACM Conference on
  AI, Ethics, and Society*, 7, 584–596. https://doi.org/10.1609/aies.v7i1.31660
- OECD (2022). *OECD Framework for the Classification of AI Systems*. https://doi.org/10.1787/cb6d9eca-en
- Regulation (EU) 2024/1689 laying down harmonised rules on artificial intelligence (AI Act).
  https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- Slattery, P., Saeri, A. K., Grundy, E. A. C., Graham, J., Noetel, M., Uuk, R., Dao, J., Pour, S.,
  Casper, S., & Thompson, N. (2026). The AI risk repository: A meta-review, database, and taxonomy of
  risks from artificial intelligence. *Patterns*, 7(5), 101517. https://doi.org/10.1016/j.patter.2026.101517
- Weidinger, L., et al. (2023). Sociotechnical safety evaluation of generative AI systems.
  https://arxiv.org/abs/2310.11986
