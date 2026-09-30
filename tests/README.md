# SolarOps — offline save tests

Tests the "Add / Edit Customer" save flow in `../solar_business_app.html`
without touching the real Supabase database. `fake-supabase.js` stands in for the
Supabase client: an in-memory database with the same unique rules as the
`2026-09-27_unique_customer_numbers.sql` migration, plus switches to simulate an
expired login (`__expired`), a failed login refresh (`__refreshFails`) and a network
failure (`__throw`).

## Run

```
cd tests
pip3 install playwright && python3 -m playwright install chromium   # first time only
npm i @supabase/supabase-js@2                                        # first time only (login tests)
python3 test_save_customer.py
python3 test_login.py
python3 test_crew_codes.py
```

## What it checks

| # | Scenario | Expected |
|---|---|---|
| 1 | Normal add | Saved, form closes |
| 2 | Login expired, refresh works | Login refreshed, saved |
| 3 | Login expired, refresh fails | Red message: log out and sign in again |
| 4 | Network down | Red message: check the internet connection |
| 5 | Hand-typed duplicate application no. | Red message: already used by another customer |
| 6 | Auto number taken by another device | Saved with the next free number, user told which |
| 7 | Double submit | Only one save |
| 8 | Edit a customer | Change saved |
| 9 | Edit fails | On-screen data left unchanged, red message |

`test_crew_codes.py` checks crew employee codes (E001…/W001…, duplicates, edit, migration not yet run).
`test_login.py` checks the login screen: normal login, the main library download blocked
(falls back to a second download site), both blocked (clear message instead of a frozen
screen), and the database unreachable (clear message).
`app_under_test.html` is generated on each run and can be deleted.
