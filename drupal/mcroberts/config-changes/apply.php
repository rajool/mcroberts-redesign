<?php

/**
 * @file
 * Applies the McRoberts information architecture (design/ia.json) to a Drupal 10 site as configuration.
 *
 * What it changes (nothing in any node body):
 *   1. URL aliases: each page in urls.md gets its new alias; the Redirect module answers the old one with a 301.
 *   2. Retired pages: their old URLs redirect (with --retire, the 5 nodes are also unpublished and lose their alias,
 *      so the redirect answers).
 *   3. Menus: main gets the 7-item tree (the live links are disabled, not deleted); utility, footer and hub-links
 *      are created and filled.
 *   4. Blocks of the mcroberts theme (after `drush theme:install mcroberts`): see blocks.md.
 *
 * Every change is logged in the state key mcroberts_ia.log, so --rollback can undo it.
 *
 * Usage, on a staging copy first:
 *   drush php:script themes/custom/mcroberts/config-changes/apply.php                     # dry run (prints the plan)
 *   drush php:script themes/custom/mcroberts/config-changes/apply.php -- --apply          # applies 1, 3, 4 and the
 *                                                                                          # redirects of 2
 *   drush php:script themes/custom/mcroberts/config-changes/apply.php -- --apply --retire # also retires the 5 pages
 *   drush php:script themes/custom/mcroberts/config-changes/apply.php -- --rollback       # undoes what was logged
 *
 * Paths are relative to the Drupal root (web/). Status: written against the Drupal 10.3+ APIs, not run on a live
 * Drupal instance yet.
 */

if (PHP_SAPI !== 'cli') {
  exit;
}

use Drupal\block\Entity\Block;
use Drupal\Core\Language\LanguageInterface;
use Drupal\menu_link_content\Entity\MenuLinkContent;
use Drupal\path_alias\Entity\PathAlias;
use Drupal\system\Entity\Menu;

$args = isset($extra) && is_array($extra) ? $extra : [];
$apply = in_array('--apply', $args, TRUE);
$retire = in_array('--retire', $args, TRUE);
$rollback = in_array('--rollback', $args, TRUE);
$data = require __DIR__ . '/ia-data.php';
$state = \Drupal::state();
$log = $state->get('mcroberts_ia.log', []);
$etm = \Drupal::entityTypeManager();
$aliases = \Drupal::service('path_alias.manager');
$has_redirect = \Drupal::moduleHandler()->moduleExists('redirect');

$say = function (string $line) {
  print $line . PHP_EOL;
};

// ----------------------------------------------------------------------------------------------- rollback
if ($rollback) {
  foreach (array_reverse($log) as $entry) {
    switch ($entry['op']) {
      case 'alias':
        if ($alias = PathAlias::load($entry['id'])) {
          $alias->setAlias($entry['old'])->save();
          $say("alias restored: {$entry['old']}");
        }
        // the Redirect module's own redirect from the old alias (auto_redirect) would now point at itself
        if (\Drupal::moduleHandler()->moduleExists('redirect')) {
          $storage = $etm->getStorage('redirect');
          $ids = $storage->getQuery()->accessCheck(FALSE)->condition('redirect_source.path', ltrim($entry['old'], '/'))->execute();
          foreach ($storage->loadMultiple($ids) as $redirect) {
            $redirect->delete();
          }
        }
        break;

      case 'alias_new':
      case 'redirect':
      case 'menu_link':
        $type = ['alias_new' => 'path_alias', 'redirect' => 'redirect', 'menu_link' => 'menu_link_content'][$entry['op']];
        if ($e = $etm->getStorage($type)->load($entry['id'])) {
          $e->delete();
          $say("removed {$type} {$entry['id']}");
        }
        break;

      case 'alias_removed':
        PathAlias::create(['path' => $entry['path'], 'alias' => $entry['alias'], 'langcode' => $entry['langcode']])->save();
        $say("alias recreated: {$entry['alias']}");
        break;

      case 'unpublished':
        if ($node = $etm->getStorage('node')->load($entry['id'])) {
          $node->setPublished()->save();
          $say("republished node {$entry['id']}");
        }
        break;

      case 'link_disabled':
        \Drupal::service('plugin.manager.menu.link')->updateDefinition($entry['id'], ['enabled' => 1]);
        $say("re-enabled menu link {$entry['id']}");
        break;

      case 'menu':
        if ($menu = Menu::load($entry['id'])) {
          $menu->delete();
          $say("removed menu {$entry['id']}");
        }
        break;

      case 'block':
        if ($block = Block::load($entry['id'])) {
          if (!empty($entry['created'])) {
            $block->delete();
            $say("removed block {$entry['id']}");
            break;
          }
          $block->setRegion($entry['region']);
          $entry['status'] ? $block->enable() : $block->disable();
          foreach ($entry['visibility'] as $condition => $config) {
            $block->setVisibilityConfig($condition, $config);
          }
          foreach ($entry['settings'] as $key => $value) {
            $block->getPlugin()->setConfigurationValue($key, $value);
          }
          $block->save();
          $say("block restored: {$entry['id']}");
        }
        break;
    }
  }
  $state->delete('mcroberts_ia.log');
  $say('Rollback done. Switch the default theme back with: drush config:set system.theme default rsd_sites_barrio');
  return;
}

if (!$apply) {
  $say('DRY RUN: nothing is saved. Add -- --apply to apply.');
}

/**
 * The system path behind an alias or a system path ("/node/12"), or NULL.
 */
$system_of = function (string $path) use ($aliases): ?string {
  if (preg_match('~^/(node|media)/\d+$~', $path)) {
    return $path;
  }
  $system = $aliases->getPathByAlias($path);
  return $system !== $path ? $system : NULL;
};

/**
 * Makes sure the Redirect module answers $source (a path) with a 301 to $system (a system path).
 */
$ensure_redirect = function (string $source, string $system) use ($etm, $has_redirect, $apply, &$log, $say) {
  if (!$has_redirect) {
    $say("  no Redirect module: keep {$source} as a second alias of {$system} instead");
    return;
  }
  $storage = $etm->getStorage('redirect');
  $found = $storage->getQuery()->accessCheck(FALSE)->condition('redirect_source.path', ltrim($source, '/'))->execute();
  if ($found) {
    $say("  redirect exists: {$source}");
    return;
  }
  $say("  redirect {$source} → {$system} (301)");
  if ($apply) {
    $redirect = $storage->create();
    $redirect->setSource(ltrim($source, '/'));
    $redirect->setRedirect($system);
    $redirect->setStatusCode(301);
    $redirect->setLanguage(LanguageInterface::LANGCODE_NOT_SPECIFIED);
    $redirect->save();
    $log[] = ['op' => 'redirect', 'id' => $redirect->id()];
  }
};

// ----------------------------------------------------------------------------------------------- 1. aliases
$say('1. URL aliases (' . count($data['aliases']) . ')');
$alias_storage = $etm->getStorage('path_alias');
foreach ($data['aliases'] as $row) {
  $old = $row['old'];
  $new = $row['new'];
  $taken = $alias_storage->loadByProperties(['alias' => $new]);
  $existing = $alias_storage->loadByProperties(['alias' => $old]);
  if ($existing) {
    $alias = reset($existing);
    $system = $alias->getPath();
    if ($taken) {
      $say("  skip {$old}: {$new} is already an alias");
      continue;
    }
    $say("  {$old} → {$new} ({$system})");
    if ($apply) {
      $alias->setAlias($new)->save();
      $log[] = ['op' => 'alias', 'id' => $alias->id(), 'old' => $old];
    }
    $ensure_redirect($old, $system);
  }
  elseif (preg_match('~^/(node|media)/\d+$~', $old)) {
    // a system path with no alias yet (/node/1813, /media/1069): it gets one; the Redirect module's route
    // normalizer sends the system path to it
    if ($taken) {
      $say("  skip {$old}: {$new} is already an alias");
      continue;
    }
    $say("  {$old}: new alias {$new}");
    if ($apply) {
      $alias = PathAlias::create(['path' => $old, 'alias' => $new, 'langcode' => \Drupal::languageManager()->getDefaultLanguage()->getId()]);
      $alias->save();
      $log[] = ['op' => 'alias_new', 'id' => $alias->id()];
    }
  }
  else {
    $say("  NOT FOUND {$old} (no such alias on this site)");
  }
}

// ----------------------------------------------------------------------------------------------- 2. retired pages
$say('2. Retired pages (' . count($data['retired']) . ')' . ($retire ? '' : ': redirects only; --retire also unpublishes'));
foreach ($data['retired'] as $row) {
  $old_system = $system_of($row['old']);
  $target = $system_of($row['new']);
  if (!$target) {
    $say("  NOT FOUND target {$row['new']} for {$row['old']}");
    continue;
  }
  if ($retire && $old_system && preg_match('~^/node/(\d+)$~', $old_system, $m)) {
    $node = $etm->getStorage('node')->load($m[1]);
    $say("  unpublish node {$m[1]} ({$row['old']}) and remove its alias");
    if ($apply && $node) {
      if ($node->isPublished()) {
        $node->setUnpublished()->save();
        $log[] = ['op' => 'unpublished', 'id' => $node->id()];
      }
      foreach ($alias_storage->loadByProperties(['alias' => $row['old']]) as $alias) {
        $log[] = ['op' => 'alias_removed', 'path' => $alias->getPath(), 'alias' => $alias->getAlias(), 'langcode' => $alias->language()->getId()];
        $alias->delete();
      }
    }
  }
  $ensure_redirect($row['old'], $target);
}

// ----------------------------------------------------------------------------------------------- 3. menus
$say('3. Menus');
$labels = [
  'utility' => ['Utility', 'Student Absent? and its number, the sign-ins, Contact Us (the district strip, the phone bar).'],
  'footer' => ['Footer', 'The three footer columns.'],
  'hub-links' => ['Hub links', 'The cards of the hubs that are not a main-menu panel (home task band, Grad, Program Planning …).'],
];
foreach ($labels as $id => [$label, $description]) {
  if (!Menu::load($id)) {
    $say("  create menu {$id}");
    if ($apply) {
      Menu::create(['id' => $id, 'label' => $label, 'description' => $description])->save();
      $log[] = ['op' => 'menu', 'id' => $id];
    }
  }
}

/**
 * A link value of ia-data.php → a link field URI (+ options).
 */
$link_of = function (string $link) use ($system_of, $say): array {
  if (str_starts_with($link, 'route:')) {
    return ['uri' => $link === 'route:<front>' ? 'internal:/' : $link, 'options' => []];
  }
  if (!str_starts_with($link, '/')) {
    return ['uri' => $link, 'options' => []];
  }
  [$path, $fragment] = array_pad(explode('#', $link, 2), 2, '');
  $system = $system_of($path);
  $options = $fragment !== '' ? ['fragment' => $fragment] : [];
  if ($system && preg_match('~^/(node|media)/(\d+)$~', $system, $m)) {
    return ['uri' => "entity:{$m[1]}/{$m[2]}", 'options' => $options];
  }
  $say("  (no page at {$path}: kept as internal:{$path})");
  return ['uri' => 'internal:' . $path, 'options' => $options];
};

$create_links = function (string $menu, array $items, string $parent = '') use (&$create_links, $link_of, $apply, &$log, $say) {
  foreach (array_values($items) as $weight => $item) {
    $link = $link_of($item['link']);
    $say(sprintf('  %s%s %s [%s]', $menu, $parent ? '  ' : ':', $item['title'], $link['uri']));
    $parent_id = '';
    if ($apply) {
      $entity = MenuLinkContent::create([
        'title' => $item['title'],
        'menu_name' => $menu,
        'link' => $link,
        'parent' => $parent,
        'weight' => $weight,
        'expanded' => !empty($item['children']),
        'enabled' => TRUE,
      ]);
      $entity->save();
      $log[] = ['op' => 'menu_link', 'id' => $entity->id()];
      $parent_id = $entity->getPluginId();
    }
    if (!empty($item['children'])) {
      $create_links($menu, $item['children'], $parent_id);
    }
  }
};

// menu main: the live links are disabled (kept, so a rollback restores the live menu exactly)
$manager = \Drupal::service('plugin.manager.menu.link');
$tree = \Drupal::menuTree()->load('main', new \Drupal\Core\Menu\MenuTreeParameters());
$walk = function (array $tree) use (&$walk) {
  $ids = [];
  foreach ($tree as $element) {
    if ($element->link->isEnabled()) {
      $ids[] = $element->link->getPluginId();
    }
    $ids = array_merge($ids, $walk($element->subtree));
  }
  return $ids;
};
$live = $walk($tree);
$say('  menu main: disable ' . count($live) . ' live links');
if ($apply) {
  foreach ($live as $plugin_id) {
    $manager->updateDefinition($plugin_id, ['enabled' => 0]);
    $log[] = ['op' => 'link_disabled', 'id' => $plugin_id];
  }
}
foreach ($data['menus'] as $menu => $items) {
  $create_links($menu, $items);
}

// ----------------------------------------------------------------------------------------------- 4. blocks
$say('4. Blocks of the mcroberts theme');
$blocks = $etm->getStorage('block');
$theme_blocks = $blocks->loadByProperties(['theme' => 'mcroberts']);
if (!$theme_blocks) {
  $say('  the mcroberts theme has no blocks yet: run `drush theme:install mcroberts` while rsd_sites_barrio is the default, then re-run');
}
$find = function (string $plugin, ?string $region = NULL) use ($theme_blocks) {
  foreach ($theme_blocks as $block) {
    if (($block->getPluginId() === $plugin || str_starts_with($block->getPluginId(), $plugin)) && ($region === NULL || $block->getRegion() === $region)) {
      return $block;
    }
  }
  return NULL;
};
$change = function ($block, array $do) use ($apply, &$log, $say) {
  if (!$block) {
    return;
  }
  $say('  ' . $block->id() . ': ' . implode(', ', array_keys($do)));
  if (!$apply) {
    return;
  }
  $entry = ['op' => 'block', 'id' => $block->id(), 'region' => $block->getRegion(), 'status' => $block->status(), 'visibility' => $block->getVisibility(), 'settings' => []];
  if (isset($do['region'])) {
    $block->setRegion($do['region']);
  }
  if (isset($do['disable'])) {
    $block->disable();
  }
  if (isset($do['all pages'])) {
    $block->getVisibilityConditions()->removeInstanceId('request_path');
  }
  foreach ($do['settings'] ?? [] as $key => $value) {
    $entry['settings'][$key] = $block->getPlugin()->getConfiguration()[$key] ?? NULL;
    $block->getPlugin()->setConfigurationValue($key, $value);
  }
  $block->save();
  $log[] = $entry;
};
$change($find('system_menu_block:main', 'primary_menu'), ['settings' => ['level' => 1, 'depth' => 0, 'expand_all_items' => TRUE]]);
$change($find('system_menu_block:main', 'footer_third'), ['disable' => TRUE]);
$change($find('system_menu_block:account'), ['disable' => TRUE]);
$change($find('block_content:', 'footer_fourth'), ['disable' => TRUE]);
$change($find('gtranslate_block'), ['disable' => TRUE]);
$change($find('search_form_block'), ['disable' => TRUE]);
$change($find('views_block:sidebar_notes-block_1'), ['disable' => TRUE]);
$change($find('views_block:sidebar_notes-block_3'), ['disable' => TRUE]);
$change($find('social_media_links_block'), ['region' => 'footer_second', 'all pages' => TRUE]);
$change($find('a11y_block'), ['all pages' => TRUE]);
foreach ([
  'mcroberts_utility' => ['system_menu_block:utility', 'secondary_menu', 'Utility', 1],
  'mcroberts_footer' => ['system_menu_block:footer', 'footer_first', 'Footer', 2],
] as $id => [$plugin, $region, $label, $depth]) {
  if (!$theme_blocks || Block::load($id)) {
    continue;
  }
  $say("  create {$id}: {$plugin} in {$region}");
  if ($apply) {
    Block::create([
      'id' => $id,
      'theme' => 'mcroberts',
      'region' => $region,
      'weight' => 0,
      'plugin' => $plugin,
      'settings' => [
        'id' => $plugin,
        'label' => $label,
        'label_display' => '0',
        'provider' => 'system',
        'level' => 1,
        'depth' => $depth,
        'expand_all_items' => TRUE,
      ],
      'visibility' => [],
    ])->save();
    $log[] = ['op' => 'block', 'id' => $id, 'created' => TRUE];
  }
}

if ($apply) {
  $state->set('mcroberts_ia.log', $log);
  $say('Done. ' . count($log) . ' changes logged (state mcroberts_ia.log); -- --rollback undoes them.');
  $say('Then: drush config:set system.theme default mcroberts && drush cache:rebuild');
}
