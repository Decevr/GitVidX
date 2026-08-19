const AGE_KEY = "gitimgx-age-ok";
const SAVE_KEY = "gitimgx-saved-videos";
const DAILY_Q = "__daily__";
const DAILY_KEY = "gitvidx-daily-v1";

const gate = document.getElementById("age-gate");
const app = document.getElementById("app");
const form = document.getElementById("search-form");
const input = document.getElementById("search-input");
const hero = document.getElementById("hero");
const moreLabel = document.getElementById("more-label");
const grid = document.getElementById("grid");
const empty = document.getElementById("empty");
const moreBtn = document.getElementById("more-btn");
const statusLine = document.getElementById("status-line");
const progress = document.getElementById("progress");
const viewer = document.getElementById("viewer");
const viewerFrame = document.getElementById("viewer-frame");
const viewerFallback = document.getElementById("viewer-fallback");
const viewerCap = document.getElementById("viewer-cap");
const viewerOpen = document.getElementById("viewer-open");
const viewerSave = document.getElementById("viewer-save");
const viewerFull = document.getElementById("viewer-full");
const refreshBtn = document.getElementById("refresh-btn");
const quickRow = document.getElementById("quick-row");
const presetRow = document.getElementById("preset-row");
const sourceRow = document.getElementById("source-row");
const catToggle = document.getElementById("cat-toggle");
const siteToggle = document.getElementById("site-toggle");
const catPanel = document.getElementById("cat-panel");
const sitePanel = document.getElementById("site-panel");
const catLabel = document.getElementById("cat-label");
const siteLabel = document.getElementById("site-label");

const HAIR = new Set([
  "blonde", "brunette", "redhead", "black hair", "auburn", "platinum",
  "grey", "pink hair", "blue hair", "purple hair",
]);
const CAMERA = new Set([
  "fly on the wall", "third person", "close up", "full body", "overhead",
  "low angle", "side view", "behind camera", "face cam", "looking at camera",
  "mirror", "handheld", "tripod", "gopro", "selfie cam", "two camera",
  "cinematic", "over the shoulder", "wide shot",
]);
const MAX_FILTERS = 4;

const state = {
  query: DAILY_Q,
  filters: [],
  source: "all",
  page: 0,
  items: [],
  index: 0,
  loading: false,
  done: false,
};

function isDailyQuery(query) {
  return (query || "") === DAILY_Q;
}

function inDaily() {
  return !state.filters.length && isDailyQuery(state.query);
}

function inSaved() {
  return !state.filters.length && state.query === "favorites";
}

function searchQuery() {
  return state.filters.length ? state.filters.join(" ") : state.query;
}

function localDay() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function dailyCacheKey(source) {
  return `${DAILY_KEY}:${localDay()}:${source || "all"}`;
}

function readDailyCache(source) {
  try {
    const raw = JSON.parse(localStorage.getItem(dailyCacheKey(source)) || "null");
    if (raw && raw.date === localDay() && Array.isArray(raw.items) && raw.items.length) {
      return raw;
    }
  } catch {
    return null;
  }
  return null;
}

function writeDailyCache(source, data) {
  try {
    localStorage.setItem(dailyCacheKey(source), JSON.stringify({
      date: data.date || localDay(),
      items: data.items || [],
      sources: data.sources || [],
    }));
  } catch {
    // ignore quota errors
  }
}

function dailyStatus(count, date) {
  const when = date || localDay();
  const pretty = new Date(`${when}T12:00:00`).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
  if (state.source !== "all") {
    return `Today on ${state.source} · ${pretty} · ${count} videos`;
  }
  return `Today's featured · ${pretty} · ${count} videos`;
}

function savedMap() {
  try {
    return JSON.parse(localStorage.getItem(SAVE_KEY) || "{}");
  } catch {
    return {};
  }
}

function isSaved(id) {
  return Boolean(savedMap()[id]);
}

function toggleSave(item) {
  const map = savedMap();
  if (map[item.id]) delete map[item.id];
  else map[item.id] = item;
  localStorage.setItem(SAVE_KEY, JSON.stringify(map));
}

function setStatus(text) {
  statusLine.textContent = text;
}

function setBusy(on) {
  if (progress) progress.hidden = !on;
  if (refreshBtn) {
    refreshBtn.hidden = inSaved();
    refreshBtn.disabled = on;
    refreshBtn.textContent = on ? "Updating…" : "Refresh";
  }
}

function hasNativeApi() {
  const host = location.hostname;
  if (host === "appassets.androidplatform.net") return true;
  if (location.protocol === "gitvidx:") return true;
  if (host === "127.0.0.1" || host === "localhost") return true;
  if (/^\d+\.\d+\.\d+\.\d+$/.test(host)) return true;
  return false;
}

function rewriteThumb(url) {
  return String(url || "")
    .replace("ei-ph.rdtcdn.com", "ei.phncdn.com")
    .replace(".rdtcdn.com", ".phncdn.com");
}

function proxy(url, referer) {
  const src = rewriteThumb(url);
  if (!src) return "";
  if (!hasNativeApi()) return src;
  return `/api/img?url=${encodeURIComponent(src)}${referer ? `&ref=${encodeURIComponent(referer)}` : ""}`;
}

function openExternal(url) {
  if (!url) return;
  if (window.GitImgX && typeof window.GitImgX.openUrl === "function") {
    window.GitImgX.openUrl(url);
    return;
  }
  window.open(url, "_blank", "noopener,noreferrer");
}

function bindThumb(img, item) {
  if (!img) return;
  img.addEventListener("error", () => {
    if (img.dataset.tried) {
      img.replaceWith(Object.assign(document.createElement("div"), { className: "thumb-empty" }));
      return;
    }
    img.dataset.tried = "1";
    img.src = item.thumb;
  });
}

function bindCard(card, item) {
  card.addEventListener("click", (event) => {
    if (event.target.closest(".heart")) {
      toggleSave(item);
      event.target.classList.toggle("on", isSaved(item.id));
      const other = document.querySelector(`.heart[data-id="${item.id}"]`);
      if (other && other !== event.target) other.classList.toggle("on", isSaved(item.id));
      return;
    }
    openViewer(state.items.indexOf(item));
  });
}

function showSkeletons() {
  hero.hidden = false;
  hero.className = "hero skeleton";
  hero.innerHTML = "";
  moreLabel.hidden = true;
  grid.innerHTML = "";
  for (let i = 0; i < 4; i += 1) {
    const card = document.createElement("article");
    card.className = "card skeleton";
    grid.appendChild(card);
  }
  empty.hidden = true;
}

function renderHero(item) {
  hero.hidden = !item;
  hero.className = "hero";
  if (!item) {
    hero.innerHTML = "";
    return;
  }
  const thumb = item.thumb ? proxy(item.thumb, item.page || item.url) : "";
  hero.innerHTML = `
    <article class="hero-card" data-id="${item.id}">
      <div class="thumb-wrap">
        ${thumb ? `<img decoding="async" alt="" src="${thumb}" />` : `<div class="thumb-empty"></div>`}
      </div>
      <div class="play" aria-hidden="true"><span>▶</span></div>
      <div class="hero-copy">
        <p class="title">${escapeHtml(item.title || "Untitled")}</p>
        <div class="meta">
          <span class="badge">${escapeHtml(item.provider || item.source)}</span>
          <span class="badge">${escapeHtml(item.duration || "VIDEO")}</span>
        </div>
      </div>
      <button type="button" class="heart${isSaved(item.id) ? " on" : ""}" data-id="${item.id}" aria-label="Save">♥</button>
    </article>
  `;
  bindThumb(hero.querySelector("img"), item);
  bindCard(hero.querySelector(".hero-card"), item);
}

function runtimeText(item) {
  const value = String(item.duration || "").trim();
  if (!value || value.toUpperCase() === "VIDEO") return "";
  return value;
}

function makePoster(item) {
  const card = document.createElement("article");
  card.className = "card video-card";
  card.dataset.id = item.id;
  const thumb = item.thumb ? proxy(item.thumb, item.page || item.url) : "";
  const runtime = runtimeText(item);
  card.innerHTML = `
    <div class="thumb-wrap">
      ${thumb ? `<img loading="lazy" decoding="async" alt="" src="${thumb}" />` : `<div class="thumb-empty"></div>`}
      <button type="button" class="heart${isSaved(item.id) ? " on" : ""}" data-id="${item.id}" aria-label="Save">♥</button>
    </div>
    <div class="card-foot">
      <p class="title">${escapeHtml(item.title || "Untitled")}</p>
      <p class="runtime">${runtime ? escapeHtml(runtime) : "Runtime unavailable"}</p>
    </div>
  `;
  bindThumb(card.querySelector("img"), item);
  bindCard(card, item);
  return card;
}

function render(reset) {
  const hasItems = state.items.length > 0;
  empty.hidden = hasItems;
  moreBtn.hidden = state.done || !hasItems || inSaved() || inDaily();
  moreLabel.hidden = !hasItems || state.items.length < 2;

  if (reset || hero.classList.contains("skeleton") || !hero.querySelector(".hero-card")) {
    renderHero(state.items[0] || null);
    grid.innerHTML = "";
    const frag = document.createDocumentFragment();
    for (const item of state.items.slice(1)) frag.appendChild(makePoster(item));
    grid.appendChild(frag);
    return;
  }

  const have = 1 + grid.querySelectorAll(".video-card").length;
  const frag = document.createDocumentFragment();
  for (const item of state.items.slice(have)) frag.appendChild(makePoster(item));
  grid.appendChild(frag);
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function setOpen(el, on) {
  if (!el) return;
  el.hidden = !on;
  el.classList.toggle("open", on);
}

function isFullscreen() {
  return Boolean(document.fullscreenElement || document.webkitFullscreenElement || viewer.classList.contains("cinema"));
}

function setFullscreen(on) {
  const node = viewer;
  if (on) {
    viewer.classList.add("cinema");
    if (viewerFull) viewerFull.textContent = "Exit full screen";
    const request = node.requestFullscreen || node.webkitRequestFullscreen;
    if (request) request.call(node).catch(() => {});
    return;
  }
  viewer.classList.remove("cinema");
  if (viewerFull) viewerFull.textContent = "Fullscreen";
  const exit = document.exitFullscreen || document.webkitExitFullscreen;
  if (document.fullscreenElement || document.webkitFullscreenElement) {
    exit.call(document).catch(() => {});
  }
}

function openViewer(index) {
  if (index < 0 || index >= state.items.length) return;
  state.index = index;
  const item = state.items[index];
  setFullscreen(false);
  setOpen(viewer, true);
  viewerCap.textContent = [item.title, item.provider, runtimeText(item)].filter(Boolean).join(" · ");
  viewerSave.textContent = isSaved(item.id) ? "Saved" : "Save";
  if (item.embed) {
    viewerFallback.hidden = true;
    viewerFrame.hidden = false;
    viewerFrame.src = item.embed;
    if (viewerFull) viewerFull.hidden = false;
  } else {
    viewerFrame.hidden = true;
    viewerFrame.src = "";
    viewerFallback.hidden = false;
    if (viewerFull) viewerFull.hidden = true;
  }
}

function closeViewer() {
  setFullscreen(false);
  setOpen(viewer, false);
  viewerFrame.src = "";
}

async function search(reset, forceRefresh) {
  if (state.loading) return;
  if (reset) {
    state.page = 0;
    state.items = [];
    state.done = false;
    showSkeletons();
  }
  if (inSaved()) {
    state.items = Object.values(savedMap());
    state.done = true;
    setBusy(false);
    setStatus(state.items.length ? `${state.items.length} saved` : "No saved videos yet.");
    render(true);
    return;
  }

  if (reset && inDaily() && !forceRefresh) {
    const cached = readDailyCache(state.source);
    if (cached) {
      state.items = cached.items;
      state.done = true;
      setBusy(false);
      setStatus(dailyStatus(state.items.length, cached.date));
      render(true);
      return;
    }
  }

  state.loading = true;
  setBusy(true);
  setStatus(reset && inDaily()
    ? (forceRefresh ? "Refreshing today's featured videos…" : "Capturing today's featured videos…")
    : forceRefresh ? "Refreshing search results…"
    : reset ? "Searching tube sites…" : "Loading more…");
  try {
    const params = new URLSearchParams({
      q: searchQuery(),
      source: state.source,
      page: String(state.page),
    });
    if (state.filters.length) params.set("tags", state.filters.join(","));
    if (forceRefresh) params.set("refresh", "1");
    let data;
    if (!hasNativeApi() && window.GitVidXSearch) {
      data = await window.GitVidXSearch.search({
        q: params.get("q"),
        source: params.get("source"),
        page: params.get("page"),
        tags: params.get("tags") || "",
        refresh: forceRefresh
      });
    } else {
      const response = await fetch(`/api/search?${params}`);
      data = await response.json();
      if (!response.ok) throw new Error(data.error || "Search failed");
    }
    const seen = new Set(state.items.map((item) => item.id));
    const next = (data.items || []).filter((item) => (item.page || item.url) && !seen.has(item.id));
    state.items.push(...next);
    state.page += 1;
    state.done = !data.next || inDaily();
    if (inDaily() && reset && state.items.length) {
      writeDailyCache(state.source, { date: data.date || localDay(), items: state.items, sources: data.sources || [] });
    }
    const countLabel = inDaily()
      ? (state.items.length
        ? dailyStatus(state.items.length, data.date)
        : data.error || "No featured videos captured yet.")
      : next.length || state.items.length
        ? `${state.items.length} videos`
        : data.error || "No public videos found for that search.";
    setStatus(forceRefresh && state.items.length ? `Updated · ${countLabel}` : countLabel);
    render(reset);
  } catch (error) {
    setStatus(error.message || "Search failed");
    if (reset) render(true);
  } finally {
    state.loading = false;
    setBusy(false);
  }
}

function setChipState(row, attr, value) {
  if (!row) return;
  for (const button of row.querySelectorAll("button")) {
    button.classList.toggle("on", button.dataset[attr] === value);
  }
}

function setFilterChips(row) {
  if (!row) return;
  for (const button of row.querySelectorAll("button[data-q]")) {
    const key = button.dataset.q;
    const on = inDaily()
      ? key === DAILY_Q
      : inSaved()
        ? key === "favorites"
        : state.filters.includes(key);
    button.classList.toggle("on", on);
  }
}

function chipLabel(row, attr, value, fallback) {
  if (!row) return fallback;
  for (const button of row.querySelectorAll("button")) {
    if (button.dataset[attr] === value) return button.textContent.trim();
  }
  return fallback;
}

function syncFilters() {
  setFilterChips(quickRow);
  setFilterChips(presetRow);
  setChipState(sourceRow, "source", state.source);
  if (catLabel) {
    if (inDaily()) catLabel.textContent = "Today";
    else if (inSaved()) catLabel.textContent = "Saved";
    else if (state.filters.length) {
      catLabel.textContent = state.filters
        .map((key) => chipLabel(presetRow, "q", key, key))
        .join(" · ");
    } else {
      catLabel.textContent = chipLabel(presetRow, "q", state.query, state.query || "Search");
    }
  }
  if (siteLabel) {
    siteLabel.textContent = chipLabel(sourceRow, "source", state.source, "All sites");
  }
}

function setPanel(panel, toggle, open) {
  if (!panel || !toggle) return;
  panel.hidden = !open;
  toggle.setAttribute("aria-expanded", open ? "true" : "false");
}

function closePanels() {
  setPanel(catPanel, catToggle, false);
  setPanel(sitePanel, siteToggle, false);
}

function togglePanel(which) {
  const catOpen = which === "cat" && catPanel && catPanel.hidden;
  const siteOpen = which === "site" && sitePanel && sitePanel.hidden;
  setPanel(catPanel, catToggle, catOpen);
  setPanel(sitePanel, siteToggle, siteOpen);
}

document.getElementById("age-yes").addEventListener("click", () => {
  localStorage.setItem(AGE_KEY, "1");
  enterApp();
});

document.getElementById("age-no").addEventListener("click", () => {
  document.body.innerHTML = `<div class="blocked"><p>GitVidX is only for adults 18+.</p></div>`;
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const query = input.value.trim();
  state.filters = [];
  state.query = query || DAILY_Q;
  closePanels();
  syncFilters();
  search(true);
});

function pickCategory(nextQuery, fromPanel) {
  if (nextQuery === DAILY_Q || nextQuery === "favorites") {
    const refreshToday = nextQuery === DAILY_Q && inDaily();
    state.filters = [];
    state.query = nextQuery;
    input.value = "";
    closePanels();
    syncFilters();
    search(true, refreshToday);
    return;
  }
  if (HAIR.has(nextQuery)) {
    state.filters = state.filters.filter((key) => !HAIR.has(key));
    state.filters.push(nextQuery);
  } else if (CAMERA.has(nextQuery)) {
    state.filters = state.filters.filter((key) => !CAMERA.has(key));
    state.filters.push(nextQuery);
  } else if (state.filters.includes(nextQuery)) {
    state.filters = state.filters.filter((key) => key !== nextQuery);
  } else {
    if (state.filters.length >= MAX_FILTERS) state.filters.shift();
    state.filters.push(nextQuery);
  }
  state.query = state.filters[0] || DAILY_Q;
  input.value = "";
  if (!fromPanel) closePanels();
  syncFilters();
  search(true);
}

function clearFilters() {
  state.filters = [];
  state.query = DAILY_Q;
  input.value = "";
  syncFilters();
  search(true);
}

if (quickRow) {
  quickRow.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-q]");
    if (button) pickCategory(button.dataset.q);
  });
}

if (presetRow) {
  presetRow.addEventListener("click", (event) => {
    if (event.target.closest("#clear-filters")) {
      clearFilters();
      return;
    }
    const button = event.target.closest("button[data-q]");
    if (button) pickCategory(button.dataset.q, true);
  });
}

if (sourceRow) {
  sourceRow.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-source]");
    if (!button) return;
    state.source = button.dataset.source;
    closePanels();
    syncFilters();
    if (!inSaved()) search(true);
  });
}

if (catToggle) catToggle.addEventListener("click", () => togglePanel("cat"));
if (siteToggle) siteToggle.addEventListener("click", () => togglePanel("site"));

if (refreshBtn) {
  refreshBtn.addEventListener("click", () => {
    if (inSaved()) return;
    search(true, true);
  });
}
moreBtn.addEventListener("click", () => search(false));
if ("IntersectionObserver" in window) {
  new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) search(false);
  }, { rootMargin: "240px" }).observe(moreBtn);
}
document.getElementById("viewer-close").addEventListener("click", closeViewer);
if (viewerFull) {
  viewerFull.addEventListener("click", () => setFullscreen(!isFullscreen()));
}
document.addEventListener("fullscreenchange", () => {
  if (!document.fullscreenElement && !document.webkitFullscreenElement) {
    viewer.classList.remove("cinema");
    if (viewerFull) viewerFull.textContent = "Fullscreen";
  }
});
document.getElementById("viewer-prev").addEventListener("click", () => openViewer(state.index - 1));
document.getElementById("viewer-next").addEventListener("click", () => openViewer(state.index + 1));
viewerSave.addEventListener("click", () => {
  const item = state.items[state.index];
  if (!item) return;
  toggleSave(item);
  viewerSave.textContent = isSaved(item.id) ? "Saved" : "Save";
  for (const heart of document.querySelectorAll(`.heart[data-id="${item.id}"]`)) {
    heart.classList.toggle("on", isSaved(item.id));
  }
});
viewerOpen.addEventListener("click", () => {
  const item = state.items[state.index];
  if (item) openExternal(item.page || item.url);
});
document.addEventListener("keydown", (event) => {
  if (viewer.hidden) return;
  if (event.key === "Escape") closeViewer();
  if (event.key === "ArrowLeft") openViewer(state.index - 1);
  if (event.key === "ArrowRight") openViewer(state.index + 1);
});

function enterApp() {
  setOpen(gate, false);
  setOpen(app, true);
  setOpen(viewer, false);
  input.value = inDaily() || inSaved() || state.filters.length ? "" : state.query;
  syncFilters();
  search(true);
}

setOpen(viewer, false);
if (localStorage.getItem(AGE_KEY) === "1") enterApp();
else setStatus("Confirm you are 18+ to search.");

if ("serviceWorker" in navigator && location.protocol.startsWith("http") && location.hostname !== "appassets.androidplatform.net") {
  navigator.serviceWorker.register("./sw.js").catch(() => {});
}

window.DE_onBack = function () {
  if (viewer && !viewer.hidden && isFullscreen()) {
    setFullscreen(false);
    return true;
  }
  if (viewer && !viewer.hidden) {
    closeViewer();
    return true;
  }
  if ((catPanel && !catPanel.hidden) || (sitePanel && !sitePanel.hidden)) {
    closePanels();
    return true;
  }
  return false;
};
