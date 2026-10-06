"""
settings.py — كل القيم السرية والمتغيرة في مكان واحد، جاية من .env

ليه شِلناها من main.py؟
لأن store.py و crawler.py محتاجينها كمان. لو سابناها في main.py،
هيبقى store.py بيستورد main.py و main.py بيستورد store.py —
دي حلقة دائرية (circular import) وPython هيرفض.

القاعدة: الحاجة اللي أكتر من ملف محتاجها، تنزل في ملف تحتهم كلهم.
"""

import pathlib

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # env_file=".env" يعني اقرا الملف ده. extra="ignore" يعني
    # لو فيه في .env مفاتيح مش معرّفة هنا، تجاهلها بدل ما تقع.
    # .env في جذر المشروع. على Vercel مفيش ملف أصلاً — المتغيرات
    # بتيجي من إعدادات المشروع، وpydantic بيقراها من البيئة لوحده.
    model_config = SettingsConfigDict(
        env_file=str(pathlib.Path(__file__).resolve().parent.parent / ".env"),
        extra="ignore",
    )

    # --- Gemini ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    # يُستعمل فقط لو الأساسي فشل بـ 503/502 بعد كل محاولاته.
    # سيبه فاضي عشان تقفل الحكاية دي.
    gemini_fallback_model: str = ""

    # --- الأدمن ---
    # إيميلات مفصولة بفاصلة. فاضية = مفيش حماية (وضع التطوير).
    admin_emails: str = ""

    # --- Supabase ---
    supabase_url: str = ""
    supabase_service_key: str = ""        # سري. بيتخطى RLS. السيرفر بس.

    # --- الزحف ---
    # الموقع بيطلب 30 ثانية بين كل طلب في robots.txt بتاعه. بنحترمها.
    crawl_delay_seconds: float = 30.0
    # لو عايز تجرّب بسرعة: حدّد عدد الأقسام. 0 = كلهم.
    crawl_max_categories: int = 0


settings = Settings()
