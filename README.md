# Cheapest Basket

Build a meal from its ingredients, set a budget, and see what that meal costs at each
market near you — with the cheapest one flagged. Prices are estimated by AI
automatically and can be corrected by hand at any time.

Built with React + Vite, Supabase for storage, and a Vercel serverless function that
keeps the AI key off the browser.

---

## What's in here

| Path | What it is |
| --- | --- |
| `src/` | The React app |
| `api/estimate-price.js` | Serverless function — **your AI code goes here** |
| `supabase/schema.sql` | Run once in Supabase to create the tables |
| `standalone/index.html` | A single-file version with no build step or database — open it in a browser and it just runs (saves to that browser only) |
| `.env.example` | Template for your keys |

If you just want to see the thing work, open `standalone/index.html` in a browser.
Everything below is for the real deployed version.

---

## Setup

### 1. Supabase

1. Create a project at [supabase.com](https://supabase.com).
2. Open **SQL Editor → New query**, paste all of `supabase/schema.sql`, and hit **Run**.
   That creates the four tables and seeds a few Turkish market chains.
3. Go to **Project Settings → API** and copy your **Project URL** and **anon public** key.

### 2. Local development

```bash
npm install
cp .env.example .env      # then paste your Supabase URL + anon key into .env
npm run dev
```

Open the URL it prints (usually `http://localhost:5173`).

One thing to know: `npm run dev` runs Vite only, so the `/api/estimate-price` function
doesn't exist locally and the app will say "AI not set up". That's expected. To test the
AI locally, use `npx vercel dev` instead — that runs both the site and the function.

### 3. Deploy to Vercel

1. Push this folder to a GitHub repo.
2. On [vercel.com](https://vercel.com) → **Add New → Project** → import that repo.
   Vercel detects Vite on its own; leave the build settings alone.
3. Before clicking Deploy, open **Environment Variables** and add all three:

   | Name | Value |
   | --- | --- |
   | `VITE_SUPABASE_URL` | your Supabase project URL |
   | `VITE_SUPABASE_ANON_KEY` | your Supabase anon key |
   | `AI_API_KEY` | your AI provider key |

4. Deploy. Every `git push` after this redeploys automatically.

---

## Hooking up the AI

`api/estimate-price.js` is a stub on purpose — that part is yours. It already handles the
plumbing (reading the key, validating the request, returning errors the UI knows how to
display); you just replace the "not implemented" return with a real API call. There's a
complete working Anthropic example commented out right below it — uncomment, and you're done.

It must return `{ price: <number>, note: "<short string>" }`.

**Why a serverless function and not just `fetch` from the browser?** Anything in `src/`
gets bundled and shipped to every visitor, so an API key there is public the moment you
deploy. `api/` runs on Vercel's server, where `process.env.AI_API_KEY` never leaves.
That's also why the AI key has no `VITE_` prefix — Vite only exposes variables that do.

### When the AI runs

It fires automatically, no button press needed:

- you finish naming an ingredient → it prices that ingredient at every market you have
- you add a market → it prices every ingredient already in the meal at that market
- **Fill missing with AI** → catches any gaps left over
- **Ask AI** on a single cell → retries just that one

Every estimate lands as an editable price tagged `AI est.` Click it, type your own
number, and it becomes `manual` — your value is never overwritten by a later estimate.

---

## How the data is stored

Four tables: `markets`, `meals`, `meal_ingredients`, `prices`.

Prices are stored per **ingredient × market**, and each price is for the exact quantity
the recipe calls for (500 g of chicken, not "chicken per kg"). That avoids unit-conversion
maths entirely and matches how you actually shop.

### Request count

Loading the app is **3 requests total**, regardless of how many ingredients or markets you
have — not one per cell. The trick is a single nested select in `src/lib/api.js`:

```js
supabase.from('meals').select(`
  id, name, budget, created_at,
  meal_ingredients (
    id, name, qty, unit,
    prices ( id, market_id, price, source, note, updated_at )
  )
`)
```

Supabase joins `meals → meal_ingredients → prices` server-side and returns the whole tree
in one response. This only works because of the foreign keys in `schema.sql`. After that,
edits update local state optimistically, so the UI never re-fetches just to show your own
change.

---

## Security notes

Two things to be aware of before you share the deployed URL:

**Row Level Security is off.** The tables are created wide open, and the Supabase anon key
ships in the browser bundle, so anyone with your URL can read and write your data. Fine for
a personal tool nobody else knows about. `supabase/schema.sql` has a commented-out policy
set at the bottom if you'd rather lock writes behind a login — note that turning RLS on
without adding a sign-in flow will make every write fail, so do one then the other.

**Don't put the AI key in `standalone/index.html` if you deploy that file publicly.** It's
designed for local use, where a pasted key only sits on your own machine. The `api/`
function exists precisely so the deployed version doesn't need one in the browser.

---

## Licence

MIT — do whatever you like with it.
