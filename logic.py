"""PURE business logic. No database, no Flask, no clock.
Everything here is unit-tested in tests/test_logic.py.  If the business
rules change, this is (almost always) the only file you edit."""
import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

ZERO = Decimal(0)
HUNDRED = Decimal(100)


@dataclass(frozen=True)
class FcoFigures:
    """Raw numbers for one FCO for one month (naira, as Decimal)."""
    fco_id: int
    name: str
    branch: Optional[str]
    disbursement: Decimal   # A. FCO Disbursement Portfolio
    overdue: Decimal        # B. FCO Overdue


@dataclass(frozen=True)
class RankedFco:
    fco_id: int
    name: str
    branch: Optional[str]
    disbursement: Decimal
    overdue: Decimal
    balance: Decimal        # C. Portfolio Balance
    bonus_percent: Decimal  # D. Bonus Percentage (unrounded)
    qualified: bool
    rank: int


def last_friday(year: int, month: int) -> date:
    """Last Friday of the month (the lock day)."""
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    return last_day - timedelta(days=(last_day.weekday() - 4) % 7)  # Mon=0 .. Fri=4


def calculate(disbursement: Decimal, overdue: Decimal) -> Tuple[Decimal, Decimal]:
    """Returns (portfolio_balance, bonus_percent).
    Overdue = 0 -> 100 %.  Disbursement = 0 -> 0 % (avoids divide-by-zero)."""
    balance = disbursement - overdue
    bonus = balance / disbursement * HUNDRED if disbursement > 0 else ZERO
    return balance, bonus


def is_qualified(disbursement: Decimal, bonus: Decimal,
                 min_bonus: Decimal, min_disbursement: Decimal) -> bool:
    """Rule 1 (bonus >= min) AND Rule 2 (disbursement >= min). Both are inclusive."""
    return bonus >= min_bonus and disbursement >= min_disbursement


def disqualification_reasons(disbursement: Decimal, bonus: Decimal,
                             min_bonus: Decimal, min_disbursement: Decimal) -> List[str]:
    reasons = []
    if bonus < min_bonus:
        reasons.append(f"Bonus % below {_plain(min_bonus)}%")
    if disbursement < min_disbursement:
        reasons.append(f"Disbursement below \u20a6{_plain(min_disbursement / 1_000_000)}M")
    return reasons


def rank_fcos(figures: List[FcoFigures], min_bonus: Decimal,
              min_disbursement: Decimal) -> List[RankedFco]:
    """Rank order:
      1. qualified FCOs first, then unqualified;
      2. higher Bonus % first;
      3. TIE-BREAK (spec edge case 1): higher Disbursement first;
      4. name A-Z (only so the order is deterministic).
    Rank 1 therefore is the Current Leader whenever anyone is qualified."""
    rows = []
    for f in figures:
        balance, bonus = calculate(f.disbursement, f.overdue)
        q = is_qualified(f.disbursement, bonus, min_bonus, min_disbursement)
        rows.append((f, balance, bonus, q))
    rows.sort(key=lambda r: (not r[3], -r[2], -r[0].disbursement, r[0].name.lower()))
    return [RankedFco(f.fco_id, f.name, f.branch, f.disbursement, f.overdue,
                      balance, bonus, q, i)
            for i, (f, balance, bonus, q) in enumerate(rows, start=1)]


def pick_winner(ranked: List[RankedFco]) -> Optional[RankedFco]:
    """Exactly ONE winner: the top qualified FCO, or None."""
    return next((r for r in ranked if r.qualified), None)


def round2(x: Decimal) -> float:
    return float(x.quantize(Decimal("0.01")))


def _plain(d: Decimal) -> str:
    return format(Decimal(d).normalize(), "f")
