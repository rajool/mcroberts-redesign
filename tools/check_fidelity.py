"""Page-by-page content fidelity: nothing dropped, nothing added.

Two passes:

1. Extracted content. For every page in content/pages.json that the build renders (types page, article, staff,
   calendar), the built page's <main> must contain every text fragment of the extracted body (coverage), and every
   word in the built <main> must occur in the live page itself or on the live site as a whole (no new words).
2. Live HTML (independent of tools/extract.py). For the same pages plus calendar events, the crawled live page
   (cache/raw/) is read directly: its main content block, minus the title and the page's own menus, is split into
   text blocks, and each block must be visible (not [hidden], aria-hidden or visually hidden) in the built page's
   content (the hero and the content column; side nav, hub cards, pager and rail do not count). Case counts, except
   the one documented display rule: ALL-CAPS calendar titles may be shown in title case (build.smart_case). Every
   live link (documents, other pages, external sites) and every embedded video must also be in the built content.
   Staff tables are compared cell by cell through the same blocks.

The built file is docs/<path>/index.html, where <path> is the page key, or the new path that
design/ia.json maps to it in "paths". Pages listed in its "retired" map redirect elsewhere and are skipped.
Every old path (a mapped page key or a retired page) must answer with a redirect stub (meta refresh), so no old
link breaks.

Documented exception: /proposal (docs/proposal/) is never compared. It is Ali's proposal to the principal, the
document about this concept, not a page of the live site, so it is the one page allowed new words (see EXEMPT).

    python3 tools/check_fidelity.py            # exit 1 on any dropped fragment or new word
    python3 tools/check_fidelity.py -v         # list every problem
"""
import html, json, re, sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXEMPT = ("/proposal",)       # the documented exception above: built paths that are never compared with the live site
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_copy import norm  # noqa: E402


class Text(HTMLParser):
    """Visible text of a document, or only of its <main> element when main_only."""
    SKIP = {"script", "style", "svg", "noscript", "template", "head"}
    VOID = {"br", "img", "input", "meta", "link", "hr", "source", "wbr", "col", "area", "base", "embed", "param", "track"}

    def __init__(self, main_only):
        super().__init__(convert_charrefs=True)
        self.main_only, self.in_main, self.stack, self.parts = main_only, 0, [], []

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            if tag == "img" and self.active():
                alt = dict(attrs).get("alt")
                if alt:
                    self.parts.append(alt)
            return
        a = dict(attrs)
        hidden = tag in self.SKIP or a.get("aria-hidden") == "true" or "concept-banner" in (a.get("class") or "").split()
        self.stack.append((tag, hidden))
        if tag == "main":
            self.in_main += 1

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                if tag == "main":
                    self.in_main -= 1
                del self.stack[i:]
                break

    def active(self):
        return (self.in_main or not self.main_only) and not any(h for _, h in self.stack)

    def handle_data(self, d):
        if self.active():
            self.parts.append(d)


def fragments(body_html):
    p = Text(main_only=False)
    p.feed(body_html)
    out = []
    for raw in p.parts:
        raw = re.sub(r"[\x80-\x9f\u200b-\u200d\u2060]", "", raw)  # stray C1 controls and zero-width marks pasted from Word
        t = norm(raw).strip(" :;,.|·•-–—")
        if t in ("read more",):  # teaser link labels; the teasers themselves are rebuilt from news.json
            continue
        if len(t) >= 3 and re.search(r"[a-z]", t):
            out.append(t)
    return out


WORD = re.compile(r"[a-z0-9À-ɏ']+")


def main():
    verbose = "-v" in sys.argv
    pages = json.loads((ROOT / "content" / "pages.json").read_text())
    ia_file = ROOT / "design" / "ia.json"
    new_of, retired = {}, set()
    if ia_file.exists():
        ia = json.loads(ia_file.read_text())
        for new, old in (ia.get("paths") or {}).items():
            new_of[old] = new
        retired = set(ia.get("retired") or {})  # merged/empty pages that now redirect elsewhere
    corpus = norm(" \n ".join((ROOT / "content" / f).read_text() for f in ("corpus.txt", "corpus-images.txt")))
    site_words = set(WORD.findall(corpus))
    ui_path = ROOT / "tools" / "ui_words.txt"
    for line in (ui_path.read_text().splitlines() if ui_path.exists() else []):
        site_words |= set(WORD.findall(norm(line)))
    checked = dropped_total = new_total = missing_files = 0
    report = []
    for old in sorted(set(new_of) | retired):
        stub = ROOT / "docs" / old.strip("/") / "index.html"
        if not stub.exists() or 'http-equiv="refresh"' not in stub.read_text():
            missing_files += 1
            report.append(f"NO REDIRECT at old URL {old}")
    for key, page in sorted(pages.items()):
        if page["type"] not in ("page", "article", "staff", "calendar") or key.startswith("/2026/") or key in retired:
            continue
        path = new_of.get(key, key)
        if path.startswith(EXEMPT):
            continue
        f = ROOT / "docs" / path.strip("/") / "index.html"
        if not f.exists():
            missing_files += 1
            report.append(f"MISSING PAGE {path} (live {key})")
            continue
        p = Text(main_only=True)
        p.feed(f.read_text())
        built = norm(" ".join(p.parts))
        built_nospace = built.replace(" ", "")
        checked += 1
        dropped = [fr for fr in fragments(page.get("body", "")) if fr not in built and fr.replace(" ", "") not in built_nospace]
        page_words = set(WORD.findall(norm(page.get("title", "") + " " + " ".join(fragments(page.get("body", ""))))))
        new_words = sorted({w for w in WORD.findall(built) if w not in page_words and w not in site_words and not w.isdigit()})
        if page["type"] == "staff":
            dropped = [d for d in dropped if d not in corpus]
        if dropped or new_words:
            report.append(f"{path}: {len(dropped)} dropped, {len(new_words)} new words")
            if verbose:
                report += [f"    - dropped: {d[:110]}" for d in dropped[:15]]
                report += [f"    + new word: {w}" for w in new_words[:25]]
        dropped_total += len(dropped)
        new_total += len(new_words)
    live_checked, live_report, live_blocks, live_links = live_pass(pages, new_of, retired, verbose)
    report += live_report
    print("\n".join(report))
    print(f"checked {checked} pages: {missing_files} missing, {dropped_total} dropped fragments, {new_total} new words")
    print(f"live HTML: checked {live_checked} pages: {live_blocks} live text blocks and {live_links} live links/videos not in the build")
    sys.exit(1 if (missing_files or dropped_total or new_total or live_blocks or live_links) else 0)


# ------------------------------------------------------------------------------------------------ live HTML pass
LIVE_HOSTS = ("mcroberts.sd38.bc.ca", "www.mcroberts.sd38.bc.ca")
LIVE_DROP = ("field--name-node-title", "nav-list", "section-menu-block", "sub-pages-menu-block", "feed-icons",
             "pagination", "menu-back-button", "visually-hidden", "sr-only")
LIVE_SKIP = {"script", "style", "svg", "noscript", "template", "form", "select", "option", "head"}
# navigation around the content does not count (the hub cards are the page's own menu block, so they do)
BUILT_DROP = ("page-sidebar", "page-rail", "section-nav-mobile", "breadcrumb", "section-pager", "article-nav", "vh",
              "region-breadcrumb")
BLOCK_TAGS = {"p", "li", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "summary", "button", "figcaption", "dt",
              "dd", "caption", "blockquote", "div", "section", "article", "tr", "ul", "ol", "table", "details", "br"}
# whitespace, dashes, colons, typed bullets (Wingdings \x9f, private-use and Unicode bullets) and zero-width marks
TIGHT = re.compile(r"[\s\-\u2010-\u2015•·:\u00a0\u200b-\u200d\u2060\ufeff\x80-\x9f\uf000-\uf0ff\u25aa\u25cf\u2023\u2043]+")


def tight(s):
    s = html.unescape(s)
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("…", "...")):
        s = s.replace(a, b)
    return TIGHT.sub("", s)


def live_url(href, page):
    """A live href → a comparable key: site path for pages, absolute URL for documents and other hosts."""
    import urllib.parse
    h = html.unescape(href or "").strip()
    if not h or h.startswith(("#", "tel:", "javascript:")):
        return None
    if h.startswith("mailto:"):
        return h.lower()
    h = re.sub(r"^(https?):/(?=[^/])", r"\1://", h)          # the live body's typos, repaired by tools/extract.py
    if re.match(r"^www\.[a-z0-9-]+\.[a-z]", h, re.I):
        h = "https://" + h
    u = urllib.parse.urlsplit(urllib.parse.urljoin("https://mcroberts.sd38.bc.ca" + page.rstrip("/") + "/", h))
    host = u.netloc.lower()
    path = urllib.parse.unquote(u.path)
    if host in LIVE_HOSTS:
        host = "mcroberts.sd38.bc.ca"
    key = host + (path.rstrip("/") or "/") + ("?" + u.query if u.query else "")
    return key.lower()


def built_url(href, page_url):
    """A built href (relative to the page's own URL) → the same kind of key as live_url()."""
    import urllib.parse
    h = html.unescape(href or "").strip()
    if not h or h.startswith(("#", "tel:", "javascript:")):
        return None
    if h.startswith("mailto:"):
        return h.lower()
    u = urllib.parse.urlsplit(urllib.parse.urljoin("https://built.invalid" + page_url, h))
    host = u.netloc.lower()
    path = urllib.parse.unquote(u.path)
    if host == "built.invalid":
        host = "mcroberts.sd38.bc.ca"
        path = re.sub(r"/index\.html$", "/", path)
    if host in LIVE_HOSTS:
        host = "mcroberts.sd38.bc.ca"
    return (host + (path.rstrip("/") or "/") + ("?" + u.query if u.query else "")).lower()


def youtube_ids(src):
    import urllib.parse
    s = urllib.parse.unquote(html.unescape(src or ""))
    return set(re.findall(r"(?:v=|youtu\.be/|/embed/)([\w-]{6,})", s))


def live_pass(pages, new_of, retired, verbose):
    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, str(ROOT))
    from extract import parse, Node  # the extractor's tolerant DOM parser (no extraction logic is used)
    import build                       # only for canon() and the documented smart_case() display rule
    index_file = ROOT / "cache" / "index.json"
    if not index_file.exists():          # cache/ is not in git: crawl first (python3 tools/crawl.py)
        return 0, ["live HTML pass skipped: no cache/index.json (run python3 tools/crawl.py)"], 0, 0
    index = json.loads(index_file.read_text())

    def cls(n):
        return (n.attrs.get("class") or "").split()

    def live_blocks(root, title):
        out, seen_title = [], [False]

        def keep(n):
            c = cls(n)
            if n.tag in LIVE_SKIP or any(x in c for x in LIVE_DROP) or "visually-hidden" in " ".join(c):
                return False
            if n.tag == "h1" and not seen_title[0] and re.sub(r"\s+", " ", n.text()).strip() == title:
                seen_title[0] = True
                return False
            # the legacy Attachments table's own column labels (Attachment | Size) become the file card's layout
            if n.tag == "thead" and n.parent is not None and any("legacy-attachments" in " ".join(cls(a)) for a in ancestors(n)):
                return False
            return True

        def text(n):
            if isinstance(n, str):
                return n
            if not keep(n):
                return " "
            inner = "".join(text(c) for c in n.children)
            return " \n " + inner + " \n " if n.tag in BLOCK_TAGS else inner

        for line in text(root).split("\n"):
            t = re.sub(r"\s+", " ", html.unescape(line).replace("\xa0", " ")).strip()
            if len(re.findall(r"[A-Za-zÀ-ɏ]", t)) >= 3:
                out.append(t)
        return out

    def ancestors(n):
        p = n.parent
        while p is not None:
            yield p
            p = p.parent

    def live_links(root):
        out = []
        for n in root.iter():
            if any(x in cls(n) for x in LIVE_DROP):
                continue
            if any(any(x in cls(a) for x in LIVE_DROP) for a in ancestors(n)):
                continue
            if n.tag == "a" and n.attrs.get("href"):
                label = re.sub(r"\s+", " ", n.text().replace("\xa0", " ")).strip()
                if label or n.find(lambda x: x.tag == "img"):      # an empty live link shows nothing
                    out.append(("a", n.attrs["href"], label))
            elif n.tag == "iframe" and n.attrs.get("src"):
                out.append(("iframe", n.attrs["src"], ""))
        return out

    def built_region(doc):
        main = doc.find(lambda x: x.tag == "main")
        parts, links, vids = [], set(), set()

        def walk(n, hidden):
            if isinstance(n, str):
                if not hidden:
                    parts.append(n)
                return
            c = cls(n)
            if n.tag in LIVE_SKIP or any(x in c for x in BUILT_DROP):
                return
            hid = hidden or "hidden" in n.attrs or n.attrs.get("aria-hidden") == "true"
            if n.tag == "a" and n.attrs.get("href"):
                links.add(n.attrs["href"])
            if n.tag == "iframe":
                vids.update(youtube_ids(n.attrs.get("src")))
            if n.tag in BLOCK_TAGS:
                parts.append(" ")
            for ch in n.children:
                walk(ch, hid)
            if n.tag in BLOCK_TAGS:
                parts.append(" ")
        walk(main, False)
        return "".join(parts), links, vids

    report, checked, n_blocks, n_links = [], 0, 0, 0
    for key, page in sorted(pages.items()):
        if page["type"] not in ("page", "article", "staff", "calendar", "event") or key in retired:
            continue
        meta = index.get(key) or {}
        if not meta.get("file"):
            continue
        path = build.canon(key)
        if path.startswith(EXEMPT):
            continue
        f = ROOT / "docs" / ("index.html" if path == "/" else path.strip("/") + "/index.html")
        if not f.exists():
            continue
        live = parse((ROOT / "cache" / "raw" / meta["file"]).read_text())
        main = live.find(lambda x: x.tag == "main")
        if main is None:
            continue
        block = main.find(lambda x: "block-system-main-block" in cls(x)) or main
        title = re.sub(r"\s+", " ", page.get("title") or "").strip()
        text, hrefs, vids = built_region(parse(f.read_text()))
        built_t = tight(text)
        page_url = "/" if path == "/" else path.rstrip("/") + "/"
        built_keys = {built_url(h, page_url) for h in hrefs} - {None}
        built_paths = {k for k in built_keys}
        checked += 1
        # a live link to the page itself (or to a retired page merged into it) is dropped by design, with its label
        self_labels = set()
        for kind, href, label in live_links(block):
            k = live_url(href, key) if kind == "a" else None
            if k and k.startswith("mcroberts.sd38.bc.ca/") and "?" not in k and \
                    build.canon(k[len("mcroberts.sd38.bc.ca"):]).lower() == path.lower():
                self_labels.add(label)
        miss = []
        for b in live_blocks(block, title):
            if b in self_labels:
                continue
            if b in ("Read more", "Read More"):      # teaser link labels: the built rows link their titles instead
                continue
            t = tight(b)
            if t in built_t or tight(build.smart_case(b)) in built_t:
                continue
            miss.append(b)
        lost = []
        for kind, href, label in live_links(block):
            if kind == "iframe":
                ids = youtube_ids(href)
                if ids and not (ids & vids):
                    lost.append("video " + ", ".join(sorted(ids)))
                continue
            k = live_url(href, key)
            if not k:
                continue
            if k.startswith("mcroberts.sd38.bc.ca/") and not re.search(r"^mcroberts\.sd38\.bc\.ca/(files|sites|system)/", k):
                p_ = k[len("mcroberts.sd38.bc.ca"):].split("?")[0]
                k = ("mcroberts.sd38.bc.ca" + build.canon(p_)).lower() if not k.count("?") else k
            if k in built_paths or k.rstrip("/") in built_paths or k == ("mcroberts.sd38.bc.ca" + path).lower():
                continue
            lost.append("link " + k + ("  [" + label[:40] + "]" if label else ""))
        if miss or lost:
            report.append(f"live {path}: {len(miss)} text blocks, {len(lost)} links/videos not in the build")
            if verbose:
                report += [f"    - text: {m[:120]}" for m in miss[:20]]
                report += [f"    - {x[:140]}" for x in lost[:20]]
        n_blocks += len(miss)
        n_links += len(lost)
    return checked, report, n_blocks, n_links



if __name__ == "__main__":
    main()
