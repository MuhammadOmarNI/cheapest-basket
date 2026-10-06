"""
اختبار القاعدة الجديدة: الموديل الضعيف نتيجته ما تتخزّنش.

دي أهم حاجة في التعديل ده. لو اتكسرت، حكم ضعيف هيتسجّل في
الداتابيز ويعيش هناك للأبد — ومحدش هيلاحظ.
"""
import sys, json, types, asyncio, httpx
import settings as settings_module

if "fastapi" not in sys.modules:
    class HTTPException(Exception):
        def __init__(self, status_code, detail=""):
            super().__init__(f"{status_code}: {detail}")
            self.status_code, self.detail = status_code, detail
    stub = types.ModuleType("fastapi")
    stub.HTTPException = HTTPException
    sys.modules["fastapi"] = stub

settings_module.settings.supabase_url = "https://demo.supabase.co"
settings_module.settings.supabase_service_key = "k"
settings_module.settings.gemini_api_key = "k"
settings_module.settings.gemini_model = "strong"
settings_module.settings.gemini_fallback_model = "weak"

import store, matcher

failures = []


def check(label, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {label}" + ("" if cond else f"  {detail}"))
    if not cond:
        failures.append(label)


# --- نسخة مبسّطة من _match_products زي ما هي في main.py ---
saves = []


async def match_products(ingredient):
    saved = store.get_ingredient(ingredient)
    if saved:
        return list(saved.get("skus") or []), False

    terms, model_a = await matcher.turkish_terms(ingredient)
    candidates = store.search_by_terms(terms)
    skus, model_b = await matcher.pick_matches(ingredient, candidates)

    strong = settings_module.settings.gemini_model
    trusted = model_a == strong and model_b == strong
    if trusted:
        store.save_ingredient(ingredient, terms, skus)
        saves.append(ingredient)
    return skus, not trusted


# --- Supabase مزيّف ---
stored = {}


def fake_db(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if "ingredient_map" in path:
        if request.method == "POST":
            row = json.loads(request.content)[0]
            stored[row["ingredient_norm"]] = row
            return httpx.Response(201, text="")
        key = request.url.params.get("ingredient_norm", "").replace("eq.", "")
        return httpx.Response(200, json=[stored[key]] if key in stored else [])
    return httpx.Response(200, json=[
        {"sku": "2900882", "name": "KIRNI PILIC GOGUS FILLET", "price": 322.0,
         "currency": "TRY", "category": "tavuk", "url": "https://x/1",
         "fetched_at": "2026-09-26T23:50:00Z", "source": "s"},
    ])


real_init = httpx.Client.__init__
httpx.Client.__init__ = lambda self, *a, **kw: real_init(
    self, *a, **{**kw, "transport": httpx.MockTransport(fake_db)})

# --- Gemini مزيّف: الموديل "strong" بيقع أو لأ حسب الإعداد ---
strong_is_down = {"yes": False}


def fake_gemini(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    model = body["model"]
    if model == "strong" and strong_is_down["yes"]:
        return httpx.Response(503, json={"error": {"message": "high demand"}})
    payload = ({"terms": ["gogus"]} if "SINGLE WORDS" in body["input"]
               else {"skus": ["2900882"]})
    return httpx.Response(200, json={"outputText": json.dumps(payload)})


real_async_init = httpx.AsyncClient.__init__
httpx.AsyncClient.__init__ = lambda self, *a, **kw: real_async_init(
    self, *a, **{**kw, "transport": httpx.MockTransport(fake_gemini)})

# ملحوظة: matcher.asyncio هو نفس موديول asyncio — مش نسخة منه.
# لازم نمسك الأصلية الأول، وإلا اللامبدا هتنادي على نفسها.
_real_run = asyncio.run
_real_sleep = asyncio.sleep
async def _no_sleep(seconds):
    pass
asyncio.sleep = _no_sleep
run = _real_run

# ======================================================== الموديل القوي ==
print("== الموديل القوي شغّال ==")
strong_is_down["yes"] = False
skus, provisional = run(match_products("chicken breast"))
check("لقى المنتج", skus == ["2900882"], skus)
check("مش مؤقتة", provisional is False)
check("اتحفظت", "chicken breast" in saves)
check("وموجودة في الداتابيز", "chicken breast" in stored)

# ======================================================= الموديل الضعيف ==
print("\n== الموديل القوي واقع، البديل اشتغل ==")
strong_is_down["yes"] = True
skus, provisional = run(match_products("milk"))
check("لسه بيرد نتيجة لليوزر", skus == ["2900882"], skus)
check("بس متعلّمة إنها مؤقتة", provisional is True)
check("وما اتحفظتش", "milk" not in saves)
check("والداتابيز نضيفة", "milk" not in stored, list(stored))

print("\n== ولما القوي يرجع ==")
strong_is_down["yes"] = False
skus, provisional = run(match_products("milk"))
check("بيعيد الحساب", provisional is False)
check("ودلوقتي بيحفظ", "milk" in stored)

print("\n== المحفوظ ما بيتحسبش تاني ==")
before = len(saves)
skus, provisional = run(match_products("chicken breast"))
check("قراها من الداتابيز", skus == ["2900882"])
check("مفيش حفظ جديد", len(saves) == before)

print()
print("ALL PASSED" if not failures else f"PROBLEMS: {failures}")
sys.exit(1 if failures else 0)
