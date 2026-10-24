"""The DISC explorer: every incident by quadrant, over time and by impact layer, its labels with their
evidence and sources, and its AI actors' disclosure over time; and the release to download — read from
the released tables.

    python explorer/serve.py              # http://localhost:8765, reading data/
    python explorer/serve.py --port 9000

Serves explorer/index.html, six JSON routes and the downloads:

    /api/data            one row per incident, the MIT names, what each AI actor disclosed after each report
    /api/codes           the incidents' labels and when the harm began
    /api/incident/<id>   one incident: its labels with their quotes, the records and every article
    /api/case/<id>       its implicated AI actors' filings, coded passages and current reports over time
    /api/text/<acc>      a filing's risk-factor section, or a current report's AI excerpt
    /api/downloads       what the Download panel lists
    /files/<name>        a table, the documentation, the licence or a codebook it lists; /files/disc.zip all

Everything comes from the Parquet tables in data/ (docs/documentation.md). The page compares two filings
itself, from their texts; the texts are copied once into a local SQLite index (explorer/.cache/) so
that a comparison reads two texts, not the whole table; the index is built in the background at
start and rebuilt when the table changes. explorer/export.py writes the same answers as files, for
hosting the page without a server.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sqlite3
import sys
import threading
import zlib
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
INDEX = HERE / ".cache/risk_factors.sqlite"
ANNUAL = ("10-K", "20-F", "40-F")
CODED_FORMS, CODED_FROM = ("10-K", "20-F", "40-F"), "2016-01-01"   # read from 2016 where a risk-factor section exists
STATUS_RANK = {"hypothetical": 1, "elsewhere": 2, "materialised": 3}
ROLE = {"deployer": "deployer", "provider": "developer"}     # the page shows "developer" as provider (EU AI Act Art. 3(3))
KIND = {"annual risk factors": "annual", "10-Q risk factors": "10-Q", "current report": "8-K"}
LINKS = {"aiid": "AIID", "aiaaic": "AIAAIC", "oecd": "OECD AIM"}
TEXT = {"aiid": "AIID description", "aiaaic": "AIAAIC summary", "oecd": "OECD AIM summary"}
TEXT_SECTIONS = ("risk_factors", "ai_excerpt")           # what /api/text serves, in this order
INDEX_SCHEMA = "2"                                     # the SQLite index's layout; a change rebuilds it

_T: dict = {}
_IDX: dict = {"state": "idle", "rows": 0, "error": None}


def _v(x):
    """A Parquet value as JSON: NaN and NA to None, arrays to lists."""
    if x is None:
        return None
    if hasattr(x, "tolist") and not isinstance(x, str):
        return x.tolist()
    try:
        return None if pd.isna(x) else x
    except (TypeError, ValueError):
        return x


def table(name: str) -> list[dict]:
    if name not in _T:
        df = pd.read_parquet(DATA / f"{name}.parquet")
        _T[name] = [{k: _v(v) for k, v in r.items()} for r in df.to_dict("records")]
    return _T[name]


def version() -> str:
    try:
        return json.loads((HERE.parent / "croissant.json").read_text(encoding="utf-8")).get("version", "")
    except (OSError, json.JSONDecodeError):
        return ""


# ── the incident side ───────────────────────────────────────────────────────────────────────────────

def _cache() -> dict:
    if "by_incident" in _T:
        return _T["by_incident"]
    inc = {r["incident_id"]: r for r in table("incidents")}
    actors = defaultdict(list)
    for a in table("incident_actors"):
        actors[a["incident_id"]].append(a)
    ev = defaultdict(dict)
    for e in table("evidence"):
        ev[e["incident_id"]][e["label"]] = {"quote": e["quote"], "ref": e["ref"]}
    recs = defaultdict(list)
    for r in table("incident_records"):
        recs[r["incident_id"]].append(r)
    db = defaultdict(dict)                         # incident -> (source, label) -> the first record's values
    for x in table("source_labels"):
        db[x["incident_id"]].setdefault((x["source"], x["label"]), x["value"] or [])
    _T["by_incident"] = {"inc": inc, "actors": actors, "ev": ev, "recs": recs, "db": db}
    return _T["by_incident"]


def _articles(incident_id: str) -> list[dict]:
    if "arts" not in _T:
        a = pd.read_parquet(DATA / "articles.parquet")
        _T["arts"] = {k: g for k, g in a.groupby("incident_id")}
    g = _T["arts"].get(incident_id)
    if g is None:
        return []
    out = [{k: _v(v) for k, v in r.items()} for r in g.to_dict("records")]
    return sorted(out, key=lambda r: (r["ref"] is None, int(r["ref"][1:]) if r["ref"] else 0, r["published"] or ""))


DB_LABELS = {          # the databases' own labels (source_labels), in the order the card lists them
    ("aiid", "mit_domain"): "MIT risk domain", ("aiid", "mit_subdomain"): "MIT risk subdomain",
    ("aiid", "mit_entity"): "MIT entity", ("aiid", "mit_intent"): "MIT intent", ("aiid", "mit_timing"): "MIT timing",
    ("aiaaic", "sector"): "Sector", ("aiaaic", "technology"): "Technology", ("aiaaic", "purpose"): "Purpose",
    ("aiaaic", "harm_individual"): "Individual harm", ("aiaaic", "harm_societal"): "Societal harm",
    ("aiaaic", "harm_environmental"): "Environmental harm", ("aiaaic", "ethical_issue"): "Ethical issue",
    ("oecd", "harm_level"): "Incident or hazard", ("oecd", "harm_types"): "Harm types",
    ("oecd", "harmed_entities"): "Harmed entities", ("oecd", "autonomy_level"): "Autonomy level",
    ("oecd", "industries"): "Industries", ("oecd", "ai_tasks"): "AI tasks"}


STATUS = {"unknown": "Unclear", "described": "Unnamed", "personal_use": "Personal, non-professional use"}   # the page's words
REDACTED = {"[private individual]": "Private individual (name removed)"}       # the personal-data rule (docs/documentation.md)
LINK_RANK = {"incident_specific": 0, "risk_type_specific": 1, "unspecific": 2}


def _position(acts: list[dict], position: str) -> list[str]:
    """The parties coded in one position, or its status where none is named (codebook-attribution §3)."""
    a = next((a for a in acts if a["position"] == position), None)
    if a is None:
        return []
    if a["status"] == "named" and a["party"]:
        return sorted({REDACTED.get(x.strip(), x.strip()) for x in str(a["party"]).split(";") if x.strip()})
    return [STATUS.get(a["status"], f"({a['status']})")]


def _linked() -> dict:
    """incident -> the revision linked to it most closely (incident-specific, risk-type specific, unspecific):
    its revision type; and
    incident -> whether a passage anticipating it names a harm to the AI actor itself
    (passage_codes.registrant_harmed), for incidents with an anticipating passage."""
    if "linked" in _T:
        return _T["linked"]
    rev = {}
    for r in table("revisions"):
        for x in r["revision_types"] or []:
            i, _, link = x.rpartition(":")
            if i not in rev or LINK_RANK.get(link, 3) < LINK_RANK.get(rev[i], 3):
                rev[i] = link
    harmed = {p["passage_id"]: p["registrant_harmed"] for p in table("passage_codes")}
    own = {}
    for o in table("outcomes"):
        ps = o["anticipating_passages"] or []
        if ps:
            own[o["incident_id"]] = own.get(o["incident_id"], False) or any(harmed.get(p) for p in ps)
    _T["linked"] = {"rev": rev, "own": own}
    return _T["linked"]


def rows() -> list[dict]:
    """One row per incident, with what the page draws and filters by; the labels come from codes()."""
    c = _cache()
    lk = _linked()
    out = []
    for i, r in c["inc"].items():
        acts = c["actors"].get(i, [])
        out.append({"id": i, "d": r["record_date"], "t": r["title"],
                    "xa": [[a["cik"], ROLE[a["position"]]] for a in acts if a["cik"] and a["position"] in ROLE],
                    "qd": [next((k for k, v in {"AA": "Covered", "AU": "Dropped", "UA": "Fixed", "UU": "Missed"}.items()
                                 if v == r["quadrant"]), None) or r["where"], r["how"]] if (r["quadrant"] or r["where"]) else None,
                    "dep": _position(acts, "deployer"), "pro": _position(acts, "provider"),
                    "up": _position(acts, "upstream_provider"), "rv": lk["rev"].get(i), "rh": lk["own"].get(i)})
    return out


def codes() -> dict:
    c = _cache()
    out, dates = {}, {}
    for i, r in c["inc"].items():
        out[i] = {"layer": r["impact_layer"], "mit": r["mit_subdomain"], "subj": r["subject_type"],
                  "harm": r["harm_types"] or [], "aut": r["autonomy_level"], "rel": r["relation"], "by": r["misuse_by"],
                  "cap": r["use_capability"], "tech": r["use_technique"], "dom": r["use_domains"] or []}
        if r["started"]:
            dates[i] = [r["started"], r["started_precision"], r["started_bound"] or "exact"]
    return {"codes": out, "files": [{"file": f"DISC {version()}", "coder": "final", "n": len(out), "mtime": 0}],
            "n_double": 0, "n_final": len(out), "dates": dates}


def detail(incident_id: str) -> dict | None:
    c = _cache()
    r = c["inc"].get(incident_id)
    if r is None:
        return None
    ev, acts, recs = c["ev"].get(incident_id, {}), c["actors"].get(incident_id, []), c["recs"].get(incident_id, [])
    q = lambda label: ev.get(label) or {}                                   # noqa: E731
    pos = {a["position"]: a for a in acts}
    rec = {"impact_layer": {"layer": r["impact_layer"], **q("impact_layer")},
           "mit": {"subdomain": r["mit_subdomain"], **q("mit_subdomain")},
           "subject": {"status": r["subject_status"], "type": r["subject_type"], "who": r["subject_who"], **q("subject")},
           "harm_types": {"types": r["harm_types"] or [], **q("harm_types")},
           "autonomy": {"level": r["autonomy_level"], **q("autonomy_level")},
           "use": {"intended_purpose": r["intended_purpose"], "purpose_quote": q("intended_purpose").get("quote"),
                   "purpose_ref": q("intended_purpose").get("ref"), "relation": r["relation"], "misuse_by": r["misuse_by"],
                   "relation_quote": q("relation").get("quote"), "relation_ref": q("relation").get("ref")},
           **{p: {"party": (pos.get(p) or {}).get("party"), "status": (pos.get(p) or {}).get("status"),
                  "acting_as": (pos.get(p) or {}).get("acting_as"), **q(p)}
              for p in ("deployer", "provider", "upstream_provider")},
           }
    hb = {"date": r["started"], "precision": r["started_precision"], "bound": r["started_bound"],
          "source": "coded", **q("started")} if r["started"] or q("started") else None
    db = c["db"].get(incident_id, {})
    return {"id": incident_id, "ev": incident_id, "d": r["record_date"], "t": r["title"],
            "src": [s for s in ("aiid", "aiaaic", "oecd") if r[f"in_{s}"]], "win": True,
            "links": [[f"{LINKS[x['source']]} {x['record_id']}", x["url"]] for x in recs if x["url"]],
            "text": [[TEXT[x["source"]], x["description"]] for x in recs if x["description"]],
            "db": [[LINKS[k[0]], name, "; ".join(db[k])] for k, name in DB_LABELS.items() if db.get(k)],
            "actors": [[a["party"], ROLE.get(a["position"], a["position"])] for a in acts
                                 if a["party"] and a["status"] == "named"][:12],
            "use_coded": {"capability": {"verb": r["use_capability"], **q("use_capability")},
                          "technique": {"technique": r["use_technique"], **q("use_technique")},
                          "domain": {"domains": r["use_domains"] or [], **q("use_domains")}},
            "harm_began": hb, "coders": {"A": rec},
            "articles": _articles(incident_id)}


# ── the disclosure side ─────────────────────────────────────────────────────────────────────────────

def regs() -> dict:
    if "regs" in _T:
        return _T["regs"]
    names = {a["cik"]: a["sec_name"] or a["name"] for a in table("actors") if a["cik"]}
    regime = {a["cik"]: a["regime"] for a in table("actors") if a["cik"]}
    out: dict[int, dict] = {}
    for f in sorted(table("filings"), key=lambda f: f["filing_date"]):
        reg = out.setdefault(f["cik"], {"cik": f["cik"], "name": names.get(f["cik"], str(f["cik"])),
                                        "regime": regime.get(f["cik"]), "processed": True, "filings": [],
                                        "passages": [], "k8": []})
        if f["form"] != "DEF 14A":
            reg["filings"].append({"acc": f["accession"], "form": f["form"], "date": f["filing_date"], "url": f["url"],
                                   "rf_words": f["risk_factor_words"], "rf_ai": None, "rf_method": None,
                                   "txt": f["accession"] in texted()})
    text = {p["passage_id"]: (p["text"], p["channel"], p["cik"]) for p in table("passages")}
    ev = defaultdict(dict)
    for e in table("passage_evidence"):
        ev[e["passage_id"]][e["label"]] = e["quote"]
    rev = {}
    for r in table("revisions"):
        old, new = text.get(r["replaces"] or "", ("",))[0], text.get(r["unit_id"], ("",))[0]
        rev[r["unit_id"]] = {**{k: r[k] for k in ("about", "domain_of_change",
                                                  "domains_before", "domains_after")},
                             "links": {x.split(":")[0]: {"link": x.split(":", 1)[1]} for x in r["revision_types"] or []},
                             "old": old}                     # the page marks what changed in the passage itself
    reps = defaultdict(list)
    for x in table("passage_filings"):
        reps[x["passage_id"]].append((x["filing_date"], x["accession"], x["form"]))
    for p in table("passage_codes"):
        t, ch, cik = text.get(p["passage_id"], ("", None, None))
        kind, reg = KIND.get(ch), out.get(cik)
        if kind is None or reg is None:                 # legal passages are not drawn on the timeline
            continue
        rs = sorted(set(reps.get(p["passage_id"], [])))
        if not rs:
            continue
        e = ev.get(p["passage_id"], {})
        rec = {"id": p["passage_id"], "kind": kind, "source": None, "discloses": p["discloses"],
               "mit": p["mit_subdomains"] or [], "primary": p["mit_primary"], "status": p["status"],
               "harm": p["harm_types"] or [], "layers": p["impact_layers"] or [], "whose": p["whose_ai"] or [],
               "relation": p["relation"] or [], "misuse_by": p["misuse_by"] or [],
               "subjects": [{"name": s.rsplit(":", 1)[0], "type": s.rsplit(":", 1)[-1]} for s in p["subjects"] or []],
               "text": t, "ev": e, "rev": rev.get(p["passage_id"]),
               "harm_quote": next((q for k, q in e.items() if k.startswith(("mit:", "harm:"))), None),
               "status_quote": e.get("status"),
               "reports": [a for _, a, _ in rs], "forms": {f: sum(x == f for _, _, x in rs) for f in {x for _, _, x in rs}},
               "first": rs[0][0], "last": rs[-1][0]}
        (reg["k8"] if kind == "8-K" else reg["passages"]).append(rec)
    for reg in out.values():
        annual = [f for f in reg["filings"] if f["form"] in ANNUAL]
        reg["annual"] = annual
        by_acc = defaultdict(list)
        for p in reg["passages"] + reg["k8"]:
            nxt = next((f for f in annual if f["date"] > p["last"]), None)
            p["end"] = None if p["kind"] == "8-K" else (nxt["date"] if nxt else None)
            for a in p["reports"]:
                by_acc[a].append(p)
        reg["by_acc"] = by_acc
    _T["regs"] = out
    return out


def is_coded(reg: dict, f: dict) -> bool:
    if f["form"] in ("8-K", "6-K"):
        return bool(reg["by_acc"].get(f["acc"]))
    return f["form"] in (*CODED_FORMS, "10-Q") and f["date"] >= CODED_FROM and bool(f["rf_words"])


def _report(reg: dict, f: dict) -> list:
    if not is_coded(reg, f):
        return [f["date"], "nc", False, {}]
    subs, ai = {}, False
    for p in reg["by_acc"].get(f["acc"], []):
        if p["discloses"] == "ai_harm":
            ai = True
            for s in p["mit"]:
                subs[s] = max(subs.get(s, 0), STATUS_RANK.get(p["status"], 1))
    return [f["date"], "coded", ai, subs]


def annual_table() -> dict:
    """cik -> what is disclosed after each annual report and each coded 10-Q: the last annual report
    plus every 10-Q since."""
    out = {}
    for cik, reg in regs().items():
        if not reg["annual"]:
            continue
        states, base = [], None
        for f in reg["filings"]:
            if f["form"] in ANNUAL:
                base = _report(reg, f)
                states.append(base)
            elif f["form"] == "10-Q" and base and base[1] == "coded" and is_coded(reg, f):
                q = _report(reg, f)
                subs = dict(base[3])
                for s_, r in q[3].items():
                    subs[s_] = max(subs.get(s_, 0), r)
                base = [f["date"], "coded", base[2] or q[2], subs]
                states.append(base)
        out[cik] = states
    return out


def case(incident_id: str) -> dict | None:
    c = _cache()
    r = c["inc"].get(incident_id)
    if r is None:
        return None
    rg = regs()
    acts = c["actors"].get(incident_id, [])
    names = {a["cik"]: a["sec_name"] or a["name"] for a in table("actors") if a["cik"]}
    resp = [{"cik": x["cik"], "name": names.get(x["cik"], ""), "acc": x["accession"], "date": x["filing_date"],
             "form": x["form"], "responds": bool(x["responds"]), "quote": x["quote"],
             "basis": None if x["read"] else "no excerpt"}
            for x in table("responses") if x["incident_id"] == incident_id]
    roles = defaultdict(set)
    for a in acts:
        if a["cik"] and a["cik"] in rg and a["position"] in ROLE:
            roles[a["cik"]].add(ROLE[a["position"]])
    lanes = []
    for cik, rs in roles.items():
        reg = rg[cik]
        filings = [{**f, "coded": is_coded(reg, f),
                    "n_ai_harm": sum(p["discloses"] == "ai_harm" for p in reg["by_acc"].get(f["acc"], [])),
                    "n_passages": len(reg["by_acc"].get(f["acc"], []))} for f in reg["filings"]]
        lanes.append({"cik": cik, "name": reg["name"], "regime": reg["regime"], "processed": True,
                      "roles": sorted(rs), "filings": filings, "passages": reg["passages"], "k8": reg["k8"],
                      "dropped": None})
    lanes.sort(key=lambda l: l["name"])
    others = sorted([a["party"], ROLE[a["position"]]] for a in acts
                    if a["position"] in ROLE and not a["cik"] and a["status"] == "named" and a["party"])
    return {"id": incident_id, "event": incident_id, "date": r["record_date"], "lanes": lanes, "has_10q": True,
            "responses": resp, "responses_coded": bool(resp), "others": others, "index": index_status()}


# ── the texts the page compares ─────────────────────────────────────────────────────────────────────

SECTIONS = "risk_factor_sections"                 # one Parquet file per filing year (src/disc.py)


def _sources() -> list[Path]:
    return sorted(DATA.glob(f"{SECTIONS}_*.parquet"))


def _source_key() -> str:
    """Which build of the filing texts the index holds: the yearly files' names and times."""
    return hashlib.sha1("|".join(f"{p.name}:{p.stat().st_mtime_ns}" for p in _sources()).encode()).hexdigest()


def texted() -> set[str]:
    """The filings with a text to compare: a risk-factor section, or a current report's AI excerpt."""
    if "texted" not in _T:
        import pyarrow as pa
        import pyarrow.compute as pc
        import pyarrow.parquet as pq
        t = pa.concat_tables([pq.read_table(p, columns=["accession", "section", "text"]) for p in _sources()])
        keep = pc.and_(pc.is_in(t["section"], value_set=pa.array(TEXT_SECTIONS)),
                       pc.greater(pc.utf8_length(pc.fill_null(t["text"], "")), 0))
        _T["texted"] = set(t.filter(keep)["accession"].to_pylist())
    return _T["texted"]


def index_status() -> dict:
    if _IDX["state"] in ("idle", "ready") and INDEX.exists():
        try:
            db = sqlite3.connect(INDEX)
            built = db.execute("SELECT source FROM meta").fetchone()[0]
            db.close()
        except sqlite3.Error:
            built = None
        _IDX["state"] = "ready" if built == f"{_source_key()}|{INDEX_SCHEMA}" else "stale"
    return dict(_IDX)


def build_index() -> None:
    if index_status()["state"] in ("ready", "building"):
        return
    _IDX.update(state="building", rows=0, error=None)

    def run() -> None:
        try:
            import pyarrow.parquet as pq
            INDEX.parent.mkdir(parents=True, exist_ok=True)
            tmp = INDEX.with_suffix(".tmp")
            tmp.unlink(missing_ok=True)
            db = sqlite3.connect(tmp)
            db.execute("CREATE TABLE rf (accession TEXT, section TEXT, text BLOB, PRIMARY KEY (accession, section))")
            batches = (b for p in _sources() for b in pq.ParquetFile(p).iter_batches(batch_size=500, columns=["accession", "section", "text"]))
            for batch in batches:
                b = batch.to_pandas()
                b = b[b["section"].isin(TEXT_SECTIONS)].fillna({"text": ""})
                db.executemany("INSERT OR REPLACE INTO rf VALUES (?,?,?)",
                               [(x.accession, x.section, zlib.compress(x.text.encode())) for x in b.itertuples()])
                _IDX["rows"] += len(b)
            db.execute("CREATE TABLE meta (source TEXT)")
            db.execute("INSERT INTO meta VALUES (?)", (f"{_source_key()}|{INDEX_SCHEMA}",))
            db.commit()
            db.close()
            tmp.replace(INDEX)
            _IDX["state"] = "ready"
        except Exception as e:                                # the page says it failed; the reason stays here
            print(f"risk-factor index failed: {e!r}", file=sys.stderr, flush=True)
            _IDX.update(state="failed", error="the risk-factor index could not be built")

    threading.Thread(target=run, daemon=True).start()


def section(accession: str) -> str | None:
    """A filing's text: its risk-factor section, else its AI excerpt (a current report has only that)."""
    db = sqlite3.connect(INDEX)
    rows_ = dict(db.execute("SELECT section, text FROM rf WHERE accession = ?", (accession,)).fetchall())
    db.close()
    t = next((rows_[k] for k in TEXT_SECTIONS if rows_.get(k) is not None), None)
    return zlib.decompress(t).decode() if t is not None else None


def text(accession: str) -> dict:
    st = index_status()
    if st["state"] == "stale":
        build_index()
        return {"index": index_status()}
    if st["state"] != "ready":
        return {"index": st}
    t = section(accession)
    return {"index": st, "acc": accession, "text": t} if t is not None else \
        {"index": st, "error": f"no risk-factor text or AI excerpt for {accession}"}


# ── downloads ───────────────────────────────────────────────────────────────────────────────────────

DOCS = HERE.parent / "docs"
DOC_FILES = (("docs/documentation.md", "Documentation"), ("LICENSE", "Licence (CC BY-SA 4.0)"))
CODEBOOKS = (("docs/codebook-incidents.md", "Incidents"), ("docs/codebook-disclosures.md", "Disclosures"))


def downloads() -> dict:
    """What the Download panel lists: each table (Parquet) with its rows and what one row is (the Files
    table of docs/documentation.md, in its order), the filing texts by year (not in the zip), the
    documentation, the licence and the codebooks. `file` is the site's path (files/<name>), `repo` the
    path in the release repository."""
    import pyarrow.parquet as pq
    about = dict(re.findall(r"^\| `(\w+)` \| ([^|`]+?) \|$", (DOCS / "documentation.md").read_text(encoding="utf-8"), re.M))
    tables = [{"name": p.stem, "file": f"files/{p.name}", "repo": f"data/{p.name}", "bytes": p.stat().st_size,
               "rows": pq.ParquetFile(p).metadata.num_rows, "about": about.get(p.stem, "")}
              for p in sorted(DATA.glob("*.parquet")) if not p.stem.startswith(SECTIONS)]
    order = list(about)
    tables.sort(key=lambda t: order.index(t["name"]) if t["name"] in order else len(order))
    sections = [{"name": p.stem, "year": p.stem[-4:], "file": f"files/{p.name}", "repo": f"data/{p.name}",
                 "bytes": p.stat().st_size, "rows": pq.ParquetFile(p).metadata.num_rows} for p in _sources()]
    doc = lambda rel, title: {"name": Path(rel).name, "title": title, "file": f"files/{Path(rel).name}",   # noqa: E731
                              "repo": rel, "bytes": (HERE.parent / rel).stat().st_size}
    return {"version": version(), "archive": f"files/{ARCHIVE}", "tables": tables, "sections": sections,
            "docs": [doc(r, t) for r, t in DOC_FILES], "codebooks": [doc(r, t) for r, t in CODEBOOKS]}


ARCHIVE = "disc.zip"
OFFERED_DOCS = {Path(r).name: r for r, _ in DOC_FILES + CODEBOOKS}


def archive(fh) -> None:
    """The dataset as one zip, under disc/: the tables downloads() lists in data/, the licence, and the
    documentation and codebooks in docs/, as in the release."""
    import zipfile
    d = downloads()
    with zipfile.ZipFile(fh, "w", zipfile.ZIP_STORED) as z:                  # Parquet is compressed already
        for f in d["tables"]:
            z.write(download_path(f["file"].removeprefix("files/")), f"disc/data/{f['name']}.parquet")
        for name, rel in OFFERED_DOCS.items():
            z.write(HERE.parent / rel, f"disc/{rel}")


def download_path(name: str) -> Path | None:
    """files/<name> -> the file on disk, for the names downloads() lists only."""
    if name in OFFERED_DOCS:
        return HERE.parent / OFFERED_DOCS[name]
    p = DATA / name
    return p if p.suffix == ".parquet" and p.parent == DATA and p.exists() else None


# ── the page and its assets ─────────────────────────────────────────────────────────────────────────

STATIC_DIR = HERE / "static"                      # the scripts and fonts the page loads, with their licences
STATIC_TYPES = {".js": "text/javascript; charset=utf-8", ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8"}
CSP_INLINE = "'sha256-INLINE'"
FONT_URL = re.compile(r"url\(static/fonts/([\w.-]+\.woff2)\)")


def page(static: bool = False) -> str:
    """index.html as served (static=False) or exported (static=True): STATIC set, and the Content Security
    Policy naming the one inline script by its hash, so that no other inline script can run. The exported
    page carries its fonts inline: sandboxed without an origin of its own (Anonymous GitHub), it may not
    fetch them."""
    html = (HERE / "index.html").read_text(encoding="utf-8")
    if html.count("const STATIC = false;") != 1 or html.count(CSP_INLINE) != 1:
        raise SystemExit("index.html: expected one `const STATIC = false;` and one CSP placeholder")
    if static:
        html = html.replace("const STATIC = false;", "const STATIC = true;").replace("font-src 'self';", "font-src 'self' data:;")
        html = FONT_URL.sub(lambda m: "url(data:font/woff2;base64,"
                            + base64.b64encode((STATIC_DIR / "fonts" / m.group(1)).read_bytes()).decode() + ")", html)
    inline = re.findall(r"<script>(.*?)</script>", html, re.S)
    if len(inline) != 1:
        raise SystemExit(f"index.html: expected one inline script, found {len(inline)}")
    digest = base64.b64encode(hashlib.sha256(inline[0].encode()).digest()).decode()
    return html.replace(CSP_INLINE, f"'sha256-{digest}'")


def static_path(rel: str) -> Path | None:
    """static/<rel> -> the file, for files inside static/ of the types above only."""
    p = (STATIC_DIR / rel).resolve()
    return p if p.is_file() and STATIC_DIR.resolve() in p.parents and p.suffix in STATIC_TYPES else None


# ── the server ──────────────────────────────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, ctype: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, status: int = 200) -> None:
        self._send(json.dumps(obj, ensure_ascii=False, default=str).encode(), "application/json; charset=utf-8", status)

    def do_GET(self) -> None:
        url = urlsplit(self.path)
        path = unquote(url.path)
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
        if host not in ("localhost", "127.0.0.1", "::1"):               # no other site's page can reach it
            self._send(b"forbidden", "text/plain", 403)
            return
        if path in ("/", "/index.html"):
            self._send(page().encode(), "text/html; charset=utf-8")
        elif path.startswith("/static/") and (p := static_path(path.removeprefix("/static/"))):
            self._send(p.read_bytes(), STATIC_TYPES[p.suffix])
        elif path == "/api/data":
            mit = table("mit_taxonomy")
            self._json({"rows": rows(), "domains": {m["domain"]: m["domain_name"] for m in mit},
                        "subdomains": {m["code"]: m["name"] for m in mit}, "annual": annual_table(), "has_10q": True,
                        "regnames": {cik: r["name"] for cik, r in regs().items()}, "version": version()})
        elif path == "/api/codes":
            self._json(codes())
        elif path.startswith("/api/case/"):
            d = case(path.rsplit("/", 1)[-1])
            self._json(d if d else {"error": "unknown incident"}, 200 if d else 404)
        elif path.startswith("/api/text/"):
            self._json(text(path.rsplit("/", 1)[-1]))
        elif path.startswith("/api/incident/"):
            d = detail(path.rsplit("/", 1)[-1])
            self._json(d if d else {"error": "unknown incident"}, 200 if d else 404)
        elif path == "/api/downloads":
            self._json(downloads())
        elif path == f"/files/{ARCHIVE}":
            if "zip" not in _T:
                import io
                archive(buf := io.BytesIO())
                _T["zip"] = buf.getvalue()
            self._send(_T["zip"], "application/zip")
        elif path.startswith("/files/") and (p := download_path(path.removeprefix("/files/"))):
            self._send(p.read_bytes(), "text/markdown; charset=utf-8" if p.suffix == ".md"
                       else "text/plain; charset=utf-8" if p.name == "LICENSE" else "application/octet-stream")
        else:
            self._send(b"not found", "text/plain", 404)

    def log_message(self, fmt, *args) -> None:
        if not self.path.startswith("/api/codes"):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8765)
    port = ap.parse_args().port
    print(f"DISC {version()}: {len(rows()):,} incidents, {len(regs())} AI actors' filings", flush=True)
    build_index()
    print(f"risk-factor index: {index_status()['state']}", flush=True)
    print(f"http://localhost:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
