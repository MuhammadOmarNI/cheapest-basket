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
login.html        Sign in / create an account (optional)

css/style.css     Every bit of styling, for all six pages

js/cloud.js       Supabase sync — paste your two keys at the top
js/auth.js        Signing in, staying signed in, signing out
js/data.js        Saving, loading, and the "which is cheapest" maths
js/ui.js          The header, nav, drifting background, colours, formatting
js/ai.js          ← YOUR PART. Two empty functions waiting for your API call
js/page-*.js      One file per page, named after the page it belongs to

supabase-setup.sql  Run once in Supabase to make the table
```

Every page loads the same scripts in the same order: `cloud.js`, `auth.js`, `data.js`,
`ui.js`, `ai.js`, then its own `page-*.js`. That's why they can all share the same data.
`cloud.js` goes first because it's where the two Supabase values live.

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

## Finding the shops near you

Settings → **Find markets near me** fills your market list with real shops, each with a
real distance. Paste your Gemini key at the top of `js/ai.js` and the button appears.

### The architecture, and the trap it avoids

The obvious approach is to send Gemini your coordinates and ask for nearby supermarkets
with distances. Try it — it answers with metre-precise numbers like "140 m", "235 m",
"355 m". Tested against a real neighbourhood in Gönyeli, **four of its five shops didn't
exist at that spot**, and the one that did was at 395 m, not the 235 m it claimed.

That isn't the model being bad. It's being asked something it cannot know: it holds no
index of shops and cannot measure metres. Asked anyway, it returns something *shaped* like
an answer. Confident, well-formatted, invented.

So each question goes to whatever can actually answer it:

| Question | Answered by | Why |
| --- | --- | --- |
| What shops are near here? | OpenStreetMap (Overpass) | It has an index. Free, no key. |
| How far is each one? | The haversine formula | Arithmetic. Exact, every time. |
| Which are really groceries? | Gemini | Judgment over retrieved facts — its strength |
| Which branch to keep? | Plain JavaScript | Picking a minimum isn't judgment |

That last row matters as much as the rest. Grouping branches and taking the nearest is a
comparison, not a decision — code does it correctly every time, for free, and you can test
it. **Never put arithmetic in a prompt.**

### Two things in `classify()` worth stealing

**`responseSchema`.** Gemini returns JSON matching a shape you declare, so there's no prose
to parse and no regex. In a pipeline that's the difference between reliable and fragile.

**The prior.** The first version of that prompt asked "is this a grocery?" with no starting
assumption — and the model excluded two real corner shops purely because it had never heard
of them. It knows big chains; it doesn't know one small shop in one neighbourhood. But OSM
had *already* said these were shops, so the honest question is narrower: which of these tags
are wrong? Starting from *"yes, unless clearly otherwise"* fixed it without touching the
model or the schema.

When a model gets something wrong, the first question is whether you asked it the right
question.

### The guardrail

A model asked to *label* a list can still quietly *add* to it. `classify()` drops anything
that comes back whose name wasn't in what we sent — an invented shop would otherwise become
a market with no coordinates and no distance.

### Honest limits

Distances are **straight-line**, not walking time. A shop 200 m away across a motorway is a
900 m walk; real routing needs a directions API.

OSM coverage varies. Some shops are missing, some are mis-tagged, some are unnamed (those
get dropped). The list is a starting point you can edit, not a survey.

### Prices

`AI.estimatePrice()` is still a stub — that part's yours. Same principle applies: the model
has no live price feed, so anything it returns is an educated guess. That's why every price
it produces is tagged **AI** and stays editable.

---

## Where your data lives

In `localStorage` — a small box of text the browser keeps for this page. It survives
closing the tab and restarting the computer, and it works with no setup and no internet.

On its own that means it's **per browser and per computer**: open the app somewhere else
and it starts empty. Supabase is what fixes that.

Settings → **Clear all my data** wipes this device deliberately.

---

## Syncing across devices (Supabase)

**Setup, once:**

1. Make a free project at [supabase.com](https://supabase.com).
2. **SQL Editor → New query**, paste all of `supabase-setup.sql`, press **Run**.
3. **Project Settings → API Keys** — copy your **Project URL** and your
   **Publishable key** (the one starting `sb_publishable_`).
4. Paste both into the top of `js/cloud.js`. Reload.

Then create an account on the **Sign in** page, and sign in with the same email on your
phone. Same list, both devices.

**Signing in is optional.** With no account the app works exactly as before, saved on this
device, and sends nothing anywhere.

**How it behaves.** This device is saved first, so every click is instant and it keeps
working with no internet — the pill in the header just says *Offline* and it catches up
later. Opening a page compares which copy was changed more recently and takes that one.

**Last save wins.** Edit the same meal on two devices at the same moment and the later
save overwrites the earlier one. For one person shopping, that's fine.

### Keeping the number of requests down

Worth knowing, because it's easy to build this badly:

- **Writes wait about a second and send once.** Typing six prices is one save, not six.
- **A pending write is flushed when you leave the page** (`keepalive`), rather than being
  dropped and re-sent later. Without this, clicking from Meals to Compare would lose the
  last thing you typed *and* leave a stale copy in the cloud looking newer than it is.
- **Opening several pages quickly reuses the last fetch.** Clicking through all five pages
  costs one request, not five.
- **The sign-in token is only renewed when it's actually about to expire**, checked against
  the clock rather than on a timer.

Measured in the tests: 5 page views → 1 fetch. 6 price edits → 1 save.

### Who can see your data

Supabase decides, not the app code. You sign in, it hands your browser a token, and the
table's rule is `auth.uid() = user_id` — you may only touch the row carrying your own user
id. A request with someone else's token gets nothing back; a request with no token gets
nothing back. The app never picks which row is yours, so it can't pick wrong.

That means the Publishable key sitting in `cloud.js` is safe to have in public. On its own
it opens nothing — it just says which project to talk to. (This is the fix for the earlier
version of this app, where a shared table and a secret code meant anyone with the key could
read every row.)

**Still true:** your password is the whole of your security, so use a real one.

**Why one table instead of four.** Every calculation already happens in the browser —
nothing asks the database to join or filter anything — so the whole app is one JSON row per
person. Splitting it into meals / ingredients / prices tables would add work on both sides
without buying anything.

---

## Putting it online

Because it's just files, almost anything will host it. On Vercel: push to GitHub, import
the repo, and deploy — no build command, no framework setting. GitHub Pages works too.

Remember the key warning above before you make it public.

---

## Licence

MIT — do whatever you like with it.
