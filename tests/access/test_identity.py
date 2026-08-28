import os
import tempfile
import unittest

from gcc_agent.access.models import ACCESS_GCC_MEMBER, ACTOR_AGENT, ACTOR_HUMAN
from gcc_agent.access.service import EmailVerificationService
from gcc_agent.common.persistence import database, users


class FakeSender:
    available = True

    def __init__(self):
        self.code = ""

    async def send_verification_code(self, recipient: str, code: str) -> None:
        self.code = code


class IdentityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        database.DB_PATH = self.path
        await database.init_db()
        await users.get_or_create_user(42)

    async def asyncTearDown(self):
        os.remove(self.path)

    async def test_human_member_requires_verified_email(self):
        self.assertEqual(
            "verified_email_required",
            await users.set_identity(42, ACTOR_HUMAN, ACCESS_GCC_MEMBER),
        )
        sender = FakeSender()
        service = EmailVerificationService(sender, "test-secret-that-is-at-least-32-bytes")
        self.assertEqual("", await service.request(42, "Member@Example.com"))
        self.assertEqual("", await service.confirm(42, sender.code))
        self.assertEqual("", await users.set_identity(42, ACTOR_HUMAN, ACCESS_GCC_MEMBER))
        self.assertTrue((await users.get_user(42)).can_use_qa())

    async def test_agent_member_requires_hashed_credential(self):
        self.assertEqual(
            "agent_credential_required",
            await users.set_identity(42, ACTOR_AGENT, ACCESS_GCC_MEMBER),
        )
        credential = "a" * 40
        self.assertEqual("", await users.store_agent_credential(42, credential))
        self.assertTrue(await users.verify_agent_credential(42, credential))
        self.assertEqual("", await users.set_identity(42, ACTOR_AGENT, ACCESS_GCC_MEMBER))
        agent = await users.get_user(42)
        self.assertFalse(agent.can_use_qa())
        self.assertTrue(agent.can_use_qa(agent_authenticated=True))

    async def test_delivery_unavailable_fails_closed(self):
        sender = FakeSender()
        sender.available = False
        service = EmailVerificationService(sender, "test-secret-that-is-at-least-32-bytes")
        self.assertEqual("delivery_unavailable", await service.request(42, "a@example.com"))
