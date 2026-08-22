-- SolarOps: Monthly payroll history
-- Run this once in Supabase Dashboard -> SQL Editor before using the Payroll page.

create table if not exists payroll_records (
  id bigint generated always as identity primary key,
  crew_id bigint not null references crew(id) on delete cascade,
  pay_period date not null,
  amount numeric not null default 0,
  status text not null default 'pending' check (status in ('pending','paid')),
  notes text,
  paid_at timestamptz,
  updated_by_device_id text,
  updated_by_device_name text,
  updated_at timestamptz not null default now(),
  unique (crew_id, pay_period)
);

alter table payroll_records enable row level security;

create policy "authenticated full access" on payroll_records for all
  using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');

grant select, insert, update, delete on public.payroll_records to anon, authenticated;
grant usage, select on all sequences in schema public to anon, authenticated;
