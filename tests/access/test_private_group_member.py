"""Private Q&A eligibility derived from current configured-group membership."""

from types import SimpleNamespace
import unittest
from unittest.mock import ANY, AsyncMock, patch

from gcc_agent.access.guard import (
    PRIVATE_GROUP_QA_REASON,
    GuardResult,
    run_guard,
    verify_group_membership,
)
from gcc_agent.access.handler import handle_whoami
from gcc_agent.telegram.app import handle_message


def make_update(user_id: int = 123, text: str = "GCC 是甚麼？"):
    return SimpleNamespace(
        message=SimpleNamespace(text=text, reply_text=AsyncMock()),
        effective_user=SimpleNamespace(
            id=user_id,
            username="member",
            first_name="Member",
            language_code="zh-TW",
            is_bot=False,
        ),
    )


def regular_user(*, actor_type: str = "human", blocked: bool = False):
    return SimpleNamespace(
        user_id=123,
        detected_lang="zh-TW",
        is_blocked=blocked,
        actor_type=actor_type,
        access_level="regular",
    )


def legacy_verified_human():
    user = regular_user()
    user.access_level = "gcc_member"
    user.email = "legacy@example.com"
    user.email_verified_at = "2026-01-01T00:00:00"
    return user


class PrivateGroupMemberGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_current_participant_statuses_are_accepted(self):
        for status, expected in (
            ("member", True),
            ("administrator", True),
            ("creator", True),
            ("left", False),
            ("kicked", False),
            ("restricted", False),
        ):
            with self.subTest(status=status):
                context = SimpleNamespace(
                    bot=SimpleNamespace(
                        get_chat_member=AsyncMock(
                            return_value=SimpleNamespace(status=status)
                        )
                    )
                )
                with patch(
                    "gcc_agent.access.guard.settings",
                    SimpleNamespace(gcc_group_id=-100123),
                ):
                    with patch(
                        "gcc_agent.access.guard.users.update_user_group_membership",
                        new_callable=AsyncMock,
                    ) as update_membership:
                        allowed = await verify_group_membership(123, "zh-TW", context)

                self.assertIs(expected, allowed)
                context.bot.get_chat_member.assert_awaited_once_with(-100123, 123)
                update_membership.assert_awaited_once_with(123, expected)

    async def test_membership_api_error_fails_closed(self):
        context = SimpleNamespace(
            bot=SimpleNamespace(
                get_chat_member=AsyncMock(side_effect=RuntimeError("unavailable"))
            )
        )
        with patch(
            "gcc_agent.access.guard.settings",
            SimpleNamespace(gcc_group_id=-100123),
        ):
            with patch(
                "gcc_agent.access.guard.users.update_user_group_membership",
                new_callable=AsyncMock,
            ) as update_membership:
                allowed = await verify_group_membership(123, "zh-TW", context)

        self.assertFalse(allowed)
        update_membership.assert_not_awaited()

    async def test_current_human_group_member_gets_request_scoped_private_qa(self):
        update = make_update()
        with patch(
            "gcc_agent.access.guard.users.get_or_create_user",
            new=AsyncMock(return_value=(regular_user(), False)),
        ):
            with patch(
                "gcc_agent.access.guard.verify_group_membership",
                new=AsyncMock(return_value=True),
            ) as membership:
                with patch(
                    "gcc_agent.access.guard.users.try_increment_daily_count",
                    new=AsyncMock(return_value=True),
                ) as increment:
                    result = await run_guard(update, SimpleNamespace(bot=object()))

        self.assertTrue(result.passed)
        self.assertEqual(PRIVATE_GROUP_QA_REASON, result.reason)
        membership.assert_awaited_once_with(123, "zh-TW", ANY)
        increment.assert_awaited_once_with(123, 20)
        update.message.reply_text.assert_not_awaited()

    async def test_nonmember_fails_closed_and_gets_welcome(self):
        update = make_update()
        with patch(
            "gcc_agent.access.guard.users.get_or_create_user",
            new=AsyncMock(return_value=(regular_user(), False)),
        ):
            with patch(
                "gcc_agent.access.guard.verify_group_membership",
                new=AsyncMock(return_value=False),
            ):
                result = await run_guard(update, SimpleNamespace(bot=object()))

        self.assertFalse(result.passed)
        self.assertEqual("welcome_only", result.reason)
        update.message.reply_text.assert_awaited_once()

    async def test_legacy_verified_human_must_still_be_current_group_member(self):
        update = make_update()
        with patch(
            "gcc_agent.access.guard.users.get_or_create_user",
            new=AsyncMock(return_value=(legacy_verified_human(), False)),
        ):
            with patch(
                "gcc_agent.access.guard.verify_group_membership",
                new=AsyncMock(return_value=False),
            ) as membership:
                result = await run_guard(update, SimpleNamespace(bot=object()))

        self.assertFalse(result.passed)
        self.assertEqual("welcome_only", result.reason)
        membership.assert_awaited_once()

    async def test_current_member_still_obeys_daily_limit(self):
        update = make_update()
        with patch(
            "gcc_agent.access.guard.users.get_or_create_user",
            new=AsyncMock(return_value=(regular_user(), False)),
        ):
            with patch(
                "gcc_agent.access.guard.verify_group_membership",
                new=AsyncMock(return_value=True),
            ):
                with patch(
                    "gcc_agent.access.guard.users.try_increment_daily_count",
                    new=AsyncMock(return_value=False),
                ):
                    result = await run_guard(update, SimpleNamespace(bot=object()))

        self.assertFalse(result.passed)
        self.assertEqual("rate_limited", result.reason)
        self.assertIn("20", update.message.reply_text.await_args.args[0])

    async def test_agent_does_not_gain_private_qa_from_group_membership(self):
        update = make_update()
        with patch(
            "gcc_agent.access.guard.users.get_or_create_user",
            new=AsyncMock(return_value=(regular_user(actor_type="agent"), False)),
        ):
            with patch(
                "gcc_agent.access.guard.verify_group_membership",
                new=AsyncMock(return_value=True),
            ) as membership:
                result = await run_guard(update, SimpleNamespace(bot=object()))

        self.assertFalse(result.passed)
        self.assertEqual("welcome_only", result.reason)
        membership.assert_not_awaited()


class PrivateGroupMemberRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_blocked_whoami_reports_no_without_membership_lookup(self):
        update = make_update(text="/whoami")
        blocked = SimpleNamespace(
            user_id=123,
            actor_type="human",
            access_level="gcc_member",
            is_blocked=True,
            can_use_qa=lambda: True,
        )
        with patch(
            "gcc_agent.access.handler._current_user",
            new=AsyncMock(return_value=blocked),
        ):
            with patch(
                "handlers.guard.verify_group_membership",
                new_callable=AsyncMock,
            ) as membership:
                await handle_whoami(update, SimpleNamespace(bot=object()))

        membership.assert_not_awaited()
        self.assertIn("qa: no", update.message.reply_text.await_args.args[0])

    async def test_membership_qa_cannot_enter_private_application_flow(self):
        update = make_update()
        guard = GuardResult(
            True,
            user=SimpleNamespace(user_id=123),
            lang="zh-TW",
            reason=PRIVATE_GROUP_QA_REASON,
        )
        with patch(
            "gcc_agent.telegram.app.run_guard",
            new=AsyncMock(return_value=guard),
        ):
            with patch(
                "gcc_agent.telegram.app.route",
                new=AsyncMock(return_value=SimpleNamespace(mode="application")),
            ):
                with patch(
                    "gcc_agent.telegram.app.handle_application",
                    new_callable=AsyncMock,
                ) as application:
                    with patch(
                        "gcc_agent.telegram.app.handle_general",
                        new_callable=AsyncMock,
                    ) as general:
                        await handle_message(update, SimpleNamespace())

        application.assert_not_awaited()
        general.assert_awaited_once_with(
            update,
            ANY,
            guard,
            allow_application=False,
        )


if __name__ == "__main__":
    unittest.main()
