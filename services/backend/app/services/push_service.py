"""推送通知服务 - Push Gateway"""

import base64
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.memory import ProactiveMessage
from app.models.push import PushDelivery, PushToken
from app.models.user import User


class PushGateway:
    """推送网关 - 统一封装各推送通道"""

    def __init__(
        self,
        config=settings,
        http_client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
        timestamp_factory: Callable[[], int] | None = None,
    ):
        self.config = config
        self.http_client_factory = http_client_factory
        self.timestamp_factory = timestamp_factory or (lambda: int(time.time()))
        self._fcm_access_token: str | None = None
        self._fcm_access_token_expires_at = 0

    async def send(
        self,
        user_id: uuid.UUID,
        character_id: str,
        trigger_type: str,
        content: str,
        db: AsyncSession,
    ) -> ProactiveMessage:
        """发送主动关怀消息"""
        # 1. 创建消息记录
        message = ProactiveMessage(
            user_id=user_id,
            character_id=character_id,
            trigger_type=trigger_type,
            content=content,
            push_status="pending",
        )
        db.add(message)
        await db.flush()

        # 2. 获取用户推送 Token
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        if not user:
            message.push_status = "failed"
            message.push_error = "用户不存在"
            await db.flush()
            return message

        # 3. 检查免打扰
        if self._is_push_disabled(user):
            message.push_status = "failed"
            message.push_error = "主动关怀已关闭"
            await db.flush()
            return message

        if self._is_dnd_time(user):
            message.push_status = "failed"
            message.push_error = "免打扰时段"
            await db.flush()
            return message

        # 4. 检查频控
        rate_limit_error = await self._rate_limit_error(user, db)
        if rate_limit_error:
            message.push_status = "failed"
            message.push_error = rate_limit_error
            await db.flush()
            return message

        if await self._check_rate_limit(user_id, db):
            message.push_status = "failed"
            message.push_error = "超过每日推送限制"
            await db.flush()
            return message

        # 5. 发送推送到当前用户的所有有效设备
        push_targets = await self._push_targets(user, db)
        title = self._get_title(character_id)
        deep_link = f"lingban://chat/{character_id}"
        if not push_targets:
            message.push_status = "failed"
            message.push_error = "用户未注册推送 Token"
            self._add_delivery(
                user_id=user_id,
                push_token_id=None,
                proactive_message_id=message.id,
                provider="none",
                notification_type="proactive",
                title=title,
                body=content,
                deep_link=deep_link,
                status="failed",
                failure_reason=message.push_error,
                db=db,
            )
            await db.flush()
            return message

        sent_count = 0
        failures: list[str] = []
        for target in push_targets:
            delivery = self._add_delivery(
                user_id=user_id,
                push_token_id=target["id"],
                proactive_message_id=message.id,
                provider=target["provider"],
                notification_type="proactive",
                title=title,
                body=content,
                deep_link=deep_link,
                status="pending",
                failure_reason=None,
                db=db,
            )
            try:
                provider_message_id = await self._do_send(
                    token=target["token"],
                    platform=target["provider"],
                    title=title,
                    body=content,
                    deep_link=deep_link,
                )
                delivery.status = "sent"
                delivery.provider_message_id = provider_message_id
                delivery.sent_at = datetime.now(timezone.utc)
                sent_count += 1
            except Exception as e:
                delivery.status = "failed"
                delivery.failure_reason = str(e)[:500]
                failures.append(delivery.failure_reason)

        if sent_count:
            message.push_status = "sent"
            message.delivered = True
            message.push_error = None
        else:
            message.push_status = "failed"
            message.push_error = "; ".join(failures)[:500] if failures else "推送发送失败"

        await db.flush()
        return message

    async def _push_targets(self, user: User, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(PushToken).where(
                PushToken.user_id == user.id,
                PushToken.is_active.is_(True),
                PushToken.permission_status == "granted",
            )
        )
        tokens = result.scalars().all()
        targets = [
            {
                "id": token.id,
                "provider": token.provider,
                "token": token.token,
            }
            for token in tokens
        ]
        if not targets and user.push_token:
            targets.append(
                {
                    "id": None,
                    "provider": user.push_platform or "",
                    "token": user.push_token,
                }
            )
        return targets

    def _add_delivery(
        self,
        user_id: uuid.UUID,
        push_token_id: uuid.UUID | None,
        proactive_message_id: uuid.UUID,
        provider: str,
        notification_type: str,
        title: str,
        body: str,
        deep_link: str,
        status: str,
        failure_reason: str | None,
        db: AsyncSession,
    ) -> PushDelivery:
        delivery = PushDelivery(
            user_id=user_id,
            push_token_id=push_token_id,
            proactive_message_id=proactive_message_id,
            provider=provider,
            notification_type=notification_type,
            title=title,
            body=body,
            deep_link=deep_link,
            status=status,
            failure_reason=failure_reason,
        )
        db.add(delivery)
        return delivery

    async def _do_send(
        self,
        token: str,
        platform: str | None,
        title: str,
        body: str,
        deep_link: str,
    ) -> str | None:
        """实际发送推送（根据平台选择通道）"""
        if platform == "apns":
            return await self._send_apns(token, title, body, deep_link)
        elif platform == "jpush":
            return await self._send_jpush(token, title, body, deep_link)
        elif platform == "fcm":
            return await self._send_fcm(token, title, body, deep_link)
        else:
            raise ValueError(f"不支持的推送平台: {platform}")

    async def _send_apns(
        self,
        token: str,
        title: str,
        body: str,
        deep_link: str,
    ) -> str | None:
        """发送 APNs 推送"""
        if not self._apns_is_configured():
            print(f"[APNs] Mock: {title} - {body}")
            return None

        host = (
            "https://api.sandbox.push.apple.com"
            if self.config.apns_use_sandbox
            else "https://api.push.apple.com"
        )
        url = f"{host}/3/device/{token}"
        payload = {
            "aps": {
                "alert": {"title": title, "body": body},
                "sound": "default",
            },
            "deep_link": deep_link,
        }
        headers = {
            "authorization": f"bearer {self._build_apns_provider_token()}",
            "apns-topic": self.config.apns_bundle_id,
            "apns-push-type": "alert",
            "apns-priority": "10",
        }
        async with self.http_client_factory(timeout=15.0, http2=True) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code < 200 or response.status_code >= 300:
            raise RuntimeError(
                f"APNs 推送失败: HTTP {response.status_code} {response.text}"
            )
        return response.headers.get("apns-id")

    async def _send_jpush(
        self,
        token: str,
        title: str,
        body: str,
        deep_link: str,
    ) -> str | None:
        """发送极光推送"""
        if not self.config.jpush_app_key or not self.config.jpush_master_secret:
            print(f"[JPUSH] Mock: {title} - {body}")
            return None

        auth = base64.b64encode(
            f"{self.config.jpush_app_key}:{self.config.jpush_master_secret}".encode(
                "utf-8"
            )
        ).decode("ascii")
        payload = {
            "platform": "all",
            "audience": {"registration_id": [token]},
            "notification": {
                "android": {
                    "alert": body,
                    "title": title,
                    "extras": {"deep_link": deep_link},
                },
                "ios": {
                    "alert": {"title": title, "body": body},
                    "sound": "default",
                    "extras": {"deep_link": deep_link},
                },
            },
            "options": {"apns_production": not self.config.apns_use_sandbox},
        }
        async with self.http_client_factory(timeout=15.0) as client:
            response = await client.post(
                self.config.jpush_api_url,
                json=payload,
                headers={
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/json",
                },
            )

        if response.status_code < 200 or response.status_code >= 300:
            raise RuntimeError(
                f"极光推送失败: HTTP {response.status_code} {response.text}"
            )
        data = response.json()
        return str(data.get("msg_id") or data.get("sendno") or "") or None

    async def _send_fcm(
        self,
        token: str,
        title: str,
        body: str,
        deep_link: str,
    ) -> str | None:
        """发送 FCM 推送"""
        if not self._fcm_is_configured():
            print(f"[FCM] Mock: {title} - {body}")
            return None

        service_account = self._load_fcm_service_account()
        project_id = self.config.fcm_project_id or service_account["project_id"]
        access_token = await self._get_fcm_access_token(service_account)
        url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
        payload = {
            "message": {
                "token": token,
                "notification": {"title": title, "body": body},
                "data": {"deep_link": deep_link},
                "android": {
                    "notification": {
                        "click_action": "FLUTTER_NOTIFICATION_CLICK",
                    },
                },
                "apns": {
                    "payload": {
                        "aps": {
                            "category": "LINGBAN_MESSAGE",
                            "sound": "default",
                        },
                    },
                },
            },
        }
        async with self.http_client_factory(timeout=15.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )

        if response.status_code < 200 or response.status_code >= 300:
            raise RuntimeError(f"FCM 推送失败: HTTP {response.status_code} {response.text}")
        return str(response.json().get("name") or "") or None

    async def _get_fcm_access_token(self, service_account: dict[str, Any]) -> str:
        now = self.timestamp_factory()
        if self._fcm_access_token and now < self._fcm_access_token_expires_at - 60:
            return self._fcm_access_token

        assertion = self._build_fcm_jwt_assertion(service_account, now)
        async with self.http_client_factory(timeout=15.0) as client:
            response = await client.post(
                self.config.fcm_oauth_token_url,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": assertion,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if response.status_code < 200 or response.status_code >= 300:
            raise RuntimeError(
                f"FCM OAuth 获取失败: HTTP {response.status_code} {response.text}"
            )
        data = response.json()
        access_token = str(data.get("access_token") or "")
        if not access_token:
            raise RuntimeError("FCM OAuth 响应缺少 access_token")
        expires_in = int(data.get("expires_in") or 3600)
        self._fcm_access_token = access_token
        self._fcm_access_token_expires_at = now + expires_in
        return access_token

    def _build_fcm_jwt_assertion(
        self,
        service_account: dict[str, Any],
        now: int,
    ) -> str:
        header = {"alg": "RS256", "typ": "JWT"}
        payload = {
            "iss": service_account["client_email"],
            "scope": self.config.fcm_scope,
            "aud": self.config.fcm_oauth_token_url,
            "iat": now,
            "exp": now + 3600,
        }
        signing_input = self._jwt_signing_input(header, payload)
        private_key = serialization.load_pem_private_key(
            service_account["private_key"].encode("utf-8"),
            password=None,
        )
        signature = private_key.sign(
            signing_input.encode("ascii"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return f"{signing_input}.{self._base64url(signature)}"

    def _build_apns_provider_token(self) -> str:
        header = {"alg": "ES256", "kid": self.config.apns_key_id}
        payload = {
            "iss": self.config.apns_team_id,
            "iat": self.timestamp_factory(),
        }
        signing_input = self._jwt_signing_input(header, payload)
        private_key = serialization.load_pem_private_key(
            Path(self.config.apns_private_key_path).read_bytes(),
            password=None,
        )
        signature = private_key.sign(
            signing_input.encode("ascii"),
            ec.ECDSA(hashes.SHA256()),
        )
        return f"{signing_input}.{self._base64url(signature)}"

    def _jwt_signing_input(self, header: dict[str, Any], payload: dict[str, Any]) -> str:
        return ".".join(
            (
                self._base64url(
                    json.dumps(header, separators=(",", ":")).encode("utf-8")
                ),
                self._base64url(
                    json.dumps(payload, separators=(",", ":")).encode("utf-8")
                ),
            )
        )

    def _base64url(self, value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    def _load_fcm_service_account(self) -> dict[str, Any]:
        return json.loads(Path(self.config.fcm_service_account_path).read_text("utf-8"))

    def _fcm_is_configured(self) -> bool:
        return bool(self.config.fcm_service_account_path)

    def _apns_is_configured(self) -> bool:
        return all(
            (
                self.config.apns_key_id,
                self.config.apns_team_id,
                self.config.apns_bundle_id,
                self.config.apns_private_key_path,
            )
        )

    def _get_title(self, character_id: str) -> str:
        """获取推送标题"""
        names = {
            "yinyue": "银月",
            "babata": "巴巴塔",
            "heihaung": "黑皇",
        }
        return names.get(character_id, "灵伴")

    def _is_push_disabled(self, user: User) -> bool:
        settings_data = user.settings or {}
        if settings_data.get("push_enabled", True) is False:
            return True
        return settings_data.get("proactive_level", "medium") == "off"

    def _frequency_policy(self, user: User) -> tuple[int, int]:
        level = (user.settings or {}).get("proactive_level", "medium")
        policies = {
            "quiet": (1, 18),
            "low": (1, 18),
            "medium": (2, 8),
            "high": (3, 4),
        }
        return policies.get(level, policies["medium"])

    async def _rate_limit_error(
        self,
        user: User,
        db: AsyncSession,
        now: datetime | None = None,
    ) -> str | None:
        max_per_day, cooldown_hours = self._frequency_policy(user)
        now = now or datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        result = await db.execute(
            select(ProactiveMessage)
            .where(
                ProactiveMessage.user_id == user.id,
                ProactiveMessage.created_at >= today_start,
                ProactiveMessage.push_status == "sent",
            )
            .order_by(ProactiveMessage.created_at.desc())
        )
        sent_messages = result.scalars().all()
        if len(sent_messages) >= max_per_day:
            return "超过每日主动关怀限制"

        if sent_messages:
            last_sent_at = sent_messages[0].created_at
            if last_sent_at.tzinfo is None:
                last_sent_at = last_sent_at.replace(tzinfo=timezone.utc)
            if now - last_sent_at < timedelta(hours=cooldown_hours):
                return "主动关怀冷却中"

        return None

    def _is_dnd_time(self, user: User, now: datetime | None = None) -> bool:
        """检查是否在免打扰时段"""
        settings_data = user.settings or {}
        dnd_enabled = settings_data.get("dnd_enabled", True)
        if not dnd_enabled:
            return False

        dnd_start = settings_data.get("dnd_start", "23:00")
        dnd_end = settings_data.get("dnd_end", "08:00")

        now = now or datetime.now()
        current_minutes = now.hour * 60 + now.minute

        start_parts = dnd_start.split(":")
        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])

        end_parts = dnd_end.split(":")
        end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])

        # 跨午夜的情况（如 23:00 - 08:00）
        if start_minutes > end_minutes:
            return current_minutes >= start_minutes or current_minutes < end_minutes
        else:
            return start_minutes <= current_minutes < end_minutes

    async def _check_rate_limit(self, user_id: uuid.UUID, db: AsyncSession) -> bool:
        """检查是否超过每日推送限制"""
        max_per_day = 3  # 每天最多 3 次主动消息

        # 查询今日已发送的主动消息数
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await db.execute(
            select(ProactiveMessage).where(
                ProactiveMessage.user_id == user_id,
                ProactiveMessage.created_at >= today_start,
                ProactiveMessage.push_status == "sent",
            )
        )
        sent_count = len(result.scalars().all())

        return sent_count >= max_per_day

    async def mark_clicked(self, message_id: uuid.UUID, db: AsyncSession) -> None:
        """标记消息已点击"""
        await db.execute(
            update(ProactiveMessage)
            .where(ProactiveMessage.id == message_id)
            .values(push_status="clicked")
        )
        await db.execute(
            update(PushDelivery)
            .where(PushDelivery.proactive_message_id == message_id)
            .values(status="clicked", clicked_at=datetime.now(timezone.utc))
        )
        await db.flush()


# 单例
push_gateway = PushGateway()
