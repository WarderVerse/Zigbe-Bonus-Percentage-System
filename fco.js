"use strict";
(async function () {
  let ctx;
  try { ctx = await api("/api/fco/dashboard"); }
  catch (e) { document.getElementById("status").textContent = "Could not load data. Refresh to try again."; return; }

  document.getElementById("title").textContent = "My Bonus Performance \u2013 " + ctx.period.label;
  renderStatus(document.getElementById("status"), ctx);
  renderLockBanner(document.getElementById("lock-banner"), ctx.current_month_lock);

  const M = clear(document.getElementById("mine"));
  const me = ctx.me;
  if (!me) {
    M.append(el("h2", null, "My data"), el("p", "muted", "No figures for you yet this month."));
  } else {
    M.append(el("h2", null, "My data"));
    const dl = el("dl", "facts");
    const add = (k, v, cls) => { dl.append(el("dt", null, k), el("dd", cls || "", v)); };
    add("My Disbursement Portfolio", naira(me.disbursement));
    add("My Overdue", naira(me.overdue));
    add("My Portfolio Balance", naira(me.balance));
    add("My Bonus Percentage", pct(me.bonus_percent), "strong");
    add("My Rank", "#" + me.rank + " of " + ctx.total_fcos);
    add("My Qualification", me.qualified
      ? "Qualified (\u2265 " + pct(ctx.thresholds.min_bonus_percent) + " and \u2265 " + short(ctx.thresholds.min_disbursement) + ")"
      : "Not qualified: " + me.reasons.join("; "));
    M.append(dl);
  }

  const L = clear(document.getElementById("leader"));
  L.append(el("h2", null, "Currently leading"));
  if (!ctx.leader) {
    L.append(el("p", "leader-name", "No qualified leader yet"));
  } else if (ctx.leader.is_me) {
    L.append(el("p", "leader-name", "You"), el("p", "leader-pct", pct(ctx.leader.bonus_percent)),
      el("p", "leader-meta", "Highest bonus % among qualified FCOs"));
  } else {
    L.append(el("p", "leader-name", ctx.leader.name), el("p", "leader-pct", pct(ctx.leader.bonus_percent)),
      el("p", "leader-meta", ctx.leader.gap > 0
        ? "You are " + +ctx.leader.gap.toFixed(2) + " percentage points behind" : ""));
  }
  renderWinner(document.getElementById("winner"), ctx.last_month_winner);
  renderDeadline(document.getElementById("deadline"), ctx.deadline);
})();
