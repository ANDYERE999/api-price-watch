const state = {
  latest: null,
  history: null,
  selectedModel: "",
  billingMode: "all",
  selectedHistoryKey: "",
};

const elements = {
  updatedAt: document.querySelector("#updated-at"),
  providerStatus: document.querySelector("#provider-status"),
  search: document.querySelector("#model-search"),
  options: document.querySelector("#model-options"),
  selectedModel: document.querySelector("#selected-model"),
  resultSummary: document.querySelector("#result-summary"),
  results: document.querySelector("#price-results"),
  historyChart: document.querySelector("#history-chart"),
  historyTitle: document.querySelector("#history-title"),
};

const historyKey = (record) => [record.provider_id, record.canonical_model, record.group, record.billing_mode, record.condition].join("|");
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);
const compactNumber = (value) => value == null ? "—" : new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 6 }).format(value);
const formatTime = (value) => new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Shanghai" }).format(new Date(value));

function renderStatuses() {
  elements.providerStatus.innerHTML = state.latest.providers.map((provider) => `
    <div class="provider-chip ${provider.ok ? "" : "failed"}" title="${escapeHtml(provider.error || `${provider.records} 条报价`)}">
      <span>${escapeHtml(provider.name)}</span><b></b>
    </div>
  `).join("");
}

function models() {
  return [...new Set(state.latest.records.map((record) => record.canonical_model))].sort();
}

function chooseInitialModel() {
  const available = models();
  const requested = new URLSearchParams(location.search).get("model");
  state.selectedModel = available.includes(requested) ? requested : available[0] || "";
  elements.search.value = state.selectedModel;
  elements.options.innerHTML = available.map((model) => `<option value="${escapeHtml(model)}"></option>`).join("");
}

function metric(label, value, unit) {
  return `<div class="metric"><span>${label}</span><strong>${compactNumber(value)}${value == null ? "" : ` ${unit}`}</strong></div>`;
}

function renderPrices() {
  const records = state.latest.records.filter((record) =>
    record.canonical_model === state.selectedModel &&
    (state.billingMode === "all" || record.billing_mode === state.billingMode)
  );
  elements.selectedModel.textContent = state.selectedModel || "—";
  const providers = new Set(records.map((record) => record.provider_id)).size;
  elements.resultSummary.textContent = `${providers} 个网站 · ${records.length} 个价格分组`;

  if (!records.length) {
    elements.results.innerHTML = `<div class="empty">没有符合当前条件的报价</div>`;
    return;
  }
  elements.results.innerHTML = records.map((record) => {
    const key = historyKey(record);
    const unit = record.currency;
    const metrics = record.billing_mode === "request"
      ? metric("每次请求", record.request_price, unit)
      : [
          metric("输入 / 1M", record.input_per_million, unit),
          metric("输出 / 1M", record.output_per_million, unit),
          metric("缓存读 / 1M", record.cache_read_per_million, unit),
          metric("缓存写 / 1M", record.cache_write_per_million, unit),
        ].join("");
    return `
      <article class="price-card ${state.selectedHistoryKey === key ? "selected" : ""}" data-history-key="${escapeHtml(key)}" tabindex="0">
        <div class="card-top"><span class="provider-name">${escapeHtml(record.provider_name)}</span><span class="currency">${escapeHtml(record.currency)}</span></div>
        <div class="group-name">${escapeHtml(record.group)} · ${escapeHtml(record.source_model)}</div>
        <div class="price-row">${metrics}</div>
        ${record.condition ? `<div class="condition">条件：${escapeHtml(record.condition)}</div>` : ""}
      </article>`;
  }).join("");

  document.querySelectorAll(".price-card").forEach((card) => {
    const select = () => {
      state.selectedHistoryKey = card.dataset.historyKey;
      renderPrices();
      renderHistory();
    };
    card.addEventListener("click", select);
    card.addEventListener("keydown", (event) => { if (event.key === "Enter") select(); });
  });
}

function polyline(points, field, width, height, padding, minimum, range) {
  const valid = points.map((point, index) => ({ value: point[field], index })).filter((point) => point.value != null);
  if (!valid.length) return "";
  return valid.map((point) => {
    const x = padding + (point.index / Math.max(points.length - 1, 1)) * (width - padding * 2);
    const y = height - padding - ((point.value - minimum) / range) * (height - padding * 2);
    return `${x},${y}`;
  }).join(" ");
}

function renderHistory() {
  const series = state.history.series?.[state.selectedHistoryKey];
  if (!series) {
    elements.historyTitle.textContent = state.selectedHistoryKey ? "当前价格尚无历史变化" : "选择上方任一报价";
    elements.historyChart.className = "chart-empty";
    elements.historyChart.textContent = "历史序列会在价格发生变化时增加节点";
    return;
  }
  const points = series.points || [];
  elements.historyTitle.textContent = `${series.provider_name} / ${series.group}${series.condition ? ` / ${series.condition}` : ""}`;
  const fields = series.billing_mode === "request" ? ["request_price"] : ["input_per_million", "output_per_million"];
  const values = points.flatMap((point) => fields.map((field) => point[field])).filter((value) => value != null);
  if (!values.length) return;
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const range = maximum - minimum || Math.max(maximum, 1);
  const width = 900, height = 300, padding = 42;
  const inputLine = polyline(points, fields[0], width, height, padding, minimum, range);
  const outputLine = fields[1] ? polyline(points, fields[1], width, height, padding, minimum, range) : "";
  const labels = points.map((point, index) => {
    if (index !== 0 && index !== points.length - 1) return "";
    const x = padding + (index / Math.max(points.length - 1, 1)) * (width - padding * 2);
    return `<text x="${x}" y="284" text-anchor="${index === 0 ? "start" : "end"}" class="chart-label">${escapeHtml(formatTime(point.captured_at))}</text>`;
  }).join("");
  elements.historyChart.className = "chart-wrap";
  elements.historyChart.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="价格历史折线图">
      <line x1="${padding}" y1="${padding}" x2="${padding}" y2="${height - padding}" stroke="#d4d0c4" />
      <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="#d4d0c4" />
      <text x="8" y="${padding + 4}" class="chart-label">${compactNumber(maximum)} ${series.currency}</text>
      <text x="8" y="${height - padding + 4}" class="chart-label">${compactNumber(minimum)}</text>
      <polyline points="${inputLine}" fill="none" stroke="#137b70" stroke-width="3" vector-effect="non-scaling-stroke" />
      ${outputLine ? `<polyline points="${outputLine}" fill="none" stroke="#ff6933" stroke-width="3" vector-effect="non-scaling-stroke" />` : ""}
      ${labels}
      <text x="${width - 170}" y="25" class="chart-label">${series.billing_mode === "request" ? "每次请求" : "绿色 输入　橙色 输出"}</text>
    </svg>`;
}

function selectModel(value) {
  const query = value.trim().toLowerCase();
  const exact = models().find((model) => model.toLowerCase() === query);
  const partial = models().find((model) => model.toLowerCase().includes(query));
  const selected = exact || partial;
  if (!selected) return;
  state.selectedModel = selected;
  state.selectedHistoryKey = "";
  elements.search.value = selected;
  history.replaceState(null, "", `${location.pathname}?model=${encodeURIComponent(selected)}`);
  renderPrices();
  renderHistory();
}

async function start() {
  try {
    const [latestResponse, historyResponse] = await Promise.all([
      fetch("./data/latest.json", { cache: "no-store" }),
      fetch("./data/history.json", { cache: "no-store" }),
    ]);
    if (!latestResponse.ok || !historyResponse.ok) throw new Error("价格数据尚未生成");
    state.latest = await latestResponse.json();
    state.history = await historyResponse.json();
    elements.updatedAt.textContent = `更新于 ${formatTime(state.latest.updated_at)}`;
    renderStatuses();
    chooseInitialModel();
    renderPrices();
    renderHistory();
  } catch (error) {
    elements.updatedAt.textContent = "数据载入失败";
    elements.results.innerHTML = `<div class="empty">${escapeHtml(error.message)}。请先运行价格更新工作流。</div>`;
  }
}

elements.search.addEventListener("change", (event) => selectModel(event.target.value));
elements.search.addEventListener("keydown", (event) => { if (event.key === "Enter") selectModel(event.target.value); });
document.querySelector("#billing-filter").addEventListener("click", (event) => {
  if (!event.target.matches("button")) return;
  document.querySelectorAll("#billing-filter button").forEach((button) => button.classList.toggle("active", button === event.target));
  state.billingMode = event.target.dataset.value;
  renderPrices();
});

start();
