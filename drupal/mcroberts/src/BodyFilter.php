<?php

namespace Drupal\mcroberts;

use Drupal\Component\Utility\Html;
use Drupal\Core\Security\TrustedCallbackInterface;

/**
 * Presentation of rich text at render time (the stored body is never changed).
 *
 * A port of the static build's transform_body() (build.py), attached by mcroberts_preprocess_field() as a
 * #post_render callback on the body field and on the text fields of paragraphs. Each step only restructures the
 * words that are already there: typed bullets become a list, a layout table becomes the layout it drew, a phone
 * number becomes a tel: link, a "click here" link takes in the words it completes, headings get ids from their own
 * text (so menu deep links such as #post-secondary-info land), the bell schedule image becomes real tables.
 */
final class BodyFilter implements TrustedCallbackInterface {

  /**
   * Ids the page chrome uses: a body heading never takes one of them.
   */
  private const CHROME_IDS = ['page-title', 'main-content', 'page-wrapper', 'site-header', 'mobile-search', 'menu-drawer',
    'a11y-dialog', 'a11y-title', 'block-a11y', 'alert-title', 'alert-more', 'header-img-area', 'block-breadcrumbs',
    'block-mainnavigation', 'section-nav-title', 'contact-card-title', 'child-title', 'pager-title', 'bar-absent', 'today',
    'events-title', 'news-title', 'tasks-title', 'contact-title', 'about-title', 'strikers-title', 'rail-news-title',
  ];

  /**
   * The SHA-1 prefix (as in assets/content) of the bell schedule image the timetable tables replace.
   */
  public const BELL_IMAGE = 'bf352cd7a200';

  private const BULLET = '/^[\s\x{00A0}]*[\x{009F}\x{F0B7}\x{F0A7}\x{2022}\x{25AA}\x{25CF}\x{00B7}\x{2023}\x{2043}][\s\x{00A0}]*/u';
  private const GENERIC_LINK = '/^(?:click(?:ing)?\s+)?here\.?$/i';
  private const BOUNDARY = '/[.!?:;)](?=[\s\x{00A0}]|$)/u';
  private const INLINE = ['strong', 'b', 'em', 'i', 'span', 'u', 'small'];
  private const DOC = '/\.(pdf|docx?|pptx?|xlsx?)(?:$|[?#])/i';

  /**
   * Heading ids already given on this page (per scope).
   *
   * @var array
   */
  private static array $used = [];

  /**
   * Image key cache: src → SHA-1 prefix.
   *
   * @var array
   */
  private static array $keys = [];

  /**
   * {@inheritdoc}
   */
  public static function trustedCallbacks() {
    return ['postRender'];
  }

  /**
   * #post_render callback: the rendered text, restructured. Context in $element['#mcroberts'].
   */
  public static function postRender($markup, array $element) {
    $context = ($element['#mcroberts'] ?? []) + [
      'path' => '',
      'title' => '',
      'node_body' => FALSE,
      'bell' => '',
      'scope' => 'page',
    ];
    try {
      return self::transform((string) $markup, $context);
    }
    catch (\Throwable $e) {
      \Drupal::logger('mcroberts')->warning('Body filter skipped on @path: @message', ['@path' => $context['path'], '@message' => $e->getMessage()]);
      return $markup;
    }
  }

  /**
   * The whole pipeline, in build.py's order.
   */
  public static function transform(string $html, array $ctx): string {
    if (trim($html) === '') {
      return $html;
    }
    $dom = Html::load($html);
    $body = $dom->getElementsByTagName('body')->item(0);
    if (!$body) {
      return $html;
    }
    $state = new \ArrayObject(['bell_img' => NULL]);
    self::widenGenericLinks($dom, $body);
    self::emptyParagraphs($body);
    self::typedBullets($dom, $body);
    self::nbspRuns($body);
    self::linkLists($dom, $body);
    self::datesList($dom, $body);
    self::capsHeadings($body);
    self::headingLevels($dom, $body);
    self::headingIds($body, $ctx['scope']);
    self::images($dom, $body, $ctx, $state);
    self::links($body);
    self::docLinks($dom, $body);
    self::structureMedia($dom, $body, $ctx);
    self::iframes($dom, $body, $ctx);
    self::phones($dom, $body);
    self::tables($dom, $body, $ctx);
    if ($ctx['node_body']) {
      $path = $ctx['path'];
      if ($path === Site::pathOf('contact')) {
        self::tweakContact($dom, $body);
      }
      elseif ($path === Site::pathOf('attendance')) {
        self::tweakAttendance($dom, $body);
      }
      elseif ($path === '/library') {
        self::tweakLibrary($dom, $body, $ctx);
      }
      elseif ($path === Site::pathOf('strikers')) {
        self::tweakStrikers($dom, $body);
      }
    }
    if ($state['bell_img'] && $ctx['bell'] !== '') {
      $img = $state['bell_img'];
      $p = $img->parentNode;
      $target = ($p instanceof \DOMElement && self::tag($p) === 'p' && count(self::kids($p)) === 1) ? $p : $img;
      // the original image stays one click away (the tables' last line links it as a file)
      $src = $img->getAttribute('src');
      $bell = str_replace('__MCROBERTS_BELL_SRC__', str_starts_with($src, 'data:') ? '#bell-title' : Html::escape($src), $ctx['bell']);
      self::replace($target, self::fragment($dom, $bell));
    }
    return self::serialize($dom, $body);
  }

  /**
   * The body's children as HTML. libxml's HTML serializer keeps an empty element as <b></b> on every Drupal 10
   * version (an XML serializer would write <b/>, which a browser reads as an open tag).
   */
  private static function serialize(\DOMDocument $dom, \DOMElement $body): string {
    $html = '';
    foreach (self::children($body) as $node) {
      $html .= $dom->saveHTML($node);
    }
    return $html;
  }

  // ------------------------------------------------------------------------------------------------- DOM helpers

  private static function tag($n): string {
    return $n instanceof \DOMElement ? strtolower($n->tagName) : '';
  }

  private static function children(\DOMNode $n): array {
    return iterator_to_array($n->childNodes, FALSE);
  }

  private static function elementChildren(\DOMNode $n): array {
    return array_values(array_filter(self::children($n), fn($c) => $c instanceof \DOMElement));
  }

  /**
   * A whitespace-only text node or a comment.
   */
  private static function blank($n): bool {
    return $n instanceof \DOMComment || ($n instanceof \DOMText && trim($n->nodeValue, " \t\n\r\0\x0B") === '');
  }

  /**
   * Children without blank text and comments.
   */
  private static function kids(\DOMNode $n): array {
    return array_values(array_filter(self::children($n), fn($c) => !self::blank($c) && ($c instanceof \DOMElement || $c instanceof \DOMText)));
  }

  /**
   * Descendant elements in document order (optionally of one tag).
   */
  private static function els(\DOMNode $root, string $tag = '*'): array {
    return $root instanceof \DOMElement || $root instanceof \DOMDocument ? iterator_to_array($root->getElementsByTagName($tag), FALSE) : [];
  }

  /**
   * The root and all its descendant elements (build.py El.iter()).
   */
  private static function all(\DOMElement $root): array {
    return array_merge([$root], self::els($root));
  }

  private static function text(\DOMNode $n): string {
    return Site::clean($n->textContent);
  }

  private static function hasAncestor(\DOMNode $n, string $tag): bool {
    for ($p = $n->parentNode; $p; $p = $p->parentNode) {
      if (self::tag($p) === $tag) {
        return TRUE;
      }
    }
    return FALSE;
  }

  private static function classes(\DOMElement $el): array {
    return preg_split('/\s+/', trim($el->getAttribute('class')), -1, PREG_SPLIT_NO_EMPTY);
  }

  private static function addClass(\DOMElement $el, string $class): void {
    $c = self::classes($el);
    if (!in_array($class, $c, TRUE)) {
      $c[] = $class;
      $el->setAttribute('class', implode(' ', $c));
    }
  }

  private static function el(\DOMDocument $dom, string $tag, array $attrs = [], array $children = []): \DOMElement {
    $el = $dom->createElement($tag);
    foreach ($attrs as $k => $v) {
      $el->setAttribute($k, (string) $v);
    }
    foreach ($children as $c) {
      $el->appendChild(is_string($c) ? $dom->createTextNode($c) : $c);
    }
    return $el;
  }

  /**
   * HTML → nodes owned by $dom.
   */
  private static function fragment(\DOMDocument $dom, string $html): array {
    $tmp = Html::load($html);
    $body = $tmp->getElementsByTagName('body')->item(0);
    $out = [];
    foreach (self::children($body) as $c) {
      $out[] = $dom->importNode($c, TRUE);
    }
    return $out;
  }

  private static function icon(\DOMDocument $dom, string $name, string $class = 'icon'): array {
    return self::fragment($dom, sprintf('<svg class="%s" aria-hidden="true" focusable="false"><use href="#i-%s"/></svg>', $class, $name));
  }

  private static function replace(\DOMNode $old, array $new): void {
    $parent = $old->parentNode;
    if (!$parent) {
      return;
    }
    foreach ($new as $n) {
      $parent->insertBefore($n, $old);
    }
    $parent->removeChild($old);
  }

  /**
   * Moves the nodes into $el (appended, in order).
   */
  private static function adopt(\DOMElement $el, array $nodes): \DOMElement {
    foreach ($nodes as $n) {
      $el->appendChild($n);
    }
    return $el;
  }

  /**
   * A run of siblings → one node in the place of the first.
   */
  private static function swapRun(array $run, \DOMNode $node): void {
    $parent = $run[0]->parentNode;
    $parent->insertBefore($node, $run[0]);
    foreach ($run as $x) {
      if ($x->parentNode) {
        $x->parentNode->removeChild($x);
      }
    }
  }

  /**
   * Runs of consecutive children passing $test; blank text between them is skipped (build.py _runs()).
   */
  private static function runs(\DOMNode $parent, callable $test): array {
    $runs = [];
    $run = [];
    foreach (array_merge(self::children($parent), [NULL]) as $ch) {
      if ($ch !== NULL && $test($ch)) {
        $run[] = $ch;
        continue;
      }
      if ($ch !== NULL && self::blank($ch) && $run) {
        continue;
      }
      if ($run) {
        $runs[] = $run;
      }
      $run = [];
    }
    return $runs;
  }

  private static function rename(\DOMElement $el, string $tag): \DOMElement {
    $new = $el->ownerDocument->createElement($tag);
    foreach (iterator_to_array($el->attributes, FALSE) as $attr) {
      $new->setAttribute($attr->nodeName, $attr->nodeValue);
    }
    foreach (self::children($el) as $c) {
      $new->appendChild($c);
    }
    $el->parentNode->replaceChild($new, $el);
    return $new;
  }

  /**
   * An internal page path of a link target ("/a/b"), or NULL for another host.
   */
  private static function targetPath(string $href): ?string {
    $parts = parse_url($href);
    if ($parts === FALSE || isset($parts['scheme']) && !in_array($parts['scheme'], ['http', 'https'], TRUE)) {
      return NULL;
    }
    $host = $parts['host'] ?? '';
    $own = [\Drupal::request()->getHost(), 'mcroberts.sd38.bc.ca', 'www.mcroberts.sd38.bc.ca'];
    if ($host !== '' && !in_array($host, $own, TRUE)) {
      return NULL;
    }
    $path = $parts['path'] ?? '/';
    $base = Site::base();
    if ($base !== '' && str_starts_with($path, $base . '/')) {
      $path = substr($path, strlen($base));
    }
    $path = Site::norm(rawurldecode($path));
    // an old alias the Redirect module answers: the page it now lives at
    if (\Drupal::moduleHandler()->moduleExists('redirect')) {
      try {
        $redirect = \Drupal::service('redirect.repository')->findMatchingRedirect(ltrim($path, '/'), [], \Drupal::languageManager()->getCurrentLanguage()->getId());
        if ($redirect) {
          $url = $redirect->getRedirectUrl()->toString();
          $path = Site::norm(($base !== '' && str_starts_with($url, $base)) ? substr($url, strlen($base)) : $url);
        }
      }
      catch (\Throwable $e) {
        // keep the path as written
      }
    }
    return $path;
  }

  private static function goIcon(\DOMDocument $dom, string $url): array {
    return self::icon($dom, preg_match('~^(https?:)?//~i', $url) ? 'ext' : 'arrow', 'icon tile-go');
  }

  // ------------------------------------------------------------------------------------------------- steps

  /**
   * A link that reads only "click here" / "here" takes in the clause it completes (WCAG 2.4.4).
   */
  private static function widenGenericLinks(\DOMDocument $dom, \DOMElement $root): void {
    foreach (self::els($root, 'a') as $a) {
      if (!preg_match(self::GENERIC_LINK, self::text($a)) || !$a->parentNode) {
        continue;
      }
      $kids = self::children($a->parentNode);
      $i = array_search($a, $kids, TRUE);
      $take = [];
      $cut = NULL;
      $j = $i - 1;
      while ($j >= 0) {
        $ch = $kids[$j];
        if ($ch instanceof \DOMText) {
          if (preg_match_all(self::BOUNDARY, $ch->nodeValue, $ms, PREG_OFFSET_CAPTURE)) {
            $last = end($ms[0]);
            $cut = [$j, $last[1] + strlen($last[0])];
            break;
          }
          array_unshift($take, $ch);
        }
        elseif ($ch instanceof \DOMElement && in_array(self::tag($ch), self::INLINE, TRUE) && !self::els($ch, 'a') && !preg_match(self::BOUNDARY, $ch->textContent)) {
          array_unshift($take, $ch);
        }
        else {
          break;
        }
        $j--;
      }
      $before = implode('', array_map(fn($x) => $x->textContent, $take));
      if ($cut !== NULL) {
        $before = substr($kids[$cut[0]]->nodeValue, $cut[1]) . $before;
      }
      if (count(preg_split('/\s+/u', Site::clean($before), -1, PREG_SPLIT_NO_EMPTY)) >= 3) {
        $moved = $take;
        if ($cut !== NULL) {
          $text = $kids[$cut[0]]->nodeValue;
          $head = substr($text, 0, $cut[1]);
          $tail = substr($text, $cut[1]);
          $lead_ws = substr($tail, 0, strlen($tail) - strlen(ltrim($tail)));
          $kids[$cut[0]]->nodeValue = $head . $lead_ws;
          if (trim($tail) !== '') {
            array_unshift($moved, $dom->createTextNode(ltrim($tail)));
          }
        }
        $first = $a->firstChild;
        foreach ($moved as $m) {
          if ($m->parentNode) {
            $m->parentNode->removeChild($m);
          }
          $a->insertBefore($m, $first);
        }
        continue;
      }
      $next = $kids[$i + 1] ?? NULL;
      if ($next instanceof \DOMText && trim($next->nodeValue) !== '') {
        $txt = $next->nodeValue;
        $end = preg_match(self::BOUNDARY, $txt, $m, PREG_OFFSET_CAPTURE) ? $m[0][1] : strlen($txt);
        $clause = substr($txt, 0, $end);
        if (count(preg_split('/\s+/u', Site::clean($clause), -1, PREG_SPLIT_NO_EMPTY)) >= 2) {
          $stripped = preg_replace('/[\s\x{00A0}]+$/u', '', $clause);
          $trail_ws = substr($clause, strlen($stripped));
          $a->appendChild($dom->createTextNode($stripped));
          $next->nodeValue = $trail_ws . substr($txt, $end);
        }
      }
    }
  }

  private static function emptyParagraphs(\DOMElement $root): void {
    foreach (self::els($root, 'p') as $p) {
      if (self::text($p) === '' && !self::els($p, 'img') && !self::els($p, 'iframe') && $p->parentNode) {
        $p->parentNode->removeChild($p);
      }
    }
  }

  private static function stripBullet(\DOMNode $el): void {
    foreach (self::children($el) as $ch) {
      if ($ch instanceof \DOMText) {
        if (trim($ch->nodeValue, "\u{00A0} \n\t") === '') {
          continue;
        }
        $ch->nodeValue = preg_replace(self::BULLET, '', $ch->nodeValue, 1);
        return;
      }
      if ($ch instanceof \DOMElement) {
        self::stripBullet($ch);
        return;
      }
    }
  }

  /**
   * Typed bullets (Wingdings or bullet glyphs at the start of consecutive paragraphs) → a real list.
   */
  private static function typedBullets(\DOMDocument $dom, \DOMElement $root): void {
    foreach (self::all($root) as $parent) {
      $run = [];
      foreach (array_merge(self::children($parent), [NULL]) as $ch) {
        if (self::tag($ch) === 'p' && preg_match(self::BULLET, $ch->textContent)) {
          $run[] = $ch;
          continue;
        }
        if ($ch !== NULL && self::blank($ch) && $run) {
          continue;
        }
        if (count($run) >= 2) {
          $ul = self::el($dom, 'ul');
          foreach ($run as $p) {
            $li = self::adopt(self::el($dom, 'li'), self::children($p));
            self::stripBullet($li);
            $ul->appendChild($li);
          }
          self::swapRun($run, $ul);
        }
        $run = [];
      }
    }
  }

  /**
   * Runs of non-breaking spaces typed for layout → one space.
   */
  private static function nbspRuns(\DOMElement $root): void {
    foreach (self::all($root) as $el) {
      foreach (self::children($el) as $c) {
        if ($c instanceof \DOMText && str_contains($c->nodeValue, "\u{00A0}")) {
          $c->nodeValue = preg_replace('/[ \x{00A0}]{2,}/u', ' ', $c->nodeValue);
        }
      }
    }
  }

  /**
   * Two or more links standing alone side by side → a link list.
   */
  private static function linkLists(\DOMDocument $dom, \DOMElement $root): void {
    $skip = ['a', 'li', 'p', 'td', 'th', 'summary', 'h2', 'h3', 'h4'];
    foreach (self::all($root) as $parent) {
      if (in_array(self::tag($parent), $skip, TRUE)) {
        continue;
      }
      $runs = self::runs($parent, fn($n) => self::tag($n) === 'a' && !self::els($n, 'img') && self::text($n) !== ''
        && !in_array('file-card', self::classes($n), TRUE));
      foreach ($runs as $run) {
        if (count($run) < 2) {
          continue;
        }
        $ul = self::el($dom, 'ul', ['class' => 'link-list']);
        foreach ($run as $link) {
          $label = self::text($link);
          while ($link->firstChild) {
            $link->removeChild($link->firstChild);
          }
          $link->appendChild($dom->createTextNode($label));
        }
        $parent->insertBefore($ul, $run[0]);
        foreach ($run as $link) {
          $ul->appendChild(self::adopt(self::el($dom, 'li'), [$link]));
        }
      }
    }
  }

  /**
   * Typed "date" heading + "- event" line pairs (Important Dates) → a dates list.
   */
  private static function datesList(\DOMDocument $dom, \DOMElement $root): void {
    $date_re = '/^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d/i';
    foreach (self::all($root) as $parent) {
      $kids = self::kids($parent);
      $i = 0;
      $pairs = [];
      while ($i + 1 < count($kids)) {
        $h = $kids[$i];
        $p = $kids[$i + 1];
        if (preg_match('/^h[3-6]$/', self::tag($h)) && preg_match($date_re, self::text($h)) && self::tag($p) === 'p'
          && preg_match('/^[-–—]\s/u', self::text($p))) {
          $pairs[] = [$h, $p];
          $i += 2;
          continue;
        }
        if (count($pairs) >= 2) {
          break;
        }
        $pairs = [];
        $i++;
      }
      if (count($pairs) < 2) {
        continue;
      }
      $dl = self::el($dom, 'dl', ['class' => 'dates']);
      $parent->insertBefore($dl, $pairs[0][0]);
      foreach ($pairs as [$h, $p]) {
        $dt = self::adopt(self::el($dom, 'dt'), self::children($h));
        foreach (self::children($p) as $c) {
          if ($c instanceof \DOMText) {
            if (trim($c->nodeValue) !== '') {
              $c->nodeValue = preg_replace('/^\s*[-–—]\s*/u', '', $c->nodeValue);
              break;
            }
            continue;
          }
          break;
        }
        $dd = self::adopt(self::el($dom, 'dd'), self::children($p));
        $dl->appendChild($dt);
        $dl->appendChild($dd);
        $parent->removeChild($h);
        $parent->removeChild($p);
      }
    }
  }

  /**
   * ALL-CAPS headings typed into the body read as eyebrows (a class only; the words stay as typed).
   */
  private static function capsHeadings(\DOMElement $root): void {
    foreach (self::els($root) as $h) {
      if (!preg_match('/^h[2-6]$/', self::tag($h))) {
        continue;
      }
      preg_match_all('/\p{L}/u', $h->textContent, $m);
      $letters = $m[0];
      if (count($letters) >= 4 && !array_filter($letters, fn($c) => !(mb_strtoupper($c) === $c && mb_strtolower($c) !== $c))) {
        self::addClass($h, 'is-caps');
      }
    }
  }

  /**
   * The page title is the h1, so the body starts at h2 and never skips a level on the way down.
   */
  private static function headingLevels(\DOMDocument $dom, \DOMElement $root): void {
    $heads = array_values(array_filter(self::els($root), fn($e) => (bool) preg_match('/^h[2-6]$/', self::tag($e))));
    if (!$heads) {
      return;
    }
    $levels = array_map(fn($h) => (int) substr(self::tag($h), 1), $heads);
    $shift = min($levels) > 2 ? min($levels) - 2 : 0;
    $prev = 1;
    foreach ($heads as $k => $h) {
      $lvl = min($levels[$k] - $shift, $prev + 1);
      if ($lvl !== $levels[$k]) {
        self::rename($h, 'h' . $lvl);
      }
      $prev = $lvl;
    }
  }

  /**
   * Heading ids from their own text, unique on the page.
   */
  private static function headingIds(\DOMElement $root, string $scope): void {
    $used = &self::$used[$scope];
    $used = $used ?? [];
    foreach (self::els($root) as $h) {
      if (!preg_match('/^h[2-6]$/', self::tag($h)) || $h->getAttribute('id') !== '') {
        continue;
      }
      $base = Site::slug($h->textContent);
      if ($base === '') {
        continue;
      }
      $id = $base;
      $n = 2;
      while (isset($used[$id]) || in_array($id, self::CHROME_IDS, TRUE)) {
        $id = $base . '-' . $n++;
      }
      $used[$id] = TRUE;
      $h->setAttribute('id', $id);
    }
  }

  /**
   * The first 12 hex digits of the SHA-1 of an image's bytes (inline data: URI or a public file), as the static
   * build names its copies in assets/content; NULL when the bytes are not at hand.
   */
  public static function imageKey(string $src): ?string {
    if (array_key_exists($src, self::$keys)) {
      return self::$keys[$src];
    }
    $key = NULL;
    if (str_starts_with($src, 'data:')) {
      $comma = strpos($src, ',');
      $data = $comma === FALSE ? FALSE : base64_decode(substr($src, $comma + 1), TRUE);
      $key = $data ? substr(sha1($data), 0, 12) : NULL;
    }
    else {
      $path = parse_url($src, PHP_URL_PATH);
      $host = parse_url($src, PHP_URL_HOST);
      if ($path && (!$host || $host === \Drupal::request()->getHost())) {
        $base = Site::base();
        if ($base !== '' && str_starts_with($path, $base . '/')) {
          $path = substr($path, strlen($base));
        }
        $public = '/' . trim(\Drupal::service('stream_wrapper_manager')->getViaScheme('public')->getDirectoryPath(), '/') . '/';
        if (str_starts_with($path, $public)) {
          $file = DRUPAL_ROOT . rawurldecode($path);
          if (is_file($file) && filesize($file) < 20000000) {
            $key = substr(sha1_file($file), 0, 12);
          }
        }
      }
    }
    return self::$keys[$src] = $key;
  }

  /**
   * data/image-text.json: the words of informative images (alt + the same words as text).
   */
  private static function imageText(): array {
    static $data = NULL;
    if ($data === NULL) {
      $file = \Drupal::service('extension.list.theme')->getPath('mcroberts') . '/data/image-text.json';
      $data = is_readable($file) ? (json_decode(file_get_contents($file), TRUE) ?: []) : [];
    }
    return $data;
  }

  private static function images(\DOMDocument $dom, \DOMElement $root, array $ctx, \ArrayObject $state): void {
    $texts = self::imageText();
    foreach (self::els($root, 'img') as $im) {
      $key = self::imageKey($im->getAttribute('src'));
      if ($key === self::BELL_IMAGE && !$state['bell_img']) {
        $state['bell_img'] = $im;
      }
      $info = $key ? ($texts[$key] ?? NULL) : NULL;
      if ($info && Site::clean($im->getAttribute('alt')) === '') {
        $im->setAttribute('alt', $info['alt']);
        if ($info['html'] !== '') {
          $holder = in_array(self::tag($im->parentNode), ['p', 'a'], TRUE) ? $im->parentNode : $im;
          while ($holder->parentNode && in_array(self::tag($holder->parentNode), ['p', 'a'], TRUE)) {
            $holder = $holder->parentNode;
          }
          if ($holder->parentNode) {
            $det = self::fragment($dom, sprintf('<details class="accordion img-text"><summary>%s</summary><div class="accordion__body">%s</div></details>',
              Html::escape($info['alt']), $info['html']));
            $after = $holder->nextSibling;
            foreach ($det as $d) {
              $holder->parentNode->insertBefore($d, $after);
            }
          }
        }
      }
      if (!$im->hasAttribute('alt')) {
        $im->setAttribute('alt', '');
      }
      $im->setAttribute('loading', 'lazy');
      $im->setAttribute('decoding', 'async');
    }
  }

  /**
   * A title attribute that repeats the link text says nothing twice.
   */
  private static function links(\DOMElement $root): void {
    foreach (self::els($root, 'a') as $a) {
      if ($a->hasAttribute('title') && mb_strtolower(Site::clean($a->getAttribute('title'))) === mb_strtolower(self::text($a))) {
        $a->removeAttribute('title');
      }
    }
  }

  /**
   * A document card: type badge, file name, download icon.
   */
  private static function card(\DOMDocument $dom, \DOMElement $link, string $kind): void {
    $label = self::adopt(self::el($dom, 'span', ['class' => 'file-name']), self::children($link));
    $link->setAttribute('class', 'file-card');
    $badge = self::el($dom, 'span', ['class' => 'file-badge', 'data-ext' => $kind, 'aria-hidden' => 'true'], [$kind]);
    $link->appendChild($badge);
    $link->appendChild($label);
    foreach (self::icon($dom, 'download') as $i) {
      $link->appendChild($i);
    }
  }

  /**
   * A paragraph that is only a link to a document → a file card; consecutive ones form one list.
   */
  private static function docLinks(\DOMDocument $dom, \DOMElement $root): void {
    $is_doc = function ($ch) {
      if (self::tag($ch) !== 'p') {
        return FALSE;
      }
      $k = self::kids($ch);
      return count($k) === 1 && self::tag($k[0]) === 'a' && preg_match(self::DOC, $k[0]->getAttribute('href'));
    };
    foreach (self::all($root) as $parent) {
      foreach (self::runs($parent, $is_doc) as $run) {
        $wrap = self::el($dom, 'div', ['class' => 'file-list']);
        $parent->insertBefore($wrap, $run[0]);
        foreach ($run as $p) {
          $link = self::kids($p)[0];
          preg_match(self::DOC, $link->getAttribute('href'), $m);
          self::card($dom, $link, strtolower($m[1]));
          $wrap->appendChild($link);
          $parent->removeChild($p);
        }
      }
    }
  }

  private static function onlyImgLink($n): bool {
    return self::tag($n) === 'a' && count(self::els($n, 'img')) === 1 && self::text($n) === '';
  }

  /**
   * Galleries, the banner reel, link chips, long document lists and launch tiles (build.py structure_media()).
   */
  private static function structureMedia(\DOMDocument $dom, \DOMElement $root, array $ctx): void {
    $cur = $ctx['path'];
    foreach (self::all($root) as $parent) {
      if (in_array(self::tag($parent), ['a', 'figure', 'li', 'td', 'th'], TRUE)) {
        continue;
      }
      // image links in a row → gallery (js/gallery.js lightbox)
      foreach (self::runs($parent, fn($n) => self::onlyImgLink($n)) as $run) {
        if (count($run) < 3) {
          continue;
        }
        $ul = self::el($dom, 'ul', ['class' => 'gallery' . ($cur === '/library/read-listen' ? ' gallery--covers' : ''), 'data-gallery' => '']);
        $parent->insertBefore($ul, $run[0]);
        foreach ($run as $link) {
          $im = self::els($link, 'img')[0];
          $cap = Site::clean(html_entity_decode($link->getAttribute('title') ?: $im->getAttribute('alt'), ENT_QUOTES | ENT_HTML5, 'UTF-8'));
          $link->removeAttribute('title');
          $link->setAttribute('class', 'gallery-link');
          $link->setAttribute('data-lightbox', $im->getAttribute('src'));
          $fig = self::adopt(self::el($dom, 'figure'), [$link]);
          if ($cap !== '') {
            $fig->appendChild(self::el($dom, 'figcaption', [], [$cap]));
          }
          $ul->appendChild(self::adopt(self::el($dom, 'li'), [$fig]));
        }
      }
      // bare images in a row → the banner reel (scroll-snap, no autoplay)
      foreach (self::runs($parent, fn($n) => self::tag($n) === 'img') as $run) {
        $banners = !array_filter($run, fn($im) => !str_starts_with(mb_strtolower(Site::clean($im->getAttribute('alt'))), 'banner'));
        if (count($run) < 2 || !($cur === '/library' || $banners)) {
          continue;
        }
        $track = self::el($dom, 'ul', ['class' => 'reel-track', 'tabindex' => '0', 'aria-label' => $ctx['title'], 'data-reel-track' => '']);
        $reel = self::el($dom, 'div', ['class' => 'reel', 'data-reel' => '']);
        $parent->insertBefore($reel, $run[0]);
        foreach ($run as $i => $im) {
          $cap = preg_replace('/^Banner\s+/i', '', Site::clean($im->getAttribute('alt')));
          if (str_contains(mb_strtolower($cap), 'description automatically generated')) {
            $cap = '';
          }
          if ($i === 0) {
            $im->setAttribute('loading', 'eager');
          }
          $fig = self::adopt(self::el($dom, 'figure'), [$im]);
          if ($cap !== '') {
            $fig->appendChild(self::el($dom, 'figcaption', ['aria-hidden' => 'true'], [$cap]));
          }
          $track->appendChild(self::adopt(self::el($dom, 'li', ['class' => 'reel-slide']), [$fig]));
        }
        $reel->appendChild($track);
        $nav = sprintf('<div class="reel-nav needs-js"><button type="button" class="reel-btn reel-prev" data-reel-prev>%1$s<span class="vh">Previous</span></button>'
          . '<ol class="reel-dots" aria-hidden="true">%2$s</ol><button type="button" class="reel-btn" data-reel-next>%1$s<span class="vh">Next</span></button></div>',
          '<svg class="icon" aria-hidden="true" focusable="false"><use href="#i-arrow"/></svg>', str_repeat('<li></li>', count($run)));
        foreach (self::fragment($dom, $nav) as $n) {
          $reel->appendChild($n);
        }
      }
      // paragraphs that are one short link each → link chips
      $chip = function ($n) {
        if (self::tag($n) !== 'p') {
          return FALSE;
        }
        $k = self::kids($n);
        $len = mb_strlen(self::text($n));
        return count($k) === 1 && self::tag($k[0]) === 'a' && !self::els($k[0], 'img') && !in_array('file-card', self::classes($k[0]), TRUE)
          && $len > 0 && $len <= 32;
      };
      foreach (self::runs($parent, $chip) as $run) {
        if (count($run) < 3) {
          continue;
        }
        $ul = self::el($dom, 'ul', ['class' => 'link-chips']);
        $parent->insertBefore($ul, $run[0]);
        foreach ($run as $p) {
          $ul->appendChild(self::adopt(self::el($dom, 'li'), [self::kids($p)[0]]));
          $parent->removeChild($p);
        }
      }
    }
    // document lists split into one wrapper per file → one list; a long one gets the filter (js/filter.js)
    foreach (self::all($root) as $parent) {
      foreach (self::runs($parent, fn($n) => self::tag($n) === 'div' && in_array('file-list', self::classes($n), TRUE)) as $run) {
        $first = array_shift($run);
        foreach ($run as $other) {
          foreach (self::elementChildren($other) as $c) {
            $first->appendChild($c);
          }
          $parent->removeChild($other);
        }
      }
    }
    foreach (self::els($root, 'div') as $fl) {
      if (!in_array('file-list', self::classes($fl), TRUE) || !$fl->parentNode) {
        continue;
      }
      $cards = array_values(array_filter(self::elementChildren($fl), fn($c) => self::tag($c) === 'a'));
      if (count($cards) >= 12 && !($fl->parentNode instanceof \DOMElement && in_array('directory', self::classes($fl->parentNode), TRUE))) {
        foreach ($cards as $c) {
          $c->setAttribute('data-filter-row', '');
        }
        $scope = self::el($dom, 'div', ['class' => 'directory', 'data-filter' => '']);
        $fl->parentNode->replaceChild($scope, $fl);
        foreach (self::fragment($dom, self::filterBar('files', count($cards))) as $n) {
          $scope->appendChild($n);
        }
        $scope->appendChild($fl);
      }
    }
    // an image link with its own label → launch tile
    foreach (self::els($root, 'a') as $link) {
      $imgs = self::els($link, 'img');
      $txt = self::text($link);
      if (count($imgs) !== 1 || $txt === '' || mb_strlen($txt) > 60 || self::hasAncestor($link, 'table') || self::hasAncestor($link, 'li')) {
        continue;
      }
      $im = $imgs[0];
      $im->setAttribute('alt', '');
      $im->parentNode->removeChild($im);
      while ($link->firstChild) {
        $link->removeChild($link->firstChild);
      }
      $link->setAttribute('class', 'launch-tile');
      $link->appendChild(self::adopt(self::el($dom, 'span', ['class' => 'launch-img']), [$im]));
      $link->appendChild(self::el($dom, 'span', ['class' => 'launch-text'], [$txt]));
      foreach (self::goIcon($dom, $link->getAttribute('href')) as $n) {
        $link->appendChild($n);
      }
      $p = $link->parentNode;
      if (self::tag($p) === 'p' && count(self::kids($p)) === 1) {
        $p->parentNode->replaceChild($link, $p);
      }
    }
  }

  /**
   * The filter bar of a long list or table (js/filter.js); shown only when scripts run.
   */
  public static function filterBar(string $uid, int $total): string {
    return sprintf('<div class="filter-bar needs-js" data-filter-bar><label class="vh" for="filter-%1$s">Search</label>'
      . '<svg class="icon" aria-hidden="true" focusable="false"><use href="#i-search"/></svg>'
      . '<input id="filter-%1$s" type="search" placeholder="Search" autocomplete="off" spellcheck="false" data-filter-input>'
      . '<output class="filter-count" for="filter-%1$s" aria-hidden="true" data-filter-total>%2$d</output>'
      . '<p class="vh" role="status" aria-atomic="true" data-filter-status><span>Search results</span> <span data-n>%2$d</span></p>'
      . '</div><p class="filter-empty" hidden data-filter-empty>Your search yielded no results.</p>', $uid, $total);
  }

  /**
   * The embeds the live site already uses, made responsive.
   */
  private static function iframes(\DOMDocument $dom, \DOMElement $root, array $ctx): void {
    foreach (self::els($root, 'iframe') as $fr) {
      $kind = NULL;
      foreach (self::classes($fr) as $c) {
        if (str_starts_with($c, 'embed-')) {
          $kind = $c;
          break;
        }
      }
      $src = $fr->getAttribute('src');
      $kind = $kind ?? (str_contains($src, 'forms.office.com') ? 'embed-form' : (str_contains($src, 'calendar.google.com') ? 'embed-calendar'
        : (str_contains($src, 'google.com/maps') ? 'embed-map' : 'embed-video')));
      foreach (['width', 'height', 'class'] as $a) {
        $fr->removeAttribute($a);
      }
      if (Site::clean($fr->getAttribute('title')) === '') {
        $fr->setAttribute('title', $ctx['title']);
      }
      $fr->setAttribute('loading', 'lazy');
      $p = $fr->parentNode;
      $target = (self::tag($p) === 'p' && count(self::elementChildren($p)) === 1 && self::text($p) === '') ? $p : $fr;
      $wrap = self::el($dom, 'div', ['class' => 'embed ' . $kind]);
      $target->parentNode->replaceChild($wrap, $target);
      $wrap->appendChild($fr);
    }
  }

  /**
   * The school's number in running text becomes a tel: link (with the extension when the text gives it).
   */
  private static function phones(\DOMDocument $dom, \DOMElement $root): void {
    $c = Site::contact();
    $d = preg_replace('/\D/', '', $c['phone']);
    if (strlen($d) !== 10) {
      return;
    }
    $re = sprintf('/%s[.\-\s]%s[.\-\s]%s(?:\s*\(\s*(?:Press|Ext\.?)\s*1\s*\)|\s*,?\s*Ext\.?\s*1\b)?/u', substr($d, 0, 3), substr($d, 3, 3), substr($d, 6));
    foreach (self::all($root) as $el) {
      if (in_array(self::tag($el), ['a', 'script', 'style'], TRUE) || self::hasAncestor($el, 'a')) {
        continue;
      }
      foreach (self::children($el) as $ch) {
        if (!$ch instanceof \DOMText || !preg_match_all($re, $ch->nodeValue, $ms, PREG_OFFSET_CAPTURE)) {
          continue;
        }
        $text = $ch->nodeValue;
        $pos = 0;
        foreach ($ms[0] as [$match, $offset]) {
          if ($offset > $pos) {
            $el->insertBefore($dom->createTextNode(substr($text, $pos, $offset - $pos)), $ch);
          }
          $tel = preg_match('/(Press|Ext)/', $match) ? $c['tel_ext'] : $c['tel'];
          $el->insertBefore(self::el($dom, 'a', ['href' => $tel], [$match]), $ch);
          $pos = $offset + strlen($match);
        }
        if ($pos < strlen($text)) {
          $el->insertBefore($dom->createTextNode(substr($text, $pos)), $ch);
        }
        $el->removeChild($ch);
      }
    }
  }

  private static function onlyImage(\DOMElement $cell): bool {
    return count(self::els($cell, 'img')) === 1 && self::text($cell) === '';
  }

  /**
   * Text outside <strong>/<b>: empty means the cell is all bold (a label).
   */
  private static function plainText(\DOMNode $el): string {
    $out = '';
    foreach (self::children($el) as $ch) {
      if ($ch instanceof \DOMText) {
        $out .= $ch->nodeValue;
      }
      elseif ($ch instanceof \DOMElement && !in_array(self::tag($ch), ['strong', 'b'], TRUE)) {
        $out .= self::plainText($ch);
      }
    }
    return Site::clean($out);
  }

  /**
   * Layout tables → the layout they drew; data tables scroll in a focusable wrapper.
   */
  private static function tables(\DOMDocument $dom, \DOMElement $root, array $ctx): void {
    foreach (self::els($root, 'table') as $t) {
      if (!$t->parentNode) {
        continue;
      }
      $rows = self::els($t, 'tr');
      $cells = count($rows) === 1 ? self::elementChildren($rows[0]) : [];
      if (count($rows) === 1 && count($cells) === 2 && (self::onlyImage($cells[0]) || self::onlyImage($cells[1]))) {
        $img_cell = self::onlyImage($cells[0]) ? $cells[0] : $cells[1];
        $text_cell = $img_cell === $cells[0] ? $cells[1] : $cells[0];
        $tels = array_values(array_filter(self::els($text_cell, 'a'), fn($l) => str_starts_with($l->getAttribute('href'), 'tel:')));
        $body = self::adopt(self::el($dom, 'div'), self::children($text_cell));
        if ($tels) {
          $btn = self::el($dom, 'a', ['class' => 'btn', 'href' => $tels[0]->getAttribute('href')]);
          foreach (self::icon($dom, 'phone') as $n) {
            $btn->appendChild($n);
          }
          $btn->appendChild($dom->createTextNode(self::text($tels[0])));
          $body->appendChild($btn);
          $ring = self::el($dom, 'span', ['class' => 'ring', 'aria-hidden' => 'true'], self::icon($dom, 'phone'));
          $node = self::el($dom, 'div', ['class' => 'callout on-dark'], [$ring, $body]);
        }
        else {
          $im = self::els($img_cell, 'img')[0];
          $wide = (int) $im->getAttribute('width') > 200;
          $fig = self::el($dom, 'div', ['class' => 'media-note-img'], [$im]);
          $node = self::el($dom, 'div', ['class' => 'media-note' . ($wide ? ' media-note--wide' : '')], [$fig, $body]);
        }
        $t->parentNode->replaceChild($node, $t);
        continue;
      }
      $flat = self::flattenTable($dom, $t, $rows, $ctx);
      if ($flat !== NULL) {
        self::replace($t, $flat);
        continue;
      }
      $cols = 0;
      foreach ($rows as $r) {
        $cols = max($cols, count(self::elementChildren($r)));
      }
      $wrap = self::el($dom, 'div', ['class' => 'table-wrap' . ($cols >= 5 ? ' is-wide' : ''), 'tabindex' => '0']);
      $t->parentNode->replaceChild($wrap, $t);
      $wrap->appendChild($t);
      if (self::els($t, 'th') && count($rows) >= 20) {
        self::directoryTable($dom, $t, $wrap);
      }
    }
  }

  /**
   * build.py flatten_table(): replacement nodes, or NULL to keep the table.
   */
  private static function flattenTable(\DOMDocument $dom, \DOMElement $t, array $rows, array $ctx): ?array {
    $cells = array_map(fn($r) => self::elementChildren($r), $rows);
    $flat = $cells ? array_merge(...$cells) : [];
    if (!$flat) {
      return [];
    }
    if (!array_filter($flat, fn($c) => self::text($c) !== '' || self::els($c, 'img') || self::els($c, 'iframe'))) {
      return [];
    }
    // one row of links (Student Login) → link tiles
    if (count($rows) === 1 && count($flat) >= 2 && !array_filter($flat, fn($c) => !(count(self::els($c, 'a')) === 1 && self::text($c) !== ''
      && self::text($c) === self::text(self::els($c, 'a')[0])))) {
      $ul = self::el($dom, 'ul', ['class' => 'link-tiles']);
      foreach ($flat as $c) {
        $href = self::els($c, 'a')[0]->getAttribute('href');
        $a = self::el($dom, 'a', ['class' => 'link-tile', 'href' => $href], [self::el($dom, 'span', [], [self::text($c)])]);
        foreach (self::goIcon($dom, $href) as $n) {
          $a->appendChild($n);
        }
        $ul->appendChild(self::el($dom, 'li', [], [$a]));
      }
      return [$ul];
    }
    // image links over a caption row (Extra-Curricular) → feature tiles named after the page they open
    if (count($rows) === 2 && count($cells[0]) === count($cells[1]) && count($cells[0]) >= 2
      && !array_filter($cells[0], fn($c) => !(self::onlyImage($c) && self::els($c, 'a')))) {
      $ul = self::el($dom, 'ul', ['class' => 'feature-tiles']);
      foreach ($cells[0] as $k => $top) {
        $link = self::els($top, 'a')[0];
        $im = self::els($top, 'img')[0];
        $url = $link->getAttribute('href');
        $target = self::targetPath($url);
        $name = $target ? Site::title($target) : '';
        $im->setAttribute('alt', '');
        $body = self::el($dom, 'span', ['class' => 'feature-body'], [
          self::el($dom, 'strong', [], [$name]),
          self::el($dom, 'span', [], [self::text($cells[1][$k])]),
        ]);
        $a = self::el($dom, 'a', ['class' => 'feature-tile', 'href' => $url], [self::el($dom, 'span', ['class' => 'feature-img'], [$im]), $body]);
        foreach (self::goIcon($dom, $url) as $n) {
          $a->appendChild($n);
        }
        $ul->appendChild(self::el($dom, 'li', [], [$a]));
      }
      return [$ul];
    }
    $heads = (bool) (self::els($t, 'th') || self::els($t, 'thead'));
    // bold label | long text rows → stacked label/text blocks
    $pairs = array_values(array_filter($cells, fn($r) => count($r) === 2));
    if (!$heads && $pairs && !array_filter($cells, fn($r) => !in_array(count($r), [1, 2], TRUE))) {
      $firsts = array_map(fn($r) => self::text($r[0]), $pairs);
      $seconds = array_map(fn($r) => self::text($r[1]), $pairs);
      $bold = count(array_filter($pairs, fn($r) => self::plainText($r[0]) === ''));
      $avg = array_sum(array_map('mb_strlen', $seconds)) / count($seconds);
      if (!array_filter($firsts, fn($f) => !(mb_strlen($f) > 0 && mb_strlen($f) <= 120)) && $bold >= max(1, 0.6 * count($pairs)) && $avg > 80) {
        $div = self::el($dom, 'div', ['class' => 'kv']);
        foreach ($cells as $r) {
          if (count($r) === 1) {
            $div->appendChild(self::adopt(self::el($dom, 'div', ['class' => 'kv-full']), self::children($r[0])));
            continue;
          }
          $lab = self::el($dom, 'p', ['class' => 'kv-label'], [self::text($r[0])]);
          $body = self::adopt(self::el($dom, 'div', ['class' => 'kv-body']), self::children($r[1]));
          $div->appendChild(self::el($dom, 'div', ['class' => 'kv-row'], [$lab, $body]));
        }
        return [$div];
      }
    }
    // short lists under bold column headers → one card per column
    $ncol = count($cells[0]);
    $body_cells = $cells ? array_merge(...array_slice($cells, 1) ?: [[]]) : [];
    if ($ncol >= 2 && $ncol <= 4 && count($rows) >= 4 && !array_filter($cells, fn($r) => count($r) !== $ncol)
      && !array_filter($cells[0], fn($c) => !(self::plainText($c) === '' && mb_strlen(self::text($c)) > 0 && mb_strlen(self::text($c)) <= 30))
      && !array_filter($body_cells, fn($c) => mb_strlen(self::text($c)) > 50)
      && count(array_filter($body_cells, fn($c) => self::plainText($c) !== '')) >= 0.6 * count($body_cells)) {
      $wrap = self::el($dom, 'div', ['class' => 'col-lists']);
      for ($j = 0; $j < $ncol; $j++) {
        $ul = self::el($dom, 'ul');
        foreach (array_slice($cells, 1) as $r) {
          if (self::text($r[$j]) !== '') {
            $ul->appendChild(self::el($dom, 'li', [], [self::text($r[$j])]));
          }
        }
        $wrap->appendChild(self::el($dom, 'section', ['class' => 'col-list'], [
          self::el($dom, 'h3', [], [Calendar::smartCase(self::text($cells[0][$j]))]),
          $ul,
        ]));
      }
      return [$wrap];
    }
    return NULL;
  }

  /**
   * A long data table (Club Directory) → searchable, each row a card on phones (labels from the header).
   */
  private static function directoryTable(\DOMDocument $dom, \DOMElement $t, \DOMElement $wrap): void {
    $thead = self::els($t, 'thead');
    $heads = $thead ? array_map(fn($th) => self::text($th), self::els($thead[0], 'th')) : [];
    self::addClass($t, 'data-cards');
    $tbody = self::els($t, 'tbody');
    $n = 0;
    foreach ($tbody ? self::els($tbody[0], 'tr') : [] as $tr) {
      $tr->setAttribute('data-filter-row', '');
      $n++;
      foreach (self::elementChildren($tr) as $i => $td) {
        if ($i < count($heads)) {
          $td->setAttribute('data-label', $heads[$i]);
        }
        if ($i === 0) {
          $th = self::rename($td, 'th');
          $th->setAttribute('scope', 'row');
        }
      }
    }
    $scope = self::el($dom, 'div', ['class' => 'directory', 'data-filter' => '']);
    $wrap->parentNode->replaceChild($scope, $wrap);
    foreach (self::fragment($dom, self::filterBar('directory', $n)) as $node) {
      $scope->appendChild($node);
    }
    $scope->appendChild($wrap);
  }

  // ------------------------------------------------------------------------------------------------- page tweaks

  /**
   * Contact Us: the loose lines before the first block (name, motto, Early Warning, Email) become a card.
   */
  private static function tweakContact(\DOMDocument $dom, \DOMElement $root): void {
    $lead = [];
    foreach (self::children($root) as $ch) {
      if (in_array(self::tag($ch), ['h2', 'h3', 'p', 'div', 'iframe'], TRUE)) {
        break;
      }
      $lead[] = $ch;
    }
    if (!$lead) {
      return;
    }
    $groups = [];
    foreach ($lead as $ch) {
      if (in_array(self::tag($ch), ['strong', 'em'], TRUE) || !$groups) {
        $groups[] = [];
      }
      $groups[count($groups) - 1][] = $ch;
    }
    $card = self::el($dom, 'div', ['class' => 'contact-intro on-dark']);
    $root->insertBefore($card, $lead[0]);
    $lines = 0;
    foreach ($groups as $g) {
      $kids = array_values(array_filter($g, fn($c) => !self::blank($c)));
      $one = count($kids) === 1 ? self::tag($kids[0]) : '';
      $cls = (!$lines && $one === 'strong') ? 'ci-name' : ($one === 'em' ? 'ci-motto' : 'ci-line');
      if ($cls === 'ci-line') {
        $p = self::adopt(self::el($dom, 'p', ['class' => $cls]), $g);
      }
      else {
        $text = Site::clean(implode('', array_map(fn($c) => $c->textContent, $g)));
        foreach ($g as $c) {
          if ($c->parentNode) {
            $c->parentNode->removeChild($c);
          }
        }
        $p = self::el($dom, 'p', ['class' => $cls], [$text]);
      }
      $card->appendChild($p);
      $lines++;
    }
  }

  /**
   * Student Attendance: the bold sentence is the lead, the typed list of what to say becomes numbered steps.
   */
  private static function tweakAttendance(\DOMDocument $dom, \DOMElement $root): void {
    foreach (self::els($root, 'p') as $p) {
      $k = self::kids($p);
      if (count($k) === 1 && self::tag($k[0]) === 'strong' && mb_strlen(self::text($p)) > 40) {
        self::addClass($p, 'lead');
        break;
      }
    }
    foreach (self::els($root, 'p') as $p) {
      if (str_starts_with(mb_strtolower(self::text($p)), 'please provide the following information')) {
        for ($n = $p->nextSibling; $n; $n = $n->nextSibling) {
          if ($n instanceof \DOMElement) {
            if (self::tag($n) === 'ul') {
              $ol = self::rename($n, 'ol');
              self::addClass($ol, 'steps');
            }
            break;
          }
        }
        break;
      }
    }
  }

  /**
   * Strikers Athletics: the team logo leads, on a forest arch plate.
   */
  private static function tweakStrikers(\DOMDocument $dom, \DOMElement $root): void {
    $p = self::els($root, 'p')[0] ?? NULL;
    if ($p) {
      $k = self::kids($p);
      if (count($k) === 1 && self::tag($k[0]) === 'img') {
        $plate = self::el($dom, 'div', ['class' => 'logo-plate', 'aria-hidden' => 'true'], [$k[0]]);
        $p->parentNode->replaceChild($plate, $p);
      }
    }
  }

  /**
   * Library Learning Commons: the banner reel, then Library Events, About Us, Newsletter Archive and Social Media as
   * cards. Applied only when the body holds those four sections.
   */
  private static function tweakLibrary(\DOMDocument $dom, \DOMElement $root, array $ctx): void {
    $kids = self::elementChildren($root);
    $reel = NULL;
    $secs = [];
    $cur = NULL;
    foreach ($kids as $c) {
      if (!$reel && in_array('reel', self::classes($c), TRUE)) {
        $reel = $c;
      }
      if (self::tag($c) === 'h2') {
        $cur = self::text($c);
        $secs[$cur] = [];
      }
      elseif ($cur !== NULL) {
        $secs[$cur][] = $c;
      }
    }
    foreach (['Library Events', 'About Us', 'Newsletter Archive', 'Social Media'] as $need) {
      if (!isset($secs[$need])) {
        return;
      }
    }
    $icon = fn($n) => sprintf('<svg class="icon" aria-hidden="true" focusable="false"><use href="#i-%s"/></svg>', $n);
    $rows = [];
    $roles = [];
    foreach ($secs['About Us'] as $n) {
      if (self::tag($n) === 'h3') {
        $roles[] = self::text($n);
      }
      elseif (self::tag($n) === 'p') {
        $rows[] = [$roles, self::text($n)];
        $roles = [];
      }
    }
    $about = '';
    foreach ($rows as [$r, $v]) {
      $hours = $r === ['Hours'];
      $about .= sprintf('<div class="llc-person%s">%s<dt>%s</dt><dd>%s</dd></div>', $hours ? ' is-hours' : '', $icon($hours ? 'clock' : 'people'),
        implode(' ', array_map(fn($x) => '<span>' . Html::escape($x) . '</span>', $r)), Html::escape($v));
    }
    $nl = '';
    foreach ($secs['Newsletter Archive'] as $n) {
      foreach (self::els($n, 'a') as $link) {
        $im = self::els($link, 'img');
        $img_html = '';
        if ($im) {
          $im[0]->setAttribute('alt', '');
          $img_html = $dom->saveHTML($im[0]);
        }
        $target = self::targetPath($link->getAttribute('href'));
        $nl = sprintf('<a class="llc-tile" href="%s"><span class="llc-tile-img">%s</span><span>%s</span>%s</a>', Html::escape($link->getAttribute('href')),
          $img_html, Html::escape($target ? Site::title($target) : ''), str_replace('class="icon"', 'class="icon tile-go"', $icon('arrow')));
      }
    }
    $social = '';
    foreach ($secs['Social Media'] as $n) {
      foreach (self::tag($n) === 'a' ? [$n] : self::els($n, 'a') as $link) {
        $label = str_replace(['/', '?'], ['/<wbr>', '<wbr>?'], Html::escape(self::text($link)));
        $social = sprintf('<a class="llc-social" href="%s"><span class="ring">%s</span><span>%s</span></a>', Html::escape($link->getAttribute('href')), $icon('insta'), $label);
      }
    }
    $events = implode('', array_map(fn($n) => $dom->saveHTML($n), $secs['Library Events']));
    $html = sprintf('<div class="llc"><section class="llc-card llc-events"><h2>Library Events</h2>%s</section>'
      . '<section class="llc-card llc-about on-dark"><h2>About Us</h2><dl>%s</dl></section>'
      . '<section class="llc-card"><h2>Newsletter Archive</h2>%s</section>'
      . '<section class="llc-card"><h2>Social Media</h2>%s</section></div>', $events, $about, $nl, $social);
    $nodes = self::fragment($dom, $html);
    foreach (self::children($root) as $c) {
      if ($c !== $reel) {
        $root->removeChild($c);
      }
    }
    foreach ($nodes as $n) {
      $root->appendChild($n);
    }
  }

  // ------------------------------------------------------------------------------------------------- hub support

  /**
   * Paths and URLs a body shows as tiles (feature, launch and link tiles), so the hub cards do not repeat them
   * (build.py tiled_urls()). Runs the same layout detection on the raw body.
   */
  public static function tiledUrls(string $raw, string $path, string $title): array {
    if (trim($raw) === '') {
      return [];
    }
    $html = self::transform($raw, ['path' => $path, 'title' => $title, 'node_body' => FALSE, 'bell' => '', 'scope' => 'tiles:' . $path]);
    $out = [];
    if (preg_match_all('/<a\b[^>]*>/', $html, $m)) {
      foreach ($m[0] as $tag) {
        if (preg_match('/class="[^"]*\b(feature-tile|launch-tile|link-tile)\b/', $tag) && preg_match('/href="([^"]+)"/', $tag, $h)) {
          $href = html_entity_decode($h[1], ENT_QUOTES | ENT_HTML5, 'UTF-8');
          $out[] = $href;
          if ($p = self::targetPath($href)) {
            $out[] = $p;
          }
        }
      }
    }
    unset(self::$used['tiles:' . $path]);
    return array_values(array_unique($out));
  }

}
