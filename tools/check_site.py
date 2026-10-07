"""Check the built site: every internal link and asset resolves, and nothing loads from a host we do not allow.

For every .html file under docs/ (or the folders given):
  - every relative href/src/action/poster resolves to a file in the build (a directory URL needs its index.html),
    and a #fragment exists as an id in the target page;
  - no URL starts at the root ("/..."), so the site works under any sub-path;
  - scripts and stylesheets come from the build itself, except Google Fonts (fonts.googleapis.com / fonts.gstatic.com);
  - images come from the build; iframes only from the embed hosts the live site already uses;
  - every <use href="#id"> points at a symbol on the page; ids are unique;
  - the URLs inside the embedded today-data JSON resolve too;
  - redirect stubs (the old URLs, design/ia.json "paths" and "retired"): a meta refresh whose target resolves, is not
    itself a redirect (no chains), equals rel=canonical when one is given, and carries noindex; no page links to a redirect stub, so
    every internal link already points at the clean URL.
CSS files under docs/assets/css are checked for url(...) references the same way.

    python3 tools/check_site.py [folder ...]      # exit 1 on any problem
"""
import json, re, sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parent.parent
FONT_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com"}
EMBED_HOSTS = {"www.google.com", "maps.google.com", "calendar.google.com", "docs.google.com", "forms.office.com",
               "www.youtube.com", "www.youtube-nocookie.com", "player.vimeo.com"}
SKIP_SCHEMES = ("mailto:", "tel:", "webcal:", "data:", "sms:")


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs, self.ids, self.uses, self.symbols, self.json = [], [], [], set(), []
        self._json = False
        self.refresh = self.canonical = None
        self.noindex = False
        self.headings = []              # heading levels in document order (heading-order check)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if re.match(r"^h[1-6]$", tag):
            self.headings.append(int(tag[1]))
        if a.get("id"):
            self.ids.append(a["id"])
            if tag == "symbol":
                self.symbols.add(a["id"])
        if tag == "use":
            self.uses.append(a.get("href") or a.get("xlink:href") or "")
            return
        if tag == "meta" and (a.get("http-equiv") or "").lower() == "refresh":
            m = re.search(r"url=(.+)$", a.get("content") or "", re.I)
            self.refresh = m.group(1).strip() if m else ""
        if tag == "meta" and (a.get("name") or "").lower() == "robots" and "noindex" in (a.get("content") or ""):
            self.noindex = True
        if tag == "link" and "canonical" in (a.get("rel") or "").lower():
            self.canonical = a.get("href")
        for k in ("href", "src", "action", "poster"):
            if a.get(k) is not None:
                self.refs.append((tag, k, a[k], (a.get("rel") or "").lower()))
        if a.get("srcset"):
            for part in a["srcset"].split(","):
                if part.strip():
                    self.refs.append((tag, "srcset", part.strip().split()[0], ""))
        self._json = tag == "script" and a.get("type") == "application/json"

    handle_startendtag = handle_starttag

    def handle_data(self, d):
        if self._json:
            self.json.append(d)

    def handle_endtag(self, tag):
        if tag == "script":
            self._json = False


def target_file(base_dir, url):
    path = unquote(urlsplit(url).path)
    t = (base_dir / path).resolve() if path else None
    if t is None:
        return None
    if path.endswith("/") or t.is_dir():
        t = t / "index.html"
    return t


def main():
    folders = [Path(a).resolve() for a in sys.argv[1:]] or [ROOT / "docs"]
    errors, checked, id_cache = [], 0, {}

    def ids_of(f):
        if f not in id_cache:
            p = Page()
            p.feed(f.read_text(errors="replace"))
            id_cache[f] = set(p.ids)
        return id_cache[f]

    def check_url(src_file, tag, attr, url, rel_attr, root):
        nonlocal checked
        checked += 1
        where = "{} <{} {}>".format(src_file.relative_to(root.parent), tag, attr)
        if url.startswith(SKIP_SCHEMES) or url == "":
            return
        if url.lower().startswith("javascript:"):
            errors.append("{}: javascript: URL".format(where))
            return
        if url.startswith("#"):
            if url[1:] and url[1:] not in ids_of(src_file):
                errors.append("{}: missing #{} on the page".format(where, url[1:]))
            return
        parts = urlsplit(url)
        if parts.scheme in ("http", "https") or url.startswith("//"):
            host = parts.hostname or ""
            if tag == "script" or (tag == "link" and "stylesheet" in rel_attr):
                if host not in FONT_HOSTS:
                    errors.append("{}: third-party script/style from {}".format(where, host))
            elif tag == "link" and "preconnect" in rel_attr:
                if host not in FONT_HOSTS:
                    errors.append("{}: preconnect to {}".format(where, host))
            elif tag == "iframe":
                if host not in EMBED_HOSTS:
                    errors.append("{}: iframe from {}".format(where, host))
            elif tag in ("img", "source", "video", "audio", "link"):
                errors.append("{}: external asset {}".format(where, url[:80]))
            return
        if parts.scheme:
            errors.append("{}: unexpected scheme {}".format(where, url[:60]))
            return
        if url.startswith("/"):
            errors.append("{}: root-absolute URL {}".format(where, url[:80]))
            return
        t = target_file(src_file.parent, url)
        if t is None or not t.exists():
            errors.append("{}: broken {}".format(where, url[:100]))
            return
        try:
            t.relative_to(root)
        except ValueError:
            errors.append("{}: points outside the site {}".format(where, url[:80]))
            return
        if parts.fragment and t.suffix == ".html" and parts.fragment not in ids_of(t):
            errors.append("{}: missing #{} in {}".format(where, parts.fragment, t.relative_to(root)))

    def is_stub(f):
        if f not in stub_cache:
            p = Page()
            p.feed(f.read_text(errors="replace"))
            stub_cache[f] = p.refresh is not None
        return stub_cache[f]

    stub_cache, pages, stubs = {}, 0, 0
    for root in folders:
        for f in sorted(root.rglob("*.html")):
            pages += 1
            p = Page()
            p.feed(f.read_text(errors="replace"))
            where = f.relative_to(root.parent)
            if p.refresh is not None:          # a redirect stub
                stubs += 1
                t = target_file(f.parent, p.refresh) if p.refresh and not urlsplit(p.refresh).scheme else None
                if not p.refresh:
                    errors.append("{}: redirect without a target".format(where))
                elif t is None or not t.exists():
                    errors.append("{}: redirect to a missing page {}".format(where, p.refresh))
                elif is_stub(t):
                    errors.append("{}: redirect chain via {}".format(where, p.refresh))
                if p.canonical is not None and p.canonical != p.refresh:   # stubs carry no canonical (noindex, a 301 in Drupal)
                    errors.append("{}: canonical {} differs from the redirect {}".format(where, p.canonical, p.refresh))
                if not p.noindex:
                    errors.append("{}: redirect stub without noindex".format(where))
            else:
                for tag, attr, url, rel_attr in p.refs:
                    if tag != "a" or urlsplit(url).scheme or url.startswith(("#", "/")):
                        continue
                    t = target_file(f.parent, url)
                    if t is not None and t.exists() and t.suffix == ".html" and is_stub(t):
                        errors.append("{}: links to the old URL {} (a redirect)".format(where, url[:90]))
            # heading order: no heading more than one level below the one before it (h1 → h3 fails axe heading-order)
            for prev_h, h in zip(p.headings, p.headings[1:]):
                if h - prev_h > 1:
                    errors.append("{}: heading order h{} → h{}".format(where, prev_h, h))
                    break
            dupes = {i for i in p.ids if p.ids.count(i) > 1}
            for d in sorted(dupes):
                errors.append("{}: duplicate id {}".format(f.relative_to(root.parent), d))
            for u in p.uses:
                if not u.startswith("#") or u[1:] not in p.symbols:
                    errors.append("{}: <use> of missing symbol {}".format(f.relative_to(root.parent), u))
            is_404 = f.name == "404.html"
            for tag, attr, url, rel_attr in p.refs:
                if is_404 and not url.startswith(("http", "#", "mailto:", "tel:", "webcal:")):
                    # 404.html is served at any depth; it sets <base> to the site root at runtime
                    t = (root / urlsplit(url).path)
                    if url.startswith("/") or not (t / "index.html" if (url.endswith("/") or t.is_dir()) else t).exists():
                        errors.append("{}: broken {}".format(f.relative_to(root.parent), url[:100]))
                    continue
                check_url(f, tag, attr, url, rel_attr, root)
            for blob in p.json:
                try:
                    data = json.loads(blob)
                except ValueError:
                    errors.append("{}: embedded JSON does not parse".format(f.relative_to(root.parent)))
                    continue
                for e in data.get("events", []) if isinstance(data, dict) else []:
                    check_url(f, "a", "data-u", e.get("u", ""), "", root)
        for css in sorted((root / "assets" / "css").glob("*.css")) if (root / "assets" / "css").exists() else []:
            for url in re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", css.read_text()):
                check_url(css, "css", "url", url, "", root)

    for e in errors[:200]:
        print("ERR ", e)
    print("checked {} pages ({} redirect stubs), {} URLs: {} problems".format(pages, stubs, checked, len(errors)))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
