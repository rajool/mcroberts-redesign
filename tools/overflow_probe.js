/* Text-size overflow probe: paste into the console (or DevTools evaluate) on any built page, at each width
   (360, 390, 768, 1024, 1280, 1440). For the site's own Text increase steps 0..5 it applies the size and reports
   whether the page scrolls sideways (scrollWidth > clientWidth) and the innermost elements past the right edge.
   Every row must read ok: true. The text size is reset afterwards. */
() => {
  const doc = document.documentElement;
  const name = (el) => {
    const cls = (e) => (e.getAttribute('class') || '').trim().split(/\s+/)[0];
    const p = el.parentElement && el.parentElement.closest('[class]');
    return (p ? '.' + cls(p) + ' > ' : '') + el.tagName.toLowerCase() + (cls(el) ? '.' + cls(el) : '');
  };
  const out = [];
  for (let s = 0; s <= 5; s++) {
    window.McR.a11yApply({ size: s });
    window.dispatchEvent(new Event('resize'));
    void doc.offsetWidth;
    const cw = doc.clientWidth, sw = doc.scrollWidth, bad = [];
    if (sw > cw) {
      document.querySelectorAll('body *').forEach((el) => {
        const r = el.getBoundingClientRect();
        if (!r.width || r.right <= cw + 1 || getComputedStyle(el).position === 'fixed') return;
        if (Array.from(el.children).some((k) => k.getBoundingClientRect().right > cw + 1)) return;
        bad.push(name(el) + ' ' + Math.round(r.right));
      });
    }
    out.push(s + ':' + (sw <= cw ? 'ok' : sw + '>' + cw + ' ' + [...new Set(bad)].slice(0, 6).join(' | ')));
  }
  window.McR.a11yApply({ size: 0 });
  window.dispatchEvent(new Event('resize'));
  return out;
}
