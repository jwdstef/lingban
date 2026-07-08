import base64
import json
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.services.payment_service import (
    PaymentNotificationError,
    PaymentService,
)


@dataclass
class FakeSettings:
    wechat_pay_app_id: str = "wx-test-app"
    wechat_pay_mch_id: str = "1900000001"
    wechat_pay_api_v3_key: str = "0123456789abcdef0123456789abcdef"
    wechat_pay_private_key_path: str = ""
    wechat_pay_notify_url: str = "https://example.test/pay/notify"
    wechat_pay_merchant_serial_no: str = "merchant-serial"
    wechat_pay_platform_public_key_path: str = ""


class PaymentServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_key_path = Path(self.temp_dir.name) / "merchant.pem"
        private_key_path.write_bytes(
            self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        public_key_path = Path(self.temp_dir.name) / "platform-public.pem"
        public_key_path.write_bytes(
            self.private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
        self.settings = FakeSettings(
            wechat_pay_private_key_path=str(private_key_path),
            wechat_pay_platform_public_key_path=str(public_key_path),
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_build_request_authorization_header_uses_rsa_signature(self):
        service = PaymentService(
            config=self.settings,
            timestamp_factory=lambda: "1780000000",
            nonce_factory=lambda: "request-nonce",
        )
        body = '{"appid":"wx-test-app"}'

        header = service.build_request_authorization(
            method="POST",
            url_path="/v3/pay/transactions/app",
            body=body,
        )

        self.assertTrue(header.startswith("WECHATPAY2-SHA256-RSA2048 "))
        self.assertIn('mchid="1900000001"', header)
        self.assertIn('serial_no="merchant-serial"', header)
        self.assertIn('nonce_str="request-nonce"', header)
        self.assertIn('timestamp="1780000000"', header)

        signature = header.split('signature="', 1)[1].split('"', 1)[0]
        self.private_key.public_key().verify(
            base64.b64decode(signature),
            b"POST\n/v3/pay/transactions/app\n1780000000\nrequest-nonce\n"
            + body.encode("utf-8")
            + b"\n",
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

    def test_build_app_payment_params_signs_prepay_id(self):
        service = PaymentService(
            config=self.settings,
            timestamp_factory=lambda: "1780000001",
            nonce_factory=lambda: "app-nonce",
        )

        params = service.build_app_payment_params("wx-prepay-id")

        self.assertEqual(params["appid"], "wx-test-app")
        self.assertEqual(params["partnerid"], "1900000001")
        self.assertEqual(params["prepayid"], "wx-prepay-id")
        self.assertEqual(params["package"], "Sign=WXPay")
        self.assertEqual(params["noncestr"], "app-nonce")
        self.assertEqual(params["timestamp"], "1780000001")

        self.private_key.public_key().verify(
            base64.b64decode(params["sign"]),
            b"wx-test-app\n1780000001\napp-nonce\nwx-prepay-id\n",
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

    def test_decrypt_notification_resource_uses_api_v3_key(self):
        service = PaymentService(config=self.settings)
        plaintext = {
            "out_trade_no": "LB202607080001",
            "trade_state": "SUCCESS",
            "transaction_id": "4200000000000000001",
        }
        nonce = b"notify-nonce"
        associated_data = b"transaction"
        ciphertext = AESGCM(self.settings.wechat_pay_api_v3_key.encode("utf-8")).encrypt(
            nonce,
            json.dumps(plaintext).encode("utf-8"),
            associated_data,
        )

        decrypted = service.decrypt_notification_resource(
            {
                "nonce": nonce.decode("utf-8"),
                "associated_data": associated_data.decode("utf-8"),
                "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
            }
        )

        self.assertEqual(decrypted, plaintext)

    def test_verify_notification_signature_rejects_invalid_signature(self):
        service = PaymentService(config=self.settings)

        with self.assertRaises(PaymentNotificationError):
            service.verify_notification_signature(
                timestamp="1780000002",
                nonce="notify-nonce",
                body='{"id":"notification"}',
                signature=base64.b64encode(b"not-a-real-signature").decode("ascii"),
            )


if __name__ == "__main__":
    unittest.main()
