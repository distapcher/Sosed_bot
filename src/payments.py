from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from yookassa import Configuration, Payment
from yookassa.domain.notification import WebhookNotificationFactory

from .config import Settings

log = logging.getLogger("sosed.payments")


@dataclass(frozen=True)
class CreatedPayment:
    payment_id: str
    confirmation_url: str
    amount_rub: float


def configure_yookassa(settings: Settings) -> None:
    Configuration.configure(settings.yookassa_shop_id, settings.yookassa_secret_key)


def create_subscription_payment(settings: Settings, *, telegram_user_id: int) -> CreatedPayment:
    if not settings.payment_enabled:
        raise RuntimeError("Payments are disabled")

    amount = f"{settings.payment_amount_rub:.2f}"
    idempotence_key = str(uuid.uuid4())

    payment = Payment.create(
        {
            "amount": {"value": amount, "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": settings.payment_return_url,
            },
            "capture": True,
            "description": settings.payment_description,
            "metadata": {
                "telegram_user_id": str(telegram_user_id),
                "access_days": str(settings.payment_access_days),
            },
        },
        idempotence_key,
    )

    confirmation = payment.confirmation
    if confirmation is None or not confirmation.confirmation_url:
        raise RuntimeError("YooKassa did not return confirmation URL")

    return CreatedPayment(
        payment_id=payment.id,
        confirmation_url=confirmation.confirmation_url,
        amount_rub=settings.payment_amount_rub,
    )


def parse_webhook(body: bytes) -> tuple[str, str, int, int, float]:
    """
    Returns: event, payment_id, telegram_user_id, access_days, amount_rub
    """
    notification = WebhookNotificationFactory().create(body.decode("utf-8"))
    event = notification.event
    payment = notification.object

    metadata = payment.metadata or {}
    telegram_user_id = int(metadata.get("telegram_user_id", 0))
    access_days = int(metadata.get("access_days", 0))

    amount_value = payment.amount.value if payment.amount else "0"
    amount_rub = float(amount_value)

    return event, payment.id, telegram_user_id, access_days, amount_rub
