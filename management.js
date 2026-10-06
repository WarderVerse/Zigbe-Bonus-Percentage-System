"use strict";
(async function () {
  let ctx;
  try { ctx = await api("/api/management/dashboard"); }
  catch (e) { document.getElementById("status").textContent = "Could not load data. Refresh to try again."; return; }

  document.getElementById("title").textContent =
    "FCO Disbursement Portfolio Leaderboard \u2013 " + ctx.period.label;
  renderStatus(document.getElementById("status"), ctx);
  renderLockBanner(document.getElementById("lock-banner"), ctx.current_month_lock);

  const L = clear(document.getElementById("leader"));
  L.append(el("h2", null, "Current leader"));
  if (ctx.leader) {
    L.append(el("p", "leader-name", ctx.leader.name));
    L.append(el("p", "leader-pct", pct(ctx.leader.bonus_percent)));
    L.append(el("p", "leader-meta", "Disbursement " + short(ctx.leader.disbursement)
      + " \u2022 Overdue " + short(ctx.leader.overdue)));
  } else {
    L.append(el("p", "leader-name", "No qualified leader yet"));
    L.append(el("p", "leader-meta", "Needs at least " + pct(ctx.thresholds.min_bonus_percent)
      + " bonus and " + short(ctx.thresholds.min_disbursement) + " disbursed."));
  }

  const tbody = clear(document.querySelector("#board tbody"));
  if (!ctx.rows.length) {
    const tr = el("tr"); const td = el("td", "muted", "Nothing to show yet."); td.colSpan = 7;
    tr.append(td); tbody.append(tr);
  }
  for (const r of ctx.rows) {
    const tr = el("tr", r.qualified ? "" : "dim");
    tr.append(el("td", null, r.rank), el("td", "strong", r.name),
      el("td", "num", naira(r.disbursement)), el("td", "num", naira(r.overdue)),
      el("td", "num", naira(r.balance)), el("td", "num strong", pct(r.bonus_percent)));
    const q = el("td");
    q.append(el("span", r.qualified ? "tag ok" : "tag no",
      r.qualified ? "Yes" : "No (" + r.reasons.join("; ") + ")"));
    tr.append(q); tbody.append(tr);
  }
  renderWinner(document.getElementById("winner"), ctx.last_month_winner);
  renderDeadline(document.getElementById("deadline"), ctx.deadline);
})();
