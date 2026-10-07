# Drupal mapping: live McRoberts site → `mcroberts` sub-theme

How https://mcroberts.sd38.bc.ca is built (reverse-engineered from the 191 crawled pages in `cache/raw/`, the live theme's
public CSS/JS, and the contrib sources on git.drupalcode.org), and exactly how a new Drupal 10 sub-theme `mcroberts`
(base theme `bootstrap_barrio`) delivers the redesign with **zero content migration and zero configuration migration**.

Evidence keys used below: **[M]** seen in crawled markup, **[S]** seen in `drupalSettings`, **[C]** seen in the live theme
CSS/JS (`/themes/custom/rsd_sites_barrio/css/style.css`, `js/global.js`, the Color-module `colors.css`), **[D]** read in
the contrib/core source on git.drupalcode.org, **[I]** inferred (verify on a branch environment, section 14).

---

## 1. Platform facts

| Fact | Value | Evidence |
|---|---|---|
| Core | Drupal **10.6.14** (`?v=10.6.14` on core JS), PHP side unknown | [M] |
| Hosting / topology | Platform.sh, **one shared codebase for all SD38 school sites** (multisite: files under `/files/mcroberts/`). `rsd_sites_barrio` is the district theme on boyd, mcnair, palmer, mcmath, macneill … (all checked live) | [M] |
| Theme chain | `rsd_sites_barrio` (custom, district) → `bootstrap_barrio` (contrib 5.5.x; 5.5.20 supports `^10.3 \|\| ^11`) | [M][D] |
| Bootstrap | **5.2.0 from cdn.jsdelivr.net** (CSS + bundle JS), attached by both `bootstrap_barrio/bootstrap_cdn` and `rsd_sites_barrio/bootstrap_cdn` | [M][S] |
| Colour | contrib **Color** module: `/files/mcroberts/color/rsd_sites_barrio-1548cbd3/colors.css` (header gradient `#335f4a → #50976f`, accent `#51ba8d`) | [M][C] |
| Icons | Font Awesome **6.6.0 from cdnjs** (front page only, via social_media_links), Bootstrap-Icons SVGs inlined by templates | [M] |
| Analytics | `google_analytics` module, GA4 `G-Q9N69RR4TH` | [S] |
| Asset aggregation | **OFF**: home loads 63 CSS + 28 JS files; average 83 CSS/JS requests per page | [M] |
| jQuery | 3.7.1 on every page (core views AJAX, fitvids, colorbox, cycle2, global.js) | [M] |
| Third-party runtime | jsdelivr (Bootstrap, js-cookie, rrule, OpenDyslexic font), cdnjs (FA, cycle2), unpkg (FullCalendar 4.4.2, moment), cdn.gtranslate.net, googletagmanager | [M] |

---

## 2. Live page skeleton (rsd_sites_barrio `page.html.twig`, as rendered)

```
body.HAS-HEADER-IMG.layout-{no|two}-sidebars.has-featured-top.path-*.page-node-N.node--type-*
└ .dialog-off-canvas-main-canvas > #page-wrapper > #page
  ├ header#header.header[role=banner][aria-label="Site header"]
  │ ├ #district-branding  (HARDCODED: link to sd38.bc.ca, .district-logo "District Logo" + .district-statement "Slogan",
  │ │                      both text-indented CSS background images sd38-brand-logo.png / sd38-brand-statement.png)
  │ ├ #header-img-area    (background photo injected by bg_image_formatter <style> targeting "body #header-img-area")
  │ │ ├ .col-lg-9 > section.region.region-top-header       → site_header_content_block view (logo, <h1> name, <em> slogan)
  │ │ └ .col-lg-3 > section.region.region-top-header-form  → sidebar_notes:block_4 (site_header_notes; empty)
  │ └ nav#navbar-main.navbar.navbar-expand-lg > button.navbar-toggler[aria-label="Toggle navigation"]
  │     └ #CollapsingNavbar.collapse > (primary_menu, no region wrapper) nav#block-mainnavigation.menu--main
  ├ .highlighted > aside.container[role=complementary]   → highlighted (status messages fallback)
  ├ .featured-top > aside.featured-top__inner.container  → section.region-featured-top → news_alerts:block_1
  ├ #main-wrapper > #main.container
  │ ├ (breadcrumb region, no wrapper) #block-breadcrumbs          (all node pages)
  │ └ .row.row-offcanvas
  │   ├ main#content.col[role=main] > section > a#main-content + content region
  │   ├ #sidebar_first.col-lg-3 > aside   (front only) — ALSO contains the HARDCODED Bootstrap modal
  │   │      #accessibilityModal "Accessibility Settings" > section.region-accessibility-dropdown (a11y block)
  │   │      + "Learn more about how the Richmond School District supports accessibility." + "Close"
  │   └ #sidebar_second.col-lg-3 > aside  (front only) — starts with HARDCODED #accessibility-btn "⚙ Accessibility Settings"
  └ footer.site-footer > .container > .row
    ├ .col-lg  HARDCODED: sd38-logo-white.png link + "Copyright © 2026 School District No. 38 (Richmond)"
    ├ .col-lg  (empty: footer_second)
    ├ .col-lg  section.region-footer-third  → mainnavigation_2 (main menu, level 1)
    └ .col-lg  section.region-footer-fourth → account menu ("Log in") + address block; then HARDCODED #accessibility-btn again
```

Hardcoded strings in that template (existing site copy the sub-theme must reproduce verbatim, no new words):
`Skip to main content` (barrio html.html.twig), `Toggle navigation`, `Accessibility Settings`, `Learn more`
`about how the Richmond School District supports accessibility.`, `Close`, `Copyright © 2026` + `School District No. 38 (Richmond)`
(year is dynamic), `District Logo`, `Slogan` (hidden image replacements).

---

## 3. Regions

Machine names come from `region-*` classes and barrio's region list. **Keep every machine name** in `mcroberts.info.yml`
so the block copy at theme install (section 11.1) lands each block in the same region.

| Region (machine name) | Where it renders on live | Blocks on live (HTML id) | Pages | Role in redesign |
|---|---|---|---|---|
| `top_header` | inside `#header-img-area`, left col | `block-views-block-site-header-content-block-block-1` | all 191 | Hero / masthead: crest + name + slogan over header photo |
| `top_header_form` | `#header-img-area`, right col | `block-views-block-sidebar-notes-block-4` (empty note) | all | Optional hero note slot (renders nothing while empty) |
| `primary_menu` | inside `#CollapsingNavbar` (no wrapper) | `block-mainnavigation` | all | Primary nav (mega/disclosure menu + mobile drawer) |
| `highlighted` | `.highlighted` | status messages (`data-drupal-messages-fallback`) | all | Drupal messages |
| `featured_top` | `.featured-top` | `block-views-block-news-alerts-block-1` | all | **Site-wide alert bar** (section 11.9) |
| `breadcrumb` | top of `#main` | `block-breadcrumbs` | 180 (all nodes) | Breadcrumb |
| `content` | `main#content` | `block-mainpagecontent`; front also `block-views-block-sidebar-notes-block-3` (centre note, empty) | all | Main content |
| `sidebar_first` | left aside | `block-searchform`, `block-views-block-upcoming-events-block-1`, `block-views-block-sidebar-notes-block-1` (empty), `block-socialmedialinks` | front only (5: `/`, `/node?page=0..3`) | Front: events band; utility blocks |
| `sidebar_second` | right aside | `block-gtranslate`, `block-views-block-sidebar-notes-block-2` ("Student Absent?"), `block-views-block-district-quick-links-block-1`, `block-views-block-home-page-buttons-block-1` | front only | Front: "top tasks" band |
| `accessibility_dropdown` | inside hardcoded modal in sidebar_first | `block-a11y` | front only | Accessibility dialog, **every page** |
| `footer_third` | footer col 3 | `block-mainnavigation-2` (main menu, depth 1) | all | Footer sitemap |
| `footer_fourth` | footer col 4 | `block-useraccountmenu` ("Log in"), `block-ecolesecondairehughmcrobertssecondaryschooladdressblock` | all | Footer contact + login |
| `header`, `header_form`, `secondary_menu`, `featured_bottom_first/second/third`, `footer_first`, `footer_second`, `footer_fifth`, `page_top`, `page_bottom` | barrio regions, empty/unseen | — | — | Declare anyway (superset); `header_form`/`footer_second` are the targets of the optional placement tweaks |

Front-only blocks almost certainly carry a `<front>` request-path visibility condition (they also render on `/node?page=N`,
which is the front-page route) [I]. The a11y block may or may not have its own restriction: either way it is only *printed*
on the front page because its region sits inside the sidebar_first wrapper. Result on live: **186 of 191 pages show an
"Accessibility Settings" button whose target `#accessibilityModal` does not exist** (dead button), and GTranslate,
Search and Social are front-page-only.

---

## 4. Blocks

| Live HTML id → config id (inferred) | Plugin | Region | Visible | Content / notes |
|---|---|---|---|---|
| `block-views-block-site-header-content-block-block-1` → `views_block__site_header_content_block_block_1` | views_block | top_header | all | logo `Academic-MCRO LOGO-sm.png` (style `large`, `alt=""`), `<h1>` site name link, `<em>` "Learning Together... Achieving Our Dreams"; classes `header-content img-bg logo-sm` |
| `block-views-block-sidebar-notes-block-4` | views_block | top_header_form | all | sidebar_note in `site_header_notes` (empty) |
| `block-mainnavigation` → `mainnavigation` | system_menu_block:main | primary_menu | all | 9 top items, 4 expanded (News, Information, Parents, Students) with 34 children; Library/Extra-Curricular have children but "show as expanded" off |
| (messages) | system_messages_block | highlighted | all | fallback div |
| `block-views-block-news-alerts-block-1` | views_block | featured_top | all | empty today; row markup known from CSS (§11.9) |
| `block-breadcrumbs` → `breadcrumbs` | system_breadcrumb_block | breadcrumb | nodes | `nav[aria-label=breadcrumb] > ol.breadcrumb`, no `aria-current` |
| `block-mainpagecontent` → `mainpagecontent` | system_main_block | content | all | |
| `block-views-block-sidebar-notes-block-3` | views_block | content | front | `home_page_centre_notes` (empty) |
| `block-searchform` → `searchform` | search_form_block | sidebar_first | front | title "Search" + bi-search SVG; GET `/search/node`, field `keys` |
| `block-views-block-upcoming-events-block-1` | views_block | sidebar_first | front | title "Upcoming Events" + bi-calendar3 SVG |
| `block-views-block-sidebar-notes-block-1` | views_block | sidebar_first | front | `sidebar_note_left` (empty) |
| `block-socialmedialinks` → `socialmedialinks` | social_media_links_block | sidebar_first | front | title "Social Media"; email, Instagram `hugh_mcroberts`, X `hugh_mcroberts`; icon-only links (no accessible name) |
| `block-gtranslate` → `gtranslate` | gtranslate_block | sidebar_second | front | title "Translate" + bi-globe2 SVG; `.gtranslate_wrapper` + inline settings + `cdn.gtranslate.net/widgets/latest/fd.js` |
| `block-views-block-sidebar-notes-block-2` | views_block | sidebar_second | front | `sidebar_note_right`: h2 "Student Absent?", `tel:604-668-6600` "(Ext. 1)" |
| `block-views-block-district-quick-links-block-1` | views_block | sidebar_second | front | rich text `field_content_area`: 3 image links (MyEducation BC, School Cash Online, ERASE) hotlinked from sd38.bc.ca, **no alt** (names only in `title`) |
| `block-views-block-home-page-buttons-block-1` | views_block | sidebar_second | front | 2 `home_page_button` nodes: MyEd parent-portal photo → `/parents/myed-parent-portal-request-assistance`, Office 365 → portal.office.com (images, no alt, `target=_blank`) |
| `block-a11y` → `a11y` | a11y_block | accessibility_dropdown | front | buttons Dyslexic, Contrast, Invert, Text decrease/reset/increase |
| `block-mainnavigation-2` → `mainnavigation_2` | system_menu_block:main | footer_third | all | level 1 only |
| `block-useraccountmenu` → `useraccountmenu` | system_menu_block:account | footer_fourth | all | "Log in" |
| `block-ecolesecondairehughmcrobertssecondaryschooladdressblock` | block_content (bundle `address_block`) | footer_fourth | all | title "École Secondaire Hugh McRoberts Secondary School"; `field_address` (Apple Maps link), `field_phone` label "Phone", `field_school_email_address` |

Editors (logged in) additionally get local tasks/actions and contextual links; their placement is not visible to
anonymous crawls [I].

---

## 5. Views and displays

| View : display | Format / row | Where | Content & copy (all from config) | Notes for theming |
|---|---|---|---|---|
| `frontpage : page_1` (path `/node` = front) | Unformatted, row class `post`, **fields** (title, trimmed body in `.small`) | front content | header `<h2>Latest News`; 10 rows; footer link "News Archive" → `/news`; page `<title>` "Latest News \| …" | Title field is rewritten as a link around a linked title → **nested `<a><a>`** (invalid). No image, no date in output. |
| `upcoming_events : block_1` | HTML list `ul.shaded-rows`, fields title (link) + `field_event_date` (`<small class="text-muted"><time>Oct 5 2026`) | sidebar_first (front) | 8 rows; **AJAX mini pager** (falls back to `/node?page=N`) | `drupalSettings.views.ajaxViews` entry; keep `.js-view-dom-id-*` wrapper and pager markup classes `js-pager__items` for AJAX |
| `news_alerts : block_1` | fields, rows `.news-alert.standard-alert` / `.urgent-alert` with `h2`, `p`, `.alert-icon`, `.more-link`, wrappers `a.news-alert-link` / `a.alert-redirect`, editor ops `.sd38-news-alerts .ops-links` | featured_top (all) | empty at crawl time; the same view exists on every SD38 school site [M] | Row structure from [C]; entity type not exposed [I] |
| `sidebar_notes : block_1..4` | unformatted, rendered **node** `sidebar_note` in view modes `sidebar_note_left` (1), `sidebar_note_right` (2), `home_page_centre_notes` (3), `site_header_notes` (4) | sf / ss / content / top_header_form | only block_2 has content ("Student Absent?") | Empty notes render empty wrappers → hide when body empty |
| `site_header_content_block : block_1` | fields: logo image, name, slogan; header photo via bg_image_formatter | top_header (all) | name + motto | Inline `<style>` targets `body #header-img-area` → keep that id |
| `district_quick_links : block_1` | fields: `field_content_area` (rich text) | sidebar_second (front) | 3 image links | alt missing (content); fixable in preprocess (§11.4) |
| `home_page_buttons : block_1` | rendered node `home_page_button` (default) | sidebar_second (front) | 2 image buttons | DS `bs_1col` + field_group link to `field_link` |
| `calendar : block_1` | **fullcalendar_view** style (`.js-drupal-fullcalendar[data-calendar-view-name=calendar]`) | on `calendar_page` node via DS dynamic block field | footer: `webcal://mcroberts.sd38.bc.ca/calendar-feed.ics` "Subscribe to our calendar" + "Notes:" list | FullCalendar **v4.4.2** from unpkg, plugins moment/interaction/dayGrid/timeGrid/list/rrule, `defaultView dayGridMonth`, `defaultMobileView listYear` under 768px, 359 events in settings |
| `article_feed : entity_view_1` | **EVA** (`view-eva`) attached to paragraph `article_feed`; **views_bootstrap grid** (col-12/sm-6/lg-4) | `/news/newsletters` (node 2) | `<h3>` title link + "Posted:" `<time>`; 6 per page; AJAX mini pager (41 pages) | |
| `news_archive_page : page_1` (path `/news`) | views_bootstrap grid (col-12/sm-6/md-4/lg-3), rendered node `article` in `vertical_teaser` | `/news` | header `<h1>News Archive`; 20 per page; mini pager | teaser = title h2 + trimmed body + "Read more" (with `aria-label="Read more about …"`) |
| `staff_page_list : block_2` | table, **grouped** by staff group, `views_conditional` name column | on `staff_page` node via DS dynamic block field | groups: School Administrators, Counselling Staff, Office Staff, Teaching Staff, Support Staff; columns Name / Position / Grade/Dept. / Email / Online | Group `<h2>` is printed **inside `<table>`** (invalid); `block_1` presumably exists but unseen |

Search uses core `search` (`/search/node`, page not crawled).

---

## 6. Content model

### 6.1 Node types and view modes

| Bundle | Pages crawled | View modes seen | Rendering | Fields seen |
|---|---|---|---|---|
| `page` | 99 | `full`, `full_content_with_menu_list_` (7 landing pages: Information, Parents, Students-0, About Us …), `full_content_w_sidebar_menu_` (PAC), `full_content_includes_menu_block_` (Library) | Display Suite; the trailing-underscore view modes per node suggest **DS "switch view mode"** [I]; layout has no `bs-*` classes → likely a layout defined in `rsd_sites_barrio` [I] | `node_title` (DS), `body`, paragraphs reference (rendered in `.content-section` wrappers), DS dynamic fields `sub_pages_menu_block`, `section_menu_block`, token field `menu_back_button_field` (renders an empty `<a href>`), `field_legacy_attachments` (file) |
| `article` | 58 full + teasers | `full`, `vertical_teaser` | DS (`bs_1col_stacked` teaser; full has `bs-region--right`) | `node_title`, `body`, attachments (media `file`) printed under `<h2>Attachments`, "Updated:" changed date. **No image field rendered.** Aliases `/news/YYYY/MM/slug`, `/school-learning-story/news/…`, `/our-school-story/news/…` (pathauto by section [I]) |
| `calendar_event` | 21 | `full` | DS `bs_2col_stacked` | `node_title`, `field_event_date` printed under `<h2>Event Date` as "Wed, Oct 14 2026, All day" (format matches Smart Date [I]). **Titles carry U+FEFF BOM characters** (26 pages, also in calendar JSON). Aliases `/YYYY/slug` |
| `calendar_page` | 1 (`/school-calendar`) | `full` | DS, left col calendar view + right col body ("Monthly calendar pages" PDF link) | `dynamic_block_field:calendar_block`, `body` |
| `staff_page` | 1 (`/information/our-staff`) | `staff_listing_table_grouped` | DS `bs_2col_stacked` | `dynamic_block_field:staff_listing_block_grouped` |
| `sidebar_note` | in views | `site_header_notes`, `home_page_centre_notes`, `sidebar_note_left`, `sidebar_note_right` | node template (single class attr, no DS classes) | `body` |
| `home_page_button` | in views | `default` | DS `bs_1col` + field_group link | `field_tile_image`, `field_link` (new tab) |

Staff members, the site-header record and news alerts are entities whose type is not exposed in markup [I].

### 6.2 Other entities

| Entity | Bundle | Fields / formatter |
|---|---|---|
| block_content | `address_block` | `field_address` (address module, Apple Maps link, `translate="no"`), `field_phone` (telephone, inline label "Phone"), `field_school_email_address` (email) |
| media | `file` | `field_media_file` (DS `bs_1col`), mime classes `file--mime-application-pdf`, docx, pptx; link text = filename |
| media | `image` | `field_media_image` (galleries, colorbox) |
| media | `remote_video` | oEmbed iframe via `/media/oembed?url=…youtube…` (2 pages); standalone media URLs on (`/media/1069`) |

### 6.3 Paragraph types

Two families: **bootstrap_paragraphs** types (template classes `paragraph--type--bp-*`, `paragraph--id--N`) and
**site-defined types rendered through DS + bootstrap_layouts** (classes `paragraph--type-*`, `bs-1col`/`bs-2col`).

| Type | Pages | View mode / layout | Markup & behaviour | Redesign treatment |
|---|---|---|---|---|
| `bp_simple` | 4 (30 instances) | default (bootstrap_paragraphs template) | `field bp_text` rich text | prose |
| `bp_blank` | 2 | default | `bp_unrestricted` | prose |
| `bp_accordion` | 4 (Counselling, Career Centre, Learning Updates, Library Q) | default | `bp_header` h2 + sections (title button + body paragraphs) using **Bootstrap collapse JS** (`data-bs-toggle`) | `<details>/<summary>`, no JS |
| `embedded_video` | 2 | default | wraps remote_video media; renders empty on both crawled pages | responsive 16:9 |
| `file_attachments` | 13 | DS `bs_1col`, inner `row row-cols-1 row-cols-sm-2` | list of media `file` | file list with type/size chips |
| `article_feed` | 43 (newsletters + pages) | DS `bs_1col` + EVA `article_feed` | grid of newsletters | card grid |
| `basic_text_section` | 6 | DS `bs_1col`, region class `basic-text-section` | heading + `field_section_content` | prose / side panel |
| `image_and_text_section` | 2 | DS `bs_2col`, view mode `image_left_uncropped_`, wrapper `mts mts-il` | image left, `<h2>` + text right | media-object split |
| `image_banner` | 1 (Library) | DS `bs_1col` | `field_banner_image` via **imagefield_slideshow** (jQuery Cycle2 from cdnjs, auto-advancing 3 s) | static or paused-by-default slideshow (reduced motion) |
| `image_gallery` | 3 | DS `bs_1col`, view mode `_-columns` (as printed), `row row-cols-4` | heading "Image Gallery", `field_media_image` thumbnails (480 square) with **colorbox** lightbox; `aria-label` contains raw JSON (bug) | gallery grid + lightbox |
| `tile_links_section` | 2 | DS `bs_1col`, `row row-cols-2 row-cols-lg-4/6` | contains `tile_link` | tile grid |
| `tile_link` | 2 | DS view modes `coloured_tile` (text) and an image tile (220 square `field_tile_image`) | field_group link wrapper `.field-group-link`, colour class `bg-sd38sagegreen` / `bg-sd38oceangreen` / `bg-sd38blue…` | tile with brand colour |
| `columns` / `bp_columns` | **not observed** in the crawl | — | — | style generically if present |

### 6.4 Rich-text reality (affects CSS, not templates)

Inside `body`/`bp_text`/`field_section_content`: inline `font-size` ×293, `font-family` ×284, `color` ×132, `background` ×46,
legacy CKEditor 4 classes (`rtejustify`, `rtecenter`), `MsoNormal`, `<font>` ×5, `<o:p>`, typed bullets with `&nbsp;`
indentation, **base64 images** on 8 pages (About Us is 317 KB), CKEditor 5 list classes `ck-list-marker-bold/italic/color`.
Bootstrap classes inside content are rare (`table`, `table-responsive`).

---

## 7. Contrib modules visible in markup

| Module | Evidence | Theme implication |
|---|---|---|
| `a11y` (2.0.0-beta / 1.x plugins) | `/modules/contrib/a11y/plugins/*`, `block-a11y`, settings `a11y` | contract in §11.7 |
| `gtranslate` (3.0.x) | `block-gtranslate`, `.gtranslate_wrapper`, `window.gtranslateSettings` (en, zh-CN, fr, de, it, ja, ru, es; widget `fd` = flag links + `select.gt_selector`) | contract in §11.8 |
| `social_media_links` (8.x-2.x) | `.social-media-links--platforms`, `fontawesome.component` | override `social-media-links-platforms.html.twig` with inline SVG; drop FA CDN |
| `fullcalendar_view` (5.x, FullCalendar v4) | `fullCalendarView` settings, unpkg assets | restyle `.fc-*` via `libraries-extend` |
| `ds` (Display Suite) + likely `ds_switch_view_mode` [I] | `field--type-ds`, `dynamic-block-field…`, `dynamic-token-field…`, `node-title` | layout templates are DS layout templates (§11.5) |
| `bootstrap_layouts` | `bs-1col`, `bs-1col-stacked`, `bs-2col`, `bs-2col-stacked`, `bs-region--*` | override the four layout templates |
| `bootstrap_paragraphs` | `paragraph--type--bp-*`, `bootstrap-paragraphs*.css`, accordion JS | override `paragraph--bp-accordion.html.twig`; drop its CSS/JS |
| `paragraphs` | `paragraphs.unpublished` lib | — |
| `eva` | `view-eva`, display id `entity_view_1` | — |
| `views_bootstrap` | `views-bootstrap-*` ids, `grid views-view-grid row` | override `views-bootstrap-grid--*.html.twig` |
| `views_conditional` | `views-field-views-conditional-field` | — |
| `field_group` + `field_group_link` | `field-group-link`, `drupalSettings.field_group.link` | — |
| `bg_image_formatter` | inline `<style>body #header-img-area{…background-size:cover…}` | keep `#header-img-area` |
| `focal_point` | `?h=006e3e13` on `header_image` style | — |
| `address`, `telephone`, `media`, `media oembed`, `search`, `block_content`, `breadcrumb` | classes | — |
| `colorbox` | `colorbox/colorbox`, `colorbox/default` | keep JS, replace skin |
| `imagefield_slideshow` | `cycle-slideshow`, cycle2 from cdnjs | keep, restyle, respect reduced motion |
| `fitvids` | `fitvids` settings (selector `.node`, which mostly fails because of the duplicate class attribute) | replace with CSS `aspect-ratio` |
| `google_analytics` | settings | untouched |
| `ckeditor5_plugin_pack` (indent block) | library on every page | keep |
| `color` | `colors.css` | not used by `mcroberts` |
| `pathauto` [I], `webform` [I: dead link `/form/myed-bc-portal-request-assistanc`] | alias patterns | — |

---

## 8. Body classes and front-end settings

| Class | Source | Use |
|---|---|---|
| `layout-no-sidebars` (186) / `layout-two-sidebars` (5) | barrio `preprocess_html` (inherited by `mcroberts`) | layout switches |
| `has-featured-top` (191) | barrio, true even when the alert view is empty | do not rely on it; test rendered emptiness |
| `path-frontpage`, `path-node`, `path-news`, `path-media` | core | |
| `page-node-N`, `node--type-{bundle}`, `page-view-frontpage`, `page-view-news-archive-page` | barrio | |
| `HAS-HEADER-IMG` | rsd_sites_barrio preprocess | not needed |

`drupalSettings` keys: `path`, `ajaxPageState` (libraries list is gzip+base64; decoded in this research), `views.ajaxViews`
(news_alerts, upcoming_events, article_feed), `fitvids`, `google_analytics`, `a11y`, `field_group`, `colorbox`, `fullCalendarView`.

---

## 9. Libraries loaded (decoded from `ajaxPageState`) and their fate

| Library | Pages | Fate in `mcroberts` |
|---|---|---|
| `bootstrap_barrio/global-styling` (32 component CSS + barrio.js scroll classes) | 191 | **override → false**, own CSS |
| `bootstrap_barrio/bootstrap_cdn`, `rsd_sites_barrio/bootstrap_cdn` (Bootstrap 5.2 CSS+JS) | 191 | **not attached** (`bootstrap_barrio_source: ''`) + override → false |
| `bootstrap_barrio/messages_white`, `links`, `file` | 191 / 63 / 36 | override → false (own styles) |
| `core/components.bootstrap_barrio--menu_columns`, `--breadcrumb` (SDC) | 191 / 180 | unused once `menu--account` and `breadcrumb` are overridden |
| `social_media_links/fontawesome.component` (FA 6.6 CDN) | 5 | override → false, inline SVG |
| `social_media_links/social_media_links.theme` | 191 | keep (tiny) or override |
| `bootstrap_paragraphs/bootstrap-paragraphs`, `bp-accordion` | 6 / 4 | override → false |
| `fitvids/fitvids`, `fitvids/init` | 191 | override → false (CSS aspect-ratio) |
| `colorbox/colorbox` / `colorbox/default` | 3 | keep / override skin → false + own skin |
| `imagefield_slideshow/imagefield_slideshow` | 1 | keep, extend |
| `fullcalendar_view/fullcalendar` | 1 | keep, extend with own CSS |
| `a11y/global, contrast, dyslexic, invert, textsize` | 5 | keep, extend |
| `views/views.ajax`, `views/views.module`, `system/base`, `paragraphs/drupal.paragraphs.unpublished`, `media/oembed.formatter`, `ckeditor5_plugin_pack_indent_block/indent_block`, `google_analytics/google_analytics` | various | keep |

---

## 10. Markup defects the new templates fix without touching content or config

| Defect (live) | Count | Fix in `mcroberts` |
|---|---|---|
| Duplicate `class` attribute on every node/paragraph layout wrapper (`<div class="row justify-content-center" class="node …">`, browsers drop the second) | 190 pages | layout templates use `attributes.addClass()` |
| Two `<h1>` (site name in header + node title) | 183 pages (+1 with 3, +1 with 5) | header name is `<h1>` only when `is_front`, else `<p>` |
| Accessibility button with no modal | 186 pages | dialog rendered in `page.html.twig` on every page |
| Duplicate `id="accessibility-btn"` | 5 | one opener button |
| Nested `<a><a>` in front news titles | 5 | `views-view-fields--frontpage` builds one link |
| `<img>` without `alt` (logo, quick links, buttons, district logos) | 191 | decorative `alt=""` where a link has text; preprocess for quick links |
| `<h2>` inside `<table>` (staff) | 1 | `views-view-table--staff-page-list`: heading before table or `<caption>` |
| `role=complementary` on highlighted/featured_top, nested `<nav>` in `<nav>` | all | correct landmarks |
| Breadcrumb lacks `aria-current="page"` | 180 | `breadcrumb.html.twig` |
| Colorbox `aria-label='{"alt":…}'` | 3 | `colorbox-formatter.html.twig` |
| Empty `<a href></a>` from menu back-button token | 1 | hide when empty |
| BOM U+FEFF in event titles | 26 pages + calendar JSON | `mcroberts.theme` strips it on output (§11.4) |
| Icon-only social links | 5 | visually hidden platform name |

---

## 11. The `mcroberts` sub-theme

### 11.1 Install, preview and rollback (why this is zero-migration)

1. Add `web/themes/custom/mcroberts/` to the district codebase (one deploy; inert for every other school site).
2. On a **Platform.sh branch environment** of the McRoberts site (production DB + files cloned automatically): `drush theme:install mcroberts`.
   Core `block_theme_initialize()` (10.6 source, read) then **copies every `rsd_sites_barrio` block placement into
   `mcroberts`**: same plugin, settings, visibility and weight; same region when the region machine name exists, otherwise the
   theme's default region. Copied block config ids get the theme prefix via `BlockRepository::getUniqueMachineName($id, $theme)`,
   so HTML ids become e.g. `block-mcroberts-mainnavigation`. **Therefore: never style `#block-*` ids; target plugin classes and
   plugin-based template suggestions.**
3. The copy only happens when the new theme has **no** blocks: `mcroberts` must ship **no `config/optional/block.block.*`**
   (the barrio starter kit ships 14 of them; delete them).
4. `drush config:set system.theme default mcroberts`. Review. Rollback = set `rsd_sites_barrio` back as default (one value).
   Keep `rsd_sites_barrio` installed: other sites use it, and any layout plugin it defines stays discoverable [I].
5. If the site deploys with `drush config:import`, export the new config (`core.extension`, `system.theme`, `mcroberts.settings`,
   `block.block.mcroberts_*`) into the McRoberts config directory, otherwise the next deploy reverts it.

No node, paragraph, media, menu, view, field, display or content-type change is required.

### 11.2 `mcroberts.info.yml`

```yaml
name: McRoberts
type: theme
description: 'Hugh McRoberts Secondary redesign. Sub-theme of Bootstrap Barrio; same regions as rsd_sites_barrio.'
core_version_requirement: ^10.3 || ^11
base theme: bootstrap_barrio
libraries:
  - mcroberts/global
libraries-override:
  bootstrap_barrio/global-styling: false
  bootstrap_barrio/bootstrap_cdn: false
  bootstrap_barrio/bootstrap: false
  bootstrap_barrio/messages_white: false
  bootstrap_barrio/links: false
  bootstrap_barrio/file: false
  social_media_links/fontawesome.component: false
  bootstrap_paragraphs/bootstrap-paragraphs: false
  bootstrap_paragraphs/bp-accordion: false
  fitvids/fitvids: false
  fitvids/init: false
  colorbox/default: false
libraries-extend:
  a11y/global: [mcroberts/a11y]
  fullcalendar_view/fullcalendar: [mcroberts/calendar]
  colorbox/colorbox: [mcroberts/gallery]
  imagefield_slideshow/imagefield_slideshow: [mcroberts/slideshow]
regions:                       # superset: every barrio region + accessibility_dropdown
  top_header: 'Top header'
  top_header_form: 'Top header form'
  header: Header
  header_form: 'Header form'
  primary_menu: 'Primary menu'
  secondary_menu: 'Secondary menu'
  page_top: 'Page top'
  page_bottom: 'Page bottom'
  highlighted: Highlighted
  featured_top: 'Featured top'
  breadcrumb: Breadcrumb
  content: Content
  sidebar_first: 'Sidebar first'
  sidebar_second: 'Sidebar second'
  featured_bottom_first: 'Featured bottom first'
  featured_bottom_second: 'Featured bottom second'
  featured_bottom_third: 'Featured bottom third'
  footer_first: 'Footer first'
  footer_second: 'Footer second'
  footer_third: 'Footer third'
  footer_fourth: 'Footer fourth'
  footer_fifth: 'Footer fifth'
  accessibility_dropdown: 'Accessibility dropdown'
```

### 11.3 `mcroberts.libraries.yml` (no build step, no CDN)

```yaml
global:
  css:
    base:      { css/tokens.css: {}, css/base.css: {}, css/prose.css: {} }
    layout:    { css/layout.css: {} }
    component: { css/compat.css: {}, css/header.css: {}, css/nav.css: {}, css/alert.css: {}, css/cards.css: {},
                 css/events.css: {}, css/paragraphs.css: {}, css/files.css: {}, css/tables.css: {}, css/footer.css: {},
                 css/forms.css: {}, css/messages.css: {}, css/editor-ui.css: {} }
    theme:     { css/print.css: { media: print } }
  js:
    js/nav.js:    { attributes: { defer: true } }    # disclosure menu + mobile drawer (replaces Bootstrap collapse/dropdown + global.js)
    js/dialog.js: { attributes: { defer: true } }    # native <dialog> opener for Accessibility Settings
  dependencies: [core/drupal, core/once]
a11y:      { css: { component: { css/a11y.css: {} } } }
calendar:  { css: { component: { css/fullcalendar.css: {} } } }
gallery:   { css: { component: { css/gallery.css: {} } } }
slideshow: { css: { component: { css/slideshow.css: {} } } }
fonts:     { css: { base: { fonts/fonts.css: {} } } }   # self-hosted woff2 (or Google Fonts as type: external)
```

CSS is plain files with custom properties and `@layer`; Drupal aggregation concatenates them unchanged.

### 11.4 `config/install/mcroberts.settings.yml` and `mcroberts.theme`

Theme settings (theme config, not site config):
`bootstrap_barrio_source: ''`, `bootstrap_barrio_library: ''` (no Bootstrap), `bootstrap_barrio_bootstrap_icons: 0`,
`bootstrap_barrio_icons: ''`, `bootstrap_barrio_google_fonts: ''`, `bootstrap_barrio_messages_widget: 'alerts'`,
`bootstrap_barrio_system_messages: ''`, `bootstrap_barrio_navbar_flyout: 0`, `bootstrap_barrio_navbar_slide: 0`,
`bootstrap_barrio_enable_color: false`, `bootstrap_barrio_image_fluid: 0`, `bootstrap_barrio_button: 1` (keeps `btn` classes,
styled by compat.css), `favicon.use_default: true` (ship the same `favicon.ico` as rsd_sites_barrio).

`mcroberts.theme` (all code, no config):

| Hook | Purpose |
|---|---|
| `hook_theme_suggestions_block_alter` | add region suggestions `block__{region}__{base_plugin_id}` (load `Block::load($variables['elements']['#id'])->getRegion()`) so the footer menu can differ from the header menu |
| `hook_preprocess_block` | for `system_menu_block:main` in a footer region set `content['#theme'] = 'menu__main__footer'` |
| `hook_preprocess_page` | `copyright_year` (`date('Y')`), `district_url` |
| `hook_preprocess_field` + `hook_preprocess_views_view_field` | strip leading U+FEFF from `node_title` / views `title` |
| `hook_js_settings_alter` (themes may implement it) | strip U+FEFF from `fullCalendarView[*].calendar_options.events[*].title` |
| `hook_preprocess_views_view_field` (district_quick_links) | DOM-parse `field_content_area`, set each `img[alt]` to its parent link's existing `title` |
| `hook_preprocess_image` | `decoding="async"` |

### 11.5 Template overrides (concrete list)

Paths under `templates/`. DS layout suggestions follow DS code: `{layout}__{entity_type}_{bundle}_{view_mode}`
(file `bs-1col--node-article-vertical-teaser.html.twig`).

| File | Overrides | Contract to keep |
|---|---|---|
| `layout/page.html.twig` | barrio/rsd page | region print order: district strip → header (`#header-img-area` id **must stay**) with `top_header`, `top_header_form`, `header_form` utilities, `primary_menu` → `featured_top` alert bar (print only if `page.featured_top\|render\|striptags('<img>')\|trim` non-empty) → `highlighted` → `breadcrumb` → `main#main-content` (`content`, `sidebar_first`, `sidebar_second` as asides) → `featured_bottom_*` → footer (`footer_first..fifth` + hardcoded district logo/copyright) → `<dialog id="accessibilityModal">` wrapping `page.accessibility_dropdown` + "Learn more…" sentence + "Close" (rendered only when the region is non-empty, together with its opener button "Accessibility Settings") |
| `layout/page--front.html.twig` | front composition | same regions re-composed: hero (`top_header`, larger), top-tasks band (`sidebar_second`: Student Absent?, quick links, home buttons, translate), news (`content`: frontpage view + centre note), events band (`sidebar_first`: Upcoming Events, search, social). No block moves needed. |
| `layout/region.html.twig`, `region--primary-menu.html.twig`, `region--featured-top.html.twig`, `region--accessibility-dropdown.html.twig` | barrio region wrappers | drop `row d-flex` utility classes; keep `region region-*` classes |
| `block/block.html.twig` | barrio | plain wrapper, keep `block block-{module} block-{plugin}` classes |
| `block/block--system-menu-block--main.html.twig`, `navigation/menu--main.html.twig` | barrio + rsd global.js | disclosure pattern: parent `<a>` stays a link, sibling `<button aria-expanded aria-controls aria-labelledby="{link id}">` toggles the `<ul hidden>`; Esc closes; 2 levels; mobile drawer opened by a button labelled "Toggle navigation" |
| `navigation/menu--main--footer.html.twig` | footer copy | flat list, level 1 |
| `navigation/menu--account.html.twig` | barrio SDC menu_columns | "Log in" link |
| `navigation/breadcrumb.html.twig` | barrio SDC breadcrumb | `aria-current="page"` on last |
| `navigation/views-mini-pager.html.twig`, `navigation/pager.html.twig` | rsd pager | keep `js-pager__items` + `pager__item` classes for Views AJAX; reuse existing "Next page"/"Go to next page"/"Pagination" strings |
| `block/block--search-form-block.html.twig` (+ `form/form--search-block-form.html.twig`) | rsd | GET `/search/node`, `keys`; title "Search" |
| `block/block--gtranslate-block.html.twig` | rsd | print `{{ content }}` untouched (§11.8); title "Translate" + globe SVG |
| `block/block--a11y-block.html.twig`, `misc/a11y-template.html.twig` | a11y module template | §11.7 |
| `block/block--social-media-links-block.html.twig`, `misc/social-media-links-platforms.html.twig` | module | inline SVG icons, visually hidden platform name, same hrefs |
| `block/block--views-block--upcoming-events-block-1.html.twig` | rsd | title "Upcoming Events" + calendar SVG |
| `block/block--block-content--type--address-block.html.twig` | (core bundle suggestion, verified in 10.6) | address/phone/email, `tel:` and `mailto:` links |
| `views/views-view--frontpage.html.twig`, `views-view-unformatted--frontpage.html.twig`, `views-view-fields--frontpage.html.twig` | rsd + Views rewrite | one link per title via `path('entity.node.canonical', {'node': row._entity.id})`; header "Latest News", footer "News Archive"; date may be printed from `row._entity.created.value\|date(...)` (format change only) |
| `views/views-view--upcoming-events.html.twig`, `views-view-list--upcoming-events.html.twig`, `views-view-fields--upcoming-events.html.twig` | rsd | keep `js-view-dom-id-*` wrapper (AJAX pager); date badge from `field_event_date` |
| `views/views-view--news-alerts.html.twig`, `views-view-fields--news-alerts.html.twig` | rsd | output nothing when `rows` empty; keep `.news-alert` + `.standard-alert/.urgent-alert` classes |
| `views/views-view--sidebar-notes.html.twig`, `content/node--sidebar-note.html.twig` | rsd | suppress empty notes |
| `views/views-view--site-header-content-block.html.twig`, `views-view-fields--site-header-content-block.html.twig` | rsd | logo image unchanged; `<h1>` only on front |
| `views/views-view--district-quick-links.html.twig`, `views-view--home-page-buttons.html.twig`, `content/bs-1col--node-home-page-button-default.html.twig` | rsd | tiles; link `aria-label` = node title |
| `views/views-view--calendar.html.twig` | rsd | keep the module's `views-view-fullcalendar.html.twig` and `.js-drupal-fullcalendar` data attributes; restyle footer ("Subscribe to our calendar", "Notes:") |
| `views/views-bootstrap-grid--news-archive-page.html.twig`, `views-bootstrap-grid--article-feed.html.twig` | views_bootstrap | semantic `<ul>` card grid |
| `views/views-view-table--staff-page-list.html.twig` | core/barrio table | group heading outside the table, `scope` headers, stacked rows under 600px |
| `content/bs-1col.html.twig`, `bs-1col-stacked.html.twig`, `bs-2col.html.twig`, `bs-2col-stacked.html.twig` | bootstrap_layouts + rsd variants | merge classes with `attributes.addClass()` (fixes duplicate class) |
| `content/bs-1col--node-article-vertical-teaser.html.twig` | DS | news card (title, summary, "Read more" with its aria-label) |
| `content/bs-2col--node-article-full.html.twig` [layout name to confirm] | DS | article: title, body, "Attachments" list, "Updated:" |
| `content/bs-2col-stacked--node-calendar-event-full.html.twig` | DS | "Event Date" |
| `content/bs-2col-stacked--node-staff-page-staff-listing-table-grouped.html.twig` | DS | |
| `content/{layout}--node-page-full*.html.twig` (4 view modes) | rsd custom layout [I] | sub-page nav (`sub_pages_menu_block`, `section_menu_block`) as pill list or side nav |
| `paragraphs/paragraph--bp-accordion.html.twig` | bootstrap_paragraphs | `<details name="accordion-{id}">` per `bp_accordion_section`, summary = `bp_accordion_section_title`, body = rendered `bp_accordion_section_body` |
| `paragraphs/paragraph--bp-simple.html.twig`, `paragraph--bp-blank.html.twig`, `paragraph--embedded-video.html.twig` | bootstrap_paragraphs | thin wrappers |
| `paragraphs/bs-1col--paragraph-file-attachments-default.html.twig`, `…-article-feed-default`, `…-basic-text-section-default`, `…-image-banner-default`, `…-image-gallery-*`, `…-tile-links-section-*`, `…-tile-link-*`, `bs-2col--paragraph-image-and-text-section-image-left-uncropped-.html.twig` | DS | component markup per §6.3 |
| `field/file-link.html.twig`, `media/media--file.html.twig` | core | file chip: icon by mime class, filename, size |
| `field/colorbox-formatter.html.twig` | colorbox | correct `aria-label` (image alt) |
| `misc/status-messages.html.twig` | barrio toasts | static messages, `role=status/alert` |
| `navigation/menu-local-tasks.html.twig` | barrio | editor tabs without Bootstrap |
| `content/search-result.html.twig` (optional) | barrio | results list |

### 11.6 Bootstrap: keep or drop

**Drop Bootstrap CSS and JS entirely.** Everything that needed Bootstrap JS is replaced: navbar collapse and dropdowns
(`nav.js`), the accessibility modal (`<dialog>`), accordions (`<details>`), toasts (static messages). Classes still emitted
by *configuration* (Views style/row classes, DS layout region classes, paragraph wrappers, barrio's button preprocess) and by
the few content classes get a ~3 KB `compat.css`:

`row`, `col`, `col-12`, `col-4`, `col-sm-6`, `col-sm-12`, `col-md-4`, `col-md-6`, `col-md-12`, `col-lg`, `col-lg-3/4/6/9`,
`col-xl-3/4`, `row-cols-1/2/4`, `row-cols-sm-2`, `row-cols-lg-4/6`, `no-gutters`, `d-flex`, `d-block`, `d-none`,
`align-items-center/stretch`, `justify-content-center/between`, `mb-1..5`, `mt-3`, `text-muted`, `small`, `visually-hidden`,
`visually-hidden-focusable`, `table`, `table-striped`, `table-hover`, `table-responsive`, `btn`, `btn-primary`,
`btn-secondary`, `btn-light`, `btn-sm`, `bg-white`, `bg-lightgrey`, tile colours `bg-sd38sagegreen/oceangreen/blue/bluelight/
bluelagoon/royalblue/tealsky` (re-tuned for 4.5:1 text contrast), `form-control`.
`prose.css` neutralises legacy inline typography inside `.text-formatted`: `[style*="font-family"]{font-family:inherit!important}`,
same for `font-size`, `line-height`, `background`; `span[style*="color"]` keeps colour only above contrast threshold (or inherits);
`.rtejustify{text-align:start}`; `iframe[src*="youtube"],iframe[src*="vimeo"]{aspect-ratio:16/9;width:100%;height:auto}`
(replaces fitvids); `img{max-width:100%;height:auto}` (tames base64 images).

### 11.7 a11y module contract (keep it working)

- JS contract [D]: `contrast.js` and `invert.js` push `contrast(2)` / `invert(1)` into **`body.style.filter`**; `textsize.js` sets
  **`body.style.zoom`** in steps of 0.025 stored in cookie `a11y_textsize`; `opendyslexic.js` toggles `body.a11y-opendyslexic`
  (font from jsdelivr); state in cookies via `Cookies` (js-cookie from jsdelivr, part of `a11y/global`); buttons found by
  `document.querySelector('.a11y-contrast-control')` etc.; active state = `.is-active`.
- Override `a11y-template.html.twig` only to swap the PNG `<img>` icons for inline SVG and put the existing label text
  ("Dyslexic", "Contrast", "Invert", "Text decrease", "Text reset", "Text increase") directly in the `<button>` (the module nests
  `<label>` in `<button>`, invalid). **Keep every id, class (`a11y-control a11y-*-control`) and `data-a11y-action`.** Add
  `aria-pressed` mirroring `.is-active` from our own tiny observer if wanted.
- Render the region **once per page**: two copies break the `querySelector` binding.
- A `filter` on `body` makes `body` the containing block for `position: fixed` descendants: use `position: sticky` for the header
  and keep the dialog a top-layer `<dialog>` (unaffected). Use `rem` units so zoom scales cleanly. Never set `font-family`
  with `!important` (dyslexic font must win). Our CSS must not set `filter` on `body`.

### 11.8 GTranslate contract

- The block output is built in PHP [D]: `<div class="gtranslate_wrapper"></div>` + inline `window.gtranslateSettings` + a loader
  that appends `cdn.gtranslate.net/widgets/latest/fd.js`. The template must print `{{ content }}` unchanged; do not move or
  rename `.gtranslate_wrapper`.
- The `fd` widget renders flag links (`a.glink` with 24 px flag `img`, `a.gt-current-lang`) + `<br>` + `select.gt_selector`
  (`aria-label="Select Language"`, first option "Select Language", native language names). Style those selectors.
- `url_structure: none` → translation via the `googtrans` cookie, so the chosen language persists across pages; the switcher
  itself should still be on every page (§11.10). Place the block **once** per page.
- Google's translate layer may push `body{top:…}`; layout must not depend on `body` offsets.

### 11.9 `news_alerts` → site-wide alert bar

- Region `featured_top` sits between header and main on every page; `region--featured-top.html.twig` renders a full-bleed bar
  only when the view has rows (live prints an empty wrapper and still sets `has-featured-top`).
- Row classes come from the view config [C]: `.news-alert.standard-alert` (live: white with blue `#24408d` border) and
  `.news-alert.urgent-alert` (live: red `rgba(191,31,47,.9)` with white text); children `h2`, `p`, `.alert-icon`, `.more-link`,
  link wrappers `a.news-alert-link` / `a.alert-redirect`. Map to tokens `--alert-standard-*`, `--alert-urgent-*`; keep
  the classes; demote `h2` visually (not semantically). No `role="alert"` (would re-announce on every page load).
- Optional dismiss (sessionStorage, keyed by text hash) labelled with the existing word "Close".
- Logged-in editors keep `.ops-links` dropbuttons (core dropbutton CSS still loads in admin contexts).

### 11.10 Optional configuration tweaks (block placement and visibility only)

All tweaks touch only the copied `block.block.mcroberts_*` entities, so `rsd_sites_barrio` and every other school site are
untouched and rollback stays one setting.

| # | Block | Live | Tweak | Why |
|---|---|---|---|---|
| 1 | `mcroberts_gtranslate` | sidebar_second, `<front>` | region `header_form`, visibility all pages | Translate on every page (multilingual families) |
| 2 | `mcroberts_a11y` | accessibility_dropdown, front-only print | remove any `<front>` condition | dialog works site-wide (fixes 186 dead buttons) |
| 3 | `mcroberts_searchform` | sidebar_first, `<front>` | region `header_form`, all pages | search everywhere |
| 4 | `mcroberts_socialmedialinks` | sidebar_first, `<front>` | region `footer_second`, all pages | footer social |
| 5 | `mcroberts_views_block__sidebar_notes_block_2` ("Student Absent?") | sidebar_second, `<front>` | keep; optionally add a second placement in `footer_first` (all pages except `<front>`) | absence line one tap away everywhere |

Zero-config alternative for 1–4: `hook_preprocess_page` builds the same plugins (`plugin.manager.block` →
`createInstance('gtranslate_block')`, `search_form_block`, `a11y_block`, `social_media_links_block`) into page variables.
It works, but hides the placement from editors; prefer the block tweaks.

Outside "block placement only" and therefore a separate decision for the district: enable CSS/JS aggregation
(`system.performance`), which alone cuts ~80 requests per page; add alt text to the quick-link and home-button images.

### 11.11 File tree

```
web/themes/custom/mcroberts/
├── mcroberts.info.yml
├── mcroberts.libraries.yml
├── mcroberts.theme
├── favicon.ico                      # same file as rsd_sites_barrio
├── screenshot.png
├── config/install/mcroberts.settings.yml
├── config/schema/mcroberts.schema.yml
├── css/  tokens.css base.css prose.css layout.css compat.css header.css nav.css alert.css cards.css events.css
│         paragraphs.css files.css tables.css footer.css forms.css messages.css editor-ui.css a11y.css fullcalendar.css
│         gallery.css slideshow.css print.css
├── js/   nav.js dialog.js
├── fonts/ fonts.css *.woff2
├── images/ sd38-logo-white.png sd38-brand-logo.png sd38-brand-statement.png icons.svg   # copies of the district assets
└── templates/
    ├── layout/     page.html.twig page--front.html.twig region.html.twig region--primary-menu.html.twig
    │               region--featured-top.html.twig region--accessibility-dropdown.html.twig
    ├── block/      block.html.twig block--system-menu-block--main.html.twig block--search-form-block.html.twig
    │               block--gtranslate-block.html.twig block--a11y-block.html.twig block--social-media-links-block.html.twig
    │               block--views-block--upcoming-events-block-1.html.twig block--block-content--type--address-block.html.twig
    ├── navigation/ menu--main.html.twig menu--main--footer.html.twig menu--account.html.twig breadcrumb.html.twig
    │               pager.html.twig views-mini-pager.html.twig menu-local-tasks.html.twig
    ├── views/      views-view--frontpage.html.twig views-view-unformatted--frontpage.html.twig views-view-fields--frontpage.html.twig
    │               views-view--upcoming-events.html.twig views-view-list--upcoming-events.html.twig views-view-fields--upcoming-events.html.twig
    │               views-view--news-alerts.html.twig views-view-fields--news-alerts.html.twig views-view--sidebar-notes.html.twig
    │               views-view--site-header-content-block.html.twig views-view-fields--site-header-content-block.html.twig
    │               views-view--district-quick-links.html.twig views-view--home-page-buttons.html.twig views-view--calendar.html.twig
    │               views-bootstrap-grid--news-archive-page.html.twig views-bootstrap-grid--article-feed.html.twig
    │               views-view-table--staff-page-list.html.twig
    ├── content/    bs-1col.html.twig bs-1col-stacked.html.twig bs-2col.html.twig bs-2col-stacked.html.twig
    │               bs-1col--node-article-vertical-teaser.html.twig bs-2col--node-article-full.html.twig
    │               bs-2col-stacked--node-calendar-event-full.html.twig bs-2col-stacked--node-staff-page-staff-listing-table-grouped.html.twig
    │               bs-1col--node-home-page-button-default.html.twig node--sidebar-note.html.twig
    │               {page layout}--node-page-full*.html.twig (names from rsd_sites_barrio source)
    ├── paragraphs/ paragraph--bp-accordion.html.twig paragraph--bp-simple.html.twig paragraph--bp-blank.html.twig
    │               paragraph--embedded-video.html.twig bs-1col--paragraph-*.html.twig bs-2col--paragraph-image-and-text-section-image-left-uncropped-.html.twig
    ├── field/      file-link.html.twig colorbox-formatter.html.twig
    ├── media/      media--file.html.twig
    ├── form/       form--search-block-form.html.twig
    └── misc/       status-messages.html.twig a11y-template.html.twig social-media-links-platforms.html.twig
```

---

## 12. Redesign component → Drupal construct (for the design and build agents)

| Component in the concept | Drupal construct | Data available (no new words) |
|---|---|---|
| District strip | hardcoded in `page.html.twig` | district logo + statement images, link sd38.bc.ca |
| Masthead / hero | region `top_header` → view `site_header_content_block` | crest image (unchanged), name, slogan, header photo (CSS background on `#header-img-area`) |
| Primary nav (desktop disclosure, mobile drawer) | region `primary_menu` → menu `main` | 9 items, 4 with children (34) |
| Utility cluster (Search, Translate, Accessibility Settings) | `header_form` (tweaks 1, 3) + dialog of `accessibility_dropdown` | "Search", "Translate", "Accessibility Settings" |
| Alert bar | `featured_top` → `news_alerts` | alert rows (empty today) |
| Breadcrumb | `breadcrumb` | "Home" + trail |
| Front: top tasks | `sidebar_second` (front) | "Student Absent?" 604-668-6600 (Ext. 1), MyEducation BC, School Cash Online, ERASE (link titles), MyEd parent portal, Office 365 buttons |
| Front: Latest News | `content` → `frontpage` | title + summary (no images); "Latest News", "News Archive" |
| Front: Upcoming Events | `sidebar_first` → `upcoming_events` | title + date, AJAX pager |
| News archive / newsletters | `news_archive_page`, `article_feed` | title, summary, "Read more", "Posted:" date |
| Article page | node `article` full | title, body, Attachments, Updated: |
| Event page | node `calendar_event` full | title, Event Date |
| School calendar | `calendar_page` + fullcalendar view | month/week/list year, "Subscribe to our calendar", Notes |
| Section landing (Information, Parents, Students …) | page view mode `full_content_with_menu_list_` | title, body, child-page pills |
| Sub-page side nav | DS `sub_pages_menu_block` / `section_menu_block` | menu children |
| Accordion, files, gallery, tiles, image+text, banner, video | paragraph types §6.3 | as authored |
| Staff directory | `staff_page_list:block_2` | 5 groups, Name/Position/Grade/Dept./Email/Online |
| Footer | `footer_third` (menu L1), `footer_fourth` (Log in, address block), hardcoded district logo + copyright | address, Phone, email |

Design consequences: news cards are **text-first** (no article images exist); event items carry only title + date;
empty sidebar notes must collapse to nothing; quick links are images unless their `title` text is surfaced by preprocess.

---

## 13. What stays exactly as it is

Content (all nodes, paragraphs, media, files), menus, views, displays, DS layouts and fields, block content, URLs and aliases,
search, GA, GTranslate and a11y configuration, the calendar feed (`/calendar-feed.ics`), and every other SD38 site.

## 14. Verify on the branch environment before switching

1. `drush ev` list of layout plugin definitions → exact names of the page/article layouts (rsd_sites_barrio-provided?) to name
   the DS template overrides.
2. Read `rsd_sites_barrio` source from the district repo (templates for header view, accordion, pager, DS layouts) to confirm
   every hardcoded string listed in §2.
3. After `theme:install`, compare Block layout of both themes (`drush config:get block.block.mcroberts_*` vs rsd) and confirm
   no block fell into `content`.
4. Confirm visibility conditions of the front-only blocks and of `a11y`.
5. Lighthouse + axe on `/`, `/information/about-us`, `/school-calendar`, `/information/our-staff`, `/news/newsletters`.

## Sources

- Crawled markup: `cache/raw/*.html` (191 pages), `cache/index.json`; decoded `drupalSettings.ajaxPageState.libraries`.
- Live theme assets: `/themes/custom/rsd_sites_barrio/css/style.css`, `/js/global.js`, `/files/mcroberts/color/rsd_sites_barrio-1548cbd3/colors.css`,
  `/modules/contrib/a11y/plugins/*`; sibling sites boyd, mcnair, palmer, mcmath, macneill `.sd38.bc.ca` (shared theme).
- Drupal core 10.6.x `core/modules/block/block.module` (`block_theme_initialize`), `src/BlockRepository.php`,
  `core/modules/block_content/block_content.module` (bundle suggestions) — git.drupalcode.org/project/drupal.
- bootstrap_barrio 5.5.20 (`bootstrap_barrio.info.yml`, `.libraries.yml`, `.theme`, `theme-settings.php`, `subtheme/`, `js/*.js`) —
  git.drupalcode.org/project/bootstrap_barrio.
- bootstrap_layouts 8.x-5.7 templates; bootstrap_paragraphs 5.0.2 `paragraph--bp-accordion.html.twig`; ds 8.x-3.x
  `ds_theme_suggestions_alter()`; a11y 2.0.0-beta2 `a11y-template.html.twig` and `a11y.libraries.yml`; gtranslate 3.0.6
  `GTranslateBlock.php`; views_bootstrap 5.5.x, social_media_links 8.x-2.10, fullcalendar_view 5.2.5 template lists;
  GTranslate `fd.js` widget (cdn.gtranslate.net).

## Breadcrumb: menu based

Core's `PathBasedBreadcrumbBuilder` builds the trail from the URL. The new URLs follow the menu (design/ia.md), so
for most pages that trail already matches the menu. For the pages that sit outside their section's path (Contact Us,
School Learning Story and its posts, the `/2026/*` calendar events), the theme's companion module registers a
`BreadcrumbBuilderInterface` service with a higher priority that returns the active trail of menu `main` (the
`menu_breadcrumb` contrib module does the same, if the district prefers a module). The static preview renders that
menu-based trail.

