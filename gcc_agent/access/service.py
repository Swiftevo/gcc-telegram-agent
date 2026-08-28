"""Identity and email-verification application services."""

from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import re
import secrets

from gcc_agent.access.email_sender import EmailSender
from gcc_agent.common.persistence import users

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def normalize_email(raw: str) -> str:
    return (raw or "").strip().lower()


def is_valid_email(raw: str) -> bool:
    value = normalize_email(raw)
    return bool(value) and len(value) <= 254 and bool(_EMAIL_RE.fullmatch(value))


def mask_email(email: str) -> str:
    value = (email or "").strip()
    if "@" not in value:
        return ""
    local, domain = value.split("@", 1)
    return f"{local[:1]}***@{domain}"


class EmailVerificationService:
    def __init__(self, sender: EmailSender, secret: str):
        self.sender = sender
        self.secret = secret

    def _hash(self, user_id: int, email: str, code: str) -> str:
        payload = f"{user_id}:{email}:{code}".encode()
        return hmac.new(self.secret.encode(), payload, hashlib.sha256).hexdigest()

    async def request(self, user_id: int, raw_email: str) -> str:
        email = normalize_email(raw_email)
        if not is_valid_email(email):
            return "invalid"
        if len(self.secret) < 32 or not self.sender.available:
            return "delivery_unavailable"
        code = f"{secrets.randbelow(1_000_000):06d}"
        expires = (_utcnow() + timedelta(minutes=10)).isoformat()
        error = await users.save_email_challenge(
            user_id, email, self._hash(user_id, email, code), expires, attempts=5
        )
        if error:
            return error
        try:
            await self.sender.send_verification_code(email, code)
        except Exception:
            # Invalidate a code whose delivery status is unknown.
            for _ in range(5):
                await users.fail_email_challenge(user_id)
            return "delivery_failed"
        return ""

    async def confirm(self, user_id: int, code: str) -> str:
        challenge = await users.get_email_challenge(user_id)
        if not challenge:
            return "not_requested"
        try:
            expires_at = datetime.fromisoformat(challenge["expires_at"])
        except (TypeError, ValueError):
            return "expired"
        if expires_at <= _utcnow():
            for _ in range(max(1, challenge["attempts_remaining"])):
                await users.fail_email_challenge(user_id)
            return "expired"
        if not re.fullmatch(r"\d{6}", (code or "").strip()):
            await users.fail_email_challenge(user_id)
            return "invalid_code"
        actual = self._hash(user_id, challenge["pending_email"], code.strip())
        if not hmac.compare_digest(actual, challenge["code_hash"]):
            await users.fail_email_challenge(user_id)
            return "invalid_code"
        try:
            await users.complete_email_challenge(user_id, challenge["pending_email"])
        except Exception:
            return "taken"
        return ""
