"""Article dates from the crawl: the live article page prints "Updated: Monday, October 5, 2026".

pages.json has no date for articles and news.json misses some, so the build reads this map first.
Reads cache/raw/ (via cache/index.json) and writes content/article-dates.json {path: "YYYY-MM-DD"}.

    python3 tools/article_dates.py
"""
import json, re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    pages = json.loads((ROOT / "content" / "pages.json").read_text())
    index = json.loads((ROOT / "cache" / "index.json").read_text())
    out = {}
    for path, page in pages.items():
        if page.get("type") != "article" or path not in index:
            continue
        raw = (ROOT / "cache" / "raw" / index[path]["file"]).read_text(errors="replace")
        m = re.search(r"Updated:</strong>\s*([A-Z][a-z]+, [A-Z][a-z]+ \d{1,2}, \d{4})", raw)
        if m:
            out[path] = datetime.strptime(m.group(1), "%A, %B %d, %Y").strftime("%Y-%m-%d")
    (ROOT / "content" / "article-dates.json").write_text(json.dumps(dict(sorted(out.items())), indent=1) + "\n")
    print(f"{len(out)} article dates")


if __name__ == "__main__":
    main()
