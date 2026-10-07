#!/usr/bin/env python3
"""Render content/ into docs/ (GitHub Pages) with the shared theme in theme/.

Every page is plain server-rendered HTML whose markup mirrors what the Drupal 10 sub-theme `mcroberts`
(bootstrap_barrio) would print: live region names, ids and module classes are kept, and each component carries a
comment naming its Drupal source. Every link and asset URL is relative, so the site works under any sub-path.

    python3 build.py                 # build for today (America/Vancouver)
    BUILD_DATE=2026-10-16 python3 build.py   # build as if it were another day (today-dependent parts)

The site structure comes from design/ia.json: the main menu (desktop mega panels and the phone accordion), the utility
bar, the footer columns, the grouped hub sections, the clean URLs every page is rendered at, and a redirect stub at
every old URL (path alias + Redirect module). Breadcrumbs, the section menu, the section pager and search.json follow it.

Besides basic pages, articles and hubs it renders the special views: School Calendar (agenda + JS month grid),
calendar events (/2026/*), Bell Schedule (the timetable image as tables + live now/next), Our Staff (filterable
tables), News Archive / Newsletters (filter + pager), School Learning Story (content/learning-story.json, made by
tools/learning_story.py), /search (client-side, over docs/assets/search.json) and 404.html. Today-dependent parts
embed a small JSON and are refreshed in the browser (theme/js/today.js, calendar.js, bell.js); for testing, the
calendar and bell pages accept ?today=YYYY-MM-DD&time=HH:MM. Files are only rewritten when their content changes.

Python 3.9+ standard library only; macOS `sips` resizes two images when present (otherwise originals are copied).
"""
import html
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
THEME = ROOT / "theme"
DOCS = ROOT / "docs"
LIVE = "https://mcroberts.sd38.bc.ca"

CSS_FILES = ["tokens.css", "base.css", "layout.css", "components.css", "pages.css"]
PRINT_CSS = "print.css"
JS_FILES = ["behaviors.js", "nav.js", "a11y.js"]
# Only what the design uses: Newsreader roman with its optical sizes (display headings), the italic without them
# (a few words: slogan, "Secondary School", quotes), Noto Sans 400-750. 232 KB instead of 315 KB on first load.
FONTS = ("https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400..600"
         "&family=Newsreader:ital,wght@1,300..600&family=Noto+Sans:wght@400..750&display=swap")

# ---------------------------------------------------------------------------------------------- information architecture
# design/ia.json is the site structure: menus (main, utility, footer), hub sections, clean URLs and retired pages.
# Drupal: path aliases (+ Pathauto patterns) give each node its clean URL; the Redirect module answers every old alias
# with a 301 (here: a redirect stub page at the old path, see redirect_stub()).
IA = json.loads((ROOT / "design" / "ia.json").read_text())
NEW_OF = {old: new for new, old in IA["paths"].items()}      # live path → clean URL
RETIRED = dict(IA.get("retired") or {})                      # retired live path → where it redirects


def canon(path):
    """A live path (or a clean URL) → the URL this site serves that content at."""
    for _ in range(4):
        if path in NEW_OF:
            path = NEW_OF[path]
        elif path in RETIRED:
            path = RETIRED[path]
        else:
            break
    return path


# ---------------------------------------------------------------------------------------------- content
# Every content record is keyed by its clean URL; the live path it came from is kept in "livePath".
_PAGES_RAW = json.loads((CONTENT / "pages.json").read_text())
PAGES = {}
for _k, _v in _PAGES_RAW.items():
    if _k in RETIRED:
        continue
    _v = dict(_v, livePath=_k)
    for _c in _v.get("children") or []:
        if _c.get("href"):
            _c["href"] = canon(_c["href"])
    if _v.get("items"):
        _v["items"] = [canon(h) for h in _v["items"] if h not in RETIRED]
    PAGES[canon(_k)] = _v
SITE = json.loads((CONTENT / "site.json").read_text())
SITE["frontNews"] = [canon(h) for h in SITE.get("frontNews", []) if h not in RETIRED]
NEWS = [dict(n, href=canon(n["href"])) for n in json.loads((CONTENT / "news.json").read_text())
        if n["href"] not in RETIRED]                          # a retired duplicate post is not listed twice
EVENTS_RAW = json.loads((CONTENT / "events.json").read_text())
BELL = json.loads((CONTENT / "bell-schedule.json").read_text())
IMAGES = json.loads((CONTENT / "images.json").read_text())
_rank_file = CONTENT / "news-rank.json"           # tools/news_rank.py: position in the live listing, 0 = newest
NEWS_RANK = {canon(k): v for k, v in (json.loads(_rank_file.read_text()) if _rank_file.exists() else {}).items()}
_dates_file = CONTENT / "article-dates.json"
ARTICLE_DATES = {canon(k): v for k, v in (json.loads(_dates_file.read_text()) if _dates_file.exists() else {}).items()
                 if k not in RETIRED}

CREST = "39ef9ae7e316.png"          # the logo: copied byte for byte, never altered
DISTRICT_LOGO = SITE["district"]["logo"]
HEADER_IMG = SITE["headerImage"]
STRIKERS_LOGO = "9f4ea14a6ad5.png"
BUILDING = "de1fed0d163f.png"
# Right-sized copies made with sips (decision fix 6): name -> (output name, sips arguments)
DERIVED = {
    STRIKERS_LOGO: ("9f4ea14a6ad5-480.png", ["-Z", "480"]),
    BUILDING: ("de1fed0d163f.jpg", ["-s", "format", "jpeg", "-s", "formatOptions", "80"]),
}
# The crest scaled down (pixels untouched otherwise) for the masthead, sticky nav and drawer (shown at most 84 px tall),
# and as the favicon and touch icon; the original file still ships byte for byte (sign-off, and the logo itself).
CREST_SIZES = {"200": ("39ef9ae7e316-200.png", ["-Z", "200"]), "180": ("39ef9ae7e316-180.png", ["-Z", "180"]),
               "32": ("39ef9ae7e316-32.png", ["-Z", "32"])}
CREST_USED = set()


def crest_src(cur, size):
    """URL of a scaled crest copy (made with sips in copy_assets), with its pixel size."""
    out_name, _ = CREST_SIZES[size]
    CREST_USED.add(size)
    w, h = IMAGES["size"].get(CREST, [400, 348])
    k = int(size) / max(w, h)
    return asset(cur, "img/" + out_name), round(w * k), round(h * k)

NAME = SITE["name"]
PHONE = SITE["phone"]                       # 604-668-6600
PHONE_DOTS = PHONE.replace("-", ".")        # 604.668.6600 (the footer spelling)
TEL = "tel:+1" + re.sub(r"\D", "", PHONE)
TEL_EXT = TEL + ",1"
EMAIL = SITE["email"]
ADDR1 = SITE["address"][0]
ADDR2 = "{}, {} {}".format(SITE["address"][1], SITE["address"][2], SITE["address"][3])
# the postal code never breaks across lines
ADDR2_HTML = "{}, {} <span class=\"nowrap\">{}</span>".format(html.escape(SITE["address"][1]), html.escape(SITE["address"][2]),
                                                         html.escape(SITE["address"][3]))
LANG_NAMES = {"en": "English", "zh-CN": "简体中文", "zh-TW": "繁體中文", "fr": "Français", "de": "Deutsch",
              "it": "Italiano", "ja": "日本語", "ru": "Русский", "es": "Español", "ko": "한국어", "pa": "ਪੰਜਾਬੀ",
              "hi": "हिन्दी", "tl": "Tagalog", "vi": "Tiếng Việt", "fa": "فارسی", "ar": "العربية"}

LANG_TAGS = {"zh-CN": "zh-Hans", "zh-TW": "zh-Hant"}     # BCP 47 tags for the option lang attributes
_story_file = CONTENT / "learning-story.json"
STORY = json.loads(_story_file.read_text()) if _story_file.exists() else {"intro": "", "sections": []}
for _sec in STORY.get("sections", []):
    for _it in _sec.get("items", []):
        _it["href"] = canon(_it["href"])

# Pages this build renders (at their clean URLs): every node the crawl found, plus the client-side search page
SEARCH = "/search"
BUILT = {"/", SEARCH} | {p for p, v in PAGES.items()
                         if v["type"] in ("page", "article", "listing", "calendar", "staff", "event")}
# Old URLs that answer with a redirect: every live path that has a clean alias, and every retired page
REDIRECTS = {old: canon(old) for old in list(NEW_OF) + list(RETIRED)}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]
MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
               "October", "November", "December"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAYS_LONG = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
COLS = {0: "MON", 1: "TUE", 2: "WED", 3: "THU", 4: "FRI"}

USED_IMAGES = set()
HEADING_IDS = {}                 # page → ids given to its body headings
CHROME_IDS = {"page-title", "main-content", "page-wrapper", "site-header", "mobile-search", "menu-drawer", "a11y-dialog", "a11y-title",
              "block-a11y", "alert-title", "alert-more", "header-img-area", "block-breadcrumbs", "block-mainnavigation",
              "section-nav-title", "contact-card-title", "child-title", "pager-title", "bar-absent", "today", "events-title",
              "news-title", "tasks-title", "contact-title", "about-title", "strikers-title", "rail-news-title"}


def build_today():
    forced = os.environ.get("BUILD_DATE")
    if forced:
        return date.fromisoformat(forced)
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Vancouver")).date()
    except Exception:
        return date.today()


TODAY = build_today()

# ---------------------------------------------------------------------------------------------- tiny DOM
VOID = {"br", "hr", "img", "input", "meta", "link", "source", "wbr", "col", "area", "base", "embed", "param", "track"}


class El:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children = []
        self.parent = parent

    def cls(self):
        return (self.attrs.get("class") or "").split()

    def add_class(self, c):
        cs = self.cls()
        if c not in cs:
            cs.append(c)
        self.attrs["class"] = " ".join(cs)

    def iter(self):
        yield self
        for ch in self.children:
            if isinstance(ch, El):
                yield from ch.iter()

    def elements(self, tag=None):
        return [n for n in self.iter() if n is not self and (tag is None or n.tag == tag)]

    def text(self):
        out = []
        for ch in self.children:
            out.append(ch if isinstance(ch, str) else (" " if ch.tag == "br" else ch.text()))
        return "".join(out)

    def element_children(self):
        return [c for c in self.children if isinstance(c, El)]


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = El("#root")
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        el = El(tag, attrs, self.cur)
        self.cur.children.append(el)
        if tag not in VOID:
            self.cur = el

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(El(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, d):
        self.cur.children.append(d)


def parse(s):
    p = _Parser()
    p.feed(s or "")
    p.close()
    return p.root


def serialize(node):
    if isinstance(node, str):
        return html.escape(node, quote=False)
    if node.tag == "#root":
        return "".join(serialize(c) for c in node.children)
    if node.tag == "#raw":
        return node.attrs["html"]
    attrs = ""
    for k, v in node.attrs.items():
        attrs += " " + k if v is None else ' {}="{}"'.format(k, html.escape(str(v), quote=True))
    if node.tag in VOID:
        return "<{}{}>".format(node.tag, attrs)
    return "<{}{}>{}</{}>".format(node.tag, attrs, "".join(serialize(c) for c in node.children), node.tag)


def raw(s):
    return El("#raw", {"html": s})


def replace_node(old, new_nodes):
    parent = old.parent
    i = parent.children.index(old)
    parent.children[i:i + 1] = new_nodes
    for n in new_nodes:
        if isinstance(n, El):
            n.parent = parent


def norm_ws(s):
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ").replace("﻿", "")).strip()


# ---------------------------------------------------------------------------------------------- URLs
def depth(cur):
    return 0 if cur == "/" else len(cur.strip("/").split("/"))


def rel(cur, target):
    prefix = "../" * depth(cur)
    t = "" if target == "/" else target.strip("/") + "/"
    return (prefix + t) or "./"


def asset(cur, sub):
    return "../" * depth(cur) + "assets/" + sub


def out_file(path):
    return DOCS / "index.html" if path == "/" else DOCS / path.strip("/") / "index.html"


def resolve(cur, href):
    """Map a content href to (url, external_page). Built pages → relative URL; other live pages → absolute live URL
    flagged so the caller adds the external-link marker; documents keep their absolute live URL."""
    h = html.unescape(href or "").strip()
    if not h:
        return h, False
    rest = None
    for base in (LIVE, "http://mcroberts.sd38.bc.ca", "https://www.mcroberts.sd38.bc.ca"):
        if h.startswith(base + "/") or h == base:
            rest = h[len(base):] or "/"
    if rest is None:
        if h.startswith("/") and not h.startswith("//"):
            rest = h
        else:
            return h, False
    path, _, frag = rest.partition("#")
    path_only, _, query = path.partition("?")
    norm = ("/" + path_only.strip("/")) if path_only.strip("/") else "/"
    norm = canon(norm)                       # old aliases and retired pages → the clean URL (no redirect hop)
    if norm in BUILT and not query:
        return rel(cur, norm) + ("#" + frag if frag else ""), False
    is_file = bool(re.search(r"\.[a-z0-9]{2,5}$", norm, re.I)) or norm.startswith(("/files/", "/sites/", "/system/"))
    return LIVE + rest, not is_file


def icon(name, cls="icon"):
    return '<svg class="{}" aria-hidden="true" focusable="false"><use href="#i-{}"/></svg>'.format(cls, name)


EXT = icon("ext", "icon ext-mark")


def a(cur, href, inner, cls="", attrs="", mark=True):
    url, ext = resolve(cur, href)
    c = ' class="{}"'.format(cls) if cls else ""
    arrow = icon("arrow")
    if ext and mark and arrow in inner:      # an arrow link to the live site: the arrow becomes the external mark
        inner = inner.replace(arrow, icon("ext"))
        mark = False
    return '<a{} href="{}"{}>{}{}</a>'.format(c, html.escape(url), attrs, inner, EXT if (ext and mark) else "")


SMALL_COPIES = {}                  # optimised name → its 960 px wide copy (srcset), made with sips in copy_assets


def img_srcset(cur, name):
    """srcset for a content image wider than 1000 px: a 960 px copy beside the optimised original (Drupal: a
    responsive_image style with the same two widths)."""
    mapped = IMAGES["map"].get(name, name)
    w, h = IMAGES["size"].get(mapped, [None, None])
    if not w or w <= 1000 or name in DERIVED or name == CREST:
        return ""
    stem, ext = mapped.rsplit(".", 1)
    small = "{}-960.{}".format(stem, ext)
    SMALL_COPIES[mapped] = small
    return "{} 960w, {} {}w".format(asset(cur, "img/" + small), asset(cur, "img/" + mapped), w)


def img_src(cur, name):
    """Original name (as in assets/content) → URL of the optimised copy, plus its pixel size."""
    if name in DERIVED:
        out_name = DERIVED[name][0]
    else:
        out_name = IMAGES["map"].get(name, name)
    USED_IMAGES.add(name)
    w, h = IMAGES["size"].get(IMAGES["map"].get(name, name), [None, None])
    return asset(cur, "img/" + out_name), w, h


def esc(s):
    return html.escape(s or "", quote=True)


# ---------------------------------------------------------------------------------------------- text and dates
def clean_title(t):
    return norm_ws(html.unescape(t or ""))


KEEP_UPPER = {"S1", "S2", "PT", "PLT", "PAC", "CLC", "TVR", "BC", "GLA", "GNA", "LTF", "UBC", "AM", "PM", "AP",
              "ABCD", "BADC", "COLLAB"}
SMALL = {"of", "and", "the", "to", "for", "in", "at", "on", "a", "an", "or", "by"}


def smart_case(t):
    """ALL-CAPS calendar titles become title case (same words, case only)."""
    letters = [c for c in t if c.isalpha()]
    if not letters or sum(c.isupper() for c in letters) / len(letters) < 0.85:
        return t
    words = t.split(" ")
    out = []
    for i, w in enumerate(words):
        core = re.sub(r"[^A-Za-z0-9]", "", w)
        if core.upper() in KEEP_UPPER or re.search(r"\d", core):
            out.append(w)
        elif i and core.lower() in SMALL:
            out.append(w.lower())
        else:
            out.append("-".join(p[:1].upper() + p[1:].lower() if p else p for p in w.split("-")))
    return " ".join(out)


def d_iso(d):
    return d.isoformat()


def fmt_long(d):
    return "{}, {} {}, {}".format(DAYS_LONG[d.weekday()], MONTHS_LONG[d.month - 1], d.day, d.year)


def fmt_day_long(d):
    return "{}, {} {}".format(DAYS_LONG[d.weekday()], MONTHS_LONG[d.month - 1], d.day)


def fmt_short(d):
    return "{}, {} {}".format(DAYS[d.weekday()], MONTHS[d.month - 1], d.day)


def date_chip(d, tag="time", cls="date-chip"):
    return ('<{t} class="{c}" datetime="{iso}"><span class="m">{m}</span><span class="n">{n}</span>'
            '<span class="d">{w}</span></{t}>').format(t=tag, c=cls, iso=d_iso(d), m=MONTHS[d.month - 1], n=d.day,
                                                     w=DAYS[d.weekday()])


LINE = "\u2028"     # a <br> inside a teaser, kept apart so the card can show the lines as lines


def el_text(el, br=" "):
    return "".join(c if isinstance(c, str) else (br if c.tag == "br" else el_text(c, br)) for c in el.children)


def first_sentence(body, limit=170, br=" "):
    root = parse(body)
    for el in root.iter():
        if el.tag in ("p", "li"):
            t = re.sub(r"[ \t\r\n\xa0\ufeff]+", " ", el_text(el, br)).strip()
            t = re.sub(r" ?\u2028 ?", LINE, t).strip(LINE)
            kids = [c for c in el.children if not (isinstance(c, str) and not c.strip())]
            if len(t) < 50 or (kids and isinstance(kids[0], El) and kids[0].tag == "a"):
                continue
            m = re.match(r"(.+?[.!?])(?=\s+[A-Z(“\"]|\s*$)", t)
            s = m.group(1) if m else t
            if len(s) > limit:
                s = s[:limit].rsplit(" ", 1)[0].rstrip(",;:-–— ") + "…"
            return s
    return ""


def page_title(path):
    p = PAGES.get(path) or {}
    t = clean_title(p.get("title"))
    if not t and p.get("body"):
        root = parse(p["body"])
        links = root.elements("a")
        t = norm_ws(links[0].text()) if links else ""
    return t


# ---------------------------------------------------------------------------------------------- news
NEWS_BY_HREF = {n["href"]: n for n in NEWS}


def article_date(href):
    s = ARTICLE_DATES.get(href) or (NEWS_BY_HREF.get(href) or {}).get("date")
    if s:
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            pass
    return None


def url_month(href):
    m = re.search(r"/(20\d\d)/(\d\d)/", href)
    return (int(m.group(1)), int(m.group(2))) if m else None


def news_sort_key(item):
    """Newest first with reverse=True: by date, then posts sharing a date in the live listing's order."""
    d = article_date(item["href"])
    rank = -NEWS_RANK.get(item["href"], 10 ** 6)
    if d:
        return (d.year, d.month, d.day, rank)
    um = url_month(item["href"]) or (1900, 1)
    return (um[0], um[1], 0, rank)


WEEKLIES = sorted([n for n in NEWS if clean_title(n["title"]).lower().startswith("striker weekly")],
                  key=news_sort_key, reverse=True)


def weekly_range(item):
    return clean_title(item["title"]).split(":", 1)[-1].strip()


# ---------------------------------------------------------------------------------------------- calendar
ROT_RE = re.compile(r"^(?:COLLAB\s+)?(?:ABCD|BADC)$|^PLT Rot \d+$", re.I)
NO_SCHOOL = {"thanksgiving", "remembrance day", "winter break", "christmas", "boxing day", "new year's day",
             "bc family day", "spring break", "good friday", "easter monday", "victoria day", "canada day", "bc day",
             "national day for truth and reconciliation"}


def is_no_school(title):
    return "NO SCHOOL" in title.upper() or title.lower() in NO_SCHOOL


def noschool_tag(title):
    """A day off is never colour alone: a visible "No School" tag (the calendar legend's own words) unless the title
    already says it (PRO-D DAY - NO SCHOOL)."""
    if is_no_school(title) and "no school" not in title.lower():
        return ' <span class="tag-noschool">No School</span>'
    return ""


LABELS = {"today": "Today", "next": "Next", "noschool": "No School"}


EVENTS = []
for _e in EVENTS_RAW:
    _t = clean_title(_e["title"])
    EVENTS.append({"d": date.fromisoformat(_e["start"][:10]), "t": _t})
EVENTS.sort(key=lambda e: (e["d"], e["t"]))
CODES = {}
for _e in EVENTS:
    if ROT_RE.match(_e["t"]):
        CODES.setdefault(_e["d"], _e["t"])
EVENT_PAGES = {}
for _p, _v in PAGES.items():
    if _v["type"] == "event" and _v.get("date"):
        EVENT_PAGES.setdefault((clean_title(_v["title"]).lower(), _v["date"][:10]), _p)


def real_events(start):
    seen, out = set(), []
    for e in EVENTS:
        if e["d"] < start or ROT_RE.match(e["t"]):
            continue
        key = (e["t"].lower(), e["d"])
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def event_href(e):
    return EVENT_PAGES.get((e["t"].lower(), d_iso(e["d"])), "/school-calendar")


SCHOOL_YEAR = int(re.search(r"(20\d\d)", BELL.get("collaborationDaysTitle", "")).group(1)) if re.search(
    r"(20\d\d)", BELL.get("collaborationDaysTitle", "")) else TODAY.year


def school_date(text):
    m = re.match(r"\s*([A-Za-z]+)\.?\s+(\d{1,2})", text)
    if not m:
        return None
    mon = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"].index(m.group(1)[:3].lower()) + 1
    return date(SCHOOL_YEAR if mon >= 8 else SCHOOL_YEAR + 1, mon, int(m.group(2)))


ROTATIONS = []
for _sem in BELL["semesters"]:
    for _r in _sem["rotations"]:
        _name, _, _span = _r.partition(":")
        _a, _, _b = _span.partition(" - ")
        ROTATIONS.append({"name": _name.strip(), "from": school_date(_a), "to": school_date(_b)})
COLLAB_DAYS = [(school_date(x), x) for x in BELL["collaborationDays"]]


def rotation_for(d):
    for r in ROTATIONS:
        if r["from"] and r["to"] and r["from"] <= d <= r["to"]:
            return r["name"]
    code = CODES.get(d, "")
    if code.endswith("ABCD"):
        return "Rotation One"
    if code.endswith("BADC"):
        return "Rotation Two"
    return None


def school_day(start):
    for i in range(60):
        d = start + timedelta(days=i)
        if d in CODES:
            return d
    return None


def minutes(rng):
    vals = []
    for t in rng.split("-"):
        h, _, m = t.partition(":")
        h = int(h)
        if h < 7:
            h += 12
        vals.append(h * 60 + int(m or 0))
    return max(vals[1] - vals[0], 20)


# ---------------------------------------------------------------------------------------------- menu tree (design/ia.json)
PRIMARY = IA["primary"]          # menu main: level 1 = top item (its hub), level 2 = column (group), level 3 = link
UTILITY = IA["utility"]          # menu utility (new core menu): the slim top bar
FOOTER_MENU = IA["footer"]       # menu footer (new core menu): three short columns
HUBS = IA["hubs"]                # hub page → its grouped sections (main-menu subtree / "hub links" menu)
TOPS = {m["href"]: m for m in PRIMARY}


def bare(href):
    return (href or "").split("#")[0]


def is_internal(href):
    return bool(href) and href.startswith("/")


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", norm_ws(t).lower()).strip("-")


FIRST_HOME = {}                  # page → the top item where the menu lists it first
MENU_LABEL = {}                  # href → its first menu label (a hub card reads the menu label of the same link)
for _m in PRIMARY:
    for _g in _m["groups"]:
        for _node in ([_g] if _g.get("href") else []) + _g["children"]:
            MENU_LABEL.setdefault(_node["href"], _node["label"])
            if is_internal(_node["href"]):
                FIRST_HOME.setdefault(bare(_node["href"]), _m)
for _m in PRIMARY:
    MENU_LABEL.setdefault(_m["href"], _m["label"])
    FIRST_HOME[_m["href"]] = _m


def panel_label(top, href):
    """The label a link has inside one top item's panel (None when the panel does not list it)."""
    for g in (top or {}).get("groups", []):
        for node in ([g] if g.get("href") else []) + g["children"]:
            if node["href"] == href:
                return node["label"]
    return None


def parent_path(path):
    parts = path.strip("/").split("/")
    return "/" + "/".join(parts[:-1]) if len(parts) > 1 else "/"


def section_of(path):
    """The top menu item a page belongs to: its URL prefix (each URL sits under its first home in the menu), else
    the item that lists it (or its nearest listed ancestor) first. Calendar events live under School Calendar."""
    if (PAGES.get(path) or {}).get("type") == "event":
        return TOPS.get("/school-calendar")
    for m in PRIMARY:
        if path == m["href"] or path.startswith(m["href"].rstrip("/") + "/"):
            return m
    p = path
    while p and p != "/":
        if p in FIRST_HOME:
            return FIRST_HOME[p]
        p = parent_path(p)
    return None


def url_children(path):
    """Built pages one level below `path` in the URL tree."""
    d = depth(path)
    kids = [p for p in BUILT if p != path and p.startswith(path.rstrip("/") + "/") and depth(p) == d + 1
            and PAGES.get(p, {}).get("type") == "page"]
    return sorted(kids, key=lambda p: page_title(p).lower())


def section_order(sec):
    """The section's own pages in menu order (hub, then each column top to bottom): the prev/next sequence.
    Cross-listed pages are left to the section whose URL they sit under, so prev and next agree both ways."""
    out = []
    for g in sec["groups"]:
        for node in ([g] if g.get("href") else []) + g["children"]:
            h = node["href"]
            if (is_internal(h) and "#" not in h and h in BUILT and h != sec["href"] and h not in out
                    and section_of(h) is sec):
                out.append(h)
    return out


def menu_trail(sec, cur):
    """The menu link that stands for `cur` in this section: the page itself, else its nearest listed ancestor."""
    listed = {bare(c["href"]) for g in sec["groups"] for c in g["children"]} | {
        g["href"] for g in sec["groups"] if g.get("href")}
    p = cur
    while p and p != "/":
        if p in listed:
            return p
        p = parent_path(p)
    return None


def breadcrumbs(path):
    """system_breadcrumb_block (path based); a page whose URL is not under its section hub (Contact Us, School
    Learning Story) gets the hub crumb the menu tree gives it, so the trail always matches the menu."""
    crumbs = [("Home", "/")]
    parts = path.strip("/").split("/")
    for i in range(1, len(parts)):
        p = "/" + "/".join(parts[:i])
        if p in PAGES and page_title(p):
            crumbs.append((page_title(p), p))
    sec = section_of(path)
    if sec and sec["href"] != path and sec["href"] not in [h for _, h in crumbs]:
        crumbs.insert(1, (page_title(sec["href"]) or sec["label"], sec["href"]))
    return crumbs


def bell_col(d, code):
    """Which bell-schedule column a school day follows: Collaboration Days for COLLAB codes, otherwise the weekday;
    a Tuesday or Thursday coded ABCD/BADC (PLT CANCELLED) runs the Monday pattern."""
    c = (code or "").upper()
    if c.startswith("COLLAB"):
        return "Collaboration Days"
    col = COLS.get(d.weekday(), "MON")
    if not c.startswith("PLT") and col in ("TUE", "THU"):
        return "MON"
    return col


# ---------------------------------------------------------------------------------------------- chrome
SPRITE = """<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">
<symbol id="i-phone" viewBox="0 0 24 24"><path d="M6.7 3.6h2.5l1.5 4-1.9 1.3a11.6 11.6 0 0 0 6.3 6.3l1.3-1.9 4 1.5v2.5a2.1 2.1 0 0 1-2.3 2.1A16.4 16.4 0 0 1 4.6 5.9a2.1 2.1 0 0 1 2.1-2.3z"/></symbol>
<symbol id="i-calendar" viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="15.5" rx="2.2"/><path d="M3.5 9.8h17M8 3v4M16 3v4"/><path d="M7.5 13.5h2M11 13.5h2M14.5 13.5h2M7.5 16.8h2M11 16.8h2"/></symbol>
<symbol id="i-cal-plus" viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="15.5" rx="2.2"/><path d="M3.5 9.8h17M8 3v4M16 3v4M12 12.6v5M9.5 15.1h5"/></symbol>
<symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12.5" r="8.5"/><path d="M12 8v4.8l3.2 2M9.5 2.8h5"/></symbol>
<symbol id="i-paper" viewBox="0 0 24 24"><path d="M4 5.2h12.5V18a2 2 0 0 0 2 2H6a2 2 0 0 1-2-2z"/><path d="M16.5 9H20v9a2 2 0 0 1-2 2M7 8.7h6.5M7 12h6.5M7 15.3h4"/></symbol>
<symbol id="i-cap" viewBox="0 0 24 24"><path d="M2.5 9.2 12 4.5l9.5 4.7L12 14z"/><path d="M6.5 11.3v4.6c0 1.4 2.5 2.8 5.5 2.8s5.5-1.4 5.5-2.8v-4.6M21.5 9.2v5.3"/></symbol>
<symbol id="i-wallet" viewBox="0 0 24 24"><path d="M4 7.2A2.2 2.2 0 0 1 6.2 5H17v2.2"/><rect x="4" y="7.2" width="16.5" height="12.3" rx="2.2"/><path d="M20.5 11h-4a2.4 2.4 0 0 0 0 4.8h4"/><circle cx="16.6" cy="13.4" r=".6"/></symbol>
<symbol id="i-apps" viewBox="0 0 24 24"><rect x="4" y="4" width="7" height="7" rx="1.6"/><rect x="13" y="4" width="7" height="7" rx="1.6"/><rect x="4" y="13" width="7" height="7" rx="1.6"/><rect x="13" y="13" width="7" height="7" rx="1.6"/></symbol>
<symbol id="i-shield" viewBox="0 0 24 24"><path d="M12 3.2 19.5 6v5.6c0 4.4-3.1 7.9-7.5 9.2-4.4-1.3-7.5-4.8-7.5-9.2V6z"/><path d="m9 12.2 2.1 2.1L15.2 10"/></symbol>
<symbol id="i-search" viewBox="0 0 24 24"><circle cx="10.8" cy="10.8" r="6.3"/><path d="m15.6 15.6 4.9 4.9"/></symbol>
<symbol id="i-globe" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.8"/><path d="M3.2 12h17.6M12 3.2c2.4 2.4 3.6 5.3 3.6 8.8s-1.2 6.4-3.6 8.8c-2.4-2.4-3.6-5.3-3.6-8.8S9.6 5.6 12 3.2z"/></symbol>
<symbol id="i-access" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="7.4" r="1.15" fill="currentColor" stroke="none"/><path d="M7.4 9.8 12 10.9l4.6-1.1M12 10.9v3.4l-2.2 4M12 14.3l2.2 4"/></symbol>
<symbol id="i-menu" viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h10"/></symbol>
<symbol id="i-close" viewBox="0 0 24 24"><path d="m6 6 12 12M18 6 6 18"/></symbol>
<symbol id="i-chev" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></symbol>
<symbol id="i-arrow" viewBox="0 0 24 24"><path d="M4.5 12h15M13.5 6l6 6-6 6"/></symbol>
<symbol id="i-ext" viewBox="0 0 24 24"><path d="M7 17 17 7M8.5 7H17v8.5"/></symbol>
<symbol id="i-insta" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="4.6"/><circle cx="12" cy="12" r="3.7"/><circle cx="16.9" cy="7.1" r=".7" fill="currentColor"/></symbol>
<symbol id="i-x" viewBox="0 0 24 24"><path d="M5 4.5h3.8L19 19.5h-3.8zM18.5 4.5 13.4 10.4M5.6 19.5l5.2-6"/></symbol>
<symbol id="i-mail" viewBox="0 0 24 24"><rect x="3.5" y="5.5" width="17" height="13" rx="2.2"/><path d="m4.2 7 7.8 6 7.8-6"/></symbol>
<symbol id="i-pin" viewBox="0 0 24 24"><path d="M12 20.8s-6.4-5.9-6.4-10.6a6.4 6.4 0 0 1 12.8 0c0 4.7-6.4 10.6-6.4 10.6z"/><circle cx="12" cy="10.2" r="2.3"/></symbol>
<symbol id="i-alert" viewBox="0 0 24 24"><path d="M12 4 21 19.5H3z"/><path d="M12 10v4.2M12 16.9v.2"/></symbol>
<symbol id="i-check" viewBox="0 0 24 24"><path d="m5.5 12.5 4.2 4.2 8.8-9"/></symbol>
<symbol id="i-people" viewBox="0 0 24 24"><circle cx="9" cy="8.5" r="3.2"/><path d="M3.5 19c.6-3.3 2.8-5.2 5.5-5.2s4.9 1.9 5.5 5.2"/><circle cx="16.8" cy="9.3" r="2.5"/><path d="M15.6 14.1c2.4.1 4.2 1.7 4.9 4.6"/></symbol>
<symbol id="i-family" viewBox="0 0 24 24"><circle cx="8" cy="6.8" r="2.6"/><circle cx="16.4" cy="8.2" r="2.1"/><path d="M3.8 20v-4.6c0-2.4 1.9-4.3 4.2-4.3s4.2 1.9 4.2 4.3V20M12.6 20v-3.4c0-2 1.7-3.6 3.8-3.6s3.8 1.6 3.8 3.6V20"/></symbol>
<symbol id="i-dys" viewBox="0 0 24 24"><path d="M4 18.5 8.7 5.5h.6l4.7 13M5.8 14h6.4"/><path d="M15.2 10.2c.6-.9 1.6-1.4 2.7-1.4 1.6 0 2.6 1 2.6 2.6v7.1M20.5 13.6c-3.4 0-5.6.8-5.6 2.7 0 1.4 1 2.3 2.5 2.3 1.6 0 3.1-1.2 3.1-3"/></symbol>
<symbol id="i-contrast" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><path d="M12 3.5v17a8.5 8.5 0 0 0 0-17z" fill="currentColor"/></symbol>
<symbol id="i-invert" viewBox="0 0 24 24"><rect x="3.5" y="3.5" width="17" height="17" rx="3"/><path d="M3.5 20.5 20.5 3.5V17.5a3 3 0 0 1-3 3z" fill="currentColor"/></symbol>
<symbol id="i-tminus" viewBox="0 0 24 24"><path d="M3 18 7.4 6h.6L12.4 18M4.6 14h6.2M15 12h6"/></symbol>
<symbol id="i-treset" viewBox="0 0 24 24"><path d="M5 18 9.6 6h.6L14.8 18M6.7 14h6.4"/><path d="M19.5 7.5a3.6 3.6 0 1 1-1 4.3M19.6 4.8v2.9h-2.9"/></symbol>
<symbol id="i-tplus" viewBox="0 0 24 24"><path d="M3 18 7.4 6h.6L12.4 18M4.6 14h6.2M15 12h6M18 9v6"/></symbol>
<symbol id="i-list" viewBox="0 0 24 24"><path d="M9 6.5h11M9 12h11M9 17.5h11"/><circle cx="4.6" cy="6.5" r=".9"/><circle cx="4.6" cy="12" r=".9"/><circle cx="4.6" cy="17.5" r=".9"/></symbol>
<symbol id="i-grid" viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="15.5" rx="2.2"/><path d="M3.5 9.8h17M3.5 15.2h17M9.2 9.8v10.7M14.8 9.8v10.7M8 3v4M16 3v4"/></symbol>
<symbol id="i-help" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.6"/><path d="M9.6 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1.1.9-1.1 1.6v.6"/><circle cx="12" cy="16.9" r=".55"/></symbol>
<symbol id="i-download" viewBox="0 0 24 24"><path d="M12 4v11M7.5 10.5 12 15l4.5-4.5M5 19.5h14"/></symbol>
</svg>"""


def translate_block(uid, variant):
    """GTranslate block (gtranslate_block): .gtranslate_wrapper kept; languages from the block config, native names."""
    opts = "".join('<option value="en|{0}" lang="{3}"{1}>{2}</option>'.format(code, " selected" if code == "en" else "",
                                                                           LANG_NAMES.get(code, code), LANG_TAGS.get(code, code))
                   for code in SITE["translateLanguages"])
    label_txt = '<span class="label-gt">Translate</span>' if variant != "utility" else ""
    return ('<div class="translate gtranslate_wrapper">'
            '<span class="tool-btn" aria-hidden="true">{globe}{label}<span class="current" translate="no">English</span></span>'
            '<label class="vh" for="gt-{uid}">Translate</label>'
            '<select id="gt-{uid}" class="gt_selector notranslate" translate="no" data-gt-select>{opts}</select>'
            '{chev}</div>').format(globe=icon("globe"), label=label_txt, uid=uid, opts=opts,
                                   chev=icon("chev", "chev"))


def search_form(cur, uid):
    url = rel(cur, SEARCH)          # search.view_node_search: /search/node?keys= → our /search?keys=
    return ('<form class="search-form" role="search" action="{}" method="get">'
            '<label class="vh" for="search-{uid}">Search</label>'
            '<input id="search-{uid}" type="search" name="keys" placeholder="Search" autocomplete="off">'
            '<button type="submit">{}<span class="vh">Search</span></button></form>').format(esc(url), icon("search"), uid=uid)


def a11y_button(cls="tool-btn", label=True):
    txt = '<span class="label-a11y">Accessibility Settings</span>' if label else '<span class="vh">Accessibility Settings</span>'
    return '<button class="{}" type="button" data-open-dialog="a11y-dialog" commandfor="a11y-dialog" command="show-modal" aria-haspopup="dialog">{}{}</button>'.format(
        cls, icon("access"), txt)


def quick_links():
    """district_quick_links (image links whose names live in the title attribute) + the Office 365 home page button."""
    out = [(q["title"], q["href"]) for q in SITE["quickLinks"] if q.get("title")]
    out.append(("Office 365", "https://portal.office.com"))
    return out


UTIL_ABSENT, UTIL_NUMBER = UTILITY[0], UTILITY[1]     # "Student Absent?" + "604-668-6600 (Ext. 1)"


ATTENDANCE = "/parents/student-attendance"


def here_attr(cur, href):
    """aria-current="page" on a link to the page it sits on (Student Absent? on Student Attendance itself)."""
    return ' aria-current="page"' if (is_internal(href) and "#" not in href and canon(bare(href)) == cur) else ""


def absent_pill(cur, cls="absent-pill"):
    """menu utility, first two links as one pill (the live sidebar_note's own words): "Student Absent?" opens Student
    Attendance (the number, what to say, the 8:30 a.m. rule); the number beside it stays visible and dials."""
    return ('<span class="{c}"><span class="dot" aria-hidden="true">{pi}</span>{lab} {num}</span>').format(
        c=cls, pi=icon("phone"), lab=a(cur, UTIL_ABSENT["href"], esc(UTIL_ABSENT["label"]), "txt", here_attr(cur, UTIL_ABSENT["href"])),
        num='<a class="num" href="{}">{}</a>'.format(esc(UTIL_NUMBER["href"]), esc(UTIL_NUMBER["label"])))


def lockup(cur, cls="lockup", post=True, eager=True):
    src, w, h = crest_src(cur, "200")
    return ('<a class="{cls}" href="{home}"><img src="{src}" alt="" width="{w}" height="{h}"{fp}>'
            '<span class="lockup-text"><span class="lockup-pre">École Secondaire</span>'
            '<span class="lockup-name">Hugh McRoberts</span>{post}</span>'
            '<span class="vh">Home</span></a>').format(
        cls=cls, home=rel(cur, "/"), src=src, w=w, h=h, fp=' fetchpriority="high"' if eager else "",
        post='<span class="lockup-post">Secondary School</span>' if post else "")


def menu_icon(href):
    return icon("ext", "icon ext-mark") if re.match(r"^https?:", href or "") else icon("arrow")


# An in-site page that a menu item reaches only through its external target (the menu sends visitors straight to
# the catalogue): on that page the item is its active trail.
STANDS_FOR = {"/library/library-catalogue": "https://search.follettsoftware.com/metasearch/ui/21989"}


def menu_link(cur, node, cls="", trail=None, arrow=True, glue=False):
    """One menu link: aria-current on the page itself, is-active-trail on the link that stands for it. glue: the
    arrow stays on the line of the label's last word (an inline link that wraps never leaves it alone on a line)."""
    href = node["href"]
    here = is_internal(href) and "#" not in href and canon(href) == cur
    stands = STANDS_FOR.get(cur) == href
    c = " ".join(x for x in (cls, "is-active-trail" if (not here and ((trail and bare(href) == trail and "#" not in href) or stands)) else "") if x)
    external = re.match(r"^https?:", href)
    mark = menu_icon(href) if arrow else (icon("ext", "icon ext-mark") if external else "")
    label = node["label"].strip()
    if glue and mark and " " in label:
        head, last = label.rsplit(" ", 1)
        inner = '<span>{} <span class="nowrap">{}{}</span></span>'.format(esc(head), esc(last), mark)
    else:
        inner = "<span>{}</span>".format(esc(node["label"])) + mark
    return a(cur, href, inner, c, ' aria-current="page"' if here else "")


def group_title(cur, g, tag, cls, gid=None, glue=False):
    if not g.get("label"):
        return ""
    idattr = ' id="{}"'.format(gid) if gid else ""
    if g.get("href"):
        return '<{t} class="{c}"{i}>{l}</{t}>'.format(t=tag, c=cls, i=idattr, l=menu_link(cur, {"label": g["label"], "href": g["href"]}, glue=glue))
    return '<{t} class="{c}"{i}>{l}</{t}>'.format(t=tag, c=cls, i=idattr, l=esc(g["label"]))


# Pages a short panel shows as image tiles (as the hub shows them). A tile page leaves the panel's link columns, so no
# panel lists a page twice; a tile for a page the green card already lists is a mouse-only copy (see mega_tiles).
MEGA_TILES = {"/extra-curricular": ["/extra-curricular/strikers-athletics", "/extra-curricular/club-directory"],
              "/library": ["/library/read-listen", "/library/make-play"]}
LOGOS = {STRIKERS_LOGO}            # logo art: shown whole on forest (object-fit: contain), never cropped


def tile_image(pth):
    """A tile's image: the page's own first image, else the one the section page links it with (TILE_IMAGE)."""
    return first_image(pth) or TILE_IMAGE.get(pth)


def tiled(paths):
    return [p for p in paths if p in BUILT and tile_image(p)]


def mega_tiles(cur, paths, quiet=()):
    """Two of the section's own pages as image tiles. A tile whose page the green card already links (quiet) stays
    a mouse target only: out of the tab order and hidden from screen readers, so each page is one tab stop and one
    announcement. When every tile is quiet the whole list is hidden."""
    lis = []
    paths = tiled(paths)
    all_quiet = bool(paths) and all(p in quiet for p in paths)
    for pth in paths:
        name = tile_image(pth)
        src, w, h = img_src(cur, name)
        cls = " is-logo" if name in LOGOS else (" is-icon" if name.endswith(".png") and (w or 0) <= 600 else "")
        q = pth in quiet
        lis.append('<li{lh}><a class="mega-tile{c}" href="{u}"{tq}><span class="mega-tile-img"><img src="{s}" alt="" width="{w}" height="{h}" '
                   'loading="lazy" decoding="async"></span><span class="mega-tile-t">{t}</span>{go}</a></li>'.format(
                       lh=' aria-hidden="true"' if (q and not all_quiet) else "", c=cls, u=rel(cur, pth),
                       tq=' tabindex="-1"' if q else "", s=src, w=w, h=h, t=esc(MENU_LABEL.get(pth) or page_title(pth)),
                       go=icon("arrow")))
    return '<ul class="mega-tiles"{}>{}</ul>'.format(' aria-hidden="true"' if all_quiet else "", "".join(lis)) if lis else ""


def mega_events(cur):
    """School Calendar panel: the next three events (view upcoming_events, block_1). Built for today and refreshed
    from assets/search.json when the panel first opens on a later day (js/nav.js)."""
    items = []
    for e in real_events(TODAY)[:3]:
        url, ext = resolve(cur, event_href(e))
        items.append('<li><a href="{u}"{ns}>{chip}<span class="t">{t}{tag}</span></a></li>'.format(
            u=esc(url), ns=' class="is-noschool"' if is_no_school(e["t"]) else "", chip=date_chip(e["d"]),
            t=esc(smart_case(e["t"])), tag=' <span class="tag-noschool">No School</span>' if is_no_school(e["t"]) and "school" not in e["t"].lower() else ""))
    return ('<div class="mega-feature mega-feature--events" data-mega-events data-built="{b}" data-index="{i}" data-root="{r}" data-noschool="No School">'
            '<p class="mega-card-title">Upcoming Events</p><ol class="mega-events">{li}</ol></div>').format(
        b=d_iso(TODAY), i=asset(cur, "search.json"), r="../" * depth(cur), li="".join(items))


def mega_feature(cur, m, quiet=()):
    """A short panel gets live content in its free space: News the latest Striker Weekly, About Us the address block,
    School Calendar the next events, Extra-Curricular and Library two of their pages as image tiles."""
    if m["href"] == "/school-calendar":
        return mega_events(cur)
    if m["href"] in MEGA_TILES:
        return mega_tiles(cur, MEGA_TILES[m["href"]], quiet)
    if m["href"] == "/news" and WEEKLIES:
        # the whole card is the link (the live title is "Striker Weekly: Oct 5 to 9"), so it never reads as a bare date
        w = WEEKLIES[0]
        return a(cur, w["href"], '<span class="mega-card-title">Striker Weekly</span><span class="mega-feature-sub">Week at a Glance'
                 ' for Parents</span><span class="big-num">{}</span>{}'.format(esc(weekly_range(w)), icon("arrow", "icon mega-feature-go")),
                 "mega-feature mega-feature--link")
    if m["href"] == "/about-us":
        return ('<div class="mega-feature"><p class="mega-card-title" id="mega-contact-t">Contact Us</p><p>{}<br>{}</p>'
                '<a class="big-num" href="{}" aria-describedby="mega-contact-t">{}</a><a class="feature-mail" href="mailto:{}">{}</a></div>').format(
            esc(ADDR1), ADDR2_HTML, TEL, PHONE_DOTS, EMAIL, EMAIL)
    return ""


def mega_panel(cur, m, mid):
    """One mega panel: the hub title, the most-requested column (groups[0], the links marked featured), then one
    column per group with the group's own live heading. Group titles are not headings (they come before the h1)."""
    sec = section_of(cur)
    trail = menu_trail(m, cur) if sec is m else None
    feat, rest = m["groups"][0], m["groups"][1:]
    feat_links = "".join("<li>{}</li>".format(menu_link(cur, c, "", trail)) for c in feat["children"])
    if len(feat["children"]) == 1:
        # a lone most-requested link gets its card line too (as on the hub), so the green card has some weight
        desc = card_desc(feat["children"][0])
        if desc:
            feat_links = feat_links[:-5] + '<p class="mega-featured-desc">{}</p></li>'.format(
                esc(desc.replace(LINE, " ")))
    cols = []
    tiles = set(tiled(MEGA_TILES.get(m["href"], [])))
    page_of = lambda c: canon(bare(c["href"])) if (is_internal(c["href"]) and "#" not in c["href"]) else None
    for i, g in enumerate(rest, 1):
        gid = "{}-g{}".format(mid, i)
        kids = [c for c in g["children"] if page_of(c) not in tiles]     # a tile page is not listed again
        if not kids:
            continue
        title = group_title(cur, g, "p", "mega-col-title", gid)
        links = "".join("<li>{}</li>".format(menu_link(cur, c, "", trail)) for c in kids)
        cols.append('<div class="mega-col{u}">{t}<ul class="mega-links"{lb}>{l}</ul></div>'.format(
            u="" if g.get("label") else " is-plain", t=title, l=links,
            lb=' aria-labelledby="{}"'.format(gid) if g.get("label") else ""))
    feature = mega_feature(cur, m, {page_of(c) for c in feat["children"]} & tiles)
    if feature:
        cols.append('<div class="mega-col mega-col--feature">{}</div>'.format(feature))
    n_cols = len(cols) - (1 if feature else 0) + (2 if feature else 0)
    here = canon(m["href"]) == cur
    head = a(cur, m["href"], "<span>{}</span>{}".format(esc(m["label"]), icon("arrow")), "mega-title",
             ' aria-current="page"' if here else "")
    return ('<div class="mega" id="{mid}" hidden><div class="wrap mega-grid" style="--cols:{n}">'
            '<div class="mega-lead">{head}<ul class="mega-featured">{feat}</ul></div>'
            '{cols}</div></div>').format(mid=mid, n=max(n_cols, 1), head=head,
                                          feat=feat_links, cols="".join(cols))


def primary_nav(cur):
    sec = section_of(cur)
    lis = []
    for m in PRIMARY:
        mid = "mega-" + slug(m["label"])
        here = canon(m["href"]) == cur
        top_cls = "menu-top" + (" is-active-trail" if (sec is m and not here) else "")
        lis.append('<li class="has-mega">{link}<button type="button" class="menu-toggle" aria-expanded="false" '
                   'aria-controls="{mid}">{chev}<span class="vh">{t}</span></button>{panel}</li>'.format(
                       link=a(cur, m["href"], esc(m["label"]), top_cls, ' aria-current="page"' if here else ""),
                       mid=mid, chev=icon("chev", "chev"), t=esc(m["label"]), panel=mega_panel(cur, m, mid)))
    crest, w, h = crest_src(cur, "200")
    return ('<!-- region primary_menu → block mainnavigation (system_menu_block:main, design/ia.json "primary": 7 items;'
            ' level 2 = columns, the first one the most-requested links). W3C APG disclosure navigation with top-level'
            ' links: each label links to its hub, the button beside it opens the panel (menu--main.html.twig) -->\n'
            '<nav class="primary region region-primary-menu" id="block-mainnavigation" aria-label="Main navigation"><div class="wrap">'
            '<a class="mini-crest" href="{home}" tabindex="-1" aria-hidden="true"><img src="{crest}" alt="" width="{w}" height="{h}"></a>'
            '<ul class="menu-root" data-disclosure-nav>{lis}</ul>{pill}</div></nav>').format(
        home=rel(cur, "/"), crest=crest, w=w, h=h, lis="".join(lis), pill=absent_pill(cur, "sticky-absent"))


def utility_links(cur, cls_ext="icon icon-xs"):
    """menu utility after the pill: the three sign-ins (straight to the services) and Contact Us."""
    out = []
    for n in UTILITY[2:]:
        ext = re.match(r"^https?:", n["href"])
        out.append('<li>{}</li>'.format(a(cur, n["href"], esc(n["label"]) + (icon("ext", cls_ext) if ext else ""))))
    return "".join(out)


def utility_strip(cur):
    src, w, h = img_src(cur, DISTRICT_LOGO)
    return ('<!-- District strip (hardcoded in page.html.twig) + menu utility (system_menu_block:utility, design/ia.json'
            ' "utility"): Student Absent? and its number as one pill, the three sign-ins, Contact Us -->\n'
            '<nav class="utility on-dark"><div class="wrap">'
            '<a class="district-link" href="{dh}"><img src="{src}" alt="{dn}" width="{w}" height="{h}"></a>'
            '<ul class="signin utility-menu"><li class="utility-absent">{pill}</li>{links}</ul></div></nav>').format(
        dh=esc(SITE["district"]["href"]), src=src, dn=esc(SITE["district"]["name"]), w=w, h=h,
        links=utility_links(cur),
        pill=absent_pill(cur))


def header(cur):
    return ('<header class="site-header" id="site-header" data-sticky-header>'
            '<span class="sticky-sentinel" aria-hidden="true"></span>\n'
            '<!-- region top_header (view site_header_content_block: crest, name) + header_form (Search; Accessibility Settings sits in the footer, Translate is not placed) -->\n'
            '<div class="masthead"><div class="wrap"><div class="region region-top-header">{lockup}</div>'
            '<div class="mast-tools region region-header-form">{search}</div>'
            '<div class="mobile-actions">'
            '<button class="icon-btn" type="button" aria-expanded="false" aria-controls="mobile-search" data-toggle-search>{si}<span class="vh">Search</span></button>'
            '{tabpill}'
            '<button class="menu-btn" type="button" data-open-dialog="menu-drawer" commandfor="menu-drawer" command="show-modal" aria-haspopup="dialog" aria-expanded="false" aria-controls="menu-drawer">{mi}<span class="txt">Menu</span></button>'
            '</div></div></div>'
            '<div class="mobile-search" id="mobile-search" hidden><div class="wrap">{msearch}</div></div>\n'
            '{nav}</header>').format(
        lockup=lockup(cur), search=search_form(cur, "desktop"),
        si=icon("search"), mi=icon("menu"), tabpill=absent_pill(cur, "absent-pill tablet-absent"),
        msearch=search_form(cur, "mobile"), nav=primary_nav(cur))


ALERT_TITLE = "Snow and Extreme Weather Protocols"
ALERT_TEXT = "Any district-wide closure will be decided by 6:30 a.m. at the latest"
# the alert's own key (Drupal: the alert node's id and changed time): a new or edited alert shows again after Close
ALERT_KEY = hashlib.sha1((ALERT_TITLE + "\n" + ALERT_TEXT).encode()).hexdigest()[:10]


def alert_band(cur):
    url, _ = resolve(cur, "/school-calendar/snow-and-extreme-weather-protocols")
    return ('<!-- region featured_top → view news_alerts (block_1). Rendered only when the view has rows; row classes'
            ' .news-alert.standard-alert / .urgent-alert from the view config. Demo row: the real Snow protocol copy. -->\n'
            '<div class="featured-top" data-alert="{key}"><div class="region region-featured-top"><section class="news-alert standard-alert" aria-labelledby="alert-title">'
            '<div class="wrap"><span class="alert-icon" aria-hidden="true">{ai}</span><div class="alert-body">'
            '<p class="alert-title" id="alert-title">{t}</p>'
            '<p>{x}</p>'
            '<a class="more-link" href="{url}"><span id="alert-more">Read more</span><span class="vh">: {t}</span></a>'
            '</div><button class="alert-close" type="button" data-alert-close>{ci}<span class="label">Close</span></button>'
            '</div></section></div></div>').format(ai=icon("alert"), url=esc(url), ci=icon("close", "icon icon-xs"), key=ALERT_KEY,
                                                    t=esc(ALERT_TITLE), x=esc(ALERT_TEXT))


def footer(cur):
    """Footer: menu footer (design/ia.json "footer": Get in Touch, Helpful Links, Important information for parents)
    with the address_block folded into Get in Touch, then Social Media, the district logo and copyright."""
    crest, w, h = img_src(cur, CREST)
    dlogo, dw, dh = img_src(cur, DISTRICT_LOGO)
    social_icons = {"instagram": ("insta", "Instagram"), "twitter": ("x", "Twitter"), "email": ("mail", "Email")}
    social = "".join('<li><a href="{}"><span class="ring">{}</span>{}</a></li>'.format(
        esc(s["href"]), icon(social_icons[s["kind"]][0]), social_icons[s["kind"]][1])
        for s in sorted(SITE["social"], key=lambda s: ["instagram", "twitter", "email"].index(s["kind"])))
    regions = ["region-footer-fourth", "region-footer-first", "region-footer-third"]
    cols = []
    for i, col in enumerate(FOOTER_MENU):
        fid = "foot-" + slug(col["label"])
        items = []
        kids = col["children"]
        j = 0
        while j < len(kids):
            n = kids[j]
            if n["href"] == UTIL_ABSENT["href"] and j + 1 < len(kids) and kids[j + 1]["href"].startswith("tel:"):
                items.append('<li class="foot-absent">{}</li>'.format(absent_pill(cur, "absent-pill")))
                j += 2
                continue
            if n["href"].startswith("mailto:"):
                items.append('<li>{}<a href="{}">{}</a></li>'.format(icon("mail"), esc(n["href"]), esc(n["label"])))
            elif "maps." in n["href"]:
                items.append('<li>{}<address><a href="{}">{}</a><br>{}</address></li>'.format(
                    icon("pin"), esc(SITE["mapHref"]), esc(n["label"]), ADDR2_HTML))
            else:
                ext = re.match(r"^https?:", n["href"])
                items.append("<li>{}</li>".format(a(cur, n["href"], esc(n["label"]) + (icon("ext", "icon icon-xs") if ext else ""))))
            j += 1
        if i == 0:      # address_block: the school's main line under the Early Warning number
            items.append('<li>{}<span><span class="lbl">Telephone:</span> <a href="{}">{}</a></span></li>'.format(
                icon("phone"), TEL, PHONE_DOTS))
        cols.append('<nav class="region {r}" aria-labelledby="{fid}"><h2 id="{fid}">{t}</h2><ul class="foot-list{x}">{li}</ul></nav>'.format(
            r=regions[i] if i < len(regions) else "", fid=fid, t=esc(col["label"]), li="".join(items),
            x=" contact-lines" if i == 0 else ""))
    # one contentinfo landmark holds the sign-off, the footer menus and (on phones) the bottom action bar; "Log in"
    # (account menu) stays off the public pages, as design/ia.md says
    return ('<footer class="page-footer">\n<!-- Sign-off: top_header data repeated -->\n'
            '<div class="signoff"><div class="wrap"><img src="{crest}" alt="" width="{w}" height="{h}" loading="lazy" decoding="async">'
            '<p class="name">{name}</p><p class="motto">Learning Together… Achieving Our Dreams</p></div></div>\n'
            '<!-- footer: menu footer (system_menu_block:footer, 3 columns) + address_block, block social media,'
            ' hardcoded district logo + copyright -->\n'
            '<div class="site-footer on-dark"><div class="wrap foot-grid">{cols}'
            '<div class="region region-footer-second"><h2>Social Media</h2><ul class="social">{social}</ul></div></div>'
            '<div class="foot-bottom"><div class="wrap"><div class="foot-district">'
            '<a href="{dh}"><img src="{dlogo}" alt="{dn}" width="{dw}" height="{dhh}" loading="lazy" decoding="async"></a>'
            '<span><span>Copyright © {year}</span> <span>{dn}</span></span></div>'
            '<div class="links region region-footer-fifth">{a11y}</div></div></div></div>\n{bar}\n</footer>').format(
        crest=crest, w=w, h=h, name=esc(NAME), cols="".join(cols), social=social, dh=esc(SITE["district"]["href"]),
        dlogo=dlogo, dn=esc(SITE["district"]["name"]), dw=dw, dhh=dh, year=TODAY.year,
        a11y=a11y_button("", label=True).replace(' class=""', ""), bar=action_bar(cur))


def action_bar(cur):
    """Phone bottom bar (design/ia.json utility, phone rule): Student Absent? and its number lead, then
    Search and Menu. The number keeps a 44 px target, so an absence is one tap from every page."""
    return ('<!-- Phone bottom action bar: menu utility\'s Student Absent? pill, then Search and Menu -->\n'
            '<div class="action-bar{dup}">'
            '<span class="bar-absent" role="group" aria-labelledby="bar-absent">{lab}<a class="bar-num" href="{tel}">{pi}<span>{num}</span></a></span>'
            '<button class="bar-btn" type="button" aria-expanded="false" aria-controls="mobile-search" data-toggle-search>{si}<span>Search</span></button>'
            '<button class="bar-btn" type="button" data-open-dialog="menu-drawer" commandfor="menu-drawer" command="show-modal" aria-haspopup="dialog" aria-expanded="false" aria-controls="menu-drawer">{mi}<span>Menu</span></button>'
            '</div>').format(
        lab=a(cur, UTIL_ABSENT["href"], "<span>{}</span>{}".format(esc(UTIL_ABSENT["label"]), icon("arrow")), "bar-label",
              ' id="bar-absent"' + here_attr(cur, UTIL_ABSENT["href"])),
        tel=esc(UTIL_NUMBER["href"]), pi=icon("phone"), num=esc(UTIL_NUMBER["label"]),
        si=icon("search"), mi=icon("menu"),
        # the front page's Today card and Student Attendance's call-out carry the call button on the first screen, so
        # the bar is built folded there (js/nav.js absentDup unfolds it once that button scrolls away)
        dup=" has-dup" if cur in ("/", ATTENDANCE) else "")


def drawer(cur):
    """Phone menu: the same main-menu tree as an accordion (hub link, most-requested links, then each column)."""
    sec = section_of(cur)
    items = []
    for m in PRIMARY:
        trail = menu_trail(m, cur) if sec is m else None
        feat, rest = m["groups"][0], m["groups"][1:]
        body = '<ul class="drawer-featured">{}</ul>'.format(
            "".join("<li>{}</li>".format(menu_link(cur, c, "", trail, arrow=False)) for c in feat["children"]))
        for g in rest:
            body += '<div class="drawer-group">{}<ul>{}</ul></div>'.format(
                group_title(cur, g, "p", "drawer-group-title"),
                "".join("<li>{}</li>".format(menu_link(cur, c, "", trail, arrow=False)) for c in g["children"]))
        here = canon(m["href"]) == cur
        # one section open at a time (exclusive accordion: details name=…, no script)
        items.append('<li><details name="drawer-nav"{o}><summary>{t}{chev}</summary><div class="drawer-panel">{hub}{body}</div></details></li>'.format(
            o=" open" if sec is m else "", t=esc(m["label"]), chev=icon("chev", "chev"), body=body,
            hub=a(cur, m["href"], "<span>{}</span>{}".format(esc(m["label"]), icon("arrow")), "drawer-section-link",
                  ' aria-current="page"' if here else "")))
    return ('<!-- Phone menu: native modal dialog (focus trap + Esc for free); the same menu main, then menu utility -->\n'
            '<dialog class="drawer" id="menu-drawer" aria-label="Menu"><div class="drawer-head">{lockup}'
            '<button class="close-btn" type="button" data-close-dialog commandfor="menu-drawer" command="close" autofocus>{ci}Close</button></div>'
            '<div class="drawer-body">{search}'
            '<nav aria-label="Main navigation"><ul class="drawer-nav">{items}</ul></nav>'
            '<ul class="drawer-signin"><li class="drawer-absent">{pill}</li>{signin}</ul>'
            '<button class="close-btn drawer-close-end" type="button" data-close-dialog commandfor="menu-drawer" command="close">{ci}Close</button>'
            '</div></dialog>').format(
        lockup=lockup(cur, post=False, eager=False), ci=icon("close"), search=search_form(cur, "drawer"),
        items="".join(items),
        pill=absent_pill(cur), signin=utility_links(cur, "icon"))


def a11y_dialog(cur):
    controls = [("dyslexic", "a11y-dyslexic-control", "dys", "Dyslexic", True),
                ("contrast", "a11y-contrast-control", "contrast", "Contrast", True),
                ("invert", "a11y-invert-control", "invert", "Invert", True),
                ("text-decrease", "a11y-textsize-decrease", "tminus", "Text decrease", False),
                ("text-reset", "a11y-textsize-reset", "treset", "Text reset", False),
                ("text-increase", "a11y-textsize-increase", "tplus", "Text increase", False)]
    btns = "".join('<button type="button" class="a11y-control {c}" data-a11y-action="{a}"{p}>{i}{t}</button>'.format(
        c=c, a=act, p=' aria-pressed="false"' if toggle else "", i=icon(ic), t=t) for act, c, ic, t, toggle in controls)
    return ('<!-- region accessibility_dropdown (a11y block) inside a native dialog; module classes and data-a11y-action kept -->\n'
            '<dialog class="a11y-dialog" id="a11y-dialog" aria-labelledby="a11y-title"><div class="a11y-inner">'
            '<h2 id="a11y-title">{ai}Accessibility Settings</h2><div class="region region-accessibility-dropdown" id="block-a11y"><div class="a11y-grid">{btns}</div></div>'
            '<p class="a11y-note"><a class="link" href="https://sd38.bc.ca/accessibility">Learn more about how the Richmond School District supports accessibility.</a></p>'
            '<div class="a11y-foot"><button class="close-btn" type="button" data-close-dialog commandfor="a11y-dialog" command="close">{ci}Close</button></div>'
            '</div></dialog>').format(ai=icon("access"), btns=btns, ci=icon("close"))


HEAD_SCRIPT = ("document.documentElement.classList.add('js');"   # JS-only controls (.needs-js) paint at once: no layout shift
               "(function(){try{var s=JSON.parse(localStorage.getItem('mcr-a11y')||'{}')||{},r=document.documentElement;"
               "if(s.contrast)r.classList.add('a11y-contrast');if(s.invert)r.classList.add('a11y-invert');"
               "if(s.size)r.style.fontSize=(100+s.size*10)+'%';"
               "if(s.dyslexic)r.classList.add('a11y-opendyslexic')}catch(e){}"
               # an alert closed earlier in this session is hidden before the first paint (no jump; js/nav.js alertBand)
               "try{if(sessionStorage.getItem('mcr-alert-" + ALERT_KEY + "')==='closed')document.documentElement.classList.add('alert-closed')}catch(e){}})();")


def shell(cur, title, main, body_class, description="", extra_js=(), preload=None, base_script=False, extra_css=()):
    css = "".join('<link rel="stylesheet" href="{}">'.format(asset(cur, "css/" + f)) for f in list(CSS_FILES) + list(extra_css))
    css += '<link rel="stylesheet" href="{}" media="print">'.format(asset(cur, "css/" + PRINT_CSS))
    js = "".join('<script src="{}" defer></script>'.format(asset(cur, "js/" + f)) for f in list(JS_FILES) + list(extra_js))
    full_title = NAME if not title else "{} | {}".format(title, NAME)
    pre = '<link rel="preload" as="image" href="{}" fetchpriority="high">'.format(preload) if preload else ""
    icon_href, _, _ = crest_src(cur, "32")
    touch_href, _, _ = crest_src(cur, "180")
    # 404.html answers any missing URL at any depth, so its relative URLs need a <base>: SITE_BASE when the build
    # knows the sub-path, else the first path segment on a *.github.io project site. A <base> would send in-page
    # links (#main-content, the skip link) to the site root, so they are pointed back at this document.
    site_base = os.environ.get("SITE_BASE", "").strip()
    base = ('<script>(function(){var p=location.pathname.split("/"),b=' + (json.dumps("/" + site_base.strip("/") + "/" if site_base.strip("/") else "/") if site_base else
            '"/";if(/\\.github\\.io$/.test(location.hostname)&&p.length>2)b="/"+p[1]+"/"') + ';'
            'document.write(\'<base href="\'+b+\'">\');'
            'document.addEventListener("DOMContentLoaded",function(){document.querySelectorAll(\'a[href^="#"]\').forEach(function(a){'
            'a.setAttribute("href",location.pathname+location.search+a.getAttribute("href"))})})})();</script>') if base_script else ""
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n{base}'
            '<meta name="robots" content="noindex,nofollow">\n'
            '<title>{title}</title>\n<meta name="description" content="{desc}">\n<meta name="theme-color" content="#10291a">\n'
            '<link rel="icon" href="{icon}" type="image/png"><link rel="apple-touch-icon" href="{touch}">\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link rel="stylesheet" href="{fonts}">\n{pre}{css}\n<script>{hs}</script>\n{js}\n</head>\n'
            '<body class="{bc}">\n<!-- Icon sprite: our own inline SVG (replaces Font Awesome and the module PNG icons) -->\n{sprite}\n'
            '<a class="skip-link" href="#main-content">Skip to main content</a>\n'
            '<div class="concept-banner" role="note">Design concept for discussion — not the official school website. '
            'The official site is <a href="{live}">mcroberts.sd38.bc.ca</a>. '
            '<a class="concept-about" href="{about}">About this concept</a></div>\n'
            '<div class="page" id="page-wrapper">\n{utility}\n{header}\n{alert}\n<!-- MAIN:START -->\n'
            '<main id="main-content" class="region region-content" tabindex="-1">\n{main}\n</main>\n<!-- MAIN:END -->\n{footer}\n</div>\n'
            '{drawer}\n{a11y}\n</body>\n</html>\n').format(
        base=base, title=esc(full_title), desc=esc(description or SITE["motto"]), icon=icon_href, touch=touch_href, fonts=esc(FONTS),
        pre=pre, css=css, hs=HEAD_SCRIPT, js=js, bc=esc(body_class), sprite=SPRITE, live=LIVE, about=rel(cur, PROPOSAL),
        utility=utility_strip(cur),
        header=header(cur), alert=alert_band(cur), main=main, footer=footer(cur),
        drawer=drawer(cur), a11y=a11y_dialog(cur))


# ---------------------------------------------------------------------------------------------- body transforms
PHONE_RE = re.compile(r"604[.\-\s]668[.\-\s]6600(?:\s*\(\s*(?:Press|Ext\.?)\s*1\s*\)|\s*,?\s*Ext\.?\s*1\b)?")
FILE_EXTS = {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx"}


def has_ancestor(el, tag):
    n = el.parent
    while n is not None:
        if isinstance(n, El) and n.tag == tag:
            return True
        n = n.parent
    return False


def autolink_phones(root):
    for el in list(root.iter()):
        if el.tag in ("a", "script", "style") or has_ancestor(el, "a"):
            continue
        new_children, changed = [], False
        for ch in el.children:
            if isinstance(ch, str) and PHONE_RE.search(ch):
                pos = 0
                for m in PHONE_RE.finditer(ch):
                    new_children.append(ch[pos:m.start()])
                    txt = m.group(0)
                    tel = TEL_EXT if re.search(r"(Press|Ext)", txt) else TEL
                    link = El("a", {"href": tel}, el)
                    link.children.append(txt)
                    new_children.append(link)
                    pos = m.end()
                new_children.append(ch[pos:])
                changed = True
            else:
                new_children.append(ch)
        if changed:
            el.children = [c for c in new_children if c != ""]


BULLET_RE = re.compile(r"^[\s\xa0]*[\x9f\uf0b7\uf0a7\u2022\u25aa\u25cf\u00b7\u2023\u2043][\s\xa0]*")


def strip_bullet(el):
    for i, ch in enumerate(el.children):
        if isinstance(ch, str):
            if not ch.strip("\xa0 \n\t"):
                continue
            el.children[i] = BULLET_RE.sub("", ch, count=1)
            return
        if isinstance(ch, El):
            strip_bullet(ch)
            return


DASH_LINE_RE = re.compile(r"^[\s\xa0]*[-\u2013][\s\xa0]+")


def dash_lines(root):
    """A paragraph whose lines after the first each start with a typed "- " (the PAC roles, the Career Centre links,
    the mural's flora) → that first line, then a real list of the rest. The typed hyphens are the list's bullets, so no
    word changes; a short first line ("1. Chair") is set as the list's lead (BodyFilter::dashLines())."""
    for p in list(root.elements("p")):
        kids = [c for c in p.children if not (isinstance(c, str) and not c.strip())]
        wrap = kids[0] if (len(kids) == 1 and isinstance(kids[0], El) and kids[0].tag in ("em", "strong", "i", "b", "span")) else None
        lines = [[]]
        for c in (wrap or p).children:
            if isinstance(c, El) and c.tag == "br":
                lines.append([])
            else:
                lines[-1].append(c)
        lines = [l for l in lines if any(isinstance(x, El) or x.strip("\xa0 \n\t") for x in l)]
        if len(lines) < 2:
            continue

        def lead(line):
            first = next((x for x in line if not (isinstance(x, str) and not x.strip("\xa0 \n\t"))), None)
            return first if isinstance(first, str) and DASH_LINE_RE.match(first) else None

        if lead(lines[0]) is not None or any(lead(l) is None for l in lines[1:]):
            continue
        for l in lines[1:]:
            i = l.index(lead(l))
            l[i] = DASH_LINE_RE.sub("", l[i], count=1)

        def box(tag, line):
            el = El(tag)
            target = el
            if wrap is not None:
                target = El(wrap.tag, wrap.attrs, el)
                el.children.append(target)
            for x in line:
                if isinstance(x, El):
                    x.parent = target
                target.children.append(x)
            return el

        head = box("p", lines[0])
        head.attrs = dict(p.attrs)
        if len(norm_ws(head.text())) <= 40 and not head.elements("a"):
            head.add_class("list-lead")
        ul = El("ul")
        for l in lines[1:]:
            li = box("li", l)
            li.parent = ul
            ul.children.append(li)
        replace_node(p, [head, ul])


def only_image(cell):
    imgs = cell.elements("img")
    return len(imgs) == 1 and not norm_ws(cell.text())


# Images that carry information (WCAG 1.1.1): alt = the image's own title; the concussion flowchart's words are also
# given as text right after it. Every word is transcribed from the image (content/corpus-images.txt).
def _ul(items):
    return "<ul>{}</ul>".format("".join("<li>{}</li>".format(esc(x)) for x in items))


def _lead(label, text=""):
    return '<p><strong>{}</strong>{}</p>'.format(esc(label), (" " + esc(text)) if text else "")


CONCUSSION_TEXT = "".join([
    "<p>A concussion is a brain injury and should be taken seriously.</p>",
    "<p>If you suspect a concussion, please report it to the principal and child's parent/guardian.</p>",
    "<p>A significant impact to the head or body that can cause the brain to move inside the skull</p>",
    _lead("STOP", "REMOVE FROM ACTIVITY IMMEDIATELY AND ASSESS FOR RED FLAGS"),
    _lead("RED FLAGS"),
    _ul(["Neck pain or tenderness", "Double vision", "Seizure or convulsion", "Weakness or tingling/burning in arms or legs",
         "Severe or increasing headache", "Loss of consciousness", "Deteriorating conscious state", "Vomiting",
         "Increasingly restless, agitated, or combative"]),
    _lead("IF YES TO ANY OF THE ABOVE:", "Call an ambulance or seek immediate medical care"),
    _lead("FOLLOW MEDICAL ADVICE, AND:"),
    "<p>Follow initial recovery protocol of physical and cognitive rest (2 days max):</p>",
    _ul(["Limited screen time (computers, TV, smartphones)", "Limited cognitive activity (reading, schoolwork)",
         "Limited physical activity"]),
    _lead("Note:", "Sleep is important! Do not wake during the night if sleeping comfortably"),
    _lead("AFTER 48 HOURS:"),
    _ul(["Follow Return to Activity protocol", "Follow Return to School protocol", "Follow Return to Sport protocol"]),
    _lead("IF NO TO ALL RED FLAGS:", "Assess for signs and symptoms of concussion"),
    _lead("CONCUSSION SIGNS AND SYMPTOMS"),
    _ul(["Headache", "Dizziness", "Nausea", "Blurred vision", "Light/Sound sensitivity", "Imbalance", "Ringing in the ears",
         'Seeing "stars"', "Irritability", "Fogginess", "Fatigue", "Difficulty concentrating", "Poor memory", "Neck pain",
         "Sadness", "Confusion"]),
    _lead("IF YES TO ANY OF THE ABOVE:", "SEEK MEDICAL ATTENTION from a licensed healthcare professional (physician/nurse practitioner*)"),
    "<p><small>* If applicable in your area</small></p>",
    _lead("IF NO SYMPTOMS:", "Limit physical activity and watch for concussion signs and symptoms for up to 48 hours"),
    _lead("IF SYMPTOMS OBSERVED WITHIN 48 HOURS"),
    _lead("IF NO SYMPTOMS OBSERVED AFTER 48 HOURS"),
    _lead("RESUME NORMAL ACTIVITY"),
    _lead("MENTAL HEALTH"),
    "<p>During the course of recovery from a concussion, seek medical attention for mental health challenges as needed, such as:</p>",
    _ul(["More emotional", "Irritability", "Sadness", "Nervousness or anxiousness", "Trouble falling asleep", "Depression"]),
    "<p>For more information on concussions, visit cattonline.com.</p>",
])
IMAGE_TEXT = {
    "c235ab92427a.png": ("Concussion Awareness, Response, and Management", CONCUSSION_TEXT),
    "bbcc5a0e0e76.jpg": ("Thank you for your support", ""),
    "7551c96b0920.png": ("Career Centre", ""),
    "a43685aafa0f.png": ("Welcome to School Cash Online", ""),
}


GENERIC_LINK = re.compile(r"^(?:click(?:ing)?\s+)?here\.?$", re.I)
INLINE_TAGS = {"strong", "b", "em", "i", "span", "u", "small"}
BOUNDARY = re.compile(r"[.!?:;)](?=[\s\u00a0]|$)")


def widen_generic_links(root):
    """A link that reads only "click here" / "here" says nothing in a screen reader's links list (WCAG 2.4.4,
    Lighthouse link-text). Same words, wider anchor: the clause it completes moves inside the link, the words before
    it back to the sentence start, or, when the link opens the sentence, the words after it to the sentence end."""
    for a_el in [n for n in root.iter() if n.tag == "a" and GENERIC_LINK.match(norm_ws(n.text()))]:
        parent = a_el.parent
        if parent is None:
            continue
        kids = parent.children
        i = kids.index(a_el)
        # backward: text nodes and inline formatting back to the last sentence boundary
        take, j, cut = [], i - 1, None
        while j >= 0:
            ch = kids[j]
            if isinstance(ch, str):
                ms = list(BOUNDARY.finditer(ch))
                if ms:
                    cut = (j, ms[-1].end())
                    break
                take.insert(0, ch)
            elif ch.tag in INLINE_TAGS and not ch.elements("a") and not BOUNDARY.search(ch.text()):
                take.insert(0, ch)
            else:
                break
            j -= 1
        before = "".join(x if isinstance(x, str) else x.text() for x in take)
        if cut is not None:
            before = kids[cut[0]][cut[1]:] + before
        if len(norm_ws(before).split()) >= 3:
            moved = take[:]
            if cut is not None:
                head, tail = kids[cut[0]][:cut[1]], kids[cut[0]][cut[1]:]
                lead_ws = tail[:len(tail) - len(tail.lstrip())]
                kids[cut[0]] = head + lead_ws
                if tail.strip():
                    moved.insert(0, tail.lstrip())
                first = cut[0] + 1
            else:
                first = j + 1
            del kids[first:i]
            for m in moved:
                if isinstance(m, El):
                    m.parent = a_el
            a_el.children = moved + a_el.children
            continue
        # forward: the words after the link up to the end of the sentence
        k = i + 1
        if k < len(kids) and isinstance(kids[k], str) and kids[k].strip():
            txt = kids[k]
            m = BOUNDARY.search(txt)
            end = m.start() if m else len(txt)
            clause = txt[:end]
            if len(norm_ws(clause).split()) >= 2:
                trail_ws = clause[len(clause.rstrip()):]
                a_el.children.append(clause.rstrip())
                kids[k] = trail_ws + txt[end:]


def transform_body(cur, body, title):
    root = parse(body)
    widen_generic_links(root)

    # empty paragraphs
    for p in root.elements("p"):
        if not norm_ws(p.text()) and not p.elements("img") and not p.elements("iframe") and p.parent:
            replace_node(p, [])

    # typed bullets (Wingdings or bullet glyphs at the start of consecutive paragraphs) → a real list
    for parent in list(root.iter()):
        run = []
        kids = list(parent.children)
        for ch in kids + [None]:
            if isinstance(ch, El) and ch.tag == "p" and BULLET_RE.match(ch.text()):
                run.append(ch)
                continue
            if isinstance(ch, str) and not ch.strip() and run:
                continue
            if len(run) >= 2:
                ul = El("ul", {}, parent)
                for p_el in run:
                    li = El("li", {}, ul)
                    li.children = p_el.children
                    for c in li.children:
                        if isinstance(c, El):
                            c.parent = li
                    strip_bullet(li)
                    ul.children.append(li)
                i = parent.children.index(run[0])
                for p_el in run:
                    parent.children.remove(p_el)
                parent.children.insert(i, ul)
            run = []

    dash_lines(root)

    # runs of non-breaking spaces typed for layout ("Telephone:" + 12 &nbsp;) → one space (whitespace only)
    for el in root.iter():
        el.children = [re.sub(r"[ \xa0]{2,}", " ", c) if isinstance(c, str) and "\xa0" in c else c for c in el.children]

    # two or more links standing alone side by side (Program Planning's Grade 7 / Grade 8-11 links) → a link list
    for parent in list(root.iter()):
        if parent.tag in ("a", "li", "p", "td", "th", "summary", "h2", "h3", "h4"):
            continue
        for run in _runs(parent, lambda n: isinstance(n, El) and n.tag == "a" and not n.elements("img") and norm_ws(n.text())
                         and "file-card" not in n.cls()):
            if len(run) < 2:
                continue
            ul = El("ul", {"class": "link-list"})
            for link in run:
                link.children = [norm_ws(link.text())] + [c for c in link.children if isinstance(c, El) and c.tag == "#raw"]
                ul.children.append(_adopt(El("li", {}, ul), [link]))
            _swap_run(parent, run, ul)

    # typed "date" heading + "- event" line pairs (Important Dates) → a dates list; the typed hyphen is punctuation
    date_re = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d", re.I)
    for parent in list(root.iter()):
        kids = [c for c in parent.children if not (isinstance(c, str) and not c.strip())]
        i, pairs_at = 0, []
        while i + 1 < len(kids):
            h, p_el = kids[i], kids[i + 1]
            if (isinstance(h, El) and re.match(r"^h[3-6]$", h.tag) and date_re.match(norm_ws(h.text()))
                    and isinstance(p_el, El) and p_el.tag == "p" and re.match(r"^[-–—]\s", norm_ws(p_el.text()))):
                pairs_at.append((h, p_el))
                i += 2
                continue
            if pairs_at and len(pairs_at) >= 2:
                break
            pairs_at = [] if not pairs_at or len(pairs_at) < 2 else pairs_at
            i += 1
        if len(pairs_at) >= 2:
            dl = El("dl", {"class": "dates"})
            for h, p_el in pairs_at:
                dt = _adopt(El("dt", {}, dl), h.children)
                strip_lead = list(p_el.children)
                for j, c in enumerate(strip_lead):
                    if isinstance(c, str):
                        if c.strip():
                            strip_lead[j] = re.sub(r"^\s*[-–—]\s*", "", c)
                            break
                        continue
                    break
                dd = _adopt(El("dd", {}, dl), [c for c in strip_lead if c != ""])
                dl.children += [dt, dd]
            first = pairs_at[0][0]
            idx = parent.children.index(first)
            for h, p_el in pairs_at:
                parent.children.remove(h)
                parent.children.remove(p_el)
            parent.children.insert(idx, dl)
            dl.parent = parent

    # ALL-CAPS headings typed into the body read as eyebrows (class only; the words stay as typed)
    for h in root.iter():
        if re.match(r"^h[2-6]$", h.tag):
            letters = [c for c in h.text() if c.isalpha()]
            if len(letters) >= 4 and all(c.isupper() for c in letters):
                h.add_class("is-caps")

    # heading order: the page title is the h1, so the body starts at h2
    levels = [int(h.tag[1]) for h in root.iter() if re.match(r"^h[2-6]$", h.tag)]
    if levels and min(levels) > 2:
        shift = min(levels) - 2
        for h in root.iter():
            if re.match(r"^h[2-6]$", h.tag):
                h.tag = "h{}".format(int(h.tag[1]) - shift)
    # ...and no heading skips a level on the way down (a body that opens with h3 before its first h2): a heading
    # deeper than one below the one before it moves up, keeping its words and id
    prev = 1
    for h in root.iter():
        if re.match(r"^h[2-6]$", h.tag):
            lvl = min(int(h.tag[1]), prev + 1)
            h.tag = "h{}".format(lvl)
            prev = lvl

    # heading ids from their own text (a small theme preprocess; the body stays untouched), so a menu deep link
    # such as /students/career-centre-information#post-secondary-info lands on its section
    used = HEADING_IDS.setdefault(cur, set())
    for h in root.iter():
        if re.match(r"^h[2-6]$", h.tag) and not h.attrs.get("id"):
            base = slug(h.text())
            if not base:
                continue
            hid, n = base, 2
            while hid in used or hid in CHROME_IDS:
                hid, n = "{}-{}".format(base, n), n + 1
            used.add(hid)
            h.attrs["id"] = hid

    # images: @img/<name> → optimised copy with intrinsic size, lazy
    for im in root.elements("img"):
        src = im.attrs.get("src", "")
        if src.startswith("@img/"):
            name = src[5:]
            url, w, h = img_src(cur, name)
            im.attrs["src"] = url
            if not (im.attrs.get("width") and im.attrs.get("height")) and w:
                im.attrs["width"], im.attrs["height"] = str(w), str(h)
            info = IMAGE_TEXT.get(name)
            if info and not norm_ws(im.attrs.get("alt")):
                im.attrs["alt"] = info[0]
                if info[1]:
                    holder = im.parent if im.parent is not None and im.parent.tag in ("p", "a") else im
                    while holder.parent is not None and holder.parent.tag in ("p", "a"):
                        holder = holder.parent
                    if holder.parent is not None:
                        det = raw('<details class="accordion img-text"><summary>{}</summary><div class="accordion__body">{}</div>'
                                  '</details>'.format(esc(info[0]), info[1]))
                        i = holder.parent.children.index(holder)
                        holder.parent.children.insert(i + 1, det)
            srcset = img_srcset(cur, name)
            if srcset:
                im.attrs["srcset"] = srcset
                im.attrs["sizes"] = "(max-width: 47rem) 100vw, 44rem"
        im.attrs.setdefault("alt", "")
        im.attrs["loading"] = "lazy"
        im.attrs["decoding"] = "async"

    # links
    for link in root.elements("a"):
        href = link.attrs.get("href")
        if href is None:
            continue
        url, ext = resolve(cur, href)
        link.attrs["href"] = url
        if "title" in link.attrs and norm_ws(link.attrs["title"]).lower() == norm_ws(link.text()).lower():
            del link.attrs["title"]
        if "file-card" in link.cls():
            m = re.search(r"\.([a-z0-9]{2,5})(?:$|[?#])", url.lower())
            kind = (link.attrs.get("data-ext") or "").lower()
            kind = kind if kind in FILE_EXTS else (m.group(1) if m and m.group(1) in FILE_EXTS else "")
            link.attrs.pop("data-ext", None)
            size = link.attrs.pop("data-size", None)     # legacy Attachments table: the file's size column
            label = El("span", {"class": "file-name"}, link)
            label.children = link.children
            for c in label.children:
                if isinstance(c, El):
                    c.parent = label
            if size:
                label.children.append(raw('<span class="file-size">{}</span>'.format(esc(size))))
            badge = raw('<span class="file-badge" data-ext="{0}" aria-hidden="true">{1}</span>'.format(
                kind, kind or icon("paper")))
            link.children = [badge, label, raw(icon("download"))]
        elif ext:
            link.children.append(raw(EXT))

    # a paragraph that is only a link to a document (the article Attachments field, legacy attachments) → file card
    doc_re = re.compile(r"\.(pdf|docx?|pptx?|xlsx?)(?:$|[?#])", re.I)
    for parent in list(root.iter()):
        run, groups = [], []
        for ch in parent.children + [None]:
            is_doc = False
            if isinstance(ch, El) and ch.tag == "p":
                kids = [c for c in ch.children if not (isinstance(c, str) and not c.strip())]
                if len(kids) == 1 and isinstance(kids[0], El) and kids[0].tag == "a" and doc_re.search(kids[0].attrs.get("href", "")):
                    is_doc = True
            if is_doc:
                run.append(ch)
                continue
            if isinstance(ch, str) and not ch.strip() and run:
                continue
            if run:
                groups.append(run)
            run = []
        for run in groups:
            wrap = El("div", {"class": "file-list"}, parent)
            for p_el in run:
                link = [c for c in p_el.children if isinstance(c, El)][0]
                kind = doc_re.search(link.attrs["href"]).group(1).lower()
                link.attrs["class"] = "file-card"
                label = El("span", {"class": "file-name"}, link)
                label.children = [c for c in link.children if not (isinstance(c, El) and c.tag == "#raw")]
                link.children = [raw('<span class="file-badge" data-ext="{0}" aria-hidden="true">{0}</span>'.format(kind)),
                                 label, raw(icon("download"))]
                link.parent = wrap
                wrap.children.append(link)
            i = parent.children.index(run[0])
            for p_el in run:
                parent.children.remove(p_el)
            parent.children.insert(i, wrap)

    structure_media(root, cur)

    # iframes: the embeds the live site already uses, made responsive
    for fr in root.elements("iframe"):
        kind = next((c for c in fr.cls() if c.startswith("embed-")), "embed-video")
        fr.attrs.pop("width", None)
        fr.attrs.pop("height", None)
        fr.attrs.pop("class", None)
        if not norm_ws(fr.attrs.get("title")):
            fr.attrs["title"] = title
        fr.attrs["loading"] = "lazy"
        wrap = El("div", {"class": "embed " + kind})
        target = fr.parent if (fr.parent.tag == "p" and len(fr.parent.element_children()) == 1 and not norm_ws(fr.parent.text())) else fr
        replace_node(target, [wrap])
        fr.parent = wrap
        wrap.children = [fr]

    autolink_phones(root)

    # tables: a one-row [image | text] layout table → media note (or a call-out when it leads with a phone number);
    # every other table scrolls inside a focusable wrapper
    for t in root.elements("table"):
        rows = t.elements("tr")
        cells = rows[0].element_children() if len(rows) == 1 else []
        if len(rows) == 1 and len(cells) == 2 and any(only_image(c) for c in cells):
            img_cell = cells[0] if only_image(cells[0]) else cells[1]
            text_cell = cells[1] if img_cell is cells[0] else cells[0]
            tels = [l for l in text_cell.elements("a") if l.attrs.get("href", "").startswith("tel:")]
            body_div = El("div")
            body_div.children = text_cell.children
            for c in body_div.children:
                if isinstance(c, El):
                    c.parent = body_div
            if tels:
                btn = raw('<a class="btn" href="{}">{}{}</a>'.format(esc(tels[0].attrs["href"]), icon("phone"),
                                                                     esc(norm_ws(tels[0].text()))))
                body_div.children.append(btn)
                node = El("div", {"class": "callout on-dark"})
                node.children = [raw('<span class="ring" aria-hidden="true">{}</span>'.format(icon("phone"))), body_div]
            else:
                im = img_cell.elements("img")[0]
                wide = int(im.attrs.get("width") or 0) > 200
                node = El("div", {"class": "media-note" + (" media-note--wide" if wide else "")})
                fig = El("div", {"class": "media-note-img"})
                fig.children = [im]
                node.children = [fig, body_div]
            replace_node(t, [node])
        else:
            flat = flatten_table(cur, t, rows)
            if flat is not None:
                replace_node(t, flat)
                continue
            cols = max((len(r.element_children()) for r in rows), default=0)
            wrap = El("div", {"class": "table-wrap" + (" is-wide" if cols >= 5 else "")})
            replace_node(t, [wrap])
            t.parent = wrap
            wrap.children = [t]
            if t.elements("th") and len(rows) >= 20:
                directory_table(t, wrap)

    tweak = PAGE_TWEAKS.get(cur)
    if tweak:
        tweak(root, cur)
    return serialize(root)


def _tweak_attendance(root, cur):
    """Student Attendance: the bold sentence after the call-out is the lead; the typed list of what to say on the
    phone becomes a numbered list (decision graft 4)."""
    for p in root.elements("p"):
        kids = [c for c in p.children if not (isinstance(c, str) and not c.strip())]
        if len(kids) == 1 and isinstance(kids[0], El) and kids[0].tag == "strong" and len(norm_ws(p.text())) > 40:
            p.add_class("lead")
            break
    for p in root.elements("p"):
        if norm_ws(p.text()).lower().startswith("please provide the following information"):
            sib = p.parent.children[p.parent.children.index(p) + 1:]
            nxt = next((s for s in sib if isinstance(s, El)), None)
            if nxt is not None and nxt.tag == "ul":
                nxt.tag = "ol"
                nxt.add_class("steps")
            break


# ---------------------------------------------------------------------------------------------- media, tiles and layout tables
def _kids(el):
    return [c for c in el.children if not (isinstance(c, str) and not c.strip())]


def _only_img_link(node):
    """An <a> whose only content is one image (gallery items)."""
    return isinstance(node, El) and node.tag == "a" and len(node.elements("img")) == 1 and not norm_ws(node.text())


def _runs(parent, test):
    """Runs of consecutive children passing `test` (whitespace between them is skipped)."""
    runs, run = [], []
    for ch in parent.children + [None]:
        if ch is not None and test(ch):
            run.append(ch)
            continue
        if isinstance(ch, str) and not ch.strip() and run:
            continue
        if run:
            runs.append(run)
        run = []
    return runs


def _swap_run(parent, run, node):
    i = parent.children.index(run[0])
    for x in run:
        parent.children.remove(x)
    parent.children.insert(i, node)
    node.parent = parent


def _adopt(parent, nodes):
    parent.children = list(nodes)
    for n in parent.children:
        if isinstance(n, El):
            n.parent = parent
    return parent


def _plain_text(el):
    """Text outside <strong>/<b>: empty means the cell is all bold (a label)."""
    out = []
    for ch in el.children:
        if isinstance(ch, str):
            out.append(ch)
        elif ch.tag not in ("strong", "b"):
            out.append(_plain_text(ch))
    return norm_ws("".join(out))


def unrel(cur, url):
    """A URL this build wrote for page `cur` → the site path it points at (None for other hosts)."""
    if url.startswith(LIVE):
        return ("/" + url[len(LIVE):].split("#")[0].split("?")[0].strip("/")).rstrip("/") or "/"
    if re.match(r"^[a-z]+:|^//", url):
        return None
    parts = [x for x in cur.strip("/").split("/") if x]
    for seg in url.split("#")[0].split("?")[0].split("/"):
        if seg == "..":
            if parts:
                parts.pop()
        elif seg not in ("", "."):
            parts.append(seg)
    return "/" + "/".join(parts)


def go_icon(url):
    return icon("ext" if re.match(r"^(https?:)?//", url) else "arrow", "icon tile-go")


def structure_media(root, cur):
    """Galleries, banner reels, launch tiles and link chips (the live site's colorbox galleries, the Library banner
    slideshow, image links and one-link paragraphs), each mapped to what Drupal renders."""
    title = page_title(cur)
    for parent in list(root.iter()):
        if parent.tag in ("a", "figure", "li", "td", "th"):
            continue
        # image links in a row → gallery + lightbox (field_image, colorbox formatter)
        for run in _runs(parent, _only_img_link):
            if len(run) < 3:
                continue
            ul = El("ul", {"class": "gallery" + (" gallery--covers" if cur == "/library/read-listen" else ""),
                           "data-gallery": None})
            for link in run:
                im = link.elements("img")[0]
                cap = norm_ws(html.unescape(link.attrs.pop("title", "") or im.attrs.get("alt", "")))
                link.attrs["class"] = "gallery-link"
                link.attrs["data-lightbox"] = im.attrs.get("src", "")
                fig = El("figure")
                fig.children = [link]
                link.parent = fig
                if cap:
                    fig.children.append(_adopt(El("figcaption", {}, fig), [cap]))
                ul.children.append(_adopt(El("li", {}, ul), [fig]))
            _swap_run(parent, run, ul)
        # bare images in a row → banner reel (the Library page slideshow), scroll-snap, no autoplay
        for run in _runs(parent, lambda n: isinstance(n, El) and n.tag == "img"):
            # only the Library's banner slideshow is a reel; other images next to each other stay inline as on
            # the live site (their alt text is never turned into a visible caption)
            if len(run) < 2 or not (cur == "/library" or all(
                    norm_ws(im.attrs.get("alt", "")).lower().startswith("banner") for im in run)):
                continue
            track = El("ul", {"class": "reel-track", "tabindex": "0", "aria-label": title, "data-reel-track": None})
            for i, im in enumerate(run):
                # the slide keeps the live alt text; the caption shows it without the "banner" prefix and is
                # hidden from screen readers, which already hear the alt
                cap = re.sub(r"^Banner\s+", "", norm_ws(im.attrs.get("alt", "")), flags=re.I)
                if "description automatically generated" in cap.lower():
                    cap = ""
                if i == 0:
                    im.attrs["loading"] = "eager"
                fig = _adopt(El("figure"), [im])
                if cap:
                    fig.children.append(_adopt(El("figcaption", {"aria-hidden": "true"}, fig), [cap]))
                track.children.append(_adopt(El("li", {"class": "reel-slide"}, track), [fig]))
            nav = raw('<div class="reel-nav needs-js"><button type="button" class="reel-btn reel-prev" data-reel-prev>{}'
                      '<span class="vh">Previous</span></button><ol class="reel-dots" aria-hidden="true">{}</ol>'
                      '<button type="button" class="reel-btn" data-reel-next>{}<span class="vh">Next</span></button></div>'.format(
                          icon("arrow"), "<li></li>" * len(run), icon("arrow")))
            reel = _adopt(El("div", {"class": "reel", "data-reel": None}), [track, nav])
            _swap_run(parent, run, reel)
        # paragraphs that are one short link each (Biblio Bites months) → link chips
        def chip_p(n):
            if not (isinstance(n, El) and n.tag == "p"):
                return False
            k = _kids(n)
            return (len(k) == 1 and isinstance(k[0], El) and k[0].tag == "a" and not k[0].elements("img")
                    and "file-card" not in k[0].cls() and 0 < len(norm_ws(n.text())) <= 32)
        for run in _runs(parent, chip_p):
            if len(run) < 3:
                continue
            ul = El("ul", {"class": "link-chips"})
            for p_el in run:
                link = _kids(p_el)[0]
                ul.children.append(_adopt(El("li", {}, ul), [link]))
            _swap_run(parent, run, ul)
    if cur in DATED_DOCS:
        dated_documents(root)
    # file attachment paragraphs that hold only files (no heading, no description) → one list
    for parent in list(root.iter()):
        def plain_group(n):
            return (isinstance(n, El) and n.tag == "div" and "paragraph--type-file-attachments" in n.cls()
                    and [c.tag for c in n.element_children()] == ["div"] and "file-list" in n.element_children()[0].cls())
        for run in _runs(parent, plain_group):
            first = run[0].element_children()[0]
            for other in run[1:]:
                for c in other.element_children()[0].element_children():
                    c.parent = first
                    first.children.append(c)
                parent.children.remove(other)
    # document lists split into one wrapper per file (PAC minutes) → one list; a long one gets the filter
    for parent in list(root.iter()):
        for run in _runs(parent, lambda n: isinstance(n, El) and n.tag == "div" and "file-list" in n.cls()):
            first = run[0]
            for other in run[1:]:
                for c in other.element_children():
                    c.parent = first
                    first.children.append(c)
                parent.children.remove(other)
    for fl in root.elements("div"):
        cards = [c for c in fl.element_children() if c.tag == "a"] if "file-list" in fl.cls() else []
        if len(cards) >= 12 and fl.parent is not None and "directory" not in (fl.parent.attrs.get("class") or ""):
            for c in cards:
                c.attrs["data-filter-row"] = None
            scope = El("div", {"class": "directory", "data-filter": None})
            replace_node(fl, [scope])
            _adopt(scope, [raw(filter_bar("files", len(cards))), fl])
    # an image link with its own label (Digital Resources, Library Catalogue) → launch tile
    for link in root.elements("a"):
        imgs = link.elements("img")
        txt = norm_ws(link.text())
        if len(imgs) != 1 or not txt or len(txt) > 60 or has_ancestor(link, "table") or has_ancestor(link, "li"):
            continue
        im = imgs[0]
        im.attrs["alt"] = ""
        link.attrs["class"] = "launch-tile"
        link.children = [_adopt(El("span", {"class": "launch-img"}), [im]),
                         _adopt(El("span", {"class": "launch-text"}), [txt]),
                         raw(go_icon(link.attrs.get("href", "")))]
        for c in link.children:
            if isinstance(c, El):
                c.parent = link
        if link.parent.tag == "p" and len(_kids(link.parent)) == 1:
            replace_node(link.parent, [link])


DATED_DOCS = {"/parents/pac/meeting-minutes", "/parents/pac/meeting-agendas"}
_MON = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def doc_date(text):
    """The meeting date in a PAC file name or heading: 2023 09 13, 20250910, 2026-4-8, Nov 8, 2023, May 2025 ..."""
    t = text or ""
    m = re.search(r"(20\d\d)(\d\d)(\d\d)(?!\d)", t) or re.search(r"(20\d\d)[ _.\-]+(\d{1,2})[ _.\-]+(\d{1,2})(?!\d)", t)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    m = re.search(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(20\d\d)", t)
    if m and m.group(1)[:3].lower() in _MON:
        return date(int(m.group(3)), _MON.index(m.group(1)[:3].lower()) + 1, int(m.group(2)))
    m = re.search(r"\b([A-Za-z]{3,9})\.?,?\s+(20\d\d)", t)
    if m and m.group(1)[:3].lower() in _MON:
        return date(int(m.group(2)), _MON.index(m.group(1)[:3].lower()) + 1, 1)
    return None


def dated_documents(root):
    """PAC Meeting Minutes / Agendas: one file attachments paragraph per meeting (some with a heading such as
    "September 2025 PAC Meeting Minutes") → one list, newest first, each card titled by its paragraph's heading.
    Drupal: the paragraphs sorted by date in the node template (or a view of media sorted by the date field)."""
    groups = [g for g in root.elements("div") if "paragraph--type-file-attachments" in g.cls()]
    if not groups:
        return
    entries = []
    for order, g in enumerate(groups):
        heads = [h for h in g.element_children() if re.match(r"^h[2-6]$", h.tag)]
        head = norm_ws(heads[0].text()) if heads else ""
        for card in [c for c in g.elements("a") if "file-card" in c.cls()]:
            label = next((c for c in card.element_children() if "file-name" in c.cls()), None)
            name = norm_ws(label.text()) if label is not None else ""
            d = doc_date(name) or doc_date(head) or date(1900, 1, 1)
            if head and label is not None:
                kids = label.children
                label.children = [raw('<span class="file-title">{}</span>'.format(esc(head))),
                                  _adopt(El("span", {"class": "file-sub"}, label), kids)]
            entries.append((d, order, card))
    entries.sort(key=lambda e: (e[0], e[1]), reverse=True)
    wrap = El("div", {"class": "file-list file-list--dated"})
    _adopt(wrap, [e[2] for e in entries])
    first = groups[0]
    replace_node(first, [wrap])
    for g in groups[1:]:
        if g.parent is not None and g in g.parent.children:
            g.parent.children.remove(g)


def flatten_table(cur, t, rows):
    """Tables the live site used for layout → the layout itself. Returns replacement nodes, or None to keep the table."""
    cells = [r.element_children() for r in rows]
    flat = [c for r in cells for c in r]
    if not flat:
        return []
    # an empty grid left in the body → nothing
    if not any(norm_ws(c.text()) or c.elements("img") or c.elements("iframe") for c in flat):
        return []
    # one row of links (Student Login) → link tiles
    if len(rows) == 1 and len(flat) >= 2 and all(
            len(c.elements("a")) == 1 and norm_ws(c.text()) and norm_ws(c.text()) == norm_ws(c.elements("a")[0].text())
            for c in flat):
        lis = "".join('<li><a class="link-tile" href="{}"><span>{}</span>{}</a></li>'.format(
            esc(c.elements("a")[0].attrs.get("href", "")), esc(norm_ws(c.text())), go_icon(c.elements("a")[0].attrs.get("href", "")))
            for c in flat)
        return [raw('<ul class="link-tiles">{}</ul>'.format(lis))]
    # image links over a caption row (Extra-Curricular) → feature tiles named after the page they open
    if (len(rows) == 2 and len(cells[0]) == len(cells[1]) >= 2
            and all(only_image(c) and c.elements("a") for c in cells[0])):
        lis = []
        for top, bottom in zip(cells[0], cells[1]):
            link, im = top.elements("a")[0], top.elements("img")[0]
            url = link.attrs.get("href", "")
            target = unrel(cur, url)
            name = page_title(target) if target else ""
            im.attrs["alt"] = ""
            lis.append('<li><a class="feature-tile" href="{u}"><span class="feature-img">{img}</span><span class="feature-body">'
                       '<strong>{t}</strong><span>{c}</span></span>{go}</a></li>'.format(
                           u=esc(url), img=serialize(im), t=esc(name), c=esc(norm_ws(bottom.text())), go=go_icon(url)))
        return [raw('<ul class="feature-tiles">{}</ul>'.format("".join(lis)))]
    heads = bool(t.elements("th") or t.elements("thead"))
    # bold label | long text rows (School Learning Story posts) → stacked label/text blocks
    pairs = [r for r in cells if len(r) == 2]
    if not heads and pairs and all(len(r) in (1, 2) for r in cells):
        firsts = [norm_ws(r[0].text()) for r in pairs]
        seconds = [norm_ws(r[1].text()) for r in pairs]
        if (all(0 < len(f) <= 120 for f in firsts) and sum(not _plain_text(r[0]) for r in pairs) >= max(1, .6 * len(pairs))
                and sum(map(len, seconds)) / len(seconds) > 80):
            div = El("div", {"class": "kv"})
            for r in cells:
                if len(r) == 1:          # a full-width row (Photos:) stays one block
                    div.children.append(_adopt(El("div", {"class": "kv-full"}, div), r[0].children))
                    continue
                row = El("div", {"class": "kv-row"}, div)
                lab = _adopt(El("p", {"class": "kv-label"}, row), [norm_ws(r[0].text())])
                body = _adopt(El("div", {"class": "kv-body"}, row), r[1].children)
                row.children = [lab, body]
                div.children.append(row)
            return [div]
    # short lists under bold column headers (Strikers sports by season) → one card per column
    ncol = len(cells[0])
    if (2 <= ncol <= 4 and len(rows) >= 4 and all(len(r) == ncol for r in cells)
            and all(not _plain_text(c) and 0 < len(norm_ws(c.text())) <= 30 for c in cells[0])
            and all(len(norm_ws(c.text())) <= 50 for r in cells[1:] for c in r)
            and sum(bool(_plain_text(c)) for r in cells[1:] for c in r) >= .6 * sum(len(r) for r in cells[1:])):
        cols = []
        for j in range(ncol):
            items = [norm_ws(r[j].text()) for r in cells[1:] if norm_ws(r[j].text())]
            cols.append('<section class="col-list"><h3>{}</h3><ul>{}</ul></section>'.format(
                esc(smart_case(norm_ws(cells[0][j].text()))), "".join("<li>{}</li>".format(esc(x)) for x in items)))
        return [raw('<div class="col-lists">{}</div>'.format("".join(cols)))]
    return None


def filter_bar(uid, total, hidden=True):
    """Client-side filter for a list or table (js/filter.js); .needs-js shows it only when scripts run."""
    return ('<div class="filter-bar{h}" data-filter-bar><label class="vh" for="filter-{u}">Search</label>{si}'
            '<input id="filter-{u}" type="search" placeholder="Search" autocomplete="off" spellcheck="false" data-filter-input>'
            '<output class="filter-count" for="filter-{u}" aria-hidden="true" data-filter-total>{n}</output>'
            '<p class="vh" role="status" aria-atomic="true" data-filter-status><span>Search results</span> <span data-n>{n}</span></p>'
            '</div><p class="filter-empty" hidden data-filter-empty>Your search yielded no results.</p>').format(h=" needs-js" if hidden else "", u=uid, si=icon("search"), n=total)


def directory_table(t, wrap):
    """A long data table (Club Directory) → searchable, and each row a card on phones (labels from the header)."""
    heads = [norm_ws(th.text()) for th in (t.elements("thead")[0].elements("th") if t.elements("thead") else [])]
    t.add_class("data-cards")
    body = t.elements("tbody")
    n = 0
    for tr in (body[0].elements("tr") if body else []):
        tr.attrs["data-filter-row"] = None
        n += 1
        for i, td in enumerate(tr.element_children()):
            if i < len(heads):
                td.attrs["data-label"] = heads[i]
            if i == 0:
                td.tag, td.attrs["scope"] = "th", "row"
    scope = El("div", {"class": "directory", "data-filter": None})
    replace_node(wrap, [scope])
    _adopt(scope, [raw(filter_bar("directory", n)), wrap])


def first_image(path):
    m = re.search(r'@img/([^"]+)', (PAGES.get(path) or {}).get("body", ""))
    return m.group(1) if m else None


def image_tiles(cur, paths, heading_tag="h3"):
    """Child or sibling pages as photo tiles: each page's own first image (icons shown whole), or an arch icon well."""
    lis = []
    for pth in paths:
        name = first_image(pth)
        url, ext = resolve(cur, pth)
        if name:
            src, w, h = img_src(cur, name)
            is_icon = name.endswith(".png") and (w or 0) <= 600
            media = '<img src="{}" alt="" width="{}" height="{}" loading="lazy" decoding="async">'.format(src, w, h)
        else:
            is_icon = True
            media = '<span class="tile-ico">{}</span>'.format(icon("search" if "research" in pth else "paper"))
        lis.append('<li><a class="photo-tile{c}" href="{u}"><span class="photo-tile-img">{m}</span>'
                   '<{h} class="photo-tile-title">{t}</{h}>{go}</a></li>'.format(
                       c=" is-icon" if is_icon else "", u=esc(url), m=media, h=heading_tag, t=esc(page_title(pth)),
                       go=icon("ext" if ext else "arrow", "icon tile-go")))
    return '<ul class="photo-tiles">{}</ul>'.format("".join(lis))


def _tweak_library(root, cur):
    """Library Learning Commons: banner reel, then Library Events, About Us, Newsletter Archive and Social Media as
    cards (DS layout bs_2col); the Library pages follow as the hub's photo tiles (hub_sections)."""
    kids = [c for c in root.children if isinstance(c, El)]
    reel = next((c for c in kids if "reel" in c.cls()), None)
    secs, order, cur_h = {}, [], None
    for c in kids:
        if c.tag == "h2":
            cur_h = norm_ws(c.text())
            secs[cur_h] = []
            order.append(cur_h)
        elif cur_h:
            secs[cur_h].append(c)
    rows, roles = [], []
    for n in secs.get("About Us", []):
        if n.tag == "h3":
            roles.append(norm_ws(n.text()))
        elif n.tag == "p":
            rows.append((roles, norm_ws(n.text())))
            roles = []
    about = "".join('<div class="llc-person{c}">{ico}<dt>{r}</dt><dd>{v}</dd></div>'.format(
        c=" is-hours" if r == ["Hours"] else "", ico=icon("clock" if r == ["Hours"] else "people"),
        r=" ".join('<span>{}</span>'.format(esc(x)) for x in r), v=esc(v)) for r, v in rows)
    nl = ""
    for n in secs.get("Newsletter Archive", []):
        for link in n.elements("a"):
            im = link.elements("img")
            target = unrel(cur, link.attrs.get("href", ""))
            img_html = ""
            if im:
                im[0].attrs["alt"] = ""
                img_html = serialize(im[0])
            nl = '<a class="llc-tile" href="{}"><span class="llc-tile-img">{}</span><span>{}</span>{}</a>'.format(
                esc(link.attrs.get("href", "")), img_html, esc(page_title(target) if target else ""), icon("arrow", "icon tile-go"))
    social = ""
    for n in secs.get("Social Media", []):
        for link in ([n] if n.tag == "a" else n.elements("a")):
            href = link.attrs.get("href", "")
            label = norm_ws(link.text())         # the live link text (the full URL), allowed to wrap after each slash
            social = '<a class="llc-social" href="{}"><span class="ring">{}</span><span>{}</span></a>'.format(
                esc(href), icon("insta"), esc(label).replace("/", "/<wbr>").replace("?", "<wbr>?"))
    events = "".join(serialize(n) for n in secs.get("Library Events", []))
    html_out = ('<!-- body field split by its h2s into DS regions (the Library pages follow as the hub sections) -->'
                '<div class="llc"><section class="llc-card llc-events"><h2>Library Events</h2>{ev}</section>'
                '<section class="llc-card llc-about on-dark"><h2>About Us</h2><dl>{about}</dl></section>'
                '<section class="llc-card"><h2>Newsletter Archive</h2>{nl}</section>'
                '<section class="llc-card"><h2>Social Media</h2>{social}</section></div>').format(
        ev=events, about=about, nl=nl, social=social)
    root.children = ([reel] if reel else []) + [raw(html_out)]


def _tweak_strikers(root, cur):
    """Strikers Athletics: the team logo leads, on a forest arch plate beside the opening paragraphs."""
    for p_el in root.elements("p"):
        k = _kids(p_el)
        if len(k) == 1 and isinstance(k[0], El) and k[0].tag == "img":
            plate = _adopt(El("div", {"class": "logo-plate", "aria-hidden": "true"}), [k[0]])
            replace_node(p_el, [plate])
        break


def _tweak_bell(root, cur):
    """Bell Schedule: the timetable image becomes real tables (custom block from content/bell-schedule.json)."""
    for im in root.elements("img"):
        if "bf352cd7a200" in im.attrs.get("src", ""):
            target = im.parent if (im.parent.tag == "p" and len(_kids(im.parent)) == 1) else im
            replace_node(target, [raw(bell_html(cur))])
            return


def _tweak_contact(root, cur):
    """Contact Us: the loose inline lines before Address (name, motto, Early Warning, Email) become a card, one line
    per bold label, as the live page shows them."""
    lead = []
    for ch in list(root.children):
        if isinstance(ch, El) and ch.tag in ("h2", "h3", "p", "div", "iframe"):
            break
        lead.append(ch)
    if not lead:
        return
    groups = []
    for ch in lead:
        if isinstance(ch, El) and ch.tag in ("strong", "em") or not groups:
            groups.append([])
        groups[-1].append(ch)
    lines = []
    for g in groups:
        kids = [c for c in g if not (isinstance(c, str) and not c.strip())]
        cls = "ci-name" if not lines and kids and isinstance(kids[0], El) and kids[0].tag == "strong" and len(kids) == 1 else (
            "ci-motto" if len(kids) == 1 and isinstance(kids[0], El) and kids[0].tag == "em" else "ci-line")
        node = _adopt(El("p", {"class": cls}), g)
        if cls != "ci-line":
            node.children = [norm_ws(node.text())]
        lines.append(node)
    card = _adopt(El("div", {"class": "contact-intro on-dark"}), lines)
    i = root.children.index(lead[0])
    for ch in lead:
        root.children.remove(ch)
    root.children.insert(i, card)
    card.parent = root


BELL_PATH = "/school-calendar/bell-schedule"
PAGE_TWEAKS = {"/contact-us": _tweak_contact, "/parents/student-attendance": _tweak_attendance, "/library": _tweak_library,
               "/extra-curricular/strikers-athletics": _tweak_strikers, BELL_PATH: _tweak_bell}


# ---------------------------------------------------------------------------------------------- page pieces
def nowrap_ranges(h):
    """A number range typed with spaces ("Incoming 9 - 12") never breaks inside, so no line starts with its dash. Takes
    and returns escaped HTML; the words are unchanged."""
    return re.sub(r"(\d+) - (\d+)", r'<span class="nowrap">\1 - \2</span>', h)


def page_hero(cur, title, eyebrow="", meta="", compact=False):
    """Page header. Hubs keep the tall photo band; leaf and task pages get the compact one, so the body starts on the
    first screen. When the menu names the page differently (Bell Schedule → "Timetable Structure 2026-2027"), the
    menu label is the eyebrow, so the hero confirms where the visitor landed."""
    src, w, h = img_src(cur, HEADER_IMG)
    crumbs = breadcrumbs(cur)
    lis = "".join("<li>{}</li>".format(a(cur, href, esc(t))) for t, href in crumbs)
    lis += '<li><span aria-current="page">{}</span></li>'.format(esc(title))
    label = MENU_LABEL.get(cur)
    alias = bool(label and norm_ws(label).lower() != norm_ws(title).lower() and cur not in TOPS
                 and norm_ws(label).lower() not in norm_ws(title).lower())
    if alias:
        eb = '<p class="eyebrow eyebrow--alias">{}</p>'.format(esc(label))
    elif eyebrow:
        eb = '<p class="eyebrow">{}</p>'.format(esc(eyebrow))
    else:
        eb = '<p class="eyebrow" aria-hidden="true"></p>'
    return ('<!-- node full: #header-img-area photo (bg_image_formatter), breadcrumb region (system_breadcrumb_block), title -->\n'
            '<header class="page-hero on-dark{c}" id="header-img-area">'
            '<div class="page-hero-img" aria-hidden="true"><img src="{src}" alt="" width="{w}" height="{h}" fetchpriority="high"></div>'
            '<div class="wrap"><div class="region region-breadcrumb"><nav class="breadcrumb" id="block-breadcrumbs" aria-label="breadcrumb"><ol>{lis}</ol></nav></div>'
            '{eb}<h1 id="page-title">{t}</h1>{meta}</div></header>').format(
        c=" page-hero--compact" if compact else "", src=src, w=w, h=h, lis=lis, eb=eb, t=nowrap_ranges(esc(title)), meta=meta)


def section_nav(cur):
    """Section menu (menu block: the main-menu subtree of the page's section, design/ia.json): the hub, the
    most-requested links, then each column under its own heading. The page is marked aria-current; a page the menu
    does not list (an article, the PDF page) marks its nearest listed ancestor as the active trail."""
    sec = section_of(cur)
    if not sec:
        return "", ""
    trail = menu_trail(sec, cur)

    def groups(title_tag):
        out = []
        for i, g in enumerate(sec["groups"]):
            links = "".join("<li>{}</li>".format(menu_link(cur, c, "", trail, arrow=False)) for c in g["children"])
            out.append('<div class="nav-group{f}">{t}<ul>{l}</ul></div>'.format(
                f=" is-featured" if i == 0 else "", t=group_title(cur, g, title_tag, "nav-group-title", glue=True), l=links))
        return "".join(out)

    here = ' aria-current="page"' if canon(sec["href"]) == cur else ""
    head = a(cur, sec["href"], "<span>{}</span>{}".format(esc(sec["label"]), icon("arrow")), "", here)
    desktop = ('<aside class="page-sidebar region region-sidebar-first"><!-- menu block: main, the {t} subtree -->'
               '<nav class="section-nav" aria-labelledby="section-nav-title"><h2 id="section-nav-title">{head}</h2>'
               '{groups}</nav></aside>').format(t=esc(sec["label"]), head=head, groups=groups("h3"))
    mobile = ('<details class="section-nav-mobile"><summary><span>{t}</span>{chev}</summary>'
              '<div class="section-nav-mobile-body">{head}{groups}</div></details>').format(
        t=esc(sec["label"]), chev=icon("chev", "chev"),
        head=a(cur, sec["href"], "<span>{}</span>{}".format(esc(sec["label"]), icon("arrow")), "nav-hub-link", here),
        groups=groups("p"))
    return desktop, mobile


def section_pager(cur):
    """Previous / next through the section in menu order (design/ia.json): the book navigation a hub implies."""
    sec = section_of(cur)
    if not sec or cur == sec["href"]:
        return ""
    order = section_order(sec)
    if cur not in order:
        return ""
    i = order.index(cur)
    prev_p = order[i - 1] if i > 0 else sec["href"]
    next_p = order[i + 1] if i + 1 < len(order) else None

    def card(target, cls, label):
        if not target:
            return ""
        return ('<a class="{cls}" href="{u}" rel="{rel}"><span class="dir">{arrow}{label}</span>'
                '<span class="t">{t}</span></a>').format(cls=cls, u=rel(cur, target), rel=cls, arrow=icon("arrow"),
                                                         label=label, t=esc(TOPS[target]["label"] if target in TOPS else (
                    panel_label(sec, target) or page_title(target))))

    return ('<!-- book-style pager over the section menu (menu order from design/ia.json) -->'
            '<div class="article-nav section-pager">{}{}</div>').format(
        card(prev_p, "prev", "Previous"), card(next_p, "next", "Next"))


def absent_card(cur, cls="rail-absent"):
    """sidebar_note "Student Absent?" as a card holding the same pair as every other Student Absent? control
    (design/ia.json utility): the label opens Student Attendance, the number dials the Early Warning line."""
    return ('<div class="{c} on-dark"><span class="ring" aria-hidden="true">{pi}</span>'
            '{lab}<a class="absent-num" href="{telx}">{ph} <span class="absent-ext">(Ext. 1)</span></a></div>').format(
        c=cls, pi=icon("phone"), telx=TEL_EXT, ph=PHONE,
        lab=a(cur, UTIL_ABSENT["href"], '<span>Student Absent?</span>' + icon("arrow"), "absent-title"))


def rail(cur, extra="", after=""):
    """Rail (region sidebar_second): Student Absent?, Bell Schedule and School Calendar lead on every page, then any
    page extra (Latest News on articles), then the address block. A page never repeats itself here: Student
    Attendance has no Student Absent? card (its body is the call-out), Contact Us no address card."""
    absent = "" if cur == ATTENDANCE else absent_card(cur)
    links = []
    if cur != BELL_PATH:
        links.append(a(cur, BELL_PATH, '<span class="task-ico">{}</span><span>Bell Schedule</span>{}'.format(icon("clock"), icon("arrow"))))
    if cur != "/school-calendar":
        links.append(a(cur, "/school-calendar", '<span class="task-ico">{}</span><span>School Calendar</span>{}'.format(
            icon("calendar"), icon("arrow")), mark=False))
    contact = "" if cur == "/contact-us" else (
        '<section class="contact-card" aria-labelledby="contact-card-title"><h2 id="contact-card-title">Contact Us</h2>'
        '<address>{a1}<br>{a2}</address><ul>'
        '<li><span>Telephone:</span> <a href="{tel}">{pd}</a></li>'
        '<li><span>Early Warning:</span> <a href="{telx}">{pd} Ext. 1</a></li>'
        '<li><a href="mailto:{em}">{em}</a></li></ul></section>').format(
        a1=esc(ADDR1), a2=ADDR2_HTML, tel=TEL, pd=PHONE_DOTS, telx=TEL_EXT, em=EMAIL)
    return ('<!-- Rail: sidebar_note "Student Absent?" (sidebar_notes:block_2) + Bell Schedule + School Calendar + address_block -->\n'
            '<aside class="page-rail region region-sidebar-second">{extra}{absent}{links}{after}{contact}</aside>').format(
        extra=extra, absent=absent, links='<ul class="rail-links">{}</ul>'.format("".join("<li>{}</li>".format(x) for x in links)) if links else "",
        after=after, contact=contact)


def card_desc(c):
    """A card's line under its title: the page's first sentence (or the first under the linked heading)."""
    path, _, frag = c["href"].partition("#")
    target = canon(path) if is_internal(path) else path
    desc = section_sentence(target, frag) if target in BUILT else ""
    if desc and not frag and lead_is_subsection(target) and (c.get("title") or c.get("label")) != page_title(target):
        desc = page_title(target)      # Bell Schedule: its first sentence belongs to a sub-section (PLT)
    return desc


def keep_dash(t):
    """A spaced hyphen stays on the line of the word before it (no line starts with '-'): a no-break space only."""
    return t.replace(" - ", "\u00a0- ")


def child_cards(cur, children, heading_tag="h3", numbered=False, start=1, cls=""):
    """Rich cards (title, the page's first sentence, arrow) for a list of {"title", "href"}. A list of title-only
    cards is compact (title and arrow on one row); in a list that mixes both, every card keeps one shape (title on
    top, arrow on the bottom edge), so the cards of a row line up."""
    lis = []
    descs = [card_desc(c) for c in children]
    all_bare = not any(descs)
    for (i, c), desc in zip(enumerate(children, start), descs):
        href = c["href"]
        url, ext = resolve(cur, href)
        go = icon("cal-plus") if href.startswith("webcal:") else icon("arrow")
        lis.append('<li><a class="hub-card{b}" href="{u}">{num}<{h}>{t}{x}</{h}>{d}'
                   '<span class="go" aria-hidden="true">{go}</span></a></li>'.format(
                       b=" hub-card--bare" if all_bare else "", u=esc(url), num='<span class="num" aria-hidden="true">{:02d}</span>'.format(i) if numbered else "",
                       h=heading_tag, t=keep_dash(nowrap_ranges(esc(c["title"]))), x=EXT if ext else "",
                       d="<p>{}</p>".format("".join('<span class="ln">{}</span>'.format(esc(x)) for x in desc.split(LINE))
                                            if LINE in desc else esc(desc)) if desc else "",
                       go=go))
    return '<ul class="hub-cards{}">{}</ul>'.format(" " + cls if cls else "", "".join(lis))


def section_sentence(path, frag=""):
    """A card's line: the page's first sentence, or for a deep link the first sentence under that heading."""
    body = (PAGES.get(path) or {}).get("body", "")
    if frag:
        root = parse(body)
        for h in root.iter():
            if re.match(r"^h[2-6]$", h.tag) and slug(h.text()) == frag and h.parent is not None:
                sibs = h.parent.children[h.parent.children.index(h) + 1:]
                part = []
                for x in sibs:
                    if isinstance(x, El) and re.match(r"^h[2-6]$", x.tag) and int(x.tag[1]) <= int(h.tag[1]):
                        break
                    part.append(serialize(x))
                return first_sentence("".join(part), br=LINE)
    return first_sentence(body, br=LINE)


def lead_is_subsection(path):
    """True when a page's first sentence sits under one of its own sub-headings (the body leads with an image or a
    table), so that sentence speaks for the sub-section, not for the page."""
    for el in parse((PAGES.get(path) or {}).get("body", "")).iter():
        if re.match(r"^h[2-6]$", el.tag):
            return True
        if el.tag in ("p", "li") and len(norm_ws(el.text())) >= 50:
            return False
    return False


def hub_label(href, cur=None):
    """A hub card's label: the menu label of the same link (in this hub's own panel first), else the page title (for
    the PDF page: its link text)."""
    return (panel_label(TOPS.get(cur), href) or MENU_LABEL.get(href) or page_title(canon(bare(href))) or href)


def tiled_urls(body_html):
    """URLs the page body already shows as tiles (Extra-Curricular's feature tiles), so the hub does not repeat them."""
    out = set()
    for tag in re.findall(r"<a\b[^>]*>", body_html):
        if re.search(r'class="[^"]*\b(feature-tile|launch-tile|link-tile|btn-subscribe)\b', tag):
            m = re.search(r'href="([^"]+)"', tag)
            if m:
                out.add(html.unescape(m.group(1)))
    return out


# A page with no image of its own shows the image its section page already links it with (Biblio Bites: the
# Newsletter icon in Newsletter Archive; Club Directory: the Clubs image on Extra-Curricular); Q & A gets its own
# arch icon well.
TILE_IMAGE = {"/library/biblio-bites": "c112f9fb0d63.png", "/extra-curricular/club-directory": "a2df4487b35d.png"}
TILE_ICON = {"/library/q-and-a": "help"}


def photo_tile(cur, href, label, heading_tag):
    """A hub card for the Library: the page's own first image (icons shown whole), or an arch icon well."""
    path = canon(bare(href))
    name = first_image(path) or TILE_IMAGE.get(path)
    url, ext = resolve(cur, href)
    if name:
        src, w, h = img_src(cur, name)
        is_icon = name.endswith(".png") and (w or 0) <= 600
        media = '<img src="{}" alt="" width="{}" height="{}" loading="lazy" decoding="async">'.format(src, w, h)
    else:
        is_icon = True
        media = '<span class="tile-ico">{}</span>'.format(icon(TILE_ICON.get(path, "paper")))
    return ('<li><a class="photo-tile{c}" href="{u}"><span class="photo-tile-img">{m}</span>'
            '<{h} class="photo-tile-title">{t}</{h}>{go}</a></li>').format(
        c=" is-icon" if is_icon else "", u=esc(url), m=media, h=heading_tag, t=esc(label),
        go=icon("ext" if ext else "arrow", "icon tile-go"))


def hub_sections(cur, body_html=""):
    """Hub page sections (design/ia.json "hubs"): the main-menu subtree on the section hubs, the "hub links" menu on
    the small ones, both through one card template, so hub and menu cannot drift apart. Self-links are dropped, and
    so are links the body already shows as tiles. A labelled group gets its live heading (h2, a link when the menu
    item links); the cards of an unlabelled group are h2 themselves, so no heading level is skipped."""
    spec = HUBS.get(cur)
    if not spec:
        return ""
    shown = tiled_urls(body_html)
    skip = {unrel(cur, u) for u in shown} | {u for u in shown if u.startswith("webcal:")}
    is_top = cur in TOPS
    library = cur == "/library"
    out, n = [], 1
    for gi, sec in enumerate(spec["sections"]):
        links = [h for h in sec["links"] if not ("#" not in h and is_internal(h) and canon(h) == cur)
                 and not (is_internal(h) and "#" not in h and canon(h) in skip) and h not in skip]
        if not links:
            continue
        heading = sec.get("heading")
        tag = "h3" if heading else "h2"
        featured = is_top and gi == 0
        gid = "hub-{}".format(slug(heading)) if heading else ""
        if heading:
            inner = a(cur, sec["href"], "<span>{}</span>{}".format(esc(heading), icon("arrow"))) if sec.get("href") else esc(heading)
            title = '<h2 class="hub-group-title" id="{}">{}</h2>'.format(gid, inner)
        else:
            title = ""
        if library:
            cards = '<ul class="photo-tiles">{}</ul>'.format("".join(photo_tile(cur, h, hub_label(h, cur), tag) for h in links))
        else:
            cards = child_cards(cur, [{"title": hub_label(h, cur), "href": h} for h in links], tag, False, n,
                                "hub-cards--featured" if featured else "")
        n += len(links)
        out.append('<{el} class="hub-group{f}"{lab}>{title}{cards}</{el}>'.format(
            el="section" if heading else "div", f=" hub-group--featured" if featured else "",
            lab=' aria-labelledby="{}"'.format(gid) if heading else "", title=title, cards=cards))
    src = "menu block: main (the {} subtree)".format(TOPS[cur]["label"]) if is_top else "menu block: hub links"
    return '<!-- {} as cards, grouped as in design/ia.json -->\n<div class="hub-sections">{}</div>'.format(src, "".join(out))


def body_class(path, extra=""):
    bc = (PAGES.get(path) or {}).get("bodyClass", "")
    return (bc + " " + extra).strip()


# ---------------------------------------------------------------------------------------------- templates
def render_page(path):
    """Basic page (node page full; DS layouts full_content_*): title hero, section menu, body, hub sections or child
    pages, section pager, rail. A section hub (Parents, Students, About Us ...) is its own menu: no sidebar."""
    p = PAGES[path]
    title = page_title(path)
    sec = section_of(path)
    eyebrow = sec["label"] if sec and sec["href"] != path else ""
    desktop_nav, mobile_nav = ("", "") if path in TOPS else section_nav(path)
    body = transform_body(path, p.get("body", ""), title)
    kids = [c for c in (p.get("children") or []) if c.get("href") and c["href"] != path]
    kids_html = hub_sections(path, body) if path in HUBS else ""
    if kids_html:
        pass
    elif kids:
        kids_html = '<section class="child-pages" aria-labelledby="child-title"><h2 id="child-title" class="vh">{}</h2>{}</section>'.format(
            esc(title), child_cards(path, kids))
    elif not norm_ws(text_of(body)) and "<img" not in body and "<iframe" not in body:
        # an empty page: its sibling pages as photo tiles, so it is never a dead end
        parent = parent_path(path)
        sibs = [x for x in url_children(parent) if x != path]
        if sibs:
            kids_html = '<section class="child-pages" aria-labelledby="child-title"><h2 id="child-title" class="vh">{}</h2>{}</section>'.format(
                esc(page_title(parent)), image_tiles(path, sibs))
    extra_js = []
    if "data-gallery" in body or "data-reel" in body:
        extra_js.append("gallery.js")
    if "data-filter" in body:
        extra_js.append("filter.js")
    extra_css = []
    if path == BELL_PATH:
        extra_js.append("bell.js")
        extra_css.append("views.css")
    grid_cls = "page-grid" if desktop_nav else "page-grid no-sidebar"
    prose = '<!-- field body (+ paragraphs) -->\n<div class="prose">{}</div>'.format(body) if norm_ws(text_of(body)) or "<img" in body else ""
    main = ('{hero}\n<div class="page-body"><div class="wrap {grid}">'
            '<article class="page-content{hub}">{prose}{kids}{pager}{mnav}</article>{side}'
            '{rail}</div></div>').format(hero=page_hero(path, title, eyebrow, compact=path not in HUBS and path not in TOPS),
                                          grid=grid_cls, side=desktop_nav,
                                          hub=" is-hub" if path in HUBS else "", mnav=mobile_nav, prose=prose,
                                          kids=kids_html, pager=section_pager(path), rail=rail(path))
    return shell(path, title, main, body_class(path), first_sentence(p.get("body", "")), extra_js=extra_js, extra_css=extra_css)


def built_articles():
    arts = [p for p, v in PAGES.items() if v["type"] == "article" and p in BUILT and p != "/news"]
    return sorted(arts, key=lambda p: (article_date(p) or date(1900, 1, 1), -NEWS_RANK.get(p, 10 ** 6), p))


def collection(path):
    return "news" if path.startswith("/news/") else "story"


def render_article(path):
    """Article (node article full, DS bs_2col): date, breadcrumb, body, Attachments, previous / next by date."""
    p = PAGES[path]
    title = page_title(path)
    d = article_date(path)
    sec = section_of(path)
    meta = ('<p class="hero-meta"><strong>Updated:</strong> <time datetime="{}">{}</time></p>'.format(d_iso(d), fmt_long(d))
            if d else "")
    body = transform_body(path, p.get("body", ""), title)
    same = [x for x in built_articles() if collection(x) == collection(path)]
    i = same.index(path)
    prev_p = same[i - 1] if i > 0 else None
    next_p = same[i + 1] if i + 1 < len(same) else None

    def nav_card(target, cls, label):
        if not target:
            return ""
        td = article_date(target)
        return ('<a class="{cls}" href="{u}" rel="{rel}"><span class="dir">{arrow}{label}</span>'
                '<span class="t">{t}</span>{time}</a>').format(
            cls=cls, u=rel(path, target), rel="prev" if cls == "prev" else "next", arrow=icon("arrow"), label=label,
            t=esc(page_title(target)), time='<time datetime="{}">{}</time>'.format(d_iso(td), fmt_long(td)) if td else "")

    pager = ""
    if prev_p or next_p:
        pager = '<nav class="article-nav" aria-labelledby="pager-title"><h2 class="vh" id="pager-title">{}</h2>{}{}</nav>'.format(
            esc(page_title("/news") if collection(path) == "news" else "School Learning Story"),
            nav_card(prev_p, "prev", "Previous"), nav_card(next_p, "next", "Next"))
    latest = [x for x in reversed(built_articles()) if collection(x) == "news" and x != path][:5]
    latest_html = ('<section class="rail-news" aria-labelledby="rail-news-title"><h2 id="rail-news-title">Latest News</h2><ul>{}</ul>'
                   '</section>').format("".join('<li><a href="{}">{}<span>{}</span></a></li>'.format(
                       rel(path, x), '<time datetime="{}">{}</time>'.format(d_iso(article_date(x)), fmt_short(article_date(x)))
                       if article_date(x) else "", esc(page_title(x))) for x in latest))
    if collection(path) == "news":
        back = [("/news", page_title("/news") or "News Archive"), ("/news/newsletters", "Newsletters")]
    else:
        back = [("/school-learning-story", "School Learning Story")]
    side = ('<aside class="page-sidebar article-meta region region-sidebar-first">{chip}<ul class="article-back">{links}</ul></aside>').format(
        chip=('<time class="date-chip date-chip--lg" datetime="{iso}"><span class="m">{m}</span><span class="n">{n}</span>'
              '<span class="d">{w}</span><span class="y">{y}</span></time>').format(
            iso=d_iso(d), m=MONTHS[d.month - 1], n=d.day, w=DAYS[d.weekday()], y=d.year) if d else "",
        links="".join("<li>{}</li>".format(a(path, h, "<span>{}</span>{}".format(esc(t), icon("arrow")), "arrow-link"))
                      for h, t in back))
    main = ('{hero}\n<div class="page-body"><div class="wrap page-grid">'
            '<article class="page-content"><!-- field body + field attachments (media file) -->\n<div class="prose">{body}</div>{pager}'
            '<!-- Latest News under the article, not in the rail: a short story leaves no empty band under it -->{latest}</article>{side}'
            '{rail}</div></div>').format(hero=page_hero(path, title, sec["label"] if sec else "", meta, compact=True), side=side, body=body,
                                         pager=pager, latest=latest_html, rail=rail(path))
    return shell(path, title, main, body_class(path), first_sentence(p.get("body", "")))


def teaser_text(t):
    """A teaser read from the live listing (Drupal trims it mid-phrase): an ellipsis says it goes on. Punctuation only,
    so no new words."""
    t = norm_ws(t)
    return t + "\u2026" if t and t[-1] not in ".!?\u2026:)\"\u201d\u2019" else t


def news_row(cur, item):
    d = article_date(item["href"])
    um = url_month(item["href"])
    url, ext = resolve(cur, item["href"])
    if d:
        chip = date_chip(d)
    elif um:
        chip = '<span class="date-chip"><span class="m">{}</span><span class="n" style="font-size:1.1rem">{}</span></span>'.format(
            MONTHS[um[1] - 1], um[0])
    else:
        chip = '<span class="date-chip"></span>'
    teaser = teaser_text(item.get("teaser"))
    return ('<li class="row">{chip}<div><h3><a href="{u}">{t}</a>{x}</h3>{p}</div></li>').format(
        chip=chip, u=esc(url), t=esc(clean_title(item["title"])), x=EXT if ext else "",
        p="<p>{}</p>".format(esc(teaser)) if teaser else "")


def month_key(item):
    d = article_date(item["href"])
    if d:
        return (d.year, d.month)
    return url_month(item["href"]) or (1900, 1)


def grouped(items):
    groups = []
    for it in sorted(items, key=news_sort_key, reverse=True):
        k = month_key(it)
        if not groups or groups[-1][0] != k:
            groups.append((k, []))
        groups[-1][1].append(it)
    return groups


def news_card(cur, item, posted=True):
    d = article_date(item["href"])
    url, ext = resolve(cur, item["href"])
    t = clean_title(item["title"])
    weekly = t.lower().startswith("striker weekly")
    meta = '<p class="meta"><span>Posted:</span> <time datetime="{}">{}</time></p>'.format(d_iso(d), fmt_short(d)) if (d and posted) else ""
    teaser = teaser_text(item.get("teaser"))
    return ('<li class="news-card{w}">{meta}<h3><a href="{u}">{t}</a>{x}</h3>{p}</li>').format(
        w=" news-card--weekly" if weekly else "", meta=meta, u=esc(url), t=esc(t), x=EXT if ext else "",
        p="<p>{}</p>".format(esc(teaser)) if (teaser and not weekly) else "")


def render_listing(path):
    """Listings: Newsletters (paragraph article_feed → EVA article_feed) and School Learning Story (its posts)."""
    p = PAGES[path]
    title = page_title(path)
    if path == "/news/newsletters":
        items = [n for n in NEWS if n.get("newsletter")]
        listed = {n["href"] for n in items}
        items += [NEWS_BY_HREF[h] for h in p.get("items") or [] if h in NEWS_BY_HREF and h not in listed]
        blocks = "".join('<section class="month" aria-labelledby="m-{y}-{m:02d}" data-pager-group><h2 class="month-title" id="m-{y}-{m:02d}">{label}</h2>'
                         '<ul class="card-grid">{cards}</ul></section>'.format(
                             y=y, m=m, label="{} {}".format(MONTHS_LONG[m - 1], y) if y > 1900 else "",
                             cards="".join(news_card(path, it).replace('<li class="news-card', '<li data-pager-item class="news-card', 1)
                                           for it in its)) for (y, m), its in grouped(items))
        blocks = '<div class="paged" data-pager data-pager-size="24" tabindex="-1" aria-labelledby="page-title">{}{}{}</div>'.format(
            pager_tools(title, len(items), filters=False), blocks, pager_nav())
    else:
        items = [NEWS_BY_HREF.get(h) or {"href": h, "title": page_title(h), "teaser": first_sentence(PAGES.get(h, {}).get("body", ""))}
                 for h in p.get("items") or []]
        blocks = '<ul class="card-grid">{}</ul>'.format("".join(news_card(path, it) for it in items))
    desktop_nav, mobile_nav = section_nav(path)
    sec = section_of(path)
    grid = "page-grid" if desktop_nav else "page-grid no-sidebar"
    main = ('{hero}\n<div class="page-body"><div class="wrap {grid}"><div class="page-content">'
            '<!-- view article_feed (EVA) / listing -->\n{blocks}{pager}{mnav}</div>{side}{rail}</div></div>').format(pager=section_pager(path),
        hero=page_hero(path, title, sec["label"] if sec and sec["href"] != path else "", compact=True), grid=grid, side=desktop_nav,
        mnav=mobile_nav, blocks=blocks, rail=rail(path))
    paged = "data-pager" in blocks
    return shell(path, title, main, body_class(path), extra_js=["pager.js"] if paged else [],
                 extra_css=["views.css"] if paged else [])


# ---------------------------------------------------------------------------------------------- front page
def today_parts(cur):
    """Everything the Today card shows for the build date; mirrors theme/js/today.js."""
    day = school_day(TODAY)
    info = {"day": day}
    if day:
        code = CODES[day]
        rot = rotation_for(day)
        col = bell_col(day, code)
        info.update(code=code, rot=rot, rows=(BELL["rotations"].get(rot) or {}).get(col, []) if rot else [])
    evs = real_events(TODAY)
    info["events"] = evs
    return info


def blocks_html(rows):
    out = []
    for rng, label in rows:
        cls = ' class="is-plt"' if label == "PLT" else ' class="is-lunch"' if label == "Lunch" else ' class="is-collab"' if "Collab" in label else ""
        blk = ' data-blk="{}"'.format(label.lower()) if label in ("A", "B", "C", "D") else ""
        out.append('<li style="--m:{}"{}{}><b>{}</b><time>{}</time></li>'.format(minutes(rng), cls, blk, esc(label), esc(rng)))
    return "".join(out)


def week_html(day):
    monday = day - timedelta(days=day.weekday())
    out = []
    for i in range(5):
        d = monday + timedelta(days=i)
        c = CODES.get(d, "")
        cls = []
        if d == TODAY:
            cls.append("is-today")
            if day != TODAY:
                cls.append("is-quiet")      # the card shows a later day: today keeps its tag, in outline only
        elif d < TODAY:
            cls.append("is-past")
        if d == day and d != TODAY:
            cls.append("is-shown")          # the day whose blocks the card shows
        if not c:
            cls.append("is-off")
        out.append('<li{cls}{cur}>{tag}<span class="d">{dd}</span><span class="n">{n}</span><span class="c">{c}</span></li>'.format(
            cls=' class="{}"'.format(" ".join(cls)) if cls else "", cur=' aria-current="date"' if d == TODAY else "",
            tag='<span class="tag-today">Today</span>' if d == TODAY else "", dd=DAYS[d.weekday()], n=d.day, c=esc(c)))
    return "".join(out)


def collab_html():
    """Collaboration Days: a past day is struck through in the markup (<s>), the next one highlighted (a class only:
    it is not today, so it carries no aria-current). Mirrors js/today.js and js/bell.js."""
    out, next_set = [], False
    for d, label in COLLAB_DAYS:
        cls, past = "", bool(d and d < TODAY)
        if past:
            cls = ' class="is-past"'
        elif d and not next_set:
            cls = ' class="is-next"'
            next_set = True
        t = '<time datetime="{}">{}</time>'.format(d_iso(d) if d else "", esc(label))
        out.append('<li{}>{}</li>'.format(cls, "<s>{}</s>".format(t) if past else t))
    return "".join(out)


def event_item(cur, e):
    url, ext = resolve(cur, event_href(e))
    return ('<li class="event{ns}"><a href="{u}">{chip}<span class="title"><span>{t}</span>{x}{tag}</span></a></li>').format(
        ns=" event--noschool" if is_no_school(e["t"]) else "", u=esc(url), chip=date_chip(e["d"]),
        t=esc(smart_case(e["t"])), x=EXT if ext else "", tag=noschool_tag(e["t"]))


def today_data(cur, info):
    end = TODAY + timedelta(days=400)
    evs = []
    for e in real_events(TODAY):
        if e["d"] > end:
            break
        url, ext = resolve(cur, event_href(e))
        evs.append({"d": d_iso(e["d"]), "t": smart_case(e["t"]), "u": url, "x": 1 if ext else 0, "o": 1 if is_no_school(e["t"]) else 0})
    data = {
        "built": d_iso(TODAY),
        "labels": LABELS,
        "codes": {d_iso(d): c for d, c in sorted(CODES.items()) if d >= TODAY - timedelta(days=7)},
        "rotations": [{"name": r["name"], "from": d_iso(r["from"]), "to": d_iso(r["to"])} for r in ROTATIONS if r["from"] and r["to"]],
        "bell": BELL["rotations"],
        "collab": [{"d": d_iso(d), "t": t} for d, t in COLLAB_DAYS if d],
        "events": evs,
        "n": 8,
    }
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def render_home():
    cur = "/"
    info = today_parts(cur)
    day = info["day"]
    evs = info["events"]
    hero_src, hw, hh = img_src(cur, HEADER_IMG)
    bell_url, _ = resolve(cur, BELL_PATH)
    cal_url, cal_ext = resolve(cur, "/school-calendar")
    weekly = WEEKLIES[0] if WEEKLIES else None
    first = evs[0] if evs else None

    # --- hero
    hero = ('<!-- region top_header: view site_header_content_block (name, slogan); the photo keeps #header-img-area for'
            ' bg_image_formatter, here as a real <img> so the browser finds it early -->\n'
            '<section class="hero"><div class="wrap"><div class="hero-text">'
            '<h1><span class="h1-pre">École Secondaire</span><span class="h1-main">Hugh McRoberts</span>'
            '<span class="h1-post">Secondary School</span></h1>'
            '<p class="slogan">Learning Together… <em>Achieving Our Dreams</em></p>'
            '<p class="hero-lead">McRoberts Secondary is a dual-track school offering both English and French Immersion programs.</p>'
            '</div><figure class="hero-media"><span class="arch-keyline" aria-hidden="true"></span>'
            '<span class="arch-year" aria-hidden="true">1962</span><div class="arch">'
            '<img src="{src}" alt="" width="{w}" height="{h}" fetchpriority="high" decoding="async"></div>'
            '<figcaption class="arch-caption">{pin}<span>{a1}</span><span>Richmond, BC</span></figcaption></figure>'
            '</div></section>').format(src=hero_src, w=hw, h=hh, pin=icon("pin"), a1=esc(ADDR1))

    # --- Today card
    if day:
        chips = ('<li class="chip">{}</li>'.format(esc(info["rot"])) if info.get("rot") else "") + \
                '<li class="chip chip--forest">{}</li>'.format(esc(info["code"]))
        eyebrow = "Today" if day == TODAY else ""        # the next school day: its date says so, no eyebrow
        next_line = ""
        if first:
            nu, nx = resolve(cur, event_href(first))
            next_line = ('<a class="next" href="{u}" data-t="next"><span class="lbl">Next</span>'
                         '<time datetime="{iso}">{d}</time><span class="t">{t}{x}</span>{arrow}</a>').format(
                u=esc(nu), t=esc(smart_case(first["t"])), x="", iso=d_iso(first["d"]),
                d=fmt_short(first["d"]), arrow=icon("ext" if nx else "arrow"))
        today = ('<!-- Today: view upcoming_events (date contextual filter = today → the rotation code) + custom block'
                 ' (timetable from the bell schedule); refreshed in the browser by js/today.js -->\n'
                 '<section class="today region region-sidebar-first" id="today" aria-labelledby="today-title">'
                 '<div class="today-head"><p class="eyebrow{ebh}" data-t="eyebrow">{eb}</p>'
                 '<h2 id="today-title"><a href="{bell}">Bell Schedule</a></h2>'
                 '<time class="today-date" datetime="{iso}" data-t="date">{date}</time>'
                 '<ul class="chips" data-t="chips">{chips}</ul></div>'
                 '{next}'
                 '<div class="today-absent"><span class="dot" aria-hidden="true">{pi}</span>{lab}'
                 '<a class="num" href="{telx}">{ph} (Ext. 1)</a></div>'
                 '<ol class="blocks" data-t="blocks">{blocks}</ol>'
                 '<ol class="week" data-t="week">{week}</ol>'
                 '<div class="collab"><p class="collab-title">{ct}</p><ol data-t="collab">{collab}</ol></div>'
                 '</section>').format(
            eb=eyebrow or "Today", ebh="" if eyebrow else " is-empty", bell=esc(bell_url), iso=d_iso(day), date=fmt_day_long(day), chips=chips, next=next_line,
            telx=TEL_EXT, pi=icon("phone"), ph=PHONE, blocks=blocks_html(info["rows"]), week=week_html(day),
            lab=a(cur, UTIL_ABSENT["href"], "<span>Student Absent?</span>" + icon("arrow"), "lbl"),
            ct=esc(BELL["collaborationDaysTitle"].rstrip(":")), collab=collab_html())
    else:
        today = ""

    # --- Helpful Links tiles (≤ 8): live sub-lines where the data exists
    def tile(href, ico, label, sub, live_key=None, ext_icon=False):
        url, ext = resolve(cur, href)
        subhtml = ('<span class="live" data-t="{}">{}</span>'.format(live_key, sub) if live_key
                   else '<span class="sub">{}</span>'.format(sub))
        return ('<li><a class="task" href="{u}"><span class="task-ico">{i}</span><span class="task-label"><strong>{l}</strong>'
                '{s}</span>{go}</a></li>').format(u=esc(url), i=icon(ico), l=esc(label), s=subhtml,
                                                  go=icon("ext" if (ext_icon or ext) else "arrow", "icon task-go"))

    bell_sub = (('<span>{}</span> · '.format(esc(info["rot"])) if info.get("rot") else "") +
                '<span>{}</span>'.format(esc(info["code"]))) if day else "Timetable Structure 2026-2027"
    cal_sub = ('<span>{}</span> · <time datetime="{}">{} {}</time>'.format(
        esc(smart_case(first["t"])), d_iso(first["d"]), MONTHS[first["d"].month - 1], first["d"].day)
        if first else "Upcoming Events")
    tiles = [
        # the same pair as the utility bar: the label opens Student Attendance, the number dials (ia.md, task 1)
        '<li class="is-featured"><div class="task task--absent on-dark"><span class="task-ico" aria-hidden="true">{pi}</span>'
        '<span class="absent-body">{lab}<a class="absent-num" href="{telx}">{ph} <span class="absent-ext">(Ext. 1)</span></a></span></div></li>'.format(
            telx=TEL_EXT, pi=icon("phone"), ph=PHONE,
            lab=a(cur, UTIL_ABSENT["href"], "<span>Student Absent?</span>" + icon("arrow"), "absent-title")),
        tile("/school-calendar", "calendar", "School Calendar", cal_sub, "tile-calendar"),
        tile(BELL_PATH, "clock", "Bell Schedule", bell_sub, "tile-bell"),
    ]
    if weekly:
        tiles.append(tile(weekly["href"], "paper", "Striker Weekly", esc(weekly_range(weekly)), "tile-weekly"))
    ql = dict((n, h) for n, h in quick_links())
    tiles.append(tile(ql.get("MyEducation BC", "https://myeducation.gov.bc.ca/aspen/logon.do"), "cap", "MyEducation BC",
                      "<span>Parents</span> · <span>Students</span>", ext_icon=True))
    tiles.append(tile(ql.get("School Cash Online", "https://schoolcashonline.com/"), "wallet", "School Cash Online", "Parents", ext_icon=True))
    tiles.append(tile("https://portal.office.com", "apps", "Office 365", "Students", ext_icon=True))
    tasks = ('<!-- Front page sidebar_second: sidebar_notes:block_2 (Student Absent?), district_quick_links, home_page_buttons -->\n'
             '<section class="tasks region region-sidebar-second" aria-labelledby="tasks-title"><h2 class="eyebrow tasks-title" id="tasks-title">Helpful Links</h2>'
             '<ul class="task-grid">{}</ul></section>').format("".join(tiles))
    front_top = '<div class="front-top"><div class="wrap front-top-grid">{}{}</div></div>'.format(today, tasks)

    # --- Latest News + Striker Weekly
    front = [h for h in SITE.get("frontNews", []) if not clean_title((NEWS_BY_HREF.get(h) or {}).get("title", page_title(h))).lower().startswith("striker weekly")]
    items = [NEWS_BY_HREF.get(h) or {"href": h, "title": page_title(h), "teaser": first_sentence(PAGES.get(h, {}).get("body", ""))} for h in front]
    items.sort(key=news_sort_key, reverse=True)     # the dates shown run in order, as on the archive, rail and pager
    lead, cards, rows = (items[0] if items else None), items[1:3], items[3:7]
    news_html = ""
    if lead:
        ld = article_date(lead["href"])
        lurl, lext = resolve(cur, lead["href"])
        lead_teaser = teaser_text(lead.get("teaser") or first_sentence(PAGES.get(lead["href"], {}).get("body", ""), 400))
        feature = ('<article class="story-feature"><div class="meta">{time}</div><h3 id="feature-title"><a href="{u}">{t}</a></h3>'
                   '<p>{p}</p><a class="arrow-link" href="{u}"><span id="feature-more">Read more</span><span class="vh">: {t}</span>{arrow}</a>'
                   '</article>').format(
            time='<time datetime="{}">{}</time>'.format(d_iso(ld), fmt_long(ld)) if ld else "", u=esc(lurl),
            t=esc(clean_title(lead["title"])), p=esc(lead_teaser), arrow=icon("arrow"))
        card_html = "".join(
            '<li class="story-card">{chip}<div><h3><a href="{u}">{t}</a></h3><p>{p}</p></div></li>'.format(
                chip=date_chip(article_date(c["href"])) if article_date(c["href"]) else '<span class="date-chip"></span>',
                u=esc(resolve(cur, c["href"])[0]), t=esc(clean_title(c["title"])), p=esc(teaser_text(c.get("teaser"))))
            for c in cards)
        row_html = "".join(
            '<li class="story">{date}<div><h3><a href="{u}">{t}</a></h3></div></li>'.format(
                date=('<time class="date" datetime="{}"><span class="m">{}</span><span class="n">{}</span></time>'.format(
                    d_iso(article_date(r["href"])), MONTHS[article_date(r["href"]).month - 1], article_date(r["href"]).day)
                      if article_date(r["href"]) else '<span class="date"></span>'),
                u=esc(resolve(cur, r["href"])[0]), t=esc(clean_title(r["title"]))) for r in rows)
        weekly_html = ""
        if weekly:
            wurl, _ = resolve(cur, weekly["href"])
            wd = article_date(weekly["href"])
            past = "".join('<li><a href="{}">{}{}</a></li>'.format(esc(resolve(cur, w["href"])[0]), esc(clean_title(w["title"])), icon("arrow"))
                           for w in WEEKLIES[1:3])
            weekly_html = ('<aside class="news-side" aria-labelledby="weekly-title"><div class="weekly"><div class="weekly-plate">'
                           '<span class="tag">Newsletters</span><h3 class="weekly-name" id="weekly-title">Striker Weekly</h3>'
                           '<span class="weekly-sub">a Week at a Glance for Parents</span></div><div class="weekly-issue">'
                           '<time class="range" id="weekly-range"{dt}>{range}</time><p>{teaser}</p>'
                           '<a class="btn btn-solid" href="{u}"><span id="weekly-more">Read more</span><span class="vh">: Striker Weekly {range}</span>{arrow}</a>'
                           '</div><ul class="weekly-past">{past}</ul><div class="weekly-foot">{nl}</div></div></aside>').format(
                dt=' datetime="{}"'.format(d_iso(wd)) if wd else "", range=esc(weekly_range(weekly)),
                teaser=esc(teaser_text(weekly.get("teaser"))), u=esc(wurl), arrow=icon("arrow", "icon icon-sm"), past=past,
                nl=a(cur, "/news/newsletters", "<span>Newsletters</span>" + icon("arrow"), "arrow-link"))
        news_html = ('<!-- content → view frontpage (Latest News, 10 rows); Striker Weekly from the newsletters feed -->\n'
                     '<section class="news" aria-labelledby="news-title"><div class="wrap"><div class="section-head"><div>'
                     '<p class="eyebrow">News</p><h2 id="news-title">Latest News</h2></div>{archive}</div>'
                     '<div class="news-grid"><div class="news-main">{feature}<ul class="story-cards">{cards}</ul>'
                     '<ul class="story-list">{rows}</ul></div>{weekly}</div></div></section>').format(
            archive=a(cur, "/news", "<span>News Archive</span>" + icon("arrow"), "arrow-link"), feature=feature,
            cards=card_html, rows=row_html, weekly=weekly_html)

    # --- Upcoming Events
    events_html = ('<!-- sidebar_first → view upcoming_events (block_1): the next real events, rotation codes'
                   ' (ABCD, BADC, PLT Rot n, COLLAB) excluded -->\n'
                   '<section class="events on-dark region region-sidebar-first" id="block-views-block-upcoming-events-block-1" aria-labelledby="events-title"><div class="wrap"><div class="section-head">'
                   '<div><p class="eyebrow">School Calendar</p><h2 id="events-title">Upcoming Events</h2></div>'
                   '<div class="events-actions"><a class="btn btn-ghost" href="webcal://mcroberts.sd38.bc.ca/calendar-feed.ics">{cp}Subscribe to our calendar</a>'
                   '{cal}</div></div><ul class="event-grid" data-t="events">{items}</ul></div></section>').format(
        cp=icon("cal-plus", "icon icon-sm"), cal=a(cur, "/school-calendar", "<span>School Calendar</span>" + icon("arrow"), "arrow-link"),
        items="".join(event_item(cur, e) for e in evs[:8]))

    # --- Parents and Students hubs (design/ia.json hubs["/"]: the home task band)
    def hub(sec, ico):
        hid = "hub-" + slug(sec["heading"])
        links = "".join("<li>{}</li>".format(a(cur, h, "<span>{}</span>{}".format(esc(hub_label(h)), menu_icon(h))))
                        for h in sec["links"])
        return ('<section class="hub" aria-labelledby="{hid}"><div class="hub-head"><span class="hub-ico" aria-hidden="true">{i}</span>'
                '<h2 id="{hid}">{t}</h2></div><ul class="hub-links" style="--rows:{rows}">{links}</ul></section>').format(
            hid=hid, i=icon(ico), t=a(cur, sec["href"], esc(sec["heading"]) + icon("arrow")), links=links,
            rows=(len(sec["links"]) + 1) // 2)

    band = HUBS.get("/", {}).get("sections", [])
    hubs = ('<!-- menu block "hub links" (design/ia.json hubs["/"]): the Parents and Students task lists -->\n'
            '<div class="hubs"><div class="wrap hub-pair">{}</div></div>').format(
        "".join(hub(sec, "family" if i == 0 else "cap") for i, sec in enumerate(band)))

    # --- About Us + Mission Statement
    bsrc, bw, bh = img_src(cur, BUILDING)
    about = ('<!-- Heritage: About Us copy (node /about-us) + Mission Statement (child page) -->\n'
             '<section class="about" aria-labelledby="about-title"><div class="wrap"><div class="about-grid"><div class="about-text">'
             '<p class="eyebrow">About Us</p><h2 class="about-statement" id="about-title">McRoberts has a long and well-established tradition of '
             '<em>student achievement and academic excellence, athletics and community involvement.</em></h2>'
             '<ul class="facts"><li><span class="fact-num">1962</span><p>The school first opened in November 1962</p></li>'
             '<li><span class="fact-num">8–12</span><p>over 1000 students in Grades 8 to 12</p></li>'
             '<li><span class="fact-num"><em>École</em></span><p>English and French Immersion programs</p></li></ul>'
             '<div class="about-links">{l1}{l2}{l3}</div></div>'
             '<figure class="about-media"><span class="arch-keyline" aria-hidden="true"></span><div class="arch">'
             '<img src="{bsrc}" alt="" width="{bw}" height="{bh}" loading="lazy" decoding="async"></div>'
             '<figcaption>McRoberts is a bilingual school where staff, students, and parents learn together in an environment of trust, support, and mutual respect.</figcaption>'
             '</figure></div>'
             '<figure class="mission"><figcaption class="eyebrow" id="mission-title">Mission Statement</figcaption>'
             '<blockquote><p>Our purpose is to enable all learners to develop their potential, prepare for the future, and achieve their dreams.</p></blockquote>'
             '{ml}</figure></div></section>').format(
        l1=a(cur, "/about-us", "<span>About Us</span>" + icon("arrow"), "arrow-link"),
        l2=a(cur, "/about-us/our-staff", "<span>Our Staff</span>" + icon("arrow"), "arrow-link"),
        l3=a(cur, "/about-us/catchment", "<span>Catchment</span>" + icon("arrow"), "arrow-link"),
        bsrc=bsrc, bw=bw, bh=bh,
        ml=a(cur, "/about-us/mission-statement",
             '<span id="mission-more">Read more</span><span class="vh">: Mission Statement</span>' + icon("arrow"), "arrow-link"))

    # --- Strikers band
    ssrc, sw, sh = img_src(cur, STRIKERS_LOGO)
    strikers = ('<!-- Extra-Curricular: nodes /extra-curricular/strikers-athletics (quote, provincial banners) and /club-directory -->\n'
                '<section class="strikers on-dark" aria-labelledby="strikers-title"><p class="strikers-word" aria-hidden="true">Strikers</p>'
                '<div class="wrap strikers-grid"><div class="strikers-logo"><img src="{src}" alt="" width="480" height="{h}" loading="lazy" decoding="async"></div>'
                '<div class="strikers-body"><p class="eyebrow">Strikers</p><h2 id="strikers-title">Extra-Curricular</h2>'
                '<blockquote class="strikers-quote"><p>As a Striker, you are expected to be committed to practicing and playing hard while always representing our school with '
                '<em>pride, sportsmanship, and class.</em></p></blockquote>'
                '<div class="strikers-links">{sa}{cd}</div></div></div>'
                '<div class="wrap banners-wrap"><p class="banners-cap">McRoberts has previously won provincial banners for field hockey, soccer, rugby, and curling.</p>'
                '<ul class="banners" aria-hidden="true"><li><span>field hockey</span></li><li><span>soccer</span></li>'
                '<li><span>rugby</span></li><li><span>curling</span></li></ul></div></section>').format(
        src=ssrc, h=round(480 * (sh or 1579) / (sw or 1600)),
        sa=a(cur, "/extra-curricular/strikers-athletics", "<strong>Strikers Athletics</strong><span>Learn more about our different athletic teams</span>" + icon("arrow"), "strikers-cta"),
        cd=a(cur, "/extra-curricular/club-directory", "<strong>Club Directory</strong><span>Learn more about our student-led clubs</span>" + icon("arrow"), "strikers-cta"))

    # --- Contact
    contact = ('<!-- block_content address_block (footer_fourth), given room on the front page -->\n'
               '<section class="contact" aria-labelledby="contact-title"><div class="wrap contact-grid"><div>'
               '<h2 id="contact-title">Contact Us</h2>'
               '<address class="contact-address"><a href="{map}">{pin}<span>{a1}<br>{a2h}</span></a></address></div>'
               '<ul class="contact-cards">'
               '<li><a href="{tel}"><span class="task-ico">{pi}</span><span class="lbl">Telephone:</span><span class="val">{pd}</span></a></li>'
               '<li><a href="{telx}"><span class="task-ico">{ci}</span><span class="lbl">Early Warning:</span><span class="val">{pd}<small>Ext. 1</small></span></a></li>'
               '<li><a href="mailto:{em}"><span class="task-ico">{mi}</span><span class="lbl">Email:</span><span class="val val--email">{emw}</span></a></li>'
               '</ul></div></section>').format(
        name=esc("École Secondaire Hugh McRoberts Secondary"), map=esc(SITE["mapHref"]), pin=icon("pin"), a1=esc(ADDR1),
        a2=esc(ADDR2), a2h=ADDR2_HTML, tel=TEL, telx=TEL_EXT, pi=icon("phone"), ci=icon("clock"), mi=icon("mail"), pd=PHONE_DOTS, em=EMAIL,
        emw=EMAIL)

    data = '<script type="application/json" id="today-data">{}</script>'.format(today_data(cur, info))
    main = "\n".join([hero, front_top, news_html, events_html, hubs, about, strikers, contact, data])
    return shell(cur, "", main, body_class("/", "path-frontpage"),
                 "McRoberts Secondary is a dual-track school offering both English and French Immersion programs.",
                 extra_js=["today.js"], preload=hero_src)


# ---------------------------------------------------------------------------------------------- calendar
WEBCAL = "webcal://mcroberts.sd38.bc.ca/calendar-feed.ics"


def json_script(id_, data):
    return '<script type="application/json" id="{}">{}</script>'.format(
        id_, json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))


def cal_days():
    """Calendar dates → {"codes": [rotation codes], "events": [titles]} (duplicates in the feed removed)."""
    days, seen = {}, set()
    for e in EVENTS:
        key = (e["t"].lower(), e["d"])
        if key in seen:
            continue
        seen.add(key)
        day = days.setdefault(e["d"], {"codes": [], "events": []})
        (day["codes"] if ROT_RE.match(e["t"]) else day["events"]).append(e["t"])
    return dict(sorted(days.items()))


CAL_DAYS = cal_days()


def event_link(cur, title, d, inner):
    href = EVENT_PAGES.get((title.lower(), d_iso(d)))
    return a(cur, href, inner) if (href and href != cur) else inner


def agenda_day(cur, d, info, today=None, ids=True):
    """One date of the agenda (view calendar, list display): arch date chip, the events, the rotation code."""
    codes, evs = info["codes"], info["events"]
    cls = ["aday"]
    code_only = bool(codes and not evs)
    if code_only and not (today and d == today):      # today always shows in full
        cls.append("is-code-only")
    if not codes and not evs:
        cls.append("is-empty")
    if any(is_no_school(t) for t in evs):
        cls.append("is-noschool")
    if d.weekday() >= 5:
        cls.append("is-weekend")
    if today and d < today:
        cls.append("is-past")
    if today and d == today:
        cls.append("is-today")
    items = "".join('<li class="ev{}">{}{}</li>'.format(
        " ev--noschool" if is_no_school(t) else "", event_link(cur, t, d, "<span>{}</span>".format(esc(smart_case(t)))),
        noschool_tag(t)) for t in evs)
    code_html = "".join('<span class="aday-code">{}</span>'.format(event_link(cur, c, d, esc(c))) for c in codes)
    tag = '<span class="tag-today">Today</span>' if (today and d == today) else ""
    return ('<li class="{cls}"{id} data-date="{iso}"{co}{cur}>{chip}<div class="aday-body">{tag}{evs}{codes}</div></li>').format(
        cls=" ".join(cls), id=' id="d-{}"'.format(d_iso(d)) if ids else "", iso=d_iso(d), co=" data-codes-only" if code_only else "",
        cur=' aria-current="date"' if (today and d == today) else "", chip=date_chip(d), tag=tag,
        evs='<ul class="aday-events">{}</ul>'.format(items) if items else "", codes=code_html)


def subscribe_btn(cls="btn btn-subscribe"):
    return '<a class="{}" href="{}">{}<span>Subscribe to our calendar</span></a>'.format(cls, WEBCAL, icon("cal-plus"))


def file_card(url, name, ext="pdf"):
    """A document card; the badge names the type in words only for document types (an image gets the paper icon)."""
    badge = ext if ext in FILE_EXTS else icon("paper")
    return ('<a class="file-card" href="{}"><span class="file-badge" data-ext="{e}" aria-hidden="true">{b}</span>'
            '<span class="file-name">{}</span>{}</a>').format(esc(url), esc(name), icon("download"), e=ext, b=badge)


def render_calendar(path):
    """Calendar page (node calendar_page + view calendar, fullcalendar_view display page_1). Server-rendered agenda
    (works without JS); js/calendar.js adds the month grid, refreshes today and remembers the view."""
    p = PAGES[path]
    title = page_title(path)
    root = parse(p.get("body", ""))
    uls = root.elements("ul")
    notes = "".join("<li>{}</li>".format(esc(norm_ws(li.text()))) for li in (uls[0].elements("li") if uls else []))
    print_p = next((norm_ws(x.text()) for x in root.elements("p") if "printable" in x.text()), "")
    pdf = uls[1].elements("a")[0] if len(uls) > 1 and uls[1].elements("a") else None
    days = dict(CAL_DAYS)
    first, last = min(days), max(days)
    if first <= TODAY <= last and TODAY not in days:
        days[TODAY] = {"codes": [], "events": []}
    months = []
    for d in sorted(days):
        k = (d.year, d.month)
        if not months or months[-1][0] != k:
            months.append((k, []))
        months[-1][1].append(d)
    chips, blocks = [], []
    prev_year = None
    # the filled chip is the month on screen (aria-current; js/calendar.js moves it with the list or the grid), the
    # outlined chip is this month
    shown = (TODAY.year, TODAY.month) if first <= TODAY <= last else (first.year, first.month)
    for (y, m), ds in months:
        mid = "m-{}-{:02d}".format(y, m)
        here = (y, m) == (TODAY.year, TODAY.month)
        chips.append('<li><a href="#{mid}" data-month="{y}-{m:02d}"{cls}{cur}><span>{mn}</span>{yr}</a></li>'.format(
            mid=mid, y=y, m=m, cls=' class="is-this-month"' if here else "", cur=' aria-current="true"' if (y, m) == shown else "",
            mn=MONTHS[m - 1], yr=" <small>{}</small>".format(y) if y != prev_year else ""))
        prev_year = y
        # with scripts on, the agenda shows this month and the next (js/calendar.js monthWindow); built folded, so
        # nothing moves when the script runs. Scripts off, every month shows.
        nxt = (TODAY.year + (TODAY.month == 12), TODAY.month % 12 + 1)
        past = " is-folded" if (first <= TODAY <= last and (y, m) not in ((TODAY.year, TODAY.month), nxt)) else ""
        blocks.append('<section class="cal-mblock{past}" id="{mid}" aria-labelledby="{mid}-t"><h2 class="month-title" id="{mid}-t">{label}</h2>'
                      '<ol class="agenda">{rows}</ol></section>'.format(
                          mid=mid, past=past, label="{} {}".format(MONTHS_LONG[m - 1], y),
                          rows="".join(agenda_day(path, d, days[d], TODAY) for d in ds)))
    data = {"built": d_iso(TODAY), "first": d_iso(first), "last": d_iso(last), "labels": LABELS,
            "ev": []}
    for d, info in CAL_DAYS.items():
        for t in info["events"]:
            href = EVENT_PAGES.get((t.lower(), d_iso(d)))
            data["ev"].append([d_iso(d), smart_case(t), 2 if is_no_school(t) else 0, rel(path, href) if href else ""])
        for c in info["codes"]:
            href = EVENT_PAGES.get((c.lower(), d_iso(d)))
            data["ev"].append([d_iso(d), c, 1, rel(path, href) if href else ""])
    # the calendar leads (the task is "when is the next day off?"); the body's Notes fold away under their own
    # label, the printable PDF and the hub links follow it
    intro = ('<!-- field body: Notes and the Monthly calendar pages (PDF), after the calendar -->\n'
             '<div class="cal-intro"><details class="cal-notes accordion"><summary>Notes:</summary><div class="accordion__body">'
             '<ul>{notes}</ul></div></details><div class="cal-print"><p>{pp}</p>{pdf}</div></div>').format(
        notes=notes, pp=esc(print_p), pdf=file_card(pdf.attrs["href"], norm_ws(pdf.text())) if pdf is not None else "")
    toolbar = ('<div class="cal-toolbar">'
               '<div class="seg cal-views needs-js" role="group" aria-label="{t}" data-cal-views>'
               '<button type="button" aria-pressed="true" data-view="list">{li}<span>list</span></button>'
               '<button type="button" aria-pressed="false" data-view="month">{gi}<span>month</span></button></div>'
               '<label class="switch"><input type="checkbox" role="switch" checked data-cal-codes><span class="switch-track" aria-hidden="true"></span>'
               '<span class="switch-label"><span>ABCD</span> <span>BADC</span> <span>PLT Rot</span> <span>COLLAB</span></span></label>'
               '<p class="cal-legend"><span class="sw" aria-hidden="true"></span><span class="tag-noschool">No School</span></p>'
               '{sub}</div>'
               '<nav class="cal-months" aria-label="{t}"><ul>{chips}</ul></nav>').format(
        t=esc(title), li=icon("list"), gi=icon("grid"), chips="".join(chips), sub=subscribe_btn("btn btn-subscribe cal-subscribe"))
    main = ('{hero}\n<div class="page-body"><div class="wrap page-grid no-sidebar"><div class="page-content cal" data-calendar>'
            '<!-- view calendar (fullcalendar_view): agenda = listYear, month grid = dayGridMonth; rotation codes'
            ' (ABCD, BADC, PLT Rot n, COLLAB) can be hidden -->\n{toolbar}'
            '<div class="cal-list" data-cal-list>{blocks}</div><div class="cal-grid" data-cal-grid hidden></div>{data}'
            '{intro}{hub}</div>'
            '{rail}</div></div>').format(hero=page_hero(path, title, compact=True), intro=intro,
                                         hub=hub_sections(path, toolbar), toolbar=toolbar, blocks="".join(blocks),
                                         data=json_script("cal-data", data), rail=rail(path))
    return shell(path, title, main, body_class(path), " ".join(norm_ws(li.text()) for li in (uls[0].elements("li")[:1] if uls else [])),
                 extra_js=["calendar.js"], extra_css=["views.css"])


def render_event(path):
    """Calendar event (node calendar_event full): field_event_date, plus that day's code, timetable and what comes next."""
    p = PAGES[path]
    raw_title = page_title(path)
    title = smart_case(raw_title)
    d = date.fromisoformat(p["date"][:10])
    t_el = parse(p.get("body", "")).elements("time")
    when = norm_ws(t_el[0].text()) if t_el else fmt_long(d)
    code = CODES.get(d)
    rot = rotation_for(d) if code else None
    rows = (BELL["rotations"].get(rot) or {}).get(bell_col(d, code), []) if rot else []
    chips = (('<li class="chip">{}</li>'.format(esc(rot)) if rot else "") +
             ('<li class="chip chip--forest">{}</li>'.format(esc(code)) if code else ""))
    noschool = is_no_school(raw_title)
    chip_lg = ('<time class="date-chip date-chip--lg" datetime="{iso}"><span class="m">{m}</span><span class="n">{n}</span>'
               '<span class="d">{w}</span><span class="y">{y}</span></time>').format(
        iso=d_iso(d), m=MONTHS[d.month - 1], n=d.day, w=DAYS[d.weekday()], y=d.year)
    bell_url = rel(path, BELL_PATH)
    bell = ('<section class="event-bell" aria-labelledby="ev-bell"><h2 id="ev-bell"><a href="{u}">Bell Schedule</a></h2>'
            '<ol class="blocks">{b}</ol></section>').format(u=bell_url, b=blocks_html(rows)) if rows else ""
    day_row = '<ol class="agenda">{}</ol>'.format(agenda_day(path, d, CAL_DAYS.get(d, {"codes": [], "events": []}), ids=False))
    nxt = []
    for e in real_events(d + timedelta(days=1)):
        if e["d"] not in [x for x in nxt]:
            nxt.append(e["d"])
        if len(nxt) >= 4:
            break
    upcoming = "".join(agenda_day(path, x, {"codes": [], "events": CAL_DAYS[x]["events"]}, ids=False) for x in nxt)
    cal_url = rel(path, "/school-calendar")
    main = ('{hero}\n<div class="page-body"><div class="wrap page-grid no-sidebar"><article class="page-content event-page">'
            '<!-- node calendar_event: field_event_date; the day from view calendar; timetable from the bell schedule block -->\n'
            '<div class="event-when{ns}">{chip}<div><h2>Event Date</h2><p><time datetime="{iso}">{when}</time>{nst}</p>'
            '<ul class="chips">{chips}</ul></div></div>{bell}'
            '<section class="event-day" aria-labelledby="ev-day"><h2 id="ev-day"><a href="{cal}#d-{iso}">School Calendar</a></h2>{day}</section>'
            '<section class="event-next" aria-labelledby="ev-next"><h2 id="ev-next">Upcoming Events</h2><ol class="agenda">{up}</ol></section>'
            '<div class="event-actions">{sub}<a class="arrow-link" href="{cal}"><span>School Calendar</span>{arrow}</a></div>'
            '</article>{rail}</div></div>').format(
        hero=page_hero(path, title, "School Calendar", compact=True), ns=" is-noschool" if noschool else "", chip=chip_lg, iso=d_iso(d),
        nst=noschool_tag(raw_title),
        when=esc(when), chips=chips, bell=bell, cal=cal_url, day=day_row, up=upcoming, sub=subscribe_btn(),
        arrow=icon("arrow"), rail=rail(path))
    return shell(path, "{} · {}".format(title, fmt_long(d)), main, body_class(path), "{} {}".format(title, when),
                 extra_css=["views.css"])


# ---------------------------------------------------------------------------------------------- bell schedule
def _hm(t):
    h, _, m = t.strip().partition(":")
    h = int(h)
    if h < 7:
        h += 12
    return h * 60 + int(m or 0)


def bell_cell(rows):
    lis = []
    for rng, label in rows:
        a_, _, b_ = rng.partition("-")
        start, end = _hm(a_), _hm(b_)
        kind = {"PLT": "plt", "Lunch": "lunch"}.get(label) or ("collab" if "Collab" in label else label.lower())
        lis.append('<li class="blk blk-{k}" style="--r:{r};--l:{l}" data-from="{s}" data-to="{e}"><b>{lab}</b>'
                   '<time><span>{a}</span><span class="dash">-</span><span>{b}</span></time></li>'.format(
                       k=esc(kind), r=start - 510 + 1, l=max(end - start, 1), s=start, e=end, lab=esc(label),
                       a=esc(a_), b=esc(b_)))
    return '<ol class="bday">{}</ol>'.format("".join(lis))


def bell_today(day):
    """The school day the live card shows: today when it is one, else the next."""
    code = CODES.get(day) if day else None
    rot = rotation_for(day) if day else None
    col = bell_col(day, code) if day else None
    return code, rot, col


def bell_html(cur):
    day = school_day(TODAY)
    code, rot, col = bell_today(day)
    hl = col if (day == TODAY and col in ("Collaboration Days", COLS.get(day.weekday()))) else None
    rows = (BELL["rotations"].get(rot) or {}).get(col, []) if rot else []
    chips = (('<li class="chip">{}</li>'.format(esc(rot)) if rot else "") +
             ('<li class="chip chip--forest">{}</li>'.format(esc(code)) if code else ""))
    live = ('<div class="bell-today" data-b="card"><div class="bt-head"><p class="eyebrow{ebh}" data-b="eyebrow">{eb}</p>'
            '<time class="bt-date" data-b="date" datetime="{iso}">{date}</time><ul class="chips" data-b="chips">{chips}</ul></div>'
            '<ol class="bt-nn" data-b="nn" hidden><li class="is-now"><span class="lbl">Now</span><b></b><time></time></li>'
            '<li class="is-next"><span class="lbl">Next</span><b></b><time></time></li></ol>'
            '<ol class="blocks" data-b="blocks">{blocks}</ol></div>').format(
        eb="Today", ebh="" if day == TODAY else " is-empty", iso=d_iso(day) if day else "",
        date=fmt_day_long(day) if day else "", chips=chips, blocks=blocks_html(rows))
    # semesters and rotation date ranges (the table at the top of the image)
    heads, dates, rot_rows = [], [], [[], []]
    for sem in BELL["semesters"]:
        heads.append('<th scope="col">{}</th>'.format(esc(smart_case(sem["name"]))))
        dates.append('<td class="sem-dates">{}</td>'.format(esc(sem["dates"])))
        for i, r in enumerate(sem["rotations"][:2]):
            name, _, span = r.partition(":")
            a_, _, b_ = span.partition(" - ")
            fr, to = school_date(a_), school_date(b_)
            here = fr and to and fr <= TODAY <= to
            rot_rows[i].append('<td class="sem-rot{c}" data-from="{f}" data-to="{t}"><span class="rname">{n}:</span> '
                               '<span>{s}</span></td>'.format(c=" is-current" if here else "", f=d_iso(fr) if fr else "",
                                                              t=d_iso(to) if to else "", n=esc(name.strip()), s=esc(span.strip())))
    semesters = ('<div class="table-wrap sem-wrap"><table class="sem-table"><thead><tr>{}</tr></thead><tbody>'
                 '<tr>{}</tr><tr>{}</tr><tr>{}</tr></tbody></table></div>').format(
        "".join(heads), "".join(dates), "".join(rot_rows[0]), "".join(rot_rows[1]))
    tables = []
    for n, (rname, cols) in enumerate(BELL["rotations"].items(), 1):
        ths, tds = [], []
        for c in BELL["days"]:
            is_hl = rname == rot and c == hl
            ths.append('<th scope="col" data-col="{c}"{cl}>{tag}<span>{c}</span></th>'.format(
                c=esc(c), cl=' class="is-today"' if is_hl else "",
                tag='<span class="tag-today">Today</span>' if is_hl else ""))
            tds.append('<td data-col="{c}"{cl}>{cell}</td>'.format(c=esc(c), cl=' class="is-today"' if is_hl else "",
                                                                   cell=bell_cell(cols.get(c, []))))
        tables.append('<section class="rot" aria-labelledby="rot-{n}"><h3 class="rot-name" id="rot-{n}">{r}</h3>'
                      '<div class="rot-wrap" role="region" aria-labelledby="rot-{n}"><table class="rot-table" data-rot="{r}" aria-labelledby="rot-{n}"><thead><tr>{th}</tr></thead>'
                      '<tbody><tr>{td}</tr></tbody></table></div></section>'.format(n=n, r=esc(rname), th="".join(ths), td="".join(tds)))
    src, w, h = img_src(cur, "bf352cd7a200.png")
    data = {"built": d_iso(TODAY), "labels": LABELS,
            "codes": {d_iso(d): c for d, c in sorted(CODES.items())},
            "rotations": [{"name": r["name"], "from": d_iso(r["from"]), "to": d_iso(r["to"])} for r in ROTATIONS if r["from"] and r["to"]],
            "bell": BELL["rotations"], "collab": [{"d": d_iso(d), "t": t} for d, t in COLLAB_DAYS if d]}
    return ('<!-- custom block (block_content bell_schedule): the timetable image as real tables, from content/bell-schedule.json;'
            ' js/bell.js highlights today, the current block and the next one (America/Vancouver) -->\n'
            '<section class="bell" data-bell aria-labelledby="bell-title"><h2 class="bell-title" id="bell-title">{title}</h2>'
            '{live}{sem}<div class="rots">{tables}</div>'
            '<div class="collab bell-collab"><h3 class="collab-title">{ct}</h3><ol data-b="collab">{collab}</ol></div>'
            '<p class="bell-orig">{orig}</p>{data}</section>').format(
        title=esc(smart_case(BELL["title"])), live=live, sem=semesters, tables="".join(tables),
        ct=esc(BELL["collaborationDaysTitle"].rstrip(":")), collab=collab_html(),
        orig=file_card(src, smart_case(BELL["title"]), "png"), data=json_script("bell-data", data))


# ---------------------------------------------------------------------------------------------- staff
def staff_slug(t):
    return "staff-" + re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def render_staff(path):
    """Staff page (node staff_page: field staff tables, one per group) → searchable tables, emails as links."""
    title = page_title(path)
    groups = PAGES[path]["staff"]
    total = sum(len(g["rows"]) for g in groups)
    nav = "".join('<li><a href="#{id}"><span>{t}</span> <span class="n" data-filter-group-n="{id}">{n}</span></a></li>'.format(
        id=staff_slug(g["group"]), t=esc(g["group"]), n=len(g["rows"])) for g in groups)
    def cell_html(raw_html):
        """One live cell: its text, its links resolved (Class Website links leave the site, so they get the mark)."""
        root = parse(raw_html)
        for link in root.elements("a"):
            url, ext = resolve(path, link.attrs.get("href", ""))
            link.attrs["href"] = url
            link.attrs.pop("title", None)
            kids = link.children
            if url.startswith("mailto:") and len(kids) == 1 and isinstance(kids[0], str) and "@" in kids[0]:
                local, _, domain = kids[0].partition("@")       # a narrow column breaks an address at its @ only
                link.children = [local, El("wbr", {}, link), "@" + domain]
            if ext or re.match(r"^https?://", url) and not url.startswith(LIVE):
                link.children.append(raw(EXT))
        return serialize(root).strip()

    secs = []
    for g in groups:
        sid = staff_slug(g["group"])
        cols = g.get("cols") or ["Name", "Position", "Email"]
        kinds = [slug(c) or "col" for c in cols]
        rows = []
        for r in g["rows"]:
            cells = r.get("cells") or [esc(r["name"]), esc(r["position"]),
                                       '<a href="mailto:{0}">{1}</a>'.format(esc(r["email"]), esc(r["email"]).replace("@", "<wbr>@", 1)) if r.get("email") else ""]
            tds = []
            for i, c in enumerate(cells):
                lab = cols[i] if i < len(cols) else ""
                body = cell_html(c) if r.get("cells") else c
                if i == 0:
                    tds.append('<th scope="row" data-label="{l}">{b}</th>'.format(l=esc(lab), b=body))
                else:
                    tds.append('<td data-label="{l}" class="c-{k}"{e}>{b}</td>'.format(
                        l=esc(lab), k=kinds[i] if i < len(kinds) else "col", b=body,
                        e=' data-empty' if not norm_ws(re.sub(r"<[^>]+>", "", body)) else ""))
            rows.append("<tr data-filter-row>{}</tr>".format("".join(tds)))
        head = "".join('<th scope="col" class="c-{}">{}</th>'.format(k, esc(c)) for c, k in zip(cols, kinds))
        secs.append('<section class="staff-group" id="{id}" aria-labelledby="{id}-t" data-filter-group="{id}">'
                    '<h2 class="staff-title" id="{id}-t"><span>{t}</span> <span class="n" data-filter-group-n="{id}">{n}</span></h2>'
                    '<div class="table-wrap"><table class="staff-table data-cards cols-{nc}"><thead><tr>{head}</tr></thead>'
                    '<tbody>{rows}</tbody></table></div></section>'.format(
                        id=sid, t=esc(g["group"]), n=len(g["rows"]), nc=len(cols), head=head, rows="".join(rows)))
    desktop_nav, mobile_nav = section_nav(path)
    main = ('{hero}\n<div class="page-body"><div class="wrap page-grid page-grid--rail-below"><div class="page-content staff" data-filter>'
            '<!-- node staff_page: the staff paragraphs (group title + rows) as tables; js/filter.js filters rows -->\n'
            '<div class="staff-tools">{bar}<nav class="group-chips" aria-label="{t}"><ul>{nav}</ul></nav></div>{secs}{pager}{mnav}</div>{side}{rail}</div></div>').format(pager=section_pager(path),
        hero=page_hero(path, title, (section_of(path) or {}).get("label", ""), compact=True), side=desktop_nav, mnav=mobile_nav, bar=filter_bar("staff", total),
        t=esc(title), nav=nav, secs="".join(secs), rail=rail(path))
    return shell(path, title, main, body_class(path), extra_js=["filter.js"], extra_css=["views.css"])


# ---------------------------------------------------------------------------------------------- news, newsletters, story
def pager_tools(label, total, filters=True):
    seg = ('<div class="seg" role="group" aria-label="{l}"><button type="button" aria-pressed="true" data-pager-filter="">All</button>'
           '<button type="button" aria-pressed="false" data-pager-filter="newsletter">Newsletters</button></div>').format(l=esc(label)) if filters else ""
    return ('<div class="list-tools needs-js" data-pager-tools>{seg}<p class="list-count" aria-hidden="true">{ic}'
            '<span class="list-count-label">{l}</span><output data-pager-count>{n}</output></p><p class="vh" role="status" aria-atomic="true" data-pager-status>'
            '<span>{l}</span> <span data-n>{n}</span></p></div>').format(seg=seg, ic=icon("paper"), n=total, l=esc(label))


def pager_nav():
    return '<nav class="pager" aria-label="Page navigation" hidden data-pager-nav></nav>'


def render_news_archive(path):
    """View news_archive_page:page_1 (path /news): all news, newest first, grouped by month; js/pager.js adds the
    All / Newsletters filter and the pager (?page=n, 0-based like Drupal's)."""
    title = page_title(path) or "News Archive"
    blocks = []
    for (y, m), items in grouped(NEWS):
        mid = "m-{}-{:02d}".format(y, m)
        rows = "".join(news_row(path, it).replace('<li class="row">', '<li class="row{}" data-pager-item data-kind="{}">'.format(
            " row--weekly" if clean_title(it["title"]).lower().startswith("striker weekly") else "",
            "newsletter" if it.get("newsletter") else "news"), 1) for it in items)
        blocks.append('<section class="month" aria-labelledby="{mid}" data-pager-group><h2 class="month-title" id="{mid}">{label}</h2>'
                      '<ul class="rows">{rows}</ul></section>'.format(
                          mid=mid, label="{} {}".format(MONTHS_LONG[m - 1], y) if y > 1900 else "", rows=rows))
    main = ('{hero}\n<div class="page-body"><div class="wrap page-grid no-sidebar"><div class="page-content is-hub">'
            '<!-- view news_archive_page (vertical_teaser rows, full pager) -->\n'
            '<div class="paged" data-pager data-pager-size="20" tabindex="-1" aria-labelledby="page-title">{tools}{blocks}{nav}</div>{hub}</div>{rail}</div></div>').format(
        hero=page_hero(path, title, "News", compact=True), hub=hub_sections(path), tools=pager_tools(title, len(NEWS)),
        blocks="".join(blocks), nav=pager_nav(), rail=rail(path))
    return shell(path, title, main, body_class(path), extra_js=["pager.js"], extra_css=["views.css"])


def render_story(path):
    """School Learning Story (node with paragraphs: intro, then basic text + article feed for Our Focus, Our Evidence,
    Our Actions) → a numbered story list."""
    title = page_title(path)
    intro = transform_body(path, STORY.get("intro", ""), title) if STORY.get("intro") else ""
    secs = []
    for n, sec in enumerate(STORY.get("sections", []), 1):
        items = []
        for it in sec["items"]:
            h = it["href"]
            body = (PAGES.get(h) or {}).get("body", "")
            d = date.fromisoformat(it["posted"]) if it.get("posted") else article_date(h)
            url, ext = resolve(path, h)
            thumb = ""
            name = (NEWS_BY_HREF.get(h) or {}).get("img")
            if name:
                src, w, hh = img_src(path, name)
                thumb = '<span class="story-thumb"><img src="{}" alt="" width="{}" height="{}" loading="lazy" decoding="async"></span>'.format(src, w, hh)
            items.append('<li class="story-item"><a href="{u}">{chip}<span class="story-text"><span class="story-h">{t}{x}</span>'
                         '{meta}<span class="story-p">{p}</span></span>{thumb}</a></li>'.format(
                             u=esc(url), chip=date_chip(d) if d else '<span class="date-chip"></span>',
                             t=esc(page_title(h) or h), x=EXT if ext else "",
                             meta='<span class="meta"><span>Posted:</span> <time datetime="{}">{} {}, {}</time></span>'.format(
                                 d_iso(d), MONTHS[d.month - 1], d.day, d.year) if d else "",
                             p=esc(first_sentence(body, 200)), thumb=thumb))
        sid = "story-{}".format(n)
        secs.append('<section class="story-sec" aria-labelledby="{sid}"><div class="story-sec-head"><span class="story-num" aria-hidden="true">{n:02d}</span>'
                    '<h2 id="{sid}">{t}</h2><div class="prose">{text}</div></div><ol class="ls-list">{items}</ol></section>'.format(
                        sid=sid, n=n, t=esc(sec["title"]), text=transform_body(path, sec.get("text", ""), title), items="".join(items)))
    main = ('{hero}\n<div class="page-body"><div class="wrap page-grid no-sidebar"><div class="page-content">'
            '<!-- paragraphs: basic text (intro) + basic text and article_feed (EVA) for each part of the story -->\n'
            '<div class="prose story-intro">{intro}</div>{secs}{pager}</div>{rail}</div></div>').format(pager=section_pager(path),
        hero=page_hero(path, title, compact=True), intro=intro, secs="".join(secs), rail=rail(path))
    return shell(path, title, main, body_class(path), first_sentence(STORY.get("intro", "")), extra_css=["views.css"])


# ---------------------------------------------------------------------------------------------- search and 404
def section_title(path):
    if path.startswith("/news/") or path == "/news":
        return "News"
    if path.startswith("/school-learning-story"):
        return "School Learning Story"
    sec = section_of(path)
    return sec["label"] if sec else ""


def text_of(body):
    return norm_ws(html.unescape(re.sub(r"<[^>]+>", " ", body or "")))


def menu_aliases():
    """Every label design/ia.json gives a URL (main menu, utility, footer, hub links): what visitors call the page."""
    out = {}

    def add(href, label):
        if href and label and is_internal(href):
            out.setdefault(canon(bare(href)), []).append(norm_ws(label))

    for m in PRIMARY:
        add(m["href"], m["label"])
        for g in m["groups"]:
            add(g.get("href"), g.get("label"))
            for c in g["children"]:
                add(c["href"], c["label"])
    for col in FOOTER_MENU:
        for c in col["children"]:
            add(c["href"], c["label"])
    for n in UTILITY:
        add(n["href"], n["label"])
    for spec in HUBS.values():
        for sec in spec["sections"]:
            add(sec.get("href"), sec.get("heading"))
    return out


def build_search_index():
    """docs/assets/search.json: every built page, the news items we link to on the live site, and the calendar.
    u is relative to the site root (pages) or absolute (live site, e = 1). a = the page's menu labels and its own
    section headings (so "bell" finds the Bell Schedule, titled "Timetable Structure 2026-2027"); p = 1 for pages
    (a page outranks a dated post on a tie); o = 1 for a day with no school."""
    out = []
    aliases = menu_aliases()
    for path in sorted(BUILT - {SEARCH}):
        pg = PAGES.get(path) or {}
        if pg.get("type") == "event":
            continue
        t = page_title(path) or (NAME if path == "/" else "")
        text = text_of(pg.get("body"))
        if pg.get("type") == "staff":
            text = " ".join("{} {}".format(g["group"], " ".join(text_of(c) for c in (r.get("cells") or [r["name"], r["position"]])))
                            for g in pg["staff"] for r in g["rows"])
        if path == "/":
            text = SITE["motto"]
        if path == "/school-learning-story":
            text = text_of(STORY.get("intro"))
        item = {"t": t, "u": "" if path == "/" else path.strip("/") + "/", "s": section_title(path), "x": text[:3000]}
        heads = [norm_ws(html.unescape(re.sub(r"<[^>]+>", " ", h))) for h in re.findall(r"<h[23][^>]*>(.*?)</h[23]>", pg.get("body") or "")]
        alias = []
        for x in aliases.get(path, []) + heads:
            if x and x.lower() != t.lower() and x not in alias:
                alias.append(x)
        if alias:
            item["a"] = " · ".join(alias)[:600]
        d = article_date(path) if pg.get("type") == "article" else None
        if d:
            item["d"] = d_iso(d)
        else:
            item["p"] = 1
        out.append(item)
    for n in NEWS:
        if n["href"] in BUILT:
            continue
        d = article_date(n["href"])
        item = {"t": clean_title(n["title"]), "u": LIVE + n["href"], "s": "News", "x": teaser_text(n.get("teaser")), "e": 1}
        if d:
            item["d"] = d_iso(d)
        out.append(item)
    for d, info in CAL_DAYS.items():
        for t in info["events"]:
            href = EVENT_PAGES.get((t.lower(), d_iso(d)))
            ev = {"t": smart_case(t), "u": href.strip("/") + "/" if href else "school-calendar/#d-" + d_iso(d),
                  "s": "School Calendar", "x": "", "d": d_iso(d), "c": 1}
            if is_no_school(t):
                ev["o"] = 1
            out.append(ev)
    return json.dumps(out, ensure_ascii=False, separators=(",", ":"))


def render_search(path):
    """Search page (core search page node_search at /search/node): the form, then results from assets/search.json
    filtered in the browser (js/search.js), reading ?keys= like Drupal."""
    cur = path
    form = ('<form class="search-page-form" role="search" action="./" method="get">'
            '<label for="search-keys">Enter your keywords</label><div class="search-page-row">'
            '<input id="search-keys" type="search" name="keys" autocomplete="off" spellcheck="false">'
            '<button class="btn btn-solid" type="submit">{si}<span>Search</span></button></div></form>').format(si=icon("search"))
    cards = child_cards(cur, [{"title": m["label"], "href": m["href"]} for m in PRIMARY], "h3", False)
    main = ('{hero}\n<div class="page-body"><div class="wrap page-grid no-sidebar"><div class="page-content search-page" '
            'data-search data-index="{idx}" data-root="{root}">'
            '<!-- search.view_node_search: search form block + results list -->\n{form}'
            '<section class="search-results" aria-labelledby="sr-title" hidden data-search-results>'
            '<h2 id="sr-title"><span>Search results</span> <span class="n" data-search-n></span></h2>'
            '<p class="search-empty" hidden data-search-empty>Your search yielded no results.</p>'
            '<ol class="results" data-search-list></ol></section>'
            '<p class="vh" role="status" aria-atomic="true" data-search-status></p>'
            '<section class="search-browse" aria-labelledby="sb-title"><h2 id="sb-title" class="eyebrow">Helpful Links</h2>{cards}</section>'
            '</div>{rail}</div></div>').format(
        hero=page_hero(cur, "Search", compact=True), idx=asset(cur, "search.json"), root="../" * depth(cur), form=form, cards=cards,
        rail=rail(cur))
    return shell(cur, "Search", main, "path-search", extra_js=["search.js"], extra_css=["views.css"])


def render_404():
    cur = "/"
    cards = child_cards(cur, [{"title": m["label"], "href": m["href"]} for m in PRIMARY], "h2", False)
    main = ('<!-- system 404 page (Page not found) in the theme -->\n'
            '<header class="page-hero page-hero--404 on-dark"><div class="wrap nf-wrap"><div>'
            '<nav class="breadcrumb" aria-label="breadcrumb"><ol><li><a href="./">Home</a></li></ol></nav>'
            '<h1>Page not found</h1><p class="nf-lead">The requested page could not be found.</p></div>'
            '<p class="nf-num" aria-hidden="true"><span>4</span><span class="nf-arch">0</span><span>4</span></p></div></header>'
            '<div class="page-body"><div class="wrap"><div class="nf-search">{form}</div>'
            '<ul class="task-grid nf-tasks">{absent}{bell}{cal}</ul>{cards}</div></div>').format(
        form=search_form(cur, "404"), cards=cards,
        # the three top tasks as the front page's Helpful Links tiles (same component)
        absent='<li>{}</li>'.format(absent_card(cur, "task task--absent")),
        bell=('<li><a class="task" href="{}"><span class="task-ico">{}</span><span class="task-label"><strong>Bell Schedule</strong>'
              '<span class="sub">{}</span></span>{}</a></li>').format(rel(cur, BELL_PATH), icon("clock"), esc(page_title(BELL_PATH)), icon("arrow", "icon task-go")),
        cal=('<li><a class="task" href="{}"><span class="task-ico">{}</span><span class="task-label"><strong>School Calendar</strong>'
             '<span class="sub">Upcoming Events</span></span>{}</a></li>').format(rel(cur, "/school-calendar"), icon("calendar"), icon("arrow", "icon task-go")))
    return shell(cur, "Page not found", main, "path-404", base_script=True, extra_css=["views.css"])


# ---------------------------------------------------------------------------------------------- proposal
# docs/proposal/ is Ali's proposal to the principal: the document about this concept, linked from the concept banner
# ("About this concept"). It is not school content and not part of the Drupal theme. It is the one page allowed new
# words, so tools/check_copy.py and tools/check_fidelity.py skip docs/proposal/ (a documented exception in each).
# Its stylesheet and screenshots live in design/proposal/ (shots of the live site and of this preview, taken 2026-10-06);
# tools/proposal_pdf.py prints this page to the US Letter PDF beside it with headless Google Chrome.
PROPOSAL = "/proposal"
PROPOSAL_SRC = ROOT / "design" / "proposal"
PROPOSAL_PDF = "mcroberts-website-redesign-proposal.pdf"
THEME_ZIP = "downloads/mcroberts-drupal-theme.zip"     # the Drupal 10 sub-theme, linked when the build finds it
PREVIEW_URL = os.environ.get("PREVIEW_URL", "https://rajool.github.io/mcroberts-redesign/").strip()  # the public address of docs/, when known (written out on paper)

# Lighthouse, mobile (accessibility, best practices). Today: research/audit.md §1 (mcroberts.sd38.bc.ca, 2026-10-06).
# Redesign: the QA run on this preview (2026-10-06). SEO is left out: the preview is noindex on purpose.
LH_TODAY = {"home": (87, 100), "attendance": (91, 100)}
LH_REDESIGN = {"home": (100, 100), "attendance": (100, 100)}
# research/audit.md: H5 (two or more h1s), C1 (tel: links), H4 (the heaviest page), C5 (all images), C4 (link colour)
AUDIT = {"multi_h1": "183 of 191", "heavy_page": 3.87e6, "images": 31.7e6, "link_fg": "#51ba8d", "link_bg": "#ffffff"}
HEAVY_PAGE = "/our-school-story/news/2024/12/grade-8-student-mentor-connections"
CAREER_PHOTO = "7551c96b0920.png"     # the Career Centre door photo (C5)
# design/ia.md §1: blind tree test with simulated testers, 26 tasks (success rate): the final menu (fresh re-test of
# design/ia.json) and the live menu. With 2 testers per tree one task is worth about 4 points (ia.md §1, last bullet).
TREE_TEST = {"tasks": 26, "new": "92.3%", "live": "73.1%", "point": "about 4 points"}
# research/benchmark.md §5: McRoberts today and the best of the 12 benchmark sites, scored 1 to 5. The redesign column
# is Ali's own score of this preview against the same "what 5 looks like" column.
BENCH = [
    ("Top tasks for parents and students", 2, 5, 5, "Eastside Catholic"),
    ("Menu and site structure", 3, 5, 5, "Stevenson, Saint Xavier"),
    ("Header and school identity", 3, 5, 5, "Brighton College, Saint Xavier"),
    ("Home page story", 2, 4, 5, "Saint Xavier, Webb School"),
    ("News", 2, 4, 4, "Walnut Grove, Stevenson"),
    ("Events and calendar", 2, 4, 4, "Westdale, Fairfax Academy"),
    ("Alerts and closures", 2, 4, 4, "Eastside Catholic, Walnut Grove"),
    ("Look and feel", 2, 5, 5, "Brighton College, West Island College, Saint Xavier"),
    ("Photos", 2, 3, 5, "Brighton College, Webb School"),
    ("Accessibility", 3, 4, 4, "Shenton College, James Ruse"),
    ("Translation", 3, 1, 5, "Fort Smith"),   # this version shows no Translate control (owner's choice, 2026-10-07)
    ("On a phone", 2, 4, 4, "Eastside Catholic, Westdale"),
]
# The seven before/after pairs: (image name, kind, title, one sentence, alt today, alt redesign)
PAIRS = [
    ("home", "phone", "The first screen on a phone",
     "The first screen now shows the day's blocks, the next event and a one-tap call to report an absence. "
     "Today that number is almost four screens down.",
     "Today's home page on a phone: the crest, the school name and a menu button.",
     "The redesigned home page on a phone: the day's blocks, the next event and the absence call button."),
    ("attendance", "phone", "Reporting an absence",
     "The page starts right away, and the Early Warning number is a button that calls it. "
     "Today the title starts near the bottom of the screen and the number is plain text, not a call link.",
     "Today's Student Attendance page on a phone: the header fills most of the screen.",
     "The redesigned Student Attendance page on a phone, with a call button for the Early Warning number."),
    ("bell", "phone", "The bell schedule",
     "The timetable is real text and tables that show today's blocks and what comes next. "
     "Today it is a picture, and on a phone its times are about 3 pixels tall.",
     "Today's bell schedule on a phone: a picture of the timetable, too small to read.",
     "The redesigned bell schedule on a phone: today's date, rotation and blocks as text."),
    ("calendar", "phone", "The school calendar",
     "The calendar is a full-width list by month, No School days are marked, and the timetable codes are small tags "
     "you can hide. Today it is a small scroll box that starts in early September.",
     "Today's school calendar on a phone: a small scroll box that starts on September 7.",
     "The redesigned school calendar on a phone: a list for this month with month buttons."),
    ("menu", "desktop", "The menu",
     "Each menu opens one clear panel, with the most requested pages first and the rest in labelled groups. "
     "Today some pages, like Strikers Athletics and Club Directory, are not in the menu at all.",
     "Today's Parents menu: one long list.",
     "The redesigned Parents menu: the most requested pages first, then four labelled groups."),
    ("news", "desktop", "News",
     "Every story shows its date, and the newsletters have their own filter. Today the news cards have no dates.",
     "Today's News Archive: cards with no dates.",
     "The redesigned News Archive: dated stories and a Newsletters filter."),
]
# own inline icons (24px grid, stroke): the four things that stay the same
P_ICONS = {
    "crest": '<path d="M12 3l7 3v5c0 4.6-3 8.4-7 10-4-1.6-7-5.4-7-10V6l7-3z"/><path d="M12 3v18M5 11h14"/>',
    "words": '<path d="M5 6h14M5 10h14M5 14h9M5 18h6"/>',
    "drupal": '<rect x="4" y="4" width="16" height="6" rx="1.5"/><rect x="4" y="14" width="16" height="6" rx="1.5"/>'
              '<path d="M8 7h.01M8 17h.01"/>',
    "undo": '<path d="M9 14L4 9l5-5"/><path d="M4 9h10a6 6 0 010 12h-3"/>',
}


def _p_icon(name):
    return ('<svg class="p-icon" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false" fill="none" '
            'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{}</svg>').format(P_ICONS[name])


def _jpeg_size(path):
    """(width, height) of a JPEG, read from its start-of-frame marker."""
    data = path.read_bytes()
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            return int.from_bytes(data[i + 7:i + 9], "big"), int.from_bytes(data[i + 5:i + 7], "big")
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7 or marker == 0xFF:
            i += 1 if marker == 0xFF else 2
            continue
        i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    raise ValueError("no frame size in {}".format(path))


def _contrast(fg, bg):
    def lum(h):
        c = [int(h.lstrip("#")[k:k + 2], 16) / 255 for k in (0, 2, 4)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    a, b = sorted((lum(fg), lum(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def _token(name):
    return re.search(r"--{}:\s*(#[0-9a-fA-F]{{6}})".format(re.escape(name)), (THEME / "css" / "tokens.css").read_text()).group(1)


def _size(n):
    return "{:.1f} MB".format(n / 1e6) if n >= 1e6 else "{:.0f} KB".format(n / 1e3)


def _p_img(name, alt, cls=""):
    # no lazy loading: headless Chrome prints the page once it has loaded, and a lazy image would print blank
    w, h = _jpeg_size(PROPOSAL_SRC / "img" / name)
    return '<img{} src="img/{}" width="{}" height="{}" alt="{}" decoding="async">'.format(
        ' class="{}"'.format(cls) if cls else "", name, w, h, esc(alt))


def _p_pair(n, item):
    name, kind, title, sentence, alt_today, alt_new = item
    # each screenshot links to its full-size file, to look closer on a screen
    shots = "".join('<figure class="shot"><figcaption class="shot-label shot-label--{k}">{lab}</figcaption>'
                    '<a href="img/{f}">{img}</a></figure>'.format(
        k=k, lab=lab, f="{}-{}-{}.jpg".format(name, kind, k), img=_p_img("{}-{}-{}.jpg".format(name, kind, k), alt))
        for k, lab, alt in
        (("today", "Today's site", alt_today), ("redesign", "Redesign", alt_new)))
    return ('<article class="pair pair--{kind}"><h3><span class="pair-n" aria-hidden="true">{n}</span>{t}</h3>'
            '<div class="shots">{shots}</div><p class="pair-cap">{s}</p></article>').format(
        kind=kind, n=n, t=esc(title), shots=shots, s=esc(sentence))


def _url_html(u):
    """An address as HTML that may break only after a slash (<wbr>), never inside a word."""
    return re.sub(r"(?<!/)/(?!/)", "/<wbr>", esc(u))


def _meter(v):
    return '<span class="meter" aria-hidden="true">{}</span>'.format("".join(
        '<i class="on"></i>' if k < v else "<i></i>" for k in range(5)))


def _ia_outline():
    util = []
    for u in UTILITY:
        if u["href"].startswith("tel:"):
            continue
        if u["href"] == ATTENDANCE:
            tel = next((x["label"] for x in UTILITY if x["href"].startswith("tel:")), "")
            util.append('<li class="ia-chip ia-chip--absent">{} <b>{}</b></li>'.format(esc(u["label"]), esc(tel)))
        else:
            util.append('<li class="ia-chip">{}</li>'.format(esc(u["label"])))
    cells = []
    for i, m in enumerate(PRIMARY, 1):
        groups = m.get("groups") or []
        first, rest = (groups[0].get("children") or [] if groups else []), groups[1:]
        others = [c for g in rest for c in (g.get("children") or [])]
        names = [g["label"] for g in rest if g.get("label")]
        items = "".join('<li class="ia-top">{}</li>'.format(esc(c["label"])) for c in first)
        more = ""
        if len(first) + len(others) <= 6:        # a short menu is shown whole, its other links quieter
            items += "".join("<li>{}</li>".format(esc(c["label"])) for c in others)
        elif others:                               # a long one: the most requested, then its groups by name
            more = '<p class="ia-more"><b>+{} more</b>{}</p>'.format(
                len(others), (" in " + esc(", ".join(names))) if names else "")
        cells.append('<li class="ia-cell"><h3><span class="ia-i" aria-hidden="true">{}</span>{}</h3><ul>{}</ul>{}</li>'.format(
            i, esc(m["label"]), items, more))
    test = ('<li class="ia-cell ia-test"><h3>Tree test</h3>'
            '<div class="tt"><p class="tt-row tt-new"><span class="tt-bar" style="--v:{nv}"></span><b>{new}</b> the new menu</p>'
            '<p class="tt-row"><span class="tt-bar" style="--v:{lv}"></span><b>{live}</b> today&#x27;s menu</p></div>'
            '<p class="tt-text">In a blind tree test with simulated testers and {n} everyday tasks, the new menu '
            'led to the right page {new} of the time, against {live} for today&#x27;s menu. With two testers '
            'each, one task is worth {pt}, so read these as a direction.</p></li>').format(
        n=TREE_TEST["tasks"], new=TREE_TEST["new"], live=TREE_TEST["live"], pt=TREE_TEST["point"],
        nv=TREE_TEST["new"].rstrip("%"), lv=TREE_TEST["live"].rstrip("%"))
    return ('<div class="ia"><div class="ia-util"><p class="ia-k">On every page</p><ul>{}</ul></div>'
            '<ul class="ia-menu">{}{}</ul></div>').format("".join(util), "".join(cells), test)


def render_proposal():
    cur = PROPOSAL
    # measured on this build: every page the build renders (not old files left in docs/)
    built = [out_file(p) for p in sorted(BUILT)] + [DOCS / "404.html"]
    texts = [f.read_text() for f in built if f.exists()]
    one_h1 = sum(1 for t in texts if len(re.findall(r"<h1[\s>]", t)) == 1)
    multi_h1 = sum(1 for t in texts if len(re.findall(r"<h1[\s>]", t)) > 1)
    tel_pages = sum(1 for t in texts if 'href="tel:' in t)
    career_before = (ROOT / "assets" / "content" / CAREER_PHOTO).stat().st_size
    career_after = (DOCS / "assets" / "img" / IMAGES["map"].get(CAREER_PHOTO, CAREER_PHOTO)).stat().st_size
    heavy_file = out_file(canon(HEAVY_PAGE))
    heavy_html = heavy_file.read_text()
    story = heavy_html[heavy_html.index("</header>", heavy_html.index('class="page-hero')):heavy_html.index("</main>")]
    heavy_photos = dict.fromkeys(re.findall(r'<img\b[^>]*?\ssrc="([^"]+)"', story))   # the story's own photos, as today
    heavy_after = heavy_file.stat().st_size + sum((heavy_file.parent / src).resolve().stat().st_size for src in heavy_photos)
    images_after = sum(f.stat().st_size for f in (DOCS / "assets" / "img").iterdir() if f.is_file())
    link_before = _contrast(AUDIT["link_fg"], AUDIT["link_bg"])
    link_after = _contrast(_token("forest"), _token("paper"))
    assert one_h1 == len(texts) and multi_h1 == 0, "a page has no h1 or more than one"

    home = rel(cur, "/")
    preview = PREVIEW_URL or home
    zip_ok = (DOCS / THEME_ZIP).exists()
    pdf_ok = (DOCS / "proposal" / PROPOSAL_PDF).exists()
    icon_href, _, _ = crest_src(cur, "32")

    same = [
        ("crest", "The crest", "Used exactly as it is: no new colours, no cropping, no redrawing. "
                               "The site&#x27;s green comes from the crest."),
        ("words", "Every word", "Every heading, menu label and page uses words that are on our site today. "
                                "A check compares each page with the live site and finds 0 new words."),
        ("drupal", "Drupal 10 and the district&#x27;s setup", "The same content and views; no page text is edited. "
                                                             "A new theme plus settings for menus, page addresses (old "
                                                             "ones redirect) and blocks. The bell schedule and a few "
                                                             "home-page sentences are kept in the theme."),
        ("undo", "Easy to undo", "Two steps: make the current theme the default again, then run the undo script that "
                                 "comes with the theme. It puts back today&#x27;s menu, page addresses and any retired pages."),
    ]
    same_html = "".join('<li><span class="well">{}</span><h3>{}</h3><p>{}</p></li>'.format(_p_icon(k), t, d)
                        for k, t, d in same)

    bench_rows = "".join(
        '<tr><th scope="row">{a}</th><td class="c-today">{t}{mt}</td><td class="c-new">{r}{mr}</td>'
        '<td class="c-best">{b}{mb}<small>{who}</small></td></tr>'.format(
            a=esc(a), t=t, mt=_meter(t), r=r, mr=_meter(r), b=b, mb=_meter(b), who=esc(who))
        for a, t, r, b, who in BENCH)
    bench_total = (sum(x[1] for x in BENCH), sum(x[2] for x in BENCH), len(BENCH) * 5)

    numbers = [
        ("Lighthouse accessibility, home page on a phone", LH_TODAY["home"][0], LH_REDESIGN["home"][0]),
        ("Lighthouse accessibility, Student Attendance on a phone", LH_TODAY["attendance"][0], LH_REDESIGN["attendance"][0]),
        ("Lighthouse best practices, both pages", min(LH_TODAY["home"][1], LH_TODAY["attendance"][1]),
         min(LH_REDESIGN["home"][1], LH_REDESIGN["attendance"][1])),
        ("Contrast of link text (4.5 : 1 is the minimum)", "{:.1f} : 1".format(link_before), "{:.1f} : 1".format(link_after)),
        ("Pages with more than one main heading", AUDIT["multi_h1"], "{} of {}".format(multi_h1, len(texts))),
        ("Pages where the absence number calls with one tap", "Home page only", "All {}".format(tel_pages)),
        ("Career Centre photo", _size(career_before), _size(career_after)),
        ("Heaviest page with its photos (a story with images pasted into the text)", _size(AUDIT["heavy_page"]), _size(heavy_after)),
        ("All images on the site", _size(AUDIT["images"]), _size(images_after)),
    ]
    num_rows = "".join('<tr><th scope="row">{}</th><td class="c-today">{}</td><td class="c-new">{}</td></tr>'.format(
        esc(a), esc(str(b)), esc(str(c))) for a, b, c in numbers)

    phones = "".join(_p_pair(i, p) for i, p in enumerate(PAIRS, 1) if p[1] == "phone")
    desks = "".join(_p_pair(i, p) for i, p in enumerate(PAIRS, 1) if p[1] == "desktop")

    zip_name = THEME_ZIP.rsplit("/", 1)[-1]
    # on paper the address is written out (a break only after a slash, never inside a word)
    zip_where = '<span class="url">{}</span>'.format(_url_html(PREVIEW_URL + THEME_ZIP)) if PREVIEW_URL else zip_name
    if zip_ok:
        zip_step = ('<a href="{}" download>Download the Drupal theme</a> ({}) and pass it to whoever looks after our '
                    'site at the district.').format("../" * depth(cur) + THEME_ZIP, zip_where)
    else:
        zip_step = 'Download the Drupal theme ({}) and pass it to whoever looks after our site at the district.'.format(zip_where)
    preview_line = ('<a href="{u}">Open the live preview</a>{w}').format(
        u=esc(preview), w=' <span class="url">{}</span>'.format(_url_html(PREVIEW_URL)) if PREVIEW_URL else "")

    main = '''<header class="cover">
<p class="eyebrow">Website redesign proposal</p>
<h1>A new look for the McRoberts website</h1>
<p class="dek">Built only from what our school already has.</p>
<dl class="meta"><div><dt>For</dt><dd>Mr. Jason Leslie, Principal</dd></div>
<div><dt>From</dt><dd>Ali Rajool, McRoberts parent and PAC Co-Treasurer</dd></div>
<div><dt>Date</dt><dd>October 2026</dd></div></dl>
</header>
<section class="intro" aria-labelledby="summary-title">
<div class="letter"><h2 class="vh" id="summary-title">Summary</h2>
<p class="hi">Hi Mr. Leslie,</p>
<p>Our school website has a lot of good information, but it is hard to use, especially on a phone. On a phone, a parent
who wants to report an absence has to scroll almost four screens down the home page to find the number, and the bell
schedule is a picture that is too small to read. I took the site&#x27;s own pages and built a working preview of a new
design. It keeps the crest and every word as they are today, and it stays on Drupal 10, so it can be added as a new
theme without changing the text of any page.</p></div>
<aside class="ask" aria-labelledby="ask-title"><h2 id="ask-title">What I am asking</h2>
<p class="ask-big">Your feedback.</p>
<p>Please open the preview on your phone and on a computer, and tell me what works and what doesn&#x27;t. If you like the
direction, I would be happy to walk you through it.</p>
<p class="ask-link">{preview_line}</p></aside>
</section>
<figure class="hero-shot">
<div class="hero-today"><p class="shot-label shot-label--today">Today&#x27;s site</p>{hero_today}</div>
<div class="hero-new"><p class="shot-label shot-label--redesign">Redesign</p><div class="hero-stage">{hero_desk}{hero_phone}</div></div>
<figcaption><b>The home page.</b> The crest, our name and our motto lead the page, with the top tasks right under
them and the absence number in the top bar of every page (on a phone, a call button in the bottom bar). The yellow
bar shows how an alert from the school would look.</figcaption></figure>
<section class="sec sec--same" aria-labelledby="same-title">
<h2 id="same-title">What stays exactly the same</h2>
<ul class="same-grid">{same}</ul>
</section>
<section class="sec sec--ia" aria-labelledby="ia-title">
<h2 id="ia-title">A simpler site structure</h2>
<p class="lead">Seven menus, named after what people come for, each with the most requested pages first. A slim bar on
every page holds the absence line and the main sign-ins.</p>
{ia}
</section>
<section class="sec sec--pairs" aria-labelledby="pairs-title">
<h2 id="pairs-title">The biggest improvements</h2>
<p class="lead">Each pair shows the same view: today&#x27;s site on the left, the redesign on the right.</p>
<div class="pairs pairs--phone">{phones}</div>
<div class="pairs pairs--desktop">{desks}</div>
</section>
<section class="sec sec--numbers" aria-labelledby="numbers-title">
<h2 id="numbers-title">Accessibility and speed, before and after</h2>
<p class="lead">Measured with Lighthouse on a phone and from the files themselves. The big gains are in accessibility
and in the heaviest files.</p>
<div class="table-wrap"><table class="numbers">
<thead><tr><th scope="col">Measure</th><th scope="col">Today</th><th scope="col">Redesign</th></tr></thead>
<tbody>{num_rows}</tbody></table></div>
<p class="note">Lighthouse SEO is not compared: the preview is set to stay out of search engines on purpose.</p>
</section>
<section class="sec sec--compare" aria-labelledby="compare-title">
<h2 id="compare-title">How it compares with the best school websites</h2>
<p class="lead">I compared McRoberts with 12 of the best school websites today, most of them launched or awarded in 2025
or 2026, from BC to the UK, on a scale of 1 to 5, and scored the redesign the same way. The redesign&#x27;s scores are my
own, so please judge them on the preview.</p>
<div class="table-wrap"><table class="bench">
<thead><tr><th scope="col">Area</th><th scope="col">Today</th><th scope="col">Redesign</th><th scope="col">Best of the 12</th></tr></thead>
<tbody>{bench_rows}</tbody>
<tfoot><tr><th scope="row">Total, out of {tmax}</th><td class="c-today">{tt}</td><td class="c-new">{tr}</td><td class="c-best"></td></tr></tfoot>
</table></div>
</section>
<section class="sec sec--adopt" aria-labelledby="adopt-title">
<h2 id="adopt-title">How to adopt it</h2>
<ol class="steps">
<li><span><a href="{preview}">Look at the live preview</a> on a phone and on a computer.</span></li>
<li><span>{zip_step}</span></li>
<li><span>Try it on a staging copy first. A Platform.sh branch environment copies the live site&#x27;s content, so the
real site does not change while it is tested.</span></li>
<li><span>When it looks right, make the new theme the default and apply its settings for menus, page addresses and
blocks.</span></li>
<li><span>If anything goes wrong, make the current theme the default again and run the theme&#x27;s undo script (the
steps are in its README).</span></li>
</ol>
</section>
<footer class="signoff">
<p class="thanks">Thank you for reading this, and for everything you and the staff do for our kids. I would love to hear
what you think.</p>
<p class="sig">Ali Rajool</p>
<p class="role">McRoberts parent and PAC Co-Treasurer</p>
</footer>'''.format(
        preview_line=preview_line, preview=esc(preview), same=same_html, ia=_ia_outline(), bench_rows=bench_rows,
        tmax=bench_total[2], tt=bench_total[0], tr=bench_total[1], phones=phones, desks=desks, num_rows=num_rows,
        zip_step=zip_step,
        hero_today=_p_img("home-desktop-today.jpg", "Today's home page on a computer.", "hero-old"),
        hero_desk=_p_img("home-desktop-redesign.jpg", "The redesigned home page on a computer.", "hero-desk"),
        hero_phone=_p_img("home-phone-redesign.jpg", "The redesigned home page on a phone.", "hero-phone"))

    bar = '<nav class="doc-bar" aria-label="Proposal"><a href="{}">Back to the preview</a>{}</nav>'.format(
        esc(home), ' <a href="{}" download>Download this proposal (PDF)</a>'.format(PROPOSAL_PDF) if pdf_ok else "")
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<meta name="robots" content="noindex,nofollow">\n'
            '<title>McRoberts website redesign proposal</title>\n'
            '<meta name="description" content="A proposal for a new design of the McRoberts Secondary website, '
            'from a McRoberts parent.">\n<meta name="theme-color" content="#10291a">\n'
            '<link rel="icon" href="{icon}" type="image/png">\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link rel="stylesheet" href="{fonts}">\n<link rel="stylesheet" href="{tokens}">\n'
            '<link rel="stylesheet" href="proposal.css">\n</head>\n<body class="proposal-page">\n'
            '<a class="skip-link" href="#main-content">Skip to main content</a>\n'
            '<div class="concept-banner" role="note">Design concept for discussion — not the official school website. '
            'The official site is <a href="{live}">mcroberts.sd38.bc.ca</a>.</div>\n'
            '<div class="doc">\n{bar}\n<main id="main-content" tabindex="-1">\n{main}\n</main>\n</div>\n'
            '</body>\n</html>\n').format(icon=icon_href, fonts=esc(FONTS), tokens=asset(cur, "css/tokens.css"), live=LIVE,
                                         bar=bar, main=main)


def copy_proposal_assets():
    dst = DOCS / "proposal"
    (dst / "img").mkdir(parents=True, exist_ok=True)
    copy(PROPOSAL_SRC / "proposal.css", dst / "proposal.css")
    for f in sorted((PROPOSAL_SRC / "img").glob("*.jpg")):
        copy(f, dst / "img" / f.name)


# ---------------------------------------------------------------------------------------------- redirects
def redirect_stub(old, new):
    """The Redirect module's 301 for a static host: at the old URL, a page that sends the browser on at once (meta
    refresh, plus location.replace so the back button skips it and ?query / #fragment survive), names the clean URL as
    canonical and is never indexed. Without scripts or refresh, the link to the page remains."""
    url = rel(old, new)
    title = page_title(new) or NAME
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<meta name="robots" content="noindex,nofollow">\n'
            '<title>{t}</title>\n'
            '<meta http-equiv="refresh" content="0; url={u}">\n'
            '<script>location.replace({js} + location.search + location.hash);</script>\n'
            '<style>body{{margin:0;font:1rem/1.5 system-ui,sans-serif;background:#f7f3ea;color:#14211a}}'
            '.concept-banner{{background:#10291a;color:#fff;padding:.5rem 1rem;font-size:.875rem}}'
            '.concept-banner a{{color:#e3b65a}}p{{padding:2rem 1rem}}a{{color:#1f4d2b}}</style>\n</head>\n<body>\n'
            '<!-- Redirect module: {old} → {new} (301) -->\n'
            '<div class="concept-banner" role="note">Design concept for discussion — not the official school website. '
            'The official site is <a href="{live}">mcroberts.sd38.bc.ca</a>.</div>\n'
            '<p><a href="{u}">{t}</a></p>\n</body>\n</html>\n').format(
        t=esc(title), u=esc(url), js=json.dumps(url), old=old, new=new, live=LIVE)


# ---------------------------------------------------------------------------------------------- assets and output
def write(path, text):
    """Write only when the content changed: a rebuild never truncates a file a browser is fetching."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def copy(src, dst):
    if not dst.exists() or dst.stat().st_size != src.stat().st_size or dst.read_bytes() != src.read_bytes():
        shutil.copyfile(src, dst)


def copy_assets():
    for sub in ("css", "js"):
        dst = DOCS / "assets" / sub
        dst.mkdir(parents=True, exist_ok=True)
        for f in sorted((THEME / sub).iterdir()):
            if f.is_file():
                copy(f, dst / f.name)
    img_dst = DOCS / "assets" / "img"
    img_dst.mkdir(parents=True, exist_ok=True)
    sips = shutil.which("sips")
    crest_src_file = ROOT / "assets" / "content" / CREST
    for size in sorted(CREST_USED):
        out_name, args = CREST_SIZES[size]
        out = img_dst / out_name
        if out.exists() and out.stat().st_mtime >= crest_src_file.stat().st_mtime:
            continue
        if sips:
            subprocess.run([sips, *args, str(crest_src_file), "--out", str(out)], capture_output=True, check=True)
        else:
            shutil.copyfile(crest_src_file, out)
    for mapped, small in sorted(SMALL_COPIES.items()):
        src = ROOT / "assets" / "img" / mapped
        out = img_dst / small
        if not src.exists() or (out.exists() and out.stat().st_mtime >= src.stat().st_mtime):
            continue
        if sips:
            args = ["--resampleWidth", "960"] + (["-s", "formatOptions", "78"] if small.endswith(".jpg") else [])
            subprocess.run([sips, *args, str(src), "--out", str(out)], capture_output=True, check=True)
        else:
            shutil.copyfile(src, out)
    for name in sorted(USED_IMAGES):
        if name == CREST:
            copy(ROOT / "assets" / "content" / CREST, img_dst / CREST)   # byte for byte
            continue
        if name in DERIVED:
            out_name, args = DERIVED[name]
            out = img_dst / out_name
            src = ROOT / "assets" / "content" / name
            if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
                continue
            if sips:
                subprocess.run([sips, *args, str(src), "--out", str(out)], capture_output=True, check=True)
            else:
                shutil.copyfile(src, out)
            continue
        mapped = IMAGES["map"].get(name, name)
        src = ROOT / "assets" / "img" / mapped
        if not src.exists():
            src = ROOT / "assets" / "content" / name
        if src.exists():
            copy(src, img_dst / mapped)


def main():
    DOCS.mkdir(exist_ok=True)
    count = 0
    write(out_file("/"), render_home())
    count += 1
    for path in sorted(BUILT - {"/"}):
        kind = (PAGES.get(path) or {}).get("type")
        if path == SEARCH:
            doc = render_search(path)
        elif path == "/news":
            doc = render_news_archive(path)
        elif path == "/school-learning-story":
            doc = render_story(path)
        elif kind == "calendar":
            doc = render_calendar(path)
        elif kind == "staff":
            doc = render_staff(path)
        elif kind == "event":
            doc = render_event(path)
        elif kind == "listing":
            doc = render_listing(path)
        elif kind == "article":
            doc = render_article(path)
        else:
            doc = render_page(path)
        write(out_file(path), doc)
        count += 1
    clash = set(REDIRECTS) & BUILT
    assert not clash, "an old URL is also a page: {}".format(sorted(clash))
    for old, new in sorted(REDIRECTS.items()):
        write(out_file(old), redirect_stub(old, new))
    write(DOCS / "404.html", render_404())
    write(DOCS / "assets" / "search.json", build_search_index())
    copy_assets()
    # last: the proposal reports numbers measured on the pages and images written above
    copy_proposal_assets()
    write(out_file(PROPOSAL), render_proposal())
    write(DOCS / ".nojekyll", "")
    write(DOCS / "robots.txt", "User-agent: *\nDisallow: /\n")
    print("built {} pages (+404, {} redirects) for {} into {}".format(count, len(REDIRECTS), TODAY.isoformat(),
                                                                     DOCS.relative_to(ROOT)))


if __name__ == "__main__":
    main()
