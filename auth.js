// Login / Register / Forgot / Terms
const $ = s => document.querySelector(s);

// tab switching
document.querySelectorAll(".auth-tab").forEach(t => t.addEventListener("click", () => {
  document.querySelectorAll(".auth-tab").forEach(x => x.classList.remove("active"));
  t.classList.add("active");
  const tab = t.dataset.tab;
  $("#login-form").classList.toggle("active", tab === "login");
  $("#register-form").classList.toggle("active", tab === "register");
  $(".auth-welcome").textContent = tab === "login" ? "Welcome Back!" : "Join Us Today!";
}));

// password show/hide
document.addEventListener("click", e => {
  if (e.target.classList.contains("toggle-eye")){
    const inp = document.getElementById(e.target.dataset.target);
    if (inp) inp.type = inp.type === "password" ? "text" : "password";
  }
});

// live password rules
const RULES = {
  len: v => v.length >= 8, upper: v => /[A-Z]/.test(v), lower: v => /[a-z]/.test(v),
  num: v => /\d/.test(v), special: v => /[^A-Za-z0-9]/.test(v),
};
const regPass = $("#reg-pass");
if (regPass) regPass.addEventListener("input", () => {
  const v = regPass.value;
  document.querySelectorAll("#pw-rules li").forEach(li =>
    li.classList.toggle("ok", RULES[li.dataset.rule](v)));
});
const validPassword = v => Object.values(RULES).every(f => f(v));
const validEmail = v => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v);

async function post(url, body){
  const r = await fetch(url, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
  return [r.ok, await r.json()];
}

// LOGIN
$("#login-form").addEventListener("submit", async e => {
  e.preventDefault();
  const err = $("#login-error"); err.textContent = "";
  const email = e.target.email.value.trim(), pw = e.target.password.value;
  if (!email) return err.textContent = "Please enter your email address.";
  if (!validEmail(email)) return err.textContent = "Invalid email format.";
  if (!pw) return err.textContent = "Please enter your password.";
  const [ok, d] = await post("/api/login", {email, password:pw, remember:e.target.remember.checked});
  if (ok) location.href = d.redirect; else err.textContent = d.error;
});

// REGISTER
$("#register-form").addEventListener("submit", async e => {
  e.preventDefault();
  const err = $("#register-error"); err.textContent = "";
  const name = e.target.full_name.value.trim(), email = e.target.email.value.trim();
  const pw = e.target.password.value, cpw = e.target.confirm.value;
  if (!name) return err.textContent = "Please enter your full name.";
  if (!validEmail(email)) return err.textContent = "Invalid email format.";
  if (!validPassword(pw)) return err.textContent = "Password must be 8+ chars with upper, lower, number & special character.";
  if (pw !== cpw) return err.textContent = "Passwords do not match.";
  if (!e.target.terms.checked) return err.textContent = "Please accept the Terms & Conditions.";
  const [ok, d] = await post("/api/register", {full_name:name, email, password:pw, confirm:cpw, terms:true});
  if (ok) location.href = d.redirect; else err.textContent = d.error;
});

// modals open/close
function openModal(id){ document.getElementById(id).hidden = false; }
document.addEventListener("click", e => {
  if (e.target.id === "forgot-link"){ e.preventDefault(); openModal("forgot-modal"); }
  if (e.target.id === "terms-link"){ e.preventDefault(); openModal("terms-modal"); }
  if (e.target.dataset.close !== undefined || e.target.classList.contains("modal")){
    const m = e.target.closest(".modal"); if (m) m.hidden = true;
  }
});

// FORGOT
$("#forgot-submit").addEventListener("click", async () => {
  const err = $("#forgot-error"); err.textContent = "";
  const email = $("#fp-email").value.trim(), pw = $("#fp-pass").value;
  if (!validEmail(email)) return err.textContent = "Invalid email format.";
  if (!validPassword(pw)) return err.textContent = "Password must be 8+ chars with upper, lower, number & special.";
  const [ok, d] = await post("/api/forgot", {email, password:pw});
  if (ok){ err.style.color = "#2e9e5b"; err.textContent = d.message; }
  else { err.style.color = "#c0392b"; err.textContent = d.error; }
});
