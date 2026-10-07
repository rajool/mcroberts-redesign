/**
 * @file
 * McRoberts: Drupal bridge, part 2 (loads right after js/behaviors.js).
 *
 * McR.once() now hands the marking to core/once (both use the data-once attribute, so nothing is bound twice), and
 * the preview's own page-load run of every feature stands down: Drupal.attachBehaviors() runs them instead.
 */
((Drupal, once, window) => {
  const McR = window.McR;
  McR.once = (id, selector, context) => {
    const root = context || document;
    const elements = [];
    if (root.nodeType === 1 && root.matches(selector)) {
      elements.push(root);
    }
    root.querySelectorAll(selector).forEach((element) => elements.push(element));
    return once(id, elements);
  };
  McR.attachBehaviors = () => {};
})(Drupal, once, window);
