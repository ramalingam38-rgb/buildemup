// design.js — BuildEase "enter your plot + floors, see your home" (S60 v2).
//
// 3-step wizard: Plot -> Floors & rooms (per-floor composition) -> Budget.
// On generate, runs the orchestrator once per residential floor (free-form
// input), then renders a compacted floor plan per floor. Room SIZES are
// engine-computed; the arrangement is a tidy shelf-pack preview (the
// engine's spatial placement is still being refined — B-C12).

(function () {
  "use strict";

  // ── Room + floor vocab (mirrors the old brief form) ──
  const ROOM_TYPES = [
    { value: "bedroom_master", label: "Master bedroom" },
    { value: "bedroom_regular", label: "Bedroom" },
    { value: "bathroom_attached", label: "Bathroom (attached)" },
    { value: "bathroom_common", label: "Bathroom (common)" },
    { value: "kitchen", label: "Kitchen" },
    { value: "living", label: "Living" },
    { value: "dining", label: "Dining" },
    { value: "pooja", label: "Pooja" },
    { value: "study", label: "Study" },
    { value: "store", label: "Store" },
    { value: "utility", label: "Utility" },
    { value: "balcony", label: "Balcony" },
  ];
  const FLOOR_USES = [
    { value: "residential", label: "Residential" },
    { value: "stilt_parking", label: "Stilt parking (no rooms)" },
    { value: "terrace", label: "Terrace (no rooms)" },
  ];
  const GROUND_DEFAULT = [
    { t: "living", c: 1 }, { t: "kitchen", c: 1 },
    { t: "bedroom_master", c: 1 }, { t: "bathroom_attached", c: 1 },
    { t: "bathroom_common", c: 1 }, { t: "pooja", c: 1 },
  ];
  const UPPER_DEFAULT = [
    { t: "bedroom_regular", c: 2 }, { t: "bathroom_attached", c: 1 },
    { t: "bathroom_common", c: 1 },
  ];

  const COLORS = {
    bedroom: "#bfdbfe", bathroom: "#fde68a", kitchen: "#fbcfe8",
    living: "#bbf7d0", pooja: "#fecaca", utility: "#e2e8f0",
    study: "#ddd6fe", staircase: "#cbd5e1", dining: "#fed7aa",
    store: "#e5e7eb", balcony: "#cffafe",
  };
  const colorFor = (c) => COLORS[(c || "").toLowerCase()] || "#e5e7eb";
  const pretty = (c) => {
    const s = (c || "").replace(/_/g, " ");
    return s.charAt(0).toUpperCase() + s.slice(1);
  };

  // ── Elements ──
  const form = document.getElementById("design-form");
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");
  const genBtn = document.getElementById("generate-btn");
  const statusText = document.getElementById("status-text");
  const floorCount = document.getElementById("floor-count");
  const floorList = document.getElementById("floor-list");
  const result = document.getElementById("result");

  let step = 1;
  const TOTAL = 3;

  // ── Wizard ──
  function showStep(n) {
    document.querySelectorAll(".step-panel").forEach((p) => {
      p.classList.toggle("hidden", Number(p.dataset.step) !== n);
    });
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
    if (step < TOTAL) { step += 1; showStep(step); window.scrollTo({ top: 0, behavior: "smooth" }); }
  });
  prevBtn.addEventListener("click", () => {
    if (step > 1) { step -= 1; showStep(step); window.scrollTo({ top: 0, behavior: "smooth" }); }
  });

  // ── Per-floor composition ──
  floorCount.addEventListener("change", rebuildFloors);

  function rebuildFloors() {
    const n = Number(floorCount.value);
    floorList.innerHTML = "";
    for (let i = 0; i < n; i += 1) {
      const isGround = i === 0;
      const label = isGround ? "Ground floor" : "Floor " + i;
      const defaults = isGround ? GROUND_DEFAULT : UPPER_DEFAULT;
      const panel = document.createElement("div");
      panel.className = "floor-panel";
      panel.dataset.floor = String(i);
      panel.innerHTML =
        '<div class="flex items-baseline justify-between mb-3">' +
        '<h4 class="font-semibold">' + label + "</h4>" +
        '<select class="floor-use text-sm" data-floor="' + i + '">' +
        FLOOR_USES.map((f) => '<option value="' + f.value + '">' + f.label + "</option>").join("") +
        "</select></div>" +
        '<div class="rooms" data-floor="' + i + '">' +
        defaults.map((r) => roomRowHtml(r.t, r.c)).join("") +
        "</div>" +
        '<button type="button" class="add-room mt-2 text-xs text-blue-600 underline" data-floor="' + i + '">+ Add room</button>';
      floorList.appendChild(panel);
    }
    wireFloorHandlers();
  }

  function roomRowHtml(type, count) {
    return (
      '<div class="room-row">' +
      '<select class="room-type flex-1">' +
      ROOM_TYPES.map((rt) => '<option value="' + rt.value + '"' + (rt.value === type ? " selected" : "") + ">" + rt.label + "</option>").join("") +
      "</select>" +
      '<input type="number" class="room-count" style="width:64px" min="1" max="10" value="' + count + '">' +
      '<button type="button" class="rm-room text-slate-400 hover:text-red-500" title="Remove">✕</button>' +
      "</div>"
    );
  }

  function wireFloorHandlers() {
    floorList.querySelectorAll(".add-room").forEach((b) => {
      b.onclick = () => {
        const cont = floorList.querySelector('.rooms[data-floor="' + b.dataset.floor + '"]');
        const tmp = document.createElement("div");
        tmp.innerHTML = roomRowHtml("bedroom_regular", 1);
        const row = tmp.firstElementChild;
        cont.appendChild(row);
        row.querySelector(".rm-room").onclick = () => row.remove();
      };
    });
    floorList.querySelectorAll(".rm-room").forEach((b) => {
      b.onclick = () => b.closest(".room-row").remove();
    });
    floorList.querySelectorAll(".floor-use").forEach((sel) => {
      sel.onchange = () => {
        const cont = floorList.querySelector('.rooms[data-floor="' + sel.dataset.floor + '"]');
        const btn = floorList.querySelector('.add-room[data-floor="' + sel.dataset.floor + '"]');
        const noRooms = sel.value !== "residential";
        cont.style.display = noRooms ? "none" : "";
        if (btn) btn.style.display = noRooms ? "none" : "";
      };
    });
  }

  // ── Collect floors → per-floor FloorRoomBrief shapes ──
  function collectFloors() {
    const floors = [];
    floorList.querySelectorAll(".floor-panel").forEach((panel) => {
      const idx = Number(panel.dataset.floor);
      const use = panel.querySelector(".floor-use").value;
      const rows = [];
      panel.querySelectorAll(".room-row").forEach((row) => {
        rows.push({
          type: row.querySelector(".room-type").value,
          count: Number(row.querySelector(".room-count").value) || 0,
        });
      });
      floors.push({ idx: idx, use: use, rows: rows });
    });
    return floors;
  }

  function floorToBrief(floor) {
    let bedrooms = 0, bathrooms = 0, hasKitchen = false, hasLiving = false,
      hasPooja = false, hasUtility = false, hasMaster = false;
    const other = [];
    floor.rows.forEach((r) => {
      const c = Math.max(0, r.count);
      switch (r.type) {
        case "bedroom_master": bedrooms += c; if (c > 0) hasMaster = true; break;
        case "bedroom_regular": bedrooms += c; break;
        case "bathroom_attached":
        case "bathroom_common": bathrooms += c; break;
        case "kitchen": if (c > 0) hasKitchen = true; break;
        case "living": if (c > 0) hasLiving = true; break;
        case "pooja": if (c > 0) hasPooja = true; break;
        case "utility": if (c > 0) hasUtility = true; break;
        default:
          for (let k = 0; k < c; k += 1) other.push(r.type);
      }
    });
    return {
      bedroom_count: bedrooms,
      bathroom_count: bathrooms,
      has_kitchen: hasKitchen,
      has_living: hasLiving,
      has_pooja: hasPooja,
      has_utility: hasUtility,
      has_master_bedroom: hasMaster,
      other_rooms: other,
      floor_label: floor.idx === 0 ? "ground" : "floor" + floor.idx,
    };
  }

  function plotPayload() {
    const fd = new FormData(form);
    return {
      width_ft: Number(fd.get("width_ft")),
      depth_ft: Number(fd.get("depth_ft")),
      facing: fd.get("facing"),
      city: fd.get("city"),
      road_width_ft: Number(fd.get("road_ft")),
      plot_type: fd.get("plot_type"),
    };
  }

  // ── Generate ──
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    genBtn.disabled = true;
    genBtn.textContent = "Generating…";
    statusText.textContent = "running the engine…";

    const plot = plotPayload();
    const vastu = new FormData(form).get("vastu") || "OFF";
    const floors = collectFloors();

    // Run residential floors through the pipeline (parallel).
    const runs = floors.map(async (floor) => {
      if (floor.use !== "residential" || floor.rows.length === 0) {
        return { floor: floor, kind: floor.use, preview: null, body: null };
      }
      const brief = floorToBrief(floor);
      try {
        const resp = await fetch("/api/orchestrate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ plot: plot, brief: brief, include_payloads: true, config: { vastu_tier: vastu } }),
        });
        const text = await resp.text();
        const body = text ? JSON.parse(text) : {};
        if (!resp.ok || body.ok === false) {
          return { floor: floor, kind: "error", errors: body.errors || ["rejected"], body: body };
        }
        return { floor: floor, kind: "residential", preview: body.layout_preview, body: body };
      } catch (err) {
        return { floor: floor, kind: "fetch_error", errors: [String(err)] };
      }
    });

    let results;
    try {
      results = await Promise.all(runs);
    } catch (err) {
      genBtn.disabled = false; genBtn.textContent = "Generate my design";
      statusText.textContent = "";
      result.classList.remove("hidden");
      result.innerHTML = errorCard(
        "Couldn't reach the engine. If this is the first run in a while the free " +
        "server may be waking up — wait ~30s and try again.",
      );
      return;
    }

    genBtn.disabled = false; genBtn.textContent = "Generate my design";
    statusText.textContent = "";
    render(plot, results);
  });

  // ── Render results ──
  function render(plot, results) {
    result.classList.remove("hidden");
    result.innerHTML = "";

    // Cost (from the first residential run's C7).
    const firstRes = results.find((r) => r.kind === "residential" && r.body);
    result.appendChild(costCard(firstRes ? firstRes.body : null));

    // One card per floor.
    results.forEach((r) => {
      result.appendChild(floorCard(plot, r));
    });

    // Technical phases (collapsible) from the first residential run.
    if (firstRes && firstRes.body) {
      result.appendChild(techCard(firstRes.body.phases || []));
    }
    result.scrollIntoView({ behavior: "smooth" });
  }

  function floorCard(plot, r) {
    const card = document.createElement("section");
    card.className = "bg-white rounded-xl shadow-sm border border-slate-200 p-6";
    const label = r.floor.idx === 0 ? "Ground floor" : "Floor " + r.floor.idx;

    if (r.kind === "stilt_parking" || r.kind === "terrace") {
      card.innerHTML =
        '<h2 class="text-lg font-semibold mb-1">' + label + "</h2>" +
        '<p class="text-sm text-slate-500">' +
        (r.kind === "stilt_parking" ? "Stilt parking — no rooms on this floor." : "Terrace — no rooms on this floor.") +
        "</p>";
      return card;
    }
    if (r.kind === "error" || r.kind === "fetch_error") {
      card.innerHTML =
        '<h2 class="text-lg font-semibold mb-1">' + label + "</h2>" +
        '<p class="text-sm text-red-700">Couldn\'t generate: ' + escapeHtml((r.errors || []).join("; ")) + "</p>";
      return card;
    }

    const lp = r.preview;
    if (!lp || !(lp.rooms || []).length) {
      card.innerHTML =
        '<h2 class="text-lg font-semibold mb-1">' + label + "</h2>" +
        '<div class="text-sm text-amber-700">' + explainNoPlan(r.body ? r.body.phases : []) + "</div>";
      return card;
    }

    // Compact-pack the engine-sized rooms for a clean view.
    const packed = packRooms(lp.rooms, (lp.envelope || {}).width_m || 10);
    const fillPct = lp.envelope && lp.envelope.width_m && lp.envelope.depth_m
      ? Math.round((100 * sumArea(lp.rooms)) / (lp.envelope.width_m * lp.envelope.depth_m))
      : null;

    card.innerHTML =
      '<div class="flex items-baseline justify-between mb-1">' +
      '<h2 class="text-lg font-semibold">' + label + "</h2>" +
      '<span class="text-xs text-slate-500">' + lp.rooms.length + " rooms · " +
      ((lp.envelope || {}).width_m || "?") + "m × " + ((lp.envelope || {}).depth_m || "?") + "m plot</span>" +
      "</div>" +
      '<div class="plan-svg mb-3">' + renderSvg(packed) + "</div>" +
      '<div class="mb-2">' + roomLegend(lp.rooms) + "</div>" +
      '<p class="text-xs text-slate-400 italic">Room sizes are engine-computed (NBC minimums). ' +
      "Positions are packed for a clean view — the engine's spatial layout with doors, " +
      "corridors and wall-sharing is the next stage." +
      (fillPct !== null ? " (Rooms use ~" + fillPct + "% of the buildable area.)" : "") +
      "</p>";
    return card;
  }

  function sumArea(rooms) {
    return rooms.reduce((s, r) => s + (r.width_m || 0) * (r.depth_m || 0), 0);
  }

  // Shelf-pack rooms left-to-right, wrapping rows, within a target width.
  // Guarantees no overlap; produces a tidy grid-like arrangement.
  function packRooms(rooms, envW) {
    const gap = 0.15; // 15cm visual gap between rooms
    const sorted = rooms.slice().sort((a, b) =>
      (b.depth_m || 0) - (a.depth_m || 0) || (b.width_m || 0) - (a.width_m || 0),
    );
    const placed = [];
    let x = 0, y = 0, rowDepth = 0, maxW = 0;
    sorted.forEach((r) => {
      const w = r.width_m || 0, d = r.depth_m || 0;
      if (x > 0 && x + w > envW + 0.001) {
        x = 0; y += rowDepth + gap; rowDepth = 0;
      }
      placed.push({ category: r.category, x_m: x, y_m: y, width_m: w, depth_m: d });
      x += w + gap;
      rowDepth = Math.max(rowDepth, d);
      maxW = Math.max(maxW, x - gap);
    });
    const totalH = y + rowDepth;
    return { rooms: placed, W: Math.max(envW, maxW), H: totalH };
  }

  function renderSvg(packed) {
    const rooms = packed.rooms;
    if (!rooms.length) return "";
    const W = packed.W || 1, H = packed.H || 1;
    const pad = 24, tW = 760;
    const tH = Math.max(220, Math.round((tW * H) / W));
    const scale = Math.min((tW - 2 * pad) / W, (tH - 2 * pad) / H);
    const px = (x) => pad + x * scale;
    const py = (y) => pad + y * scale; // top-down; packing already top-origin

    const out = [
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + tW + " " + tH + '" preserveAspectRatio="xMidYMid meet">',
      '<rect width="100%" height="100%" fill="#fafafa"/>',
    ];
    rooms.forEach((r) => {
      const x = px(r.x_m), y = py(r.y_m), w = r.width_m * scale, h = r.depth_m * scale;
      out.push('<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h +
        '" fill="' + colorFor(r.category) + '" stroke="#475569" stroke-width="1.2" rx="2"/>');
      const cx = x + w / 2, cy = y + h / 2;
      out.push('<text x="' + cx + '" y="' + (cy - 2) + '" font-size="11" font-weight="600" fill="#1e293b" text-anchor="middle">' + escapeHtml(pretty(r.category)) + "</text>");
      out.push('<text x="' + cx + '" y="' + (cy + 11) + '" font-size="9" fill="#64748b" text-anchor="middle">' + r.width_m.toFixed(1) + "×" + r.depth_m.toFixed(1) + "m</text>");
    });
    out.push("</svg>");
    return out.join("");
  }

  function roomLegend(rooms) {
    return rooms.slice().sort((a, b) => (a.category || "").localeCompare(b.category || ""))
      .map((r) =>
        '<span class="room-pill"><span class="room-swatch" style="background:' + colorFor(r.category) + '"></span>' +
        escapeHtml(pretty(r.category)) + ' <span class="text-slate-400">' +
        (r.width_m || 0).toFixed(1) + "×" + (r.depth_m || 0).toFixed(1) + "m</span></span>",
      ).join("");
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
      const found = c07.payload.foundation || {};
      html += '<p class="text-2xl font-semibold">' + lk(v) + "</p>" +
        '<p class="text-xs text-slate-500">Structural cost (foundation, frame, slab, walls)' +
        (found.type ? " · foundation: " + escapeHtml(String(found.type)) : "") + "</p>" +
        '<p class="text-xs text-slate-400 mt-2">Structural only — finishes, MEP, contractor margin extra. Directional, not a quote.</p>';
    } else {
      html += '<p class="text-slate-400 text-sm">Cost estimate unavailable for this input.</p>';
    }
    card.innerHTML = html;
    return card;
  }

  function techCard(phases) {
    const card = document.createElement("section");
    card.className = "bg-white rounded-xl shadow-sm border border-slate-200 p-6";
    card.innerHTML =
      '<button type="button" id="tech-toggle" class="text-sm font-medium text-slate-600 hover:text-slate-900">▸ Engine phases (technical)</button>' +
      '<div id="tech-body" class="hidden mt-4 grid grid-cols-2 md:grid-cols-3 gap-2"></div>';
    const body = card.querySelector("#tech-body");
    phases.forEach((p) => {
      const chip = document.createElement("div");
      chip.className = "phase-chip";
      chip.innerHTML = "<span>" + escapeHtml(p.phase_id) + '</span><span class="chip-badge chip-' + (p.status || "skipped") + '">' + escapeHtml(p.status || "?") + "</span>";
      body.appendChild(chip);
    });
    card.querySelector("#tech-toggle").onclick = (e) => {
      body.classList.toggle("hidden");
      e.target.textContent = (body.classList.contains("hidden") ? "▸" : "▾") + " Engine phases (technical)";
    };
    return card;
  }

  function errorCard(msg) {
    return '<section class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">' +
      '<p class="text-red-700 font-medium">' + escapeHtml(msg) + "</p></section>";
  }

  function escapeHtml(s) {
    if (s === null || s === undefined) return "";
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  // ── Init ──
  rebuildFloors();
  showStep(1);
})();
