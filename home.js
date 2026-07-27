// Home page: text search entry, popular chips, trending styles with pages

function runTextSearch(query){
  sessionStorage.setItem("ssf_pending", JSON.stringify({type:"text", query}));
  location.href = "/results";
}

document.getElementById("home-text-form").addEventListener("submit", e => {
  e.preventDefault();
  const q = document.getElementById("home-text-input").value.trim();
  if (q) runTextSearch(q);
});

document.querySelectorAll(".pop-chip").forEach(c =>
  c.addEventListener("click", () => runTextSearch(c.textContent.trim())));

// trending
const grid = document.getElementById("trending-grid");
const pager = document.getElementById("trending-pager");

async function loadTrending(page){
  grid.innerHTML = "<p class='muted'>Loading…</p>";
  const d = await (await fetch(`/api/trending?page=${page}`)).json();
  grid.innerHTML = "";
  d.items.forEach(p => grid.appendChild(SSF.card(p)));
  pager.innerHTML = "";
  for (let i = 1; i <= d.total_pages; i++){
    const b = document.createElement("button");
    b.textContent = i; if (i === d.page) b.classList.add("active");
    b.addEventListener("click", () => { loadTrending(i); window.scrollTo({top:grid.offsetTop-120,behavior:"smooth"}); });
    pager.appendChild(b);
  }
}
loadTrending(1);
