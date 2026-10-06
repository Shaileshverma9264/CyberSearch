"use strict";

const CONFIG = {
  endpoint: "/api/search",
  apiKey: "58c49cb2dbbf8dc53009705ecd7c4132",
  blockedFields: [
    "Aadhaar",
    "AadhaarNumber",
    "DocumentNumber",
    "Password",
    "Passcode",
    "Token",
    "Secret",
    "CreditCard",
    "CardNumber",
  ],
  maxHistory: 10,
};

const form = document.getElementById("searchForm");
const queryInput = document.getElementById("queryInput");
const searchButton = document.getElementById("searchButton");
const searchText = document.querySelector(".search-text");
const loader = document.querySelector(".loader");
const clearButton = document.getElementById("clearButton");
const stats = document.getElementById("stats");
const statQuery = document.getElementById("statQuery");
const statSources = document.getElementById("statSources");
const statRecords = document.getElementById("statRecords");
const statTime = document.getElementById("statTime");
const resultsSection = document.getElementById("resultsSection");
const sourcesContainer = document.getElementById("sourcesContainer");
const emptyState = document.getElementById("emptyState");
const errorBox = document.getElementById("errorBox");
const errorMessage = document.getElementById("errorMessage");
const closeError = document.getElementById("closeError");
const rawContainer = document.getElementById("rawContainer");
const rawJson = document.getElementById("rawJson");
const toggleRaw = document.getElementById("toggleRaw");
const copyJson = document.getElementById("copyJson");
const copyRaw = document.getElementById("copyRaw");
const historyList = document.getElementById("historyList");
const clearHistory = document.getElementById("clearHistory");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = queryInput.value.trim();
  if (!query) return showError("Please enter a search query.");
  if (query.length > 200) return showError("Query is too long.");
  await performSearch(query);
});

queryInput.value = "917565049866";
performSearch("917565049866");

async function performSearch(query) {
  setLoading(true);
  hideError();
  const start = performance.now();

  try {
    const url = `${CONFIG.endpoint}?${new URLSearchParams({ key: CONFIG.apiKey, query }).toString()}`;
    const response = await fetch(url, { method: "GET" });

    if (!response.ok) {
      throw new Error(`Server returned HTTP ${response.status}`);
    }

    const payload = await response.json();
    const result = normalizeApiResult(payload, query);

    if (!result || result.status !== true) {
      throw new Error(
        result?.message || "The API did not return a successful result.",
      );
    }

    const elapsed = Math.round(performance.now() - start);
    renderResults(
      { ...result, response_time_ms: result.response_time_ms ?? elapsed },
      elapsed,
    );
    saveHistory(query);
  } catch (error) {
    console.error("Search error:", error);
    showError(error.message || "Unable to connect to the search API.");
  } finally {
    setLoading(false);
  }
}

function normalizeApiResult(payload, fallbackQuery) {
  if (!payload || typeof payload !== "object") {
    return { status: false, message: "Empty API response." };
  }

  const status = payload.status ?? payload.success ?? payload.ok ?? true;
  const message = payload.message || payload.error || payload.msg || "";

  if (status === false || payload.success === false || payload.error === true) {
    return { status: false, message: message || "API returned an error." };
  }

  const query = payload.query || payload.search || fallbackQuery;
  const data =
    payload.data && typeof payload.data === "object"
      ? payload.data
      : payload.result && typeof payload.result === "object"
        ? payload.result
        : payload.response && typeof payload.response === "object"
          ? payload.response
          : payload.records && Array.isArray(payload.records)
            ? { records: payload.records }
            : payload;

  return {
    status: true,
    query,
    data,
    response_time_ms:
      payload.response_time_ms ??
      payload.responseTime ??
      payload.time ??
      payload.elapsed ??
      0,
    message,
  };
}

function renderResults(result, elapsed) {
  emptyState.classList.add("hidden");
  resultsSection.classList.remove("hidden");
  stats.classList.remove("hidden");
  rawContainer.classList.add("hidden");

  statQuery.textContent = result.query || "—";

  const sources = getSources(result.data);
  const recordCount = sources.reduce(
    (total, source) => total + source.records.length,
    0,
  );

  statSources.textContent = sources.length;
  statRecords.textContent = recordCount;
  statTime.textContent = `${result.response_time_ms ?? elapsed} ms`;

  renderSources(sources);

  const safeResult = sanitizeObject(result);
  rawJson.textContent = JSON.stringify(safeResult, null, 2);
}

function getSources(data) {
  if (!data || typeof data !== "object") return [];

  return Object.entries(data)
    .filter(
      ([, value]) =>
        value && typeof value === "object" && Array.isArray(value.records),
    )
    .map(([key, value]) => ({ key, ...value, records: value.records || [] }));
}

function renderSources(sources) {
  sourcesContainer.innerHTML = "";

  if (!sources.length) {
    sourcesContainer.innerHTML = `
      <div class="source-card">
        <div class="source-header">
          <div>
            <div class="source-title">No records</div>
            <div class="source-description">The API returned no displayable records.</div>
          </div>
        </div>
      </div>`;
    return;
  }

  sources.forEach((source) => {
    const card = document.createElement("article");
    card.className = "source-card";

    const header = document.createElement("div");
    header.className = "source-header";

    const title = document.createElement("div");
    const sourceTitle = document.createElement("div");
    sourceTitle.className = "source-title";
    sourceTitle.textContent = source.title || source.key || "Source";

    title.appendChild(sourceTitle);

    if (source.description) {
      const description = document.createElement("div");
      description.className = "source-description";
      description.textContent = source.description;
      title.appendChild(description);
    }

    const count = document.createElement("div");
    count.className = "source-count";
    count.textContent = `${source.records.length} RECORD${source.records.length === 1 ? "" : "S"}`;

    header.appendChild(title);
    header.appendChild(count);
    card.appendChild(header);

    source.records.map(sanitizeObject).forEach((record, index) => {
      card.appendChild(createRecordTable(record, index + 1));
    });

    sourcesContainer.appendChild(card);
  });
}

function createRecordTable(record) {
  const wrapper = document.createElement("div");
  wrapper.className = "table-wrapper";

  const table = document.createElement("table");
  const tbody = document.createElement("tbody");
  const entries = Object.entries(record);

  if (!entries.length) {
    tbody.innerHTML = "<tr><td>No displayable fields</td></tr>";
  } else {
    entries.forEach(([key, value]) => {
      const tr = document.createElement("tr");
      const keyCell = document.createElement("td");
      const valueCell = document.createElement("td");

      keyCell.textContent = key;
      valueCell.textContent = formatValue(value);

      tr.appendChild(keyCell);
      tr.appendChild(valueCell);
      tbody.appendChild(tr);
    });
  }

  table.appendChild(tbody);
  wrapper.appendChild(table);
  return wrapper;
}

function sanitizeObject(value) {
  if (Array.isArray(value)) return value.map(sanitizeObject);

  if (value && typeof value === "object") {
    const result = {};

    Object.entries(value).forEach(([key, child]) => {
      if (
        CONFIG.blockedFields.some(
          (blocked) => blocked.toLowerCase() === key.toLowerCase(),
        )
      )
        return;
      result[key] = sanitizeObject(child);
    });

    return result;
  }

  return value;
}

function formatValue(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function setLoading(loading) {
  searchButton.disabled = loading;
  searchText.classList.toggle("hidden", loading);
  loader.classList.toggle("hidden", !loading);
}

function showError(message) {
  errorMessage.textContent = message;
  errorBox.classList.remove("hidden");
}

function hideError() {
  errorBox.classList.add("hidden");
}

closeError.addEventListener("click", hideError);

clearButton.addEventListener("click", () => {
  queryInput.value = "";
  queryInput.focus();
});

toggleRaw.addEventListener("click", () => {
  rawContainer.classList.toggle("hidden");
  toggleRaw.textContent = rawContainer.classList.contains("hidden")
    ? "Raw JSON"
    : "Hide JSON";
});

copyJson.addEventListener("click", async () => {
  await copyToClipboard(rawJson.textContent);
  temporaryButtonText(copyJson, "Copied!");
});

copyRaw.addEventListener("click", async () => {
  await copyToClipboard(rawJson.textContent);
  temporaryButtonText(copyRaw, "COPIED");
});

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }
}

function temporaryButtonText(button, text) {
  const original = button.textContent;
  button.textContent = text;
  setTimeout(() => (button.textContent = original), 1200);
}

function getHistory() {
  try {
    return JSON.parse(localStorage.getItem("cybersearch_history")) || [];
  } catch {
    return [];
  }
}

function saveHistory(query) {
  let history = getHistory().filter((item) => item.query !== query);
  history.unshift({ query, time: new Date().toISOString() });
  history = history.slice(0, CONFIG.maxHistory);

  localStorage.setItem("cybersearch_history", JSON.stringify(history));
  renderHistory();
}

function renderHistory() {
  const history = getHistory();
  historyList.innerHTML = "";

  if (!history.length) {
    historyList.innerHTML =
      '<div class="history-empty">No recent searches.</div>';
    return;
  }

  history.forEach((item) => {
    const row = document.createElement("div");
    row.className = "history-item";

    const query = document.createElement("span");
    query.className = "history-query";
    query.textContent = item.query;

    const time = document.createElement("span");
    time.className = "history-time";
    time.textContent = formatHistoryTime(item.time);

    row.appendChild(query);
    row.appendChild(time);

    row.addEventListener("click", () => {
      queryInput.value = item.query;
      window.scrollTo({ top: 0, behavior: "smooth" });
    });

    historyList.appendChild(row);
  });
}

function formatHistoryTime(date) {
  const diff = Date.now() - new Date(date).getTime();
  const seconds = Math.floor(diff / 1000);

  if (seconds < 60) return "just now";

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  return `${Math.floor(hours / 24)}d ago`;
}

clearHistory.addEventListener("click", () => {
  localStorage.removeItem("cybersearch_history");
  renderHistory();
});

renderHistory();
