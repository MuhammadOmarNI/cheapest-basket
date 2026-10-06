/* ===========================================================================
   api.js — الكلام مع سيرفر الأسعار (FastAPI).

   ده الوصلة اللي كانت ناقصة: الباكند عنده ١٠٠٠+ سعر حقيقي، والتطبيق
   كان لسه بيطلب من اليوزر يكتبهم بإيده.

   كل حاجة هنا اختيارية: لو السيرفر مش شغّال، التطبيق بيفضل يشتغل
   بالضبط زي الأول — أسعار يدوية محفوظة على الجهاز. ده مقصود.
   السيرفر إضافة، مش شرط.
   =========================================================================== */

var API = (function () {
  'use strict';

  // السيرفر لما تشغّله على جهازك.
  var LOCAL = 'http://127.0.0.1:8010';

  /**
   * فين الـ API؟ مكانين محتملين:
   *
   *   منشور على Vercel  →  نفس الدومين، تحت /api
   *   على جهازك         →  127.0.0.1:8010
   *
   * مش بنخمّن: بنجرّب الاتنين في check() وناخد اللي يرد. كده نفس
   * الملف بالظبط بيشتغل في الحالتين من غير إعداد — ومن غير ما
   * تنسى تغيّر سطر قبل ما ترفع.
   *
   * ولسه تقدر تفرض عنوان من الـ console:
   *   localStorage.setItem('basket-api', 'http://192.168.1.5:8010')
   */
  function candidates() {
    try {
      var forced = localStorage.getItem('basket-api');
      if (forced) return [forced];
    } catch (e) { /* نافذة خاصة */ }

    // file:// مالهاش origin تنفع، فالمحلي هو الوحيد الممكن
    if (location.protocol !== 'http:' && location.protocol !== 'https:') {
      return [LOCAL];
    }

    return [location.origin + '/api', LOCAL];
  }

  var chosen = null;

  function base() { return chosen || candidates()[0]; }

  // الحالة. ready بتفضل false لحد ما check() ترد.
  var state = { ready: false, source: null, checked: false, units: null, canRefresh: true };

  /* ================================================================ fetch == */

  function call(path, options) {
    return fetch(base() + path, options).then(function (response) {
      return response.text().then(function (body) {
        var data = null;
        try { data = body ? JSON.parse(body) : null; } catch (e) { /* مش JSON */ }

        if (!response.ok) {
          var why = (data && data.detail) || body || ('HTTP ' + response.status);
          throw new Error(typeof why === 'string' ? why : JSON.stringify(why));
        }
        return data;
      });
    });
  }

  /* ================================================================ check == */

  /**
   * بيشوف السيرفر شغّال ولا لأ. بيتنادى مرة واحدة لكل صفحة.
   *
   * بيرجّع Promise بترد true/false — وعمرها ما ترفض. الصفحات بتسأل
   * السؤال ده عشان تقرر تعرض زرار ولا لأ، ومحتاجة إجابة مش استثناء.
   */
  function check() {
    if (state.checked) return Promise.resolve(state.ready);

    var list = candidates();

    // بنجرّب واحد ورا التاني لحد ما واحد يرد. مش بالتوازي: الأول
    // هو الأرجح، ومفيش داعي نضرب على الجهاز المحلي كل مرة.
    function tryNext(i) {
      if (i >= list.length) {
        state.ready = false;
        state.checked = true;
        return false;
      }
      chosen = list[i];
      return call('/config')
        .then(function (config) {
          state.ready = true;
          state.source = config.price_source || 'Online market';
          state.canRefresh = config.can_refresh !== false;
          state.checked = true;
          return true;
        })
        .catch(function () { return tryNext(i + 1); });
    }

    return tryNext(0);
  }

  /* ================================================================ units == */

  /**
   * الوحدات اللي السيرفر بيقبلها.
   *
   * مش مكتوبة هنا عن قصد: الباكند بيرفض أي وحدة مش في قايمته، فلو
   * كتبناها في المكانين هننسى واحد منهم يوم ما نضيف وحدة.
   *
   * fallback صغير عشان صفحة الوجبات تفضل تشتغل والسيرفر مقفول.
   */
  var FALLBACK_UNITS = [
    { value: 'g', label: 'g' }, { value: 'kg', label: 'kg' },
    { value: 'ml', label: 'ml' }, { value: 'l', label: 'L' },
    { value: 'piece', label: 'piece' }
  ];

  function units() {
    if (state.units) return Promise.resolve(state.units);

    return call('/units')
      .then(function (data) {
        state.units = data.units;
        return state.units;
      })
      .catch(function () {
        state.units = FALLBACK_UNITS;
        return state.units;
      });
  }

  /* ================================================================ price == */

  /**
   * سعر مكوّن واحد.
   *
   * بيرجّع: { low, high, basis, observations, provisional, ignored }
   * أو بيرمي Error برسالة مفهومة.
   */
  function price(ingredient, qty, unit, area) {
    var body = {
      ingredient: String(ingredient || '').trim(),
      area: area || 'Nicosia'
    };

    // الكمية والوحدة اختياريين، بس لازم يروحوا مع بعض: الباكند
    // محتاج الاتنين عشان يحوّل، وواحد لوحده مالوش معنى.
    if (qty && unit) {
      body.qty = Number(qty);
      body.unit = String(unit).toLowerCase();
    }

    return call('/price', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
  }

  return {
    base: base,
    check: check,
    units: units,
    price: price,
    isReady: function () { return state.ready; },
    source: function () { return state.source; },
    canRefresh: function () { return state.canRefresh; }
  };
})();
