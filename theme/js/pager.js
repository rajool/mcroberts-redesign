/* McRoberts theme: filter and pager for long listings (News Archive, Newsletters).
   The build prints every item, grouped by month, so the page is complete without JS. This shows one page of
   [data-pager-item]s at a time (data-pager-size), hides month groups left empty, adds the All / Newsletters
   filter (data-kind) and a Drupal-style full pager. The URL keeps ?page=n (0-based, as Drupal's pager) and
   ?type=newsletter, so Back, Forward and shared links work.
   Drupal: views_view (full pager, exposed filter on the newsletter flag); this is its progressive twin. */
(function () {
  'use strict';
  var McR = window.McR;

  McR.behaviors.pager = {
    attach: function (context) {
      McR.once('mcr-pager', '[data-pager]', context).forEach(function (box) {
        var size = +box.getAttribute('data-pager-size') || 20;
        var items = Array.prototype.slice.call(box.querySelectorAll('[data-pager-item]'));
        var groups = Array.prototype.slice.call(box.querySelectorAll('[data-pager-group]'));
        var tools = box.querySelector('[data-pager-tools]');
        var nav = box.querySelector('[data-pager-nav]');
        var count = box.querySelector('[data-pager-count]');
        var status = box.querySelector('[data-pager-status] [data-n]');
        var filters = Array.prototype.slice.call(box.querySelectorAll('[data-pager-filter]'));

        var read = function () {
          var q = new URLSearchParams(location.search);
          return { page: Math.max(0, parseInt(q.get('page') || '0', 10) || 0), kind: q.get('type') || '' };
        };
        var url = function (st) {
          var q = new URLSearchParams(location.search);
          if (st.page) q.set('page', st.page); else q.delete('page');
          if (st.kind) q.set('type', st.kind); else q.delete('type');
          var s = q.toString();
          return location.pathname + (s ? '?' + s : '');
        };
        var link = function (st, page, inner, attrs) {
          return '<a href="' + McR.esc(url({ page: page, kind: st.kind })) + '" data-page="' + page + '"' + (attrs || '') + '>' + inner + '</a>';
        };

        var render = function (st) {
          var match = items.filter(function (it) { return !st.kind || it.getAttribute('data-kind') === st.kind; });
          var pages = Math.max(1, Math.ceil(match.length / size));
          if (st.page > pages - 1) st.page = pages - 1;
          var from = st.page * size, to = from + size;
          var visible = new Set(match.slice(from, to));
          items.forEach(function (it) { it.hidden = !visible.has(it); });
          groups.forEach(function (g) { g.hidden = !g.querySelector('[data-pager-item]:not([hidden])'); });
          filters.forEach(function (b) { b.setAttribute('aria-pressed', String((b.getAttribute('data-pager-filter') || '') === st.kind)); });
          if (count) count.textContent = match.length;
          /* the status says which page loaded too (digits only): "307 · 2/16" */
          if (status) status.textContent = match.length + (pages > 1 ? ' · ' + (st.page + 1) + '/' + pages : '');
          if (!nav) return;
          nav.hidden = pages < 2;
          if (pages < 2) { nav.innerHTML = ''; return; }
          var out = [];
          var arrow = McR.icon('arrow');
          if (st.page > 0) out.push('<li class="pager-prev">' + link(st, st.page - 1, arrow + '<span class="vh">Previous page</span>', ' rel="prev"') + '</li>');
          var shown = [0, pages - 1, st.page - 1, st.page, st.page + 1].filter(function (n, i, a) { return n >= 0 && n < pages && a.indexOf(n) === i; }).sort(function (a, b) { return a - b; });
          shown.forEach(function (n, i) {
            if (i && n - shown[i - 1] > 1) out.push('<li class="pager-gap" aria-hidden="true">…</li>');
            out.push('<li>' + link(st, n, '<span class="vh">Page</span> ' + (n + 1), n === st.page ? ' aria-current="page"' : '') + '</li>');
          });
          if (st.page < pages - 1) out.push('<li class="pager-next">' + link(st, st.page + 1, '<span class="vh">Next page</span>' + arrow, ' rel="next"') + '</li>');
          nav.innerHTML = '<ul>' + out.join('') + '</ul>';
        };

        var state = read();
        render(state);
        var go = function (st, push) {
          state = st;
          render(state);
          if (push) history.pushState(null, '', url(state));
          box.focus({ preventScroll: true });
          box.scrollIntoView({ block: 'start' });
        };
        if (nav) nav.addEventListener('click', function (e) {
          var a = e.target.closest('a[data-page]');
          if (!a) return;
          e.preventDefault();
          go({ page: +a.getAttribute('data-page'), kind: state.kind }, true);
        });
        filters.forEach(function (b) {
          b.addEventListener('click', function () {
            state = { page: 0, kind: b.getAttribute('data-pager-filter') || '' };
            render(state);
            history.replaceState(null, '', url(state));
          });
        });
        window.addEventListener('popstate', function () { state = read(); render(state); });
      });
    }
  };
})();
