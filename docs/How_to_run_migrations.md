# How to run a SolarOps database migration

Migrations are the SQL files in `Solar Ops/migrations/`. Each is run **once**, in date order,
in the Supabase SQL Editor.

1. Open https://supabase.com/dashboard/project/ddrvhfbcqobkscaanfqw/sql/new (signed in to Supabase).
2. Open the migration file, copy the SQL for the step, paste it into the editor, click **Run** (Cmd + Enter).
3. Read the result before moving to the next step.

## 2026-09-30_crew_employee_codes.sql

One step: open the file, copy all of it, paste into the SQL Editor, click **Run**. Expect *"Success. No rows returned"*. Existing crew keep a blank code until you edit them in the app (✎) and choose Staff or Workman.

## 2026-09-27_unique_customer_numbers.sql

**Step 1 — check for duplicates.** Must return *"Success. No rows returned"*. If it lists rows,
edit those customers in the app so every number is unique, then run it again.

```sql
select 'Application No.' as field, upper(btrim(app_no)) as number, count(*) as times_used,
       array_agg(name order by id) as customers
from customers
where coalesce(btrim(app_no), '') <> ''
group by 1, 2 having count(*) > 1
union all
select 'Work Order No.', upper(btrim(work_order_no)), count(*),
       array_agg(name order by id)
from customers
where coalesce(btrim(work_order_no), '') <> ''
group by 1, 2 having count(*) > 1;
```

**Step 2 — add the protection.**

```sql
create unique index if not exists customers_app_no_unique
  on customers (upper(btrim(app_no)))
  where coalesce(btrim(app_no), '') <> '';

create unique index if not exists customers_work_order_no_unique
  on customers (upper(btrim(work_order_no)))
  where coalesce(btrim(work_order_no), '') <> '';
```

**Undo (only if ever needed):**

```sql
drop index if exists customers_app_no_unique;
drop index if exists customers_work_order_no_unique;
```
