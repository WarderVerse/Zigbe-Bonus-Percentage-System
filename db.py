"""SQLite access + schema. Money is stored as INTEGER kobo (1 naira = 100 kobo)
so there are never floating-point errors. Percentages are stored as TEXT
(a Decimal string) for the same reason."""
import sqlite3
from decimal import Decimal, ROUND_HALF_UP

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS fcos (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL UNIQUE,
    branch  TEXT,
    status  TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive'))
);
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('management','fco')),
    fco_id        INTEGER REFERENCES fcos(id)
);
-- Used by DATA_SOURCE=local. Replace/extend for your real core system (see README).
CREATE TABLE IF NOT EXISTS loans (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    reference    TEXT UNIQUE,
    fco_id       INTEGER NOT NULL REFERENCES fcos(id),
    amount_kobo  INTEGER NOT NULL CHECK (amount_kobo >= 0),
    overdue_kobo INTEGER NOT NULL DEFAULT 0 CHECK (overdue_kobo >= 0),
    disbursed_on TEXT NOT NULL            -- ISO date YYYY-MM-DD
);
CREATE INDEX IF NOT EXISTS idx_loans_fco_date ON loans (fco_id, disbursed_on);

CREATE TABLE IF NOT EXISTS daily_bonus_calculation (
    calc_date         TEXT    NOT NULL,   -- ISO date (WAT) the 12PM job ran
    fco_id            INTEGER NOT NULL REFERENCES fcos(id),
    disbursement_kobo INTEGER NOT NULL,
    overdue_kobo      INTEGER NOT NULL,
    balance_kobo      INTEGER NOT NULL,
    bonus_percentage  TEXT    NOT NULL,   -- Decimal string, 4 dp
    qualified         INTEGER NOT NULL,   -- 0/1
    rank              INTEGER NOT NULL,
    PRIMARY KEY (calc_date, fco_id)
);
CREATE TABLE IF NOT EXISTS monthly_winners (
    year              INTEGER NOT NULL,
    month             INTEGER NOT NULL,
    fco_id            INTEGER REFERENCES fcos(id),   -- NULL = nobody qualified
    disbursement_kobo INTEGER,
    overdue_kobo      INTEGER,
    balance_kobo      INTEGER,
    bonus_percentage  TEXT,
    locked_at         TEXT NOT NULL,                 -- ISO timestamp with +01:00
    PRIMARY KEY (year, month)                        -- one lock per month, ever
);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def get_db() -> sqlite3.Connection:
    """One connection per web request."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_PATH"])
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def to_kobo(naira: Decimal) -> int:
    return int((Decimal(naira) * 100).to_integral_value(rounding=ROUND_HALF_UP))


def from_kobo(kobo: int) -> Decimal:
    return Decimal(int(kobo)) / Decimal(100)
