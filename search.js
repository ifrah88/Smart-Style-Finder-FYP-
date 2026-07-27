// Text search page + Image search page

// ---- text ----
const textForm = document.getElementById("text-form");
if (textForm){
  const go = q => { sessionStorage.setItem("ssf_pending", JSON.stringify({type:"text", query:q})); location.href = "/results"; };
  textForm.addEventListener("submit", e => {
    e.preventDefault();
    const q = document.getElementById("text-input").value.trim();
    if (q) go(q);
  });
  document.querySelectorAll(".pop-chip").forEach(c => c.addEventListener("click", () => go(c.textContent.trim())));
}

// ---- image ----
const imageForm = document.getElementById("image-form");
if (imageForm){
  const input = document.getElementById("image-input");
  const drop = document.getElementById("drop-zone");
  const preview = document.getElementById("preview");
  const def = document.getElementById("drop-default");
  const btn = document.getElementById("image-search-btn");

  function showPreview(file){
    if (!file) return;
    preview.src = URL.createObjectURL(file);
    preview.hidden = false; def.hidden = true; btn.disabled = false;
  }
  input.addEventListener("change", () => showPreview(input.files[0]));
  ["dragover","dragleave","drop"].forEach(ev => drop.addEventListener(ev, e => {
    e.preventDefault();
    drop.classList.toggle("dragover", ev === "dragover");
    if (ev === "drop" && e.dataTransfer.files.length){ input.files = e.dataTransfer.files; showPreview(e.dataTransfer.files[0]); }
  }));

  const imgErr = document.getElementById("image-error");
  imageForm.addEventListener("submit", async e => {
    e.preventDefault();
    const file = input.files[0]; if (!file) return;
    imgErr.textContent = "";
    btn.disabled = true; btn.textContent = "Analysing your photo…";
    const fd = new FormData(); fd.append("image", file);
    try{
      const res = await fetch("/api/search/image", {method:"POST", body:fd});
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Search failed.");
      sessionStorage.setItem("ssf_results", JSON.stringify({type:data.type, results:data.results}));
      location.href = "/results";
    }catch(err){
      btn.disabled = false; btn.textContent = "🔍 Find Similar Dresses";
      imgErr.textContent = err.message;
    }
  });
}
