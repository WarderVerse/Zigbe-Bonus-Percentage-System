"""Where the 'actual data' comes from (spec section 1: Disbursement + Overdue).

Contract: a source is a function  (conn, year, month, cfg) -> list[FcoFigures].
Register it in SOURCES and select it with DATA_SOURCE=<key> in .env.
To connect Zigbe's real loan system, add a function here (see README section 9)."""
from typing import List

from .db import from_kobo
from .logic import FcoFigures


def _month_bounds(year: int, month: int):
    start = f"{year:04d}-{month:02d}-01"
    ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
    return start, f"{ny:04d}-{nm:02d}-01"


def local_source(conn, year: int, month: int, cfg) -> List[FcoFigures]:
    """Reads the app's own `loans` table.
    Disbursement = sum of loans disbursed in the month.
    Overdue      = sum of overdue amounts ON THOSE SAME loans (spec: 'from that portfolio')."""
    start, end = _month_bounds(year, month)
    rows = conn.execute(
        """SELECT f.id, f.name, f.branch,
                  COALESCE(SUM(l.amount_kobo), 0)  AS disb,
                  COALESCE(SUM(l.overdue_kobo), 0) AS overdue
           FROM fcos f
           LEFT JOIN loans l ON l.fco_id = f.id
                            AND l.disbursed_on >= ? AND l.disbursed_on < ?
           WHERE f.status = 'active'
           GROUP BY f.id ORDER BY f.id""", (start, end)).fetchall()
    return [FcoFigures(r["id"], r["name"], r["branch"],
                       from_kobo(r["disb"]), from_kobo(r["overdue"])) for r in rows]


SOURCES = {"local": local_source}


def get_actual_data(conn, year: int, month: int, cfg) -> List[FcoFigures]:
    key = cfg["DATA_SOURCE"]
    if key not in SOURCES:
        raise RuntimeError(f"Unknown DATA_SOURCE '{key}'. Known: {sorted(SOURCES)}")
    return SOURCES[key](conn, year, month, cfg)
