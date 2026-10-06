"""
crawler.py — يجيب الأسعار من kibrissanalmarket.com

الـ selectors اللي تحت مش تخمين. فتحنا الموقع وفحصنا الـ DOM بنفسنا:

    div.product-inner                          ← الكرتونة بتاعة كل منتج
      div.skucuk                               ← الباركود
      h2.woocommerce-loop-product__title       ← الاسم
      span.price                               ← السعر، شكله "272.00 ₺"
      a.woocommerce-loop-product__link[href]   ← لينك المنتج

    a[href*="/urun-grubu/"]                    ← لينكات الأقسام
"""

import asyncio
import re
import httpx
from bs4 import BeautifulSoup

from settings import settings
from store import _normalise      # نفس دالة التبسيط بالظبط — لازم تكون واحدة


BASE = "https://www.kibrissanalmarket.com"
SOURCE = "kibrissanalmarket.com"
# الاسم اللي اليوزر يشوفه في التطبيق كمحل
SOURCE_LABEL = "Kıbrıs Sanal Market"

# نقول مين إحنا. موقع محترم من حقه يعرف مين بيزحف عليه.
HEADERS = {"User-Agent": "CheapestBasket/1.0 (personal price comparison project)"}

# أقسام مش أكل — ما تزحفهاش، بتضيّع وقت وبتوسّخ الجدول.
SKIP = (
    "kisisel-bakim", "ev-yasam-bakim", "evcil-hayvan", "kirtasiye",
    "cinsel-saglik", "bebek", "alkol-ve-sigara",
)


# ===========================================================================
# 1) استخراج البيانات من HTML
# ===========================================================================

def parse_price(text: str) -> float | None:
    """
    "272.00 ₺"    -> 272.0
    "1.234,56 ₺"  -> 1234.56      (الشكل التركي: نقطة للألوف، فاصلة للكسور)
    "29,99 ₺"     -> 29.99

    ليه كل ده؟ لأن الموقع بيرندر بالإعدادات التركية، والشكل بيتغيّر
    لما الرقم يعدّي الألف. لو عاملنا النقطة كعلامة كسور دايماً،
    1.234,56 هتبقى 1.23 — وهنسجّل سعر غلط ومش هنعرف.
    """
    if not text:
        return None

    # شيل كل حاجة مش رقم ولا نقطة ولا فاصلة (العملة، المسافات، "KDV" ...)
    raw = re.sub(r"[^\d.,]", "", text)
    if not raw:
        return None

    if "," in raw and "." in raw:
        # الاتنين موجودين: الأخير هو علامة الكسور
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")    # تركي
        else:
            raw = raw.replace(",", "")                       # إنجليزي
    elif "," in raw:
        raw = raw.replace(",", ".")

    try:
        value = float(raw)
    except ValueError:
        return None

    # سعر بصفر أو سالب مش سعر. أرجعنا None والصف ده يتجاهل.
    return value if value > 0 else None


def parse_products(html: str, category: str = "") -> list[dict]:
    """بياخد صفحة قسم ويرجّع قايمة منتجات جاهزة للتخزين."""
    soup = BeautifulSoup(html, "html.parser")
    rows = []

    for box in soup.select("div.product-inner"):
        title = box.select_one("h2.woocommerce-loop-product__title")
        price_el = box.select_one("span.price")
        if not title or not price_el:
            continue                                   # كرتونة ناقصة، عدّيها

        name = title.get_text(strip=True)
        price = parse_price(price_el.get_text(" ", strip=True))
        if not name or price is None:
            continue                                   # مش هنخزّن سعر ما فهمناهوش

        sku_el = box.select_one("div.skucuk")
        link = box.select_one("a.woocommerce-loop-product__link")

        rows.append({
            "source": SOURCE,
            "sku": sku_el.get_text(strip=True) if sku_el else None,
            "name": name,
            "name_norm": _normalise(name),
            "price": price,
            "currency": "TRY",
            "category": category,
            "url": link.get("href") if link else None,
        })

    return rows


def parse_categories(html: str) -> list[str]:
    """
    بياخد الصفحة الرئيسية ويرجّع لينكات الأقسام الفرعية.

    ليه الفرعية بس؟ القسم الرئيسي "/urun-grubu/meyve-ve-sebze/" بيعرض
    جزء من منتجاته، أما الفرعي "/urun-grubu/meyve-ve-sebze/sebze/"
    بيعرضهم كلهم. الفرعية = تغطية أحسن بنفس عدد الطلبات.
    """
    soup = BeautifulSoup(html, "html.parser")
    found = set()

    for a in soup.select('a[href*="/urun-grubu/"]'):
        href = (a.get("href") or "").split("?")[0].rstrip("/")
        if not href:
            continue
        path = href.replace(BASE, "").replace("https://kibrissanalmarket.com", "")
        parts = [p for p in path.split("/") if p]

        # ['urun-grubu', 'meyve-ve-sebze', 'sebze'] = قسم فرعي
        if len(parts) != 3 or parts[0] != "urun-grubu":
            continue
        if any(skip in path for skip in SKIP):
            continue

        found.add(path + "/")

    return sorted(found)


# ===========================================================================
# 2) الزحف نفسه
# ===========================================================================

async def fetch(client: httpx.AsyncClient, path: str) -> str:
    response = await client.get(BASE + path, headers=HEADERS)
    response.raise_for_status()      # 404 أو 500 يرفع استثناء بدل ما يمرّ بهدوء
    return response.text


async def crawl(progress=None, save=None) -> dict:
    """
    الزحف كامل.

    progress: دالة بننادي عليها بعد كل قسم عشان الواجهة تعرف إحنا فين.
    save:     دالة بتحفظ منتجات قسم واحد. بننادي عليها بعد كل قسم.

    ليه بنحفظ قسم قسم مش مرة واحدة في الآخر؟

      مرة واحدة:  الزحف 36 دقيقة. لو وقع في القسم 70، الـ 35 دقيقة
                  اللي فاتت كلها تضيع، والجدول يفضل فاضي طول الوقت.
      قسم قسم:    أي انقطاع بيخسّرك قسم واحد، والنتايج بتبان في
                  الجدول أول بأول.

    التكلفة: 71 طلب لـ Supabase بدل 3. مقبولة — دي بتحصل مرة في
    اليوم، مش في كل طلب يوزر.

    بيرجّع: {"categories": n, "products": n, "saved": n, "errors": [...]}
    """
    def report(**kw):
        if progress:
            progress(**kw)

    errors: list[str] = []
    seen: set[str] = set()             # أسماء شفناها قبل كده، عشان العد يبقى صح
    saved = 0

    async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
        # --- الصفحة الرئيسية: منها نعرف الأقسام ---
        report(stage="categories", done=0, total=0, message="بجيب قايمة الأقسام…")
        home = await fetch(client, "/")
        categories = parse_categories(home)

        if settings.crawl_max_categories:
            categories = categories[: settings.crawl_max_categories]

        total = len(categories)
        report(stage="crawling", done=0, total=total,
               message=f"لقيت {total} قسم. ببدأ…")

        # --- قسم قسم، بفاصل زمني ---
        for index, path in enumerate(categories, start=1):
            # الانتظار قبل الطلب، مش بعده — كده أول طلب بعد الصفحة الرئيسية
            # بيستنى كمان. الموقع طلب 30 ثانية بين الطلبات، مش بعد آخر واحد.
            await asyncio.sleep(settings.crawl_delay_seconds)

            try:
                html = await fetch(client, path)
                found = parse_products(html, category=path.strip("/").split("/")[-1])

                # نفس المنتج ممكن يتكرر جوه نفس الصفحة. لازم نشيل
                # التكرار قبل الحفظ، لأن Supabase بيرفض دفعة فيها
                # نفس المفتاح مرتين.
                batch = list({row["name"]: row for row in found}.values())

                if save and batch:
                    # الحفظ بيستنى لحد ما يخلص قبل ما نكمّل. أبطأ
                    # شوية، بس بيضمن إن اللي الواجهة بتعرضه حقيقي.
                    await save(batch)
                    saved += len(batch)

                seen.update(row["name"] for row in batch)

            except Exception as error:
                errors.append(f"{path}: {type(error).__name__}")

            report(stage="crawling", done=index, total=total,
                   products=len(seen), saved=saved,
                   message=f"{index}/{total} — {len(seen)} منتج لحد الآن")

    return {
        "categories": total,
        "products": len(seen),
        "saved": saved,
        "errors": errors,
    }
