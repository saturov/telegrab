from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

from telegrab.models import ExitCode, TelegrabError

APP_NAME = "telegrab"
APP_AUTHOR = "bitmanager"
ENV_API_ID = "TELEGRAB_API_ID"
ENV_API_HASH = "TELEGRAB_API_HASH"


@dataclass(frozen=True)
class RuntimeConfig:
    api_id: int
    api_hash: str
    data_dir: Path
    config_path: Path
    session_stem: Path


@dataclass(frozen=True)
class RuntimeEnvironment:
    config_path: Path
    data_dir: Path
    session_stem: Path
    credentials_present: bool
    credentials_source: str
    env_api_id_valid: bool


def _config_file_path() -> Path:
    return Path(user_config_dir(APP_NAME, APP_AUTHOR)) / "config.json"


def _data_dir_path() -> Path:
    return Path(user_data_dir(APP_NAME, APP_AUTHOR))


def _read_file_config(config_path: Path) -> dict[str, object]:
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TelegrabError(ExitCode.NOT_AUTHORIZED, f"Invalid config file format: {config_path}") from exc


def _read_api_id(raw_value: str | int | None) -> int | None:
    if raw_value is None:
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise TelegrabError(ExitCode.NOT_AUTHORIZED, "TELEGRAB_API_ID must be an integer.") from exc


def inspect_runtime_environment() -> RuntimeEnvironment:
    config_path = _config_file_path()
    config_data = _read_file_config(config_path)

    env_api_id_raw = os.getenv(ENV_API_ID)
    env_api_hash = os.getenv(ENV_API_HASH)
    env_api_id_valid = True
    env_api_id: int | None = None
    if env_api_id_raw is not None:
        try:
            env_api_id = _read_api_id(env_api_id_raw)
        except TelegrabError:
            env_api_id_valid = False

    file_api_id = _read_api_id(config_data.get("api_id"))
    file_api_hash = config_data.get("api_hash")

    env_credentials_present = env_api_id is not None and isinstance(env_api_hash, str) and bool(env_api_hash.strip())
    file_credentials_present = file_api_id is not None and isinstance(file_api_hash, str) and bool(file_api_hash.strip())

    if env_credentials_present:
        credentials_source = "env"
        credentials_present = True
    elif file_credentials_present:
        credentials_source = "file"
        credentials_present = True
    else:
        credentials_source = "missing"
        credentials_present = False

    data_dir = _data_dir_path()
    return RuntimeEnvironment(
        config_path=config_path,
        data_dir=data_dir,
        session_stem=data_dir / "user_session",
        credentials_present=credentials_present,
        credentials_source=credentials_source,
        env_api_id_valid=env_api_id_valid,
    )


def load_runtime_config() -> RuntimeConfig:
    environment = inspect_runtime_environment()
    config_data = _read_file_config(environment.config_path)

    env_api_id = _read_api_id(os.getenv(ENV_API_ID))
    env_api_hash = os.getenv(ENV_API_HASH)

    file_api_id = _read_api_id(config_data.get("api_id"))
    file_api_hash = config_data.get("api_hash")

    api_id = env_api_id if env_api_id is not None else file_api_id
    api_hash = env_api_hash if env_api_hash else file_api_hash

    if api_id is None or not isinstance(api_hash, str) or not api_hash.strip():
        raise TelegrabError(
            ExitCode.NOT_AUTHORIZED,
            "Missing Telegram API credentials. Set TELEGRAB_API_ID and TELEGRAB_API_HASH or create config file.",
        )

    environment.data_dir.mkdir(parents=True, exist_ok=True)

    return RuntimeConfig(
        api_id=api_id,
        api_hash=api_hash.strip(),
        data_dir=environment.data_dir,
        config_path=environment.config_path,
        session_stem=environment.session_stem,
    )
