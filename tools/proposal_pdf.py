"""Print the proposal page (docs/proposal/) to the US Letter PDF beside it, with headless Google Chrome.

The page must be served over HTTP (it loads Google Fonts and its screenshots), for example by a local server on docs/.
Its print stylesheet (design/proposal/proposal.css, @page size: letter) sets the paper; this script then checks that
every page of the PDF is 612 x 792 pt and that every screenshot the page shows is in the PDF as a picture (not a
broken-image icon): it prints again once if not, then fails. Run it after build.py whenever the proposal changes,
then run build.py once more: the page links the PDF only when the file exists.

    python3 tools/proposal_pdf.py                       # http://127.0.0.1:8790/proposal/
    python3 tools/proposal_pdf.py http://host/path/proposal/
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "proposal" / "mcroberts-website-redesign-proposal.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
LETTER = (612.0, 792.0)


def media_boxes(pdf):
    data = pdf.read_bytes()
    pages = len(re.findall(rb"/Type\s*/Page\b", data))
    boxes = [tuple(float(x) for x in m.split()) for m in re.findall(rb"/MediaBox\s*\[\s*([^\]]+?)\s*\]", data)]
    return pages, boxes


def pictures(pdf):
    """Image XObjects at least 100 px wide: the screenshots. A broken image prints as a 16 px icon."""
    data = pdf.read_bytes()
    n = 0
    for chunk in re.split(rb"\bendobj\b", data):
        head = chunk.split(b"stream", 1)[0]
        if re.search(rb"/Subtype\s*/Image\b", head):
            w = re.search(rb"/Width\s+(\d+)", head)
            if w and int(w.group(1)) >= 100:
                n += 1
    return n


def screenshots():
    """The distinct screenshot files the built page shows (docs/proposal/index.html)."""
    html = (OUT.parent / "index.html").read_text()
    return len(set(re.findall(r'<img\b[^>]*?\ssrc="(img/[^"]+)"', html)))


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8790/proposal/"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    want = screenshots()
    for attempt in (1, 2):
        # the virtual time budget lets every screenshot load and decode before Chrome prints
        subprocess.run([CHROME, "--headless=new", "--no-pdf-header-footer", "--virtual-time-budget=15000",
                        "--print-to-pdf={}".format(OUT), url], check=True, capture_output=True)
        got = pictures(OUT)
        if got >= want:
            break
        print("only {} of {} screenshots printed as pictures{}".format(got, want, ", printing again" if attempt == 1 else ""))
    pages, boxes = media_boxes(OUT)
    sizes = {(b[2] - b[0], b[3] - b[1]) for b in boxes}
    ok = pages > 0 and sizes == {LETTER}
    print("{}: {} pages, MediaBox {} ({}), {} of {} screenshots as pictures".format(
        OUT.relative_to(ROOT), pages, ", ".join("{:g} x {:g} pt".format(*s) for s in sorted(sizes)),
        "US Letter" if ok else "NOT US Letter", got, want))
    sys.exit(0 if ok and got >= want else 1)


if __name__ == "__main__":
    main()
