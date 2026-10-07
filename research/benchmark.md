# Benchmark: the best school websites of 2024-2026 vs. McRoberts

Research date: 2026-10-06. Every site below was visited on that date. The DOM of each home page was inspected in an
isolated Chrome (header, nav, fixed elements, fonts, skip links, translation, scripts, image loading, footer), and the
award or launch claims were checked against the source cited. Four screenshots are in `shots/benchmark/`:

| file | what it shows |
|---|---|
| `westdale-hwdsb-1440.jpg` | Canadian public board, Drupal: utility bar, split hero, a row of 4 task tiles |
| `walnut-grove-sd35-mobile-390.jpg` | BC public school on mobile: the task links become a one-at-a-time carousel (anti-pattern) |
| `brighton-college-1440.jpg` | Editorial premium: inset photo hero, crest centred with clear space, very large serif display type |
| `west-island-college-1440.jpg` | Green-palette Canadian school, but a modal blocks the first screen (anti-pattern) |

The current McRoberts site was assessed from `shots/audit/` (Lighthouse JSON and screenshots made by the audit
agent), `content/*.json` and `cache/raw/home-42099b.html`.

## 1. The shortlist

| # | Site | Type, country | Recognition / why chosen |
|---|---|---|---|
| 1 | [Westdale Secondary](https://westdale.hwdsb.on.ca/) (HWDSB) | Public secondary, ON, Canada | New board-wide sites launched 2026-05-19 for all 93 HWDSB schools ([EducationNewsCanada](https://educationnewscanada.com/article/education/level/k12/3/1201190/introducing-hwdsb-s-new-board-and-school-websites.html)). **Runs on Drupal** (`drupalSettings`, theme `schoolkit_universal`, Bootstrap navbar), so it is the closest technical match to our constraint |
| 2 | [Walnut Grove Secondary](https://www.sd35.bc.ca/wgss/) (SD35 Langley) | Public secondary, BC, Canada | New district and school sites launched 2025-06-26 ([EducationNewsCanada](https://educationnewscanada.com/article/education/level/k12/3/1148681/langley-schools-launches-new-websites.html)). Same province and the same parent tasks as McRoberts: MyEdBC, ERASE, school fees, absence |
| 3 | [Stevenson High School](https://www.d125.org/) (District 125) | Public high school, IL, USA | A large, top-ranked public high school whose site puts tasks first (Finalsite) |
| 4 | [Fort Smith Public Schools](https://www.fortsmithschools.org/) | Public district, AR, USA | 2025 NYX Awards Silver, Website/School ([NYX](https://nyxawards.com/winner-info.php?id=7952)) |
| 5 | [James Ruse Agricultural HS](https://jamesruse-h.schools.nsw.gov.au/) | Public secondary, NSW, Australia | Built on the NSW Department of Education's statewide school-site design system, the equivalent of SD38's shared district theme |
| 6 | [Shenton College](https://www.shenton.wa.edu.au/) | Public secondary, WA, Australia | Australian Access Awards, Accessible Website of the Year ([Shenton](https://shenton.wa.edu.au/?p=2228)). The award is from 2019, but the current build still shows the patterns |
| 7 | [Fairfax Academy](https://www.fairfax.bham.sch.uk/) | State academy, Birmingham, UK | Trust-wide relaunch 2026-06-18 on SEND-friendly principles ([FMAT](https://fmat.co.uk/fmats-digital-transformation-continues-with-the-launch-of-three-school-websites/)) |
| 8 | [Webb School of Knoxville](https://www.webbschool.org/) | Independent, TN, USA | 2025 NYX Awards Gold, Website/School ([NYX](https://nyxawards.com/winner-info.php?id=8072)) |
| 9 | [Saint Xavier High School](https://www.saintx.com/) | Independent Catholic high school, KY, USA | 2025 NYX Awards Gold, Website/School ([NYX](https://nyxawards.com/winner-info.php?id=7951)) |
| 10 | [Eastside Catholic School](https://www.eastsidecatholic.org/) | Independent 6-12, WA, USA | Finalsite, "Best Private and Independent School Websites of 2025" ([EC post](https://www.eastsidecatholic.org/about-us/blog/p/~board/all-school/post/redesigned-website-kudos)) |
| 11 | [West Island College](https://www.westislandcollege.ab.ca/) | Independent 7-12, AB, Canada | 2025 Vega Digital Awards Gold, Website - School/University ([WIC](https://www.westislandcollege.ab.ca/our-community/stories-from-the-den/post-details/~board/stories-from-the-den/post/wic-wins-gold-at-the-vega-digital-awards)) |
| 12 | [Brighton College](https://www.brightoncollege.org.uk/) | Independent, UK | Built by Thursday Studio and listed on Awwwards ([Thursday on Awwwards](https://www.awwwards.com/thursdaystudio/)). The editorial ceiling of school web design |

Considered and dropped:
- Cleveden Secondary ([Schooljotter "5 best secondary school websites"](https://www.schooljotter.com/5-best-secondary-school-websites-2025)): its domain now redirects to an ad network.
- West Derby School: dated build with no skip link.
- Wesley College Melbourne: an admissions-marketing site with 8 trackers and an empty `h1`.

## 2. Site notes (only the patterns worth stealing, plus the warnings)

### 1. Westdale Secondary, HWDSB (Drupal)
- **Header:** a pill-shaped utility bar sits top-right on every page with three icon links: *Staff Tools · Language · Search*.
  The main nav has 6 items, and two of them are task words: *News Hub · About · **Bell Times** · Families · Students ·
  Contact*.
- **Hero:** split layout. A building photo sits on the left, and a solid brand-colour panel on the right carries one
  sentence of welcome.
- **Task bar:** four large rounded tiles in different colours sit directly under the hero, each with an icon and a
  chevron: *Student Tools · Quick Finds · Community Newsletter · Upcoming Events*.
- **Home sections:** Announcements, News Stories, then "Our Calendar". The calendar shows the next 3 events with date
  chips and a "View Calendar" link, and *Subscribe* sits in the News Hub menu.
- **Other details:** Google Translate in the utility bar, a footer with address, phone and email plus Subscribe, a
  "Report a problem" widget, and a land acknowledgement.
- **Weak:** visually generic (Myriad Pro, stock blue, only 5 images on the home page, no lazy-loading).
- **Lesson:** a Canadian public board shipped this on Drupal with Bootstrap. The structure is right. McRoberts can
  match it and then go well past it visually.

### 2. Walnut Grove Secondary, SD35 Langley (BC)
- **Task row:** the first thing after the welcome is a row of 9 icon links: *Submit an Absence · Bell Schedule · School
  Day Schedule · Calendar · Pay School Fees · Registration · Staff Directory · MyEdBC Help · ERASE Reporting Tool*.
  These are almost exactly McRoberts' tasks.
- **Safety pages:** "School Status" and "Emergency Preparedness & Response" are pages in the *Our School* menu, and
  closures show up as events ("Thanksgiving (School Closed)").
- **News:** cards are tagged **DISTRICT NEWS** vs school news. This solves the mixing problem McRoberts has, where
  board-meeting notices sit between Striker Weeklies.
- **Header and footer:** *LOGIN* and *TRANSLATE* are in the top bar. The type is **BC Sans** (the BC government font).
  The footer has a land acknowledgement naming the local Nations.
- **Weak (see screenshot):** on a 390px phone the 9 task links collapse into a carousel that shows one tile at a time,
  so 8 of the 9 tasks are hidden behind arrows. The site also loads the accessiBe overlay (`acsbapp.com`). The FTC
  fined accessiBe US$1M in January 2025 over its accessibility claims
  ([TechCrunch](https://techcrunch.com/2025/01/03/ftc-orders-ai-accessibility-startup-accessibe-to-pay-1m-for-misleading-advertising)).
  Don't copy either.

### 3. Stevenson High School (public, US)
- **Sticky header** (135px) with a *Find It Fast* quick-links dropdown and *Calendar* in the utility row.
- **Audience mega menus:** STUDENTS, PARENTS and ABOUT US, each with about 12 links (Bell Schedules, Food Services,
  Health Services, Report a Concern, Clubs...).
- **Home order:** Latest News (a recurring student-profile series) → Upcoming Events → Featured Videos → "By the
  Numbers" statistics. Weglot translation. The footer has Calendar, Contact, Directions, Directory and Staff Links.
- **Weak:** the home page has no `h1`, and it loads the AudioEye overlay script.

### 4. Fort Smith Public Schools (public district, US; NYX Silver 2025)
- The **language selector is the second focusable element**, right after the skip link (Weglot "English"), so a parent
  who does not read English finds it first.
- "Our Schools" mega menu grouped by level, and Finalsite AI site search.
- Work Sans for UI, with a script display face for personality.
- The footer carries the safety and compliance links: *Storm Shelters · State-Required Information · Website
  Accessibility*, plus a nondiscrimination statement.

### 5. James Ruse AHS (NSW statewide public template)
- **Two skip links** (to the navigation and to the content), Public Sans (an open-source government font), and Material
  icons in the mega menu.
- **Hero:** the school name with the school values as a subtitle line ("Acceptance, Service, Participation...") and a
  single call to action.
- **Home order:** "Quick links", "Key dates", "Principal's message", socials. The footer has an Acknowledgement of
  Country.
- **Lesson:** a district-wide theme can still feel crafted when the typography, spacing and one strong component set
  are good. That is exactly SD38's situation with `rsd_sites_barrio`.
- **Weak:** the school name is not marked up as an `h1`.

### 6. Shenton College (public, WA; accessibility award)
- The `h1` is a short identity line ("Proudly Public").
- The top bar is **split into ESSENTIALS** (Newsletter, Dates, News, Uniform, Map) **and LOGIN** (Compass, Moodle, DOE
  IKON, iCentre, Subject Selection). It cleanly separates "find information" from "sign in to a system".
  - McRoberts has the same two families: Striker Weekly, Calendar and Bell Schedule on one side; MyEducation BC, School
    Cash Online and Office 365 on the other.
- Large 21px body text, heavy 800-weight headings, one skip link, and an acknowledgement in Noongar with English.

### 7. Fairfax Academy (UK state academy)
- **Motto as the hero line** ("Enriching Lives; Transforming Futures"), followed by the school values as single words.
  This maps directly to *Learning Together... Achieving Our Dreams*.
- Four area cards (Our Academy, Curriculum, Sixth Form, Parents).
- **Events list with time ranges** ("October 7 @ 4:00 pm - 6:30 pm") and a "Full Calendar" link. Google Translate
  in the header.
- **Weak:** WordPress/Elementor with "Click here" link text and no lazy images.

### 8. Webb School of Knoxville (independent; NYX Gold 2025)
- A **utility row** (*Login · Calendar · Alumni*) above an off-canvas main menu.
- Muted looping video hero.
- Mission pillars set as large `h2` statements, three division cards, and a repeated brand line ("Webb is where...").
- A **serif and sans pairing from one family** (Freight Text / Freight Sans).
- 83 of 110 images lazy-loaded, and a skip link. The `h1` text is just "Home" (weak).

### 9. Saint Xavier High School (independent; NYX Gold 2025)
- **Two small navs** besides the main menu:
  - by audience: *Parents · Alumni · Board · Students*
  - an explicit **"Popular Pages"** list: *Athletics · Directory · Parents · Calendar · Shop · Livestream · Give*
- **Heritage block: "Since 1864"** with the four core values. This is the direct analogue of McRoberts' "first opened
  in November 1962".
- **Google Fonts only** (Libre Caslon Text + DM Sans), which proves a premium look needs no paid fonts. Gold call to
  action on dark green and navy.
- News and events open in a modal panel.
- **Weak:** the autoplay muted looping hero video has no visible pause control (risk under WCAG 2.2.2).

### 10. Eastside Catholic School (independent; Finalsite best of 2025)
- **Sticky header with a "Quick Links" menu whose first item is "Attendance: Report an Absence"**, followed by Bus Pass,
  Canvas, Lunch Menu, Parking Pass...
- **"School Delays & Emergency Info" is a permanent page** in About.
- The mission statement is the first `h2`.
- Figtree + EB Garamond (both Google Fonts). 120 of 141 images lazy-loaded. Weglot translation, AI search, and an
  interactive transportation map.
- Footer: a one-paragraph description, address, phone, email and socials.

### 11. West Island College (independent, Calgary; Vega Gold 2025)
- The **forest-green palette** (`#36573D`, nearly McRoberts' crest green) with white and pale grey shows that a
  green-crest school can look premium.
- **The search overlay opens with "Popular Searches" and FAQ-style questions** ("What clubs are offered?", "What are
  the school uniforms like?").
- Proxima Nova Light at 74px for display, and a land acknowledgement in the footer.
- **Weak (see screenshot):** an Open House modal and a type animation block the first screen on load, and a chatbot
  bubble covers the corner. That is the opposite of a task-first parent site.

### 12. Brighton College (independent, UK; Thursday Studio / Awwwards)
- **Inset hero:** a full-bleed photo inside a ~20px frame, with the **crest centred at the top with generous clear
  space**.
- **A very large editorial serif** (Rhymes) with one italic accent line, over Neue Haas Unica for body text.
- Ghost outline buttons (*Enquire · Apply · Visit*) and **one vertical side tab for the single most important action**
  ("Book an Open Morning"). Then a stats band ("Record Results"), and a footer with *Term Dates*.
- **Weak:** no skip link, and a cookie wall dims the whole page.
- **Lesson:** this is the visual ambition, but every one of these touches has to sit on top of a solid task layer.

## 3. What the best sites converge on

1. **Utility bar on every page.** Translate · Search · sign-ins, top-right, compact and icon plus label (Westdale,
   Walnut Grove, Webb, Shenton, Fort Smith). Fort Smith even puts language first in the tab order.
2. **A task bar directly under the hero, as a grid, not a carousel.** It holds 4-9 large icon tiles. When there is an
   absence task, it comes first (Eastside, Walnut Grove, Westdale, Stevenson's "Find It Fast").
3. **Audience navigation.** Parents and Students are top-level menus that open as mega-menu panels of 7-10 links in
   grouped columns ([NN/g, mega menus](https://www.nngroup.com/articles/mega-menus-work-well/)). Saint X adds a
   separate "Popular Pages" list.
4. **Information separated from sign-in** (Shenton's ESSENTIALS vs LOGIN, Webb's utility Login).
5. **Identity in the hero:** school name, motto or values line, one real photo, and the crest with clear space
   (Fairfax, James Ruse, Brighton). Heritage gets its own block ("Since 1864" at Saint X).
6. **News split by source** (school vs district at Walnut Grove), with dates on every card and one featured story.
7. **Events as date chips** (month and day), 3-5 items, a "View calendar" link and a calendar subscription
   (Westdale, Fairfax, Stevenson).
8. **Closures handled in three layers:**
   - a site-wide alert banner region
   - a permanent emergency or delays page (Eastside's "School Delays & Emergency Info", Walnut Grove's "School
     Status")
   - closures shown as calendar events
9. **Type pairs a characterful serif display face with a humanist sans for UI**, and Google Fonts are enough
   (Saint X, Eastside). Public templates use open government fonts (Public Sans, BC Sans).
10. **Restrained colour:** one deep brand colour, white, warm or cool greys and a single accent for calls to action.
    The alert colour stays outside the brand palette.
11. **Footer as a utility:** address, phone, email, directions and map, socials, district, compliance and safety
    links, and (in Canada and Australia) a land acknowledgement.
12. **Mobile:** a compact sticky header (crest + Menu), the task grid in 2 columns within the first screen, and
    Translate reachable from the header rather than the bottom of the page.

Anti-patterns seen on otherwise good sites (avoid all of them):
- Modal interstitials on load (WIC) and cookie walls that dim the page (Brighton).
- Task links in a carousel on mobile (Walnut Grove).
- Accessibility overlays (accessiBe on Walnut Grove, AudioEye on Stevenson).
- Autoplay video with no pause control (Saint X).
- A missing or meaningless `h1`: none at Stevenson and James Ruse, "Home" at Webb and Saint X.
- "Click here" link text (Fairfax).
- Flags used for languages: a flag is a country, not a language (McRoberts today).

## 4. McRoberts today (evidence)

- **Layout:** Bootstrap 3 columns.
  - Left column: Search, Upcoming Events, Social Media.
  - Centre: 10 text-only news cards, then "News Archive".
  - Right column: Accessibility Settings, Translate, *Student Absent? 604-668-6600 (Ext. 1)*, and five image-logo tiles
    (MyEducation BC, School Cash Online, ERASE, the MyEd password-reset image, Office 365).
  - The header is about 330px tall at 1440px: the district bar, then a green-tinted 1400x400 photo with the crest, the
    full school name and the slogan.
- **Lighthouse** (audit agent): home on desktop scores accessibility 0.87 and SEO 0.75. It fails `color-contrast`,
  `heading-order`, `image-alt`, `link-name` and `link-text`. Student Attendance on mobile scores 0.91 accessibility.
- **Mobile:** the right sidebar stacks after all 10 news cards. *Student Absent?*, Translate and the MyEd and School
  Cash links land about 3,200 CSS px down a 390px-wide page, roughly 4 screen heights. The whole page is about 4,840
  CSS px tall.
- **Events block:** it shows the timetable rotation codes as if they were events ("ABCD", "PLT Rot 2", 5 days in a
  row), so no real event (Thanksgiving, PAC Meeting, Immunization Clinic) is visible.
- **Bell schedule:** `/information/bell-schedule` is a 682x908 *image* of the timetable with `alt=""`.
- **Translate:** GTranslate is configured for en, zh-CN, fr, de, it, ja, ru and es, with a row of country flags (Canada
  for English).
  - It offers no Traditional Chinese, Punjabi, Tagalog or Korean, so the list does not match Richmond's families.
  - The fix is configuration only and adds no new words.
- **Alerts:** a `news_alerts` view block already sits in the `featured-top` region. It is empty and unstyled, so the
  mechanism exists in Drupal and needs only a design.
- **Accessibility Settings:** the contrib `a11y` module (contrast, invert, dyslexia font, text size). This is
  acceptable because it is not an overlay that claims compliance.
- **Content strengths the redesign can use:**
  - the slogan
  - "first opened in November 1962"
  - dual-track English and French Immersion, "École"
  - Strikers (70 mentions) and Striker Weekly (94)
  - PLT, the Club Directory and Strikers Athletics
  - the School Learning Story posts
  - a calendar ICS feed ("Subscribe to our calendar")

Wording limits from rule 3 (no new words):
- "Quick Links" and "Announcements" do **not** appear in the corpus. Use existing labels: the menu labels, "Student
  Absent?", "Upcoming Events", "Latest News".
- The site has **no land acknowledgement**, so the redesign cannot add one. Raise it with the principal as a question
  instead.

## 5. Comparison matrix (1 = poor, 5 = best practice)

| # | Dimension | McRoberts | Evidence (McRoberts) | Benchmark best | What "5" looks like |
|---|---|---|---|---|---|
| 1 | Parent and student top tasks | **2** | The absence line and system logos sit in the right sidebar. Bell Schedule, Calendar and Striker Weekly are not on the home page | Eastside 5, Walnut Grove 4 (desktop) | Absence first, then 6-9 task tiles under the hero, one tap on any device |
| 2 | Navigation and IA | **3** | 9 clear top labels with Parents and Students already audience-based, but Bootstrap click-dropdowns, a 9-item "Information" grab-bag and duplicate `/information` and `/information-0` pages | Stevenson 5, Saint X 5 | Audience mega panels, grouped columns of 7-10 links, plus a popular-pages list |
| 3 | Header and identity | **3** | Crest, École name and slogan are present, but the crest is small (~95px) on a busy tinted photo, the header is ~330px tall including the district bar and is not sticky, and the district bar competes | Brighton 5, Saint X 5 | Crest with clear space on a calm field, a compact sticky bar on scroll, the slogan as display type |
| 4 | Hero and storytelling | **2** | No hero story: since 1962, French Immersion and the Strikers are invisible on the home page, and the School Learning Story is buried in the menu | Saint X 5, Webb 5 | One real photo, the motto, and a heritage and values block built from existing copy |
| 5 | News | **2** | 10 text-only cards with no dates on the cards and no images, and Striker Weekly mixed with district board notices | Walnut Grove 4, Stevenson 4 | A featured story plus a dated list, a source tag (school vs district), and Striker Weekly pinned |
| 6 | Events and calendar | **2** | Rotation codes "ABCD" and "PLT Rot 2" fill the 5 slots, and *Subscribe to our calendar* exists only on the calendar page | Westdale 4, Fairfax 4 | Date chips with real events, the rotation shown separately, plus a subscribe link |
| 7 | Alerts and closures | **2** | An empty `news_alerts` region exists, the Snow and Extreme Weather Protocols page is buried under Information, and nothing appears on the home page | Eastside 4, Walnut Grove 4 | A site-wide high-contrast banner, a permanent protocols link, and closures in the calendar |
| 8 | Visual system (type, colour, spacing) | **2** | Bootstrap defaults and system font, a light-green link colour that fails contrast, and grey boxes | Brighton 5, WIC 5, Saint X 5 | A serif and sans Google Fonts pairing, a token-based green, black and white palette with one accent, and generous spacing |
| 9 | Imagery | **2** | One green-tinted header photo and image-of-text logos, and no school photography anywhere else on the home page | Brighton 5, Webb 5 | Real school photos with duotone treatment in the crest green and no stock |
| 10 | Accessibility (WCAG 2.2 AA) | **3** | Has a skip link, one `h1`, landmarks and the a11y module, and Lighthouse scores 0.87. Fails contrast, heading order, link names and alt text. Quick links are images of text and the bell schedule is an image | Shenton 4, James Ruse 4 | Lighthouse 1.0: real text and tables, visible focus, 24px targets, reduced-motion support, no overlay |
| 11 | Translation and multilingual | **3** | GTranslate is on the home page (good), but it sits in a sidebar, uses country flags, has a language list that does not match Richmond, and lands about 3,200px down on mobile | Fort Smith 5, Westdale 4 | A "Translate" globe button in the utility bar on every page, language names written in their own scripts, no flags |
| 12 | Mobile | **2** | Three columns stack into a page ~4,840px long with the tasks at the bottom, and the header uses about a third of the first screen | Eastside 4, Westdale 4 | A sticky compact header, the 2-column task grid within the first screen, and translate and search in the header |

**McRoberts total: 28/60.** The strongest benchmark sites score 4-5 on most rows. The gap is mostly structural (tasks, events,
alerts, mobile ordering) and visual (type, colour, imagery). It is **not** a content gap: every element of a "5" above
can be built from McRoberts' existing words and existing Drupal blocks.

## 6. What the redesign should adopt (mapped to Drupal and McRoberts content)

| Pattern | Source sites | McRoberts implementation (existing words only) | Drupal construct |
|---|---|---|---|
| Utility bar | Westdale, Shenton, Webb | *Translate*, *Search* and *Accessibility Settings* top-right on every page. A separate sign-in group for MyEducation BC, School Cash Online and Office 365 | Header region with the existing `block-gtranslate`, `block-searchform` and `block-a11y` |
| Alert banner | Eastside, Walnut Grove | Full width above the header, amber or red (never the brand green), linking to *Snow and Extreme Weather Protocols*, closable with "Close" | Existing `news_alerts` view in `featured-top` |
| Hero | Fairfax, Brighton, James Ruse | The crest (untouched) with clear space, the full École name, and *Learning Together... Achieving Our Dreams* as large display type, over the existing header photo treated in duotone | Branding block plus the header-image field |
| Task grid | Eastside, Walnut Grove, Westdale | *Student Absent?* with a `tel:` link to 604-668-6600 (Ext. 1) first, then School Calendar, Bell Schedule, Striker Weekly (latest), MyEducation BC, School Cash Online, ERASE, Office 365, Counselling Centre. Text tiles with inline SVG icons, 2 columns on mobile | `district_quick_links` and `home_page_buttons` views plus the sidebar-notes block, all restyled |
| Audience mega menu | Stevenson, Saint X, NN/g | Parents (12 links) and Students (12 links) as 2-3 column panels. Information (9 links) is grouped visually, with existing page titles as group heads and no new headings | Main menu, rendered as a keyboard-operable disclosure panel |
| Heritage and identity block | Saint X ("Since 1864") | "first opened in November 1962", dual-track English and French Immersion, Strikers, from About Us and the Mission Statement | A block with a link to `/information/about-us` |
| News | Walnut Grove, Stevenson | One featured story plus a dated list, with Striker Weekly pinned as its own card ("a Week at a Glance for Parents") and board notices grouped | `news` view display |
| Events | Westdale, Fairfax | Date chips for real events. The ABCD and PLT rotation codes move to a separate compact strip with their calendar titles, and *Subscribe to our calendar* (webcal) sits under the list | `upcoming_events` view filtered by term, plus the ICS link |
| Type | Saint X, Eastside | A Google Fonts serif display face plus a humanist sans for UI (for example Fraunces or Libre Caslon with Inter, Figtree or DM Sans) | Theme CSS custom properties |
| Colour | WIC | Forest green `~#1F4D2B` (crest-derived), near-black, white, warm paper grey, and one accent for calls to action. Every text colour at least 4.5:1 | `:root` tokens in the sub-theme |
| Footer | Fort Smith, Walnut Grove | Address, phone, email, map link, Social Media, the district logo and copyright, plus a repeat of the main menu | Footer region (existing content) |
| Accessibility | Shenton, James Ruse | The bell schedule as a real table, task tiles as text not images, no autoplay, `prefers-reduced-motion`, 24px targets, a visible focus ring, no overlay | Theme templates |

Do not build:
- popups or modals on load
- carousels for tasks or news
- autoplay video
- chatbots or AI search (also blocked by the supply-chain rule)
- flags for languages
- "Quick Links" or "Announcements" headings, which are new words
- a land acknowledgement, which is not in the corpus
