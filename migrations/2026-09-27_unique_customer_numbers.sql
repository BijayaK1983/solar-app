-- SolarOps: Unique application & work order numbers
-- Run once in Supabase Dashboard -> SQL Editor.
-- Stops two devices from saving the same Application No. or Work Order No.
-- (Matching ignores upper/lower case and surrounding spaces; blank numbers are allowed
-- on any number of customers.) The app version that handles these errors can be
-- deployed before or after this migration.

-- STEP 1 — Check for duplicates that already exist. This must return NO rows.
-- If it returns rows, edit those customers in the app so each number is unique,
-- then run this check again.
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

-- STEP 2 — Add the unique indexes (run after step 1 comes back empty).
create unique index if not exists customers_app_no_unique
  on customers (upper(btrim(app_no)))
  where coalesce(btrim(app_no), '') <> '';

create unique index if not exists customers_work_order_no_unique
  on customers (upper(btrim(work_order_no)))
  where coalesce(btrim(work_order_no), '') <> '';
