import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.admin_auth import expected_admin_token, require_admin


class AdminAuthTest(unittest.IsolatedAsyncioTestCase):
    def test_expected_token_uses_debug_default(self):
        with patch("app.core.admin_auth.settings.admin_api_token", ""), patch(
            "app.core.admin_auth.settings.debug",
            True,
        ):
            self.assertEqual(expected_admin_token(), "dev-admin-token")

    async def test_require_admin_accepts_valid_token(self):
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="secret-admin",
        )
        with patch("app.core.admin_auth.settings.admin_api_token", "secret-admin"):
            await require_admin(credentials)

    async def test_require_admin_rejects_invalid_token(self):
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="wrong",
        )
        with patch("app.core.admin_auth.settings.admin_api_token", "secret-admin"):
            with self.assertRaises(HTTPException) as ctx:
                await require_admin(credentials)

        self.assertEqual(ctx.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
