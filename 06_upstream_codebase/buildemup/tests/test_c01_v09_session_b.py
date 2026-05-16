"""
v0.9 Session B tests — Server-side save/resume (SQLite + API + HTTP).

Covers:
  - BriefStorage (SQLite): save, resume, delete, TTL expiry, token format
  - API layer: handle_brief_save, handle_brief_resume
  - HTTP server end-to-end: POST /api/brief/save → token → GET /api/brief/resume
  - Frontend static: check updated brief_form.js has save-to-server logic
"""
import sys
import os
import json
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _isolated_storage():
    """Fresh storage on a temp DB file — every test gets a clean slate."""
    from buildemup.utils.brief_storage import BriefStorage
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)    # BriefStorage will recreate it
    return BriefStorage(db_path=path), path


def _cleanup(path):
    # S55 Batch 4 (Windows fix): SQLite connections take a tick to fully
    # release the file handle on Windows even after the `with` block
    # exits. PermissionError on the unlink is benign — the OS cleans up
    # the temp file on next sweep. FileNotFoundError happens when a
    # prior cleanup already ran.
    import gc
    gc.collect()
    for _ in range(3):
        try:
            os.unlink(path)
            return
        except FileNotFoundError:
            return
        except PermissionError:
            time.sleep(0.05)
            gc.collect()
    # Final attempt — swallow if still locked (temp file, OS will clean).
    try:
        os.unlink(path)
    except (FileNotFoundError, PermissionError):
        pass


# ─────────────────────────────────────────────────────────────────────────
# BriefStorage unit tests
# ─────────────────────────────────────────────────────────────────────────

def test_storage_save_and_resume():
    """Basic save returns token; resume returns the payload."""
    storage, path = _isolated_storage()
    try:
        payload = {"plot_width_m": 12.0, "city": "chennai", "step": 2}
        token, expires_at = storage.save(payload)
        assert len(token) == 24
        assert expires_at > time.time()
        got = storage.resume(token)
        assert got == payload
        print(f"PASS save + resume round-trip (token={token[:8]}...)")
    finally:
        _cleanup(path)


def test_storage_token_format():
    """Tokens are 24 hex chars."""
    from buildemup.utils.brief_storage import BriefStorage
    storage, path = _isolated_storage()
    try:
        token, _ = storage.save({"x": 1})
        assert len(token) == 24
        # Must be valid hex
        int(token, 16)
        # Must differ across saves
        token2, _ = storage.save({"y": 2})
        assert token != token2
        print(f"PASS tokens are 24 hex chars and unique per save")
    finally:
        _cleanup(path)


def test_storage_existing_token_updates_in_place():
    """existing_token=X updates the same row, returns same token."""
    storage, path = _isolated_storage()
    try:
        t1, _ = storage.save({"step": 1})
        t2, _ = storage.save({"step": 2}, existing_token=t1)
        assert t1 == t2
        # Resumed payload reflects the update
        assert storage.resume(t1)["step"] == 2
        # Count should still be 1 (update, not duplicate)
        assert storage.count() == 1
        print(f"PASS existing_token → in-place update, same token")
    finally:
        _cleanup(path)


def test_storage_unknown_token_raises():
    """Resume with a valid-format but unknown token → TokenNotFoundError."""
    from buildemup.utils.brief_storage import TokenNotFoundError
    storage, path = _isolated_storage()
    try:
        try:
            storage.resume("0" * 24)
            assert False, "Expected TokenNotFoundError"
        except TokenNotFoundError as e:
            assert "No saved brief" in str(e)
        print("PASS unknown token raises TokenNotFoundError")
    finally:
        _cleanup(path)


def test_storage_invalid_token_format_raises():
    """Resume with malformed token (wrong length, non-hex) → raises."""
    from buildemup.utils.brief_storage import TokenNotFoundError
    storage, path = _isolated_storage()
    try:
        for bad in ["short", "not-hex-at-all--zzzzzzzz", "", None, "0" * 100]:
            try:
                storage.resume(bad)
                assert False, f"Should have raised for: {bad!r}"
            except TokenNotFoundError:
                pass  # expected
        print("PASS malformed tokens rejected")
    finally:
        _cleanup(path)


def test_storage_payload_too_large_rejected():
    """Payloads > 1 MB are rejected."""
    from buildemup.utils.brief_storage import (
        PayloadTooLargeError, MAX_PAYLOAD_BYTES,
    )
    storage, path = _isolated_storage()
    try:
        huge = {"x": "A" * (MAX_PAYLOAD_BYTES + 1000)}
        try:
            storage.save(huge)
            assert False, "Expected PayloadTooLargeError"
        except PayloadTooLargeError:
            pass
        print(f"PASS payloads > {MAX_PAYLOAD_BYTES} bytes rejected")
    finally:
        _cleanup(path)


def test_storage_ttl_expiry():
    """Expired rows are unreadable and auto-pruned on next save."""
    import sqlite3
    from buildemup.utils.brief_storage import TokenNotFoundError
    storage, path = _isolated_storage()
    try:
        token, _ = storage.save({"x": 1})
        # Force the row to be expired
        with sqlite3.connect(path) as c:
            c.execute(
                "UPDATE briefs SET expires_at = ? WHERE token = ?",
                (time.time() - 3600, token),
            )
            c.commit()
        # Resume must now fail
        try:
            storage.resume(token)
            assert False, "Expected expired raise"
        except TokenNotFoundError as e:
            assert "expired" in str(e).lower()
        # count() excludes expired
        assert storage.count() == 0
        # Another save prunes the expired row
        storage.save({"y": 2})
        with sqlite3.connect(path) as c:
            rows = c.execute("SELECT token FROM briefs").fetchall()
        assert len(rows) == 1   # only the fresh one
        print("PASS TTL expiry + auto-pruning on save")
    finally:
        _cleanup(path)


def test_storage_delete():
    """delete() removes a row and returns True; False when not present."""
    storage, path = _isolated_storage()
    try:
        t, _ = storage.save({"x": 1})
        assert storage.delete(t) is True
        assert storage.delete(t) is False    # already gone
        assert storage.count() == 0
        print("PASS delete + idempotent second call")
    finally:
        _cleanup(path)


def test_storage_count_and_prune_expired():
    """count() excludes expired; prune_expired() deletes them."""
    import sqlite3
    storage, path = _isolated_storage()
    try:
        t1, _ = storage.save({"a": 1})
        t2, _ = storage.save({"b": 2})
        assert storage.count() == 2
        # Expire t1
        with sqlite3.connect(path) as c:
            c.execute(
                "UPDATE briefs SET expires_at = ? WHERE token = ?",
                (time.time() - 100, t1),
            )
            c.commit()
        assert storage.count() == 1     # excludes expired
        n = storage.prune_expired()
        assert n == 1
        print("PASS count excludes expired, prune_expired removes them")
    finally:
        _cleanup(path)


# ─────────────────────────────────────────────────────────────────────────
# API layer unit tests
# ─────────────────────────────────────────────────────────────────────────

def _reset_api_storage(db_path):
    """Point the API singleton at a fresh DB."""
    from buildemup.api.brief_endpoint import _reset_storage_singleton
    os.environ["BUILDEMUP_DB_PATH"] = db_path
    _reset_storage_singleton()


def test_api_save_endpoint_returns_token_and_url():
    """POST-style save via handle_brief_save returns token + resume URL."""
    from buildemup.api.brief_endpoint import handle_brief_save
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    _reset_api_storage(path)
    try:
        payload = {"plot_width_m": 12.0, "city": "chennai"}
        status, body = handle_brief_save(
            json.dumps(payload),
            host_base_url="https://example.com",
        )
        assert status == 200
        assert body["ok"] is True
        assert len(body["token"]) == 24
        assert body["resume_url"].startswith("https://example.com/?resume=")
        assert body["resume_url"].endswith(body["token"])
        assert "expires_at_utc" in body
        assert "ephemeral_storage_warning" in body
        print(f"PASS API save returns token + resume URL "
              f"({body['resume_url'][:60]}...)")
    finally:
        _cleanup(path)


def test_api_save_rejects_bad_json():
    """Malformed body → 400."""
    from buildemup.api.brief_endpoint import handle_brief_save
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    _reset_api_storage(path)
    try:
        status, body = handle_brief_save("{not json}")
        assert status == 400
        assert body["ok"] is False
        print("PASS API save rejects malformed JSON")
    finally:
        _cleanup(path)


def test_api_save_rejects_non_dict_body():
    """JSON array or string → 400."""
    from buildemup.api.brief_endpoint import handle_brief_save
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    _reset_api_storage(path)
    try:
        status, body = handle_brief_save('["not", "a", "dict"]')
        assert status == 400
        assert "JSON object" in body["errors"][0]
        print("PASS API save rejects non-dict body")
    finally:
        _cleanup(path)


def test_api_save_too_large_payload():
    """Very large payload → 400 with clear message."""
    from buildemup.api.brief_endpoint import handle_brief_save
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    _reset_api_storage(path)
    try:
        huge = {"x": "A" * 2_000_000}
        status, body = handle_brief_save(json.dumps(huge))
        assert status == 400
        assert "exceeds" in body["errors"][0].lower()
        print("PASS API save rejects > 1MB payload")
    finally:
        _cleanup(path)


def test_api_resume_roundtrip():
    """Save → token → resume returns the exact payload."""
    from buildemup.api.brief_endpoint import (
        handle_brief_save, handle_brief_resume,
    )
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    _reset_api_storage(path)
    try:
        payload = {"plot_width_m": 12.0, "city": "chennai", "step": 3}
        _, body = handle_brief_save(json.dumps(payload))
        token = body["token"]
        status, body2 = handle_brief_resume(token)
        assert status == 200
        assert body2["ok"] is True
        assert body2["payload"] == payload
        assert body2["token"] == token
        print("PASS API save → resume roundtrip")
    finally:
        _cleanup(path)


def test_api_resume_unknown_token_404():
    """Unknown token → 404."""
    from buildemup.api.brief_endpoint import handle_brief_resume
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    _reset_api_storage(path)
    try:
        status, body = handle_brief_resume("0" * 24)
        assert status == 404
        assert body["ok"] is False
        print("PASS API resume with unknown token → 404")
    finally:
        _cleanup(path)


def test_api_resume_missing_token_400():
    """Empty token → 400."""
    from buildemup.api.brief_endpoint import handle_brief_resume
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    _reset_api_storage(path)
    try:
        status, body = handle_brief_resume("")
        assert status == 400
        assert "token" in body["errors"][0].lower()
        print("PASS API resume with empty token → 400")
    finally:
        _cleanup(path)


def test_api_save_with_existing_token_updates_in_place():
    """existing_token in body → same token, updated content."""
    from buildemup.api.brief_endpoint import (
        handle_brief_save, handle_brief_resume,
    )
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    _reset_api_storage(path)
    try:
        _, body = handle_brief_save(json.dumps({"step": 1}))
        t = body["token"]
        _, body2 = handle_brief_save(json.dumps(
            {"step": 2, "existing_token": t}
        ))
        assert body2["token"] == t
        # Resume gets the NEW content, not original
        _, resumed = handle_brief_resume(t)
        assert resumed["payload"]["step"] == 2
        # existing_token must not leak into stored payload
        assert "existing_token" not in resumed["payload"]
        print("PASS existing_token → in-place update via API")
    finally:
        _cleanup(path)


# ─────────────────────────────────────────────────────────────────────────
# HTTP server end-to-end
# ─────────────────────────────────────────────────────────────────────────

def test_http_save_resume_end_to_end():
    """Full HTTP cycle: POST /save → GET /resume → payload matches."""
    import threading
    import urllib.request
    import urllib.error
    from http.server import HTTPServer
    from buildemup.api.server import BriefCaptureHandler

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    _reset_api_storage(path)
    try:
        srv = HTTPServer(("127.0.0.1", 0), BriefCaptureHandler)
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
        try:
            base = f"http://127.0.0.1:{port}"
            payload = {"plot_width_m": 12.0, "city": "chennai", "step": 2}

            # 1. Save
            req = urllib.request.Request(
                f"{base}/api/brief/save",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                save_body = json.loads(r.read())
            assert save_body["ok"] is True
            token = save_body["token"]
            assert len(token) == 24
            assert token in save_body["resume_url"]

            # 2. Resume
            with urllib.request.urlopen(
                f"{base}/api/brief/resume?token={token}", timeout=5
            ) as r:
                resume_body = json.loads(r.read())
            assert resume_body["payload"] == payload

            # 3. Bad token via HTTP → 404
            try:
                urllib.request.urlopen(
                    f"{base}/api/brief/resume?token=deadbeef00000000deadbeef",
                    timeout=5,
                )
                assert False, "Expected 404"
            except urllib.error.HTTPError as e:
                assert e.code == 404

            # 4. Missing token → 400
            try:
                urllib.request.urlopen(
                    f"{base}/api/brief/resume", timeout=5,
                )
                assert False, "Expected 400"
            except urllib.error.HTTPError as e:
                assert e.code == 400
            print("PASS HTTP save/resume end-to-end + 404 + 400")
        finally:
            srv.shutdown()
            srv.server_close()
    finally:
        _cleanup(path)


def test_http_save_uses_request_host_for_resume_url():
    """Resume URL built from Host header, not hardcoded."""
    import threading
    import urllib.request
    from http.server import HTTPServer
    from buildemup.api.server import BriefCaptureHandler

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    _reset_api_storage(path)
    try:
        srv = HTTPServer(("127.0.0.1", 0), BriefCaptureHandler)
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
        try:
            base = f"http://127.0.0.1:{port}"
            req = urllib.request.Request(
                f"{base}/api/brief/save",
                data=json.dumps({"x": 1}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                body = json.loads(r.read())
            # Host header in the request gets used to build resume URL
            assert f"127.0.0.1:{port}" in body["resume_url"]
            print(f"PASS resume URL uses request Host: "
                  f"{body['resume_url']}")
        finally:
            srv.shutdown()
            srv.server_close()
    finally:
        _cleanup(path)


# ─────────────────────────────────────────────────────────────────────────
# Frontend JS checks
# ─────────────────────────────────────────────────────────────────────────

def test_frontend_js_has_server_save_logic():
    """brief_form.js now uses /api/brief/save and /api/brief/resume."""
    from pathlib import Path
    js_path = Path(__file__).parent.parent / "static" / "brief_form.js"
    js = js_path.read_text()
    # Server endpoints referenced
    assert "/api/brief/save" in js
    assert "/api/brief/resume" in js
    # Async functions present
    assert "saveToServer" in js
    assert "resumeFromServer" in js
    # Fallback to localStorage still exists
    assert "localStorage" in js
    # Cross-device messaging in disclosure
    assert "any device" in js.lower() or "cross" in js.lower()
    print("PASS frontend JS wired to server save/resume")


def test_frontend_html_save_disclosure_updated():
    """Form HTML disclosure no longer says 'browser only'."""
    from pathlib import Path
    html_path = Path(__file__).parent.parent / "static" / "brief_form.html"
    # S55 fix (same family as S54-005): explicit UTF-8 — Windows
    # defaults to cp1252 and the file contains UTF-8 emoji bytes.
    html = html_path.read_text(encoding="utf-8")
    # Old phrasing should be gone
    assert "browser only" not in html
    # New phrasing
    assert "any device" in html or "30 days" in html
    print("PASS form HTML disclosure updated (no longer 'browser only')")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 1 v0.9 Session B — Server-side save/resume")
    print("=" * 70)
    print()
    print("--- Storage layer ---")
    test_storage_save_and_resume()
    test_storage_token_format()
    test_storage_existing_token_updates_in_place()
    test_storage_unknown_token_raises()
    test_storage_invalid_token_format_raises()
    test_storage_payload_too_large_rejected()
    test_storage_ttl_expiry()
    test_storage_delete()
    test_storage_count_and_prune_expired()
    print()
    print("--- API layer ---")
    test_api_save_endpoint_returns_token_and_url()
    test_api_save_rejects_bad_json()
    test_api_save_rejects_non_dict_body()
    test_api_save_too_large_payload()
    test_api_resume_roundtrip()
    test_api_resume_unknown_token_404()
    test_api_resume_missing_token_400()
    test_api_save_with_existing_token_updates_in_place()
    print()
    print("--- HTTP end-to-end ---")
    test_http_save_resume_end_to_end()
    test_http_save_uses_request_host_for_resume_url()
    print()
    print("--- Frontend ---")
    test_frontend_js_has_server_save_logic()
    test_frontend_html_save_disclosure_updated()
    print()
    print("=" * 70)
    print("ALL V0.9 SESSION B TESTS PASSED")
    print("=" * 70)
