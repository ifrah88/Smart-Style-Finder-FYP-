// Product page: booking + feedback modals
const productTop = document.querySelector(".product-top");
const PID = productTop.dataset.pid;
const PRODUCT = {product_id:PID, title:productTop.dataset.title, brand:productTop.dataset.brand, price:productTop.dataset.price};

function open(id){ document.getElementById(id).hidden = false; }
function close(id){ document.getElementById(id).hidden = true; }

document.addEventListener("click", e => {
  if (e.target.dataset.close !== undefined || e.target.classList.contains("modal")){
    const m = e.target.closest(".modal"); if (m) m.hidden = true;
  }
});

// ---- booking ----
document.getElementById("book-btn").addEventListener("click", () => {
  // prevent past dates
  const today = new Date().toISOString().split("T")[0];
  document.getElementById("booking-date").min = today;
  open("booking-modal");
});
let duration = "1 Day";
document.querySelectorAll("#duration-opts .dur").forEach(b => b.addEventListener("click", () => {
  document.querySelectorAll("#duration-opts .dur").forEach(x => x.classList.remove("active"));
  b.classList.add("active"); duration = b.textContent.trim();
}));
document.getElementById("confirm-booking").addEventListener("click", async () => {
  const err = document.getElementById("booking-error"); err.textContent = "";
  const date = document.getElementById("booking-date").value;
  if (!date){ err.textContent = "Please select a booking date."; return; }
  const res = await fetch("/api/booking", {method:"POST", headers:{"Content-Type":"application/json"},
    body:JSON.stringify({product_id:PID, date, duration})});
  const d = await res.json();
  if (!res.ok){ err.textContent = d.error; return; }
  const badge = document.getElementById("bookings-badge");
  if (badge) badge.textContent = d.bookings_count;
  close("booking-modal");
  alert("✅ Booking confirmed! View it under Bookings.");
});

// ---- feedback ----
const fbBtn = document.getElementById("feedback-btn");
if (fbBtn) fbBtn.addEventListener("click", () => open("feedback-modal"));
let rating = 0, experience = "";
document.querySelectorAll("#star-rate .star").forEach(s => {
  s.addEventListener("click", () => {
    rating = +s.dataset.v;
    document.querySelectorAll("#star-rate .star").forEach(x => {
      const on = +x.dataset.v <= rating; x.classList.toggle("on", on); x.textContent = on ? "★" : "☆";
    });
  });
});
document.querySelectorAll("#exp-opts .exp").forEach(b => b.addEventListener("click", () => {
  document.querySelectorAll("#exp-opts .exp").forEach(x => x.classList.remove("active"));
  b.classList.add("active"); experience = b.textContent.trim();
}));
document.getElementById("submit-feedback").addEventListener("click", async () => {
  const err = document.getElementById("feedback-error"); err.textContent = "";
  const msg = document.getElementById("fb-message").value.trim();
  const rec = document.querySelector("input[name=rec]:checked").value;
  if (!rating){ err.textContent = "Please rate your experience."; return; }
  if (!msg){ err.textContent = "Please write your feedback."; return; }
  const res = await fetch("/api/feedback", {method:"POST", headers:{"Content-Type":"application/json"},
    body:JSON.stringify({product_id:PID, rating, experience, message:msg, recommend:rec})});
  const d = await res.json();
  if (!res.ok){ err.textContent = d.error; return; }
  // prepend to reviews
  const list = document.getElementById("reviews-list");
  const no = document.getElementById("no-reviews"); if (no) no.remove();
  const name = document.querySelector(".user-btn").textContent.replace("👤 Hi,","").replace("▾","").trim();
  const div = document.createElement("div"); div.className = "review";
  div.innerHTML = `<div class="review-avatar">${(name[0]||"U").toUpperCase()}</div>
    <div class="review-body"><div class="review-head"><strong>${name}</strong>
    <span class="stars">${"★".repeat(rating)}${"☆".repeat(5-rating)}</span></div>
    <p>${msg.replace(/[<>]/g,"")}</p></div>`;
  list.prepend(div);
  const cnt = document.getElementById("review-count"); cnt.textContent = +cnt.textContent + 1;
  close("feedback-modal");
  alert("Thank you for your feedback! 💬");
});

// auto-open booking if arrived via "Book Dress"
if (new URLSearchParams(location.search).get("book")) open("booking-modal");
