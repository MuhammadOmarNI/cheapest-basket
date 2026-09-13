/**
 * ============================================================================
 *  YOUR AI GOES HERE
 * ============================================================================
 *
 *  This is a Vercel Serverless Function. It runs on Vercel's server, NOT in
 *  the browser — which is the whole point: your API key stays secret.
 *
 *  It answers two things:
 *    GET  /api/estimate-price   ->  { configured: true|false }
 *                                   the app asks this on load so it knows
 *                                   whether to show the AI buttons
 *    POST /api/estimate-price   ->  { price: 145, note: "..." }
 *                                   body: { ingredient, market, meal }
 *
 *  To turn it on:
 *    1. Add AI_API_KEY in Vercel -> your project -> Settings -> Environment
 *       Variables (and in your local .env if you run `vercel dev`).
 *    2. Replace the "not implemented" return below with a real call —
 *       there's a complete, working example commented out underneath it.
 *
 *  Whatever you return gets saved as an "AI est." price that the user can
 *  click and overwrite by hand. Returning an error just leaves the cell empty
 *  with a retry link, so a failure here never breaks the app.
 */

export default async function handler(req, res) {
  const configured = Boolean(process.env.AI_API_KEY)

  // --- status check, used by the app on load -------------------------------
  if (req.method === 'GET') {
    return res.status(200).json({ configured })
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  if (!configured) {
    return res.status(501).json({
      error: 'AI not set up — add AI_API_KEY in Vercel, then edit api/estimate-price.js',
    })
  }

  const { ingredient, market, meal } = req.body || {}

  if (!ingredient?.name || !market?.name) {
    return res.status(400).json({ error: 'Missing ingredient or market' })
  }

  try {
    // =======================================================================
    // REPLACE THIS with your real AI call.
    // =======================================================================
    return res.status(501).json({
      error: 'Not implemented yet — see api/estimate-price.js',
    })

    // -----------------------------------------------------------------------
    // WORKING EXAMPLE (Anthropic). Delete the return above, then uncomment:
    // -----------------------------------------------------------------------
    //
    // const quantity = [ingredient.qty, ingredient.unit].filter(Boolean).join(' ')
    //
    // const prompt =
    //   'You estimate grocery prices in Istanbul, Turkey for a household budgeting tool.\n' +
    //   `Market chain: ${market.name}\n` +
    //   `Item: ${ingredient.name}\n` +
    //   `Quantity needed: ${quantity || 'not specified'}\n` +
    //   'Estimate what buying that quantity costs at that chain, in Turkish lira. ' +
    //   'You do not have live prices — give your best general estimate.\n' +
    //   'Reply with ONLY a JSON object: {"price": <number>, "note": "<one short sentence>"}'
    //
    // const response = await fetch('https://api.anthropic.com/v1/messages', {
    //   method: 'POST',
    //   headers: {
    //     'content-type': 'application/json',
    //     'x-api-key': process.env.AI_API_KEY,
    //     'anthropic-version': '2023-06-01',
    //   },
    //   body: JSON.stringify({
    //     model: 'claude-sonnet-4-5',
    //     max_tokens: 200,
    //     messages: [{ role: 'user', content: prompt }],
    //   }),
    // })
    //
    // if (!response.ok) {
    //   const detail = await response.text()
    //   console.error('AI provider error', response.status, detail)
    //   return res.status(502).json({ error: 'AI provider rejected the request' })
    // }
    //
    // const data = await response.json()
    // const text = data.content?.[0]?.text ?? ''
    //
    // // Models sometimes wrap JSON in prose — grab the object out of the middle.
    // const start = text.indexOf('{')
    // const end = text.lastIndexOf('}')
    // if (start === -1 || end === -1) {
    //   return res.status(502).json({ error: 'AI did not return JSON' })
    // }
    //
    // const parsed = JSON.parse(text.slice(start, end + 1))
    // const price = Number(parsed.price)
    //
    // if (!Number.isFinite(price)) {
    //   return res.status(502).json({ error: 'AI did not return a usable price' })
    // }
    //
    // return res.status(200).json({
    //   price,
    //   note: typeof parsed.note === 'string' ? parsed.note.slice(0, 200) : null,
    // })
  } catch (err) {
    console.error('estimate-price failed', err)
    return res.status(502).json({ error: 'AI request failed' })
  }
}
