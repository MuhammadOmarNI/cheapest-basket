"""
اختبار store.py من غير Supabase حقيقي.

بنستبدل طبقة النقل في httpx بواحدة مزيّفة بترد ردود جاهزة وتسجّل كل
طلب خرج. كده نتأكد إن الطلبات نفسها مبنية صح — الهيدرز، الـ params،
شكل الـ upsert — قبل ما نلمس داتابيز حقيقية.

الحتة الأهم اللي بنتأكد منها: Prefer: resolution=merge-duplicates
لو ناقص، تاني زحف هيفشل كله على أول منتج مكرر.
"""
import pathlib as _pathlib, sys as _sys
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parent.parent))

import json, sys, httpx
from lib import settings as settings_module

# نحط قيم وهمية قبل ما نستورد store
settings_module.settings.supabase_url = "https://demo.supabase.co"
settings_module.settings.supabase_service_key = "service-key-123"

from lib import store

failures = []
sent = []          # كل طلب خرج، بنفحصه بعدين


def check(label, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {label}" + ("" if cond else f"  {detail}"))
    if not cond:
        failures.append(label)


def handler(request: httpx.Request) -> httpx.Response:
    sent.append(request)
    path = request.url.path

    if path.endswith("admin_settings"):
        if request.method == "GET":
            return httpx.Response(200, json=[{"id": 1, "price_mode": "site"}])
        return httpx.Response(200, json=[{"id": 1, "price_mode": "ai"}])

    if path.endswith("product_prices"):
        if request.method == "POST":
            return httpx.Response(201, text="")
        # طلب العدّ بييجي بهيدر Range
        if request.headers.get("Range") == "0-0":
            return httpx.Response(206, json=[{"id": 1}],
                                  headers={"content-range": "0-0/1487"})
        if request.url.params.get("order", "").startswith("fetched_at"):
            return httpx.Response(200, json=[{"fetched_at": "2026-09-26T21:00:00Z"}])
        return httpx.Response(200, json=[
            {"sku": "2900882", "name": "KIRNI PILIC GOGUS FILLET", "price": 322.0,
             "currency": "TRY", "category": "tavuk", "url": "https://x/1",
             "fetched_at": "2026-09-26T21:00:00Z", "source": "kibrissanalmarket.com"},
        ])

    return httpx.Response(404, text="unexpected path " + path)


# نخلّي كل httpx.Client جديد يستخدم الطبقة المزيّفة
real_init = httpx.Client.__init__
def patched_init(self, *a, **kw):
    kw["transport"] = httpx.MockTransport(handler)
    real_init(self, *a, **kw)
httpx.Client.__init__ = patched_init


# ------------------------------------------------------------- الإعدادات ---
print("== get_settings ==")
result = store.get_settings()
check("بيرجّع الصف", result["price_mode"] == "site", result)
req = sent[-1]
check("بيسأل على الصف رقم 1", req.url.params.get("id") == "eq.1")
check("المفتاح في apikey", req.headers.get("apikey") == "service-key-123")
check("والمفتاح في Authorization", req.headers.get("authorization") == "Bearer service-key-123")

print("\n== set_mode ==")
store.set_mode("ai")
req = sent[-1]
check("بيستخدم PATCH مش POST", req.method == "PATCH", req.method)
check("بيبعت الطريقة الجديدة", json.loads(req.content)["price_mode"] == "ai")

# ---------------------------------------------------------------- الحفظ ---
print("\n== upsert_prices ==")
sent.clear()
rows = [{"source": "s", "name": f"P{i}", "name_norm": f"p{i}", "price": i + 1.0}
        for i in range(1203)]          # أكتر من دفعتين عشان نتأكد من التقسيم
saved = store.upsert_prices(rows)

check("رجّع العدد الكامل", saved == 1203, saved)
check("قسّمها 3 دفعات (500+500+203)", len(sent) == 3, f"{len(sent)} طلبات")
sizes = [len(json.loads(r.content)) for r in sent]
check("أحجام الدفعات صح", sizes == [500, 500, 203], sizes)

prefer = sent[0].headers.get("Prefer", "")
check("فيه resolution=merge-duplicates", "resolution=merge-duplicates" in prefer, prefer)
check("on_conflict = source,name", sent[0].url.params.get("on_conflict") == "source,name")

print("\n== upsert بقايمة فاضية ==")
sent.clear()
check("مش بيبعت طلب أصلاً", store.upsert_prices([]) == 0 and len(sent) == 0)

# ---------------------------------------------------------------- البحث ---
print("\n== search_prices ==")
sent.clear()
store.search_prices("GÖĞÜS")
params = sent[-1].url.params
check("بيبسّط الحروف التركية قبل البحث",
      params.get("name_norm") == "ilike.*gogus*", params.get("name_norm"))

sent.clear()
store.search_prices("")
check("بحث فاضي = مفيش فلتر", "name_norm" not in sent[-1].url.params)

print("\n== count_prices ==")
sent.clear()
summary = store.count_prices()
check("قرا العدد من content-range", summary["count"] == 1487, summary)
check("وجاب آخر تحديث", summary["last_updated"] == "2026-09-26T21:00:00Z", summary)

# --------------------------------------------------------------- الأخطاء ---
print("\n== لما Supabase يرفض ==")
def bad(request):
    return httpx.Response(401, text="Invalid API key")
httpx.Client.__init__ = lambda self, *a, **kw: real_init(self, *a, **{**kw, "transport": httpx.MockTransport(bad)})
try:
    store.get_settings()
    check("بيرفع StoreError", False, "ما رفعش حاجة")
except store.StoreError as error:
    check("بيرفع StoreError", True)
    check("والرسالة فيها الكود", "401" in str(error), str(error))

print()
print("ALL PASSED" if not failures else f"PROBLEMS: {failures}")
sys.exit(1 if failures else 0)
