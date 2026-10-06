/* ===========================================================================
   auth.js — signing in, so the database knows who you are.

   Before this, your row was found by a long random code, and anyone holding
   the key could read every row. Now Supabase itself checks who's asking: you
   get a token when you sign in, and the database rule is simply
   "you may only touch the row with your own user id".

   No library. Supabase's login is plain HTTP too, so this is all fetch().

   About the token: it works for about an hour, then has to be renewed using a
   second, longer-lived "refresh token". Rather than a timer ticking in the
   background, we check the clock right before a request and only renew when
   it's actually about to expire — no wasted calls.
   =========================================================================== */

var AUTH = (function () {
  'use strict';

  var STORE = 'basket-session';
  var session = load();
  var refreshing = null;   // so two calls at once don't both renew

  function base() { return SUPABASE_URL + '/auth/v1'; }

  function on() { return Boolean(SUPABASE_URL && SUPABASE_KEY); }

  /* ================================================================ store == */

  function load() {
    try {
      var raw = localStorage.getItem(STORE);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function keep(data, emailAddress) {
    session = {
      access_token: data.access_token,
      refresh_token: data.refresh_token,
      // expires_in is seconds from now; store the actual moment instead.
      expires_at: Date.now() + ((data.expires_in || 3600) * 1000),
      email: emailAddress || (data.user && data.user.email) || (session && session.email),
      user_id: (data.user && data.user.id) || (session && session.user_id)
    };
    try { localStorage.setItem(STORE, JSON.stringify(session)); } catch (e) { /* ignore */ }
    return session;
  }

  function forget() {
    session = null;
    try { localStorage.removeItem(STORE); } catch (e) { /* ignore */ }
  }

  /* ================================================================= who == */

  function signedIn() { return Boolean(session && session.refresh_token); }
  function email() { return session ? session.email : null; }
  function userId() { return session ? session.user_id : null; }

  /* ============================================================== requests == */

  function post(path, body, token) {
    var head = { 'apikey': SUPABASE_KEY, 'Content-Type': 'application/json' };
    if (token) head['Authorization'] = 'Bearer ' + token;

    return fetch(base() + path, {
      method: 'POST',
      headers: head,
      body: JSON.stringify(body || {})
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok) {
          // Supabase puts the readable reason in different fields depending on
          // which part of it answered.
          throw new Error(data.error_description || data.msg || data.message ||
                          data.error || ('Request failed (' + res.status + ')'));
        }
        return data;
      });
    });
  }

  /* ================================================================ signup == */

  /**
   * Resolves to 'signed-in' if the account is ready to use straight away, or
   * 'check-email' if Supabase wants the address confirmed first.
   */
  function signUp(emailAddress, password) {
    return post('/signup', { email: emailAddress, password: password })
      .then(function (data) {
        if (data.access_token) {
          keep(data, emailAddress);
          return 'signed-in';
        }
        return 'check-email';
      });
  }

  function signIn(emailAddress, password) {
    return post('/token?grant_type=password', { email: emailAddress, password: password })
      .then(function (data) {
        keep(data, emailAddress);
        return session;
      });
  }

  function signOut() {
    var token = session && session.access_token;
    forget();
    if (!token) return Promise.resolve();
    // Tell the server too, but don't let a failure here trap you signed in.
    return post('/logout', {}, token).catch(function () { return null; });
  }

  /* =============================================================== renewal == */

  function renew() {
    if (refreshing) return refreshing;   // one renewal at a time, not three

    refreshing = post('/token?grant_type=refresh_token', {
      refresh_token: session.refresh_token
    }).then(function (data) {
      keep(data);
      refreshing = null;
      return session.access_token;
    }).catch(function (err) {
      refreshing = null;
      // The refresh token is dead — signed out for real, not just offline.
      if (/refresh|token|grant|invalid/i.test(err.message || '')) forget();
      throw err;
    });

    return refreshing;
  }

  /**
   * The token to put in an Authorization header. Renews first, but only when
   * it's within a minute of expiring — otherwise this costs no request at all.
   */
  function token() {
    if (!signedIn()) return Promise.reject(new Error('Not signed in'));
    if (session.expires_at - Date.now() > 60000) {
      return Promise.resolve(session.access_token);
    }
    return renew();
  }

  return {
    on: on, signedIn: signedIn, email: email, userId: userId,
    signUp: signUp, signIn: signIn, signOut: signOut, token: token
  };
})();
