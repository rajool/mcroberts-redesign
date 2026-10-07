<?php

namespace Drupal\mcroberts;

use Drupal\Core\Menu\MenuTreeParameters;

/**
 * Site structure for the McRoberts theme.
 *
 * Ports of the static build's menu-tree helpers (build.py): the information architecture of design/ia.json lives in
 * Drupal as menu configuration (menus main, utility, footer and hub-links, see config-changes/), and these helpers
 * read it to place the page in its section (eyebrow, breadcrumb hub, section menu, previous/next, hub cards).
 *
 * Everything is plain arrays of strings, so the templates stay simple. Paths are path aliases without the base path
 * ("/parents/student-attendance"), the same keys design/ia.json uses.
 */
final class Site {

  /**
   * An in-site page the main menu reaches only through its external target: on that page the item is its trail.
   */
  public const STANDS_FOR = [
    '/library/library-catalogue' => 'https://search.follettsoftware.com/metasearch/ui/21989',
  ];

  /**
   * Pages a short mega panel shows as image tiles (build.py MEGA_TILES).
   */
  public const MEGA_TILES = [
    '/extra-curricular' => ['/extra-curricular/strikers-athletics', '/extra-curricular/club-directory'],
    '/library' => ['/library/read-listen', '/library/make-play'],
  ];

  /**
   * Hubs whose cards are photo tiles (build.py: the Library hub).
   */
  public const PHOTO_HUBS = ['/library'];

  /**
   * Per-request memo.
   *
   * @var array
   */
  private static array $memo = [];

  /**
   * A theme setting of mcroberts (with Bootstrap Barrio's defaults behind it).
   */
  public static function setting(string $key, $default = NULL) {
    $value = theme_get_setting($key, 'mcroberts');
    return $value ?? $default;
  }

  /**
   * A path from the mcroberts_paths setting.
   */
  public static function pathOf(string $key): string {
    $paths = (array) self::setting('mcroberts_paths', []);
    return $paths[$key] ?? '/';
  }

  /**
   * The base path of the site without a trailing slash ('' at the web root).
   */
  public static function base(): string {
    return rtrim(\Drupal::request()->getBasePath(), '/');
  }

  /**
   * A path alias → the URL to print (base path prefixed).
   */
  public static function url(string $path): string {
    if (preg_match('~^[a-z][a-z0-9+.\-]*:~i', $path) || str_starts_with($path, '//')) {
      return $path;
    }
    return self::base() . ($path === '' ? '/' : $path);
  }

  /**
   * The URL of a file inside this theme.
   */
  public static function themeFile(string $relative): string {
    return self::base() . '/' . \Drupal::service('extension.list.theme')->getPath('mcroberts') . '/' . ltrim($relative, '/');
  }

  /**
   * "/a/b/?q#f" → "/a/b"; "" → "/".
   */
  public static function norm(?string $path): string {
    $path = (string) $path;
    $path = explode('#', $path, 2)[0];
    $path = explode('?', $path, 2)[0];
    $path = trim($path, '/');
    return $path === '' ? '/' : '/' . $path;
  }

  /**
   * The parent of a path ("/a/b" → "/a", "/a" → "/").
   */
  public static function parent(string $path): string {
    $parts = explode('/', trim($path, '/'));
    array_pop($parts);
    return $parts ? '/' . implode('/', $parts) : '/';
  }

  /**
   * The path alias of the current page ("/" on the front page).
   */
  public static function current(): string {
    if (!isset(self::$memo['current'])) {
      if (\Drupal::service('path.matcher')->isFrontPage()) {
        self::$memo['current'] = '/';
      }
      else {
        $system = \Drupal::service('path.current')->getPath();
        self::$memo['current'] = self::norm(\Drupal::service('path_alias.manager')->getAliasByPath($system));
      }
    }
    return self::$memo['current'];
  }

  /**
   * Whitespace collapsed, non-breaking spaces and byte-order marks (U+FEFF, in the live event titles) removed.
   */
  public static function clean(?string $text): string {
    $text = str_replace(["\u{FEFF}", "\u{00A0}"], ['', ' '], (string) $text);
    return trim(preg_replace('/\s+/u', ' ', $text));
  }

  /**
   * build.py slug(): lower case, runs of other characters → "-".
   */
  public static function slug(string $text): string {
    return trim(preg_replace('/[^a-z0-9]+/', '-', mb_strtolower(self::clean($text))), '-');
  }

  /**
   * The entity a path alias stands for (node or media), or NULL.
   */
  public static function entityAt(string $path) {
    $path = self::norm($path);
    if (array_key_exists($path, self::$memo['entity'] ?? [])) {
      return self::$memo['entity'][$path];
    }
    $entity = NULL;
    $system = $path === '/' ? '' : \Drupal::service('path_alias.manager')->getPathByAlias($path);
    if (preg_match('~^/(node|media)/(\d+)$~', $system, $m)) {
      try {
        $entity = \Drupal::entityTypeManager()->getStorage($m[1])->load($m[2]);
      }
      catch (\Exception $e) {
        $entity = NULL;
      }
    }
    self::$memo['entity'][$path] = $entity;
    return $entity;
  }

  /**
   * build.py page_title(): the page's own title (its label), or "" when the path is not a page.
   */
  public static function title(string $path): string {
    $entity = self::entityAt($path);
    return $entity ? self::clean($entity->label()) : '';
  }

  /**
   * The raw body HTML of the node at a path ("" when none).
   */
  public static function body(string $path): string {
    $entity = self::entityAt($path);
    if ($entity && $entity->getEntityTypeId() === 'node' && $entity->hasField('body') && !$entity->get('body')->isEmpty()) {
      return (string) $entity->get('body')->value;
    }
    return '';
  }

  // ------------------------------------------------------------------------------------------------- menus

  /**
   * A menu as plain nested arrays: title, url, path (internal), http (http/https link), external, nolink, children.
   */
  public static function tree(string $menu): array {
    if (isset(self::$memo['tree'][$menu])) {
      return self::$memo['tree'][$menu];
    }
    $service = \Drupal::menuTree();
    $parameters = new MenuTreeParameters();
    $parameters->onlyEnabledLinks();
    $tree = $service->load($menu, $parameters);
    $tree = $service->transform($tree, [
      ['callable' => 'menu.default_tree_manipulators:checkAccess'],
      ['callable' => 'menu.default_tree_manipulators:generateIndexAndSort'],
    ]);
    return self::$memo['tree'][$menu] = self::plain($tree);
  }

  /**
   * Menu link tree elements → plain arrays.
   */
  private static function plain(array $tree): array {
    $out = [];
    foreach ($tree as $element) {
      if (isset($element->access) && !$element->access->isAllowed()) {
        continue;
      }
      $link = $element->link;
      $url = $link->getUrlObject();
      $item = [
        'title' => self::clean((string) $link->getTitle()),
        'url' => '',
        'path' => NULL,
        'fragment' => '',
        'external' => FALSE,
        'http' => FALSE,
        'nolink' => FALSE,
        'children' => $element->subtree ? self::plain($element->subtree) : [],
      ];
      if ($url->isRouted() && in_array($url->getRouteName(), ['<nolink>', '<none>', '<button>'], TRUE)) {
        $item['nolink'] = TRUE;
      }
      else {
        try {
          $item['url'] = $url->toString();
        }
        catch (\Exception $e) {
          continue;
        }
        if ($url->isExternal()) {
          $item['external'] = TRUE;
          $item['http'] = (bool) preg_match('~^https?:~i', $item['url']);
        }
        else {
          $base = self::base();
          $local = ($base !== '' && str_starts_with($item['url'], $base)) ? substr($item['url'], strlen($base)) : $item['url'];
          $item['path'] = self::norm($local);
          $item['fragment'] = (string) ($url->getOption('fragment') ?? '');
        }
      }
      $out[] = $item;
    }
    return $out;
  }

  /**
   * A menu item → a link node {label, url, path, fragment, http, external} (NULL for a <nolink> item).
   */
  public static function node(array $item): ?array {
    if ($item['nolink']) {
      return NULL;
    }
    return [
      'label' => $item['title'],
      'url' => $item['url'],
      'path' => $item['path'],
      'fragment' => $item['fragment'],
      'http' => $item['http'],
      'external' => $item['external'],
    ];
  }

  /**
   * A column title in square brackets is an admin-only name: the column has no visible heading.
   */
  private static function isPlain(string $title): bool {
    return (bool) preg_match('/^\[.*\]$/u', trim($title));
  }

  /**
   * Menu main as design/ia.json "primary": [{label, url, path, groups: [{label|NULL, href: node|NULL, children}]}].
   */
  public static function primary(): array {
    if (isset(self::$memo['primary'])) {
      return self::$memo['primary'];
    }
    $tops = [];
    foreach (self::tree('main') as $top) {
      if ($top['nolink'] || $top['path'] === NULL) {
        continue;
      }
      $groups = [];
      foreach ($top['children'] as $g) {
        $plain = self::isPlain($g['title']);
        $children = [];
        foreach ($g['children'] as $c) {
          if ($n = self::node($c)) {
            $children[] = $n;
          }
        }
        if (!$g['children'] && !$g['nolink']) {
          // a link placed straight under a top item: a one-link column without a heading
          $children[] = self::node($g);
          $groups[] = ['label' => NULL, 'href' => NULL, 'children' => $children];
          continue;
        }
        $groups[] = [
          'label' => $plain ? NULL : $g['title'],
          'href' => ($plain || $g['nolink']) ? NULL : self::node($g),
          'children' => $children,
        ];
      }
      if (!$groups) {
        $groups[] = ['label' => NULL, 'href' => NULL, 'children' => []];
      }
      $tops[] = [
        'label' => $top['title'],
        'url' => $top['url'],
        'path' => $top['path'],
        'mid' => 'mega-' . self::slug($top['title']),
        'groups' => $groups,
      ];
    }
    return self::$memo['primary'] = $tops;
  }

  /**
   * The top item whose hub is this path.
   */
  public static function top(string $path): ?array {
    foreach (self::primary() as $m) {
      if ($m['path'] === $path) {
        return $m;
      }
    }
    return NULL;
  }

  /**
   * The nodes of a group: its own link (when the heading links) and its children.
   */
  private static function groupNodes(array $g): array {
    return array_merge($g['href'] ? [$g['href']] : [], $g['children']);
  }

  /**
   * build.py FIRST_HOME: page path → index of the top item that lists it first.
   */
  private static function firstHome(): array {
    if (!isset(self::$memo['first_home'])) {
      $home = [];
      foreach (self::primary() as $i => $m) {
        foreach ($m['groups'] as $g) {
          foreach (self::groupNodes($g) as $n) {
            if ($n['path'] !== NULL && !isset($home[$n['path']])) {
              $home[$n['path']] = $i;
            }
          }
        }
      }
      foreach (self::primary() as $i => $m) {
        $home[$m['path']] = $i;
      }
      self::$memo['first_home'] = $home;
    }
    return self::$memo['first_home'];
  }

  /**
   * build.py MENU_LABEL: link key ("/path", "/path#frag" or the external URL) → its first menu label.
   */
  public static function menuLabel(string $key): ?string {
    if (!isset(self::$memo['menu_label'])) {
      $labels = [];
      foreach (self::primary() as $m) {
        foreach ($m['groups'] as $g) {
          foreach (self::groupNodes($g) as $n) {
            $labels += [self::key($n) => $n['label']];
          }
        }
      }
      foreach (self::primary() as $m) {
        $labels += [$m['path'] => $m['label']];
      }
      self::$memo['menu_label'] = $labels;
    }
    return self::$memo['menu_label'][$key] ?? NULL;
  }

  /**
   * The key of a link node: its path (with #fragment) or its external URL.
   */
  public static function key(array $n): string {
    if ($n['path'] === NULL) {
      return $n['url'];
    }
    return $n['path'] . ($n['fragment'] !== '' ? '#' . $n['fragment'] : '');
  }

  /**
   * build.py panel_label(): the label a link has inside one top item's panel.
   */
  public static function panelLabel(?array $top, string $key): ?string {
    foreach ($top['groups'] ?? [] as $g) {
      foreach (self::groupNodes($g) as $n) {
        if (self::key($n) === $key) {
          return $n['label'];
        }
      }
    }
    return NULL;
  }

  /**
   * build.py section_of(): the top item a page belongs to (its URL prefix, else the item that lists it first).
   * Calendar events belong to School Calendar.
   */
  public static function sectionOf(string $path, ?string $bundle = NULL): ?array {
    $tops = self::primary();
    if ($bundle === 'calendar_event') {
      return self::top(self::pathOf('calendar'));
    }
    foreach ($tops as $m) {
      if ($path === $m['path'] || ($m['path'] !== '/' && str_starts_with($path, rtrim($m['path'], '/') . '/'))) {
        return $m;
      }
    }
    $home = self::firstHome();
    $p = $path;
    while ($p !== '' && $p !== '/') {
      if (isset($home[$p])) {
        return $tops[$home[$p]];
      }
      $p = self::parent($p);
    }
    return NULL;
  }

  /**
   * build.py menu_trail(): the menu link that stands for $path in a section (the page, else its listed ancestor).
   */
  public static function trail(?array $sec, string $path): ?string {
    if (!$sec) {
      return NULL;
    }
    $listed = [];
    foreach ($sec['groups'] as $g) {
      foreach ($g['children'] as $c) {
        if ($c['path'] !== NULL) {
          $listed[$c['path']] = TRUE;
        }
      }
      if ($g['href'] && $g['href']['path'] !== NULL) {
        $listed[$g['href']['path']] = TRUE;
      }
    }
    $p = $path;
    while ($p !== '' && $p !== '/') {
      if (isset($listed[$p])) {
        return $p;
      }
      $p = self::parent($p);
    }
    return NULL;
  }

  /**
   * A link node decorated for the current page: current (aria-current), trail (is-active-trail).
   */
  public static function decorate(array $n, ?string $trail, string $cur): array {
    $here = $n['path'] !== NULL && $n['fragment'] === '' && $n['path'] === $cur;
    $stands = (self::STANDS_FOR[$cur] ?? NULL) === $n['url'];
    $n['current'] = $here;
    $n['trail'] = !$here && (($trail !== NULL && $n['path'] === $trail && $n['fragment'] === '') || $stands);
    // the label split so the arrow stays on the line of its last word (section menu headings)
    $label = trim($n['label']);
    $cut = mb_strrpos($label, ' ');
    $n['head'] = $cut === FALSE ? '' : mb_substr($label, 0, $cut);
    $n['last'] = $cut === FALSE ? $label : mb_substr($label, $cut + 1);
    return $n;
  }

  /**
   * Menu main decorated for the current page, for the mega menu, the phone drawer and the section menu.
   */
  public static function primaryFor(string $cur, ?string $bundle = NULL): array {
    $sec = self::sectionOf($cur, $bundle);
    $out = [];
    foreach (self::primary() as $m) {
      $is_sec = $sec && $sec['path'] === $m['path'];
      $trail = $is_sec ? self::trail($m, $cur) : NULL;
      $groups = [];
      foreach ($m['groups'] as $g) {
        $g['children'] = array_map(fn($c) => self::decorate($c, $trail, $cur), $g['children']);
        $g['href'] = $g['href'] ? self::decorate($g['href'], $trail, $cur) : NULL;
        $groups[] = $g;
      }
      $m['groups'] = $groups;
      $m['current'] = $m['path'] === $cur;
      $m['section'] = $is_sec;
      $m['trail'] = $is_sec && !$m['current'];
      $m['trail_path'] = $trail;
      $out[] = $m;
    }
    return $out;
  }

  /**
   * build.py section_order(): the section's own pages in menu order (the previous/next sequence).
   */
  public static function sectionOrder(array $sec): array {
    $out = [];
    foreach ($sec['groups'] as $g) {
      foreach (self::groupNodes($g) as $n) {
        $h = $n['path'];
        if ($h === NULL || $n['fragment'] !== '' || $h === $sec['path'] || in_array($h, $out, TRUE)) {
          continue;
        }
        $home = self::sectionOf($h);
        if ($home && $home['path'] === $sec['path'] && self::entityAt($h)) {
          $out[] = $h;
        }
      }
    }
    return $out;
  }

  /**
   * build.py section_pager(): previous / next through the section in menu order.
   */
  public static function pager(string $cur, ?string $bundle = NULL): ?array {
    $sec = self::sectionOf($cur, $bundle);
    if (!$sec || $cur === $sec['path']) {
      return NULL;
    }
    $order = self::sectionOrder($sec);
    $i = array_search($cur, $order, TRUE);
    if ($i === FALSE) {
      return NULL;
    }
    $prev = $i > 0 ? $order[$i - 1] : $sec['path'];
    $next = $order[$i + 1] ?? NULL;
    $card = function (?string $target) use ($sec) {
      if ($target === NULL) {
        return NULL;
      }
      $top = self::top($target);
      $label = $top ? $top['label'] : (self::panelLabel($sec, $target) ?? self::title($target));
      return ['url' => self::url($target), 'label' => $label];
    };
    return ['label' => $sec['label'], 'prev' => $card($prev), 'next' => $card($next)];
  }

  /**
   * The breadcrumb crumb the menu adds (build.py breadcrumbs()): a page whose URL is not under its section hub
   * gets the hub after Home. Returns [text, url] or NULL.
   */
  public static function hubCrumb(string $cur, ?string $bundle, array $urls): ?array {
    $sec = self::sectionOf($cur, $bundle);
    if (!$sec || $sec['path'] === $cur) {
      return NULL;
    }
    $hub_url = self::url($sec['path']);
    if (in_array($hub_url, $urls, TRUE)) {
      return NULL;
    }
    return [self::title($sec['path']) ?: $sec['label'], $hub_url];
  }

  // ------------------------------------------------------------------------------------------------- hubs

  /**
   * The grouped cards of a hub page: menu hub-links (an entry for this page) or the page's own main-menu panel.
   * [{heading|NULL, href: node|NULL, links: [nodes]}].
   */
  public static function hubSpec(string $path): ?array {
    foreach (self::tree('hub-links') as $hub) {
      if ($hub['path'] === $path || ($path === '/' && $hub['path'] === '/')) {
        $sections = [];
        foreach ($hub['children'] as $s) {
          $links = [];
          foreach ($s['children'] as $c) {
            if ($n = self::node($c)) {
              $links[] = $n;
            }
          }
          $plain = self::isPlain($s['title']);
          $sections[] = [
            'heading' => $plain ? NULL : $s['title'],
            'href' => ($plain || $s['nolink']) ? NULL : self::node($s),
            'links' => $links,
          ];
        }
        return $sections;
      }
    }
    $top = self::top($path);
    if ($top) {
      return array_map(fn($g) => ['heading' => $g['label'], 'href' => $g['href'], 'links' => $g['children']], $top['groups']);
    }
    return NULL;
  }

  /**
   * build.py hub_sections(): the hub's sections as card lists. Self-links and links the body already shows as
   * tiles ($skip: paths or URLs) are dropped.
   */
  public static function hubSections(string $cur, array $skip = []): array {
    $spec = self::hubSpec($cur);
    if (!$spec) {
      return [];
    }
    $is_top = (bool) self::top($cur);
    $photo = in_array($cur, self::PHOTO_HUBS, TRUE);
    $tiles = Teaser::tileImages();
    $out = [];
    $n = 1;
    foreach ($spec as $gi => $sec) {
      $links = [];
      foreach ($sec['links'] as $l) {
        $self = $l['path'] !== NULL && $l['fragment'] === '' && $l['path'] === $cur;
        $shown = ($l['path'] !== NULL && $l['fragment'] === '' && in_array($l['path'], $skip, TRUE)) || in_array($l['url'], $skip, TRUE);
        if (!$self && !$shown) {
          $links[] = $l;
        }
      }
      if (!$links) {
        continue;
      }
      $heading = $sec['heading'];
      $tag = $heading ? 'h3' : 'h2';
      $cards = [];
      foreach ($links as $l) {
        if ($photo) {
          $tile = $l['path'] !== NULL ? ($tiles[$l['path']] ?? NULL) : NULL;
          $cards[] = [
            'url' => $l['url'],
            'label' => $l['label'],
            'external' => $l['http'],
            'img' => isset($tile['file']) ? ['src' => self::themeFile($tile['file']), 'w' => $tile['w'], 'h' => $tile['h']] : NULL,
            'icon' => !isset($tile['file']) || !empty($tile['icon_art']),
            'ico' => $tile['icon'] ?? 'paper',
          ];
        }
        else {
          $cards[] = Teaser::card($l, $l['label']);
        }
      }
      $out[] = [
        'heading' => $heading,
        'href' => $sec['href'],
        'id' => $heading ? 'hub-' . self::slug($heading) : '',
        'tag' => $tag,
        'featured' => $is_top && $gi === 0,
        'photo' => $photo,
        'cards' => $cards,
        'bare' => !$photo && !array_filter(array_column($cards, 'desc')),
        'start' => $n,
      ];
      $n += count($links);
    }
    return $out;
  }

  // ------------------------------------------------------------------------------------------------- mega menu

  /**
   * The mega panels of menu main for the current page (build.py mega_panel() and mega_feature()): the
   * most-requested column, one column per group (a page shown as a tile leaves its column), and the panel's live
   * feature: School Calendar the next events, News the latest Striker Weekly, About Us the address, Extra-Curricular
   * and Library two of their pages as image tiles.
   */
  public static function megaPanels(array $tops): array {
    $tiles_data = Teaser::tileImages();
    $out = [];
    foreach ($tops as $m) {
      $feat = $m['groups'][0];
      $rest = array_slice($m['groups'], 1);
      $tile_paths = array_values(array_filter(self::MEGA_TILES[$m['path']] ?? [], fn($p) => isset($tiles_data[$p]['file'])));
      $page_of = fn($c) => ($c['path'] !== NULL && $c['fragment'] === '') ? $c['path'] : NULL;
      $lone_desc = count($feat['children']) === 1 ? Teaser::cardDesc($feat['children'][0]) : '';
      $cols = [];
      foreach ($rest as $i => $g) {
        $kids = array_values(array_filter($g['children'], fn($c) => !in_array($page_of($c), $tile_paths, TRUE)));
        if (!$kids) {
          continue;
        }
        $cols[] = ['label' => $g['label'], 'href' => $g['href'], 'gid' => $m['mid'] . '-g' . ($i + 1), 'links' => $kids];
      }
      $feature = NULL;
      if ($m['path'] === self::pathOf('calendar')) {
        $feature = [
          'kind' => 'events',
          'built' => Calendar::today(),
          'events' => array_map([Calendar::class, 'eventItem'], array_slice(Calendar::realEvents(Calendar::today()), 0, 3)),
        ];
      }
      elseif ($tile_paths) {
        $quiet = array_values(array_intersect(array_filter(array_map($page_of, $feat['children'])), $tile_paths));
        $tiles = [];
        foreach ($tile_paths as $p) {
          $t = $tiles_data[$p];
          $tiles[] = [
            'url' => self::url($p),
            'label' => self::menuLabel($p) ?? self::title($p),
            'src' => self::themeFile($t['file']),
            'w' => $t['w'],
            'h' => $t['h'],
            'cls' => !empty($t['logo']) ? ' is-logo' : (!empty($t['icon_art']) ? ' is-icon' : ''),
            'quiet' => in_array($p, $quiet, TRUE),
          ];
        }
        $feature = ['kind' => 'tiles', 'tiles' => $tiles, 'all_quiet' => count($quiet) === count($tiles)];
      }
      elseif ($m['path'] === self::pathOf('news')) {
        $weekly = Teaser::weeklies(1)[0] ?? NULL;
        $feature = $weekly ? ['kind' => 'weekly', 'url' => $weekly['url'], 'range' => $weekly['range']] : NULL;
      }
      elseif ($m['path'] === self::pathOf('about')) {
        $feature = ['kind' => 'contact', 'contact' => self::contact()];
      }
      $out[] = $m + [
        'featured' => $feat['children'],
        'lone_desc' => $lone_desc,
        'cols' => $cols,
        'feature' => $feature,
        'n_cols' => max(count($cols) + ($feature ? 2 : 0), 1),
      ];
    }
    return $out;
  }

  // ------------------------------------------------------------------------------------------------- chrome data

  /**
   * Menu utility: Student Absent? and its number (the first two links), then the sign-ins and Contact Us.
   */
  public static function utility(): array {
    if (isset(self::$memo['utility'])) {
      return self::$memo['utility'];
    }
    $items = array_values(array_filter(array_map([self::class, 'node'], self::tree('utility'))));
    $fallback = (array) self::setting('mcroberts_absent', []);
    $absent = $items[0] ?? NULL;
    $number = $items[1] ?? NULL;
    if (!$absent || $absent['path'] === NULL || !$number || !str_starts_with($number['url'], 'tel:')) {
      // menu utility not created yet: the same pair from the theme settings
      $absent = [
        'label' => $fallback['label'] ?? 'Student Absent?',
        'url' => self::url($fallback['path'] ?? self::pathOf('attendance')),
        'path' => $fallback['path'] ?? self::pathOf('attendance'),
        'fragment' => '',
        'http' => FALSE,
        'external' => FALSE,
      ];
      $number = [
        'label' => $fallback['number_label'] ?? '',
        'url' => $fallback['number_uri'] ?? '',
        'path' => NULL,
        'fragment' => '',
        'http' => FALSE,
        'external' => TRUE,
      ];
      $rest = $items;
    }
    else {
      $rest = array_slice($items, 2);
    }
    return self::$memo['utility'] = ['absent' => $absent, 'number' => $number, 'links' => $rest];
  }

  /**
   * Menu footer as columns of typed lines (build.py footer()): link, absent pill, mail, address.
   */
  public static function footerColumns(): array {
    $regions = ['region-footer-fourth', 'region-footer-first', 'region-footer-third'];
    $contact = self::contact();
    $absent_path = self::utility()['absent']['path'];
    $cols = [];
    foreach (self::tree('footer') as $i => $col) {
      $kids = array_values(array_filter(array_map([self::class, 'node'], $col['children'])));
      $items = [];
      for ($j = 0; $j < count($kids); $j++) {
        $n = $kids[$j];
        if ($n['path'] !== NULL && $n['path'] === $absent_path && isset($kids[$j + 1]) && str_starts_with($kids[$j + 1]['url'], 'tel:')) {
          $items[] = ['kind' => 'absent'];
          $j++;
          continue;
        }
        if (str_starts_with($n['url'], 'mailto:')) {
          $items[] = ['kind' => 'mail', 'url' => $n['url'], 'label' => $n['label']];
        }
        elseif (str_contains($n['url'], 'maps.')) {
          $items[] = ['kind' => 'address', 'url' => $contact['map_url'] ?: $n['url'], 'label' => $n['label']];
        }
        else {
          $items[] = ['kind' => 'link', 'url' => $n['url'], 'label' => $n['label'], 'http' => $n['http']];
        }
      }
      $cols[] = [
        'label' => $col['title'],
        'id' => 'foot-' . self::slug($col['title']),
        'region' => $regions[$i] ?? '',
        'items' => $items,
        'contact' => $i === 0,
      ];
    }
    return $cols;
  }

  /**
   * School contact: the block_content address_block when it exists, else the theme settings.
   */
  public static function contact(): array {
    if (isset(self::$memo['contact'])) {
      return self::$memo['contact'];
    }
    $c = (array) self::setting('mcroberts_contact', []) + [
      'address_line1' => '', 'locality' => '', 'administrative_area' => '', 'postal_code' => '', 'map_url' => '',
      'phone' => '', 'email' => '',
    ];
    try {
      $storage = \Drupal::entityTypeManager()->getStorage('block_content');
      $ids = $storage->getQuery()->accessCheck(FALSE)->condition('type', 'address_block')->range(0, 1)->execute();
      $block = $ids ? $storage->load(reset($ids)) : NULL;
      if ($block) {
        if ($block->hasField('field_address') && !$block->get('field_address')->isEmpty()) {
          $a = $block->get('field_address')->first()->getValue();
          foreach (['address_line1', 'locality', 'administrative_area', 'postal_code'] as $k) {
            if (!empty($a[$k])) {
              $c[$k] = $a[$k];
            }
          }
        }
        if ($block->hasField('field_phone') && !$block->get('field_phone')->isEmpty()) {
          $c['phone'] = self::clean($block->get('field_phone')->value);
        }
        if ($block->hasField('field_school_email_address') && !$block->get('field_school_email_address')->isEmpty()) {
          $c['email'] = self::clean($block->get('field_school_email_address')->value);
        }
      }
    }
    catch (\Exception $e) {
      // block_content not installed: the settings stand
    }
    $digits = preg_replace('/\D/', '', $c['phone']);
    $c['tel'] = 'tel:+1' . $digits;
    $c['tel_ext'] = $c['tel'] . ',1';
    $c['phone_dots'] = str_replace('-', '.', $c['phone']);
    $c['line2'] = trim($c['locality'] . ', ' . $c['administrative_area'], ', ');
    return self::$memo['contact'] = $c;
  }

  /**
   * The GTranslate languages, in the order of the block configuration, with their native names.
   */
  public static function languages(): array {
    $names = [
      'en' => 'English', 'zh-CN' => '简体中文', 'zh-TW' => '繁體中文', 'fr' => 'Français', 'de' => 'Deutsch',
      'it' => 'Italiano', 'ja' => '日本語', 'ru' => 'Русский', 'es' => 'Español', 'ko' => '한국어', 'pa' => 'ਪੰਜਾਬੀ',
      'hi' => 'हिन्दी', 'tl' => 'Tagalog', 'vi' => 'Tiếng Việt', 'fa' => 'فارسی', 'ar' => 'العربية',
    ];
    $tags = ['zh-CN' => 'zh-Hans', 'zh-TW' => 'zh-Hant'];
    $codes = [];
    $config = \Drupal::config('gtranslate.settings')->get('languages');
    if (is_array($config)) {
      foreach ($config as $k => $v) {
        $code = is_string($k) ? ($v ? $k : NULL) : (is_string($v) ? $v : NULL);
        if ($code) {
          $codes[] = $code;
        }
      }
    }
    if (!$codes) {
      $codes = (array) self::setting('mcroberts_languages', ['en']);
    }
    if (!in_array('en', $codes, TRUE)) {
      array_unshift($codes, 'en');
    }
    return array_map(fn($code) => [
      'value' => 'en|' . $code,
      'lang' => $tags[$code] ?? $code,
      'label' => $names[$code] ?? $code,
      'selected' => $code === 'en',
    ], $codes);
  }

  /**
   * The data every page's chrome needs (header, drawer, phone bar, footer, rail).
   */
  public static function chrome(): array {
    if (isset(self::$memo['chrome'])) {
      return self::$memo['chrome'];
    }
    $site = \Drupal::config('system.site');
    $name = self::clean($site->get('name'));
    // the lockup: "École Secondaire" / "Hugh McRoberts" / "Secondary School"
    $pre = $main = $post = '';
    if (preg_match('/^(École Secondaire)\s+(.+?)\s+(Secondary School)$/u', $name, $m)) {
      [, $pre, $main, $post] = $m;
    }
    $slogan = self::clean($site->get('slogan'));
    $cur = self::current();
    $util = self::utility();
    $absent = $util['absent'];
    $district = (array) self::setting('mcroberts_district', []);
    $contact = self::contact();
    $search = '/search/node';
    try {
      $search = \Drupal\Core\Url::fromRoute('search.view_node_search')->toString();
    }
    catch (\Exception $e) {
      $search = self::url('/search/node');
    }
    return self::$memo['chrome'] = [
      'home' => self::url('/'),
      'name' => $name,
      'name_pre' => $pre,
      'name_main' => $main,
      'name_post' => $post,
      'motto' => str_replace('...', '…', $slogan),
      'crest' => ['src' => self::themeFile('images/39ef9ae7e316-200.png'), 'w' => 200, 'h' => 174],
      'crest_full' => ['src' => self::themeFile('logo.png'), 'w' => 400, 'h' => 348],
      'icon32' => self::themeFile('images/39ef9ae7e316-32.png'),
      'icon180' => self::themeFile('images/39ef9ae7e316-180.png'),
      'district' => [
        'name' => $district['name'] ?? '',
        'url' => $district['url'] ?? '',
        'logo' => ['src' => self::themeFile('images/ce22c9dd5452.png'), 'w' => 329, 'h' => 86],
      ],
      'absent' => [
        'label' => $absent['label'],
        'url' => $absent['url'],
        'current' => $absent['path'] === $cur,
        'number' => $util['number']['label'],
        'tel' => $util['number']['url'],
      ],
      'signin' => $util['links'],
      'contact' => $contact,
      'languages' => self::languages(),
      'search_action' => $search,
      'year' => date('Y'),
      'paths' => [
        'bell' => self::url(self::pathOf('bell')),
        'calendar' => self::url(self::pathOf('calendar')),
        'attendance' => self::url(self::pathOf('attendance')),
        'contact' => self::url(self::pathOf('contact')),
        'news' => self::url(self::pathOf('news')),
        'newsletters' => self::url(self::pathOf('newsletters')),
        'story' => self::url(self::pathOf('story')),
      ],
      'here' => [
        'bell' => $cur === self::pathOf('bell'),
        'calendar' => $cur === self::pathOf('calendar'),
        'attendance' => $cur === self::pathOf('attendance'),
        'contact' => $cur === self::pathOf('contact'),
      ],
      'webcal' => (string) self::setting('mcroberts_webcal', ''),
      'header_img' => ['src' => self::themeFile('images/9f961d6d672b.jpg'), 'w' => 1400, 'h' => 400],
    ];
  }

}
