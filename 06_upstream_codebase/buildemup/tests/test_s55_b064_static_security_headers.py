"""B-064 (S55): CSP + Cache-Control + nosniff on static assets.

Spec § 5b.3 already mandates `Cache-Control: no-store, no-cache,
must-revalidate` for /check-init responses; this hardens the static
UI surface served via _serve_static (brief_form.html, /c3a/*.html,
/c3a/*.js, /c3a/*.css, etc.).

The helper `_static_security_headers(ext)` is the unit under test —
we don't need to spin up an HTTPServer to assert correctness.
"""
from __future__ import annotations

import unittest

from buildemup.api.server import (
    _static_security_headers,
    _STATIC_CACHE_CONTROL,
    _STATIC_CSP,
)


class TestB064StaticSecurityHeaders(unittest.TestCase):

    def test_html_gets_no_cache_must_revalidate(self):
        headers = _static_security_headers(".html")
        self.assertEqual(headers["Cache-Control"], "no-cache, must-revalidate")

    def test_js_gets_short_cache_window(self):
        headers = _static_security_headers(".js")
        self.assertEqual(
            headers["Cache-Control"], "public, max-age=300, must-revalidate"
        )

    def test_css_gets_short_cache_window(self):
        headers = _static_security_headers(".css")
        self.assertEqual(
            headers["Cache-Control"], "public, max-age=300, must-revalidate"
        )

    def test_unknown_extension_falls_back_to_no_store(self):
        headers = _static_security_headers(".xyz")
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_csp_is_always_present(self):
        for ext in (".html", ".js", ".css", ".png", ".unknown"):
            headers = _static_security_headers(ext)
            self.assertIn("Content-Security-Policy", headers)
            self.assertEqual(headers["Content-Security-Policy"], _STATIC_CSP)

    def test_csp_denies_third_party_scripts(self):
        """script-src allows 'self' + only the Tailwind Play CDN.

        S59 deploy (Render) relaxed script-src to allow
        https://cdn.tailwindcss.com — the Tailwind Play CDN script
        used by orchestrator_run.html, quote_compare.html, and
        brief_form.html. No other remote scripts permitted; no
        'unsafe-inline' for scripts. (Pre-1.0 we should bundle
        Tailwind and re-tighten to script-src 'self'.)
        """
        self.assertIn("default-src 'self'", _STATIC_CSP)
        self.assertIn("script-src 'self'", _STATIC_CSP)
        # Tailwind Play CDN is the ONLY remote script allowance.
        self.assertIn("https://cdn.tailwindcss.com", _STATIC_CSP)
        # No 'unsafe-inline' for scripts (inline scripts still
        # forbidden — anything that runs must live in a .js file).
        self.assertNotIn("'unsafe-inline' 'self'", _STATIC_CSP.split(";")[1])
        # Defense-in-depth: no other CDN hosts snuck in.
        for forbidden_cdn in (
            "unpkg.com", "jsdelivr.net", "cdnjs.cloudflare.com",
            "ajax.googleapis.com", "code.jquery.com",
        ):
            self.assertNotIn(forbidden_cdn, _STATIC_CSP)

    def test_csp_forbids_framing(self):
        """frame-ancestors 'none' prevents clickjacking via iframe embed."""
        self.assertIn("frame-ancestors 'none'", _STATIC_CSP)

    def test_nosniff_is_always_set(self):
        for ext in (".html", ".js", ".css", ".png"):
            headers = _static_security_headers(ext)
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_referrer_policy_is_strict(self):
        headers = _static_security_headers(".html")
        self.assertEqual(
            headers["Referrer-Policy"], "strict-origin-when-cross-origin"
        )

    def test_cache_table_covers_expected_extensions(self):
        """Sanity check: the explicit Cache-Control table has entries
        for the three extensions we actually serve."""
        for ext in (".html", ".js", ".css"):
            self.assertIn(ext, _STATIC_CACHE_CONTROL)


if __name__ == "__main__":
    unittest.main()
