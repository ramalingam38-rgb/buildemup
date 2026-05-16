/**
 * BuildemUp Brief Form — vanilla JS.
 *
 * Handles:
 *   - 4-step wizard navigation
 *   - Dynamic floor composition (G, G+1, G+2, G+3)
 *   - Plot-type-aware UI (semi-detached shows shared_side picker;
 *     corner plot shows second road field)
 *   - Vastu partial-items loaded from API
 *   - localStorage save/resume with generated token (Q3 decision)
 *   - Submit → POST /api/brief/capture, render result
 *
 * No framework. No build step. Deploys as-is.
 */

// ─── Configuration ──────────────────────────────────────────────────────
const API_BRIEF = "/api/brief/capture";
const API_VASTU_ITEMS = "/api/vastu/partial-items";
const LOCALSTORAGE_KEY_PREFIX = "buildemup_brief_";

// ─── Unit conversion helpers (added in v0.10.1 — feet UI) ───────────────
// User enters feet, API expects metres. All conversions kept in one place.
const FT_PER_M = 3.28084;
const M_PER_FT = 0.3048;
const SQFT_PER_SQM = 10.7639;

function feetToMetres(ft) {
  return Number((ft * M_PER_FT).toFixed(4));  // 4 decimal places preserved
}
function metresToFeet(m) {
  return Number((m * FT_PER_M).toFixed(2));
}
function sqmToSqft(sqm) {
  return Math.round(sqm * SQFT_PER_SQM);
}
function fmtFeet(m) {
  // Render a metre value as "X.X ft (Y.Y m)" for display
  return `${metresToFeet(m).toFixed(1)} ft (${m.toFixed(2)} m)`;
}
function fmtArea(sqm) {
  // Render an area as "X sqft (Y sqm)" for display
  return `${sqmToSqft(sqm)} sqft (${sqm.toFixed(0)} sqm)`;
}

// ─── Room defaults (match NBC typical Indian residential) ────────────────
const DEFAULT_ROOMS_BY_FLOOR = {
  ground_residential: [
    { room_type: "living", count: 1 },
    { room_type: "kitchen", count: 1 },
    { room_type: "bathroom_common", count: 1 },
    { room_type: "pooja", count: 1 },
  ],
  upper_residential: [
    { room_type: "bedroom_master", count: 1 },
    { room_type: "bathroom_attached", count: 1 },
    { room_type: "bedroom_regular", count: 1 },
    { room_type: "bathroom_common", count: 1 },
  ],
  terrace: [
    { room_type: "utility", count: 1 },
  ],
  stilt: [],
};

const ROOM_TYPES = [
  { value: "bedroom_master",     label: "Master bedroom" },
  { value: "bedroom_regular",    label: "Regular bedroom" },
  { value: "bathroom_attached",  label: "Bathroom (attached)" },
  { value: "bathroom_common",    label: "Bathroom (common)" },
  { value: "kitchen",            label: "Kitchen" },
  { value: "living",             label: "Living" },
  { value: "dining",             label: "Dining" },
  { value: "pooja",              label: "Pooja" },
  { value: "balcony",            label: "Balcony" },
  { value: "utility",            label: "Utility" },
  { value: "store",              label: "Store" },
  { value: "staircase",          label: "Staircase" },
];

const FLOOR_USES = [
  { value: "residential",           label: "Residential" },
  { value: "stilt_parking",         label: "Stilt parking (ground floor only)" },
  { value: "terrace_accessible",    label: "Terrace (accessible, top only)" },
  { value: "terrace_inaccessible",  label: "Terrace (inaccessible, top only)" },
];

// ─── State ───────────────────────────────────────────────────────────────
let currentStep = 1;
const totalSteps = 4;
let resumeToken = null;

// ─── Elements ────────────────────────────────────────────────────────────
const form = document.getElementById("brief-form");
const prevBtn = document.getElementById("prev-btn");
const nextBtn = document.getElementById("next-btn");
const submitBtn = document.getElementById("submit-btn");
const saveLaterBtn = document.getElementById("save-later-btn");
const plotTypeSelect = document.getElementById("plot-type-select");
const sharedSideContainer = document.getElementById("shared-side-container");
const cornerPlotCheck = document.getElementById("corner-plot-check");
const secondRoadContainer = document.getElementById("second-road-container");
const floorCountSelect = document.getElementById("floor-count-select");
const floorList = document.getElementById("floor-list");
const vastuPartialList = document.getElementById("vastu-partial-list");
const resultPanel = document.getElementById("result-panel");

// ─── Wizard navigation ───────────────────────────────────────────────────
function showStep(n) {
  document.querySelectorAll(".step-panel").forEach(panel => {
    panel.classList.toggle(
      "hidden", Number(panel.dataset.step) !== n
    );
  });
  document.querySelectorAll(".step-indicator").forEach(ind => {
    const stepNum = Number(ind.dataset.step);
    const circle = ind.querySelector(".step-num");
    const label = ind.querySelector("span:last-child");
    if (stepNum < n) {
      // Completed
      circle.className = "step-num w-8 h-8 flex items-center justify-center rounded-full border-2 border-blue-600 bg-blue-600 text-white font-semibold";
      label.className = "ml-2 text-gray-700";
      circle.textContent = "✓";
    } else if (stepNum === n) {
      circle.className = "step-num w-8 h-8 flex items-center justify-center rounded-full border-2 border-blue-600 bg-blue-600 text-white font-semibold";
      label.className = "ml-2 text-gray-700";
      circle.textContent = String(stepNum);
    } else {
      circle.className = "step-num w-8 h-8 flex items-center justify-center rounded-full border-2 border-gray-300 bg-white text-gray-500 font-semibold";
      label.className = "ml-2 text-gray-500";
      circle.textContent = String(stepNum);
    }
  });
  prevBtn.classList.toggle("hidden", n === 1);
  nextBtn.classList.toggle("hidden", n === totalSteps);
  submitBtn.classList.toggle("hidden", n !== totalSteps);
}

nextBtn.addEventListener("click", () => {
  if (!validateStep(currentStep)) return;
  if (currentStep < totalSteps) {
    currentStep += 1;
    if (currentStep === 2) rebuildFloorList();
    if (currentStep === 3 && typeof refreshNbcSetbackHint === "function") {
      refreshNbcSetbackHint();
    }
    showStep(currentStep);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
});

prevBtn.addEventListener("click", () => {
  if (currentStep > 1) {
    currentStep -= 1;
    showStep(currentStep);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
});

function validateStep(n) {
  // Light validation — required fields. Heavy validation is server-side.
  const panel = document.querySelector(`.step-panel[data-step="${n}"]`);
  const requiredInputs = panel.querySelectorAll("[required]");
  for (const inp of requiredInputs) {
    if (!inp.value || inp.value.trim() === "") {
      inp.focus();
      inp.classList.add("border-red-500");
      alert("Please fill all required fields marked with *");
      return false;
    }
    inp.classList.remove("border-red-500");
  }
  // Step 3: min ≤ max budget
  if (n === 3) {
    const minB = Number(form.budget_min_lakhs.value);
    const maxB = Number(form.budget_max_lakhs.value);
    if (minB > maxB) {
      alert("Budget minimum cannot exceed maximum.");
      return false;
    }
  }
  return true;
}

// ─── Plot-type-aware UI ──────────────────────────────────────────────────
plotTypeSelect.addEventListener("change", () => {
  const isSemi = plotTypeSelect.value === "semi_detached";
  sharedSideContainer.classList.toggle("hidden", !isSemi);
  const sharedSelect = form.shared_side;
  if (sharedSelect) sharedSelect.required = isSemi;
});

cornerPlotCheck.addEventListener("change", () => {
  const isCorner = cornerPlotCheck.checked;
  secondRoadContainer.classList.toggle("hidden", !isCorner);
  const srInput = form.second_road_width_ft;
  if (srInput) srInput.required = isCorner;
});

// ─── NBC setback hint (added v0.10.1) ───────────────────────────────────
// When the user reaches Step 3 (or changes the city/plot dimensions/type),
// fetch the NBC-required setbacks from the server and display in feet.
// Best-effort — silently hide the hint if API errors out.
const nbcHintBox = document.getElementById("nbc-setback-hint");
const nbcHintText = document.getElementById("nbc-setback-hint-text");

async function refreshNbcSetbackHint() {
  if (!nbcHintBox || !nbcHintText) return;
  // Need plot dimensions to make the call
  const widthFt = Number(form.plot_width_ft.value);
  const depthFt = Number(form.plot_depth_ft.value);
  const roadFt = Number(form.road_width_ft.value);
  if (!widthFt || !depthFt || !roadFt) {
    nbcHintBox.classList.add("hidden");
    return;
  }

  const payload = {
    city: form.city.value,
    plot_width_m: feetToMetres(widthFt),
    plot_depth_m: feetToMetres(depthFt),
    plot_facing: form.plot_facing.value,
    plot_type: form.plot_type.value,
    road_width_m: feetToMetres(roadFt),
    corner_plot: form.corner_plot.checked,
    second_road_width_m: form.corner_plot.checked && form.second_road_width_ft.value
      ? feetToMetres(Number(form.second_road_width_ft.value))
      : null,
    shared_side: form.plot_type.value === "semi_detached"
      ? (form.shared_side ? form.shared_side.value : null)
      : null,
  };

  try {
    const resp = await fetch("/api/setback/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!resp.ok || !data.ok) {
      nbcHintBox.classList.add("hidden");
      return;
    }
    nbcHintText.textContent =
      `Front ${data.front_ft.toFixed(1)} ft, ` +
      `Rear ${data.rear_ft.toFixed(1)} ft, ` +
      `Left ${data.side_left_ft.toFixed(1)} ft, ` +
      `Right ${data.side_right_ft.toFixed(1)} ft ` +
      `(per ${data.source_authority}). You may enter different values; ` +
      `we'll flag compliance.`;
    nbcHintBox.classList.remove("hidden");
  } catch (_) {
    nbcHintBox.classList.add("hidden");
  }
}

// Refresh the hint whenever any input that affects setback rules changes
[
  "plot_width_ft", "plot_depth_ft", "road_width_ft",
  "city", "plot_type", "corner_plot", "second_road_width_ft",
  "shared_side",
].forEach((fieldName) => {
  const el = form[fieldName];
  if (el) el.addEventListener("change", refreshNbcSetbackHint);
});

// ─── Floor composition (dynamic per floor count) ────────────────────────
floorCountSelect.addEventListener("change", rebuildFloorList);

function rebuildFloorList() {
  const count = Number(floorCountSelect.value);
  floorList.innerHTML = "";

  for (let i = 0; i < count; i += 1) {
    const isGround = (i === 0);
    const isTop = (i === count - 1 && count >= 3);
    let defaultUse, defaultRooms;
    if (isGround) {
      defaultUse = "residential";
      defaultRooms = DEFAULT_ROOMS_BY_FLOOR.ground_residential;
    } else if (isTop) {
      defaultUse = "terrace_accessible";
      defaultRooms = DEFAULT_ROOMS_BY_FLOOR.terrace;
    } else {
      defaultUse = "residential";
      defaultRooms = DEFAULT_ROOMS_BY_FLOOR.upper_residential;
    }

    const floorPanel = document.createElement("div");
    floorPanel.className = "p-4 rounded-md border border-gray-200 bg-gray-50";
    floorPanel.dataset.floorNumber = String(i);
    const label = isGround ? "Ground floor" : `Floor ${i}`;

    const useOptions = FLOOR_USES.map(fu =>
      `<option value="${fu.value}"${fu.value === defaultUse ? " selected" : ""}>${fu.label}</option>`
    ).join("");

    const roomRows = defaultRooms.map((r, idx) => renderRoomRow(i, idx, r)).join("");

    floorPanel.innerHTML = `
      <div class="flex items-baseline justify-between mb-3">
        <h4 class="font-semibold">${label}</h4>
        <select class="floor-use-select text-sm px-2 py-1 border border-gray-300 rounded-md"
                data-floor="${i}">
          ${useOptions}
        </select>
      </div>
      <div class="rooms-container space-y-2" data-floor="${i}">
        ${roomRows}
      </div>
      <button type="button" class="add-room-btn mt-3 text-xs text-blue-600 underline underline-offset-2"
              data-floor="${i}">+ Add room</button>
    `;
    floorList.appendChild(floorPanel);
  }

  // Wire up add-room and floor-use-change handlers
  floorList.querySelectorAll(".add-room-btn").forEach(btn => {
    btn.addEventListener("click", () => addRoomRow(Number(btn.dataset.floor)));
  });
  floorList.querySelectorAll(".floor-use-select").forEach(sel => {
    sel.addEventListener("change", () => onFloorUseChange(Number(sel.dataset.floor), sel.value));
  });
  floorList.querySelectorAll(".remove-room-btn").forEach(btn => {
    btn.addEventListener("click", (e) => e.target.closest(".room-row").remove());
  });
}

function renderRoomRow(floorIdx, roomIdx, defaultRoom = {}) {
  const defaultType = defaultRoom.room_type || "bedroom_regular";
  const defaultCount = defaultRoom.count || 1;
  const typeOptions = ROOM_TYPES.map(rt =>
    `<option value="${rt.value}"${rt.value === defaultType ? " selected" : ""}>${rt.label}</option>`
  ).join("");
  return `
    <div class="room-row flex items-center gap-2" data-room="${roomIdx}">
      <select class="room-type-select flex-1 px-2 py-1 text-sm border border-gray-300 rounded-md">
        ${typeOptions}
      </select>
      <input type="number" class="room-count-input w-20 px-2 py-1 text-sm border border-gray-300 rounded-md"
             min="1" max="10" value="${defaultCount}">
      <button type="button" class="remove-room-btn text-gray-400 hover:text-red-500" title="Remove">✕</button>
    </div>
  `;
}

function addRoomRow(floorIdx) {
  const container = floorList.querySelector(`.rooms-container[data-floor="${floorIdx}"]`);
  if (!container) return;
  const existingCount = container.querySelectorAll(".room-row").length;
  const tempDiv = document.createElement("div");
  tempDiv.innerHTML = renderRoomRow(floorIdx, existingCount);
  const row = tempDiv.firstElementChild;
  container.appendChild(row);
  row.querySelector(".remove-room-btn").addEventListener("click", () => row.remove());
}

function onFloorUseChange(floorIdx, newUse) {
  // If stilt or terrace_inaccessible, clear rooms (not typically itemized)
  const container = floorList.querySelector(`.rooms-container[data-floor="${floorIdx}"]`);
  if (!container) return;
  if (newUse === "stilt_parking" || newUse === "terrace_inaccessible") {
    container.innerHTML = "";
  }
}

// ─── Vastu partial items loader ──────────────────────────────────────────
async function loadVastuPartialItems() {
  try {
    const resp = await fetch(API_VASTU_ITEMS);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    if (!data.ok) throw new Error("API said not ok");
    vastuPartialList.innerHTML = data.partial_items
      .map(item => `<li>${escapeHtml(item)}</li>`)
      .join("");
  } catch (e) {
    // Fallback: show the items hardcoded (same as server, worst case)
    vastuPartialList.innerHTML = [
      "Main door direction (most important)",
      "Kitchen direction (southeast preferred)",
      "Master bedroom direction (southwest preferred)",
      "Pooja room direction (northeast preferred)",
      "Toilet/bathroom location (avoid northeast)",
      "Staircase direction (avoid northeast)",
      "Water tank location (underground northeast / overhead southwest)",
    ].map(i => `<li>${escapeHtml(i)}</li>`).join("");
  }
}

// ─── Collect form data → JSON payload for API ────────────────────────────
// Form fields are in FEET (user-friendly). API/engine expects METRES.
// We convert here, in one place, so the rest of the JS + entire backend
// don't need to know about the unit change.
function collectFormData() {
  const payload = {
    plot_width_m: feetToMetres(Number(form.plot_width_ft.value)),
    plot_depth_m: feetToMetres(Number(form.plot_depth_ft.value)),
    plot_facing: form.plot_facing.value,
    city: form.city.value,
    road_width_m: feetToMetres(Number(form.road_width_ft.value)),
    plot_type: form.plot_type.value,
    corner_plot: form.corner_plot.checked,
    second_road_width_m: form.corner_plot.checked
      ? feetToMetres(Number(form.second_road_width_ft.value))
      : null,
    shared_side: form.plot_type.value === "semi_detached"
      ? (form.shared_side ? form.shared_side.value : null)
      : null,
    user_setback_front_m: feetToMetres(Number(form.user_setback_front_ft.value)),
    user_setback_rear_m: feetToMetres(Number(form.user_setback_rear_ft.value)),
    user_setback_side_left_m: feetToMetres(Number(form.user_setback_side_left_ft.value)),
    user_setback_side_right_m: feetToMetres(Number(form.user_setback_side_right_ft.value)),
    budget_min_lakhs: Number(form.budget_min_lakhs.value),
    budget_max_lakhs: Number(form.budget_max_lakhs.value),
    vastu_preference: getRadioValue("vastu_preference") || "off",
    additional_requirements: form.additional_requirements.value
      ? [form.additional_requirements.value]
      : [],
    user_email: form.user_email.value || null,
    user_phone: form.user_phone.value || null,
    resume_token: resumeToken,
    floors: collectFloors(),
  };
  return payload;
}

function collectFloors() {
  const floors = [];
  floorList.querySelectorAll("[data-floor-number]").forEach(panel => {
    const floorNumber = Number(panel.dataset.floorNumber);
    const useSelect = panel.querySelector(".floor-use-select");
    const floorUse = useSelect ? useSelect.value : "residential";
    const rooms = [];
    panel.querySelectorAll(".room-row").forEach(row => {
      const type = row.querySelector(".room-type-select").value;
      const count = Number(row.querySelector(".room-count-input").value);
      if (count > 0) {
        rooms.push({ room_type: type, count });
      }
    });
    floors.push({
      floor_number: floorNumber,
      floor_use: floorUse,
      rooms,
    });
  });
  return floors;
}

function getRadioValue(name) {
  const el = form.querySelector(`input[name="${name}"]:checked`);
  return el ? el.value : null;
}

// ─── Save & Resume (v0.9 server-backed, localStorage fallback) ──────────
function generateResumeToken() {
  // 12-byte token from crypto.getRandomValues → 24 hex chars (matches server)
  const arr = new Uint8Array(12);
  crypto.getRandomValues(arr);
  return Array.from(arr, b => b.toString(16).padStart(2, "0")).join("");
}

async function saveToServer(formState, existingToken) {
  const body = { ...formState };
  if (existingToken) body.existing_token = existingToken;
  const resp = await fetch("/api/brief/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error(`save failed: HTTP ${resp.status}`);
  return await resp.json();
}

async function resumeFromServer(token) {
  const resp = await fetch(`/api/brief/resume?token=${encodeURIComponent(token)}`);
  if (resp.status === 404) return null;  // not found or expired
  if (!resp.ok) throw new Error(`resume failed: HTTP ${resp.status}`);
  const data = await resp.json();
  return data.payload;
}

saveLaterBtn.addEventListener("click", async () => {
  const data = collectFormData();
  data.current_step = currentStep;
  data.saved_at = new Date().toISOString();

  saveLaterBtn.disabled = true;
  saveLaterBtn.textContent = "Saving...";

  try {
    // Try server first
    const result = await saveToServer(data, resumeToken);
    resumeToken = result.token;
    // Also cache in localStorage as a fast-path for same-browser resume
    try {
      localStorage.setItem(LOCALSTORAGE_KEY_PREFIX + resumeToken, JSON.stringify(data));
    } catch (_) {}
    const urlLine = `Your resume URL: ${result.resume_url}`;
    const expiryLine = `Valid for 30 days (expires ${result.expires_at_utc.split("T")[0]}).`;
    const warningLine = result.ephemeral_storage_warning
      ? `\n\n⚠ ${result.ephemeral_storage_warning}`
      : "";
    alert(
      `Saved on the server.\n\n${urlLine}\n\n${expiryLine}\n\n` +
      `Copy the URL to resume on any device.${warningLine}`
    );
  } catch (err) {
    // Fallback: localStorage only
    if (!resumeToken) resumeToken = generateResumeToken();
    try {
      localStorage.setItem(LOCALSTORAGE_KEY_PREFIX + resumeToken, JSON.stringify(data));
      alert(
        `Saved on this browser only (server save failed: ${err.message}).\n\n` +
        `Resume URL: ${window.location.pathname}?resume=${resumeToken}\n\n` +
        `⚠ Clear cookies or switch devices = progress lost.`
      );
    } catch (storageErr) {
      alert(`Could not save — both server and browser storage failed.\n\n${storageErr.message}`);
    }
  } finally {
    saveLaterBtn.disabled = false;
    saveLaterBtn.textContent = "Save & continue later";
  }
});

async function tryResume() {
  const url = new URL(window.location.href);
  const token = url.searchParams.get("resume");
  if (!token) return;

  // Prefer server (cross-device). Fall back to localStorage if server down.
  let data = null;
  try {
    data = await resumeFromServer(token);
  } catch (_) {
    // Server unreachable — check localStorage
  }
  if (!data) {
    const raw = localStorage.getItem(LOCALSTORAGE_KEY_PREFIX + token);
    if (raw) {
      try { data = JSON.parse(raw); } catch (_) { data = null; }
    }
  }
  if (!data) {
    alert("No saved brief found for that resume link (or the link expired).");
    return;
  }
  resumeToken = token;
  restoreForm(data);
  if (data.current_step) {
    currentStep = Math.max(1, Math.min(totalSteps, data.current_step));
    if (currentStep >= 2) rebuildFloorList();
    showStep(currentStep);
  }
}

function restoreForm(data) {
  // Saved data uses metres (because collectFormData() converts before saving).
  // We convert back to feet for display in the form.
  const metreToFeetFields = {
    "plot_width_m":            "plot_width_ft",
    "plot_depth_m":            "plot_depth_ft",
    "road_width_m":            "road_width_ft",
    "user_setback_front_m":    "user_setback_front_ft",
    "user_setback_rear_m":     "user_setback_rear_ft",
    "user_setback_side_left_m":  "user_setback_side_left_ft",
    "user_setback_side_right_m": "user_setback_side_right_ft",
  };
  for (const [mField, ftField] of Object.entries(metreToFeetFields)) {
    if (data[mField] != null && form[ftField]) {
      form[ftField].value = metresToFeet(Number(data[mField]));
    }
  }
  // Unitless fields (string/number, no conversion needed)
  const passThroughFields = [
    "plot_facing", "city", "plot_type",
    "budget_min_lakhs", "budget_max_lakhs",
    "user_email", "user_phone",
  ];
  for (const f of passThroughFields) {
    if (data[f] != null && form[f]) form[f].value = data[f];
  }
  if (data.corner_plot) {
    form.corner_plot.checked = true;
    secondRoadContainer.classList.remove("hidden");
    if (data.second_road_width_m != null && form.second_road_width_ft) {
      form.second_road_width_ft.value = metresToFeet(Number(data.second_road_width_m));
    }
  }
  if (data.plot_type === "semi_detached") {
    sharedSideContainer.classList.remove("hidden");
    if (data.shared_side) form.shared_side.value = data.shared_side;
  }
  if (data.vastu_preference) {
    const radio = form.querySelector(
      `input[name="vastu_preference"][value="${data.vastu_preference}"]`
    );
    if (radio) radio.checked = true;
  }
  if (data.additional_requirements && data.additional_requirements.length > 0) {
    form.additional_requirements.value = data.additional_requirements[0];
  }
  if (data.floors && Array.isArray(data.floors)) {
    if (floorCountSelect) {
      floorCountSelect.value = String(data.floors.length);
      rebuildFloorList();
      // Replay room compositions
      data.floors.forEach((f, floorIdx) => {
        const panel = floorList.querySelector(`[data-floor-number="${floorIdx}"]`);
        if (!panel) return;
        const useSelect = panel.querySelector(".floor-use-select");
        if (useSelect) useSelect.value = f.floor_use;
        const container = panel.querySelector(".rooms-container");
        if (container) {
          container.innerHTML = f.rooms.map((r, idx) =>
            renderRoomRow(floorIdx, idx, r)
          ).join("");
          container.querySelectorAll(".remove-room-btn").forEach(btn => {
            btn.addEventListener("click", (e) => e.target.closest(".room-row").remove());
          });
        }
      });
    }
  }
}

// ─── Submit handler ──────────────────────────────────────────────────────
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!validateStep(currentStep)) return;

  submitBtn.disabled = true;
  submitBtn.textContent = "Processing...";

  const payload = collectFormData();

  try {
    const resp = await fetch(API_BRIEF, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    renderResult(data, resp.ok);
  } catch (err) {
    renderResult(
      { ok: false, errors: [`Network error: ${err.message}`] },
      false,
    );
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Submit Brief";
  }
});

function renderResult(data, isOk) {
  resultPanel.classList.remove("hidden");
  if (!isOk || !data.ok) {
    const errorList = (data.errors || ["Unknown error"])
      .map(e => `<li>${escapeHtml(e)}</li>`)
      .join("");
    resultPanel.innerHTML = `
      <div class="rounded-lg border border-red-200 bg-red-50 p-6">
        <h3 class="text-lg font-semibold text-red-900 mb-2">Could not process your brief</h3>
        <ul class="text-sm text-red-800 list-disc pl-5">
          ${errorList}
        </ul>
      </div>
    `;
    resultPanel.scrollIntoView({ behavior: "smooth" });
    return;
  }

  const readyBadge = data.ready_for_downstream
    ? `<span class="inline-block px-3 py-1 text-xs rounded-full bg-green-100 text-green-800">READY</span>`
    : `<span class="inline-block px-3 py-1 text-xs rounded-full bg-amber-100 text-amber-800">REVIEW CONCERNS</span>`;

  const topGuidance = (data.top_guidance || []).map((m, i) => {
    const color = m.severity === "strong_concern" ? "red" :
                  m.severity === "concern" ? "amber" : "blue";
    return `
      <li class="p-3 rounded-md border border-${color}-200 bg-${color}-50 text-sm">
        <div class="font-semibold text-${color}-900 mb-1 uppercase text-xs">${m.severity}</div>
        <div class="text-${color}-900">${escapeHtml(m.text)}</div>
      </li>
    `;
  }).join("");

  const costLine = data.c7_preview_cost_lakhs != null
    ? `₹${data.c7_preview_cost_lakhs}L estimated via Component 7`
    : "Cost engine did not return an estimate";

  resultPanel.innerHTML = `
    <div class="rounded-lg border border-gray-200 bg-white p-6 space-y-6">
      <div class="flex items-center justify-between border-b border-gray-200 pb-4">
        <h3 class="text-lg font-semibold">Your brief is captured</h3>
        ${readyBadge}
      </div>
      <div class="space-y-3">
        <div class="text-sm text-gray-700">
          <strong>Plot:</strong> ${fmtFeet(data.brief_summary.plot_width_m)} × ${fmtFeet(data.brief_summary.plot_depth_m)}
          — ${fmtArea(data.brief_summary.plot_area_sqm)},
          ${data.brief_summary.plot_facing}-facing,
          ${data.brief_summary.city}, ${data.brief_summary.plot_type}
        </div>
        <div class="text-sm text-gray-700">
          <strong>Floors:</strong> ${data.brief_summary.floor_count}
          (G+${data.brief_summary.floor_count - 1}),
          ${data.brief_summary.total_built_area_sqft.toFixed(0)} sqft estimated built
        </div>
        <div class="text-sm text-gray-700">
          <strong>Budget:</strong> ₹${data.brief_summary.budget_min_lakhs}L–${data.brief_summary.budget_max_lakhs}L |
          <strong>${costLine}</strong>
        </div>
        <div class="text-sm text-gray-700">
          <strong>Compliance:</strong>
          ${data.brief_summary.compliance.is_setback_compliant ? "✓ Compliant" : "✗ Non-compliant"}
          per ${escapeHtml(data.brief_summary.compliance.source_authority)}
        </div>
      </div>
      ${data.top_guidance && data.top_guidance.length > 0 ? `
        <div>
          <h4 class="font-semibold mb-3">Top ${data.top_guidance.length} recommendations</h4>
          <ol class="space-y-2">${topGuidance}</ol>
        </div>
      ` : ""}
      <div>
        <button type="button" id="toggle-full-btn"
          class="text-sm text-blue-600 underline underline-offset-2">
          Show full report
        </button>
        <pre id="full-explain" class="hidden mt-4 p-4 rounded-md bg-gray-50 text-xs overflow-x-auto border border-gray-200 whitespace-pre-wrap">${escapeHtml(data.combined_rendered_explain || data.rendered_explain || "")}</pre>
      </div>
      <div class="text-xs text-gray-500 border-t border-gray-200 pt-3">
        Trace ID: <code>${data.trace_id}</code> |
        KB: ${Object.entries(data.kb_versions || {}).map(([k, v]) => `${k}=${v}`).join(", ")}
      </div>
    </div>
  `;
  const toggleBtn = document.getElementById("toggle-full-btn");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const full = document.getElementById("full-explain");
      full.classList.toggle("hidden");
      toggleBtn.textContent = full.classList.contains("hidden") ? "Show full report" : "Hide full report";
    });
  }
  resultPanel.scrollIntoView({ behavior: "smooth" });
}

function escapeHtml(s) {
  if (s == null) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ─── Init ────────────────────────────────────────────────────────────────
rebuildFloorList();
loadVastuPartialItems();
tryResume();
showStep(currentStep);
