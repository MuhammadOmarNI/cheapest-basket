/* ===========================================================================
   page-login.js — sign up, sign in, sign out.

   Signing in is optional. The app works fine without it, saved on this device;
   an account is only what lets your phone and your laptop see the same list.
   =========================================================================== */

(function () {
  'use strict';

  UI.start();

  var card = document.getElementById('auth-card');
  var mode = 'in';     // 'in' = sign in, 'up' = create an account
  var busy = false;

  function render(message, tone) {
    // Supabase isn't set up at all — nothing to sign in to.
    if (!CLOUD.on()) {
      card.innerHTML =
        '<div class="card-head"><h1>Accounts aren’t set up</h1></div>' +
        '<p class="hint">This app works perfectly well without one — everything is ' +
        'saved in this browser. An account only adds syncing between devices.</p>' +
        '<p class="hint">To switch it on, put your Supabase Project URL and ' +
        'Publishable key at the top of <code>js/cloud.js</code>.</p>';
      return;
    }

    // Already signed in — show who, and the way out.
    if (AUTH.signedIn()) {
      card.innerHTML =
        '<div class="card-head"><h1>You’re signed in</h1></div>' +
        '<p class="hint">As <strong>' + UI.esc(AUTH.email()) + '</strong>. Your meals and ' +
        'prices are saved to your account, so any device you sign in on shows the same list.</p>' +
        (message ? '<p class="hint ' + (tone || '') + '">' + UI.esc(message) + '</p>' : '') +
        '<div class="row">' +
          '<a class="btn" href="index.html" style="text-decoration:none">Back to the app</a>' +
          '<button type="button" class="btn-soft" id="signout-btn">Sign out</button>' +
        '</div>';
      return;
    }

    var creating = mode === 'up';

    card.innerHTML =
      '<div class="card-head">' +
        '<h1>' + (creating ? 'Create an account' : 'Sign in') + '</h1>' +
      '</div>' +

      '<p class="hint">' +
        (creating
          ? 'One account, and every device you sign in on shares the same meals and prices.'
          : 'Welcome back. Your list is waiting.') +
      '</p>' +

      '<form id="auth-form">' +
        '<label style="margin-bottom:12px">Email' +
          '<input type="email" id="email" autocomplete="email" required ' +
            'placeholder="you@example.com" style="margin-top:4px">' +
        '</label>' +
        '<label style="margin-bottom:14px">Password' +
          '<input type="password" id="password" required minlength="6" ' +
            'autocomplete="' + (creating ? 'new-password' : 'current-password') + '" ' +
            'placeholder="at least 6 characters" style="margin-top:4px">' +
        '</label>' +
        '<button type="submit" class="btn" id="submit-btn">' +
          (creating ? 'Create account' : 'Sign in') +
        '</button>' +
      '</form>' +

      (message ? '<p class="hint ' + (tone || '') + '">' + UI.esc(message) + '</p>' : '') +

      '<p class="hint">' +
        (creating
          ? 'Already have one? <a href="#" id="switch">Sign in instead</a>.'
          : 'No account yet? <a href="#" id="switch">Create one</a>.') +
      '</p>' +

      '<p class="hint">You can also just <a href="index.html">use it without an account</a> — ' +
      'everything stays on this device.</p>';
  }

  /* ================================================================ events == */

  document.addEventListener('click', function (e) {
    var el = e.target.closest('#switch, #signout-btn');
    if (!el) return;

    if (el.id === 'switch') {
      e.preventDefault();
      mode = mode === 'in' ? 'up' : 'in';
      render();

    } else if (el.id === 'signout-btn') {
      if (!confirm('Sign out? Your meals stay on this device.')) return;
      AUTH.signOut().then(function () {
        render();
        UI.refreshHeader();   // the pill has to stop claiming you're synced
        UI.toast('Signed out');
      });
    }
  });

  document.addEventListener('submit', function (e) {
    if (e.target.id !== 'auth-form') return;
    e.preventDefault();
    if (busy) return;

    var email = document.getElementById('email').value.trim();
    var password = document.getElementById('password').value;
    if (!email || !password) return;

    busy = true;
    var btn = document.getElementById('submit-btn');
    btn.disabled = true;
    btn.textContent = mode === 'up' ? 'Creating…' : 'Signing in…';

    var job = mode === 'up'
      ? AUTH.signUp(email, password)
      : AUTH.signIn(email, password).then(function () { return 'signed-in'; });

    job.then(function (result) {
      busy = false;

      if (result === 'check-email') {
        mode = 'in';
        render('Account created. Check ' + email + ' for a confirmation link, then sign in.', 'good');
        return;
      }

      // Signed in. Pull whatever the account already holds, or seed it with
      // what's on this device if the account is brand new.
      UI.toast('Signed in', 'good');
      UI.refreshHeader();   // drawn while you were still signed out
      return CLOUD.afterSignIn().then(function (outcome) {
        // 'pulled' reloads the page by itself; anything else lands us here.
        if (outcome !== 'pulled') {
          render(outcome === 'seeded'
            ? 'Your meals on this device are now saved to your account.'
            : null, 'good');
        }
      });

    }).catch(function (err) {
      busy = false;
      var text = err.message || 'Something went wrong';
      // Supabase's wording for this one is confusing; say it plainly.
      if (/invalid login/i.test(text)) text = 'That email and password don’t match.';
      if (/already registered/i.test(text)) text = 'That email already has an account — sign in instead.';
      render(text, 'bad');
    });
  });

  render();
})();
