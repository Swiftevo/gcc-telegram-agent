"""Administrative read-only statistics repository."""

from datetime import datetime

from gcc_agent.common.persistence.database import connect


async def get_stats() -> dict:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    async with connect(rows=True) as db:
        async def scalar(sql: str, params=()):
            async with db.execute(sql, params) as cursor:
                return (await cursor.fetchone())["n"]

        return {
            "total_users": await scalar("SELECT COUNT(*) n FROM users"),
            "active_today": await scalar(
                "SELECT COUNT(*) n FROM users WHERE count_reset_date=? AND daily_count>0",
                (today,),
            ),
            "messages_today": await scalar(
                "SELECT COUNT(*) n FROM messages WHERE created_at LIKE ?", (f"{today}%",)
            ),
            "ai_calls_today": await scalar(
                "SELECT COUNT(*) n FROM messages WHERE role='assistant' "
                "AND link_served=0 AND created_at LIKE ?",
                (f"{today}%",),
            ),
            "tokens_today": await scalar(
                "SELECT COALESCE(SUM(tokens_used),0) n FROM messages WHERE created_at LIKE ?",
                (f"{today}%",),
            ),
            "applications_today": await scalar(
                """SELECT COUNT(*) n FROM sessions
                   WHERE draft_json LIKE '%"collection_step": 4%' AND created_at LIKE ?""",
                (f"{today}%",),
            ),
        }
