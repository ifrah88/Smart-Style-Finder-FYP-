const grid = document.getElementById("results-grid");
const sub = document.getElementById("results-sub");
const typeEl = document.getElementById("search-type");
const empty = document.getElementById("results-empty");

let _allResults = [];

function parsePrice(p) {
  return parseInt(String(p || "0").replace(/[^0-9]/g, ""), 10) || 0;
}

function renderGrid(results) {
  grid.innerHTML = "";
  if (!results || !results.length) {
    sub.textContent = "We found 0 matching products.";
    empty.hidden = false; return;
  }
  empty.hidden = true;
  sub.textContent = `We found ${results.length} matching product${results.length === 1 ? "" : "s"} for you.`;
  results.forEach(p => grid.appendChild(SSF.card(p, {actions: true, showConf: true})));
}

window.applySort = function(dir) {
  document.querySelectorAll(".sort-btn").forEach(b => b.classList.remove("sort-active"));
  const btn = document.getElementById("sort-" + dir);
  if (btn) btn.classList.add("sort-active");
  if (dir === "none") {
    renderGrid(_allResults);
  } else {
    const sorted = [..._allResults].sort((a, b) =>
      dir === "asc" ? parsePrice(a.price) - parsePrice(b.price)
                    : parsePrice(b.price) - parsePrice(a.price)
    );
    renderGrid(sorted);
  }
};

function render(type, results) {
  _allResults = results || [];
  typeEl.textContent = (type === "Image Upload" ? "🖼️ " : "🔠 ") + "Search Type: " + type;
  empty.hidden = true;
  document.querySelectorAll(".sort-btn").forEach(b => b.classList.remove("sort-active"));
  const defBtn = document.getElementById("sort-none");
  if (defBtn) defBtn.classList.add("sort-active");
  renderGrid(_allResults);
  sessionStorage.setItem("ssf_last", JSON.stringify({type, results: _allResults}));
}

async function run() {
  const stored = sessionStorage.getItem("ssf_results");
  if (stored) {
    sessionStorage.removeItem("ssf_results");
    const d = JSON.parse(stored);
    return render(d.type, d.results);
  }
  const pending = sessionStorage.getItem("ssf_pending");
  if (pending) {
    sessionStorage.removeItem("ssf_pending");
    const d = JSON.parse(pending);
    sub.textContent = "Searching the collection…";
    const res = await fetch("/api/search/text", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({query: d.query})});
    const data = await res.json();
    if (!res.ok) { sub.textContent = data.error || "Search failed."; return; }
    return render(data.type, data.results);
  }
  const last = sessionStorage.getItem("ssf_last");
  if (last) {
    const d = JSON.parse(last);
    return render(d.type, d.results);
  }
  sub.textContent = "Start a search to see matching products.";
  empty.hidden = false;
}
run();
