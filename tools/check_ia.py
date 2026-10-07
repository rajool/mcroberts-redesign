"""Validate an information-architecture file (default design/ia.json).

Rules:
- every navigation label is live-site copy (content/corpus.txt, case-insensitive, like check_copy.py);
- every href is a page we have (content/pages.json), a path the file maps in "paths" (new clean URL -> old path),
  an absolute http(s) URL, or tel:/mailto:;
- every content page (type page, staff, calendar, listing) is reachable from "primary", "utility" or "footer"
  or from a hub listed in "hubs" — no orphans. Articles and events are reached through News and the calendar.

    python3 tools/check_ia.py [design/ia.json]
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_copy import norm  # same normalisation as the copy check

ROOT = Path(__file__).resolve().parent.parent


def walk(items, out):
    for it in items or []:
        out.append(it)
        walk(it.get("children"), out)
        for g in it.get("groups", []) or []:
            out.append({"label": g.get("label"), "href": g.get("href")})
            walk(g.get("children"), out)


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "design" / "ia.json"
    ia = json.loads(path.read_text())
    pages = json.loads((ROOT / "content" / "pages.json").read_text())
    corpus = norm(" \n ".join((ROOT / "content" / f).read_text() for f in ("corpus.txt", "corpus-images.txt")))
    paths = ia.get("paths", {})  # new path -> old path
    known = set(pages) | set(paths)
    nodes = []
    for key in ("primary", "utility", "footer"):
        walk(ia.get(key), nodes)
    for hub, spec in (ia.get("hubs") or {}).items():
        nodes.append({"label": None, "href": hub})
        for sec in spec.get("sections", []):
            nodes.append({"label": sec.get("heading"), "href": sec.get("href")})
            for h in sec.get("links", []):
                nodes.append({"label": None, "href": h if isinstance(h, str) else h.get("href")})
    errors = []
    for n in nodes:
        lab, href = n.get("label"), n.get("href")
        if lab and norm(lab).strip(" :") not in corpus:
            errors.append(f"label not on the live site: {lab!r}")
        if href and not re.match(r"^(https?:|tel:|mailto:|webcal:)", href) and href.split("#")[0] not in known:
            errors.append(f"unknown href: {href}")
    reach = {paths.get(n["href"], n["href"]) for n in nodes if n.get("href")}
    reach |= {n["href"] for n in nodes if n.get("href")}
    orphans = [k for k, p in pages.items() if p["type"] in ("page", "staff", "calendar", "listing")
               and k not in reach and paths.get(k, k) not in reach and k not in set(ia.get("retired", {}))]
    for o in sorted(orphans):
        errors.append(f"orphan page: {o} ({pages[o]['title']})")
    for old, new in (ia.get("retired") or {}).items():
        if old not in pages:
            errors.append(f"retired path is not a page: {old}")
        if new not in known:
            errors.append(f"retired path {old} redirects to unknown {new}")
    for e in errors:
        print(e)
    print(f"{path.name}: {len(nodes)} nodes, {len(errors)} problems")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
