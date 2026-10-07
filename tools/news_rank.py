"""Live listing order of the news posts: the position of each post in the crawled /news page, then the
/news/newsletters pages in page order (the live view sorts by created date, so posts that share a date keep the
order the school published them in).

Reads cache/raw/ (via cache/index.json) and writes content/news-rank.json {path: rank}, 0 = newest. The build sorts
every news list by (date desc, rank asc).

    python3 tools/news_rank.py
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r'href="(?:https://mcroberts\.sd38\.bc\.ca)?(/news/20\d\d/\d\d/[^"#?]+)"')


def main():
    index = json.loads((ROOT / "cache" / "index.json").read_text())
    pages = [k for k in index if k.startswith("/news/newsletters?page=")]
    order = ["/news", "/news/newsletters"] + sorted(pages, key=lambda k: int(k.rsplit("=", 1)[1]))
    out = {}
    for key in order:
        if not (index.get(key) or {}).get("file"):
            continue
        raw = (ROOT / "cache" / "raw" / index[key]["file"]).read_text(errors="replace")
        for href in LINK.findall(raw):
            out.setdefault(href, len(out))
    (ROOT / "content" / "news-rank.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"{len(out)} news ranks")


if __name__ == "__main__":
    main()
