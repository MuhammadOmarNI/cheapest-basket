"""
refresh.py — بيزحف الموقع ويحفظ الأسعار في Supabase.

ليه سكريبت مش زرار في الموقع المنشور؟

  الزحف بياخد ~٣٦ دقيقة (٧١ قسم × ٣٠ ثانية، احترامًا لـ robots.txt).
  أقصى مدة لدالة على Vercel ٣٠٠ ثانية. الفرق مش قابل للتقريب.

فالزحف بيفضل على جهازك، والنتيجة بتروح Supabase، والموقع المنشور
بيقراها من هناك. الموقع ما بيزحفش — بيقرا بس.

شغّله من جذر المشروع:

    python tools/refresh.py              كل الأقسام
    python tools/refresh.py --limit 3    ٣ أقسام بس (للتجربة)
    python tools/refresh.py --fast       من غير انتظار (للتجربة المحلية فقط)
"""

import argparse
import asyncio
import pathlib
import sys
import time

# الجذر في المسار عشان "lib" تتلاقى من أي مكان
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from lib import crawler, store          # noqa: E402
from lib.settings import settings       # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Crawl prices into Supabase")
    parser.add_argument("--limit", type=int, default=0,
                        help="عدد الأقسام (0 = كلهم)")
    parser.add_argument("--fast", action="store_true",
                        help="من غير انتظار بين الطلبات — للتجربة على نسخة محلية فقط")
    args = parser.parse_args()

    if not (settings.supabase_url and settings.supabase_service_key):
        print("✗ Supabase مش مضبوط. حط supabase_url و supabase_service_key في .env")
        return 1

    if args.limit:
        settings.crawl_max_categories = args.limit

    if args.fast:
        # تحذير مش تعليق: تجاهل crawl-delay على موقع حد تاني مش
        # تسريع — ده ضغط على سيرفره، والموقع من حقه يحظرك.
        print("⚠ --fast بيتجاهل crawl-delay. استعمله على نسخة محلية بس.")
        settings.crawl_delay_seconds = 0

    total = args.limit or "كل"
    minutes = (args.limit or 71) * settings.crawl_delay_seconds / 60
    print(f"بيزحف {total} قسم · متوقّع ~{minutes:.0f} دقيقة")
    print("سيبه شغّال. كل قسم بيتحفظ لوحده، فأي قطع بيخسّرك قسم واحد.\n")

    started = time.time()
    saved_total = {"n": 0}

    def progress(**kw):
        done, all_ = kw.get("done"), kw.get("total")
        if done is None:
            return
        products = kw.get("products", 0)
        # \r يكتب فوق نفس السطر بدل ما يملا الشاشة ٧١ سطر
        print(f"\r  {done}/{all_} قسم · {products} منتج", end="", flush=True)

    async def save(batch):
        await asyncio.to_thread(store.upsert_prices, batch)
        saved_total["n"] += len(batch)

    try:
        result = asyncio.run(crawler.crawl(progress=progress, save=save))
    except KeyboardInterrupt:
        print(f"\n\n⚠ اتوقف بإيدك. {saved_total['n']} منتج اتحفظوا قبلها.")
        return 130
    except Exception as error:
        print(f"\n\n✗ وقع: {type(error).__name__}: {error}")
        print(f"  {saved_total['n']} منتج اتحفظوا قبل الوقعة.")
        return 1

    took = (time.time() - started) / 60
    print(f"\n\n✓ خلص في {took:.0f} دقيقة")
    print(f"  {result['saved']} منتج محفوظ من {result['categories']} قسم")

    if result["errors"]:
        print(f"  {len(result['errors'])} قسم فشل:")
        for e in result["errors"][:5]:
            print(f"    - {e}")

    summary = store.count_prices()
    print(f"\n  الجدول دلوقتي فيه {summary['count']} منتج.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
