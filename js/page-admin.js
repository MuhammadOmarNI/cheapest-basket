/* ===========================================================================
   page-admin.js — صفحة الأدمن: اختيار المصدر، التحديث، وجدول الأسعار.

   كل حاجة هنا بتمرّ على الباكند المحلي. الصفحة نفسها مش بتلمس Supabase
   ولا بتعرف مفتاحه — لأن مفتاح الكتابة (service_role) عايش على السيرفر
   بس. لو كان في المتصفح، أي حد يفتح View Source ياخده ويعدّل الأسعار.
   =========================================================================== */

(function () {
  'use strict';

  UI.start({ bare: 'Admin' });

  // العنوان بييجي من api.js — بيلاقي السيرفر لوحده سواء منشور
  // (نفس الدومين) أو على جهازك (127.0.0.1:8010). كان هنا ثابت
  // بنفس الاسم، وكان بيحجب الموديول كله.

  var apiState    = document.getElementById('api-state');
  var modesBox    = document.getElementById('modes');
  var modeState   = document.getElementById('mode-state');
  var dbSummary   = document.getElementById('db-summary');
  var refreshBtn  = document.getElementById('refresh-btn');
  var refreshMsg  = document.getElementById('refresh-msg');
  var progress    = document.getElementById('progress');
  var progressFill= document.getElementById('progress-fill');
  var progressVal = document.getElementById('progress-value');
  var searchInput = document.getElementById('search');
  var tableBody   = document.querySelector('#prices tbody');
  var rowsCount   = document.getElementById('rows-count');

  document.getElementById('api-url').textContent = API.base();

  /* ================================================================ HTTP == */

  /**
   * نداء واحد للباكند. بيرمي Error برسالة مفهومة في كل حالة فشل،
   * عشان كل مكان بينادي عليه يتعامل مع نوع واحد من الأخطاء.
   *
   * بيضيف الـ token بتاعك لو إنت مسجّل دخول. الباكند هو اللي بيقرر
   * إن كان ده كفاية ولا لأ — الواجهة ما بتحكمش على صلاحيات.
   */
  function call(path, options) {
    return withToken(options).then(function (opts) {
      return send(path, opts);
    });
  }

  /**
   * الزحف مستحيل على استضافة serverless — ٣٦ دقيقة مقابل سقف ٣٠٠
   * ثانية. بنخفي الزرار بدل ما نسيبه يضغط ويستنى ويشوف 501.
   */
  function applyRefreshSupport() {
    if (API.canRefresh()) return;
    refreshBtn.hidden = true;
    refreshMsg.textContent =
      'التحديث بيتعمل من جهازك: شغّل python tools/refresh.py — الموقع هنا بيقرا بس.';
  }

  function withToken(options) {
    var opts = options || {};
    if (!(window.AUTH && AUTH.signedIn())) return Promise.resolve(opts);

    return AUTH.token()
      .then(function (token) {
        var headers = {};
        Object.keys(opts.headers || {}).forEach(function (k) {
          headers[k] = opts.headers[k];
        });
        headers.Authorization = 'Bearer ' + token;
        var copy = {};
        Object.keys(opts).forEach(function (k) { copy[k] = opts[k]; });
        copy.headers = headers;
        return copy;
      })
      // الـ token مش راضي يتجدد؟ نكمّل من غيره — الباكند هيرد 401
      // برسالة مفهومة، وده أحسن من إننا نوقف هنا بصمت.
      .catch(function () { return opts; });
  }

  function send(path, options) {
    return fetch(API.base() + path, options)
      .then(function (response) {
        return response.text().then(function (body) {
          var data = null;
          try { data = body ? JSON.parse(body) : null; } catch (e) { /* مش JSON */ }

          if (!response.ok) {
            // FastAPI بيحط رسالة الغلط في detail
            var why = (data && data.detail) || body || ('HTTP ' + response.status);
            throw new Error(typeof why === 'string' ? why : JSON.stringify(why));
          }
          return data;
        });
      })
      .catch(function (error) {
        // TypeError من fetch = السيرفر مش موجود خالص (مش رد بخطأ)
        if (error instanceof TypeError) {
          throw new Error('السيرفر مش شغّال على ' + API.base());
        }
        throw error;
      });
  }

  /* ============================================================== المصدر == */

  function loadMode() {
    return call('/admin/settings').then(function (row) {
      var input = modesBox.querySelector('input[value="' + row.price_mode + '"]');
      if (input) input.checked = true;
      modeState.textContent = row.price_mode === 'ai' ? 'بحث مؤرّض' : 'زحف الموقع';
    });
  }

  modesBox.addEventListener('change', function (e) {
    var input = e.target.closest('input[name="mode"]');
    if (!input) return;

    modeState.textContent = 'بيحفظ…';
    call('/admin/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: input.value })
    })
      .then(function (row) {
        modeState.textContent = row.price_mode === 'ai' ? 'بحث مؤرّض' : 'زحف الموقع';
        UI.toast('الطريقة اتغيّرت', 'good');
      })
      .catch(function (error) {
        modeState.textContent = 'ما اتحفظش';
        UI.toast(error.message, 'bad');
        loadMode();          // رجّع الاختيار للحقيقة بدل ما تسيبه على كدب
      });
  });

  /* ============================================================= التحديث == */

  var poller = null;

  function paintJob(job) {
    var running = job.running;

    refreshBtn.disabled = running;
    refreshBtn.textContent = running ? 'بيحدّث…' : 'تحديث الأسعار';
    refreshMsg.textContent = job.message || '';

    // شريط التقدم يظهر وقت الشغل بس
    progress.hidden = !running || !job.total;

    if (running && job.total) {
      var percent = Math.round((job.done / job.total) * 100);
      progressFill.style.width = percent + '%';
      progressVal.textContent = percent + '%';
    }

    if (job.stage === 'error') refreshMsg.className = 'hint admin-error';
    else refreshMsg.className = 'hint';

    return running;
  }

  function poll() {
    call('/admin/refresh/status')
      .then(function (job) {
        if (!paintJob(job)) {
          // خلص: وقّف السؤال وحدّث الأرقام والجدول
          clearInterval(poller);
          poller = null;
          loadPrices();
          if (job.stage === 'done') UI.toast(job.message, 'good');
          if (job.stage === 'error') UI.toast('التحديث فشل', 'bad');
        }
      })
      .catch(function (error) {
        clearInterval(poller);
        poller = null;
        refreshMsg.textContent = error.message;
        refreshBtn.disabled = false;
      });
  }

  function startPolling() {
    if (poller) return;
    // كل ٣ ثواني كفاية — التحديث بياخد دقايق، مفيش داعي نسأل كل نص ثانية
    poller = setInterval(poll, 3000);
    poll();
  }

  refreshBtn.addEventListener('click', function () {
    refreshBtn.disabled = true;
    refreshMsg.textContent = 'بيبدأ…';

    call('/admin/refresh', { method: 'POST' })
      .then(startPolling)
      .catch(function (error) {
        refreshBtn.disabled = false;
        refreshMsg.textContent = error.message;
        UI.toast(error.message, 'bad');
      });
  });

  /* ============================================================== الجدول == */

  function when(iso) {
    if (!iso) return '—';
    var d = new Date(iso);
    return isNaN(d) ? '—' : d.toLocaleDateString('ar-EG', {
      day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
    });
  }

  function loadPrices() {
    var q = searchInput.value.trim();
    tableBody.innerHTML = '<tr><td colspan="4" class="muted">بيحمّل…</td></tr>';

    call('/admin/prices?limit=200&q=' + encodeURIComponent(q))
      .then(function (data) {
        dbSummary.textContent = data.summary.count
          ? data.summary.count + ' منتج · آخر تحديث ' + when(data.summary.last_updated)
          : 'الجدول فاضي';

        rowsCount.textContent = data.rows.length
          ? 'بيعرض ' + data.rows.length
          : '';

        if (!data.rows.length) {
          tableBody.innerHTML = '<tr><td colspan="4" class="muted">' +
            (q ? 'مفيش نتيجة لـ "' + UI.esc(q) + '"' :
                 'مفيش أسعار لسه — اضغط تحديث') + '</td></tr>';
          return;
        }

        tableBody.innerHTML = data.rows.map(function (r) {
          var name = r.url
            ? '<a href="' + UI.esc(r.url) + '" target="_blank" rel="noopener">' + UI.esc(r.name) + '</a>'
            : UI.esc(r.name);
          return '<tr>' +
            '<td>' + name + (r.sku ? '<span class="muted">' + UI.esc(r.sku) + '</span>' : '') + '</td>' +
            // dir="ltr" عشان الرقم والعملة يفضلوا "322 ₺" مش "₺ 322".
            // الصفحة RTL، والمتصفح بيقلب الترتيب من غير التحديد ده.
            '<td dir="ltr" class="admin-price">' + UI.money(r.price) + '</td>' +
            '<td>' + UI.esc(r.category || '—') + '</td>' +
            '<td>' + when(r.fetched_at) + '</td>' +
          '</tr>';
        }).join('');
      })
      .catch(function (error) {
        tableBody.innerHTML = '<tr><td colspan="4" class="admin-error">' +
          UI.esc(error.message) + '</td></tr>';
      });
  }

  document.getElementById('search-btn').addEventListener('click', loadPrices);
  searchInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') loadPrices();
  });


  /* ============================================================ جرّب سعر == */

  var tryIngredient = document.getElementById('try-ingredient');
  var tryQty        = document.getElementById('try-qty');
  var tryUnit       = document.getElementById('try-unit');
  var tryBtn        = document.getElementById('try-btn');
  var tryState      = document.getElementById('try-state');
  var tryResult     = document.getElementById('try-result');

  /**
   * بيملا الـ select من /units.
   *
   * ليه مش مكتوبة في الـ HTML؟ عشان الباكند بيرفض أي وحدة مش في
   * قايمته. لو كتبناها في المكانين، يوم ما نضيف وحدة هننسى واحد
   * منهم واليوزر هياخد 422 من غير ما يفهم ليه.
   */
  function loadUnits() {
    return call('/units').then(function (data) {
      tryUnit.innerHTML = data.units.map(function (u) {
        return '<option value="' + UI.esc(u.value) + '">' + UI.esc(u.label) + '</option>';
      }).join('');
      tryUnit.value = 'l';
    });
  }

  function money(value) {
    return UI.money(value);
  }

  function showRange(data) {
    var counted = data.observations.filter(function (o) { return o.total != null || data.basis.indexOf('per') === 0; });

    var head =
      '<div class="range">' +
        '<span class="range-num">' + money(data.low) + '</span>' +
        '<span class="range-arrow">→</span>' +
        '<span class="range-num">' + money(data.high) + '</span>' +
        '<span class="range-basis" dir="ltr">' + UI.esc(data.basis) + '</span>' +
      '</div>';

    var notes = [];
    if (data.ignored) {
      notes.push(data.ignored + ' منتج بوحدة مختلفة — مش داخل في الحساب');
    }
    if (data.provisional) {
      notes.push('نتيجة مؤقتة: الموديل البديل هو اللي ردّ، وما اتحفظتش');
    }
    var note = notes.length ? '<p class="range-note">' + UI.esc(notes.join(' · ')) + '</p>' : '';

    var rows = data.observations.map(function (o) {
      var out = o.total == null && data.basis.indexOf('per') !== 0;
      var name = o.source
        ? '<a href="' + UI.esc(o.source) + '" target="_blank" rel="noopener">' + UI.esc(o.shop) + '</a>'
        : UI.esc(o.shop);
      return '<tr' + (out ? ' class="dim"' : '') + '>' +
        '<td>' + name + (o.size ? '<span class="muted" dir="ltr">' + UI.esc(o.size) + '</span>' : '') + '</td>' +
        '<td dir="ltr" class="admin-price">' + money(o.price) + '</td>' +
        '<td dir="ltr" class="admin-price">' + (o.unit_price != null ? money(o.unit_price) : '—') + '</td>' +
        '<td dir="ltr" class="admin-price">' + (o.total != null ? money(o.total) : '—') + '</td>' +
      '</tr>';
    }).join('');

    tryResult.innerHTML = head + note +
      '<div class="scroller"><table><thead><tr>' +
        '<th>المنتج</th><th>سعر العلبة</th><th>سعر الوحدة</th><th>الإجمالي</th>' +
      '</tr></thead><tbody>' + rows + '</tbody></table></div>';
  }

  tryBtn.addEventListener('click', function () {
    var ingredient = tryIngredient.value.trim();
    if (!ingredient) { tryState.textContent = 'اكتب مكوّن'; return; }

    tryBtn.disabled = true;
    tryState.textContent = 'بيدوّر…';
    tryResult.innerHTML = '';

    call('/price', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ingredient: ingredient,
        qty: Number(tryQty.value) || 1,
        unit: tryUnit.value,
        area: 'Nicosia'
      })
    })
      .then(function (data) {
        tryState.textContent = data.observations.length + ' منتج';
        showRange(data);
      })
      .catch(function (error) {
        tryState.textContent = '';
        tryResult.innerHTML = '<p class="admin-error">' + UI.esc(error.message) + '</p>';
      })
      .then(function () { tryBtn.disabled = false; });
  });

  tryIngredient.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') tryBtn.click();
  });

  /* =============================================================== البداية == */

  // check() بيجرّب العناوين المحتملة ويثبّت اللي يرد. لازم يخلص
  // قبل أي نداء تاني، وإلا كل واحد هيجرّب لوحده.
  API.check().then(function () {
    return call('/config');
  })
    .then(function (config) {
      apiState.textContent = config.supabase_ready ? 'متصل' : 'Supabase مش مضبوط';
      if (!config.supabase_ready) {
        apiState.className = 'eyebrow admin-error';
        return;
      }
      applyRefreshSupport();
      return loadUnits().then(loadMode).then(loadPrices)
        .then(function () { if (API.canRefresh()) poll(); });
    })
    .catch(function (error) {
      apiState.textContent = error.message;
      apiState.className = 'eyebrow admin-error';
      tableBody.innerHTML = '<tr><td colspan="4" class="admin-error">' +
        UI.esc(error.message) + '</td></tr>';
    });
})();
