/* McRoberts theme: client-side filter for long tables and lists (Our Staff, Club Directory).
   Markup from the build: [data-filter] scope, a [data-filter-bar] (.needs-js: shown only with JS) with the input, rows [data-filter-row],
   optional groups [data-filter-group="id"] with their counts [data-filter-group-n="id"], a visible total and a
   polite status for screen readers, and a visible "no results" line when nothing matches. Every word typed must start a word of the row (accents, case and
   punctuation ignored), so "Ms. K" finds Ms. K Brodie and not Ms. B Fackler.
   Drupal: Drupal.behaviors.mcrobertsFilter on the staff paragraphs and on any table the editor marks. */
(function () {
  'use strict';
  var McR = window.McR;
  var fold = function (s) {
    return String(s).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  };

  McR.behaviors.filter = {
    attach: function (context) {
      McR.once('mcr-filter', '[data-filter]', context).forEach(function (scope) {
        var bar = scope.querySelector('[data-filter-bar]');
        var input = scope.querySelector('[data-filter-input]');
        if (!bar || !input) return;
        // a row's text is its cells joined by spaces (textContent runs "Leslie" and "Principal" together)
        var rows = Array.prototype.slice.call(scope.querySelectorAll('[data-filter-row]')).map(function (el) {
          var cells = el.querySelectorAll('th, td');
          var text = cells.length ? Array.prototype.map.call(cells, function (c) { return c.textContent; }).join(' ') : el.textContent;
          return { el: el, text: ' ' + fold(text), group: el.closest('[data-filter-group]') };
        });
        var empty = scope.querySelector('[data-filter-empty]');
        var groups = Array.prototype.slice.call(scope.querySelectorAll('[data-filter-group]'));
        var total = scope.querySelector('[data-filter-total]');
        var status = scope.querySelector('[data-filter-status] [data-n]');
        var timer = null;

        var apply = function () {
          var terms = fold(input.value).split(' ').filter(Boolean);
          var shown = 0, perGroup = {};
          rows.forEach(function (r) {
            var ok = terms.every(function (t) { return r.text.indexOf(' ' + t) !== -1; });
            r.el.hidden = !ok;
            if (ok) {
              shown++;
              if (r.group) perGroup[r.group.getAttribute('data-filter-group')] = (perGroup[r.group.getAttribute('data-filter-group')] || 0) + 1;
            }
          });
          groups.forEach(function (g) {
            var id = g.getAttribute('data-filter-group'), n = perGroup[id] || 0;
            g.hidden = n === 0;
            document.querySelectorAll('[data-filter-group-n="' + id + '"]').forEach(function (c) {
              c.textContent = n;
              var li = c.closest('li');
              if (li) li.hidden = n === 0;
            });
          });
          scope.classList.toggle('is-filtered', terms.length > 0);
          if (total) total.textContent = shown;
          if (status) status.textContent = shown;
          if (empty) empty.hidden = !(terms.length && shown === 0);
        };
        input.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(apply, 120); });
        input.addEventListener('keydown', function (e) {
          if (e.key === 'Escape' && input.value) { e.preventDefault(); input.value = ''; apply(); }
        });
        if (input.value) apply();
      });
    }
  };
})();
