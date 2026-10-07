# Design decision: direction for the full build

Judged 2026-10-06 against `design/BRIEF.md`. Evidence is in `shots/judge/`: home pages at 1440 (full page), home pages at
390 (first screen at 3x, full page at 1.5x because a 3x full page goes past Chrome's 16384 px capture limit), page.html
at both sizes (viewport), the Parents mega menu open at 1440 and the phone menu open at 390. Also checked in the browser:
keyboard focus on the first Tab stop, the Parents disclosure (Enter opens it, Esc closes it and returns focus), the phone
menu (Enter opens it, Esc closes it and returns focus), duplicate ids, `h1` count, `tel:` links, and whether the crest is
untouched (no filter, clip, blend or recolour). Copy was checked with `tools/check_copy.py` plus a stricter pass that also
reads `aria-hidden` text, CSS `content:` strings and JS-inserted strings.

## Scores

Weights: visual excellence and modernity x3, school identity with the crest untouched x2, parent/student task clarity x2,
accessibility x2, content fidelity x2, Drupal feasibility x1. The maximum is 120.

| Concept | Visual x3 | Identity x2 | Tasks x2 | A11y x2 | Content x2 | Drupal x1 | **Total** |
|---|---|---|---|---|---|---|---|
| **heritage** (Crest & Canopy) | 8.5 | 9.5 | 8 | 9 | 8 | 9 | **103.5** |
| clarity (Community Clarity) | 7 | 7.5 | 9.5 | 9 | 8 | 9 | **98** |
| strikers (Striker Energy) | 8.5 | 7 | 7.5 | 7.5 | 7.5 | 8 | **92.5** |

### heritage: 103.5
- **Visual.** This is the most finished piece. The editorial serif lockup, the arched duotone "canopy" photo with the 1962
  mark, arched date chips and arched heritage photo repeat one motif from top to bottom, and the paper/forest/brass palette
  feels expensive. Its weak spots: the Helpful Links tiles are generic, the Strikers logo is a 72 px badge, the Mission
  card has a big empty middle, and the page is quiet all the way down, with no high-energy moment.
- **Identity.** The strongest of the three. It uses the crest untouched at 3 sizes (masthead, sticky mini-crest, footer
  sign-off), takes its forest green from the crest, and shows 1962, École and the bilingual quote. It reads as *this*
  school, not as a template.
- **Tasks.** Student Absent? appears 3 times (tile, utility pill, phone bottom bar), with `tel:+16046686600,1`. The Today
  strip is very good. At 390 px, though, the alert band (about 300 px) plus the hero push the tiles to the bottom of the
  first screen.
- **A11y.** The skip link is the first Tab stop. The 3-colour focus ring shows on paper and on forest. The phone menu is a
  real modal `<dialog>` and focus comes back to the button. The mega menu passes the Enter and Esc tests, and body links are
  underlined. The 4 hidden mega-panel `h3`s and the alert `h2` come before the `h1` in the DOM.
- **Content.** check_copy is clean apart from the GTranslate language names. Upcoming Events skips 2 real events
  (Oct 14 "Gr. 12 CLC Pitch Day" and Oct 22 "Gr. 12 TVR Signing Assembly (PLT)") but shows events after them. The Snow
  protocol is shown as a live alert in October.
- **Drupal.** HTML comments name each region and view, and the live hooks are kept (`#header-img-area`, `.gt_selector`,
  `.news-alert.standard-alert`, a11y classes). Vanilla JS, no libraries.

### clarity: 98
- **Visual.** Clean and competent, but it looks like a 2023 SaaS/edtech template. The Helpful Links tiles are mostly
  empty space, news dates show only the month ("Oct 2026"), and Atkinson's slashed zeros make phone numbers and
  addresses look technical. It would not make anyone gasp.
- **Identity.** The crest is untouched (it is also used large in the About band) and the greens come from the crest, but
  the page has little personality of its own.
- **Tasks.** The best of the three. The first screen at 390 shows the slogan, a Today card (date, Rotation One / PLT Rot 2,
  the next real event) and a full-width Student Absent? call button. It has Parents and Students hubs that list every
  child link, an inner-page rail with Student Absent?, Bell Schedule and School Calendar, and a 4-item phone bar.
- **A11y.** It uses a hyperlegible body face, the skip link is the first Tab stop, focus rings are clear, targets are
  44 px, and the menus pass the Enter and Esc tests.
- **Content.** check_copy is clean and there is no fake alert. It also skips the Oct 22 event, shows month-only dates,
  and lifts a bare "1000" out of "over 1000 students".
- **Drupal.** The best mapping comments, a menu rendered once, and the smallest JS.

### strikers: 92.5
- **Visual.** It has the most "wow": condensed Archivo, the scoreboard Bell Schedule band, an outlined STRIKERS word
  driven by scroll, and provincial-banner pennants. But it reads like an athletics department or esports brand, not an
  École secondaire. Nearly everything is in caps, the black-and-gold hazard stripes feel like a construction site, and
  "STUDENT ABSENT?" sits on top of gold stripes.
- **Identity.** The crest is untouched (on a white plate in the footer), but the voice comes from the Strikers helmet
  (gold and ink black), not from the crest. The school name is reset as condensed caps.
- **Tasks.** The overlapping bento is strong on desktop. At 390, the slogan fills the first screen and only the Student
  Absent? tile starts to show. `tel:604-668-6600` has no `,1` to dial the extension.
- **A11y.** The first Tab stop is the concept-banner link and the skip link is second. Long all-caps condensed text is
  harder for ESL and dyslexic readers. The page `h1` has a 0.7 s "rise" entrance animation, and screenshots caught it
  half-faded.
- **Content.** It turns a calendar entry (PRO-D DAY - NO SCHOOL) into an alert. It shows "Student Achievement: schools
  should be for all learners", which is one bullet cut out of a list. Its Upcoming Events are correctly chronological.
- **Drupal.** Feasible, but the region mapping lives only in CSS comments, not in the HTML.

## Winner: heritage (Crest & Canopy)

It best matches the brief's "feels like *this* school" test, and it is the version a principal can sign off on. Its
weaknesses are the phone first screen and a lack of energy further down, and those are exactly what the other two do
best. So the build is heritage's system (type, palette, arch motif, components) with the grafts below.

## Grafts from the runners-up

1. **(clarity) Phone first screen.** On phones, put a Today card directly under a compact hero: the date, the
   Rotation One and PLT Rot 2 chips, a "Next" line with the next real event linked, and a full-width Student Absent?
   call button (`tel:+16046686600,1`). At 360x640, Student Absent? and at least 2 more top tasks must show without
   scrolling.
2. **(clarity) Parents and Students hubs.** Add 2 home-page panels that list every child link from `menu.json`, with
   the section title as a link with an arrow ("Parents →"). Give the mega-panel titles the same arrow so it is obvious
   they are links.
3. **(clarity) Inner-page rail.** Under Student Absent?, add Bell Schedule and School Calendar links, so the rail does
   more than repeat the contact block.
4. **(clarity) Numbered list.** On Student Attendance, use a numbered list for "Please provide the following
   information" instead of check marks, which read as "already done".
5. **(strikers) Energy band.** Add one high-energy band between About and the footer, in forest with gold used only on
   dark: a large Strikers Athletics logo, the quote "As a Striker… pride, sportsmanship, and class.", and the 4
   provincial-banner pennants (field hockey, soccer, rugby, curling) with the real sentence above them. This replaces
   the 72 px badge card. An outlined "STRIKERS" word may drift only under `prefers-reduced-motion: no-preference`.
6. **(strikers) Collaboration Days.** Add the 2026-27 Collaboration Days chips to heritage's Today / Bell Schedule
   strip, with past ones struck through and the next one highlighted. Give the "Today" day card a tag like the
   scoreboard has.
7. **(strikers) Sticky phone pill.** Once the header has scrolled away, slide a compact Student Absent? phone pill into
   the sticky nav row next to the mini-crest.
8. **(strikers) Featured news.** Show the 2 dated rows after the lead story as small cards with teasers. Keep the plain
   rows for the rest.

## Fixes the winner needs

1. **Events data.** Upcoming Events must be the next N events in date order after removing only the rotation codes
   (`ABCD`, `PLT Rot n`, `COLLAB ABCD`). Today it skips Oct 14 "Gr. 12 CLC Pitch Day" and Oct 22 "Gr. 12 TVR Signing
   Assembly (PLT)". Build the list from `content/events.json`, not by hand. Gold highlighting stays only on no-school
   days (Thanksgiving, Pro-D Day).
2. **Data-driven Today strip.** The Today strip is hard-coded. Build it from `events.json` (the rotation code for the
   build date) and `bell-schedule.json`, and note the Drupal source in the comment: an `upcoming_events` display with a
   date contextual filter plus a custom block for the timetable.
3. **Compact phone alert.** On phones, collapse the alert band to one line (icon, title, Read more, Close), at most about
   72 px tall. Keep the Snow protocol text as the demonstration, because it is real, evergreen copy. Keep it mapped to
   `featured_top` / `news_alerts`.
4. **Name shown twice.** On the desktop home page, the full name appears twice within 300 px (masthead and hero).
   Either let the hero lockup be the only large name on the front page (the masthead shows the crest and a small
   wordmark), or start the hero with the slogan. Keep exactly one `h1`.
5. **Heading order.** Turn the 4 mega-panel feature-card `h3`s into non-headings (`p.mega-card-title`) or `h2`s, and
   make sure no heading level is skipped in the DOM before the `h1`.
6. **Right-size images with `sips`.** `9f4ea14a6ad5.png` (Strikers logo, 2511 px, 241 KB) should be at most 2x its
   display size. `de1fed0d163f.png` (building, 207 KB PNG) should become a JPEG. Set `width`/`height`, `decoding="async"`
   and lazy loading below the fold. The full-page capture showed the logo blank because the large image decoded late.
7. **Mission card.** Its middle is empty. Pin the quote to the top and the link to the bottom with a smaller fixed
   height, or merge the card into the About block.
8. **Helpful Links tiles.** Give them more character. Tie the icon wells to the arch motif and show live sub-lines
   where the data exists (next event under School Calendar, today's code under Bell Schedule, the week under Striker
   Weekly). Keep 8 tasks at most.
9. **Phone menu button.** Add `aria-haspopup="dialog"` and `aria-expanded` to it, and add the Translate select inside
   the phone menu dialog so multilingual families can find it in both places.
10. **Content check.** Keep every visible phrase passing `check_copy.py`, and add the GTranslate language names to
    `tools/ui_words.txt` (that file is empty today). Keep the "1962", "8–12" and "École" fact labels exactly as written
    in the About Us copy.
11. **Re-check.** Re-run Lighthouse (home on mobile and desktop, page on mobile and desktop), measure no horizontal
    scroll at 360, 390, 768, 1024 and 1440, and check reduced motion and forced colours after the grafts, especially the
    new energy band.
