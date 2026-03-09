from __future__ import annotations

from typing import Any

from telegrab.models import ExitCode, TelegrabError

EXIT_CODES = {
    str(int(ExitCode.SUCCESS)): "success",
    str(int(ExitCode.INVALID_LINK)): "invalid input or unsupported link",
    str(int(ExitCode.NOT_AUTHORIZED)): "missing credentials or Telegram authorization required",
    str(int(ExitCode.NOT_ACCESSIBLE)): "channel or message is not accessible",
    str(int(ExitCode.NO_VIDEO)): "message does not contain a video",
    str(int(ExitCode.RESTRICTED)): "Telegram content restriction prevents download",
    str(int(ExitCode.API_ERROR)): "Telegram or runtime error",
}

COMMAND_DESCRIPTIONS: dict[str, dict[str, Any]] = {
    "telegrab": {
        "summary": "Download a single Telegram video from one message link.",
        "output_modes": ["text", "json"],
        "commands": ["fetch", "login", "status", "doctor", "describe"],
        "exit_codes": EXIT_CODES,
    },
    "fetch": {
        "summary": "Download the video from one Telegram message link.",
        "arguments": [
            {"name": "telegram_link", "type": "string", "required": True},
        ],
        "options": [
            {"name": "--output-dir", "type": "path", "required": False, "default": "./downloads"},
            {"name": "--name-template", "type": "string", "required": False, "default": None},
            {"name": "--overwrite", "type": "boolean", "required": False, "default": False},
            {"name": "--dry-run", "type": "boolean", "required": False, "default": False},
            {"name": "--output", "type": "enum", "required": False, "default": "text", "values": ["text", "json"]},
        ],
        "response": {
            "command": "fetch",
            "status": "ok|error",
            "exit_code": "int",
            "error_code": "int|null",
            "error_message": "string|null",
            "source_url": "string",
            "file_path": "string|null",
            "would_write_to": "string|null",
            "message_id": "int|null",
            "chat_id": "int|null",
            "dry_run": "bool",
        },
        "exit_codes": EXIT_CODES,
    },
    "login": {
        "summary": "Authorize Telegram user session for later downloads.",
        "arguments": [],
        "options": [
            {"name": "--phone", "type": "string", "required": False, "default": None},
            {"name": "--output", "type": "enum", "required": False, "default": "text", "values": ["text", "json"]},
        ],
        "response": {
            "command": "login",
            "status": "ok|error",
            "exit_code": "int",
            "error_code": "int|null",
            "error_message": "string|null",
            "authorized": "bool",
            "user_id": "int|null",
            "username": "string|null",
        },
        "exit_codes": EXIT_CODES,
    },
    "status": {
        "summary": "Check whether the current Telegram session is authorized.",
        "arguments": [],
        "options": [
            {"name": "--output", "type": "enum", "required": False, "default": "text", "values": ["text", "json"]},
        ],
        "response": {
            "command": "status",
            "status": "ok|error",
            "exit_code": "int",
            "error_code": "int|null",
            "error_message": "string|null",
            "authorized": "bool",
            "user_id": "int|null",
            "username": "string|null",
        },
        "exit_codes": EXIT_CODES,
    },
    "doctor": {
        "summary": "Report local configuration and session diagnostics without network calls.",
        "arguments": [],
        "options": [
            {"name": "--output", "type": "enum", "required": False, "default": "text", "values": ["text", "json"]},
        ],
        "response": {
            "command": "doctor",
            "status": "ok|error",
            "exit_code": "int",
            "error_code": "int|null",
            "error_message": "string|null",
            "version": "string",
            "config_path": "string",
            "data_dir": "string",
            "session_path": "string",
            "credentials_present": "bool",
            "credentials_source": "env|file|missing",
            "session_present": "bool",
        },
        "exit_codes": EXIT_CODES,
    },
    "describe": {
        "summary": "Describe telegrab commands, arguments, outputs, and exit codes.",
        "arguments": [
            {"name": "command", "type": "string", "required": False},
        ],
        "options": [
            {"name": "--output", "type": "enum", "required": False, "default": "json", "values": ["text", "json"]},
        ],
        "response": {
            "command": "describe",
            "status": "ok|error",
            "exit_code": "int",
            "error_code": "int|null",
            "error_message": "string|null",
            "target": "string",
            "description": "object",
        },
        "exit_codes": EXIT_CODES,
    },
}


def describe_command(target: str | None) -> tuple[str, dict[str, Any]]:
    normalized = "telegrab" if target is None else target.strip().lower()
    description = COMMAND_DESCRIPTIONS.get(normalized)
    if description is None:
        raise TelegrabError(ExitCode.INVALID_LINK, f"Unknown command for describe: {target}")
    return normalized, description
