# Best practices for a public secondary-school website

Research checklist for the Hugh McRoberts redesign. Every item gives the **rule**, **why** and a **source**. Item IDs
(`TT-1`, `A-3` and so on) let the concept, the Drupal mapping and the QA pass refer to a rule. Sources are primary
wherever one exists (W3C, web.dev, NN/g, design systems, drupal.org). The hard constraints in `design/BRIEF.md` win
whenever a rule here would conflict with them, and §12 lists where they meet.

## 0. Live-site baseline (measured 2026-10-06)

These are the facts the rules below are written against. The test was `mcroberts.sd38.bc.ca/`, Lighthouse mobile
plus the Performance API in the isolated Chrome, and the crawl in `cache/raw/`.

- **Stack:** Drupal **10.6.14** (core assets `?v=10.6.14`), theme `rsd_sites_barrio` on `bootstrap_barrio`. The site
  loads Bootstrap **5.2.0** from cdn.jsdelivr.net, Font Awesome **6.6.0** from cdnjs, js-cookie from jsDelivr, jQuery,
  fitvids, the contrib `a11y` module ("Accessibility Settings": contrast, invert, OpenDyslexic, text size), GTranslate
  and Google Analytics (gtag).
- **Weight (homepage):** **121 requests**, about **641 KB** transferred, **63 stylesheets and 31 scripts, none of them
  aggregated**, served from 7 hosts. The DOM has about 777 nodes.
- **LCP element:** a `DIV` with a **CSS background image** (`mcroberts-bg_0.jpg`). The preload scanner cannot discover
  it (see P-2). CLS was 0 in the sample.
- **Lighthouse (mobile):** Accessibility **87**, Best Practices 100, SEO 75. The failures are colour contrast (26 nodes,
  mostly news-title links), **15 links without an accessible name** (empty news-title links), **6 images without
  `alt`** (from sd38.bc.ca), heading order skipped (`h4.visually-hidden`), 3 non-descriptive links, and no meta
  description.
- **Bell schedule** (`/information/bell-schedule`) is a 682×908 **image of a table with `alt=""`**. Screen readers
  cannot read it, it cannot be zoomed without blurring, and GTranslate cannot translate it.
- **Alert slot already exists:** the view `news_alerts` (display `block_1`) sits in region `featured_top` on every
  page. It is empty today.
- **GTranslate config:** an inline widget (`fd.js` from cdn.gtranslate.net) with **flag** style (`en` shown as the
  Canada flag). Its languages are `en, zh-CN, fr, de, it, ja, ru, es`.
- **Closure timing:** the site's own Snow and Extreme Weather Protocols page says district closures are "decided by
  6:30 a.m. at the latest".

## 1. Top tasks and the homepage

- [ ] **TT-1. Design the homepage around the few top tasks, not around the organisation.** Why: top tasks are the
  small set (under 10, often under 5) that matter most to users, and IA built on them outperforms org-chart IA.
  Source: https://www.palantir.net/blog/mastering-top-tasks-methodology-enhancing-customer-experience-and-organizational-value (Gerry McGovern's method).
- [ ] **TT-2. Parents' evidence-based top tasks are calendar, staff contact, news and announcements, and the bell
  schedule. Add absence reporting, MyEd and School Cash Online, which come from the brief.** Why: a BC district survey
  (Delta SD, 2025) names exactly these as what parents look for. Across K-12 sites, **Calendars are the #2 page after
  the homepage**, followed by the staff directory, parent/student resources and lunch. Sources:
  https://district.public.deltasd.bc.ca/wp-content/uploads/sites/2/2025/12/Communications-Survey-Parent-Responses-Infographic.pdf ·
  https://smartsites.parentsquare.com/most-visited
- [ ] **TT-3. Treat the site as an occasional-use reference tool: obvious labels, zero learning curve.** Why: in the
  same BC survey only 3% of parents visit daily and 8% weekly, 66% visit "occasionally" and 20% never. 73% want urgent
  news by email. A visitor arrives with one question and leaves. Source: Delta SD infographic (above).
- [ ] **TT-4. Put a "most requested" band of at most 8 top-task links high on the homepage: 2 columns on desktop,
  1 on mobile, chosen from data.** Why: Canada.ca's mandatory pattern for landing pages. **Constraint:** the band's
  heading must be existing words (e.g. "Helpful Links", `corpus.txt` l.29) or the audience labels "Parents" and
  "Students". It must not be "Most requested". Source: https://design.canada.ca/common-design-patterns/most-requested.html
- [ ] **TT-5. "Student Absent?" is the #1 parent action. Make it a block on every page with a `tel:` link to the
  number exactly as the site writes it ("604.668.6600 (Press 1)").** Why: it is a help mechanism, so it must keep the
  same relative order across pages (A-5). Tapping a number beats copying it on a phone. Source:
  https://www.w3.org/WAI/WCAG22/Understanding/consistent-help.html
- [ ] **TT-6. Keep the hero slim. At 360×640 the top tasks must be visible without scrolling.** Why: large hero images
  push key functions below the fold and users miss them. Source: https://www.nngroup.com/articles/image-focused-design/
- [ ] **TT-7. No auto-rotating carousel.** Why: users ignore moving panels as ads, and motion hurts users with motor
  and attention difficulties. If anything moves for more than 5 s, WCAG 2.2.2 requires a pause control. Sources:
  https://www.nngroup.com/articles/auto-forwarding/ · https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html
- [ ] **TT-8. Write and lay out for teens: chunked, scannable, fast, with no childish decoration.** Why: teens have
  lower reading skills and "dramatically lower" patience than adults. They struggled most on school and government
  sites with dense content. They like a professional look and dislike pointless multimedia. Source:
  https://www.nngroup.com/articles/usability-of-websites-for-teenagers/
- [ ] **TT-9. Students' top tasks are MyEd, Office 365 ("Student Login"), Counselling Centre, Career Centre and
  Grad 2026. Surface them as the Students column of the top-task band and the first items of the Students menu.**
  Why: these are the brief's tasks. They already exist as menu items, so this adds no new words. Source:
  `design/BRIEF.md`, `content/INVENTORY.md`

## 2. Information architecture and navigation

- [ ] **IA-1. Keep the topic-based primary navigation. Keep "Parents" and "Students" only because their content is
  mostly mutually exclusive, and cross-link the shared items (MyEd appears under both).** Why: audience navigation fails
  when users can't self-identify or fear missing content meant for the other group. It works when the audience
  sections hold distinct content. Source: https://www.nngroup.com/articles/audience-based-navigation/
- [ ] **IA-2. On desktop, show the navigation as visible links. Never hide it behind a hamburger.** Why: hidden
  navigation cut discoverability by more than 20% and made tasks 39% slower on desktop. Source:
  https://www.nngroup.com/articles/hamburger-menus/
- [ ] **IA-3. On mobile, use combo navigation: a labelled menu button ("Menu", listed in `tools/ui_words.txt`) plus the
  top tasks visible on the page.** Why: with more than 4 top-level items, hiding them on mobile is acceptable, but
  combo navigation beat hidden navigation (hidden: 15% slower, 11% harder). Text labels beat a bare icon. Sources:
  https://www.nngroup.com/articles/hamburger-menus/ · https://www.nngroup.com/articles/find-navigation-mobile-even-hamburger/
- [ ] **IA-4. Use mega-menu panels for Information (9 children), Parents (12) and Students (12): one panel per
  section, grouped columns, everything visible without scrolling.** Why: a two-dimensional panel shows the whole
  section at once and puts less strain on memory than long dropdowns. Source:
  https://www.nngroup.com/articles/mega-menus-work-well/
- [ ] **IA-5. Open panels on click or tap with the disclosure pattern: `<button aria-expanded aria-controls>`, Esc
  closes, no `role="menu"`. Keep each top-level label a real link to its landing page, with a separate toggle button
  next to it.** Why: APG says `menu`/`menubar` roles are wrong for site navigation. Its "Disclosure Navigation Menu
  with Top-Level Links" example is exactly this hybrid. Sources:
  https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/examples/disclosure-navigation/ ·
  https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/examples/disclosure-navigation-hybrid/
- [ ] **IA-6. If panels also open on hover: wait 0.5 s before opening, open within 0.1 s once the pointer settles, and
  close 0.5 s after the pointer leaves. Panels must also be dismissible with Esc, hoverable and persistent.** Why: this
  avoids flicker and accidental opening, and meets WCAG 1.4.13. Sources:
  https://www.nngroup.com/articles/mega-menus-work-well/ ·
  https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html
- [ ] **IA-7. Put utility navigation top-right on every page: Search field, Translate and Accessibility Settings, with
  icons that always have text labels.** Why: users look for utilities there, and icon-only controls are misread.
  Source: https://www.nngroup.com/articles/utility-navigation/
- [ ] **IA-8. Give section landing pages (`/information-0`, `/parents`, `/students-0`, now empty with children) a
  card grid of their child pages, using the child titles.** Why: users arriving via a top-level link get the same
  overview the mega menu gives. Source: https://www.nngroup.com/articles/mega-menus-work-well/ ("clickable top-level
  items linking to dedicated pages")
- [ ] **IA-9. Keep navigation, header, footer and help blocks in the same order on every page.** Why: WCAG 3.2.3
  Consistent Navigation and 3.2.6 Consistent Help. Source:
  https://www.w3.org/WAI/WCAG22/Understanding/consistent-help.html
- [ ] **IA-10. Show breadcrumbs on pages two or more levels deep (Drupal's system breadcrumb block).** Why: they show
  location and give one-tap upward navigation on deep pages such as `/information/about-us/mission-statement`. Source:
  https://www.nngroup.com/articles/breadcrumbs/

## 3. Search

- [ ] **S-1. On desktop, show search as a visible, labelled text field, not just an icon, about 27 characters wide.**
  Why: users scan for "the little box where I can type", and a narrow box hides longer queries. A 27-character field
  fits about 90% of queries (an NN/g rule of thumb cited by the Queensland Government design system). Sources:
  https://www.nngroup.com/articles/search-visible-and-simple/ · https://www.designsystem.qld.gov.au/components/search-input/tabs/overview
- [ ] **S-2. On mobile, put the search field at the top of the opened menu, or behind a labelled button in the
  header.** Why: teens and parents rely on search but struggle to phrase queries, so it must be easy to find. Source:
  https://www.nngroup.com/articles/usability-of-websites-for-teenagers/
- [ ] **S-3. Keep Drupal's existing Search block and results route. Only restyle the results (title, snippet, date).**
  Why: this is a platform constraint. Source: `design/BRIEF.md`

## 4. Accessibility: the WCAG 2.2 AA criteria that bite in practice

- [ ] **A-1. Focus not obscured (2.4.11, AA): a sticky header must never cover the focused element. Set
  `scroll-padding-top` to the header height, and keep any sticky header compact on mobile.** Why: sticky headers and
  banners are the textbook failure. Source: https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html
- [ ] **A-2. Focus visible (2.4.7, AA), aiming at Focus Appearance (2.4.13, AAA): a two-colour ring at least 2 CSS px
  thick on `:focus-visible`, e.g. `outline: 3px solid #fff; box-shadow: 0 0 0 6px #000` (or forest green on light
  surfaces).** Why: the indicator must reach 3:1 against every background. Green #1f4d2b on black is only **2.15:1**,
  so a single-colour ring fails somewhere, and WCAG technique C40 is exactly this two-colour pattern. Sources:
  https://www.w3.org/WAI/WCAG22/Techniques/css/C40 · https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html
- [ ] **A-3. Target size (2.5.8, AA): every pointer target is at least 24×24 CSS px, or spaced so a 24 px circle
  around it touches no other target. Aim for 44×44 on primary nav, top tasks, the menu button and pager (2.5.5, AAA).**
  Why: small icon links (social, pager, close buttons) are the usual failure. Inline links in sentences are exempt.
  Sources: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html ·
  https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced.html
- [ ] **A-4. Dragging movements (2.5.7, AA): anything that scrolls sideways (a gallery, horizontal chips) also has
  previous and next buttons, or simply wraps.** Why: users with motor impairments can't drag reliably. Source:
  https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html
- [ ] **A-5. Consistent help (3.2.6, A): "Contact Us", the phone and email in the footer, and "Student Absent?" stay
  in the same relative order on every page.** Why: users who need help learn where it is once. Source:
  https://www.w3.org/WAI/WCAG22/Understanding/consistent-help.html
- [ ] **A-6. Accessible authentication (3.3.8, AA): the Drupal login (`/user/login`, staff only) keeps
  `autocomplete="username"` and `"current-password"`, allows paste and password managers, and has no puzzle CAPTCHA.
  Any webform uses non-cognitive spam protection.** Why: memorising, transcribing or solving is a cognitive-function
  test. Source: https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-minimum.html
- [ ] **A-7. Redundant entry (3.3.7, A): a multi-step webform never asks twice for what it already has.** Source:
  https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/
- [ ] **A-8. Contrast (1.4.3 / 1.4.11): body text 4.5:1, large text (24 px, or 18.66 px bold) 3:1, UI boundaries and
  icons 3:1.** Why: the live site fails on 26 nodes. Bootstrap's default palette is not contrast-safe, so test every
  pair. Sources: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html ·
  https://getbootstrap.com/docs/5.3/getting-started/accessibility/ (see C-1 for the computed pairs)
- [ ] **A-9. Use of colour (1.4.1): links inside prose are underlined.** Why: green #1f4d2b next to black body text is
  2.15:1, below the 3:1 needed to tell links apart by colour alone. Source:
  https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html
- [ ] **A-10. Reduced motion: put every non-essential animation, smooth scrolling and view transition inside
  `@media (prefers-reduced-motion: no-preference)`. Nothing auto-plays.** Why: vestibular disorders (2.3.3 via
  technique C39) and 2.2.2 Pause, Stop, Hide. Sources: https://www.w3.org/WAI/WCAG22/Techniques/css/C39 ·
  https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html
- [ ] **A-11. Reflow (1.4.10): no two-dimensional scrolling at 320 CSS px. Wide tables scroll inside their own
  container, which needs `role="region"`, `aria-labelledby` pointing at the table caption or heading, and
  `tabindex="0"`.** Why: data tables are the allowed exception, but the page around them must still reflow. Source:
  https://www.w3.org/WAI/WCAG22/Understanding/reflow.html
- [ ] **A-12. Text spacing (1.4.12): no fixed heights on anything containing text. Layouts survive line-height 1.5,
  paragraph spacing 2em, letter spacing 0.12em and word spacing 0.16em.** Why: cards and pills with fixed heights clip
  text. Source: https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html
- [ ] **A-13. Resize text (1.4.4): fluid type uses rem bounds and a rem + vw preferred value. Test at 200% zoom and
  with a larger browser font size.** Why: a size made of vw alone does not grow with zoom. Sources:
  https://adrianroselli.com/2019/12/responsive-type-and-zoom.html ·
  https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html
- [ ] **A-14. Structure: keep "Skip to main content" as the first focusable element. Use landmarks (`header`, `nav`
  with an `aria-label` per nav, `main`, `footer`), one `h1` per page and no skipped heading levels.** Why: 2.4.1 and
  1.3.1. The live site skips a level (`h4.visually-hidden`). The BC Design System also requires one H1 and sequential
  headings. Source: https://www2.gov.bc.ca/gov/content/digital/design-system/foundations/typography
- [ ] **A-15. Link purpose (2.4.4): in a news card the article title is the link. If "Read more" stays, tie it to the
  title with `aria-describedby`. Never output an empty `<a>`.** Why: the live site has 15 links with no name and 3
  non-descriptive ones. Source: https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html
- [ ] **A-16. Images: give every content image a meaningful `alt`, and decorative images `alt=""`. Replace images of
  text with real text, e.g. the bell schedule becomes a real `<table>` with the same words.** Why: 1.1.1 and 1.4.5
  Images of Text. Six images on the live site have no alt. Sources: https://www.w3.org/WAI/tutorials/images/decision-tree/ ·
  https://www.w3.org/WAI/WCAG22/Understanding/images-of-text.html
- [ ] **A-17. Modals (the Accessibility Settings modal, a full-screen mobile menu): use the native `<dialog>` with
  `showModal()`. Focus moves in, Tab stays inside, Esc closes, and focus returns to the button that opened it.**
  Source: https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/
- [ ] **A-18. Keep the a11y module's "Accessibility Settings" as an extra. The page must pass WCAG without it.** Why:
  toolbars and overlays don't fix the underlying markup. Source: https://overlayfactsheet.com/

## 5. Performance: Core Web Vitals on Drupal

- [ ] **P-1. Targets at the 75th percentile, mobile and desktop separately: LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1.**
  INP replaced FID in 2024. Source: https://web.dev/articles/vitals
  - Our own budget for the concept: theme CSS ≤ 40 KB and theme JS ≤ 15 KB compressed, ≤ 2 font files above the
    fold, and no third-party request added by the theme.
- [ ] **P-2. The LCP image is an `<img>` in the HTML (not a CSS `background-image`), with `fetchpriority="high"`, no
  `loading="lazy"`, `width`/`height`, and `srcset`/`sizes`.** Why: the live LCP is a CSS background the preload
  scanner can't see. Resource load delay should stay under 10% of LCP. Source: https://web.dev/articles/optimize-lcp
- [ ] **P-3. Lazy-load every image below the fold (Drupal core's default since 9.1). Set the hero image's formatter
  to eager.** Why: lazy-loading an in-viewport image delays LCP. Sources: https://www.drupal.org/node/3173719 ·
  https://web.dev/articles/browser-level-image-lazy-loading
- [ ] **P-4. Turn on CSS and JS aggregation (Configuration → Development → Performance).** Why: the live site ships 63
  stylesheets and 31 scripts unaggregated. Drupal 10.1 rewrote aggregation to build files on demand. Source:
  https://www.drupal.org/docs/administering-a-drupal-site/managing-site-performance-and-scalability/aggregate-css-and-js-files-in-drupal-core
- [ ] **P-5. Serve images through Responsive Image styles (`srcset`/`sizes` or `<picture>`) with a WebP derivative.**
  Why: phones get small files, and all sources in one `srcset` must share a MIME type. Source:
  https://www.drupal.org/docs/user_guide/en/structure-image-responsive.html
- [ ] **P-6. CLS: `width`/`height` or `aspect-ratio` on every image and embed. Reserve space for JS-injected widgets:
  the GTranslate `.gtranslate_wrapper` gets a `min-height`/`min-width`. Server-render the alert region so nothing is
  injected later. Animate only `transform`/`opacity`.** Source: https://web.dev/articles/optimize-cls
- [ ] **P-7. INP: keep theme JS small, deferred and event-driven. No work over 50 ms in a handler, no layout
  thrashing, no client-side HTML rendering. Load third-party scripts (gtag, GTranslate) `async`/`defer`.** Source:
  https://web.dev/articles/optimize-inp
- [ ] **P-8. Fonts: at most 2 variable families, WOFF2 only (Google Fonts does this), `preconnect` to
  `fonts.gstatic.com` with `crossorigin`, and `display=swap`. Use a metric-matched fallback (`size-adjust`). Inline
  SVG icons replace Font Awesome.** Why: icon fonts cause layout shift, and every family costs a round trip. Source:
  https://web.dev/articles/font-best-practices
- [ ] **P-9. Keep pages bfcache-eligible (no `unload` handlers) and leave Drupal Internal and Dynamic Page Cache on.**
  Why: back and forward navigation becomes instant and doesn't reflow. Source: https://web.dev/articles/optimize-cls
- [ ] **P-10 (optional polish). Add cross-document view transitions with `@view-transition { navigation: auto; }`
  inside a `prefers-reduced-motion: no-preference` query.** Why: this is pure progressive enhancement for a multi-page
  site like Drupal (Chrome and Edge 126+, Safari 18.2+). Other browsers navigate normally. Source:
  https://developer.chrome.com/docs/web-platform/view-transitions/cross-document

## 6. Typography

- [ ] **TY-1. Body text at least 16 px (1rem), set in rem. Body line-height 1.5–1.6, headings about 1.1–1.25.** Why:
  BC Design System baseline (16 px, rem, 1.5 line-height). WCAG 1.4.8 asks for at least 1.5 within paragraphs.
  Sources: https://www2.gov.bc.ca/gov/content/digital/design-system/foundations/typography ·
  https://www.w3.org/WAI/WCAG22/Understanding/visual-presentation.html
- [ ] **TY-2. Fluid sizes with `clamp(min-rem, rem + vw, max-rem)`, e.g. H1 `clamp(2rem, 1.4rem + 2.6vw, 3.5rem)`. Use
  a modular scale such as the BC Design System's Major Third (H1 36 px down to H6 18 px at the small end).** Why:
  smooth scaling from 360 to 1440 px without breakpoints, and it stays zoomable (A-13). Sources:
  https://adrianroselli.com/2019/12/responsive-type-and-zoom.html ·
  https://www2.gov.bc.ca/gov/content/digital/design-system/foundations/typography
- [ ] **TY-3. Measure: about 60–75 characters for Latin body text (`max-width: 68ch`), never more than 80. Chinese
  text no more than 40 characters.** Sources: https://baymard.com/blog/line-length-readability ·
  https://www.w3.org/WAI/WCAG22/Understanding/visual-presentation.html · https://www.w3.org/TR/clreq/
- [ ] **TY-4. Request variable Google Fonts by axis range, e.g. `css2?family=Noto+Sans:wght@400..800&display=swap`.**
  Why: one file covers every weight. Noto Sans is the open parent of **BC Sans** (BC Sans is "a modified version of
  Noto Sans"). It gives the BC public-service feel, covers É/é for "École", and has `wght` 100–900 and `wdth` axes. A
  second, display family is optional. Sources: https://developers.google.com/fonts/docs/css2 ·
  https://www2.gov.bc.ca/gov/content/digital/design-system/foundations/typography
- [ ] **TY-5. `text-wrap: balance` on headings and `text-wrap: pretty` on paragraphs, as progressive enhancement.**
  Why: balanced headline lines and fewer orphans. `balance` works on 6 lines or fewer and is supported in all major
  engines. Source: https://developer.chrome.com/docs/css-ui/css-text-wrap-balance
- [ ] **TY-6. Use `font-variant-numeric: tabular-nums` for times, dates, phone numbers and the bell-schedule table.**
  Why: digits line up in columns. Source: https://developer.mozilla.org/en-US/docs/Web/CSS/font-variant-numeric
- [ ] **TY-7. Never `text-transform: uppercase` on running text, never justify text, and don't skip heading levels for
  visual size.** Why: 1.4.8 says no justification, and the BC Design System's heading-order rule applies. Source:
  https://www.w3.org/WAI/WCAG22/Understanding/visual-presentation.html

## 7. Colour and contrast (computed against the crest palette)

- [ ] **C-1. Use only tested pairs.** All ratios below were computed with the WCAG relative-luminance formula. Source:
  https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html

  | Pair | Ratio | Use |
  |---|---|---|
  | forest green #1f4d2b on white | **9.75:1** | body text, links, buttons (AAA) |
  | white on forest green #1f4d2b | 9.75:1 | header, footer, button text |
  | green #1f4d2b on tint #e8f0ea | 8.39:1 | tinted panels |
  | green #1f4d2b on warm off-white #f5f1e6 | 8.64:1 | alternate band |
  | green #2e7d32 on white | 5.13:1 | secondary accent text |
  | green #3b8a4f on white | **4.26:1** | large text and UI only, **not body** |
  | grey #6b7280 on white | 4.83:1 | lightest permissible meta text |
  | green #1f4d2b vs black | **2.15:1** | never the only cue between them (A-2, A-9) |
- [ ] **C-2. Never convey state by colour alone. Pair an icon or text with every colour (alerts, event types, active
  nav).** Source: https://www2.gov.bc.ca/gov/content/digital/design-system/foundations/colour
- [ ] **C-3. Name colours by role in design tokens (surface, text, border, icon, support for
  info/success/warning/danger) on `:root`. Components never use raw hex values.** Why: the BC Design System's token
  model. It also allows a dark mode later. Source:
  https://www2.gov.bc.ca/gov/content/digital/design-system/foundations/design-tokens

## 8. Emergency and closure alerts

- [ ] **AL-1. Render the existing `news_alerts` view (block_1, region `featured_top`) as the site-wide alert band:
  full width, at the top of every page directly under the concept banner, server-rendered.** Why: it is already a
  Drupal construct, so this adds no new platform pieces or words. Design systems put site alerts "one of the first
  things users see". Sources: https://designsystem.digital.gov/components/site-alert/ ·
  https://www2.gov.bc.ca/gov/content/digital/design-system/components/alert-banner
- [ ] **AL-2. Show one alert at a time. If several are published, combine them into a list inside one band.** Sources:
  https://designsystem.digital.gov/components/site-alert/ ·
  https://design-system.service.gov.uk/components/notification-banner/
- [ ] **AL-3. Content: a short heading, an optional one-line description, and a link to the full news item. Pair the
  colour with an icon. Use an emergency (dark or red) and an info variant.** Why: GOV.UK's emergency banner has exactly
  these parts and varies colour by severity. Source: https://design-guide.publishing.service.gov.uk/components/emergency-banner
- [ ] **AL-4. Make the band a `role="region"` with an `aria-label`, **not** `role="alert"`, because it is
  server-rendered and persistent. Use `role="alert"` only for something injected after load.** Source:
  https://designsystem.digital.gov/components/site-alert/
- [ ] **AL-5. On the homepage, show a larger variant. It must be the first content on a phone at 6:30 a.m.** Why:
  district closures are decided by 6:30 a.m., and the homepage is where parents check. Sources:
  https://design-guide.publishing.service.gov.uk/components/emergency-banner ·
  `/information/snow-and-extreme-weather-protocols`
- [ ] **AL-6. If the alert can be dismissed, store the dismissal in `localStorage` keyed to node id plus changed time,
  so a new or edited alert shows again. It never auto-hides.** Source:
  https://www2.gov.bc.ca/gov/content/digital/design-system/components/alert-banner (dismiss is optional)
- [ ] **AL-7. When the view is empty, render nothing: no empty band and no reserved gap.** Why: it is server-rendered,
  so this causes no CLS. Drupal views cache tags invalidate it on node save. Source: https://web.dev/articles/optimize-cls

## 9. Events and calendar

- [ ] **EV-1. Default to an agenda list grouped by date, at every width. A month grid is optional at tablet width and
  up.** Why: list views are faster for finding dates across month breaks, scale to phones and show details without a
  click. Grids are better only for spotting busy weeks. Source: https://discovery.ucl.ac.uk/id/eprint/1408077/ (UCL
  study, list vs grid calendars; abstract as indexed, the page returns 403 to fetchers)
- [ ] **EV-2. Every list entry has the same mini-IA: a date block (weekday, abbreviated month, day) top-left, then
  title, time and location when present.** Why: users scan the top-left first, and a consistent layout makes entries
  easy to compare. Source: https://www.nngroup.com/articles/list-entries/
- [ ] **EV-3. Write dates out, never all-numeric: "October 13, 2026", "Tue Oct 13", times like "4:30 pm". Put the
  machine-readable value in `<time datetime="2026-10-13T16:30">`.** Why: "01/02/03" is ambiguous, which matters for
  newcomer families. Date formatting counts as allowed UI chrome. Sources: https://design.canada.ca/style-guide/ ·
  https://www.nngroup.com/articles/date-input/
- [ ] **EV-4. Keep "Subscribe to our calendar" (the existing `webcal://…/calendar-feed.ics` link) prominent on the
  School Calendar page and next to the "Upcoming Events" block. Keep the monthly PDF link.** Why: a subscription
  pushes changes to families' own calendars, which suits a site visited only occasionally (TT-3). Source:
  `content/pages.json` (/school-calendar), Delta SD infographic (above)
- [ ] **EV-5. On the homepage, "Upcoming Events" shows the next few items, then a link to School Calendar.
  Rotation-day entries (ABCD, PLT Rot) can be styled as compact chips so they don't drown out real events.** Why: same
  words, better hierarchy. Source: https://www.nngroup.com/articles/list-entries/ ("reserve unique callouts")

## 10. Multilingual families

- [ ] **ML-1. Make Translate visible in the header on every page, within the first screen on mobile, labelled with
  the globe icon and the existing word "Translate".** Why: Richmond's 2021 Census mother tongues (base 209,040) are
  **Cantonese 21.5% (44,985)**, **Mandarin 21.1% (44,060)** and English 31.3%. **10.5% (21,870) speak neither English
  nor French.** Source: Statistics Canada, Census Profile 2021, Richmond (CY),
  https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/details/page.cfm?Lang=E&DGUIDlist=2021A00055915015
  (read 2026-10-06)
- [ ] **ML-2. Show language names in their own language and script, with `lang` on each name (e.g. `<span
  lang="zh-Hans">中文（简体）</span>`), not flags. Choose a GTranslate style with names and a dropdown instead of the
  current flags.** Why: WCAG 3.1.2 Language of Parts, and a flag is not a language (the live site shows English as the
  Canada flag). Sources: https://www.w3.org/WAI/WCAG22/Understanding/language-of-parts.html ·
  https://www.drupal.org/project/gtranslate (style options)
- [ ] **ML-3. All meaningful text is real HTML text: no images of text or tables.** Why: GTranslate translates the DOM
  only, so the bell-schedule image stays English for every translated visitor. Source:
  https://www.w3.org/WAI/WCAG22/Understanding/images-of-text.html
- [ ] **ML-4. Mark names that must not be translated with `translate="no"`: the school name, "Strikers", "Striker
  Weekly", "MyEd", "School Cash Online", phone numbers.** Why: Google's translator honours the attribute, so "Strikers"
  isn't turned into a literal word. Source: https://www.w3.org/International/questions/qa-translate-flag
- [ ] **ML-5. Layouts survive text expansion and contraction: no fixed widths on buttons, nav items or cards. Font
  stacks fall back to system CJK fonts (PingFang, Microsoft YaHei/JhengHei, Noto Sans CJK) instead of loading Noto
  Sans SC/TC web fonts. CJK text gets line-height about 1.7 and a measure of 40 characters or less (via `:lang(zh)` if
  the widget updates `<html lang>`; verify).** Why: translated strings change length, CJK web fonts are several MB, and
  the Chinese layout requirements put the line gap at 50–100% of font size. Sources:
  https://www.w3.org/International/articles/article-text-size · https://www.w3.org/TR/clreq/
- [ ] **ML-6. Load GTranslate's third-party script `async` and reserve its box (P-6). Don't add other translation
  tooling.** Why: the widget sends page text to Google's servers and loads from cdn.gtranslate.net. It is existing
  site functionality, kept as-is. Source: https://www.drupal.org/project/gtranslate
- [ ] **ML-7 (recommendation for the principal, config only, not in the concept). The GTranslate list has `zh-CN`
  only, with no Traditional Chinese (`zh-TW`), Punjabi or Tagalog. Yet Cantonese is the top non-English mother tongue,
  Tagalog is 3.7% and Punjabi 2.4%.** Why: adding languages is a module setting, not a platform change. Source: Census
  Profile (above)

## 11. Design systems worth borrowing from

- [ ] **DS-1. BC Design System, the provincial public-service look: BC Sans/Noto Sans, a 16 px rem base, a Major
  Third scale, role-named tokens, one alert banner at a time with `role="status"` by default, header and footer
  components, WCAG AA.** (`design.gov.bc.ca` did not resolve on 2026-10-06; the canonical home is the www2 URL.)
  Source: https://www2.gov.bc.ca/gov/content/digital/design-system
- [ ] **DS-2. Canada.ca: the "Most requested" band (TT-4) and its date and time style (EV-3).** Sources:
  https://design.canada.ca/common-design-patterns/most-requested.html · https://design.canada.ca/style-guide/
- [ ] **DS-3. GOV.UK: high-contrast, two-tone focus states that work on every background, one notification banner per
  page placed before the `h1`, and an emergency banner that is larger on the homepage.** Sources:
  https://design-system.service.gov.uk/get-started/focus-states/ ·
  https://design-system.service.gov.uk/components/notification-banner/ ·
  https://design-guide.publishing.service.gov.uk/components/emergency-banner
- [ ] **DS-4. USWDS: when to use which ARIA role on site alerts (AL-4).** Source:
  https://designsystem.digital.gov/components/site-alert/
- [ ] **DS-5. WAI-ARIA APG: disclosure navigation (IA-5) and modal dialog (A-17).** Source:
  https://www.w3.org/WAI/ARIA/apg/patterns/

## 12. Drupal 10 front end

- [ ] **D-1. Ship as a new sub-theme of `bootstrap_barrio`, generated with `scripts/create_subtheme.sh` (or by copying
  `subtheme/`). Keep the region machine names of `rsd_sites_barrio` (e.g. `featured_top`) so existing block placements
  map 1:1.** Source: https://www.drupal.org/node/2977597
- [ ] **D-2. Build components as Single Directory Components: `components/<name>/` holds `<name>.component.yml` (the
  props and slots schema), `.twig`, `.css` and `.js`, and is called with `include('theme_name:card', {...})` or
  `embed` for slots.** Why: SDC is stable in core since **10.3**, and the live site runs 10.6.14. Each component's
  CSS and JS attach automatically, only where it is used. Source:
  https://www.drupal.org/docs/develop/theming-drupal/using-single-directory-components
- [ ] **D-3. Twig: override by theme suggestion (`page.html.twig`, `menu--main.html.twig`,
  `block--system-menu-block--main.html.twig`, `views-view-unformatted--news-alerts.html.twig`, `node--article--teaser`)
  and call SDCs from them. Keep logic in preprocess, not Twig.** Source:
  https://www.drupal.org/docs/develop/theming-drupal/twig-in-drupal/twig-template-naming-conventions
- [ ] **D-4. `libraries.yml`: one global library declared in `.info.yml` (tokens, base, layout); per-template extras
  via `attach_library()`; `libraries-override` to drop unneeded inherited assets. JS depends only on `core/drupal` and
  `core/once`, with `attributes: { defer: true }`. Bump `version` whenever a file changes.** Source:
  https://www.drupal.org/docs/develop/theming-drupal/adding-assets-css-js-to-a-drupal-theme-via-librariesyml
- [ ] **D-5. Write vanilla JS as `Drupal.behaviors.x = { attach(context) { once('x', '.sel', context).forEach(…) } }`
  and never use jQuery in theme code.** Why: `core/once` replaced `jquery.once` in 9.2, and Barrio 5.5.x no longer
  requires jQuery. Behaviors re-run on AJAX (Views pagers). Sources: https://www.drupal.org/node/3158256 ·
  https://www.drupal.org/project/bootstrap_barrio ·
  https://www.drupal.org/docs/drupal-apis/javascript-api/javascript-api-overview
- [ ] **D-6. Put CSS custom properties on `:root` as the single source of truth, then map them to Bootstrap: the root
  `--bs-*` variables plus component variables such as `.btn-primary { --bs-btn-bg: var(--color-brand); … }`. Setting
  `--bs-primary` alone doesn't recolour compiled components. Load Bootstrap from the local library through Barrio's
  setting, not the jsDelivr CDN.** Sources: https://getbootstrap.com/docs/5.3/customize/css-variables/ ·
  https://www.drupal.org/project/bootstrap_barrio (local or composer delivery)
- [ ] **D-7. Make components respond to their container (`container-type: inline-size`, `@container`), not the
  viewport, so the same card works in the main column and in a sidebar.** Why: Baseline since February 2023. Source:
  https://web.dev/blog/cq-stable
- [ ] **D-8. Every visual component maps to an existing construct.** Source: `design/BRIEF.md`;
  `research/drupal-mapping.md` holds the full map.

  | Component | Drupal construct |
  |---|---|
  | alert band | `news_alerts` view |
  | "Student Absent?" | its block |
  | "Latest News" and "News Archive" | news views |
  | "Upcoming Events" | events view and the ICS feed |
  | Translate | `block-gtranslate` |
  | Accessibility Settings | a11y module block |
  | mega menu | main menu, system menu block depth 2 |
  | breadcrumbs | system breadcrumb block |
  | landing-page cards | child menu links or book/children |
- [ ] **D-9. Progressive enhancement: navigation, search, the calendar link and alerts work with JS off. Top-level
  links go to landing pages, and JS only adds the panels.** Why: server-rendered HTML is the platform contract, and it
  is resilient on slow school Wi-Fi. Source: `design/BRIEF.md`; https://web.dev/articles/optimize-inp (less JS
  means better INP)

## 13. Where these rules meet the brief's constraints

- **No new words:** pattern labels from design systems ("Most requested", "Quick links", "Alert") can't be copied.
  Use corpus words ("Helpful Links", "Parents", "Students", block titles) or no heading. Every UI-chrome word
  ("Menu", "Back to top") goes into `tools/ui_words.txt`. Visually hidden text still counts as words: build accessible
  names from existing titles (`aria-labelledby` or `aria-describedby`) rather than new phrases.
- **Logo:** the crest is green, black and white only. The focus ring and accents must be derived from those colours,
  so use two-tone white plus black or green rings (A-2) rather than GOV.UK yellow.
- **Supply chain:** drop Font Awesome and the CDN copies of Bootstrap and js-cookie from the theme (P-8, D-6). GTranslate
  and gtag are existing site services, not theme code. Keep them, loaded async.
