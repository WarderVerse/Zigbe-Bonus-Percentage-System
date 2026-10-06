"""Command-line tools:  flask --app run <command>   (see README section 8)."""
import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import click
from flask import current_app
from werkzeug.security import generate_password_hash

from .db import connect, to_kobo
from .jobs import run_daily_job, save_snapshot  # noqa: F401


def _conn():
    return connect(current_app.config["DATABASE_PATH"])


def register_cli(app):
    @app.cli.command("add-fco")
    @click.argument("name")
    @click.option("--branch", default=None)
    def add_fco(name, branch):
        """Add a Field Credit Officer."""
        c = _conn()
        with c:
            c.execute("INSERT INTO fcos (name, branch) VALUES (?, ?)", (name, branch))
        click.echo(f"Added FCO {name}")

    @app.cli.command("create-user")
    @click.argument("username")
    @click.option("--role", type=click.Choice(["management", "fco"]), required=True)
    @click.option("--fco-name", default=None, help="Required for role=fco")
    @click.password_option()
    def create_user(username, role, fco_name, password):
        """Create a login. FCO users must be linked to an FCO by name."""
        c = _conn()
        fco_id = None
        if role == "fco":
            row = c.execute("SELECT id FROM fcos WHERE name = ?", (fco_name,)).fetchone()
            if not row:
                raise click.ClickException(f"No FCO named '{fco_name}'. Run add-fco first.")
            fco_id = row["id"]
        with c:
            c.execute("INSERT INTO users (username, password_hash, role, fco_id) VALUES (?,?,?,?)",
                      (username.strip().lower(), generate_password_hash(password), role, fco_id))
        click.echo(f"Created {role} user {username}")

    @app.cli.command("import-loans")
    @click.argument("csv_path", type=click.Path(exists=True))
    def import_loans(csv_path):
        """Import/refresh loans from CSV. Columns: reference,fco_name,amount,overdue,disbursed_on
        (amounts in naira, date as YYYY-MM-DD). Re-importing the same reference UPDATES it."""
        c = _conn()
        n = 0
        with c, open(csv_path, newline="", encoding="utf-8-sig") as fh:
            for i, r in enumerate(csv.DictReader(fh), start=2):
                try:
                    fco = c.execute("SELECT id FROM fcos WHERE name = ?", (r["fco_name"].strip(),)).fetchone()
                    if not fco:
                        raise ValueError(f"unknown FCO '{r['fco_name']}'")
                    amount, overdue = Decimal(r["amount"]), Decimal(r.get("overdue") or 0)
                    date.fromisoformat(r["disbursed_on"])
                    if overdue > amount or amount < 0 or overdue < 0:
                        raise ValueError("overdue must be between 0 and amount")
                except (ValueError, InvalidOperation, KeyError) as e:
                    raise click.ClickException(f"Row {i}: {e}. Nothing was imported.")
                c.execute("""INSERT INTO loans (reference, fco_id, amount_kobo, overdue_kobo, disbursed_on)
                             VALUES (?,?,?,?,?)
                             ON CONFLICT(reference) DO UPDATE SET fco_id=excluded.fco_id,
                               amount_kobo=excluded.amount_kobo, overdue_kobo=excluded.overdue_kobo,
                               disbursed_on=excluded.disbursed_on""",
                          (r["reference"], fco["id"], to_kobo(amount), to_kobo(overdue), r["disbursed_on"]))
                n += 1
        click.echo(f"Imported {n} loans")

    @app.cli.command("run-daily-job")
    @click.option("--date", "on", default=None, help="YYYY-MM-DD (default: today in WAT)")
    def run_job(on):
        """Run the 12PM job now (same code the scheduler/cron runs)."""
        run_date = date.fromisoformat(on) if on else None
        ranked, locked = run_daily_job(_conn(), current_app.config, run_date=run_date)
        click.echo(f"Ranked {len(ranked)} FCOs. Month locked by this run: {locked}")

    @app.cli.command("seed-demo")
    def seed_demo():
        """Load demo FCOs, loans, logins and a past winner. DEV ONLY."""
        c = _conn()
        if c.execute("SELECT COUNT(*) AS n FROM fcos").fetchone()["n"]:
            raise click.ClickException("Database already has FCOs; refusing to seed.")
        now = datetime.now(ZoneInfo(current_app.config["TIMEZONE"]))
        first = date(now.year, now.month, 1).isoformat()
        demo = [("Ayo", "Port Harcourt", 25_000_000, 1_500_000), ("Blessing", "Lagos", 22_000_000, 2_000_000),
                ("Emeka", "Enugu", 18_000_000, 1_000_000), ("Chidi", "Abuja", 30_000_000, 6_000_000),
                ("Funke", "Ibadan", 21_000_000, 2_500_000)]
        pw = generate_password_hash("DemoPass123!")
        with c:
            for name, branch, disb, over in demo:
                fid = c.execute("INSERT INTO fcos (name, branch) VALUES (?,?)", (name, branch)).lastrowid
                for k in range(5):  # 5 equal loans; all overdue sits on the first one
                    c.execute("INSERT INTO loans (reference, fco_id, amount_kobo, overdue_kobo, disbursed_on) "
                              "VALUES (?,?,?,?,?)", (f"DEMO-{name}-{k}", fid, to_kobo(Decimal(disb) / 5),
                                                    to_kobo(Decimal(over)) if k == 0 else 0, first))
                if name in ("Ayo", "Blessing"):
                    c.execute("INSERT INTO users (username, password_hash, role, fco_id) VALUES (?,?,?,?)",
                              (name.lower(), pw, "fco", fid))
            c.execute("INSERT INTO users (username, password_hash, role) VALUES ('manager', ?, 'management')", (pw,))
            py, pm = (now.year - 1, 12) if now.month == 1 else (now.year, now.month - 1)
            bl = c.execute("SELECT id FROM fcos WHERE name='Blessing'").fetchone()["id"]
            c.execute("""INSERT INTO monthly_winners VALUES (?,?,?,?,?,?,?,?)""",
                      (py, pm, bl, to_kobo(Decimal(24_000_000)), to_kobo(Decimal(1_800_000)),
                       to_kobo(Decimal(22_200_000)), "92.5000", now.isoformat()))
        run_daily_job(c, current_app.config)
        click.echo("Demo loaded. Logins (password DemoPass123!): manager, ayo, blessing")
