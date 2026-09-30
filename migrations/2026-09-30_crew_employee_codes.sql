-- SolarOps: Employee codes for crew
-- Run once in Supabase Dashboard -> SQL Editor.
-- Adds a category (Staff / Workman) and an employee code to each crew member.
-- Staff codes are E001, E002 ...; Workman codes are W001, W002 ... — the app
-- generates the next one when a category is chosen. Existing crew keep a blank
-- code until you edit them in the app and pick their category.

alter table crew
  add column if not exists emp_category text,
  add column if not exists emp_code text;

alter table crew drop constraint if exists crew_emp_category_check;
alter table crew add constraint crew_emp_category_check
  check (emp_category is null or emp_category in ('Staff', 'Workman'));

-- No two crew members can share a code (ignores upper/lower case and spaces;
-- blank codes are allowed).
create unique index if not exists crew_emp_code_unique
  on crew (upper(btrim(emp_code)))
  where coalesce(btrim(emp_code), '') <> '';
