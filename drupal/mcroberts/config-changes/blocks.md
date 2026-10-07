# Block placements of the `mcroberts` theme

`drush theme:install mcroberts`, run while `rsd_sites_barrio` is the default theme, copies every block placement of
`rsd_sites_barrio` into `mcroberts` (core `block_theme_initialize()`): same plugin, settings, visibility and weight,
same region, because `mcroberts.info.yml` declares every live region machine name. The copies get the theme prefix
(`mcroberts_…`), so `rsd_sites_barrio` and every other SD38 school site stay untouched, and rolling back is one
setting. These are the changes to those copies. `apply.php` makes them (it finds each block by plugin and region,
not by id) and logs them for `--rollback`; by hand they are on *Structure → Block layout → McRoberts*.

| Block (live id) | Plugin | Live | Change on `mcroberts` | Why |
|---|---|---|---|---|
| `mainnavigation` | `system_menu_block:main` | primary_menu, all pages | level 1, depth unlimited, *Expand all menu links* on | the mega panels show all three levels |
| new `mcroberts_utility` | `system_menu_block:utility` | — | create in **secondary_menu**, all pages, title hidden, depth 1 | the district strip's list (Student Absent?, its number, the sign-ins, Contact Us) |
| new `mcroberts_footer` | `system_menu_block:footer` | — | create in **footer_first**, all pages, title hidden, depth 2 | the three footer columns |
| `socialmedialinks` | `social_media_links_block` | sidebar_first, `<front>` | region **footer_second**, all pages | Social Media in the footer of every page |
| `a11y` | `a11y_block` | accessibility_dropdown, printed on the front page only | remove any `<front>` condition | the Accessibility Settings dialog works on every page (186 live pages have a dead button) |
| `mainnavigation_2` | `system_menu_block:main` | footer_third, all pages | **disable** | the footer has no copy of the main menu (design/ia.md) |
| `useraccountmenu` | `system_menu_block:account` | footer_fourth, all pages | **disable** | "Log in" stays off the public pages; editors use `/user/login` |
| `ecolesecondairehughmcrobertssecondaryschooladdressblock` | `block_content:…` (address_block) | footer_fourth, all pages | **disable** | the theme reads the same block content for the footer's Get in Touch column, the rail and the front page; nothing is retyped |
| `gtranslate` | `gtranslate_block` | sidebar_second, `<front>` | **disable** | Translate is in the header, the phone bar and the phone menu of every page (the theme's control, the block's languages) |
| `searchform` | `search_form_block` | sidebar_first, `<front>` | **disable** | the search box is in the header and the phone menu of every page (same `/search/node?keys=`) |
| `views_block__sidebar_notes_block_1` | `views_block:sidebar_notes-block_1` | sidebar_first, `<front>` | **disable** | empty note |
| `views_block__sidebar_notes_block_3` | `views_block:sidebar_notes-block_3` | content, `<front>` | **disable** | empty note |

Unchanged, and how the theme prints them:

| Block | Region | Printed as |
|---|---|---|
| `views_block__site_header_content_block_block_1` | top_header | the crest lockup in the masthead |
| `views_block__sidebar_notes_block_4` | top_header_form | only when the note has text |
| `views_block__news_alerts_block_1` | featured_top | the alert band, only when the view has rows |
| messages | highlighted | status messages |
| `breadcrumbs` | breadcrumb | inside the page header of views, search and user pages (node pages build the same breadcrumb in their header) |
| `mainpagecontent` | content | the page |
| `views_block__upcoming_events_block_1` | sidebar_first, `<front>` | the front page's Upcoming Events band |
| `views_block__sidebar_notes_block_2` ("Student Absent?") | sidebar_second, `<front>` | leads Helpful Links on the front page |
| `views_block__district_quick_links_block_1` | sidebar_second, `<front>` | MyEducation BC and School Cash Online tiles |
| `views_block__home_page_buttons_block_1` | sidebar_second, `<front>` | the Office 365 tile |

Check after the copy (research/drupal-mapping.md §14): `drush config:get block.block.mcroberts_<id>` for each row
above, and that no block fell into `content` because its region was missing.

## Display Suite

Nothing changes. The live node displays render through Display Suite layouts (`ds_entity_view`, not
`node.html.twig`); the theme routes the displays of `page`, `article`, `calendar_event`, `calendar_page` and
`staff_page` to its own node templates (`mcroberts_theme_suggestions_ds_entity_view_alter()` and the
`ds-entity-view--mcroberts-node-*.html.twig` templates), with the same fields. Paragraph and media displays keep
their DS layouts; `templates/` styles what they print.
