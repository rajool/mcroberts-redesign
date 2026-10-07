"""Turn the crawled Drupal pages (cache/raw/) into clean, structured content (content/).

Every word the redesign shows comes from here, so this script never invents text: it only
keeps, cleans and restructures what the live site already says.

    python3 tools/extract.py
"""
import base64, hashlib, html, json, re, subprocess, urllib.parse, urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "cache" / "raw"
OUT = ROOT / "content"
IMG_DIR = ROOT / "assets" / "content"
BASE = "https://mcroberts.sd38.bc.ca"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"

VOID = {"br", "hr", "img", "input", "meta", "link", "source", "wbr", "col", "area", "base", "embed", "param", "track"}
KEEP = {"p", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "a", "strong", "em", "table", "thead", "tbody", "tfoot",
        "tr", "th", "td", "caption", "img", "iframe", "blockquote", "hr", "br", "figure", "figcaption", "sup", "sub",
        "dl", "dt", "dd", "time", "details", "summary", "video", "source"}
RENAME = {"b": "strong", "i": "em", "h1": "h2"}
DROP = {"script", "style", "svg", "button", "form", "input", "select", "textarea", "label", "noscript", "nav", "template"}
ATTRS = {"a": {"href", "title"}, "img": {"src", "alt", "width", "height"}, "iframe": {"src", "title", "width", "height", "allow", "allowfullscreen"},
         "td": {"colspan", "rowspan"}, "th": {"colspan", "rowspan", "scope"}, "ol": {"start", "type", "reversed"},
         "time": {"datetime"}, "video": {"src", "controls", "poster"}, "source": {"src", "type"}}


# ---------------------------------------------------------------- tiny DOM
class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag, self.attrs, self.children, self.parent = tag, dict(attrs or {}), [], parent

    def cls(self):
        return self.attrs.get("class", "") or ""

    def has(self, c):
        return c in self.cls().split()

    def iter(self):
        yield self
        for ch in self.children:
            if isinstance(ch, Node):
                yield from ch.iter()

    def find(self, pred):
        for n in self.iter():
            if pred(n):
                return n
        return None

    def find_all(self, pred):
        return [n for n in self.iter() if pred(n)]

    def text(self):
        out = []
        for ch in self.children:
            out.append(ch.text() if isinstance(ch, Node) else ch)
        return "".join(out)


class Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse(s):
    b = Builder()
    b.feed(s)
    return b.root


# ---------------------------------------------------------------- helpers
ROUTES = {}  # crawled path -> True
IMAGES = {}  # source url -> local file name


def clean_text(s):
    s = s.replace("﻿", "").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()


def link(href):
    """Internal crawled page -> route ('/path'); anything else -> absolute URL on its own host."""
    if not href:
        return href
    href = href.strip()
    if href.startswith(("mailto:", "tel:", "#", "webcal:")):
        return href
    # typos in the live body that browsers resolve against the school host (and 404): https:/www.x, www.x
    href = re.sub(r"^(https?):/(?=[^/])", r"\1://", href)
    if re.match(r"^www\.[a-z0-9-]+\.[a-z]", href, re.I):
        href = "https://" + href
    absu = urllib.parse.urljoin(BASE + "/", href)
    u = urllib.parse.urlsplit(absu)
    if u.netloc in ("mcroberts.sd38.bc.ca", "www.mcroberts.sd38.bc.ca"):
        path = urllib.parse.unquote(u.path).rstrip("/") or "/"
        if path in ROUTES and not u.query:
            return path + ("#" + u.fragment if u.fragment else "")
        return BASE + u.path + ("?" + u.query if u.query else "") + ("#" + u.fragment if u.fragment else "")
    return absu


def save_image(src):
    """Copy an image into assets/content and return its local name (or None)."""
    if not src:
        return None
    if src in IMAGES:
        return IMAGES[src]
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if src.startswith("data:"):
            head, data = src.split(",", 1)
            ext = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp"}.get(head[5:].split(";")[0], "png")
            blob = base64.b64decode(data)
        else:
            absu = urllib.parse.urljoin(BASE + "/", src)
            ext = (re.search(r"\.(png|jpe?g|gif|webp|svg)", urllib.parse.urlsplit(absu).path, re.I) or [None, "jpg"])[1].lower().replace("jpeg", "jpg")
            try:
                req = urllib.request.Request(absu, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=30) as r:
                    blob = r.read()
            except Exception:  # some district hosts refuse the system Python's TLS; curl negotiates fine
                blob = subprocess.run(["curl", "-sSfL", "-A", UA, absu], capture_output=True, check=True).stdout
        name = hashlib.sha1(blob).hexdigest()[:12] + "." + ext
        (IMG_DIR / name).write_bytes(blob)
        IMAGES[src] = name
        return name
    except Exception as e:
        print("  image failed", src[:80], e)
        IMAGES[src] = None
        return None


def render(n):
    """Serialize a cleaned subtree to HTML."""
    if isinstance(n, str):
        return html.escape(n, quote=False)
    if n.tag == "#root":
        return "".join(render(c) for c in n.children)
    attrs = "".join(f' {k}="{html.escape(str(v))}"' if v is not None else f" {k}" for k, v in n.attrs.items())
    if n.tag in VOID:
        return f"<{n.tag}{attrs}>"
    return f"<{n.tag}{attrs}>" + "".join(render(c) for c in n.children) + f"</{n.tag}>"


def file_card(a, size=""):
    href = link(a.attrs.get("href", ""))
    name = clean_text(a.text())
    ext = (re.search(r"\.([a-z0-9]{2,4})(?:$|\?)", urllib.parse.unquote(href), re.I) or [None, "file"])[1].lower()
    n = Node("a", {"class": "file-card", "href": href, "data-ext": ext})
    if size:
        n.attrs["data-size"] = size
    n.children = [name]
    return n


def is_card(x):
    return isinstance(x, Node) and x.tag == "a" and x.has("file-card")


def group_cards(root):
    """Consecutive file cards (media file fields, one per Bootstrap column on the live site) → one div.file-list."""
    for n in list(root.iter()):
        if n.has("file-list"):
            continue
        out, run = [], []
        for ch in n.children + [None]:
            if is_card(ch):
                run.append(ch)
                continue
            if isinstance(ch, str) and not ch.strip() and run:
                continue
            if run:
                wrap = Node("div", {"class": "file-list"}, n)
                wrap.children = run
                out.append(wrap)
                run = []
            if ch is not None:
                out.append(ch)
        n.children = out
    return root


def transform(n, ctx):
    """Return a list of cleaned nodes/strings for node n."""
    if isinstance(n, str):
        return [n]
    tag = n.tag
    c = n.cls()
    if tag in DROP or "visually-hidden" in c.split() or tag == "#comment":
        # accordion buttons carry the question text; handled by the accordion branch
        return []
    if n.has("field--name-node-title") or n.has("nav-list") or "menu-back-button" in c or "section-menu-block" in c \
            or "sub-pages-menu-block" in c or n.has("feed-icons") or n.has("js-drupal-fullcalendar") or n.has("pagination"):
        return []
    if tag == "h1" and (not (ctx or {}).get("title") or clean_text(n.text()) == ctx["title"]):
        return []
    # Bootstrap paragraphs accordion -> <details>
    # (one .card.panel holds N .panel-heading / .panel-collapse pairs: one <details> per pair)
    if n.has("card") and n.find(lambda x: x.has("panel-collapse")):
        out, head = [], None
        for ch in n.children:
            if not isinstance(ch, Node):
                continue
            if ch.has("panel-heading"):
                head = ch
            elif ch.has("panel-collapse"):
                btn = head.find(lambda x: x.tag == "button") if head is not None else None
                d = Node("details", {"class": "accordion"})
                summ = Node("summary")
                summ.children = [clean_text((btn or head).text()) if (btn or head) is not None else ""]
                inner = Node("div", {"class": "accordion__body"})
                for c in ch.children:
                    inner.children.extend(transform(c, ctx))
                d.children = [summ, inner]
                out.append(d)
                head = None
        return out
    # file attachments
    if (tag == "span" and n.has("file")) or n.has("field--name-field-media-file"):
        return [file_card(a) for a in n.find_all(lambda x: x.tag == "a" and x.attrs.get("href"))]
    if n.has("field--name-field-legacy-attachments"):
        # field label "Attachments" + table (Attachment | Size) → the label, then one card per file with its size
        lab = n.find(lambda x: x.has("field__label"))
        out = []
        if lab is not None and clean_text(lab.text()):
            h = Node("h2")
            h.children = [clean_text(lab.text())]
            out.append(h)
        for tr in n.find_all(lambda x: x.tag == "tr"):
            a = tr.find(lambda x: x.tag == "a" and x.attrs.get("href"))
            if a is None:
                continue
            tds = [c for c in tr.children if isinstance(c, Node) and c.tag == "td"]
            out.append(file_card(a, clean_text(tds[1].text()) if len(tds) > 1 else ""))
        return out
    if n.has("paragraph--type-file-attachments"):
        # the paragraph keeps its own h2 and description (p, ul, video); its files follow as cards
        kids = []
        for ch in n.children:
            kids.extend(transform(ch, ctx))
        if not kids:
            return []
        wrap = Node("div", {"class": "paragraph--type-file-attachments"})
        wrap.children = kids
        return [wrap]
    # embedded video (Drupal oembed iframe)
    if tag == "iframe":
        src = n.attrs.get("src", "")
        if "/media/oembed" in src:
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(html.unescape(src)).query)
            yt = q.get("url", [""])[0]
            vid = (re.search(r"v=([\w-]{6,})", yt) or re.search(r"youtu\.be/([\w-]{6,})", yt))
            if vid:
                src = f"https://www.youtube-nocookie.com/embed/{vid.group(1)}"
        it = Node("iframe", {"src": html.unescape(src), "title": n.attrs.get("title") or "", "loading": "lazy", "allowfullscreen": None})
        if "forms.office.com" in src:
            it.attrs["class"] = "embed-form"
        elif "calendar.google.com" in src:
            it.attrs["class"] = "embed-calendar"
        elif "google.com/maps" in src:
            it.attrs["class"] = "embed-map"
        else:
            it.attrs["class"] = "embed-video"
        return [it]
    if tag == "img":
        name = save_image(n.attrs.get("src"))
        if not name:
            return []
        attrs = {"src": "@img/" + name, "alt": clean_text(n.attrs.get("alt", "") or "")}
        for k in ("width", "height"):
            v = n.attrs.get(k)
            if v and str(v).isdigit():
                attrs[k] = v
        attrs["loading"] = "lazy"
        return [Node("img", attrs)]
    kids = []
    for ch in n.children:
        kids.extend(transform(ch, ctx))
    tag = RENAME.get(tag, tag)
    if tag not in KEEP:
        return kids  # unwrap div/span/section/font/u/...
    allowed = ATTRS.get(tag, set())
    attrs = {k: v for k, v in n.attrs.items() if k in allowed}
    if tag == "a":
        href = attrs.get("href")
        if not href:
            return kids
        attrs["href"] = link(href)
        if attrs.get("title") and clean_text(attrs["title"]) == clean_text("".join(k if isinstance(k, str) else k.text() for k in kids)):
            attrs.pop("title")
    if tag in ("td", "th") and n.parent is not None and n.parent.tag == "tr":
        pass
    if tag == "iframe":
        attrs["loading"] = "lazy"
    m = Node(tag, attrs)
    m.children = kids
    return [m]


def tidy(root):
    """Remove empty blocks, collapse whitespace-only paragraphs, drop layout tables of one cell."""
    def empty(x):
        if isinstance(x, str):
            return not clean_text(x)
        if x.tag in ("img", "iframe", "hr", "br", "video"):
            return False
        return all(empty(c) for c in x.children)

    def walk(n):
        out = []
        for ch in n.children:
            if isinstance(ch, Node):
                walk(ch)
                if ch.tag in ("p", "li", "h2", "h3", "h4", "h5", "h6", "strong", "em", "a", "div", "blockquote", "summary", "figure") and empty(ch):
                    continue
            out.append(ch)
        # trim <br> at the start and end of blocks
        while out and isinstance(out[0], Node) and out[0].tag == "br":
            out.pop(0)
        while out and isinstance(out[-1], Node) and out[-1].tag == "br":
            out.pop()
        n.children = out
    walk(root)
    return root



BULLET = re.compile(r"^\s*[\u2022\u25cf\u00b7]\s*")


def structure(s):
    """Same words, real structure: typed bullets become lists, short bold lead-ins become headings."""
    def para(m):
        inner = m.group(1)
        segs = re.split(r"<br>", inner)
        if sum(1 for x in segs if BULLET.match(re.sub(r"<[^>]+>", "", x))) >= 2:
            out, run, text = [], [], []
            for seg in segs:
                plain = re.sub(r"<[^>]+>", "", seg)
                if BULLET.match(plain):
                    if text:
                        out.append("<p>" + "<br>".join(text).strip() + "</p>")
                        text = []
                    run.append("<li>" + re.sub(r"^(\s*(?:<[^>]+>)*)\s*[\u2022\u25cf\u00b7]\s*", r"\1", seg).strip() + "</li>")
                elif run and plain.strip()[:1].islower():  # a bullet that wrapped onto the next line
                    run[-1] = run[-1][:-5] + " " + seg.strip() + "</li>"
                else:
                    if run:
                        out.append("<ul>" + "".join(run) + "</ul>")
                        run = []
                    if plain.strip():
                        text.append(seg)
            if text:
                out.append("<p>" + "<br>".join(text).strip() + "</p>")
            if run:
                out.append("<ul>" + "".join(run) + "</ul>")
            return "".join(out)
        return m.group(0)
    s = re.sub(r"<p>(.*?)</p>", para, s)

    def lead(m):
        head, rest = m.group(1).strip(), m.group(2).strip()
        words = re.sub(r"<[^>]+>", "", head).strip()
        if 0 < len(words.split()) <= 7 and not words.endswith((".", ",")) and "<a" not in head:
            return f"<h3>{words.rstrip(':').strip()}</h3>" + (f"<p>{rest}</p>" if re.sub(r"<[^>]+>", "", rest).strip() else "")
        return m.group(0)
    s = re.sub(r"<p><strong>([^<]*(?:<em>[^<]*</em>)?[^<]*)</strong>(?:<br>)?(.*?)</p>", lead, s)
    return s


def clean_html(fragment_nodes, ctx=None):
    root = Node("#root")
    for n in fragment_nodes:
        root.children.extend(transform(n, ctx or {}))
    group_cards(root)
    tidy(root)
    s = render(root)
    s = re.sub(r"[ \t\r\n]+", " ", s)
    s = s.replace("﻿", "").replace("&nbsp;", " ")
    s = re.sub(r">\s+<", "><", s)
    s = re.sub(r"(<br>\s*){3,}", "<br><br>", s)
    return structure(s).strip()


# ---------------------------------------------------------------- page readers
def main_node(doc):
    return doc.find(lambda x: x.tag == "main")


def page_title(main):
    h1 = main.find(lambda x: x.tag == "h1")
    return clean_text(h1.text()) if h1 else ""


def read_article(main):
    node = main.find(lambda x: x.has("node--type-article"))
    t = main.find(lambda x: x.tag == "time" and x.attrs.get("datetime"))
    date = t.attrs["datetime"][:10] if t else None
    body_parts = []
    for n in (node or main).iter():
        if n.has("field--name-body") or n.has("field--name-field-section-content") or n.has("field--name-field-media-image") \
                or n.has("paragraph--type-file-attachments") or n.has("field--name-field-legacy-attachments") or n.has("field--name-field-banner-image") \
                or n.has("field--name-field-media-file") or (n.tag == "h2" and n.has("field-label-above")) \
                or n.has("paragraph--type-image-gallery"):
            # skip nested matches (a field inside an already-taken field)
            p = n.parent
            nested = False
            while p is not None:
                if p in body_parts:
                    nested = True
                    break
                p = p.parent
            if not nested:
                body_parts.append(n)
    return date, clean_html(body_parts, {"title": page_title(main)})


def read_page(main):
    """Generic Drupal page: everything in the main content block except the title and the page's own menus."""
    block = main.find(lambda x: x.has("block-system-main-block")) or main
    return clean_html([block], {"title": page_title(main)})


def read_navlist(main):
    nl = main.find(lambda x: x.has("nav-list"))
    if not nl:
        return []
    return [{"title": clean_text(a.text()), "href": link(a.attrs.get("href"))} for a in nl.find_all(lambda x: x.tag == "a")]


def read_staff(main):
    groups = []
    view = main.find(lambda x: x.has("view-staff-page-list"))
    if not view:
        return groups
    cur = None
    for n in view.iter():
        if n.tag == "h2":
            cur = {"group": clean_text(n.text()), "cols": [], "rows": []}
            groups.append(cur)
        elif n.tag == "th" and cur is not None and n.parent is not None and n.parent.parent is not None and n.parent.parent.tag == "thead":
            cur["cols"].append(clean_text(n.text()))
        elif n.tag == "tr" and cur is not None and n.parent.tag == "tbody":
            cells = [c for c in n.children if isinstance(c, Node) and c.tag == "td"]
            row = [clean_text(c.text()) for c in cells]
            email = next((a.attrs["href"][7:] for c in cells for a in c.find_all(lambda x: x.tag == "a") if a.attrs.get("href", "").startswith("mailto:")), "")
            cur["rows"].append({"name": row[0] if row else "", "position": row[1] if len(row) > 1 else "", "email": email,
                                "cells": [clean_html(list(c.children)) for c in cells]})
    return groups


def read_listing(main):
    """News teasers from listing pages (front page, /news, /news/newsletters, article feeds)."""
    items = []
    for h in main.find_all(lambda x: x.tag in ("h2", "h3") and x.find(lambda y: y.tag == "a")):
        a = h.find(lambda y: y.tag == "a")
        href = a.attrs.get("href", "")
        if not href.startswith(("/news/", "/our-school-story/", "/school-learning-story/")):
            continue
        box = h.parent
        teaser, date = "", None
        for _ in range(4):
            if box is None:
                break
            if len(box.find_all(lambda y: y.tag in ("h2", "h3") and y.find(lambda z: z.tag == "a"))) > 1:
                break          # climbed past this item into the list
            t = box.find(lambda y: y.tag == "time" and y.attrs.get("datetime"))
            sm = box.find(lambda y: y.has("small") and y is not h)
            if t and not date:
                date = t.attrs["datetime"][:10]
            if sm and not teaser and not sm.find(lambda y: y.tag == "time"):
                teaser = clean_text(sm.text())
            # the vertical_teaser view mode prints the trimmed body summary instead (minus its Read more link)
            fb = box.find(lambda y: y.has("field--name-body"))
            if fb is not None and not teaser:
                teaser = clean_text("".join(c if isinstance(c, str) else ("" if c.has("more-link") else c.text())
                                            for c in fb.children))
            if date or teaser:
                break
            box = box.parent
        item = {"title": clean_text(a.text()), "href": href.rstrip("/"), "date": date, "teaser": teaser}
        if href.startswith(("/school-learning-story/", "/our-school-story/")):
            # the feed's square teaser thumbnail (image style square_image_thumbnail_220x220), when the post has one
            box = h.parent
            for _ in range(4):
                if box is None:
                    break
                if len(box.find_all(lambda y: y.tag in ("h2", "h3") and y.find(lambda z: z.tag == "a"))) > 1:
                    break          # climbed past this item into the list
                im = box.find(lambda y: y.tag == "img" and "220x220" in y.attrs.get("src", ""))
                if im is not None:
                    name = save_image(im.attrs["src"])
                    if name:
                        item["img"] = name
                    break
                box = box.parent
        items.append(item)
    return items


def read_blocks(doc, region_id):
    """Sidebar blocks of the front page, as heading + cleaned HTML."""
    reg = doc.find(lambda x: x.attrs.get("id") == region_id)
    if not reg:
        return []
    out = []
    for b in reg.find_all(lambda x: x.has("block") and x.attrs.get("id")):
        h = next((c for c in b.children if isinstance(c, Node) and c.tag == "h2"), None)
        content = b.find(lambda x: x.has("content"))
        out.append({"id": b.attrs["id"], "heading": clean_text(h.text()) if h else "", "html": clean_html([content]) if content else ""})
    return out


# ---------------------------------------------------------------- calendar
def read_ics(path):
    events = []
    text = path.read_text().replace("\r\n ", "").replace("\n ", "")
    for block in text.split("BEGIN:VEVENT")[1:]:
        block = block.split("END:VEVENT")[0]
        ev = {}
        for line in block.strip().splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            key = k.split(";")[0]
            ev[key] = (v, k)
        def dt(key):
            if key not in ev:
                return None, False
            v, k = ev[key]
            if "VALUE=DATE" in k or len(v) == 8:
                return datetime.strptime(v[:8], "%Y%m%d").strftime("%Y-%m-%d"), True
            return datetime.strptime(v[:15], "%Y%m%dT%H%M%S").strftime("%Y-%m-%dT%H:%M"), False
        start, allday = dt("DTSTART")
        end, _ = dt("DTEND")
        summ = clean_text(ev.get("SUMMARY", ("", ""))[0].replace("\\,", ",").replace("\\;", ";"))
        url = ev.get("URL", ("", ""))[0]
        loc = clean_text(ev.get("LOCATION", ("", ""))[0].replace("\\,", ","))
        desc = clean_text(ev.get("DESCRIPTION", ("", ""))[0].replace("\\n", " ").replace("\\,", ","))
        events.append({"title": summ, "start": start, "end": end, "allDay": allday, "url": link(url) if url else "", "location": loc, "description": desc})
    events.sort(key=lambda e: (e["start"] or "", e["title"]))
    return events


def read_fullcalendar(path):
    """The live School Calendar page embeds its FullCalendar events (drupalSettings.fullCalendarView[n].calendar_options):
    the ICS feed's events plus the weeks before the feed starts (the feed begins a week back; the page's own grid from
    the start of the school year). Same shape as read_ics."""
    raw = path.read_text(errors="replace")
    m = re.search(r'<script type="application/json" data-drupal-selector="drupal-settings-json">(.*?)</script>', raw, re.S)
    if not m:
        return []
    events, seen = [], set()
    for view in json.loads(m.group(1)).get("fullCalendarView") or []:
        for e in json.loads(view.get("calendar_options") or "{}").get("events", []):
            title = clean_text(html.unescape(e.get("title", "")))
            allday = bool(e.get("allDay"))
            start = (e.get("start") or "")[:10 if allday else 16]
            if not title or not start or (title, start) in seen:
                continue
            seen.add((title, start))
            events.append({"title": title, "start": start, "end": (e.get("end") or "")[:10 if allday else 16] or None,
                           "allDay": allday, "url": link(e["url"]) if e.get("url") else "", "location": "",
                           "description": clean_text(html.unescape(e.get("des") or ""))})
    return events


def merge_events(feed, page):
    """The feed is the source; the calendar page fills in the dates before the feed's first date."""
    if not feed:
        return page
    first = min(e["start"] for e in feed)
    out = [e for e in page if e["start"] < first] + feed
    out.sort(key=lambda e: (e["start"] or "", e["title"]))
    return out


# ---------------------------------------------------------------- main
def main():
    index = json.loads((ROOT / "cache" / "index.json").read_text())
    for k, v in index.items():
        if v.get("file") and "?" not in k:
            ROUTES[k] = True
    OUT.mkdir(exist_ok=True)
    pages, news = {}, {}
    home_doc = parse((RAW / index["/"]["file"]).read_text())

    for key, meta in sorted(index.items()):
        if not meta.get("file"):
            continue
        doc = parse((RAW / meta["file"]).read_text())
        main_ = main_node(doc)
        if main_ is None:
            continue
        # listings (paginated or not) feed the news index
        for it in read_listing(main_):
            cur = news.setdefault(it["href"], it)
            for f in ("date", "teaser", "img"):
                if not cur.get(f) and it.get(f):
                    cur[f] = it[f]
            if key.startswith("/news/newsletters"):
                cur["newsletter"] = True
        if "?" in key:
            continue
        body_cls = (doc.find(lambda x: x.tag == "body") or Node("body")).cls()
        title = page_title(main_)
        rec = {"path": key, "title": title}
        if main_.find(lambda x: x.has("node--type-article")) and not main_.find(lambda x: x.has("view-article-feed")):
            rec["type"] = "article"
            rec["date"], rec["body"] = read_article(main_)
        elif main_.find(lambda x: x.has("node--type-calendar-event")):
            rec["type"] = "event"
            t = main_.find(lambda x: x.tag == "time" and x.attrs.get("datetime"))
            rec["date"] = t.attrs["datetime"] if t else None
            rec["body"] = read_page(main_)
        elif main_.find(lambda x: x.has("node--type-staff-page")):
            rec["type"] = "staff"
            rec["staff"] = read_staff(main_)
            rec["body"] = ""
        elif main_.find(lambda x: x.has("node--type-calendar-page")):
            rec["type"] = "calendar"
            rec["body"] = read_page(main_)
            ft = main_.find(lambda x: x.has("view-footer"))
            rec["notes"] = clean_html([ft]) if ft else ""
        elif key == "/":
            rec["type"] = "home"
        elif main_.find(lambda x: x.has("view-news-archive-page")) or main_.find(lambda x: x.has("view-article-feed")):
            rec["type"] = "listing"
            rec["items"] = [it["href"] for it in read_listing(main_)]
            intro = main_.find(lambda x: x.has("field--name-body"))
            rec["body"] = clean_html([intro]) if intro else ""
        else:
            rec["type"] = "page"
            rec["body"] = read_page(main_)
        rec["children"] = read_navlist(main_)
        rec["bodyClass"] = body_cls
        pages[key] = rec
        print(f"{rec['type']:9} {key}")

    # navigation tree (main menu on the front page)
    nav = home_doc.find(lambda x: x.attrs.get("id") == "block-mainnavigation")
    menu = []
    for li in [c for c in nav.find(lambda x: x.tag == "ul").children if isinstance(c, Node) and c.tag == "li"]:
        a = li.find(lambda x: x.tag == "a")
        item = {"title": clean_text(a.text()), "href": link(a.attrs.get("href")), "children": []}
        sub = li.find(lambda x: x.tag == "ul")
        if sub:
            for sli in [c for c in sub.children if isinstance(c, Node) and c.tag == "li"]:
                sa = sli.find(lambda x: x.tag == "a")
                item["children"].append({"title": clean_text(sa.text()), "href": link(sa.attrs.get("href"))})
        menu.append(item)

    # site-wide facts, straight from the header, sidebars and footer of the front page
    header = home_doc.find(lambda x: x.has("header-content"))
    logo = header.find(lambda x: x.tag == "img")
    motto = header.find(lambda x: x.tag == "em")
    addr = home_doc.find(lambda x: x.has("block-content-address_block"))
    social = [{"href": a.attrs["href"], "kind": a.cls().replace("social-media-link-icon--", "")}
              for a in home_doc.find(lambda x: x.attrs.get("id") == "block-socialmedialinks").find_all(lambda x: x.tag == "a")]
    quick = []
    for b in home_doc.find_all(lambda x: x.has("view-district-quick-links") or x.has("view-home-page-buttons")):
        for a in b.find_all(lambda x: x.tag == "a"):
            img = a.find(lambda x: x.tag == "img")
            quick.append({"href": link(a.attrs.get("href")), "title": a.attrs.get("title", ""), "img": save_image(img.attrs.get("src")) if img else None,
                          "source": "district" if b.has("view-district-quick-links") else "school"})
    # the header background image lives in inline CSS
    raw_home = (RAW / index["/"]["file"]).read_text()
    bg = re.search(r"url\(['\"]?([^'\")]*mcroberts-bg[^'\")]*)", raw_home)
    site = {
        "name": clean_text(header.find(lambda x: x.tag == "h1").text()),
        "motto": clean_text(motto.text()) if motto else "",
        "logo": save_image(logo.attrs.get("src").replace("/styles/large/public", "")) or save_image(logo.attrs.get("src")),
        "logoStyled": save_image(logo.attrs.get("src")),
        "headerImage": save_image(bg.group(1)) if bg else None,
        "district": {"name": "School District No. 38 (Richmond)", "href": "https://www.sd38.bc.ca", "logo": save_image("/themes/custom/rsd_sites_barrio/images/sd38-logo-white.png")},
        "address": [clean_text(s.text()) for s in addr.find_all(lambda x: x.tag == "span")],
        "mapHref": addr.find(lambda x: x.tag == "a").attrs.get("href"),
        "phone": "604-668-6600",
        "email": "mcroberts@sd38.bc.ca",
        "social": social,
        "quickLinks": quick,
        "frontBlocks": read_blocks(home_doc, "sidebar_first") + read_blocks(home_doc, "sidebar_second"),
        "copyright": "Copyright © 2026 School District No. 38 (Richmond)",
        "accessibilityNote": clean_html([home_doc.find(lambda x: x.attrs.get("id") == "accessibilityModal").find(lambda x: x.tag == "p")]),
        "frontNews": [it["href"] for it in read_listing(main_node(home_doc))],
        # GTranslate block settings (native language names are shown in the switcher)
        "translateLanguages": json.loads((re.search(r'"languages":(\[[^\]]*\])', raw_home) or [None, "[]"])[1]),
    }

    events = merge_events(read_ics(ROOT / "cache" / "calendar-feed.ics"), read_fullcalendar(RAW / index["/school-calendar"]["file"]))
    # crawled articles get their date onto the news index
    for p in pages.values():
        if p["type"] == "article" and p["path"] in news and not news[p["path"]].get("date"):
            news[p["path"]]["date"] = p.get("date")
    news_list = sorted(news.values(), key=lambda x: (x.get("date") or "", x["title"]), reverse=True)

    (OUT / "pages.json").write_text(json.dumps(pages, indent=1, ensure_ascii=False))
    (OUT / "menu.json").write_text(json.dumps(menu, indent=1, ensure_ascii=False))
    (OUT / "site.json").write_text(json.dumps(site, indent=1, ensure_ascii=False))
    (OUT / "news.json").write_text(json.dumps(news_list, indent=1, ensure_ascii=False))
    (OUT / "events.json").write_text(json.dumps(events, indent=1, ensure_ascii=False))
    print("pages", len(pages), "news", len(news_list), "events", len(events), "images", len([v for v in IMAGES.values() if v]))


if __name__ == "__main__":
    main()
