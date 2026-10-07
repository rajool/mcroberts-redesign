/* McRoberts theme: Bell Schedule (custom block bell_schedule on /information/bell-schedule).
   The build prints the timetable tables, the semester table and the Today card for the build date. This keeps
   them true on the day the page is read, on the school's clock (America/Vancouver):
   - the Today card: date, rotation, the day's code (from the calendar feed), its blocks, and Now / Next;
   - the rotation table column of today, with the current and next block marked;
   - the current rotation in the semester table and the Collaboration Days (past struck, next highlighted).
   Re-checks every 30 seconds while the page is visible. ?today=YYYY-MM-DD&time=HH:MM simulates a moment.
   Drupal: Drupal.behaviors.mcrobertsBell, attached with the block's library. */
(function () {
  'use strict';
  var McR = window.McR;
  var D = McR.date;
  var esc = McR.esc;
  var COLS = { 1: 'MON', 2: 'TUE', 3: 'WED', 4: 'THU', 5: 'FRI' };

  var S = McR.school;
  function minutes(r) { return Math.max(r.to - r.from, 20); }

  function render(root, data) {
    var now = D.now();
    var today = now.iso;
    var q = function (k) { return root.querySelector('[data-b="' + k + '"]'); };
    /* the shared rule (js/behaviors.js McR.school.day): today until its last bell, then the next school day */
    var day = S.day(data, now);
    var info = day ? S.blocks(data, day) : null;
    var nowRow = -1, nextRow = -1;
    if (info && day === today) {
      info.rows.forEach(function (r, i) {
        if (now.min >= r.from && now.min < r.to) nowRow = i;
        if (nextRow < 0 && r.from > now.min) nextRow = i;
      });
    } else if (info) {
      nextRow = 0;
    }

    /* Today card */
    if (info) {
      var eb = q('eyebrow');
      /* Today, or no eyebrow at all for the next school day (its date line says which day it is) */
      if (eb) eb.classList.toggle('is-empty', day !== today);   /* the line stays: nothing shifts */
      var dt = q('date');
      if (dt) { dt.setAttribute('datetime', day); dt.textContent = D.long(day); }
      var chips = q('chips');
      if (chips) chips.innerHTML = (info.rot ? '<li class="chip">' + esc(info.rot) + '</li>' : '') + '<li class="chip chip--forest">' + esc(info.code) + '</li>';
      var blocks = q('blocks');
      if (blocks) {
        blocks.innerHTML = info.rows.map(function (r, i) {
          var cls = r.label === 'PLT' ? 'is-plt' : r.label === 'Lunch' ? 'is-lunch' : /Collab/.test(r.label) ? 'is-collab' : '';
          if (day === today && i === nowRow) cls += ' is-now';
          if (i === nextRow) cls += ' is-next';
          var blk = /^[ABCD]$/.test(r.label) ? ' data-blk="' + r.label.toLowerCase() + '"' : '';
          return '<li style="--m:' + minutes(r) + '"' + (cls.trim() ? ' class="' + cls.trim() + '"' : '') + blk + '><b>' + esc(r.label) + '</b><time>' + esc(r.range) + '</time></li>';
        }).join('');
      }
      var nn = q('nn');
      if (nn) {
        var fill = function (li, r) {
          li.hidden = !r;
          if (!r) return;
          li.querySelector('b').textContent = r.label;
          li.querySelector('time').textContent = r.range;
        };
        fill(nn.querySelector('.is-now'), day === today && nowRow >= 0 ? info.rows[nowRow] : null);
        fill(nn.querySelector('.is-next'), nextRow >= 0 ? info.rows[nextRow] : null);
        nn.hidden = nowRow < 0 && nextRow < 0;
      }
    }

    /* Rotation tables: today's column, current and next block */
    root.querySelectorAll('.rot-table .is-today, .rot-table .is-now, .rot-table .is-next').forEach(function (el) {
      el.classList.remove('is-today', 'is-now', 'is-next');
    });
    root.querySelectorAll('.rot-table .tag-today').forEach(function (t) { t.remove(); });
    if (info && day === today) {
      var weekdayCol = COLS[D.dow(today)];
      var table = root.querySelector('.rot-table[data-rot="' + info.rot + '"]');
      if (table && (info.col === weekdayCol || info.col === 'Collaboration Days')) {
        var th = table.querySelector('th[data-col="' + info.col + '"]');
        var td = table.querySelector('td[data-col="' + info.col + '"]');
        if (th) {
          th.classList.add('is-today');
          th.insertAdjacentHTML('afterbegin', '<span class="tag-today">' + esc(data.labels.today) + '</span>');
          /* a frame narrower than its table (phones) opens on today's column, once; the visitor's own scroll stays */
          var w = th.closest('.rot-wrap');
          if (w && !w.hasAttribute('data-at-today') && w.scrollWidth > w.clientWidth + 1) {
            w.setAttribute('data-at-today', '');
            w.scrollLeft += th.getBoundingClientRect().left - w.getBoundingClientRect().left - 8;
          }
        }
        if (td) {
          td.classList.add('is-today');
          var lis = td.querySelectorAll('.blk');
          if (nowRow >= 0 && lis[nowRow]) lis[nowRow].classList.add('is-now');
          if (nextRow >= 0 && lis[nextRow]) lis[nextRow].classList.add('is-next');
        }
      }
    }

    /* Semester table: the rotation running today */
    root.querySelectorAll('.sem-rot[data-from]').forEach(function (td) {
      td.classList.toggle('is-current', today >= td.getAttribute('data-from') && today <= td.getAttribute('data-to'));
    });

    /* Collaboration Days */
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
  }

  McR.behaviors.bellSchedule = {
    attach: function (context) {
      McR.once('mcr-bell', '[data-bell]', context).forEach(function (root) {
        var node = root.querySelector('#bell-data');
        var data;
        try { data = JSON.parse(node.textContent); } catch (e) { return; }
        render(root, data);
        setInterval(function () { if (!document.hidden) render(root, data); }, 30000);
        document.addEventListener('visibilitychange', function () { if (!document.hidden) render(root, data); });
      });
    }
  };
})();
