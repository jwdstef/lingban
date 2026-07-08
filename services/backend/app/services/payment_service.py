from __future__ import annotations

import base64
import json
import secrets
import time
from pathlib import Path
from typing import Any, Callable, Mapping

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.x509 import load_pem_x509_certificate

from app.core.config import settings


class PaymentProviderError(RuntimeError):
    """Raised when the upstream payment provider rejects or fails a request."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class PaymentNotificationError(RuntimeError):
    """Raised when a payment notification cannot be trusted or decrypted."""


class PaymentService:
    def __init__(
        self,
        config=settings,
        http_client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
        timestamp_factory: Callable[[], str] | None = None,
        nonce_factory: Callable[[], str] | None = None,
    ):
        self.config = config
        self.http_client_factory = http_client_factory
        self.timestamp_factory = timestamp_factory or (lambda: str(int(time.time())))
        self.nonce_factory = nonce_factory or (lambda: secrets.token_hex(16))
        self._private_key = None
        self._platform_public_key = None

    def is_configured(self) -> bool:
        return all(
            bool(str(getattr(self.config, field, "")).strip())
            for field in (
                "wechat_pay_app_id",
                "wechat_pay_mch_id",
                "wechat_pay_merchant_serial_no",
                "wechat_pay_api_v3_key",
                "wechat_pay_private_key_path",
                "wechat_pay_notify_url",
            )
        )

    def is_notification_verification_configured(self) -> bool:
        return bool(
            str(getattr(self.config, "wechat_pay_platform_public_key_path", "")).strip()
        )

    def build_request_authorization(
        self,
        method: str,
        url_path: str,
        body: str,
        timestamp: str | None = None,
        nonce: str | None = None,
    ) -> str:
        timestamp = timestamp or self.timestamp_factory()
        nonce = nonce or self.nonce_factory()
        message = f"{method.upper()}\n{url_path}\n{timestamp}\n{nonce}\n{body}\n"
        signature = self._sign(message.encode("utf-8"))
        return (
            "WECHATPAY2-SHA256-RSA2048 "
            f'mchid="{self.config.wechat_pay_mch_id}",'
            f'nonce_str="{nonce}",'
            f'signature="{signature}",'
            f'timestamp="{timestamp}",'
            f'serial_no="{self.config.wechat_pay_merchant_serial_no}"'
        )

    def build_app_payment_params(self, prepay_id: str) -> dict[str, str]:
        timestamp = self.timestamp_factory()
        nonce = self.nonce_factory()
        message = (
            f"{self.config.wechat_pay_app_id}\n{timestamp}\n{nonce}\n{prepay_id}\n"
        )
        signature = self._sign(message.encode("utf-8"))
        return {
            "appid": self.config.wechat_pay_app_id,
            "partnerid": self.config.wechat_pay_mch_id,
            "prepayid": prepay_id,
            "package": "Sign=WXPay",
            "noncestr": nonce,
            "timestamp": timestamp,
            "sign": signature,
            "sign_type": "RSA",
        }

    async def create_app_prepay_order(
        self,
        *,
        description: str,
        out_trade_no: str,
        amount_cents: int,
        currency: str = "CNY",
        attach: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise PaymentProviderError("WeChat Pay is not fully configured")

        url_path = "/v3/pay/transactions/app"
        request_body: dict[str, Any] = {
            "appid": self.config.wechat_pay_app_id,
            "mchid": self.config.wechat_pay_mch_id,
            "description": description[:127],
            "out_trade_no": out_trade_no,
            "notify_url": self.config.wechat_pay_notify_url,
            "amount": {
                "total": amount_cents,
                "currency": currency,
            },
        }
        if attach:
            request_body["attach"] = attach[:128]

        body = json.dumps(request_body, ensure_ascii=False, separators=(",", ":"))
        authorization = self.build_request_authorization("POST", url_path, body)
        url = f"{self.config.wechat_pay_api_base_url.rstrip('/')}{url_path}"
        async with self.http_client_factory(timeout=15.0) as client:
            response = await client.post(
                url,
                content=body.encode("utf-8"),
                headers={
                    "Accept": "application/json",
                    "Authorization": authorization,
                    "Content-Type": "application/json",
                },
            )

        response_text = response.text
        if response.status_code < 200 or response.status_code >= 300:
            raise PaymentProviderError(
                "WeChat Pay order creation failed",
                status_code=response.status_code,
                response_body=response_text,
            )

        try:
            response_body = response.json()
        except json.JSONDecodeError as exc:
            raise PaymentProviderError("WeChat Pay returned invalid JSON") from exc

        prepay_id = str(response_body.get("prepay_id") or "")
        if not prepay_id:
            raise PaymentProviderError("WeChat Pay response missing prepay_id")

        return {
            "prepay_id": prepay_id,
            "payment_params": self.build_app_payment_params(prepay_id),
            "raw_request": request_body,
            "raw_response": response_body,
        }

    def parse_payment_notification(
        self,
        body: bytes | str,
        headers: Mapping[str, str],
    ) -> dict[str, Any]:
        body_text = body.decode("utf-8") if isinstance(body, bytes) else body
        timestamp = self._header(headers, "Wechatpay-Timestamp")
        nonce = self._header(headers, "Wechatpay-Nonce")
        signature = self._header(headers, "Wechatpay-Signature")
        if not timestamp or not nonce or not signature:
            raise PaymentNotificationError("Missing WeChat Pay notification signature")

        self.verify_notification_signature(
            timestamp=timestamp,
            nonce=nonce,
            body=body_text,
            signature=signature,
        )

        try:
            notification = json.loads(body_text)
        except json.JSONDecodeError as exc:
            raise PaymentNotificationError("Invalid WeChat Pay notification JSON") from exc

        resource = notification.get("resource")
        if not isinstance(resource, dict):
            raise PaymentNotificationError("Missing WeChat Pay notification resource")
        return self.decrypt_notification_resource(resource)

    def verify_notification_signature(
        self,
        *,
        timestamp: str,
        nonce: str,
        body: str,
        signature: str,
    ) -> None:
        if not self.is_notification_verification_configured():
            raise PaymentNotificationError(
                "WeChat Pay platform public key is not configured"
            )
        message = f"{timestamp}\n{nonce}\n{body}\n".encode("utf-8")
        try:
            self._load_platform_public_key().verify(
                base64.b64decode(signature),
                message,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except (InvalidSignature, ValueError) as exc:
            raise PaymentNotificationError("Invalid WeChat Pay notification signature") from exc

    def decrypt_notification_resource(self, resource: Mapping[str, Any]) -> dict[str, Any]:
        key = str(getattr(self.config, "wechat_pay_api_v3_key", "")).encode("utf-8")
        if len(key) != 32:
            raise PaymentNotificationError("WeChat Pay API v3 key must be 32 bytes")

        try:
            decrypted = AESGCM(key).decrypt(
                str(resource["nonce"]).encode("utf-8"),
                base64.b64decode(str(resource["ciphertext"])),
                str(resource.get("associated_data", "")).encode("utf-8"),
            )
            return json.loads(decrypted.decode("utf-8"))
        except Exception as exc:
            raise PaymentNotificationError(
                "Failed to decrypt WeChat Pay notification resource"
            ) from exc

    def _sign(self, message: bytes) -> str:
        signature = self._load_private_key().sign(
            message,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("ascii")

    def _load_private_key(self):
        if self._private_key is None:
            private_key_path = Path(self.config.wechat_pay_private_key_path)
            self._private_key = serialization.load_pem_private_key(
                private_key_path.read_bytes(),
                password=None,
            )
        return self._private_key

    def _load_platform_public_key(self):
        if self._platform_public_key is None:
            public_key_path = Path(self.config.wechat_pay_platform_public_key_path)
            data = public_key_path.read_bytes()
            if b"BEGIN CERTIFICATE" in data:
                self._platform_public_key = load_pem_x509_certificate(data).public_key()
            else:
                self._platform_public_key = serialization.load_pem_public_key(data)
        return self._platform_public_key

    def _header(self, headers: Mapping[str, str], name: str) -> str:
        lower = name.lower()
        for key, value in headers.items():
            if key.lower() == lower:
                return value
        return ""


payment_service = PaymentService()
