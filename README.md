# McRoberts website redesign (design concept)

A redesign proposal for École Secondaire Hugh McRoberts Secondary School (Richmond, BC). The live site is
https://mcroberts.sd38.bc.ca, a Drupal 10 site. This repo turns the live site's own content into a static preview of
the new design, built with the same front-end code a Drupal 10 sub-theme of `bootstrap_barrio` would use.

The rules are in `design/BRIEF.md`. In short: the crest is never altered, the site stays on Drupal 10, there are no
new words, every page carries the concept banner and `noindex`, and no third-party libraries are used.

## Build

Python 3.9 or later, standard library only. On macOS, `sips` makes the resized image copies.

    python3 build.py                          # renders content/ into docs/ for today (America/Vancouver)
    BUILD_DATE=2026-10-16 python3 build.py    # as if it were another day
    SITE_BASE=/mcroberts-redesign/ python3 build.py   # optional: fixes the 404 page's base for a known sub-path

`docs/` is the GitHub Pages site. Every link is relative, so it works at any sub-path. Never edit `docs/` by hand:
change `theme/` or `build.py`, then rebuild. Parts that depend on the date (Today card, Upcoming Events, the
calendar's current month, Collaboration Days) are rendered for the build day and refreshed in the browser.

To refresh the content from the live site:

    python3 tools/crawl.py           # live pages → cache/raw/ (not in git)
    python3 tools/extract.py         # cache/raw/ → content/*.json (pages, menu, site, news, events)
    python3 tools/images.py          # assets/content/ → assets/img/ (web sizes) + content/images.json
    python3 tools/inventory.py       # content/corpus.txt (every phrase the live site shows) + INVENTORY.md
    python3 tools/article_dates.py   # content/article-dates.json
    python3 tools/learning_story.py  # content/learning-story.json
    python3 build.py

### The proposal

`docs/proposal/` is the proposal to the principal, linked from the concept banner ("About this concept"). `build.py`
renders it last (`render_proposal`), from its stylesheet and screenshots in `design/proposal/` and from numbers it
measures on the build itself. Its print stylesheet makes a five-page US Letter document. To make the PDF beside it:

    python3 build.py
    python3 tools/proposal_pdf.py      # headless Google Chrome prints http://127.0.0.1:8790/proposal/ and checks the page size
    python3 build.py                   # the page links the PDF once the file exists

`PREVIEW_URL=https://… python3 build.py` makes the proposal's preview link absolute and writes the address out, which
the PDF needs once the preview has a public address. The proposal links `docs/downloads/mcroberts-drupal-theme.zip`
when the build finds it.

## Folders

| Folder | What it holds |
|---|---|
| `design/` | The brief, the chosen direction (`decision.md`), the site structure (`ia.json`, explained in `ia.md`), and the proposal's stylesheet and screenshots (`proposal/`) |
| `research/` | Audit of the live site, benchmark, best practices, and how every component maps to Drupal (`drupal-mapping.md`) |
| `content/` | The live site's content as data. `corpus-images.txt` holds the words shown inside images, transcribed |
| `assets/` | The live site's images (`content/`, originals; the crest is `39ef9ae7e316.png`) and web copies (`img/`) |
| `theme/` | The front-end code shared with the Drupal theme: `css/` (tokens, base, layout, components, pages, views, print) and `js/` (vanilla behaviours, each started from an `attach(context)` function) |
| `drupal/mcroberts/` | The Drupal 10 sub-theme of Bootstrap Barrio (templates, preprocess, the IA as configuration changes); its `css/` and `js/` are copies of `theme/`. See its README |
| `build.py` | Renders `content/` with `theme/` into `docs/` |
| `tools/` | Crawler, extractor, image and inventory scripts, and the checks |
| `concepts/` | The three first concepts; `heritage` was chosen |
| `docs/` | The built site (generated) |
| `shots/`, `cache/` | Screenshots and the crawl cache (not in git) |

## Drupal theme

    python3 tools/package_drupal.py   # theme/ → drupal/mcroberts/{css,js}, images, data, generated config-changes,
                                      # then docs/downloads/mcroberts-drupal-theme.zip (same bytes on a rebuild)
    python3 tools/check_drupal.py     # static checks of the theme: YAML, Twig, PHP, the css/js copies

Run both after a change to `theme/`, `design/ia.json` or `drupal/`, and after `python3 build.py` on a clean `docs/`
(the zip lives in `docs/downloads/`). No PHP or Drupal is needed for either.

## Checks

All five must pass after every change:

    python3 build.py                        # builds without errors
    python3 tools/check_copy.py docs        # 0 phrases not on the live site
    python3 tools/check_site.py docs        # 0 problems: links, assets, ids, redirects, banner, noindex
    python3 tools/check_ia.py design/ia.json   # 0 problems in the site structure
    python3 tools/check_fidelity.py         # 0 missing pages, 0 dropped fragments, 0 new words, and nothing
                                            # of the live HTML (text, links, videos) missing from the build

`check_copy` reads every visible phrase, including `aria-hidden` text, and accepts only the live site's words,
`content/corpus-images.txt` and the short list of UI words in `tools/ui_words.txt`. `check_fidelity` compares each
page twice: with the extracted content, and directly with the crawled live HTML (`cache/raw/`), so a gap in the
extractor cannot hide. Add `-v` to either for details.

One documented exception: both skip `docs/proposal/`. The proposal is the document about this concept, not school
content, so it is the one page allowed new words. `check_site` still checks it like every other page.

## Notes for the school

- Calendar titles typed in capitals ("PRO-D DAY - NO SCHOOL") are shown in title case. The words are unchanged.
- The live Student Login page links to `/form/myed-bc-portal-request-assistanc`, which returns 404 on the live site.
  The preview keeps the link as it is. In Drupal it should point to the MyEd Student Portal: Request Assistance page.
- The Translate block lists the languages set in the live GTranslate block. Adding Traditional Chinese, Punjabi,
  Tagalog, Farsi, Korean and Vietnamese, the home languages of many Richmond families, is a block setting.
