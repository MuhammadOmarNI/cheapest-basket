"""
اختبار المطابقة، وGemini مزيّف.

اللي بنتأكد منه:
  · الحاجز بيرمي أي sku الموديل اخترعه
  · تنضيف كلمات البحث (جمل، حروف تركية، كلمات قصيرة)
  · فلتر الـ OR في PostgREST مبني صح ومفيهوش حروف بتكسره
  · الربط المحفوظ بيمنع أي نداء لـ Gemini
"""
import sys, json, httpx, asyncio, types
import settings as settings_module

# fastapi مش متثبّت في بيئة الاختبار دي، وmatcher محتاج HTTPException منه
# بس. بنحط بديل صغير في sys.modules قبل الاستيراد بدل ما نثبّت المكتبة كلها.
if "fastapi" not in sys.modules:
    class HTTPException(Exception):
        def __init__(self, status_code, detail=""):
            super().__init__(f"{status_code}: {detail}")
            self.status_code, self.detail = status_code, detail
    stub = types.ModuleType("fastapi")
    stub.HTTPException = HTTPException
    sys.modules["fastapi"] = stub

settings_module.settings.supabase_url = "https://demo.supabase.co"
settings_module.settings.supabase_service_key = "service-key-123"
settings_module.settings.gemini_api_key = "fake-key"

import store, matcher

failures = []
sent = []


def check(label, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {label}" + ("" if cond else f"  {detail}"))
    if not cond:
        failures.append(label)


def equals(label, got, want):
    """للقيم. check() بتاخد شرط — لو بعتّ ليها قيمة، أي قيمة
    غير فاضية هتعدّي، والاختبار يبقى مش بيفحص حاجة."""
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f"  got={got!r} want={want!r}"))
    if not ok:
        failures.append(label)


CANDIDATES = [
    {"sku": "2900882", "name": "KIRNI PILIC GOGUS FILLET"},
    {"sku": "2900830", "name": "KIRNI PILIC GOGUS SIS SADE (kg)"},
    {"sku": "2900824", "name": "KIRNI PILIC BAGET BUT (kg)"},
]

gemini_reply = {"terms": ["gogus", "pilic", "tavuk"]}


def fake_gemini(request: httpx.Request) -> httpx.Response:
    sent.append(request)
    return httpx.Response(200, json={"outputText": json.dumps(gemini_reply)})


real_async_init = httpx.AsyncClient.__init__
httpx.AsyncClient.__init__ = lambda self, *a, **kw: real_async_init(
    self, *a, **{**kw, "transport": httpx.MockTransport(fake_gemini)})

run = asyncio.run

# ------------------------------------------------------------ كلمات البحث ---
print("== turkish_terms ==")
gemini_reply = {"terms": ["gogus", "pilic", "tavuk"]}
equals("بيرجّعها بالترتيب", run(matcher.turkish_terms("chicken breast"))[0],
       ["gogus", "pilic", "tavuk"])

body = json.loads(sent[-1].content)
check("بعت response_format", "response_format" in body, list(body))
check("والـ schema جواه", "schema" in body["response_format"])
check("مفيش tools (مش بحث مؤرّض)", "tools" not in body, list(body))

gemini_reply = {"terms": ["GÖĞÜS", "chicken breast fillet", "et", "  ", "gogus"]}
got, _ = run(matcher.turkish_terms("x"))
print("   من", gemini_reply["terms"], "→", got)
check("الحروف التركية اتبسّطت", "gogus" in got)
check("الجملة بقت أول كلمة", "chicken" in got, got)
check("الكلمة القصيرة اتشالت", "et" not in got, got)
check("المكرر اتشال", got.count("gogus") == 1, got)

gemini_reply = {"terms": []}
try:
    run(matcher.turkish_terms("x"))
    check("قايمة فاضية بترفع خطأ", False, "ما رفعش")
except Exception as e:
    check("قايمة فاضية بترفع خطأ", "502" in str(e) or "ما رجّعش" in str(e), str(e)[:60])

# ------------------------------------------------------------- الاختيار ---
print("\n== pick_matches والحاجز ==")
gemini_reply = {"skus": ["2900882", "2900830"]}
equals("بياخد الصح", run(matcher.pick_matches("chicken breast", CANDIDATES))[0],
       ["2900882", "2900830"])

gemini_reply = {"skus": ["2900882", "9999999", "INVENTED"]}
got, _ = run(matcher.pick_matches("chicken breast", CANDIDATES))
equals("المخترع اترمى", got, ["2900882"])

gemini_reply = {"skus": []}
equals("ولا واحد = قايمة فاضية", run(matcher.pick_matches("caviar", CANDIDATES))[0], [])

sent.clear()
check("مرشّحين فاضيين = مفيش نداء أصلاً",
      run(matcher.pick_matches("x", []))[0] == [] and len(sent) == 0)

# --------------------------------------------------------- استعلام الـ OR ---
print("\n== search_by_terms ==")
db_sent = []


def fake_db(request: httpx.Request) -> httpx.Response:
    db_sent.append(request)
    if "ingredient_map" in request.url.path:
        return httpx.Response(200, json=[])
    return httpx.Response(200, json=[
        {"sku": "2900882", "name": "KIRNI PILIC GOGUS FILLET", "price": 322.0,
         "currency": "TRY", "category": "tavuk", "url": "https://x/1",
         "fetched_at": "2026-09-26T23:50:00Z", "source": "kibrissanalmarket.com"},
        {"sku": None, "name": "NO BARCODE", "price": 10.0, "currency": "TRY",
         "category": "x", "url": None, "fetched_at": "2026-09-26T23:50:00Z",
         "source": "kibrissanalmarket.com"},
    ])


real_init = httpx.Client.__init__
httpx.Client.__init__ = lambda self, *a, **kw: real_init(
    self, *a, **{**kw, "transport": httpx.MockTransport(fake_db)})

rows = store.search_by_terms(["gogus", "pilic"])
cond = db_sent[-1].url.params.get("or")
print("   الفلتر:", cond)
check("شكل الـ OR صح", cond == "(name_norm.ilike.*gogus*,name_norm.ilike.*pilic*)", cond)
check("اللي من غير باركود اتشال", len(rows) == 1, rows)

db_sent.clear()
store.search_by_terms(["go,gus)", "sü-t", "a"])
cond = db_sent[-1].url.params.get("or")
print("   بعد التنضيف:", cond)
check("الفاصلة والقوس اتشالوا", "," not in cond.replace("*,name_norm", "*|name_norm")
      .replace("|", "") or ")" not in cond[1:-1], cond)
check("الشرطة اتشالت", "sut" in cond, cond)
check("الحرف الواحد اتشال", "*a*" not in cond, cond)

print("\n== prices_by_skus ==")
db_sent.clear()
store.prices_by_skus(["2900882", "2900830"])
check("فلتر in صح", db_sent[-1].url.params.get("sku") == 'in.("2900882","2900830")',
      db_sent[-1].url.params.get("sku"))
check("مرتّب بالسعر", db_sent[-1].url.params.get("order") == "price.asc")

db_sent.clear()
check("قايمة فاضية = مفيش طلب",
      store.prices_by_skus([]) == [] and len(db_sent) == 0)



# ===========================================================================
# الإعادة عند 503
# ===========================================================================
print("\n== الإعادة (retry) ==")

waits = []
real_sleep = asyncio.sleep
async def no_sleep(seconds):          # ما نستناش فعلاً في الاختبار
    waits.append(seconds)
asyncio.sleep = no_sleep

plan = []          # ردود متتابعة
attempts = {'n': 0}

def flaky(request: httpx.Request) -> httpx.Response:
    i = attempts['n']
    attempts['n'] += 1
    status, payload = plan[min(i, len(plan) - 1)]
    if status == 200:
        return httpx.Response(200, json={"outputText": json.dumps(payload)})
    return httpx.Response(status, json={"error": {"message": payload}})

httpx.AsyncClient.__init__ = lambda self, *a, **kw: real_async_init(
    self, *a, **{**kw, "transport": httpx.MockTransport(flaky)})

# --- 503 مرتين بعدين نجح ---
attempts['n'] = 0; waits.clear()
plan = [(503, "high demand"), (503, "high demand"), (200, {"terms": ["sut"]})]
equals("نجح بعد محاولتين فاشلتين", run(matcher.turkish_terms("milk"))[0], ["sut"])
equals("عمل 3 محاولات", attempts['n'], 3)
equals("استنى 2 ثم 5 ثواني", waits, [2, 5])

# --- 503 دايماً ---
attempts['n'] = 0; waits.clear()
plan = [(503, "high demand")]
try:
    run(matcher.turkish_terms("milk"))
    check("بيستسلم بعد 3 محاولات", False, "ما رفعش خطأ")
except Exception as e:
    check("بيستسلم بعد 3 محاولات", "503" in str(e), str(e)[:70])
equals("مش أكتر من 3", attempts['n'], 3)

# --- 429: مفيش إعادة خالص ---
attempts['n'] = 0; waits.clear()
plan = [(429, "quota")]
try:
    run(matcher.turkish_terms("milk"))
    check("429 بيرفع خطأ", False, "ما رفعش")
except Exception as e:
    check("429 بيرفع خطأ", "429" in str(e), str(e)[:60])
equals("429 مفيش إعادة — الحصة مش هترجع بالإلحاح", attempts['n'], 1)

# --- 400: غلط في طلبنا، الإعادة مش هتنفع ---
attempts['n'] = 0
plan = [(400, "bad schema")]
try:
    run(matcher.turkish_terms("milk"))
    check("400 بيرفع خطأ", False, "ما رفعش")
except Exception as e:
    check("400 بيرفع 502", "502" in str(e), str(e)[:60])
equals("400 مفيش إعادة", attempts['n'], 1)



# ===========================================================================
# الموديل البديل
# ===========================================================================
print("\n== الموديل البديل ==")

asyncio.sleep = no_sleep
used = []

def by_model(request: httpx.Request) -> httpx.Response:
    model = json.loads(request.content)["model"]
    used.append(model)
    if model == "primary":
        return httpx.Response(503, json={"error": {"message": "high demand"}})
    return httpx.Response(200, json={"outputText": json.dumps({"terms": ["sut"]})})

httpx.AsyncClient.__init__ = lambda self, *a, **kw: real_async_init(
    self, *a, **{**kw, "transport": httpx.MockTransport(by_model)})

settings_module.settings.gemini_model = "primary"
settings_module.settings.gemini_fallback_model = "backup"

used.clear()
terms, model = run(matcher.turkish_terms("milk"))
equals("البديل أنقذ الطلب", terms, ["sut"])
equals("وقال إن البديل هو اللي رد", model, "backup")
equals("جرّب الأساسي 3 مرات ثم البديل", used, ["primary"] * 3 + ["backup"])

# --- من غير بديل: بيفشل ---
settings_module.settings.gemini_fallback_model = ""
used.clear()
try:
    run(matcher.turkish_terms("milk"))
    check("من غير بديل بيفشل", False, "ما رفعش")
except Exception as e:
    check("من غير بديل بيفشل", "503" in str(e), str(e)[:50])
equals("وما جربش موديل تاني", set(used), {"primary"})

# --- 429 ما بيروحش للبديل ---
def always_429(request):
    used.append(json.loads(request.content)["model"])
    return httpx.Response(429, json={"error": {"message": "quota"}})

httpx.AsyncClient.__init__ = lambda self, *a, **kw: real_async_init(
    self, *a, **{**kw, "transport": httpx.MockTransport(always_429)})

settings_module.settings.gemini_fallback_model = "backup"
used.clear()
try:
    run(matcher.turkish_terms("milk"))
except Exception:
    pass
equals("429 ما بيجربش البديل (الحصة للحساب كله)", used, ["primary"])

asyncio.sleep = real_sleep

print()
print("ALL PASSED" if not failures else f"PROBLEMS: {failures}")
sys.exit(1 if failures else 0)
