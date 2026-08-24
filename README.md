# SolarOps — Installation Business Manager

A single-page web app for running a solar installation business: customer pipeline,
task/team assignment, inventory, crew & payments, and settings. Live at:

`https://bijayak1983.github.io/solar-app/solar_business_app.html`

This doc is for anyone working on the **code**. For deployment access, credentials,
and infra ops (GitHub, Supabase dashboards, database password, etc.), see
`PROJECT_DOCUMENTATION.md` — that file is intentionally git-ignored and not in this
repo; ask the project owner for it directly if you need infra access.

## Tech stack

- **No build step.** Everything is one file: `solar_business_app.html` (HTML + CSS
  + JS inline). Open it in a browser or serve it statically — that's the whole app.
- **Backend**: [Supabase](https://supabase.com) (hosted Postgres) via the
  `@supabase/supabase-js` client, loaded from a CDN `<script>` tag — no npm/node
  involved anywhere in this project.
- **Auth**: one shared login for the whole team (Supabase Auth, email/password),
  not per-user accounts.
- **Hosting**: static file hosting on GitHub Pages, deployed via `git push`.
- **PWA**: `manifest.json` + `sw.js` let it be "installed" to a phone/laptop home
  screen with an offline-capable app shell (the data itself still needs network,
  since it lives in Supabase).

## File map

| File | What it is |
|---|---|
| `solar_business_app.html` | The entire app |
| `manifest.json` | PWA manifest — name, icons, colors |
| `sw.js` | Service worker — caches the static shell only (explicitly ignores Supabase API calls, see comments in the fetch handler) |
| `icon-192.png`, `icon-512.png` | App icons |
| `.claude/launch.json` | Local dev server config (`python3 -m http.server 8934`) |

## Code structure inside `solar_business_app.html`

The `<script>` block is organized top-to-bottom as:

1. **Supabase client setup** — `SUPABASE_URL`, `SUPABASE_ANON_KEY` (safe to be
   public — access is enforced by Row Level Security server-side, not by hiding
   this key), and `sb`, the client instance used everywhere below.
2. **`STAGES`** — the 11-step customer pipeline (Lead → ... → Grid Connected),
   each with a `key` (used as a property name in `stageDates`) and a display
   `label`. `STAGE_COLORS` is a parallel array of hex colors for the funnel
   chart/progress dots.
3. **In-memory state** — `customers`, `teams`, `inventory`, `crewList`,
   `assignments`, `categoryPrices` are plain arrays/objects, all loaded fresh
   from Supabase on login (`loadAllData()`) and mutated directly by the UI code.
   There's no framework/virtual DOM — every mutation calls a `render*()` function
   that rebuilds the relevant `innerHTML` from scratch.
4. **Device identity** — `getDeviceId()` / `getDeviceName()` read/write two
   `localStorage` keys unique to that browser. `deviceStamp()` bundles those plus
   a timestamp, spread into every Supabase insert/update so rows carry
   `updated_by_device_id` / `updated_by_device_name`.
5. **Row ↔ object mappers** — `rowTo*()` and `*ToRow()` pairs convert between
   Supabase's `snake_case` columns and the app's `camelCase` JS objects (e.g.
   `rowToCustomer` / `customerToRow`). Any time you add a field to a table, it
   needs to be added to both directions here or it'll silently vanish.
6. **Auth flow** — `initAuth()` checks for an existing Supabase session on load;
   `handleLogin()` / `handleLogout()` manage the shared login; `onAuthenticated()`
   is the single entry point that loads data, renders everything, and subscribes
   to realtime updates.
7. **Realtime sync** — `subscribeRealtime()` listens to Postgres change events on
   all six tables. `handleRemoteChange()` debounces (300ms) and skips the event
   if it was caused by this same device (via `updated_by_device_id`), then does a
   full `loadAllData()` + re-render on anything else. This is a blunt "just
   refetch everything" strategy — fine at this data scale, not something to
   over-optimize prematurely.
8. **Per-tab sections** (Pipeline, Task Assignment, Teams, Inventory, Crew,
   Settings) — each has the same shape: a `render*()` function that rebuilds a
   `<tbody>`/container from the in-memory array, and `save*()`/`delete*()`
   functions that are `async`, write to Supabase first, update the local array
   from the result, then call the relevant `render*()` calls. **Pattern to
   follow when adding a new mutation**: write to Supabase → on success, patch
   the local array → re-render. Don't render optimistically before the write
   succeeds; several `save*` functions `return` early with an `alert()` if
   Supabase returns an error, leaving state untouched.
9. **Dashboard** — `renderDashboard()` derives all stats (revenue, funnel counts,
   "needs attention" list) from the in-memory arrays each time it's called; there's
   no separate aggregation table, it's all computed client-side on every render.

## Business logic worth knowing before you touch it

- **Pipeline stages**: a customer's progress is just an index (`stageIndex`) into
  `STAGES`. `stageDates` is a `{stageKey: "YYYY-MM-DD"}` map recording when each
  stage was first reached — `advanceStage()`/`jumpStage()` only set a date if one
  isn't already recorded, so re-visiting a stage doesn't overwrite history.
- **Task Assignment's three linked dropdowns**: Customer / Application No. / Work
  Order No. are three different *labels* for selecting the same customer. Changing
  any one calls `onAssignIdentifierChange()`, which syncs the other two selects to
  the same underlying customer ID and reloads the form via
  `loadAssignFormForCustomer()`.
- **Team matching**: `buildTeamOptions()` sorts teams by current active workload
  (`teamWorkload()` — assignments not yet `Completed`) and puts teams whose `zone`
  text-matches the customer's `city` first (marked with a ★). It's a simple
  substring match (`cityMatch()`), not geocoding.
- **Completing an assignment auto-advances the pipeline**: `cycleAssignmentStatus()`
  bumps a customer to the "Installation Completed" stage if they're not already
  past it, when their assignment status is set to `Completed`.

## Local development

```bash
python3 -m http.server 8934
```

Open `http://localhost:8934/solar_business_app.html`. Login/database features work
identically to production — Supabase treats `localhost` as a normal origin. There's
no build/watch step; just edit the HTML file and reload the browser.

## Deploying

```bash
git add solar_business_app.html manifest.json sw.js icon-192.png icon-512.png
git commit -m "describe the change"
git push origin main
```

GitHub Pages rebuilds automatically from `main`, usually live within ~1 minute.
Whoever's SSH key is set up for this repo can push directly — see
`PROJECT_DOCUMENTATION.md` (not in this repo) for the deploy-access setup.

## Database schema

Six Supabase/Postgres tables: `customers`, `teams`, `inventory`, `crew`,
`assignments`, `app_settings`. All are behind Row Level Security — only an
authenticated session (i.e. someone who's logged into the app) can read or write
any of them. The full `CREATE TABLE` / RLS policy SQL is kept in
`PROJECT_DOCUMENTATION.md` alongside the credentials needed to run it, since
rebuilding the schema and accessing the project are the same permission level.

## Known simplifications (not bugs, just current scope)

- One shared login for the whole team — no per-user accounts or permissions.
  Device name/ID stamping (see above) is the only "who did this" trail.
- No pagination — every table loads and renders its full contents on every login
  and every realtime change. Fine at small-business scale; would need revisiting
  well before thousands of rows.
- No form validation beyond "name is required" on a couple of modals.
