"""
netcheck.py — أصغر حاجة ممكنة تفشل بنفس الطريقة.

الفكرة: لو الغلط بيحصل هنا كمان، يبقى مش في FastAPI ولا في الـ prompt
ولا في الـ API key. يبقى في الشبكة أو في TLS على الجهاز ده.

شغّله كده (وإنت جوه الـ venv، من فولدر api):
    python netcheck.py
"""
import os, ssl, sys
import httpx
import certifi

URL = "https://generativelanguage.googleapis.com/v1beta/models"

print("python      :", sys.version.split()[0])
print("httpx       :", httpx.__version__)
print("openssl     :", ssl.OPENSSL_VERSION)
print("certifi     :", certifi.where())

# httpx بيقرا المتغيرات دي لوحده. لو واحد منهم متسيب من VPN قديم،
# كل طلب هيروح لمكان ميت وإحنا مش واخدين بالنا.
print("\n-- proxy environment variables --")
found_proxy = False
for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
             "http_proxy", "https_proxy", "all_proxy", "NO_PROXY"):
    value = os.environ.get(name)
    if value:
        found_proxy = True
        print(f"  {name} = {value}")
if not found_proxy:
    print("  (none — good)")

print("\n-- attempt 1: normal request --")
try:
    r = httpx.get(URL, timeout=20)
    print(f"  OK  status {r.status_code}")          # 403 كفاية: يعني وصلنا لجوجل
    print(f"      {r.text[:120]}")
except Exception as e:
    print(f"  FAILED  {type(e).__name__}: {e}")
    # السبب الحقيقي بيكون متخبي تحت، مش في الرسالة اللي فوق
    cause = e.__cause__
    depth = 1
    while cause is not None and depth < 5:
        print(f"      cause {depth}: {type(cause).__name__}: {cause}")
        cause = cause.__cause__
        depth += 1

print("\n-- attempt 2: same request, TLS verification off --")
# ملحوظة أمان: ده للتشخيص بس. لو دي نجحت والأولى فشلت،
# يبقى في برنامج على الجهاز بيفتح الـ HTTPS في النص (antivirus غالباً).
try:
    r = httpx.get(URL, timeout=20, verify=False)
    print(f"  OK  status {r.status_code}")
    print("      => الشبكة سليمة. المشكلة في الشهادات (certificates).")
except Exception as e:
    print(f"  FAILED  {type(e).__name__}: {e}")
    print("      => المشكلة مش شهادات. الاتصال نفسه مقفول.")
