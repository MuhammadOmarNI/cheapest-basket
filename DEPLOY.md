# النشر على Vercel

## قبل ما ترفع — ٣ حاجات إجبارية

**١. تأكد إن `.env` مش هيروح GitHub.**

```bash
git status --short | grep .env     # المفروض ما يطلعش حاجة
```

الملف في `.gitignore` خلاص. لو ظهر، يبقى اتضاف قبل كده — شيله:

```bash
git rm --cached .env
```

> لو المفتاح السري راح GitHub مرة واحدة، اعتبره مكشوف حتى لو مسحته
> بعدها. اعمل واحد جديد من Supabase.

**٢. املا `admin_emails`.** من غيرها، النسخة المنشورة بترفض كل
تعديلات الأدمن (بتفشل مقفولة عن قصد).

**٣. شغّل الاختبارات.**

```bash
python tests/test_deploy.py
```

---

## الرفع

```bash
git init
git add -A
git commit -m "Cheapest Basket"
gh repo create cheapest-basket --private --source=. --push
```

بعدين على [vercel.com/new](https://vercel.com/new): اختار الريبو → Deploy.
مفيش build command ولا framework — Vercel بيلاقي `vercel.json` لوحده.

---

## متغيرات البيئة على Vercel

Project Settings → Environment Variables. **لكل البيئات** (Production،
Preview، Development):

| الاسم | القيمة |
|---|---|
| `supabase_url` | `https://xxxx.supabase.co` |
| `supabase_service_key` | المفتاح السري (service_role) |
| `gemini_api_key` | مفتاح Gemini |
| `gemini_model` | `gemini-3.6-flash` |
| `gemini_fallback_model` | `gemini-3.5-flash-lite` |
| `admin_emails` | إيميلك |

بعد أي تغيير فيهم: **Redeploy**. المتغيرات بتتقري وقت البناء.

---

## الزحف بيفضل على جهازك

الزحف ~٣٦ دقيقة. أقصى مدة لدالة على Vercel **٣٠٠ ثانية**. الفرق ده
مش قابل للتقريب، فالموقع المنشور **بيقرا بس**:

```
جهازك:  python tools/refresh.py  →  Supabase
Vercel:                             Supabase  →  الزوّار
```

```bash
python tools/refresh.py              # كل الأقسام (~36 دقيقة)
python tools/refresh.py --limit 3    # ٣ أقسام للتجربة
```

صفحة الأدمن على النسخة المنشورة بتخفي زرار التحديث وبتقول السبب.

---

## التشغيل محلياً بعد النقل

```bash
python -m uvicorn api.index:app --reload --port 8010
```

**من جذر المشروع** مش من `api/` — عشان `lib` تتلاقى.

الواجهة بتلاقي الـ API لوحدها: على الاستضافة بتستعمل نفس الدومين،
وعلى جهازك بترجع لـ `127.0.0.1:8010`. مفيش سطر تغيّره قبل ما ترفع.

---

## اللي بيتغيّر بين المحلي والمنشور

| | على جهازك | منشور |
|---|---|---|
| CORS | مفتوح | مقفول (نفس الدومين) |
| `admin_emails` فاضي | مفتوح | **مرفوض** |
| الزحف | شغّال | مرفوض (501) |
| عنوان الـ API | `127.0.0.1:8010` | `/api` |

الكود بيعرف هو فين من متغير `VERCEL` اللي المنصة بتحطه لوحدها.

---

## المفاتيح — مين عام ومين سري

| المفتاح | مكانه | عام؟ |
|---|---|---|
| Supabase **publishable** | `js/cloud.js` | ✅ عام — RLS ماسكاه |
| Supabase **service_role** | متغير بيئة | ❌ **سري** — بيتخطى RLS |
| Gemini | متغير بيئة | ❌ سري |

الأول موجود في كود الواجهة وده صح: لوحده مش بيفتح حاجة، لأن
سياسات RLS بتمنع أي حد من قراءة صف مش بتاعه.
