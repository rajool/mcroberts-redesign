# Information architecture

The navigation, landing pages and URLs of the redesigned McRoberts site. Machine-readable source: `design/ia.json`.
Every label is copy that already appears on the live site (a page title, menu label, heading or phrase in
`content/corpus.txt`). No page body or page title changes. Only the structure changes: menus, groups, hubs, URLs, and
the duplicate and empty pages.

`python3 tools/check_ia.py design/ia.json` reports **239 nodes, 0 problems**. Further checks:
- every featured link sits in its own panel;
- no group holds more than 6 links;
- no clean URL collides with an existing page;
- no two aliases point at the same page;
- no menu links to a retired page or to an old URL that has a clean alias;
- 55 of the 57 live content pages are in the main menu or the utility bar itself. The other two (the Library
  Catalogue page, which only holds a link, and the concussion PDF page) are listed on their hubs.

## 1. Tree-test evidence

Four trees were tested blind with simulated testers: the live menu and three proposals (audience-first, top-task-first
and topic-first). Each tree had 2 independent testers and the same 26 tasks for 7 personas. A task counts as
failed below when either tester missed the answer page.

| Tree | Success | First click | Tasks failed |
|---|---|---|---|
| Live site (current menu) | 73.1% | 73.1% | 7, 12, 13, 14, 16, 21, 23, 24 |
| Audience-first | 86.5% | 88.5% | 1, 5, 16, 20 |
| **Top-task-first (base of this IA)** | **88.5%** | **94.2%** | 1, 16, 20 |
| Topic-first | 80.8% | 76.9% | 1, 5, 6, 8, 16, 20, 23 |
| **Final IA (this file), fresh blind re-test** | **92.3%** | **94.2%** | 2 new testers, same 26 tasks (2026-10-06) |

| # | Task (persona) | Live | Audience | Tasks | Topics | Final tree: where the answer is |
|---|---|---|---|---|---|---|
| 1 | Phone number to report an absence (new Grade 8 parent) | yes | **no** | **no** | **no** | Utility: Student Absent? and the number beside it · Parents > Student Attendance · Contact Us |
| 2 | Is school closed after a snowstorm? | yes | yes | yes | yes | School Calendar > and Parents > Snow and Extreme Weather Protocols |
| 3 | Order the free hot lunch | yes | yes | yes | yes | Parents > Universal Hot Lunch @ McRoberts |
| 4 | When the December break starts | yes | yes | yes | yes | School Calendar |
| 5 | Set up an account to pay fees (Grade 11 parent) | yes | **no** | yes | **no** | Parents > School Cash Online |
| 6 | MyEd password help | yes | yes | yes | **no** | Parents > MyEd Parent Portal: Request Assistance |
| 7 | Course list and due date for Grade 12 | **no** | yes | yes | yes | Students > Academic Support > Grade 8 - 11 (Incoming 9 - 12) Program Planning |
| 8 | Concussion guidance | yes | yes | yes | **no** | Parents > and Extra-Curricular > District Concussion Protocol, with the PDF listed on it |
| 9 | A copy of the Friday newsletter | yes | yes | yes | yes | News > Newsletters |
| 10 | When classes end on Monday (Grade 9) | yes | yes | yes | yes | School Calendar > Bell Schedule |
| 11 | Book a counsellor | yes | yes | yes | yes | Students > Counselling Centre |
| 12 | Form for volunteer hours | **no** | yes | yes | yes | Students > Required for Graduation > Career Education Volunteer Hours |
| 13 | Chess club room | **no** | yes | yes | yes | Extra-Curricular > Club Directory |
| 14 | Basketball team contact | **no** | yes | yes | yes | Extra-Curricular > Strikers Athletics |
| 15 | Updates for this year's grads (Grade 12) | yes | yes | yes | yes | Students > Grad 2027 |
| 16 | Send official marks to universities | **no** | **no** | **no** | **no** | Students > Career Exploration > Post-Secondary Info · Students > Career Centre Information · Grad 2027 hub |
| 17 | Reference letter form and notice | yes | yes | yes | yes | Students > Career Exploration > Reference Letters |
| 18 | Library hours | yes | yes | yes | yes | Library |
| 19 | Area the school serves (prospective family) | yes | yes | yes | yes | Parents > Welcome to McRoberts > Catchment · About Us > Catchment |
| 20 | Can my children continue in French? | yes | **no** | **no** | **no** | Parents > Welcome to McRoberts > French Immersion Program · About Us > French Immersion Program |
| 21 | Grade 8 course selection sheet | **no** | yes | yes | yes | Parents > Welcome to McRoberts > and Students > Academic Support > Grade 7 (Incoming 8) Program Planning |
| 22 | Donate with a tax receipt (business owner) | yes | yes | yes | yes | Parents > Resources for Parents > Donations · About Us > Donations |
| 23 | Principal's name and email | **no** | yes | yes | **no** | About Us > Our Staff · footer |
| 24 | Last month's PAC minutes | **no** | yes | yes | yes | Parents > Parent Advisory Committee (PAC) > PAC Meeting Minutes |
| 25 | When and where the PAC meets | yes | yes | yes | yes | Parents > Parent Advisory Committee (PAC) |
| 26 | Driver form and police check for an away game | yes | yes | yes | yes | Parents > Resources for Parents > and Extra-Curricular > Athletics Info for Parents · Strikers Athletics |

**What the evidence shows**
- All three new trees beat the live menu, by 8 to 15 points. Most of the live menu's failures are pages it never
  shows: Strikers Athletics, Club Directory, PAC Meeting Minutes, the Program Planning sub-pages and Career Education
  Volunteer Hours. The top-task-first tree is best on both measures and fails nothing that another new tree passes,
  so it is the base.
- Tasks 1, 16 and 20 failed in **every** new tree. The cause is structural, so choosing a different tree would not
  have fixed them:
  - **Task 1:** all three put "Student Absent?" in the utility bar as a bare `tel:` link. The label matches the
    task, but the number stays hidden in the link, and on a desktop the link does nothing useful. The live menu,
    which sends people to Student Attendance, passed.
  - **Task 16:** no label anywhere says post-secondary or universities, and "Career Centre" reads as jobs.
  - **Task 20:** no label mentions French Immersion. The answer page, About Us, appeared only as a top label.
- The audience tree's School Cash Online information sat in an unlabelled third column, while the sign-in sat in the
  utility bar (task 5). The topic tree spread top tasks across the vague buckets "Learning" and "Services" and put
  protocols under About Us (tasks 5, 6, 8, 23). Those are patterns to avoid, and this IA avoids them.
- The final tree puts every answer under a labelled path that matches the task's wording. Full success is a
  projection, not a measurement: re-run the tree test on `design/ia.json` before the build is signed off. With 2
  testers per tree, one task is worth about 4 points, so read the figures as direction, not precision.

## 2. Structure

### Main menu: 7 items, mega menu on desktop, the same tree as an accordion on phones

Each top label is a real link to its hub, and a separate button opens its panel. In every panel the first column is
the "most requested" column: the links marked `featured` in `ia.json`, shown first and slightly stronger. The other
columns use headings that already exist on the live site, or have no heading.

1. **Parents** `/parents`
   - *Most requested:* Student Attendance · School Cash Online · MyEd Parent Portal: Request Assistance · Learning
     Updates · Universal Hot Lunch @ McRoberts
   - **Welcome to McRoberts:** Grade 7 (Incoming 8) Program Planning · French Immersion Program (`/about-us`) ·
     Catchment · Presentations for Parents
   - **Resources for Parents:** Updating Student Contact Information · Student Accident Insurance · Athletics Info for
     Parents · Donations · Helpful Links
   - **Important information for parents:** Responsible Use of Technology Info · Violence Threat Risk Assessment
     (VTRA) Protocol and Fair Notice · District Concussion Protocol · Snow and Extreme Weather Protocols
   - **Parent Advisory Committee (PAC)** (heading links to `/parents/pac`): PAC Meeting Agendas · PAC Meeting Minutes
2. **Students** `/students`
   - *Most requested:* Student Login · MyEd Student Portal: Request Assistance · Counselling Centre · Career Centre
     Information · Grad 2027
   - **Academic Support:** Program Planning · Grade 7 (Incoming 8) Program Planning · Grade 8 - 11 (Incoming 9 - 12)
     Program Planning · Online Learning with Richmond Virtual School (RVS) · Core Competencies · Personal Learning
     Time (PLT)
   - **Required for Graduation:** Provincial Graduation Assessments · Capstone/Career-Life Connections (CLC) ·
     Career Education Volunteer Hours
   - **Career Exploration:** Post-Secondary Info (`/students/career-centre-information#post-secondary-info`) ·
     Reference Letters · Career Education · Career Education 8 & 9
3. **School Calendar** `/school-calendar`
   - *Most requested:* Bell Schedule
   - Personal Learning Time (PLT) · Snow and Extreme Weather Protocols · Subscribe to our calendar (`webcal:` feed)
4. **News** `/news`
   - *Most requested:* Newsletters
   - School Learning Story
5. **Extra-Curricular** `/extra-curricular`
   - *Most requested:* Strikers Athletics · Club Directory
   - **Resources for Parents:** Athletics Info for Parents · District Concussion Protocol
6. **Library** `/library`
   - *Most requested:* Library Catalogue (opens the catalogue itself) · Digital Resources
   - Read & Listen · Make & Play · Q & A · Biblio Bites: A Monthly Library Newsletter
7. **About Us** `/about-us`
   - *Most requested:* Contact Us · Our Staff
   - Mission Statement · French Immersion Program (`/about-us`) · Catchment · Donations

"Home" is dropped because the crest links home. The vague "Information" bucket is split up and its pages are filed
by task.

### Utility bar (every page)

**Student Absent?** (to Student Attendance) · **604-668-6600 (Ext. 1)** (`tel:+16046686600,1`) · **MyEducation BC** ·
**School Cash Online** · **Office 365** · **Contact Us**

Rendering rules:
- "Student Absent?" and the number make up one pill, just as the live sidebar block reads ("Student Absent?" over
  "604-668-6600 (Ext. 1)").
- The label opens the attendance page: the number, what to tell the school, and the 8:30 a.m. confirmation rule.
- The number is always visible and dials on tap.
- On phones the pair leads the sticky bottom bar, followed by Translate, Search and Menu. The number keeps its 44 px
  tap target, so an absence is still one tap.
- The three sign-ins go straight to the services. Their help pages sit in the panels.

### Footer: 3 short columns, with no copy of the main menu

- **Get in Touch:** Contact Us · Our Staff · Student Absent? · 604-668-6600 (Ext. 1) · mcroberts@sd38.bc.ca ·
  8980 Williams Road (map)
- **Helpful Links:** MyEducation BC · School Cash Online · Office 365 · Subscribe to our calendar · School District
  No. 38 (Richmond)
- **Important information for parents:** Snow and Extreme Weather Protocols · District Concussion Protocol ·
  Violence Threat Risk Assessment (VTRA) Protocol and Fair Notice · Responsible Use of Technology Info · ERASE

The existing address, Social Media, Accessibility Settings, district logo and copyright blocks stay. "Log in" stays
off the public menus.

### Hubs (landing pages that list their pages as cards, under the page's own body)

| Hub | Sections |
|---|---|
| `/` (home task band) | **Parents:** Student Attendance, School Calendar, Newsletters, Bell Schedule, School Cash Online, MyEd Parent Portal: Request Assistance, Universal Hot Lunch @ McRoberts, Contact Us · **Students:** Student Login, Counselling Centre, Career Centre Information, Grad 2027, Program Planning, Bell Schedule, Club Directory, Library |
| `/parents`, `/students`, `/school-calendar`, `/news`, `/extra-curricular`, `/about-us` | The same groups as the menu panel (self-links dropped) |
| `/library` | The menu panel, but the first card is the Library Catalogue page |
| `/students/grad` (Grad 2027) | **Required for Graduation:** Provincial Graduation Assessments, CLC, Career Education Volunteer Hours · **Post-Secondary Info:** Career Centre Information, Reference Letters |
| `/students/program-planning` | Grade 7 (Incoming 8) and Grade 8 - 11 (Incoming 9 - 12) Program Planning |
| `/students/career-education` | Career Education 8 & 9, CLC, Career Education Volunteer Hours (the page body says "use the links below") |
| `/parents/pac` | PAC Meeting Agendas, PAC Meeting Minutes |
| `/parents/district-concussion-protocol` | The school's PDF "Concussion Awareness, Response and Management" |

A hub card's label is the menu label of the same link (so the fragment link reads "Post-Secondary Info" and the bell
page reads "Bell Schedule"). Otherwise it is the page title, and for the PDF page it is the file's link text.

## 3. Decisions and rationale

**Base: top-task-first.** It had the best success and first-click rates. Its "most requested" column reflects the
Canada.ca / GOV.UK pattern, and research IA-2 to IA-8 already backs its mechanics: visible desktop menu, mega panels,
disclosure buttons with top-level links, and hubs.

**Fix for task 1: the number becomes visible.** "Student Absent?" now opens Student Attendance, the page the live
menu used and that passed. The number sits next to the label as its own `tel:` link, in the live block's own words,
so it can be seen on a desktop and dialled with one tap on a phone. This also fixes audit C1: the absence line is on
every page and is tappable.

**Fix for task 16: post-secondary scent.**
- "Post-Secondary Info" is the Career Centre page's own `h2`. It is added as a deep link at the top of a "Career
  Exploration" column. That heading comes from the Counselling Centre page, where it lists post-secondary planning.
- The Career Centre page is 1,100 words long, so the link lands on the right section: the theme gives each body
  heading an `id` taken from its own text. Without the id, the link still opens the right page.
- Grad 2027 is a one-sentence page and the first place a Grade 12 student looks. It becomes a hub with a
  "Required for Graduation" section (from the graduation assessments table) and a "Post-Secondary Info" section.
  The page itself is not edited.

**Fix for task 20: French Immersion becomes visible.** "French Immersion Program" is live copy from the catchment
page. It links to About Us, whose first sentence says the school is dual-track English and French Immersion. It is
listed under About Us and under Parents > Welcome to McRoberts, where prospective families start. The school's
defining program (the "École" in its name) was missing from every menu.

**Grafts from the other proposals**
- *Year-free Grad URL* (audience, topics): `/students/grad`, labelled with the page's own title, "Grad 2027". The
  label changes with the title each fall, and the URL never has to.
- *Library Catalogue opens the catalogue* (audience): the in-between page only holds a link, so the menu skips it.
  The page stays published and is the first card on the Library hub.
- *The concussion PDF stays* (topics): the other two proposals redirected `/media/1069` away. Strikers Athletics
  links to it ("here"), so that redirect would have broken the link to the school's PDF. It keeps working: it gets a
  clean alias under the protocol, and the District Concussion Protocol page lists it, so parents find it where they
  look.
- *One URL family for School Learning Story* (topics): the 5 posts under `/our-school-story/news/...` are listed on
  School Learning Story, so they move under `/school-learning-story/news/...`.
- *Short PAC URLs:* `/parents/pac/meeting-minutes` and similar, short enough to paste into a PAC email.
- *Donations cross-listed under About Us:* donors who are not parents look there. The page stays at
  `/parents/donations`, its first home, where the tree test found it.

**Labels**
- Every menu label is the page title, with these exceptions. All of them are live copy:

| Label | Page title | Why |
|---|---|---|
| Bell Schedule | Timetable Structure 2026-2027 | The live menu word; the timetable image itself is headed BELL SCHEDULE |
| Catchment | McRoberts Catchment | The live menu word |
| Library | Library Learning Commons | The live menu word; short enough for a 7-item bar. The hub shows the full title |
| French Immersion Program | About Us | A scent link to the page's first sentence (task 20) |
| Post-Secondary Info | Career Centre Information | A deep link to that page's own heading (task 16) |
| 604-668-6600 (Ext. 1) | (`tel:` link) | The live "Student Absent?" block's own text |

- "Grad 2026" becomes "Grad 2027", the page's own title. "Career Education & Volunteer Hours" becomes "Career
  Education", the page's own title; Volunteer Hours has its own link.
- Column headings, all from live pages:
  - Welcome to McRoberts (Grade 7 Program Planning)
  - Resources for Parents (Strikers Athletics)
  - Important information for parents (the concussion handout line on Strikers Athletics)
  - Academic Support, Career Exploration (Counselling Centre)
  - Required for Graduation (Provincial Graduation Assessments)
  - Get in Touch (Career Centre)

**Cross-listing.** A page appears in a second panel only when a second audience needs it:
- Grade 7 Program Planning, Catchment and French Immersion Program (Parents and About Us or Students);
- Personal Learning Time (PLT) and Snow and Extreme Weather Protocols (School Calendar and Students or Parents);
- Athletics Info for Parents and District Concussion Protocol (Parents and Extra-Curricular);
- Donations (Parents and About Us).

Each page keeps one URL, which also sets its breadcrumb.

**Deliberately not done**
- No invented buckets such as "School Life", "Services" or "Learning". No live page uses them as a section, and the
  topic tree's "Learning" and "Services" scored worst on first click.
- No page split or rewritten. The Career Centre page stays one page, and the deep link does the wayfinding.
- No dedicated French Immersion page: that would be new content, which is the school's call.

## 4. URLs and redirects

Principles:
- A page's URL sits under its first home in the menu, so Drupal's path-based breadcrumb matches the menu for almost every page. The few that sit outside their section's path (Contact Us under About Us, School Learning Story under News, the calendar events under School Calendar) get their trail from the menu: the theme's companion module adds a small menu-based BreadcrumbBuilder (the menu_breadcrumb approach), which is what the static preview shows (research/drupal-mapping.md).
- `-0`, `/node/`, `/media/`, year-stamped and `/information/` URLs go.
- Long but correct URLs stay as they are, which limits churn (for example the Program Planning pages and VTRA).
- With the contrib Redirect module (the standard companion of Pathauto), every old alias returns a 301. Without it,
  the old alias can be kept as a second alias of the same node: Pathauto's "leave the existing alias functioning"
  setting, or an extra entry under URL aliases. Either way, no link breaks.

| Live URL | New URL | Page |
|---|---|---|
| `/students-0` | `/students` | Students |
| `/students/grad-2026` | `/students/grad` | Grad 2027 |
| `/students/career-education-volunteer-hours` | `/students/career-education` | Career Education |
| `/students/career-education-volunteer-hours/career-education-8-9` | `/students/career-education/career-education-8-9` | Career Education 8 & 9 |
| `/students/career-education-volunteer-hours/capstonecareer-life-connections-clc` | `/students/career-education/capstone-career-life-connections-clc` | Capstone/Career-Life Connections (CLC) |
| `/students/career-education-volunteer-hours/career-education-volunteer-hour-requirements` | `/students/career-education/career-education-volunteer-hours` | Career Education Volunteer Hours |
| `/students/updating-student-contact-information` | `/parents/updating-student-contact-information` | Updating Student Contact Information (a form for families) |
| `/information/about-us` | `/about-us` | About Us |
| `/information/about-us/mission-statement` | `/about-us/mission-statement` | Mission Statement |
| `/information/our-staff` | `/about-us/our-staff` | Our Staff |
| `/information/catchment` | `/about-us/catchment` | McRoberts Catchment |
| `/information/contact-us` | `/contact-us` | Contact Us (short and guessable; linked from every page) |
| `/information/bell-schedule` | `/school-calendar/bell-schedule` | Timetable Structure 2026-2027 |
| `/information/personal-learning-time-plt` | `/school-calendar/personal-learning-time-plt` | Personal Learning Time (PLT) |
| `/information/snow-and-extreme-weather-protocols` | `/school-calendar/snow-and-extreme-weather-protocols` | Snow and Extreme Weather Protocols |
| `/information/donations` | `/parents/donations` | Donations |
| `/information/district-concussion-protocol` | `/parents/district-concussion-protocol` | District Concussion Protocol |
| `/media/1069` | `/parents/district-concussion-protocol/concussion-awareness-response-and-management` | The concussion PDF page |
| `/parents/parent-advisory-committee-pac` | `/parents/pac` | Parent Advisory Committee (PAC) |
| `/parents/parent-advisory-committee-pac/pac-meeting-agendas` | `/parents/pac/meeting-agendas` | PAC Meeting Agendas |
| `/parents/parent-advisory-committee-pac/pac-meeting-minutes` | `/parents/pac/meeting-minutes` | PAC Meeting Minutes |
| `/node/1813` | `/library/biblio-bites` | Biblio Bites: A Monthly Library Newsletter |
| `/library/q` | `/library/q-and-a` | Q & A |
| `/our-school-story/news/<5 posts>` | `/school-learning-story/news/<same slug>` | SEL Survey January 2024, Developing Community Through Awards, McRoberts Mural, Grade 8 - Student Mentor Connections, McRoberts Teacher Book Club |

**Retired pages** (taken out of every menu; their URL redirects):

| Page | Redirects to | Why |
|---|---|---|
| `/information` (Information) | `/about-us` | An orphan copy that lists the whole top menu |
| `/information-0` (Information) | `/about-us` | Its 9 pages are now filed by task; About Us is the closest single home |
| `/news/2026/08/back-school-schedules-and-calendars-0` | the original post | Same body, published twice the same week |
| `/library/research-inquiry` (Research & Inquiry) | `/library` | The live page is empty (0 words) |
| `/parents/parent-advisory-committee-pac/pac-constitution-and-bylaws` | `/parents/pac` | The live page is empty (0 words) |

The two empty pages stay in Drupal as unpublished nodes. As soon as they have content, the school can publish them
and add the menu link back. Nothing is lost.

## 5. Drupal build notes

- **Menus:** three core menus. `main` holds the 7 panels; `utility` and `footer` are new. A fourth core menu, "hub
  links", holds the sections of the five small hubs.
- **Main menu levels:** level 1 = top item, level 2 = column, level 3 = link.
  - A column with a heading is a level-2 item: `route:<nolink>`, or a link when the heading links (PAC).
  - A column without a heading is a level-2 `route:<nolink>` item whose title the template does not print. That
    title is an admin-only name, not visible copy.
  - The first column of each panel is the "most requested" column, so no contrib attribute module is needed.
- **Disclosure pattern:** each top label stays a link, and the `menu--main.html.twig` disclosure button opens its
  panel (APG "disclosure navigation with top-level links"). The phone accordion renders the same tree.
- **Hubs:** core's menu block renders the main-menu subtree on the six section hubs and the "hub links" subtree on
  the small ones, both through one card template. Hub and menu therefore cannot drift apart.
- **Paths:** path aliases, plus Pathauto patterns for new nodes in each section.
- **Heading ids:** a small theme preprocess gives each body `h2`/`h3` an `id` from its own text, so fragment links such
  as `#post-secondary-info` resolve. The body stays untouched.
- **Static build:** `tools/check_fidelity.py` expects a built page for every live page key. It needs to skip the keys
  in `retired`, and the build should write a redirect stub at each retired path.
