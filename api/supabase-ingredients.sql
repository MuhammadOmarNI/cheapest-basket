-- ===========================================================================
-- جدول ربط المكوّنات بالمنتجات
--
-- شغّله مرة واحدة: Supabase → SQL Editor → New query → Run
-- ===========================================================================

create table if not exists ingredient_map (
  ingredient_norm  text        primary key,    -- "chicken breast" بعد التبسيط
  original         text        not null,       -- اللي اليوزر كتبه بالظبط
  terms            jsonb       not null,       -- الكلمات التركية اللي دوّرنا بيها
  skus             jsonb       not null,       -- الباركودات اللي Gemini قال إنها المكوّن ده
  updated_at       timestamptz not null default now()
);

alter table ingredient_map enable row level security;
create policy "anyone can read ingredient map" on ingredient_map for select using (true);
-- مفيش policy للكتابة: الباكند بيكتب بمفتاح service_role زي الجداول التانية.


-- ---------------------------------------------------------------------------
-- ليه بنخزّن الـ skus مش الأسعار؟
--
-- لأن دول حاجتين بيتغيّروا بسرعات مختلفة تماماً:
--
--   السعر  →  بيتغيّر كل أسبوع. الزحف بيحدّثه.
--   الربط  →  "chicken breast يعني KIRNI PILIC GOGUS FILLET" — ده
--             ما بيتغيّرش. اسأل عنه مرة واحدة وخلاص.
--
-- لو خزّنّا السعر هنا، كان كل زحف هيخلّي الجدول ده قديم.
-- خزّنّا الربط، فالسعر بييجي طازة من product_prices في كل مرة.
--
-- والنتيجة العملية: أول مرة حد يسأل عن مكوّن = نداءين لـ Gemini.
-- كل مرة بعد كده = صفر. حتى لما الأسعار تتغيّر.
-- ---------------------------------------------------------------------------
