# Redesign brief: Hugh McRoberts Secondary website

A design proposal by a parent (Ali Rajool, PAC Co-Treasurer) for the principal, Mr. Jason Leslie. Goal: the most modern,
usable and beautiful secondary-school website we can make, built only from what the school already has.

## Hard constraints (never break)

1. **Logo is identity, untouched.** Use `assets/content/39ef9ae7e316.png` (the crest, 400x348, transparent PNG) as-is:
   no recolour, crop, redraw, filter, shadow or re-typesetting. Give it clear space. Scaling is fine.
   The colour system may be *derived* from it (forest green ~#1f4d2b, black, white).
2. **Platform stays Drupal 10.** The live site is Drupal 10 on Platform.sh with the district theme `rsd_sites_barrio`
   (a sub-theme of contrib `bootstrap_barrio`, Bootstrap 5). The redesign must be deliverable as a Drupal 10 theme
   (a new sub-theme of `bootstrap_barrio`) using the *same* content types, views, blocks, menus and regions.
   So: server-rendered HTML, progressive enhancement, vanilla JS only, CSS custom properties, no React/Vue/SPA,
   no build step Drupal cannot host. Every component must map to a Drupal construct (region, block, view, field,
   paragraph type, menu); see `research/drupal-mapping.md`.
3. **No new words.** Every visible phrase comes from the live site (`content/corpus.txt`): headings, the slogan
   ("Learning Together... Achieving Our Dreams"), page copy, menu labels, block titles ("Latest News", "Upcoming Events",
   "Student Absent?", "News Archive", "Search", "Translate", "Social Media", "Accessibility Settings",
   "Subscribe to our calendar", "Skip to main content", "Read more", "Close"). Restructuring, regrouping, re-ordering,
   turning typed bullets into real lists, or turning an image of a table into a real table (same words) is fine.
   Tiny UI chrome with no content meaning (e.g. "Menu", "Back to top", arrows, dates formatted differently) is allowed
   but keep it minimal and list each such word in `tools/ui_words.txt`.
4. **Concept banner.** Every page carries a slim, clearly visible banner saying it is a design concept and not the
   official site, linking to https://mcroberts.sd38.bc.ca, plus `<meta name="robots" content="noindex,nofollow">`.
   This banner is the only meta copy allowed.
5. **Supply chain.** No third-party libraries, CDNs or icon fonts. Allowed: Google Fonts, our own inline SVG icons,
   the Python standard library for the build, the OS's `sips` for images.

## Quality bar

- WCAG 2.2 AA (contrast, visible focus, target size, keyboard menus, reduced motion, skip link, landmarks, alt text).
- Mobile-first; excellent at 360px and at 1440px. Fast: no layout shift, lazy images, small CSS and JS.
- Parents' top tasks one tap away: report an absence (604-668-6600, Ext. 1), calendar, news and the Striker Weekly,
  MyEd, School Cash Online, bell schedule, contact. Students: MyEd, Office 365, counselling, career centre, grad.
- Multilingual families (Richmond): the existing Translate (GTranslate) block stays, and is easy to find.
- Feels like *this* school: green crest, the Strikers, French Immersion (École), since 1962.

## Sources

`content/` (pages.json, menu.json, site.json, news.json, events.json, INVENTORY.md, corpus.txt), `assets/content/`
(images from the live site), `cache/raw/` (raw crawled HTML of the live site, for reference only).
