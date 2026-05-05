const dataUrls = {
  captures: "./data/register-explorer.json",
  inventory: "./data/source-inventory.json",
};

const aliasStorageKey = "register-explorer-aliases-v1";
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

const state = {
  data: null,
  inventory: null,
  deviceColumns: new Map(),
  selectedCell: null,
  selectedCaptureId: null,
  aliases: loadAliases(),
};

const els = {
  datasetMeta: document.querySelector("#dataset-meta"),
  headerStack: document.querySelector("#header-stack"),
  headerToggle: document.querySelector("#header-toggle"),
  deviceSelect: document.querySelector("#device-select"),
  powerSelect: document.querySelector("#power-select"),
  layoutSelect: document.querySelector("#layout-select"),
  primarySelect: document.querySelector("#primary-select"),
  connectedSelect: document.querySelector("#connected-select"),
  signalInputSelect: document.querySelector("#signal-input-select"),
  registerFilter: document.querySelector("#register-filter"),
  compareSelect: document.querySelector("#compare-select"),
  varyingOnly: document.querySelector("#varying-only"),
  attemptedOnly: document.querySelector("#attempted-only"),
  labeledOnly: document.querySelector("#labeled-only"),
  diffOnly: document.querySelector("#diff-only"),
  registerSummary: document.querySelector("#register-summary"),
  inventorySummary: document.querySelector("#inventory-summary"),
  matrixHead: document.querySelector("#matrix-table thead"),
  matrixBody: document.querySelector("#matrix-table tbody"),
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
  const response = await fetch(url);
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
  fillMultiSelect(els.deviceSelect, [...state.deviceColumns.keys()]);
  fillMultiSelect(els.powerSelect, facetValues("power_state"));
  fillMultiSelect(els.layoutSelect, facetValues("layout_mode"));
  fillMultiSelect(els.primarySelect, facetValues("primary_input"));
  fillMultiSelect(els.connectedSelect, ["hdmi", "dp", "tb"]);
  fillMultiSelect(els.signalInputSelect, ["hdmi", "dp", "tb"]);
  fillCompareSelect();
  installMultiSelectBehavior();
  updateFilterSummaries();
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

  [
    els.deviceSelect,
    els.powerSelect,
    els.layoutSelect,
    els.primarySelect,
    els.connectedSelect,
    els.signalInputSelect,
    els.compareSelect,
    els.varyingOnly,
    els.attemptedOnly,
    els.labeledOnly,
    els.diffOnly,
  ].forEach((element) => {
    element.addEventListener("change", () => {
      updateFilterSummaries();
      render();
    });
  });

  els.registerFilter.addEventListener("input", () => render());

  document.querySelectorAll(".filter-action").forEach((button) => {
    button.addEventListener("click", () => {
      const select = document.querySelector(`#${button.dataset.target}`);
      if (!(select instanceof HTMLSelectElement)) return;
      if (button.dataset.action === "none") {
        clearSelections(select);
        updateFilterSummaries();
        render();
        return;
      }
      [...select.options].forEach((option) => {
        option.selected = true;
      });
      updateFilterSummaries();
      render();
    });
  });
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
  const connectedInputs = getSelectedValues(els.connectedSelect);
  const signalInputs = getSelectedValues(els.signalInputSelect);
  const filterPowers = isRestrictiveSelection(els.powerSelect, powers);
  const filterLayouts = isRestrictiveSelection(els.layoutSelect, layouts);
  const filterPrimaries = isRestrictiveSelection(els.primarySelect, primaries);
  const filterConnected = isRestrictiveSelection(els.connectedSelect, connectedInputs);
  const filterSignal = isRestrictiveSelection(els.signalInputSelect, signalInputs);

  return state.data.captures.filter((capture) => {
    if (selectedDevices.length && !selectedDevices.some((device) => capture.devices[device])) return false;
    if (filterPowers && !powers.includes(capture.power_state)) return false;
    if (filterLayouts && !layouts.includes(capture.layout_mode)) return false;
    if (filterPrimaries && !primaries.includes(capture.primary_input)) return false;
    if (filterConnected && !hasOverlap(capture.connected_inputs ?? [], connectedInputs)) return false;
    if (filterSignal && !hasOverlap(capture.signal_present_inputs ?? [], signalInputs)) return false;
    return true;
  });
}

function getVisibleColumns(captures) {
  const compareCaptures = getCompareCaptures();
  const registerFilter = normalizeRegFilter(els.registerFilter.value);
  const showVaryingOnly = els.varyingOnly.checked;
  const attemptedOnly = els.attemptedOnly.checked;
  const labeledOnly = els.labeledOnly.checked;
  const diffOnly = els.diffOnly.checked;
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
      if (
        diffOnly &&
        compareCaptures.length &&
        !captures.some((capture) => changedAgainstAny(capture, compareCaptures, device, reg))
      ) {
        continue;
      }

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

  els.datasetMeta.innerHTML = `
    <div><strong>Generated:</strong> ${escapeHtml(state.data.generated_at)}</div>
    <div><strong>Total / Visible:</strong> ${state.data.captures.length} / ${captures.length}</div>
    <div><strong>Modes:</strong> ${captureModeSummary(captures)}</div>
    <div><strong>Devices:</strong> ${escapeHtml(selectedDevices.join(", ") || "none")}</div>
    <div><strong>Compare:</strong> ${compareCaptures.length} baseline(s)</div>
  `;

  els.registerSummary.innerHTML = `
    <div><strong>${columns.length}</strong> visible register(s)</div>
    <div><strong>${nullCount}</strong> attempted null cell(s)</div>
    <div>${activeRegisterFilterSummary()}</div>
  `;

  const selectedDeviceSummary = selectedDevices.length === 1 ? selectedDevices[0] : `${selectedDevices.length} selected devices`;
  els.inventorySummary.innerHTML = `
    <div><strong>${namedVisible}</strong> visible register(s) have labels</div>
    <div><strong>${Object.keys(state.aliases).length}</strong> custom rename(s) saved locally</div>
    <div class="header-actions">
      <button class="mini-button" id="reset-device-aliases" type="button">Reset Device Labels</button>
      <button class="mini-button" id="reset-all-aliases" type="button">Reset All Labels</button>
    </div>
    <div class="hint">Device reset applies to ${escapeHtml(selectedDeviceSummary)}.</div>
  `;
  document.querySelector("#reset-device-aliases")?.addEventListener("click", resetSelectedDeviceAliases);
  document.querySelector("#reset-all-aliases")?.addEventListener("click", resetAllAliases);
}

function activeRegisterFilterSummary() {
  const filters = [];
  if (els.varyingOnly.checked) filters.push("varying only");
  if (els.attemptedOnly.checked) filters.push("attempted by all");
  if (els.labeledOnly.checked) filters.push("labeled only");
  if (els.diffOnly.checked) filters.push("changed vs compare");
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
      <div class="capture-label ${capture.capture_id === state.selectedCaptureId ? "selected" : ""}" data-capture-id="${escapeHtml(capture.capture_id)}" title="${escapeHtml(captureStatusCode(capture))}">
        <div class="capture-title">${escapeHtml(captureStatusCode(capture))}</div>
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
      cell.className = `cell ${cellState.kind}${changedAgainstAny(capture, compareCaptures, column.device, column.reg) ? " changed" : ""}`;
      if (
        state.selectedCell &&
        state.selectedCell.captureId === capture.capture_id &&
        state.selectedCell.device === column.device &&
        state.selectedCell.reg === column.reg
      ) {
        cell.classList.add("selected");
      }
      cell.textContent = formatCellState(cellState);
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
    <div class="header-actions">
      <button class="mini-button" id="rename-current-register" type="button">Rename Register</button>
      <button class="mini-button" id="reset-current-register" type="button">Reset Label</button>
    </div>
  `;
  document.querySelector("#rename-current-register")?.addEventListener("click", () => renameAlias(device, reg));
  document.querySelector("#reset-current-register")?.addEventListener("click", () => resetAlias(device, reg));
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
      <button class="mini-button danger" id="delete-capture-btn" type="button">Delete Capture</button>
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
    els.connectedSelect,
    els.signalInputSelect,
    els.compareSelect,
  ].forEach((select) => {
    select.addEventListener("mousedown", (event) => {
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
        render();
      });
    });
  });
}

function updateFilterSummaries() {
  updateFilterSummary(els.deviceSelect, "device-select-summary");
  updateFilterSummary(els.powerSelect, "power-select-summary");
  updateFilterSummary(els.layoutSelect, "layout-select-summary");
  updateFilterSummary(els.primarySelect, "primary-select-summary");
  updateFilterSummary(els.connectedSelect, "connected-select-summary");
  updateFilterSummary(els.signalInputSelect, "signal-input-select-summary");
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
