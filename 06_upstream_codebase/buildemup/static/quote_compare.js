// quote_compare.js — drives the C17 quote-comparison UI (S59 #9/#14).
//
// POSTs to /api/quote/compare with the parsed_quote + cost_lines
// JSON payloads. Renders the summary block, signatures, and an
// optional full report panel.

(function () {
  "use strict";

  const SAMPLE_PARSED_QUOTE = {
    parsed_quote_id: "pq-demo-001",
    contractor_label: "Anand Constructions Pvt Ltd",
    quote_date_iso: "2026-05-15",
    quote_total_inr: 425000.0,
    parsed_quote_signature: "demo-signature-not-real-sha256",
    line_items: [
      {
        line_id: "L001",
        raw_label: "Cement OPC 53 (50kg bag) — UltraTech",
        quantity: 250.0,
        unit: "bag",
        rate: 425.0,
        total: 106250.0,
        is_lump_sum_hint: false,
      },
      {
        line_id: "L002",
        raw_label: "Ready Mix Concrete M20",
        quantity: 8.0,
        unit: "cum",
        rate: 5100.0,
        total: 40800.0,
        is_lump_sum_hint: false,
      },
      {
        line_id: "L003",
        raw_label: "Painting works — entire interior",
        quantity: null,
        unit: "",
        rate: null,
        total: 80000.0,
        is_lump_sum_hint: true,
      },
    ],
  };

  const SAMPLE_COST_LINES = [
    {
      item_id: "C7-RCC-CEMENT-001",
      label: "Cement OPC 53",
      category: "structural_rcc",
      quantity: 250.0,
      unit: "bag",
      rate_category: "structural_rcc",
      rate_key: "cement_opc_53",
      severity: "critical",
    },
    {
      item_id: "C7-RCC-RMC-001",
      label: "Ready Mix Concrete M20",
      category: "structural_rcc",
      quantity: 8.0,
      unit: "cum",
      rate_category: "structural_rcc",
      rate_key: "rmc_m20",
      severity: "critical",
    },
  ];

  const form = document.getElementById("quote-form");
  const runBtn = document.getElementById("run-btn");
  const loadSample = document.getElementById("load-sample-btn");
  const runStatus = document.getElementById("run-status");
  const resultPanel = document.getElementById("result-panel");
  const summaryGrid = document.getElementById("summary-grid");
  const signatures = document.getElementById("signatures");
  const payloadPanel = document.getElementById("payload-panel");
  const payloadPre = document.getElementById("payload-pre");

  loadSample.addEventListener("click", () => {
    form.parsed_quote_json.value = JSON.stringify(
      SAMPLE_PARSED_QUOTE, null, 2,
    );
    form.cost_lines_json.value = JSON.stringify(SAMPLE_COST_LINES, null, 2);
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    runBtn.disabled = true;
    runBtn.textContent = "Running…";
    runStatus.textContent = "comparing against rate provider";
    resultPanel.classList.add("hidden");
    payloadPanel.classList.add("hidden");

    let parsedQuote, costLines;
    try {
      parsedQuote = JSON.parse(form.parsed_quote_json.value || "{}");
    } catch (err) {
      runStatus.textContent = "parsed_quote JSON parse error: " + err;
      runBtn.disabled = false;
      runBtn.textContent = "Run quote comparison";
      return;
    }
    try {
      costLines = JSON.parse(form.cost_lines_json.value || "[]");
    } catch (err) {
      runStatus.textContent = "cost_lines JSON parse error: " + err;
      runBtn.disabled = false;
      runBtn.textContent = "Run quote comparison";
      return;
    }

    const formData = new FormData(form);
    const payload = {
      project_id: formData.get("project_id"),
      jurisdiction_profile_id: formData.get("jurisdiction_profile_id"),
      declared_domain_scope: formData.get("declared_domain_scope"),
      parsed_quote: parsedQuote,
      cost_lines: costLines,
      include_payload: !!formData.get("include_payload"),
    };

    let response, body;
    try {
      response = await fetch("/api/quote/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      body = await response.json();
    } catch (err) {
      runStatus.textContent = "request failed: " + err;
      runBtn.disabled = false;
      runBtn.textContent = "Run quote comparison";
      return;
    }

    runBtn.disabled = false;
    runBtn.textContent = "Run quote comparison";

    if (!response.ok) {
      runStatus.textContent = "error " + response.status;
      summaryGrid.innerHTML =
        '<pre class="col-span-3 text-red-700">' +
        escapeHtml(JSON.stringify(body, null, 2)) +
        "</pre>";
      resultPanel.classList.remove("hidden");
      return;
    }

    runStatus.textContent = "done";
    renderResult(body);
  });

  function renderResult(body) {
    resultPanel.classList.remove("hidden");
    const s = body.summary || {};
    summaryGrid.innerHTML = "";
    const cells = [
      ["Matched lines", s.matched_lines, ""],
      ["Gaps in quote (BOQ items missing)", s.gaps_in_quote, ""],
      ["Unmatched quote lines", s.unmatched_quote_lines, ""],
      ["Lump-sum indicators", s.lump_sum_indicators, ""],
      ["Quote total (₹)", numberFmt(s.quote_total_inr), ""],
      ["Delta vs estimate (%)", numberFmt(s.delta_pct), "pct"],
      ["Report confidence", s.report_confidence_tier, "tier"],
      ["Decomposition style", s.decomposition_style, ""],
      ["Advisory flags", s.advisory_flags, ""],
    ];
    cells.forEach(([label, value, _meta]) => {
      const card = document.createElement("div");
      card.className =
        "p-3 rounded-md border border-gray-200 bg-gray-50";
      card.innerHTML =
        '<div class="text-xs text-gray-500 mb-1">' +
        escapeHtml(label) +
        '</div><div class="text-base font-semibold">' +
        escapeHtml(value === undefined || value === null ? "—" : value) +
        "</div>";
      summaryGrid.appendChild(card);
    });

    signatures.textContent = JSON.stringify(body.signatures || {}, null, 2);

    if (body.report) {
      payloadPanel.classList.remove("hidden");
      payloadPre.textContent = JSON.stringify(body.report, null, 2);
    }
  }

  function numberFmt(n) {
    if (n === undefined || n === null) return "—";
    if (typeof n !== "number") return n;
    return n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
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
