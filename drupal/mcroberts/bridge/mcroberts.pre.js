/**
 * @file
 * McRoberts: Drupal bridge, part 1 (loads before js/behaviors.js).
 *
 * The theme's scripts in js/ are byte-for-byte the static preview's. Each registers its feature as
 * McR.behaviors.<name> = { attach(context) { … } }, binding elements through McR.once(). Here every such
 * registration also becomes a Drupal behavior, Drupal.behaviors.mcroberts<Name>, so Drupal attaches each feature on
 * page load and again on every AJAX insert, with the context it passes. No jQuery.
 */
((Drupal, window) => {
  const McR = window.McR || {};
  window.McR = McR;
  const behaviorName = (key) => `mcroberts${key.charAt(0).toUpperCase()}${key.slice(1)}`;
  McR.behaviors = new Proxy({}, {
    set(target, key, behavior) {
      target[key] = behavior;
      if (typeof key === 'string' && behavior && typeof behavior.attach === 'function') {
        Drupal.behaviors[behaviorName(key)] = {
          attach(context) {
            behavior.attach(context || document);
          },
        };
      }
      return true;
    },
  });
  McR.drupal = true;
})(Drupal, window);
