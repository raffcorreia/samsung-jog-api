const dataUrls = {
  captures: "./data/register-explorer.json",
  inventory: "./data/source-inventory.json",
};

const aliasStorageKey = "register-explorer-aliases-v1";
const excludedCapturesKey = "register-explorer-excluded-v1";
const irrelevantCountsKey = "register-explorer-irrelevant-v1";
const constantsKey = "register-explorer-constants-v1";
const relevantsKey = "register-explorer-relevants-v1";
const filterStateKey = "register-explorer-filters-v1";
const defaultAliases = {
  "0x37_ddc:0x10": "brightness",
  "0x37_ddc:0x12": "contrast",
  "0x37_ddc:0x60": "primary input",
  "0x37_ddc:0x62": "speaker volume",
  "0x37_ddc:0xD6": "power mode",
  "0x37_ddc:0xDC": "display app",
  "0x54:0x10": "hdmi active state",
  "0x54:0x40": "hdmi active flag",
  "0x58:0x02": "scaler sanity",
  "0x58:0x48": "display mode",
  "0x58:0x4A": "audio source",
  "0x58:0xA1": "signal presence",
  "0x58:0xE0": "pipeline byte 0",
  "0x58:0xE1": "pipeline byte 1 / osd guard",
  "0x58:0xE2": "pipeline byte 2",
  "0x58:0xE3": "pipeline byte 3",
};

const DEVICE_LABELS = {
  "0x37_ddc": "0x37 (DDC)",
  "0x50": "0x50 (EDID)",
};

const TEST_CASES = [
  { num: 1,  label: "1 — Standby",              filters: { power: ["standby"] } },
  { num: 2,  label: "2 — Idle",                 filters: { power: ["on"], layout: ["idle"] } },
  { num: 3,  label: "3 — Single: TB",           filters: { power: ["on"], layout: ["single"], primary: ["tb"] } },
  { num: 4,  label: "4 — PIP TB+HDMI (S)",      filters: { power: ["on"], layout: ["pip"], primary: ["tb"], secondary: ["hdmi"], size: ["small"] } },
  { num: 5,  label: "5 — PIP TB+HDMI (M)",      filters: { power: ["on"], layout: ["pip"], primary: ["tb"], secondary: ["hdmi"], size: ["medium"] } },
  { num: 6,  label: "6 — PIP TB+HDMI (L)",      filters: { power: ["on"], layout: ["pip"], primary: ["tb"], secondary: ["hdmi"], size: ["large"] } },
  { num: 7,  label: "7 — PIP TB+DP (L)",        filters: { power: ["on"], layout: ["pip"], primary: ["tb"], secondary: ["dp"], size: ["large"] } },
  { num: 8,  label: "8 — PIP TB+DP (M)",        filters: { power: ["on"], layout: ["pip"], primary: ["tb"], secondary: ["dp"], size: ["medium"] } },
  { num: 9,  label: "9 — PIP TB+DP (S)",        filters: { power: ["on"], layout: ["pip"], primary: ["tb"], secondary: ["dp"], size: ["small"] } },
  { num: 10, label: "10 — PBP TB/DP Audio L",   filters: { power: ["on"], layout: ["pbp"], primary: ["tb"], secondary: ["dp"],   audio: ["left"] } },
  { num: 11, label: "11 — PBP TB/DP Audio R",   filters: { power: ["on"], layout: ["pbp"], primary: ["tb"], secondary: ["dp"],   audio: ["right"] } },
  { num: 12, label: "12 — PBP TB/HDMI Audio L", filters: { power: ["on"], layout: ["pbp"], primary: ["tb"], secondary: ["hdmi"], audio: ["left"] } },
  { num: 13, label: "13 — PBP TB/HDMI Audio R", filters: { power: ["on"], layout: ["pbp"], primary: ["tb"], secondary: ["hdmi"], audio: ["right"] } },
  { num: 14, label: "14 — Single: HDMI",        filters: { power: ["on"], layout: ["single"], primary: ["hdmi"] } },
  { num: 15, label: "15 — PIP HDMI+TB (S)",     filters: { power: ["on"], layout: ["pip"], primary: ["hdmi"], secondary: ["tb"], size: ["small"] } },
  { num: 16, label: "16 — PIP HDMI+TB (M)",     filters: { power: ["on"], layout: ["pip"], primary: ["hdmi"], secondary: ["tb"], size: ["medium"] } },
  { num: 17, label: "17 — PIP HDMI+TB (L)",     filters: { power: ["on"], layout: ["pip"], primary: ["hdmi"], secondary: ["tb"], size: ["large"] } },
  { num: 18, label: "18 — PIP HDMI+DP (L)",     filters: { power: ["on"], layout: ["pip"], primary: ["hdmi"], secondary: ["dp"], size: ["large"] } },
  { num: 19, label: "19 — PIP HDMI+DP (M)",     filters: { power: ["on"], layout: ["pip"], primary: ["hdmi"], secondary: ["dp"], size: ["medium"] } },
  { num: 20, label: "20 — PIP HDMI+DP (S)",     filters: { power: ["on"], layout: ["pip"], primary: ["hdmi"], secondary: ["dp"], size: ["small"] } },
  { num: 21, label: "21 — PBP HDMI/DP Audio R", filters: { power: ["on"], layout: ["pbp"], primary: ["hdmi"], secondary: ["dp"],   audio: ["right"] } },
  { num: 22, label: "22 — PBP HDMI/DP Audio L", filters: { power: ["on"], layout: ["pbp"], primary: ["hdmi"], secondary: ["dp"],   audio: ["left"] } },
  { num: 23, label: "23 — PBP HDMI/TB Audio R", filters: { power: ["on"], layout: ["pbp"], primary: ["hdmi"], secondary: ["tb"],   audio: ["right"] } },
  { num: 24, label: "24 — PBP HDMI/TB Audio L", filters: { power: ["on"], layout: ["pbp"], primary: ["hdmi"], secondary: ["tb"],   audio: ["left"] } },
  { num: 25, label: "25 — Single: DP",          filters: { power: ["on"], layout: ["single"], primary: ["dp"] } },
  { num: 26, label: "26 — PIP DP+TB (S)",       filters: { power: ["on"], layout: ["pip"], primary: ["dp"], secondary: ["tb"], size: ["small"] } },
  { num: 27, label: "27 — PIP DP+TB (M)",       filters: { power: ["on"], layout: ["pip"], primary: ["dp"], secondary: ["tb"], size: ["medium"] } },
  { num: 28, label: "28 — PIP DP+TB (L)",       filters: { power: ["on"], layout: ["pip"], primary: ["dp"], secondary: ["tb"], size: ["large"] } },
  { num: 29, label: "29 — PIP DP+HDMI (L)",     filters: { power: ["on"], layout: ["pip"], primary: ["dp"], secondary: ["hdmi"], size: ["large"] } },
  { num: 30, label: "30 — PIP DP+HDMI (M)",     filters: { power: ["on"], layout: ["pip"], primary: ["dp"], secondary: ["hdmi"], size: ["medium"] } },
  { num: 31, label: "31 — PIP DP+HDMI (S)",     filters: { power: ["on"], layout: ["pip"], primary: ["dp"], secondary: ["hdmi"], size: ["small"] } },
  { num: 32, label: "32 — PBP DP/HDMI Audio R", filters: { power: ["on"], layout: ["pbp"], primary: ["dp"], secondary: ["hdmi"], audio: ["right"] } },
  { num: 33, label: "33 — PBP DP/HDMI Audio L", filters: { power: ["on"], layout: ["pbp"], primary: ["dp"], secondary: ["hdmi"], audio: ["left"] } },
  { num: 34, label: "34 — PBP DP/TB Audio R",   filters: { power: ["on"], layout: ["pbp"], primary: ["dp"], secondary: ["tb"],   audio: ["right"] } },
  { num: 35, label: "35 — PBP DP/TB Audio L",   filters: { power: ["on"], layout: ["pbp"], primary: ["dp"], secondary: ["tb"],   audio: ["left"] } },
];

const state = {
  data: null,
  inventory: null,
  deviceColumns: new Map(),
  selectedCell: null,
  selectedCaptureId: null,
  aliases: loadAliases(),
  excludedCaptures: loadExcluded(),
  irrelevantCounts: loadIrrelevantCounts(),
  constants: loadConstants(),
  relevants: loadRelevants(),
};

const els = {
  datasetMeta: document.querySelector("#dataset-meta"),
  captureFilterToggle: document.querySelector("#capture-filter-toggle"),
  captureFilterList: document.querySelector("#capture-filter-list"),
  captureFilterBadge: document.querySelector("#capture-filter-badge"),
  headerStack: document.querySelector("#header-stack"),
  headerToggle: document.querySelector("#header-toggle"),
  deviceSelect: document.querySelector("#device-select"),
  powerSelect: document.querySelector("#power-select"),
  layoutSelect: document.querySelector("#layout-select"),
  primarySelect: document.querySelector("#primary-select"),
  audioSelect: document.querySelector("#audio-select"),
  pipSizeSelect: document.querySelector("#pip-size-select"),
  secondarySelect: document.querySelector("#secondary-select"),
  connectedSelect: document.querySelector("#connected-select"),
  jogButtonSelect: document.querySelector("#jog-button-select"),
  testCaseSelect: document.querySelector("#test-case-select"),
  registerFilter: document.querySelector("#register-filter"),
  compareSelect: document.querySelector("#compare-select"),
  varyingOnly: document.querySelector("#varying-only"),
  attemptedOnly: document.querySelector("#attempted-only"),
  labeledOnly: document.querySelector("#labeled-only"),
  diffOnly: document.querySelector("#diff-only"),
  equalsOnly: document.querySelector("#equals-only"),
  hideIrrelevants: document.querySelector("#hide-irrelevants"),
  irrelevantsOnly: document.querySelector("#irrelevants-only"),
  hideAllNull: document.querySelector("#hide-all-null"),
  hideAllZero: document.querySelector("#hide-all-zero"),
  hideConstants: document.querySelector("#hide-constants"),
  hideNoConsensus: document.querySelector("#hide-no-consensus"),
  relevantOnly: document.querySelector("#relevants-only"),
  registerSummary: document.querySelector("#register-summary"),
  inventorySummary: document.querySelector("#inventory-summary"),
  matrixHead: document.querySelector("#matrix-table thead"),
  matrixBody: document.querySelector("#matrix-table tbody"),
  copyCsvBtn: document.querySelector("#copy-csv-btn"),
  cellDetail: document.querySelector("#cell-detail"),
  captureDetail: document.querySelector("#capture-detail"),
};

void init();

async function init() {
  const [captureData, inventoryData] = await Promise.all([
    fetchJson(dataUrls.captures),
    fetchJson(dataUrls.inventory),
  ]);

  state.data = captureData;
  state.inventory = inventoryData;
  buildDeviceColumns(captureData.captures);

  hydrateControls();
  bindEvents();
  render();
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load ${url}: ${response.status}`);
  }
  return response.json();
}

function buildDeviceColumns(captures) {
  const deviceColumns = new Map();
  for (const capture of captures) {
    for (const [device, payload] of Object.entries(capture.devices)) {
      if (!deviceColumns.has(device)) {
        deviceColumns.set(device, new Set());
      }
      const bucket = deviceColumns.get(device);
      Object.keys(payload.values ?? {}).forEach((reg) => bucket.add(normalizeReg(reg)));
      (payload.attempted_registers ?? []).forEach((reg) => bucket.add(normalizeReg(reg)));
    }
  }

  for (const [device, regs] of deviceColumns) {
    deviceColumns.set(device, [...regs].sort(compareHexRegs));
  }
  state.deviceColumns = deviceColumns;
}

function hydrateControls() {
  fillMultiSelectLabeled(els.deviceSelect, [...state.deviceColumns.keys()], DEVICE_LABELS);
  fillMultiSelect(els.powerSelect, facetValues("power_state"));
  fillMultiSelect(els.layoutSelect, facetValues("layout_mode"));
  fillMultiSelect(els.primarySelect, facetValues("primary_input"));
  fillMultiSelect(els.audioSelect, ["any", "left", "right"], ["any"]);
  fillMultiSelect(els.pipSizeSelect, ["any", "small", "medium", "large"], ["any"]);
  fillMultiSelect(els.secondarySelect, facetValues("secondary_input"));
  fillMultiSelect(els.connectedSelect, ["any", "dp", "hdmi", "tb"], ["any"]);
  fillMultiSelect(els.jogButtonSelect, ["none", "center", "up", "down", "left", "right"]);
  fillCompareSelect();
  applyFilterState();
  installMultiSelectBehavior();
  updateFilterSummaries();
  renderCaptureList();
  hydrateTestCaseSelect();
  syncTestCasePreset();
}

function facetValues(key) {
  return [...new Set(state.data.captures.map((capture) => capture[key]).filter(Boolean))].sort();
}

function fillMultiSelect(select, values, selectedValues = values) {
  const selected = new Set(selectedValues);
  select.innerHTML = values
    .map(
      (value) =>
        `<option value="${escapeHtml(value)}"${selected.has(value) ? " selected" : ""}>${escapeHtml(value)}</option>`,
    )
    .join("");
}

function fillMultiSelectLabeled(select, values, labels, selectedValues = values) {
  const selected = new Set(selectedValues);
  select.innerHTML = values
    .map(
      (value) =>
        `<option value="${escapeHtml(value)}"${selected.has(value) ? " selected" : ""}>${escapeHtml(labels[value] ?? value)}</option>`,
    )
    .join("");
}

function fillCompareSelect() {
  fillMultiSelect(
    els.compareSelect,
    state.data.captures.map((capture) => capture.capture_id),
    [],
  );
}

function bindEvents() {
  els.headerToggle.addEventListener("click", () => {
    const hidden = els.headerStack.classList.toggle("hidden");
    els.headerToggle.textContent = hidden ? "Show Header" : "Hide Header";
  });

  els.captureFilterToggle.addEventListener("click", () => {
    els.captureFilterList.classList.toggle("open");
  });

  els.varyingOnly.addEventListener("change", () => { if (els.varyingOnly.checked) els.equalsOnly.checked = false; });
  els.equalsOnly.addEventListener("change", () => { if (els.equalsOnly.checked) els.varyingOnly.checked = false; });
  els.hideIrrelevants.addEventListener("change", () => { if (els.hideIrrelevants.checked) els.irrelevantsOnly.checked = false; });
  els.irrelevantsOnly.addEventListener("change", () => { if (els.irrelevantsOnly.checked) els.hideIrrelevants.checked = false; });

  [
    els.deviceSelect,
    els.powerSelect,
    els.layoutSelect,
    els.primarySelect,
    els.audioSelect,
    els.pipSizeSelect,
    els.secondarySelect,
    els.connectedSelect,
    els.compareSelect,
    els.varyingOnly,
    els.attemptedOnly,
    els.labeledOnly,
    els.diffOnly,
    els.equalsOnly,
    els.hideIrrelevants,
    els.irrelevantsOnly,
    els.hideAllNull,
    els.hideAllZero,
    els.hideConstants,
    els.hideNoConsensus,
    els.relevantOnly,
  ].forEach((element) => {
    element.addEventListener("change", () => {
      updateFilterSummaries();
      saveFilterState();
      render();
      syncTestCasePreset();
    });
  });

  els.testCaseSelect.addEventListener("change", () => {
    const num = parseInt(els.testCaseSelect.value, 10);
    if (isNaN(num)) { state.activeJogTc = null; return; }
    const tc = TEST_CASES.find((t) => t.num === num);
    if (tc) { state.activeJogTc = null; applyTestCasePreset(tc); }
    else applyJogTcPreset(num);
  });

  els.registerFilter.addEventListener("input", () => { saveFilterState(); render(); });

  document.querySelectorAll(".filter-action").forEach((button) => {
    button.addEventListener("click", () => {
      const select = document.querySelector(`#${button.dataset.target}`);
      if (!(select instanceof HTMLSelectElement)) return;
      if (button.dataset.action === "none") {
        clearSelections(select);
      } else {
        [...select.options].forEach((option) => { option.selected = true; });
      }
      updateFilterSummaries();
      saveFilterState();
      render();
      syncTestCasePreset();
    });
  });

  document.querySelector("#reset-all-filters")?.addEventListener("click", resetAllFilters);
  els.copyCsvBtn?.addEventListener("click", copyMatrixCsv);
}

function render() {
  const visibleCaptures = getVisibleCaptures();
  const visibleColumns = getVisibleColumns(visibleCaptures);

  clearStaleSelections(visibleCaptures, visibleColumns);
  renderMeta(visibleCaptures, visibleColumns);
  renderMatrix(visibleCaptures, visibleColumns);
}

function getVisibleCaptures() {
  const selectedDevices = getSelectedValues(els.deviceSelect);
  const powers = getSelectedValues(els.powerSelect);
  const layouts = getSelectedValues(els.layoutSelect);
  const primaries = getSelectedValues(els.primarySelect);
  const audioValues = getSelectedValues(els.audioSelect);
  const pipSizes = getSelectedValues(els.pipSizeSelect);
  const secondaries = getSelectedValues(els.secondarySelect);
  const connectedInputs = getSelectedValues(els.connectedSelect);
  const jogButtonValues = getSelectedValues(els.jogButtonSelect);
  const filterPowers = isRestrictiveSelection(els.powerSelect, powers);
  const filterLayouts = isRestrictiveSelection(els.layoutSelect, layouts);
  const filterPrimaries = isRestrictiveSelection(els.primarySelect, primaries);
  const filterSecondaries = isRestrictiveSelection(els.secondarySelect, secondaries);
  const audioAny = audioValues.includes("any");
  const audioSpecific = audioValues.filter((v) => v !== "any");
  const pipSizeAny = pipSizes.includes("any");
  const pipSizeSpecific = pipSizes.filter((v) => v !== "any");
  const connectedAny = connectedInputs.includes("any");
  const connectedSpecific = connectedInputs.filter((v) => v !== "any");

  return state.data.captures.filter((capture) => {
    if (state.excludedCaptures.has(capture.capture_id)) return false;
    if (selectedDevices.length && !selectedDevices.some((device) => capture.devices[device])) return false;
    if (filterPowers && !powers.includes(capture.power_state)) return false;
    if (filterLayouts && !layouts.includes(capture.layout_mode)) return false;
    if (filterPrimaries && !primaries.includes(capture.primary_input)) return false;
    if (filterSecondaries && !secondaries.includes(capture.secondary_input)) return false;
    if (!audioAny) {
      const captureAudio = capture.audio_side;
      if (audioSpecific.length === 0) {
        if (captureAudio != null) return false;
      } else {
        if (!audioSpecific.includes(captureAudio)) return false;
      }
    }
    if (!pipSizeAny) {
      const sizeLabel = capturePipSizeLabel(capture);
      if (pipSizeSpecific.length === 0) {
        if (sizeLabel !== null) return false;
      } else {
        if (!pipSizeSpecific.includes(sizeLabel)) return false;
      }
    }
    if (!connectedAny) {
      const captureConnected = capture.connected_inputs ?? [];
      if (captureConnected.length > 0) {
        if (connectedSpecific.length === 0) {
          return false;
        } else {
          if (!connectedSpecific.every((v) => captureConnected.includes(v))) return false;
        }
      }
      // empty connected_inputs = unknown; pass the filter regardless
    }
    if (isRestrictiveSelection(els.jogButtonSelect, jogButtonValues)) {
      const btnKey = capture.jog_button ?? "none";
      if (!jogButtonValues.includes(btnKey)) return false;
    }
    return true;
  }).sort((a, b) => {
    const ta = a.test_case ?? Infinity;
    const tb = b.test_case ?? Infinity;
    if (ta !== tb) return ta - tb;
    return (a.captured_at ?? "").localeCompare(b.captured_at ?? "");
  });
}

function getVisibleColumns(captures) {
  const compareCaptures = getCompareCaptures();
  const registerFilter = normalizeRegFilter(els.registerFilter.value);
  const showVaryingOnly = els.varyingOnly.checked;
  const showEqualsOnly = els.equalsOnly.checked;
  const attemptedOnly = els.attemptedOnly.checked;
  const labeledOnly = els.labeledOnly.checked;
  const diffOnly = els.diffOnly.checked;
  const hideIrrelevants = els.hideIrrelevants.checked;
  const irrelevantsOnly = els.irrelevantsOnly.checked;
  const hideAllNull = els.hideAllNull.checked;
  const hideAllZero = els.hideAllZero.checked;
  const hideConstants = els.hideConstants.checked;
  const hideNoConsensus = els.hideNoConsensus.checked;
  const relevantOnly = els.relevantOnly.checked;
  const selectedDevices = getSelectedValues(els.deviceSelect);
  const columns = [];

  for (const device of selectedDevices) {
    const regs = state.deviceColumns.get(device) ?? [];
    for (const reg of regs) {
      if (registerFilter && !columnMatchesFilter(device, reg, registerFilter)) continue;
      if (labeledOnly && !getAlias(device, reg)) continue;

      const states = captures.map((capture) => valueState(capture, device, reg));
      if (attemptedOnly && states.some((entry) => entry.kind === "unattempted")) continue;
      if (showVaryingOnly && !isVarying(states, captures.length)) continue;
      if (showEqualsOnly && isVarying(states, captures.length)) continue;
      if (
        diffOnly &&
        compareCaptures.length &&
        !captures.some((capture) => changedAgainstAny(capture, compareCaptures, device, reg))
      ) {
        continue;
      }

      const irrCount = getIrrelevantCount(device, reg);
      if (hideIrrelevants && irrCount > 0) continue;
      if (irrelevantsOnly && irrCount === 0) continue;
      if (hideAllNull && states.some((s) => s.kind === "null") && states.every((s) => s.kind !== "value")) continue;
      if (hideAllZero && states.some((s) => s.kind === "value") && states.every((s) => s.kind !== "value" || s.value === 0)) continue;
      if (hideConstants && isConstant(device, reg)) continue;
      if (hideNoConsensus && hasNoConsensus(device, reg)) continue;
      if (relevantOnly && getRelevants(device, reg).length === 0) continue;

      columns.push({ device, reg });
    }
  }

  return columns;
}

function clearStaleSelections(captures, columns) {
  const captureIds = new Set(captures.map((capture) => capture.capture_id));
  const columnKeys = new Set(columns.map((column) => columnKey(column.device, column.reg)));

  if (state.selectedCaptureId && !captureIds.has(state.selectedCaptureId)) {
    state.selectedCaptureId = null;
    resetCaptureDetail();
  }

  if (state.selectedCell) {
    const selectedKey = columnKey(state.selectedCell.device, state.selectedCell.reg);
    if (!captureIds.has(state.selectedCell.captureId) || !columnKeys.has(selectedKey)) {
      state.selectedCell = null;
      resetCellDetail();
    }
  }
}

function renderMeta(captures, columns) {
  const selectedDevices = getSelectedValues(els.deviceSelect);
  const compareCaptures = getCompareCaptures();
  const nullCount = columns.reduce(
    (count, column) =>
      count +
      captures.filter((capture) => valueState(capture, column.device, column.reg).kind === "null").length,
    0,
  );
  const namedVisible = columns.filter((column) => getAlias(column.device, column.reg)).length;
  const irrelevantCount = Object.keys(state.irrelevantCounts).length;

  els.datasetMeta.innerHTML = `
    <div><strong>Generated:</strong> ${escapeHtml(state.data.generated_at)}</div>
    <div><strong>Total / Visible:</strong> ${state.data.captures.length} / ${captures.length}</div>
    <div><strong>Modes:</strong> ${captureModeSummary(captures)}</div>
    <div><strong>Devices:</strong> ${escapeHtml(selectedDevices.join(", ") || "none")}</div>
    <div><strong>Compare:</strong> ${compareCaptures.length} baseline(s)</div>
  `;

  els.registerSummary.innerHTML = `
    <div><strong>${columns.length}</strong> visible register(s)${irrelevantCount > 0 ? ` · <strong>${irrelevantCount}</strong> irrelevant` : ""}${state.constants.size > 0 ? ` · <strong>${state.constants.size}</strong> constant` : ""}</div>
    <div><strong>${nullCount}</strong> attempted null cell(s)</div>
    <div>${activeRegisterFilterSummary()}</div>
    <div class="header-actions">
      <button class="mini-button" id="mark-visible-irrelevant" type="button" title="Increment the irrelevancy count by 1 for every currently visible register. Registers with high counts are hidden by the irrelevancy filter.">Mark Visible as Irrelevant</button>
      <button class="mini-button" id="mark-intra-pair-irrelevant" type="button" title="Scan test case pairs (two captures of the same logical state) and increment the irrelevancy count for any register whose value differs within a pair — those are noise, not signal.">Mark Intra-pair Noise</button>
      <button class="mini-button" id="mark-visible-constants" type="button" title="Tag every currently visible register as a constant. Constants are always shown at 100% opacity regardless of other filters.">Mark Visible as Constants</button>
      <button class="mini-button" id="mark-visible-relevant" type="button" title="Add the selected test case number to the relevance list of every currently visible register. Requires a test case to be selected.">Mark Visible as Relevant</button>
      <button class="mini-button danger" id="reset-irrelevancy" type="button" title="Clear all irrelevancy counts globally. Cannot be undone.">Reset Irrelevancy</button>
      <button class="mini-button danger" id="reset-constants" type="button" title="Remove all constant tags globally. Cannot be undone.">Reset Constants</button>
      <button class="mini-button danger" id="reset-relevants" type="button" title="Remove all test case relevance assignments globally. Cannot be undone.">Reset Relevants</button>
    </div>
  `;
  document.querySelector("#mark-visible-irrelevant")?.addEventListener("click", markVisibleAsIrrelevant);
  document.querySelector("#mark-intra-pair-irrelevant")?.addEventListener("click", markIntraPairNoiseAsIrrelevant);
  document.querySelector("#mark-visible-constants")?.addEventListener("click", markVisibleAsConstants);
  document.querySelector("#mark-visible-relevant")?.addEventListener("click", markVisibleAsRelevant);
  document.querySelector("#reset-irrelevancy")?.addEventListener("click", resetIrrelevancy);
  document.querySelector("#reset-constants")?.addEventListener("click", resetConstants);
  document.querySelector("#reset-relevants")?.addEventListener("click", resetRelevants);

  const selectedDeviceSummary = selectedDevices.length === 1 ? selectedDevices[0] : `${selectedDevices.length} selected devices`;
  els.inventorySummary.innerHTML = `
    <div><strong>${namedVisible}</strong> visible register(s) have labels</div>
    <div><strong>${Object.keys(state.aliases).length}</strong> custom rename(s) saved locally</div>
    <div class="header-actions">
      <button class="mini-button" id="reset-device-aliases" type="button" title="Remove all custom register labels for the currently selected device(s).">Reset Device Labels</button>
      <button class="mini-button" id="reset-all-aliases" type="button" title="Remove every custom register and device label saved locally.">Reset All Labels</button>
    </div>
    <div class="hint">Device reset applies to ${escapeHtml(selectedDeviceSummary)}.</div>
  `;
  document.querySelector("#reset-device-aliases")?.addEventListener("click", resetSelectedDeviceAliases);
  document.querySelector("#reset-all-aliases")?.addEventListener("click", resetAllAliases);
}

function activeRegisterFilterSummary() {
  const filters = [];
  if (els.varyingOnly.checked) filters.push("varying only");
  if (els.equalsOnly.checked) filters.push("equal only");
  if (els.attemptedOnly.checked) filters.push("attempted by all");
  if (els.labeledOnly.checked) filters.push("labeled only");
  if (els.diffOnly.checked) filters.push("changed vs compare");
  if (els.hideIrrelevants.checked) filters.push("irrelevants hidden");
  if (els.irrelevantsOnly.checked) filters.push("irrelevants only");
  if (els.hideAllNull.checked) filters.push("all-null hidden");
  if (els.hideAllZero.checked) filters.push("all-zero hidden");
  if (els.hideConstants.checked) filters.push("constants hidden");
  if (els.hideNoConsensus.checked) filters.push("no-consensus hidden");
  if (els.relevantOnly.checked) filters.push("relevants only");
  return filters.length ? filters.join(" · ") : "all matching registers shown";
}

function captureModeSummary(captures) {
  const counts = new Map();
  for (const capture of captures) {
    counts.set(capture.layout_mode, (counts.get(capture.layout_mode) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([mode, count]) => `${mode}: ${count}`)
    .join(" · ");
}

function renderMatrix(captures, columns) {
  const compareCaptures = getCompareCaptures();
  els.matrixHead.innerHTML = "";
  els.matrixBody.innerHTML = "";

  const headRow = document.createElement("tr");
  headRow.appendChild(makeHeaderCell("Capture"));
  for (const column of columns) {
    headRow.appendChild(makeRegisterHeaderCell(column.device, column.reg));
  }
  els.matrixHead.appendChild(headRow);

  const bodyFrag = document.createDocumentFragment();
  for (const capture of captures) {
    const row = document.createElement("tr");
    const metaCell = document.createElement("td");
    metaCell.innerHTML = `
      <div class="capture-label ${capture.capture_id === state.selectedCaptureId ? "selected" : ""}" data-capture-id="${escapeHtml(capture.capture_id)}" title="${escapeHtml(capture.capture_id)}">
        <div class="capture-title">${escapeHtml(captureStatusCode(capture))}</div>
        <div class="capture-id">${escapeHtml(capture.capture_id)}</div>
      </div>
    `;
    metaCell.querySelector(".capture-label").addEventListener("click", () => {
      if (hasActiveSelection()) return;
      if (state.selectedCaptureId === capture.capture_id) {
        state.selectedCaptureId = null;
        resetCaptureDetail();
        renderMatrix(captures, columns);
        return;
      }
      state.selectedCaptureId = capture.capture_id;
      renderCaptureDetail(capture);
      renderMatrix(captures, columns);
    });
    row.appendChild(metaCell);

    for (const column of columns) {
      const cellState = valueState(capture, column.device, column.reg);
      const cell = document.createElement("td");
      cell.className = `cell ${cellState.kind}${changedAgainstAny(capture, compareCaptures, column.device, column.reg) ? " changed" : ""}${isConstant(column.device, column.reg) ? " constant" : ""}`;
      if (
        state.selectedCell &&
        state.selectedCell.captureId === capture.capture_id &&
        state.selectedCell.device === column.device &&
        state.selectedCell.reg === column.reg
      ) {
        cell.classList.add("selected");
      }
      const irrCount = getIrrelevantCount(column.device, column.reg);
      const badge = irrCount > 0 ? `<span class="irr-count">${irrCount}</span>` : "";
      const relList = getRelevants(column.device, column.reg);
      const relBadge = relList.length > 0 ? `<span class="rel-list">${relList.join("·")}</span>` : "";
      cell.innerHTML = `${badge}<span class="cell-value">${escapeHtml(formatCellState(cellState))}</span>${relBadge}<span class="cell-irr-controls"><button class="irr-btn" type="button" data-delta="-1">−</button><button class="irr-btn" type="button" data-delta="1">+</button></span>`;
      cell.querySelectorAll(".irr-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          adjustIrrelevancy(column.device, column.reg, parseInt(btn.dataset.delta, 10));
        });
      });
      cell.addEventListener("click", () => {
        if (hasActiveSelection()) return;
        const alreadySelected =
          state.selectedCell &&
          state.selectedCell.captureId === capture.capture_id &&
          state.selectedCell.device === column.device &&
          state.selectedCell.reg === column.reg;
        if (alreadySelected) {
          state.selectedCell = null;
          resetCellDetail();
          renderMatrix(captures, columns);
          return;
        }
        state.selectedCell = { captureId: capture.capture_id, device: column.device, reg: column.reg };
        renderCellDetail(capture, column.device, column.reg, cellState, compareCaptures);
        renderMatrix(captures, columns);
      });
      row.appendChild(cell);
    }
    bodyFrag.appendChild(row);
  }
  els.matrixBody.appendChild(bodyFrag);
}

function makeHeaderCell(text) {
  const th = document.createElement("th");
  th.textContent = text;
  return th;
}

function makeRegisterHeaderCell(device, reg) {
  const th = document.createElement("th");
  const alias = getAlias(device, reg);
  th.innerHTML = `
    <div class="reg-head ${alias ? "named" : ""}">
      <span class="reg-device">${escapeHtml(device)}</span>
      <span class="reg-code">${escapeHtml(reg)}</span>
      <span class="reg-alias">${escapeHtml(alias || "")}</span>
    </div>
  `;
  th.title = alias ? `${device} ${reg} — ${alias}` : `${device} ${reg}`;
  th.addEventListener("dblclick", () => renameAlias(device, reg));
  return th;
}

function renderCellDetail(capture, device, reg, cellState, compareCaptures) {
  const devicePayload = capture.devices[device];
  const detail = devicePayload?.details?.[reg] ?? null;
  const compareStates = compareCaptures.map((compareCapture) => ({
    captureId: compareCapture.capture_id,
    state: valueState(compareCapture, device, reg),
  }));

  els.cellDetail.classList.remove("empty");
  els.cellDetail.innerHTML = `
    <dl class="kv">
      <dt>Capture</dt><dd>${escapeHtml(capture.capture_id)}</dd>
      <dt>Capture Code</dt><dd class="mono">${escapeHtml(captureStatusCode(capture, device))}</dd>
      <dt>Code Legend</dt><dd class="mono">device|power|layout|primary|connected|signal</dd>
      <dt>Device</dt><dd>${escapeHtml(device)}</dd>
      <dt>Register</dt><dd class="mono">${escapeHtml(reg)}</dd>
      <dt>Label</dt><dd>${escapeHtml(getAlias(device, reg) || "—")}</dd>
      <dt>State</dt><dd>${escapeHtml(cellState.kind)}</dd>
      <dt>Rendered Value</dt><dd class="mono">${escapeHtml(formatCellState(cellState))}</dd>
      <dt>Compared Values</dt><dd class="mono">${escapeHtml(formatCompareStates(compareStates))}</dd>
      <dt>Changed</dt><dd>${changedAgainstAny(capture, compareCaptures, device, reg) ? "yes" : "no"}</dd>
      <dt>Attempted</dt><dd>${isAttempted(devicePayload, reg) ? "yes" : "no"}</dd>
      <dt>Raw Detail</dt><dd class="mono">${escapeHtml(JSON.stringify(detail ?? {}, null, 0))}</dd>
    </dl>
    <hr style="margin:10px 0;border:none;border-top:1px solid var(--line)">
    <h2 style="margin-bottom:6px">Register Relevance</h2>
    <p style="margin:0 0 6px;font-size:0.78rem;color:var(--muted)">Comma-separated test case numbers</p>
    <input id="relevants-edit" type="text" value="${escapeHtml(getRelevants(device, reg).join(", "))}" placeholder="e.g. 3, 7, 14" style="width:100%" />
    <div class="header-actions">
      <button class="mini-button" id="rename-current-register" type="button" title="Set a custom display label for this register.">Rename Register</button>
      <button class="mini-button" id="reset-current-register" type="button" title="Remove the custom label and restore the default register name.">Reset Label</button>
    </div>
  `;
  document.querySelector("#rename-current-register")?.addEventListener("click", () => renameAlias(device, reg));
  document.querySelector("#reset-current-register")?.addEventListener("click", () => resetAlias(device, reg));
  document.querySelector("#relevants-edit")?.addEventListener("change", (e) => {
    const parsed = e.target.value.split(/[\s,]+/).map((s) => parseInt(s, 10)).filter((n) => !isNaN(n));
    setRelevants(device, reg, parsed);
    render();
  });
}

function renderCaptureDetail(capture) {
  els.captureDetail.classList.remove("empty");
  els.captureDetail.innerHTML = `
    <dl class="kv">
      <dt>Capture ID</dt><dd>${escapeHtml(capture.capture_id)}</dd>
      <dt>Captured At</dt><dd>${escapeHtml(capture.captured_at ?? "—")}</dd>
      <dt>Capture Code</dt><dd class="mono">${escapeHtml(captureStatusCode(capture))}</dd>
      <dt>Code Legend</dt><dd class="mono">device-filter|power|layout|primary|connected|signal</dd>
      <dt>State</dt><dd>${escapeHtml(capture.state_label)}</dd>
      <dt>Layout</dt><dd>${escapeHtml(capture.layout_mode)}</dd>
      <dt>Primary</dt><dd>${escapeHtml(capture.primary_input ?? "—")}</dd>
      <dt>Secondary</dt><dd>${escapeHtml(capture.secondary_input ?? "—")}</dd>
      <dt>Connected</dt><dd>${escapeHtml((capture.connected_inputs ?? []).join(", ") || "—")}</dd>
      <dt>Signal Inputs</dt><dd>${escapeHtml((capture.signal_present_inputs ?? []).join(", ") || "—")}</dd>
      <dt>Source</dt><dd>${escapeHtml(capture.source_file ?? "canonical capture")}</dd>
      <dt>Flags</dt><dd class="mono">${escapeHtml(JSON.stringify(capture.flags ?? {}))}</dd>
      <dt>Notes</dt><dd>${escapeHtml((capture.notes ?? []).join(" | ") || "—")}</dd>
    </dl>
    <div class="header-actions">
      <button class="mini-button danger" id="delete-capture-btn" type="button" title="Permanently delete this capture file from disk. Cannot be undone.">Delete Capture</button>
    </div>
  `;
  document.querySelector("#delete-capture-btn")?.addEventListener("click", () => deleteCapture(capture.capture_id));
}

async function deleteCapture(captureId) {
  if (!window.confirm(`Delete capture "${captureId}"?\n\nThis removes the file from disk and cannot be undone.`)) return;
  try {
    const response = await fetch("/api/delete-capture", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ capture_id: captureId }),
    });
    const result = await response.json();
    if (!response.ok) {
      window.alert(result.error);
      return;
    }
    await reloadData();
  } catch (err) {
    window.alert(`Delete failed: ${err.message}`);
  }
}

async function reloadData() {
  const [captureData, inventoryData] = await Promise.all([
    fetchJson(dataUrls.captures),
    fetchJson(dataUrls.inventory),
  ]);
  state.data = captureData;
  state.inventory = inventoryData;
  state.selectedCell = null;
  state.selectedCaptureId = null;
  buildDeviceColumns(captureData.captures);
  hydrateControls();
  renderCaptureList();
  resetCellDetail();
  resetCaptureDetail();
  render();
}

function resetCellDetail() {
  els.cellDetail.className = "detail-panel empty";
  els.cellDetail.textContent = "Select a cell to inspect its raw value, attempt state, and metadata.";
}

function resetCaptureDetail() {
  els.captureDetail.className = "detail-panel empty";
  els.captureDetail.textContent = "Click any row label to inspect the full capture metadata.";
}

function getCompareCaptures() {
  const compareIds = getSelectedValues(els.compareSelect);
  return state.data.captures.filter((capture) => compareIds.includes(capture.capture_id));
}

function valueState(capture, device, reg) {
  const payload = capture.devices[device];
  if (!payload) return { kind: "unattempted", value: undefined };

  const attempted = isAttempted(payload, reg);
  if (!attempted) return { kind: "unattempted", value: undefined };

  if (!(reg in (payload.values ?? {}))) return { kind: "unattempted", value: undefined };

  const value = payload.values[reg];
  if (value === null) return { kind: "null", value: null };
  return { kind: "value", value };
}

function isAttempted(payload, reg) {
  return new Set(payload?.attempted_registers ?? []).has(reg);
}

function isVarying(states, captureCount) {
  if (captureCount < 2) return false;
  const distinct = new Set(states.map((entry) => JSON.stringify([entry.kind, entry.value])));
  return distinct.size > 1;
}

function changedAgainstAny(capture, compareCaptures, device, reg) {
  if (!compareCaptures.length) return false;
  const left = valueState(capture, device, reg);
  return compareCaptures.some((compareCapture) => {
    const right = valueState(compareCapture, device, reg);
    return left.kind !== right.kind || left.value !== right.value;
  });
}

function formatCellState(cellState) {
  if (cellState.kind === "unattempted") return "—";
  if (cellState.kind === "null") return "null";
  if (typeof cellState.value === "number") return `0x${cellState.value.toString(16).toUpperCase().padStart(2, "0")}`;
  return String(cellState.value);
}

function formatCompareStates(compareStates) {
  if (!compareStates.length) return "—";
  return compareStates
    .map(({ captureId, state: compareState }) => `${captureId}: ${formatCellState(compareState)}`)
    .join(" | ");
}

function normalizeReg(reg) {
  if (!reg) return "";
  const value = reg.trim().toLowerCase();
  if (value.startsWith("0x")) return `0x${value.slice(2).toUpperCase().padStart(2, "0")}`;
  return `0x${value.toUpperCase().padStart(2, "0")}`;
}

function normalizeRegFilter(value) {
  const trimmed = value.trim();
  if (!trimmed) return "";
  if (/^(0x)?[0-9a-fA-F]{1,2}$/.test(trimmed)) {
    return normalizeReg(trimmed);
  }
  return trimmed.toLowerCase();
}

function getSelectedValues(select) {
  return [...select.selectedOptions].map((option) => option.value);
}

function installMultiSelectBehavior() {
  [
    els.deviceSelect,
    els.powerSelect,
    els.layoutSelect,
    els.primarySelect,
    els.audioSelect,
    els.pipSizeSelect,
    els.secondarySelect,
    els.connectedSelect,
    els.jogButtonSelect,
    els.compareSelect,
  ].forEach((select) => {
    select.addEventListener("mousedown", (event) => {
      if (event.button !== 0) return;
      const option = event.target.closest("option");
      if (!option) return;
      const previous = new Set(getSelectedValues(select));
      const clickedValue = option.value;
      event.preventDefault();
      requestAnimationFrame(() => {
        const nextSelected = new Set(previous);
        if (nextSelected.has(clickedValue)) {
          nextSelected.delete(clickedValue);
        } else {
          nextSelected.add(clickedValue);
        }
        [...select.options].forEach((candidate) => {
          candidate.selected = nextSelected.has(candidate.value);
        });
        select.focus();
        updateFilterSummaries();
        saveFilterState();
        render();
        syncTestCasePreset();
      });
    });

    select.addEventListener("contextmenu", (event) => {
      const option = event.target.closest("option");
      if (!option) return;
      event.preventDefault();
      [...select.options].forEach((o) => { o.selected = o === option; });
      select.focus();
      updateFilterSummaries();
      saveFilterState();
      render();
      syncTestCasePreset();
    });
  });
}

function updateFilterSummaries() {
  updateFilterSummary(els.deviceSelect, "device-select-summary");
  updateFilterSummary(els.powerSelect, "power-select-summary");
  updateFilterSummary(els.layoutSelect, "layout-select-summary");
  updateFilterSummary(els.primarySelect, "primary-select-summary");
  updateFilterSummary(els.audioSelect, "audio-select-summary");
  updateFilterSummary(els.pipSizeSelect, "pip-size-select-summary");
  updateFilterSummary(els.secondarySelect, "secondary-select-summary");
  updateFilterSummary(els.connectedSelect, "connected-select-summary");
  updateFilterSummary(els.compareSelect, "compare-select-summary");
}

function updateFilterSummary(select, summaryId) {
  const summary = document.querySelector(`#${summaryId}`);
  if (!summary) return;
  const selected = getSelectedValues(select);
  const total = select.options.length;
  if (!selected.length) {
    summary.textContent = "Selected: none";
    return;
  }
  if (selected.length === total) {
    summary.textContent = "Selected: all";
    return;
  }
  summary.textContent = `Selected: ${selected.join(", ")}`;
}

function clearSelections(select) {
  [...select.options].forEach((option) => {
    option.selected = false;
  });
}

function hasOverlap(left, right) {
  return right.some((value) => left.includes(value));
}

function isRestrictiveSelection(select, selectedValues) {
  return selectedValues.length > 0 && selectedValues.length < select.options.length;
}

function columnMatchesFilter(device, reg, registerFilter) {
  const alias = getAlias(device, reg).toLowerCase();
  const deviceText = device.toLowerCase();
  const regText = reg.toLowerCase();
  const filter = registerFilter.toLowerCase();
  return regText.includes(filter) || deviceText.includes(filter) || alias.includes(filter);
}

function columnKey(device, reg) {
  return `${device}:${reg}`;
}

function aliasKey(device, reg) {
  return `${device}:${reg}`;
}

function loadExcluded() {
  try {
    return new Set(JSON.parse(localStorage.getItem(excludedCapturesKey) || "[]"));
  } catch {
    return new Set();
  }
}

function saveExcluded() {
  localStorage.setItem(excludedCapturesKey, JSON.stringify([...state.excludedCaptures]));
}

function loadIrrelevantCounts() {
  try {
    return JSON.parse(localStorage.getItem(irrelevantCountsKey) || "{}");
  } catch {
    return {};
  }
}

function saveIrrelevantCounts() {
  localStorage.setItem(irrelevantCountsKey, JSON.stringify(state.irrelevantCounts));
}

function loadConstants() {
  try {
    return new Set(JSON.parse(localStorage.getItem(constantsKey) || "[]"));
  } catch {
    return new Set();
  }
}

function saveConstants() {
  localStorage.setItem(constantsKey, JSON.stringify([...state.constants]));
}

function isConstant(device, reg) {
  return state.constants.has(columnKey(device, reg));
}

function hasNoConsensus(device, reg) {
  return state.data.captures.some(
    (c) => c.devices?.[device]?.read_stats?.retry_detail?.[reg]?.no_consensus === true
  );
}

function markVisibleAsConstants() {
  const captures = getVisibleCaptures();
  const columns = getVisibleColumns(captures);
  if (!columns.length) { window.alert("No visible registers to mark."); return; }
  if (!window.confirm(`Mark ${columns.length} visible register(s) as constants?`)) return;
  for (const { device, reg } of columns) state.constants.add(columnKey(device, reg));
  saveConstants();
  render();
}

function resetConstants() {
  if (!state.constants.size) return;
  if (!window.confirm(`Clear all ${state.constants.size} constant mark(s)?`)) return;
  state.constants.clear();
  saveConstants();
  render();
}

function loadRelevants() {
  try {
    const raw = JSON.parse(localStorage.getItem(relevantsKey) || "{}");
    return Object.fromEntries(Object.entries(raw).map(([k, v]) => [k, Array.isArray(v) ? v : []]));
  } catch {
    return {};
  }
}

function saveRelevants() {
  localStorage.setItem(relevantsKey, JSON.stringify(state.relevants));
}

function getRelevants(device, reg) {
  return state.relevants[columnKey(device, reg)] ?? [];
}

function setRelevants(device, reg, list) {
  const key = columnKey(device, reg);
  const sorted = [...new Set(list.filter((n) => Number.isInteger(n)))].sort((a, b) => a - b);
  if (sorted.length === 0) {
    delete state.relevants[key];
  } else {
    state.relevants[key] = sorted;
  }
  saveRelevants();
}

function markVisibleAsRelevant() {
  const captures = getVisibleCaptures();
  const columns = getVisibleColumns(captures);
  if (!columns.length) { window.alert("No visible registers."); return; }
  const tcVal = els.testCaseSelect.value;
  const num = tcVal ? parseInt(tcVal, 10) : NaN;
  if (isNaN(num)) { window.alert("Select a test case first."); return; }
  if (!window.confirm(`Add test case ${num} to relevance list of ${columns.length} visible register(s)?`)) return;
  for (const { device, reg } of columns) {
    const key = columnKey(device, reg);
    const list = state.relevants[key] ?? [];
    if (!list.includes(num)) state.relevants[key] = [...list, num].sort((a, b) => a - b);
  }
  saveRelevants();
  render();
}

function loadFilterState() {
  try {
    return JSON.parse(localStorage.getItem(filterStateKey) || "null");
  } catch {
    return null;
  }
}

function saveFilterState() {
  const saved = {
    device: getSelectedValues(els.deviceSelect),
    power: getSelectedValues(els.powerSelect),
    layout: getSelectedValues(els.layoutSelect),
    primary: getSelectedValues(els.primarySelect),
    audio: getSelectedValues(els.audioSelect),
    pipSize: getSelectedValues(els.pipSizeSelect),
    secondary: getSelectedValues(els.secondarySelect),
    connected: getSelectedValues(els.connectedSelect),
    jogButton: getSelectedValues(els.jogButtonSelect),
    compare: getSelectedValues(els.compareSelect),
    registerFilter: els.registerFilter.value,
    varyingOnly: els.varyingOnly.checked,
    attemptedOnly: els.attemptedOnly.checked,
    labeledOnly: els.labeledOnly.checked,
    diffOnly: els.diffOnly.checked,
    equalsOnly: els.equalsOnly.checked,
    hideIrrelevants: els.hideIrrelevants.checked,
    irrelevantsOnly: els.irrelevantsOnly.checked,
    hideAllNull: els.hideAllNull.checked,
    hideAllZero: els.hideAllZero.checked,
    hideConstants: els.hideConstants.checked,
    hideNoConsensus: els.hideNoConsensus.checked,
    relevantOnly: els.relevantOnly.checked,
  };
  localStorage.setItem(filterStateKey, JSON.stringify(saved));
}

function applyFilterState() {
  const saved = loadFilterState();
  if (!saved) return;
  applySelectState(els.deviceSelect, saved.device);
  applySelectState(els.powerSelect, saved.power);
  applySelectState(els.layoutSelect, saved.layout);
  applySelectState(els.primarySelect, saved.primary);
  if (saved.audio) applySelectState(els.audioSelect, saved.audio);
  applySelectState(els.pipSizeSelect, saved.pipSize);
  applySelectState(els.secondarySelect, saved.secondary);
  applySelectState(els.connectedSelect, saved.connected);
  if (saved.jogButton) applySelectState(els.jogButtonSelect, saved.jogButton);
  applySelectState(els.compareSelect, saved.compare);
  if (saved.registerFilter != null) els.registerFilter.value = saved.registerFilter;
  if (saved.varyingOnly != null) els.varyingOnly.checked = saved.varyingOnly;
  if (saved.attemptedOnly != null) els.attemptedOnly.checked = saved.attemptedOnly;
  if (saved.labeledOnly != null) els.labeledOnly.checked = saved.labeledOnly;
  if (saved.diffOnly != null) els.diffOnly.checked = saved.diffOnly;
  if (saved.equalsOnly != null) els.equalsOnly.checked = saved.equalsOnly;
  if (saved.hideIrrelevants != null) els.hideIrrelevants.checked = saved.hideIrrelevants;
  if (saved.irrelevantsOnly != null) els.irrelevantsOnly.checked = saved.irrelevantsOnly;
  if (saved.hideAllNull != null) els.hideAllNull.checked = saved.hideAllNull;
  if (saved.hideAllZero != null) els.hideAllZero.checked = saved.hideAllZero;
  if (saved.hideConstants != null) els.hideConstants.checked = saved.hideConstants;
  if (saved.hideNoConsensus != null) els.hideNoConsensus.checked = saved.hideNoConsensus;
  if (saved.relevantOnly != null) els.relevantOnly.checked = saved.relevantOnly;
}

function applySelectState(select, savedValues) {
  if (!Array.isArray(savedValues)) return;
  const available = new Set([...select.options].map((o) => o.value));
  const toSelect = new Set(savedValues.filter((v) => available.has(v)));
  [...select.options].forEach((o) => { o.selected = toSelect.has(o.value); });
}

function csvEscape(value) {
  const s = String(value ?? "");
  return s.includes(",") || s.includes('"') || s.includes("\n") ? `"${s.replace(/"/g, '""')}"` : s;
}

async function copyMatrixCsv() {
  const captures = getVisibleCaptures();
  const columns = getVisibleColumns(captures);
  if (!captures.length || !columns.length) {
    window.alert("Nothing visible to copy.");
    return;
  }

  const header = [
    "capture_id",
    "state",
    ...columns.map(({ device, reg }) => {
      const alias = getAlias(device, reg);
      return alias ? `${alias} (${device}:${reg})` : `${device}:${reg}`;
    }),
  ];

  const rows = captures.map((capture) => [
    capture.capture_id,
    capture.state_label ?? "",
    ...columns.map(({ device, reg }) => formatCellState(valueState(capture, device, reg))),
  ]);

  const csv = [header, ...rows].map((row) => row.map(csvEscape).join(",")).join("\n");

  await navigator.clipboard.writeText(csv);
  const orig = els.copyCsvBtn.textContent;
  els.copyCsvBtn.textContent = "Copied!";
  setTimeout(() => { els.copyCsvBtn.textContent = orig; }, 1500);
}

function resetAllFilters() {
  els.testCaseSelect.value = "";
  localStorage.removeItem(filterStateKey);
  [els.deviceSelect, els.powerSelect, els.layoutSelect, els.primarySelect, els.audioSelect, els.pipSizeSelect, els.secondarySelect, els.connectedSelect, els.jogButtonSelect].forEach((sel) => {
    [...sel.options].forEach((o) => { o.selected = true; });
  });
  clearSelections(els.compareSelect);
  els.registerFilter.value = "";
  els.varyingOnly.checked = false;
  els.attemptedOnly.checked = false;
  els.labeledOnly.checked = false;
  els.diffOnly.checked = false;
  els.equalsOnly.checked = false;
  els.hideIrrelevants.checked = false;
  els.irrelevantsOnly.checked = false;
  els.hideAllNull.checked = false;
  els.hideAllZero.checked = false;
  els.hideConstants.checked = false;
  els.hideNoConsensus.checked = false;
  els.relevantOnly.checked = false;
  updateFilterSummaries();
  render();
  syncTestCasePreset();
}

function getIrrelevantCount(device, reg) {
  return state.irrelevantCounts[columnKey(device, reg)] ?? 0;
}

function adjustIrrelevancy(device, reg, delta) {
  const key = columnKey(device, reg);
  const next = Math.max(0, (state.irrelevantCounts[key] ?? 0) + delta);
  if (next === 0) {
    delete state.irrelevantCounts[key];
  } else {
    state.irrelevantCounts[key] = next;
  }
  saveIrrelevantCounts();
  render();
}

function resetRelevants() {
  const count = Object.keys(state.relevants).length;
  if (!count) return;
  if (!window.confirm(`Clear all ${count} relevance assignment(s)?`)) return;
  state.relevants = {};
  saveRelevants();
  render();
}

function resetIrrelevancy() {
  if (!window.confirm("Reset all irrelevancy counts?")) return;
  state.irrelevantCounts = {};
  saveIrrelevantCounts();
  render();
}

function markVisibleAsIrrelevant() {
  const captures = getVisibleCaptures();
  const columns = getVisibleColumns(captures);
  if (!columns.length) {
    window.alert("No visible registers to mark.");
    return;
  }
  if (!window.confirm(`Add 1 to the irrelevancy count for ${columns.length} visible register(s)?`)) return;
  for (const { device, reg } of columns) {
    const key = columnKey(device, reg);
    state.irrelevantCounts[key] = (state.irrelevantCounts[key] ?? 0) + 1;
  }
  saveIrrelevantCounts();
  render();
}

function markIntraPairNoiseAsIrrelevant() {
  const selectedDevices = getSelectedValues(els.deviceSelect);
  const allCaptures = state.data.captures.filter((c) => !state.excludedCaptures.has(c.capture_id));

  function capturesForTestCase(tc) {
    return allCaptures.filter((c) => {
      if (tc.filters.power && !tc.filters.power.includes(c.power_state)) return false;
      if (tc.filters.layout && !tc.filters.layout.includes(c.layout_mode)) return false;
      if (tc.filters.primary && !tc.filters.primary.includes(c.primary_input)) return false;
      if (tc.filters.secondary && !tc.filters.secondary.includes(c.secondary_input)) return false;
      if (tc.filters.audio && !tc.filters.audio.includes(c.audio_side)) return false;
      if (tc.filters.size && !tc.filters.size.includes(capturePipSizeLabel(c))) return false;
      return true;
    });
  }

  const noisy = new Set();
  let testedCount = 0;
  for (const tc of TEST_CASES) {
    const pair = capturesForTestCase(tc);
    if (pair.length < 2) continue;
    testedCount++;
    const [a, b] = pair;
    for (const device of selectedDevices) {
      const regs = state.deviceColumns.get(device) ?? [];
      for (const reg of regs) {
        const va = valueState(a, device, reg);
        const vb = valueState(b, device, reg);
        if (va.kind !== vb.kind || va.value !== vb.value) {
          noisy.add(columnKey(device, reg));
        }
      }
    }
  }

  if (!noisy.size) {
    window.alert(`Checked ${testedCount} test case(s) — no intra-pair differences found.`);
    return;
  }
  if (!window.confirm(`Checked ${testedCount} test case(s). Add 1 to the irrelevancy count for ${noisy.size} register(s) that differ within at least one pair?`)) return;
  for (const key of noisy) {
    state.irrelevantCounts[key] = (state.irrelevantCounts[key] ?? 0) + 1;
  }
  saveIrrelevantCounts();
  render();
}

function renderCaptureList() {
  const hiddenCount = state.excludedCaptures.size;
  els.captureFilterBadge.textContent = hiddenCount ? `${hiddenCount} hidden` : "";
  els.captureFilterBadge.className = hiddenCount ? "badge active" : "badge";

  const sorted = [...state.data.captures].sort((a, b) =>
    (b.captured_at ?? "").localeCompare(a.captured_at ?? ""),
  );

  els.captureFilterList.innerHTML = sorted
    .map((capture) => {
      const excluded = state.excludedCaptures.has(capture.capture_id);
      return `
        <label class="capture-filter-item${excluded ? " excluded" : ""}" title="${escapeHtml(capture.capture_id)}">
          <input type="checkbox" class="capture-filter-check" ${excluded ? "" : "checked"} data-id="${escapeHtml(capture.capture_id)}" />
          <span class="capture-filter-code">${escapeHtml(captureStatusCode(capture))}</span>
          <span class="capture-filter-id">${escapeHtml(capture.capture_id)}</span>
        </label>`;
    })
    .join("");

  els.captureFilterList.querySelectorAll(".capture-filter-check").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      const id = checkbox.dataset.id;
      if (checkbox.checked) {
        state.excludedCaptures.delete(id);
      } else {
        state.excludedCaptures.add(id);
      }
      saveExcluded();
      renderCaptureList();
      render();
    });
  });
}

function loadAliases() {
  try {
    return JSON.parse(localStorage.getItem(aliasStorageKey) || "{}");
  } catch {
    return {};
  }
}

function saveAliases() {
  localStorage.setItem(aliasStorageKey, JSON.stringify(state.aliases));
}

function getAlias(device, reg) {
  const key = aliasKey(device, reg);
  return state.aliases[key] || defaultAliases[key] || "";
}

function renameAlias(device, reg) {
  const current = getAlias(device, reg);
  const next = window.prompt(`Label for ${device} ${reg}`, current);
  if (next === null) return;
  const trimmed = next.trim();
  const key = aliasKey(device, reg);
  if (!trimmed || trimmed === defaultAliases[key]) {
    delete state.aliases[key];
  } else {
    state.aliases[key] = trimmed;
  }
  saveAliases();
  render();
}

function resetAlias(device, reg) {
  delete state.aliases[aliasKey(device, reg)];
  saveAliases();
  render();
}

function resetSelectedDeviceAliases() {
  const selectedDevices = getSelectedValues(els.deviceSelect);
  if (!selectedDevices.length) return;
  const scope = selectedDevices.length === 1 ? selectedDevices[0] : `${selectedDevices.length} selected devices`;
  if (!window.confirm(`Reset all custom labels for ${scope}?`)) {
    return;
  }
  for (const key of Object.keys(state.aliases)) {
    if (selectedDevices.some((device) => key.startsWith(`${device}:`))) {
      delete state.aliases[key];
    }
  }
  saveAliases();
  render();
}

function resetAllAliases() {
  if (!window.confirm("Reset all custom labels for every device?")) {
    return;
  }
  state.aliases = {};
  saveAliases();
  render();
}

function hydrateTestCaseSelect() {
  const groups = [
    { label: "Baseline", slice: [0, 2] },
    { label: "Group A — Primary: TB", slice: [2, 13] },
    { label: "Group B — Primary: HDMI", slice: [13, 24] },
    { label: "Group C — Primary: DP", slice: [24, 35] },
  ];
  els.testCaseSelect.innerHTML = '<option value="">— None —</option>';
  for (const { label, slice } of groups) {
    const group = document.createElement("optgroup");
    group.label = label;
    for (const tc of TEST_CASES.slice(slice[0], slice[1])) {
      const opt = document.createElement("option");
      opt.value = String(tc.num);
      opt.textContent = tc.label;
      group.appendChild(opt);
    }
    els.testCaseSelect.appendChild(group);
  }

  const jogNums = [...new Set(
    state.data.captures
      .filter((c) => (c.test_case ?? 0) >= 50)
      .map((c) => c.test_case)
  )].sort((a, b) => a - b);
  if (jogNums.length > 0) {
    const group = document.createElement("optgroup");
    group.label = "Jog Scans";
    for (const num of jogNums) {
      const sample = state.data.captures.find((c) => c.test_case === num);
      const opt = document.createElement("option");
      opt.value = String(num);
      opt.textContent = `${num} — ${sample?.state_label ?? "JOG"}`;
      group.appendChild(opt);
    }
    els.testCaseSelect.appendChild(group);
  }
}

function syncTestCasePreset() {
  const match = findMatchingTestCase();
  els.testCaseSelect.value = match ? String(match.num) : "";
}

function findMatchingTestCase() {
  const power = getSelectedValues(els.powerSelect).sort();
  const layout = getSelectedValues(els.layoutSelect).sort();
  const primary = getSelectedValues(els.primarySelect).sort();
  const audioValues = getSelectedValues(els.audioSelect);
  const audioAny = audioValues.includes("any");
  const audioSpecific = audioValues.filter((v) => v !== "any").sort();
  const pipSizes = getSelectedValues(els.pipSizeSelect);
  const pipSizeAny = pipSizes.includes("any");
  const pipSizeSpecific = pipSizes.filter((v) => v !== "any").sort();
  const secondary = getSelectedValues(els.secondarySelect).sort();
  const allSecondary = [...els.secondarySelect.options].map((o) => o.value).sort();
  const secondaryIsRestricted = !arraysEqual(secondary, allSecondary);

  return TEST_CASES.find((tc) => {
    if (tc.filters.power && !arraysEqual(power, [...tc.filters.power].sort())) return false;
    if (tc.filters.layout && !arraysEqual(layout, [...tc.filters.layout].sort())) return false;
    if (tc.filters.primary && !arraysEqual(primary, [...tc.filters.primary].sort())) return false;
    if (!audioAny) {
      if (!tc.filters.audio) return false;
      if (!arraysEqual(audioSpecific, [...tc.filters.audio].sort())) return false;
    }
    if (!pipSizeAny) {
      if (!tc.filters.size) return false;
      if (!arraysEqual(pipSizeSpecific, [...tc.filters.size].sort())) return false;
    }
    if (secondaryIsRestricted) {
      if (!tc.filters.secondary) return false;
      if (!arraysEqual(secondary, [...tc.filters.secondary].sort())) return false;
    }
    return true;
  });
}

function applyJogTcPreset(num) {
  const sample = state.data.captures.find((c) => c.test_case === num);
  const baseTcNum = sample?.base_test_case;
  const baseTc = baseTcNum != null ? TEST_CASES.find((t) => t.num === baseTcNum) : null;
  if (baseTc) {
    applyTestCasePreset(baseTc);
    // Override jog button filter to the specific button for this jog TC
    const btn = sample?.jog_button;
    if (btn) applySelectState(els.jogButtonSelect, [btn]);
    updateFilterSummaries();
    saveFilterState();
    render();
  } else {
    render();
  }
}

function applyTestCasePreset(tc) {
  const allValues = (select) => [...select.options].map((o) => o.value);
  applySelectState(els.powerSelect, tc.filters.power ?? allValues(els.powerSelect));
  applySelectState(els.layoutSelect, tc.filters.layout ?? allValues(els.layoutSelect));
  applySelectState(els.primarySelect, tc.filters.primary ?? allValues(els.primarySelect));
  applySelectState(els.audioSelect, tc.filters.audio ?? ["any"]);
  applySelectState(els.pipSizeSelect, tc.filters.size ?? ["any"]);
  applySelectState(els.secondarySelect, tc.filters.secondary ?? allValues(els.secondarySelect));
  applySelectState(els.connectedSelect, ["any"]);
  applySelectState(els.jogButtonSelect, ["none"]);
  updateFilterSummaries();
  saveFilterState();
  render();
}

function arraysEqual(a, b) {
  return a.length === b.length && a.every((v, i) => v === b[i]);
}

function capturePipSizeLabel(capture) {
  const size = capture.pip?.size;
  if (size === 1) return "small";
  if (size === 2) return "medium";
  if (size === 3) return "large";
  return null;
}

function captureStatusCode(capture, deviceOverride = null) {
  const deviceCode = deviceOverride || selectedDeviceScopeCode();
  const connected = compactArrayCode(capture.connected_inputs);
  const signal = compactArrayCode(capture.signal_present_inputs);
  return [
    deviceCode,
    capture.power_state ?? "-",
    capture.layout_mode ?? "-",
    capture.primary_input ?? "-",
    connected,
    signal,
  ].join("|");
}

function selectedDeviceScopeCode() {
  const devices = getSelectedValues(els.deviceSelect);
  return devices.length ? devices.join("+") : "-";
}

function compactArrayCode(values) {
  return values?.length ? values.join("+") : "-";
}

function hasActiveSelection() {
  const selection = window.getSelection();
  return !!selection && !selection.isCollapsed && selection.toString().trim().length > 0;
}

function compareHexRegs(left, right) {
  return parseInt(left, 16) - parseInt(right, 16);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
