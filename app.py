"""
Smart Style Finder — local web app.

Multi-page app: login/register -> home -> text/image search -> results ->
product details (booking + feedback). Search is powered by clip_retrieval.

Run:  python app.py   then open http://127.0.0.1:5000
"""
from __future__ import annotations

import os
import re
import tempfile
import threading
from functools import wraps

from flask import (Flask, abort, g, jsonify, redirect, render_template, request,
                   send_file, session, url_for)
from itsdangerous import URLSafeSerializer

import db
from clip_retrieval import ClipRetrieval, SHORTLIST

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "ssf_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

MAX_RESULTS = SHORTLIST
CONF_THRESHOLD = 0.60

PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ---------------------------------------------------------------------------
# Fashion query vocabulary — used to reject non-fashion input before CLIP.
# Words that appear here indicate a valid search (at least one must match).
_FASHION_WORDS = {
    # ---- colours (all anchor names, base labels, and common aliases) ----
    "black", "charcoal", "white", "cream", "grey", "gray", "off", "blue",
    "navy", "teal", "turquoise", "green", "mint", "olive", "red", "maroon",
    "pink", "blush", "fuchsia", "rose", "purple", "lilac", "lavender",
    "orange", "yellow", "lemon", "gold", "mustard", "brown", "tan", "beige",
    "peach", "rust", "multi", "multicolor", "multicolour", "colourful",
    # ---- patterns / design ----
    "embroidered", "embroidery", "embroided", "embrioded", "embrodered",
    "printed", "print", "solid", "jacquard",
    "floral", "geometric", "striped", "stripes", "dotted", "dots", "paisley",
    "abstract", "checkered", "plaid", "batik", "brocade", "block", "digital",
    "sequined", "embellished", "plain", "textured", "woven",
    # ---- garment types ----
    "kurti", "kurta", "shirt", "dress", "shalwar", "kameez", "dupatta",
    "suit", "top", "blouse", "gown", "maxi", "midi", "mini", "pant", "pants",
    "trouser", "trousers", "skirt", "tunic", "coat", "jacket", "saree",
    "lehenga", "outfit", "clothing", "clothes", "wear", "garment",
    # ---- fabrics ----
    "lawn", "chiffon", "cotton", "silk", "linen", "georgette", "organza",
    "velvet", "denim", "polyester", "crepe", "net", "satin", "muslin",
    "khaddar", "karandi", "cambric", "nida", "slub", "fabric",
}

# Multi-word colour phrases checked as substrings (single-word coverage above
# already handles most, but these make "baby pink" / "off white" explicit).
_FASHION_PHRASES = [
    "off white", "baby pink", "sky blue", "powder blue", "hot pink",
    "light grey", "light gray", "dark green", "dark blue", "deep red",
]


def _is_valid_fashion_query(q: str) -> bool:
    """Return True if the query contains at least one recognised fashion term."""
    q_low = q.lower()
    words = re.findall(r"[a-z]+", q_low)
    if any(w in _FASHION_WORDS for w in words):
        return True
    return any(phrase in q_low for phrase in _FASHION_PHRASES)


# ---------------------------------------------------------------------------
# Attribute-match re-ranking
# Maps query words → CNN design class (the 4 classes the model predicts)
_DESIGN_MAP = {
    "embroidered": "embroidered", "embroidery": "embroidered",
    "embroided": "embroidered", "embrioded": "embroidered", "embrodered": "embroidered",
    "printed": "printed", "print": "printed", "floral": "printed",
    "geometric": "printed", "block": "printed", "digital": "printed",
    "solid": "solid", "plain": "solid",
    "jacquard": "jacquard", "woven": "jacquard", "brocade": "jacquard",
}

# Maps query colour words → base palette label (from color_palette _ANCHOR_BASE)
_COLOUR_QUERY_MAP = {
    "black": "black", "charcoal": "black",
    "white": "white", "cream": "white",
    "grey": "grey", "gray": "grey",
    "blue": "blue", "navy": "blue", "sky": "blue", "powder": "blue", "turquoise": "blue",
    "teal": "green", "green": "green", "mint": "green", "olive": "green",
    "red": "red",
    "maroon": "maroon",
    "pink": "pink", "blush": "pink", "rose": "pink", "fuchsia": "pink",
    "purple": "purple",
    "lilac": "lilac", "lavender": "lilac",
    "orange": "orange",
    "yellow": "yellow", "gold": "yellow", "mustard": "yellow", "lemon": "yellow",
    "brown": "brown",
    "beige": "beige", "tan": "beige",
    "peach": "peach",
    "rust": "rust",
}

_COLOUR_PHRASES = {
    "baby pink": "pink", "hot pink": "pink",
    "off white": "white",
    "sky blue": "blue", "powder blue": "blue",
    "light grey": "grey", "light gray": "grey",
}


def _attribute_boost(query: str, results: list) -> list:
    """Hard-tier re-ranking so that explicit attribute matches always rise above
    non-matching results, regardless of raw CLIP score.

    Tiers (lower = ranked higher):
      0 — design AND colour both match query terms  (e.g. red + embroidered)
      1 — design matches only                       (e.g. embroidered, wrong colour)
      2 — colour name matches only                  (e.g. red, wrong design)
      3 — neither attribute matches explicitly

    Within each tier, the original CLIP+colour score decides order.
    If the query contains no explicit design or colour term, ranking is unchanged.
    """
    q_low = query.lower()
    words = re.findall(r"[a-z]+", q_low)

    target_designs = {_DESIGN_MAP[w] for w in words if w in _DESIGN_MAP}
    target_colours = {_COLOUR_QUERY_MAP[w] for w in words if w in _COLOUR_QUERY_MAP}
    for phrase, col in _COLOUR_PHRASES.items():
        if phrase in q_low:
            target_colours.add(col)

    if not target_designs and not target_colours:
        return results  # no explicit attributes in query — leave order unchanged

    for r in results:
        design_hit = (
            target_designs and
            (r.get("design") or "").lower() in target_designs
        )
        colour_hit = False
        if target_colours:
            pal = [c.lower() for c in (r.get("palette") or [])]
            csv_col = (r.get("colour") or "").lower()
            colour_hit = any(tc in pal or tc in csv_col for tc in target_colours)

        if design_hit and colour_hit:
            r["_tier"] = 0
        elif design_hit:
            r["_tier"] = 1
        elif colour_hit:
            r["_tier"] = 2
        else:
            r["_tier"] = 3

    # Primary sort: tier (ascending). Secondary: original score (descending).
    results.sort(key=lambda x: (x.get("_tier", 3), -x["score"]))
    return results

app = Flask(__name__)
app.secret_key = "smart-style-finder-local-secret-key-change-me"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

# token auth for the mobile app (web keeps using cookie sessions)
_token_ser = URLSafeSerializer(app.secret_key, salt="ssf-auth")


def make_token(user):
    return _token_ser.dumps({"uid": user["id"], "uname": user["full_name"]})


def read_token(tok):
    try:
        return _token_ser.loads(tok)
    except Exception:
        return None


@app.after_request
def _cors(resp):
    # allow the mobile app / Expo web client to call the API
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Auth-Token"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


db.init_db()

# ---- engine (load once; warm CLIP in background) ----
engine = ClipRetrieval()
PIDS = engine.meta["product_ids"].astype(str)
PID_TO_IDX = {p: i for i, p in enumerate(PIDS)}
PID_TO_IMG = {p: str(ip) for p, ip in zip(PIDS, engine.meta["image_path"])}
POPULAR = ["Black Lawn Shirt", "Floral Printed Dress", "Baby Pink Embroidered",
           "Party Wear Dress", "White Chikankari Kurti", "Blue Printed Kurti"]


def _warm():
    try:
        engine.text_embed("warm up")
    except Exception:
        pass


threading.Thread(target=_warm, daemon=True).start()


# --------------------------------------------------------------------- helpers
def login_required(f):
    @wraps(f)
    def wrap(*a, **k):
        if "uid" in session:
            return f(*a, **k)
        # mobile: authenticate via X-Auth-Token header
        data = read_token(request.headers.get("X-Auth-Token", ""))
        if data:
            g.uid, g.uname = data["uid"], data["uname"]
            return f(*a, **k)
        if request.path.startswith("/api/"):
            return jsonify(error="Not authenticated."), 401
        return redirect(url_for("login_page"))
    return wrap


def cur_uid():
    return session.get("uid") or getattr(g, "uid", None)


def cur_uname():
    return session.get("uname") or getattr(g, "uname", "User")




def _price(v) -> str:
    try:
        return f"PKR {int(float(v)):,}"
    except Exception:
        return str(v or "")


def _ctx():
    """Common template context (user + bookings count)."""
    uid = session.get("uid")
    return {
        "user_name": session.get("uname", ""),
        "logged_in": uid is not None,
        "bookings_count": db.count_bookings(uid) if uid else 0,
        "popular": POPULAR,
    }


def product_by_id(pid: str, score: int | None = None) -> dict | None:
    i = PID_TO_IDX.get(str(pid))
    if i is None:
        return None
    m = engine.meta
    cnt = int(engine.pal_counts[i])
    # detected dominant colour (from actual pixels) is more accurate than the
    # noisy CSV label, so use it for display; fall back to the CSV colour.
    detected = str(engine.pal_names[i][0]) if cnt > 0 else ""
    return {
        "product_id": pid,
        "title": str(m["title"][i]) or "Untitled",
        "brand": (str(m["brand"][i]) or "Sapphire").title(),
        "colour": detected or str(m["colour"][i]),
        "design": str(m["design"][i]),
        "fabric": str(m["fabric"][i]) or "—",
        "price": _price(m["price"][i]),
        "palette": [str(x) for x in engine.pal_names[i][:cnt]],
        "img_url": f"/pimg/{pid}",
        "score": score,
    }


def _threshold(results):
    if not results:
        return []
    # Normalise against the top-ranked result (after attribute tiering) so that
    # tier-0 matches aren't penalised by a tier-3 item with a higher raw CLIP score.
    best = results[0]["score"] or 1.0
    kept = []
    for r in results:
        conf = r["score"] / best
        if conf >= CONF_THRESHOLD:
            r["confidence"] = min(100, round(conf * 100))
            kept.append(r)
    return kept


def _format(results):
    out = []
    for r in results:
        pal = r.get("palette") or []
        out.append({
            "product_id": r["product_id"],
            "title": r["title"] or "Untitled",
            "brand": (r.get("brand") or "Sapphire").title(),
            "colour": (pal[0] if pal else r["colour"]),  # detected colour > noisy CSV label
            "design": r["design"],
            "fabric": (r.get("fabric") or "—"),
            "price": _price(r.get("price")),
            "palette": r.get("palette", []),
            "confidence": r.get("confidence", 100),
            "img_url": f"/pimg/{r['product_id']}",
        })
    return out


# ----------------------------------------------------------------------- auth
@app.route("/login")
def login_page():
    if "uid" in session:
        return redirect(url_for("home"))
    return render_template("login.html")


@app.route("/api/register", methods=["POST"])
def api_register():
    d = request.json or {}
    name = (d.get("full_name") or "").strip()
    email = (d.get("email") or "").strip()
    pw = d.get("password") or ""
    cpw = d.get("confirm") or ""
    if not name:
        return jsonify(error="Please enter your full name."), 400
    if not EMAIL_RE.match(email):
        return jsonify(error="Invalid email format."), 400
    if not PASSWORD_RE.match(pw):
        return jsonify(error="Password does not meet the requirements."), 400
    if pw != cpw:
        return jsonify(error="Passwords do not match."), 400
    if not d.get("terms"):
        return jsonify(error="You must accept the Terms & Conditions."), 400
    ok, msg = db.create_user(name, email, pw)
    if not ok:
        return jsonify(error=msg), 400
    u = db.get_user_by_email(email)
    session["uid"], session["uname"] = u["id"], u["full_name"]
    return jsonify(ok=True, redirect=url_for("home"), token=make_token(u), name=u["full_name"])


@app.route("/api/login", methods=["POST"])
def api_login():
    d = request.json or {}
    email = (d.get("email") or "").strip()
    pw = d.get("password") or ""
    if not email:
        return jsonify(error="Please enter your email address."), 400
    if not EMAIL_RE.match(email):
        return jsonify(error="Invalid email format."), 400
    u = db.verify_login(email, pw)
    if not u:
        return jsonify(error="Incorrect email or password."), 401
    session["uid"], session["uname"] = u["id"], u["full_name"]
    if d.get("remember"):
        session.permanent = True
    return jsonify(ok=True, redirect=url_for("home"), token=make_token(u), name=u["full_name"])


@app.route("/api/forgot", methods=["POST"])
def api_forgot():
    d = request.json or {}
    email = (d.get("email") or "").strip()
    pw = d.get("password") or ""
    if not db.get_user_by_email(email):
        return jsonify(error="No account found with that email."), 404
    if not PASSWORD_RE.match(pw):
        return jsonify(error="New password does not meet the requirements."), 400
    db.update_password(email, pw)
    return jsonify(ok=True, message="Password reset. You can now log in.")


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify(ok=True, redirect=url_for("login_page"))


# ----------------------------------------------------------------------- pages
@app.route("/")
def index():
    return redirect(url_for("home") if "uid" in session else url_for("login_page"))


@app.route("/home")
@login_required
def home():
    return render_template("home.html", **_ctx())


@app.route("/search/text")
@login_required
def search_text_page():
    return render_template("search_text.html", **_ctx())


@app.route("/search/image")
@login_required
def search_image_page():
    return render_template("search_image.html", **_ctx())


@app.route("/results")
@login_required
def results_page():
    return render_template("results.html", **_ctx())


@app.route("/product/<pid>")
@login_required
def product_page(pid):
    score = request.args.get("score", type=int)
    p = product_by_id(pid, score)
    if not p:
        abort(404)
    # similar products via image similarity of this item
    similar = []
    try:
        seg = str(engine.meta["seg_path"][PID_TO_IDX[pid]])
        for r in engine.search_by_seg(seg, k=6):
            if r["product_id"] != pid:
                similar.append(_format([r])[0])
        similar = similar[:4]
    except Exception:
        similar = []
    reviews = db.list_feedback(pid)
    return render_template("product.html", product=p, similar=similar,
                           reviews=reviews, **_ctx())


@app.route("/bookings")
@login_required
def bookings_page():
    items = db.list_bookings(session["uid"])
    return render_template("bookings.html", bookings=items, **_ctx())


@app.route("/feedback")
@login_required
def feedback_page():
    return render_template("feedback.html", **_ctx())


@app.route("/about")
@login_required
def about_page():
    return render_template("about.html", **_ctx())




# ------------------------------------------------------------------------ apis
@app.route("/api/search/text", methods=["POST"])
@login_required
def api_search_text():
    q = (request.json or {}).get("query", "").strip()
    if not q:
        return jsonify(error="Please type something to search."), 400
    if not _is_valid_fashion_query(q):
        return jsonify(
            error="No matches found. Please describe a dress using colour or "
                  "pattern keywords (e.g. 'pink embroidered shirt')."
        ), 422
    raw = engine.search_by_text(q, k=MAX_RESULTS)
    raw = _attribute_boost(q, raw)
    res = _threshold(raw)
    # If we have 6+ exact attribute matches (tier 0), drop lower tiers to avoid noise
    tier0 = [r for r in res if r.get("_tier", 3) == 0]
    if len(tier0) >= 6:
        res = [r for r in res if r.get("_tier", 3) <= 1]
    return jsonify(query=q, type="Text", results=_format(res))


@app.route("/api/search/image", methods=["POST"])
@login_required
def api_search_image():
    f = request.files.get("image")
    if not f or not f.filename:
        return jsonify(error="No image uploaded."), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED:
        return jsonify(error="Unsupported file type."), 400
    path = os.path.join(UPLOAD_DIR, f"u{cur_uid()}{ext}")
    f.save(path)
    # human gate: YOLO must detect a person before we run colour / search
    try:
        from human_detector import has_person
        ok, conf = has_person(path)
        if not ok:
            return jsonify(error="No person detected in the image. Please upload a clear "
                                 "photo of someone wearing a dress or outfit."), 422
    except Exception:
        pass  # if the detector is unavailable, don't block search
    res = _threshold(engine.search_by_image(path, k=MAX_RESULTS))
    return jsonify(type="Image Upload", results=_format(res))


@app.route("/api/trending")
@login_required
def api_trending():
    page = max(1, request.args.get("page", 1, type=int))
    per = 10
    start = (page - 1) * per
    total_pages = 3
    items = []
    for i in range(start, min(start + per, len(PIDS))):
        cnt = int(engine.pal_counts[i])
        items.append(_format([{
            "product_id": str(PIDS[i]),
            "title": str(engine.meta["title"][i]),
            "brand": str(engine.meta["brand"][i]),
            "colour": str(engine.meta["colour"][i]),
            "design": str(engine.meta["design"][i]),
            "fabric": str(engine.meta["fabric"][i]),
            "price": str(engine.meta["price"][i]),
            "palette": [str(x) for x in engine.pal_names[i][:cnt]], "confidence": 100,
        }])[0])
    return jsonify(page=page, total_pages=total_pages, items=items)


@app.route("/api/booking", methods=["POST"])
@login_required
def api_booking():
    d = request.json or {}
    pid = d.get("product_id")
    p = product_by_id(pid)
    if not p:
        return jsonify(error="Product not found."), 404
    booking_date = (d.get("date") or "").strip()
    if not booking_date:
        return jsonify(error="Please select a booking date."), 400
    from datetime import date as _date
    try:
        if _date.fromisoformat(booking_date) < _date.today():
            return jsonify(error="Booking date cannot be in the past."), 400
    except ValueError:
        return jsonify(error="Invalid date format."), 400
    # phone is optional here (the website has no phone field); the mobile app
    # enforces phone client-side before sending.
    db.add_booking(cur_uid(), p, booking_date, d.get("size", "M"),
                   d.get("phone", ""), d.get("note", ""))
    return jsonify(ok=True, bookings_count=db.count_bookings(cur_uid()))


@app.route("/api/booking/cancel", methods=["POST"])
@login_required
def api_cancel_booking():
    bid = (request.json or {}).get("id")
    ok = db.cancel_booking(cur_uid(), bid)
    return jsonify(ok=ok, bookings_count=db.count_bookings(cur_uid()))


@app.route("/api/booking/confirm", methods=["POST"])
@login_required
def api_confirm_booking():
    bid = (request.json or {}).get("id")
    ok = db.confirm_booking(cur_uid(), bid)
    return jsonify(ok=ok)


@app.route("/api/me")
@login_required
def api_me():
    u = db.get_user_by_id(cur_uid()) or {}
    return jsonify(name=u.get("full_name", cur_uname()), email=u.get("email", ""),
                   joined=(u.get("created_at", "") or "")[:10],
                   bookings=db.count_bookings(cur_uid()))


@app.route("/api/profile/update", methods=["POST"])
@login_required
def api_profile_update():
    d = request.json or {}
    name = (d.get("full_name") or "").strip()
    email = (d.get("email") or "").strip()
    if not name:
        return jsonify(error="Full name cannot be empty."), 400
    if not EMAIL_RE.match(email):
        return jsonify(error="Invalid email format."), 400
    ok, msg = db.update_profile(cur_uid(), name, email)
    if not ok:
        return jsonify(error=msg), 409
    session["uname"] = name
    return jsonify(ok=True, name=name, email=email)


@app.route("/api/feedback", methods=["POST"])
@login_required
def api_feedback():
    d = request.json or {}
    pid = d.get("product_id")
    if not product_by_id(pid):
        return jsonify(error="Product not found."), 404
    db.add_feedback(cur_uid(), cur_uname(), pid,
                    int(d.get("rating", 0) or 0), d.get("experience", ""),
                    (d.get("message") or "").strip(), d.get("recommend", ""))
    return jsonify(ok=True)


# ---- JSON endpoints used by the mobile app ----
@app.route("/api/product/<pid>")
@login_required
def api_product(pid):
    p = product_by_id(pid, request.args.get("score", type=int))
    if not p:
        return jsonify(error="Product not found."), 404
    similar = []
    try:
        seg = str(engine.meta["seg_path"][PID_TO_IDX[pid]])
        for r in engine.search_by_seg(seg, k=6):
            if r["product_id"] != pid:
                similar.append(_format([r])[0])
        similar = similar[:4]
    except Exception:
        similar = []
    return jsonify(product=p, similar=similar, reviews=db.list_feedback(pid))


@app.route("/api/bookings")
@login_required
def api_bookings():
    items = db.list_bookings(cur_uid())
    for b in items:
        b["img_url"] = f"/pimg/{b['product_id']}"
        b["booking_id"] = f"#BK{10000 + int(b['id'])}"
        b["status"] = b.get("status") or "Pending"
        b["size"] = b.get("size") or "M"
    return jsonify(bookings=items, count=len(items))


@app.route("/pimg/<product_id>")
def product_image(product_id):
    p = PID_TO_IMG.get(product_id)
    if not p or not os.path.exists(p):
        abort(404)
    return send_file(p)


@app.before_request
def _preflight():
    if request.method == "OPTIONS":
        return ("", 204)


if __name__ == "__main__":
    # 0.0.0.0 so a phone on the same WiFi can reach it (use the laptop's LAN IP)
    print("Smart Style Finder running at http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
