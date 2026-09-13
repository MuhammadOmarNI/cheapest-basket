import { useState } from 'react'
import { colorForMarket, formatMoney } from '../lib/color'

const cellKey = (marketId, ingredientId) => `${marketId}:${ingredientId}`

export default function CompareSection({
  meal,
  markets,
  aiConfigured,
  pendingAi,
  aiErrors,
  onSavePrice,
  onRemovePrice,
  onAskAi,
  onFillMissing,
}) {
  const [editing, setEditing] = useState(null) // cellKey currently being edited
  const ingredients = meal.meal_ingredients

  if (!markets.length) {
    return <p className="empty-state">Add at least one market to start comparing prices.</p>
  }
  if (!ingredients.length) {
    return <p className="empty-state">Add ingredients to your meal to build the ledger.</p>
  }

  // --- totals, completeness, and the cheapest market ------------------------
  const totals = {}
  markets.forEach((m) => { totals[m.id] = { sum: 0, filled: 0 } })
  ingredients.forEach((ing) => {
    markets.forEach((m) => {
      const price = ing.prices.find((p) => p.market_id === m.id)
      if (price) {
        totals[m.id].sum += Number(price.price)
        totals[m.id].filled += 1
      }
    })
  })

  const complete = markets.filter((m) => totals[m.id].filled === ingredients.length)
  const cheapestId = complete.length
    ? complete.reduce((best, m) => (totals[m.id].sum < totals[best.id].sum ? m : best)).id
    : null

  const budget = meal.budget == null ? null : Number(meal.budget)
  const isEstimating = pendingAi.size > 0

  function commitPrice(marketId, ingredientId, rawValue) {
    setEditing(null)
    const value = Number(rawValue)
    if (rawValue === '' || !Number.isFinite(value)) return
    onSavePrice(marketId, ingredientId, value, 'manual')
  }

  function renderCell(market, ing) {
    const key = cellKey(market.id, ing.id)
    const price = ing.prices.find((p) => p.market_id === market.id)

    if (pendingAi.has(key)) {
      return <span className="price-pending">Estimating…</span>
    }

    // An existing price, being edited in place.
    if (price && editing === key) {
      return (
        <input
          type="number"
          className="price-input"
          step="0.01"
          min="0"
          autoFocus
          defaultValue={price.price}
          onBlur={(e) => commitPrice(market.id, ing.id, e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') e.currentTarget.blur()
            if (e.key === 'Escape') setEditing(null)
          }}
        />
      )
    }

    // An existing price — click it to overwrite the AI's guess with your own.
    if (price) {
      return (
        <span className="price-cell">
          <span className="price-value-wrap">
            <span className="price-value" title="Click to edit" onClick={() => setEditing(key)}>
              {formatMoney(price.price)}
            </span>
            <span
              className={`price-source-tag ${price.source === 'ai' ? 'ai' : 'manual'}`}
              title={price.note || undefined}
            >
              {price.source === 'ai' ? 'AI est.' : 'manual'}
            </span>
          </span>
          <button
            type="button"
            className="btn-icon"
            title="Remove price"
            onClick={() => onRemovePrice(price.id, market.id, ing.id)}
          >
            ×
          </button>
        </span>
      )
    }

    // Empty cell: type a price, or ask the AI for one.
    return (
      <span className="cell-empty-actions">
        <input
          type="number"
          className="price-input"
          step="0.01"
          min="0"
          placeholder="0"
          onBlur={(e) => commitPrice(market.id, ing.id, e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') e.currentTarget.blur() }}
        />
        <button
          type="button"
          className="ask-ai-btn"
          disabled={!aiConfigured}
          onClick={() => onAskAi(market, ing)}
        >
          {aiConfigured ? 'Ask AI' : 'AI not set up'}
        </button>
        {aiErrors[key] && <span className="price-error">{aiErrors[key]}</span>}
      </span>
    )
  }

  return (
    <section className="card card-green">
      <div className="card-head">
        <h2>Price ledger</h2>
        <p className="ask-note">
          New ingredients and markets get an AI price estimate automatically — click any price to
          edit it with your own number. Estimates aren&apos;t live prices, so confirm in-store.
        </p>
      </div>

      <div className="ledger-actions">
        <button
          type="button"
          className="btn-ghost btn-small"
          disabled={!aiConfigured || isEstimating}
          onClick={onFillMissing}
        >
          {!aiConfigured ? 'AI not set up' : isEstimating ? 'Estimating…' : 'Fill missing with AI'}
        </button>
      </div>

      <div className="ledger-scroll">
        <table>
          <thead>
            <tr>
              <th>Ingredient</th>
              {markets.map((m) => (
                <th key={m.id} style={{ borderBottomColor: colorForMarket(m.id) }}>
                  <span className="market-col-head">
                    <span className="dot" style={{ background: colorForMarket(m.id) }} />
                    {m.name}
                    {m.id === cheapestId && <span className="crown">👑</span>}
                  </span>
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {ingredients.map((ing) => (
              <tr key={ing.id}>
                <td>
                  {ing.name || '(unnamed)'}
                  <span className="muted">
                    {ing.qty ?? ''} {ing.unit ?? ''}
                  </span>
                </td>
                {markets.map((m) => (
                  <td key={m.id}>{renderCell(m, ing)}</td>
                ))}
              </tr>
            ))}
          </tbody>

          <tfoot>
            <tr className="totals-row">
              <td>Total</td>
              {markets.map((m) => {
                const t = totals[m.id]
                return (
                  <td key={m.id}>
                    <span className="total-cell">
                      <span>{t.filled ? formatMoney(t.sum) : '—'}</span>
                      {t.filled < ingredients.length && (
                        <span className="missing-note">{ingredients.length - t.filled} missing</span>
                      )}
                      {m.id === cheapestId && <span className="badge">Cheapest</span>}
                    </span>
                  </td>
                )
              })}
            </tr>

            <tr className="budget-row">
              <td>{budget ? `Budget ${formatMoney(budget)}` : 'No budget set'}</td>
              {markets.map((m) => {
                const t = totals[m.id]
                if (!budget || t.filled !== ingredients.length) return <td key={m.id} />
                const delta = budget - t.sum
                return (
                  <td key={m.id} className={delta >= 0 ? 'under' : 'over'}>
                    {delta >= 0
                      ? `under by ${formatMoney(delta)}`
                      : `over by ${formatMoney(-delta)}`}
                  </td>
                )
              })}
            </tr>
          </tfoot>
        </table>
      </div>

      <div className="ledger-summary">
        <span>
          {complete.length
            ? `${complete.length} of ${markets.length} market(s) fully priced.`
            : 'No market has every ingredient priced yet.'}
        </span>
      </div>
    </section>
  )
}
