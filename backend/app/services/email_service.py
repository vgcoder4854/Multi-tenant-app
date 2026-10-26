"""Mocked email service.

Real email is out of scope for this assessment; this service logs what *would* be
sent to the console. Swap the body for a real provider (SMTP, SES, ...) later
without touching the services that call it.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("app.email")


def send_invitation_email(*, to_email: str, org_name: str, role: str, raw_token: str) -> None:
    """Pretend to email an invitation. The raw token is printed once for demos."""
    logger.info(
        "[mocked email] Invitation to %s for '%s' as %s. token=%s",
        to_email,
        org_name,
        role,
        raw_token,
    )
    print(
        f"[mocked email] -> {to_email}: you were invited to '{org_name}' as {role}. "
        f"Invitation token: {raw_token}"
    )


def send_notification_email(*, to_email: str, subject: str, body: str) -> None:
    """Pretend to email a notification."""
    logger.info("[mocked email] notification to %s: %s", to_email, subject)
