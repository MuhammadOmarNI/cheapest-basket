import { supabase } from '../supabaseClient'

/**
 * One nested select = ONE request that joins
 *   meals -> meal_ingredients -> prices
 * instead of a separate query per ingredient. This works because of the
 * foreign keys defined in supabase/schema.sql.
 *
 * Loading the app costs 3 requests total (markets + meal list + this one),
 * no matter how many ingredients or markets you have.
 */
const MEAL_SELECT = `
  id, name, budget, created_at,
  meal_ingredients (
    id, name, qty, unit,
    prices ( id, market_id, price, source, note, updated_at )
  )
`

// ---------------------------------------------------------------- reads ----

export async function fetchMealList() {
  const { data, error } = await supabase
    .from('meals')
    .select('id, name')
    .order('created_at')
  if (error) throw error
  return data
}

export async function fetchMeal(mealId) {
  const { data, error } = await supabase
    .from('meals')
    .select(MEAL_SELECT)
    .eq('id', mealId)
    .single()
  if (error) throw error
  // Normalise so components never have to null-check these arrays.
  return {
    ...data,
    meal_ingredients: (data.meal_ingredients ?? []).map((ing) => ({
      ...ing,
      prices: ing.prices ?? [],
    })),
  }
}

export async function fetchMarkets() {
  const { data, error } = await supabase
    .from('markets')
    .select('id, name, sort_order')
    .order('sort_order')
  if (error) throw error
  return data
}

// --------------------------------------------------------------- meals ----

export async function createMeal(name) {
  const { data, error } = await supabase
    .from('meals')
    .insert({ name, budget: null })
    .select('id, name')
    .single()
  if (error) throw error
  return data
}

export async function updateMeal(id, patch) {
  const { error } = await supabase.from('meals').update(patch).eq('id', id)
  if (error) throw error
}

export async function deleteMeal(id) {
  const { error } = await supabase.from('meals').delete().eq('id', id)
  if (error) throw error
}

// --------------------------------------------------------- ingredients ----

export async function addIngredient(mealId, ingredient) {
  const { data, error } = await supabase
    .from('meal_ingredients')
    .insert({ meal_id: mealId, ...ingredient })
    .select()
    .single()
  if (error) throw error
  return { ...data, prices: [] }
}

export async function updateIngredient(id, patch) {
  const { error } = await supabase.from('meal_ingredients').update(patch).eq('id', id)
  if (error) throw error
}

export async function deleteIngredient(id) {
  const { error } = await supabase.from('meal_ingredients').delete().eq('id', id)
  if (error) throw error
}

// ------------------------------------------------------------- markets ----

export async function addMarket(name, sortOrder) {
  const { data, error } = await supabase
    .from('markets')
    .insert({ name, sort_order: sortOrder })
    .select()
    .single()
  if (error) throw error
  return data
}

export async function deleteMarket(id) {
  const { error } = await supabase.from('markets').delete().eq('id', id)
  if (error) throw error
}

// -------------------------------------------------------------- prices ----

export async function upsertPrice({ market_id, ingredient_id, price, source = 'manual', note = null }) {
  const { data, error } = await supabase
    .from('prices')
    .upsert(
      { market_id, ingredient_id, price, source, note, updated_at: new Date().toISOString() },
      { onConflict: 'market_id,ingredient_id' }
    )
    .select()
    .single()
  if (error) throw error
  return data
}

export async function deletePrice(id) {
  const { error } = await supabase.from('prices').delete().eq('id', id)
  if (error) throw error
}
