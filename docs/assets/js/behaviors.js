/* McRoberts theme: behaviour registry.
   Each feature registers McR.behaviors.<name> = { attach: function (context) { ... } } and binds its elements
   through McR.once(), so it maps one to one onto Drupal.behaviors + core/once in the Drupal theme:
     Drupal.behaviors.mcrobertsNav = { attach(context) { once('mcr-nav', '[data-disclosure-nav]', context).forEach(...) } };
   Vanilla ES2019, no dependencies. Everything works without JS except the menus, dialogs and the a11y controls. */
(function () {
  'use strict';
  var McR = window.McR = window.McR || {};
  McR.behaviors = McR.behaviors || {};

  /* core/once stand-in: returns the matching elements not yet processed under this id */
  McR.once = function (id, selector, context) {
    var root = context || document;
    var list = [];
    if (root.nodeType === 1 && root.matches(selector)) list.push(root);
    list = list.concat(Array.prototype.slice.call(root.querySelectorAll(selector)));
    return list.filter(function (el) {
      var done = (el.getAttribute('data-once') || '').split(' ');
      if (done.indexOf(id) !== -1) return false;
      el.setAttribute('data-once', (done.join(' ') + ' ' + id).trim());
      return true;
    });
  };

  /* Storage that never throws (private windows, blocked storage) */
  McR.store = function (area, key, value) {
    try {
      var s = window[area];
      if (value === undefined) return s.getItem(key);
      if (value === null) s.removeItem(key); else s.setItem(key, value);
    } catch (e) { /* storage unavailable: the page still works, it just forgets */ }
    return null;
  };

  /* Dates on the school's clock (America/Vancouver), as ISO strings: shared by calendar.js and bell.js */
  McR.date = {
    MONTHS: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'June', 'July', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec'],
    MONTHS_LONG: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
    DAYS: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
    DAYS_LONG: ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
    parse: function (iso) { var p = iso.split('-'); return new Date(Date.UTC(+p[0], +p[1] - 1, +p[2])); },
    iso: function (d) { return d.toISOString().slice(0, 10); },
    add: function (iso, n) { var d = McR.date.parse(iso); d.setUTCDate(d.getUTCDate() + n); return McR.date.iso(d); },
    dow: function (iso) { return McR.date.parse(iso).getUTCDay(); },
    /* { iso: 'YYYY-MM-DD', min: minutes since midnight } in Vancouver; ?today=YYYY-MM-DD&time=HH:MM overrides for testing */
    now: function () {
      var q = new URLSearchParams(location.search), out = null;
      try {
        var parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Vancouver', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(new Date());
        var get = function (t) { return (parts.filter(function (x) { return x.type === t; })[0] || {}).value; };
        out = { iso: get('year') + '-' + get('month') + '-' + get('day'), min: (+get('hour') % 24) * 60 + (+get('minute')) };
      } catch (e) {
        var n = new Date();
        out = { iso: n.getFullYear() + '-' + String(n.getMonth() + 1).padStart(2, '0') + '-' + String(n.getDate()).padStart(2, '0'), min: n.getHours() * 60 + n.getMinutes() };
      }
      if (/^\d{4}-\d\d-\d\d$/.test(q.get('today') || '')) out.iso = q.get('today');
      var t = /^(\d\d?):(\d\d)$/.exec(q.get('time') || '');
      if (t) out.min = (+t[1]) * 60 + (+t[2]);
      return out;
    },
    long: function (iso) { var d = McR.date.parse(iso); return McR.date.DAYS_LONG[d.getUTCDay()] + ', ' + McR.date.MONTHS_LONG[d.getUTCMonth()] + ' ' + d.getUTCDate(); }
  };
  /* The school day both Today cards show (front page Today, Bell Schedule): today until its last bell has rung, then
     the next school day. One rule, shared by js/today.js and js/bell.js, so the two never disagree.
     data = the embedded JSON: codes {date: rotation code}, rotations [{name, from, to}], bell {rotation: {column: rows}}. */
  var COLS = { 1: 'MON', 2: 'TUE', 3: 'WED', 4: 'THU', 5: 'FRI' };
  var hm = function (t) { var p = t.trim().split(':'), h = +p[0]; if (h < 7) h += 12; return h * 60 + (+p[1] || 0); };
  McR.school = {
    rotationFor: function (data, day) {
      var r = data.rotations.filter(function (x) { return day >= x.from && day <= x.to; })[0];
      if (r) return r.name;
      var code = data.codes[day] || '';
      if (/ABCD$/.test(code)) return 'Rotation One';
      if (/BADC$/.test(code)) return 'Rotation Two';
      return null;
    },
    /* same rule as build.py bell_col(): COLLAB → Collaboration Days; a Tuesday/Thursday without PLT runs Monday */
    colFor: function (day, code) {
      if (/^COLLAB/i.test(code || '')) return 'Collaboration Days';
      var col = COLS[McR.date.dow(day)] || 'MON';
      if (!/^PLT/i.test(code || '') && (col === 'TUE' || col === 'THU')) return 'MON';
      return col;
    },
    next: function (data, from) {
      for (var i = 0; i < 60; i++) { var d = McR.date.add(from, i); if (data.codes[d]) return d; }
      return null;
    },
    blocks: function (data, day) {
      var code = data.codes[day], rot = McR.school.rotationFor(data, day), col = McR.school.colFor(day, code);
      var rows = (rot && data.bell[rot] && data.bell[rot][col]) || [];
      return { code: code, rot: rot, col: col, rows: rows.map(function (r) {
        var p = r[0].split('-');
        return { label: r[1], range: r[0], from: hm(p[0]), to: hm(p[1]) };
      }) };
    },
    day: function (data, now) {
      var today = now.iso;
      if (data.codes[today]) {
        var rows = McR.school.blocks(data, today).rows;
        if (!rows.length || now.min < rows[rows.length - 1].to) return today;
        return McR.school.next(data, McR.date.add(today, 1));
      }
      return McR.school.next(data, today);
    }
  };

  McR.esc = function (s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  };
  McR.icon = function (name, cls) {
    return '<svg class="icon' + (cls ? ' ' + cls : '') + '" aria-hidden="true" focusable="false"><use href="#i-' + name + '"/></svg>';
  };

  /* Print: closed accordions open for the printout and close again after (Safari and Firefox print a closed
     <details> empty; print.css covers Chrome) */
  if (!McR._print) {
    McR._print = true;
    window.addEventListener('beforeprint', function () {
      document.querySelectorAll('details:not([open])').forEach(function (d) { d.setAttribute('data-print-opened', ''); d.open = true; });
    });
    window.addEventListener('afterprint', function () {
      document.querySelectorAll('details[data-print-opened]').forEach(function (d) { d.removeAttribute('data-print-opened'); d.open = false; });
    });
  }

  /* Subscribe to our calendar: webcal:// opens the calendar app on Apple devices; elsewhere (Android Chrome,
     Windows) nothing handles it, so the same feed is linked over https. Drupal: the same block template. */
  McR.behaviors.webcal = {
    attach: function (context) {
      if (/Mac|iPhone|iPad|iPod/.test(navigator.platform || '') || /iPhone|iPad|Macintosh/.test(navigator.userAgent)) return;
      McR.once('mcr-webcal', 'a[href^="webcal:"]', context).forEach(function (a) {
        a.setAttribute('href', a.getAttribute('href').replace(/^webcal:/, 'https:'));
      });
    }
  };

  /* Section menu: sticky only while the whole list fits the window (layout.css .page-sidebar.is-sticky); a longer
     list scrolls with the page, so no link ever hides in a nested scroll box. Re-measured on resize and when the
     text size changes (Accessibility Settings), via ResizeObserver. */
  McR.behaviors.sidebarFit = {
    attach: function (context) {
      McR.once('mcr-sidebar', '.page-sidebar', context).forEach(function (side) {
        var nav = document.querySelector('.primary');
        var fit = function () {
          var top = (nav ? nav.getBoundingClientRect().height : 0) + 48;
          side.classList.toggle('is-sticky', side.scrollHeight + top <= window.innerHeight);
        };
        fit();
        window.addEventListener('resize', fit);
        if (window.ResizeObserver) new ResizeObserver(fit).observe(side);
      });
    }
  };

  /* Table frames (.table-wrap, .rot-wrap): a tab stop only while the table is wider than its frame, so the keyboard
     can scroll it, and then a region named by the nearest heading before it (or the table's caption); a fade marks
     the clipped edge until the frame is scrolled to the end. Re-checked on resize. No words of its own. */
  var frameId = 0;
  var frameName = function (w) {
    var cap = w.querySelector('caption');
    var h = cap;
    for (var n = w; !h && n && n !== document.body; n = n.parentElement) {
      for (var p = n.previousElementSibling; p && !h; p = p.previousElementSibling) {
        if (/^H[1-6]$/.test(p.tagName)) h = p;
        else { var hs = p.querySelectorAll('h1, h2, h3, h4, h5, h6'); if (hs.length) h = hs[hs.length - 1]; }
      }
    }
    h = h || document.getElementById('page-title');
    if (!h) return '';
    if (!h.id) h.id = 'mcr-frame-' + (++frameId);
    return h.id;
  };
  McR.behaviors.scrollFrames = {
    attach: function (context) {
      McR.once('mcr-frame', '.table-wrap, .rot-wrap', context).forEach(function (w) {
        var own = !w.hasAttribute('role');            /* .rot-wrap is a named region already */
        var check = function () {
          var more = w.scrollWidth > w.clientWidth + 1;
          if (more) {
            w.setAttribute('tabindex', '0');
            if (own) {
              var id = frameName(w);
              w.setAttribute('role', 'region');
              if (id) w.setAttribute('aria-labelledby', id);
            }
          } else {
            w.removeAttribute('tabindex');
            if (own) { w.removeAttribute('role'); w.removeAttribute('aria-labelledby'); }
          }
          w.classList.toggle('has-more', more && w.scrollLeft + w.clientWidth < w.scrollWidth - 2);
        };
        check();
        w.addEventListener('scroll', check, { passive: true });
        if (window.ResizeObserver) new ResizeObserver(check).observe(w);
        else window.addEventListener('resize', check);
      });
    }
  };

  McR.attachBehaviors = function (context) {
    Object.keys(McR.behaviors).forEach(function (name) {
      try { McR.behaviors[name].attach(context || document); } catch (e) { if (window.console) console.error(name, e); }
    });
  };

  /* Scripts load with defer, so every behaviour file has run before DOMContentLoaded; once() makes the
     load fallback harmless. */
  var run = function () { McR.attachBehaviors(document); };
  if (document.readyState === 'complete') run();
  else {
    document.addEventListener('DOMContentLoaded', run);
    window.addEventListener('load', run);
  }
})();
