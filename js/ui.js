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
    { id: 'dashboard', file: 'index.html',    label: 'Dashboard', icon: '◉' },
    { id: 'meals',     file: 'meals.html',    label: 'Meals',     icon: '✚' },
    { id: 'compare',   file: 'compare.html',  label: 'Compare',   icon: '⇄' },
    { id: 'game',      file: 'game.html',     label: 'Game',      icon: '★' },
    { id: 'settings',  file: 'settings.html', label: 'Settings',  icon: '⚙' }
  ];

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

  function dot(market) {
    return '<span class="dot" style="background:' + marketColor(market) + '"></span>';
  }

  function marketTag(market) {
    return '<span class="market-name">' + dot(market) + esc(market.name) + '</span>';
  }

  /* ================================================================ chrome == */

  /** Builds the header and nav, and marks the page you're on. */
  function buildHeader(current) {
    var links = PAGES.map(function (p) {
      var active = p.id === current ? ' active' : '';
      return '<a class="nav-link nav-' + p.id + active + '" href="' + p.file + '">' +
        '<span class="nav-icon">' + p.icon + '</span>' + p.label + '</a>';
    }).join('');

    var where = DB.settings().location;

    return '<header class="topbar">' +
      '<a class="brand" href="index.html"><span class="brand-mark">🛒</span>Cheapest Basket</a>' +
      '<a class="where" href="settings.html" title="Change where you shop">' +
        (where ? '📍 ' + esc(where) : '📍 Set your area') +
      '</a>' +
    '</header>' +
    '<nav class="nav">' + links + '</nav>';
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
   */
  function start() {
    var page = document.body.getAttribute('data-page');
    document.body.insertAdjacentHTML('afterbegin', buildBackdrop());
    var shell = document.querySelector('.page');
    if (shell) shell.insertAdjacentHTML('afterbegin', buildHeader(page));
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
    marketColor: marketColor, esc: esc, money: money, qtyLabel: qtyLabel,
    dot: dot, marketTag: marketTag, reducedMotion: reducedMotion,
    start: start, toast: toast, growBars: growBars, countTo: countTo
  };
})();
