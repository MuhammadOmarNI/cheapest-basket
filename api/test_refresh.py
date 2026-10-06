"""
اختبار التعديلين الجداد:
  1. الزحف بيحفظ قسم قسم، مش مرة واحدة في الآخر
  2. حماية الأدمن
"""
import sys, types, asyncio, json, httpx
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
settings_module.settings.crawl_delay_seconds = 0      # مش هننتظر في الاختبار

import crawler, store

failures = []
run = asyncio.run


def check(label, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {label}" + ("" if cond else f"  {detail}"))
    if not cond:
        failures.append(label)


def equals(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f"  got={got!r} want={want!r}"))
    if not ok:
        failures.append(label)


# ---------------------------------------------------------------- fixtures ---
HOME = """
<a href="/urun-grubu/et-tavuk-denizurunleri/tavuk/">1</a>
<a href="/urun-grubu/meyve-ve-sebze/sebze/">2</a>
<a href="/urun-grubu/temel-gida/ekmek/">3</a>
"""


def page(names):
    return "".join(
        f'<div class="product-inner"><a href="/urunler/{n}/" '
        f'class="woocommerce-loop-product__link"><div class="skucuk">{i}</div>'
        f'<h2 class="woocommerce-loop-product__title">{n}</h2></a>'
        f'<span class="price">{10 + i}.00 ₺</span></div>'
        for i, n in enumerate(names, start=1)
    )


PAGES = {
    "/": HOME,
    "/urun-grubu/et-tavuk-denizurunleri/tavuk/": page(["TAVUK A", "TAVUK B"]),
    "/urun-grubu/meyve-ve-sebze/sebze/":          page(["SEBZE A"]),
    "/urun-grubu/temel-gida/ekmek/":              page(["EKMEK A", "EKMEK A"]),  # مكرر
}

fail_on = {"path": None}


def site(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == fail_on["path"]:
        return httpx.Response(500, text="boom")
    return httpx.Response(200, text=PAGES.get(path, "<html></html>"))


real_async_init = httpx.AsyncClient.__init__
httpx.AsyncClient.__init__ = lambda self, *a, **kw: real_async_init(
    self, *a, **{**kw, "transport": httpx.MockTransport(site)})


# ======================================================== الحفظ قسم قسم ==
print("== الزحف بيحفظ بعد كل قسم ==")
batches = []


async def save(batch):
    batches.append([r["name"] for r in batch])

result = run(crawler.crawl(save=save))

equals("3 أقسام", result["categories"], 3)
equals("3 دفعات حفظ — مش واحدة", len(batches), 3)
equals("كل دفعة قسم لوحده", batches,
       [["TAVUK A", "TAVUK B"], ["SEBZE A"], ["EKMEK A"]])
equals("المكرر جوه القسم اتشال", batches[2], ["EKMEK A"])
equals("العدد الكلي", result["products"], 4)
equals("والمحفوظ", result["saved"], 4)

# ===================================================== لما قسم يقع ==
print("\n== قسم بيفشل في النص ==")
batches.clear()
fail_on["path"] = "/urun-grubu/meyve-ve-sebze/sebze/"
result = run(crawler.crawl(save=save))

equals("الأقسام السليمة اتحفظت", batches, [["TAVUK A", "TAVUK B"], ["EKMEK A"]])
equals("والفشل اتسجّل", len(result["errors"]), 1)
check("الخطأ فيه اسم القسم", "sebze" in result["errors"][0], result["errors"])
equals("المحفوظ = اللي نجح", result["saved"], 3)
fail_on["path"] = None

# =========================================== الحفظ من غير save callback ==
print("\n== من غير دالة حفظ ==")
result = run(crawler.crawl())
equals("بيزحف عادي", result["products"], 4)
equals("ومحفوظ = صفر", result["saved"], 0)

# =============================================== التقدم بيتبلّغ ==
print("\n== تقارير التقدم ==")
reports = []
run(crawler.crawl(progress=lambda **kw: reports.append(kw), save=save))
stages = [r.get("stage") for r in reports]
check("بيبلّغ عن الأقسام الأول", stages[0] == "categories", stages[:2])
check("وبعدين عن كل قسم", stages.count("crawling") == 4, stages)
last = reports[-1]
equals("آخر تقرير 3 من 3", (last["done"], last["total"]), (3, 3))
check("وفيه العدد المحفوظ", "saved" in last, last)

# ===================================================== حماية الأدمن ==
print("\n== whoami ==")
users = {"good-token": {"email": "Me@Example.com"}}


def auth(request: httpx.Request) -> httpx.Response:
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    if token in users:
        return httpx.Response(200, json=users[token])
    return httpx.Response(401, json={"message": "invalid"})


real_init = httpx.Client.__init__
httpx.Client.__init__ = lambda self, *a, **kw: real_init(
    self, *a, **{**kw, "transport": httpx.MockTransport(auth)})

equals("token صالح", store.whoami("good-token"), {"email": "Me@Example.com"})
equals("token مزوّر", store.whoami("fake"), None)
equals("من غير token", store.whoami(""), None)


# نسخة من require_admin زي ما هي في main.py
def admin_list():
    return [e.strip().lower() for e in settings_module.settings.admin_emails.split(",") if e.strip()]


async def require_admin(authorization=None):
    from fastapi import HTTPException
    allowed = admin_list()
    if not allowed:
        return "dev"
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        raise HTTPException(401, "لازم تسجّل دخول.")
    user = await asyncio.to_thread(store.whoami, token)
    if not user:
        raise HTTPException(401, "الجلسة انتهت.")
    email = (user.get("email") or "").lower()
    if email not in allowed:
        raise HTTPException(403, "مش أدمن.")
    return email


def status_of(authorization):
    try:
        return run(require_admin(authorization))
    except Exception as e:
        return getattr(e, "status_code", "?")


print("\n== require_admin ==")
settings_module.settings.admin_emails = ""
equals("قايمة فاضية = مفتوح (تطوير)", status_of(None), "dev")

settings_module.settings.admin_emails = "me@example.com"
equals("من غير header", status_of(None), 401)
equals("header فاضي", status_of("Bearer "), 401)
equals("token مزوّر", status_of("Bearer fake"), 401)
equals("أدمن صح", status_of("Bearer good-token"), "me@example.com")

users["other-token"] = {"email": "someone@else.com"}
equals("يوزر عادي = 403 مش 401", status_of("Bearer other-token"), 403)

settings_module.settings.admin_emails = "  ME@EXAMPLE.COM , other@x.com "
equals("حالة الحروف والمسافات ما تفرقش", status_of("Bearer good-token"), "me@example.com")

print()
print("ALL PASSED" if not failures else f"PROBLEMS: {failures}")
sys.exit(1 if failures else 0)
