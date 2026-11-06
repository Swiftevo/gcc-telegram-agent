"""Fail closed on unverified wallet and payment-destination questions."""

import re


_CHAIN_ADDRESS = re.compile(r"(?<![0-9a-f])0x[0-9a-f]{40}(?![0-9a-f])", re.I)
_EXPLICIT_DESTINATION_TERMS = (
    "收款", "收幣", "收币",
    "recipient", "receiving account", "錢包地址", "钱包地址", "wallet address",
)
_GCC_MULTISIG = re.compile(r"\bgcc\b.{0,16}(?:多簽|多签|multisig|multi-sig)|"
                           r"(?:多簽|多签|multisig|multi-sig).{0,16}\bgcc\b", re.I)
_GENERIC_ADDRESS_TERMS = ("地址", "address")
_WALLET_TERMS = ("錢包", "钱包", "wallet", "safe")
_PAYMENT_TERMS = (
    "捐款", "捐贈", "捐赠", "資助", "资助", "轉帳", "转账",
    "匯款", "汇款", "付款", "打款", "donat", "fund", "grant",
    "transfer", "payment", "send", "receive", "usdc", "usdt", "eth",
)
_DESTINATION_PHRASES = (
    "轉到哪", "转到哪", "打到哪", "匯到哪", "汇到哪",
    "給哪個帳戶", "给哪个账户", "to which account", "where to send",
)
_GCC_WALLET = re.compile(r"\bgcc\b.{0,16}(?:錢包|钱包|wallet|safe)|"
                         r"(?:錢包|钱包|wallet|safe).{0,16}\bgcc\b", re.I)
_FOLLOW_UP_TERMS = (
    "這個", "这个", "那個", "那个", "該", "该", "地址", "錢包", "钱包",
    "給我", "给我", "發我", "发我", "send it", "give me", "that address",
    "that wallet", "is it", "which one",
)

REPLIES = {
    "zh-TW": (
        "目前沒有經 GCC 核准可供 Bot 提供的現行收款錢包地址及鏈別。"
        "請透過 GCC 官方聯絡渠道核對；不要只憑歷史提案、聊天訊息或 Bot 推測轉帳。\n"
        "https://www.gccofficial.org/contact"
    ),
    "zh-CN": (
        "目前没有经 GCC 核准可供 Bot 提供的现行收款钱包地址及链别。"
        "请通过 GCC 官方联系渠道核对；不要只凭历史提案、聊天消息或 Bot 推测转账。\n"
        "https://www.gccofficial.org/contact"
    ),
    "en": (
        "The Bot has no GCC-approved current receiving wallet address and network to provide. "
        "Please confirm both through GCC's official contact channel before sending funds. "
        "Do not rely on a historical proposal or a chat message.\n"
        "https://www.gccofficial.org/contact"
    ),
}


def _previous_destination_refusal(previous_messages: list[dict] | None) -> bool:
    if not previous_messages:
        return False
    last = previous_messages[-1]
    return last.get("role") == "assistant" and last.get("content") in REPLIES.values()


def select_payment_destination_reply(
    text: str, lang: str, previous_messages: list[dict] | None = None
) -> str | None:
    """Prevent wallet destinations from falling through to the language model."""
    value = text.casefold().strip()
    if not value:
        return None
    is_destination = (
        bool(_CHAIN_ADDRESS.search(value))
        or bool(_GCC_MULTISIG.search(value))
        or bool(_GCC_WALLET.search(value))
        or any(term in value for term in _EXPLICIT_DESTINATION_TERMS)
        or any(term in value for term in _DESTINATION_PHRASES)
        or (
            any(term in value for term in _GENERIC_ADDRESS_TERMS)
            and any(term in value for term in _PAYMENT_TERMS + _WALLET_TERMS)
        )
        or (
            any(term in value for term in _WALLET_TERMS)
            and any(term in value for term in _PAYMENT_TERMS)
        )
    )
    if not is_destination and _previous_destination_refusal(previous_messages):
        is_destination = any(term in value for term in _FOLLOW_UP_TERMS)
    return REPLIES.get(lang, REPLIES["zh-TW"]) if is_destination else None
