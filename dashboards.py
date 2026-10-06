"""Builds the JSON for the two dashboards (spec section 4).
Dashboards READ THE SAVED 12PM SNAPSHOT - they do not recalculate on page load."""
from datetime import datetime
from zoneinfo import ZoneInfo

from .db import from_kobo
from .logic import disqualification_reasons, last_friday, round2
from decimal import Decimal

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def _snapshot(conn, year, month):
    start = f"{year:04d}-{month:02d}-01"
    ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
    end = f"{ny:04d}-{nm:02d}-01"
    d = conn.execute("""SELECT MAX(calc_date) AS d FROM daily_bonus_calculation
                        WHERE calc_date >= ? AND calc_date < ?""", (start, end)).fetchone()["d"]
    if not d:
        return None, []
    rows = conn.execute(
        """SELECT b.*, f.name, f.branch FROM daily_bonus_calculation b
           JOIN fcos f ON f.id = b.fco_id WHERE b.calc_date = ? ORDER BY b.rank""", (d,)).fetchall()
    return d, rows


def _row_json(r, cfg):
    disb, bonus = from_kobo(r["disbursement_kobo"]), Decimal(r["bonus_percentage"])
    return {
        "rank": r["rank"], "fco_id": r["fco_id"], "name": r["name"], "branch": r["branch"],
        "disbursement": float(disb), "overdue": float(from_kobo(r["overdue_kobo"])),
        "balance": float(from_kobo(r["balance_kobo"])), "bonus_percent": round2(bonus),
        "qualified": bool(r["qualified"]),
        "reasons": [] if r["qualified"] else disqualification_reasons(
            disb, bonus, cfg["MIN_BONUS_PERCENT"], cfg["MIN_DISBURSEMENT"]),
    }


def _winner_json(w):
    if w is None:
        return None
    out = {"year": w["year"], "month": w["month"], "label": f'{MONTHS[w["month"] - 1]} {w["year"]}',
           "locked_at": w["locked_at"], "no_winner": w["fco_id"] is None}
    if w["fco_id"] is not None:
        out.update(name=w["name"], bonus_percent=round2(Decimal(w["bonus_percentage"])),
                   disbursement=float(from_kobo(w["disbursement_kobo"])))
    return out


def _context(conn, cfg):
    now = datetime.now(ZoneInfo(cfg["TIMEZONE"]))
    y, m = now.year, now.month
    snap_date, rows = _snapshot(conn, y, m)
    lock_day = last_friday(y, m)
    deadline = datetime(y, m, lock_day.day, cfg["CALC_HOUR"], 0, tzinfo=now.tzinfo)
    cur = conn.execute("""SELECT w.*, f.name FROM monthly_winners w
                          LEFT JOIN fcos f ON f.id = w.fco_id WHERE w.year=? AND w.month=?""",
                       (y, m)).fetchone()
    last = conn.execute("""SELECT w.*, f.name FROM monthly_winners w
                           LEFT JOIN fcos f ON f.id = w.fco_id
                           WHERE (w.year * 100 + w.month) < ?
                           ORDER BY w.year DESC, w.month DESC LIMIT 1""", (y * 100 + m,)).fetchone()
    return {
        "company": cfg["COMPANY_NAME"],
        "period": {"year": y, "month": m, "label": f"{MONTHS[m - 1]} {y}"},
        "snapshot_date": snap_date,
        "deadline": {"iso": deadline.isoformat(),
                     "label": deadline.strftime("%A %d %B %Y, %I:%M %p WAT").replace(" 0", " ")},
        "thresholds": {"min_bonus_percent": float(cfg["MIN_BONUS_PERCENT"]),
                       "min_disbursement": float(cfg["MIN_DISBURSEMENT"])},
        "current_month_lock": _winner_json(cur),
        "last_month_winner": _winner_json(last),
    }, rows


def management_dashboard(conn, cfg):
    ctx, rows = _context(conn, cfg)
    data = [_row_json(r, cfg) for r in rows]
    ctx["rows"] = data
    ctx["leader"] = data[0] if data and data[0]["qualified"] else None
    return ctx


def fco_dashboard(conn, cfg, fco_id):
    """Data minimisation: an FCO receives ONLY their own row plus the leader's name and %."""
    ctx, rows = _context(conn, cfg)
    data = [_row_json(r, cfg) for r in rows]
    mine = next((r for r in data if r["fco_id"] == fco_id), None)
    leader = data[0] if data and data[0]["qualified"] else None
    ctx["me"] = mine
    ctx["total_fcos"] = len(data)
    ctx["leader"] = None if leader is None else {
        "name": leader["name"], "bonus_percent": leader["bonus_percent"],
        "is_me": leader["fco_id"] == fco_id,
        "gap": 0 if leader["fco_id"] == fco_id or mine is None
        else round(leader["bonus_percent"] - mine["bonus_percent"], 2)}
    return ctx
