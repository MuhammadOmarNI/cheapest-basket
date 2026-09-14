/* ===========================================================================
   page-meals.js — add meals, and list what goes into them.

   Pick a meal from the list and its ingredient editor opens underneath.
   =========================================================================== */

(function () {
  'use strict';

  UI.start();

  var listWrap = document.getElementById('meal-list-wrap');
  var editor = document.getElementById('editor');
  var newBtn = document.getElementById('new-meal-btn');
  var form = document.getElementById('new-meal-form');
  var nameInput = document.getElementById('new-meal-name');
  var cancelBtn = document.getElementById('cancel-meal');

  // Opening straight from a link like meals.html?meal=abc123
  var openId = new URLSearchParams(location.search).get('meal');

  /* ============================================================ meal list == */

  function renderList() {
    var meals = DB.meals();

    if (!meals.length) {
      listWrap.innerHTML = '<p class="empty-state">No meals yet. Add one above, then list ' +
        'what goes into it.</p>';
      return;
    }

    listWrap.innerHTML = '<ul class="meal-list">' + meals.map(function (m) {
      var count = m.ingredients.length;
      var ranked = DB.rankMarkets(m);
      var sub = !count
        ? 'No ingredients yet'
        : count + ' ingredient' + (count === 1 ? '' : 's') +
          (ranked.length ? ' · ' + UI.money(ranked[0].total) + ' at ' + ranked[0].market.name
                         : ' · no prices yet');
      return '<li>' +
        '<button type="button" class="meal-card' + (m.id === openId ? ' selected' : '') +
          '" data-open="' + m.id + '">' +
          '<span class="meal-name">' + UI.esc(m.name) + '</span>' +
          '<span class="meal-sub">' + UI.esc(sub) + '</span>' +
        '</button>' +
        '<button type="button" class="btn-x" title="Delete meal" data-del="' + m.id + '">×</button>' +
      '</li>';
    }).join('') + '</ul>';
  }

  /* =============================================================== editor == */

  function renderEditor() {
    var meal = openId ? DB.meal(openId) : null;

    if (!meal) {
      editor.hidden = true;
      editor.innerHTML = '';
      return;
    }

    editor.hidden = false;
    editor.innerHTML =
      '<div class="card-head">' +
        '<h2>' + UI.esc(meal.name) + '</h2>' +
        '<a class="btn-soft btn-small" href="compare.html?meal=' + meal.id +
          '" style="text-decoration:none">Price it up →</a>' +
      '</div>' +

      '<label>Meal name<input type="text" id="meal-name" value="' + UI.esc(meal.name) + '"></label>' +

      '<span class="eyebrow">Ingredients</span>' +

      (meal.ingredients.length
        ? '<ul class="ing-list">' + meal.ingredients.map(function (ing) {
            return '<li class="ing-row">' +
              '<input type="text" value="' + UI.esc(ing.name) + '" placeholder="Ingredient" ' +
                'data-ing="' + ing.id + '" data-field="name">' +
              '<input type="text" value="' + UI.esc(ing.qty == null ? '' : ing.qty) + '" ' +
                'placeholder="Qty" data-ing="' + ing.id + '" data-field="qty">' +
              '<input type="text" value="' + UI.esc(ing.unit) + '" placeholder="unit" ' +
                'data-ing="' + ing.id + '" data-field="unit">' +
              '<button type="button" class="btn-x" title="Remove" data-rm="' + ing.id + '">×</button>' +
            '</li>';
          }).join('') + '</ul>'
        : '<p class="empty-state">Nothing in this meal yet.</p>') +

      '<form class="ing-row" id="add-ing">' +
        '<input type="text" id="ing-name" placeholder="Add an ingredient…">' +
        '<input type="text" id="ing-qty" placeholder="Qty">' +
        '<input type="text" id="ing-unit" placeholder="unit">' +
        '<button type="submit" class="btn-x plus" title="Add">+</button>' +
      '</form>';
  }

  function renderAll() {
    renderList();
    renderEditor();
  }

  /* ================================================================ events == */

  newBtn.addEventListener('click', function () {
    form.hidden = false;
    newBtn.hidden = true;
    nameInput.focus();
  });

  cancelBtn.addEventListener('click', function () {
    form.hidden = true;
    newBtn.hidden = false;
    nameInput.value = '';
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var name = nameInput.value.trim();
    if (!name) return;
    var meal = DB.addMeal(name);
    openId = meal.id;
    nameInput.value = '';
    form.hidden = true;
    newBtn.hidden = false;
    renderAll();
    UI.toast('Added "' + name + '"', 'good');
  });

  // One listener for the whole page, rather than re-attaching after every render.
  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-open], [data-del], [data-rm]');
    if (!el) return;

    if (el.hasAttribute('data-open')) {
      openId = el.getAttribute('data-open');
      renderAll();
      editor.scrollIntoView({ behavior: UI.reducedMotion() ? 'auto' : 'smooth', block: 'nearest' });

    } else if (el.hasAttribute('data-del')) {
      var meal = DB.meal(el.getAttribute('data-del'));
      if (!meal) return;
      if (!confirm('Delete "' + meal.name + '" and its prices?')) return;
      DB.removeMeal(meal.id);
      if (openId === meal.id) openId = null;
      renderAll();
      UI.toast('Deleted "' + meal.name + '"');

    } else if (el.hasAttribute('data-rm')) {
      DB.removeIngredient(openId, el.getAttribute('data-rm'));
      renderAll();
    }
  });

  document.addEventListener('submit', function (e) {
    if (e.target.id !== 'add-ing') return;
    e.preventDefault();
    var name = document.getElementById('ing-name').value.trim();
    if (!name) return;
    DB.addIngredient(
      openId, name,
      document.getElementById('ing-qty').value.trim(),
      document.getElementById('ing-unit').value.trim()
    );
    renderAll();
    var next = document.getElementById('ing-name');
    if (next) next.focus();
  });

  /* Fields save when you leave them, so typing never interrupts itself with a
     re-render. `true` on the end means "catch it on the way down" — blur
     doesn't bubble, so a normal listener here would never hear it. */
  document.addEventListener('blur', function (e) {
    var el = e.target;
    if (!el || !el.getAttribute) return;

    if (el.id === 'meal-name') {
      DB.renameMeal(openId, el.value);
      renderList();
      var head = editor.querySelector('h2');
      if (head) head.textContent = el.value;
      return;
    }

    var ingId = el.getAttribute('data-ing');
    if (!ingId) return;
    var field = el.getAttribute('data-field');
    var patch = {};
    patch[field] = field === 'qty' ? (el.value === '' ? null : Number(el.value)) : el.value;
    DB.updateIngredient(openId, ingId, patch);
    renderList();
  }, true);

  renderAll();
})();
