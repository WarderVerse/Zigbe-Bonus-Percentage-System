/* Shared helpers. SECURITY RULE: never use innerHTML with server data; build nodes with el(). */
"use strict";

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined && text !== null) n.textContent = text;
  return n;
}
function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); return node; }

const naira = n => "\u20a6" + Number(n).toLocaleString("en-NG", { maximumFractionDigits: 2 });
const short = n => {
  const v = Number(n);
  return "\u20a6" + (v >= 1e6 ? +(v / 1e6).toFixed(2) + "M" : v.toLocaleString("en-NG"));
};
const pct = n => +Number(n).toFixed(2) + "%";
const lagos = iso => new Date(iso).toLocaleString("en-GB", {
  timeZone: "Africa/Lagos", weekday: "short", day: "numeric", month: "short",
  hour: "numeric", minute: "2-digit", hour12: true });

async function api(url) {
  const r = await fetch(url, { credentials: "same-origin" });
  if (r.status === 401) { location.href = "/login"; throw new Error("signed out"); }
  if (!r.ok) throw new Error("Server error " + r.status);
  return r.json();
}

function bindLogout() {
  const b = document.getElementById("logout");
  if (!b) return;
  b.addEventListener("click", async () => {
    await fetch("/api/logout", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    location.href = "/login";
  });
}

/* Boxes used on both dashboards */
function renderWinner(node, w) {
  clear(node);
  node.append(el("h2", null, "Last month winner"));
  if (!w) { node.append(el("p", "muted", "No month has been locked yet.")); return; }
  if (w.no_winner) {
    node.append(el("p", null, w.label + ": no qualified winner, no bonus."));
  } else {
    node.append(el("p", "strong", w.name));
    node.append(el("p", null, w.label + " \u2022 Bonus " + pct(w.bonus_percent)
      + (w.disbursement ? " \u2022 Disbursement " + short(w.disbursement) : "")));
  }
  node.append(el("p", "muted", "Locked " + lagos(w.locked_at)));
}
function renderDeadline(node, d) {
  clear(node);
  node.append(el("h2", null, "Deadline"));
  node.append(el("p", "strong", d.label));
  node.append(el("p", "muted", "The winner is locked at this time on the last Friday of the month."));
}
function renderLockBanner(node, lock) {
  if (!lock) { node.hidden = true; return; }
  node.hidden = false;
  node.textContent = lock.no_winner
    ? "This month is locked: no qualified winner."
    : "This month is locked. Official winner: " + lock.name + " (" + pct(lock.bonus_percent) + ").";
}
function renderStatus(node, ctx) {
  node.textContent = ctx.snapshot_date
    ? "Figures as at 12:00 PM WAT on " + ctx.snapshot_date + ". Updated daily."
    : "No figures yet this month. The first calculation runs at 12:00 PM WAT.";
}
document.addEventListener("DOMContentLoaded", bindLogout);
