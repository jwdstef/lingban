import unittest
import uuid
from dataclasses import dataclass, field

from app.routers.settings import UpdateSettingsRequest, update_settings


@dataclass
class FakeUser:
    id: uuid.UUID
    settings: dict = field(default_factory=dict)


class FakeDb:
    def __init__(self):
        self.flushed = False

    async def flush(self):
        self.flushed = True


class SettingsRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_update_settings_preserves_age_verification_metadata(self):
        user = FakeUser(
            id=uuid.uuid4(),
            settings={
                "age_verified": True,
                "age_verified_at": "2026-07-07T00:00:00+00:00",
                "age_verification_method": "birth_date",
                "birth_year": 1990,
                "push_enabled": True,
            },
        )
        db = FakeDb()

        response = await update_settings(
            data=UpdateSettingsRequest(
                settings={
                    "age_verified": False,
                    "age_verified_at": "tampered",
                    "age_verification_method": "manual",
                    "birth_year": 2020,
                    "push_enabled": False,
                }
            ),
            user=user,
            db=db,
        )

        self.assertTrue(db.flushed)
        self.assertEqual(user.settings["age_verified"], True)
        self.assertEqual(user.settings["age_verified_at"], "2026-07-07T00:00:00+00:00")
        self.assertEqual(user.settings["age_verification_method"], "birth_date")
        self.assertEqual(user.settings["birth_year"], 1990)
        self.assertEqual(user.settings["push_enabled"], False)
        self.assertEqual(response["settings"], user.settings)


if __name__ == "__main__":
    unittest.main()
