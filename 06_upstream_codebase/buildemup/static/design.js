// design.js — BuildEase "enter your own plot, see your home" page (S60).
//
// Collects the user's plot + room wishes, POSTs free-form to
// /api/orchestrate, and renders the resulting floor plan (from
// layout_preview), the room list, the C7 cost estimate, and a
// collapsible engine-phase panel.

(function () {
  "use strict";

  const form = document.getElementById("design-form");
  const btn = document.getElementById("generate-btn");
  const statusText = document.getElementById("status-text");
  const result = document.getElementById("result");
  const planStatus = document.getElementById("plan-status");
  const planMeta = document.getElementById("plan-meta");
  const planSvg = document.getElementById("plan-svg");
  const planNote = document.getElementById("plan-note");
  const roomList = document.getElementById("room-list");
  const costSummary = document.getElementById("cost-summary");
  const phaseChips = document.getElementById("phase-chips");

  const COLORS = {
    bedroom: "#bfdbfe",
    bathroom: "#fde68a",
    kitchen: "#fbcfe8",
    living: "#bbf7d0",
    pooja: "#fecaca",
    utility: "#e2e8f0",
    study: "#ddd6fe",
    staircase: "#cbd5e1",
    dining: "#fed7aa",
  };
  const colorFor = (c) => COLORS[(c || "").toLowerCase()] || "#e5e7eb";
  const pretty = (c) => {
    const s = (c || "").replace(/_/g, " ");
    return s.charAt(0).toUpperCase() + s.slice(1);
  };

  // Tech-details toggle.
  document.getElementById("tech-toggle").addEventListener("click", (e) => {
    const body = document.getElementById("tech-body");
    body.classList.toggle("hidden");
    e.target.textContent =
      (body.classList.contains("hidden") ? "▸" : "▾") +
      " Technical details (engine phases)";
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    btn.disabled = true;
    btn.textContent = "Generating…";
    statusText.textContent = "running the engine — a few seconds…";

    const fd = new FormData(form);
    const payload = {
      plot: {
        width_ft: Number(fd.get("width_ft")),
        depth_ft: Number(fd.get("depth_ft")),
        facing: fd.get("facing"),
        city: fd.get("city"),
        road_width_ft: 30,
      },
      brief: {
        bedroom_count: Number(fd.get("bedroom_count")),
        bathroom_count: Number(fd.get("bathroom_count")),
        has_kitchen: fd.get("has_kitchen") === "on",
        has_living: fd.get("has_living") === "on",
        has_pooja: fd.get("has_pooja") === "on",
        has_utility: fd.get("has_utility") === "on",
      },
      include_payloads: true,
      config: { vastu_tier: "OFF" },
    };

    let resp, body;
    try {
      resp = await fetch("/api/orchestrate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const text = await resp.text();
      body = text ? JSON.parse(text) : {};
    } catch (err) {
      finishBtn();
      statusText.textContent = "";
      showError(
        "Couldn't reach the engine. If this is the first run after a while, " +
          "the free server may still be waking up — wait ~30 seconds and try again.",
      );
      return;
    }
    finishBtn();
    statusText.textContent = "";

    if (!resp.ok || body.ok === false) {
      const errs = (body.errors || ["unknown error"]).join("; ");
      showError("The engine rejected the inputs: " + errs);
      return;
    }
    render(payload, body);
  });

  function finishBtn() {
    btn.disabled = false;
    btn.textContent = "Generate my design";
  }

  function showError(msg) {
    result.classList.remove("hidden");
    planMeta.textContent = "";
    planNote.textContent = "";
    planSvg.innerHTML = "";
    roomList.innerHTML = "";
    costSummary.innerHTML = "";
    phaseChips.innerHTML = "";
    planStatus.innerHTML =
      '<span class="text-red-700 font-medium">' + escapeHtml(msg) + "</span>";
  }

  function render(payload, body) {
    result.classList.remove("hidden");
    const phases = body.phases || [];
    const lp = body.layout_preview;

    // ── Phase chips (technical) ──
    phaseChips.innerHTML = "";
    phases.forEach((p) => {
      const chip = document.createElement("div");
      chip.className = "phase-chip";
      chip.innerHTML =
        "<span>" +
        escapeHtml(p.phase_id) +
        '</span><span class="chip-badge chip-' +
        (p.status || "skipped") +
        '">' +
        escapeHtml(p.status || "?") +
        "</span>";
      phaseChips.appendChild(chip);
    });

    // ── Floor plan ──
    if (lp && (lp.rooms || []).length > 0) {
      const env = lp.envelope || {};
      planMeta.textContent =
        (env.width_m || "?") + "m × " + (env.depth_m || "?") + "m buildable area";
      planStatus.innerHTML =
        '<span class="text-green-700 font-medium">' +
        lp.rooms.length +
        " rooms placed.</span> Here's how they fit on your plot:";
      planSvg.innerHTML = renderSvg(lp);
      planNote.textContent =
        "This shows where each room sits and its size — generated by the layout " +
        "engine from your inputs. Doors, wall thicknesses and the final " +
        "dimensioned drawing come in the next engine stage.";
      renderRoomList(lp.rooms);
    } else {
      // No layout — explain why, honestly, using the phase that stopped.
      planSvg.innerHTML = "";
      planMeta.textContent = "";
      planNote.textContent = "";
      roomList.innerHTML =
        '<p class="text-slate-500">No rooms placed for this combination.</p>';
      planStatus.innerHTML = explainNoPlan(phases);
    }

    // ── Cost estimate (from C7) ──
    renderCost(phases);
  }

  function renderRoomList(rooms) {
    // Group by category with counts.
    const sorted = rooms.slice().sort((a, b) =>
      (a.category || "").localeCompare(b.category || ""),
    );
    roomList.innerHTML = sorted
      .map(
        (r) =>
          '<span class="room-pill">' +
          '<span class="room-swatch" style="background:' +
          colorFor(r.category) +
          '"></span>' +
          escapeHtml(pretty(r.category)) +
          ' <span class="text-slate-400">' +
          (r.width_m || 0).toFixed(1) +
          "×" +
          (r.depth_m || 0).toFixed(1) +
          "m</span></span>",
      )
      .join("");
  }

  function explainNoPlan(phases) {
    // Find the first phase that stopped the chain (stub or error).
    const order = phases.map((p) => p.phase_id);
    const friendly = {
      c06_orientation:
        "The orientation step doesn't support this plot facing yet " +
        "(diagonal facings like NE/SE are coming soon). Try North, East, " +
        "South or West.",
      c08_corridor:
        "The corridor planner couldn't route hallways for this plot + room " +
        "mix. Try a slightly larger plot or fewer rooms.",
      c09_room_sizer:
        "Your rooms don't fit this plot. ",
      c10_wet_zones:
        "The plumbing planner couldn't fit the bathroom + kitchen on a plot " +
        "this small. Try a larger plot or fewer wet rooms.",
    };
    for (const pid of order) {
      const p = phases.find((x) => x.phase_id === pid);
      if (!p) continue;
      if (p.status === "stub" || p.status === "error") {
        let msg = friendly[pid] || "";
        // For room-sizer, append the precise deficit if present.
        if (pid === "c09_room_sizer" && p.stub_reason) {
          msg += escapeHtml(p.stub_reason);
        } else if (!msg) {
          msg =
            "The engine stopped at " +
            escapeHtml(pid) +
            ": " +
            escapeHtml(p.stub_reason || p.error_message || "(no detail)");
        }
        return (
          '<span class="text-amber-700 font-medium">Couldn\'t place rooms.</span> ' +
          msg
        );
      }
    }
    return '<span class="text-slate-500">No floor plan available for this input.</span>';
  }

  function renderCost(phases) {
    const c07 = phases.find((p) => p.phase_id === "c07_structural_grid");
    if (!c07 || c07.status !== "ok" || !c07.payload) {
      costSummary.innerHTML =
        '<p class="text-slate-400">Cost estimate unavailable for this input.</p>';
      return;
    }
    const cost = (c07.payload && c07.payload.cost) || {};
    const exact = cost.exact_value;
    const found = cost.found_value;
    const foundation = (c07.payload && c07.payload.foundation) || {};
    if (exact === undefined && found === undefined) {
      costSummary.innerHTML =
        '<p class="text-slate-400">Cost estimate unavailable for this input.</p>';
      return;
    }
    const v = exact !== undefined ? exact : found;
    const lakhs = (n) => "₹" + (n / 100000).toFixed(1) + "L";
    costSummary.innerHTML =
      '<p class="mb-2"><span class="text-slate-500">Structural cost (foundation, ' +
      "frame, slab, walls):</span><br><span class=\"text-2xl font-semibold\">" +
      lakhs(v) +
      "</span></p>" +
      (foundation.type
        ? '<p class="text-xs text-slate-500">Foundation: ' +
          escapeHtml(String(foundation.type)) +
          "</p>"
        : "") +
      '<p class="text-xs text-slate-400 mt-2">Structural only — finishes, MEP, ' +
      "and contractor margin are extra. Directional estimate, not a quote.</p>";
  }

  // ── SVG floor-plan renderer ──
  function renderSvg(lp) {
    const rooms = lp.rooms || [];
    const cols = lp.columns || [];
    const env = lp.envelope || {};
    if (rooms.length === 0) return "";

    let W = env.width_m || 0;
    let H = env.depth_m || 0;
    rooms.forEach((r) => {
      W = Math.max(W, (r.x_m || 0) + (r.width_m || 0));
      H = Math.max(H, (r.y_m || 0) + (r.depth_m || 0));
    });
    W = W || 1;
    H = H || 1;

    const pad = 28;
    const tW = 720;
    const tH = Math.round((tW * H) / W) + 0; // keep aspect
    const innerW = tW - 2 * pad;
    const innerH = tH - 2 * pad;
    const scale = Math.min(innerW / W, innerH / H);
    const px = (x) => pad + x * scale;
    const py = (y) => tH - pad - y * scale; // flip Y, north up

    const out = [
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' +
        tW +
        " " +
        tH +
        '" preserveAspectRatio="xMidYMid meet">',
      '<rect width="100%" height="100%" fill="#fafafa"/>',
    ];

    // Envelope outline.
    out.push(
      '<rect x="' +
        px(0) +
        '" y="' +
        py(H) +
        '" width="' +
        W * scale +
        '" height="' +
        H * scale +
        '" fill="none" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="5 4"/>',
    );

    // Rooms.
    rooms.forEach((r) => {
      const x = px(r.x_m || 0);
      const y = py((r.y_m || 0) + (r.depth_m || 0));
      const w = (r.width_m || 0) * scale;
      const h = (r.depth_m || 0) * scale;
      out.push(
        '<rect x="' +
          x +
          '" y="' +
          y +
          '" width="' +
          w +
          '" height="' +
          h +
          '" fill="' +
          colorFor(r.category) +
          '" stroke="#475569" stroke-width="1.2" rx="2"/>',
      );
      const cx = x + w / 2;
      const cy = y + h / 2;
      out.push(
        '<text x="' +
          cx +
          '" y="' +
          (cy - 3) +
          '" font-size="11" font-weight="600" fill="#1e293b" text-anchor="middle">' +
          escapeHtml(pretty(r.category)) +
          "</text>",
      );
      out.push(
        '<text x="' +
          cx +
          '" y="' +
          (cy + 11) +
          '" font-size="9" fill="#64748b" text-anchor="middle">' +
          (r.width_m || 0).toFixed(1) +
          "×" +
          (r.depth_m || 0).toFixed(1) +
          "m</text>",
      );
    });

    // Columns.
    cols.forEach((c) => {
      out.push(
        '<rect x="' +
          (px(c.x_m || 0) - 2) +
          '" y="' +
          (py(c.y_m || 0) - 2) +
          '" width="4" height="4" fill="#475569"/>',
      );
    });

    // North arrow.
    out.push(
      '<g transform="translate(' +
        (tW - 26) +
        ",26)\">" +
        '<line x1="0" y1="8" x2="0" y2="-8" stroke="#334155" stroke-width="1.5"/>' +
        '<path d="M0,-10 L-3,-4 L3,-4 Z" fill="#334155"/>' +
        '<text x="0" y="20" font-size="9" fill="#334155" text-anchor="middle">N</text>' +
        "</g>",
    );

    out.push("</svg>");
    return out.join("");
  }

  function escapeHtml(s) {
    if (s === null || s === undefined) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }
})();
