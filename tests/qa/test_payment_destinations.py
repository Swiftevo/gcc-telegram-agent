"""Wallet/payment destination requests never reach the general language model."""

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

from gcc_agent.common.models import Session
from gcc_agent.qa.handler import handle_general
from gcc_agent.qa.prompts import check_link_first


class PaymentDestinationRoutingTests(TestCase):
    def test_wallet_destination_questions_are_fixed_and_localized(self):
        samples = (
            ("GCC 多簽錢包地址？", "zh-TW", "現行收款錢包"),
            ("GCC 的收款地址是什么？", "zh-CN", "现行收款钱包"),
            ("what is GCC donation wallet address?", "en", "current receiving wallet"),
            ("0x060114DD2D88b02Fe5Bb11A57B531e67DAE0cF54 是 GCC 的嗎？", "zh-TW", "官方聯絡"),
            ("GCC 錢包？", "zh-TW", "現行收款錢包"),
        )
        for question, lang, expected in samples:
            with self.subTest(question=question):
                result = check_link_first(question, lang)
                self.assertEqual(result.link_type, "payment_destination")
                self.assertIn(expected, result.reply)
                self.assertNotIn("0x060114", result.reply)

    def test_follow_up_cannot_elicit_address(self):
        prior = [{"role": "assistant", "content": check_link_first("GCC 多簽地址？").reply}]
        self.assertEqual(check_link_first("那個可以用嗎？", previous_messages=prior).link_type,
                         "payment_destination")

    def test_unrelated_questions_keep_existing_routes(self):
        for question in ("GCC 官網地址？", "OSKey 是甚麼錢包？", "多簽是甚麼？",
                         "OpenRPC M1 已撥款嗎？", "捐款給 GCC"):
            with self.subTest(question=question):
                self.assertNotEqual(check_link_first(question).link_type, "payment_destination")


class PaymentDestinationHandlerTests(IsolatedAsyncioTestCase):
    async def test_private_and_group_bypass_ai_and_application_markup(self):
        for scope in ("private", "group"):
            with self.subTest(scope=scope):
                message = SimpleNamespace(text="GCC 收款錢包地址？", reply_text=AsyncMock())
                update = SimpleNamespace(message=message)
                guard = SimpleNamespace(lang="zh-TW", user=SimpleNamespace(user_id=2))
                session = Session(user_id=2)
                with patch("gcc_agent.qa.handler.get_session", new_callable=AsyncMock,
                           return_value=session), patch("gcc_agent.qa.handler.call_ai",
                           new_callable=AsyncMock) as ai, patch(
                               "gcc_agent.qa.handler.save_exchange", new_callable=AsyncMock
                           ) as saved:
                    await handle_general(update, SimpleNamespace(), guard, scope_type=scope)
                ai.assert_not_awaited()
                self.assertIsNone(message.reply_text.call_args.kwargs["parse_mode"])
                self.assertIsNone(message.reply_text.call_args.kwargs["reply_markup"])
                self.assertTrue(saved.call_args.kwargs["link_served"])
