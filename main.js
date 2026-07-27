// Smart Style Finder — frontend logic (vanilla JS)

const $ = (sel) => document.querySelector(sel);

const els = {
  toggles: document.querySelectorAll(".toggle-btn"),
  textForm: $("#text-form"),
  textInput: $("#text-input"),
  imageForm: $("#image-form"),
  imageInput: $("#image-input"),
  dropZone: $("#drop-zone"),
  dropDefault: $("#drop-default"),
  preview: $("#preview"),
  imageBtn: $("#image-search-btn"),
  examples: $("#examples"),
  resultsSection: $("#results-section"),
  resultsTitle: $("#results-title"),
  results: $("#results"),
  loader: $("#loader"),
  loaderText: $("#loader-text"),
  error: $("#error"),
};

// approximate swatch colours for the dataset's colour names
const SWATCH = {
  black: "#222", white: "#f4f4f4", "off white": "#efeada", beige: "#d8c3a0",
  grey: "#9a9a9a", blue: "#3a5bbf", green: "#3f9a52", red: "#c0392b",
  maroon: "#7e2a33", pink: "#e07aa0", peach: "#f0b49a", purple: "#8a5cc0",
  lilac: "#c4b0dd", orange: "#e08a35", yellow: "#dcc23c", brown: "#7a5538",
  rust: "#a8512c", multi: "linear-gradient(90deg,#e07,#fc3,#3cf)",
};

// ---------- mode toggle ----------
els.toggles.forEach((btn) => {
  btn.addEventListener("click", () => {
    els.toggles.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const mode = btn.dataset.mode;
    els.textForm.classList.toggle("active", mode === "text");
    els.examples.style.display = mode === "text" ? "flex" : "none";
    els.imageForm.classList.toggle("active", mode === "image");
  });
});

// ---------- example chips ----------
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    els.textInput.value = chip.textContent;
    els.textForm.requestSubmit();
  });
});

// ---------- text search ----------
els.textForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = els.textInput.value.trim();
  if (!query) return;
  await runSearch("/search/text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  }, `Results for “${query}”`);
});

// ---------- image upload UX ----------
els.imageInput.addEventListener("change", () => showPreview(els.imageInput.files[0]));

["dragover", "dragleave", "drop"].forEach((evt) =>
  els.dropZone.addEventListener(evt, (e) => {
    e.preventDefault();
    els.dropZone.classList.toggle("dragover", evt === "dragover");
    if (evt === "drop" && e.dataTransfer.files.length) {
      els.imageInput.files = e.dataTransfer.files;
      showPreview(e.dataTransfer.files[0]);
    }
  })
);

function showPreview(file) {
  if (!file) return;
  els.preview.src = URL.createObjectURL(file);
  els.preview.hidden = false;
  els.dropDefault.hidden = true;
  els.imageBtn.disabled = false;
}

els.imageForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = els.imageInput.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("image", file);
  await runSearch("/search/image", { method: "POST", body: fd },
    "Similar pieces", "Analysing your photo…");
});

// ---------- core search runner ----------
async function runSearch(url, opts, titleText, loaderMsg = "Searching the collection…") {
  els.error.hidden = true;
  els.resultsSection.hidden = true;
  els.loaderText.textContent = loaderMsg;
  els.loader.hidden = false;
  window.scrollTo({ top: document.querySelector(".search-card").offsetTop - 40, behavior: "smooth" });

  try {
    const res = await fetch(url, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Something went wrong.");
    renderResults(data.results, titleText);
  } catch (err) {
    els.error.textContent = err.message;
    els.error.hidden = false;
  } finally {
    els.loader.hidden = true;
  }
}

function renderResults(results, titleText) {
  els.results.innerHTML = "";
  if (!results || !results.length) {
    els.error.textContent = "No matches found. Try a different search.";
    els.error.hidden = false;
    return;
  }
  els.resultsTitle.textContent = `${titleText} · ${results.length} matches`;
  results.forEach((r, i) => {
    const swatch = SWATCH[r.colour] || "#ccc";
    const card = document.createElement("article");
    card.className = "card";
    card.innerHTML = `
      <div class="card-img-wrap">
        <img src="${r.img_url}" alt="${escapeHtml(r.title)}" loading="lazy" />
      </div>
      <div class="card-body">
        <span class="card-rank">${r.confidence}% match</span>
        <span class="card-brand">${escapeHtml(r.brand)}</span>
        <span class="card-title">${escapeHtml(r.title)}</span>
        <div class="card-meta">
          <span class="swatch" style="background:${swatch}"></span>
          <span class="card-colour">${escapeHtml(r.colour)} · ${escapeHtml(r.design)}</span>
        </div>
        <span class="card-price">${escapeHtml(r.price)}</span>
      </div>`;
    els.results.appendChild(card);
  });
  els.resultsSection.hidden = false;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
