import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from './lib/api'
import { checkAiConfigured, estimatePrice } from './lib/ai'
import MealSection from './components/MealSection'
import MarketsSection from './components/MarketsSection'
import CompareSection from './components/CompareSection'
import './App.css'

const TABS = [
  { key: 'meal', label: 'Meal', color: 'blue' },
  { key: 'markets', label: 'Markets', color: 'purple' },
  { key: 'compare', label: 'Compare', color: 'green' },
]

const cellKey = (marketId, ingredientId) => `${marketId}:${ingredientId}`

/** Returns a new meal object with one price replaced (or added). */
function withPrice(meal, ingredientId, marketId, savedPrice) {
  return {
    ...meal,
    meal_ingredients: meal.meal_ingredients.map((ing) =>
      ing.id === ingredientId
        ? { ...ing, prices: [...ing.prices.filter((p) => p.market_id !== marketId), savedPrice] }
        : ing
    ),
  }
}

/** Returns a new meal object with one price removed. */
function withoutPrice(meal, ingredientId, marketId) {
  return {
    ...meal,
    meal_ingredients: meal.meal_ingredients.map((ing) =>
      ing.id === ingredientId
        ? { ...ing, prices: ing.prices.filter((p) => p.market_id !== marketId) }
        : ing
    ),
  }
}

export default function App() {
  const [tab, setTab] = useState('meal')
  const [markets, setMarkets] = useState([])
  const [mealList, setMealList] = useState([])
  const [meal, setMeal] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)

  const [aiConfigured, setAiConfigured] = useState(false)
  const [pendingAi, setPendingAi] = useState(() => new Set())
  const [aiErrors, setAiErrors] = useState({})

  // Refs let async callbacks read the latest values without going stale.
  const mealRef = useRef(null)
  const marketsRef = useRef([])
  const inFlight = useRef(new Set())
  const didInit = useRef(false)

  useEffect(() => { mealRef.current = meal }, [meal])
  useEffect(() => { marketsRef.current = markets }, [markets])

  useEffect(() => {
    if (didInit.current) return // React StrictMode runs effects twice in dev
    didInit.current = true
    init()
  }, [])

  async function init() {
    try {
      const [marketRows, meals, ai] = await Promise.all([
        api.fetchMarkets(),
        api.fetchMealList(),
        checkAiConfigured(),
      ])
      setMarkets(marketRows)
      setMealList(meals)
      setAiConfigured(ai)
      if (meals.length) setMeal(await api.fetchMeal(meals[0].id))
    } catch (err) {
      setLoadError(err.message || String(err))
    } finally {
      setLoading(false)
    }
  }

  // ------------------------------------------------------------ meals ----

  async function loadMeal(id) {
    setMeal(await api.fetchMeal(id))
  }

  async function handleNewMeal(name) {
    const created = await api.createMeal(name)
    setMealList((list) => [...list, created])
    await loadMeal(created.id)
  }

  async function handleDeleteMeal(id) {
    await api.deleteMeal(id)
    const remaining = mealList.filter((m) => m.id !== id)
    setMealList(remaining)
    if (remaining.length) await loadMeal(remaining[0].id)
    else setMeal(null)
  }

  // ----------------------------------------------------------- prices ----

  const savePrice = useCallback(async (marketId, ingredientId, price, source = 'manual', note = null) => {
    const saved = await api.upsertPrice({
      market_id: marketId,
      ingredient_id: ingredientId,
      price,
      source,
      note,
    })
    setMeal((prev) => (prev ? withPrice(prev, ingredientId, marketId, saved) : prev))
    setAiErrors((prev) => {
      const next = { ...prev }
      delete next[cellKey(marketId, ingredientId)]
      return next
    })
  }, [])

  const removePrice = useCallback(async (priceId, marketId, ingredientId) => {
    await api.deletePrice(priceId)
    setMeal((prev) => (prev ? withoutPrice(prev, ingredientId, marketId) : prev))
  }, [])

  // --------------------------------------------------------------- AI ----

  /**
   * Asks the AI for ONE cell. Skips silently if that cell already has a price
   * or a request is already in flight, which is what makes it safe to call in
   * a loop from the auto-fill helpers below.
   */
  const requestAiPrice = useCallback(
    async (market, ingredient) => {
      if (!aiConfigured) return

      const currentMeal = mealRef.current
      if (!currentMeal) return

      const key = cellKey(market.id, ingredient.id)
      if (inFlight.current.has(key)) return

      const existing = currentMeal.meal_ingredients.find((i) => i.id === ingredient.id)
      if (existing?.prices.some((p) => p.market_id === market.id)) return

      inFlight.current.add(key)
      setPendingAi(new Set(inFlight.current))
      setAiErrors((prev) => {
        const next = { ...prev }
        delete next[key]
        return next
      })

      try {
        const result = await estimatePrice(ingredient, market, currentMeal)
        const price = Number(result?.price)
        if (!Number.isFinite(price)) throw new Error('No usable price returned')
        await savePrice(market.id, ingredient.id, price, 'ai', result.note ?? null)
      } catch (err) {
        const message = err?.message ? String(err.message) : 'AI request failed'
        setAiErrors((prev) => ({ ...prev, [key]: message.slice(0, 70) }))
      } finally {
        inFlight.current.delete(key)
        setPendingAi(new Set(inFlight.current))
      }
    },
    [aiConfigured, savePrice]
  )

  // Fired the moment an ingredient gets a name: price it at every market.
  const autoFillForIngredient = useCallback(
    (ingredient) => {
      if (!aiConfigured || !ingredient.name) return
      marketsRef.current.forEach((market) => requestAiPrice(market, ingredient))
    },
    [aiConfigured, requestAiPrice]
  )

  // Fired when a market is added: price every ingredient already in the meal.
  const autoFillForMarket = useCallback(
    (market) => {
      if (!aiConfigured) return
      const currentMeal = mealRef.current
      if (!currentMeal) return
      currentMeal.meal_ingredients.forEach((ing) => {
        if (ing.name) requestAiPrice(market, ing)
      })
    },
    [aiConfigured, requestAiPrice]
  )

  // Manual catch-up button for any gaps left behind.
  const fillAllMissing = useCallback(() => {
    if (!aiConfigured) return
    const currentMeal = mealRef.current
    if (!currentMeal) return
    currentMeal.meal_ingredients.forEach((ing) => {
      if (!ing.name) return
      marketsRef.current.forEach((market) => requestAiPrice(market, ing))
    })
  }, [aiConfigured, requestAiPrice])

  // ------------------------------------------------------------ render ----

  if (loading) return <div className="loading">Loading…</div>

  if (loadError) {
    return (
      <div className="app">
        <section className="card card-blue">
          <h2>Couldn&apos;t reach the database</h2>
          <p className="error-text">{loadError}</p>
          <p className="ask-note">
            Check that <code>VITE_SUPABASE_URL</code> and <code>VITE_SUPABASE_ANON_KEY</code> are
            set, and that you ran <code>supabase/schema.sql</code> in your Supabase project.
          </p>
        </section>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1>Cheapest Basket</h1>
        <p>Build a meal, add your markets, compare the total — cheapest one wins.</p>
      </header>

      {!aiConfigured && (
        <div className="banner info">
          <span>
            <strong>AI pricing isn&apos;t set up yet.</strong> Add <code>AI_API_KEY</code> in Vercel
            and fill in <code>api/estimate-price.js</code>. You can still type prices by hand.
          </span>
        </div>
      )}

      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            className={`tab tab-${t.color} ${tab === t.key ? 'active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main>
        {tab === 'meal' &&
          (meal ? (
            <MealSection
              meal={meal}
              mealList={mealList}
              onSwitchMeal={loadMeal}
              onNewMeal={handleNewMeal}
              onDeleteMeal={handleDeleteMeal}
              onMealChange={setMeal}
              onMealRenamed={(id, name) =>
                setMealList((list) => list.map((m) => (m.id === id ? { ...m, name } : m)))
              }
              onIngredientNamed={autoFillForIngredient}
            />
          ) : (
            <section className="card card-blue">
              <h2>No meals yet</h2>
              <p className="ask-note">Start by giving your first meal a name.</p>
              <div>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => {
                    const name = window.prompt('Name this meal:')
                    if (name) handleNewMeal(name)
                  }}
                >
                  + Create your first meal
                </button>
              </div>
            </section>
          ))}

        {tab === 'markets' && (
          <MarketsSection
            markets={markets}
            onMarketsChange={setMarkets}
            onMarketAdded={autoFillForMarket}
          />
        )}

        {tab === 'compare' && meal && (
          <CompareSection
            meal={meal}
            markets={markets}
            aiConfigured={aiConfigured}
            pendingAi={pendingAi}
            aiErrors={aiErrors}
            onSavePrice={savePrice}
            onRemovePrice={removePrice}
            onAskAi={requestAiPrice}
            onFillMissing={fillAllMissing}
          />
        )}
      </main>
    </div>
  )
}
