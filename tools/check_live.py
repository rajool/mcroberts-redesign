"""Compare every built page with the LIVE page it came from (cache/raw/), independently of tools/extract.py.

For each live content page: every text fragment inside the live main content block (accordion questions
included) must appear in the built page's <main>, and every document the live page links to (PDF, Word,
Excel, PowerPoint, /files/...) must be linked from the built page. Built pages are found at their IA path
(design/ia.json "paths"); retired pages are skipped.

    python3 tools/check_live.py        # summary, exit 1 on any gap
    python3 tools/check_live.py -v     # every missing fragment and document
"""
import json, re, sys, urllib.parse
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_copy import norm  # noqa: E402
from check_fidelity import Text  # noqa: E402  (visible text of the built <main>)

VOID = {"br", "img", "input", "meta", "link", "hr", "source", "wbr", "col", "area", "base", "embed", "param", "track"}
SKIP_TAGS = {"script", "style", "svg", "noscript", "template", "form", "select", "textarea"}
SKIP_CLASSES = {"visually-hidden", "nav-list", "pagination", "js-drupal-fullcalendar", "feed-icons", "field--name-node-title"}
SKIP_SUBSTR = ("menu-back-button", "section-menu-block", "sub-pages-menu-block")
DOC = re.compile(r"(/files/|\.(pdf|docx?|xlsx?|pptx?)(\?|#|$))", re.I)
BASE = "https://mcroberts.sd38.bc.ca/"


class LiveMain(HTMLParser):
    """Text fragments and document links inside the live page's main content block."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.depth_in, self.frags, self.docs = [], None, [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "")
        if tag in VOID:
            if tag == "img" and self.inside() and a.get("alt"):
                pass  # live alt text is too often a file name; images are compared by the reviewers
            return
        skip = tag in SKIP_TAGS or bool(set(cls.split()) & SKIP_CLASSES) or any(s in cls for s in SKIP_SUBSTR) or tag == "h1"
        self.stack.append((tag, skip))
        if self.depth_in is None and "block-system-main-block" in cls.split():
            self.depth_in = len(self.stack)
        if tag == "a" and self.inside() and a.get("href") and DOC.search(a["href"]):
            self.docs.add(canon(a["href"]))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                if self.depth_in is not None and i < self.depth_in:  # left the main content block
                    self.depth_in = None
                del self.stack[i:]
                break

    def inside(self):
        return self.depth_in is not None and len(self.stack) >= self.depth_in and not any(s for _, s in self.stack)

    def handle_data(self, d):
        if self.inside():
            d = re.sub(r"[\x80-\x9f​-‍⁠﻿]", "", d)
            t = norm(d).strip(" :;,.|·•-–—")
            if len(t) >= 3 and re.search(r"[a-z]", t) and t not in ("read more", "attachment", "size"):  # teaser links and Drupal file-table headers
                self.frags.append(t)


def canon(href):
    u = urllib.parse.urlsplit(urllib.parse.urljoin(BASE, href.strip()))
    return (u.netloc.replace("www.", "") + urllib.parse.unquote(u.path)).lower()


class BuiltLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs = set()

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            h = dict(attrs).get("href")
            if h:
                self.hrefs.add(canon(h))


def main():
    verbose = "-v" in sys.argv
    index = json.loads((ROOT / "cache" / "index.json").read_text())
    pages = json.loads((ROOT / "content" / "pages.json").read_text())
    ia = json.loads((ROOT / "design" / "ia.json").read_text()) if (ROOT / "design" / "ia.json").exists() else {}
    new_of = {old: new for new, old in (ia.get("paths") or {}).items()}
    retired = set(ia.get("retired") or {})
    total_frag = total_doc = missing_pages = checked = 0
    lines = []
    for key, page in sorted(pages.items()):
        if page["type"] not in ("page", "article", "staff", "calendar") or key.startswith("/2026/") or key in retired:
            continue
        meta = index.get(key) or {}
        if not meta.get("file"):
            continue
        live = LiveMain()
        live.feed((ROOT / "cache" / "raw" / meta["file"]).read_text())
        path = new_of.get(key, key)
        f = ROOT / "docs" / path.strip("/") / "index.html"
        if not f.exists():
            missing_pages += 1
            lines.append(f"MISSING PAGE {path} (live {key})")
            continue
        html_text = f.read_text()
        t = Text(main_only=True)
        t.feed(html_text)
        built = norm(" ".join(t.parts))
        built_ns = built.replace(" ", "")
        links = BuiltLinks()
        links.feed(html_text)
        miss_f = [x for x in dict.fromkeys(live.frags) if x not in built and x.replace(" ", "") not in built_ns]
        miss_d = sorted(d for d in live.docs if d not in links.hrefs)
        checked += 1
        if miss_f or miss_d:
            words = sum(len(x.split()) for x in miss_f)
            lines.append(f"{path}: {len(miss_f)} fragments (~{words} words), {len(miss_d)} documents missing")
            if verbose:
                lines += [f"    - {x[:120]}" for x in miss_f[:20]]
                lines += [f"    # {d}" for d in miss_d[:20]]
        total_frag += len(miss_f)
        total_doc += len(miss_d)
    print("\n".join(lines))
    print(f"checked {checked} pages against the live HTML: {missing_pages} missing pages, {total_frag} missing fragments, {total_doc} missing documents")
    sys.exit(1 if (missing_pages or total_frag or total_doc) else 0)


if __name__ == "__main__":
    main()
