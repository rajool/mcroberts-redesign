# McRoberts: Drupal 10 theme

The redesign of https://mcroberts.sd38.bc.ca (École Secondaire Hugh McRoberts Secondary School) as a Drupal 10
sub-theme of Bootstrap Barrio. It prints the same markup as the static preview (`build.py` in the repository),
with the same CSS and JavaScript, on the site's own content and configuration.

> **Status: untested on a live Drupal instance; verify on a staging copy.** No PHP or Drupal ran while this
> package was written. Every file was checked statically (`tools/check_drupal.py`: YAML structure, Twig tag
> balance and include targets, PHP bracket balance and cross-references, the bridge JavaScript through
> `node --check`) and re-read, and the APIs were checked against the Drupal 10.3+ and contrib sources the research
> read (`research/drupal-mapping.md`). Install it on a Platform.sh branch environment of the McRoberts site first;
> the checklist at the end lists what to look at.

## Requirements

- Drupal 10.3 or later (or 11), PHP 8.1 or later.
- Bootstrap Barrio 5.5.x, the base theme of the district theme `rsd_sites_barrio` (already in the district codebase).
- Core modules already on the site: Views, Search, Menu UI, Path alias, Block, Block Content, Media.
- Recommended: Redirect (answers the old URLs with a 301). Used when present, never required: Display Suite,
  a11y, GTranslate, Social Media Links, bootstrap_paragraphs, fullcalendar_view.
- No new contrib module, no build step, no CDN. Google Fonts (Newsreader, Noto Sans) is the only external file,
  declared as an external library (`mcroberts/fonts`).

## Install

On a **staging copy** (Platform.sh branch environment: production database and files, cloned):

1. Put the folder at `web/themes/custom/mcroberts/` in the district codebase (one deploy; inert for every other
   SD38 school site, which never enables it).
2. `drush theme:install mcroberts` **while `rsd_sites_barrio` is still the default theme**. Core then copies every
   block placement into `mcroberts` (same plugins, settings, visibility, weights, and regions: the theme declares
   every live region machine name). The copy only happens for a theme with no blocks, so the theme ships none.
3. `drush php:script themes/custom/mcroberts/config-changes/apply.php` prints the plan; add `-- --apply` to apply
   it (URL aliases, redirects, menus, block placements; see `config-changes/README.md`).
4. `drush config:set system.theme default mcroberts && drush cache:rebuild`.
5. If the site deploys with `drush config:import`, export and commit the McRoberts configuration
   (`core.extension`, `system.theme`, `mcroberts.settings`, `block.block.mcroberts_*`, `system.menu.*`), or the next
   deploy reverts it. Menu links, aliases and redirects are content entities and stay.

The same in the UI: *Appearance → McRoberts → Install*, then the tables in `config-changes/` (*Structure → Menus*,
*Configuration → URL aliases / URL redirects*, *Structure → Block layout → McRoberts*), then *Set as default*.

Theme settings (`config/install/mcroberts.settings.yml`, change with `drush config:set mcroberts.settings …`):
`mcroberts_concept_banner` (off: the preview's "design concept" banner and `noindex`, for a public demo copy only),
`mcroberts_paths` (the pages the theme links to by alias), `mcroberts_webcal` (the calendar feed), and fallbacks for
the contact details, the Student Absent? pair and the Translate languages, used only when the site's own data is
missing.

## How it maps to the live site (zero content migration)

Nothing in any node, paragraph, media item or field changes. The theme reads what is there:

| On the page | Drupal source |
|---|---|
| District strip, Student Absent? pill, sign-ins | menu `utility` (region secondary_menu), hardcoded district logo as on live |
| Crest lockup | view `site_header_content_block` (region top_header); the crest is `logo.png`, the original file byte for byte, and `images/39ef9ae7e316-*.png` its scaled copies |
| Translate, Accessibility Settings, Search | the theme's controls on every page (GTranslate languages from its configuration, the a11y module's class contract, GET `/search/node?keys=`) |
| Mega menu, phone menu, section menu, previous/next, breadcrumb hub | menu `main` (3 levels: item, column, link) |
| Alert band | view `news_alerts` (region featured_top), only when it has rows |
| Page header, body, hub cards, rail | the node templates (`templates/content/`), fed by `mcroberts_preprocess_node()`; hub cards from menu `main` or menu `hub-links` |
| Rich text | the body and paragraph text fields, restructured at render time by `src/BodyFilter.php` (typed bullets → lists, layout tables → their layout, phone numbers → `tel:` links, heading ids for deep links, …); the stored text never changes |
| Accordions, documents | `paragraph--bp-accordion.html.twig` (native `<details>`), `field--field-media-file.html.twig` and `field--field-legacy-attachments.html.twig` (file cards) |
| Front page | `page--front.html.twig`: Today (calendar_event nodes + the bell schedule), Helpful Links (sidebar_second: the Student Absent? note, district quick links, home page buttons), Latest News (view `frontpage`), Upcoming Events (view `upcoming_events`), the Parents and Students lists (menu `hub-links`) |
| School Calendar | `node--calendar-page.html.twig`: agenda + month grid from the published calendar_event nodes (FullCalendar from unpkg is not loaded) |
| Bell Schedule | the timetable image becomes tables (`misc/mcroberts-bell-schedule.html.twig`, data in `data/bell-schedule.json`, transcribed word for word) |
| Our Staff | `node--staff-page.html.twig` + view `staff_page_list` (block_2), grouped tables with a filter |
| Footer | menu `footer` (region footer_first), Social Media (region footer_second), the address block's data, district logo and copyright |

**Display Suite stays as it is.** The live node displays render through DS layouts (`ds_entity_view`), which skip
`node.html.twig`. The theme adds a template suggestion for the five node types it composes and routes them to the
same node templates (`ds-entity-view--mcroberts-node-*.html.twig`), with the node's fields. A node display without a
DS layout uses `node--*.html.twig` directly.

**Bootstrap is not loaded.** `libraries-override` switches off Bootstrap and Barrio's component CSS and the module
skins the theme replaces (Font Awesome CDN, bootstrap_paragraphs, fitvids, colorbox skin). The Bootstrap classes that
configuration still prints (DS layouts, views_bootstrap grids) get a small `bridge/compat.css`.

## Front-end code

`css/` and `js/` are byte-for-byte copies of the preview's `theme/` folder, written by `tools/package_drupal.py`
(never edit the copies; it also refuses to zip when they differ). `bridge/` holds the only Drupal-specific files:

- `mcroberts.pre.js` and `mcroberts.post.js` wrap every feature in `Drupal.behaviors` (one behavior per feature,
  `Drupal.behaviors.mcroberts<Name>`) and hand the element marking to `core/once`. No jQuery.
- `compat.css` (the Bootstrap classes configuration still prints; typed fonts and colours inside rich text) and
  `drupal.css` (status messages, editor tabs, the toolbar offset).

Page-specific libraries are attached by the templates that need them: `mcroberts/today` (front page),
`calendar`, `bell`, `filter`, `gallery`, `views`.

## The new information architecture: configuration

`config-changes/` holds the menus (`menus.md`), the 28 changed URL aliases and 5 retired pages (`urls.md`,
`redirects.csv`) and the block placements (`blocks.md`), plus `apply.php`, which applies them with a dry run and a
log. In short:

- menu `main`: the live links are disabled (not deleted) and the 7-item tree is created; new menus `utility`,
  `footer` and `hub-links`. A column title in square brackets is an admin name the theme does not print.
- URL aliases change on the nodes themselves (`/information/our-staff` → `/about-us/our-staff` …); the Redirect
  module answers every old alias with a 301.
- blocks of `mcroberts` only: the utility and footer menu blocks are added, Social Media moves to the footer, the
  a11y block shows on every page, and the blocks the theme now prints itself (footer copy of the main menu, Log in,
  the address block, GTranslate, the search form, two empty notes) are disabled.

## Roll back

1. `drush config:set system.theme default rsd_sites_barrio` (one value; `rsd_sites_barrio` and its blocks were never
   changed).
2. `drush php:script themes/custom/mcroberts/config-changes/apply.php -- --rollback` re-enables the live main menu
   links, removes the new links and menus, restores the old aliases, removes the redirects, republishes retired
   pages and restores the `mcroberts` blocks (everything in the state key `mcroberts_ia.log`).
3. `drush theme:uninstall mcroberts` if wanted.

## Where it differs from the static preview

- Search is core search, rendered on the server (`/search/node?keys=`); the advanced search form is left out.
- News Archive and the newsletters feed use Drupal's pager; the preview's All / Newsletters switch is not there.
- News dates are the node's created ("Posted:") and changed ("Updated:") times.
- Every calendar event links to its own node (the preview links only the events whose pages it built).
- The School Calendar panel of the mega menu is rendered per day; it is not re-read in the browser on a later day.
- Translate and Accessibility Settings run the preview's own scripts (Google page translation through the
  `googtrans` cookie; colour tokens instead of page filters); the GTranslate widget and the a11y module's scripts
  are not loaded, while their blocks, settings and class contracts stay.
- Image galleries (colorbox), the Library banner slideshow, tile links and image + text paragraphs print their
  module and DS markup, with `bridge/compat.css`; the preview restyled them from flattened content.
- Copy the preview shows from other pages is in the templates: the front page's hero line, About Us, Mission
  Statement and Strikers sentences (`page--front.html.twig`). The bell schedule data and the pictures of the menu
  and Library tiles are theme files (`data/`, `images/`). A school edit of those pages does not reach them.
- The page-specific restructuring of Contact Us, Student Attendance, Strikers Athletics and the Library applies
  only when the body has the structure the live page has; otherwise the body prints as written.
- School Learning Story prints its paragraphs and article feed as cards, not the preview's numbered story list;
  the PAC Meeting Minutes and Agendas keep one file list per paragraph, not one list sorted by meeting date.

## Verify on the staging copy

1. After `theme:install`: `drush config:get block.block.mcroberts_<id>` for the blocks in `config-changes/blocks.md`;
   no block fell into `content`.
2. Display Suite: the five node types render through the theme's templates (look for `page-hero` on a basic page,
   an article, an event, School Calendar and Our Staff).
3. Views: the `views-element-container` wrapper is gone around the quick links, home buttons, alerts, site header
   and upcoming events (the container suggestions `container__view__<view>__<display>`); field names used in the
   preprocess (`field_event_date`, `field_content_area`, `field_link`, `bp_accordion_section`) match, and the
   Social Media Links template still receives `platforms` with a `url` per platform.
4. Front page: Helpful Links lists the Student Absent? note first, then the three day tiles, then the quick links.
5. Menus: the mega panels show all three levels; `[Most requested]` columns print no heading.
6. Redirects: every row of `redirects.csv` answers 301; `/node/1813` and `/media/1069` reach their new aliases.
7. Caching: today-dependent parts (Today, School Calendar, Bell Schedule, Upcoming Events) set a max-age to midnight;
   if the anonymous page cache serves pages longer, the scripts still correct them in the browser.
8. Lighthouse and axe on `/`, `/about-us`, `/school-calendar`, `/about-us/our-staff`, `/news/newsletters`.

## Files

```
mcroberts.info.yml          regions (the live machine names), libraries-override, logo
mcroberts.libraries.yml     fonts, global, views, today, calendar, bell, filter, gallery, pager
mcroberts.theme             preprocess hooks and template suggestions
logo.png                    the crest, the original file byte for byte
config/install, config/schema   theme settings
src/                        Site (menus, sections, contact), Teaser (card lines, news items),
                            Calendar (events, bell schedule, today), BodyFilter (rich text at render time)
css/, js/                   copies of the preview's theme/ (tools/package_drupal.py)
bridge/                     Drupal.behaviors + core/once adapter; compat.css, drupal.css
data/                       bell-schedule.json, image-text.json, tiles.json, empty.json
images/                     scaled crest, district logo, header photo, front-page and tile pictures
templates/layout            html, page, page--front, page--404, regions
templates/block             block wrappers (main menu, events band, Student Absent? note, a11y, search, …)
templates/navigation        menu--main (mega menu), menu--utility, menu--footer, breadcrumb, pagers
templates/views             frontpage, upcoming_events, news_alerts, site header, quick links, home buttons,
                            staff list, news archive, article feed, view containers
templates/content           node--page, node--article (+ teaser), node--calendar-event, node--calendar-page,
                            node--staff-page, and their Display Suite routes
templates/paragraphs        paragraph--bp-accordion
templates/field             file cards, entity reference lists
templates/form, misc        search form and results, status messages, social links, the bell schedule
templates/includes          shared partials and macros (icon sprite, lockup, drawer, hero, rail, cards …)
config-changes/             menus, URL aliases, redirects, block placements, apply.php
```
