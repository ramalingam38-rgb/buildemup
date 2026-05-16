"""S7b § 8.1 + § 9.7 — Startup config validation (P32) tests.

Two tests covering the exit-vs-warn behavior of `_validate_config()`:
prod mode must `sys.exit(1)` on failure; non-prod must continue with
WARNING logs.
"""
from __future__ import annotations

import logging
import os
import unittest

from buildemup.api import server as server_mod


class _CapturingHandler(logging.Handler):
    """Logging handler that appends formatted records to a list."""

    def __init__(self):
        super().__init__()
        self.records: list[str] = []
        self.setFormatter(logging.Formatter("%(levelname)s|%(message)s"))

    def emit(self, record):
        self.records.append(self.format(record))


class TestConfigValidationProd(unittest.TestCase):
    """P32 prod mode: missing required env vars MUST sys.exit(1)."""

    def setUp(self):
        # Snapshot env we'll mutate
        self._snapshot = {
            k: os.environ.get(k) for k in (
                "BUILDEMUP_ENV", "RESEND_API_KEY",
                "BUILDEMUP_DATABASE_PATH", "BUILDEMUP_ADMIN_TOKEN",
            )
        }
        self.handler = _CapturingHandler()
        self.handler.setLevel(logging.DEBUG)
        logging.getLogger("buildemup.api.server").addHandler(self.handler)
        logging.getLogger("buildemup.api.server").setLevel(logging.DEBUG)

    def tearDown(self):
        for k, v in self._snapshot.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        logging.getLogger("buildemup.api.server").removeHandler(self.handler)

    def test_prod_missing_required_env_calls_sys_exit_1(self):
        """In prod, missing RESEND_API_KEY must terminate the process.

        Railway treats sys.exit(1) on container start as a failed
        deploy and routes no traffic — that's the desired outcome.
        """
        os.environ["BUILDEMUP_ENV"] = "prod"
        os.environ.pop("RESEND_API_KEY", None)
        # Set the others so this is the ONE failure
        os.environ["BUILDEMUP_DATABASE_PATH"] = "/tmp/test.db"
        os.environ["BUILDEMUP_ADMIN_TOKEN"] = "x" * 32

        with self.assertRaises(SystemExit) as cm:
            server_mod._validate_config()
        self.assertEqual(cm.exception.code, 1)

        # ERROR-level log line for the missing var
        errors = [r for r in self.handler.records
                  if r.startswith("ERROR")]
        self.assertTrue(
            any("RESEND_API_KEY missing" in r for r in errors),
            f"expected RESEND_API_KEY error in logs; got {errors!r}",
        )


class TestConfigValidationNonProd(unittest.TestCase):
    """P32 non-prod: missing required env vars must NOT exit."""

    def setUp(self):
        self._snapshot = {
            k: os.environ.get(k) for k in (
                "BUILDEMUP_ENV", "RESEND_API_KEY",
                "BUILDEMUP_DATABASE_PATH", "BUILDEMUP_ADMIN_TOKEN",
            )
        }
        self.handler = _CapturingHandler()
        self.handler.setLevel(logging.DEBUG)
        logging.getLogger("buildemup.api.server").addHandler(self.handler)
        logging.getLogger("buildemup.api.server").setLevel(logging.DEBUG)

    def tearDown(self):
        for k, v in self._snapshot.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        logging.getLogger("buildemup.api.server").removeHandler(self.handler)

    def test_dev_missing_env_logs_warning_does_not_exit(self):
        """Local dev shouldn't be blocked by production-only secrets."""
        os.environ["BUILDEMUP_ENV"] = "dev"
        os.environ.pop("RESEND_API_KEY", None)
        os.environ.pop("BUILDEMUP_DATABASE_PATH", None)
        os.environ.pop("BUILDEMUP_ADMIN_TOKEN", None)

        # Must NOT raise SystemExit
        server_mod._validate_config()  # raises if assertion fails

        # WARNING-level lines for each missing var
        warnings = [r for r in self.handler.records
                    if r.startswith("WARNING")]
        self.assertTrue(
            any("RESEND_API_KEY missing" in r for r in warnings),
            f"expected RESEND_API_KEY warning; got {warnings!r}",
        )
        self.assertTrue(
            any("non-fatal" in r for r in warnings),
            "expected 'non-fatal' marker in WARNING messages",
        )


if __name__ == "__main__":
    unittest.main()
