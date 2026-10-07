/* McRoberts · "Community Clarity" — progressive enhancement only, no libraries.
   In the Drupal sub-theme each block below becomes a Drupal.behaviors entry using core/once. */
(function () {
  'use strict';

  var header = document.querySelector('.site-header');
  var desktop = window.matchMedia('(min-width: 1080px)');

  /* ---- Disclosure navigation (W3C APG disclosure pattern): mega panels on desktop, accordion in the mobile drawer ---- */
  var toggles = Array.prototype.slice.call(document.querySelectorAll('.menu__toggle'));

  function setPanel(btn, open) {
    btn.setAttribute('aria-expanded', String(open));
    var panel = document.getElementById(btn.getAttribute('aria-controls'));
    if (panel) panel.hidden = !open;
  }
  function closePanels(except) {
    toggles.forEach(function (b) { if (b !== except) setPanel(b, false); });
  }
  toggles.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var open = btn.getAttribute('aria-expanded') !== 'true';
      if (desktop.matches) closePanels(btn);
      setPanel(btn, open);
    });
    var li = btn.parentElement;
    li.addEventListener('focusout', function (e) {
      if (desktop.matches && e.relatedTarget && !li.contains(e.relatedTarget)) setPanel(btn, false);
    });
  });
  document.addEventListener('click', function (e) {
    if (desktop.matches && !e.target.closest('.primary-nav')) closePanels();
  });

  /* ---- Mobile drawer + search ---- */
  var menuBtn = document.querySelector('.menu-btn');
  var searchBtn = document.querySelector('.search-toggle');
  var search = document.getElementById('site-search');

  function drawerTop() {
    var bar = document.querySelector('.brandbar');
    if (bar) header.style.setProperty('--drawer-top', Math.max(0, bar.getBoundingClientRect().bottom) + 'px');
  }
  function setDrawer(open) {
    if (!menuBtn) return;
    if (open) { setSearch(false); drawerTop(); }
    header.classList.toggle('nav-open', open);
    menuBtn.setAttribute('aria-expanded', String(open));
    document.documentElement.classList.toggle('no-scroll', open);
  }
  function setSearch(open) {
    if (!searchBtn || !search) return;
    search.classList.toggle('is-open', open);
    searchBtn.setAttribute('aria-expanded', String(open));
    if (open) { setDrawer(false); var q = search.querySelector('input'); if (q) q.focus(); }
  }
  if (menuBtn) menuBtn.addEventListener('click', function () { setDrawer(menuBtn.getAttribute('aria-expanded') !== 'true'); });
  if (searchBtn) searchBtn.addEventListener('click', function () { setSearch(searchBtn.getAttribute('aria-expanded') !== 'true'); });

  desktop.addEventListener('change', function () { setDrawer(false); setSearch(false); closePanels(); });

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var openBtn = toggles.filter(function (b) { return b.getAttribute('aria-expanded') === 'true'; })[0];
    if (openBtn && desktop.matches) { setPanel(openBtn, false); openBtn.focus(); return; }
    if (header.classList.contains('nav-open')) { setDrawer(false); menuBtn.focus(); return; }
    if (search && search.classList.contains('is-open')) { setSearch(false); searchBtn.focus(); }
  });

  /* ---- Show the mini crest in the sticky nav once the brand bar has scrolled away (desktop) ---- */
  var brandbar = document.querySelector('.brandbar');
  if ('IntersectionObserver' in window && brandbar) {
    new IntersectionObserver(function (entries) {
      header.classList.toggle('is-stuck', !entries[0].isIntersecting);
    }, { threshold: 0, rootMargin: '-2px 0px 0px 0px' }).observe(brandbar);
  }

  /* ---- Section nav: open on wide screens, collapsed <details> on phones ---- */
  var side = document.getElementById('sidenav-details');
  if (side) {
    var wide = window.matchMedia('(min-width: 1000px)');
    var syncSide = function () { side.open = wide.matches; };
    syncSide();
    wide.addEventListener('change', syncSide);
  }

  /* ---- Accessibility Settings: native <dialog> wrapping the a11y module's controls (same classes / data attributes) ---- */
  var dialog = document.getElementById('accessibilityModal');
  var zoom = 1;
  if (dialog && typeof dialog.showModal === 'function') {
    document.querySelectorAll('[data-a11y-open]').forEach(function (b) {
      b.addEventListener('click', function () { dialog.showModal(); });
    });
    dialog.querySelector('[data-a11y-close]').addEventListener('click', function () { dialog.close(); });
    dialog.addEventListener('click', function (e) { if (e.target === dialog) dialog.close(); });

    var filters = { contrast: 'contrast(1.6)', invert: 'invert(1) hue-rotate(180deg)' };
    var applyFilters = function () {
      var f = [];
      dialog.querySelectorAll('[data-a11y-action="contrast"], [data-a11y-action="invert"]').forEach(function (b) {
        if (b.getAttribute('aria-pressed') === 'true') f.push(filters[b.dataset.a11yAction]);
      });
      document.body.style.filter = f.join(' ');
    };
    dialog.querySelectorAll('.a11y-control').forEach(function (b) {
      b.addEventListener('click', function () {
        var action = b.dataset.a11yAction;
        if (b.hasAttribute('aria-pressed')) {
          var on = b.getAttribute('aria-pressed') !== 'true';
          b.setAttribute('aria-pressed', String(on));
          b.classList.toggle('is-active', on);
          if (action === 'dyslexic') document.body.classList.toggle('a11y-opendyslexic', on);
          else applyFilters();
          return;
        }
        if (action === 'textsize-increase') zoom = Math.min(1.5, zoom + 0.1);
        if (action === 'textsize-decrease') zoom = Math.max(0.8, zoom - 0.1);
        if (action === 'textsize-reset') zoom = 1;
        document.documentElement.style.fontSize = (zoom * 100) + '%';
      });
    });
  }
})();
