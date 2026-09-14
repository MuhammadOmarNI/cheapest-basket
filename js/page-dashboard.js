/* ===========================================================================
   page-dashboard.js — the front page.

   Three counts, then the answer to the question this whole app exists for:
   which market is cheapest for everything you cook, and by how much.
   =========================================================================== */

(function () {
  'use strict';

  UI.start();

  var overviewEl = document.getElementById('overview');
  var previewEl = document.getElementById('meals-preview');

  function statsHtml(s) {
    return '<div class="stat-row">' +
      '<div class="stat"><span class="stat-value">' + s.mealCount + '</span>' +
        '<span class="stat-label">' + (s.mealCount === 1 ? 'meal' : 'meals') + '</span></div>' +
      '<div class="stat"><span class="stat-value">' + s.marketCount + '</span>' +
        '<span class="stat-label">' + (s.marketCount === 1 ? 'market' : 'markets') + '</span></div>' +
      '<div class="stat"><span class="stat-value">' + s.pricedCount + '</span>' +
        '<span class="stat-label">priced</span></div>' +
    '</div>';
  }

  function barsHtml(s) {
    var max = Math.max.apply(null, s.byMarket.map(function (b) { return b.total; }).concat([1]));

    // Rendered at zero width; UI.growBars() sets the real width next frame so
    // the sizes arrive as movement instead of appearing already finished.
    return '<div class="bars" role="img" aria-label="Total cost of ' + s.comparableCount +
        ' meals at each market">' +
      s.byMarket.map(function (b, i) {
        var pct = Math.max((b.total / max) * 100, 2);
        return '<div class="bar-row" title="' + UI.esc(b.market.name) + ': ' + UI.money(b.total) + '">' +
          '<span class="bar-label">' + UI.dot(b.market) + UI.esc(b.market.name) + '</span>' +
          '<span class="bar-track"><span class="bar-fill" data-width="' + pct +
            '" style="transition-delay:' + (i * 70) + 'ms;background:' +
            UI.marketColor(b.market) + '"></span></span>' +
          '<span class="bar-value' + (i === 0 ? ' best' : '') + '">' + UI.money(b.total) + '</span>' +
        '</div>';
      }).join('') +
    '</div>';
  }

  function renderOverview() {
    var s = DB.overview();

    if (!s.winner) {
      overviewEl.innerHTML = statsHtml(s) +
        '<p class="hint">' +
          (s.mealCount
            ? 'Add prices for one meal at every market and the comparison appears here. ' +
              '<a href="compare.html">Go to Compare</a>.'
            : 'Start by adding a meal. <a href="meals.html">Go to Meals</a>.') +
        '</p>';
      return;
    }

    overviewEl.innerHTML = statsHtml(s) +
      '<div class="headline">' +
        '<span class="eyebrow">Cheapest place to shop</span>' +
        '<span class="headline-main">' + UI.dot(s.winner.market) + UI.esc(s.winner.market.name) + '</span>' +
        '<span class="headline-sub"><strong id="win-total">' + UI.money(s.winner.total) + '</strong>' +
          ' for ' + (s.comparableCount === 1 ? 'your meal' : 'all ' + s.comparableCount + ' meals') +
          (s.runnerUp
            ? ' · ' + UI.money(s.runnerUp.total - s.winner.total) + ' less than ' + UI.esc(s.runnerUp.market.name)
            : '') +
        '</span>' +
      '</div>' +
      barsHtml(s) +
      (s.comparableCount < s.mealCount
        ? '<p class="hint">Comparing ' + s.comparableCount + ' of ' + s.mealCount +
          ' meals. The rest aren’t priced at every market yet, and counting them would ' +
          'make a market look cheap just for having gaps.</p>'
        : '');

    UI.growBars(overviewEl);
    // Count the headline figure up from zero on arrival.
    UI.countTo(document.getElementById('win-total'), 0, s.winner.total);
  }

  function renderPreview() {
    var meals = DB.meals();

    if (!meals.length) {
      previewEl.innerHTML = '';
      return;
    }

    previewEl.innerHTML =
      '<div class="card-head" style="margin-bottom:12px">' +
        '<h2>Your meals</h2>' +
        '<a class="btn-soft btn-small" href="meals.html" style="text-decoration:none">Edit meals</a>' +
      '</div>' +
      '<ul class="meal-list">' +
        meals.map(function (m) {
          var ranked = DB.rankMarkets(m);
          var count = m.ingredients.length;
          var sub = !count
            ? 'No ingredients yet'
            : count + ' ingredient' + (count === 1 ? '' : 's') +
              (ranked.length
                ? ' · ' + UI.money(ranked[0].total) + ' at ' + ranked[0].market.name
                : ' · no prices yet');
          return '<li><a class="meal-card" href="compare.html?meal=' + m.id + '">' +
            '<span class="meal-name">' + UI.esc(m.name) + '</span>' +
            '<span class="meal-sub">' + UI.esc(sub) + '</span>' +
          '</a></li>';
        }).join('') +
      '</ul>';
  }

  renderOverview();
  renderPreview();
})();
