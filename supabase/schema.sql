-- Cheapest Basket — database schema
-- Run this once in Supabase: SQL Editor -> New query -> paste -> Run.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

create table if not exists markets (
  id         uuid primary key default gen_random_uuid(),
  name       text not null,
  sort_order int  not null default 0
);

create table if not exists meals (
  id         uuid primary key default gen_random_uuid(),
  name       text not null,
  budget     numeric,
  created_at timestamptz not null default now()
);

create table if not exists meal_ingredients (
  id      uuid primary key default gen_random_uuid(),
  meal_id uuid not null references meals(id) on delete cascade,
  name    text not null default '',
  qty     numeric,
  unit    text
);

create table if not exists prices (
  id            uuid primary key default gen_random_uuid(),
  market_id     uuid not null references markets(id) on delete cascade,
  ingredient_id uuid not null references meal_ingredients(id) on delete cascade,
  price         numeric not null,
  source        text not null default 'manual',   -- 'manual' | 'ai'
  note          text,
  updated_at    timestamptz not null default now(),
  unique (market_id, ingredient_id)
);

-- The foreign keys above do two jobs:
--   1. Deleting a meal removes its ingredients and their prices automatically.
--   2. They let PostgREST embed related rows, which is how the app loads a
--      whole meal (meal -> ingredients -> prices) in ONE request instead of
--      one request per ingredient. See MEAL_SELECT in src/lib/api.js.

-- Helpful indexes for the lookups the app actually does.
create index if not exists meal_ingredients_meal_id_idx on meal_ingredients (meal_id);
create index if not exists prices_ingredient_id_idx      on prices (ingredient_id);
create index if not exists prices_market_id_idx          on prices (market_id);

-- ---------------------------------------------------------------------------
-- Starter markets (edit or delete these in the app later)
-- ---------------------------------------------------------------------------

insert into markets (name, sort_order)
select * from (values
  ('Migros', 1), ('A101', 2), ('Şok', 3), ('CarrefourSA', 4), ('BİM', 5)
) as seed(name, sort_order)
where not exists (select 1 from markets);

-- ---------------------------------------------------------------------------
-- SECURITY — read this before sharing your deployed URL
-- ---------------------------------------------------------------------------
-- As created above, these tables have Row Level Security OFF. Anyone who has
-- your site's URL (the anon key ships in the browser bundle) can read AND
-- write this data. That is fine for a personal tool you don't advertise.
--
-- If you'd rather lock it down, the simplest option is read-only for the
-- public and writes only from your own authenticated account. Uncomment and
-- run this AFTER you've set up Supabase Auth and signed in at least once:
--
-- alter table markets          enable row level security;
-- alter table meals            enable row level security;
-- alter table meal_ingredients enable row level security;
-- alter table prices           enable row level security;
--
-- create policy "public read" on markets          for select using (true);
-- create policy "public read" on meals            for select using (true);
-- create policy "public read" on meal_ingredients for select using (true);
-- create policy "public read" on prices           for select using (true);
--
-- create policy "auth write" on markets          for all using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');
-- create policy "auth write" on meals            for all using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');
-- create policy "auth write" on meal_ingredients for all using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');
-- create policy "auth write" on prices           for all using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');
--
-- Note: turning RLS on without adding a sign-in flow to the app will make
-- every write fail. Do one then the other.
