#!/usr/bin/env python3
"""Static checks of the Drupal theme drupal/mcroberts/ (no PHP or Drupal needed; Python standard library only).

    python3 tools/check_drupal.py        # prints problems, exits 1 when there are any

  - YAML (*.yml): no tabs, two-space indentation, every line a key, a list item, a comment or a continuation,
    balanced quotes and flow braces; libraries.yml: every css/js file exists; info.yml: the regions of
    research/drupal-mapping.md are all declared.
  - Twig (*.twig): balanced {% %} block tags (if/for/block/macro/set/verbatim/apply/embed), else/elseif only inside
    if or for, balanced brackets inside every tag and print, every include/extends/import target exists, every
    macro called as m.x is defined in includes/macros.html.twig, every library in attach_library() exists.
  - PHP (*.php, *.theme): balanced (), [] and {} outside strings and comments, every Site::/Calendar::/Teaser::/
    BodyFilter:: call names a method of that class, every _mcroberts_*() call names a function in mcroberts.theme.
  - css/ and js/ identical to theme/ (tools/package_drupal.py --check).
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEME = ROOT / "drupal" / "mcroberts"
PROBLEMS = []


def problem(path, line, msg):
    PROBLEMS.append("{}:{}: {}".format(path.relative_to(ROOT), line, msg))


# ------------------------------------------------------------------------------------------------- YAML
def check_yaml(path):
    lines = path.read_text().split("\n")
    stack = [0]
    for n, raw in enumerate(lines, 1):
        if "\t" in raw:
            problem(path, n, "tab character")
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2:
            problem(path, n, "odd indentation")
        body = line.strip()
        # strip a trailing comment outside quotes
        out, q = "", None
        for ch in body:
            if q:
                out += ch
                if ch == q:
                    q = None
                continue
            if ch in "'\"":
                q = ch
            elif ch == "#" and (not out or out[-1] == " "):
                break
            out += ch
        if q:
            problem(path, n, "unbalanced quote")
        body = out.strip()
        if body.count("{") != body.count("}") or body.count("[") != body.count("]"):
            problem(path, n, "unbalanced flow collection")
        if body.startswith("- "):
            continue
        m = re.match(r"""^('[^']*'|"[^"]*"|[A-Za-z0-9_./@\-]+(?: [A-Za-z0-9_]+)*)\s*:(\s|$)""", body)
        if not m:
            problem(path, n, "not a 'key: value' line: " + body[:60])


def check_libraries(path):
    text = path.read_text()
    for m in re.finditer(r"^\s{6}((?:css|js|bridge|images|fonts)/[^:\s]+):", text, re.M):
        if not (THEME / m.group(1)).exists():
            problem(path, text[:m.start()].count("\n") + 1, "missing file " + m.group(1))
    return set(re.findall(r"^([a-z_]+):\s*$", text, re.M))


def check_info(path):
    text = path.read_text()
    need = ["top_header", "top_header_form", "header", "header_form", "primary_menu", "secondary_menu", "page_top",
            "page_bottom", "highlighted", "featured_top", "breadcrumb", "content", "sidebar_first", "sidebar_second",
            "featured_bottom_first", "featured_bottom_second", "featured_bottom_third", "footer_first", "footer_second",
            "footer_third", "footer_fourth", "footer_fifth", "accessibility_dropdown"]
    regions = text.split("regions:", 1)[1] if "regions:" in text else ""
    for r in need:
        if not re.search(r"^\s{2}" + r + r":", regions, re.M):
            problem(path, 1, "region not declared: " + r)
    for key in ("name:", "type: theme", "base theme: bootstrap_barrio", "core_version_requirement:"):
        if key not in text:
            problem(path, 1, "missing " + key)


# ------------------------------------------------------------------------------------------------- Twig
OPENERS = {"if": "endif", "for": "endfor", "block": "endblock", "macro": "endmacro", "verbatim": "endverbatim",
           "apply": "endapply", "embed": "endembed", "spaceless": "endspaceless", "with": "endwith"}
SIMPLE = {"include", "extends", "import", "from", "set", "else", "elseif", "do", "use", "trans", "endtrans"}


def brackets_ok(s):
    pairs = {"(": ")", "[": "]", "{": "}"}
    st, q = [], None
    for ch in s:
        if q:
            if ch == q:
                q = None
            continue
        if ch in "'\"":
            q = ch
        elif ch in pairs:
            st.append(pairs[ch])
        elif ch in ")]}":
            if not st or st.pop() != ch:
                return False
    return not st and q is None


def check_twig(path, macros, libraries):
    text = path.read_text()
    # verbatim blocks are opaque
    text_scan = re.sub(r"\{%-?\s*verbatim\s*-?%\}.*?\{%-?\s*endverbatim\s*-?%\}", lambda m: "\n" * m.group(0).count("\n"),
                       text, flags=re.S)
    text_scan = re.sub(r"\{#.*?#\}", lambda m: "\n" * m.group(0).count("\n"), text_scan, flags=re.S)
    stack = []
    for m in re.finditer(r"\{%-?(.*?)-?%\}|\{\{-?(.*?)-?\}\}", text_scan, re.S):
        line = text_scan[:m.start()].count("\n") + 1
        inner = (m.group(1) if m.group(1) is not None else m.group(2)).strip()
        if not brackets_ok(inner):
            problem(path, line, "unbalanced brackets or quotes: " + inner[:70])
        if m.group(1) is None:
            for call in re.findall(r"\bm\.([a-z_]+)\(", inner):
                if call not in macros:
                    problem(path, line, "unknown macro m." + call)
            for lib in re.findall(r"attach_library\('mcroberts/([a-z_]+)'\)", inner):
                if lib not in libraries:
                    problem(path, line, "unknown library mcroberts/" + lib)
            continue
        word = inner.split()[0] if inner else ""
        if word in OPENERS:
            if word == "set" or (word == "with" and False):
                pass
            stack.append((word, line))
        elif word == "set":
            # {% set x %}…{% endset %} is the capture form (no "=")
            if "=" not in inner:
                stack.append(("set", line))
        elif word.startswith("end"):
            if not stack:
                problem(path, line, "stray " + word)
                continue
            top, at = stack.pop()
            want = "endset" if top == "set" else OPENERS[top]
            if word != want:
                problem(path, line, "{} closes {} opened on line {}".format(word, top, at))
        elif word in ("else", "elseif"):
            if not stack or stack[-1][0] not in ("if", "for"):
                problem(path, line, word + " outside if/for")
        elif word not in SIMPLE:
            problem(path, line, "unknown tag " + word)
        for target in re.findall(r"(?:include|extends|import|from)\s+'(@mcroberts/[^']+)'", inner):
            if not (THEME / "templates" / target[len("@mcroberts/"):]).exists():
                problem(path, line, "missing template " + target)
        for call in re.findall(r"\bm\.([a-z_]+)\(", inner):
            if call not in macros:
                problem(path, line, "unknown macro m." + call)
    for word, line in stack:
        problem(path, line, "unclosed " + word)


# ------------------------------------------------------------------------------------------------- PHP
def strip_php(text):
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("//", i) or c == "#":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            out.append("\n" * text[i:j].count("\n"))
            i = n if j < 0 else j + 2
            continue
        if c in "'\"":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            out.append(c + "\n" * text[i:j].count("\n") + c)
            i = j + 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def check_php(path, methods, functions):
    text = path.read_text()
    if not text.startswith("<?php"):
        problem(path, 1, "does not start with <?php")
    code = strip_php(text)
    pairs = {"(": ")", "[": "]", "{": "}"}
    st = []
    for k, ch in enumerate(code):
        if ch in pairs:
            st.append((pairs[ch], k))
        elif ch in ")]}":
            if not st or st[-1][0] != ch:
                problem(path, code[:k].count("\n") + 1, "unbalanced " + ch)
                return
            st.pop()
    for want, k in st:
        problem(path, code[:k].count("\n") + 1, "unclosed bracket")
    for cls, meth in re.findall(r"\b(Site|Calendar|Teaser|BodyFilter)::([a-zA-Z_]+)\b(?!\s*::)", code):
        if meth == "class" or meth.isupper() or meth in methods.get(cls, set()):
            continue
        problem(path, 1, "unknown {}::{}".format(cls, meth))
    for fn in re.findall(r"\b(_mcroberts_[a-z_]+)\s*\(", code):
        if fn not in functions:
            problem(path, 1, "unknown function " + fn)
    for m in re.finditer(r"\bself::([a-zA-Z_]+)\b", code):
        name = m.group(1)
        if name.isupper() or name.startswith("$"):
            continue
    return code


def main():
    for y in sorted(THEME.rglob("*.yml")):
        check_yaml(y)
    libraries = check_libraries(THEME / "mcroberts.libraries.yml")
    check_info(THEME / "mcroberts.info.yml")
    macros = set(re.findall(r"\{%\s*macro\s+([a-z_]+)\(", (THEME / "templates/includes/macros.html.twig").read_text()))
    for t in sorted(THEME.rglob("*.twig")):
        check_twig(t, macros, libraries)
    methods = {}
    for cls in ("Site", "Calendar", "Teaser", "BodyFilter"):
        src = (THEME / "src" / (cls + ".php")).read_text()
        methods[cls] = set(re.findall(r"function\s+([a-zA-Z_]+)\s*\(", src)) | set(re.findall(r"const\s+([A-Z_]+)\s*=", src))
    functions = set(re.findall(r"^function\s+([a-z_]+)\s*\(", (THEME / "mcroberts.theme").read_text(), re.M))
    for p in sorted(list(THEME.rglob("*.php")) + [THEME / "mcroberts.theme"]):
        check_php(p, methods, functions)
    for js in sorted((THEME / "bridge").glob("*.js")):
        r = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
        if r.returncode:
            problem(js, 1, r.stderr.strip().splitlines()[0] if r.stderr.strip() else "node --check failed")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "package_drupal.py"), "--check"], capture_output=True, text=True)
    if r.returncode:
        PROBLEMS.append(r.stdout.strip())
    twig = len(list(THEME.rglob("*.twig")))
    php = len(list(THEME.rglob("*.php"))) + 1
    yml = len(list(THEME.rglob("*.yml")))
    print("check_drupal: {} Twig, {} PHP, {} YAML files: {} problems".format(twig, php, yml, len(PROBLEMS)))
    for p in PROBLEMS:
        print("  " + p)
    sys.exit(1 if PROBLEMS else 0)


if __name__ == "__main__":
    main()
