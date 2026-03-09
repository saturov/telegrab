from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class ExitCode(IntEnum):
    SUCCESS = 0
    INVALID_LINK = 2
    NOT_AUTHORIZED = 3
    NOT_ACCESSIBLE = 4
    NO_VIDEO = 5
    RESTRICTED = 6
    API_ERROR = 7


@dataclass(frozen=True)
class ParsedLink:
    source_url: str
    message_id: int
    username: str | None = None
    internal_channel_id: int | None = None

    @property
    def is_public(self) -> bool:
        return self.username is not None

    @property
    def is_private_internal(self) -> bool:
        return self.internal_channel_id is not None


@dataclass(kw_only=True)
class CommandResult:
    command: str
    status: str
    exit_code: int
    error_code: int | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "status": self.status,
            "exit_code": self.exit_code,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


@dataclass(kw_only=True)
class FetchResult(CommandResult):
    source_url: str
    file_path: str | None = None
    would_write_to: str | None = None
    message_id: int | None = None
    chat_id: int | None = None
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "source_url": self.source_url,
                "file_path": self.file_path,
                "would_write_to": self.would_write_to,
                "message_id": self.message_id,
                "chat_id": self.chat_id,
                "dry_run": self.dry_run,
            }
        )
        return payload


@dataclass(kw_only=True)
class StatusResult(CommandResult):
    authorized: bool
    user_id: int | None = None
    username: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "authorized": self.authorized,
                "user_id": self.user_id,
                "username": self.username,
            }
        )
        return payload


@dataclass(kw_only=True)
class DoctorResult(CommandResult):
    version: str
    config_path: str
    data_dir: str
    session_path: str
    credentials_present: bool
    credentials_source: str
    session_present: bool

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "version": self.version,
                "config_path": self.config_path,
                "data_dir": self.data_dir,
                "session_path": self.session_path,
                "credentials_present": self.credentials_present,
                "credentials_source": self.credentials_source,
                "session_present": self.session_present,
            }
        )
        return payload


@dataclass(kw_only=True)
class DescribeResult(CommandResult):
    target: str
    description: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "target": self.target,
                "description": self.description,
            }
        )
        return payload


@dataclass(frozen=True)
class PreparedDownload:
    source_url: str
    message_id: int
    file_path: str | None = None
    would_write_to: str | None = None
    chat_id: int | None = None
    dry_run: bool = False

    def to_fetch_result(self) -> FetchResult:
        return FetchResult(
            command="fetch",
            status="ok",
            exit_code=int(ExitCode.SUCCESS),
            source_url=self.source_url,
            file_path=self.file_path,
            would_write_to=self.would_write_to,
            message_id=self.message_id,
            chat_id=self.chat_id,
            dry_run=self.dry_run,
        )


class TelegrabError(Exception):
    def __init__(self, code: ExitCode, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
