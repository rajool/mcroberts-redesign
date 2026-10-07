/* McRoberts theme: Accessibility Settings and Translate.
   a11y module contract kept: buttons .a11y-control.a11y-*-control with data-a11y-action, active state .is-active,
   dyslexic = body.a11y-opendyslexic. Where the module writes body.style.filter / body.style.zoom and cookies, this
   stand-in sets classes on the root element (html.a11y-contrast, html.a11y-invert) and localStorage,
   so a choice follows the visitor from page to page. The <head> applies the saved state before first paint.
   GTranslate contract kept: .gtranslate_wrapper + select.gt_selector with the languages from the block config. */
(function () {
  'use strict';
  var McR = window.McR;
  var KEY = 'mcr-a11y';
  var root = document.documentElement;

  function read() {
    try { return JSON.parse(McR.store('localStorage', KEY) || '{}') || {}; } catch (e) { return {}; }
  }
  /* Contrast swaps the colour tokens (stronger rules, white surfaces, no shadows) instead of filtering the page,
     so structure gets stronger and the crest is never filtered; Invert keeps the module's filter but turns the
     crest back (base.css), so the logo is shown as it is. */
  function apply(s) {
    root.style.filter = '';
    root.classList.toggle('a11y-contrast', !!s.contrast);
    root.classList.toggle('a11y-invert', !!s.invert);
    root.style.fontSize = s.size ? (100 + s.size * 10) + '%' : '';
    root.classList.toggle('a11y-opendyslexic', !!s.dyslexic);
    document.body.classList.toggle('a11y-opendyslexic', !!s.dyslexic);
  }
  McR.a11yApply = apply;

  McR.behaviors.a11ySettings = {
    attach: function (context) {
      var controls = McR.once('mcr-a11y', '.a11y-control[data-a11y-action]', context);
      if (!controls.length) return;
      var state = read();
      var sync = function () {
        controls.forEach(function (b) {
          var a = b.getAttribute('data-a11y-action');
          if (a === 'dyslexic' || a === 'contrast' || a === 'invert') {
            b.setAttribute('aria-pressed', String(!!state[a]));
            b.classList.toggle('is-active', !!state[a]);
          }
        });
      };
      apply(state);
      sync();
      controls.forEach(function (b) {
        b.addEventListener('click', function () {
          var a = b.getAttribute('data-a11y-action');
          if (a === 'dyslexic' || a === 'contrast' || a === 'invert') state[a] = !state[a];
          else if (a === 'text-increase') state.size = Math.min((state.size || 0) + 1, 5);
          else if (a === 'text-decrease') state.size = Math.max((state.size || 0) - 1, -2);
          else if (a === 'text-reset') state.size = 0;
          McR.store('localStorage', KEY, JSON.stringify(state));
          apply(state);
          sync();
        });
      });
    }
  };

  /* Translate: keep every copy of the selector in step. The GTranslate widget reads the googtrans cookie;
     on the public preview the choice opens Google's translation of this page, which is what the widget shows. */
  McR.behaviors.translate = {
    attach: function (context) {
      var selects = McR.once('mcr-gt', 'select[data-gt-select]', context);
      if (!selects.length) return;
      var all = function () { return Array.prototype.slice.call(document.querySelectorAll('select[data-gt-select]')); };
      selects.forEach(function (sel) {
        sel.addEventListener('change', function () {
          var value = sel.value;
          var label = sel.options[sel.selectedIndex].text;
          all().forEach(function (o) {
            o.value = value;
            var cur = o.parentNode.querySelector('.current');
            if (cur) cur.textContent = label;
          });
          var lang = value.split('|')[1] || 'en';
          try { document.cookie = 'googtrans=/en/' + lang + '; path=/; SameSite=Lax'; } catch (e) { /* cookies off */ }
          var local = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname) || location.protocol === 'file:';
          if (lang !== 'en' && !local) {
            location.href = 'https://translate.google.com/translate?sl=en&tl=' + encodeURIComponent(lang) + '&u=' + encodeURIComponent(location.href);
          }
        });
      });
    }
  };
})();
