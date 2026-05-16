"""S8 § 5.6.1 + § 4.11 — Phase 5 static-serving behaviors (Session 28).

These tests cover the two server.py patches added in Session 28 to
complete Phase 5:

  (1) /c3a/_test_harness.html is gated behind C3A_TEST_MODE=1 per
      § 4.11 ("NOT served in production"). When the env var is unset
      or != "1", the route returns 404. When set, it serves the file.

  (2) /c3a/*.html responses inject `<meta name="c3a-test-mode"
      content="1">` after the <head> tag when C3A_TEST_MODE=1, per
      § 5.6.1. This surfaces the test-mode flag to the browser so
      _shared.js isTestMode() returns true and c3aFetch disables its
      503 auto-retry (External Item 3 / P36). Injection is idempotent
      and applies only to /c3a/*.html (not js/css, not other surfaces).

Why these tests live in tests/validation/ rather than tests/e2e/:
they verify HTTP-level server behavior, not browser-level flow.
The validation suite's live_server fixture is the right fit and the
budget impact is sub-second.

These tests use pytest's monkeypatch fixture for env-var hygiene so
test ordering does not matter.
"""
from __future__ import annotations

import urllib.error
import urllib.request


def _get(url: str) -> tuple[int, bytes, dict[str, str]]:
    """GET helper. Returns (status, body, headers).

    Treats 4xx/5xx as data, not exceptions, so tests can assert on
    them naturally.
    """
    try:
        resp = urllib.request.urlopen(url, timeout=5)
        return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


# ─────────────────────────────────────────────────────────────────────
# § 4.11 — _test_harness.html route guard
# ─────────────────────────────────────────────────────────────────────


def test_test_harness_returns_404_when_test_mode_unset(
    live_server, monkeypatch,
):
    """§ 4.11: production deploys must NOT expose the test harness.

    Protects: § 4.11 invariant — _test_harness.html is for e2e tests
    only; serving it in prod would let any caller bypass test-mode
    gating of c3aFetch's 503 auto-retry, breaking real-user behavior.
    """
    monkeypatch.delenv("C3A_TEST_MODE", raising=False)
    status, body, _ = _get(f"{live_server}/c3a/_test_harness.html")
    assert status == 404, (
        f"expected 404 with C3A_TEST_MODE unset; got {status}"
    )


def test_test_harness_returns_404_when_test_mode_not_one(
    live_server, monkeypatch,
):
    """§ 4.11: only the literal value "1" unlocks the harness.

    Protects: prevents truthy-but-not-one values (e.g. "true", "yes",
    "0", empty) from accidentally exposing the harness in prod due
    to lax env-var parsing.
    """
    for value in ("0", "true", "yes", "", "TRUE", "1 "):
        monkeypatch.setenv("C3A_TEST_MODE", value)
        status, _, _ = _get(f"{live_server}/c3a/_test_harness.html")
        assert status == 404, (
            f'C3A_TEST_MODE={value!r} should be 404; got {status}'
        )


def test_test_harness_returns_200_when_test_mode_one(
    live_server, monkeypatch,
):
    """§ 4.11: when C3A_TEST_MODE=1, harness is served.

    Protects: the e2e tests that load /c3a/_test_harness.html to
    exercise handlePageFlow's branch dispatch (§ 4.11 v1.2 P-4).
    """
    monkeypatch.setenv("C3A_TEST_MODE", "1")
    status, body, headers = _get(
        f"{live_server}/c3a/_test_harness.html",
    )
    assert status == 200, f"expected 200 with C3A_TEST_MODE=1; got {status}"
    # The harness body identifies itself in its <title>
    assert b"Test Harness" in body
    # Served as HTML
    ct = headers.get("Content-Type", "")
    assert "text/html" in ct, f"unexpected content-type: {ct!r}"


# ─────────────────────────────────────────────────────────────────────
# § 5.6.1 — Test-mode meta-tag injection on /c3a/*.html
# ─────────────────────────────────────────────────────────────────────


def test_meta_tag_injected_for_case_html_when_test_mode_set(
    live_server, monkeypatch,
):
    """§ 5.6.1: c3a-test-mode meta tag is injected into /c3a/case.html
    when C3A_TEST_MODE=1.

    Protects: _shared.js isTestMode() returns true, which disables
    c3aFetch's 503 auto-retry — necessary for tests to deterministically
    observe 503 paths without the wrapper retrying first.
    """
    monkeypatch.setenv("C3A_TEST_MODE", "1")
    status, body, _ = _get(f"{live_server}/c3a/case.html")
    assert status == 200
    # The injected tag appears exactly once, with the canonical content
    text = body.decode("utf-8")
    assert text.count('name="c3a-test-mode"') == 1, (
        f"expected exactly one c3a-test-mode meta tag; got "
        f"{text.count('c3a-test-mode')}"
    )
    assert '<meta name="c3a-test-mode" content="1">' in text


def test_meta_tag_not_injected_when_test_mode_unset(
    live_server, monkeypatch,
):
    """§ 5.6.1: when env var is unset, the meta tag is NOT injected.

    Protects: production users get the production behavior (with 503
    auto-retry), not the test-mode behavior.
    """
    monkeypatch.delenv("C3A_TEST_MODE", raising=False)
    status, body, _ = _get(f"{live_server}/c3a/case.html")
    assert status == 200
    assert b'name="c3a-test-mode"' not in body, (
        "meta tag should NOT be injected when C3A_TEST_MODE is unset"
    )


def test_meta_tag_idempotent_for_test_harness(
    live_server, monkeypatch,
):
    """§ 5.6.1 idempotency: _test_harness.html has the meta tag
    hardcoded; the injector must NOT add a second copy when serving
    it in test mode.

    Protects: a duplicate meta tag could cause unpredictable behavior
    in browsers parsing multiple meta tags with the same name.
    """
    monkeypatch.setenv("C3A_TEST_MODE", "1")
    status, body, _ = _get(f"{live_server}/c3a/_test_harness.html")
    assert status == 200
    text = body.decode("utf-8")
    assert text.count('name="c3a-test-mode"') == 1, (
        f"injector duplicated the meta tag: count="
        f"{text.count('c3a-test-mode')}"
    )


def test_meta_tag_not_injected_for_js_or_css(
    live_server, monkeypatch,
):
    """§ 5.6.1: injection is HTML-only; JS/CSS assets are
    served byte-identical regardless of env.

    Protects: case.js and _shared.css must NEVER be modified by the
    server — modifying JS could break parsing; modifying CSS could
    introduce broken rules.

    Note: a substring check for `name="c3a-test-mode"` would falsely
    fire on _shared.js, which legitimately contains that string in
    its querySelector for the meta tag. The real invariant is
    byte-identity with the file on disk; we assert that directly.
    """
    from buildemup.api.server import STATIC_DIR

    monkeypatch.setenv("C3A_TEST_MODE", "1")
    for path in ("/c3a/case.js", "/c3a/_shared.css", "/c3a/_shared.js"):
        status, body, _ = _get(f"{live_server}{path}")
        assert status == 200, f"{path} returned {status}"
        on_disk = (STATIC_DIR / path.lstrip("/")).read_bytes()
        assert body == on_disk, (
            f"{path} body differs from on-disk file by "
            f"{len(body) - len(on_disk)} bytes — server modified it"
        )


def test_meta_tag_not_injected_for_non_c3a_html(
    live_server, monkeypatch,
):
    """§ 5.6.1: only /c3a/*.html is targeted. /brief_form.html and
    other static HTML surfaces stay untouched even with env set.

    Protects: surfaces outside C3a (e.g. brief_form) aren't accidentally
    flagged as test-mode-aware; their behavior shouldn't change based
    on a C3a-specific env var.
    """
    monkeypatch.setenv("C3A_TEST_MODE", "1")
    status, body, _ = _get(f"{live_server}/brief_form.html")
    assert status == 200
    assert b'name="c3a-test-mode"' not in body, (
        "meta tag was wrongly injected into /brief_form.html"
    )


def test_meta_tag_position_after_head_tag(
    live_server, monkeypatch,
):
    """§ 5.6.1: tag is injected immediately after <head>, BEFORE
    any <link> or other meta — so isTestMode() can find it without
    waiting for full document parse.

    Protects: predictable position for the e2e tests that verify
    isTestMode() at page-load time.
    """
    monkeypatch.setenv("C3A_TEST_MODE", "1")
    _, body, _ = _get(f"{live_server}/c3a/case.html")
    text = body.decode("utf-8")
    head_pos = text.find("<head>")
    meta_pos = text.find('<meta name="c3a-test-mode"')
    title_pos = text.find("<title>")
    assert head_pos != -1, "<head> tag missing"
    assert meta_pos != -1, "c3a-test-mode meta tag missing"
    assert head_pos < meta_pos < title_pos, (
        f"meta tag misplaced: head={head_pos} meta={meta_pos} "
        f"title={title_pos}"
    )
