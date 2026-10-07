/* McRoberts theme: School Calendar (view calendar, fullcalendar_view display page_1).
   The build renders the agenda (FullCalendar's listYear: every date with its events), which works without JS.
   This behaviour adds: today kept current when the page is opened on a later day, the rotation-code switch
   remembered, and the month grid (FullCalendar's dayGridMonth) built from the embedded #cal-data JSON, with the
   APG date-grid keyboard model (arrows, Home/End, Page Up/Down) and a day panel for phones.
   Drupal: Drupal.behaviors.mcrobertsCalendar; the JSON is the view's rows, cache-tagged per day. */
(function () {
  'use strict';
  var McR = window.McR;
  var D = McR.date;
  var esc = McR.esc;

  function chip(iso) {
    var d = D.parse(iso);
    return '<time class="date-chip" datetime="' + iso + '"><span class="m">' + D.MONTHS[d.getUTCMonth()] + '</span><span class="n">' +
      d.getUTCDate() + '</span><span class="d">' + D.DAYS[d.getUTCDay()].slice(0, 3) + '</span></time>';
  }

  /* Agenda: past / today classes for the real date, and a row for today when it has no events */
  function refreshAgenda(root, data, today) {
    var list = root.querySelector('[data-cal-list]');
    if (!list) return;
    var rows = Array.prototype.slice.call(list.querySelectorAll('.aday[data-date]'));
    var hasToday = false;
    rows.forEach(function (li) {
      var d = li.getAttribute('data-date');
      var tag = li.querySelector('.tag-today');
      if (d !== today && li.classList.contains('is-empty')) { li.remove(); return; }
      li.classList.toggle('is-past', d < today);
      li.classList.toggle('is-today', d === today);
      li.classList.toggle('is-code-only', li.hasAttribute('data-codes-only') && d !== today);
      if (d === today) {
        hasToday = true;
        li.setAttribute('aria-current', 'date');
        if (!tag) li.querySelector('.aday-body').insertAdjacentHTML('afterbegin', '<span class="tag-today">' + esc(data.labels.today) + '</span>');
      } else {
        li.removeAttribute('aria-current');
        if (tag) tag.remove();
      }
    });
    if (!hasToday && today >= data.first && today <= data.last) {
      var block = list.querySelector('#m-' + today.slice(0, 7));
      var ol = block && block.querySelector('.agenda');
      if (ol) {
        var after = Array.prototype.slice.call(ol.children).filter(function (li) { return li.getAttribute('data-date') > today; })[0];
        var html = '<li class="aday is-empty is-today' + (D.dow(today) % 6 === 0 ? ' is-weekend' : '') + '" id="d-' + today + '" data-date="' + today +
          '" aria-current="date">' + chip(today) + '<div class="aday-body"><span class="tag-today">' + esc(data.labels.today) + '</span></div></li>';
        if (after) after.insertAdjacentHTML('beforebegin', html); else ol.insertAdjacentHTML('beforeend', html);
      }
    }
    root.querySelectorAll('.cal-months a[data-month]').forEach(function (a) {
      a.classList.toggle('is-this-month', a.getAttribute('data-month') === today.slice(0, 7));
    });
  }

  /* The month chips: the filled one (aria-current) is the month on screen, in the list or in the grid; this month
     keeps its outline (.is-this-month), so the two never read as one */
  function markChip(root, ym) {
    root.querySelectorAll('.cal-months a[data-month]').forEach(function (a) {
      if (a.getAttribute('data-month') === ym) a.setAttribute('aria-current', 'true');
      else a.removeAttribute('aria-current');
    });
  }

  /* The agenda opens on this month and the next: the other months fold away (display: none via .is-folded), so the
     page stays short and the Notes, printable calendar and hub cards below it are within reach. A month chip shows
     its month (and scrolls to it); the button after the list unfolds the following month, labelled with that
     month's own heading. A URL into a folded month (#d-2026-09-21 from search) unfolds it. Without JS every month
     shows. */
  function monthWindow(root, today) {
    var list = root.querySelector('[data-cal-list]');
    if (!list) return;
    var blocks = Array.prototype.slice.call(list.querySelectorAll('.cal-mblock'));
    var cur = 'm-' + today.slice(0, 7);
    var start = blocks.map(function (b) { return b.id; }).indexOf(cur);
    if (start === -1) start = 0;                       /* outside the school year: from September */
    var target = location.hash ? document.getElementById(decodeURIComponent(location.hash.slice(1))) : null;
    var tBlock = target && target.closest && target.closest('.cal-mblock');
    if (tBlock && blocks.indexOf(tBlock) !== -1) start = blocks.indexOf(tBlock);
    var shown = {};
    var more = document.createElement('button');
    more.type = 'button';
    more.className = 'btn btn-ghost cal-more';
    list.insertAdjacentElement('afterend', more);
    var apply = function () {
      blocks.forEach(function (b, i) {
        b.classList.toggle('is-folded', !shown[i]);
        b.classList.remove('is-past-month');
      });
      var last = -1;
      blocks.forEach(function (b, i) { if (shown[i]) last = i; });
      var next = blocks[last + 1];
      more.hidden = !next;
      if (next) {
        var h = next.querySelector('.month-title');
        more.innerHTML = '<span>' + esc(h ? h.textContent : '') + '</span>' + McR.icon('chev');
      }
    };
    var current = start;
    var mark = function () { if (blocks[current]) markChip(root, blocks[current].id.slice(2)); };
    var showOnly = function (i) { shown = {}; shown[i] = true; if (i === start) shown[i + 1] = true; current = i; apply(); mark(); };
    showOnly(start);
    more.addEventListener('click', function () {
      var last = -1;
      blocks.forEach(function (b, i) { if (shown[i]) last = i; });
      if (!blocks[last + 1]) return;
      shown[last + 1] = true;
      apply();
      var h = blocks[last + 1].querySelector('.month-title');
      if (h) { h.setAttribute('tabindex', '-1'); h.focus({ preventScroll: true }); }
    });
    root.querySelectorAll('.cal-months a[data-month]').forEach(function (a) {
      a.addEventListener('click', function () {
        var i = blocks.map(function (b) { return b.id; }).indexOf('m-' + a.getAttribute('data-month'));
        if (i !== -1) showOnly(i);
      });
    });
    window.addEventListener('hashchange', function () {
      var t = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      var b = t && t.closest('.cal-mblock');
      var i = blocks.indexOf(b);
      if (i !== -1 && !shown[i]) { shown[i] = true; current = i; apply(); mark(); t.scrollIntoView(); }
    });
    return function (month) {
      more.hidden = month || !blocks.some(function (b, i) { return !shown[i] && i > start; });
      if (!month) { apply(); mark(); }
    };
  }

  /* Month grid --------------------------------------------------------------------------------------------- */
  function MonthGrid(root, data, today) {
    this.root = root;
    this.data = data;
    this.today = today;
    this.el = root.querySelector('[data-cal-grid]');
    this.byDay = {};
    var self = this;
    data.ev.forEach(function (e) { (self.byDay[e[0]] = self.byDay[e[0]] || []).push(e); });
    this.firstMonth = data.first.slice(0, 7);
    this.lastMonth = data.last.slice(0, 7);
    var start = today.slice(0, 7);
    if (start < this.firstMonth || start > this.lastMonth) start = this.firstMonth;
    this.month = start;
    this.selected = null;
  }

  MonthGrid.prototype.monthAdd = function (ym, n) {
    var y = +ym.slice(0, 4), m = +ym.slice(5, 7) - 1 + n;
    y += Math.floor(m / 12);
    m = ((m % 12) + 12) % 12;
    return y + '-' + String(m + 1).padStart(2, '0');
  };

  MonthGrid.prototype.defaultDay = function (ym) {
    if (this.today.slice(0, 7) === ym) return this.today;
    var self = this;
    var days = Object.keys(this.byDay).filter(function (d) {
      return d.slice(0, 7) === ym && self.byDay[d].some(function (e) { return e[2] !== 1; });
    }).sort();
    return days[0] || ym + '-01';
  };

  MonthGrid.prototype.render = function (ym, focusDay) {
    var self = this;
    this.month = ym;
    var first = D.parse(ym + '-01');
    var y = first.getUTCFullYear(), m = first.getUTCMonth();
    var daysIn = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
    var lead = first.getUTCDay();
    var title = D.MONTHS_LONG[m] + ' ' + y;
    var sel = focusDay && focusDay.slice(0, 7) === ym ? focusDay : this.defaultDay(ym);
    this.selected = sel;
    var head = D.DAYS.map(function (d, i) {
      return '<th scope="col"' + (i % 6 === 0 ? ' class="is-weekend"' : '') + '><abbr title="' + D.DAYS_LONG[i] + '">' + d + '</abbr></th>';
    }).join('');
    var cells = [], i;
    for (i = 0; i < lead; i++) cells.push('<td class="is-out"></td>');
    for (i = 1; i <= daysIn; i++) {
      var iso = ym + '-' + String(i).padStart(2, '0');
      var evs = this.byDay[iso] || [];
      var cls = [];
      if ((lead + i - 1) % 7 === 0 || (lead + i - 1) % 7 === 6) cls.push('is-weekend');
      if (iso < this.today) cls.push('is-past');
      if (iso === this.today) cls.push('is-today');
      if (evs.some(function (e) { return e[2] === 2; })) cls.push('is-noschool');
      var codes = evs.filter(function (e) { return e[2] === 1; });
      var real = evs.filter(function (e) { return e[2] !== 1; });
      cells.push('<td' + (cls.length ? ' class="' + cls.join(' ') + '"' : '') + '>' +
        '<button type="button" class="mday" data-date="' + iso + '" tabindex="' + (iso === sel ? '0' : '-1') + '" aria-pressed="' + (iso === sel) + '"' +
        (iso === this.today ? ' aria-current="date"' : '') + '>' +
        '<span class="mday-n" aria-hidden="true">' + i + '</span><span class="vh">' + D.long(iso) +
        (cls.indexOf('is-noschool') !== -1 ? ', ' + esc(this.data.labels.noschool) : '') + '</span>' +
        (iso === this.today ? '<span class="tag-today">' + esc(this.data.labels.today) + '</span>' : '') +
        codes.map(function (e) { return '<span class="mday-code">' + esc(e[1]) + '</span>'; }).join('') +
        '<span class="mday-evs">' + real.map(function (e) {
          /* a day off says so in words, not only in gold (WCAG 1.4.1), unless its title already does */
          var tag = e[2] === 2 && !/no school/i.test(e[1]) ? '<span class="tag-noschool" aria-hidden="true">' + esc(self.data.labels.noschool) + '</span>' : '';
          return '<span class="mev' + (e[2] === 2 ? ' mev--ns' : '') + '">' + esc(e[1]) + '</span>' + tag;
        }).join('') + '</span></button></td>');
    }
    while (cells.length % 7) cells.push('<td class="is-out"></td>');
    var rows = '';
    for (i = 0; i < cells.length; i += 7) rows += '<tr>' + cells.slice(i, i + 7).join('') + '</tr>';
    markChip(this.root, ym);
    var canPrev = ym > this.firstMonth, canNext = ym < this.lastMonth;
    this.el.innerHTML =
      '<div class="mg-head"><button type="button" class="mg-btn mg-prev" data-mg="prev"' + (canPrev ? '' : ' disabled') + '>' + McR.icon('arrow') +
      '<span class="vh">Previous</span></button><h2 class="mg-title" id="mg-title" aria-live="polite">' + title + '</h2>' +
      '<button type="button" class="mg-btn" data-mg="next"' + (canNext ? '' : ' disabled') + '>' + McR.icon('arrow') + '<span class="vh">Next</span></button>' +
      '<button type="button" class="mg-today" data-mg="today">' + esc(this.data.labels.today.toLowerCase()) + '</button></div>' +
      '<div class="mg-scroll"><table class="mg-table" aria-labelledby="mg-title"><thead><tr>' + head + '</tr></thead><tbody>' + rows + '</tbody></table></div>' +
      '<div class="mg-detail" data-mg-detail></div>';
    this.detail(sel);
  };

  MonthGrid.prototype.detail = function (iso) {
    var self = this;
    var box = this.el.querySelector('[data-mg-detail]');
    if (!box) return;
    var evs = this.byDay[iso] || [];
    var real = evs.filter(function (e) { return e[2] !== 1; });
    var codes = evs.filter(function (e) { return e[2] === 1; });
    var link = function (e, inner) { return e[3] ? '<a href="' + esc(e[3]) + '">' + inner + '</a>' : inner; };
    box.innerHTML = '<div class="aday' + (iso === this.today ? ' is-today' : '') + (real.some(function (e) { return e[2] === 2; }) ? ' is-noschool' : '') + '">' + chip(iso) +
      '<div class="aday-body"><p class="mg-detail-date">' + D.long(iso) + '</p>' +
      (real.length ? '<ul class="aday-events">' + real.map(function (e) {
        var tag = e[2] === 2 && !/no school/i.test(e[1]) ? ' <span class="tag-noschool">' + esc(self.data.labels.noschool) + '</span>' : '';
        return '<li class="ev' + (e[2] === 2 ? ' ev--noschool' : '') + '">' + link(e, '<span>' + esc(e[1]) + '</span>') + tag + '</li>';
      }).join('') + '</ul>' : '') +
      codes.map(function (e) { return '<span class="aday-code">' + link(e, esc(e[1])) + '</span>'; }).join('') + '</div></div>';
  };

  MonthGrid.prototype.select = function (iso, focus) {
    if (iso.slice(0, 7) !== this.month) {
      if (iso.slice(0, 7) < this.firstMonth || iso.slice(0, 7) > this.lastMonth) return;
      this.render(iso.slice(0, 7), iso);
    } else {
      this.selected = iso;
      this.el.querySelectorAll('.mday').forEach(function (b) {
        var on = b.getAttribute('data-date') === iso;
        b.setAttribute('aria-pressed', String(on));
        b.tabIndex = on ? 0 : -1;
      });
      this.detail(iso);
    }
    var btn = this.el.querySelector('.mday[data-date="' + iso + '"]');
    if (btn && focus) btn.focus();
  };

  MonthGrid.prototype.bind = function () {
    var self = this;
    this.el.addEventListener('click', function (e) {
      var b = e.target.closest('button');
      if (!b || !self.el.contains(b)) return;
      var act = b.getAttribute('data-mg');
      if (act === 'prev') self.render(self.monthAdd(self.month, -1));
      else if (act === 'next') self.render(self.monthAdd(self.month, 1));
      else if (act === 'today') self.render(self.today.slice(0, 7) >= self.firstMonth && self.today.slice(0, 7) <= self.lastMonth ? self.today.slice(0, 7) : self.month, self.today);
      else if (b.classList.contains('mday')) self.select(b.getAttribute('data-date'), false);
      if (act) { var keep = self.el.querySelector('[data-mg="' + act + '"]'); if (keep && !keep.disabled) keep.focus(); else { var s = self.el.querySelector('.mday[tabindex="0"]'); if (s) s.focus(); } }
    });
    this.el.addEventListener('keydown', function (e) {
      var b = e.target.closest('.mday');
      if (!b) return;
      var iso = b.getAttribute('data-date'), dow = D.dow(iso), to = null;
      switch (e.key) {
        case 'ArrowLeft': to = D.add(iso, -1); break;
        case 'ArrowRight': to = D.add(iso, 1); break;
        case 'ArrowUp': to = D.add(iso, -7); break;
        case 'ArrowDown': to = D.add(iso, 7); break;
        case 'Home': to = D.add(iso, -dow); break;
        case 'End': to = D.add(iso, 6 - dow); break;
        case 'PageUp': to = self.monthAdd(iso.slice(0, 7), -1) + iso.slice(7); break;
        case 'PageDown': to = self.monthAdd(iso.slice(0, 7), 1) + iso.slice(7); break;
        default: return;
      }
      e.preventDefault();
      if (!/-\d\d$/.test(to) || isNaN(D.parse(to))) return;
      var p = D.parse(to);
      if (D.iso(p) !== to) to = D.iso(new Date(Date.UTC(p.getUTCFullYear(), p.getUTCMonth(), 0))); /* Feb 30 → Feb 28 */
      self.select(to, true);
    });
  };

  McR.behaviors.calendar = {
    attach: function (context) {
      McR.once('mcr-calendar', '[data-calendar]', context).forEach(function (root) {
        var node = root.querySelector('#cal-data');
        var data;
        try { data = JSON.parse(node.textContent); } catch (e) { return; }
        var today = D.now().iso;
        if (today !== data.built) refreshAgenda(root, data, today);
        var listMode = monthWindow(root, today);

        /* rotation codes on or off, remembered */
        var codes = root.querySelector('[data-cal-codes]');
        var applyCodes = function () { root.classList.toggle('hide-codes', !codes.checked); };
        if (codes) {
          var saved = McR.store('localStorage', 'mcr-cal-codes');
          if (saved === '0') codes.checked = false;
          applyCodes();
          codes.addEventListener('change', function () { applyCodes(); McR.store('localStorage', 'mcr-cal-codes', codes.checked ? '1' : '0'); });
        }

        /* list / month */
        var views = root.querySelector('[data-cal-views]');
        var list = root.querySelector('[data-cal-list]');
        var gridEl = root.querySelector('[data-cal-grid]');
        var grid = null;
        var show = function (view, remember) {
          var month = view === 'month';
          if (month && !grid) { grid = new MonthGrid(root, data, today); grid.render(grid.month); grid.bind(); }
          list.hidden = month;
          gridEl.hidden = !month;
          if (listMode) listMode(month);
          root.classList.toggle('is-month', month);
          views.querySelectorAll('[data-view]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-view') === view)); });
          if (remember) McR.store('localStorage', 'mcr-cal-view', view);
        };
        if (views && list && gridEl) {
          views.addEventListener('click', function (e) {
            var b = e.target.closest('[data-view]');
            if (b) show(b.getAttribute('data-view'), true);
          });
          if (McR.store('localStorage', 'mcr-cal-view') === 'month') show('month', false);
          /* the month chips scroll the agenda, or turn the grid to that month */
          root.querySelectorAll('.cal-months a[data-month]').forEach(function (a) {
            a.addEventListener('click', function (e) {
              if (!grid || gridEl.hidden) return;
              e.preventDefault();
              var ym = a.getAttribute('data-month');
              grid.render(ym, grid.defaultDay(ym));
              gridEl.scrollIntoView({ block: 'start' });
            });
          });
        }
      });
    }
  };
})();
