"""Web-ready copies of the live site's images: assets/content/<name> -> assets/img/<name>.

Longest side at most 1600 px; large opaque PNGs become JPEG. Uses macOS sips only.
Prints a JSON map {original name: optimized name} into content/images.json.
    python3 tools/images.py
"""
import json, re, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC, DST = ROOT / "assets" / "content", ROOT / "assets" / "img"
MAX = 1600
KEEP_PNG = {"39ef9ae7e316.png", "1653644d0ced.png", "ce22c9dd5452.png"}  # crest and district logo: untouched pixels


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


def main():
    DST.mkdir(parents=True, exist_ok=True)
    mapping, sizes = {}, {}
    for p in sorted(SRC.iterdir()):
        if p.suffix.lower() not in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            continue
        w, h, alpha = props(p)
        if p.name in KEEP_PNG or p.suffix.lower() == ".gif":
            out = DST / p.name
            out.write_bytes(p.read_bytes())
        else:
            to_jpeg = p.suffix.lower() != ".jpg" and (((not alpha) and p.stat().st_size > 150_000) or p.stat().st_size > 600_000)
            out = DST / (p.stem + (".jpg" if to_jpeg or p.suffix.lower() in (".jpg", ".jpeg") else p.suffix.lower()))
            cmd = ["sips", str(p), "--out", str(out)]
            if max(w, h) > MAX:
                cmd[1:1] = ["-Z", str(MAX)]
            if out.suffix == ".jpg":
                cmd[1:1] = ["-s", "format", "jpeg", "-s", "formatOptions", "78"]
            if len(cmd) == 4:  # nothing to change: sips would not write the file at all
                out.write_bytes(p.read_bytes())
            else:
                subprocess.run(cmd, capture_output=True, check=True)
        w2, h2, _ = props(out)
        mapping[p.name] = out.name
        sizes[out.name] = [w2, h2]
    (ROOT / "content" / "images.json").write_text(json.dumps({"map": mapping, "size": sizes}, indent=1))
    before = sum(p.stat().st_size for p in SRC.iterdir())
    after = sum(p.stat().st_size for p in DST.iterdir())
    print(f"{len(mapping)} images: {before/1e6:.1f} MB -> {after/1e6:.1f} MB")


if __name__ == "__main__":
    main()
