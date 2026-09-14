/* ===========================================================================
   page-compare.js — the prices, three ways.

     Cheapest per item   one row per ingredient, lowest price found and where
     Every market        the whole grid, one column per market
     Cheapest market     the single shop where the basket costs least

   Click any price to type your own over it.
   =========================================================================== */

(function () {
  'use strict';

  UI.start();

  var picker = document.getElementById('meal-picker');
  var tabsWrap = document.getElementById('tabs-wrap');
  var viewEl = document.getElementById('view');
  var askBtn = document.getElementById('ask-ai-btn');

  var VIEWS = [
    { id: 'item',   label: 'Cheapest per item' },
    { id: 'all',    label: 'Every market' },
    { id: 'market', label: 'Cheapest market' }
  ];

  var mealId = new URLSearchParams(location.search).get('meal');
  var view = 'item';
  var busy = {};        // cells waiting on the AI
  var errors = {};      // cells where the AI failed
  var justSaved = null; // cell that just changed, so it can flash
  var flashTimer = null;

  function key(marketId, ingId) { return marketId + ':' + ingId; }
  function current() { return mealId ? DB.meal(mealId) : null; }

  /* ================================================================ pieces == */

  function priceCell(ing, market) {
    var k = key(market.id, ing.id);
    if (busy[k]) return '<span class="price-busy">…</span>';

    var price = ing.prices[market.id];
    var flash = justSaved === k ? ' just-saved' : '';

    if (!price) {
      var cell = '<button type="button" class="price-add" data-edit="' + k + '">add price</button>';
      if (errors[k]) cell += '<span class="price-error">' + UI.esc(errors[k]) + '</span>';
      return cell;
    }

    return '<span class="price-cell' + flash + '">' +
      '<button type="button" class="price-value" title="Click to edit" data-edit="' + k + '">' +
        UI.money(price.value) + '</button>' +
      '<span class="tag ' + (price.source === 'ai' ? 'ai' : 'manual') + '"' +
        (price.note ? ' title="' + UI.esc(price.note) + '"' : '') + '>' +
        (price.source === 'ai' ? 'AI' : 'you') + '</span>' +
      '<button type="button" class="btn-x tiny" title="Remove price" data-clear="' + k + '">×</button>' +
    '</span>';
  }

  /* -------------------------------------------------------- 1. per item --- */

  function viewPerItem(meal) {
    var rows = DB.cheapestPerIngredient(meal);
    var priced = rows.filter(function (r) { return r.price; });
    var sum = priced.reduce(function (acc, r) { return acc + r.price.value; }, 0);
    var missing = rows.length - priced.length;
    var markets = DB.markets();

    return '<div class="view"><ul class="price-list">' +
      rows.map(function (r) {
        var where = r.market || markets[0];
        return '<li class="price-row">' +
          '<span class="price-item">' + UI.esc(r.ingredient.name) +
            '<span class="muted">' + UI.esc(UI.qtyLabel(r.ingredient)) + '</span></span>' +
          '<span class="price-where">' +
            (r.market ? UI.marketTag(r.market) : '<span class="muted">—</span>') + '</span>' +
          '<span class="price-slot">' + (where ? priceCell(r.ingredient, where) : '') + '</span>' +
        '</li>';
      }).join('') +
      '</ul>' +
      '<div class="total-row"><span>Total, buying each item wherever it’s cheapest</span>' +
        '<strong>' + (priced.length ? UI.money(sum) : '—') + '</strong></div>' +
      (missing ? '<p class="hint">' + missing + ' ingredient' + (missing === 1 ? '' : 's') +
        ' still unpriced.</p>' : '') +
    '</div>';
  }

  /* ----------------------------------------------------- 2. every market --- */

  function viewAllMarkets(meal) {
    var markets = DB.markets();
    var ranked = DB.rankMarkets(meal);
    var cheapestId = ranked.length ? ranked[0].market.id : null;
    var n = meal.ingredients.length;

    return '<div class="view"><div class="scroller"><table>' +
      '<thead><tr><th>Ingredient</th>' +
        markets.map(function (m) {
          return '<th><span class="col-head">' + UI.dot(m) + UI.esc(m.name) +
            (m.id === cheapestId ? '<span class="crown">👑</span>' : '') + '</span></th>';
        }).join('') +
      '</tr></thead>' +

      '<tbody>' + meal.ingredients.map(function (ing) {
        return '<tr><td>' + UI.esc(ing.name) +
          '<span class="muted">' + UI.esc(UI.qtyLabel(ing)) + '</span></td>' +
          markets.map(function (m) {
            return '<td>' + priceCell(ing, m) + '</td>';
          }).join('') + '</tr>';
      }).join('') + '</tbody>' +

      '<tfoot><tr><td>Total</td>' +
        markets.map(function (m) {
          var filled = meal.ingredients.filter(function (i) { return i.prices[m.id]; }).length;
          var total = DB.mealTotalAt(meal, m.id);
          return '<td' + (m.id === cheapestId ? ' class="best"' : '') + '>' +
            (filled ? UI.money(total) : '—') +
            (filled < n ? '<span class="muted">' + (n - filled) + ' missing</span>' : '') +
          '</td>';
        }).join('') +
      '</tr></tfoot></table></div></div>';
  }

  /* --------------------------------------------------- 3. cheapest shop --- */

  function viewCheapestMarket(meal) {
    var ranked = DB.rankMarkets(meal);

    if (!ranked.length) {
      return '<div class="view"><p class="empty-state">No market has a price for every ' +
        'ingredient yet. Fill the gaps in <strong>Every market</strong> and the winner ' +
        'shows up here.</p></div>';
    }

    var winner = ranked[0];
    var rest = ranked.slice(1);

    return '<div class="view">' +
      '<div class="winner">' +
        '<span class="winner-label">Cheapest place to buy everything</span>' +
        '<span class="winner-name">' + UI.dot(winner.market) + ' ' + UI.esc(winner.market.name) + '</span>' +
        '<span class="winner-total">' + UI.money(winner.total) + '</span>' +
      '</div>' +
      '<ul class="price-list">' + meal.ingredients.map(function (ing) {
        return '<li class="price-row">' +
          '<span class="price-item">' + UI.esc(ing.name) +
            '<span class="muted">' + UI.esc(UI.qtyLabel(ing)) + '</span></span>' +
          '<span class="price-slot wide">' + priceCell(ing, winner.market) + '</span>' +
        '</li>';
      }).join('') + '</ul>' +
      (rest.length
        ? '<div class="runners"><span class="eyebrow">Same basket elsewhere</span><ul>' +
            rest.map(function (r) {
              return '<li>' + UI.marketTag(r.market) + '<span>' + UI.money(r.total) +
                '<span class="muted">+' + UI.money(r.total - winner.total) + '</span></span></li>';
            }).join('') +
          '</ul></div>'
        : '') +
    '</div>';
  }

  /* ================================================================ render == */

  function renderPicker() {
    var meals = DB.meals();
    if (!meals.length) { picker.innerHTML = '<option>No meals yet</option>'; return; }
    if (!mealId || !DB.meal(mealId)) mealId = meals[0].id;

    picker.innerHTML = meals.map(function (m) {
      return '<option value="' + m.id + '"' + (m.id === mealId ? ' selected' : '') + '>' +
        UI.esc(m.name) + '</option>';
    }).join('');
  }

  function render() {
    var meal = current();

    if (!meal) {
      tabsWrap.innerHTML = '';
      viewEl.innerHTML = '<p class="empty-state">No meals yet. ' +
        '<a href="meals.html">Add one first</a>.</p>';
      askBtn.hidden = true;
      return;
    }

    if (!meal.ingredients.length) {
      tabsWrap.innerHTML = '';
      viewEl.innerHTML = '<p class="empty-state">"' + UI.esc(meal.name) + '" has no ingredients. ' +
        '<a href="meals.html?meal=' + meal.id + '">Add some</a>.</p>';
      askBtn.hidden = true;
      return;
    }

    if (!DB.markets().length) {
      tabsWrap.innerHTML = '';
      viewEl.innerHTML = '<p class="empty-state">No markets yet. ' +
        '<a href="settings.html">Add a market</a> to compare against.</p>';
      askBtn.hidden = true;
      return;
    }

    askBtn.hidden = !AI.ready;

    tabsWrap.innerHTML = '<div class="tabs">' + VIEWS.map(function (v) {
      return '<button type="button" class="tab' + (view === v.id ? ' active' : '') +
        '" data-view="' + v.id + '">' + v.label + '</button>';
    }).join('') + '</div>';

    viewEl.innerHTML =
      view === 'item' ? viewPerItem(meal) :
      view === 'all' ? viewAllMarkets(meal) :
      viewCheapestMarket(meal);

    if (!AI.ready) {
      viewEl.insertAdjacentHTML('beforeend',
        '<p class="hint">Prices are yours to type in for now — click any of them. ' +
        'Open <code>js/ai.js</code> to let the AI fill them in instead.</p>');
    }
  }

  /* ================================================================ prices == */

  function savePrice(marketId, ingId, value, source, note) {
    DB.setPrice(mealId, ingId, marketId, value, source, note);
    delete errors[key(marketId, ingId)];
    justSaved = key(marketId, ingId);
    clearTimeout(flashTimer);
    flashTimer = setTimeout(function () { justSaved = null; }, 900);
  }

  /** Swaps a price for a text box in place, so focus lands where you clicked. */
  function startEditing(button) {
    var parts = button.getAttribute('data-edit').split(':');
    var marketId = parts[0];
    var ingId = parts[1];
    var ing = DB.ingredient(mealId, ingId);
    if (!ing) return;

    var holder = button.closest('.price-cell') || button;
    var existing = ing.prices[marketId];

    var input = document.createElement('input');
    input.type = 'number';
    input.className = 'price-input';
    input.step = '0.01';
    input.min = '0';
    input.value = existing ? existing.value : '';

    holder.replaceWith(input);
    input.focus();
    input.select();

    var done = false;
    function commit() {
      if (done) return;
      done = true;
      if (input.value !== '' && isFinite(Number(input.value))) {
        savePrice(marketId, ingId, Number(input.value), 'manual', null);
      }
      render();
    }
    input.addEventListener('blur', commit);
    input.addEventListener('keydown', function (ev) {
      if (ev.key === 'Enter') input.blur();
      if (ev.key === 'Escape') { done = true; render(); }
    });
  }

  /* ==================================================================== AI == */

  function askAiForMissing() {
    var meal = current();
    if (!meal) return;

    var jobs = [];
    meal.ingredients.forEach(function (ing) {
      if (!ing.name.trim()) return;
      DB.markets().forEach(function (market) {
        if (ing.prices[market.id]) return;
        jobs.push({ ing: ing, market: market });
      });
    });

    if (!jobs.length) { UI.toast('Every price is already filled in'); return; }

    askBtn.disabled = true;
    UI.toast('Asking the AI for ' + jobs.length + ' price' + (jobs.length === 1 ? '' : 's') + '…');

    // Four at a time, so twenty cells don't fire twenty requests at once.
    var queue = jobs.slice();
    var running = 0;
    var finished = 0;

    function next() {
      if (!queue.length && running === 0) {
        askBtn.disabled = false;
        UI.toast('Filled in ' + finished + ' of ' + jobs.length, finished ? 'good' : 'bad');
        render();
        return;
      }
      while (queue.length && running < 4) {
        (function (job) {
          running++;
          var k = key(job.market.id, job.ing.id);
          busy[k] = true;
          render();

          Promise.resolve()
            .then(function () {
              return AI.estimatePrice(job.ing, job.market, meal, DB.settings().location);
            })
            .then(function (result) {
              if (!result || !isFinite(Number(result.price))) throw new Error('No price returned');
              savePrice(job.market.id, job.ing.id, Number(result.price), 'ai', result.note);
              finished++;
            })
            .catch(function (err) { errors[k] = err.message || 'Failed'; })
            .then(function () {
              delete busy[k];
              running--;
              render();
              next();
            });
        })(queue.shift());
      }
    }
    next();
  }

  /* ================================================================ events == */

  picker.addEventListener('change', function () {
    mealId = picker.value;
    render();
  });

  askBtn.addEventListener('click', askAiForMissing);

  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-view], [data-edit], [data-clear]');
    if (!el) return;

    if (el.hasAttribute('data-view')) {
      view = el.getAttribute('data-view');
      render();
    } else if (el.hasAttribute('data-edit')) {
      startEditing(el);
    } else if (el.hasAttribute('data-clear')) {
      var parts = el.getAttribute('data-clear').split(':');
      DB.clearPrice(mealId, parts[1], parts[0]);
      render();
    }
  });

  renderPicker();
  render();
})();
