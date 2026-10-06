"""
sizes.py — بيقرا الحجم من اسم المنتج.

المشكلة اللي بيحلها:

    KOOP KÜÇÜK SUT 200ML        17.99 ₺
    KOOP 1L SUT                 75.00 ₺
    ALASKA 1KG KONSANTRE SUT   478.99 ₺

"من 17.99 لـ 478.99" رقم ملوش أي معنى — دول أحجام مختلفة.
المقارنة الوحيدة العادلة هي سعر اللتر أو الكيلو.

الشغل ده كله بالكود، مفيش AI. استخراج رقم من نص مسألة قواعد،
والقواعد بتتنفّذ صح ١٠٠٪ من المرات ومجاناً.
"""

import re


# ---------------------------------------------------------------------------
# الوحدات اللي التطبيق بيفهمها.
#
# دي المصدر الوحيد: الـ select box في الواجهة بيتبني منها عن طريق
# endpoint، والباكند بيتحقق منها. لو كانت مكتوبة في المكانين، يوم
# ما نضيف وحدة هننسى واحد منهم — وده بيفضل ساكت لحد ما يوزر يشتكي.
# ---------------------------------------------------------------------------
UNITS = [
    {"value": "g",     "label": "g",     "base": "KG", "factor": 0.001},
    {"value": "kg",    "label": "kg",    "base": "KG", "factor": 1.0},
    {"value": "ml",    "label": "ml",    "base": "L",  "factor": 0.001},
    {"value": "l",     "label": "L",     "base": "L",  "factor": 1.0},
    {"value": "piece", "label": "piece", "base": None, "factor": 1.0},
]

UNIT_VALUES = [u["value"] for u in UNITS]


def find_unit(value: str | None) -> dict | None:
    """بيدوّر على الوحدة. بيقبل "L" و"l" و"Litre"? لأ — القيمة بالظبط بس."""
    if not value:
        return None
    wanted = str(value).strip().lower()
    for unit in UNITS:
        if unit["value"] == wanted:
            return unit
    return None


def to_base(qty: float, unit: str) -> tuple[float, str | None] | None:
    """
    (2, "l")    -> (2.0, "L")
    (500, "ml") -> (0.5, "L")
    (3, "piece")-> (3.0, None)      قطع، مش وزن ولا حجم

    بيحوّل طلب اليوزر لنفس المقياس اللي بنخزّن بيه، عشان الضرب
    يبقى بين رقمين من نفس النوع.
    """
    found = find_unit(unit)
    if not found or qty is None or qty <= 0:
        return None
    return qty * found["factor"], found["base"]


# لواحق الوحدات زي ما الموقع بيكتبها جوه اسم المنتج.
# اسم مختلف عن UNITS فوق عن قصد: دي بتقرا نص، وديك بتوصف اختيارات اليوزر.
NAME_UNITS = {
    "KG": ("KG", 1.0),
    "GR": ("KG", 0.001),
    "G":  ("KG", 0.001),
    "LT": ("L", 1.0),
    "L":  ("L", 1.0),
    "ML": ("L", 0.001),
    "CL": ("L", 0.01),
}

PATTERN = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(KG|GR|G|LT|L|ML|CL)\b",
    re.IGNORECASE,
)

# منتجات بتتباع بالكيلو من غير رقم: "... BAGET BUT (kg)"
BARE_KG = re.compile(r"\(\s*kg\s*\)", re.IGNORECASE)


def parse_size(name: str) -> tuple[float, str] | None:
    """
    "KOOP 1L SUT"        -> (1.0, "L")
    "... 200ML"          -> (0.2, "L")
    "... 55GR"           -> (0.055, "KG")
    "... BAGET BUT (kg)" -> (1.0, "KG")
    "KIRNI PILIC FILLET" -> None

    بيرجّع الكمية بالوحدة الأساسية (لتر أو كيلو)، عشان كل المقارنات
    تبقى على نفس المقياس.
    """
    if not name:
        return None

    matches = PATTERN.findall(name)
    if matches:
        # لو الاسم فيه أكتر من رقم ("2-2,5 KG")، بناخد الأخير —
        # ده اللي بيكون ملزوق بالوحدة عادةً.
        amount_text, unit_text = matches[-1]
        base, factor = NAME_UNITS[unit_text.upper()]
        try:
            amount = float(amount_text.replace(",", "."))
        except ValueError:
            return None
        if amount <= 0:
            return None
        return amount * factor, base

    if BARE_KG.search(name):
        return 1.0, "KG"

    return None


def unit_price(price: float, name: str) -> tuple[float, str, str] | None:
    """
    بيرجّع (سعر الوحدة, الوحدة, الحجم المكتوب) أو None لو مفيش حجم.

    مثال: (75.0, "KOOP 1L SUT") -> (75.0, "L", "1 L")
          (17.99, "... 200ML")  -> (89.95, "L", "0.2 L")
    """
    size = parse_size(name)
    if not size:
        return None

    amount, unit = size
    return round(price / amount, 2), unit, f"{_tidy(amount)} {unit}"


def _tidy(number: float) -> str:
    """0.2 مش 0.2000000001، و1 مش 1.0"""
    text = f"{number:.3f}".rstrip("0").rstrip(".")
    return text or "0"


def summarise(rows: list[dict], qty: float | None = None,
              unit: str | None = None) -> dict:
    """
    بياخد صفوف الأسعار ويطلّع المدى على أساس عادل.

    rows: [{"price": 75.0, "name": "KOOP 1L SUT", ...}, ...]
    qty + unit: اللي اليوزر طلبه — "عايز 2 لتر"

    بيرجّع: {"low", "high", "basis", "items", "ignored"}

    ليه هنا مش جوّه الـ endpoint؟ عشان القاعدة دي هي قلب المنتج —
    "إيه الأقل وإيه الأكتر" — ولازم تكون قابلة للاختبار لوحدها من
    غير سيرفر ولا داتابيز.
    """
    items = []
    for row in rows:
        price = float(row["price"])
        per = unit_price(price, row.get("name", ""))
        items.append({
            "price": price,
            "name": row.get("name", ""),
            "url": row.get("url") or "",
            "size": per[2] if per else None,
            "unit": per[1] if per else None,
            "unit_price": per[0] if per else None,
            "total": None,
        })

    wanted = to_base(qty, unit) if (qty and unit) else None

    # ---------------------------------------------------------------
    # 1) اليوزر حدد كمية ووحدة: "عايز 2 لتر"
    # ---------------------------------------------------------------
    if wanted:
        amount, base = wanted
        label = find_unit(unit)["label"]

        if base is None:
            # قطع: السعر × العدد، ومفيش تحويل
            for item in items:
                item["total"] = round(item["price"] * amount, 2)
            usable = items
        else:
            # بناخد اللي وحدته تطابق المطلوب بس.
            # لو طلبت لتر، منتج بالكيلو مالوش لازمة هنا.
            usable = [i for i in items if i["unit"] == base]
            for item in usable:
                item["total"] = round(item["unit_price"] * amount, 2)

        if usable:
            rest = [i for i in items if i not in usable]
            return {
                "low": min(i["total"] for i in usable),
                "high": max(i["total"] for i in usable),
                "basis": f"{_tidy(qty)} {label}",
                "items": sorted(usable, key=lambda i: i["total"]) + rest,
                # اللي استبعدناه: بنقوله لليوزر بدل ما يختفي بهدوء
                "ignored": len(rest),
            }
        # ولا منتج بالوحدة المطلوبة — بنكمّل بالطريقة العامة تحت
        # بدل ما نرجّع 404. نتيجة تقريبية مع توضيح أحسن من لا حاجة.

    # ---------------------------------------------------------------
    # 2) مفيش كمية محددة: المقارنة بسعر الوحدة لو كلها نفس الوحدة
    # ---------------------------------------------------------------
    units = {i["unit"] for i in items if i["unit"]}

    if len(units) == 1:
        base = units.pop()
        comparable = [i for i in items if i["unit_price"] is not None]
        rest = [i for i in items if i["unit_price"] is None]
        return {
            "low": min(i["unit_price"] for i in comparable),
            "high": max(i["unit_price"] for i in comparable),
            "basis": f"per {base}",
            # الترتيب بسعر الوحدة — ده الترتيب الحقيقي للرخص.
            "items": sorted(comparable, key=lambda i: i["unit_price"]) + rest,
            "ignored": len(rest),
        }

    # ---------------------------------------------------------------
    # 3) أحجام مختلطة أو مفيش أحجام: بالقطعة، وبنقول كده صراحة
    # ---------------------------------------------------------------
    return {
        "low": min(i["price"] for i in items),
        "high": max(i["price"] for i in items),
        "basis": "per item",
        "items": sorted(items, key=lambda i: i["price"]),
        "ignored": 0,
    }
