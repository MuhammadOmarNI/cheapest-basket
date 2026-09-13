import { useState } from 'react'
import * as api from '../lib/api'
import { colorForMarket } from '../lib/color'

export default function MarketsSection({ markets, onMarketsChange, onMarketAdded }) {
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleAdd(e) {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed || busy) return

    setBusy(true)
    try {
      const sortOrder = markets.length ? Math.max(...markets.map((m) => m.sort_order)) + 1 : 1
      const created = await api.addMarket(trimmed, sortOrder)
      onMarketsChange([...markets, created])
      setName('')
      // Adding a market kicks off AI estimates for every ingredient you already have.
      onMarketAdded(created)
    } finally {
      setBusy(false)
    }
  }

  async function handleRemove(market) {
    if (!window.confirm(`Remove ${market.name} and its saved prices?`)) return
    await api.deleteMarket(market.id)
    onMarketsChange(markets.filter((m) => m.id !== market.id))
  }

  return (
    <section className="card card-purple">
      <div className="card-head">
        <h2>Markets</h2>
        <p>Add every market you can reasonably shop at.</p>
      </div>

      <div className="chips">
        {markets.map((m) => (
          <span className="chip" key={m.id}>
            <span className="dot" style={{ background: colorForMarket(m.id) }} />
            {m.name}
            <button
              type="button"
              className="btn-icon"
              title="Remove market"
              onClick={() => handleRemove(m)}
            >
              ×
            </button>
          </span>
        ))}
        {markets.length === 0 && <p className="empty-state">No markets yet — add one below.</p>}
      </div>

      <form onSubmit={handleAdd} className="field-row">
        <input
          type="text"
          placeholder="Add a market, e.g. Migros"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button type="submit" className="btn-primary btn-small" disabled={busy}>
          {busy ? 'Adding…' : 'Add'}
        </button>
      </form>
    </section>
  )
}
