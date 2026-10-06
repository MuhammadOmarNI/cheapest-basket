"""
matcher.py — بيوصّل بين اللي اليوزر بيكتبه واللي الموقع كاتبه.

اليوزر بيكتب:  "chicken breast"
الجدول فيه:    "KIRNI PILIC GOGUS FILLET"

مفيش أي بحث نصّي هيوصّل بينهم. دي مسألة معنى، ودي شغلانة الموديل.

خطوتين، وكل واحدة ليها سبب:

  1. كلمات البحث — "chicken breast" بالتركي بتتكتب إزاي في أسماء
     المنتجات؟ الرد: ["gogus", "pilic", "tavuk"]. الكود بيستعملها
     يجيب مرشّحين من الداتابيز.

  2. الاختيار — من المرشّحين دول، أنهي واحد فعلاً "chicken breast"؟
     الموديل بيشوف أسماء حقيقية عندنا ويحكم عليها.

ليه مش نداء واحد نبعتله الـ 1099 منتج ونقوله اختار؟ يشتغل، بس
بيكلّف tokens في كل طلب. الطريقة دي بتضيّق العدد بالكود الأول.

والنتيجتين الاتنين بتتخزّنوا، فالنداءين دول بيحصلوا مرة واحدة
لكل مكوّن في عمر البرنامج كله.
"""

import asyncio
import json
import httpx
from fastapi import HTTPException

from settings import settings
from store import _normalise


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

# أكواد بتقول "غلط مؤقت، جرّب تاني":
#   503 = الموديل زحمة دلوقتي
#   500 = غلط عندهم
#   502/504 = مشكلة في الشبكة بينا وبينهم
RETRYABLE = {500, 502, 503, 504}

# ثواني الانتظار بين المحاولات. بتزيد (backoff) — لو الخدمة زحمة،
# إن كل العملاء يضربوا تاني في نفس اللحظة بيزوّد الزحمة مش أكتر.
RETRY_WAITS = [2, 5]


# ===========================================================================
# النداء الأساسي
# ===========================================================================

async def _ask(prompt: str, schema: dict) -> tuple[dict, str]:
    """
    بيسأل Gemini ويجبره يرد بـ JSON على الشكل اللي إحنا حاططينه.

    response_format هو اللي بيعمل ده. من غيره الموديل بيرد نثر،
    وهنبقى بنفصّل نص بـ regex — وده بيقع أول ما يغيّر صياغته.
    """
    if not settings.gemini_api_key:
        raise HTTPException(400, "gemini_api_key مش موجود في .env")

    # الموديل الأساسي، وبعده البديل لو الأساسي زحمة.
    # الترتيب مقصود: الأدق الأول دايماً. البديل حل أخير مش اختصار.
    models = [settings.gemini_model]
    if settings.gemini_fallback_model:
        models.append(settings.gemini_fallback_model)

    problem = ""
    for model in models:
        try:
            # بنرجّع اسم الموديل مع النتيجة. من غيره، اللي بينادي
            # مش هيعرف إن الرد جه من الموديل الضعيف.
            return await _ask_one(model, prompt, schema, headers_for()), model
        except HTTPException as error:
            # 503 بس هي اللي موديل تاني ممكن ينقذها — معناها "الموديل ده زحمة".
            # 429 حصة الحساب كله، و502 معناها Gemini رفض طلبنا إحنا
            # (schema غلط مثلاً) — الاتنين هيتكرروا بأي موديل.
            if error.status_code != 503:
                raise
            problem = error.detail

    raise HTTPException(503, problem)


def headers_for() -> dict:
    return {
        "x-goog-api-key": settings.gemini_api_key,
        "Content-Type": "application/json",
    }


async def _ask_one(model: str, prompt: str, schema: dict, headers: dict) -> dict:
    """محاولات موديل واحد. بيرفع HTTPException لو كلهم فشلوا."""
    body = {
        "model": model,
        "input": prompt,
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": schema,
        },
        # مفيش "tools" هنا. ده نداء عادي من غير بحث مؤرّض،
        # وعلشان كده شغّال على الخطة المجانية.
    }

    last = ""

    # range(len(RETRY_WAITS) + 1) = 3 محاولات، بينهم نومتين
    for attempt in range(len(RETRY_WAITS) + 1):
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.post(GEMINI_URL, headers=headers, json=body)
        except httpx.RequestError as error:
            last = f"Could not reach the AI service ({type(error).__name__})."
            status = 503                      # الشبكة برضه غلط مؤقت — تستاهل إعادة
        else:
            status = response.status_code
            if status == 200:
                return _extract_json(response.json())
            if status == 429:
                # الحصة خلصت. الإعادة مش هتساعد — هتستهلك أكتر بس.
                raise HTTPException(429, "Out of AI quota — try again in a few minutes.")
            last = f"Gemini said {status}: {response.text[:200]}"

        # 503 = الموديل زحمة، 500 = غلط عندهم. الاتنين بيعدّوا لوحدهم.
        # أي حاجة تانية (400، 404) غلط في طلبنا إحنا — الإعادة مش هتغيّر حاجة.
        if status not in RETRYABLE or attempt == len(RETRY_WAITS):
            break

        await asyncio.sleep(RETRY_WAITS[attempt])

    raise HTTPException(502 if status not in RETRYABLE else 503, last)


def _extract_json(raw: dict) -> dict:
    """
    بيطلّع الـ JSON من رد الـ API.

    بنجرّب أكتر من مكان لأن الـ API بيسمّي الحقل بأكتر من شكل
    (outputText / output_text)، وبنرجع للمشي على steps كآخر حل.
    ده مش خوف زيادة — ده الفرق بين إن تحديث في الـ API يوقّف
    البرنامج أو ما يحصلش حاجة.
    """
    text = raw.get("outputText") or raw.get("output_text") or ""

    if not text:
        for step in raw.get("steps", []):
            if step.get("type") != "model_output":
                continue
            for part in step.get("content", []):
                text += part.get("text", "")

    if not text:
        raise HTTPException(502, f"مفيش نص في رد Gemini: {json.dumps(raw)[:200]}")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise HTTPException(502, f"رد Gemini مش JSON صالح: {text[:200]}")


# ===========================================================================
# ١) كلمات البحث التركية
# ===========================================================================

TERMS_SCHEMA = {
    "type": "object",
    "properties": {
        "terms": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["terms"],
}


async def turkish_terms(ingredient: str) -> tuple[list[str], str]:
    prompt = (
        f"A shopper is looking for '{ingredient}' in a Turkish supermarket in North Cyprus.\n\n"
        "Give 2 to 5 SINGLE WORDS that would appear inside the product names for it, "
        "as Turkish supermarkets actually write them.\n\n"
        "Rules:\n"
        "- One word per entry. Never a phrase.\n"
        "- Most distinctive word first, most general last.\n"
        "- Plain ASCII: write 'gogus' not 'göğüs', 'sut' not 'süt'.\n"
        "- Only words that name the food itself. No brands, no packaging words.\n\n"
        "Example — for 'chicken breast': [\"gogus\", \"pilic\", \"tavuk\"]\n"
        "Example — for 'milk': [\"sut\"]"
    )

    result, model = await _ask(prompt, TERMS_SCHEMA)

    # نبسّط ونشيل الفاضي والمكرر، ونسيب الترتيب زي ما هو
    # (الأول هو الأدق، والكود بيعتمد على ده بعدين).
    clean: list[str] = []
    for term in result.get("terms", []):
        word = _normalise(str(term)).strip()
        # كلمة واحدة بس. لو الموديل رجّع جملة، ناخد أول كلمة.
        word = word.split()[0] if word.split() else ""
        # حرفين على الأقل، وإلا "a" هتطابق كل حاجة في الجدول
        if len(word) >= 3 and word not in clean:
            clean.append(word)

    if not clean:
        raise HTTPException(502, f"Gemini ما رجّعش كلمات بحث لـ '{ingredient}'")

    return clean[:5], model


# ===========================================================================
# ٢) اختيار المنتجات الصح من المرشّحين
# ===========================================================================

MATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "skus": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["skus"],
}


async def pick_matches(ingredient: str, candidates: list[dict]) -> tuple[list[str], str]:
    """
    candidates = [{"sku": "...", "name": "..."}, ...]
    بيرجّع الـ skus اللي فعلاً المكوّن المطلوب.
    """
    if not candidates:
        return [], settings.gemini_model

    listing = "\n".join(f'{c["sku"]}\t{c["name"]}' for c in candidates)

    prompt = (
        f"Below are products from a North Cyprus supermarket. "
        f"Which of them ARE '{ingredient}'?\n\n"
        "Return the SKU of every product that is that ingredient itself.\n\n"
        "Rules:\n"
        "- Include plain, raw, and frozen forms of the ingredient.\n"
        "- Exclude prepared meals, snacks and flavoured products that merely "
        "contain it (chicken-flavoured crisps are not chicken).\n"
        "- Exclude a different cut or a different part of the animal or plant.\n"
        "- Exclude infant and follow-on formula ('devam sutu', 'bebek', "
        "'cocuk devam'), and any product for a specific medical or age group. "
        "Those are a different product, not the plain ingredient.\n"
        "- Exclude concentrated, condensed, powdered and evaporated versions "
        "unless the ingredient itself names them.\n"
        "- Only SKUs from the list. Never invent one.\n"
        "- If none of them is the ingredient, return an empty list.\n\n"
        f"SKU\tNAME\n{listing}"
    )

    result, model = await _ask(prompt, MATCH_SCHEMA)

    # ------------------------------------------------------------------
    # الحاجز (guardrail)
    #
    # موديل اتطلب منه يختار من قايمة يقدر برضه يخترع حاجة مش فيها.
    # بنرمي أي sku مش في اللي بعتناه. من غير السطرين دول، منتج
    # متخيّل ممكن يبقى "سعر" في التطبيق من غير ما حد يلاحظ.
    # ------------------------------------------------------------------
    allowed = {c["sku"] for c in candidates if c.get("sku")}
    picked = [str(s) for s in result.get("skus", []) if str(s) in allowed]

    return picked, model
