import * as api from '../lib/api'

export default function MealSection({
  meal,
  mealList,
  onSwitchMeal,
  onNewMeal,
  onDeleteMeal,
  onMealChange,
  onMealRenamed,
  onIngredientNamed,
}) {
  function patchMeal(patch) {
    onMealChange({ ...meal, ...patch })
  }

  async function handleNameBlur(e) {
    const name = e.target.value
    patchMeal({ name })
    onMealRenamed(meal.id, name)
    await api.updateMeal(meal.id, { name })
  }

  async function handleBudgetBlur(e) {
    const budget = e.target.value === '' ? null : Number(e.target.value)
    patchMeal({ budget })
    await api.updateMeal(meal.id, { budget })
  }

  async function handleAddIngredient() {
    const created = await api.addIngredient(meal.id, { name: '', qty: null, unit: '' })
    patchMeal({ meal_ingredients: [...meal.meal_ingredients, created] })
  }

  function patchIngredientLocally(id, patch) {
    patchMeal({
      meal_ingredients: meal.meal_ingredients.map((ing) =>
        ing.id === id ? { ...ing, ...patch } : ing
      ),
    })
  }

  async function handleIngredientChange(id, patch) {
    patchIngredientLocally(id, patch)
    await api.updateIngredient(id, patch)
  }

  /**
   * Naming an ingredient is what kicks off the automatic AI pricing —
   * onIngredientNamed asks for an estimate at every market you've added.
   */
  async function handleIngredientNameBlur(ing, value) {
    const name = value.trim()
    patchIngredientLocally(ing.id, { name: value })
    await api.updateIngredient(ing.id, { name: value })
    if (name) onIngredientNamed({ ...ing, name: value })
  }

  async function handleRemoveIngredient(id) {
    patchMeal({ meal_ingredients: meal.meal_ingredients.filter((i) => i.id !== id) })
    await api.deleteIngredient(id)
  }

  return (
    <section className="card card-blue">
      <div className="card-head">
        <h2>Your meal</h2>
        <p>Quantities are the amount this recipe needs.</p>
      </div>

      <div className="field-row">
        <label>
          Meal
          <select value={meal.id} onChange={(e) => onSwitchMeal(e.target.value)}>
            {mealList.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name || '(untitled meal)'}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="btn-ghost btn-small"
          onClick={() => {
            const name = window.prompt('Name this meal:')
            if (name) onNewMeal(name)
          }}
        >
          + New meal
        </button>
        <button
          type="button"
          className="btn-danger btn-small"
          disabled={mealList.length <= 1}
          onClick={() => {
            if (window.confirm(`Delete "${meal.name}" and its saved prices?`)) onDeleteMeal(meal.id)
          }}
        >
          Delete
        </button>
      </div>

      <div className="field-row">
        <label>
          Meal name
          <input
            key={`name-${meal.id}`}
            type="text"
            defaultValue={meal.name}
            placeholder="e.g. Chicken &amp; rice pilaf"
            onBlur={handleNameBlur}
          />
        </label>
        <label>
          Budget (₺)
          <input
            key={`budget-${meal.id}`}
            type="number"
            min="0"
            step="1"
            defaultValue={meal.budget ?? ''}
            placeholder="0"
            onBlur={handleBudgetBlur}
          />
        </label>
      </div>

      <div className="ingredients">
        {meal.meal_ingredients.map((ing) => (
          <div className="ingredient-row" key={ing.id}>
            <input
              type="text"
              placeholder="Ingredient"
              defaultValue={ing.name}
              onBlur={(e) => handleIngredientNameBlur(ing, e.target.value)}
            />
            <input
              type="text"
              placeholder="Qty"
              defaultValue={ing.qty ?? ''}
              onBlur={(e) =>
                handleIngredientChange(ing.id, {
                  qty: e.target.value === '' ? null : Number(e.target.value),
                })
              }
            />
            <input
              type="text"
              placeholder="unit"
              defaultValue={ing.unit ?? ''}
              onBlur={(e) => handleIngredientChange(ing.id, { unit: e.target.value })}
            />
            <button
              type="button"
              className="btn-icon"
              title="Remove ingredient"
              onClick={() => handleRemoveIngredient(ing.id)}
            >
              ×
            </button>
          </div>
        ))}
        {meal.meal_ingredients.length === 0 && (
          <p className="empty-state">No ingredients yet — add the first one.</p>
        )}
      </div>

      <div>
        <button type="button" className="btn-ghost btn-small" onClick={handleAddIngredient}>
          + Add ingredient
        </button>
      </div>
    </section>
  )
}
