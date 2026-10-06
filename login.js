"use strict";
document.getElementById("login-form").addEventListener("submit", async e => {
  e.preventDefault();
  const err = document.getElementById("login-error");
  err.hidden = true;
  const r = await fetch("/api/login", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: e.target.username.value, password: e.target.password.value })
  });
  const body = await r.json().catch(() => ({}));
  if (r.ok) { location.href = body.next || "/"; return; }
  err.textContent = body.error || "Could not sign in.";
  err.hidden = false;
});
