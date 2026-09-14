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

  function status(text) { statusEl.textContent = text || ''; }

  /* =============================================================== markets == */

  function renderMarkets() {
    var markets = DB.markets();
    countEl.textContent = markets.length + (markets.length === 1 ? ' market' : ' markets');

    chips.innerHTML = markets.length
      ? markets.map(function (m) {
          return '<span class="chip">' + UI.dot(m) + UI.esc(m.name) +
            '<button type="button" class="btn-x tiny" title="Remove ' + UI.esc(m.name) +
            '" data-rm="' + m.id + '">×</button></span>';
        }).join('')
      : '<span class="muted">No markets yet — add the shops you can actually get to.</span>';
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var name = nameInput.value.trim();
    if (!name) return;

    var clash = DB.markets().some(function (m) {
      return m.name.toLowerCase() === name.toLowerCase();
    });
    if (clash) { UI.toast(name + ' is already on the list'); return; }

    DB.addMarket(name);
    nameInput.value = '';
    renderMarkets();
    UI.toast('Added ' + name, 'good');
  });

  chips.addEventListener('click', function (e) {
    var el = e.target.closest('[data-rm]');
    if (!el) return;
    var market = DB.market(el.getAttribute('data-rm'));
    if (!market) return;
    if (!confirm('Remove ' + market.name + ' and every price saved for it?')) return;
    DB.removeMarket(market.id);
    renderMarkets();
    UI.toast('Removed ' + market.name);
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
      status('This browser can’t share your location — type your area instead.');
      return;
    }
    status('Finding you…');
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        locationInput.value = pos.coords.latitude.toFixed(4) + ', ' + pos.coords.longitude.toFixed(4);
        DB.setLocation(locationInput.value);
        status('Location set from your device.');
      },
      function () { status('Location permission denied — type your area instead.'); }
    );
  });

  findBtn.addEventListener('click', function () {
    var where = locationInput.value.trim();
    if (!where) { status('Type your area first.'); return; }

    findBtn.disabled = true;
    status('Looking for markets near ' + where + '…');

    Promise.resolve()
      .then(function () { return AI.findMarkets(where); })
      .then(function (names) {
        var existing = DB.markets().map(function (m) { return m.name.toLowerCase(); });
        var added = 0;
        (names || []).forEach(function (name) {
          name = String(name).trim();
          if (!name || existing.indexOf(name.toLowerCase()) !== -1) return;
          DB.addMarket(name);
          existing.push(name.toLowerCase());
          added++;
        });
        renderMarkets();
        status(added ? 'Added ' + added + ' market' + (added === 1 ? '' : 's') + '.'
                     : 'Nothing new found.');
      })
      .catch(function (err) { status(err.message || 'Could not find markets.'); })
      .then(function () { findBtn.disabled = false; });
  });

  /* ================================================================= reset == */

  resetBtn.addEventListener('click', function () {
    if (!confirm('Delete every meal, price and market? This cannot be undone.')) return;
    DB.reset();
    locationInput.value = '';
    renderMarkets();
    UI.toast('Everything cleared');
  });

  renderMarkets();
})();
