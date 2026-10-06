/* ===========================================================================
   page-settings.js — where you shop, which markets, and the reset button.
   =========================================================================== */

(function () {
  'use strict';

  UI.start();

  var locationInput = document.getElementById('location');
  var geoBtn = document.getElementById('geo-btn');
  var findBtn = document.getElementById('find-btn');
  var statusEl = document.getElementById('status');
  var chips = document.getElementById('market-chips');
  var countEl = document.getElementById('market-count');
  var form = document.getElementById('market-form');
  var nameInput = document.getElementById('market-name');
  var resetBtn = document.getElementById('reset-btn');

  locationInput.value = DB.settings().location;
  findBtn.hidden = !AI.ready;

  // زرار مخفي من غير سبب بيخلّي اليوزر يفتكر إن البرنامج ناقص.
  if (!AI.ready) {
    findBtn.insertAdjacentHTML('afterend',
      '<span class="hint" id="find-why">' + UI.esc(T('set.findWhy')) + '</span>');
  }

  function status(text) { statusEl.textContent = text || ''; }

  /* =============================================================== markets == */

  function renderMarkets() {
    var markets = DB.markets();
    countEl.textContent = markets.length + ' ' +
      T(markets.length === 1 ? 'dash.market' : 'dash.markets');

    chips.innerHTML = markets.length
      ? markets.map(function (m) {
          return '<span class="chip">' + UI.dot(m) + UI.esc(m.name) +
            (m.metres != null
              ? '<span class="chip-far">' + UI.distance(m.metres) + '</span>'
              : '') +
            '<button type="button" class="btn-x tiny" title="Remove ' + UI.esc(m.name) +
            '" data-rm="' + m.id + '">×</button></span>';
        }).join('')
      : '<span class="muted">' + T('set.noMarkets') + '</span>';
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var name = nameInput.value.trim();
    if (!name) return;

    var clash = DB.markets().some(function (m) {
      return m.name.toLowerCase() === name.toLowerCase();
    });
    if (clash) { UI.toast(name + ' ' + T('set.alreadyHave')); return; }

    DB.addMarket(name);
    nameInput.value = '';
    renderMarkets();
    UI.toast(T('meals.added') + ' ' + name, 'good');
  });

  chips.addEventListener('click', function (e) {
    var el = e.target.closest('[data-rm]');
    if (!el) return;
    var market = DB.market(el.getAttribute('data-rm'));
    if (!market) return;
    if (!confirm(T('meals.remove') + ' ' + market.name + ' ' + T('set.removeAsk'))) return;
    DB.removeMarket(market.id);
    renderMarkets();
    UI.toast(T('set.removed') + ' ' + market.name);
  });

  /* ============================================================== location == */

  // Saves as you type — no separate save button to forget about.
  locationInput.addEventListener('input', function () {
    DB.setLocation(locationInput.value);
  });

  /* The browser gives coordinates, not a place name, and that's fine: the AI
     can work out the area from them, so there's no geocoding service needed. */
  geoBtn.addEventListener('click', function () {
    if (!navigator.geolocation) {
      status(T('set.noGeo'));
      return;
    }
    status(T('set.finding'));
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        locationInput.value = pos.coords.latitude.toFixed(4) + ', ' + pos.coords.longitude.toFixed(4);
        DB.setLocation(locationInput.value);
        status(T('set.locationSet'));
      },
      function () { status(T('set.locationDenied')); }
    );
  });

  findBtn.addEventListener('click', function () {
    var where = locationInput.value.trim();
    if (!where) { status(T('set.typeArea')); return; }

    findBtn.disabled = true;
    status('Checking the map, then asking the AI which are really grocery shops…');

    Promise.resolve()
      .then(function () { return AI.findMarkets(where); })
      .then(function (found) {
        // Markets you already have keep their identity and just learn their
        // distance — running the search twice shouldn't create a second Kiler.
        var byName = {};
        DB.markets().forEach(function (m) { byName[m.name.toLowerCase()] = m; });

        var added = 0, updated = 0;
        (found || []).forEach(function (shop) {
          var name = String(shop.name || '').trim();
          if (!name) return;
          var existing = byName[name.toLowerCase()];
          if (existing) {
            if (existing.metres !== shop.metres) {
              DB.setMarketDistance(existing.id, shop.metres);
              updated++;
            }
          } else {
            byName[name.toLowerCase()] = DB.addMarket(name, shop.metres);
            added++;
          }
        });

        renderMarkets();

        if (!added && !updated) {
          status('Nothing new — you already have the shops near there.');
        } else {
          status([added ? 'Added ' + added : '', updated ? 'updated ' + updated : '']
                   .filter(Boolean).join(', ') +
                 '. Distances are straight-line, not walking time.');
        }
      })
      .catch(function (err) { status(err.message || 'Could not find markets.'); })
      .then(function () { findBtn.disabled = false; });
  });

  /* =============================================================== account == */

  var syncBody = document.getElementById('sync-body');
  var syncState = document.getElementById('sync-state');
  var resetNote = document.getElementById('reset-note');

  function renderSync() {
    // Accounts not configured at all.
    if (!CLOUD.on()) {
      syncState.textContent = T('set.notSetUp');
      syncBody.innerHTML =
        '<p class="hint">Everything is saved in this one browser. To see the same ' +
        'meals and prices on your phone too:</p>' +
        '<ol class="steps">' +
          '<li>Make a free project at <strong>supabase.com</strong>.</li>' +
          '<li>Open <strong>SQL Editor \u2192 New query</strong>, paste all of ' +
            '<code>supabase-setup.sql</code> from this folder, and press Run.</li>' +
          '<li>Go to <strong>Project Settings \u2192 API Keys</strong> and copy your ' +
            '<strong>Project URL</strong> and <strong>Publishable key</strong>.</li>' +
          '<li>Paste them both into the top of <code>js/cloud.js</code> and reload.</li>' +
        '</ol>';
      resetNote.textContent = T('set.clearWarn');
      return;
    }

    // Configured, but nobody signed in.
    if (!AUTH.signedIn()) {
      syncState.textContent = T('set.signedOut');
      syncBody.innerHTML =
        '<p class="hint">' + T('set.savedHere') + '</p>' +
        '<div class="row">' +
          '<a class="btn" href="login.html" style="text-decoration:none">' +
            T('set.signInCta') + '</a>' +
        '</div>';
      resetNote.textContent = T('set.clearWarn');
      return;
    }

    // Signed in.
    syncState.textContent = T('set.syncedState');
    syncBody.innerHTML =
      '<p class="hint">' + T('set.signedInAs') + ' <strong>' + UI.esc(AUTH.email()) +
      '</strong>. ' + T('set.howSync') + '</p>' +
      '<div class="row">' +
        '<button type="button" class="btn-soft" id="sync-now">' + T('set.syncNow') + '</button>' +
        '<a class="btn-soft" href="login.html" style="text-decoration:none">Account</a>' +
      '</div>';

    resetNote.textContent = T('set.clearCloudNote');
  }

  CLOUD.onStatus(function (state, detail) {
    if (!syncState || !AUTH.signedIn()) return;
    syncState.textContent =
      state === 'saved' ? T('set.syncedState') :
      state === 'syncing' ? T('chrome.syncing') :
      state === 'error' ? T('chrome.offline') : '';
    if (state === 'error' && detail) syncState.title = detail;
  });

  document.addEventListener('click', function (e) {
    var el = e.target.closest('#sync-now');
    if (!el) return;
    UI.toast(T('chrome.syncing'));
    CLOUD.sync(true).then(function (result) {
      if (result === 'error') UI.toast(T('chrome.offline'), 'bad');
      else if (result === 'pulled') UI.toast(T('set.syncedState'), 'good');
      else UI.toast(T('set.upToDate'), 'good');
    });
  });

  /* ================================================================= reset == */

  resetBtn.addEventListener('click', function () {
    if (!confirm(T('set.confirmClear'))) return;
    DB.reset();
    locationInput.value = '';
    renderMarkets();
    UI.toast(T('set.cleared'));
  });

  renderMarkets();
  renderSync();
})();
