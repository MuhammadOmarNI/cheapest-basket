"""
اختبار إن النسخة المنشورة بتتصرف صح.

الفرق بين "على جهازي" و"منشور" مش تفصيلة — القواعد مختلفة:
الزحف مستحيل، والحماية لازم تبقى مفعّلة، والـ CORS مش محتاج.
"""
import pathlib as _pathlib, sys as _sys
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parent.parent))

import importlib
import json
import os
import re

failures = []


def check(label, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {label}" + ("" if cond else f"  {detail}"))
    if not cond:
        failures.append(label)


def equals(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f"  got={got!r} want={want!r}"))
    if not ok:
        failures.append(label)


ROOT = _pathlib.Path(__file__).resolve().parent.parent
SRC = (ROOT / "api/index.py").read_text(encoding="utf-8")

# ========================================================= شكل المشروع ==
print("== ملفات النشر ==")
for name in ["vercel.json", "requirements.txt", ".gitignore", ".env.example",
             "api/index.py", "lib/__init__.py", "tools/refresh.py", "index.html"]:
    check(f"{name} موجود", (ROOT / name).exists())

check("مفيش .env متسرّب", not (ROOT / ".env").exists(),
      "امسحه قبل ما ترفع — فيه مفتاحك السري")

gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
check(".env في gitignore", ".env" in gitignore)

# ليس entrypoint في الجذر: وجوده بيخلّي Vercel يعتبره framework preset
# ويوجّه كل الطلبات له — بما فيها طلبات الصفحات الثابتة.
for bad in ["main.py", "app.py", "index.py", "server.py", "asgi.py", "wsgi.py"]:
    check(f"مفيش {bad} في الجذر", not (ROOT / bad).exists(),
          "وجوده بيخلّي Vercel يوجّه كل حاجة للبايثون")

# ============================================================ vercel.json ==
print("\n== vercel.json ==")
cfg = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))

rewrites = cfg.get("rewrites", [])
check("فيه rewrite للـ /api/*", any(r["source"] == "/api/(.*)" for r in rewrites), rewrites)
equals("بيوجّه لملف واحد",
       [r["destination"] for r in rewrites if r["source"] == "/api/(.*)"], ["/api/index"])

fn = cfg.get("functions", {}).get("api/index.py", {})
check("maxDuration متحدّدة", "maxDuration" in fn, fn)
check("وأقل من سقف Hobby (300)", fn.get("maxDuration", 999) <= 300, fn.get("maxDuration"))
check("الملفات الثابتة مستبعدة من الحزمة", "js/**" in fn.get("excludeFiles", ""), fn)

# ============================================================ requirements ==
print("\n== requirements.txt ==")
reqs = (ROOT / "requirements.txt").read_text(encoding="utf-8")
for pkg in ["fastapi", "pydantic-settings", "httpx", "beautifulsoup4"]:
    check(f"{pkg} مثبّت بإصدار", re.search(rf"^{pkg}==", reqs, re.M) is not None,
          "من غير == الإصدار ممكن يتغيّر تحتك")

# ================================================== سلوك الإنتاج في الكود ==
print("\n== قواعد الإنتاج ==")
check("بيقرا متغير VERCEL", "ON_VERCEL" in SRC and 'os.environ.get("VERCEL")' in SRC)
check("CORS مقفول في الإنتاج", "if not ON_VERCEL:\n    app.add_middleware" in SRC)
check("الزحف مرفوض في الإنتاج", "if ON_VERCEL:" in SRC and "300s" in SRC)
check("الحماية بتفشل مقفولة",
      "ADMIN_EMAILS is not set" in SRC, "لازم يرفض مش يفتح")
check("/config بيقول can_refresh", "can_refresh" in SRC)

# ================================================ الدوال بتشتغل فعلاً ==
print("\n== استيراد الوحدات ==")
os.environ.setdefault("supabase_url", "https://demo.supabase.co")
os.environ.setdefault("supabase_service_key", "k")

# fastapi مش متثبّت في بيئة الاختبار دي، وmatcher محتاج HTTPException منه
import types                                             # noqa: E402
if "fastapi" not in _sys.modules:
    class HTTPException(Exception):
        def __init__(self, status_code, detail=""):
            super().__init__(f"{status_code}: {detail}")
            self.status_code, self.detail = status_code, detail
    stub = types.ModuleType("fastapi")
    stub.HTTPException = HTTPException
    _sys.modules["fastapi"] = stub

from lib import sizes, crawler, store, matcher            # noqa: E402
from lib.settings import settings                         # noqa: E402

check("lib.sizes شغّالة", sizes.parse_size("KOOP 1L SUT") == (1.0, "L"))
check("lib.crawler شغّالة", crawler.parse_price("322.00 ₺") == 322.0)
check("lib.settings بتقرا البيئة", settings.supabase_url.startswith("https://"))
check("lib.matcher فيها الحاجز", "allowed" in (ROOT / "lib/matcher.py").read_text(encoding="utf-8"))

# ===================================================== الواجهة بتلاقي الـ API ==
print("\n== js/api.js ==")
js = (ROOT / "js/api.js").read_text(encoding="utf-8")
check("بيجرّب نفس الدومين", "location.origin + '/api'" in js)
check("وبيرجع للمحلي", "127.0.0.1:8010" in js)
check("مفيش عنوان ثابت متنسي في page-admin",
      "var API = 'http" not in (ROOT / "js/page-admin.js").read_text(encoding="utf-8"))

print()
print("ALL PASSED" if not failures else f"PROBLEMS: {failures}")
raise SystemExit(1 if failures else 0)
