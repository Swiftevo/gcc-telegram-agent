"""Environment-backed configuration. Secrets are never given defaults."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int = 0) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    db_path: str = os.getenv("DB_PATH", "gcc_agent.db")
    admin_user_id: int = _int("ADMIN_USER_ID")
    admin_notify_id: int = _int("ADMIN_NOTIFY_ID")
    gcc_group_id: int = _int("GCC_GROUP_ID")
    gcc_group_invite: str = os.getenv("GCC_GROUP_INVITE", "")
    webhook_url: str = os.getenv("WEBHOOK_URL", "")
    port: int = _int("PORT", 8080)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    ai_model: str = os.getenv("AI_MODEL", "gpt-4o-mini")
    ai_max_tokens: int = _int("AI_MAX_TOKENS", 800)
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = _int("SMTP_PORT", 587)
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "")
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    email_verification_secret: str = os.getenv("EMAIL_VERIFICATION_SECRET", "")


settings = Settings()
