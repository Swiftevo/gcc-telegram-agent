"""Tests for production log sanitization."""

import logging
import unittest

from gcc_agent.telegram.app import TokenRedactionFilter


class TokenRedactionFilterTests(unittest.TestCase):
    def test_redacts_token_from_non_string_logging_argument(self) -> None:
        class URLValue:
            def __str__(self) -> str:
                return "https://api.telegram.org/bot123456:secret_value/getMe"

        record = logging.LogRecord(
            name="httpx",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="HTTP Request: POST %s",
            args=(URLValue(),),
            exc_info=None,
        )

        self.assertTrue(TokenRedactionFilter().filter(record))
        rendered = record.getMessage()

        self.assertEqual(
            "HTTP Request: POST https://api.telegram.org/bot[REDACTED]/getMe",
            rendered,
        )
        self.assertNotIn("secret_value", rendered)


if __name__ == "__main__":
    unittest.main()
