"""Email delivery boundary and SMTP implementation."""

import asyncio
from email.message import EmailMessage
import smtplib
from typing import Protocol

from gcc_agent.config import Settings


class EmailSender(Protocol):
    @property
    def available(self) -> bool: ...

    async def send_verification_code(self, recipient: str, code: str) -> None: ...


class SMTPEmailSender:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def available(self) -> bool:
        return bool(
            self.settings.smtp_host
            and self.settings.smtp_from
            and self.settings.smtp_username
            and self.settings.smtp_password
        )

    async def send_verification_code(self, recipient: str, code: str) -> None:
        if not self.available:
            raise RuntimeError("SMTP is not configured")
        await asyncio.to_thread(self._send, recipient, code)

    def _send(self, recipient: str, code: str) -> None:
        message = EmailMessage()
        message["Subject"] = "GCC email verification"
        message["From"] = self.settings.smtp_from
        message["To"] = recipient
        message.set_content(
            f"Your GCC verification code is: {code}\n"
            "It expires in 10 minutes. If you did not request this, ignore this email."
        )
        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=15) as smtp:
            if self.settings.smtp_use_tls:
                smtp.starttls()
            smtp.login(self.settings.smtp_username, self.settings.smtp_password)
            smtp.send_message(message)
