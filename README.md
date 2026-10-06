# FCO Bonus System — Zigbe Nigeria Limited

A small web app that ranks Field Credit Officers (FCOs) every day, shows two dashboards
(Management and FCO), and locks **one official bonus winner per month** on the last Friday at 12:00 PM WAT.

Stack: **Python 3.10+ / Flask**, **SQLite**, **plain HTML + CSS + JavaScript** (no frameworks, no CDNs, works offline).

Source of the rules: *"FCO BONUS SYSTEM – FULL BUSINESS LOGIC V2.0 FINAL"*. Section numbers below refer to that document.

---

## 1. The rules in one minute

For each FCO, for the current calendar month:

| Term | Meaning |
|---|---|
| **Disbursement Portfolio** | Total loans the FCO disbursed this month |
| **Overdue** | Overdue amount on *those same loans* |
| **Portfolio Balance** | Disbursement − Overdue |
| **Bonus %** | Balance ÷ Disbursement × 100 (Overdue 0 → 100 %; Disbursement 0 → 0 %) |

An FCO is **qualified** only if **Bonus % ≥ 85** *and* **Disbursement ≥ ₦20,000,000** (both inclusive).
**Only one winner:** the qualified FCO with the highest Bonus %. Tie → higher Disbursement wins.
If nobody qualifies: no winner, no bonus.

Two calculations (all times **WAT / Africa/Lagos**):

1. **Daily, 12:00 PM, 7 days a week** – recompute everyone, rank, save a snapshot. Dashboards show this snapshot.
2. **Last Friday of the month, 12:00 PM** – freeze the result and save the official winner to `monthly_winners`.
   Holidays do not matter; it is automatic. A locked month can never be changed by the app.

---

## 2. Decisions made where the document was unclear (read this!)

These were judgement calls. Confirm them with the MD; each is a small change (section 12).

| # | Situation in the document | What the code does |
|---|---|---|
| 1 | Section 3A says "rank by Bonus % DESC", but the section 4 example puts Emeka (94.4 %, *not qualified*) at rank 3 below Blessing (90.9 %). Both cannot be literally true. | **Qualified FCOs rank first** (by Bonus %, tie → Disbursement), **then** unqualified FCOs. This reproduces the example table exactly, and means *rank 1 = Current Leader* whenever anyone qualifies. |
| 2 | "Current Leader" when nobody is qualified | Shows "No qualified leader yet". |
| 3 | Which loans count for a month | Loans whose `disbursed_on` date falls in that calendar month. |
| 4 | "Overdue" changes daily | It is read **as at calculation time**. The lock uses the figures fetched at that moment on lock day. |
| 5 | Dashboard timing | Dashboards read the **saved 12 PM snapshot**; they do not recalculate on page load. On the 1st of a month before 12 PM there is no snapshot yet, so the page says so. |
| 6 | Between the lock and month-end | Daily snapshots continue, but a banner shows the locked winner and it never changes. |
| 7 | "Last Month Winner" | The most recent locked month *before* the current one. A "no winner" month is shown as such. |
| 8 | FCO dashboard "Leader box" | An FCO gets the leader's **name and Bonus % only** (never the leader's disbursement or overdue). Enforced on the server, not just hidden in the page. |
| 9 | Exact tie on Bonus % **and** Disbursement | Alphabetical by name (only to make the result stable). The document does not cover this. |
| 10 | Rounding | Comparisons use the **unrounded** value; screens show 2 decimals. Money is stored in kobo (integers), never floats. |
| 11 | Inactive FCOs (`status='inactive'`) | Excluded from ranking. |

---

## 3. Folder map

```
fco-bonus-system/
├── README.md              <- you are here
├── run.py                 Dev server entry point (python run.py)
├── config.py              Reads .env -> settings (thresholds, timezone, ...)
├── requirements.txt       Python packages
├── .env.example           Copy to .env
├── app/
│   ├── __init__.py        App factory, security headers, starts the scheduler (optional)
│   ├── logic.py           ★ PURE business rules (formula, qualification, ranking, last Friday)
│   ├── data_source.py     ★ Where "actual data" comes from (swap this for the real core system)
│   ├── jobs.py            The 12 PM daily job + monthly lock (idempotent)
│   ├── dashboards.py      Builds JSON for the two dashboards (reads snapshots)
│   ├── routes.py          URLs: pages + /api/*
│   ├── auth.py            Login guard (roles: management / fco)
│   ├── db.py              SQLite schema + helpers
│   ├── cli.py             `flask` commands (add FCOs, users, import loans, run job, demo seed)
│   ├── templates/         HTML (Jinja2): base, login, management, fco
│   └── static/            css/style.css, js/common.js, login.js, management.js, fco.js
└── tests/                 unittest suite (20 tests)
```

★ = the two files you will touch most.

### How a request flows

```
  12:00 PM WAT (scheduler OR system cron)
        │
        ▼
  jobs.run_daily_job ──► data_source.get_actual_data ──► logic.rank_fcos
        │                                                     │
        ├──► save snapshot  ─────────────► daily_bonus_calculation
        └──► if today = last Friday ─────► monthly_winners (locked once)

  Browser ──► /management or /my-bonus (HTML shell)
          └─► JS calls /api/.../dashboard ──► dashboards.py reads the snapshot tables ──► JSON ──► JS draws the page
```

Design rule: **logic.py knows nothing about the database or Flask.** That keeps the money rules easy to test and change.

---

## 4. Quick start (Ubuntu on WSL + VS Code)

```bash
cd fco-bonus-system
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"   # paste the output as SECRET_KEY in .env

flask --app run seed-demo        # demo FCOs, loans, logins (dev only)
python run.py                    # open http://127.0.0.1:5000
```

Demo logins (password `DemoPass123!`): `manager` (Management view), `ayo` and `blessing` (FCO view).
**Never run `seed-demo` in production** – it creates known passwords.

Run the tests: `SECRET_KEY=x python3 -m unittest discover -s tests -t . -v`

### Working offline
On a machine *with* internet: `pip download -r requirements.txt -d wheels`.
Copy the `wheels/` folder across, then: `pip install --no-index --find-links wheels -r requirements.txt`.
The app itself never calls the internet (system fonts, no CDN).

---

## 5. Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `SECRET_KEY` | *(required)* | Signs login sessions. App refuses to start without it. Keep it secret and stable. |
| `COMPANY_NAME` | Zigbe Nigeria Limited | Shown in the header and page titles |
| `DATABASE_PATH` | `instance/fco_bonus.db` | SQLite file (relative paths are from the project root) |
| `TIMEZONE` | Africa/Lagos | All "12 PM" and "last Friday" maths use this |
| `CALC_HOUR` | 12 | Hour of the daily job / lock |
| `MIN_BONUS_PERCENT` | 85 | Rule 1 |
| `MIN_DISBURSEMENT` | 20000000 | Rule 2 (naira) |
| `DATA_SOURCE` | local | Which function in `data_source.SOURCES` supplies the numbers |
| `ENABLE_SCHEDULER` | 0 | 1 = run the job inside the app process (see section 7) |
| `SESSION_COOKIE_SECURE` | 0 | Set 1 once served over HTTPS |

---

## 6. Database (SQLite)

| Table | Purpose |
|---|---|
| `fcos` | id, name, branch, status (`active`/`inactive`) |
| `users` | Logins. `role` = `management` or `fco`; FCO users link to an `fcos` row |
| `loans` | Used by `DATA_SOURCE=local`: reference, fco_id, amount, overdue, disbursed_on |
| `daily_bonus_calculation` | One row per (date, FCO): disbursement, overdue, balance, bonus %, qualified, rank. Re-running the same day overwrites that day only. |
| `monthly_winners` | One row per (year, month), **primary key prevents a second lock**. `fco_id` is NULL when nobody qualified. `locked_at` is the lock time. |

Money columns end in `_kobo` (₦1 = 100 kobo, stored as integers). Bonus % is a text Decimal such as `94.0000`.
Inspect with: `sqlite3 instance/fco_bonus.db ".tables"`.

---

## 7. Scheduling – the part people get wrong

The job must run **once a day at 12:00 PM WAT**. Pick ONE of these:

**A. Development / single process:** set `ENABLE_SCHEDULER=1` and run `python run.py`. APScheduler fires the job.
It only works while the process is running. With several gunicorn workers it would fire once per worker
(harmless because the job is idempotent, but wasteful) – so don't use it with multiple workers.

**B. Production (recommended): system cron** calling the same code:

```cron
# Lagos has no daylight saving: 12:00 WAT = 11:00 UTC. Use this if the server clock is UTC.
0 11 * * * cd /srv/fco-bonus-system && .venv/bin/flask --app run run-daily-job >> logs/job.log 2>&1
# If the server timezone is already Africa/Lagos, use:  0 12 * * *   (the expression in the document)
```

Check the server time zone with `timedatectl`. Note: cron does not run by default inside WSL – use option A on a WSL laptop.

**If the server was down at 12 PM:** run `flask --app run run-daily-job` as soon as it is back. Be aware this uses the data *as of now*, not as of 12 PM,
and on a lock day it will lock with that later data. Tell the MD if that ever happens. A missed day for a *normal* day just leaves a gap in snapshots (the dashboard shows the latest one).

**Idempotent by design:** running the job twice on one day gives the same snapshot; a locked month is never overwritten (`INSERT OR IGNORE` + primary key).

---

## 8. Command-line tools

Run from the project root with the venv active: `flask --app run <command>`

| Command | What it does |
|---|---|
| `add-fco "Ayo" --branch "Port Harcourt"` | Add an FCO |
| `create-user ayo --role fco --fco-name "Ayo"` | Add a login (prompts for password). Use `--role management` for managers. |
| `import-loans loans.csv` | Load/refresh loans. CSV header: `reference,fco_name,amount,overdue,disbursed_on` (naira, `YYYY-MM-DD`). Same `reference` again = update. The whole file is rejected if any row is bad. |
| `run-daily-job [--date YYYY-MM-DD]` | Run the 12 PM job now |
| `seed-demo` | Demo data (dev only) |

---

## 9. Connecting Zigbe's real loan system

Today the numbers come from the local `loans` table (`local_source` in `app/data_source.py`).
The document says the data lives in a *loan disbursement table* and a *repayment/overdue table*. To use them:

1. Open `app/data_source.py` and write a function with this exact shape:

```python
def core_source(conn, year, month, cfg) -> list[FcoFigures]:
    # query the core system (SQL / API), then return one FcoFigures per ACTIVE FCO:
    # FcoFigures(fco_id, name, branch, disbursement=Decimal(...), overdue=Decimal(...))
```

2. Register it: `SOURCES = {"local": local_source, "core": core_source}`
3. Set `DATA_SOURCE=core` in `.env`.

Rules for the query: sum **only loans disbursed in that month**; overdue must be the overdue on **those same loans**; return `Decimal`, never `float`;
include FCOs with zero disbursement (they appear as 0 %, not qualified). Everything else (ranking, snapshots, lock, dashboards) needs no change.

---

## 10. Security notes

- Passwords are hashed (Werkzeug). Sessions use HttpOnly, SameSite=Lax cookies.
- Access control is **on the server** (`auth.py`): an FCO calling the management API gets 403, and the FCO API returns only their own row plus the leader's name and %.
- The browser code never uses `innerHTML` with server data (prevents XSS). Keep it that way: build nodes with `el()` in `common.js`.
- A Content-Security-Policy (`default-src 'self'`) is set: **no inline `<script>`, no inline `style=""`, no CDN links** – they will be blocked. Put code in `static/js`, styles in `static/css`.
- Before go-live: serve over **HTTPS** (nginx/Caddy in front of gunicorn), set `SESSION_COOKIE_SECURE=1`, back up `instance/fco_bonus.db` daily, and consider login rate limiting (not included).
- Don't commit `.env` or `instance/` (already in `.gitignore`).

Production run example: `gunicorn -w 2 -b 127.0.0.1:8000 run:app` (with `ENABLE_SCHEDULER=0` and cron from section 7).

---

## 11. Testing

`tests/test_logic.py` – formula, thresholds, tie-break, last-Friday dates (including the document's Jan 30, Feb 27, Dec 26 examples).
`tests/test_jobs_and_api.py` – lock happens once, cannot be overwritten, "no winner" row, login required, role separation, FCO data minimisation.

Add a test for every rule change **before** changing code.

---

## 12. How to make common changes

| Change | Where |
|---|---|
| Different thresholds (e.g. 90 %, ₦30M) | `.env` only. No code change. |
| Different tie-break or ranking order | `rank_fcos` sort key in `app/logic.py`, then update `tests/test_logic.py` |
| Lock on a different day/time | `last_friday` in `logic.py` (day), `CALC_HOUR` in `.env` (time) |
| Show a new column on the management table | Add the field in `dashboards._row_json`, add a `<th>` in `management.html`, add a cell in `static/js/management.js` |
| Add another role (e.g. auditor) | `users.role` CHECK in `db.py` (needs a migration), `auth.login_required`, a route + page |
| Show previous months' leaderboards | Snapshots already exist per date in `daily_bonus_calculation`; add a month parameter to `dashboards._snapshot` |

Schema changes: SQLite `CREATE TABLE IF NOT EXISTS` will not alter existing tables. Write a one-off `ALTER TABLE` (or a migration script) and back up the DB first.

---

## 13. Troubleshooting

| Symptom | Likely cause |
|---|---|
| `SECRET_KEY is not set` | You didn't copy `.env.example` to `.env`, or didn't fill it in |
| Dashboard says "No figures yet this month" | The 12 PM job hasn't run this month. Run `flask --app run run-daily-job` |
| Numbers look stale | Job not running. Check cron/log or `ENABLE_SCHEDULER`; the page shows the snapshot date |
| Month wasn't locked | Job didn't run on the last Friday (section 7). Check `SELECT * FROM monthly_winners;` |
| Page loads but is blank / unstyled | Something inline was blocked by the CSP (see browser console) |
| `database is locked` | Another process holds a long write; SQLite is configured with WAL + 30 s timeout. If it is frequent, move to PostgreSQL |
| Wrong time on the lock | Server timezone vs `TIMEZONE`. Lagos = UTC+1 all year |

---

## 14. Known limitations / questions for the MD

1. Section 2 decisions above (especially #1 ranking and #4 overdue timing) need sign-off.
2. No password-reset or user-admin screen – users are created by CLI.
3. SQLite is fine for dozens of FCOs; if many concurrent users or a shared server is needed, migrate to PostgreSQL (SQL here is plain and portable).
4. No audit log of who viewed what, and no email/SMS notification of the winner.
5. The document does not say what happens to loans disbursed *after* the lock but within the same month. They appear in live snapshots but never change the locked winner.
