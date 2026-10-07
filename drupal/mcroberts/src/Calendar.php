<?php

namespace Drupal\mcroberts;

use Drupal\Core\Cache\Cache;
use Drupal\Core\Render\Markup;

/**
 * School calendar, bell schedule and "today" for the McRoberts theme.
 *
 * Ports of the static build's calendar helpers (build.py): the events are the published calendar_event nodes (the
 * same nodes the fullcalendar view and the ICS feed list), the timetable is data/bell-schedule.json (the bell
 * schedule image transcribed word for word). The browser re-renders every today-dependent part from the embedded
 * JSON (js/today.js, js/calendar.js, js/bell.js), so a page served from a cache on a later day is still right.
 */
final class Calendar {

  public const TZ = 'America/Vancouver';
  public const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'June', 'July', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec'];
  public const MONTHS_LONG = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
    'October', 'November', 'December',
  ];
  public const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  public const DAYS_LONG = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  public const COLS = [0 => 'MON', 1 => 'TUE', 2 => 'WED', 3 => 'THU', 4 => 'FRI'];
  public const ROT_RE = '/^(?:COLLAB\s+)?(?:ABCD|BADC)$|^PLT Rot \d+$/i';
  public const NO_SCHOOL = ['thanksgiving', 'remembrance day', 'winter break', 'christmas', 'boxing day',
    "new year's day", 'bc family day', 'spring break', 'good friday', 'easter monday', 'victoria day', 'canada day',
    'bc day', 'national day for truth and reconciliation',
  ];
  public const LABELS = ['today' => 'Today', 'next' => 'Next', 'noschool' => 'No School'];

  /**
   * Per-request memo.
   *
   * @var array
   */
  private static array $memo = [];

  // ------------------------------------------------------------------------------------------------- dates

  /**
   * Today on the school's clock, as YYYY-MM-DD.
   */
  public static function today(): string {
    return (new \DateTimeImmutable('now', new \DateTimeZone(self::TZ)))->format('Y-m-d');
  }

  /**
   * Seconds until the next midnight in Vancouver: the max-age of every today-dependent render.
   */
  public static function secondsToMidnight(): int {
    $tz = new \DateTimeZone(self::TZ);
    $now = new \DateTimeImmutable('now', $tz);
    $midnight = $now->setTime(0, 0)->modify('+1 day');
    return max(60, $midnight->getTimestamp() - $now->getTimestamp());
  }

  private static function date(string $iso): \DateTimeImmutable {
    return \DateTimeImmutable::createFromFormat('!Y-m-d', $iso, new \DateTimeZone('UTC'));
  }

  public static function add(string $iso, int $days): string {
    return self::date($iso)->modify(($days >= 0 ? '+' : '') . $days . ' day')->format('Y-m-d');
  }

  /**
   * Monday = 0 … Sunday = 6 (Python's weekday()).
   */
  public static function weekday(string $iso): int {
    return (int) self::date($iso)->format('N') - 1;
  }

  /**
   * Every way the templates print a date.
   */
  public static function parts(string $iso): array {
    $d = self::date($iso);
    $m = (int) $d->format('n');
    $n = (int) $d->format('j');
    $w = self::weekday($iso);
    $y = (int) $d->format('Y');
    return [
      'iso' => $iso,
      'm' => self::MONTHS[$m - 1],
      'n' => $n,
      'd' => self::DAYS[$w],
      'y' => $y,
      'long' => sprintf('%s, %s %d, %d', self::DAYS_LONG[$w], self::MONTHS_LONG[$m - 1], $n, $y),
      'day_long' => sprintf('%s, %s %d', self::DAYS_LONG[$w], self::MONTHS_LONG[$m - 1], $n),
      'short' => sprintf('%s, %s %d', self::DAYS[$w], self::MONTHS[$m - 1], $n),
      'month_day' => sprintf('%s %d', self::MONTHS[$m - 1], $n),
      'month_year' => sprintf('%s %d', self::MONTHS_LONG[$m - 1], $y),
    ];
  }

  /**
   * A Unix time → YYYY-MM-DD in Vancouver.
   */
  public static function isoOf(int $timestamp): string {
    return (new \DateTimeImmutable('@' . $timestamp))->setTimezone(new \DateTimeZone(self::TZ))->format('Y-m-d');
  }

  // ------------------------------------------------------------------------------------------------- titles

  public static function isNoSchool(string $title): bool {
    return str_contains(mb_strtoupper($title), 'NO SCHOOL') || in_array(mb_strtolower($title), self::NO_SCHOOL, TRUE);
  }

  /**
   * A day off is never colour alone: the visible "No School" tag unless the title already says it.
   */
  public static function noSchoolTag(string $title): bool {
    return self::isNoSchool($title) && !str_contains(mb_strtolower($title), 'no school');
  }

  public static function isCode(string $title): bool {
    return (bool) preg_match(self::ROT_RE, $title);
  }

  /**
   * ALL-CAPS calendar titles become title case (same words, case only).
   */
  public static function smartCase(string $t): string {
    $keep = ['S1', 'S2', 'PT', 'PLT', 'PAC', 'CLC', 'TVR', 'BC', 'GLA', 'GNA', 'LTF', 'UBC', 'AM', 'PM', 'AP', 'ABCD',
      'BADC', 'COLLAB',
    ];
    $small = ['of', 'and', 'the', 'to', 'for', 'in', 'at', 'on', 'a', 'an', 'or', 'by'];
    preg_match_all('/\p{L}/u', $t, $letters);
    $letters = $letters[0];
    if (!$letters) {
      return $t;
    }
    $upper = count(array_filter($letters, fn($c) => mb_strtoupper($c) === $c && mb_strtolower($c) !== $c));
    if ($upper / count($letters) < 0.85) {
      return $t;
    }
    $out = [];
    foreach (explode(' ', $t) as $i => $w) {
      $core = preg_replace('/[^A-Za-z0-9]/', '', $w);
      if (in_array(strtoupper($core), $keep, TRUE) || preg_match('/\d/', $core)) {
        $out[] = $w;
      }
      elseif ($i && in_array(strtolower($core), $small, TRUE)) {
        $out[] = mb_strtolower($w);
      }
      else {
        $out[] = implode('-', array_map(fn($p) => $p === '' ? $p : mb_strtoupper(mb_substr($p, 0, 1)) . mb_strtolower(mb_substr($p, 1)), explode('-', $w)));
      }
    }
    return implode(' ', $out);
  }

  // ------------------------------------------------------------------------------------------------- events

  /**
   * The date field of calendar_event (field_event_date on the live site), or NULL.
   */
  private static function dateField(): ?array {
    $defs = \Drupal::service('entity_field.manager')->getFieldDefinitions('node', 'calendar_event');
    $types = ['smartdate', 'datetime', 'daterange', 'timestamp'];
    $name = isset($defs['field_event_date']) ? 'field_event_date' : NULL;
    if (!$name) {
      foreach ($defs as $field => $def) {
        if (in_array($def->getType(), $types, TRUE) && str_starts_with($field, 'field_')) {
          $name = $field;
          break;
        }
      }
    }
    return $name ? ['name' => $name, 'type' => $defs[$name]->getType()] : NULL;
  }

  /**
   * One stored date value → YYYY-MM-DD in Vancouver (Smart Date and timestamps are Unix times, datetime fields
   * hold "Y-m-d" or a UTC "Y-m-d\TH:i:s").
   */
  private static function isoFromValue($value): ?string {
    if ($value === NULL || $value === '') {
      return NULL;
    }
    if (is_numeric($value)) {
      return self::isoOf((int) $value);
    }
    $value = (string) $value;
    if (preg_match('/^\d{4}-\d\d-\d\d$/', $value)) {
      return $value;
    }
    try {
      return (new \DateTimeImmutable($value, new \DateTimeZone('UTC')))->setTimezone(new \DateTimeZone(self::TZ))->format('Y-m-d');
    }
    catch (\Exception $e) {
      return NULL;
    }
  }

  /**
   * Published calendar_event nodes from the start of this school year: [{d, t, u}] sorted by date, then title.
   * Cached until a node changes (node_list).
   */
  public static function events(): array {
    if (isset(self::$memo['events'])) {
      return self::$memo['events'];
    }
    $today = self::today();
    $year = (int) substr($today, 0, 4) - ((int) substr($today, 5, 2) < 8 ? 1 : 0);
    $from = sprintf('%d-08-01', $year);
    $cid = 'mcroberts:events:' . $from;
    if ($cache = \Drupal::cache()->get($cid)) {
      return self::$memo['events'] = $cache->data;
    }
    $events = [];
    $field = self::dateField();
    if ($field) {
      $storage = \Drupal::entityTypeManager()->getStorage('node');
      $query = $storage->getQuery()->accessCheck(FALSE)->condition('type', 'calendar_event')->condition('status', 1);
      if (in_array($field['type'], ['smartdate', 'timestamp'], TRUE)) {
        $start = new \DateTimeImmutable($from . ' 00:00:00', new \DateTimeZone(self::TZ));
        $query->condition($field['name'] . '.value', $start->getTimestamp(), '>=');
      }
      else {
        $query->condition($field['name'] . '.value', $from, '>=');
      }
      foreach (array_chunk($query->execute(), 100) as $ids) {
        foreach ($storage->loadMultiple($ids) as $node) {
          $title = Site::clean($node->label());
          $url = $node->toUrl()->toString();
          foreach ($node->get($field['name']) as $item) {
            $iso = self::isoFromValue($item->value);
            if ($iso && $iso >= $from) {
              $events[] = ['d' => $iso, 't' => $title, 'u' => $url];
            }
          }
        }
        $storage->resetCache($ids);
      }
    }
    usort($events, fn($a, $b) => [$a['d'], $a['t']] <=> [$b['d'], $b['t']]);
    \Drupal::cache()->set($cid, $events, Cache::PERMANENT, ['node_list']);
    return self::$memo['events'] = $events;
  }

  /**
   * Date → its rotation code (ABCD, BADC, PLT Rot n, COLLAB …).
   */
  public static function codes(): array {
    if (!isset(self::$memo['codes'])) {
      $codes = [];
      foreach (self::events() as $e) {
        if (self::isCode($e['t']) && !isset($codes[$e['d']])) {
          $codes[$e['d']] = $e['t'];
        }
      }
      self::$memo['codes'] = $codes;
    }
    return self::$memo['codes'];
  }

  /**
   * Real events (no rotation codes) from a date on, each title once per day.
   */
  public static function realEvents(string $start): array {
    $seen = [];
    $out = [];
    foreach (self::events() as $e) {
      if ($e['d'] < $start || self::isCode($e['t'])) {
        continue;
      }
      $key = mb_strtolower($e['t']) . '|' . $e['d'];
      if (isset($seen[$key])) {
        continue;
      }
      $seen[$key] = TRUE;
      $out[] = $e;
    }
    return $out;
  }

  /**
   * Date → {codes: [{t, u}], events: [{t, u}]} (build.py CAL_DAYS).
   */
  public static function days(): array {
    if (isset(self::$memo['days'])) {
      return self::$memo['days'];
    }
    $days = [];
    $seen = [];
    foreach (self::events() as $e) {
      $key = mb_strtolower($e['t']) . '|' . $e['d'];
      if (isset($seen[$key])) {
        continue;
      }
      $seen[$key] = TRUE;
      $days[$e['d']] = $days[$e['d']] ?? ['codes' => [], 'events' => []];
      $days[$e['d']][self::isCode($e['t']) ? 'codes' : 'events'][] = ['t' => $e['t'], 'u' => $e['u']];
    }
    ksort($days);
    return self::$memo['days'] = $days;
  }

  /**
   * An agenda day row (build.py agenda_day()).
   */
  public static function agendaDay(string $iso, array $info, ?string $today = NULL, bool $ids = TRUE, ?string $cur_url = NULL): array {
    $codes = $info['codes'];
    $evs = $info['events'];
    $cls = ['aday'];
    $code_only = $codes && !$evs;
    if ($code_only && !($today && $iso === $today)) {
      $cls[] = 'is-code-only';
    }
    if (!$codes && !$evs) {
      $cls[] = 'is-empty';
    }
    foreach ($evs as $e) {
      if (self::isNoSchool($e['t'])) {
        $cls[] = 'is-noschool';
        break;
      }
    }
    if (self::weekday($iso) >= 5) {
      $cls[] = 'is-weekend';
    }
    if ($today && $iso < $today) {
      $cls[] = 'is-past';
    }
    if ($today && $iso === $today) {
      $cls[] = 'is-today';
    }
    $link = fn($e) => ($e['u'] && $e['u'] !== $cur_url) ? $e['u'] : NULL;
    return [
      'iso' => $iso,
      'cls' => implode(' ', $cls),
      'id' => $ids ? 'd-' . $iso : NULL,
      'code_only' => $code_only,
      'today' => $today && $iso === $today,
      'chip' => self::parts($iso),
      'events' => array_map(fn($e) => [
        't' => self::smartCase($e['t']),
        'u' => $link($e),
        'noschool' => self::isNoSchool($e['t']),
        'tag' => self::noSchoolTag($e['t']),
      ], $evs),
      'codes' => array_map(fn($c) => ['t' => $c['t'], 'u' => $link($c)], $codes),
    ];
  }

  // ------------------------------------------------------------------------------------------------- bell schedule

  /**
   * data/bell-schedule.json: title, semesters, days, rotations {name: {column: [[range, label]]}}, collaboration days.
   */
  public static function bell(): array {
    if (!isset(self::$memo['bell'])) {
      $file = \Drupal::service('extension.list.theme')->getPath('mcroberts') . '/data/bell-schedule.json';
      $data = is_readable($file) ? json_decode(file_get_contents($file), TRUE) : NULL;
      self::$memo['bell'] = is_array($data) ? $data : [
        'title' => '', 'semesters' => [], 'days' => [], 'rotations' => [], 'collaborationDaysTitle' => '', 'collaborationDays' => [],
      ];
    }
    return self::$memo['bell'];
  }

  private static function schoolYear(): int {
    if (preg_match('/(20\d\d)/', self::bell()['collaborationDaysTitle'] ?? '', $m)) {
      return (int) $m[1];
    }
    return (int) substr(self::today(), 0, 4);
  }

  /**
   * "Sept. 9" → YYYY-MM-DD in the school year of the bell schedule.
   */
  public static function schoolDate(string $text): ?string {
    if (!preg_match('/^\s*([A-Za-z]+)\.?\s+(\d{1,2})/', $text, $m)) {
      return NULL;
    }
    $mon = array_search(strtolower(substr($m[1], 0, 3)), ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], TRUE);
    if ($mon === FALSE) {
      return NULL;
    }
    $mon++;
    $year = $mon >= 8 ? self::schoolYear() : self::schoolYear() + 1;
    return sprintf('%04d-%02d-%02d', $year, $mon, (int) $m[2]);
  }

  /**
   * [{name, from, to}] from the semesters table of the bell schedule.
   */
  public static function rotations(): array {
    if (!isset(self::$memo['rotations'])) {
      $out = [];
      foreach (self::bell()['semesters'] as $sem) {
        foreach ($sem['rotations'] as $r) {
          [$name, $span] = array_pad(explode(':', $r, 2), 2, '');
          [$a, $b] = array_pad(explode(' - ', $span, 2), 2, '');
          $out[] = ['name' => trim($name), 'from' => self::schoolDate($a), 'to' => self::schoolDate($b)];
        }
      }
      self::$memo['rotations'] = $out;
    }
    return self::$memo['rotations'];
  }

  /**
   * [[iso|NULL, label]] for the Collaboration Days.
   */
  public static function collabDays(): array {
    return array_map(fn($x) => [self::schoolDate($x), $x], self::bell()['collaborationDays'] ?? []);
  }

  public static function rotationFor(string $iso): ?string {
    foreach (self::rotations() as $r) {
      if ($r['from'] && $r['to'] && $r['from'] <= $iso && $iso <= $r['to']) {
        return $r['name'];
      }
    }
    $code = self::codes()[$iso] ?? '';
    if (str_ends_with($code, 'ABCD')) {
      return 'Rotation One';
    }
    if (str_ends_with($code, 'BADC')) {
      return 'Rotation Two';
    }
    return NULL;
  }

  /**
   * The first date from $start on that has a rotation code (a school day), within 60 days.
   */
  public static function schoolDay(string $start): ?string {
    $codes = self::codes();
    for ($i = 0; $i < 60; $i++) {
      $d = self::add($start, $i);
      if (isset($codes[$d])) {
        return $d;
      }
    }
    return NULL;
  }

  /**
   * Which column of the bell schedule a school day follows (build.py bell_col()).
   */
  public static function bellCol(string $iso, ?string $code): string {
    $c = strtoupper((string) $code);
    if (str_starts_with($c, 'COLLAB')) {
      return 'Collaboration Days';
    }
    $col = self::COLS[self::weekday($iso)] ?? 'MON';
    if (!str_starts_with($c, 'PLT') && in_array($col, ['TUE', 'THU'], TRUE)) {
      return 'MON';
    }
    return $col;
  }

  private static function hm(string $t): int {
    [$h, $m] = array_pad(explode(':', trim($t), 2), 2, '0');
    $h = (int) $h;
    if ($h < 7) {
      $h += 12;
    }
    return $h * 60 + (int) $m;
  }

  /**
   * The timetable rows of a day: [[range, label]].
   */
  public static function rowsFor(?string $iso): array {
    if (!$iso) {
      return [];
    }
    $code = self::codes()[$iso] ?? NULL;
    $rot = $code ? self::rotationFor($iso) : NULL;
    return $rot ? (self::bell()['rotations'][$rot][self::bellCol($iso, $code)] ?? []) : [];
  }

  /**
   * The Today card's block list (build.py blocks_html()).
   */
  public static function blocks(array $rows): array {
    $out = [];
    foreach ($rows as [$range, $label]) {
      $vals = array_map(fn($t) => self::hm($t), explode('-', $range));
      $cls = $label === 'PLT' ? 'is-plt' : ($label === 'Lunch' ? 'is-lunch' : (str_contains($label, 'Collab') ? 'is-collab' : ''));
      $out[] = [
        'label' => $label,
        'range' => $range,
        'm' => max(($vals[1] ?? 0) - ($vals[0] ?? 0), 20),
        'cls' => $cls,
        'blk' => in_array($label, ['A', 'B', 'C', 'D'], TRUE) ? strtolower($label) : '',
      ];
    }
    return $out;
  }

  /**
   * The bell schedule table cells (build.py bell_cell()).
   */
  public static function bellCell(array $rows): array {
    $out = [];
    foreach ($rows as [$range, $label]) {
      [$a, $b] = array_pad(explode('-', $range, 2), 2, '');
      $start = self::hm($a);
      $end = self::hm($b);
      $kind = ['PLT' => 'plt', 'Lunch' => 'lunch'][$label] ?? (str_contains($label, 'Collab') ? 'collab' : strtolower($label));
      $out[] = ['kind' => $kind, 'r' => $start - 510 + 1, 'l' => max($end - $start, 1), 'from' => $start, 'to' => $end,
        'label' => $label, 'a' => $a, 'b' => $b,
      ];
    }
    return $out;
  }

  /**
   * The school week of a day (build.py week_html()).
   */
  public static function week(string $day): array {
    $today = self::today();
    $codes = self::codes();
    $monday = self::add($day, -self::weekday($day));
    $out = [];
    for ($i = 0; $i < 5; $i++) {
      $d = self::add($monday, $i);
      $c = $codes[$d] ?? '';
      $cls = [];
      if ($d === $today) {
        $cls[] = 'is-today';
        if ($day !== $today) {
          $cls[] = 'is-quiet';
        }
      }
      elseif ($d < $today) {
        $cls[] = 'is-past';
      }
      if ($d === $day && $d !== $today) {
        $cls[] = 'is-shown';
      }
      if ($c === '') {
        $cls[] = 'is-off';
      }
      $p = self::parts($d);
      $out[] = ['cls' => implode(' ', $cls), 'today' => $d === $today, 'd' => $p['d'], 'n' => $p['n'], 'c' => $c];
    }
    return $out;
  }

  /**
   * Collaboration Days: past ones struck through, the next one highlighted (build.py collab_html()).
   */
  public static function collab(): array {
    $today = self::today();
    $next = FALSE;
    $out = [];
    foreach (self::collabDays() as [$d, $label]) {
      $past = $d && $d < $today;
      $cls = '';
      if ($past) {
        $cls = 'is-past';
      }
      elseif ($d && !$next) {
        $cls = 'is-next';
        $next = TRUE;
      }
      $out[] = ['iso' => $d ?? '', 'label' => $label, 'cls' => $cls, 'past' => $past];
    }
    return $out;
  }

  /**
   * The rotation names with their date ranges, as the JSON payloads carry them.
   */
  private static function rotationsJson(): array {
    return array_values(array_map(fn($r) => ['name' => $r['name'], 'from' => $r['from'], 'to' => $r['to']],
      array_filter(self::rotations(), fn($r) => $r['from'] && $r['to'])));
  }

  private static function json(array $data): Markup {
    return Markup::create(json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP));
  }

  // ------------------------------------------------------------------------------------------------- views of today

  /**
   * Everything the front page shows for today: the Today card, the Helpful Links sub-lines, Upcoming Events and
   * the #today-data payload for js/today.js.
   */
  public static function front(): array {
    $today = self::today();
    $day = self::schoolDay($today);
    $events = self::realEvents($today);
    $out = ['day' => NULL, 'events' => [], 'first' => NULL];
    if ($day) {
      $code = self::codes()[$day];
      $rot = self::rotationFor($day);
      $out['day'] = [
        'iso' => $day,
        'is_today' => $day === $today,
        'date' => self::parts($day)['day_long'],
        'code' => $code,
        'rot' => $rot,
        'blocks' => self::blocks(self::rowsFor($day)),
        'week' => self::week($day),
        'collab' => self::collab(),
        'collab_title' => rtrim(self::bell()['collaborationDaysTitle'] ?? '', ':'),
      ];
    }
    foreach (array_slice($events, 0, 8) as $e) {
      $out['events'][] = self::eventItem($e);
    }
    $out['first'] = $events ? self::eventItem($events[0]) : NULL;
    $json_events = [];
    $end = self::add($today, 400);
    foreach ($events as $e) {
      if ($e['d'] > $end) {
        break;
      }
      $json_events[] = ['d' => $e['d'], 't' => self::smartCase($e['t']), 'u' => $e['u'], 'x' => 0, 'o' => self::isNoSchool($e['t']) ? 1 : 0];
    }
    $codes = [];
    $from = self::add($today, -7);
    foreach (self::codes() as $d => $c) {
      if ($d >= $from) {
        $codes[$d] = $c;
      }
    }
    ksort($codes);
    $out['json'] = self::json([
      'built' => $today,
      'labels' => self::LABELS,
      'codes' => (object) $codes,
      'rotations' => self::rotationsJson(),
      'bell' => (object) self::bell()['rotations'],
      'collab' => array_values(array_map(fn($c) => ['d' => $c[0], 't' => $c[1]], array_filter(self::collabDays(), fn($c) => $c[0]))),
      'events' => $json_events,
      'n' => 8,
    ]);
    return $out;
  }

  /**
   * One upcoming event (date chip, title, link, No School tag).
   */
  public static function eventItem(array $e): array {
    return [
      'url' => $e['u'],
      'title' => self::smartCase($e['t']),
      'chip' => self::parts($e['d']),
      'noschool' => self::isNoSchool($e['t']),
      'tag' => self::noSchoolTag($e['t']),
    ];
  }

  /**
   * The School Calendar page: month chips, agenda months, #cal-data (build.py render_calendar()).
   */
  public static function page(string $cur_url): array {
    $today = self::today();
    $days = self::days();
    if (!$days) {
      return ['months' => [], 'chips' => [], 'json' => self::json(['built' => $today, 'first' => $today, 'last' => $today, 'labels' => self::LABELS, 'ev' => []])];
    }
    $first = array_key_first($days);
    $last = array_key_last($days);
    $in = $first <= $today && $today <= $last;
    if ($in && !isset($days[$today])) {
      $days[$today] = ['codes' => [], 'events' => []];
      ksort($days);
    }
    $this_month = substr($today, 0, 7);
    $shown = $in ? $this_month : substr($first, 0, 7);
    $nd = self::date($today)->modify('first day of next month')->format('Y-m');
    $months = [];
    foreach ($days as $d => $info) {
      $months[substr($d, 0, 7)][] = $d;
    }
    $chips = [];
    $blocks = [];
    $prev_year = NULL;
    foreach ($months as $ym => $ds) {
      [$y, $m] = array_map('intval', explode('-', $ym));
      $mid = sprintf('m-%d-%02d', $y, $m);
      $chips[] = ['mid' => $mid, 'ym' => $ym, 'this' => $ym === $this_month, 'shown' => $ym === $shown,
        'label' => self::MONTHS[$m - 1], 'year' => $y !== $prev_year ? $y : NULL,
      ];
      $prev_year = $y;
      $blocks[] = [
        'mid' => $mid,
        'folded' => $in && !in_array($ym, [$this_month, $nd], TRUE),
        'label' => sprintf('%s %d', self::MONTHS_LONG[$m - 1], $y),
        'rows' => array_map(fn($d) => self::agendaDay($d, $days[$d], $today, TRUE, $cur_url), $ds),
      ];
    }
    $ev = [];
    foreach (self::days() as $d => $info) {
      foreach ($info['events'] as $e) {
        $ev[] = [$d, self::smartCase($e['t']), self::isNoSchool($e['t']) ? 2 : 0, $e['u'] !== $cur_url ? $e['u'] : ''];
      }
      foreach ($info['codes'] as $c) {
        $ev[] = [$d, $c['t'], 1, $c['u'] !== $cur_url ? $c['u'] : ''];
      }
    }
    return [
      'chips' => $chips,
      'months' => $blocks,
      'json' => self::json(['built' => $today, 'first' => $first, 'last' => $last, 'labels' => self::LABELS, 'ev' => $ev]),
    ];
  }

  /**
   * A calendar event page: its day, code, timetable and the next events (build.py render_event()).
   */
  public static function eventPage(string $iso, string $cur_url): array {
    $code = self::codes()[$iso] ?? NULL;
    $rot = $code ? self::rotationFor($iso) : NULL;
    $next = [];
    foreach (self::realEvents(self::add($iso, 1)) as $e) {
      if (!in_array($e['d'], $next, TRUE)) {
        $next[] = $e['d'];
      }
      if (count($next) >= 4) {
        break;
      }
    }
    $days = self::days();
    return [
      'chip' => self::parts($iso),
      'code' => $code,
      'rot' => $rot,
      'blocks' => self::blocks(self::rowsFor($iso)),
      'day' => self::agendaDay($iso, $days[$iso] ?? ['codes' => [], 'events' => []], NULL, FALSE, $cur_url),
      'next' => array_map(fn($d) => self::agendaDay($d, ['codes' => [], 'events' => $days[$d]['events'] ?? []], NULL, FALSE, $cur_url), $next),
    ];
  }

  /**
   * The bell schedule as tables, with today's card and the #bell-data payload (build.py bell_html()).
   */
  public static function bellSchedule(): array {
    $today = self::today();
    $bell = self::bell();
    $day = self::schoolDay($today);
    $code = $day ? (self::codes()[$day] ?? NULL) : NULL;
    $rot = $day ? self::rotationFor($day) : NULL;
    $col = $day ? self::bellCol($day, $code) : NULL;
    $hl = ($day === $today && $day && in_array($col, ['Collaboration Days', self::COLS[self::weekday($day)] ?? NULL], TRUE)) ? $col : NULL;
    $semesters = [];
    foreach ($bell['semesters'] as $sem) {
      $rots = [];
      foreach (array_slice($sem['rotations'], 0, 2) as $r) {
        [$name, $span] = array_pad(explode(':', $r, 2), 2, '');
        [$a, $b] = array_pad(explode(' - ', $span, 2), 2, '');
        $fr = self::schoolDate($a);
        $to = self::schoolDate($b);
        $rots[] = ['name' => trim($name), 'span' => trim($span), 'from' => $fr ?? '', 'to' => $to ?? '',
          'current' => $fr && $to && $fr <= $today && $today <= $to,
        ];
      }
      $semesters[] = ['name' => self::smartCase($sem['name']), 'dates' => $sem['dates'], 'rotations' => $rots];
    }
    $tables = [];
    $n = 0;
    foreach ($bell['rotations'] as $rname => $cols) {
      $n++;
      $cells = [];
      foreach ($bell['days'] as $c) {
        $cells[] = ['col' => $c, 'today' => $rname === $rot && $c === $hl, 'blocks' => self::bellCell($cols[$c] ?? [])];
      }
      $tables[] = ['n' => $n, 'name' => $rname, 'cells' => $cells];
    }
    return [
      'title' => self::smartCase($bell['title'] ?? ''),
      'today' => [
        'is_today' => $day === $today,
        'iso' => $day ?? '',
        'date' => $day ? self::parts($day)['day_long'] : '',
        'rot' => $rot,
        'code' => $code,
        'blocks' => self::blocks(self::rowsFor($day)),
      ],
      'semesters' => $semesters,
      'rows' => [0, 1],
      'tables' => $tables,
      'collab_title' => rtrim($bell['collaborationDaysTitle'] ?? '', ':'),
      'collab' => self::collab(),
      'json' => self::json([
        'built' => $today,
        'labels' => self::LABELS,
        'codes' => (object) self::codes(),
        'rotations' => self::rotationsJson(),
        'bell' => (object) $bell['rotations'],
        'collab' => array_values(array_map(fn($c) => ['d' => $c[0], 't' => $c[1]], array_filter(self::collabDays(), fn($c) => $c[0]))),
      ]),
    ];
  }

}
