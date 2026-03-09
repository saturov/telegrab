from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from telegrab.config import load_runtime_config
from telegrab.downloader import download_video_from_link
from telegrab.models import ExitCode, TelegrabError
from telegrab.telegram_client import TelegramGateway


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        pytest.skip(f"Missing env var for integration test: {name}")
    return value


@pytest.mark.integration
def test_public_video_download(tmp_path: Path) -> None:
    link = _require_env("TELEGRAB_TEST_LINK_PUBLIC")
    result = asyncio.run(_run_download(link=link, output_dir=tmp_path))
    assert result.file_path
    assert Path(result.file_path).exists()


@pytest.mark.integration
def test_private_video_download(tmp_path: Path) -> None:
    link = _require_env("TELEGRAB_TEST_LINK_PRIVATE")
    result = asyncio.run(_run_download(link=link, output_dir=tmp_path))
    assert Path(result.file_path).exists()


@pytest.mark.integration
def test_private_inaccessible_link_returns_code() -> None:
    link = _require_env("TELEGRAB_TEST_LINK_PRIVATE_INACCESSIBLE")
    with pytest.raises(TelegrabError) as err:
        asyncio.run(_run_download(link=link, output_dir=Path("./downloads"), overwrite=False))
    assert err.value.code == ExitCode.NOT_ACCESSIBLE


@pytest.mark.integration
def test_message_without_video_returns_code() -> None:
    link = _require_env("TELEGRAB_TEST_LINK_NO_VIDEO")
    with pytest.raises(TelegrabError) as err:
        asyncio.run(_run_download(link=link, output_dir=Path("./downloads"), overwrite=False))
    assert err.value.code == ExitCode.NO_VIDEO


@pytest.mark.integration
def test_missing_message_returns_code() -> None:
    link = _require_env("TELEGRAB_TEST_LINK_MISSING_MESSAGE")
    with pytest.raises(TelegrabError) as err:
        asyncio.run(_run_download(link=link, output_dir=Path("./downloads"), overwrite=False))
    assert err.value.code == ExitCode.NOT_ACCESSIBLE


@pytest.mark.integration
def test_requires_overwrite_for_existing_file(tmp_path: Path) -> None:
    link = _require_env("TELEGRAB_TEST_LINK_PUBLIC")

    first_result = asyncio.run(_run_download(link=link, output_dir=tmp_path, overwrite=True))
    assert Path(first_result.file_path).exists()

    with pytest.raises(TelegrabError) as err:
        asyncio.run(_run_download(link=link, output_dir=tmp_path, overwrite=False))
    assert err.value.code == ExitCode.API_ERROR


async def _run_download(link: str, output_dir: Path, overwrite: bool = True):
    cfg = load_runtime_config()
    async with TelegramGateway(cfg) as gateway:
        if not await gateway.is_authorized():
            pytest.skip("Telegram account is not authorized. Run: telegrab login")
        return await download_video_from_link(gateway, link, output_dir, overwrite=overwrite)
