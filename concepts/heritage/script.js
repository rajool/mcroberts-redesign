/* Crest & Canopy — progressive enhancement only. Everything works without JS except the
   disclosure panels, dialogs and the a11y controls. In Drupal each block below becomes a
   Drupal.behaviors entry using core/once; no jQuery, no libraries. */
(function () {
  'use strict';
  var doc = document;
  var root = doc.documentElement;

  function store(key, value) {
    try {
      if (value === undefined) return window.sessionStorage.getItem(key);
      window.sessionStorage.setItem(key, value);
    } catch (e) { return null; }
  }

  /* 1. Primary navigation: disclosure buttons → mega panels (W3C APG disclosure navigation) */
  var nav = doc.querySelector('[data-disclosure-nav]');
  if (nav) {
    var buttons = Array.prototype.slice.call(nav.querySelectorAll('button[aria-controls]'));
    var closeAll = function (except) {
      buttons.forEach(function (b) {
        if (b === except) return;
        b.setAttribute('aria-expanded', 'false');
        var p = doc.getElementById(b.getAttribute('aria-controls'));
        if (p) p.hidden = true;
      });
    };
    buttons.forEach(function (btn) {
      var panel = doc.getElementById(btn.getAttribute('aria-controls'));
      btn.addEventListener('click', function () {
        var open = btn.getAttribute('aria-expanded') === 'true';
        closeAll(btn);
        btn.setAttribute('aria-expanded', String(!open));
        if (panel) panel.hidden = open;
      });
      btn.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowDown' && panel) {
          e.preventDefault();
          if (btn.getAttribute('aria-expanded') !== 'true') btn.click();
          var first = panel.querySelector('a');
          if (first) first.focus();
        }
      });
    });
    doc.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      var openBtn = buttons.filter(function (b) { return b.getAttribute('aria-expanded') === 'true'; })[0];
      if (openBtn) { closeAll(); openBtn.focus(); }
    });
    doc.addEventListener('click', function (e) { if (!nav.contains(e.target)) closeAll(); });
    nav.addEventListener('focusout', function (e) {
      if (e.relatedTarget && !nav.contains(e.relatedTarget)) closeAll();
    });
  }

  /* 2. Dialogs: mobile menu and Accessibility Settings (native <dialog>: focus trap + Esc built in) */
  function openDialog(id, opener) {
    var d = doc.getElementById(id);
    if (!d || typeof d.showModal !== 'function') return;
    d._opener = opener;
    d.showModal();
  }
  doc.querySelectorAll('[data-open-menu]').forEach(function (b) {
    b.addEventListener('click', function () { openDialog('menu-drawer', b); });
  });
  doc.querySelectorAll('[data-open-a11y]').forEach(function (b) {
    b.addEventListener('click', function () { openDialog('a11y-dialog', b); });
  });
  doc.querySelectorAll('dialog').forEach(function (d) {
    d.addEventListener('click', function (e) { if (e.target === d) d.close(); }); /* backdrop click */
    d.addEventListener('close', function () { if (d._opener) d._opener.focus(); });
    d.querySelectorAll('[data-close-dialog]').forEach(function (c) {
      c.addEventListener('click', function () { d.close(); });
    });
  });

  /* 3. Mobile search disclosure */
  var sBtn = doc.querySelector('[data-toggle-search]');
  if (sBtn) {
    var sPanel = doc.getElementById(sBtn.getAttribute('aria-controls'));
    sBtn.addEventListener('click', function () {
      var open = sBtn.getAttribute('aria-expanded') === 'true';
      sBtn.setAttribute('aria-expanded', String(!open));
      sPanel.hidden = open;
      if (!open) { var i = sPanel.querySelector('input'); if (i) i.focus(); }
    });
  }

  /* 4. Alert band: dismiss for this session (keyed by the alert text) */
  var alertWrap = doc.querySelector('[data-alert]');
  if (alertWrap) {
    var key = 'alert:' + alertWrap.textContent.replace(/\s+/g, ' ').trim().slice(0, 80);
    if (store(key) === 'closed') alertWrap.hidden = true;
    var close = alertWrap.querySelector('[data-alert-close]');
    if (close) close.addEventListener('click', function () {
      alertWrap.hidden = true;
      store(key, 'closed');
      var main = doc.getElementById('main-content');
      if (main) main.focus({ preventScroll: true });
    });
  }

  /* 5. Sticky header state (shadow + mini crest) without scroll listeners */
  var header = doc.getElementById('site-header');
  var sentinelTarget = doc.querySelector('.featured-top') || doc.getElementById('main-content');
  if (header && 'IntersectionObserver' in window) {
    var sentinel = doc.createElement('div');
    sentinel.setAttribute('aria-hidden', 'true');
    sentinel.style.cssText = 'position:absolute;height:1px;width:1px;margin-top:-1px;';
    header.parentNode.insertBefore(sentinel, header.nextSibling);
    new IntersectionObserver(function (entries) {
      header.classList.toggle('is-stuck', !entries[0].isIntersecting);
    }, { rootMargin: '-' + (window.innerWidth >= 1024 ? 57 : 69) + 'px 0px 0px 0px' }).observe(sentinel);
  }

  /* 6. Translate: mirror the GTranslate select label (the real widget sets the googtrans cookie) */
  doc.querySelectorAll('[data-gt-select]').forEach(function (sel) {
    sel.addEventListener('change', function () {
      var label = sel.options[sel.selectedIndex].text;
      doc.querySelectorAll('[data-gt-select]').forEach(function (o) {
        o.value = sel.value;
        var cur = o.parentNode.querySelector('.current');
        if (cur) cur.textContent = label;
      });
    });
  });

  /* 7. a11y module stand-ins (live: body.style.filter / zoom / .a11y-opendyslexic, cookies) */
  var page = doc.querySelector('.page');
  var size = 100;
  var filters = { contrast: false, invert: false };
  function applyFilter() {
    var f = [];
    if (filters.contrast) f.push('contrast(1.6)');
    if (filters.invert) f.push('invert(1) hue-rotate(180deg)');
    if (page) page.style.filter = f.join(' ');
  }
  doc.querySelectorAll('.a11y-control').forEach(function (b) {
    b.addEventListener('click', function () {
      var a = b.getAttribute('data-a11y-action');
      if (a === 'dyslexic') {
        var on = root.classList.toggle('a11y-opendyslexic');
        b.setAttribute('aria-pressed', String(on)); b.classList.toggle('is-active', on);
      } else if (a === 'contrast' || a === 'invert') {
        filters[a] = !filters[a];
        b.setAttribute('aria-pressed', String(filters[a])); b.classList.toggle('is-active', filters[a]);
        applyFilter();
      } else {
        size = a === 'text-increase' ? Math.min(size + 10, 150) : a === 'text-decrease' ? Math.max(size - 10, 80) : 100;
        root.style.fontSize = size + '%';
      }
    });
  });
})();
