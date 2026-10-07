/* McRoberts theme: site search (/search?keys=…, the same query string as Drupal's /search/node).
   Fetches assets/search.json once (every page, the news archive and the calendar, built by build.py), keeps
   results that contain every word typed (accents and case ignored), ranks title over menu label over body, and
   marks the words in the title and a short excerpt. Results update as you type; the URL keeps ?keys=.
   Drupal: core search (node_search) renders the same list server-side; this is the static preview's stand-in. */
(function () {
  'use strict';
  var McR = window.McR;
  var esc = McR.esc;
  /* fold one character at a time so positions in the folded text match the original */
  var fold = function (s) {
    var out = '';
    for (var i = 0; i < s.length; i++) {
      var c = s[i].normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
      out += c.length === 1 ? c : s[i].toLowerCase().slice(0, 1) || ' ';
    }
    return out;
  };

  function mark(text, terms) {
    var f = fold(text), hits = [];
    terms.forEach(function (t) {
      var i = f.indexOf(t);
      while (i !== -1) { hits.push([i, i + t.length]); i = f.indexOf(t, i + t.length); }
    });
    if (!hits.length) return esc(text);
    hits.sort(function (a, b) { return a[0] - b[0]; });
    var out = '', pos = 0;
    hits.forEach(function (h) {
      if (h[0] < pos) return;
      out += esc(text.slice(pos, h[0])) + '<mark>' + esc(text.slice(h[0], h[1])) + '</mark>';
      pos = h[1];
    });
    return out + esc(text.slice(pos));
  }

  function excerpt(text, terms) {
    if (!text) return '';
    var f = fold(text), at = -1;
    terms.forEach(function (t) { var i = f.indexOf(t); if (i !== -1 && (at === -1 || i < at)) at = i; });
    if (at === -1) at = 0;
    var start = Math.max(0, at - 70), end = Math.min(text.length, start + 220);
    if (start > 0) start = text.indexOf(' ', start) + 1 || start;
    if (end < text.length) end = text.lastIndexOf(' ', end) > start ? text.lastIndexOf(' ', end) : end;
    return (start > 0 ? '… ' : '') + mark(text.slice(start, end), terms) + (end < text.length ? ' …' : '');
  }

  var reEsc = function (s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); };
  /* where a term sits in a field: 0 = absent, 1 = inside a word, 2 = at a word start, 3 = a whole word */
  function place(field, term) {
    if (field.indexOf(term) === -1) return 0;
    var t = reEsc(term);
    if (new RegExp('(^|[^a-z0-9])' + t + '([^a-z0-9]|$)').test(field)) return 3;
    return new RegExp('(^|[^a-z0-9])' + t).test(field) ? 2 : 1;
  }
  /* title > menu label or section heading (a) > body; a whole-word title match beats a word start ("grad" ranks
     Grad 2027 above Grade 8), and on a tie a page (p) beats a dated post */
  function score(item, terms) {
    var t = item._t || (item._t = fold(item.t)), a = item._a || (item._a = fold(item.a || '')),
      s = fold(item.s || ''), x = item._x || (item._x = fold(item.x || '')), total = 0;
    for (var i = 0; i < terms.length; i++) {
      var term = terms[i], hit = 0, pt = place(t, term), pa = place(a, term);
      hit += [0, 9, 14, 24][pt];
      hit += [0, 5, 10, 16][pa];
      /* a page whose title or menu label is this very word is what the visitor is after (Bell Schedule, Grad 2027) */
      if (item.p && (pt === 3 || pa === 3)) hit += 20;
      var n = 0, k = x.indexOf(term);
      while (k !== -1 && n < 6) { n++; k = x.indexOf(term, k + term.length); }
      hit += n;
      if (!hit) return 0;                        /* the section name only ranks, it never matches on its own */
      if (s.indexOf(term) !== -1) hit += 2;
      total += hit;
    }
    return total + (item.p ? 1 : 0);
  }

  McR.behaviors.search = {
    attach: function (context) {
      McR.once('mcr-search-page', '[data-search]', context).forEach(function (root) {
        var input = root.querySelector('input[name="keys"]');
        var form = input && input.form;
        var box = root.querySelector('[data-search-results]');
        var list = root.querySelector('[data-search-list]');
        var empty = root.querySelector('[data-search-empty]');
        var n = root.querySelector('[data-search-n]');
        var status = root.querySelector('[data-search-status]');
        var prefix = root.getAttribute('data-root') || '';
        var index = null, loading = null, timer = null;
        var load = function () {
          if (!loading) loading = fetch(root.getAttribute('data-index')).then(function (r) { return r.json(); }).then(function (d) { index = d; return d; });
          return loading;
        };
        var run = function (keys) {
          var terms = fold(keys).split(/\s+/).filter(function (t) { return t.length > 0; });
          if (!terms.length) { box.hidden = true; status.textContent = ''; return; }
          load().then(function () {
            var found = index.map(function (it) { return { it: it, sc: score(it, terms) }; })
              .filter(function (r) { return r.sc > 0; })
              .sort(function (a, b) { return b.sc - a.sc || String(b.it.d || '').localeCompare(String(a.it.d || '')); });
            box.hidden = false;
            n.textContent = found.length;
            empty.hidden = found.length > 0;
            status.textContent = box.querySelector('h2 span').textContent + ' ' + found.length;
            list.innerHTML = found.slice(0, 60).map(function (r) {
              var it = r.it, href = it.e ? it.u : prefix + it.u, d = it.d ? McR.date.parse(it.d) : null;
              return '<li class="result"><p class="result-meta">' + (it.s ? '<span class="result-sec">' + esc(it.s) + '</span>' : '') +
                (d ? '<time datetime="' + it.d + '">' + McR.date.MONTHS[d.getUTCMonth()] + ' ' + d.getUTCDate() + ', ' + d.getUTCFullYear() + '</time>' : '') +
                '</p><h3><a href="' + esc(href) + '">' + mark(it.t, terms) + '</a>' + (it.e ? McR.icon('ext', 'ext-mark') : '') + '</h3>' +
                (it.x ? '<p class="result-snip">' + excerpt(it.x, terms) + '</p>' : '') + '</li>';
            }).join('');
          }).catch(function () { box.hidden = true; });
        };
        var keys = new URLSearchParams(location.search).get('keys') || '';
        if (input) {
          input.value = keys;
          input.addEventListener('input', function () {
            clearTimeout(timer);
            timer = setTimeout(function () {
              var q = new URLSearchParams(location.search);
              if (input.value.trim()) q.set('keys', input.value.trim()); else q.delete('keys');
              history.replaceState(null, '', location.pathname + (q.toString() ? '?' + q : ''));
              run(input.value);
            }, 160);
          });
          input.addEventListener('focus', load, { once: true });
        }
        if (form) form.addEventListener('submit', function (e) { e.preventDefault(); clearTimeout(timer); run(input.value); });
        if (keys) run(keys);
      });
    }
  };
})();
