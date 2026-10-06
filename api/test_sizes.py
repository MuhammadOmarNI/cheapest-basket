"""اختبار قراءة الحجم — على أسماء حقيقية من الجدول."""
import sys
from sizes import parse_size, unit_price

failures = []


def equals(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f"  got={got!r} want={want!r}"))
    if not ok:
        failures.append(label)


print("== parse_size ==")
equals("لتر",              parse_size("KOOP 1L SUT"), (1.0, "L"))
equals("LT",               parse_size("PINAR DEVAM SUTU 1LT"), (1.0, "L"))
equals("ملّي",             parse_size("KOOP KÜÇÜK SUT 200ML"), (0.2, "L"))
equals("500ML",            parse_size("PINAR ÇOCUK DEVAM SÜTÜ 500ML"), (0.5, "L"))
equals("كيلو",             parse_size("ALASKA 1KG KONSANTRE KUTU SUT"), (1.0, "KG"))
equals("جرام",             parse_size("7 DAYS KAKAO KREMALI 55GR"), (0.055, "KG"))
equals("(kg) من غير رقم",  parse_size("KIRNI PILIC BAGET BUT (kg)"), (1.0, "KG"))
equals("مدى: بياخد الأخير", parse_size("KIRNI PILIC BUTUN 2-2,5 KG"), (2.5, "KG"))
equals("فاصلة عشرية",      parse_size("SUT 1,5 L"), (1.5, "L"))
equals("مفيش حجم",         parse_size("KIRNI PILIC GOGUS FILLET"), None)
equals("اسم فاضي",         parse_size(""), None)
equals("صفر يترفض",        parse_size("SUT 0L"), None)
# "7 DAYS" ما يتقراش على إنه 7 جرام
equals("رقم من غير وحدة",  parse_size("7 DAYS KAKAO"), None)

print("\n== unit_price ==")
equals("1 لتر بـ75",       unit_price(75.0, "KOOP 1L SUT"), (75.0, "L", "1 L"))
equals("200ml بـ17.99",    unit_price(17.99, "KOOP KÜÇÜK SUT 200ML"), (89.95, "L", "0.2 L"))
equals("1kg بـ478.99",     unit_price(478.99, "ALASKA 1KG KONSANTRE KUTU SUT"),
       (478.99, "KG", "1 KG"))
equals("من غير حجم",       unit_price(322.0, "KIRNI PILIC GOGUS FILLET"), None)

print("\n== المقارنة اللي كانت غلط ==")
small = unit_price(17.99, "KOOP KÜÇÜK SUT 200ML")[0]
big   = unit_price(75.00, "KOOP 1L SUT")[0]
print(f"   200ml = {small} ₺/L   |   1L = {big} ₺/L")
equals("الصغيرة أغلى للتر فعلاً", small > big, True)



# ===========================================================================
# المدى — على البيانات الحقيقية اللي رجعت من /price
# ===========================================================================
from sizes import summarise

print("\n== summarise: حليب (نفس الوحدة) ==")
MILK = [
    {"price": 17.99, "name": "KOOP KÜÇÜK SUT 200ML", "url": "u1"},
    {"price": 75.00, "name": "KOOP 1L SUT",          "url": "u2"},
    {"price": 95.00, "name": "KOOP 1L LAKTOZSUZ SUT","url": "u3"},
    {"price": 169.99,"name": "PINAR ORGANIK SUT 1LT","url": "u4"},
]
m = summarise(MILK)
print(f"   {m['low']} → {m['high']}  ({m['basis']})")
equals("الأساس لكل لتر", m["basis"], "per L")
equals("الأرخص = KOOP 1L",  m["low"], 75.0)
equals("الأغلى = PINAR ORGANIK", m["high"], 169.99)
equals("المرتّب أولهم الأرخص للتر", m["items"][0]["name"], "KOOP 1L SUT")
equals("و200ml مش الأرخص رغم إن سعرها أقل",
       m["items"][0]["price"] > MILK[0]["price"], True)

print("\n== summarise: أحجام مختلطة (لتر + كيلو) ==")
MIXED = [
    {"price": 75.00,  "name": "KOOP 1L SUT", "url": "u1"},
    {"price": 478.99, "name": "ALASKA 1KG KONSANTRE KUTU SUT", "url": "u2"},
]
x = summarise(MIXED)
equals("بيرجع للقطعة", x["basis"], "per item")
equals("المدى بالسعر المطلق", (x["low"], x["high"]), (75.0, 478.99))

print("\n== summarise: مفيش أحجام ==")
NOSIZE = [
    {"price": 322.0, "name": "KIRNI PILIC GOGUS FILLET", "url": "u1"},
    {"price": 289.0, "name": "KIRNI PILIC PIRZOLA", "url": "u2"},
]
n = summarise(NOSIZE)
equals("بالقطعة", n["basis"], "per item")
equals("المدى صح", (n["low"], n["high"]), (289.0, 322.0))
equals("مرتّب بالسعر", n["items"][0]["price"], 289.0)

print("\n== summarise: بعضها بحجم وبعضها لأ ==")
PART = [
    {"price": 75.00, "name": "KOOP 1L SUT", "url": "u1"},
    {"price": 40.00, "name": "SUT KUTU", "url": "u2"},        # مفيش حجم
    {"price": 17.99, "name": "SUT 200ML", "url": "u3"},
]
q = summarise(PART)
equals("بيقارن اللي يقدر", q["basis"], "per L")
equals("المدى من المقروء بس", (q["low"], q["high"]), (75.0, 89.95))
equals("اللي مش مقروء في الآخر", q["items"][-1]["name"], "SUT KUTU")
equals("وبرّه الحساب", q["items"][-1]["unit_price"], None)

print("\n== صف واحد ==")
one = summarise([{"price": 322.0, "name": "KIRNI PILIC GOGUS FILLET", "url": "u"}])
equals("low = high", (one["low"], one["high"]), (322.0, 322.0))


# ===========================================================================
# الكمية والوحدة اللي اليوزر اختارها
# ===========================================================================
from sizes import to_base, find_unit, UNIT_VALUES

print("\n== to_base ==")
equals("2 لتر",     to_base(2, "l"), (2.0, "L"))
equals("500 ملّي",   to_base(500, "ml"), (0.5, "L"))
equals("250 جرام",  to_base(250, "g"), (0.25, "KG"))
equals("3 قطع",     to_base(3, "piece"), (3.0, None))
equals("وحدة مش موجودة", to_base(1, "gallon"), None)
equals("كمية صفر",   to_base(0, "l"), None)
equals("كمية سالبة", to_base(-2, "l"), None)
equals("الحروف الكبيرة تعدّي", to_base(2, "L"), (2.0, "L"))

print("\n== summarise مع كمية ==")
MILK2 = [
    {"price": 17.99,  "name": "SUT 200ML", "url": "u1"},
    {"price": 75.00,  "name": "KOOP 1L SUT", "url": "u2"},
    {"price": 478.99, "name": "ALASKA 1KG KONSANTRE SUT", "url": "u3"},
]
r = summarise(MILK2, 2, "l")
print(f"   {r['low']} → {r['high']}  ({r['basis']})  استبعد {r['ignored']}")
equals("الأساس = الكمية المطلوبة", r["basis"], "2 L")
equals("أرخص 2 لتر", r["low"], 150.0)          # 75 ₺/L × 2
equals("أغلى 2 لتر", r["high"], 179.9)          # 89.95 ₺/L × 2
equals("اللي بالكيلو اتستبعد", r["ignored"], 1)
equals("الأرخص الأول", r["items"][0]["name"], "KOOP 1L SUT")
equals("المستبعد في الآخر من غير total", r["items"][-1]["total"], None)

print("\n== نفس الداتا بوحدة تانية ==")
r = summarise(MILK2, 500, "ml")
equals("500ml أساس", r["basis"], "500 ml")
equals("نص لتر بالأرخص", r["low"], 37.5)        # 75 × 0.5

print("\n== بالكيلو ==")
r = summarise(MILK2, 1, "kg")
equals("بيختار اللي بالكيلو بس", r["low"], 478.99)
equals("واستبعد الاتنين بتوع اللتر", r["ignored"], 2)

print("\n== قطع ==")
CHICKEN = [
    {"price": 322.0, "name": "KIRNI PILIC GOGUS FILLET", "url": "u1"},
    {"price": 289.0, "name": "KIRNI PILIC PIRZOLA", "url": "u2"},
]
r = summarise(CHICKEN, 2, "piece")
equals("قطعتين", r["basis"], "2 piece")
equals("السعر × 2", (r["low"], r["high"]), (578.0, 644.0))

print("\n== وحدة مطلوبة مفيش منها حاجة ==")
r = summarise(CHICKEN, 2, "l")
equals("ما بيقعش — بيرجع للقطعة", r["basis"], "per item")
equals("والمدى لسه صح", (r["low"], r["high"]), (289.0, 322.0))

print("\n== من غير كمية ==")
r = summarise(MILK2)
equals("بيرجع للسلوك القديم", r["basis"], "per item")   # لتر وكيلو مع بعض

print("\n== قايمة الوحدات ==")
equals("خمس وحدات", UNIT_VALUES, ["g", "kg", "ml", "l", "piece"])
equals("find_unit بيلاقي", find_unit("kg")["base"], "KG")
equals("find_unit بيرجّع None للمجهول", find_unit("stone"), None)

print()
print("ALL PASSED" if not failures else f"PROBLEMS: {failures}")
sys.exit(1 if failures else 0)
