/* McRoberts "Striker Energy" concept — vanilla JS, progressive enhancement only.
   In Drupal each block below becomes a Drupal.behaviors entry using core/once. */
(function () {
  'use strict';
  var doc = document;
  var root = doc.documentElement;
  var desktop = window.matchMedia('(min-width: 1100px)');

  /* ---- Primary nav: disclosure mega panels (W3C APG disclosure navigation) ---- */
  var nav = doc.querySelector('.primary-nav');
  var toggles = Array.prototype.slice.call(doc.querySelectorAll('.nav-toggle'));

  function setPanel(btn, open) {
    var panel = doc.getElementById(btn.getAttribute('aria-controls'));
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (panel) panel.hidden = !open;
  }
  function closeAll(except) {
    toggles.forEach(function (b) { if (b !== except) setPanel(b, false); });
  }
  toggles.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var open = btn.getAttribute('aria-expanded') !== 'true';
      if (desktop.matches) closeAll(btn);
      setPanel(btn, open);
    });
  });
  if (nav) {
    nav.addEventListener('focusout', function (e) {
      if (!desktop.matches) return;
      var item = e.target.closest('.has-panel');
      if (item && !item.contains(e.relatedTarget)) {
        var b = item.querySelector('.nav-toggle');
        if (b) setPanel(b, false);
      }
    });
  }
  doc.addEventListener('click', function (e) {
    if (desktop.matches && nav && !nav.contains(e.target)) closeAll();
  });

  /* ---- Mobile menu ---- */
  var menuBtn = doc.querySelector('.menu-btn');
  function setMenu(open) {
    if (!menuBtn) return;
    menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    root.classList.toggle('menu-open', open);
  }
  if (menuBtn) {
    menuBtn.addEventListener('click', function () {
      setMenu(menuBtn.getAttribute('aria-expanded') !== 'true');
    });
  }
  desktop.addEventListener('change', function () { setMenu(false); closeAll(); syncSectionNav(); });

  doc.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var openBtn = toggles.filter(function (b) { return b.getAttribute('aria-expanded') === 'true'; })[0];
    if (openBtn && desktop.matches) { closeAll(); openBtn.focus(); return; }
    if (root.classList.contains('menu-open')) { setMenu(false); menuBtn.focus(); }
  });

  /* ---- Sticky header state (the header itself is position: sticky) ---- */
  var header = doc.querySelector('.site-header');
  var ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      var top = header.getBoundingClientRect().top;
      var stuck = top < -1;
      doc.body.classList.toggle('is-stuck', stuck);
      ticking = false;
    });
  }
  if (header) { window.addEventListener('scroll', onScroll, { passive: true }); onScroll(); }

  /* ---- Search shortcut from the mobile action bar ---- */
  Array.prototype.forEach.call(doc.querySelectorAll('[data-focus-search]'), function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      if (!desktop.matches) setMenu(true);
      var q = doc.getElementById('q');
      window.scrollTo({ top: 0, behavior: 'auto' });
      if (q) setTimeout(function () { q.focus(); }, 30);
    });
  });

  /* ---- Alert band dismiss (labelled with the site's existing word "Close") ---- */
  var alertBand = doc.querySelector('.featured-top');
  var KEY = 'mcr-alert-dismissed';
  try { if (alertBand && sessionStorage.getItem(KEY) === '1') alertBand.classList.add('is-dismissed'); } catch (err) { /* storage blocked */ }
  Array.prototype.forEach.call(doc.querySelectorAll('[data-dismiss-alert]'), function (b) {
    b.addEventListener('click', function () {
      alertBand.classList.add('is-dismissed');
      try { sessionStorage.setItem(KEY, '1'); } catch (err) { /* storage blocked */ }
      var main = doc.getElementById('main-content');
      if (main) main.focus();
    });
  });

  /* ---- Accessibility Settings dialog (native <dialog>; a11y module keeps its classes) ---- */
  var dlg = doc.getElementById('accessibilityModal');
  var lastTrigger = null;
  Array.prototype.forEach.call(doc.querySelectorAll('[data-open-a11y]'), function (b) {
    b.addEventListener('click', function () {
      if (!dlg || typeof dlg.showModal !== 'function') return;
      lastTrigger = b;
      dlg.showModal();
    });
  });
  if (dlg) {
    dlg.addEventListener('close', function () { if (lastTrigger) lastTrigger.focus(); });
    dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.close(); });
    Array.prototype.forEach.call(dlg.querySelectorAll('[data-close-dialog]'), function (b) {
      b.addEventListener('click', function () { dlg.close(); });
    });
    /* Stand-in for the a11y module behaviour so the concept can be tried */
    var zoom = 1;
    var body = doc.body;
    Array.prototype.forEach.call(dlg.querySelectorAll('.a11y-control'), function (b) {
      var isToggle = b.getAttribute('data-a11y-action') === 'toggle';
      if (isToggle) b.setAttribute('aria-pressed', 'false');
      b.addEventListener('click', function () {
        var c = b.className;
        if (isToggle) {
          var on = b.getAttribute('aria-pressed') !== 'true';
          b.setAttribute('aria-pressed', on ? 'true' : 'false');
          b.classList.toggle('is-active', on);
          if (c.indexOf('opendyslexic') > -1) body.classList.toggle('a11y-opendyslexic', on);
          var filters = [];
          if (dlg.querySelector('.a11y-contrast-control.is-active')) filters.push('contrast(2)');
          if (dlg.querySelector('.a11y-invert-control.is-active')) filters.push('invert(1)');
          body.style.filter = filters.join(' ');
        } else {
          var act = b.getAttribute('data-a11y-action');
          zoom = act === 'increase' ? Math.min(zoom + 0.1, 1.6) : act === 'decrease' ? Math.max(zoom - 0.1, 0.8) : 1;
          body.style.zoom = zoom === 1 ? '' : String(zoom);
        }
      });
    });
  }

  /* ---- Section nav: open as a sidebar on desktop, collapsible on small screens ---- */
  var snav = doc.querySelector('.snav-d');
  function syncSectionNav() {
    if (!snav) return;
    if (desktop.matches) snav.open = true;
  }
  if (snav) {
    if (!desktop.matches) snav.open = false;
    snav.addEventListener('toggle', function () { if (desktop.matches && !snav.open) snav.open = true; });
  }
})();
