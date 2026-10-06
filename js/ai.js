/* ===========================================================================
   ai.js — finding the shops near you.

   ---------------------------------------------------------------------------
   PASTE YOUR GEMINI KEY HERE.  aistudio.google.com/apikey
   ---------------------------------------------------------------------------
*/

var GEMINI_KEY = '';
var GEMINI_MODEL = 'gemini-3.6-flash';

/* ---------------------------------------------------------------------------
   The architecture, and why it is this way
   ---------------------------------------------------------------------------
   The obvious approach is to send Gemini your coordinates and ask for nearby
   supermarkets with distances. We tried it. It answered with metre-precise
   distances — 140m, 235m, 355m — for shops it had no way to locate. Four of
   its five didn't exist at that spot at all.

   That isn't the model being bad. It's being asked a question it cannot
   answer: it holds no index of shops and cannot measure metres. Asked anyway,
   it produces something shaped like an answer.

   So each question goes to whatever can actually answer it:

     what shops are near here   ->  OpenStreetMap    (it has an index)
     how far away is each one   ->  haversine        (arithmetic, exact)
     which ones are real shops  ->  Gemini           (judgment, its strength)
     which branch to keep       ->  plain JavaScript (picking a minimum)

   That last line matters as much as the others: grouping branches and taking
   the nearest is not judgment, it's a comparison. Code does it correctly every
   time, for free, and you can test it. Never put arithmetic in a prompt.
   =========================================================================== */

var AI = {

  /* The app only shows the AI buttons when this is true. */
  get ready() { return Boolean(GEMINI_KEY); },

  /* =========================================================== 1. where == */

  /**
   * Turn whatever is in the location box into coordinates.
   * "35.2127, 33.3147" is used directly; anything else is looked up with
   * Nominatim — OpenStreetMap's free geocoder, no key needed.
   */
  resolveLocation: function (location) {
    var text = String(location || '').trim();

    var pair = text.match(/^(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)$/);
    if (pair) {
      return Promise.resolve({ lat: Number(pair[1]), lng: Number(pair[2]) });
    }

    if (!text) return Promise.reject(new Error('Set your area first'));

    return fetch('https://nominatim.openstreetmap.org/search?format=json&limit=1&q=' +
                 encodeURIComponent(text))
      .then(function (r) { return r.json(); })
      .then(function (hits) {
        if (!hits.length) throw new Error('Could not find "' + text + '" on the map');
        return { lat: Number(hits[0].lat), lng: Number(hits[0].lon) };
      });
  },

  /* ======================================================== 2. retrieval == */

  /** Every shop OpenStreetMap knows about within `radius` metres. */
  shopsAround: function (lat, lng, radius) {
    var query =
      '[out:json][timeout:25];(' +
        'node["shop"~"supermarket|convenience|grocery"](around:' + radius + ',' + lat + ',' + lng + ');' +
        'way["shop"~"supermarket|convenience|grocery"](around:' + radius + ',' + lat + ',' + lng + ');' +
      ');out center tags;';

    return fetch('https://overpass-api.de/api/interpreter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'data=' + encodeURIComponent(query)
    }).then(function (r) {
      if (!r.ok) throw new Error('Map service is busy — try again in a moment');
      return r.json();
    }).then(function (data) {
      return (data.elements || [])
        .map(function (e) {
          return {
            name: (e.tags && e.tags.name) || '',
            osmTag: (e.tags && e.tags.shop) || '',
            lat: e.lat != null ? e.lat : (e.center && e.center.lat),
            lon: e.lon != null ? e.lon : (e.center && e.center.lon)
          };
        })
        // An unnamed dot on a map is no use to anyone reading a shopping list.
        .filter(function (s) { return s.name && s.lat != null; });
    });
  },

  /* ========================================================= 3. distance == */

  /**
   * Great-circle distance in metres — the haversine formula.
   *
   * Straight line, not walking distance. A shop 200m away across a motorway
   * is a 900m walk. Fine for "which is nearest"; don't label it "walk time".
   */
  metresBetween: function (lat1, lon1, lat2, lon2) {
    var R = 6371000;
    var rad = function (d) { return d * Math.PI / 180; };
    var dLat = rad(lat2 - lat1);
    var dLon = rad(lon2 - lon1);
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(rad(lat1)) * Math.cos(rad(lat2)) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 2 * R * Math.asin(Math.sqrt(a));
  },

  /* ========================================================= 4. judgment == */

  /**
   * Ask Gemini which of these are really grocery shops, and which names are
   * the same chain spelled differently.
   *
   * Two things worth copying into your own work:
   *
   * responseSchema — Gemini returns JSON matching this shape, so there's no
   * prose to parse and no regex. In a pipeline this is the difference between
   * reliable and fragile.
   *
   * The prior — the first draft of this prompt asked "is this a grocery?" with
   * no starting assumption, and the model excluded two real corner shops
   * simply because it had never heard of them. It knows big chains; it doesn't
   * know a small shop in one neighbourhood. But OpenStreetMap has ALREADY said
   * these are shops, so the honest question is narrower: which of these tags
   * are wrong? Starting from "yes unless clearly otherwise" fixed it without
   * touching the model or the schema.
   */
  classify: function (shops) {
    var prompt =
      'OpenStreetMap has ALREADY tagged each of these as a shop, and the tag is included.\n\n' +
      'Assume each one IS a place to buy grocery ingredients. Only mark isGrocery false ' +
      'when the name makes it clear it is something else entirely — a restaurant, a kebab ' +
      'shop, a petrol station, a pet shop.\n\n' +
      'A small independent corner shop you have never heard of IS a grocery. Not recognising ' +
      'a name is not a reason to exclude it.\n\n' +
      'Also give the chain name, so different spellings of the same chain match.\n\n' +
      JSON.stringify(shops.map(function (s) {
        return { name: s.name, osmTag: s.osmTag };
      }));

    return fetch(
      'https://generativelanguage.googleapis.com/v1beta/models/' + GEMINI_MODEL +
      ':generateContent?key=' + GEMINI_KEY,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: {
            temperature: 0,          // classification, not creativity
            responseMimeType: 'application/json',
            responseSchema: {
              type: 'object',
              properties: {
                shops: {
                  type: 'array',
                  items: {
                    type: 'object',
                    properties: {
                      original:  { type: 'string' },
                      name:      { type: 'string' },
                      chain:     { type: 'string' },
                      isGrocery: { type: 'boolean' }
                    },
                    required: ['original', 'name', 'chain', 'isGrocery']
                  }
                }
              },
              required: ['shops']
            }
          }
        })
      }
    ).then(function (r) {
      return r.json().then(function (body) {
        if (!r.ok) {
          throw new Error((body.error && body.error.message) || ('Gemini said ' + r.status));
        }
        return body;
      });
    }).then(function (body) {
      var text = body.candidates &&
                 body.candidates[0].content.parts.map(function (p) { return p.text || ''; }).join('');
      if (!text) throw new Error('Gemini returned nothing usable');

      var parsed = JSON.parse(text);

      // The guardrail: drop anything it returned that we never sent. A model
      // asked to label a list can still quietly add to it, and an invented
      // shop here would be a market with no coordinates and no distance.
      var sent = {};
      shops.forEach(function (s) { sent[s.name] = true; });
      return (parsed.shops || []).filter(function (s) { return sent[s.original]; });
    });
  },

  /* ========================================================= the pipeline == */

  /**
   * The whole thing: location in, a short list of real nearby shops out,
   * each with a real distance. Resolves to [{ name, metres }].
   */
  findMarkets: function (location, radius) {
    if (!AI.ready) return Promise.reject(new Error('Add your Gemini key in js/ai.js'));

    var here;

    return AI.resolveLocation(location)
      .then(function (point) {
        here = point;
        return AI.shopsAround(point.lat, point.lng, radius || 1500);
      })
      .then(function (found) {
        if (!found.length) throw new Error('No shops mapped near there');

        // Distance first: cheap, exact, and it means the model never sees
        // anything it would have to measure.
        var withDistance = found.map(function (s) {
          return {
            name: s.name,
            osmTag: s.osmTag,
            metres: Math.round(AI.metresBetween(here.lat, here.lng, s.lat, s.lon))
          };
        });

        return AI.classify(withDistance).then(function (labelled) {
          var metresByName = {};
          withDistance.forEach(function (s) { metresByName[s.name] = s.metres; });

          // Group branches of the same chain, keep the nearest one.
          var nearest = {};
          labelled.forEach(function (s) {
            if (!s.isGrocery) return;
            var metres = metresByName[s.original];
            if (metres == null) return;
            var chain = s.chain || s.name;
            if (!nearest[chain] || metres < nearest[chain].metres) {
              nearest[chain] = { name: chain, metres: metres };
            }
          });

          return Object.keys(nearest)
            .map(function (k) { return nearest[k]; })
            .sort(function (a, b) { return a.metres - b.metres; });
        });
      });
  },

  /* ============================================================== prices == */

  /**
   * Still yours to write. Same idea as above: ask the model only what it can
   * actually know. It has no live price feed, so whatever it returns is an
   * educated guess — which is why every price it produces is tagged "AI" and
   * stays editable.
   */
  estimatePrice: function (ingredient, market, meal, location) {
    return Promise.reject(new Error('Price estimates not set up yet — see js/ai.js'));
  }
};
