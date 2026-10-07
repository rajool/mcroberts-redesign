<?php

namespace Drupal\mcroberts;

use Drupal\Component\Utility\Html;
use Drupal\node\NodeInterface;

/**
 * Card lines, teasers and news items for the McRoberts theme.
 *
 * Ports of build.py first_sentence(), section_sentence(), lead_is_subsection(), card_desc(), teaser_text(),
 * news_card() and the Striker Weekly helpers. Every line is cut from the page's own words: nothing is written here.
 */
final class Teaser {

  /**
   * A <br> inside a card line, kept apart so the card can show the lines as lines.
   */
  public const LINE = "\u{2028}";

  /**
   * Per-request memo.
   *
   * @var array
   */
  private static array $memo = [];

  /**
   * data/tiles.json: the picture each tile shows (path → file, size, logo/icon flags).
   */
  public static function tileImages(): array {
    if (!isset(self::$memo['tiles'])) {
      $file = \Drupal::service('extension.list.theme')->getPath('mcroberts') . '/data/tiles.json';
      $data = is_readable($file) ? json_decode(file_get_contents($file), TRUE) : NULL;
      self::$memo['tiles'] = is_array($data) ? $data : [];
    }
    return self::$memo['tiles'];
  }

  /**
   * The text of a node; <br> becomes $br.
   */
  public static function textOf(\DOMNode $node, string $br = ' '): string {
    $out = '';
    foreach ($node->childNodes as $child) {
      if ($child instanceof \DOMText) {
        $out .= $child->nodeValue;
      }
      elseif ($child instanceof \DOMElement) {
        $out .= strtolower($child->tagName) === 'br' ? $br : self::textOf($child, $br);
      }
    }
    return $out;
  }

  /**
   * Element children and non-blank text children.
   */
  private static function kids(\DOMNode $el): array {
    $out = [];
    foreach ($el->childNodes as $c) {
      if ($c instanceof \DOMText && trim($c->nodeValue, " \t\n\r\0\x0B\u{00A0}") === '') {
        continue;
      }
      if ($c instanceof \DOMElement || $c instanceof \DOMText) {
        $out[] = $c;
      }
    }
    return $out;
  }

  /**
   * build.py first_sentence(): the first sentence of the first real paragraph or list item.
   */
  public static function firstSentence(string $html, int $limit = 170, string $br = ' '): string {
    if (trim($html) === '') {
      return '';
    }
    $dom = Html::load($html);
    $xpath = new \DOMXPath($dom);
    foreach ($xpath->query('//body//p | //body//li') as $el) {
      $t = preg_replace('/[ \t\r\n\x{00A0}\x{FEFF}]+/u', ' ', self::textOf($el, $br));
      $t = trim($t);
      $t = preg_replace('/ ?\x{2028} ?/u', self::LINE, $t);
      $t = preg_replace('/^\x{2028}+|\x{2028}+$/u', '', $t);
      $kids = self::kids($el);
      if (mb_strlen($t) < 50 || ($kids && $kids[0] instanceof \DOMElement && strtolower($kids[0]->tagName) === 'a')) {
        continue;
      }
      $s = preg_match('/^(.+?[.!?])(?=\s+[A-Z(“"]|\s*$)/u', $t, $m) ? $m[1] : $t;
      if (mb_strlen($s) > $limit) {
        $s = mb_substr($s, 0, $limit);
        $cut = mb_strrpos($s, ' ');
        if ($cut !== FALSE) {
          $s = mb_substr($s, 0, $cut);
        }
        $s = preg_replace('/[,;:\-–— ]+$/u', '', $s) . '…';
      }
      return $s;
    }
    return '';
  }

  /**
   * build.py section_sentence(): a card's line, for a deep link the first sentence under that heading.
   */
  public static function sectionSentence(string $path, string $frag = ''): string {
    $body = Site::body($path);
    if ($frag !== '' && $body !== '') {
      $dom = Html::load($body);
      $xpath = new \DOMXPath($dom);
      foreach ($xpath->query('//body//h2 | //body//h3 | //body//h4 | //body//h5 | //body//h6') as $h) {
        if (Site::slug($h->textContent) !== $frag || !$h->parentNode) {
          continue;
        }
        $level = (int) substr(strtolower($h->tagName), 1);
        $part = '';
        for ($x = $h->nextSibling; $x; $x = $x->nextSibling) {
          if ($x instanceof \DOMElement && preg_match('/^h([2-6])$/', strtolower($x->tagName), $m) && (int) $m[1] <= $level) {
            break;
          }
          $part .= $dom->saveHTML($x);
        }
        return self::firstSentence($part, 170, self::LINE);
      }
    }
    return self::firstSentence($body, 170, self::LINE);
  }

  /**
   * build.py lead_is_subsection(): the page's first sentence sits under one of its own sub-headings.
   */
  public static function leadIsSubsection(string $path): bool {
    $body = Site::body($path);
    if ($body === '') {
      return FALSE;
    }
    $xpath = new \DOMXPath(Html::load($body));
    foreach ($xpath->query('//body//*') as $el) {
      $tag = strtolower($el->tagName);
      if (preg_match('/^h[2-6]$/', $tag)) {
        return TRUE;
      }
      if (($tag === 'p' || $tag === 'li') && mb_strlen(Site::clean($el->textContent)) >= 50) {
        return FALSE;
      }
    }
    return FALSE;
  }

  /**
   * build.py card_desc(): the line under a card's title.
   */
  public static function cardDesc(array $link): string {
    if ($link['path'] === NULL || !Site::entityAt($link['path'])) {
      return '';
    }
    $target = $link['path'];
    $desc = self::sectionSentence($target, $link['fragment']);
    if ($desc !== '' && $link['fragment'] === '' && self::leadIsSubsection($target) && $link['label'] !== Site::title($target)) {
      $desc = Site::title($target);
    }
    return $desc;
  }

  /**
   * A spaced hyphen stays on the line of the word before it (no line starts with "-").
   */
  public static function keepDash(string $t): string {
    return str_replace(' - ', "\u{00A0}- ", $t);
  }

  /**
   * A hub card: title, its line (one or more lines), arrow (or the calendar icon for the feed).
   */
  public static function card(array $link, string $title): array {
    $desc = self::cardDesc($link);
    return [
      'url' => $link['url'],
      'title' => self::keepDash($title),
      'desc' => str_replace(self::LINE, ' ', $desc),
      'lines' => str_contains($desc, self::LINE) ? explode(self::LINE, $desc) : [],
      'webcal' => str_starts_with($link['url'], 'webcal:'),
    ];
  }

  /**
   * build.py teaser_text(): a teaser Drupal trimmed mid-phrase gets an ellipsis (punctuation only).
   */
  public static function teaserText(string $t): string {
    $t = Site::clean($t);
    if ($t === '') {
      return $t;
    }
    $last = mb_substr($t, -1);
    return in_array($last, ['.', '!', '?', '…', ':', ')', '"', '”', '’'], TRUE) ? $t : $t . '…';
  }

  /**
   * A node's teaser text: its body summary, else the trimmed body, as plain text.
   */
  public static function summary(NodeInterface $node, int $length = 300): string {
    if (!$node->hasField('body') || $node->get('body')->isEmpty()) {
      return '';
    }
    $item = $node->get('body')->first();
    $text = trim((string) ($item->summary ?? ''));
    if ($text === '') {
      $text = function_exists('text_summary') ? text_summary((string) $item->value, $item->format, $length) : mb_substr((string) $item->value, 0, $length);
    }
    return Site::clean(html_entity_decode(strip_tags(str_replace(['<br>', '<br/>', '<br />', '</p>'], ' ', $text)), ENT_QUOTES | ENT_HTML5, 'UTF-8'));
  }

  /**
   * True for a Striker Weekly newsletter post.
   */
  public static function isWeekly(string $title): bool {
    return str_starts_with(mb_strtolower(Site::clean($title)), 'striker weekly');
  }

  /**
   * "Striker Weekly: Oct 5 to 9" → "Oct 5 to 9".
   */
  public static function weeklyRange(string $title): string {
    $parts = explode(':', Site::clean($title), 2);
    return trim(end($parts));
  }

  /**
   * An article as a news item: title, url, date parts (created), teaser, weekly flag.
   */
  public static function newsItem(NodeInterface $node): array {
    $title = Site::clean($node->label());
    $iso = Calendar::isoOf((int) $node->getCreatedTime());
    return [
      'nid' => (int) $node->id(),
      'title' => $title,
      'url' => $node->toUrl()->toString(),
      'date' => Calendar::parts($iso),
      'teaser' => self::teaserText(self::summary($node)),
      'weekly' => self::isWeekly($title),
      'range' => self::weeklyRange($title),
      'newsletter' => self::isWeekly($title),
    ];
  }

  /**
   * The latest published Striker Weekly posts, newest first.
   */
  public static function weeklies(int $count = 3): array {
    $key = 'weeklies:' . $count;
    if (isset(self::$memo[$key])) {
      return self::$memo[$key];
    }
    $storage = \Drupal::entityTypeManager()->getStorage('node');
    $ids = $storage->getQuery()->accessCheck(TRUE)->condition('type', 'article')->condition('status', 1)
      ->condition('title', 'Striker Weekly', 'STARTS_WITH')->sort('created', 'DESC')->range(0, $count)->execute();
    return self::$memo[$key] = array_values(array_map([self::class, 'newsItem'], $storage->loadMultiple($ids)));
  }

  /**
   * The latest published articles (not Striker Weekly), newest first.
   */
  public static function latest(int $count, ?int $except = NULL): array {
    $storage = \Drupal::entityTypeManager()->getStorage('node');
    $query = $storage->getQuery()->accessCheck(TRUE)->condition('type', 'article')->condition('status', 1)
      ->sort('created', 'DESC')->range(0, $count + 1);
    if ($except) {
      $query->condition('nid', $except, '<>');
    }
    $items = array_values(array_map([self::class, 'newsItem'], $storage->loadMultiple($query->execute())));
    return array_slice($items, 0, $count);
  }

  /**
   * The article published before and after this one (by created time).
   */
  public static function neighbours(NodeInterface $node): array {
    $storage = \Drupal::entityTypeManager()->getStorage('node');
    $out = [];
    foreach (['prev' => ['<', 'DESC'], 'next' => ['>', 'ASC']] as $key => [$op, $dir]) {
      $ids = $storage->getQuery()->accessCheck(TRUE)->condition('type', $node->bundle())->condition('status', 1)
        ->condition('created', $node->getCreatedTime(), $op)->sort('created', $dir)->range(0, 1)->execute();
      $out[$key] = $ids ? self::newsItem($storage->load(reset($ids))) : NULL;
    }
    return $out;
  }

  /**
   * Items grouped by month, newest month first: [{id, label, items}].
   */
  public static function byMonth(array $items): array {
    $groups = [];
    foreach ($items as $it) {
      $ym = sprintf('%d-%02d', $it['date']['y'], array_search($it['date']['m'], Calendar::MONTHS, TRUE) + 1);
      if (!$groups || $groups[count($groups) - 1]['ym'] !== $ym) {
        $groups[] = ['ym' => $ym, 'id' => 'm-' . $ym, 'label' => $it['date']['month_year'], 'items' => []];
      }
      $groups[count($groups) - 1]['items'][] = $it;
    }
    return $groups;
  }

}
