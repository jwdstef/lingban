import unittest
import uuid
import base64
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from app.models.push import PushDelivery
from app.services.push_service import PushGateway


@dataclass
class FakeUser:
    id: uuid.UUID
    settings: dict


@dataclass
class FakeMessage:
    created_at: datetime


class FakeScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeResult:
    def __init__(self, scalars):
        self._scalars = scalars

    def scalars(self):
        return FakeScalars(self._scalars)

    def scalar_one_or_none(self):
        if isinstance(self._scalars, list):
            return self._scalars[0] if self._scalars else None
        return self._scalars


class FakeDb:
    def __init__(self, scalars):
        self._scalars = scalars

    async def execute(self, statement):
        return FakeResult(self._scalars)


class SequenceDb:
    def __init__(self, results):
        self._results = list(results)
        self.added = []

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid.uuid4()

    async def execute(self, statement):
        if not self._results:
            return FakeResult([])
        return FakeResult(self._results.pop(0))


class FakeSettings:
    jpush_app_key = ""
    jpush_master_secret = ""
    jpush_api_url = "https://api.jpush.cn/v3/push"
    fcm_service_account_path = ""
    fcm_project_id = ""
    fcm_oauth_token_url = "https://oauth2.googleapis.com/token"
    fcm_scope = "https://www.googleapis.com/auth/firebase.messaging"
    apns_key_id = ""
    apns_team_id = ""
    apns_bundle_id = ""
    apns_private_key_path = ""
    apns_use_sandbox = True


class FakeHttpResponse:
    def __init__(self, status_code=200, data=None, headers=None, text=None):
        self.status_code = status_code
        self._data = data or {}
        self.headers = headers or {}
        self.text = text if text is not None else json.dumps(self._data)

    def json(self):
        return self._data


class FakeHttpClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, **kwargs):
        self.requests.append({"url": url, **kwargs})
        if not self.responses:
            raise AssertionError("unexpected HTTP POST")
        return self.responses.pop(0)


def _client_factory(client):
    def factory(**kwargs):
        client.factory_kwargs = kwargs
        return client

    return factory


class PushGatewayTest(unittest.IsolatedAsyncioTestCase):
    def test_push_disabled_respects_global_and_frequency_switches(self):
        gateway = PushGateway()
        user_id = uuid.uuid4()

        self.assertTrue(
            gateway._is_push_disabled(
                FakeUser(id=user_id, settings={"push_enabled": False})
            )
        )
        self.assertTrue(
            gateway._is_push_disabled(
                FakeUser(id=user_id, settings={"proactive_level": "off"})
            )
        )
        self.assertFalse(
            gateway._is_push_disabled(
                FakeUser(id=user_id, settings={"proactive_level": "medium"})
            )
        )

    def test_dnd_window_handles_midnight_crossing(self):
        gateway = PushGateway()
        user = FakeUser(
            id=uuid.uuid4(),
            settings={
                "dnd_enabled": True,
                "dnd_start": "23:00",
                "dnd_end": "08:00",
            },
        )

        self.assertTrue(gateway._is_dnd_time(user, now=datetime(2026, 7, 7, 23, 30)))
        self.assertTrue(gateway._is_dnd_time(user, now=datetime(2026, 7, 7, 7, 30)))
        self.assertFalse(gateway._is_dnd_time(user, now=datetime(2026, 7, 7, 12, 0)))

    async def test_rate_limit_uses_frequency_daily_cap(self):
        gateway = PushGateway()
        now = datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc)
        user = FakeUser(id=uuid.uuid4(), settings={"proactive_level": "quiet"})
        db = FakeDb([FakeMessage(created_at=now - timedelta(hours=20))])

        error = await gateway._rate_limit_error(user, db, now=now)

        self.assertEqual(error, "超过每日主动关怀限制")

    async def test_rate_limit_uses_frequency_cooldown(self):
        gateway = PushGateway()
        now = datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc)
        user = FakeUser(id=uuid.uuid4(), settings={"proactive_level": "medium"})
        db = FakeDb([FakeMessage(created_at=now - timedelta(hours=2))])

        error = await gateway._rate_limit_error(user, db, now=now)

        self.assertEqual(error, "主动关怀冷却中")

    async def test_rate_limit_allows_after_cooldown_and_under_cap(self):
        gateway = PushGateway()
        now = datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc)
        user = FakeUser(id=uuid.uuid4(), settings={"proactive_level": "high"})
        db = FakeDb([FakeMessage(created_at=now - timedelta(hours=5))])

        error = await gateway._rate_limit_error(user, db, now=now)

        self.assertIsNone(error)

    async def test_send_writes_delivery_for_each_active_token(self):
        gateway = PushGateway()
        user = SimpleNamespace(
            id=uuid.uuid4(),
            settings={"dnd_enabled": False, "proactive_level": "high"},
            push_token=None,
            push_platform=None,
        )
        tokens = [
            SimpleNamespace(id=uuid.uuid4(), provider="jpush", token="token-a"),
            SimpleNamespace(id=uuid.uuid4(), provider="fcm", token="token-b"),
        ]
        db = SequenceDb([user, [], [], tokens])
        sent = []

        async def fake_do_send(token, platform, title, body, deep_link):
            sent.append((token, platform, title, body, deep_link))

        with patch.object(gateway, "_do_send", side_effect=fake_do_send):
            message = await gateway.send(
                user_id=user.id,
                character_id="yinyue",
                trigger_type="time_morning",
                content="早，今天也别硬撑。",
                db=db,
            )

        deliveries = [item for item in db.added if isinstance(item, PushDelivery)]
        self.assertEqual(message.push_status, "sent")
        self.assertTrue(message.delivered)
        self.assertEqual(len(sent), 2)
        self.assertEqual(len(deliveries), 2)
        self.assertEqual([delivery.status for delivery in deliveries], ["sent", "sent"])
        self.assertEqual(
            {delivery.push_token_id for delivery in deliveries},
            {tokens[0].id, tokens[1].id},
        )

    async def test_send_records_failed_delivery_when_no_token_exists(self):
        gateway = PushGateway()
        user = SimpleNamespace(
            id=uuid.uuid4(),
            settings={"dnd_enabled": False, "proactive_level": "high"},
            push_token=None,
            push_platform=None,
        )
        db = SequenceDb([user, [], [], []])

        message = await gateway.send(
            user_id=user.id,
            character_id="yinyue",
            trigger_type="silence",
            content="好几天没聊了，还好吗？",
            db=db,
        )

        deliveries = [item for item in db.added if isinstance(item, PushDelivery)]
        self.assertEqual(message.push_status, "failed")
        self.assertEqual(message.push_error, "用户未注册推送 Token")
        self.assertEqual(len(deliveries), 1)
        self.assertEqual(deliveries[0].provider, "none")
        self.assertEqual(deliveries[0].status, "failed")
        self.assertEqual(deliveries[0].failure_reason, "用户未注册推送 Token")

    async def test_send_stores_provider_message_id(self):
        gateway = PushGateway()
        user = SimpleNamespace(
            id=uuid.uuid4(),
            settings={"dnd_enabled": False, "proactive_level": "high"},
            push_token=None,
            push_platform=None,
        )
        token = SimpleNamespace(id=uuid.uuid4(), provider="jpush", token="token-a")
        db = SequenceDb([user, [], [], [token]])

        async def fake_do_send(token, platform, title, body, deep_link):
            return "provider-message-id"

        with patch.object(gateway, "_do_send", side_effect=fake_do_send):
            await gateway.send(
                user_id=user.id,
                character_id="yinyue",
                trigger_type="time_morning",
                content="早，今天也别硬撑。",
                db=db,
            )

        deliveries = [item for item in db.added if isinstance(item, PushDelivery)]
        self.assertEqual(deliveries[0].provider_message_id, "provider-message-id")

    async def test_jpush_uses_rest_api_when_configured(self):
        settings = FakeSettings()
        settings.jpush_app_key = "app-key"
        settings.jpush_master_secret = "master-secret"
        client = FakeHttpClient(
            [FakeHttpResponse(data={"msg_id": "jpush-message-id"})]
        )
        gateway = PushGateway(
            config=settings,
            http_client_factory=_client_factory(client),
        )

        message_id = await gateway._send_jpush(
            "registration-token",
            "银月",
            "早，今天也别硬撑。",
            "lingban://chat/yinyue",
        )

        request = client.requests[0]
        expected_auth = base64.b64encode(b"app-key:master-secret").decode("ascii")
        self.assertEqual(message_id, "jpush-message-id")
        self.assertEqual(request["url"], "https://api.jpush.cn/v3/push")
        self.assertEqual(request["headers"]["Authorization"], f"Basic {expected_auth}")
        self.assertEqual(
            request["json"]["audience"]["registration_id"],
            ["registration-token"],
        )
        self.assertEqual(request["json"]["notification"]["android"]["title"], "银月")

    async def test_fcm_uses_http_v1_with_service_account(self):
        with tempfile.TemporaryDirectory() as tmp:
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            service_account = {
                "project_id": "lingban-prod",
                "client_email": "push@lingban-prod.iam.gserviceaccount.com",
                "private_key": private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                ).decode("utf-8"),
            }
            service_account_path = Path(tmp) / "firebase-service-account.json"
            service_account_path.write_text(json.dumps(service_account), encoding="utf-8")

            settings = FakeSettings()
            settings.fcm_service_account_path = str(service_account_path)
            client = FakeHttpClient(
                [
                    FakeHttpResponse(data={"access_token": "oauth-token"}),
                    FakeHttpResponse(
                        data={
                            "name": (
                                "projects/lingban-prod/messages/fcm-message-id"
                            )
                        }
                    ),
                ]
            )
            gateway = PushGateway(
                config=settings,
                http_client_factory=_client_factory(client),
                timestamp_factory=lambda: 1780000000,
            )

            message_id = await gateway._send_fcm(
                "fcm-token",
                "银月",
                "早，今天也别硬撑。",
                "lingban://chat/yinyue",
            )

        token_request = client.requests[0]
        send_request = client.requests[1]
        self.assertEqual(message_id, "projects/lingban-prod/messages/fcm-message-id")
        self.assertEqual(token_request["url"], settings.fcm_oauth_token_url)
        self.assertEqual(
            token_request["data"]["grant_type"],
            "urn:ietf:params:oauth:grant-type:jwt-bearer",
        )
        self.assertIn("assertion", token_request["data"])
        self.assertEqual(
            send_request["url"],
            "https://fcm.googleapis.com/v1/projects/lingban-prod/messages:send",
        )
        self.assertEqual(send_request["headers"]["Authorization"], "Bearer oauth-token")
        self.assertEqual(send_request["json"]["message"]["token"], "fcm-token")

    async def test_apns_uses_provider_token_and_device_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            private_key = ec.generate_private_key(ec.SECP256R1())
            private_key_path = Path(tmp) / "AuthKey_ABC123DEFG.p8"
            private_key_path.write_bytes(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

            settings = FakeSettings()
            settings.apns_key_id = "ABC123DEFG"
            settings.apns_team_id = "TEAM123456"
            settings.apns_bundle_id = "com.lingban.mobile"
            settings.apns_private_key_path = str(private_key_path)
            settings.apns_use_sandbox = True
            client = FakeHttpClient(
                [FakeHttpResponse(headers={"apns-id": "apns-message-id"})]
            )
            gateway = PushGateway(
                config=settings,
                http_client_factory=_client_factory(client),
                timestamp_factory=lambda: 1780000000,
            )

            message_id = await gateway._send_apns(
                "apns-device-token",
                "银月",
                "早，今天也别硬撑。",
                "lingban://chat/yinyue",
            )

        request = client.requests[0]
        self.assertEqual(message_id, "apns-message-id")
        self.assertEqual(
            request["url"],
            "https://api.sandbox.push.apple.com/3/device/apns-device-token",
        )
        self.assertEqual(request["headers"]["apns-topic"], "com.lingban.mobile")
        self.assertEqual(request["headers"]["apns-push-type"], "alert")
        self.assertTrue(request["headers"]["authorization"].startswith("bearer "))


if __name__ == "__main__":
    unittest.main()
