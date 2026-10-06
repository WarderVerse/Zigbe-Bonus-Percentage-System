import os
import tempfile
import unittest
from datetime import date, datetime
from decimal import Decimal as D
from zoneinfo import ZoneInfo

os.environ.setdefault("SECRET_KEY", "test-secret")

from app import create_app                      # noqa: E402
from app.db import connect, to_kobo             # noqa: E402
from app.jobs import run_daily_job              # noqa: E402


class JobTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({"DATABASE_PATH": os.path.join(self.tmp.name, "t.db"),
                               "TESTING": True, "SECRET_KEY": "x"})
        self.conn = connect(self.app.config["DATABASE_PATH"])

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def add_fco(self, name, disb, over, on="2026-01-05"):
        with self.conn:
            fid = self.conn.execute("INSERT INTO fcos (name) VALUES (?)", (name,)).lastrowid
            self.conn.execute("INSERT INTO loans (fco_id, amount_kobo, overdue_kobo, disbursed_on) "
                              "VALUES (?,?,?,?)", (fid, to_kobo(D(disb)), to_kobo(D(over)), on))

    def test_normal_day_snapshots_but_does_not_lock(self):
        self.add_fco("Ayo", 25_000_000, 1_500_000)
        _, locked = run_daily_job(self.conn, self.app.config, run_date=date(2026, 1, 15))
        self.assertFalse(locked)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) c FROM monthly_winners").fetchone()["c"], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) c FROM daily_bonus_calculation").fetchone()["c"], 1)

    def test_last_friday_locks_one_winner_and_is_idempotent(self):
        self.add_fco("Ayo", 25_000_000, 1_500_000)
        self.add_fco("Blessing", 22_000_000, 2_000_000)
        now = datetime(2026, 1, 30, 12, 0, tzinfo=ZoneInfo("Africa/Lagos"))
        _, first = run_daily_job(self.conn, self.app.config, run_date=date(2026, 1, 30), now=now)
        self.assertTrue(first)
        # Data changes after the lock; re-running must NOT change the locked winner.
        with self.conn:
            self.conn.execute("UPDATE loans SET overdue_kobo = amount_kobo")
        _, second = run_daily_job(self.conn, self.app.config, run_date=date(2026, 1, 30), now=now)
        self.assertFalse(second)
        w = self.conn.execute("SELECT * FROM monthly_winners").fetchall()
        self.assertEqual(len(w), 1)
        self.assertEqual(w[0]["bonus_percentage"], "94.0000")

    def test_no_qualified_fco_writes_no_winner_row(self):
        self.add_fco("Small", 5_000_000, 0)
        now = datetime(2026, 2, 27, 12, 0, tzinfo=ZoneInfo("Africa/Lagos"))
        run_daily_job(self.conn, self.app.config, run_date=date(2026, 2, 27), now=now)
        row = self.conn.execute("SELECT * FROM monthly_winners").fetchone()
        self.assertIsNone(row["fco_id"])


class ApiAccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({"DATABASE_PATH": os.path.join(self.tmp.name, "t.db"),
                               "TESTING": True, "SECRET_KEY": "x"})
        runner = self.app.test_cli_runner()
        res = runner.invoke(args=["seed-demo"])
        self.assertEqual(res.exit_code, 0, res.output)
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def login(self, u):
        return self.client.post("/api/login", json={"username": u, "password": "DemoPass123!"})

    def test_requires_login(self):
        self.assertEqual(self.client.get("/api/management/dashboard").status_code, 401)

    def test_wrong_password(self):
        r = self.client.post("/api/login", json={"username": "ayo", "password": "nope"})
        self.assertEqual(r.status_code, 401)

    def test_fco_cannot_open_management_api(self):
        self.login("ayo")
        self.assertEqual(self.client.get("/api/management/dashboard").status_code, 403)

    def test_fco_sees_only_self_plus_leader(self):
        self.login("blessing")
        d = self.client.get("/api/fco/dashboard").get_json()
        self.assertEqual(d["me"]["name"], "Blessing")
        self.assertEqual(d["leader"]["name"], "Ayo")
        self.assertNotIn("rows", d)
        self.assertNotIn("disbursement", d["leader"])   # leader's money is not exposed
        self.assertEqual(d["last_month_winner"]["name"], "Blessing")

    def test_management_sees_everyone_ranked(self):
        self.login("manager")
        d = self.client.get("/api/management/dashboard").get_json()
        self.assertEqual([r["name"] for r in d["rows"]], ["Ayo", "Blessing", "Funke", "Emeka", "Chidi"])
        self.assertEqual(d["leader"]["name"], "Ayo")


if __name__ == "__main__":
    unittest.main()
