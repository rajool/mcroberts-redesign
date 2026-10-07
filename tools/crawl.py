"""Crawl the live McRoberts site into cache/raw/ so the redesign uses only its real content.

Standard library only. Polite: one request at a time with a short delay, robots.txt paths skipped.
    python3 tools/crawl.py            # crawl (reuses cached pages)
    python3 tools/crawl.py --refresh  # refetch everything
"""
import hashlib, json, re, sys, time, urllib.parse, urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE = "https://mcroberts.sd38.bc.ca"
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "cache" / "raw"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
SKIP_PREFIX = ("/user", "/search", "/admin", "/node/add", "/core", "/profiles", "/filter", "/comment", "/media/oembed", "/modules", "/themes", "/files", "/sites")
ASSET_EXT = re.compile(r"\.(pdf|docx?|xlsx?|pptx?|jpe?g|png|gif|svg|webp|mp4|mp3|zip|ics|csv|txt)(\?|$)", re.I)
EVENT = re.compile(r"^/\d{4}/[^/]+$")
NEWS_ITEM = re.compile(r"^/news/\d{4}/\d{2}/")
MAX_PAGES = 420
MAX_NEWS_ITEMS = 45
MAX_EVENTS = 25


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def norm(href, page):
    href = urllib.parse.urljoin(page, href.strip())
    u = urllib.parse.urlsplit(href)
    if u.scheme not in ("http", "https") or u.netloc not in ("mcroberts.sd38.bc.ca", "www.mcroberts.sd38.bc.ca"):
        return None
    path = urllib.parse.unquote(u.path) or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    q = u.query if (path in ("/news", "/news/newsletters", "/node") and u.query.startswith("page=")) else ""
    return path + ("?" + q if q else "")


def fname(key):
    slug = re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-") or "home"
    return slug[:90] + "-" + hashlib.sha1(key.encode()).hexdigest()[:6] + ".html"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.geturl(), r.read().decode("utf-8", "replace")


def main():
    refresh = "--refresh" in sys.argv
    RAW.mkdir(parents=True, exist_ok=True)
    index_path = ROOT / "cache" / "index.json"
    index = {} if refresh or not index_path.exists() else json.loads(index_path.read_text())
    queue, seen = ["/"], {"/"}
    news_n = ev_n = 0
    assets = {}
    while queue and len(index) < MAX_PAGES:
        key = queue.pop(0)
        url = BASE + key
        entry = index.get(key)
        if entry and (RAW / entry["file"]).exists() and not refresh:
            html = (RAW / entry["file"]).read_text()
        else:
            try:
                status, final, html = fetch(url)
            except Exception as e:  # keep going; record the failure
                index[key] = {"file": None, "error": str(e)}
                print("ERR", key, e)
                continue
            f = fname(key)
            (RAW / f).write_text(html)
            index[key] = {"file": f, "status": status, "final": final}
            time.sleep(0.25)
            print(len(index), key)
        p = Links()
        p.feed(html)
        for href in p.links:
            if href.startswith(("mailto:", "tel:", "#", "javascript:")):
                continue
            if ASSET_EXT.search(href):
                a = urllib.parse.urljoin(url, href)
                assets.setdefault(a, set()).add(key)
                continue
            k = norm(href, url)
            if not k or k in seen or k.startswith(SKIP_PREFIX):
                continue
            if k.startswith("/node?page=") and int(k.split("=")[1]) > 3:
                continue
            if k.startswith("/news?page=") and int(k.split("=")[1]) > 3:
                continue
            if EVENT.match(k):
                if ev_n >= MAX_EVENTS:
                    continue
                ev_n += 1
            if NEWS_ITEM.match(k):
                if news_n >= MAX_NEWS_ITEMS:
                    continue
                news_n += 1
            seen.add(k)
            queue.append(k)
    index_path.write_text(json.dumps(index, indent=1, sort_keys=True))
    (ROOT / "cache" / "assets.json").write_text(json.dumps({a: sorted(v) for a, v in sorted(assets.items())}, indent=1))
    print("pages", len(index), "assets", len(assets), "queue left", len(queue))


if __name__ == "__main__":
    main()
