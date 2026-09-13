/**
 * Thin client for /api/estimate-price.js.
 *
 * The browser never sees your AI key — it just asks our own serverless
 * function, which holds the key and talks to the AI provider.
 *
 * Note: plain `npm run dev` (Vite) does NOT run the /api function, so the app
 * will report AI as "not set up" locally. Use `vercel dev` if you want to test
 * the AI part on your machine; on Vercel itself it just works.
 */

export async function checkAiConfigured() {
  try {
    const res = await fetch('/api/estimate-price')
    if (!res.ok) return false
    const data = await res.json()
    return Boolean(data.configured)
  } catch {
    return false
  }
}

export async function estimatePrice(ingredient, market, meal) {
  const res = await fetch('/api/estimate-price', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      ingredient: { name: ingredient.name, qty: ingredient.qty, unit: ingredient.unit },
      market: { name: market.name },
      meal: { name: meal?.name ?? null },
    }),
  })

  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`)
  return data // { price, note }
}
