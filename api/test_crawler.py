"""
اختبار الزاحف على HTML حقيقي مأخوذ من الموقع نفسه.

ليه ده مهم؟ لأن الزاحف الوحيد اللي بيقدر يغلط بهدوء. لو الـ selector
غلط، مش هيرفع خطأ — هيرجّع قايمة فاضية، والجدول يفضل فاضي، وإنت
تفكر إن المشكلة في الشبكة.
"""
import sys
from crawler import parse_price, parse_products, parse_categories

failures = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f"  got={got!r} want={want!r}"))
    if not ok:
        failures.append(label)


# ---------------------------------------------------------------- الأسعار ---
print("== parse_price ==")
check("الشكل العادي",        parse_price("272.00 ₺"), 272.0)
check("كسور",                parse_price("129.99 ₺"), 129.99)
check("مسافات ورموز",        parse_price("  28.00\xa0₺  "), 28.0)
check("الشكل التركي للألوف", parse_price("1.234,56 ₺"), 1234.56)
check("فاصلة كسور فقط",      parse_price("29,99 ₺"), 29.99)
check("فاصلة ألوف إنجليزية", parse_price("1,234.56 ₺"), 1234.56)
check("صفر يترفض",           parse_price("0.00 ₺"), None)
check("نص فاضي",             parse_price(""), None)
check("مفيش أرقام",          parse_price("Fiyat sorunuz"), None)

# --------------------------------------------------------------- المنتجات ---
# ده HTML حقيقي منسوخ من الموقع، مش مؤلّف.
REAL = """
<div class="product-inner"><span class="loop-product-categories"><a
href="https://www.kibrissanalmarket.com/urun-grubu/temel-gida/" rel="tag">Temel Gıda</a>, <a
href="https://www.kibrissanalmarket.com/urun-grubu/temel-gida/ekmek-pide-yufka/" rel="tag">Ekmek-Pide-Yufka</a></span><a
href="https://www.kibrissanalmarket.com/urunler/ekmek/" class="woocommerce-LoopProduct-link woocommerce-loop-product__link"><div
class="product-thumbnail"><img width="200" height="200" src="//www.kibrissanalmarket.com/wp-content/uploads/2021/08/ekmek.jpg"
class="attachment-shop_catalog" alt=""></div><div class="skucuk">2009530000144</div><h2
class="woocommerce-loop-product__title">EKMEK</h2></a><div class="price-add-to-cart"> <span class="price"><span
class="gt-price"><span class="woocommerce-Price-amount amount">28.00&nbsp;<span
class="woocommerce-Price-currencySymbol">&#8378;</span></span></span></span></div></div>

<div class="product-inner"><a href="https://www.kibrissanalmarket.com/urunler/kirni-pilic-gogus-fillet/"
class="woocommerce-loop-product__link"><div class="skucuk">2900882</div><h2
class="woocommerce-loop-product__title">KIRNI PILIC GOGUS FILLET</h2></a><div class="price-add-to-cart"><span
class="price"><span class="woocommerce-Price-amount amount">322.00&nbsp;<span
class="woocommerce-Price-currencySymbol">&#8378;</span></span></span></div></div>

<!-- كرتونة بغير سعر: لازم تتجاهل، مش ترفع خطأ -->
<div class="product-inner"><a href="/urunler/yok/" class="woocommerce-loop-product__link"><h2
class="woocommerce-loop-product__title">STOKTA YOK</h2></a></div>
"""

print("\n== parse_products ==")
rows = parse_products(REAL, category="tavuk")
check("عدد المنتجات (الناقص اتجاهل)", len(rows), 2)

if len(rows) == 2:
    ekmek, tavuk = rows
    check("اسم أول منتج",   ekmek["name"], "EKMEK")
    check("سعر أول منتج",   ekmek["price"], 28.0)
    check("باركود",         ekmek["sku"], "2009530000144")
    check("لينك",           ekmek["url"], "https://www.kibrissanalmarket.com/urunler/ekmek/")
    check("القسم",          ekmek["category"], "tavuk")

    check("سعر الفراخ",     tavuk["price"], 322.0)
    # الحتة المهمة: الحروف التركية بقت إنجليزية عشان البحث يلاقيها
    check("التبسيط للبحث",  tavuk["name_norm"], "kirni pilic gogus fillet")

# ---------------------------------------------------------------- الأقسام ---
CATS = """
<a href="https://www.kibrissanalmarket.com/urun-grubu/meyve-ve-sebze/">رئيسي — يتجاهل</a>
<a href="https://www.kibrissanalmarket.com/urun-grubu/meyve-ve-sebze/sebze/">فرعي</a>
<a href="https://www.kibrissanalmarket.com/urun-grubu/et-tavuk-denizurunleri/tavuk/">فرعي</a>
<a href="https://www.kibrissanalmarket.com/urun-grubu/et-tavuk-denizurunleri/tavuk/?orderby=price">نفسه بـ query</a>
<a href="https://www.kibrissanalmarket.com/urun-grubu/kisisel-bakim/sampuan/">مش أكل — يتجاهل</a>
<a href="https://www.kibrissanalmarket.com/urun-grubu/evcil-hayvan/kedi/">مش أكل — يتجاهل</a>
<a href="/urunler/ekmek/">منتج — مش قسم</a>
"""

print("\n== parse_categories ==")
cats = parse_categories(CATS)
print("   ", cats)
check("الفرعية بس، والتكرار اتشال", len(cats), 2)
check("فيها tavuk", "/urun-grubu/et-tavuk-denizurunleri/tavuk/" in cats, True)
check("الشامبو اتشال", all("kisisel" not in c for c in cats), True)
check("الرئيسي اتشال", "/urun-grubu/meyve-ve-sebze/" not in cats, True)

print()
print("ALL PASSED" if not failures else f"PROBLEMS: {failures}")
sys.exit(1 if failures else 0)
