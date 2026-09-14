/* ===========================================================================
   data.js — where everything is stored, and all the "which is cheapest" maths.

   Everything lives in localStorage, which is a little box of text the browser
   keeps for this site. No database, no server, no npm. Close the tab and come
   back tomorrow: it's still there.

   Loaded by every page, before that page's own script.
   =========================================================================== */

var DB = (function () {
  'use strict';

  var KEY = 'basket-data';

  /* -------------------------------------------------------------- shape ----
     {
       markets:  [ { id, name, order } ],
       meals:    [ { id, name, ingredients: [ { id, name, qty, unit,
                                                prices: { marketId: {...} } } ] } ],
       settings: { location },
       game:     { best }
     }
     Prices are an object keyed by market id, so looking one up is
     ing.prices[marketId] instead of searching through a list.
  -------------------------------------------------------------------------- */

  function uid() {
    return Math.random().toString(36).slice(2, 9) + Date.now().toString(36).slice(-4);
  }

  function starter() {
    return {
      markets: [
        { id: uid(), name: 'BİM', order: 1 },
        { id: uid(), name: 'A101', order: 2 },
        { id: uid(), name: 'Migros', order: 3 }
      ],
      meals: [],
      settings: { location: '' },
      game: { best: 0 }
    };
  }

  var data = load();

  function load() {
    try {
      var raw = localStorage.getItem(KEY);
      if (raw) {
        var parsed = JSON.parse(raw);
        // Fill in anything an older save is missing, so an update never wipes data.
        if (!parsed.markets) parsed.markets = [];
        if (!parsed.meals) parsed.meals = [];
        if (!parsed.settings) parsed.settings = { location: '' };
        if (!parsed.game) parsed.game = { best: 0 };
        return parsed;
      }
    } catch (e) {
      // Private browsing, cleared storage, or a corrupt save — start clean.
    }
    return starter();
  }

  function save() {
    try {
      localStorage.setItem(KEY, JSON.stringify(data));
    } catch (e) {
      // Storage full or blocked. The page keeps working; it just won't remember.
    }
  }

  /* ============================================================== markets == */

  function markets() {
    return data.markets.slice().sort(function (a, b) { return a.order - b.order; });
  }

  function addMarket(name) {
    var order = data.markets.length
      ? Math.max.apply(null, data.markets.map(function (m) { return m.order; })) + 1
      : 1;
    var market = { id: uid(), name: name, order: order };
    data.markets.push(market);
    save();
    return market;
  }

  function removeMarket(id) {
    data.markets = data.markets.filter(function (m) { return m.id !== id; });
    // Drop that market's prices too, or they'd sit in storage forever unseen.
    data.meals.forEach(function (meal) {
      meal.ingredients.forEach(function (ing) { delete ing.prices[id]; });
    });
    save();
  }

  function market(id) {
    return data.markets.filter(function (m) { return m.id === id; })[0] || null;
  }

  /* ================================================================ meals == */

  function meals() { return data.meals; }

  function meal(id) {
    return data.meals.filter(function (m) { return m.id === id; })[0] || null;
  }

  function addMeal(name) {
    var m = { id: uid(), name: name, ingredients: [] };
    data.meals.push(m);
    save();
    return m;
  }

  function renameMeal(id, name) {
    var m = meal(id);
    if (m) { m.name = name; save(); }
  }

  function removeMeal(id) {
    data.meals = data.meals.filter(function (m) { return m.id !== id; });
    save();
  }

  /* ========================================================== ingredients == */

  function addIngredient(mealId, name, qty, unit) {
    var m = meal(mealId);
    if (!m) return null;
    var ing = {
      id: uid(),
      name: name,
      qty: qty === '' || qty == null ? null : Number(qty),
      unit: unit || '',
      prices: {}
    };
    m.ingredients.push(ing);
    save();
    return ing;
  }

  function updateIngredient(mealId, ingId, patch) {
    var ing = ingredient(mealId, ingId);
    if (!ing) return;
    Object.keys(patch).forEach(function (k) { ing[k] = patch[k]; });
    save();
  }

  function removeIngredient(mealId, ingId) {
    var m = meal(mealId);
    if (!m) return;
    m.ingredients = m.ingredients.filter(function (i) { return i.id !== ingId; });
    save();
  }

  function ingredient(mealId, ingId) {
    var m = meal(mealId);
    if (!m) return null;
    return m.ingredients.filter(function (i) { return i.id === ingId; })[0] || null;
  }

  /* =============================================================== prices == */

  function setPrice(mealId, ingId, marketId, value, source, note) {
    var ing = ingredient(mealId, ingId);
    if (!ing) return;
    ing.prices[marketId] = {
      value: Number(value),
      source: source || 'manual',
      note: note || null
    };
    save();
  }

  function clearPrice(mealId, ingId, marketId) {
    var ing = ingredient(mealId, ingId);
    if (!ing) return;
    delete ing.prices[marketId];
    save();
  }

  /* ============================================================= settings == */

  function settings() { return data.settings; }

  function setLocation(text) {
    data.settings.location = text;
    save();
  }

  /* ================================================================= game == */

  function bestScore() { return data.game.best || 0; }

  function recordScore(score) {
    if (score > (data.game.best || 0)) {
      data.game.best = score;
      save();
      return true;   // a new record
    }
    return false;
  }

  /* ================================================================ maths == */

  /** Does this market have a price for every ingredient in the meal? */
  function fullyPriced(m, marketId) {
    if (!m.ingredients.length) return false;
    return m.ingredients.every(function (ing) { return ing.prices[marketId] != null; });
  }

  /** What this meal costs at one market (only counts prices that exist). */
  function mealTotalAt(m, marketId) {
    return m.ingredients.reduce(function (sum, ing) {
      var p = ing.prices[marketId];
      return sum + (p ? p.value : 0);
    }, 0);
  }

  /**
   * Markets that can supply the WHOLE meal, cheapest first.
   * A market missing half the list is left out rather than ranked — otherwise
   * it would look cheapest simply for having less to add up.
   */
  function rankMarkets(m) {
    return markets()
      .filter(function (mk) { return fullyPriced(m, mk.id); })
      .map(function (mk) { return { market: mk, total: mealTotalAt(m, mk.id) }; })
      .sort(function (a, b) { return a.total - b.total; });
  }

  /** For each ingredient: the lowest price anywhere, and which market had it. */
  function cheapestPerIngredient(m) {
    return m.ingredients.map(function (ing) {
      var best = null;
      markets().forEach(function (mk) {
        var p = ing.prices[mk.id];
        if (!p) return;
        if (!best || p.value < best.price.value) best = { market: mk, price: p };
      });
      return { ingredient: ing, market: best ? best.market : null, price: best ? best.price : null };
    });
  }

  /** Dashboard figures across every meal. */
  function overview() {
    var all = meals();
    var mkts = markets();

    // Like-for-like only: meals every market prices in full.
    var comparable = all.filter(function (m) {
      return m.ingredients.length > 0 &&
        mkts.every(function (mk) { return fullyPriced(m, mk.id); });
    });

    var byMarket = mkts.map(function (mk) {
      return {
        market: mk,
        total: comparable.reduce(function (sum, m) { return sum + mealTotalAt(m, mk.id); }, 0)
      };
    }).sort(function (a, b) { return a.total - b.total; });

    var live = mkts.length > 0 && comparable.length > 0;

    return {
      mealCount: all.length,
      marketCount: mkts.length,
      pricedCount: all.filter(function (m) { return rankMarkets(m).length > 0; }).length,
      comparableCount: comparable.length,
      byMarket: live ? byMarket : [],
      winner: live ? byMarket[0] : null,
      runnerUp: live && byMarket.length > 1 ? byMarket[1] : null
    };
  }

  /** Every priced ingredient across all meals — the game feeds on this. */
  function allPricedIngredients() {
    var out = [];
    meals().forEach(function (m) {
      m.ingredients.forEach(function (ing) {
        var withPrices = markets().filter(function (mk) { return ing.prices[mk.id]; });
        if (withPrices.length >= 2) {
          out.push({ meal: m, ingredient: ing, markets: withPrices });
        }
      });
    });
    return out;
  }

  /* ================================================================ reset == */

  function reset() {
    data = starter();
    save();
  }

  return {
    uid: uid,
    markets: markets, addMarket: addMarket, removeMarket: removeMarket, market: market,
    meals: meals, meal: meal, addMeal: addMeal, renameMeal: renameMeal, removeMeal: removeMeal,
    addIngredient: addIngredient, updateIngredient: updateIngredient,
    removeIngredient: removeIngredient, ingredient: ingredient,
    setPrice: setPrice, clearPrice: clearPrice,
    settings: settings, setLocation: setLocation,
    bestScore: bestScore, recordScore: recordScore,
    fullyPriced: fullyPriced, mealTotalAt: mealTotalAt, rankMarkets: rankMarkets,
    cheapestPerIngredient: cheapestPerIngredient, overview: overview,
    allPricedIngredients: allPricedIngredients,
    reset: reset
  };
})();
