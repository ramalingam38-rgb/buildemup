// design.js — BuildEase design page (S60 v3).
// 3-step wizard: Plot -> Floors&rooms (bedrooms with attached bath +
// common baths + other rooms) -> Setbacks (NBC hint) & budget.
// Renders a space-filling floor plan (rooms tile the plot, share walls,
// doors on shared edges). Room sizes/cost are engine-computed.

(function () {
  "use strict";

  const OTHER_ROOMS = [
    { key: "kitchen", label: "Kitchen" },
    { key: "living", label: "Living" },
    { key: "dining", label: "Dining" },
    { key: "pooja", label: "Pooja" },
    { key: "study", label: "Study" },
    { key: "utility", label: "Utility" },
    { key: "store", label: "Store" },
    { key: "balcony", label: "Balcony" },
  ];
  const FLOOR_USES = [
    { value: "residential", label: "Residential" },
    { value: "stilt_parking", label: "Stilt parking (no rooms)" },
    { value: "terrace", label: "Terrace (no rooms)" },
  ];
  const COLORS = {
    bedroom: "#bfdbfe", bathroom: "#fde68a", kitchen: "#fbcfe8",
    living: "#bbf7d0", pooja: "#fecaca", utility: "#e2e8f0",
    study: "#ddd6fe", staircase: "#cbd5e1", dining: "#fed7aa",
    store: "#e5e7eb", balcony: "#cffafe",
  };
  const colorFor = (c) => COLORS[(c || "").toLowerCase()] || "#e5e7eb";
  const pretty = (c) => { const s = (c || "").replace(/_/g, " "); return s.charAt(0).toUpperCase() + s.slice(1); };
  const FT = 3.28084;

  const form = document.getElementById("design-form");
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");
  const genBtn = document.getElementById("generate-btn");
  const statusText = document.getElementById("status-text");
  const floorCount = document.getElementById("floor-count");
  const floorList = document.getElementById("floor-list");
  const result = document.getElementById("result");
  const nbcHint = document.getElementById("nbc-hint");
  const nbcHintText = document.getElementById("nbc-hint-text");

  let step = 1;
  const TOTAL = 3;

  function showStep(n) {
    document.querySelectorAll(".step-panel").forEach((p) => p.classList.toggle("hidden", Number(p.dataset.step) !== n));
    document.querySelectorAll(".step-ind").forEach((ind) => {
      const s = Number(ind.dataset.step);
      ind.classList.toggle("active", s === n);
      ind.classList.toggle("done", s < n);
    });
    prevBtn.classList.toggle("hidden", n === 1);
    nextBtn.classList.toggle("hidden", n === TOTAL);
    genBtn.classList.toggle("hidden", n !== TOTAL);
  }
  nextBtn.addEventListener("click", () => {
    if (step === 1 && !floorList.children.length) rebuildFloors();
    if (step < TOTAL) { step += 1; showStep(step); if (step === 3) refreshSetbackHint(); window.scrollTo({ top: 0, behavior: "smooth" }); }
  });
  prevBtn.addEventListener("click", () => { if (step > 1) { step -= 1; showStep(step); window.scrollTo({ top: 0, behavior: "smooth" }); } });

  // ── Per-floor composition ──
  floorCount.addEventListener("change", rebuildFloors);

  function rebuildFloors() {
    const n = Number(floorCount.value);
    floorList.innerHTML = "";
    for (let i = 0; i < n; i += 1) {
      const isGround = i === 0;
      const label = isGround ? "Ground floor" : "Floor " + i;
      const panel = document.createElement("div");
      panel.className = "floor-panel";
      panel.dataset.floor = String(i);
      // defaults: ground -> master+1 regular, kitchen+living+pooja, 1 common bath
      //           upper -> 2 regular bedrooms, 1 common bath
      const otherChecks = OTHER_ROOMS.map((o) => {
        const on = isGround && (o.key === "kitchen" || o.key === "living" || o.key === "pooja");
        return '<label class="inline-flex items-center gap-1 text-sm mr-3 mb-1">' +
          '<input type="checkbox" class="other-room" data-key="' + o.key + '"' + (on ? " checked" : "") + "> " + o.label + "</label>";
      }).join("");
      panel.innerHTML =
        '<div class="flex items-baseline justify-between mb-3">' +
        '<h4 class="font-semibold">' + label + "</h4>" +
        '<select class="floor-use text-sm">' + FLOOR_USES.map((f) => '<option value="' + f.value + '">' + f.label + "</option>").join("") + "</select></div>" +
        '<div class="floor-body">' +
        '<div class="mb-3"><div class="text-sm font-medium text-slate-700 mb-1">Bedrooms</div>' +
        '<div class="bedrooms space-y-2"></div>' +
        '<button type="button" class="add-bed mt-2 text-xs text-blue-600 underline">+ Add bedroom</button></div>' +
        '<label class="block mb-3 max-w-[200px]"><span class="text-sm font-medium text-slate-700">Common bathrooms</span>' +
        '<input type="number" class="common-bath fld" min="0" max="6" value="1"></label>' +
        '<div class="text-sm font-medium text-slate-700 mb-1">Other rooms</div>' +
        '<div class="flex flex-wrap">' + otherChecks + "</div>" +
        "</div>";
      floorList.appendChild(panel);
      // seed bedrooms
      const beds = panel.querySelector(".bedrooms");
      if (isGround) {
        beds.appendChild(bedRow("master", true));
        beds.appendChild(bedRow("regular", false));
      } else {
        beds.appendChild(bedRow("regular", true));
        beds.appendChild(bedRow("regular", false));
      }
    }
    wireFloors();
  }

  function bedRow(type, ensuite) {
    const div = document.createElement("div");
    div.className = "bed-row room-row";
    div.innerHTML =
      '<select class="bed-type"><option value="master"' + (type === "master" ? " selected" : "") + ">Master bedroom</option>" +
      '<option value="regular"' + (type === "regular" ? " selected" : "") + ">Bedroom</option></select>" +
      '<label class="inline-flex items-center gap-1 text-sm"><input type="checkbox" class="bed-ensuite"' + (ensuite ? " checked" : "") + "> attached bathroom</label>" +
      '<button type="button" class="rm-bed text-slate-400 hover:text-red-500" title="Remove">✕</button>';
    div.querySelector(".rm-bed").onclick = () => div.remove();
    return div;
  }

  function wireFloors() {
    floorList.querySelectorAll(".add-bed").forEach((b) => {
      b.onclick = () => b.closest(".floor-panel").querySelector(".bedrooms").appendChild(bedRow("regular", false));
    });
    floorList.querySelectorAll(".floor-use").forEach((sel) => {
      sel.onchange = () => {
        const bodyEl = sel.closest(".floor-panel").querySelector(".floor-body");
        bodyEl.style.display = sel.value === "residential" ? "" : "none";
      };
    });
  }

  // ── NBC setback hint ──
  async function refreshSetbackHint() {
    const fd = new FormData(form);
    const payload = {
      city: fd.get("city"),
      plot_width_m: Number(fd.get("width_ft")) / FT,
      plot_depth_m: Number(fd.get("depth_ft")) / FT,
      plot_facing: fd.get("facing"),
      plot_type: fd.get("plot_type"),
      road_width_m: Number(fd.get("road_ft")) / FT,
    };
    try {
      const r = await fetch("/api/setback/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const d = await r.json();
      if (!r.ok || !d.ok) { nbcHint.classList.add("hidden"); return; }
      nbcHintText.textContent = "Front " + d.front_ft + " ft, Rear " + d.rear_ft + " ft, Left " + d.side_left_ft + " ft, Right " + d.side_right_ft + " ft (per " + d.source_authority + ").";
      nbcHint.classList.remove("hidden");
      // Pre-fill the user's setback fields with the legal minimum.
      form.sb_front.value = d.front_ft; form.sb_rear.value = d.rear_ft;
      form.sb_left.value = d.side_left_ft; form.sb_right.value = d.side_right_ft;
    } catch (_) { nbcHint.classList.add("hidden"); }
  }

  // ── Collect + map ──
  function plotPayload() {
    const fd = new FormData(form);
    return {
      width_ft: Number(fd.get("width_ft")), depth_ft: Number(fd.get("depth_ft")),
      facing: fd.get("facing"), city: fd.get("city"),
      road_width_ft: Number(fd.get("road_ft")), plot_type: fd.get("plot_type"),
    };
  }

  function collectFloors() {
    const floors = [];
    floorList.querySelectorAll(".floor-panel").forEach((panel) => {
      const idx = Number(panel.dataset.floor);
      const use = panel.querySelector(".floor-use").value;
      const beds = [];
      panel.querySelectorAll(".bed-row").forEach((row) => {
        beds.push({ type: row.querySelector(".bed-type").value, ensuite: row.querySelector(".bed-ensuite").checked });
      });
      const commonBath = Number(panel.querySelector(".common-bath").value) || 0;
      const other = {};
      panel.querySelectorAll(".other-room").forEach((c) => { other[c.dataset.key] = c.checked; });
      floors.push({ idx, use, beds, commonBath, other });
    });
    return floors;
  }

  function floorToBrief(floor) {
    const bedrooms = floor.beds.length;
    const ensuite = floor.beds.filter((b) => b.ensuite).length;
    const hasMaster = floor.beds.some((b) => b.type === "master");
    const o = floor.other || {};
    const otherRooms = [];
    ["dining", "study", "store", "balcony"].forEach((k) => { if (o[k]) otherRooms.push(k); });
    return {
      bedroom_count: bedrooms,
      bathroom_count: ensuite + floor.commonBath,
      has_kitchen: !!o.kitchen, has_living: !!o.living,
      has_pooja: !!o.pooja, has_utility: !!o.utility,
      has_master_bedroom: hasMaster, other_rooms: otherRooms,
      floor_label: floor.idx === 0 ? "ground" : "floor" + floor.idx,
    };
  }

  // ── Generate ──
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    genBtn.disabled = true; genBtn.textContent = "Generating…"; statusText.textContent = "running the engine…";
    const plot = plotPayload();
    const vastu = new FormData(form).get("vastu") || "OFF";
    const floors = collectFloors();
    const runs = floors.map(async (floor) => {
      if (floor.use !== "residential") return { floor, kind: floor.use };
      const brief = floorToBrief(floor);
      try {
        const resp = await fetch("/api/orchestrate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ plot, brief, include_payloads: true, config: { vastu_tier: vastu } }) });
        const text = await resp.text();
        const body = text ? JSON.parse(text) : {};
        if (!resp.ok || body.ok === false) return { floor, kind: "error", errors: body.errors || ["rejected"], body };
        return { floor, kind: "residential", preview: body.layout_preview, body };
      } catch (err) { return { floor, kind: "fetch_error", errors: [String(err)] }; }
    });
    let results;
    try { results = await Promise.all(runs); }
    catch (err) {
      genBtn.disabled = false; genBtn.textContent = "Generate my design"; statusText.textContent = "";
      result.classList.remove("hidden");
      result.innerHTML = errorCard("Couldn't reach the engine. The free server may be waking up — wait ~30s and retry.");
      return;
    }
    genBtn.disabled = false; genBtn.textContent = "Generate my design"; statusText.textContent = "";
    render(plot, results);
  });

  function render(plot, results) {
    result.classList.remove("hidden");
    result.innerHTML = "";
    const firstRes = results.find((r) => r.kind === "residential" && r.body);
    result.appendChild(costCard(firstRes ? firstRes.body : null));
    results.forEach((r) => result.appendChild(floorCard(r)));
    if (firstRes && firstRes.body) result.appendChild(techCard(firstRes.body.phases || []));
    result.scrollIntoView({ behavior: "smooth" });
  }

  function floorCard(r) {
    const card = document.createElement("section");
    card.className = "bg-white rounded-xl shadow-sm border border-slate-200 p-6";
    const label = r.floor.idx === 0 ? "Ground floor" : "Floor " + r.floor.idx;
    if (r.kind === "stilt_parking" || r.kind === "terrace") {
      card.innerHTML = '<h2 class="text-lg font-semibold mb-1">' + label + "</h2><p class=\"text-sm text-slate-500\">" +
        (r.kind === "stilt_parking" ? "Stilt parking — no rooms." : "Terrace — no rooms.") + "</p>";
      return card;
    }
    if (r.kind === "error" || r.kind === "fetch_error") {
      card.innerHTML = '<h2 class="text-lg font-semibold mb-1">' + label + "</h2><p class=\"text-sm text-red-700\">Couldn't generate: " + escapeHtml((r.errors || []).join("; ")) + "</p>";
      return card;
    }
    const lp = r.preview;
    if (!lp || !(lp.rooms || []).length) {
      card.innerHTML = '<h2 class="text-lg font-semibold mb-1">' + label + '</h2><div class="text-sm text-amber-700">' + explainNoPlan(r.body ? r.body.phases : []) + "</div>";
      return card;
    }
    const env = lp.envelope || {};
    card.innerHTML =
      '<div class="flex items-baseline justify-between mb-1">' +
      '<h2 class="text-lg font-semibold">' + label + "</h2>" +
      '<span class="text-xs text-slate-500">' + lp.rooms.length + " rooms · " + (env.width_m || "?") + "m × " + (env.depth_m || "?") + "m</span></div>" +
      '<div class="plan-svg mb-3">' + renderPlan(lp) + "</div>" +
      '<div class="mb-2">' + roomLegend(lp.rooms) + "</div>" +
      '<p class="text-xs text-slate-400 italic">Illustrative layout — rooms are sized by the engine (NBC minimums, shown in the legend) and arranged to fill the plot. Exact wall positions, corridors and door swings come in the next engine stage.</p>';
    return card;
  }

  // ── Space-filling floor plan (recursive slicing) ──
  function renderPlan(lp) {
    const env = lp.envelope || {};
    const W = env.width_m || 10, H = env.depth_m || 10;
    // Build rooms with engine area; slice-tile the WxH envelope.
    const rooms = lp.rooms.map((r) => ({ category: r.category, area: Math.max(0.1, (r.width_m || 1) * (r.depth_m || 1)) }));
    const tiled = sliceLayout(rooms, 0, 0, W, H);

    const pad = 26, tW = 760;
    const tH = Math.max(240, Math.round((tW * H) / W));
    const scale = Math.min((tW - 2 * pad) / W, (tH - 2 * pad) / H);
    const px = (x) => pad + x * scale;
    const py = (y) => pad + y * scale;

    const out = [
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + tW + " " + tH + '" preserveAspectRatio="xMidYMid meet">',
      '<rect width="100%" height="100%" fill="#f8fafc"/>',
    ];
    // Rooms
    tiled.forEach((t) => {
      out.push('<rect x="' + px(t.x) + '" y="' + py(t.y) + '" width="' + t.w * scale + '" height="' + t.h * scale +
        '" fill="' + colorFor(t.category) + '" stroke="#334155" stroke-width="2"/>');
      const cx = px(t.x) + (t.w * scale) / 2, cy = py(t.y) + (t.h * scale) / 2;
      out.push('<text x="' + cx + '" y="' + (cy - 2) + '" font-size="11" font-weight="600" fill="#1e293b" text-anchor="middle">' + escapeHtml(pretty(t.category)) + "</text>");
      out.push('<text x="' + cx + '" y="' + (cy + 11) + '" font-size="9" fill="#475569" text-anchor="middle">' + t.w.toFixed(1) + "×" + t.h.toFixed(1) + "m</text>");
    });
    // Internal doors: white gaps on shared edges between adjacent rooms.
    const DW = 0.85; // door width m
    for (let i = 0; i < tiled.length; i += 1) {
      for (let j = i + 1; j < tiled.length; j += 1) {
        const a = tiled[i], b = tiled[j];
        // vertical shared edge
        if (Math.abs((a.x + a.w) - b.x) < 0.02 || Math.abs((b.x + b.w) - a.x) < 0.02) {
          const ex = Math.abs((a.x + a.w) - b.x) < 0.02 ? a.x + a.w : b.x;
          const lo = Math.max(a.y, b.y), hi = Math.min(a.y + a.h, b.y + b.h);
          if (hi - lo >= DW + 0.1) {
            const mid = (lo + hi) / 2;
            out.push('<rect x="' + (px(ex) - 2) + '" y="' + py(mid - DW / 2) + '" width="4" height="' + DW * scale + '" fill="#f8fafc"/>');
          }
        }
        // horizontal shared edge
        if (Math.abs((a.y + a.h) - b.y) < 0.02 || Math.abs((b.y + b.h) - a.y) < 0.02) {
          const ey = Math.abs((a.y + a.h) - b.y) < 0.02 ? a.y + a.h : b.y;
          const lo = Math.max(a.x, b.x), hi = Math.min(a.x + a.w, b.x + b.w);
          if (hi - lo >= DW + 0.1) {
            const mid = (lo + hi) / 2;
            out.push('<rect x="' + px(mid - DW / 2) + '" y="' + (py(ey) - 2) + '" width="' + DW * scale + '" height="4" fill="#f8fafc"/>');
          }
        }
      }
    }
    // Outer wall (thick)
    out.push('<rect x="' + px(0) + '" y="' + py(0) + '" width="' + W * scale + '" height="' + H * scale + '" fill="none" stroke="#0f172a" stroke-width="4"/>');
    // North arrow
    out.push('<g transform="translate(' + (tW - 24) + ',24)"><line x1="0" y1="8" x2="0" y2="-8" stroke="#334155" stroke-width="1.5"/><path d="M0,-10 L-3,-4 L3,-4 Z" fill="#334155"/><text x="0" y="20" font-size="9" fill="#334155" text-anchor="middle">N</text></g>');
    out.push("</svg>");
    return out.join("");
  }

  // Recursive slicing: tile [x,y,w,h] with rooms proportional to area.
  function sliceLayout(rooms, x, y, w, h) {
    if (rooms.length === 0) return [];
    if (rooms.length === 1) return [{ category: rooms[0].category, x, y, w, h }];
    const sorted = rooms.slice().sort((a, b) => b.area - a.area);
    const total = sorted.reduce((s, r) => s + r.area, 0);
    let acc = 0, splitIdx = 0;
    for (let i = 0; i < sorted.length; i += 1) { acc += sorted[i].area; if (acc >= total / 2) { splitIdx = i + 1; break; } }
    splitIdx = Math.max(1, Math.min(sorted.length - 1, splitIdx));
    const gA = sorted.slice(0, splitIdx), gB = sorted.slice(splitIdx);
    const aA = gA.reduce((s, r) => s + r.area, 0);
    if (w >= h) {
      const wA = w * (aA / total);
      return sliceLayout(gA, x, y, wA, h).concat(sliceLayout(gB, x + wA, y, w - wA, h));
    }
    const hA = h * (aA / total);
    return sliceLayout(gA, x, y, w, hA).concat(sliceLayout(gB, x, y + hA, w, h - hA));
  }

  function roomLegend(rooms) {
    return rooms.slice().sort((a, b) => (a.category || "").localeCompare(b.category || ""))
      .map((r) => '<span class="room-pill"><span class="room-swatch" style="background:' + colorFor(r.category) + '"></span>' +
        escapeHtml(pretty(r.category)) + ' <span class="text-slate-400">' + (r.width_m || 0).toFixed(1) + "×" + (r.depth_m || 0).toFixed(1) + "m</span></span>").join("");
  }

  function explainNoPlan(phases) {
    const friendly = {
      c06_orientation: "Orientation step doesn't support this facing yet — try N/E/S/W.",
      c08_corridor: "Corridor planner couldn't route hallways — try a larger plot or fewer rooms.",
      c09_room_sizer: "Your rooms don't fit this plot. ",
      c10_wet_zones: "Plumbing planner couldn't fit bathroom+kitchen on a plot this small.",
    };
    for (const p of phases || []) {
      if (p.status === "stub" || p.status === "error") {
        let m = friendly[p.phase_id] || ("Stopped at " + p.phase_id + ".");
        if (p.phase_id === "c09_room_sizer" && p.stub_reason) m += escapeHtml(p.stub_reason);
        return "<strong>Couldn't place rooms.</strong> " + m;
      }
    }
    return "No floor plan available for this input.";
  }

  function costCard(body) {
    const card = document.createElement("section");
    card.className = "bg-white rounded-xl shadow-sm border border-slate-200 p-6";
    let html = '<h2 class="text-lg font-semibold mb-2">Cost estimate</h2>';
    const c07 = body ? (body.phases || []).find((p) => p.phase_id === "c07_structural_grid") : null;
    const cost = c07 && c07.payload ? c07.payload.cost : null;
    const v = cost ? (cost.exact_value !== undefined ? cost.exact_value : cost.found_value) : undefined;
    if (v !== undefined) {
      const lk = (n) => "₹" + (n / 100000).toFixed(1) + "L";
      const f = c07.payload.foundation || {};
      html += '<p class="text-2xl font-semibold">' + lk(v) + "</p><p class=\"text-xs text-slate-500\">Structural cost (foundation, frame, slab, walls)" +
        (f.type ? " · foundation: " + escapeHtml(String(f.type)) : "") + "</p><p class=\"text-xs text-slate-400 mt-2\">Structural only — finishes, MEP, contractor margin extra. Directional, not a quote.</p>";
    } else { html += '<p class="text-slate-400 text-sm">Cost estimate unavailable for this input.</p>'; }
    card.innerHTML = html;
    return card;
  }

  function techCard(phases) {
    const card = document.createElement("section");
    card.className = "bg-white rounded-xl shadow-sm border border-slate-200 p-6";
    card.innerHTML = '<button type="button" id="tech-toggle" class="text-sm font-medium text-slate-600 hover:text-slate-900">▸ Engine phases (technical)</button><div id="tech-body" class="hidden mt-4 grid grid-cols-2 md:grid-cols-3 gap-2"></div>';
    const body = card.querySelector("#tech-body");
    phases.forEach((p) => {
      const chip = document.createElement("div");
      chip.className = "phase-chip";
      chip.innerHTML = "<span>" + escapeHtml(p.phase_id) + '</span><span class="chip-badge chip-' + (p.status || "skipped") + '">' + escapeHtml(p.status || "?") + "</span>";
      body.appendChild(chip);
    });
    card.querySelector("#tech-toggle").onclick = (e) => { body.classList.toggle("hidden"); e.target.textContent = (body.classList.contains("hidden") ? "▸" : "▾") + " Engine phases (technical)"; };
    return card;
  }

  function errorCard(msg) { return '<section class="bg-white rounded-xl shadow-sm border border-slate-200 p-6"><p class="text-red-700 font-medium">' + escapeHtml(msg) + "</p></section>"; }

  function escapeHtml(s) {
    if (s === null || s === undefined) return "";
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  rebuildFloors();
  showStep(1);
})();
