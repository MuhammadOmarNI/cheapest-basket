"""
store.py — كل كلام مع Supabase في مكان واحد.

ليه ملف لوحده؟
لأن باقي المشروع المفروض ما يعرفش إن فيه Supabase أصلاً. بينادي على
get_settings() و upsert_prices() وخلاص. لو غيّرنا الداتابيز بعدين،
نعدّل الملف ده بس والباقي ما يتغيّرش. ده اسمه فصل الاهتمامات.
"""

import httpx
from .settings import settings          # نفس ملف الإعدادات اللي بيقرا .env


class StoreError(Exception):
    """غلط جاي من الداتابيز. main.py بيحوّله لـ HTTP status مناسب."""


# Supabase بيقدّم الجداول كـ REST API. الطريق ثابت:
#   <project-url>/rest/v1/<table-name>
def _table_url(table: str) -> str:
    # الفحص ده مش زيادة. من غيره، لو supabase_url فاضي بنبني الرابط
    # "/rest/v1/admin_settings" وhttpx بيرمي UnsupportedProtocol —
    # رسالة بتقول "الرابط ناقص http" وما بتقولش السبب الحقيقي.
    # امسك الغلط عند مصدره، وقول للي بيقراه يعمل إيه.
    if not settings.supabase_url:
        raise StoreError("supabase_url فاضي — ضيفه في api/.env")
    if not settings.supabase_url.startswith(("http://", "https://")):
        raise StoreError(
            f"supabase_url لازم يبدأ بـ https:// — القيمة الحالية: {settings.supabase_url[:40]}")
    if not settings.supabase_service_key:
        raise StoreError("supabase_service_key فاضي — ضيفه في api/.env")

    return f"{settings.supabase_url.rstrip('/')}/rest/v1/{table}"


def _headers(extra: dict | None = None) -> dict:
    """
    كل طلب لـ Supabase محتاج المفتاح مرتين: مرة في apikey ومرة في Authorization.
    ده شكل الـ API بتاعهم، مش تكرار بالغلط.

    إحنا بنستعمل service_role هنا — المفتاح السري اللي بيتخطى RLS.
    علشان كده الملف ده عمره ما يشتغل في المتصفح، والمفتاح عايش في .env بس.
    """
    head = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
    }
    if extra:
        head.update(extra)
    return head


def _check(response: httpx.Response) -> None:
    # 2xx = تمام. أي حاجة تانية نوقف عندها بدل ما نكمّل على بيانات ناقصة.
    if response.status_code >= 300:
        raise StoreError(f"Supabase {response.status_code}: {response.text[:300]}")


# ===========================================================================
# إعدادات الأدمن
# ===========================================================================

def get_settings() -> dict:
    """بيرجّع الصف الوحيد من admin_settings."""
    with httpx.Client(timeout=20) as client:
        response = client.get(
            _table_url("admin_settings"),
            headers=_headers(),
            # select=* يعني هات كل الأعمدة، و id=eq.1 يعني الصف اللي id بتاعه = 1
            params={"select": "*", "id": "eq.1"},
        )
    _check(response)
    rows = response.json()
    if not rows:
        # الجدول فاضي = ملف الـ SQL ما اتشغّلش
        raise StoreError("admin_settings is empty — run supabase-prices.sql first.")
    return rows[0]


def set_mode(mode: str) -> dict:
    """
    بيغيّر طريقة جمع الأسعار.

    لاحظ إننا مش بنتحقق هنا إن mode قيمته صح — الـ CHECK constraint
    في الداتابيز هو اللي بيرفض. مكان واحد للقاعدة أحسن من اتنين
    يمكن يختلفوا.
    """
    with httpx.Client(timeout=20) as client:
        response = client.patch(
            _table_url("admin_settings"),
            headers=_headers({"Prefer": "return=representation"}),
            params={"id": "eq.1"},
            json={"price_mode": mode, "updated_at": "now()"},
        )
    _check(response)
    return response.json()[0]


# ===========================================================================
# الأسعار
# ===========================================================================

# Supabase بيرفض الطلبات الضخمة. بنقسّم على دفعات.
CHUNK = 500


def upsert_prices(rows: list[dict]) -> int:
    """
    بيحفظ الأسعار. الموجود يتحدّث، الجديد يتضاف.

    الحتة المهمة: Prefer: resolution=merge-duplicates
    دي اللي بتحوّل الـ INSERT لـ UPSERT. من غيرها، تاني زحف هيفشل
    على أول منتج مكرر بسبب الـ unique(source, name).
    """
    if not rows:
        return 0

    saved = 0
    with httpx.Client(timeout=60) as client:
        # بنمشي على القايمة 500 في المرة
        for start in range(0, len(rows), CHUNK):
            batch = rows[start:start + CHUNK]
            response = client.post(
                _table_url("product_prices"),
                headers=_headers({
                    "Prefer": "resolution=merge-duplicates,return=minimal",
                }),
                # on_conflict بيقول لـ Supabase: الأعمدة دي هي اللي تحدد التكرار
                params={"on_conflict": "source,name"},
                json=batch,
            )
            _check(response)
            saved += len(batch)
    return saved


def search_prices(query: str = "", limit: int = 100) -> list[dict]:
    """بيدوّر في الأسعار المحفوظة. query فاضية = هات أول limit صف."""
    params = {
        "select": "sku,name,price,currency,category,url,fetched_at,source",
        "order": "name.asc",
        "limit": str(limit),
    }
    if query:
        # ilike = بحث غير حسّاس لحالة الحروف. * هي wildcard في PostgREST
        params["name_norm"] = f"ilike.*{_normalise(query)}*"

    with httpx.Client(timeout=30) as client:
        response = client.get(_table_url("product_prices"), headers=_headers(), params=params)
    _check(response)
    return response.json()


def count_prices() -> dict:
    """
    بيرجّع عدد الأسعار وآخر مرة اتحدّثت.

    ليه طلبين مش واحد؟ لأن العدد بييجي من هيدر Content-Range
    (أرخص من إننا نجيب الصفوف كلها ونعدّها في Python).
    """
    with httpx.Client(timeout=20) as client:
        head = client.get(
            _table_url("product_prices"),
            headers=_headers({"Prefer": "count=exact", "Range": "0-0"}),
            params={"select": "id"},
        )
        _check(head)
        # الهيدر شكله كده: "0-0/1234" — اللي بعد الشرطة المايلة هو العدد
        total = 0
        rng = head.headers.get("content-range", "")
        if "/" in rng and rng.split("/")[-1].isdigit():
            total = int(rng.split("/")[-1])

        newest = client.get(
            _table_url("product_prices"),
            headers=_headers(),
            params={"select": "fetched_at", "order": "fetched_at.desc", "limit": "1"},
        )
        _check(newest)
        rows = newest.json()

    return {"count": total, "last_updated": rows[0]["fetched_at"] if rows else None}


def _normalise(text: str) -> str:
    """
    بيبسّط النص للبحث: حروف صغيرة، والحروف التركية تتحول لأقرب حرف إنجليزي.

    ليه؟ عشان اليوزر اللي بيكتب "gogus" يلاقي "GÖĞÜS".
    نفس الدالة بالظبط بتستخدم وقت الزحف ووقت البحث — لازم يكونوا واحد،
    وإلا هنخزّن بشكل وندوّر بشكل تاني ومش هنلاقي حاجة.
    """
    table = str.maketrans("ıİiğĞüÜşŞöÖçÇâÂ", "iiigguussooccaa")
    return text.translate(table).lower().strip()


# ===========================================================================
# ربط المكوّنات بالمنتجات
# ===========================================================================

import re


def get_ingredient(ingredient: str) -> dict | None:
    """بيدوّر على ربط محفوظ للمكوّن ده. None يعني أول مرة نشوفه."""
    with httpx.Client(timeout=20) as client:
        response = client.get(
            _table_url("ingredient_map"),
            headers=_headers(),
            params={"select": "*", "ingredient_norm": f"eq.{_normalise(ingredient)}"},
        )
    _check(response)
    rows = response.json()
    return rows[0] if rows else None


def save_ingredient(ingredient: str, terms: list[str], skus: list[str]) -> None:
    """بيحفظ الربط. upsert عشان لو حبّينا نعيد الحساب بعدين."""
    with httpx.Client(timeout=20) as client:
        response = client.post(
            _table_url("ingredient_map"),
            headers=_headers({"Prefer": "resolution=merge-duplicates,return=minimal"}),
            params={"on_conflict": "ingredient_norm"},
            json=[{
                "ingredient_norm": _normalise(ingredient),
                "original": ingredient,
                "terms": terms,
                "skus": skus,
                "updated_at": "now()",
            }],
        )
    _check(response)


def _safe(term: str) -> str:
    """
    بيسيب الحروف والأرقام بس.

    السبب: فلتر الـ OR في PostgREST بيتفصل بفاصلة، والأقواس ليها معنى.
    كلمة فيها فاصلة أو قوس مش هتدّي غلط — هتكسر الاستعلام كله بهدوء
    وترجّع نتايج غلط. نظّف المدخل قبل ما تبنيه في استعلام.
    """
    return re.sub(r"[^0-9a-z]", "", _normalise(term))


def search_by_terms(terms: list[str], limit: int = 60) -> list[dict]:
    """بيجيب كل منتج اسمه فيه أي كلمة من الكلمات دي."""
    clean = [t for t in (_safe(x) for x in terms) if len(t) >= 3]
    if not clean:
        return []

    # or=(a.ilike.*x*,a.ilike.*y*) يعني "أي واحدة من دول"
    condition = ",".join(f"name_norm.ilike.*{t}*" for t in clean)

    with httpx.Client(timeout=30) as client:
        response = client.get(
            _table_url("product_prices"),
            headers=_headers(),
            params={
                "select": "sku,name,price,currency,category,url,fetched_at,source",
                "or": f"({condition})",
                "order": "name.asc",
                "limit": str(limit),
            },
        )
    _check(response)
    # المنتجات من غير باركود مش هتنفع في الربط (الربط بالـ sku)
    return [r for r in response.json() if r.get("sku")]


def prices_by_skus(skus: list[str]) -> list[dict]:
    """بيجيب الأسعار الحالية للباركودات دي. ده اللي بيشتغل في كل طلب متكرر."""
    if not skus:
        return []

    quoted = ",".join('"' + s.replace('"', "") + '"' for s in skus)

    with httpx.Client(timeout=30) as client:
        response = client.get(
            _table_url("product_prices"),
            headers=_headers(),
            params={
                "select": "sku,name,price,currency,category,url,fetched_at,source",
                "sku": f"in.({quoted})",
                "order": "price.asc",
            },
        )
    _check(response)
    return response.json()


def clear_ingredients() -> int:
    """
    بيمسح كل الربط المحفوظ.

    محتاجينها لما نغيّر الـ prompt: النتايج القديمة اتبنت على تعليمات
    قديمة، وهتفضل موجودة للأبد لو ما مسحناهاش. الكاش لازم يكون ليه
    طريقة تفضية، وإلا بيبقى بيانات ميتة مالكوش عليها سيطرة.
    """
    with httpx.Client(timeout=30) as client:
        response = client.delete(
            _table_url("ingredient_map"),
            headers=_headers({"Prefer": "count=exact"}),
            # PostgREST بيرفض DELETE من غير شرط — حماية من مسح جدول
            # بالغلط. "مش فاضي" بيطابق كل الصفوف بشكل صريح.
            params={"ingredient_norm": "neq."},
        )
    _check(response)
    rng = response.headers.get("content-range", "")
    return int(rng.split("/")[-1]) if rng.split("/")[-1].isdigit() else 0


def whoami(token: str) -> dict | None:
    """
    بيسأل Supabase: الـ token ده بتاع مين؟

    ليه ما نقراش الإيميل من الـ token نفسه؟ لأن أي حد يقدر يكتب
    JWT فيه أي إيميل. التحقق من التوقيع هو اللي بيفرق، وSupabase
    هو اللي عنده المفتاح. بنسأله بدل ما نحاول نتحقق بنفسنا.

    بيرجّع بيانات اليوزر، أو None لو الـ token مش صالح.
    """
    if not token:
        return None

    with httpx.Client(timeout=15) as client:
        response = client.get(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
            headers={
                "apikey": settings.supabase_service_key,
                "Authorization": f"Bearer {token}",
            },
        )

    # 401 = token مزوّر أو منتهي. مش غلط في السيرفر — ده الرد الصح.
    if response.status_code != 200:
        return None
    return response.json()
