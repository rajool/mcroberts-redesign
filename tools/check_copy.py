"""Check that the redesign says nothing new: every visible phrase must exist on the live site.

Reads every .html file under the given folders (default: docs/), collects visible text (aria-hidden text included:
it is still on screen) plus alt, title and aria-label values, and looks each phrase up in content/corpus.txt (case- and whitespace-insensitive).
Allowed besides the corpus: content/corpus-images.txt (text inside the site's images), tools/ui_words.txt (one phrase per line), dates, times and numbers, and the
concept banner (<div class="concept-banner">). A phrase the live site splits across inline elements is also matched with
whitespace removed, against the corpus and against the page bodies extracted from the live site (content/pages.json).

Documented exception: docs/proposal/ is not checked. It is Ali's proposal to the principal, the document about this
concept (linked from the banner as "About this concept"), not school content, so it is the one page allowed new words.

    python3 tools/check_copy.py [folder ...]      # exit 1 when a phrase is not found
"""
import html, re, sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXEMPT = [ROOT / "docs" / "proposal"]     # the documented exception above: the proposal may use new words

MONTHS = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
DAYS = r"(mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)[a-z]*\.?"
DATEISH = re.compile(rf"^(({MONTHS}|{DAYS}|\d{{1,4}}|am|pm|a\.m\.|p\.m\.|today|[-–—/:,.·•|()+]|\s)+)$", re.I)


def norm(s):
    s = html.unescape(s).replace("﻿", "").replace(" ", " ")
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-"), ("…", "...")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip().lower()


class Visible(HTMLParser):
    SKIP = {"script", "style", "svg", "noscript", "head", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.phrases, self.banner = [], [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("br", "img", "input", "meta", "link", "hr", "source", "wbr"):
            if tag == "img" and a.get("alt"):
                self.phrases.append(a["alt"])
            return
        # aria-hidden text is still on screen (file badges, captions, decorative words), so it is checked too
        skip = tag in self.SKIP or "concept-banner" in (a.get("class") or "").split()
        self.stack.append((tag, skip))
        if not self.skipping():
            for k in ("title", "aria-label", "placeholder"):
                if a.get(k):
                    self.phrases.append(a[k])

    def skipping(self):
        return any(s for _, s in self.stack)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, d):
        if not self.skipping() and d.strip():
            self.phrases.append(d)


def main():
    folders = [Path(a).resolve() for a in sys.argv[1:]] or [ROOT / "docs"]
    texts = [(ROOT / "content" / f).read_text() for f in ("corpus.txt", "corpus-images.txt") if (ROOT / "content" / f).exists()]
    corpus = norm(" \n ".join(t.replace("\n", " \n ") for t in texts))
    # The corpus has one line per live text node, so a sentence the live page splits across inline elements
    # (a link, a bold word, a quote) is checked once more with all whitespace removed.
    corpus_tight = re.sub(r"\s+", "", corpus)
    # corpus.txt keeps each live line once, so a word repeated inside a longer sentence can be missing there;
    # the page bodies extracted from the live site (content/pages.json) are the second source of truth.
    pages_path = ROOT / "content" / "pages.json"
    if pages_path.exists():
        import json
        bodies = " ".join((v.get("title") or "") + " " + re.sub(r"<[^>]+>", " ", v.get("body") or "")
                          for v in json.loads(pages_path.read_text()).values())
        corpus_tight += re.sub(r"\s+", "", norm(bodies))
    ui_path = ROOT / "tools" / "ui_words.txt"
    ui = {norm(x) for x in ui_path.read_text().splitlines() if x.strip()} if ui_path.exists() else set()
    missing = {}
    files = [p for f in folders for p in sorted(f.rglob("*.html"))
             if not any(d == p.parent or d in p.parents for d in EXEMPT)]
    for p in files:
        v = Visible()
        v.feed(p.read_text())
        for raw in v.phrases:
            t = norm(raw).strip(" :;,.!?-–—|·•()[]\"'")
            if not t or DATEISH.match(t) or t in ui or not re.search(r"[a-z]", t):
                continue
            if t in corpus or re.sub(r"\s+", "", t) in corpus_tight:
                continue
            missing.setdefault(t, set()).add(str(p.relative_to(ROOT)))
    for t, where in sorted(missing.items()):
        print(f"NEW  {t!r}  <- {', '.join(sorted(where)[:3])}{' ...' if len(where) > 3 else ''}")
    print(f"checked {len(files)} files: {len(missing)} phrases not on the live site")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
