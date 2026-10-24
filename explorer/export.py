"""The explorer as a static site, for hosting without a server: Anonymous GitHub, GitHub Pages, any host.

    python explorer/export.py                              # -> explorer/site/, the downloads copied into files/
    python explorer/export.py --out docs/explorer --repo-path docs/explorer
                                                           # the site inside the release repository: the
                                                           # downloads are the repository's data/, docs/, LICENSE

Writes what serve.py's routes answer as scripts that hand their data to the page (`__disc(key, data)`): a
page sandboxed without an origin of its own, as Anonymous GitHub's /w/ view serves it, may load scripts
where every fetch is refused. The page is serve.page(static=True), with STATIC set and the fonts inline.

    static/                           the scripts the page loads, and the licences of scripts and fonts
    api/data.js, api/codes.js         as /api/data and /api/codes
    api/incident/<id>.js              as /api/incident/<id>
    api/case/<id>.js                  as /api/case/<id>, each AI actor reduced to its cik and roles
    api/actor/<cik>.js                an AI actor's filings, coded passages and current reports, which
                                      every case of that AI actor shares
    texts/<hash>.js                   each distinct text the page can compare, once, gzip-compressed and
                                      base64-encoded: a filing's risk-factor section, or a current report's AI excerpt
    api/downloads.js                  the Download panel: the tables, the filing texts by year, the
                                      documentation, LICENSE and the codebooks (with their texts), and the zip
    files/                            files/disc.zip with the tables and docs; without --repo-path also a copy
                                      of every file the panel lists. Never croissant.json or metadata.json.

Serve the folder with any static server (`python -m http.server -d explorer/site`); the release keeps its copy
in docs/explorer/, which docs/index.html forwards to (GitHub Pages and Anonymous GitHub publish docs/).
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import posixpath
import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

import serve

MARK = ".disc-explorer-site"                      # a folder export.py may empty and refill


def _dump(out: Path, rel: str, obj) -> int:
    """api/x.json -> out/api/x.js: a script handing obj to the page under the key "api/x"."""
    key = rel.removesuffix(".json")
    path = out / f"{key}.js"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)
    b = f"__disc({json.dumps(key)},{data});\n".encode()
    path.write_bytes(b)
    return len(b)


def _texts(accessions: set[str]) -> dict[str, str]:
    """accession -> its text: the risk-factor section, else the AI excerpt (serve.TEXT_SECTIONS)."""
    t = pa.concat_tables([pq.read_table(p, columns=["accession", "section", "text"],
                                        filters=[("accession", "in", sorted(accessions)), ("section", "in", list(serve.TEXT_SECTIONS))])
                          for p in serve._sources()])
    by = {}
    for acc, sec, text in zip(*(t[c].to_pylist() for c in ("accession", "section", "text"))):
        if text:
            by.setdefault(acc, {})[sec] = text
    return {acc: next(s[k] for k in serve.TEXT_SECTIONS if k in s) for acc, s in by.items()}


def export(out: Path, repo_path: str | None = None) -> None:
    if out.exists():
        if not (out / MARK).exists():
            raise SystemExit(f"{out} exists and is not an exported site; choose another --out")
        shutil.rmtree(out)
    (out / "api").mkdir(parents=True)
    (out / MARK).write_text("written by explorer/export.py; emptied and refilled at each export\n")
    size = 0
    (out / "index.html").write_text(serve.page(static=True), encoding="utf-8")
    shutil.copytree(serve.STATIC_DIR, out / "static",               # the fonts are inline in the page
                    ignore=lambda d, names: [n for n in names if (Path(d) / n).is_file() and Path(n).suffix not in (".js", ".txt")])
    mit = serve.table("mit_taxonomy")
    size += _dump(out, "api/data.json", {
        "rows": serve.rows(), "domains": {m["domain"]: m["domain_name"] for m in mit},
        "subdomains": {m["code"]: m["name"] for m in mit}, "annual": serve.annual_table(), "has_10q": True,
        "regnames": {cik: r["name"] for cik, r in serve.regs().items()}, "version": serve.version()})
    size += _dump(out, "api/codes.json", serve.codes())
    ids = list(serve._cache()["inc"])
    ciks: set[int] = set()
    for i in ids:
        size += _dump(out, f"api/incident/{i}.json", serve.detail(i))
        c = serve.case(i)
        c.pop("index", None)
        c["lanes"] = [{k: l[k] for k in ("cik", "name", "regime", "processed", "roles", "dropped")} for l in c["lanes"]]
        ciks |= {l["cik"] for l in c["lanes"]}
        size += _dump(out, f"api/case/{i}.json", c)
    regs = serve.regs()
    texted = {f["acc"] for cik in ciks for f in regs[cik]["filings"] if f["txt"]}
    text = _texts(texted)
    name = {acc: hashlib.sha1(t.encode()).hexdigest()[:16] for acc, t in text.items()}
    (out / "texts").mkdir()
    tsize = 0
    for acc, t in text.items():
        f = out / "texts" / f"{name[acc]}.js"
        if not f.exists():
            b64 = base64.b64encode(gzip.compress(t.encode(), compresslevel=9, mtime=0)).decode()
            f.write_text(f'__disc("texts/{name[acc]}","{b64}");\n', encoding="ascii")
            tsize += f.stat().st_size
    for cik in ciks:
        reg = regs[cik]
        filings = [{**f, "coded": serve.is_coded(reg, f),
                    "n_ai_harm": sum(p["discloses"] == "ai_harm" for p in reg["by_acc"].get(f["acc"], [])),
                    "n_passages": len(reg["by_acc"].get(f["acc"], [])), "txt": name.get(f["acc"])}
                   for f in reg["filings"]]
        size += _dump(out, f"api/actor/{cik}.json", {"cik": cik, "name": reg["name"], "regime": reg["regime"],
                                                      "filings": filings, "passages": reg["passages"], "k8": reg["k8"]})
    dl = serve.downloads()
    listed = dl["tables"] + dl["sections"] + dl["docs"] + dl["codebooks"]
    for f in dl["docs"] + dl["codebooks"]:                      # shown in the panel without a fetch
        f["text"] = (serve.HERE.parent / f["repo"]).read_text(encoding="utf-8")
    for f in listed:
        if repo_path:                                            # the repository's own file, relative to the site
            f["file"] = posixpath.relpath(f["repo"], repo_path)
        else:                                                    # a copy in files/
            (out / f["file"]).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(serve.download_path(f["file"].removeprefix("files/")), out / f["file"])
            del f["repo"]
    (out / "files").mkdir(exist_ok=True)
    with open(out / dl["archive"], "wb") as fh:
        serve.archive(fh)
    dl["archive_bytes"] = (out / dl["archive"]).stat().st_size
    if repo_path:
        dl["archive_repo"] = posixpath.join(repo_path, dl["archive"])
    size += _dump(out, "api/downloads.json", dl)
    n_files = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"DISC {serve.version()}: {len(ids):,} incidents, {len(ciks)} AI actors, {len(set(name.values())):,} texts "
          f"({len(text):,} filings) -> {out}; data {size / 1e6:.0f} MB, texts {tsize / 1e6:.0f} MB, {n_files:,} files")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=serve.HERE / "site")
    ap.add_argument("--repo-path", help="the site's folder in the release repository (e.g. docs/explorer): the "
                    "Download panel then links the repository's data/, docs/ and LICENSE instead of copies")
    a = ap.parse_args()
    export(a.out, a.repo_path)
