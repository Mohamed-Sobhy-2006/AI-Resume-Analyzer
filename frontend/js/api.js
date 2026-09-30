/* Shared helpers + reusable API functions (fetch). Loaded on every page. */
const API_BASE = location.protocol === "file:" ? "http://127.0.0.1:8000" : "";

class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

/* ---------- small UI helpers ---------- */
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function $(id) { return document.getElementById(id); }
function showAlert(id, message, type = "error") {
  const box = $(id);
  if (box) box.innerHTML = message ? `<div class="alert ${type}">${esc(message)}</div>` : "";
}
function setLoading(button, loading, text) {
  if (!button) return;
  if (loading) { button.dataset.label = button.innerHTML; button.disabled = true; button.innerHTML = `<span class="spinner"></span>${esc(text || "Working...")}`; }
  else { button.disabled = false; button.innerHTML = button.dataset.label || button.innerHTML; }
}
function loadingHtml(text = "Loading...") { return `<p class="muted"><span class="spinner"></span>${esc(text)}</p>`; }
function chips(list, cls = "") {
  return (list && list.length) ? list.map(s => `<span class="chip ${cls}">${esc(s)}</span>`).join("") : `<span class="muted">None found</span>`;
}
function bullets(list) {
  return (list && list.length) ? `<ul class="clean">${list.map(s => `<li>${esc(s)}</li>`).join("")}</ul>` : `<p class="muted">None found</p>`;
}
function scoreBar(score) {
  const cls = score >= 70 ? "" : score >= 40 ? "mid" : "low";
  return `<div class="bar ${cls}" title="${score}%"><span style="width:${score}%"></span></div>`;
}
function formatDate(iso) { return iso ? new Date(iso + (iso.endsWith("Z") ? "" : "Z")).toLocaleString() : ""; }

/* ---------- session ---------- */
function getToken() { return localStorage.getItem("token"); }
function getUser() { try { return JSON.parse(localStorage.getItem("user")); } catch (e) { return null; } }
function clearSession() { localStorage.removeItem("token"); localStorage.removeItem("user"); localStorage.removeItem("resumeId"); }
function requireAuth() { if (!getToken()) { window.location = "login.html"; return false; } return true; }
function getResumeId() { return localStorage.getItem("resumeId"); }
function setResumeId(id) { localStorage.setItem("resumeId", id); }

function renderNav(active) {
  const links = [["dashboard.html", "Dashboard", "📊"], ["resume.html", "Resume", "📄"], ["analysis.html", "Analysis", "🔍"],
                 ["jobs.html", "Jobs", "💼"], ["career.html", "Career Advisor", "🚀"]];
  const user = getUser();
  const loggedIn = !!getToken();
  $("nav").innerHTML = `<nav class="topbar"><a class="brand" href="index.html"><span class="ico">🧠</span>AI Resume Analyzer</a>` +
    (loggedIn ? links.map(([href, label, icon]) => `<a class="link ${active === href ? "active" : ""}" href="${href}"><span class="ico">${icon}</span>${label}</a>`).join("") : "") +
    `<span class="spacer"></span>` +
    (loggedIn ? `<span class="link" style="color:#f5d0fe">👤 ${esc(user ? user.name : "")}</span><a class="link" href="#" id="logoutLink"><span class="ico">🚪</span>Logout</a>`
              : `<a class="link" href="login.html"><span class="ico">🔑</span>Login</a><a class="link" href="register.html"><span class="ico">✨</span>Register</a>`) + `</nav>`;
  const out = $("logoutLink");
  if (out) out.addEventListener("click", async e => { e.preventDefault(); await Api.logout(); window.location = "login.html"; });
}

/* ---------- core request function ---------- */
async function apiRequest(path, { method = "GET", body = null, form = null, auth = true } = {}) {
  const headers = {};
  if (auth && getToken()) headers["Authorization"] = "Bearer " + getToken();
  let payload;
  if (form) payload = form;
  else if (body) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
  let response;
  try { response = await fetch(API_BASE + path, { method, headers, body: payload }); }
  catch (e) { throw new ApiError("Cannot reach the server. Make sure run.bat is running.", 0); }
  if (response.status === 401 && auth) {                       // token missing/expired
    clearSession();
    window.location = "login.html";
    throw new ApiError("Your session has expired. Please log in again.", 401);
  }
  let data = null;
  try { data = await response.json(); } catch (e) { /* no body */ }
  if (!response.ok) throw new ApiError((data && data.detail) || `Request failed (${response.status}).`, response.status);
  return data;
}

/* ---------- reusable API functions ---------- */
const Api = {
  register: (name, email, password, confirm_password) =>
    apiRequest("/api/auth/register", { method: "POST", auth: false, body: { name, email, password, confirm_password } }),
  async login(email, password) {
    const data = await apiRequest("/api/auth/login", { method: "POST", auth: false, body: { email, password } });
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("user", JSON.stringify(data.user));
    return data;
  },
  async logout() {
    try { await fetch(API_BASE + "/api/auth/logout", { method: "POST", headers: { Authorization: "Bearer " + getToken() } }); } catch (e) { /* ignore */ }
    clearSession();
  },
  uploadResume(file) { const form = new FormData(); form.append("file", file); return apiRequest("/api/resumes/upload", { method: "POST", form }); },
  listResumes: () => apiRequest("/api/resumes"),
  getResume: id => apiRequest(`/api/resumes/${id}`),
  deleteResume: id => apiRequest(`/api/resumes/${id}`, { method: "DELETE" }),
  analyzeResume: id => apiRequest(`/api/analysis/resume/${id}`, { method: "POST" }),
  getAnalysis: id => apiRequest(`/api/analysis/resume/${id}`),
  getJobs: (params = {}) => {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v && String(v).trim())).toString();
    return apiRequest("/api/jobs" + (q ? "?" + q : ""), { auth: false });
  },
  searchJobs(params) { return this.getJobs(params); },
  createJob: job => apiRequest("/api/jobs", { method: "POST", body: job }),
  updateJob: (id, job) => apiRequest(`/api/jobs/${id}`, { method: "PUT", body: job }),
  deleteJob: id => apiRequest(`/api/jobs/${id}`, { method: "DELETE" }),
  getRecommendations: (id, refresh = false) => apiRequest(`/api/recommendations/resume/${id}?refresh=${refresh}`),
  getDashboard: () => apiRequest("/api/recommendations/dashboard"),
  getCareerAdvice: (resume_id, question) => apiRequest("/api/career/advice", { method: "POST", body: { resume_id, question } }),
  getCareerStatus: () => apiRequest("/api/career/status"),
};

/* Returns the selected resume id, or the newest resume of the user (null if none). */
async function ensureResumeId() {
  const resumes = await Api.listResumes();
  if (!resumes.length) return null;
  const saved = getResumeId();
  const found = resumes.find(r => String(r.id) === String(saved));
  const id = found ? found.id : resumes[0].id;
  setResumeId(id);
  return id;
}
