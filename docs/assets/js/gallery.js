/* McRoberts theme: image galleries and the banner reel.
   1. Gallery (the live site's colorbox field formatter): [data-gallery] links open a native <dialog> lightbox
      with the image, its caption, Previous / Next (also the arrow keys) and Close; Esc and the backdrop close it
      and focus returns to the image that opened it. Without JS each link opens the image itself.
   2. Reel (the Library banner slideshow): a scroll-snap track that scrolls by touch, trackpad and keyboard
      without JS; this adds Previous / Next buttons and the position dots. It never moves on its own.
   Drupal: Drupal.behaviors.mcrobertsGallery, attached with the gallery and slideshow libraries. */
(function () {
  'use strict';
  var McR = window.McR;
  var esc = McR.esc;
  var box = null, list = [], at = 0;

  function lightbox() {
    if (box) return box;
    box = document.createElement('dialog');
    box.className = 'lightbox';
    box.setAttribute('aria-labelledby', 'lightbox-cap');
    box.innerHTML = '<figure class="lightbox-fig"><img alt="" decoding="async"><figcaption id="lightbox-cap"></figcaption></figure>' +
      '<p class="lightbox-n" aria-hidden="true"></p>' +
      '<button type="button" class="lightbox-btn lightbox-prev" data-lb="prev">' + McR.icon('arrow') + '<span class="vh">Previous</span></button>' +
      '<button type="button" class="lightbox-btn lightbox-next" data-lb="next">' + McR.icon('arrow') + '<span class="vh">Next</span></button>' +
      '<button type="button" class="close-btn lightbox-close" data-lb="close">' + McR.icon('close') + 'Close</button>';
    document.body.appendChild(box);
    box.addEventListener('click', function (e) {
      if (e.target === box) { box.close(); return; }
      var b = e.target.closest('[data-lb]');
      if (!b) return;
      var act = b.getAttribute('data-lb');
      if (act === 'close') box.close();
      else show(at + (act === 'next' ? 1 : -1));
    });
    box.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { e.preventDefault(); show(at + 1); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); show(at - 1); }
    });
    box.addEventListener('close', function () { var o = list[at]; if (o) o.focus(); });
    return box;
  }

  function show(i) {
    at = (i + list.length) % list.length;
    var a = list[at], img = box.querySelector('img');
    var cap = a.closest('figure') && a.closest('figure').querySelector('figcaption');
    var thumb = a.querySelector('img');
    img.src = a.getAttribute('data-lightbox');
    img.alt = thumb ? thumb.alt : '';
    if (thumb) { img.width = thumb.width || 480; img.height = thumb.height || 480; }
    box.querySelector('figcaption').innerHTML = cap ? esc(cap.textContent) : '';
    box.querySelector('.lightbox-n').textContent = (at + 1) + ' / ' + list.length;
  }

  McR.behaviors.gallery = {
    attach: function (context) {
      McR.once('mcr-gallery', '[data-gallery]', context).forEach(function (g) {
        var links = Array.prototype.slice.call(g.querySelectorAll('a[data-lightbox]'));
        links.forEach(function (a, i) {
          a.addEventListener('click', function (e) {
            if (e.metaKey || e.ctrlKey || e.shiftKey || typeof HTMLDialogElement !== 'function') return;
            e.preventDefault();
            list = links;
            lightbox();
            show(i);
            box.showModal();
            box.querySelector('[data-lb="close"]').focus();
          });
        });
      });

      McR.once('mcr-reel', '[data-reel]', context).forEach(function (reel) {
        var track = reel.querySelector('[data-reel-track]');
        var nav = reel.querySelector('.reel-nav');
        var slides = track ? Array.prototype.slice.call(track.children) : [];
        if (!track || !nav || slides.length < 2) return;
        var dots = Array.prototype.slice.call(nav.querySelectorAll('.reel-dots li'));
        var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        var current = function () { return Math.round(track.scrollLeft / Math.max(1, slides[0].offsetWidth)); };
        var go = function (i) {
          var n = (i + slides.length) % slides.length;
          track.scrollTo({ left: slides[n].offsetLeft - slides[0].offsetLeft, behavior: reduce ? 'auto' : 'smooth' });
        };
        var mark = function () { var c = current(); dots.forEach(function (d, i) { d.classList.toggle('is-on', i === c); }); };
        nav.querySelector('[data-reel-prev]').addEventListener('click', function () { go(current() - 1); });
        nav.querySelector('[data-reel-next]').addEventListener('click', function () { go(current() + 1); });
        var t = null;
        track.addEventListener('scroll', function () { clearTimeout(t); t = setTimeout(mark, 60); }, { passive: true });
        mark();
      });
    }
  };
})();
