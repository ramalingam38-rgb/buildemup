"""B-062 (S55): prod + C3A_TEST_MODE=1 startup cross-check.

When BUILDEMUP_ENV=prod and C3A_TEST_MODE=1 are both set, the server
MUST refuse to start: test mode exposes /c3a/_test_harness.html AND
disables the c3aFetch 503 auto-retry path. Either alone is fine in
dev; both in prod is a deploy misconfiguration that must fail fast
so the container is marked unhealthy rather than serving real users.
"""
from __future__ import annotations

import logging
import os
import tempfile
import unittest

from buildemup.api import server as server_mod


class _CapturingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records: list[str] = []
        self.setFormatter(logging.Formatter("%(levelname)s|%(message)s"))

    def emit(self, record):
        self.records.append(self.format(record))


class _EnvSnapshot:
    """Snapshot + restore env vars across a test."""

    _KEYS = (
        "BUILDEMUP_ENV",
        "RESEND_API_KEY",
        "BUILDEMUP_DATABASE_PATH",
        "BUILDEMUP_ADMIN_TOKEN",
        "BUILDEMUP_PUBLIC_URL",
        "C3A_TEST_MODE",
    )

    def __init__(self):
        self._snapshot = {k: os.environ.get(k) for k in self._KEYS}

    def restore(self):
        for k, v in self._snapshot.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _set_prod_required_env():
    """Populate the other _PROD_REQUIRED entries so they don't fail."""
    os.environ["RESEND_API_KEY"] = "x" * 32
    os.environ["BUILDEMUP_DATABASE_PATH"] = os.path.join(
        tempfile.gettempdir(), "buildemup_b062_test.db"
    )
    os.environ["BUILDEMUP_ADMIN_TOKEN"] = "y" * 32
    os.environ["BUILDEMUP_PUBLIC_URL"] = "https://example.test"


class TestB062ProdTestModeCrosscheck(unittest.TestCase):
    """B-062 — prod + test-mode is a forbidden combination."""

    def setUp(self):
        self._env = _EnvSnapshot()
        self.handler = _CapturingHandler()
        self.handler.setLevel(logging.DEBUG)
        logger = logging.getLogger("buildemup.api.server")
        logger.addHandler(self.handler)
        logger.setLevel(logging.DEBUG)

    def tearDown(self):
        self._env.restore()
        logging.getLogger("buildemup.api.server").removeHandler(self.handler)

    def test_prod_plus_test_mode_sys_exits(self):
        """BUILDEMUP_ENV=prod + C3A_TEST_MODE=1 must sys.exit(1)."""
        os.environ["BUILDEMUP_ENV"] = "prod"
        os.environ["C3A_TEST_MODE"] = "1"
        _set_prod_required_env()

        with self.assertRaises(SystemExit) as cm:
            server_mod._validate_config()
        self.assertEqual(cm.exception.code, 1)

        errors = [r for r in self.handler.records if r.startswith("ERROR")]
        self.assertTrue(
            any("C3A_TEST_MODE" in r and "forbidden" in r for r in errors),
            f"expected C3A_TEST_MODE forbidden error; got {errors!r}",
        )

    def test_prod_without_test_mode_does_not_exit(self):
        """Prod without test mode passes the cross-check (other checks
        may still fail; we set required env to keep this isolated)."""
        os.environ["BUILDEMUP_ENV"] = "prod"
        os.environ.pop("C3A_TEST_MODE", None)
        _set_prod_required_env()

        try:
            server_mod._validate_config()
        except SystemExit:
            self.fail("_validate_config sys.exit'd without C3A_TEST_MODE set")

    def test_dev_plus_test_mode_only_warns(self):
        """Test mode in dev is fine — local harness work needs it.
        Non-prod must NOT sys.exit even with the forbidden combo absent."""
        os.environ["BUILDEMUP_ENV"] = "dev"
        os.environ["C3A_TEST_MODE"] = "1"

        try:
            server_mod._validate_config()
        except SystemExit:
            self.fail("dev + test-mode should not sys.exit")

    def test_prod_test_mode_other_string_value_does_not_trigger(self):
        """Only the exact string '1' triggers test mode; '0', 'true',
        empty string, etc. are not test mode."""
        os.environ["BUILDEMUP_ENV"] = "prod"
        os.environ["C3A_TEST_MODE"] = "0"
        _set_prod_required_env()

        try:
            server_mod._validate_config()
        except SystemExit:
            self.fail("prod + C3A_TEST_MODE=0 should not sys.exit")


if __name__ == "__main__":
    unittest.main()
