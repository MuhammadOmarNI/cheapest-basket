/* ===========================================================================
   ai.js — YOUR PART.

   Everything else in this project works right now. This file is the one piece
   left deliberately empty, because the AI call is yours to write.

   Two functions, and the app calls them for you:

     AI.findMarkets(location)
        -> resolves to an array of names: ["BİM", "A101", "Migros"]
        -> the "Find markets near me" button on the Settings page

     AI.estimatePrice(ingredient, market, meal, location)
        -> resolves to { price: 145, note: "short sentence" }
        -> the "Ask AI for prices" button on the Compare page

   Set AI.ready to true once they really call something. While it's false the
   app hides the AI buttons and lets you type prices by hand, so nothing is
   broken in the meantime.

   ⚠️  ABOUT YOUR API KEY
   This is a plain website with no server, so any key you paste below is
   readable by anyone who opens the page. That's fine while the project only
   lives on your own computer. Before you put this online for other people,
   move the call to a server (on Vercel that's an `api/` folder) and keep the
   key there — nothing in this folder should ever hold a real key in public.
   =========================================================================== */

var AI = {

  ready: false,   // flip to true once the two functions below really work

  /* -------------------------------------------------------------------------
     Find the supermarkets near a place.
     Must resolve to an array of strings.
  ------------------------------------------------------------------------- */
  findMarkets: function (location) {
    return Promise.reject(new Error('AI not set up yet — see js/ai.js'));

    // ---- EXAMPLE (Anthropic). Delete the line above, then uncomment: -------
    //
    // var prompt =
    //   'List the supermarket chains someone living in "' + location + '" would ' +
    //   'realistically shop at for everyday groceries. Give between 3 and 6.\n' +
    //   'Reply with ONLY a JSON array of names, like ["BİM", "A101", "Migros"]';
    //
    // return fetch('https://api.anthropic.com/v1/messages', {
    //   method: 'POST',
    //   headers: {
    //     'content-type': 'application/json',
    //     'x-api-key': 'PASTE_YOUR_KEY_HERE',
    //     'anthropic-version': '2023-06-01',
    //     'anthropic-dangerous-direct-browser-access': 'true'
    //   },
    //   body: JSON.stringify({
    //     model: 'claude-sonnet-4-5',
    //     max_tokens: 300,
    //     messages: [{ role: 'user', content: prompt }]
    //   })
    // })
    //   .then(function (r) { return r.json(); })
    //   .then(function (data) {
    //     var text = (data.content && data.content[0] && data.content[0].text) || '';
    //     // Models sometimes wrap JSON in a sentence — take the array out of the middle.
    //     var slice = text.slice(text.indexOf('['), text.lastIndexOf(']') + 1);
    //     return JSON.parse(slice);
    //   });
  },

  /* -------------------------------------------------------------------------
     Estimate what one ingredient costs at one market.
     Must resolve to { price: <number>, note: "<short string>" }.
  ------------------------------------------------------------------------- */
  estimatePrice: function (ingredient, market, meal, location) {
    return Promise.reject(new Error('AI not set up yet — see js/ai.js'));

    // ---- EXAMPLE (Anthropic). Delete the line above, then uncomment: -------
    //
    // var amount = [ingredient.qty, ingredient.unit].filter(Boolean).join(' ');
    //
    // var prompt =
    //   'You estimate grocery prices in ' + (location || 'Istanbul, Turkey') + '.\n' +
    //   'Market chain: ' + market.name + '\n' +
    //   'Item: ' + ingredient.name + '\n' +
    //   'Quantity needed: ' + (amount || 'not specified') + '\n' +
    //   'Estimate what buying that quantity costs at that chain, in the local ' +
    //   'currency. You do not have live prices — give your best general estimate.\n' +
    //   'Reply with ONLY JSON: {"price": <number>, "note": "<one short sentence>"}';
    //
    // return fetch('https://api.anthropic.com/v1/messages', {
    //   method: 'POST',
    //   headers: {
    //     'content-type': 'application/json',
    //     'x-api-key': 'PASTE_YOUR_KEY_HERE',
    //     'anthropic-version': '2023-06-01',
    //     'anthropic-dangerous-direct-browser-access': 'true'
    //   },
    //   body: JSON.stringify({
    //     model: 'claude-sonnet-4-5',
    //     max_tokens: 200,
    //     messages: [{ role: 'user', content: prompt }]
    //   })
    // })
    //   .then(function (r) { return r.json(); })
    //   .then(function (data) {
    //     var text = (data.content && data.content[0] && data.content[0].text) || '';
    //     var slice = text.slice(text.indexOf('{'), text.lastIndexOf('}') + 1);
    //     var parsed = JSON.parse(slice);
    //     return { price: Number(parsed.price), note: parsed.note || null };
    //   });
  }
};
