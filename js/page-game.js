/* ===========================================================================
   page-game.js — Price Guess.

   You get one ingredient and two shops. Pick the cheaper one. That's it.

   The questions are built from YOUR prices, so playing it is really a way of
   learning what you're paying where. Until you've priced something up there's
   nothing to ask about, so it falls back to a small set of practice rounds and
   says so.
   =========================================================================== */

(function () {
  'use strict';

  UI.start();

  var root = document.getElementById('game');

  /* Used only when the real data has nothing with two prices to compare yet. */
  var PRACTICE = [
    { item: 'Chicken breast', qty: '500 g', a: 'BİM', b: 'A101', pa: 178, pb: 195 },
    { item: 'Butter',         qty: '250 g', a: 'Migros', b: 'BİM', pa: 96, pb: 84 },
    { item: 'Rice',           qty: '1 kg',  a: 'A101', b: 'Migros', pa: 62, pb: 71 },
    { item: 'Eggs',           qty: '10',    a: 'BİM', b: 'Migros', pa: 78, pb: 92 },
    { item: 'Olive oil',      qty: '1 L',   a: 'Migros', b: 'A101', pa: 310, pb: 289 },
    { item: 'Tomatoes',       qty: '1 kg',  a: 'A101', b: 'BİM', pa: 44, pb: 38 },
    { item: 'Yoghurt',        qty: '1 kg',  a: 'BİM', b: 'A101', pa: 88, pb: 95 },
    { item: 'Onions',         qty: '2 kg',  a: 'Migros', b: 'BİM', pa: 52, pb: 41 }
  ];

  var score = 0;
  var streak = 0;
  var round = null;
  var answered = false;
  var usingPractice = false;

  /* ============================================================== rounds == */

  function pick(list) { return list[Math.floor(Math.random() * list.length)]; }

  /** Build a question from the user's own prices, or fall back to practice. */
  function nextRound() {
    var pool = DB.allPricedIngredients();

    // Only entries where two different markets disagree make a real question.
    var usable = [];
    pool.forEach(function (entry) {
      for (var i = 0; i < entry.markets.length; i++) {
        for (var j = i + 1; j < entry.markets.length; j++) {
          usable.push({ entry: entry, a: entry.markets[i], b: entry.markets[j] });
        }
      }
    });

    if (usable.length) {
      usingPractice = false;
      var choice = pick(usable);
      var ing = choice.entry.ingredient;
      return {
        item: ing.name,
        qty: UI.qtyLabel(ing),
        a: { name: choice.a.name, color: UI.marketColor(choice.a), price: ing.prices[choice.a.id].value },
        b: { name: choice.b.name, color: UI.marketColor(choice.b), price: ing.prices[choice.b.id].value }
      };
    }

    usingPractice = true;
    var p = pick(PRACTICE);
    return {
      item: p.item,
      qty: p.qty,
      a: { name: p.a, color: '#2a78d6', price: p.pa },
      b: { name: p.b, color: '#eb6834', price: p.pb }
    };
  }

  /* ============================================================== render == */

  function render() {
    if (!round) return;

    root.innerHTML =
      '<div class="game-top">' +
        '<div class="score-box"><span class="score-value" id="score">' + score + '</span>' +
          '<span class="score-label">score</span></div>' +
        '<div class="score-box streak"><span class="score-value">' + streak + '</span>' +
          '<span class="score-label">streak</span></div>' +
        '<div class="score-box best"><span class="score-value">' + DB.bestScore() + '</span>' +
          '<span class="score-label">best</span></div>' +
      '</div>' +

      '<div class="question">' +
        '<span class="question-item">' + UI.esc(round.item) +
          (round.qty ? ' <span class="muted">' + UI.esc(round.qty) + '</span>' : '') + '</span>' +
        '<span class="question-ask">Where is it cheaper?</span>' +
      '</div>' +

      '<div class="choices">' +
        choiceHtml('a') +
        choiceHtml('b') +
      '</div>' +

      '<div class="verdict" id="verdict"></div>' +

      (answered
        ? '<div style="display:flex;justify-content:center">' +
            '<button type="button" class="btn" id="next-btn">Next round →</button></div>'
        : '') +

      (usingPractice
        ? '<p class="hint" style="text-align:center">These are practice prices. ' +
          'Once you’ve priced your own meals in <a href="compare.html">Compare</a>, ' +
          'the questions come from your real data.</p>'
        : '');
  }

  function choiceHtml(side) {
    var c = round[side];
    var state = '';
    var priceText = '';

    if (answered) {
      var cheaper = round.a.price === round.b.price
        ? null
        : (round.a.price < round.b.price ? 'a' : 'b');
      state = cheaper === null ? '' : (side === cheaper ? ' right' : ' wrong');
      priceText = UI.money(c.price);
    }

    return '<button type="button" class="choice' + state + '" data-side="' + side + '"' +
      (answered ? ' disabled' : '') + '>' +
      '<span class="dot" style="background:' + c.color + '"></span>' +
      UI.esc(c.name) +
      '<span class="choice-price">' + priceText + '</span>' +
    '</button>';
  }

  /* ============================================================= answering == */

  function answer(side) {
    if (answered) return;
    answered = true;

    var tie = round.a.price === round.b.price;
    var cheaper = tie ? null : (round.a.price < round.b.price ? 'a' : 'b');
    var correct = tie || side === cheaper;

    if (correct) {
      score++;
      streak++;
    } else {
      streak = 0;
    }

    var record = DB.recordScore(score);
    render();

    var verdict = document.getElementById('verdict');
    if (tie) {
      verdict.className = 'verdict good';
      verdict.textContent = 'Same price at both — that one’s free.';
    } else if (correct) {
      verdict.className = 'verdict good';
      var saved = Math.abs(round.a.price - round.b.price);
      verdict.textContent = 'Right — ' + UI.money(saved) + ' cheaper.' +
        (streak >= 3 ? '  ' + streak + ' in a row!' : '');
    } else {
      verdict.className = 'verdict bad';
      verdict.textContent = round[cheaper].name + ' was cheaper.';
    }

    if (record && score > 0) UI.toast('New best score: ' + score + ' 🎉', 'good');
  }

  /* ================================================================ events == */

  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-side], #next-btn');
    if (!el) return;

    if (el.id === 'next-btn') {
      answered = false;
      round = nextRound();
      render();
    } else {
      answer(el.getAttribute('data-side'));
    }
  });

  // Keyboard: left/right or 1/2 pick a side, Enter or Space moves on.
  document.addEventListener('keydown', function (e) {
    if (!answered && (e.key === 'ArrowLeft' || e.key === '1')) answer('a');
    else if (!answered && (e.key === 'ArrowRight' || e.key === '2')) answer('b');
    else if (answered && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      answered = false;
      round = nextRound();
      render();
    }
  });

  round = nextRound();
  render();
})();
