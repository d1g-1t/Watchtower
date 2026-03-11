from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.core.models import HealthStatus, ServiceStatus, SystemHealth

logger = logging.getLogger(__name__)


class SlackAlerter:
    def __init__(
        self, webhook_url: str | None, cooldown_minutes: int = 15
    ) -> None:
        self._webhook = webhook_url
        self._cooldown = timedelta(minutes=cooldown_minutes)
        self._last_alerts: dict[str, datetime] = {}

    async def notify_if_needed(
        self,
        statuses: dict[str, ServiceStatus],
        system: SystemHealth,
    ) -> None:
        if not self._webhook:
            return

        for name, status in statuses.items():
            if status.status == HealthStatus.UNHEALTHY:
                await self._send_if_ready(name, status)

    async def _send_if_ready(
        self, name: str, status: ServiceStatus
    ) -> None:
        now = datetime.now(timezone.utc)
        last = self._last_alerts.get(name)
        if last and now - last < self._cooldown:
            return

        self._last_alerts[name] = now
        await self._send(name, status)

    async def _send(self, name: str, status: ServiceStatus) -> None:
        emoji = "\U0001f534" if status.status == HealthStatus.UNHEALTHY else "\U0001f7e1"
        degraded_info = (
            f"\n*Caused by:* `{status.degraded_by}` is down"
            if status.degraded_by
            else ""
        )
        payload = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"{emoji} *Watchtower Alert: {name.upper()}*\n"
                            f"*Status:* `{status.status.value}`\n"
                            f"*Error:* `{status.error or 'no response'}`"
                            f"{degraded_info}\n"
                            f"*Time:* {status.checked_at.strftime('%H:%M:%S UTC')}"
                        ),
                    },
                }
            ]
        }
        try:
            async with httpx.AsyncClient() as client:
                await client.post(self._webhook, json=payload)
        except Exception:
            logger.exception("slack alert failed for %s", name)
