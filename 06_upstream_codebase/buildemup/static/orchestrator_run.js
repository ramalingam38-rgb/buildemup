// orchestrator_run.js — drives the master-orchestrator UI (S59 #14).
//
// POSTs to /api/orchestrate with the form's fixture choices, then
// renders per-phase chips, the C16 drawings (when the phase ships
// OK with bundles), and per-phase detail accordions.

(function () {
  "use strict";

  const form = document.getElementById("orch-form");
  const runBtn = document.getElementById("run-btn");
  const runStatus = document.getElementById("run-status");
  const resultPanel = document.getElementById("result-panel");
  const runElapsed = document.getElementById("run-elapsed");
  const runSummaryText = document.getElementById("run-summary-text");
  const phaseChips = document.getElementById("phase-chips");
  const c3aPanel = document.getElementById("c3a-panel");
  const c3aCases = document.getElementById("c3a-cases");
  const drawingsStatus = document.getElementById("drawings-status");
  const drawingsContent = document.getElementById("drawings-content");
  const phaseDetails = document.getElementById("phase-details");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    runBtn.disabled = true;
    runBtn.textContent = "Running…";
    runStatus.textContent = "this may take 30–60 seconds";
    resultPanel.classList.add("hidden");

    const formData = new FormData(form);
    const payload = {
      plot_fixture: formData.get("plot_fixture"),
      brief_fixture: formData.get("brief_fixture"),
      include_payloads: !!formData.get("include_payloads"),
      config: {
        vastu_tier: formData.get("vastu_tier"),
        use_real_c11b_evaluator: !!formData.get("use_real_c11b_evaluator"),
        enable_full_mutation_operators:
          !!formData.get("enable_full_mutation_operators"),
      },
    };

    let response, body;
    try {
      response = await fetch("/api/orchestrate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      body = await response.json();
    } catch (err) {
      runStatus.textContent = "request failed: " + err;
      runBtn.disabled = false;
      runBtn.textContent = "Run pipeline";
      return;
    }

    runBtn.disabled = false;
    runBtn.textContent = "Run pipeline";
    runStatus.textContent = "done";

    if (!response.ok) {
      runSummaryText.innerHTML =
        '<span class="text-red-700">Pipeline request rejected.</span> ' +
        escapeHtml(JSON.stringify(body, null, 2));
      resultPanel.classList.remove("hidden");
      return;
    }

    renderResult(body);
  });

  function renderResult(body) {
    resultPanel.classList.remove("hidden");

    // Summary header.
    const overall = body.overall_status || "unknown";
    runElapsed.textContent =
      (body.total_elapsed_ms || 0).toFixed(0) + " ms";
    runSummaryText.innerHTML =
      '<span class="font-medium">' + escapeHtml(overall) + '</span> — ' +
      escapeHtml(body.summary || "");

    // Per-phase chips.
    phaseChips.innerHTML = "";
    (body.phases || []).forEach((p) => {
      phaseChips.appendChild(buildChip(p));
    });

    // C3a panel — show when extreme-case-detection phase ran.
    const c3a = (body.phases || []).find(
      (p) => p.phase_id === "c03a_extreme_case_detection",
    );
    renderC3aPanel(c3a);

    // C16 drawings (formal bundle) — with C12 placement-preview fallback.
    const c16 = (body.phases || []).find(
      (p) => p.phase_id === "c16_dual_drawings",
    );
    renderDrawings(c16, body.layout_preview);

    // Phase detail accordion.
    phaseDetails.innerHTML = "";
    (body.phases || []).forEach((p) => {
      phaseDetails.appendChild(buildDetailRow(p));
    });
  }

  function buildChip(phase) {
    const node = document.createElement("div");
    node.className = "phase-chip phase-chip-" + (phase.status || "skipped");
    const label = document.createElement("span");
    label.textContent = phase.phase_id;
    label.className = "font-medium";
    const badge = document.createElement("span");
    badge.className = "chip-status";
    badge.textContent = phase.status || "?";
    node.appendChild(label);
    node.appendChild(badge);
    return node;
  }

  function renderC3aPanel(c3a) {
    if (!c3a || c3a.status === "skipped") {
      c3aPanel.classList.add("hidden");
      return;
    }
    c3aPanel.classList.remove("hidden");
    const cases = (c3a.payload && c3a.payload.cases_detected) || [];
    if (cases.length === 0) {
      c3aCases.innerHTML =
        '<span class="text-green-700">' +
        "No extreme cases detected.</span>";
      return;
    }
    const list = cases
      .map(
        (c) =>
          '<li><span class="font-medium">' +
          escapeHtml(c.case_id || "") +
          "</span> — " +
          escapeHtml(c.category || "") +
          "</li>",
      )
      .join("");
    c3aCases.innerHTML =
      '<p class="mb-2 text-amber-700">' +
      cases.length +
      " case(s) detected — pipeline continues; route to " +
      "<code>/api/extreme-case/check</code> for interactive negotiation.</p>" +
      '<ul class="list-disc pl-6 space-y-1">' +
      list +
      "</ul>";
  }

  function renderDrawings(c16, layoutPreview) {
    drawingsContent.innerHTML = "";

    // Did C16 produce a formal bundle with drawable successes?
    const c16Successes =
      (c16 && c16.payload && c16.payload.successes) || [];

    if (c16 && c16.status === "ok" && c16Successes.length > 0) {
      const failures = (c16.payload && c16.payload.failures) || [];
      drawingsStatus.innerHTML =
        "<strong>" +
        c16Successes.length +
        "</strong> formal drawing bundle(s) rendered (C16), " +
        "<strong>" +
        failures.length +
        "</strong> per-candidate failure(s).";
      c16Successes.forEach((s, i) => {
        drawingsContent.appendChild(buildDrawingCard(s, i));
      });
      return;
    }

    // Fallback: render the C12 placement preview so the user always
    // sees a floorplan, even when the formal C16 bundle is STUB.
    if (layoutPreview && (layoutPreview.rooms || []).length > 0) {
      const c16Note = c16 && c16.stub_reason ? c16.stub_reason : "";
      drawingsStatus.innerHTML =
        '<span class="text-blue-700 font-medium">Placement preview</span> ' +
        "— " +
        (layoutPreview.rooms || []).length +
        " rooms from the live C9 sizing + C12 placement engine.";
      drawingsContent.appendChild(
        buildPreviewCard(layoutPreview, c16Note),
      );
      return;
    }

    // Nothing to draw at all — explain why honestly.
    if (!c16) {
      drawingsStatus.textContent = "C16 phase missing from response.";
    } else if (c16.status === "skipped") {
      drawingsStatus.textContent =
        "C16 skipped: " + (c16.skip_reason || "(no reason)");
    } else if (c16.status === "stub") {
      drawingsStatus.innerHTML =
        '<span class="text-amber-700">C16 STUB:</span> ' +
        escapeHtml(c16.stub_reason || "") +
        " (no upstream placement to preview)";
    } else if (c16.status === "error") {
      drawingsStatus.innerHTML =
        '<span class="text-red-700">C16 error:</span> ' +
        escapeHtml(c16.error_class || "") +
        " — " +
        escapeHtml(c16.error_message || "");
    } else {
      drawingsStatus.textContent = "No drawable geometry available.";
    }
  }

  // Render the C12 placement preview as an SVG floorplan. This is the
  // engine's actual room placement (positions + sizes from C9/C12),
  // shown when the formal C16 bundle isn't available yet.
  function buildPreviewCard(preview, c16Note) {
    const card = document.createElement("div");
    card.className = "drawing-card mb-4";

    const header = document.createElement("div");
    header.className = "flex items-baseline justify-between mb-2";
    const env = preview.envelope || {};
    header.innerHTML =
      '<span class="font-medium text-sm">Floor placement preview</span>' +
      '<span class="text-xs text-gray-500">' +
      escapeHtml(
        (env.width_m || "?") + "m × " + (env.depth_m || "?") + "m envelope",
      ) +
      "</span>";
    card.appendChild(header);

    const svgWrap = document.createElement("div");
    svgWrap.className = "drawing-svg-wrap";
    svgWrap.innerHTML = renderPreviewSvg(preview);
    card.appendChild(svgWrap);

    if (preview.note) {
      const note = document.createElement("p");
      note.className = "text-xs text-gray-500 mt-2 italic";
      note.textContent = preview.note;
      card.appendChild(note);
    }
    return card;
  }

  // SVG renderer for the placement preview. Rooms are colour-coded
  // rects (metres → scaled), columns small dark squares, plus an
  // envelope outline. Y is flipped so north reads up.
  function renderPreviewSvg(preview) {
    const rooms = preview.rooms || [];
    const columns = preview.columns || [];
    const env = preview.envelope || {};
    if (rooms.length === 0) {
      return '<p class="text-sm text-gray-500 p-4">No rooms to draw.</p>';
    }

    // Bounds: prefer envelope, fall back to room bbox.
    let W = env.width_m || 0;
    let H = env.depth_m || 0;
    rooms.forEach((r) => {
      W = Math.max(W, (r.x_m || 0) + (r.width_m || 0));
      H = Math.max(H, (r.y_m || 0) + (r.depth_m || 0));
    });
    W = W || 1;
    H = H || 1;

    const pad = 24;
    const targetW = 600;
    const targetH = 460;
    const scale = Math.min(
      (targetW - 2 * pad) / W,
      (targetH - 2 * pad) / H,
    );
    const px = (x) => pad + x * scale;
    // Flip Y so SW-origin reads naturally (north up).
    const py = (y) => targetH - pad - y * scale;

    const parts = [
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' +
        targetW +
        " " +
        targetH +
        '" preserveAspectRatio="xMidYMid meet">',
      '<rect width="100%" height="100%" fill="#fafafa"/>',
    ];

    // Envelope outline.
    parts.push(
      '<rect x="' +
        px(0) +
        '" y="' +
        py(H) +
        '" width="' +
        W * scale +
        '" height="' +
        H * scale +
        '" fill="none" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4 3"/>',
    );

    // Rooms.
    rooms.forEach((r) => {
      const x = px(r.x_m || 0);
      const y = py((r.y_m || 0) + (r.depth_m || 0)); // top-left after flip
      const w = (r.width_m || 0) * scale;
      const h = (r.depth_m || 0) * scale;
      parts.push(
        '<rect x="' +
          x +
          '" y="' +
          y +
          '" width="' +
          w +
          '" height="' +
          h +
          '" fill="' +
          colorForCategory(r.category) +
          '" stroke="#475569" stroke-width="1.2" rx="1.5"/>',
      );
      // Label: category + dimensions.
      const cx = x + w / 2;
      const cy = y + h / 2;
      parts.push(
        '<text x="' +
          cx +
          '" y="' +
          (cy - 4) +
          '" font-size="10" font-weight="600" fill="#1e293b" text-anchor="middle" dominant-baseline="middle">' +
          escapeHtml(prettyCategory(r.category)) +
          "</text>",
      );
      parts.push(
        '<text x="' +
          cx +
          '" y="' +
          (cy + 9) +
          '" font-size="8" fill="#64748b" text-anchor="middle" dominant-baseline="middle">' +
          escapeHtml(
            (r.width_m || 0).toFixed(1) + "×" + (r.depth_m || 0).toFixed(1) + "m",
          ) +
          "</text>",
      );
    });

    // Columns.
    columns.forEach((c) => {
      const cx = px(c.x_m || 0);
      const cy = py(c.y_m || 0);
      parts.push(
        '<rect x="' +
          (cx - 2.5) +
          '" y="' +
          (cy - 2.5) +
          '" width="5" height="5" fill="#334155"/>',
      );
    });

    parts.push("</svg>");
    return parts.join("");
  }

  function prettyCategory(cat) {
    const s = (cat || "").replace(/_/g, " ");
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  function buildDrawingCard(success, idx) {
    const card = document.createElement("div");
    card.className = "drawing-card mb-4";
    const bundle = (success && success.bundle) || {};
    const header = document.createElement("div");
    header.className = "flex items-baseline justify-between mb-2";
    header.innerHTML =
      '<span class="font-medium text-sm">Drawing bundle ' +
      (idx + 1) +
      "</span>" +
      '<span class="text-xs text-gray-500">' +
      escapeHtml(
        (bundle.jurisdiction_profile_id || "tn_cdbr_2019") +
          " · " +
          (bundle.declared_domain_scope || "residential_v1"),
      ) +
      "</span>";
    card.appendChild(header);

    // Build a minimal SVG visualization of the floor geometry.
    const svgWrap = document.createElement("div");
    svgWrap.className = "drawing-svg-wrap";
    svgWrap.innerHTML = renderFloorSvg(bundle);
    card.appendChild(svgWrap);

    // Compliance summary.
    const permit = bundle.permit_drawing_model || {};
    const complete = permit.legal_completeness || "?";
    const readability = permit.readability_status || "?";
    const compliance = document.createElement("p");
    compliance.className = "text-xs text-gray-600 mt-2";
    compliance.innerHTML =
      "Legal completeness: <strong>" +
      escapeHtml(complete) +
      "</strong> · Readability: <strong>" +
      escapeHtml(readability) +
      "</strong>";
    card.appendChild(compliance);
    return card;
  }

  // Render a simple SVG floorplan from the first FloorGeometry in the
  // bundle. Pulls room rects + walls + doors + columns; scales to fit a
  // 600×400 viewport.
  function renderFloorSvg(bundle) {
    const floors = (bundle && bundle.floor_geometries) || [];
    if (floors.length === 0) {
      return '<p class="text-sm text-gray-500 p-4">No floor geometry.</p>';
    }
    const floor = floors[0];
    const rooms = floor.rooms || [];
    const walls = floor.walls || [];
    const doors = floor.doors || [];
    const columns = floor.columns || [];

    // Bounding box from rooms.
    let minX = Infinity,
      minY = Infinity,
      maxX = -Infinity,
      maxY = -Infinity;
    rooms.forEach((r) => {
      minX = Math.min(minX, r.x_mm);
      minY = Math.min(minY, r.y_mm);
      maxX = Math.max(maxX, r.x_mm + r.width_mm);
      maxY = Math.max(maxY, r.y_mm + r.depth_mm);
    });
    walls.forEach((w) => {
      minX = Math.min(minX, w.start_x_mm, w.end_x_mm);
      minY = Math.min(minY, w.start_y_mm, w.end_y_mm);
      maxX = Math.max(maxX, w.start_x_mm, w.end_x_mm);
      maxY = Math.max(maxY, w.start_y_mm, w.end_y_mm);
    });
    if (!isFinite(minX) || !isFinite(minY)) {
      return '<p class="text-sm text-gray-500 p-4">No drawable geometry.</p>';
    }
    const W = maxX - minX || 1;
    const H = maxY - minY || 1;
    const pad = 20;
    const targetW = 600;
    const targetH = 400;
    const scale = Math.min(
      (targetW - 2 * pad) / W,
      (targetH - 2 * pad) / H,
    );
    const project = (x, y) => [
      pad + (x - minX) * scale,
      // Flip Y so SW-origin geometry reads naturally (north up).
      targetH - pad - (y - minY) * scale,
    ];

    const parts = [
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' +
        targetW +
        " " +
        targetH +
        '" preserveAspectRatio="xMidYMid meet">',
      '<rect width="100%" height="100%" fill="#fafafa"/>',
    ];

    // Rooms.
    rooms.forEach((r) => {
      const [x1, y1] = project(r.x_mm, r.y_mm + r.depth_mm);
      const w = r.width_mm * scale;
      const h = r.depth_mm * scale;
      parts.push(
        '<rect x="' +
          x1 +
          '" y="' +
          y1 +
          '" width="' +
          w +
          '" height="' +
          h +
          '" fill="' +
          colorForCategory(r.category) +
          '" stroke="#475569" stroke-width="1"/>',
      );
      parts.push(
        '<text x="' +
          (x1 + w / 2) +
          '" y="' +
          (y1 + h / 2) +
          '" font-size="9" fill="#1e293b" text-anchor="middle" dominant-baseline="middle">' +
          escapeHtml((r.category || "").slice(0, 12)) +
          "</text>",
      );
    });

    // Walls.
    walls.forEach((w) => {
      const [x1, y1] = project(w.start_x_mm, w.start_y_mm);
      const [x2, y2] = project(w.end_x_mm, w.end_y_mm);
      parts.push(
        '<line x1="' +
          x1 +
          '" y1="' +
          y1 +
          '" x2="' +
          x2 +
          '" y2="' +
          y2 +
          '" stroke="#0f172a" stroke-width="2"/>',
      );
    });

    // Columns.
    columns.forEach((c) => {
      const [cx, cy] = project(c.x_mm, c.y_mm);
      parts.push(
        '<rect x="' +
          (cx - 4) +
          '" y="' +
          (cy - 4) +
          '" width="8" height="8" fill="#334155"/>',
      );
    });

    // Doors as small green circles.
    doors.forEach((d) => {
      const [cx, cy] = project(d.anchor_x_mm, d.anchor_y_mm);
      parts.push(
        '<circle cx="' +
          cx +
          '" cy="' +
          cy +
          '" r="4" fill="#16a34a" stroke="#065f46" stroke-width="1"/>',
      );
    });

    parts.push("</svg>");
    return parts.join("");
  }

  function colorForCategory(cat) {
    const map = {
      bedroom: "#e0f2fe",
      bathroom: "#fde68a",
      kitchen: "#fbcfe8",
      living: "#dcfce7",
      pooja: "#fee2e2",
      utility: "#e5e7eb",
      study: "#ede9fe",
    };
    return map[(cat || "").toLowerCase()] || "#f1f5f9";
  }

  function buildDetailRow(phase) {
    const row = document.createElement("div");
    row.className = "phase-row";
    const summary = document.createElement("div");
    summary.className = "phase-row-summary";
    summary.innerHTML =
      '<span><span class="font-medium">' +
      escapeHtml(phase.phase_id) +
      "</span> " +
      '<span class="ml-2 text-xs text-gray-500">' +
      (phase.elapsed_ms || 0).toFixed(0) +
      " ms</span></span>" +
      '<span class="chip-status phase-chip-' +
      (phase.status || "skipped") +
      '">' +
      escapeHtml(phase.status || "?") +
      "</span>";
    const body = document.createElement("div");
    body.className = "phase-row-body hidden";
    body.innerHTML = buildDetailHtml(phase);
    summary.addEventListener("click", () => body.classList.toggle("hidden"));
    row.appendChild(summary);
    row.appendChild(body);
    return row;
  }

  function buildDetailHtml(phase) {
    const parts = [];
    if (phase.skip_reason) {
      parts.push(
        '<p class="mb-2"><strong>Skipped:</strong> ' +
          escapeHtml(phase.skip_reason) +
          "</p>",
      );
    }
    if (phase.stub_reason) {
      parts.push(
        '<p class="mb-2 text-amber-800"><strong>STUB:</strong> ' +
          escapeHtml(phase.stub_reason) +
          "</p>",
      );
    }
    if (phase.error_class || phase.error_message) {
      parts.push(
        '<p class="mb-2 text-red-800"><strong>Error:</strong> ' +
          escapeHtml(phase.error_class) +
          " — " +
          escapeHtml(phase.error_message) +
          "</p>",
      );
    }
    if (phase.notes && phase.notes.length > 0) {
      parts.push(
        '<p class="text-xs uppercase text-gray-500 mb-1">Notes</p><ul class="mb-2 list-disc pl-6 text-sm">' +
          phase.notes.map((n) => "<li>" + escapeHtml(n) + "</li>").join("") +
          "</ul>",
      );
    }
    if (phase.payload !== undefined) {
      parts.push(
        '<p class="text-xs uppercase text-gray-500 mb-1">Payload</p><pre>' +
          escapeHtml(JSON.stringify(phase.payload, null, 2)) +
          "</pre>",
      );
    }
    return parts.join("") || '<p class="text-sm text-gray-500">No additional detail.</p>';
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
