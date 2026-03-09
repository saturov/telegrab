from __future__ import annotations

import getpass
from pathlib import Path
from typing import Any, Callable

from telethon import TelegramClient, errors, utils
from telethon.errors import RPCError
from telethon.tl.custom.message import Message

from telegrab.config import RuntimeConfig
from telegrab.link_parser import internal_channel_id_to_peer_id
from telegrab.models import ExitCode, ParsedLink, TelegrabError

ProgressCallback = Callable[[int, int], Any]


def map_telegram_error(exc: Exception) -> TelegrabError:
    if isinstance(exc, TelegrabError):
        return exc

    if isinstance(exc, (OSError, TimeoutError)):
        return TelegrabError(ExitCode.API_ERROR, f"Network error: {exc}")

    if isinstance(exc, RPCError):
        class_name = exc.__class__.__name__.upper()
        message = str(exc)
        normalized = f"{class_name} {message.upper()}".replace("_", "")

        if any(token in normalized for token in ("AUTH", "SESSION", "PHONECODE", "PASSWORD")):
            return TelegrabError(ExitCode.NOT_AUTHORIZED, f"Telegram authorization error: {message}")
        if any(
            token in normalized
            for token in (
                "CHANNELPRIVATE",
                "CHATADMINREQUIRED",
                "USERNAMEINVALID",
                "USERNAMENOTOCCUPIED",
                "INVITEHASH",
                "MSGIDINVALID",
                "PEERIDINVALID",
            )
        ):
            return TelegrabError(ExitCode.NOT_ACCESSIBLE, f"Channel/message is not accessible: {message}")
        if any(token in normalized for token in ("CHATFORWARDSRESTRICTED", "CONTENTPROTECTED")):
            return TelegrabError(ExitCode.RESTRICTED, f"Telegram content restrictions prevent download: {message}")
        return TelegrabError(ExitCode.API_ERROR, f"Telegram API error: {message}")

    return TelegrabError(ExitCode.API_ERROR, f"Unexpected error: {exc}")


class TelegramGateway:
    def __init__(self, cfg: RuntimeConfig):
        self._cfg = cfg
        self._client = TelegramClient(str(cfg.session_stem), cfg.api_id, cfg.api_hash)

    async def __aenter__(self) -> "TelegramGateway":
        await self._client.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc: Exception | None, tb: Any) -> None:
        await self._client.disconnect()

    async def is_authorized(self) -> bool:
        try:
            return await self._client.is_user_authorized()
        except Exception as exc:
            raise map_telegram_error(exc) from exc

    async def login(self, phone: str | None = None) -> None:
        try:
            if await self._client.is_user_authorized():
                return

            phone_value = phone or input("Telegram phone number (with country code): ").strip()
            if not phone_value:
                raise TelegrabError(ExitCode.NOT_AUTHORIZED, "Phone number is required.")

            await self._client.send_code_request(phone_value)
            code = input("Login code from Telegram: ").strip()
            if not code:
                raise TelegrabError(ExitCode.NOT_AUTHORIZED, "Login code is required.")

            try:
                await self._client.sign_in(phone=phone_value, code=code)
            except errors.SessionPasswordNeededError:
                password = getpass.getpass("Telegram 2FA password: ").strip()
                if not password:
                    raise TelegrabError(ExitCode.NOT_AUTHORIZED, "2FA password is required.")
                await self._client.sign_in(password=password)
        except Exception as exc:
            raise map_telegram_error(exc) from exc

    async def resolve_entity(self, parsed_link: ParsedLink) -> Any:
        try:
            if parsed_link.is_public:
                return await self._client.get_entity(parsed_link.username)

            target_peer_id = internal_channel_id_to_peer_id(parsed_link.internal_channel_id or 0)
            async for dialog in self._client.iter_dialogs():
                if utils.get_peer_id(dialog.entity) == target_peer_id:
                    return dialog.entity
            raise TelegrabError(
                ExitCode.NOT_ACCESSIBLE,
                "Private channel from link is not visible in current account dialogs.",
            )
        except Exception as exc:
            raise map_telegram_error(exc) from exc

    async def get_message(self, entity: Any, message_id: int) -> Message:
        try:
            message = await self._client.get_messages(entity, ids=message_id)
            if message is None:
                raise TelegrabError(ExitCode.NOT_ACCESSIBLE, f"Message {message_id} does not exist.")
            return message
        except Exception as exc:
            raise map_telegram_error(exc) from exc

    async def download_media(
        self,
        message: Message,
        destination: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> Path:
        try:
            result = await self._client.download_media(
                message=message,
                file=str(destination),
                progress_callback=progress_callback,
            )
            if result is None:
                raise TelegrabError(ExitCode.RESTRICTED, "Telegram did not return media content for this message.")
            return Path(result)
        except Exception as exc:
            raise map_telegram_error(exc) from exc

    async def get_self_user(self) -> Any:
        try:
            return await self._client.get_me()
        except Exception as exc:
            raise map_telegram_error(exc) from exc
