from __future__ import annotations

from urllib.parse import urlparse

from telegrab.models import ExitCode, ParsedLink, TelegrabError
from telegrab.validation import ensure_no_control_chars

SUPPORTED_HOSTS = {"t.me", "www.t.me", "telegram.me", "www.telegram.me"}


def internal_channel_id_to_peer_id(internal_channel_id: int) -> int:
    if internal_channel_id <= 0:
        raise TelegrabError(ExitCode.INVALID_LINK, "Internal channel id must be positive.")
    return int(f"-100{internal_channel_id}")


def parse_telegram_post_link(raw_url: str) -> ParsedLink:
    if not raw_url:
        raise TelegrabError(ExitCode.INVALID_LINK, "Telegram post link is required.")

    normalized_url = ensure_no_control_chars(raw_url.strip(), "Telegram post link")
    parsed = urlparse(normalized_url)
    if parsed.scheme not in {"http", "https"}:
        raise TelegrabError(ExitCode.INVALID_LINK, "Link must start with http:// or https://.")
    if parsed.netloc.lower() not in SUPPORTED_HOSTS:
        raise TelegrabError(ExitCode.INVALID_LINK, "Only t.me and telegram.me links are supported.")
    if parsed.query:
        raise TelegrabError(ExitCode.INVALID_LINK, "Telegram link must not contain query parameters.")
    if parsed.fragment:
        raise TelegrabError(ExitCode.INVALID_LINK, "Telegram link must not contain a URL fragment.")

    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise TelegrabError(ExitCode.INVALID_LINK, "Link must include channel and message id.")

    if parts[0] == "c":
        if len(parts) < 3:
            raise TelegrabError(ExitCode.INVALID_LINK, "Private link must include internal channel id and message id.")
        internal_raw = parts[1]
        message_raw = parts[2]
        try:
            internal_id = int(internal_raw)
            message_id = int(message_raw)
        except ValueError as exc:
            raise TelegrabError(ExitCode.INVALID_LINK, "Private link contains non-numeric identifiers.") from exc
        if internal_id <= 0:
            raise TelegrabError(ExitCode.INVALID_LINK, "Internal channel id must be positive.")
        if message_id <= 0:
            raise TelegrabError(ExitCode.INVALID_LINK, "Message id must be positive.")
        return ParsedLink(
            source_url=normalized_url,
            internal_channel_id=internal_id,
            message_id=message_id,
        )

    username = parts[0].strip()
    if not username:
        raise TelegrabError(ExitCode.INVALID_LINK, "Channel username is empty.")
    try:
        message_id = int(parts[1])
    except ValueError as exc:
        raise TelegrabError(ExitCode.INVALID_LINK, "Message id must be numeric.") from exc
    if message_id <= 0:
        raise TelegrabError(ExitCode.INVALID_LINK, "Message id must be positive.")

    return ParsedLink(
        source_url=normalized_url,
        username=username,
        message_id=message_id,
    )
