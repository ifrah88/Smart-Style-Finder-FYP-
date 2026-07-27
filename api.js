import axios from "axios";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { API_BASE_URL } from "./config";

const client = axios.create({ timeout: 60000 });

// Backend address: the ngrok URL in config.js by default, overridable in-app via
// "Server settings" (persisted on the device). No Expo/dev-server dependency.
let TOKEN = null;
let NAME = null;
let BASE = API_BASE_URL;

function normalizeUrl(u) {
  u = (u || "").trim().replace(/\/+$/, "");
  if (u && !/^https?:\/\//i.test(u)) u = "http://" + u;
  return u;
}

// set the base URL of every request + attach the auth token
client.interceptors.request.use(async (cfg) => {
  cfg.baseURL = BASE;
  cfg.headers["ngrok-skip-browser-warning"] = "true"; // pass ngrok's free warning page
  if (!TOKEN) TOKEN = await AsyncStorage.getItem("ssf_token");
  if (TOKEN) cfg.headers["X-Auth-Token"] = TOKEN;
  return cfg;
});

function imgUrl(path) {
  if (!path) return null;
  return path.startsWith("http") ? path : BASE + path;
}

async function setSession(token, name) {
  TOKEN = token; NAME = name;
  await AsyncStorage.multiSet([["ssf_token", token], ["ssf_name", name || ""]]);
}

export const api = {
  imgUrl,

  // ---- configurable backend address (survives app restarts) ----
  getBaseUrl() { return BASE; },
  async setBaseUrl(url) {
    BASE = normalizeUrl(url) || API_BASE_URL;
    await AsyncStorage.setItem("ssf_base_url", BASE);
    return BASE;
  },

  async restore() {
    // user override (Server settings) wins; otherwise the config.js ngrok default
    const savedBase = await AsyncStorage.getItem("ssf_base_url");
    BASE = savedBase || API_BASE_URL;
    TOKEN = await AsyncStorage.getItem("ssf_token");
    NAME = await AsyncStorage.getItem("ssf_name");
    return TOKEN ? { token: TOKEN, name: NAME } : null;
  },
  getName() { return NAME; },

  async login(email, password) {
    const { data } = await client.post("/api/login", { email, password });
    await setSession(data.token, data.name);
    return data;
  },
  async register(full_name, email, password, confirm) {
    const { data } = await client.post("/api/register",
      { full_name, email, password, confirm, terms: true });
    await setSession(data.token, data.name);
    return data;
  },
  async logout() {
    TOKEN = null; NAME = null;
    await AsyncStorage.multiRemove(["ssf_token", "ssf_name"]);
  },
  async forgot(email, password) {
    const { data } = await client.post("/api/forgot", { email, password });
    return data;
  },
  async me() {
    const { data } = await client.get("/api/me");
    return data;
  },
  async updateProfile(full_name, email) {
    const { data } = await client.post("/api/profile/update", { full_name, email });
    if (data.ok) { NAME = full_name; await AsyncStorage.setItem("ssf_name", full_name); }
    return data;
  },
  async cancelBooking(id) {
    const { data } = await client.post("/api/booking/cancel", { id });
    return data;
  },
  async confirmBooking(id) {
    const { data } = await client.post("/api/booking/confirm", { id });
    return data;
  },

  async trending(page = 1) {
    const { data } = await client.get(`/api/trending?page=${page}`);
    return data;
  },
  async searchText(query) {
    const { data } = await client.post("/api/search/text", { query });
    return data;
  },
  async searchImage(uri) {
    const name = uri.split("/").pop() || "photo.jpg";
    const type = "image/" + (name.split(".").pop() || "jpeg").toLowerCase();
    const form = new FormData();
    form.append("image", { uri, name, type });
    const { data } = await client.post("/api/search/image", form,
      { headers: { "Content-Type": "multipart/form-data" } });
    return data;
  },
  async product(pid, score) {
    const q = score != null ? `?score=${score}` : "";
    const { data } = await client.get(`/api/product/${encodeURIComponent(pid)}${q}`);
    return data;
  },
  async bookings() {
    const { data } = await client.get("/api/bookings");
    return data;
  },
  async book(product_id, date, size, phone, note) {
    const { data } = await client.post("/api/booking", { product_id, date, size, phone, note });
    return data;
  },
  async feedback(product_id, rating, experience, message, recommend) {
    const { data } = await client.post("/api/feedback",
      { product_id, rating, experience, message, recommend });
    return data;
  },
};

export function errText(e) {
  return e?.response?.data?.error || e?.message || "Something went wrong.";
}
