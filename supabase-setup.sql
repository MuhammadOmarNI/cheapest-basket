-- ===========================================================================
--  Cheapest Basket — run this ONCE in Supabase.
--
--  Left sidebar -> SQL Editor -> New query -> paste all of this -> Run.
--
--  One row per person. Which row is yours is decided by Supabase itself: you
--  sign in, it hands your browser a token, and the rules below only let that
--  token touch the row carrying your own user id. Nothing in the app code
--  picks the row, so nothing in the app code can get it wrong.
--
--  Why one table and not four? Every calculation in this app already happens
--  in the browser — nothing asks the database to join or filter anything. So
--  splitting it into meals / ingredients / prices tables would add work on
--  both sides without buying anything.
-- ===========================================================================

drop table if exists baskets;

create table baskets (
  user_id     uuid primary key references auth.users(id) on delete cascade,
  data        jsonb not null,          -- the whole app, as JSON
  updated_at  timestamptz not null default now()
);

-- Row Level Security decides who may touch which rows. Without this line the
-- policies below are never consulted.
alter table baskets enable row level security;

-- auth.uid() is whoever is holding the token that made the request.
-- No token, no match, no row — not even an empty one.
create policy "own row read"   on baskets for select using (auth.uid() = user_id);
create policy "own row insert" on baskets for insert with check (auth.uid() = user_id);
create policy "own row update" on baskets for update using (auth.uid() = user_id);
create policy "own row delete" on baskets for delete using (auth.uid() = user_id);

-- Keep updated_at honest, so you can always tell which device saved last.
create or replace function touch_updated_at() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists baskets_touch on baskets;
create trigger baskets_touch before update on baskets
  for each row execute function touch_updated_at();
