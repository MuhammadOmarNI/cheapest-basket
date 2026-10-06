/* ===========================================================================
   cloud.js — keeping your data the same on every device.

   ---------------------------------------------------------------------------
   PASTE YOUR TWO SUPABASE VALUES HERE.
   Supabase -> Project Settings -> API Keys
   ---------------------------------------------------------------------------
*/
var SUPABASE_URL = 'https://oleddjhccpabimxdipbi.supabase.co';   // e.g. 'https://abcdefghijkl.supabase.co'
var SUPABASE_KEY = 'sb_publishable_v0ifg7XD5-EVE86gtkcORA_JXFuCwaR';   // the Publishable key (sb_publishable_...)

/* ---------------------------------------------------------------------------
   How this works
   ---------------------------------------------------------------------------
   Your browser is saved first, always. Every click is instant and the app
   works with no internet at all. Supabase is a copy kept in step with it:

     sign in         ->  fetch your row and use whichever copy is newer
     change something->  save here now, send it up a moment later

   Which row is yours is decided by Supabase, not by us: you sign in, it hands
   your browser a token, and the database rule only lets that token touch the
   row carrying your own user id. Nothing here picks the row.

   Not signed in? Everything still works, saved on this device only.

   Keeping the number of requests down:
     · writes wait ~1s and send once, so editing six prices is one request
     · a pending write is flushed when you leave the page, not re-sent later
     · opening several pages quickly reuses the last fetch instead of asking again
     · the sign-in token is only renewed when it's actually about to expire
   =========================================================================== */

var CLOUD = (function () {
  'use strict';

  var TABLE = SUPABASE_URL + '/rest/v1/baskets';
  var PULL_MARK = 'basket-last-pull';
  var PULL_GAP = 15000;   // don't re-fetch within this many ms

  var pushTimer = null;
  var pending = null;
  var listeners = [];

  function on() { return Boolean(SUPABASE_URL && SUPABASE_KEY); }
  function active() { return on() && AUTH.signedIn(); }

  function headers(token, extra) {
    var h = {
      'apikey': SUPABASE_KEY,
      'Authorization': 'Bearer ' + token,
      'Content-Type': 'application/json'
    };
    if (extra) Object.keys(extra).forEach(function (k) { h[k] = extra[k]; });
    return h;
  }

  /* =============================================================== failures == */

  /**
   * Builds the error for a request Supabase turned down, and marks the one
   * case that isn't a network problem at all.
   *
   * 401 and 403 mean "I don't accept who you say you are" — your sign-in has
   * expired. Waiting will never fix that; only signing in again will. Every
   * other status is something we can retry later.
   *
   * Without this distinction the header shows "Offline" while the internet is
   * plainly working, and nothing ever tells you to sign in. A failure you
   * can't act on is barely better than no message at all.
   */
  function refusal(status, context) {
    var expired = status === 401 || status === 403;
    var error = new Error(
      expired ? 'Your sign-in has expired — sign in again.'
              : context + ' (' + status + ')'
    );
    error.expired = expired;
    return error;
  }

  /* ================================================================== pull == */

  /** Fetch your row. Resolves to the data object, or null if you have none yet. */
  function pull() {
    if (!active()) return Promise.reject(new Error('Not signed in'));

    return AUTH.token().then(function (token) {
      return fetch(TABLE + '?select=data', { headers: headers(token) });
    }).then(function (res) {
      if (!res.ok) throw refusal(res.status, 'Supabase said no');
      return res.json();
    }).then(function (rows) {
      markPulled();
      // The rule means only your own row can come back, so there's at most one.
      return rows.length ? rows[0].data : null;
    });
  }

  function markPulled() {
    try { localStorage.setItem(PULL_MARK, String(Date.now())); } catch (e) { /* ignore */ }
  }

  function pulledRecently() {
    try {
      return Date.now() - Number(localStorage.getItem(PULL_MARK) || 0) < PULL_GAP;
    } catch (e) {
      return false;
    }
  }

  /* ================================================================== push == */

  function push(data) {
    if (!active()) return Promise.reject(new Error('Not signed in'));

    return AUTH.token().then(function (token) {
      // merge-duplicates = "insert it, or overwrite it if that row already exists"
      return fetch(TABLE, {
        method: 'POST',
        headers: headers(token, { 'Prefer': 'resolution=merge-duplicates,return=minimal' }),
        body: JSON.stringify([{ user_id: AUTH.userId(), data: data }])
      });
    }).then(function (res) {
      if (!res.ok) {
        return res.text().then(function (t) {
          var error = refusal(res.status, 'Supabase refused the save');
          if (!error.expired) error.message += ': ' + t.slice(0, 120);
          throw error;
        });
      }
      markPulled();   // what's up there is now exactly what we just sent
      return true;
    });
  }

  /**
   * Called on every single change, so it waits a moment and sends once —
   * typing a price would otherwise fire a request per keystroke.
   */
  function queuePush(data) {
    if (!active()) return;
    pending = data;
    clearTimeout(pushTimer);
    pushTimer = setTimeout(function () {
      pushTimer = null;
      pending = null;
      push(data)
        .then(function () { tell('saved'); })
        .catch(function (err) { tell('error', err.message); });
    }, 1000);
  }

  /**
   * Leaving the page while a save is still waiting would drop it, and then the
   * older copy in Supabase would look newer than it is. `keepalive` lets the
   * request finish after the page is gone, so clicking through the nav never
   * loses the last thing you typed.
   */
  function flush() {
    if (!active() || !pending) return;
    clearTimeout(pushTimer);
    pushTimer = null;
    var data = pending;
    pending = null;

    AUTH.token().then(function (token) {
      fetch(TABLE, {
        method: 'POST',
        headers: headers(token, { 'Prefer': 'resolution=merge-duplicates,return=minimal' }),
        body: JSON.stringify([{ user_id: AUTH.userId(), data: data }]),
        keepalive: true
      });
    }).catch(function () { /* nothing more we can do on the way out */ });
  }

  window.addEventListener('pagehide', flush);
  // Safari fires pagehide unreliably on tab-switch; this covers the same ground.
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') flush();
  });

  /* ================================================================== sync == */

  /**
   * Run when a page opens: work out which copy was changed more recently —
   * this device's or the one in Supabase — and make both sides agree.
   *
   * Comparing *whether they differ* isn't enough. Right after you add a meal
   * they differ because this device is ahead, and taking the cloud copy then
   * would throw the new meal away. So each change carries a timestamp and the
   * newer one wins.
   *
   * Pass true to force a fetch even if we just did one (the Sync now button).
   */
  function sync(force) {
    if (!on()) return Promise.resolve('off');
    if (!AUTH.signedIn()) { tell('signed-out'); return Promise.resolve('signed-out'); }

    // Clicking through five pages shouldn't be five fetches.
    if (!force && pulledRecently()) { tell('saved'); return Promise.resolve('fresh'); }

    tell('syncing');

    return pull().then(function (remote) {
      var localData = DB.exportAll();
      var localTime = DB.stamp();
      var remoteTime = (remote && remote.updatedAt) || 0;

      if (!remote) {
        return push(localData).then(function () { tell('saved'); return 'seeded'; });
      }

      if (remoteTime > localTime) {
        DB.importAll(remote);
        tell('saved');
        // Reload so every list, total and bar reflects the new data. It can't
        // loop: after the reload the two timestamps match.
        location.reload();
        return 'pulled';
      }

      if (localTime > remoteTime) {
        return push(localData).then(function () { tell('saved'); return 'pushed'; });
      }

      tell('saved');
      return 'same';
    }).catch(function (err) {
      if (err.expired) {
        // The token is dead, so there's nothing to log out on the server —
        // this just clears the session here so the header stops pretending
        // you're signed in. Your data stays on this device either way.
        return AUTH.signOut().catch(function () { return null; }).then(function () {
          tell('expired', err.message);
          return 'expired';
        });
      }
      tell('error', err.message);
      return 'error';
    });
  }

  /** Called right after signing in, when the local copy may be from before. */
  function afterSignIn() {
    try { localStorage.removeItem(PULL_MARK); } catch (e) { /* ignore */ }
    return sync(true);
  }

  /* =============================================================== listeners == */

  function onStatus(fn) { listeners.push(fn); }
  function tell(state, detail) {
    listeners.forEach(function (fn) {
      try { fn(state, detail); } catch (e) { /* a broken listener shouldn't stop sync */ }
    });
  }

  return {
    on: on, active: active,
    pull: pull, push: push, queuePush: queuePush, flush: flush,
    sync: sync, afterSignIn: afterSignIn,
    onStatus: onStatus
  };
})();
