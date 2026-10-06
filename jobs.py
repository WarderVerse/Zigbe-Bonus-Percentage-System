"""The two scheduled calculations (spec section 3). Both are IDEMPOTENT:
running them twice on the same day never duplicates or changes a locked winner."""
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from .data_source import get_actual_data
from .db import to_kobo
from .logic import last_friday, pick_winner, rank_fcos

_4DP = Decimal("0.0001")  # bonus % is stored with 4 decimal places


def compute_ranking(conn, cfg, year: int, month: int):
    figures = get_actual_data(conn, year, month, cfg)
    return rank_fcos(figures, cfg["MIN_BONUS_PERCENT"], cfg["MIN_DISBURSEMENT"])


def save_snapshot(conn, calc_date: date, ranked) -> None:
    """3A step 6: save daily snapshot (re-running the same day overwrites that day)."""
    with conn:
        conn.executemany(
            """INSERT OR REPLACE INTO daily_bonus_calculation
               (calc_date, fco_id, disbursement_kobo, overdue_kobo, balance_kobo,
                bonus_percentage, qualified, rank) VALUES (?,?,?,?,?,?,?,?)""",
            [(calc_date.isoformat(), r.fco_id, to_kobo(r.disbursement), to_kobo(r.overdue),
              to_kobo(r.balance), str(r.bonus_percent.quantize(_4DP)), int(r.qualified), r.rank)
             for r in ranked])


def lock_month(conn, year: int, month: int, ranked, locked_at: datetime) -> bool:
    """3B: write the official winner (or a 'no winner' row). Returns True if THIS call
    created the lock, False if the month was already locked (nothing is changed)."""
    w = pick_winner(ranked)
    row = (year, month, None, None, None, None, None, locked_at.isoformat())
    if w:
        row = (year, month, w.fco_id, to_kobo(w.disbursement), to_kobo(w.overdue),
               to_kobo(w.balance), str(w.bonus_percent.quantize(_4DP)), locked_at.isoformat())
    with conn:
        cur = conn.execute(
            """INSERT OR IGNORE INTO monthly_winners
               (year, month, fco_id, disbursement_kobo, overdue_kobo, balance_kobo,
                bonus_percentage, locked_at) VALUES (?,?,?,?,?,?,?,?)""", row)
    return cur.rowcount == 1


def run_daily_job(conn, cfg, run_date: date = None, now: datetime = None):
    """Called every day 12:00 WAT. Always snapshots; ALSO locks if today is the
    last Friday of the month, using the figures it has just fetched."""
    tz = ZoneInfo(cfg["TIMEZONE"])
    now = now or datetime.now(tz)
    today = run_date or now.date()
    ranked = compute_ranking(conn, cfg, today.year, today.month)
    save_snapshot(conn, today, ranked)
    locked = False
    if today == last_friday(today.year, today.month):
        locked = lock_month(conn, today.year, today.month, ranked, now)
    return ranked, locked

