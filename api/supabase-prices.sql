-- ===========================================================================
-- جداول الأسعار وإعدادات الأدمن
--
-- شغّله مرة واحدة: Supabase → SQL Editor → New query → Run
-- ===========================================================================


-- ---------------------------------------------------------------------------
-- 1) إعدادات الأدمن — صف واحد بس في الجدول كله
-- ---------------------------------------------------------------------------
create table if not exists admin_settings (
  id          int           primary key default 1,
  price_mode  text          not null default 'site',   -- 'site' = زحف الموقع | 'ai' = بحث مؤرّض
  source_url  text          not null default 'https://www.kibrissanalmarket.com',
  updated_at  timestamptz   not null default now(),

  -- الـ primary key بيمنع تكرار id=1، والـ check بيمنع أي id تاني.
  -- النتيجة: مستحيل يبقى في الجدول أكتر من صف واحد.
  constraint one_row_only check (id = 1),

  -- الداتابيز هي اللي ترفض القيمة الغلط، مش كود التطبيق.
  -- لو حد بعت price_mode = 'banana' الإدخال هيفشل هنا.
  constraint mode_is_known check (price_mode in ('site', 'ai'))
);

-- نحط الصف الوحيد. لو موجود، ما نعملش حاجة (عشان نعرف نشغّل الملف تاني بأمان).
insert into admin_settings (id) values (1) on conflict (id) do nothing;


-- ---------------------------------------------------------------------------
-- 2) الأسعار المزحوفة من الموقع
-- ---------------------------------------------------------------------------
create table if not exists product_prices (
  id          bigserial     primary key,
  source      text          not null,             -- اسم الموقع (عشان نضيف مصادر تانية بعدين)
  sku         text,                               -- الباركود لو الموقع بينشره
  name        text          not null,             -- الاسم زي ما هو: "KIRNI PILIC GOGUS FILLET"
  name_norm   text          not null,             -- نسخة مبسطة للبحث: "kirni pilic gogus fillet"
  price       numeric(10,2) not null check (price > 0),
  currency    text          not null default 'TRY',
  category    text,                               -- القسم اللي لقيناه فيه
  url         text,                               -- لينك المنتج — الدليل على السعر
  fetched_at  timestamptz   not null default now(),

  -- المفتاح اللي بنعرف بيه إن المنتج ده اتسجّل قبل كده.
  -- بدونه، كل زحف هيضيف نسخة جديدة وهنغرق في تكرار.
  -- معاه، الزحف التاني بيـ UPDATE السعر بدل ما يضيف صف.
  unique (source, name)
);

-- الفهارس: بدونها كل بحث بيقرا الجدول كله سطر سطر.
create index if not exists product_prices_norm_idx on product_prices (name_norm);
create index if not exists product_prices_src_idx  on product_prices (source);


-- ---------------------------------------------------------------------------
-- 3) الأمان — مين يقرا ومين يكتب
-- ---------------------------------------------------------------------------
alter table admin_settings  enable row level security;
alter table product_prices  enable row level security;

-- قراءة للجميع: الأسعار معلومة عامة منشورة على الإنترنت أصلاً،
-- والواجهة بتقراها بالمفتاح العام (publishable).
create policy "anyone can read settings" on admin_settings for select using (true);
create policy "anyone can read prices"   on product_prices for select using (true);

-- لاحظ: مفيش أي policy للـ insert / update / delete. ولا واحدة.
--
-- الكتابة بتحصل من الباكند بمفتاح service_role، وهو بيتخطى RLS بطبيعته.
-- والمفتاح ده عايش في .env على السيرفر بس، عمره ما يوصل للمتصفح.
--
-- النتيجة: المتصفح يقرا ومش بيقدر يكتب — مش لأن الكود مانعه،
-- لكن لأن الداتابيز نفسها مش هتسمح. حتى لو حد زوّر طلب بإيده.
