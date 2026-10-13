"""Web-ready copies of the live site's images: assets/content/<name> -> assets/img/<name>.

Longest side at most 1600 px; large opaque PNGs become JPEG. Uses macOS sips only.
Writes content/images.json: the map {original name: web copy name} and each web copy's pixel size.
    python3 tools/images.py

The originals are not in git (only the crest, the Strikers logo and the building photo are): tools/extract.py
downloads them, and `git restore --source=2d09564 --worktree -- assets/content` puts back the 68 of the last commit
that holds them without re-crawling (as ignored files, nothing staged; `git checkout` would stage them). The script
refuses to run, and writes nothing, while an original that content/images.json maps is missing from assets/content,
since it cannot remake that original's web copy.
    python3 tools/images.py --allow-missing   # for an image the live site no longer serves

With --allow-missing, a missing original whose web copy is in assets/img keeps its map and size entries (the copy is
kept as it is, not remade), so a page that still names it builds; an entry with no web copy either is dropped.
"""
import json, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC, DST = ROOT / "assets" / "content", ROOT / "assets" / "img"
INDEX = ROOT / "content" / "images.json"
MAX = 1600
KEEP_PNG = {"39ef9ae7e316.png", "1653644d0ced.png", "ce22c9dd5452.png"}  # crest and district logo: untouched pixels
RESTORE = "git restore --source=2d09564 --worktree -- assets/content"   # the originals of the last commit with them


def props(p):
    for _ in range(5):  # sips occasionally answers before a just-written file is readable
        out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", "-g", "hasAlpha", str(p)], capture_output=True, text=True).stdout
        if "pixelWidth" in out:
            break
        time.sleep(0.3)
    w = int(re.search(r"pixelWidth: (\d+)", out)[1])
    h = int(re.search(r"pixelHeight: (\d+)", out)[1])
    alpha = "hasAlpha: yes" in out
    return w, h, alpha


def read_index():
    """content/images.json as it is: {"map": {original: web copy}, "size": {web copy: [w, h]}}."""
    index = json.loads(INDEX.read_text()) if INDEX.exists() else {}
    return {"map": index.get("map", {}), "size": index.get("size", {})}


def web_copy(src):
    """Make the web copy of one original in assets/img; returns (its name, [width, height])."""
    w, h, alpha = props(src)
    if src.name in KEEP_PNG or src.suffix.lower() == ".gif":
        out = DST / src.name
        out.write_bytes(src.read_bytes())
    else:
        to_jpeg = src.suffix.lower() != ".jpg" and (((not alpha) and src.stat().st_size > 150_000) or src.stat().st_size > 600_000)
        out = DST / (src.stem + (".jpg" if to_jpeg or src.suffix.lower() in (".jpg", ".jpeg") else src.suffix.lower()))
        cmd = ["sips", str(src), "--out", str(out)]
        if max(w, h) > MAX:
            cmd[1:1] = ["-Z", str(MAX)]
        if out.suffix == ".jpg":
            cmd[1:1] = ["-s", "format", "jpeg", "-s", "formatOptions", "78"]
        if len(cmd) == 4:  # nothing to change: sips would not write the file at all
            out.write_bytes(src.read_bytes())
        else:
            subprocess.run(cmd, capture_output=True, check=True)
    w2, h2, _ = props(out)
    return out.name, [w2, h2]


def main():
    old = read_index()
    missing = sorted(n for n in old["map"] if not (SRC / n).is_file())
    if missing and "--allow-missing" not in sys.argv[1:]:
        sys.exit("tools/images.py: assets/content lacks {} of the {} originals that content/images.json maps "
                 "(for example {}). The originals are not in git. To put back the ones of the last commit that holds "
                 "them, without re-crawling: {} (ignored files, nothing staged). Or run the refresh first "
                 "(python3 tools/crawl.py, then python3 tools/extract.py). Then run this script again; with "
                 "--allow-missing it keeps the web copies in assets/img of the originals still missing. "
                 "Nothing was written."
                 .format(len(missing), len(old["map"]), ", ".join(missing[:3]), RESTORE))
    DST.mkdir(parents=True, exist_ok=True)
    made = {}   # original name -> (web copy name, [w, h])
    for p in sorted(SRC.iterdir()) if SRC.is_dir() else []:
        if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            made[p.name] = web_copy(p)
    kept, dropped = [], []
    for name in missing:           # only with --allow-missing: merge the existing entries, do not rebuild without them
        out = old["map"][name]
        if (DST / out).is_file():
            made[name] = (out, old["size"].get(out) or list(props(DST / out)[:2]))
            kept.append(name)
        else:
            dropped.append(name)
    mapping, sizes = {}, {}
    for name in sorted(made):
        out, size = made[name]
        mapping[name], sizes[out] = out, size
    INDEX.write_text(json.dumps({"map": mapping, "size": sizes}, indent=1))
    before = sum(p.stat().st_size for p in SRC.iterdir()) if SRC.is_dir() else 0
    after = sum(p.stat().st_size for p in DST.iterdir())
    print(f"{len(mapping)} images: {before/1e6:.1f} MB -> {after/1e6:.1f} MB")
    if kept:
        print("kept as it is the web copy of {} original(s) not in assets/content: {}{}".format(
            len(kept), ", ".join(kept[:3]), ", ..." if len(kept) > 3 else ""))
    if dropped:
        print(f"dropped from the map, no original and no web copy: {', '.join(dropped)}")


if __name__ == "__main__":
    main()
