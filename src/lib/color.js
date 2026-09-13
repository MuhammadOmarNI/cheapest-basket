// Gives every market a stable colour, derived from its id, so the same market
// is always the same colour in its chip and in its ledger column.

const PALETTE = [
  '#3B82F6', // blue
  '#A855F7', // purple
  '#EC4899', // pink
  '#F59E0B', // amber
  '#14B8A6', // teal
  '#6366F1', // indigo
  '#84CC16', // lime
  '#0EA5E9', // sky
]

export function colorForMarket(id) {
  let hash = 0
  for (let i = 0; i < id.length; i++) {
    hash = (hash * 31 + id.charCodeAt(i)) >>> 0
  }
  return PALETTE[hash % PALETTE.length]
}

export function formatMoney(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return '—'
  return (
    n.toLocaleString('tr-TR', {
      minimumFractionDigits: n % 1 === 0 ? 0 : 2,
      maximumFractionDigits: 2,
    }) + ' ₺'
  )
}
