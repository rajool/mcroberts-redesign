"""School Learning Story structure from the crawl.

The live /school-learning-story page is a node whose paragraphs are an intro text, then three pairs of
"basic text" (h2 + description) and "article feed" (posts with their Posted date). pages.json keeps only the
post list, so this reads cache/raw/ and writes content/learning-story.json:

    {"intro": "<p>...</p>", "sections": [{"title": "Our Focus", "text": "<p>...</p>",
                                          "items": [{"href": "/school-learning-story/news/...", "posted": "YYYY-MM-DD"}]}]}

Posts the live feed shows only on its second page are placed after the last post of the same feed, in the order
pages.json lists them.

    python3 tools/learning_story.py
"""
import json, re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = "/school-learning-story"


def clean(fragment):
    fragment = re.sub(r"<meta[^>]*>", "", fragment)
    fragment = re.sub(r"\s+", " ", fragment).strip()
    return fragment


def main():
    pages = json.loads((ROOT / "content" / "pages.json").read_text())
    index = json.loads((ROOT / "cache" / "index.json").read_text())
    raw = (ROOT / "cache" / "raw" / index[PATH]["file"]).read_text(errors="replace")
    start = raw.find("<h1")
    end = raw.find("region-footer", start)
    body = raw[start:end if end > 0 else None]

    intro = re.search(r'<div class="mb-5">\s*(<p>.*?</p>)', body, re.S)
    out = {"intro": clean(intro.group(1)) if intro else "", "sections": []}
    # every basic-text paragraph opens a section; the article feed after it fills the section
    for m in re.finditer(r"<h2>(.*?)</h2>(.*?)(?=<h2>|$)", body, re.S):
        title = clean(re.sub(r"<[^>]+>", "", m.group(1)))
        chunk = m.group(2)
        text = re.search(r'field--name-field-section-content[^>]*>\s*(.*?)</div>', chunk, re.S)
        items = []
        for it in re.finditer(r'<h3><a href="(/[^"]+)"[^>]*>.*?</a></h3>.*?<time[^>]*>([^<]+)</time>', chunk, re.S):
            posted = datetime.strptime(re.sub(r"\s+", " ", it.group(2)).strip(), "%b %d %Y").strftime("%Y-%m-%d")
            items.append({"href": it.group(1), "posted": posted})
        if items:
            out["sections"].append({"title": title, "text": clean(text.group(1)) if text else "", "items": items})

    seen = {i["href"]: s for s in out["sections"] for i in s["items"]}
    current = None
    for href in pages[PATH].get("items") or []:
        if href in seen:
            current = seen[href]
            continue
        if current is not None:
            pos = max(n for n, i in enumerate(current["items"]) if i["href"] in seen) + 1
            current["items"].insert(pos, {"href": href, "posted": ""})
            seen[href] = current
    (ROOT / "content" / "learning-story.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(", ".join("{}: {}".format(s["title"], len(s["items"])) for s in out["sections"]))


if __name__ == "__main__":
    main()
