/* McRoberts theme: header behaviours.
   1. Primary navigation: W3C APG disclosure navigation (region primary_menu, menu main).
   2. Dialogs: phone menu and Accessibility Settings (native <dialog>; focus trap and Esc built in). The buttons also
      carry commandfor/command, so browsers with invoker commands open and close them with scripts off.
   3. Phone search disclosure.
   4. Sticky header state (mini crest + compact Student Absent? pill) without scroll listeners.
   5. Alert band (featured_top → news_alerts): Close hides it for this browser session.
   6. Phone bottom bar: its Student Absent? pill folds while a page's own call button is on screen. */
(function () {
  'use strict';
  var McR = window.McR;

  /* 1. Disclosure navigation ------------------------------------------------------------------ */
  McR.behaviors.disclosureNav = {
    attach: function (context) {
      McR.once('mcr-nav', '[data-disclosure-nav]', context).forEach(function (nav) {
        var buttons = Array.prototype.slice.call(nav.querySelectorAll('button[aria-controls]'));
        var tops = Array.prototype.slice.call(nav.querySelectorAll(':scope > li > a, :scope > li > button'));
        var panelOf = function (b) { return document.getElementById(b.getAttribute('aria-controls')); };
        var openBtn = function () { return buttons.filter(function (b) { return b.getAttribute('aria-expanded') === 'true'; })[0]; };
        var setOpen = function (b, open) {
          b.setAttribute('aria-expanded', String(open));
          var p = panelOf(b);
          if (!p) return;
          p.hidden = !open;
          if (open) {
            /* the panel may start well below the top (header not stuck yet): it never runs past the viewport */
            p.style.setProperty('--mega-top', Math.max(0, p.getBoundingClientRect().top) + 'px');
            refreshEvents(p);
          }
        };
        var closeAll = function (except) { buttons.forEach(function (b) { if (b !== except) setOpen(b, false); }); };

        buttons.forEach(function (btn) {
          btn.addEventListener('click', function () {
            var open = btn.getAttribute('aria-expanded') === 'true';
            closeAll(btn);
            setOpen(btn, !open);
          });
          btn.addEventListener('keydown', function (e) {
            if (e.key !== 'ArrowDown') return;
            e.preventDefault();
            if (btn.getAttribute('aria-expanded') !== 'true') { closeAll(btn); setOpen(btn, true); }
            var first = panelOf(btn) && panelOf(btn).querySelector('a');
            if (first) first.focus();
          });
        });

        /* Optional APG arrow keys between the top-level items */
        tops.forEach(function (el, i) {
          el.addEventListener('keydown', function (e) {
            var next = null;
            if (e.key === 'ArrowRight') next = tops[(i + 1) % tops.length];
            else if (e.key === 'ArrowLeft') next = tops[(i - 1 + tops.length) % tops.length];
            else if (e.key === 'Home') next = tops[0];
            else if (e.key === 'End') next = tops[tops.length - 1];
            if (next) { e.preventDefault(); next.focus(); }
          });
        });

        document.addEventListener('keydown', function (e) {
          if (e.key !== 'Escape') return;
          var b = openBtn();
          if (b) { closeAll(); b.focus(); }
        });
        document.addEventListener('click', function (e) { if (!nav.contains(e.target)) closeAll(); });
        nav.addEventListener('focusout', function (e) {
          if (e.relatedTarget && !nav.contains(e.relatedTarget)) closeAll();
        });
      });
    }
  };

  /* School Calendar panel: its next events were built for the build day; on a later day, the first open re-reads
     them from assets/search.json (the calendar's events with their dates) */
  function refreshEvents(panel) {
    var box = panel.querySelector('[data-mega-events]');
    if (!box || box._done) return;
    box._done = true;
    var today = McR.date.now().iso;
    if (today === box.getAttribute('data-built') || !window.fetch) return;
    fetch(box.getAttribute('data-index')).then(function (r) { return r.json(); }).then(function (items) {
      var root = box.getAttribute('data-root') || '';
      var noschool = box.getAttribute('data-noschool') || '';
      var evs = items.filter(function (it) { return it.s === 'School Calendar' && it.d && it.d >= today && !it.e; })
        .sort(function (a, b) { return a.d < b.d ? -1 : a.d > b.d ? 1 : 0; }).slice(0, 3);
      var list = box.querySelector('ol');
      if (!list || !evs.length) return;
      list.innerHTML = evs.map(function (e) {
        var d = McR.date.parse(e.d);
        var tag = e.o && noschool && !/no school/i.test(e.t) ? ' <span class="tag-noschool">' + McR.esc(noschool) + '</span>' : '';
        return '<li><a href="' + McR.esc(root + e.u) + '"' + (e.o ? ' class="is-noschool"' : '') + '><time class="date-chip" datetime="' + e.d + '"><span class="m">' +
          McR.date.MONTHS[d.getUTCMonth()] + '</span><span class="n">' + d.getUTCDate() + '</span><span class="d">' + McR.date.DAYS[d.getUTCDay()] +
          '</span></time><span class="t">' + McR.esc(e.t) + tag + '</span></a></li>';
      }).join('');
    }).catch(function () { /* the built list stays */ });
  }

  /* 2. Dialogs ------------------------------------------------------------------------------- */
  McR.behaviors.dialogs = {
    attach: function (context) {
      McR.once('mcr-dialog-open', '[data-open-dialog]', context).forEach(function (opener) {
        opener.addEventListener('click', function () {
          var d = document.getElementById(opener.getAttribute('data-open-dialog'));
          if (!d || typeof d.showModal !== 'function' || d.open) return;
          d._opener = opener;
          d.showModal();
          if (opener.hasAttribute('aria-expanded')) opener.setAttribute('aria-expanded', 'true');
        });
      });
      McR.once('mcr-dialog', 'dialog', context).forEach(function (d) {
        d.addEventListener('click', function (e) { if (e.target === d) d.close(); }); /* backdrop */
        d.addEventListener('close', function () {
          var o = d._opener;
          if (!o) return;
          if (o.hasAttribute('aria-expanded')) o.setAttribute('aria-expanded', 'false');
          /* the opener may be hidden at this width (e.g. the phone menu after a resize): fall back to main */
          if (o.offsetParent !== null) o.focus();
          else { var m = document.getElementById('main-content'); if (m) m.focus({ preventScroll: true }); }
        });
        d.querySelectorAll('[data-close-dialog]').forEach(function (c) {
          c.addEventListener('click', function () { d.close(); });
        });
      });
      /* The phone menu is meaningless on a desktop layout: close it if the window grows past it. The layout tier is
         a container query in rem (it follows Text increase), so the test is whether the desktop menu is showing. */
      var drawer = document.getElementById('menu-drawer');
      var primary = document.querySelector('.primary');
      if (drawer && primary && !drawer._fit) {
        drawer._fit = function () { if (drawer.open && getComputedStyle(primary).display !== 'none') drawer.close(); };
        window.addEventListener('resize', drawer._fit);
      }
    }
  };

  /* 3. Phone search ---------------------------------------------------------------------------- */
  McR.behaviors.searchToggle = {
    attach: function (context) {
      McR.once('mcr-search', '[data-toggle-search]', context).forEach(function (btn) {
        var panel = document.getElementById(btn.getAttribute('aria-controls'));
        if (!panel) return;
        btn.addEventListener('click', function () {
          var open = btn.getAttribute('aria-expanded') === 'true';
          btn.setAttribute('aria-expanded', String(!open));
          panel.hidden = open;
          if (!open) { var i = panel.querySelector('input'); if (i) i.focus(); }
        });
      });
    }
  };

  /* 4. Sticky header ------------------------------------------------------------------------------ */
  McR.behaviors.stickyHeader = {
    attach: function (context) {
      McR.once('mcr-sticky', '[data-sticky-header]', context).forEach(function (header) {
        var sentinel = header.querySelector('.sticky-sentinel');
        if (!sentinel || !('IntersectionObserver' in window)) return;
        new IntersectionObserver(function (entries) {
          header.classList.toggle('is-stuck', !entries[0].isIntersecting);
        }, { rootMargin: '-2px 0px 0px 0px' }).observe(sentinel);
      });
    }
  };

  /* 5. Alert band ------------------------------------------------------------------------------- */
  McR.behaviors.alertBand = {
    attach: function (context) {
      McR.once('mcr-alert', '[data-alert]', context).forEach(function (wrap) {
        /* the key names this alert (Drupal: its node id and changed time); the inline <head> script reads the same
           key and sets html.alert-closed before the first paint, so a closed alert never shows and then jumps away */
        var key = 'mcr-alert-' + wrap.getAttribute('data-alert');
        if (McR.store('sessionStorage', key) === 'closed') { wrap.hidden = true; return; }
        var close = wrap.querySelector('[data-alert-close]');
        if (!close) return;
        close.addEventListener('click', function () {
          wrap.hidden = true;
          document.documentElement.classList.add('alert-closed');
          McR.store('sessionStorage', key, 'closed');
          var main = document.getElementById('main-content');
          if (main) main.focus({ preventScroll: true });
        });
      });
    }
  };

  /* 6. Phone bottom bar ---------------------------------------------------------------------------
     While a page's own Student Absent? call button is on screen (the front page's Today card, the call-out on Student
     Attendance), the bar's pill folds to its call icon (layout.css .action-bar.has-dup), so a screen never shows the
     same pair twice. The build renders those two pages' bar folded; scripts off, the bar shows the full pill. */
  McR.behaviors.absentDup = {
    attach: function (context) {
      var bar = document.querySelector('.action-bar');
      if (!bar) return;
      var sel = '.today-absent, .callout a.btn[href^="tel:"]';
      var targets = McR.once('mcr-absent-dup', sel, context);
      if (!targets.length) { if (!document.querySelector(sel)) bar.classList.remove('has-dup'); return; }
      if (!('IntersectionObserver' in window)) { bar.classList.remove('has-dup'); return; }
      var seen = [];
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          var i = seen.indexOf(e.target);
          if (e.isIntersecting && i === -1) seen.push(e.target);
          if (!e.isIntersecting && i !== -1) seen.splice(i, 1);
        });
        bar.classList.toggle('has-dup', seen.length > 0);
      });
      targets.forEach(function (t) { io.observe(t); });
    }
  };
})();
