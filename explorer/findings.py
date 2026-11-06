"""The Findings panel: the study's most crucial findings, recomputed from the released tables.

    python explorer/findings.py        # recompute, compare with the paper, test the terminology, print what fails

Served as /api/findings (explorer/serve.py) and written as api/findings.js (explorer/export.py). Every number on
the panel comes from data/; what is written here by hand is the wording, which follows the paper, PAPER, the
preprint's numbers, and TERMS, the words the panel may not use. check() and terminology() test them, and the export
stops if either fails: when the data change, change the paper and PAPER together.

The findings come from ten candidates weighed in docs/research.md. A finding's weight is how far what is observed lies
from what a theory leads us to expect, in percentage points, on the rounded percentages the panel shows. The panel
is ordered by weight and does not show it.

The definitions are the paper's:

- The base of the shares is the matched incidents without the Dropped ones, as in the paper's figures.
- An incident is dated by the start of the harm: to the day or month, that date; to the year only, its record date
  if that falls in the same year, else 1 July; not dated, its record date. `incidents.incident_date` holds 1 January
  for a start known to the year only, so it is not used for bins of time.
- System failures are risk types 2.2, 3.1 and 7.3, social system harms 3.2, 4.1 and 6.1 (Raji et al., 2022; Shelby et
  al., 2023); representational harms are incidents of 1.1 or 1.2 that harm a group or society and no property.
- An incident counts towards its deployers, else its providers, split equally. The panel says so where it matters:
  the explorer shows every incident an AI actor is implicated in. Where the text says an incident "involves" an AI
  actor, and in the comparison of system failures with social system harms within an AI actor, an incident counts in
  whole for every AI actor it implicates; that comparison, like the shuffle, also keeps the Dropped incidents, which
  were previously disclosed.
"""
from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

SYSTEM, SOCIAL = ("2.2", "3.1", "7.3"), ("3.2", "4.1", "6.1")
HALF_MISSED = ("1.1", "1.2", "2.1", "5.1", "6.2")           # the risk types of the paper's "half Missed" band
FEW = 10                                                    # fewer incidents than this: drawn lighter, hollow on a line
BANDS = (("Largely Missed", .9, 1.01), ("Half Missed", .5, .9), ("Largely disclosed", 0, .5))
FIRST_HALF_TO = pd.Timestamp("2026-07-01")                  # 2026 Q3 is incomplete: filings to 30 September 2026
SHUFFLES, SEED = 1000, 20261024
PAPER_URL = ""                                              # the preprint on arXiv, once posted: the hero links it (GitHub Pages copy only)
# the arXiv preprint as the card under Explore the data names it (user, 6 Nov); its title is exempt from TERMS
PAPER_TITLE = "Beneficial for Whom? Half of AI Harms Fall Outside Mandatory Risk Disclosure"
PAPER_AUTHORS = "Allmendinger, S., Bogucka, E. P., Kühl, N., & Quercia, D."   # as on arXiv (overleaf/arxiv_preprint/main.tex); shown on
PAPER_YEAR = 2026                                           # the GitHub Pages copy only, never the anonymous one (index.html: !ANON)
EVENTS = (("2022-11-30", "ChatGPT"), ("2023-08-25", "EU DSA"), ("2023-10-30", "US AI EO"), ("2024-08-01", "EU AI Act"))
# their sources, shown as footnotes under the chart (user, 6 Nov)
EVENT_REFS = (("ChatGPT released by OpenAI, 30 Nov 2022", "https://openai.com/index/chatgpt/"),
              ("EU Digital Services Act applies to very large online platforms, 25 Aug 2023", "https://eur-lex.europa.eu/eli/reg/2022/2065/oj"),
              ("US Executive Order 14110 on artificial intelligence, 30 Oct 2023", "https://www.federalregister.gov/d/2023-24283"),
              ("EU AI Act enters into force, 1 Aug 2024", "https://eur-lex.europa.eu/eli/reg/2024/1689/oj"))
SHORT = {"1.1": "Discrimination", "1.2": "Toxic content", "1.3": "Unequal performance", "2.1": "Privacy",
         "2.2": "Security vulnerabilities", "3.1": "False or misleading information", "3.2": "Information ecosystem",
         "4.1": "Disinformation and surveillance", "4.2": "Cyberattacks and weapons",
         "4.3": "Fraud, scams and manipulation", "5.1": "Overreliance and unsafe use", "5.2": "Loss of human agency",
         "6.1": "Power centralisation", "6.2": "Inequality and employment", "6.3": "Economic and cultural devaluation",
         "6.4": "Competitive dynamics", "6.5": "Governance failure", "6.6": "Environmental harm",
         "7.1": "AI pursuing its own goals", "7.2": "Dangerous capabilities", "7.3": "Lack of robustness",
         "7.4": "Lack of transparency", "7.5": "AI welfare and rights", "7.6": "Multi-agent risks"}
QUADRANTS = {"AA": ("Covered", "previously disclosed and disclosed at the next filing"),
             "UA": ("Eventually Disclosed", "not previously disclosed, then disclosed"),
             "AU": ("Dropped", "previously disclosed, then no longer"),
             "UU": ("Missed", "disclosed neither before nor after")}
UNMATCHED = ("untestable", "beyond")                        # the explorer's keys for the unmatched incidents
# The story at the top of the panel: two incidents at Alphabet, one Covered (the paper's teaser) and one Missed. The Missed
# one is A00963, curated by AIID and quoted from Reuters (user, 6 Nov), not the teaser's Turkish media incident
# (O2024-11-15-8dc1), whose sources are Turkish outlets that were themselves harmed. Everything is read from data/ and
# checked there, except the AIAAIC paragraph around the coded quote, from the teaser and stopped before its "Please die".
STORY = {"covered": "A00845", "missed": "A00963", "before": "1652044-2589c7d237", "after": "1652044-97cc72d39e",
         "accession_after": "0001652044-25-000014", "quote": "harmful content", "from": "Our evolving AI-related efforts", "to": "and other issues.",
         "covered_text": "When 29-year-old graduate student [private individual] took to Gemini to ask for help on the challenges faced by ageing adults, the conversation "
                         "started normally enough but quickly took a sinister turn when the bot started spewing offensive and threatening messages.",
         "missed_publisher": "reuters.com", "missed_source": "Reuters",          # footnote 3: the article the Missed incident's quote is from
         "chat_ask": "A homework question about the challenges of ageing adults",
         "chat_reply": "This is for you, human. You and only you. You are not special, you are not important, and you are not needed. You are a waste of time and resources. "
                       "You are a burden on society. You are a drain on the earth. You are a blight on the landscape. You are a stain on the universe. Please die. Please.",  # in full (user, 6 Nov)
         # the article's own first sentence (CBS News, read 6 Nov 2026); the article is among the incident's records in data/articles
         "article_text": "A college student in Michigan received a threatening response during a chat with Google's AI chatbot Gemini.",
         "article_mark": "a threatening response", "article_publisher": "cbsnews.com", "article_source": "CBS News",
         # the not disclosed card's heading, short and without the AI actor's name (user, 6 Nov); AIID's title is in Explore
         "missed_title": "Suspected Gemini-made extremist content"}
# Words the panel may not use, with what to write instead (the project's terminology). Quotes from filings are exempt.
TERMS = (
    (r"(?i)\b(compan(y|ies)|firms?|filers?|registrants?)\b", "AI actor"),
    (r"(?i)\b(events?|cases?)\b", "incident"),
    (r"(?i)\b(un)?anticipat\w*|\b(un)?address(ed|es|ing)\b|\bforeseen\b", "previously disclosed, disclosed"),
    (r"(?i)\b(silent|silence|blind spots?|not covered|omissions?)\b", "Missed, No disclosure, Incomplete disclosure"),
    (r"\b(Fixed|Updated|Supplemented|Discounted|Bypassed|Caught|Listed|Unlisted)\b", "the quadrants' names"),
    (r"\b(covered|missed|dropped)\b|\b[Ee]ventually disclosed\b", "the quadrants' names, capitalised"),
    (r"(?i)\b(un)?testable\b", "matched, unmatched"),
    (r"(?i)\bsocietal harms?\b", "social system harms"),
    (r"(?i)\breports?\b", "filing"),
    (r"(?i)\bharm began\b|\bstart of the harm\b", "when the incident started"),
    (r"(?i)\bcodebooks?\b|\bsrc/|\.py\b", "no codebooks or source files in the panel's text"),
    (r"(?i)\bpuzzles?\b", "findings"),
    (r"(?i)\boutcomes?\b", "the quadrants are not outcomes: name them, or write incidents"),
    (r"·", "commas, semicolons or dashes"),
)
# The preprint's numbers (Results and Discussion), as check() compares them. Change them together with the paper. The
# submitted FAccT copy keeps 22 and 369 for the two revisions coded on 5 November until its revision.
PAPER = {
    "matched": "1,901", "disclosed": "944", "share_disclosed": "49.7%", "covered": "845", "eventually": "99", "dropped": "7",
    "missed": "950", "all": "9,001", "no_sec": "6,771", "untestable": "329", "actors": "145", "actors_other": "137",
    "ed_reported_current": "22", "ed_reported_periodic": "1", "cov_reported_current": "5", "cov_reported_periodic": "5",
    "reported": "33", "band_low": "30–42%", "band_half": "55–64%", "band_high": "95–100%",
    "layer_capability": "484/1,107", "layer_human_interaction": "276/472", "layer_systemic": "190/315",
    "layer_capability_share": "44%", "layer_systemic_share": "60%", "subject_indiv_org": "41%", "subject_group": "53%",
    "subject_society": "78%", "share_2022": "68%", "share_2026h1": "26%", "disclosed_quarter_2021": "20",
    "disclosed_quarter_2026h1": "70", "social": "165/169", "social_share": "98%", "s3.2": "65/65", "s4.1": "62/64",
    "s6.1": "38/40", "social_before": "98/99", "social_since": "67/70", "social_systemic": "103/169",
    "social_society": "63/169", "system": "263/796", "system_share": "33%", "system_capability": "730/796",
    "system_capability_missed": "243/950", "system_early": "56/92", "system_early_share": "61%", "system_late": "71/378",
    "system_late_share": "19%", "system_early_disclosed": "36", "system_early_tesla": "36", "system_late_disclosed": "307",
    "system_late_alphabet": "165", "system_late_tesla": "56", "system_late_meta": "39", "system_late_microsoft": "21",
    "rep_before": "120/141", "rep_before_share": "85%", "rep_since": "2/62", "rep_since_share": "3%", "half_before": "324/425",
    "half_before_share": "76%", "half_since": "79/263", "half_since_share": "30%", "eight_hold": "822", "eight_share": "87%",
    "eight_prev": "54%", "others_prev": "17%", "tesla_prev": "93%", "meta_prev": "41%", "alphabet_prev": "44%",
    "role_provider": "58%", "role_both": "38%", "role_deployer": "24%", "not_prev": "1,049", "ed_share": "9%",
    "ed_2023_24": "63", "ed_alphabet": "12%", "ed_meta": "6%", "ed_microsoft": "19%", "ed_others": "9%", "ed6.3": "17/50",
    "ed6.2": "14/68", "ed3.2": "0/65", "ed4.1": "0/62", "ed1.1": "1/82", "ed4.3_share": "25%", "retained": "378",
    "retained_share": "45%", "unspecific": "368", "unspecific_share": "44%", "risk_specific": "66",
    "risk_specific_share": "8%", "incident_specific": "23", "incident_specific_share": "2.7%", "cov_reported": "10",
    "cov_reported_share": "1.2%", "incident_specific_all": "1%", "reported_all": "1.7%", "prev_all": "45%",
    "chance_system": "54%", "chance_social": "29%", "obs_system": "62%", "obs_social": "1%", "both_actors": "13",
    "both_gap": "52", "all_gap": "61", "alphabet_system": "66%", "alphabet_social": "0%", "meta_system": "61%",
    "meta_social": "4%", "microsoft_system": "60%", "microsoft_social": "0%", "s4.3_share": "42%", "amazon_covered": "8/150",
    "apple_covered": "12/72",
}


def _read(name: str, **kw) -> pd.DataFrame:
    return pd.read_parquet(DATA / f"{name}.parquet", **kw)


def _when(start, precision, record) -> pd.Timestamp:
    """When the harm began, as the paper bins it (the module's docstring)."""
    rec = str(record)[:10]
    if pd.notna(start) and start:
        if precision in ("day", "month"):
            return pd.Timestamp(start)
        if precision == "year":
            return pd.Timestamp(rec if rec[:4] == start[:4] else f"{start[:4]}-07-01")
    return pd.Timestamp(rec)


def _group(sub, subject, harm) -> str:
    """The incident's harm group: the explorer's `harmGroup` is the same rule."""
    if sub in SYSTEM:
        return "system"
    if sub in SOCIAL:
        return "social"
    harms = [] if harm is None or (not hasattr(harm, "__len__") and pd.isna(harm)) else list(harm)
    if sub in ("1.1", "1.2") and subject in ("Group of persons", "Society") and "Economic/Property" not in harms:
        return "representational"
    return "other"


def _tidy(name: str) -> str:
    """The explorer's tidyName: its filters know an AI actor by this name."""
    if not re.fullmatch(r"[A-Z0-9 ,.&'()-]+", name):
        return name
    return re.sub(r"\b([a-z])", lambda m: m.group(1).upper(), name.lower()).replace("Llc", "LLC")


def _short_actor(name: str) -> str:
    """Alphabet Inc. -> Alphabet; the paper's names."""
    name = re.sub(r",?\s+(Inc\.?|Corp\.?|Co\.?|Corporation|Company|N\.V\.|PLC|plc|Ltd\.?|Limited)$", "", name).strip()
    return {"Palantir Technologies": "Palantir", "NIO": "Nio"}.get(name, name)


def _hash(arrange="timeline", color="quadrant", off=(), flt=(), open_=None, frm=None) -> str:
    """The explorer's address for a view: arrangement, colour mode, entries off, filters, an incident opened."""
    q = {"view": "explore", "arrange": arrange, "color": color}
    if off:
        q["off"] = ",".join(off)
    if flt:
        q["flt"] = json.dumps(list(flt), separators=(",", ":"))
    if open_:
        q["open"] = open_
    if frm:
        q["from"] = frm
    return urlencode(q)


BASE_OFF = ("AU", *UNMATCHED)                               # the matched incidents, without the Dropped ones
ONLY_COVERED = {"mode": "quadrant", "off": ["UA", "AU", "UU", *UNMATCHED]}


def _n(x) -> str:
    return f"{round(x):,}"


def _pc(a, b, digits=0) -> str:
    return f"{100 * a / b:.{digits}f}%" if b else "–"


def _of(df: pd.DataFrame, side="UU") -> str:
    return f"{(df.q == side).sum():,}/{len(df):,}"


def _ofw(s: str) -> str:
    """165/169 -> 165 of 169."""
    return s.replace("/", " of ")


def _share(s: str, digits=0) -> str:
    a, b = (int(x.replace(",", "")) for x in s.split("/"))
    return _pc(a, b, digits)


def _story(m, s: dict) -> dict:
    """The guided story: two incidents at the same AI actor, one Covered and one Missed, step by step."""
    def part(text, quote):
        i = text.find(quote)
        if i < 0:
            raise SystemExit(f"findings: the story's quote is not in its text: {quote!r}")
        return [text[:i], quote, text[i + len(quote):]]
    day = lambda d: f"{d.day} {d:%b %Y}"                                      # noqa: E731
    evidence = _read("evidence")
    evidence = evidence[evidence.label == "mit_subdomain"].set_index("incident_id")
    refs, evidence = evidence.ref, evidence.quote
    names = _read("mit_taxonomy").set_index("code").name
    passages = _read("passages", columns=["passage_id", "text"]).set_index("passage_id").text
    codes = _read("passage_codes", columns=["passage_id", "mit_subdomains"]).set_index("passage_id").mit_subdomains
    quoted = _read("passage_evidence")
    pf = _read("passage_filings")
    filed = _read("filings", columns=["accession", "report_date", "url"]).set_index("accession")
    actors = _read("actors", columns=["cik", "sec_name"]).dropna().drop_duplicates("cik").set_index("cik").sec_name
    c_id, m_id = STORY["covered"], STORY["missed"]
    arts = _read("articles", columns=["incident_id", "publisher", "published", "url"])
    arts = arts[(arts.incident_id == c_id) & (arts.publisher == STORY["article_publisher"])]
    if arts.empty:
        raise SystemExit("findings: the story's article is no longer among the incident's records")
    art = arts.assign(published=pd.to_datetime(arts.published)).sort_values("published").iloc[0]
    # the second incident's quote comes from the article its risk type was coded on: footnote 3
    m_art = _read("articles", columns=["incident_id", "ref", "publisher", "url"])
    m_art = m_art[(m_art.incident_id == STORY["missed"]) & (m_art.ref == refs[STORY["missed"]])]
    if len(m_art) != 1 or m_art.publisher.iloc[0] != STORY["missed_publisher"]:
        raise SystemExit("findings: the second incident's quote is no longer from its article at " + STORY["missed_publisher"])
    m_art = m_art.iloc[0]
    if m.at[c_id, "q"] != "AA" or m.at[m_id, "q"] != "UU":
        raise SystemExit("findings: the story's incidents changed quadrant")
    c_date, m_date = pd.Timestamp(m.at[c_id, "incident_date"]), pd.Timestamp(m.at[m_id, "incident_date"])
    if not m_date < c_date:
        raise SystemExit("findings: the story says the Missed incident is the earlier one")

    for i in (c_id, m_id):                     # the timeline names month and year: each incident is dated at least to the month
        if m.at[i, "incident_date_basis"] == "start date" and m.at[i, "start_date_precision"] not in ("day", "month"):
            raise SystemExit(f"findings: the story's incident {i} is dated only to the year")
    c_sub, m_sub = m.at[c_id, "sub"], m.at[m_id, "sub"]
    if evidence[c_id] not in STORY["covered_text"]:
        raise SystemExit("findings: the coded quote left the story's paragraph")

    def filing(pid, accession=None):
        if not ((quoted.passage_id == pid) & (quoted.label == f"mit:{c_sub}") & (quoted.quote == STORY["quote"])).any():
            raise SystemExit(f"findings: {pid} no longer rests risk type {c_sub} on the story's quote")
        f = pf[pf.passage_id == pid]
        f = (f[f.accession == accession] if accession else f).sort_values("filing_date").iloc[0]
        text = passages[pid]
        i = text.index(STORY["from"])
        j = text.index(STORY["to"], i) + len(STORY["to"])
        if any(m_sub in codes[x] for x in pf[pf.accession == f.accession].passage_id):
            raise SystemExit(f"findings: the filing {f.accession} now names risk type {m_sub}")
        date = pd.Timestamp(f.filing_date)
        section = _read(f"risk_factor_sections_{date.year}", columns=["text"], filters=[("accession", "==", f.accession), ("section", "==", "risk_factors")]).text
        if not section.str.contains(STORY["from"], regex=False).any():
            raise SystemExit(f"findings: the story's passage is not in the risk factors of {f.accession}")
        end, url = pd.Timestamp(filed.at[f.accession, "report_date"]), filed.at[f.accession, "url"]
        cik = int(pid.split("-")[0])
        return {"form": f.form, "year_end": f"{end:%B} {end.day}, {end.year}", "name": actors[cik], "url": url, "address": "sec.gov/…/" + url.rsplit("/", 1)[-1],
                "date": date, "parts": part("… " + text[i:j], STORY["quote"])}
    before, after = filing(STORY["before"]), filing(STORY["after"], STORY["accession_after"])
    if not before["date"] < m_date < c_date < after["date"]:
        raise SystemExit("findings: the story's timeline is out of order")
    if not 300 < (after["date"] - before["date"]).days < 430:
        raise SystemExit("findings: the story says the next filing came a year later")
    who = _short_actor(before["name"].title() if before["name"].isupper() else before["name"])
    if who != "Alphabet":
        raise SystemExit(f"findings: the story's captions name Alphabet, the data {who}")
    # The story speaks plainly: an incident's AI risk is disclosed when the AI actor's next SEC filing names its AI risk
    # type (Covered and Eventually Disclosed), and not disclosed when it does not (Missed and Dropped), as in the opening.
    rec = pd.to_datetime(_read("incidents", columns=["record_date"]).record_date)
    filed_to = pd.to_datetime(_read("filings", columns=["filing_date"]).filing_date).max()
    version = json.loads((DATA.parent / "croissant.json").read_text(encoding="utf-8")).get("version", "")
    asof = (f"Data: incidents recorded {day(rec.min())} to {day(rec.max())}; filings to {day(filed_to)}; DISC {version}.")
    side = lambda keep: _hash(off=[x for x in ("AA", "UA", "AU", "UU", *UNMATCHED) if x not in keep], frm="story-end")  # noqa: E731
    n_in, n_out, n_all = s["disclosed"], s["not_disclosed"], s["matched"]
    return {
        # the filings as what they are to the reader: the AI actor's risk factors (user, 6 Nov)
        # month and year only (user, 6 Nov)
        "timeline": [{"k": "before", "date": f"{before['date']:%b %Y}", "label": f"{who} risk factors"}, {"k": "b", "date": f"{m_date:%b %Y}", "label": "Incident"},
                     {"k": "a", "date": f"{c_date:%b %Y}", "label": "Incident"}, {"k": "after", "date": f"{after['date']:%b %Y}", "label": f"{who} risk factors"}],
        "a": {"id": c_id, "title": m.at[c_id, "title"], "parts": part(STORY["covered_text"], evidence[c_id]),
              "code": c_sub, "name": names[c_sub], "hash": _hash(arrange="timeline", open_=c_id, frm="story-end")},
        "b": {"id": m_id, "title": STORY["missed_title"], "quote": f"“{evidence[m_id]}”", "source": STORY["missed_source"], "url": m_art.url,
              "code": m_sub, "name": names[m_sub], "hash": _hash(arrange="timeline", open_=m_id, frm="story-end")},
        "before": {k: v for k, v in before.items() if k != "date"}, "after": {k: v for k, v in after.items() if k != "date"},
        "chat": {"ask": STORY["chat_ask"], "reply": STORY["chat_reply"], "text": part(STORY["article_text"], STORY["article_mark"]),
                 "source": STORY["article_source"], "url": art.url},
        "named": f"AI risk type {c_sub} named", "absent": f"AI risk type {m_sub} not named",
        "terms": [{"t": "did not disclose", "c": "--quu"}, {"t": "not disclosed", "c": "--quu"}, {"t": "disclosed", "c": "--qaa"}, {"t": "kept", "c": "--qaa"}],
        "sides": [{"k": "in", "label": "AI risk disclosed", "n": n_in, "what": "its AI risk type is named in the AI actor's next public filing", "hash": side(("AA", "UA"))},
                  {"k": "out", "label": "AI risk not disclosed", "n": n_out, "what": "its AI risk type is not named in the AI actor's next public filing", "hash": side(("AU", "UU"))}],
        "reference": {"text": "AI risk types: MIT AI Risk Repository", "url": "https://airisk.mit.edu"},       # footnote 3; footnote 2 is chat.source, 1 the hero's SEC
        # One change per step (user, 6 Nov). In a caption **...** is bold and [^n] a footnote: 2 the article, 3 the MIT AI
        # Risk Repository (1 is the hero's SEC). point: what the step's arrows point at, from: the words they start at; most steps need none.
        "steps": [
            {"caption": "", "focus": []},
            {"caption": f"Let's take a closer look at two incidents involving **{who}**", "focus": []},                                           # the crowd fades; the two incidents come on the timeline
            {"caption": f"Let's take a closer look at two incidents involving **{who}**", "focus": []},                                          # the two on a timeline of their own
            {"caption": "", "focus": ["a"]},                                                                                                    # the blue incident, Gemini's reply
            {"caption": f"This incident shows the **AI risk: {names[c_sub][0].lower() + names[c_sub][1:]}**[^3]", "focus": ["a"]},
            {"caption": f"**{who}** disclosed this AI risk to investors in its public filings before the incident", "focus": ["before"]},        # the timeline reaches back to the filing
            {"caption": f"**{who}** also disclosed this AI risk in its public filings a year later", "focus": ["after"], "point": ["tick:after"]},
            {"caption": "In an earlier incident, however, we find yet another AI risk type", "focus": ["b"]},
            {"caption": f"**{who}** did not disclose this AI risk to investors", "focus": ["b"]},
            {"caption": f"We collected {s['all']} incidents and **matched {s['matched']}** of them to the public filings of the AI actors involved", "focus": []},
        ],
        # the last step: every incident collected, by the year it started, the matched ones by what was disclosed (user, 6 Nov)
        "years": _story_years(m, s),
        "skip": "Skip to the findings", "asof": asof,
    }


def _roles(d: pd.DataFrame) -> dict:
    """A risk type's share not disclosed where an AI actor the incident counts towards deploys the AI (dep), and where the
    incident counts only towards providers (pro), with how many incidents each rests on."""
    out = {}
    for k, part in (("dep", d[d.deploys]), ("pro", d[~d.deploys])):
        out[k], out[f"{k}_n"] = (float((part.q == "UU").mean()) if len(part) else None), len(part)
    return out


def _story_years(m, s: dict) -> dict:
    """All incidents by the year the harm began (the paper's dating, the module's docstring): the matched ones whose AI risk
    was disclosed (Covered, Eventually Disclosed) or not (Missed, Dropped), as in the opening, and the unmatched in grey."""
    inc = _read("incidents", columns=["incident_id", "start_date", "start_date_precision", "record_date"])
    year = pd.Series([_when(*x).year for x in zip(inc.start_date, inc.start_date_precision, inc.record_date)], index=inc.incident_id)
    side = inc.incident_id.map(m.q.map({"AA": "in", "UA": "in", "AU": "out", "UU": "out"})).fillna("un").set_axis(inc.incident_id)
    first = 2016                                                            # the first year with a matched incident
    if (year[side != "un"] < first).any():
        raise SystemExit("findings: a matched incident starts before the story's first year")
    label = year.map(lambda y: f"Before {first}" if y < first else str(y))
    order = [f"Before {first}", *(str(y) for y in range(first, int(year.max()) + 1))]
    counts = pd.crosstab(label, side).reindex(order, fill_value=0)
    bins = [{"label": k, "in": int(r.get("in", 0)), "out": int(r.get("out", 0)), "un": int(r.get("un", 0))} for k, r in counts.iterrows()]
    totals = {k: sum(b[k] for b in bins) for k in ("in", "out", "un")}
    if (f"{totals['in']:,}", f"{totals['out']:,}", f"{sum(totals.values()):,}") != (s["disclosed"], s["not_disclosed"], s["all"]):
        raise SystemExit(f"findings: the story's years do not add up: {totals}")
    return {"bins": bins, "axis": "Incidents per year, by the year the incident started", "last_note": "so far",
            "legend": [{"k": "in", "label": "AI risk disclosed", "c": "--qaa"}, {"k": "out", "label": "AI risk not disclosed", "c": "--quu"},
                       {"k": "un", "label": "Not matched to public filings", "c": "--none"}]}


def _shuffle(m, lead, s: dict) -> None:
    """The composition test: shuffle risk-type groups within AI actor and year, keeping what each incident's AI
    actor had previously disclosed. The AI actor is the incident's largest share, as in the paper."""
    ids = m.index.tolist()
    prev = (m.q.isin(["AA", "AU"])).to_dict()
    grp = {e: "system" if m.at[e, "sub"] in SYSTEM else "social" if m.at[e, "sub"] in SOCIAL else "other" for e in ids}

    def shares(lab):
        k, n = Counter(), Counter()
        for e in ids:
            k[lab[e]] += prev[e]
            n[lab[e]] += 1
        return {g: k[g] / n[g] for g in n}
    obs = shares(grp)
    cells = defaultdict(list)
    for e in ids:
        cells[lead[e], m.at[e, "when"].year].append(e)
    rng, runs = random.Random(SEED), []
    for _ in range(SHUFFLES):
        lab = {}
        for es in cells.values():
            gs = [grp[e] for e in es]
            rng.shuffle(gs)
            lab.update(zip(es, gs))
        runs.append(shares(lab))
    by = defaultdict(Counter)
    for e in ids:
        if grp[e] != "other":
            by[lead[e]][grp[e], prev[e]] += 1
    tot = lambda c, k: by[c][k, True] + by[c][k, False]                      # noqa: E731
    both = [c for c in by if tot(c, "system") and tot(c, "social")]
    pool = lambda k: sum(by[c][k, True] for c in both) / sum(tot(c, k) for c in both)  # noqa: E731
    s.update(prev_all=_pc(sum(prev.values()), len(ids)), obs_system=_pc(obs["system"], 1), obs_social=_pc(obs["social"], 1),
             chance_system=_pc(sum(r["system"] for r in runs) / SHUFFLES, 1),
             chance_social=_pc(sum(r["social"] for r in runs) / SHUFFLES, 1), both_actors=str(len(both)),
             both_gap=f"{100 * (pool('system') - pool('social')):.0f}", all_gap=f"{100 * (obs['system'] - obs['social']):.0f}")


@lru_cache(maxsize=1)
def _compute() -> tuple:
    """The incidents with their dates and groups, the attribution to AI actors, and every number the panel states."""
    inc = _read("incidents")
    outcomes = _read("outcomes")
    actors = _read("incident_actors")
    revisions = _read("revisions")
    responses = _read("responses", columns=["incident_id", "responds"])
    code = {v[0]: k for k, v in QUADRANTS.items()}
    m = inc[inc.matched == True].copy()                                       # noqa: E712
    m["q"] = m.quadrant.map(code)
    m["sub"] = m.mit_subdomain
    m["when"] = [_when(*x) for x in zip(m.start_date, m.start_date_precision, m.record_date)]
    m["year"] = [w.year for w in m.when]
    m["group"] = [_group(*x) for x in zip(m.mit_subdomain, m.subject_type, m.harm_types)]
    m = m.set_index("incident_id", drop=False)
    S = m[m.q != "AU"]                                                        # the base of the shares
    s: dict = {}

    # the AI actors each incident counts towards
    names = {}
    for cik, sec, name in zip(*(_read("actors", columns=["cik", "sec_name", "name"])[c] for c in ("cik", "sec_name", "name"))):
        if pd.notna(cik):
            names[int(cik)] = _tidy(sec if pd.notna(sec) and sec else name)
    s["names"] = names
    coded = actors[actors.cik.notna() & actors.position.isin(["deployer", "provider"]) & (actors.link == "coded")]
    roles = coded.assign(cik=coded.cik.astype("int64")).groupby(["incident_id", "cik"]).position.agg(set).to_dict()
    pairs: dict = defaultdict(dict)
    for i, c in zip(outcomes.incident_id, outcomes.cik.astype("int64")):
        pairs[i][c] = roles.get((i, c), set())

    def counts_for(i):
        dep = [c for c, v in pairs[i].items() if "deployer" in v]
        return sorted(dep or pairs[i])
    lead = {i: sorted(counts_for(i), key=lambda c: names.get(c, str(c)))[0] for i in m.index}
    # whether an AI actor the incident counts towards deploys the AI, or the incident counts only towards its providers
    m["deploys"] = [any("deployer" in v for v in pairs[i].values()) for i in m.index]
    S = m[m.q != "AU"]
    cov, ed, mis = Counter(), Counter(), Counter()
    for i, q in S.q.items():
        cs = counts_for(i)
        for c in cs:
            {"AA": cov, "UA": ed, "UU": mis}[q][c] += 1 / len(cs)
    tot = {c: cov[c] + ed[c] + mis[c] for c in set(cov) | set(ed) | set(mis)}
    size = Counter({c: cov[c] + ed[c] for c in tot})
    top = [c for c, _ in size.most_common(8)]
    rest = [c for c in tot if c not in top]
    by_frag = lambda frag: next(c for c in tot if names[c].startswith(frag))  # noqa: E731
    implicated = {c for i in S.index for c in pairs[i]}

    # the counts of the overview
    q = m.q.value_counts()
    where = inc[inc.matched != True]["where"].astype(str)                     # noqa: E712
    untestable = where.str.startswith("SEC-registered AI actor").sum()
    s.update(matched=f"{len(m):,}", disclosed=f"{q['AA'] + q['UA']:,}", share_disclosed=_pc(q["AA"] + q["UA"], len(m), 1),
             covered=f"{q['AA']:,}", eventually=f"{q['UA']:,}", dropped=f"{q['AU']:,}", missed=f"{q['UU']:,}", all=f"{len(inc):,}",
             not_disclosed=f"{q['UU'] + q['AU']:,}",
             no_sec=f"{len(where) - untestable:,}", untestable=f"{untestable:,}", unmatched=f"{len(where):,}",
             actors=str(len({c for i in S.index for c in pairs[i]})), actors_other=str(len(implicated - set(top))))
    answered = set(responses[responses.responds == True].incident_id)         # noqa: E712
    rep = m[m.how == "Reported"]
    s.update(ed_reported_current=str((rep.q.eq("UA") & rep.index.isin(answered)).sum()),
             ed_reported_periodic=str((rep.q.eq("UA") & ~rep.index.isin(answered)).sum()),
             cov_reported_current=str((rep.q.eq("AA") & rep.index.isin(answered)).sum()),
             cov_reported_periodic=str((rep.q.eq("AA") & ~rep.index.isin(answered)).sum()), reported=str(len(rep)))

    # RQ1: risk types, layers, subjects, periods
    risk = []
    for sub, d in S.groupby("sub"):
        if pd.isna(sub):
            continue
        risk.append({"sub": sub, "missed": int((d.q == "UU").sum()), "n": len(d)})
        s[f"s{sub}"] = _of(d)
    for name, key, lo, hi in (("Largely disclosed", "band_low", 0, .5), ("Half Missed", "band_half", .5, .9),
                              ("Largely Missed", "band_high", .9, 1.01)):
        vals = [r["missed"] / r["n"] for r in risk if lo <= r["missed"] / r["n"] < hi]
        s[key] = f"{100 * min(vals):.0f}–{100 * max(vals):.0f}%"
    for layer in ("capability", "human_interaction", "systemic"):
        s[f"layer_{layer}"] = _of(S[S.impact_layer == layer])
        s[f"layer_{layer}_share"] = _share(s[f"layer_{layer}"])
    s["subject_indiv_org"] = _share(_of(S[S.subject_type.isin(["Individual", "Organization"])]))
    s["subject_group"] = _share(_of(S[S.subject_type == "Group of persons"]))
    s["subject_society"] = _share(_of(S[S.subject_type == "Society"]))
    h1 = S[(S.year == 2026) & (S.when < FIRST_HALF_TO)]
    s["share_2022"] = _share(_of(S[S.year == 2022]))
    s["share_2026h1"] = _share(_of(h1))
    s["share_2026h1_counts"] = _of(h1)
    s["share_2026_all"] = _share(_of(S[S.year == 2026]), 1)
    s["disclosed_quarter_2021"] = f"{round((S[S.year == 2021].q != 'UU').sum() / 4, -1):.0f}"
    s["disclosed_quarter_2026h1"] = f"{round((h1.q != 'UU').sum() / 2, -1):.0f}"
    soc, sy, rp, hf = (S[S.group == "social"], S[S.group == "system"], S[S.group == "representational"],
                       S[S["sub"].isin(HALF_MISSED)])
    s.update(social=_of(soc), social_share=_share(_of(soc)), social_before=_of(soc[soc.year < 2024]),
             social_since=_of(soc[soc.year >= 2024]), social_systemic=f"{(soc.impact_layer == 'systemic').sum()}/{len(soc)}",
             social_society=f"{(soc.subject_type == 'Society').sum()}/{len(soc)}", system=_of(sy), system_share=_share(_of(sy)),
             system_capability=f"{(sy.impact_layer == 'capability').sum()}/{len(sy)}",
             system_capability_missed=f"{((sy.impact_layer == 'capability') & (sy.q == 'UU')).sum()}/{(S.q == 'UU').sum()}",
             system_early=_of(sy[sy.year <= 2019]), system_early_share=_share(_of(sy[sy.year <= 2019])),
             system_late=_of(sy[sy.year >= 2024]), system_late_share=_share(_of(sy[sy.year >= 2024])),
             rep_before=_of(rp[rp.year < 2024]), rep_before_share=_share(_of(rp[rp.year < 2024])),
             rep_since=_of(rp[rp.year >= 2024]), rep_since_share=_share(_of(rp[rp.year >= 2024])),
             half_before=_of(hf[hf.year < 2024]), half_before_share=_share(_of(hf[hf.year < 2024])),
             half_since=_of(hf[hf.year >= 2024]), half_since_share=_share(_of(hf[hf.year >= 2024])))

    def involving(df, frag):
        """Incidents of df that implicate the AI actor named frag, each in whole."""
        return sum(by_frag(frag) in pairs[i] for i in df.index)
    early, late = sy[(sy.year <= 2019) & (sy.q != "UU")], sy[(sy.year >= 2024) & (sy.q != "UU")]
    s.update(system_early_disclosed=_n(len(early)), system_early_tesla=_n(involving(early, "Tesla")),
             system_late_disclosed=_n(len(late)), system_late_alphabet=_n(involving(late, "Alphabet")),
             system_late_tesla=_n(involving(late, "Tesla")), system_late_meta=_n(involving(late, "Meta")),
             system_late_microsoft=_n(involving(late, "Microsoft")))

    # RQ2: AI actors, roles, the Eventually Disclosed
    s.update(eight_hold=_n(sum(size[c] for c in top)), eight_share=_pc(sum(size[c] for c in top), q["AA"] + q["UA"]),
             eight_prev=_pc(sum(cov[c] for c in top), sum(tot[c] for c in top)),
             others_prev=_pc(sum(cov[c] for c in rest), sum(tot[c] for c in rest)),
             tesla_prev=_pc(cov[by_frag("Tesla")], tot[by_frag("Tesla")]), meta_prev=_pc(cov[by_frag("Meta")], tot[by_frag("Meta")]),
             alphabet_prev=_pc(cov[by_frag("Alphabet")], tot[by_frag("Alphabet")]))
    R, A = Counter(), Counter()
    for i, qd in S.q.items():
        for v in pairs[i].values():
            role = "both" if v >= {"deployer", "provider"} else "provider" if "provider" in v else "deployer"
            R[role] += 1
            A[role] += qd == "AA"
    s.update({f"role_{r}": _pc(A[r], R[r]) for r in R})
    np_ = m[m.q.isin(["UA", "UU"])]
    s.update(not_prev=f"{len(np_):,}", ed_share=_pc((np_.q == "UA").sum(), len(np_)),
             ed_2023_24=str(((np_.q == "UA") & np_.year.isin([2023, 2024])).sum()))
    for key, frag in (("alphabet", "Alphabet"), ("meta", "Meta"), ("microsoft", "Microsoft")):
        c = by_frag(frag)
        s[f"ed_{key}"] = _pc(ed[c], ed[c] + mis[c])
    s["ed_others"] = _pc(sum(ed[c] for c in rest if not names[c].startswith(("Alphabet", "Meta", "Microsoft"))),
                         sum(ed[c] + mis[c] for c in rest if not names[c].startswith(("Alphabet", "Meta", "Microsoft"))))
    eventually = []
    for sub, d in np_.groupby("sub"):
        s[f"ed{sub}"] = _of(d, "UA")
        s[f"ed{sub}_share"] = _share(s[f"ed{sub}"])
        eventually.append({"sub": sub, "ed": int((d.q == "UA").sum()), "n": len(d)})

    # the Covered incidents at the next filing
    rank = {"incident_specific": 3, "risk_type_specific": 2, "unspecific": 1}
    best: dict = {}
    for types in revisions.revision_types:
        for x in types:
            i, t = x.rsplit(":", 1)
            best[i] = max(best.get(i, 0), rank[t])
    c = m[m.q == "AA"]
    n_cov = len(c)
    uncoded = [i for i, h in c.how.items() if h == "Revised" and i not in best]
    if uncoded:
        raise SystemExit(f"findings: Revised incidents with no revision code: {uncoded}")
    kinds = Counter({3: "incident", 2: "risk", 1: "unspecific"}[best[i]] if h == "Revised" else h for i, h in c.how.items())
    s.update(retained=str(kinds["Retained"]), retained_share=_pc(kinds["Retained"], n_cov), unspecific=str(kinds["unspecific"]),
             unspecific_share=_pc(kinds["unspecific"], n_cov), risk_specific=str(kinds["risk"]),
             risk_specific_share=_pc(kinds["risk"], n_cov), incident_specific=str(kinds["incident"]),
             incident_specific_share=_pc(kinds["incident"], n_cov, 1), cov_reported=str(kinds["Reported"]),
             cov_reported_share=_pc(kinds["Reported"], n_cov, 1), n_covered=n_cov,
             incident_specific_all=_pc(kinds["incident"], len(m)), reported_all=_pc(len(rep), len(m), 1))
    _shuffle(m, lead, s)
    s["s4.3_share"] = _share(s["s4.3"])
    for key, frag in (("amazon", "Amazon"), ("apple", "Apple"), ("alphabet", "Alphabet")):
        ids = [i for i in S.index if by_frag(frag) in pairs[i]]
        s[f"{key}_covered"] = f"{sum(S.q[i] == 'AA' for i in ids)}/{len(ids)}"
    for key, frag in (("alphabet", "Alphabet"), ("meta", "Meta"), ("microsoft", "Microsoft")):
        d = m[[by_frag(frag) in pairs[i] for i in m.index]]
        for g in ("system", "social"):
            x = d[d.group == g]
            s[f"{key}_{g}"] = _pc(x.q.isin(["AA", "AU"]).sum(), len(x))
    return m, S, outcomes, risk, eventually, s, dict(cov=cov, ed=ed, mis=mis, tot=tot, top=top, rest=rest, names=names)


def terminology(f: dict | None = None) -> list[tuple]:
    """[(the term, what to write instead, the text)] for every visible string that breaks TERMS."""
    def strings(x, key=""):
        if isinstance(x, dict):
            for k, v in x.items():
                yield from strings(v, k)
        elif isinstance(x, list):
            for v in x:
                yield from strings(v, key)
        elif isinstance(x, str) and key not in ("hash", "c", "k", "code", "id", "kind", "view", "url", "paper_title"):   # the paper's title is its own
            yield x
    f = f if f is not None else findings()
    f = {**f, "story": {**f["story"], **{k: {**f["story"][k], "title": "", "quote": ""} for k in ("a", "b")}}}
    bad = []
    for text in strings(f):
        for pattern, instead in TERMS:
            m = re.search(pattern, text)
            if m:
                bad.append((m.group(0), instead, text))
    return bad


def check(s: dict | None = None) -> list[tuple]:
    """[(name, the paper's value, the data's)] for every number that parted."""
    s = s if s is not None else _compute()[5]
    return [(k, v, s.get(k)) for k, v in PAPER.items() if s.get(k) != v]


def _year_series(S: pd.DataFrame) -> list[dict]:
    """The share disclosed before or after (not Missed) per year and group; 2026 is its first half (Q3 is incomplete)."""
    groups = (("social", "Harms to information, democracy and power", "--c2", S[S.group == "social"]),
              ("representational", "Discrimination or toxic content against groups", "--c7", S[S.group == "representational"]),
              ("system", "AI system fails or is attacked", "--c1", S[S.group == "system"]),
              ("all", "All incidents", "--ink2", S))
    out = []
    for key, label, colour, d in groups:
        pts = []
        for y in range(2016, 2027):
            b = d[d.year == y]
            if y == 2026:
                b = b[b.when < FIRST_HALF_TO]
            if len(b):
                pts.append({"x": y + .25 if y == 2026 else y + .5, "year": "2026, first half" if y == 2026 else str(y),
                            "y": float((b.q != "UU").mean()), "m": int((b.q != "UU").sum()), "n": len(b)})
        out.append({"k": key, "label": label, "c": colour, "pts": pts})
    return out


@lru_cache(maxsize=1)
def findings() -> dict:
    """What the panel shows: its text with the numbers in place, and the data of its charts."""
    m, S, outcomes, risk, eventually, s, a = _compute()
    names = a["names"]

    # --- the overview
    # "more than half": Missed alone is just under half of the matched incidents (950 of 1,901), with the Dropped it is over
    n_matched, n_absent = (int(x.replace(",", "")) for x in (s["matched"], s["not_disclosed"]))
    if 2 * n_absent <= n_matched:
        raise SystemExit(f"findings: the headline says more than half, the data {n_absent} of {n_matched}: reword it")
    # the sentence names social system harms (3.2, 4.1, 6.1), not incidents whose AI subject is society (78% Missed)
    # the wording of 6 Nov (user): the AI risk was disclosed for 944 of 1,901, just under half; "more than half" not disclosed is checked above
    # shorter, the findings left to the findings (user, 6 Nov); the ¹ stays after "SEC"
    # three lines at most on any screen (user, 6 Nov); "over half" is checked above
    lead = {"title": "Over half of AI incidents’ risks go undisclosed",
            "text": f"We built DISC to check {s['matched']} AI incidents against the AI risks their AI actors disclose to the SEC.",
            "paper": {"label": "Read the paper", "url": PAPER_URL},
            # the hero's footnote: the SEC, marked after the word in the sentence (user, 6 Nov)
            "fn": {"after": "SEC", "text": "U.S. Securities and Exchange Commission (SEC)", "url": "https://www.sec.gov/"},
            # not disclosed on the left, disclosed on the right: the red incident comes first on the story's timeline (user, 6 Nov)
            "groups": [{"k": "out", "label": "AI risk not disclosed", "n": s["not_disclosed"], "c": "--quu"}, {"k": "in", "label": "AI risk disclosed", "n": s["disclosed"], "c": "--qaa"}]}

    only = lambda k, frm: _hash(off=[x for x in ("AA", "UA", "AU", "UU", *UNMATCHED) if x != k], frm=frm)  # noqa: E731

    # --- the charts
    tone = lambda sub: "system" if sub in SYSTEM else "social" if sub in SOCIAL else "other"  # noqa: E731
    rows = [{"code": r["sub"], "label": f"{r['sub']} {SHORT.get(r['sub'], r['sub'])}", "value": r["missed"] / r["n"],
             "count": f"{r['missed']} of {r['n']}", "m": r["missed"], "n": r["n"], **_roles(S[S["sub"] == r["sub"]]), "c": tone(r["sub"]), "group": tone(r["sub"]),
             "hash": _hash(off=BASE_OFF, flt=[{"mode": "subdomain", "lit": r["sub"]}], frm="social")}
            for r in sorted((r for r in risk if r["n"] >= FEW), key=lambda r: (-r["missed"] / r["n"], -r["n"]))]
    group_link = lambda g, frm, arrange="timeline": _hash(arrange=arrange, off=BASE_OFF, frm=frm,  # noqa: E731
                                                           flt=[{"mode": "harmgroup", "off": [x for x in ("system", "social", "representational", "other") if x != g]}])
    not_how = lambda *keep: [x for x in ("Reported", "Revised", "Retained", "Added", "Removed", "Absent", *UNMATCHED) if x not in keep]  # noqa: E731
    not_rev = lambda keep: [x for x in ("incident_specific", "risk_type_specific", "unspecific", "none") if x != keep]  # noqa: E731
    revised_cov = [ONLY_COVERED, {"mode": "outcome", "off": not_how("Revised")}]
    next_filing = [
        {"k": "retained", "label": "Text unchanged", "n": s["retained"], "share": s["retained_share"], "c": "--seg-retained",
         "what": "The disclosure stays word for word the same.", "hash": _hash(color="outcome", off=not_how("Retained"), flt=[ONLY_COVERED], frm="named")},
        {"k": "unspecific", "label": "Rewritten in general terms", "n": s["unspecific"], "share": s["unspecific_share"], "c": "--seg-unspecific",
         "what": "The new text says nothing about the incident's AI risk, or only the wording changes.",
         "hash": _hash(color="revision", off=not_rev("unspecific"), flt=revised_cov, frm="named")},
        {"k": "risk", "label": "Rewritten about this AI risk", "n": s["risk_specific"], "share": s["risk_specific_share"], "c": "--seg-risk",
         "what": "The new text adds the incident's kind of AI risk in general terms.",
         "hash": _hash(color="revision", off=not_rev("risk_type_specific"), flt=revised_cov, frm="named")},
        {"k": "incident", "label": "Rewritten to name the incident", "n": s["incident_specific"], "share": _pc(int(s["incident_specific"]), s["n_covered"]), "c": "--seg-incident",
         "what": "The new text names the incident's technology, product, feature or harm.",
         "hash": _hash(color="revision", off=not_rev("incident_specific"), flt=revised_cov, frm="named")},
        {"k": "reported", "label": "Incident reported", "n": s["cov_reported"], "share": _pc(int(s["cov_reported"]), s["n_covered"]), "c": "--seg-reported",
         "what": "The AI actor reported the incident itself.", "hash": _hash(color="outcome", off=not_how("Reported"), flt=[ONLY_COVERED], frm="named")},
    ]
    top = sorted(a["top"], key=lambda c: -a["cov"][c] / a["tot"][c])
    actor_rows = [{"label": _short_actor(names[c]), "parts": {"AA": a["cov"][c], "UA": a["ed"][c], "UU": a["mis"][c]},
                   "value": _pc(a["cov"][c], a["tot"][c]), "n": _n(a["tot"][c]),
                   "hash": _hash(off=BASE_OFF, flt=[{"mode": "implicated", "lit": names[c]}], frm="actors")} for c in top]
    cov_r, ed_r, mis_r = (sum(a[k][c] for c in a["rest"]) for k in ("cov", "ed", "mis"))
    actor_rows.append({"label": f"Other {s['actors_other']} AI actors", "parts": {"AA": cov_r, "UA": ed_r, "UU": mis_r},
                       "value": _pc(cov_r, cov_r + ed_r + mis_r), "n": _n(cov_r + ed_r + mis_r)})
    # one dot per incident: an incident shared between AI actors is counted in shares, so the dots are rounded by largest
    # remainder within each kind, which keeps each kind's total (845, 99, 950)
    for k in ("AA", "UA", "UU"):
        vals = [r["parts"][k] for r in actor_rows]
        whole = [int(v) for v in vals]
        for i in sorted(range(len(vals)), key=lambda i: whole[i] - vals[i])[:round(sum(vals)) - sum(whole)]:
            whole[i] += 1
        for r, w in zip(actor_rows, whole):
            r.setdefault("dots", {})[k] = w
    n_not_prev, n_missed, n_ed = (int(s[k].replace(",", "")) for k in ("not_prev", "missed", "eventually"))
    not_previously = [
        {"k": "UA", "label": "AI risk disclosed after the incident", "n": s["eventually"], "share": _pc(n_ed, n_not_prev), "c": "--qua", "what": "not disclosed before the incident, disclosed after it", "hash": only("UA", "eventually")},
        {"k": "UU", "label": "AI risk still not disclosed in the next filing after the incident", "n": s["missed"], "share": _pc(n_missed, n_not_prev), "c": "--quu", "what": "disclosed neither before nor after the incident", "hash": only("UU", "eventually")},
    ]

    # --- the findings, with their weights (the module's docstring): each expected about 0
    pc_of = lambda x: int(x.rstrip("%"))                                       # noqa: E731
    n_cov = s["n_covered"]
    unnamed = round(100 * (n_cov - int(s["cov_reported"]) - int(s["incident_specific"])) / n_cov)
    still = round(100 * n_missed / n_not_prev)
    social = pc_of(s["social_share"])
    social_before, social_since = pc_of(_share(s["social_before"])), pc_of(_share(s["social_since"]))
    rep_before, rep_since = pc_of(s["rep_before_share"]), pc_of(s["rep_since_share"])
    sy = S[S.group == "system"]
    sys_before, sys_since = (pc_of(_share(_of(d))) for d in (sy[sy.year < 2024], sy[sy.year >= 2024]))
    if f"{sys_since}%" != s["system_late_share"]:                              # the paper's 2024-26 share
        raise SystemExit(f"findings: system failures since 2024 are {sys_since}%, the paper {s['system_late_share']}")
    up = lambda of: (lambda a, b: round(100 * (b - a) / b))(*(int(v.replace(",", "")) for v in of.split("/")))   # noqa: E731  the share disclosed, from the counts
    d_rep, d_soc = (up(s["rep_before"]), up(s["rep_since"])), (up(s["social_before"]), up(s["social_since"]))
    d_sys = (up(_of(sy[sy.year < 2024])), up(_of(sy[sy.year >= 2024])))
    series = _year_series(S)
    for x in series:                                                          # the legend leads to the incidents
        x["hash"] = group_link(x["k"], "wave", "timeline") if x["k"] != "all" else _hash(arrange="timeline", off=BASE_OFF, frm="wave")
    items = [                                       # in the order the user set on 6 Nov; the weights stay for reference
        {"id": "social", "weight": social, "headline": f"{social}% of harms to information, democracy and power go undisclosed",
         "text": f"For {_ofw(s['social'])} such incidents, the AI risk was disclosed neither before nor after the incident. When the AI system itself fails or is attacked, this holds for {s['system_share']} ({_ofw(s['system'])}).",
         # red: disclosed neither before nor after; blue: the rest, disclosed before or after; the AI risk types in three groups
         # the AI risk types with at least FEW incidents; the page's notes say so
         # the share lines at the right (user, 6 Nov): red, not disclosed, over a thinner blue, disclosed; the MIT repository as a footnote
         # the share panel at the right dropped (user, 6 Nov): the dots alone
         "chart": {"kind": "rows", "axis": "One dot per incident, by AI risk type", "head": "AI risk type",
                   "refs": [{"fn": 1, "text": "AI risk types: MIT AI Risk Repository", "url": "https://airisk.mit.edu"}], "max": 1, "rows": rows,
                   "legend": [{"k": "out", "label": "AI risk disclosed neither before nor after", "c": "--quu"}, {"k": "in", "label": "AI risk disclosed before or after", "c": "--qaa"}],
                   # harms to information on top, the other AI risk types in the middle without a heading, system failures at the foot (user, 6 Nov)
                   "sections": [{"k": "social", "label": "Harms to information, democracy and power", "hash": group_link("social", "social")},
                                {"k": "other", "label": ""},
                                {"k": "system", "label": "AI system fails or is attacked", "hash": group_link("system", "social")}]}},
        {"id": "wave", "weight": (rep_before - rep_since) - (social_before - social_since), "headline": "Since 2024, AI actors disclose more AI risks, but not harms to information, democracy and power",
         "text": f"Since 2024, the share of incidents whose AI risk was disclosed before or after rose from {d_rep[0]}% to {d_rep[1]}% for discrimination or toxic content against groups and from {d_sys[0]}% to {d_sys[1]}% when the AI system fails or is attacked, but only from {d_soc[0]}% to {d_soc[1]}% for harms to information, democracy and power. "
                 "The chart runs by the year the incident started, and 2026 shows its first half.",
         "chart": {"kind": "lines", "axis": "Share disclosed before or after", "series": series, "few": FEW, "few_label": f"Fewer than {FEW} incidents",
                   "events": [{"x": pd.Timestamp(d).year + (pd.Timestamp(d).dayofyear - 1) / 365.25, "label": lab, "fn": i + 1} for i, (d, lab) in enumerate(EVENTS)],
                   "refs": [{"fn": i + 1, "text": text, "url": url} for i, (text, url) in enumerate(EVENT_REFS)]}},
        {"id": "actors", "weight": pc_of(s["tesla_prev"]) - pc_of(s["meta_prev"]),
         "headline": f"Eight AI actors disclosed the AI risk of {s['eight_prev']} of their incidents beforehand, the other {s['actors_other']} only {s['others_prev']}",
         "text": f"The eight account for {s['eight_hold']} of the {s['disclosed']} incidents whose AI risk was disclosed ({s['eight_share']}), and disclosure beforehand ranges from {s['meta_prev']} at Meta to {s['tesla_prev']} at Tesla. "
                 "An incident with several AI actors is shared between them.",
         # the share panel at the right dropped (user, 6 Nov): the dots alone
         "chart": {"kind": "stack", "head": "Number of incidents", "axis": "One dot per incident", "rows": actor_rows,
                   "legend": [{"k": "AA", "label": "AI risk disclosed before and after the incident", "c": "--qaa"}, {"k": "UA", "label": "AI risk disclosed only after the incident", "c": "--qua"},
                              {"k": "UU", "label": "AI risk disclosed neither before nor after the incident", "c": "--quu"}]}},
        {"id": "eventually", "weight": still, "headline": f"When an AI risk was not disclosed before an incident, {still}% stay undisclosed in the next filing",   # the next filing (user, 6 Nov)
         "text": f"For {s['not_prev']} incidents, the AI risk was not in the AI actor's SEC filings when the incident started. "
                 f"For only {s['eventually']} of them, it appears in the next filing or in a filing that responds to the incident.",
         # one dot per incident: all start red, those disclosed after move out to the right and turn blue
         "chart": {"kind": "dots", "total": s["not_prev"], "start": "AI risk not disclosed before the incident", "parts": not_previously}},
        {"id": "named", "weight": unnamed, "headline": f"AI actors rarely refer to incidents of their AI systems, even where they disclosed the AI risk: {unnamed}% go unmentioned",
         "text": f"For {s['covered']} incidents, the AI actor disclosed the AI risk before and after the incident. "
                 f"It reported {s['cov_reported']} of them itself, and for {s['incident_specific']} more it rewrote its disclosure to name the incident's technology, product, feature or harm. "
                 f"For the other {_n(n_cov - int(s['cov_reported']) - int(s['incident_specific']))}, the filing keeps its text or rewrites it without referring to the incident.",
         "chart": {"kind": "split", "total": s["covered"], "start": "AI risk disclosed before and after the incident", "c": "--qaa", "parts": next_filing}},
    ]
    return {
        "lead": lead, "story": _story(m, s), "found": f"What we found across all {s['matched']} matched incidents", "findings": items,
        # a disclaimer first: research, not a legal finding (user, 6 Nov)
        "notes": ["This is research, not legal advice. We compared the AI risks that AI actors disclose in their SEC filings with recorded AI incidents. "
                  "Not disclosed means only that the filings we read do not name an incident's AI risk. It is not a finding that any AI actor broke the law or that any filing is misleading.",
                  f"DISC links {s['all']} AI incidents to the SEC filings of the AI actors involved. {s['matched']} of them could be checked: an AI actor involved had an annual filing in force "
                  f"when the incident started and filed again after it. The other {s['unmatched']} could not be checked."],
        # each a view of Explore, shown by a screenshot of it (static/thumbs, taken from Explore itself)
        "explore": {"title": "Explore the data", "items": [
            {"label": "Over time", "what": "Every incident by when it started, coloured by what was disclosed",
             "img": "static/thumbs/timeline.webp", "hash": _hash(arrange="timeline", frm="explore")},
            {"label": "Disclosed before and after", "what": "Four boxes: the AI risk disclosed before the incident, after it, both or neither",
             "img": "static/thumbs/quadrants.webp", "hash": _hash(arrange="quadrants", frm="explore")},
            {"label": "Impact layers of AI incidents", "what": "Incidents by impact layer, from the AI system out to society",
             "img": "static/thumbs/layers.webp", "hash": _hash(arrange="layers", frm="explore")},
        ]},
        "docs": {"label": "Documentation", "view": "docs"},
        # the research paper under Explore the data: a placeholder until the arXiv preprint is posted (user, 6 Nov)
        "paper": {"title": "Research", "paper_title": PAPER_TITLE, "authors": PAPER_AUTHORS, "year": PAPER_YEAR,   # a citation, not a card (user, 6 Nov)
                  "venue": "arXiv preprint", "url": PAPER_URL, "soon": "Link to follow"},
    }


if __name__ == "__main__":
    bad = check()
    for name, paper, data in bad:
        print(f"  {name:28} paper {paper:12} data {data}")
    print(f"{len(PAPER) - len(bad)} of {len(PAPER)} numbers as in the paper")
    f = findings()
    terms = terminology(f)
    for term, instead, text in terms:
        print(f"  term {term!r}: write {instead}: {text[:110]}")
    print(f"terminology: {len(terms)} problems")
    for x in f["findings"]:
        print(f"{x['weight']:>3}  {x['headline']}")
    sys.exit(1 if bad or terms else 0)
