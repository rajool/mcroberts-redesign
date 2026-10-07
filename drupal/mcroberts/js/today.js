/* McRoberts theme: today-dependent parts of the front page.
   The build renders Today (bell schedule + rotation code), the Collaboration Days chips, the live sub-lines of
   Helpful Links and Upcoming Events for the build date. When the page is opened on a later day, this script
   re-renders the same markup from the small JSON embedded in the page (#today-data), so the page stays correct.
   Drupal: Today = view upcoming_events with a date contextual filter (rotation code) + a custom block holding the
   timetable; Upcoming Events = upcoming_events:block_1 with the rotation codes excluded; both are cache-tagged per day. */
(function () {
  'use strict';
  var McR = window.McR;
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'June', 'July', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec'];
  var MONTHS_LONG = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  var DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  var DAYS_LONG = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function parse(iso) { var p = iso.split('-'); return new Date(Date.UTC(+p[0], +p[1] - 1, +p[2])); }
  function iso(d) { return d.toISOString().slice(0, 10); }
  function addDays(isoDate, n) { var d = parse(isoDate); d.setUTCDate(d.getUTCDate() + n); return iso(d); }
  function dow(isoDate) { return parse(isoDate).getUTCDay(); }
  function minutes(range) {
    var m = range.split('-').map(function (t) {
      var hm = t.split(':'), h = +hm[0];
      if (h < 7) h += 12;
      return h * 60 + (+hm[1] || 0);
    });
    return Math.max(m[1] - m[0], 20);
  }
  var ICON = function (name, cls) { return '<svg class="icon' + (cls ? ' ' + cls : '') + '" aria-hidden="true" focusable="false"><use href="#i-' + name + '"/></svg>'; };

  function render(data, now) {
    var root = document;
    var today = now.iso;
    var q = function (k) { return root.querySelector('[data-t="' + k + '"]'); };
    var day = McR.school.day(data, now);           /* today until its last bell, then the next school day */
    /* once the card has moved on to a later day, today's events are over: Next, the School Calendar tile and
       Upcoming Events start tomorrow (a day off in between, such as Thanksgiving Monday, is the true next item) */
    var from = (day && day !== today) ? addDays(today, 1) : today;
    var events = data.events.filter(function (e) { return e.d >= from; });

    /* Today head */
    if (day) {
      var dt = parse(day);
      var info = McR.school.blocks(data, day);
      var code = info.code;
      var rot = info.rot;
      var eyebrow = q('eyebrow');
      /* Today, or no eyebrow at all for the next school day (its date line says which day it is) */
      if (eyebrow) eyebrow.classList.toggle('is-empty', day !== today);   /* the line stays: nothing shifts */
      var date = q('date');
      if (date) { date.setAttribute('datetime', day); date.textContent = DAYS_LONG[dt.getUTCDay()] + ', ' + MONTHS_LONG[dt.getUTCMonth()] + ' ' + dt.getUTCDate(); }
      var chips = q('chips');
      if (chips) chips.innerHTML = (rot ? '<li class="chip">' + esc(rot) + '</li>' : '') + '<li class="chip chip--forest">' + esc(code) + '</li>';
      var rows = rot && data.bell[rot] && data.bell[rot][info.col];
      var blocks = q('blocks');
      if (blocks && rows) {
        blocks.innerHTML = rows.map(function (r) {
          var cls = r[1] === 'PLT' ? ' class="is-plt"' : r[1] === 'Lunch' ? ' class="is-lunch"' : /Collab/.test(r[1]) ? ' class="is-collab"' : '';
          var blk = /^[ABCD]$/.test(r[1]) ? ' data-blk="' + r[1].toLowerCase() + '"' : '';
          return '<li style="--m:' + minutes(r[0]) + '"' + cls + blk + '><b>' + esc(r[1]) + '</b><time>' + esc(r[0]) + '</time></li>';
        }).join('');
      }
      var week = q('week');
      if (week) {
        var monday = addDays(day, 1 - dow(day));
        var out = '';
        for (var i = 0; i < 5; i++) {
          var d = addDays(monday, i), c = data.codes[d] || '', pd = parse(d);
          var cls = [];
          if (d === today) { cls.push('is-today'); if (day !== today) cls.push('is-quiet'); }   /* a later day is shown: today in outline */
          else if (d < today) cls.push('is-past');
          if (d === day && d !== today) cls.push('is-shown');   /* the day whose blocks the card shows */
          if (!c) cls.push('is-off');
          out += '<li' + (cls.length ? ' class="' + cls.join(' ') + '"' : '') + (d === today ? ' aria-current="date"' : '') + '>' +
            (d === today ? '<span class="tag-today">' + esc(data.labels.today) + '</span>' : '') +
            '<span class="d">' + DAYS[pd.getUTCDay()] + '</span><span class="n">' + pd.getUTCDate() + '</span><span class="c">' + esc(c) + '</span></li>';
        }
        week.innerHTML = out;
      }
      var tileBell = q('tile-bell');
      if (tileBell) tileBell.innerHTML = (rot ? '<span>' + esc(rot) + '</span> · ' : '') + '<span>' + esc(code) + '</span>';
    }

    /* Collaboration Days: past struck through, the next one highlighted */
    var collab = q('collab');
    if (collab) {
      var nextSet = false;
      collab.innerHTML = data.collab.map(function (c) {
        var cls = '', past = c.d < today;
        if (past) cls = ' class="is-past"';
        else if (!nextSet) { cls = ' class="is-next"'; nextSet = true; }   /* not today: a highlight, no aria-current */
        var t = '<time datetime="' + c.d + '">' + esc(c.t) + '</time>';
        return '<li' + cls + '>' + (past ? '<s>' + t + '</s>' : t) + '</li>';
      }).join('');
    }

    /* Next event line + School Calendar tile */
    var first = events[0];
    var next = q('next');
    if (next && first) {
      var fd = parse(first.d);
      next.setAttribute('href', first.u);
      next.querySelector('.t').textContent = first.t;
      var arrow = next.querySelector(':scope > svg use');
      if (arrow) arrow.setAttribute('href', first.x ? '#i-ext' : '#i-arrow');
      var t = next.querySelector('time');
      t.setAttribute('datetime', first.d);
      t.textContent = DAYS[fd.getUTCDay()] + ', ' + MONTHS[fd.getUTCMonth()] + ' ' + fd.getUTCDate();
    }
    var tileCal = q('tile-calendar');
    if (tileCal && first) {
      var f2 = parse(first.d);
      tileCal.innerHTML = '<span>' + esc(first.t) + '</span> · <time datetime="' + first.d + '">' + MONTHS[f2.getUTCMonth()] + ' ' + f2.getUTCDate() + '</time>';
    }

    /* Upcoming Events */
    var list = q('events');
    if (list) {
      list.innerHTML = events.slice(0, data.n).map(function (e) {
        var d = parse(e.d);
        var tag = e.o && !/no school/i.test(e.t) ? ' <span class="tag-noschool">' + esc(data.labels.noschool) + '</span>' : '';
        return '<li class="event' + (e.o ? ' event--noschool' : '') + '"><a href="' + esc(e.u) + '">' +
          '<time class="date-chip" datetime="' + e.d + '"><span class="m">' + MONTHS[d.getUTCMonth()] + '</span><span class="n">' + d.getUTCDate() + '</span><span class="d">' + DAYS[d.getUTCDay()] + '</span></time>' +
          '<span class="title"><span>' + esc(e.t) + '</span>' + (e.x ? ICON('ext', 'ext-mark') : '') + tag + '</span></a></li>';
      }).join('');
    }
  }

  McR.behaviors.today = {
    attach: function (context) {
      McR.once('mcr-today', '#today-data', context).forEach(function (node) {
        var data;
        try { data = JSON.parse(node.textContent); } catch (e) { return; }
        /* always: after the last bell the card moves on to the next school day, whatever day the page was built */
        render(data, McR.date.now());
      });
    }
  };
  McR.todayRender = render; /* exposed for testing a moment: McR.todayRender(data, {iso: '2026-10-16', min: 600}) */
})();
