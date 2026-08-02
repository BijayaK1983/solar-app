-- SolarOps: Inventory upgrade migration
-- Run this once in Supabase Dashboard -> SQL Editor, BEFORE deploying the updated
-- solar_business_app.html (the new code expects these columns/table to exist).

-- 1. Inventory: supplier + purchase-order (reorder) tracking
alter table inventory
  add column if not exists supplier text,
  add column if not exists supplier_phone text,
  add column if not exists on_order_qty int,
  add column if not exists on_order_date date;

-- 2. Stock movement history (every manual adjust, receive, and auto-deduct)
create table if not exists inventory_movements (
  id bigint generated always as identity primary key,
  inventory_id bigint references inventory(id) on delete cascade,
  change_qty int not null,
  reason text,
  customer_id bigint references customers(id) on delete set null,
  updated_by_device_id text,
  updated_by_device_name text,
  created_at timestamptz not null default now()
);

alter table inventory_movements enable row level security;

create policy "authenticated full access" on inventory_movements for all
  using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');

grant select, insert, update, delete on public.inventory_movements to anon, authenticated;
grant usage, select on all sequences in schema public to anon, authenticated;

-- 3. Bill of Materials per category (drives auto-deduct on installation completion)
alter table app_settings
  add column if not exists category_bom jsonb not null default '{"1KW":[],"3KW":[],"5KW":[]}'::jsonb;

-- 4. Prevent double stock-deduction if an assignment's status is toggled back and forth
alter table assignments
  add column if not exists stock_deducted boolean not null default false;
