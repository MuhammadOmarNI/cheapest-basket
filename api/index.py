import os
import pathlib
import sys

# الجذر لازم يبقى في المسار عشان "lib" تتلاقى. Vercel بيحط الملف ده
# جوه api/، وبايثون بيضيف فولدر الملف مش الجذر.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime, timezone
import asyncio
import httpx

from lib.settings import settings     # الإعدادات
from lib import store                  # كلام Supabase
from lib import crawler                # الزحف
from lib import matcher                # ربط المكوّن بالمنتج
from lib import sizes                  # قراءة الحجم من اسم المنتج


# Vercel بيحط المتغير ده لوحده. بنستعمله نفرّق بين "على جهازي"
# و"منشور على النت" — القواعد مختلفة بين الاتنين.
ON_VERCEL = bool(os.environ.get("VERCEL"))

app = FastAPI(title="Cheapest Basket API")

# ---------------------------------------------------------------------------
# CORS — لازم، وإلا صفحة الأدمن مش هتقدر تكلّم السيرفر ده
#
# المتصفح بيمنع صفحة على origin إنها تقرا رد من origin تاني، إلا لو
# السيرفر قال صريح إنه موافق. صفحتنا فاتحة من file:// أو من 127.0.0.1:5500
# والسيرفر على 127.0.0.1:8010 — دول origins مختلفة.
#
# allow_origins=["*"] مقبول هنا لأن الـ API مالهوش أسرار للقراءة.
# في الإنتاج: حدّد الدومين بالظبط.
# ---------------------------------------------------------------------------
# منشور: الواجهة والـ API على نفس الدومين، فمفيش CORS أصلاً.
# على الجهاز: الصفحة بتتفتح من file:// أو من بورت تاني، فمحتاجينه.
if not ON_VERCEL:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ===========================================================================
# الأشكال (Models)
# ===========================================================================

class PriceRequest(BaseModel):
    ingredient: str = Field(min_length=1, max_length=80)
    qty: float | None = Field(default=None, gt=0, le=10000)
    # الوحدة لازم تكون واحدة من قايمة النظام. Pydantic بيرفض غيرها
    # بـ 422 قبل ما الكود يشتغل أصلاً — الواجهة بتبني الـ select من
    # نفس القايمة، فالاتنين ما يختلفوش أبداً.
    unit: Literal["g", "kg", "ml", "l", "piece"] | None = None
    area: str = Field(min_length=2, max_length=120)


class Observation(BaseModel):
    price: float
    shop: str
    source: str
    size: str | None = None          # "1 L" — مقروء من اسم المنتج
    unit_price: float | None = None  # ₺ لكل لتر أو كيلو
    total: float | None = None       # تكلفة الكمية اللي اليوزر طلبها


class PriceRange(BaseModel):
    ingredient: str
    low: float
    high: float
    observations: list[Observation]
    # على أي أساس اتحسب low/high: "per L" أو "per KG" أو "per item".
    # من غير السطر ده، رقمين لوحدهم ممكن يتقروا غلط.
    basis: str = "per item"
    # منتجات مالهاش وحدة مطابقة فاستبعدناها من الحساب.
    # بنعدّها عشان الواجهة تقول "و3 منتجات تانية" بدل ما تختفي بهدوء.
    ignored: int = 0
    # True يعني الموديل البديل (الأضعف) هو اللي طلّع الربط، وإحنا
    # ما حفظناش النتيجة. الواجهة تقدر تنبّه اليوزر، والطلب الجاي
    # هيعيد الحساب بالموديل القوي.
    provisional: bool = False


class ModeRequest(BaseModel):
    # Literal كان هيبقى أضيق، بس إحنا سايبين الداتابيز هي اللي ترفض
    # القيمة الغلط عن طريق الـ CHECK constraint. مكان واحد للقاعدة.
    mode: str = Field(pattern="^(site|ai)$")


# ===========================================================================
# الأساسيات
# ===========================================================================

@app.get("/health")
def health():
    return {"ok": True}


@app.get("/config")
def config():
    """
    بيرجّع إيه جاهز وإيه لأ — بـ true/false بس.
    عمره ما يرجّع مفتاح ولا جزء من مفتاح.
    """
    # كل قيمة لوحدها، مش واحدة مجمّعة. "supabase_ready: false" بتقولك
    # إن في مشكلة؛ الحقول دي بتقولك مشكلة إيه بالظبط ومن غير ما نطبع أي مفتاح.
    return {
        "gemini_ready": bool(settings.gemini_api_key),
        "supabase_ready": bool(settings.supabase_url and settings.supabase_service_key),
        "supabase_url_set": bool(settings.supabase_url),
        "supabase_url_has_scheme": settings.supabase_url.startswith("https://"),
        "supabase_key_set": bool(settings.supabase_service_key),
        # طول المفتاح مش سر، لكنه بيفرق: مفتاح مقصوص بالغلط
        # هيبان هنا فوراً بدل ما ندوّر على 401 غامضة
        "supabase_key_length": len(settings.supabase_service_key),
        # لو false، أي حد يفتح الصفحة يقدر يضغط تحديث.
        # مقبول وإنت بتطوّر على جهازك، كارثة لو نشرت كده.
        "admin_protected": bool(admin_list()),
        # اسم المحل اللي الأسعار جاية منه. الواجهة بتستعمله عشان
        # تحط الأسعار في العمود الصح — بدل ما تكتبه بإيدها وتختلف
        # عن الباكند يوم ما نضيف مصدر تاني.
        "price_source": crawler.SOURCE_LABEL,
        # الواجهة بتخفي زرار التحديث لما يكون مستحيل أصلاً
        "can_refresh": not ON_VERCEL,
    }


@app.get("/units")
def units():
    """
    الوحدات اللي اليوزر يقدر يختار منها.

    الواجهة بتبني الـ select box من هنا بدل ما تكتبها بإيدها.
    كده يوم ما نضيف وحدة، تظهر لوحدها في كل مكان.
    """
    return {"units": [{"value": u["value"], "label": u["label"]} for u in sizes.UNITS]}


@app.get("/models")
async def models():
    """
    الموديلات المتاحة لمفتاحك.

    بيرجّع الأسماء بس — مفيش أي جزء من المفتاح.
    فايدته: نختار موديل موجود فعلاً بدل ما نخمّن اسم ونشوف 404.
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                headers={"x-goog-api-key": settings.gemini_api_key},
            )
    except httpx.RequestError as error:
        raise HTTPException(503, f"Could not reach the AI service ({type(error).__name__}).")

    if response.status_code != 200:
        raise HTTPException(502, f"Gemini said {response.status_code}: {response.text[:200]}")

    names = [
        m.get("name", "").replace("models/", "")
        for m in response.json().get("models", [])
    ]
    return {
        "using": settings.gemini_model,
        "fallback": settings.gemini_fallback_model or None,
        "available": sorted(n for n in names if n),
    }



# ===========================================================================
# حماية الأدمن
# ===========================================================================

def admin_list() -> list[str]:
    return [e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()]


async def require_admin(authorization: str | None = Header(default=None)) -> str:
    """
    Dependency بتتحط على كل endpoint بيغيّر حاجة.

    FastAPI بينفّذها قبل الـ endpoint نفسه، ولو رفعت خطأ، الـ endpoint
    عمره ما يشتغل. ده أنضف من إننا نكتب نفس الفحص في أول كل دالة
    وننسى واحدة.

    التحقق بيحصل عند Supabase مش عندنا — هو اللي عنده مفتاح التوقيع.
    """
    allowed = admin_list()

    if not allowed:
        # على الجهاز: مفتوح، عشان تجرّب من غير تعقيد.
        # منشور: مقفول. "نسيت تضبط الحماية" مش سبب كافي إن أي حد
        # على الإنترنت يقدر يمسح جداولك. الافتراضي الآمن هو الرفض.
        if ON_VERCEL:
            raise HTTPException(503, "Admin is disabled: ADMIN_EMAILS is not set.")
        return "dev"

    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    if not token:
        raise HTTPException(401, "لازم تسجّل دخول.")

    user = await asyncio.to_thread(store.whoami, token)
    if not user:
        raise HTTPException(401, "الجلسة انتهت — سجّل دخول تاني.")

    email = (user.get("email") or "").lower()
    if email not in allowed:
        # 403 مش 401: إحنا عارفينك، بس مش مسموح لك.
        raise HTTPException(403, "الحساب ده مش أدمن.")

    return email


# ===========================================================================
# الأدمن — الإعدادات
# ===========================================================================

@app.get("/admin/settings")
def admin_settings():
    try:
        return store.get_settings()
    except store.StoreError as error:
        raise HTTPException(502, str(error))


@app.put("/admin/settings")
def admin_set_mode(req: ModeRequest, who: str = Depends(require_admin)):
    try:
        return store.set_mode(req.mode)
    except store.StoreError as error:
        raise HTTPException(502, str(error))


# ===========================================================================
# الأدمن — التحديث
# ===========================================================================

# حالة المهمة، في الذاكرة. صفحة الأدمن بتسأل عليها كل شوية.
#
# ليه في الذاكرة ومش في الداتابيز؟ لأنها بتموت مع السيرفر وده صح —
# مهمة اتقطعت مش مهمة شغّالة. لو كان عندنا أكتر من سيرفر كان لازم
# نحطها في مكان مشترك (Redis أو جدول)، بس إحنا سيرفر واحد.
JOB: dict = {
    "running": False,
    "stage": "idle",
    "done": 0,
    "total": 0,
    "products": 0,
    "saved": 0,
    "message": "لسه ما اتحدّثش",
    "started_at": None,
    "finished_at": None,
    "errors": [],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _run_refresh() -> None:
    """
    الزحف + الحفظ. بيشتغل في الخلفية، والدالة دي مش بترفع استثناءات
    لبرّا — لو وقعت، بتكتب السبب في JOB وتسيب الحالة نضيفة.
    مهمة خلفية بترفع استثناء مش حد هيشوفه.
    """
    JOB.update(running=True, stage="starting", done=0, total=0, products=0,
               saved=0, errors=[], started_at=_now(), finished_at=None,
               message="بيبدأ…")

    def progress(**kw):
        JOB.update(**kw)

    async def save(batch):
        # store بيستعمل httpx.Client العادي (مش async)، فبنشغّله في
        # thread لوحده عشان ما يوقفش الـ event loop وباقي الطلبات
        # تفضل تردّ وإحنا بنحفظ.
        await asyncio.to_thread(store.upsert_prices, batch)

    try:
        result = await crawler.crawl(progress=progress, save=save)

        JOB.update(
            stage="done", saved=result["saved"], products=result["products"],
            errors=result["errors"], finished_at=_now(),
            message=f"خلص — {result['saved']} منتج محفوظ"
            + (f"، {len(result['errors'])} قسم فشل" if result["errors"] else ""),
        )
    except Exception as error:
        # الأقسام اللي اتحفظت قبل الوقعة بتفضل محفوظة. ده بالظبط
        # اللي كسبناه من الحفظ قسم قسم.
        JOB.update(stage="error", finished_at=_now(),
                   message=f"وقع بعد {JOB['saved']} منتج: "
                           f"{type(error).__name__}: {error}"[:300])
    finally:
        # في finally عشان تتنفّذ سواء نجح أو فشل. من غيرها، فشل واحد
        # يخلّي running=True للأبد وزر التحديث يقفل خلاص.
        JOB["running"] = False


@app.post("/admin/refresh")
async def admin_refresh(background: BackgroundTasks,
                        who: str = Depends(require_admin)):
    """
    بيبدأ التحديث ويرجّع فوراً. مش بيستنى الزحف يخلص —
    الزحف بياخد دقايق (30 ثانية × عدد الأقسام) وأي متصفح هيقطع الاتصال.
    """
    if ON_VERCEL:
        # الزحف ٣٦ دقيقة. أقصى مدة لدالة على Vercel ٣٠٠ ثانية.
        # مش تحسين ممكن — ده سقف المنصة، والحل إن الزحف يفضل
        # محلي: شغّل tools/refresh.py من جهازك، والنتيجة بتروح
        # Supabase، والموقع المنشور بيقراها من هناك.
        raise HTTPException(501,
            "Crawling takes ~36 minutes and a serverless function stops at 300s. "
            "Run it locally instead: python tools/refresh.py")

    if JOB["running"]:
        # 409 Conflict = الطلب سليم بس الحالة الحالية مش سامحة
        raise HTTPException(409, "التحديث شغّال بالفعل.")

    if not (settings.supabase_url and settings.supabase_service_key):
        raise HTTPException(400, "Supabase مش مضبوط — حطّ المفاتيح في .env")

    background.add_task(_run_refresh)
    return {"started": True}


@app.get("/admin/refresh/status")
def admin_refresh_status():
    return JOB


@app.delete("/admin/ingredients")
def admin_clear_ingredients(who: str = Depends(require_admin)):
    """
    بيمسح الربط المحفوظ كله. استعمله لما تغيّر الـ prompt —
    النتايج القديمة اتبنت على تعليمات قديمة.
    """
    try:
        return {"cleared": store.clear_ingredients()}
    except store.StoreError as error:
        raise HTTPException(502, str(error))


@app.get("/admin/prices")
def admin_prices(q: str = "", limit: int = 100):
    try:
        return {
            "summary": store.count_prices(),
            "rows": store.search_prices(q, min(limit, 500)),
        }
    except store.StoreError as error:
        raise HTTPException(502, str(error))


# ===========================================================================
# البحث المؤرّض (Grounded search) — طريقة الـ AI
# ===========================================================================

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


async def search_prices(ingredient: str, qty, unit, area: str) -> dict:
    amount = " ".join(str(x) for x in [qty, unit] if x)
    prompt = (
        f"What does {ingredient} cost in supermarkets in {area} in right now? "
        + (f"Quantity of interest {amount}. " if amount else "")
        + "Give several specific prices you can find, each with the shop name. "
        + "Only report prices you actually found published somewhere. "
        + "If you cannot find any, say so plainly instead of estimating. "
    )

    try:                                                    # نحاول نبعت الطلب
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                GEMINI_URL,
                headers={
                    "x-goog-api-key": settings.gemini_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.gemini_model,
                    "input": prompt,
                    "tools": [{"type": "google_search"}],
                },
            )
    except httpx.RequestError as error:                      # الطلب ما وصلش أصلاً
        # RequestError هو الأب لكل أخطاء الشبكة في httpx:
        # ConnectError, ConnectTimeout, ReadTimeout — واحد يمسكهم كلهم
        raise HTTPException(503, f"Could not reach the AI service ({type(error).__name__}).")

    if response.status_code == 429:                          # وصل، بس الحصة خلصت
        raise HTTPException(429,
            "Out of AI quota. Grounded search is not available on the Gemini free tier — "
            "switch the admin page to site mode, or enable billing.")

    if response.status_code != 200:                          # وصل، ورجع خطأ تاني
        raise HTTPException(502, f"Gemini said {response.status_code}: {response.text[:300]}")

    return response.json()


@app.post("/search-debug")
async def search_debug(req: PriceRequest):
    raw = await search_prices(req.ingredient, req.qty, req.unit, req.area)

    text = ""        # هنجمع فيه نص الرد
    sources = []     # وهنا اللينكات

    for step in raw.get("steps", []):
        if step.get("type") != "model_output":
            continue
        for part in step.get("content", []):
            text += part.get("text", "")
            for note in part.get("annotations") or []:
                citation = note.get("url_citation") or {}
                if citation.get("url"):
                    sources.append(citation["url"])

    return {"text": text, "sources": sources}


# ===========================================================================
# السعر — بيتبع الطريقة اللي الأدمن اختارها
# ===========================================================================

async def _match_products(ingredient: str) -> tuple[list[str], bool]:
    """
    بيرجّع (الباركودات بتاعة المكوّن ده, هل النتيجة مؤقتة).

    أول مرة: نداءين لـ Gemini، وبنحفظ النتيجة.
    كل مرة بعد كده: قراءة واحدة من الداتابيز وخلاص.
    """
    saved = store.get_ingredient(ingredient)
    if saved:
        return list(saved.get("skus") or []), False

    # 1) الكلمات التركية اللي المنتج ممكن يتكتب بيها
    terms, model_a = await matcher.turkish_terms(ingredient)

    # 2) الكود بيضيّق القايمة — مش الموديل. فلترة مش حكم.
    candidates = store.search_by_terms(terms)

    # 3) الموديل بيحكم على الأسماء الحقيقية اللي عندنا
    skus, model_b = await matcher.pick_matches(ingredient, candidates)

    # ------------------------------------------------------------------
    # بنحفظ لو الموديل القوي هو اللي رد على الخطوتين.
    #
    # لو الموديل البديل (الأضعف) اشتغل، النتيجة دي مش بتتخزّن. ليه؟
    # لأن الحفظ هنا دايم — محدش هيراجعه بعد كده، وكل اليوزرز هياخدوا
    # نفس الإجابة للأبد. حكم ضعيف يتخزّن مرة = غلط يعيش سنين.
    #
    # التكلفة إن الطلب الجاي هيدفع نداءين تاني. مقبولة — أحسن من
    # إننا نسجّل "شيبسي بطعم الفراخ" على إنه فراخ.
    # ------------------------------------------------------------------
    strong = settings.gemini_model
    trusted = model_a == strong and model_b == strong

    if trusted:
        # بنحفظ حتى لو القايمة فاضية: "دوّرنا وملقيناش" نتيجة برضه.
        store.save_ingredient(ingredient, terms, skus)

    return skus, not trusted


@app.post("/price", response_model=PriceRange)
async def price(req: PriceRequest) -> PriceRange:
    try:
        mode = store.get_settings()["price_mode"]
    except store.StoreError:
        mode = "site"        # الداتابيز مش راضية ترد؟ نكمّل بالطريقة الأرخص

    if mode == "ai":
        # لسه محتاج خطوة تانية: نداء يحوّل نص البحث المؤرّض لأرقام.
        # ولسه مقفول على الخطة المجانية أصلاً.
        raise HTTPException(501, "AI mode: the extraction step isn't built yet.")

    # --- طريقة الموقع: بنقرا من اللي زحفناه ---
    try:
        skus, provisional = await _match_products(req.ingredient)
        rows = store.prices_by_skus(skus)
    except store.StoreError as error:
        raise HTTPException(502, str(error))

    if not rows:
        raise HTTPException(404,
            f"مفيش منتج في الجدول بيطابق '{req.ingredient}'. "
            "يمكن الموقع مش بيبيعه، أو محتاج تحديث من صفحة الأدمن.")

    # القاعدة نفسها في sizes.summarise — مختبرة لوحدها من غير سيرفر.
    summary = sizes.summarise(rows, req.qty, req.unit)

    found = [
        Observation(
            price=i["price"],
            # اسم المنتج أنفع لليوزر من اسم الموقع — بيوريه إيه بالظبط
            # اللي اتسعّر، فلو الربط غلط يبان فوراً.
            shop=i["name"],
            source=i["url"],
            size=i["size"],
            unit_price=i["unit_price"],
            total=i["total"],
        )
        for i in summary["items"]
    ]

    return PriceRange(
        ingredient=req.ingredient,
        low=summary["low"],
        high=summary["high"],
        observations=found,
        basis=summary["basis"],
        ignored=summary["ignored"],
        provisional=provisional,
    )


# ===========================================================================
# المسار على Vercel
#
# الراوتات فوق معمولة على "/config" و"/price". على جهازك uvicorn بيسمع
# على 127.0.0.1:8010 فالمسار يوصل زي ما هو. لكن Vercel بيسلّم الدالة
# المسار الأصلي للطلب — يعني "/api/config" — والـ rewrite بيختار الدالة
# بس، مش بيقصّ الـ "/api". فأول نشرة ردّت 404 من FastAPI على كل حاجة.
#
# الحل: نلفّ التطبيق في تطبيق خارجي، ونركّب نفس التطبيق مرتين. Mount
# في Starlette بيقصّ البادئة قبل ما يسلّم، فـ "/api/config" بيوصل جوه
# كـ "/config" — ونفس الراوتات تشتغل على الاتنين من غير تكرار كود.
# ===========================================================================

_routes = app

app = FastAPI(title="Cheapest Basket API")
app.mount("/api", _routes)   # منشور
app.mount("/", _routes)      # على جهازك
