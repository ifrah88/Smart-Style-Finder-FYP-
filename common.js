// Shared helpers across pages
window.SSF = (function () {
  const SWATCH = {
    black:"#222",white:"#f0f0f0","off white":"#efeada",beige:"#d8c3a0",grey:"#9a9a9a",
    blue:"#3a5bbf",green:"#3f9a52",red:"#c0392b",maroon:"#7e2a33",pink:"#e07aa0",
    peach:"#f0b49a",purple:"#8a5cc0",lilac:"#c4b0dd",orange:"#e08a35",yellow:"#dcc23c",
    brown:"#7a5538",rust:"#a8512c",multi:"linear-gradient(90deg,#e07,#fc3,#3cf)"
  };
  function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}

  // product card. opts.actions => show View/Book buttons
  function card(p, opts={}){
    const sw = SWATCH[p.colour] || "#ccc";
    const el = document.createElement("article");
    el.className = "p-card";
    const conf = (opts.showConf && p.confidence!=null) ? `<span class="p-conf">${p.confidence}% match</span>` : "";
    const actions = opts.actions ? `<div class="p-actions">
        <button class="btn-outline view-btn">👁 View Details</button>
        <button class="btn-primary book-btn">📅 Book Dress</button></div>` : "";
    el.innerHTML = `
      <div class="p-card-img"><img src="${p.img_url}" alt="${esc(p.title)}" loading="lazy"></div>
      <div class="p-card-body">
        ${conf}
        <span class="p-brand">${esc(p.brand)}</span>
        <span class="p-title">${esc(p.title)}</span>
        <span class="p-meta"><span class="sw" style="display:inline-block;width:11px;height:11px;border-radius:50%;background:${sw};vertical-align:middle;margin-right:5px"></span>${esc(p.colour)} · ${esc(p.fabric||p.design)}</span>
        <span class="p-price">${esc(p.price)}</span>
        ${actions}
      </div>`;
    const go = () => location.href = `/product/${encodeURIComponent(p.product_id)}` + (p.confidence!=null?`?score=${p.confidence}`:"");
    el.querySelector(".p-card-img").addEventListener("click", go);
    el.querySelector(".p-title").addEventListener("click", go);
    if (opts.actions){
      el.querySelector(".view-btn").addEventListener("click", go);
      el.querySelector(".book-btn").addEventListener("click", () => location.href = `/product/${encodeURIComponent(p.product_id)}?book=1`);
    }
    return el;
  }
  return { SWATCH, esc, card };
})();

// user dropdown + logout + edit profile
document.addEventListener("click", (e) => {
  const menu = document.getElementById("user-menu");
  if (menu){
    if (e.target.closest(".user-btn")) menu.classList.toggle("open");
    else if (!e.target.closest(".user-menu")) menu.classList.remove("open");
  }
  if (e.target.id === "logout-link"){
    e.preventDefault();
    fetch("/api/logout",{method:"POST"}).then(r=>r.json()).then(d=>location.href=d.redirect);
  }
  if (e.target.id === "edit-profile-link"){
    e.preventDefault();
    menu && menu.classList.remove("open");
    // Pre-fill fields from server
    fetch("/api/me").then(r=>r.json()).then(u=>{
      document.getElementById("ep-name").value = u.name || "";
      document.getElementById("ep-email").value = u.email || "";
      document.getElementById("ep-error").textContent = "";
      document.getElementById("ep-success").textContent = "";
      document.getElementById("edit-profile-modal").hidden = false;
    });
  }
  if (e.target.id === "edit-profile-close" || (e.target.classList.contains("modal") && e.target.id === "edit-profile-modal")){
    document.getElementById("edit-profile-modal").hidden = true;
  }
});

// Edit Profile submit
const epSubmit = document.getElementById("ep-submit");
if (epSubmit){
  epSubmit.addEventListener("click", async () => {
    const err = document.getElementById("ep-error");
    const suc = document.getElementById("ep-success");
    err.textContent = ""; suc.textContent = "";
    const name = document.getElementById("ep-name").value.trim();
    const email = document.getElementById("ep-email").value.trim();
    if (!name) return err.textContent = "Full name cannot be empty.";
    if (!email) return err.textContent = "Email cannot be empty.";
    const res = await fetch("/api/profile/update", {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({full_name: name, email})
    });
    const data = await res.json();
    if (!res.ok) return err.textContent = data.error || "Update failed.";
    suc.textContent = "Profile updated successfully.";
    // Update the nav greeting
    const btn = document.querySelector(".user-btn");
    if (btn) btn.textContent = `👤 Hi, ${data.name.split(" ")[0]} ▾`;
  });
}
