#!/usr/bin/env python3
"""Package the Drupal 10 theme drupal/mcroberts/ and zip it into docs/downloads/mcroberts-drupal-theme.zip.

    python3 tools/package_drupal.py           # sync, generate, zip
    python3 tools/package_drupal.py --check   # only report whether css/ and js/ match theme/ (exit 1 if not)

What it does (Python 3.9+ standard library only):
  1. css/ and js/: byte-for-byte copies of theme/css and theme/js, so the theme ships the preview's front-end code
     (less the preview's stand-ins for core search and the views pager, js/search.js and js/pager.js)
     unchanged (stale files are removed). bridge/ holds the only Drupal-specific CSS/JS and is not touched here.
  2. logo.png: the crest assets/content/39ef9ae7e316.png, byte for byte. images/: the scaled crest copies, the
     district logo, the header photo, the front-page pictures and the menu/hub tile pictures the preview uses.
  3. data/: bell-schedule.json (the timetable image transcribed word for word), image-text.json (the words of the
     informative images, keyed by the first 12 hex digits of the image's SHA-1, as in assets/content), tiles.json.
  4. templates/includes/sprite.html.twig and head-script.html.twig: generated from build.py, so the icon sprite
     and the inline <head> script are the preview's own.
  5. config-changes/: menus.md, urls.md, redirects.csv and ia-data.php, generated from design/ia.json.
  6. docs/downloads/mcroberts-drupal-theme.zip: deterministic (sorted entries, fixed timestamps), so a rebuild
     writes the same bytes.
"""
import csv
import hashlib
import io
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEME_SRC = ROOT / "theme"
DRUPAL = ROOT / "drupal" / "mcroberts"
ZIP_OUT = ROOT / "docs" / "downloads" / "mcroberts-drupal-theme.zip"
CREST = "39ef9ae7e316.png"
ZIP_DATE = (2026, 1, 1, 0, 0, 0)
SKIP_NAMES = {".DS_Store"}
# the static preview's stand-ins for what Drupal does on the server: core search (search.js) and the views pager
# (pager.js); the theme does not ship them
PREVIEW_ONLY = {"js": {"pager.js", "search.js"}}


def same(a, b):
    return b.exists() and a.stat().st_size == b.stat().st_size and a.read_bytes() == b.read_bytes()


def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not same(src, dst):
        shutil.copyfile(src, dst)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def mirror(sub):
    """theme/<sub> → drupal/mcroberts/<sub>, exact (less the preview-only files); files that left theme/ leave the copy too."""
    src, dst = THEME_SRC / sub, DRUPAL / sub
    dst.mkdir(parents=True, exist_ok=True)
    names = {f.name for f in src.iterdir() if f.is_file() and f.name not in SKIP_NAMES | PREVIEW_ONLY.get(sub, set())}
    for name in sorted(names):
        copy(src / name, dst / name)
    for f in dst.iterdir():
        if f.is_file() and f.name not in names:
            f.unlink()
    return sorted(names)


def check_mirror():
    bad = []
    for sub in ("css", "js"):
        src, dst = THEME_SRC / sub, DRUPAL / sub
        a = {f.name for f in src.iterdir() if f.is_file() and f.name not in SKIP_NAMES | PREVIEW_ONLY.get(sub, set())}
        b = {f.name for f in dst.iterdir() if f.is_file() and f.name not in SKIP_NAMES} if dst.exists() else set()
        bad += ["{}/{} missing".format(sub, n) for n in sorted(a - b)]
        bad += ["{}/{} extra".format(sub, n) for n in sorted(b - a)]
        bad += ["{}/{} differs".format(sub, n) for n in sorted(a & b) if not same(src / n, dst / n)]
    return bad


# ------------------------------------------------------------------------------------------- PHP / Markdown output
def php(v, indent=0):
    pad = "  " * indent
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return "'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'"
    if isinstance(v, dict):
        if not v:
            return "[]"
        rows = ["{}  {} => {},".format(pad, php(k), php(x, indent + 1)) for k, x in v.items()]
        return "[\n" + "\n".join(rows) + "\n" + pad + "]"
    if isinstance(v, (list, tuple)):
        if not v:
            return "[]"
        rows = ["{}  {},".format(pad, php(x, indent + 1)) for x in v]
        return "[\n" + "\n".join(rows) + "\n" + pad + "]"
    raise TypeError(type(v))


def md(s):
    return (s or "").replace("|", "\\|")


def link_of(href):
    """design/ia.json href → the link value the apply script resolves (path alias, external URI or route)."""
    if href is None:
        return "route:<nolink>"
    if href == "/":
        return "route:<front>"
    return href


def menu_data(b):
    ia = b.IA
    main = []
    for m in ia["primary"]:
        groups = []
        for i, g in enumerate(m["groups"]):
            title = g["label"] or ("[Most requested]" if i == 0 else "[More]")
            groups.append({"title": title, "link": link_of(g["href"]),
                           "children": [{"title": c["label"], "link": link_of(c["href"])} for c in g["children"]]})
        main.append({"title": m["label"], "link": link_of(m["href"]), "children": groups})
    utility = [{"title": n["label"], "link": link_of(n["href"])} for n in ia["utility"]]
    footer = [{"title": col["label"], "link": link_of(col["href"]),
               "children": [{"title": c["label"], "link": link_of(c["href"])} for c in col["children"]]}
              for col in ia["footer"]]
    # "hub links": the home task band, the small hubs, and a section hub whose cards differ from its menu panel
    # (Library: the first card is the Library Catalogue page, the menu opens the catalogue itself)
    hubs = []
    for hub, spec in ia["hubs"].items():
        top = b.TOPS.get(hub)
        if top:
            menu_groups = [(g["label"], g["href"], [c["href"] for c in g["children"] if c["href"] != hub])
                           for g in top["groups"]]
            hub_groups = [(s["heading"], s["href"], [h for h in s["links"] if h != hub]) for s in spec["sections"]]
            if menu_groups == hub_groups:
                continue
        sections = []
        for s in spec["sections"]:
            sections.append({"title": s["heading"] or "[Cards]", "link": link_of(s["href"]),
                             "children": [{"title": b.hub_label(h, None if hub == "/" else hub), "link": link_of(h)}
                                          for h in s["links"]]})
        title = "Home" if hub == "/" else (b.page_title(hub) or hub)
        hubs.append({"title": "[{}]".format(title), "link": link_of(hub), "children": sections})
    return {"main": main, "utility": utility, "footer": footer, "hub-links": hubs}


def url_data(b):
    ia = b.IA
    aliases = []
    for new, old in ia["paths"].items():
        aliases.append({"old": old, "new": new, "title": b.page_title(new) or ""})
    retired = [{"old": old, "new": new, "title": b.clean_title((b._PAGES_RAW.get(old) or {}).get("title")) or ""}
               for old, new in ia["retired"].items()]
    return aliases, retired


def menus_md(menus):
    out = ["# Menus (generated from design/ia.json)", "",
           "Generated by `tools/package_drupal.py`; edit `design/ia.json`, then re-run it. `config-changes/apply.php`",
           "creates exactly these links. A column title in square brackets is an admin-only name: the theme never prints",
           "it (`[Most requested]` is the first column of a panel, `[More]` and `[Cards]` a column without a heading).",
           "Paths are the new URLs (`urls.md`); the script stores each internal link as `entity:node/N`, so it keeps",
           "working if an alias changes later.", ""]
    out += ["## Menu `main` (7 items; level 2 = columns, level 3 = links)", "",
            "| Level 1 | Level 2 (column) | Level 3 (link) | Link |", "|---|---|---|---|"]
    for m in menus["main"]:
        out.append("| **{}** | | | `{}` |".format(md(m["title"]), m["link"]))
        for g in m["children"]:
            out.append("| | {} | | `{}` |".format(md(g["title"]), g["link"]))
            for c in g["children"]:
                out.append("| | | {} | `{}` |".format(md(c["title"]), c["link"]))
    out += ["", "## Menu `utility` (new, flat)", "", "| Link text | Link |", "|---|---|"]
    out += ["| {} | `{}` |".format(md(n["title"]), n["link"]) for n in menus["utility"]]
    out += ["", "## Menu `footer` (new; level 1 = the three columns)", "",
            "| Column | Link text | Link |", "|---|---|---|"]
    for col in menus["footer"]:
        out.append("| **{}** | | `{}` |".format(md(col["title"]), col["link"]))
        out += ["| | {} | `{}` |".format(md(c["title"]), c["link"]) for c in col["children"]]
    out += ["", "## Menu `hub-links` (new; the cards of the hubs that are not a main-menu panel)", "",
            "Level 1 is the hub page itself (admin name), level 2 a section (its heading, or `[Cards]`), level 3 a card.",
            "The six section hubs (Parents, Students, School Calendar, News, Extra-Curricular, About Us) need no entry:",
            "they show their own `main` panel as cards, self-links dropped.", "",
            "| Hub page | Section | Card | Link |", "|---|---|---|---|"]
    for h in menus["hub-links"]:
        out.append("| **{}** | | | `{}` |".format(md(h["title"]), h["link"]))
        for s in h["children"]:
            out.append("| | {} | | `{}` |".format(md(s["title"]), s["link"]))
            out += ["| | | {} | `{}` |".format(md(c["title"]), c["link"]) for c in s["children"]]
    return "\n".join(out) + "\n"


def urls_md(aliases, retired):
    out = ["# URL aliases and redirects (generated from design/ia.json)", "",
           "Generated by `tools/package_drupal.py`. For every row the page keeps its node: only its path alias changes,",
           "and the Redirect module answers the old URL with a 301 to the page (`redirects.csv`, the same list).",
           "`/node/1813` and `/media/1069` are system paths, not aliases: they get the new alias and the Redirect",
           "module's route normalizer sends the system path to it, so they need no redirect entity.", "",
           "## Changed aliases ({})".format(len(aliases)), "", "| Live URL (old alias) | New URL | Page |", "|---|---|---|"]
    out += ["| `{}` | `{}` | {} |".format(a["old"], a["new"], md(a["title"])) for a in aliases]
    out += ["", "## Retired pages ({}): the old URL redirects, the node is unpublished (optional, `--retire`)".format(len(retired)),
            "", "| Live URL | Redirects to | Page |", "|---|---|---|"]
    out += ["| `{}` | `{}` | {} |".format(r["old"], r["new"], md(r["title"])) for r in retired]
    return "\n".join(out) + "\n"


def redirects_csv(aliases, retired):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["source", "destination", "status_code", "kind"])
    for a in aliases:
        if a["old"].startswith(("/node/", "/media/")):
            continue
        w.writerow([a["old"], a["new"], 301, "alias changed"])
    for r in retired:
        w.writerow([r["old"], r["new"], 301, "page retired"])
    return buf.getvalue()


# ------------------------------------------------------------------------------------------- images and data
def theme_images(b):
    """name in docs/assets/img (or assets/) → copied to images/ under the same name; returns the tile map."""
    img_built = ROOT / "docs" / "assets" / "img"

    def find(name):
        for d in (img_built, ROOT / "assets" / "img", ROOT / "assets" / "content"):
            if (d / name).exists():
                return d / name
        raise SystemExit("image not found: {} (run python3 build.py first)".format(name))

    names = ["39ef9ae7e316-200.png", "39ef9ae7e316-180.png", "39ef9ae7e316-32.png",
             b.IMAGES["map"].get(b.DISTRICT_LOGO, b.DISTRICT_LOGO), b.IMAGES["map"].get(b.HEADER_IMG, b.HEADER_IMG),
             b.DERIVED[b.BUILDING][0], b.DERIVED[b.STRIKERS_LOGO][0]]
    tiles = {}
    paths = [p for ps in b.MEGA_TILES.values() for p in ps]
    for sec in b.HUBS.get("/library", {}).get("sections", []):
        paths += [b.canon(h) for h in sec["links"]]
    for p in dict.fromkeys(paths):
        name = b.tile_image(p)
        if not name:
            icon = b.TILE_ICON.get(p)
            if icon:
                tiles[p] = {"icon": icon}
            continue
        out_name = b.DERIVED[name][0] if name in b.DERIVED else b.IMAGES["map"].get(name, name)
        w, h = b.IMAGES["size"].get(b.IMAGES["map"].get(name, name), [None, None])
        tiles[p] = {"file": "images/" + out_name, "w": w, "h": h, "logo": name in b.LOGOS,
                    "icon_art": bool(name.endswith(".png") and (w or 0) <= 600)}
        names.append(out_name)
    wanted = set()
    for n in names:
        copy(find(n), DRUPAL / "images" / n)
        wanted.add(n)
    for f in (DRUPAL / "images").iterdir():
        if f.is_file() and f.name not in wanted:
            f.unlink()
    copy(ROOT / "assets" / "content" / CREST, DRUPAL / "logo.png")
    return tiles


def main():
    if "--check" in sys.argv:
        bad = check_mirror()
        print("css/js: {}".format("identical to theme/" if not bad else "; ".join(bad)))
        sys.exit(1 if bad else 0)

    sys.path.insert(0, str(ROOT))
    import build as b   # the static build's own data and helpers (module code only; main() is not run)

    css, js = mirror("css"), mirror("js")
    tiles = theme_images(b)

    # data
    write(DRUPAL / "data" / "bell-schedule.json", (ROOT / "content" / "bell-schedule.json").read_text())
    image_text = {name.rsplit(".", 1)[0]: {"alt": alt, "html": body} for name, (alt, body) in b.IMAGE_TEXT.items()}
    write(DRUPAL / "data" / "image-text.json", json.dumps(image_text, ensure_ascii=False, indent=1) + "\n")
    write(DRUPAL / "data" / "tiles.json", json.dumps(tiles, ensure_ascii=False, indent=1, sort_keys=True) + "\n")

    # generated partials
    write(DRUPAL / "templates" / "includes" / "sprite.html.twig",
          "{# Icon sprite: our own inline SVG. Generated by tools/package_drupal.py from build.py SPRITE; do not edit. #}\n"
          "{% verbatim %}" + b.SPRITE + "{% endverbatim %}\n")
    head = b.HEAD_SCRIPT
    key_at = head.index(b.ALERT_KEY)
    write(DRUPAL / "templates" / "includes" / "head-script.html.twig",
          "{# Inline <head> script: saved Accessibility Settings and a closed alert applied before the first paint.\n"
          "   Generated by tools/package_drupal.py from build.py HEAD_SCRIPT; alert_key comes from mcroberts_preprocess_html(). #}\n"
          "{% verbatim %}" + head[:key_at] + "{% endverbatim %}{{ alert_key }}{% verbatim %}"
          + head[key_at + len(b.ALERT_KEY):] + "{% endverbatim %}\n")

    # configuration changes from design/ia.json
    menus = menu_data(b)
    aliases, retired = url_data(b)
    cc = DRUPAL / "config-changes"
    write(cc / "menus.md", menus_md(menus))
    write(cc / "urls.md", urls_md(aliases, retired))
    write(cc / "redirects.csv", redirects_csv(aliases, retired))
    write(cc / "ia-data.php",
          "<?php\n\n/**\n * @file\n * The new information architecture as data, for apply.php.\n *\n"
          " * Generated by tools/package_drupal.py from design/ia.json; do not edit by hand.\n */\n\n"
          "if (PHP_SAPI !== 'cli') {\n  exit;\n}\n\nreturn " + php({"menus": menus, "aliases": aliases, "retired": retired}) + ";\n")

    # zip
    ZIP_OUT.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in DRUPAL.rglob("*") if p.is_file() and p.name not in SKIP_NAMES)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files:
            info = zipfile.ZipInfo("mcroberts/" + p.relative_to(DRUPAL).as_posix(), ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, p.read_bytes())
    data = buf.getvalue()
    if not ZIP_OUT.exists() or ZIP_OUT.read_bytes() != data:
        ZIP_OUT.write_bytes(data)

    bad = check_mirror()
    if bad:
        raise SystemExit("css/js copies differ from theme/: " + "; ".join(bad))
    print("drupal/mcroberts: {} css + {} js identical to theme/, {} files; zip {} KB, sha256 {}".format(
        len(css), len(js), len(files), round(len(data) / 1024), hashlib.sha256(data).hexdigest()[:12]))


if __name__ == "__main__":
    main()
