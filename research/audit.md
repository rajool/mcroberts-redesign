# Audit of the current site: mcroberts.sd38.bc.ca

Audited 2026-10-06 against the live site (Drupal 10, theme `rsd_sites_barrio`) and the 191 crawled pages in `cache/raw/`.
Evidence files: `shots/audit/` (Lighthouse JSON and HTML reports, `home-desktop-1440.png`, `home-mobile-390.png`).
Method: Lighthouse (accessibility, best practices, SEO, agentic browsing; the Chrome tool leaves out the Performance
category), a Chrome performance trace for Core Web Vitals, live DOM measurements at 390px and 1440px, a stdlib HTML parse
of every crawled page, and HEAD requests on all 140 image URLs.

## 1. Scores

| Page | Device | Accessibility | Best practices | SEO | Agentic browsing |
|---|---|---|---|---|---|
| `/` | desktop | **87** | 100 | **75** | **50** |
| `/` | mobile | **87** | 100 | **75** | **50** |
| `/parents/student-attendance` | mobile | **91** | 100 | **77** | 100 |

Failed audits on `/`: color-contrast (35 nodes desktop, 26 mobile), link-name (15), image-alt (6), link-text (3),
heading-order, meta-description, accessibility tree not well formed. On the attendance page: color-contrast (6),
image-alt, link-text (2), meta-description.

**Performance** (trace of `/` at 390px, Slow 4G, 4x CPU): LCP **1.08 s**, CLS **0.00**. Field data (CrUX p75):
LCP **1.24 s**, INP **89 ms**, CLS **0.00**. Speed is not where the home page falls down; usability and accessibility
are. The exceptions are a few very heavy pages (issues C5 and H4) and some server settings (M2).

**What already works, so keep it:** fast TTFB with the Drupal page cache (HIT), CLS 0, `lang="en"`, a working
"Skip to main content" link, breadcrumbs on inner pages, a real `<table>` for Our Staff, an ICS calendar feed, and
GTranslate with 105 languages.

## 2. Issues ranked by severity

Severity: **Critical** means it blocks a top task or shuts some users out. **High** means it seriously slows people
down or misleads them. **Medium** is about quality, upkeep or efficiency. **Low** is polish.
Every fix keeps the logo, Drupal 10 and the site's existing words (see `design/BRIEF.md`).

### Critical

**C1. The top parent tasks (report an absence, translate, search) exist only on the home page, and on mobile they sit
far down it.**
- Evidence: `block-gtranslate`, `block-searchform`, "Student Absent?" and `block-views-block-upcoming-events-block-1`
  appear on 5 of 191 crawled pages (`/` and its `/node?page=N` copies). None of the 186 inner pages has Translate,
  Search or the absence number.
- Mobile 390px, `/`: the sidebar blocks render after all 10 news cards. Search starts at y=2,368px, Translate at
  3,043px, "Student Absent?" at 3,154px, MyEd/School Cash at 3,240px, and the page is 4,837px long. That is 3.6 to 3.8
  screens of scrolling to report an absence or change language.
- `/parents/student-attendance`: the number is shown as bold text, "604.668.6600 (Press 1)", not as a `tel:` link.
  There are **0 `tel:` links in body copy on the whole site**; the only one is the home sidebar. The two places also
  give the number in different formats: "604.668.6600 (Press 1)" and "604-668-6600 (Ext. 1)".
- **Fix:** put a utility bar in the header region on every page (Drupal block layout, visibility "all pages"): the
  existing "Student Absent?" sidebar-note block (tap to call, `tel:6046686600`), the GTranslate block and the search
  form block. On mobile it becomes a sticky bottom action bar with three targets of at least 44px. Every phone number
  in body copy becomes a `tel:` link through a text-format filter or a theme preprocess.

**C2. The bell schedule is a picture of text, and the calendar fills up with its codes.**
- Evidence: `/information/bell-schedule` (page title "Timetable Structure 2026-2027") shows the entire timetable as
  `inline-images/image_0.png` (682x908, **no alt attribute**): semester dates, Rotation One and Rotation Two, blocks
  A-D with times, PLT, Lunch, and the 2026-27 collaboration days. On a 390px phone the image is scaled to about 358px,
  so the times are about 3px tall. Block meaning relies on colour alone. Screen readers, GTranslate and site search
  get nothing from it.
- **Fix:** rebuild it as real, responsive HTML tables using the image's own words (allowed by the brief: "an image of a
  table into a real table, same words"). On mobile, show one card per day with the times, plus a Semester One /
  Semester Two switch. Colour stays only as a secondary cue next to the A/B/C/D letters. Add the transcription of the
  image to the corpus so that `tools/check_copy.py` accepts "Rotation One", "Collaboration Days" and so on. Drupal: a
  body field holding an HTML table, or a paragraph type that holds the table.

**C3. The most-used links are images with no text.**
- Evidence (`/`, Lighthouse `image-alt` and `link-name`): the district quick links are images only (MyEducation BC,
  School Cash Online, ERASE), labelled by a `title` attribute and nothing else. The two home-page buttons ("Do you
  need your MyEd BC password reset?" and Office 365) are `<a target="_blank"><img>` with **no alt and no title**,
  even though one of them links to an internal page (`/parents/myed-parent-portal-request-assistance`).
  12 images on the home page have no `alt`.
- Each news headline on `/` is a nested anchor, `<h2><a href=…><a href=… hreflang="en">Title</a></a></h2>`.
  The browser splits it into an empty link followed by the real one, which gives 10 empty tab stops (Lighthouse
  link-name, zero width). The social links (email, Instagram, X) are icons only and also have no accessible name.
- `/extra-curricular`: the **only** way to reach Strikers Athletics and Club Directory is two base64 images with no
  alt (`title="Athlertics"`, `title="Clubs"`). Neither page is in the menu.
- **Fix:** turn the tiles into text-first cards. The label comes from existing words (the title attribute or the
  linked page title: "MyEducation BC", "School Cash Online", "ERASE", "MyEd Parent Portal: Request Assistance",
  "Office 365"), with the brand mark as a decorative image (`alt=""`). Fix the theme template so the news title is
  output once, inside one link. Give the social icons visually hidden names taken from the existing link targets.
  Extra-Curricular cards use the page titles "Strikers Athletics" and "Club Directory". Drupal: field templates for
  the `home_page_button` and district quick links views, `views-view-fields` overrides.

**C4. The brand link colour fails contrast everywhere.**
- Evidence (Lighthouse color-contrast): link and headline green `#51ba8d` on white is **2.4:1** (on `#eff2f1` it is
  2.12:1 and on `#e3e9e6` it is 1.94:1). It is used for every news headline, event link, breadcrumb and "News Archive".
  The Accessibility Settings button (white on `#51ba8c`) is 2.39:1. Footer text `#add2c0` on `#167d4c` is 3.13:1.
  Nav grey `#777` on `#fcfcfc` is 4.36:1. Event dates `#6c757d` on `#e3e9e6` are 3.81:1.
- **Fix:** derive the palette from the crest. Forest green `#1f4d2b` on white is **9.75:1**, so it works for links,
  headlines and the footer background, with white text at 9.75:1. Use a lighter tint only for surfaces, never for
  text. Links are underlined in body copy. Focus rings use a 3px custom style; today the browser default is a 1px
  `auto` outline.

**C5. A 24 MB photo on the Career Centre page.**
- Evidence: `/students/career-centre-information` embeds `inline-images/CareerCentre.png`, **24.18 MB**,
  4284x5712 pixels. It is a phone photo of the Career Centre door saved as PNG, shown at 411x548 with an empty `alt`.
  It sits 70 words into the page, so on mobile it loads straight away. This single file is 24.2 MB of the 31.7 MB
  total for all 140 images on the site.
- **Fix:** output every body image through a Drupal image style or responsive image style (WebP, 2x the rendered
  width, `loading="lazy"`, width and height set). For this photo that means about 822px wide, around 100-150 KB, a
  saving of more than 99%. Also set a maximum upload resolution on the image field and the CKEditor image upload.

### High

**H1. On mobile, the header takes up the first screen and the menu is hard to find.**
- Evidence (390px): the district bar plus a 515px hero with the crest and school name fill y=0-557. The menu toggle
  is at y=565. It is not sticky (`position: relative`), shows no visible text, and is named only by
  `aria-label="Toggle navigation"`. On inner pages the `<h1>` starts at **y=697px of an 844px screen**
  (`/parents/student-attendance`), so content begins at the bottom of the first screen on every page. On desktop the
  crest is about 70px, yet it is a 180 KB PNG (`Academic-MCRO LOGO-sm.png`, 480x418) loaded with `loading="lazy"`
  even though it is visible on first paint.
- **Fix:** use a compact sticky header (crest at 40-56px using the original `39ef9ae7e316.png` unchanged, school name,
  menu button), keep the full crest hero for the home page only, and keep inner-page headers under 25% of the
  viewport. Load the crest eagerly with set dimensions. Drupal: `page.html.twig` with the
  `{% if is_front %}` hero variant.

**H2. The calendar is mostly timetable codes, and the home page shows only codes.**
- Evidence (`content/events.json`): **159 of 323 events (49%)** are codes: "BADC" ×52, "ABCD" ×39, "PLT Rot 1" ×30,
  "PLT Rot 2" ×30, "COLLAB BADC" ×5, "COLLAB ABCD" ×3. **0 of 323 events have a description.** 19 distinct titles are
  in ALL CAPS ("PRO-D DAY - NO SCHOOL", "EARLY DISMISSAL (1:15PM)", "S1 INTERIMS PUBLISHED"). On 2026-10-06 the home
  "Upcoming Events" block listed 5 of 5 as codes (ABCD, PLT Rot 2, ABCD, PLT Rot 2, ABCD), which pushed out
  Thanksgiving, the Immunization Clinic and the PAC Meeting. Event `<h1>`s begin with a byte-order mark
  (`"﻿ABCD"`). Each event page is an 8-word stub ("Event Date Mon, Oct 5 2026, All day").
- **Fix:** split the Views output. Day-order and rotation codes become a small "today" chip in the header or the
  calendar day cell (for example "ABCD · PLT Rot 2"), linked to the bell schedule table where the letters are
  explained. They are filtered out of "Upcoming Events" with a Views filter on the title pattern, or better with an
  event-type taxonomy. Real events get date tiles. CSS cannot turn ALL CAPS titles into correct sentence
  case, because acronyms such as PRO-D, PLT and S1 must stay capitalised. So the concept keeps the words as they are
  but shows them at normal weight and size so they do not shout, and the school is told the titles should be retyped.
  Strip the BOM in a preprocess.

**H3. Information architecture: empty landing pages, duplicate routes, missing pages and mismatched labels.**
- Evidence: `/parents`, `/students-0` and `/information-0` hold only the title and a bare list of child links with no
  descriptions. `/information` is an orphan copy that lists the whole top menu. The `-0` suffixes show a second node
  created over an old alias. Top-level items with children are Bootstrap `data-bs-toggle="dropdown"` toggles, so the
  menu never reaches `/parents`, `/students-0` or `/information-0`; Lighthouse flags "Information" as non-descriptive
  link text. Menu: 9 top-level items and 34 children; Parents (12) and Students (12) are flat lists that mix
  priorities (School Cash Online next to the VTRA Protocol). **20 content pages are not in the menu**, among them
  Strikers Athletics, Club Directory, all 6 Library sub-pages, PAC Meeting Agendas, PAC Meeting Minutes, PAC
  Constitution, Career Education 8 & 9, CLC, both Program Planning sub-pages and Mission Statement. Label mismatches:
  menu "Grad 2026" leads to the page "Grad 2027" (one sentence of content); "Bell Schedule" leads to "Timetable
  Structure 2026-2027"; "Library" leads to "Library Learning Commons". Thin pages: `/library/research-inquiry`
  (0 words), `/library/library-catalogue` (2), `/library/make-play` (2 plus photos), `/library/read-listen` (4),
  PAC Constitution and Bylaws (0).
- **Fix:** turn section landing pages into real hubs. Render the existing child pages as cards (title plus the first
  sentence of each page's own body as a summary) with a Views block "child pages of current menu item". Use a mega
  menu on desktop and an accordion on mobile, where the parent label is a link and a separate disclosure button opens
  the children. Add third-level pages to the menu (menu UI only). Group long lists by what the pages already cover
  (attendance, payments, reports, PAC), without new headings. Redirect `/information` to `/information-0` with the
  Redirect module.

**H4. Images embedded as base64 make some pages enormous, and HTML is sent uncompressed.**
- Evidence: 8 pages carry base64 images in body copy, about 5.5 MB in all.
  `/our-school-story/news/2024/12/grade-8-student-mentor-connections` is a **3.87 MB HTML document**, 3.83 MB of it
  base64. It cannot be cached as images or lazy-loaded, and it blocks parsing. Others: `/extra-curricular` (472 KB),
  `/information/district-concussion-protocol` (374 KB), `/information/about-us` (277 KB), the phone icon on
  `/parents/student-attendance` (43 KB). The server returns HTML **without gzip or brotli** even when the request
  accepts them (`/` is 61 KB raw; the 3.87 MB page also goes out raw). Lighthouse DocumentLatency reports
  "Compression was applied: FAILED".
- **Fix:** move the embedded images to managed files (a one-time content cleanup; the concept build has already
  extracted them to `assets/content/`). Add a text-format filter that rejects `data:` URIs. Turn on compression at
  the platform level (Platform.sh routes/web config) or in Drupal performance settings.

**H5. The heading structure is broken on almost every page.**
- Evidence: **183 of 191 pages have two `<h1>`s**, because the site name in the header is an `<h1>` wrapped in a link,
  next to the page title. 55 pages skip levels: h1 to h3 on 43 newsletter and listing pages, plus h2 to h5 for
  "Accessibility Settings" and h2 to h4 for "Pagination". `/students/career-education-volunteer-hours/career-education-8-9`
  has four `<h1>`s (Career Education 8 & 9, Rationale, Goals, Assessment).
  `/students/provincial-graduation-assessments` has an empty `<h1>`. 42 bold paragraphs act as headings (17 on Career
  Centre, plus "Early Dismissal" and "Lates/Truancy" on Student Attendance). On the home page all 10 news teasers are
  `<h2>`s, at the same level as "Latest News".
- **Fix:** the site name becomes a link inside `<p>`/`<div>` on every page; one `<h1>` per page. News teasers become
  `<h3>` under "Latest News". The theme maps bold-only paragraphs to visual headings only where content editors
  re-tag them. Add the CKEditor 5 heading plugin limited to h2-h4, and a theme rule that styles a stray `h1` in body
  copy as `h2`.

**H6. The news is mostly PDF notices, presented as a flat list.**
- Evidence: **101 of 308 news posts (33%)** are "Striker Weekly": a 22-word teaser ("Please see the Striker Weekly
  (a Week at a Glance for Parents)…") plus a PDF attachment. On `/`, 3 of the 10 equal-weight news cards are Striker
  Weekly. The cards have no dates and no images. The home page `<title>` is "Latest News | École Secondaire…". The
  home news list is paginated (`/node?page=1..3`), which duplicates `/news`. `/news` repeats "Read more" 40 times.
  The same-week duplicate post `/news/2026/08/back-school-schedules-and-calendars` and `…-calendars-0` is published
  twice.
- **Fix:** separate the newsletter flag (the `newsletter: true` field already exists) into its own compact "Striker
  Weekly" strip with the latest issue and a direct PDF link. News cards show the date and, where one exists, the
  image. The home page shows 3 to 6 stories and then "News Archive". "Read more" gets the headline appended as
  visually hidden text, made from existing words.

**H7. The School Calendar page does not work well on phones.**
- Evidence (390px, `/school-calendar`): FullCalendar draws on the client. The 358 KB HTML embeds every event as JSON.
  It opens in "list year" view inside a **389px inner scroll box** starting at September 7, not today, with
  low-contrast green titles. The toolbar (`prev/next`, `today`, `month/week/list`) wraps across three rows.
  "Subscribe to our calendar" is a `webcal:` link, and the note tells users to "right click the subcription
  button", which cannot be done on a phone. The printable calendar is a PDF.
- **Fix:** render the agenda server-side (a Views list grouped by month, starting today, no inner scroll) and enhance
  it with a month grid only at 768px and up. Offer "Subscribe to our calendar" as both the `webcal:` link and the
  `https` `.ics` URL. Keep "Monthly calendar pages" as a labelled file link with type and size.

### Medium

**M1. Content pasted from Word: inline styles, spacing hacks, typed bullets and layout tables.**
- Evidence: 1,392 `style=` attributes in body copy on 38 pages (Career Centre 268, Learning Updates 159, Counselling
  Centre 142, Strikers Athletics 122, PLT 114, Mission Statement 110), mostly
  `<span style="font-family:Arial;font-size:16px">`. 1,211 `&nbsp;` used for spacing (Career Centre 315; Contact Us
  lines up labels with runs of 17). 117 empty paragraphs (Career Centre 55). Typed bullets instead of lists on at
  least 8 pages (PAC 15, Career Centre 11, About Us 9, McRoberts Mural 4, Student Attendance 3, Helpful Links 2,
  Catchment 1). Layout tables on 10 pages (Student Attendance uses a bordered 2-cell table for icon and text; Mission
  Statement; four School Learning Story posts; Student Login). 72 `<u>` and 9 `<font>` tags.
- **Fix:** a "Basic HTML" text format with "Limit allowed HTML" so `style` and `font` are dropped at render time,
  without editing content. Add a theme safety net
  (`.field--name-body [style*="font"]{font: inherit !important}`). In the concept, typed bullets become real
  `<ul>`, layout tables become plain blocks, and runs of `&nbsp;` collapse.

**M2. Front-end delivery: no aggregation, heavy GTM, short caching.**
- Evidence: Drupal CSS/JS aggregation is **off**. The home page loads **63 separate stylesheets and 28 scripts**,
  122 requests in all, about 732 KB decoded. Google Tag Manager uses **972 ms of main thread** at 4x CPU. Images are
  sent with `cache-control: max-age=300` (5 minutes). The LCP element is the decorative green photo
  (`#header-img-area`, a CSS background, LCP load delay 699 ms). Scripts come from cdn.jsdelivr.net, cdnjs and
  cdn.gtranslate.net.
- **Fix:** turn on "Aggregate CSS files" and "Aggregate JavaScript files" (admin/config/development/performance).
  Load GTM after the load event. Give image derivatives long cache lifetimes (they already have `itok` hashes).
  Make the hero photo a real `<img>` with `fetchpriority="high"` and responsive sizes, or drop it on inner pages.
  The new theme ships one CSS file under about 30 KB and one small vanilla JS file.

**M3. The Translate control is not built for multilingual families.**
- Evidence: 8 flag shortcuts (a Canadian flag for English, 简体中文, Français, Deutsch, Italiano, 日本語, Русский,
  Español), each 26x19px, below the 24px minimum target height in WCAG 2.2. Languages are shown as country flags.
  Traditional Chinese, Punjabi, Filipino and Korean are available but only inside a 105-option `<select>`. Content in
  images (bell schedule, home tiles, posters) and PDFs cannot be translated at all.
- **Fix:** put the existing GTranslate block in the header on every page as a globe button labelled "Translate" that
  opens the language list with each language in its own script. No flags. Targets at least 44px. Removing images of
  text (C2, C3) makes that content translatable.

**M4. Key content lives in PDFs and posters.**
- Evidence: 130 PDF links across 50 pages (PAC Meeting Minutes 18, PAC Meeting Agendas 13, Action Post #1 12,
  Learning Updates 9, CLC 9). Images of text: the bell schedule, the athletics banquet poster, three "BITESIZED"
  newsletters and "McRoberts Grade 8 Monthly Tip" (`/school-learning-story/news/2026/04/action-post-2`), "Awards
  Invitation 2024", "Your Voice Matters", and the home tiles. All of them lack alt text.
- **Fix:** file links show their type and size (a `file_link` formatter override), use the file's own name as the
  label, and open in the same tab. Posters get an alt that repeats the poster's own headline (existing words).
  Agendas and minutes become a dated list.

**M5. The footer is very long and repeats everything.**
- Evidence (390px): the footer is 947px tall. It repeats the whole main navigation (a second `nav` named "Main
  navigation"), the district logo (no alt, on 191 of 191 pages) and a public "Log in" link. The address is
  right-aligned.
- **Fix:** a short footer with the address, phone (`tel:`), email, social links and Accessibility Settings, the
  district logo with alt from its existing link title ("School District No. 38 (Richmond)"), and no duplicate
  navigation. Keep "Log in" off the public theme or make it visually quiet.

**M6. Embedded frames have no title, and forms are in iframes.**
- Evidence: the Google Map on `/information/contact-us` and the Microsoft Forms on
  `/parents/myed-parent-portal-request-assistance`, `/students/myed-student-portal-request-assistance` and
  `/students/updating-student-contact-information` have no `title`.
- **Fix:** give each iframe a title from the page heading, make the forms full-width with a fallback link, and use a
  click-to-load map (a static address card first).

**M7. The Accessibility Settings widget stands in for an accessible base.**
- Evidence: the a11y module modal (Dyslexic, Contrast, Invert, text size) appears on every page. Its trigger fails
  contrast (2.39:1), and on `/` its id `accessibility-btn` appears twice.
- **Fix:** keep the block, since its title is existing copy, but restyle it as a quiet footer and header control with
  one id. The base theme meets AA on its own (C4, H5), so the widget is only an extra.

### Low

- **L1. SEO:** no `<meta name="description">` on any of the 191 pages; the home title is "Latest News". Fix: the
  Metatag module default pattern from the node summary; the front page title becomes the school name.
- **L2. Invalid HTML:** duplicate attributes on 190 of 191 pages (`<div class="row …" class="node …">` in the node
  template), a nested `<main>` pasted into body copy on 2 pages (Student Attendance is one), and a duplicate id on `/`.
  Fix: the new theme templates; strip `<main>` in the text format.
- **L3. Weak alt text:** Word's auto-generated alt ("A table covered with hand prints Description automatically
  generated") on the Grade 8 Mentor post. Colorbox links on `/library/make-play` have
  `aria-label='{"alt":"Fuse bead station"}'`, which is raw JSON read aloud. Fix: a formatter override that uses the
  image alt; strip "Description automatically generated".
- **L4. Search:** the submit button has zero width (Enter is the only way to search), and the search block exists only
  on `/`. Fix: a visible search button with an icon and accessible name, in the header on every page.
- **L5. Typos and stale labels in existing copy** (flag to the school; the concept keeps them as they are):
  "Athlertics" (title attribute), "subcription" (`/school-calendar`), "Girl Forgotton" (Library alt), the menu
  "Grad 2026" versus the page "Grad 2027".
- **L6. Many links open new tabs:** 502 `target="_blank"` links, internal pages included (the home MyEd button), with
  no warning. Fix: same tab for anything on sd38.bc.ca; an icon with visually hidden text for external links.

## 3. What the redesign must therefore do (in priority order)

1. On every page: a sticky utility bar (Student Absent? as tap-to-call, Translate, Search, menu) and a compact
   header. On mobile a bottom action bar. (C1, H1, M3, L4)
2. A crest-derived AA palette (`#1f4d2b` and black and white), underlined links, a strong 3px focus ring. (C4)
3. Text-first, labelled cards for MyEd, School Cash Online, ERASE, Office 365, the MyEd password help and the
   Extra-Curricular entries; one link per news headline. (C3)
4. The bell schedule as real responsive tables; timetable codes moved out of "Upcoming Events" into a "today" chip.
   (C2, H2)
5. Section hub pages built from existing child pages; a full menu including the 20 missing pages; disclosure buttons
   separate from parent links. (H3)
6. Responsive image styles, no base64, compression and aggregation on, GTM deferred. (C5, H4, M2)
7. One `<h1>` per page, clean heading levels, real lists, inline styles dropped through the text format. (H5, M1)
8. A Striker Weekly strip separate from news; dated news cards; a server-rendered agenda on mobile. (H6, H7)
