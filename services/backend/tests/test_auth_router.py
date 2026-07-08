import unittest
from datetime import date
from unittest.mock import patch

from fastapi import HTTPException

from app.routers.auth import (
    RegisterRequest,
    UpdateSettingsRequest,
    _is_at_least_age,
    register,
    update_settings,
)


class FakeResult:
    def __init__(self, scalar_value=None):
        self._scalar_value = scalar_value

    def scalar_one_or_none(self):
        return self._scalar_value


class FakeDb:
    def __init__(self, *results):
        self._results = list(results)
        self.added = []
        self.flushed = False
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return self._results.pop(0) if self._results else FakeResult()

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flushed = True


class AuthRouterTest(unittest.IsolatedAsyncioTestCase):
    def test_age_helper_accepts_exactly_18(self):
        self.assertTrue(
            _is_at_least_age(
                birth_date=date(2008, 7, 7),
                today=date(2026, 7, 7),
                minimum_age=18,
            )
        )

    def test_age_helper_rejects_one_day_under_18(self):
        self.assertFalse(
            _is_at_least_age(
                birth_date=date(2008, 7, 8),
                today=date(2026, 7, 7),
                minimum_age=18,
            )
        )

    async def test_register_requires_birth_date(self):
        db = FakeDb()

        with self.assertRaises(HTTPException) as ctx:
            await register(
                RegisterRequest(
                    email="missing-birth@example.test",
                    nickname="Missing Birth",
                    password="Secret123!",
                ),
                db=db,
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("18", ctx.exception.detail)
        self.assertEqual(db.statements, [])
        self.assertEqual(db.added, [])

    async def test_register_rejects_under_18(self):
        db = FakeDb()

        with self.assertRaises(HTTPException) as ctx:
            await register(
                RegisterRequest(
                    email="underage@example.test",
                    nickname="Underage",
                    password="Secret123!",
                    birth_date=date(2010, 1, 1),
                ),
                db=db,
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("18", ctx.exception.detail)
        self.assertEqual(db.statements, [])
        self.assertEqual(db.added, [])

    async def test_register_stores_only_age_verification_metadata(self):
        db = FakeDb(FakeResult())

        with patch("app.routers.auth.hash_password", return_value="hashed"), patch(
            "app.routers.auth.create_access_token",
            return_value="token",
        ):
            response = await register(
                RegisterRequest(
                    email="adult@example.test",
                    nickname="Adult",
                    password="Secret123!",
                    birth_date=date(1990, 1, 1),
                ),
                db=db,
            )

        self.assertEqual(response.access_token, "token")
        self.assertTrue(db.flushed)
        self.assertEqual(len(db.added), 1)

        user = db.added[0]
        self.assertEqual(user.email, "adult@example.test")
        self.assertEqual(user.settings["age_verified"], True)
        self.assertEqual(user.settings["birth_year"], 1990)
        self.assertEqual(user.settings["age_verification_method"], "birth_date")
        self.assertIn("age_verified_at", user.settings)
        self.assertNotIn("birth_date", user.settings)
        self.assertNotIn("birthday", user.settings)

    async def test_auth_settings_update_preserves_age_verification_metadata(self):
        user = db_user = type(
            "FakeUser",
            (),
            {
                "settings": {
                    "age_verified": True,
                    "age_verified_at": "2026-07-07T00:00:00+00:00",
                    "age_verification_method": "birth_date",
                    "birth_year": 1990,
                    "memory_enabled": True,
                }
            },
        )()
        db = FakeDb()

        response = await update_settings(
            data=UpdateSettingsRequest(
                settings={
                    "age_verified": False,
                    "age_verified_at": "tampered",
                    "age_verification_method": "manual",
                    "birth_year": 2020,
                    "memory_enabled": False,
                }
            ),
            user=user,
            db=db,
        )

        self.assertIs(user, db_user)
        self.assertTrue(db.flushed)
        self.assertEqual(user.settings["age_verified"], True)
        self.assertEqual(user.settings["age_verified_at"], "2026-07-07T00:00:00+00:00")
        self.assertEqual(user.settings["age_verification_method"], "birth_date")
        self.assertEqual(user.settings["birth_year"], 1990)
        self.assertEqual(user.settings["memory_enabled"], False)
        self.assertEqual(response["settings"], user.settings)


if __name__ == "__main__":
    unittest.main()
