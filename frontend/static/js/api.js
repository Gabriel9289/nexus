const API = "http://127.0.0.1:8000";
let ws    = null;

// --- Storage ||||||||||||||-
const getToken  = ()  => localStorage.getItem("nx_token");
const setToken  = (t) => localStorage.setItem("nx_token", t);
const getUser   = ()  => JSON.parse(localStorage.getItem("nx_user") || "null");
const setUser   = (u) => localStorage.setItem("nx_user", JSON.stringify(u));
const clearAuth = ()  => { localStorage.removeItem("nx_token"); localStorage.removeItem("nx_user"); };
const isLoggedIn = () => !!getToken();

const authHeaders = () => ({
  "Content-Type":  "application/json",
  "Authorization": `Bearer ${getToken()}`
});

const jsonHeaders = () => ({ "Content-Type": "application/json" });

// --- Auth ||||||||||||||----
async function apiRegister(data) {
  const r = await fetch(`${API}/auth/register`, {
    method: "POST", headers: jsonHeaders(), body: JSON.stringify(data)
  });
  return [r.status, await r.json()];
}

async function apiLogin(email, password) {
  const r = await fetch(`${API}/auth/login`, {
    method: "POST", headers: jsonHeaders(),
    body: JSON.stringify({ email, password })
  });
  return [r.status, await r.json()];
}

async function apiMe() {
  const r = await fetch(`${API}/auth/me`, { headers: authHeaders() });
  return [r.status, await r.json()];
}

// --- Tweets ||||||||||||||--
async function apiPostTweet(body, reply_to_id = null) {
  const r = await fetch(`${API}/tweets/`, {
    method: "POST", headers: authHeaders(),
    body: JSON.stringify({ body, reply_to_id })
  });
  return [r.status, await r.json()];
}

async function apiGetTweet(id) {
  const r = await fetch(`${API}/tweets/${id}`, { headers: authHeaders() });
  return [r.status, await r.json()];
}

async function apiDeleteTweet(id) {
  const r = await fetch(`${API}/tweets/${id}`, {
    method: "DELETE", headers: authHeaders()
  });
  return r.status;
}

async function apiGetFeed(skip = 0) {
  const r = await fetch(`${API}/tweets/?skip=${skip}`, { headers: authHeaders() });
  return [r.status, await r.json()];
}

async function apiExplore(skip = 0) {
  const r = await fetch(`${API}/tweets/explore/all?skip=${skip}`, { headers: authHeaders() });
  return [r.status, await r.json()];
}

async function apiGetReplies(tweet_id) {
  const r = await fetch(`${API}/tweets/${tweet_id}/replies`, { headers: authHeaders() });
  return [r.status, await r.json()];
}

async function apiLike(id) {
  const r = await fetch(`${API}/tweets/${id}/like`, {
    method: "POST", headers: authHeaders()
  });
  return [r.status, await r.json()];
}

async function apiRetweet(id) {
  const r = await fetch(`${API}/tweets/${id}/retweet`, {
    method: "POST", headers: authHeaders()
  });
  return [r.status, await r.json()];
}

async function apiBookmark(id) {
  const r = await fetch(`${API}/tweets/${id}/bookmark`, {
    method: "POST", headers: authHeaders()
  });
  return [r.status, await r.json()];
}

async function apiMyBookmarks() {
  const r = await fetch(`${API}/tweets/me/bookmarks`, { headers: authHeaders() });
  return [r.status, await r.json()];
}

async function apiTrending() {
  const r = await fetch(`${API}/tweets/hashtags/trending`);
  return [r.status, await r.json()];
}

async function apiSearch(q) {
  const r = await fetch(`${API}/tweets/search/query?q=${encodeURIComponent(q)}`, {
    headers: authHeaders()
  });
  return [r.status, await r.json()];
}

// --- Follows & Profiles --------------
async function apiGetProfile(username) {
  const r = await fetch(`${API}/users/${username}`, { headers: authHeaders() });
  return [r.status, await r.json()];
}

async function apiGetUserTweets(username) {
  const r = await fetch(`${API}/users/${username}/tweets`, { headers: authHeaders() });
  return [r.status, await r.json()];
}

async function apiGetUserLikes(username) {
  const r = await fetch(`${API}/users/${username}/likes`, { headers: authHeaders() });
  return [r.status, await r.json()];
}

async function apiFollow(username) {
  const r = await fetch(`${API}/users/${username}/follow`, {
    method: "POST", headers: authHeaders()
  });
  return [r.status, await r.json()];
}

async function apiGetFollowers(username) {
  const r = await fetch(`${API}/users/${username}/followers`, { headers: authHeaders() });
  return [r.status, await r.json()];
}

async function apiGetFollowing(username) {
  const r = await fetch(`${API}/users/${username}/following`, { headers: authHeaders() });
  return [r.status, await r.json()];
}

async function apiSuggestions() {
  const r = await fetch(`${API}/suggestions/who-to-follow`, { headers: authHeaders() });
  return [r.status, await r.json()];
}

// --- Notifications -------------------
async function apiGetNotifications() {
  const r = await fetch(`${API}/notifications/`, { headers: authHeaders() });
  return [r.status, await r.json()];
}

async function apiUnreadCount() {
  const r = await fetch(`${API}/notifications/unread`, { headers: authHeaders() });
  return [r.status, await r.json()];
}

async function apiMarkAllRead() {
  const r = await fetch(`${API}/notifications/read`, {
    method: "POST", headers: authHeaders()
  });
  return [r.status, await r.json()];
}

// --- WebSocket ----====-
function connectWS(onMessage) {
  if (!isLoggedIn()) return;
  ws = new WebSocket(`ws://127.0.0.1:8000/ws?token=${getToken()}`);

  ws.onopen = () => {
    console.log("Nexus WS connected");
    setInterval(() => {
      if (ws.readyState === WebSocket.OPEN)
        ws.send(JSON.stringify({ type: "ping" }));
    }, 25000);
  };

  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type !== "pong") onMessage(msg);
  };

  ws.onclose = () => {
    // Reconnect after 3 seconds
    setTimeout(() => connectWS(onMessage), 3000);
  };
}

// --- UI Helpers ----====
function showToast(msg, type = "") {
  let el = document.getElementById("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.className   = `toast ${type} show`;
  setTimeout(() => el.className = `toast ${type}`, 2800);
}

function timeAgo(iso) {
  const s = (Date.now() - new Date(iso)) / 1000;
  if (s < 60)    return `${Math.floor(s)}s`;
  if (s < 3600)  return `${Math.floor(s/60)}m`;
  if (s < 86400) return `${Math.floor(s/3600)}h`;
  return new Date(iso).toLocaleDateString("en-ZA", { day:"numeric", month:"short" });
}

function initTheme() {
  const t   = localStorage.getItem("nx_theme") || "dark";
  document.documentElement.setAttribute("data-theme", t === "light" ? "light" : "");
  const btn = document.getElementById("themeBtn");
  if (btn) btn.textContent = t === "light" ? "🌙" : "☀️";
}

function toggleTheme() {
  const light = document.documentElement.getAttribute("data-theme") === "light";
  const next  = light ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", next === "light" ? "light" : "");
  localStorage.setItem("nx_theme", next);
  const btn = document.getElementById("themeBtn");
  if (btn) btn.textContent = next === "light" ? "🌙" : "☀️";
}

function highlightHashtags(text) {
  return text.replace(
    /#(\w+)/g,
    `<span class="tweet-hashtag" onclick="event.stopPropagation();searchHashtag('$1')">#$1</span>`
  );
}

function searchHashtag(tag) {
  window.location.href = `index.html?q=%23${tag}`;
}

function avatarHTML(user, size = 42) {
  const letter = (user.display_name || user.username || "?")[0].toUpperCase();
  return `<div class="avatar" style="width:${size}px;height:${size}px"
              onclick="event.stopPropagation();window.location.href='profile.html?u=${user.username}'">
            ${letter}
          </div>`;
}

function tweetCardHTML(t, showReplyTo = false) {
  const user = getUser();
  const isOwn = user && user.id === t.author.id;
  return `
    <div class="tweet-card" id="tweet-${t.id}"
         onclick="window.location.href='tweet.html?id=${t.id}'">
      ${avatarHTML(t.author)}
      <div class="tweet-body">
        <div class="tweet-header">
          <span class="tweet-name"
                onclick="event.stopPropagation();window.location.href='profile.html?u=${t.author.username}'">
            ${t.author.display_name || t.author.username}
          </span>
          <span class="tweet-handle">@${t.author.username}</span>
          <span class="tweet-time">· ${timeAgo(t.created_at)}</span>
          ${isOwn ? `<span style="margin-left:auto">
            <button style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:18px"
                    onclick="event.stopPropagation();deleteTweet(${t.id})">🗑</button>
          </span>` : ""}
        </div>
        <div class="tweet-text">${highlightHashtags(t.body)}</div>
        <div class="tweet-actions">
          <button class="action-btn reply-btn"
                  onclick="event.stopPropagation();window.location.href='tweet.html?id=${t.id}'">
            💬 <span>${t.reply_count}</span>
          </button>
          <button class="action-btn rt-btn ${t.retweeted ? 'retweeted' : ''}"
                  onclick="event.stopPropagation();doRetweet(${t.id}, this)">
            🔁 <span>${t.retweet_count}</span>
          </button>
          <button class="action-btn like-btn ${t.liked ? 'liked' : ''}"
                  onclick="event.stopPropagation();doLike(${t.id}, this)">
            ${t.liked ? "❤️" : "🤍"} <span>${t.like_count}</span>
          </button>
          <button class="action-btn bm-btn ${t.bookmarked ? 'bookmarked' : ''}"
                  onclick="event.stopPropagation();doBookmark(${t.id}, this)">
            ${t.bookmarked ? "🔖" : "📎"}
          </button>
        </div>
      </div>
    </div>`;
}

async function deleteTweet(id) {
  const status = await apiDeleteTweet(id);
  if (status === 204) {
    document.getElementById(`tweet-${id}`)?.remove();
    showToast("Tweet deleted");
  }
}

async function doLike(id, btn) {
  if (!isLoggedIn()) { window.location.href = "login.html"; return; }
  const [, data] = await apiLike(id);
  const span = btn.querySelector("span");
  if (span) span.textContent = data.like_count;
  btn.classList.toggle("liked", data.liked);
  btn.innerHTML = `${data.liked ? "❤️" : "🤍"} <span>${data.like_count}</span>`;
}

async function doRetweet(id, btn) {
  if (!isLoggedIn()) { window.location.href = "login.html"; return; }
  const [status, data] = await apiRetweet(id);
  if (status === 400) { showToast(data.detail, "error"); return; }
  btn.classList.toggle("retweeted", data.retweeted);
  btn.querySelector("span").textContent = data.retweet_count;
}

async function doBookmark(id, btn) {
  if (!isLoggedIn()) { window.location.href = "login.html"; return; }
  const [, data] = await apiBookmark(id);
  btn.classList.toggle("bookmarked", data.bookmarked);
  btn.textContent = data.bookmarked ? "🔖" : "📎";
  showToast(data.bookmarked ? "Saved to bookmarks" : "Removed from bookmarks");
}