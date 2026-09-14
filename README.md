# Cheapest Basket

Keep a list of meals, write down what each ingredient costs at the shops near you, and
see where the whole basket is cheapest. There's a small game too.

**Three languages, no build step.** Double-click `index.html` and it runs. No npm, no
install, no server, nothing to compile. Everything is saved in your browser.

---

## What each file does

```
index.html        Dashboard — the summary, and which market wins
meals.html        Meals — add meals and their ingredients
compare.html      Compare — the prices, three different ways
game.html         Price Guess — a small game built from your own prices
settings.html     Settings — your area, your markets, and a reset button

css/style.css     Every bit of styling, for all five pages

js/data.js        Saving, loading, and the "which is cheapest" maths
js/ui.js          The header, nav, drifting background, colours, formatting
js/ai.js          ← YOUR PART. Two empty functions waiting for your API call
js/page-*.js      One file per page, named after the page it belongs to
```

Every page loads the same four scripts in the same order: `data.js`, `ui.js`, `ai.js`,
then its own `page-*.js`. That's why they can all share the same data.

---

## The three ways of comparing

**Cheapest per item** — one row per ingredient with the lowest price found anywhere and
which shop had it. The total assumes you'd visit all of them.

**Every market** — the full grid, a column per shop. Click any cell to type a price.

**Cheapest market** — the single shop where the whole basket costs least, plus what the
same basket costs elsewhere.

A market only competes for "cheapest market" once it has a price for *every* ingredient.
Otherwise a shop with half its prices missing would win just for having less to add up.

---

## Adding the AI

`js/ai.js` is the one file left deliberately empty — that part is yours. It has two
functions to fill in, and a complete working example commented out under each:

- `AI.findMarkets(location)` → `["BİM", "A101", ...]`, powers **Find markets near me**
- `AI.estimatePrice(ingredient, market, meal, location)` → `{ price, note }`, powers
  **Ask AI for prices**

Set `AI.ready = true` once they really work. Until then the AI buttons stay hidden and
you type prices by hand, so nothing is broken in the meantime.

**About your API key.** This is a plain website with no server, so a key pasted into
`ai.js` is readable by anyone who opens the page. That's fine while this only lives on
your own computer. Before putting it online for other people, move the call to a server
(on Vercel that means an `api/` folder) and keep the key there.

---

## Where your data lives

In `localStorage` — a small box of text the browser keeps for this page. It survives
closing the tab and restarting the computer.

What that also means: it's **per browser and per computer**. Open the app in a different
browser and it starts empty. Clearing your browsing data clears it too. There's no
account and no server, which is what makes the whole thing work with no setup.

Settings → **Clear all my data** wipes it deliberately.

---

## Putting it online

Because it's just files, almost anything will host it. On Vercel: push to GitHub, import
the repo, and deploy — no build command, no framework setting. GitHub Pages works too.

Remember the key warning above before you make it public.

---

## Licence

MIT — do whatever you like with it.
