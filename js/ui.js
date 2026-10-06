/* ===========================================================================
   ui.js — the bits every page shares: the header, the drifting background,
   colours, money formatting, and a little pop-up message.

   Loaded on every page, after data.js and before the page's own script.
   =========================================================================== */

var UI = (function () {
  'use strict';

  /* The five pages, in nav order. Each has its own accent colour, so you always
     know which part of the app you're in without reading the header. */
  var PAGES = [
    { id: 'dashboard', file: 'index.html',    key: 'nav.dashboard', icon: '◉' },
    { id: 'meals',     file: 'meals.html',    key: 'nav.meals',     icon: '✚' },
    { id: 'compare',   file: 'compare.html',  key: 'nav.compare',   icon: '⇄' },
    { id: 'game',      file: 'game.html',     key: 'nav.game',      icon: '★' },
    { id: 'settings',  file: 'settings.html', key: 'nav.settings',  icon: '⚙' }
  ];

  /* admin.html مش في القايمة دي عن قصد.

     صفحة الأدمن أداة تشغيل، مش جزء من التطبيق: بتكلّم سيرفر محلي،
     وبتزحف على موقع تاني، وبتمسح جداول. اليوزر العادي ماينفعش يشوف
     زرار بيبدأ زحف 36 دقيقة. الوصول ليها بالرابط المباشر، والباكند
     بيتحقق من الإيميل قبل أي تعديل. */

  /* Market colours. Fixed slots by the market's own order number — never
     hashed, never recycled — so a market keeps its colour when another one is
     deleted. This exact sequence is checked for colour-blind separation:
     the closest adjacent pair is ΔE 9.1 under protanopia. Three of them sit
     under 3:1 contrast on white, which is why a market's NAME is always shown
     next to its dot and every bar carries its value as text. */
  var MARKET_COLORS = [
    '#2a78d6', '#eb6834', '#1baf7a', '#eda100',
    '#e87ba4', '#008300', '#4a3aa7', '#e34948'
  ];

  function marketColor(market) {
    var slot = (Number(market && market.order ? market.order : 1) - 1) % MARKET_COLORS.length;
    if (slot < 0) slot += MARKET_COLORS.length;
    return MARKET_COLORS[slot];
  }

  /* ============================================================== helpers == */

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function money(value) {
    var n = Number(value);
    if (!isFinite(n)) return '—';
    return n.toLocaleString('tr-TR', {
      minimumFractionDigits: n % 1 === 0 ? 0 : 2,
      maximumFractionDigits: 2
    }) + ' ₺';
  }

  function reducedMotion() {
    return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }

  function qtyLabel(ing) {
    return [ing.qty, ing.unit].filter(Boolean).join(' ');
  }

  /** Metres under a kilometre, kilometres above it — nobody reads "1502 m". */
  function distance(metres) {
    if (metres == null) return '';
    return metres < 1000
      ? Math.round(metres) + ' m'
      : (metres / 1000).toFixed(1) + ' km';
  }

  function dot(market) {
    return '<span class="dot" style="background:' + marketColor(market) + '"></span>';
  }

  function marketTag(market) {
    return '<span class="market-name">' + dot(market) + esc(market.name) + '</span>';
  }


  /* ============================================================ language == */

  /**
   * شريط صغير فوق على الشمال. مش جوه الهيدر عن قصد — اللغة إعداد
   * للمتصفح كله، مش جزء من الصفحة، واليوزر اللي مش فاهم الواجهة
   * محتاج يلاقيه من غير ما يقرا حاجة.
   *
   * left ثابتة مش inset-inline-start: المبدّل المفروض يفضل في نفس
   * المكان لما اللغة تتقلب لعربي، وإلا اللي بدّل بالغلط مش هيلاقيه.
   */
  function buildLangBar() {
    return '<div class="langbar">' +
      '<span class="langbar-globe" aria-hidden="true">\u2295</span>' +
      '<select id="lang-select" aria-label="' + esc(T('chrome.language')) + '">' +
        I18N.LANGS.map(function (l) {
          return '<option value="' + l.code + '"' +
            (l.code === I18N.lang() ? ' selected' : '') + '>' + esc(l.label) + '</option>';
        }).join('') +
      '</select>' +
    '</div>';
  }

  function wireLangBar() {
    var select = document.getElementById('lang-select');
    if (select) {
      select.addEventListener('change', function () { I18N.set(select.value); });
    }
  }

  /* ================================================================ chrome == */

  /**
   * هيدر صفحة الأدمن: شريط بسيط فيه رجوع للتطبيق، من غير nav.
   *
   * ومن غير DB كمان — صفحة الأدمن مابتحمّلش data.js، فما ينفعش
   * نسأل عن منطقة اليوزر هنا.
   */
  function buildBareHeader(title) {
    return '<header class="topbar topbar-bare">' +
      '<span class="brand"><span class="brand-mark">▤</span>' + esc(title) + '</span>' +
      '<span class="top-right">' +
        accountPill() +
        '<a class="where" href="index.html">← ' + esc(T('chrome.backToApp')) + '</a>' +
      '</span>' +
    '</header>';
  }

  /** Builds the header and nav, and marks the page you're on. */
  function buildHeader(current) {
    var links = PAGES.map(function (p) {
      var active = p.id === current ? ' active' : '';
      return '<a class="nav-link nav-' + p.id + active + '" href="' + p.file + '">' +
        '<span class="nav-icon">' + p.icon + '</span>' + T(p.key) + '</a>';
    }).join('');

    var where = DB.settings().location;

    return '<header class="topbar">' +
      '<a class="brand" href="index.html"><span class="brand-mark">🛒</span>Cheapest Basket</a>' +
      '<span class="top-right">' +
        accountPill() +
        '<a class="where" href="settings.html" title="' + esc(T('set.whereShop')) + '">' +
          (where ? '📍 ' + esc(where) : '📍 ' + esc(T('chrome.setArea'))) +
        '</a>' +
      '</span>' +
    '</header>' +
    '<nav class="nav">' + links + '</nav>';
  }

  /**
   * One pill, three possible jobs: invite you to sign in, report how syncing
   * is going, or stay out of the way when accounts aren't set up at all.
   */
  function accountPill() {
    if (!(window.CLOUD && CLOUD.on())) return '';

    if (!AUTH.signedIn()) {
      return '<a class="sync-pill" href="login.html" title="' + esc(T('chrome.signIn')) + '">' +
        '<span class="sync-dot"></span>' + T('chrome.signIn') + '</a>';
    }

    return '<a class="sync-pill" href="login.html" id="sync-pill" ' +
      'title="' + esc(T('chrome.signedInAs') + ' ' + AUTH.email()) + '">' +
      '<span class="sync-dot"></span><span id="sync-text">' + T('chrome.syncing') + '</span></a>';
  }

  /** Keeps that pill honest about what syncing is actually doing. */
  var WORDS = {
    syncing: [T('chrome.syncing'), 'busy'],
    saved: [T('chrome.synced'), 'ok'],
    error: [T('chrome.offline'), 'bad'],
    // Not the same thing as Offline, and it mustn't look like it: this one
    // is asking you to do something.
    expired: [T('chrome.signIn'), 'bad']
  };

  // The listener is registered once for the life of the page. refreshHeader()
  // runs on every sign-in and sign-out, and registering again each time would
  // pile up copies that all fire on every status change.
  var watching = false;

  function watchSync() {
    if (!(window.CLOUD && CLOUD.on() && AUTH.signedIn())) return;

    if (!watching) {
      watching = true;
      CLOUD.onStatus(function (state, detail) {
        if (state === 'expired') {
          // CLOUD has already cleared the session, so redrawing the header
          // turns the pill into a "Sign in" link on its own.
          refreshHeader();
          toast(detail || T('chrome.expired'), 'bad');
          return;
        }

        var pill = document.getElementById('sync-pill');
        var text = document.getElementById('sync-text');
        if (!pill || !text) return;
        var word = WORDS[state] || WORDS.syncing;
        text.textContent = word[0];
        pill.className = 'sync-pill sync-' + word[1];
        pill.title = state === 'error' && detail
          ? detail
          : T('chrome.signedInAs') + ' ' + AUTH.email();
      });
    }

    CLOUD.sync();
  }

  /** Slow-drifting colour in the background, so the page is never quite still. */
  function buildBackdrop() {
    return '<div class="backdrop" aria-hidden="true">' +
      '<span class="blob blob-1"></span>' +
      '<span class="blob blob-2"></span>' +
      '<span class="blob blob-3"></span>' +
    '</div>';
  }

  /**
   * Call once at the top of every page script.
   * Reads which page it is from <body data-page="...">.
   *
   * start({ bare: 'Admin' }) بيدي هيدر بسيط من غير nav — للصفحات
   * اللي مش جزء من التطبيق.
   */
  function start(options) {
    var bare = options && options.bare;
    var page = document.body.getAttribute('data-page');
    document.body.insertAdjacentHTML('afterbegin', buildBackdrop() + buildLangBar());
    I18N.apply();     // النصوص الثابتة في الـ HTML
    var shell = document.querySelector('.page');
    if (shell) {
      shell.insertAdjacentHTML('afterbegin',
        bare ? buildBareHeader(bare) : buildHeader(page));
    }
    wireLangBar();
    watchSync();
  }

  /**
   * Redraw the header in place. Signing in or out changes what the pill should
   * say, and that happens long after the header was first drawn.
   */
  function refreshHeader() {
    var bar = document.querySelector('.topbar');
    if (!bar) return;

    // الصفحة البسيطة ملهاش nav — نعيد رسم الشريط بس
    if (bar.classList.contains('topbar-bare')) {
      var title = bar.querySelector('.brand').textContent.replace('\u25a4', '').trim();
      bar.outerHTML = buildBareHeader(title);
      watchSync();
      return;
    }

    var nav = document.querySelector('.nav');
    if (!nav) return;
    var page = document.body.getAttribute('data-page');
    nav.remove();
    bar.outerHTML = buildHeader(page);
    watchSync();
  }

  /* ================================================================= toast == */

  var toastTimer = null;

  /** A short message that slides in at the bottom and leaves on its own. */
  function toast(message, kind) {
    var el = document.querySelector('.toast');
    if (!el) {
      el = document.createElement('div');
      el.className = 'toast';
      document.body.appendChild(el);
    }
    el.textContent = message;
    el.className = 'toast show' + (kind ? ' toast-' + kind : '');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.className = 'toast'; }, 2400);
  }

  /* ================================================================== bars == */

  /**
   * Bars render at zero width with the real width in data-width; this sets it
   * on the next frame so they grow in rather than appearing already finished.
   */
  function growBars(root) {
    var fills = (root || document).querySelectorAll('.bar-fill[data-width]');
    requestAnimationFrame(function () {
      for (var i = 0; i < fills.length; i++) {
        fills[i].style.width = fills[i].getAttribute('data-width') + '%';
      }
    });
  }

  /** Counts an element's number from one value to another. */
  function countTo(el, from, to, format) {
    if (!el) return;
    format = format || money;
    if (reducedMotion() || from === to) { el.textContent = format(to); return; }

    var t0 = performance.now();
    (function step(now) {
      var t = Math.min((now - t0) / 700, 1);
      var eased = 1 - Math.pow(1 - t, 3);
      el.textContent = format(Math.round(from + (to - from) * eased));
      if (t < 1) requestAnimationFrame(step);
    })(t0);
  }

  return {
    PAGES: PAGES,
    marketColor: marketColor, esc: esc, money: money, qtyLabel: qtyLabel, distance: distance,
    dot: dot, marketTag: marketTag, reducedMotion: reducedMotion,
    start: start, refreshHeader: refreshHeader,
    toast: toast, growBars: growBars, countTo: countTo
  };
})();
