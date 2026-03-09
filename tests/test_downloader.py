import asyncio
from types import SimpleNamespace

import pytest

from pathlib import Path

from telegrab.downloader import (
    build_output_filename,
    download_video_from_link,
    guess_video_extension,
    is_video_message,
    normalize_output_dir,
)
from telegrab.models import ExitCode, TelegrabError


class DocumentAttributeVideo:
    pass


def _fake_message(*, video=None, mime_type: str = "", file_ext: str | None = None, attributes=None):
    if attributes is None:
        attributes = []
    return SimpleNamespace(
        video=video,
        file=SimpleNamespace(ext=file_ext) if file_ext is not None else None,
        document=SimpleNamespace(mime_type=mime_type, attributes=attributes),
    )


def test_is_video_message_true_from_video_field() -> None:
    message = _fake_message(video=object())
    assert is_video_message(message) is True


def test_is_video_message_true_from_attributes() -> None:
    message = _fake_message(attributes=[DocumentAttributeVideo()])
    assert is_video_message(message) is True


def test_is_video_message_false() -> None:
    message = _fake_message(mime_type="application/pdf")
    assert is_video_message(message) is False


def test_guess_video_extension_prefers_file_extension() -> None:
    message = _fake_message(file_ext=".mkv", mime_type="video/mp4")
    assert guess_video_extension(message) == ".mkv"


def test_guess_video_extension_from_mime_type() -> None:
    message = _fake_message(mime_type="video/webm")
    assert guess_video_extension(message) == ".webm"


def test_build_output_filename_default() -> None:
    name = build_output_filename("My Channel", 77, ".mp4")
    assert name == "My_Channel_77.mp4"


def test_build_output_filename_template() -> None:
    name = build_output_filename("My Channel", 77, ".mp4", "{channel}-{message_id}.{ext}")
    assert name == "My_Channel-77.mp4"


def test_build_output_filename_template_rejects_paths() -> None:
    with pytest.raises(TelegrabError) as err:
        build_output_filename("A", 1, ".mp4", "../bad")
    assert err.value.code == ExitCode.INVALID_LINK


def test_build_output_filename_template_rejects_invalid_format() -> None:
    with pytest.raises(TelegrabError) as err:
        build_output_filename("A", 1, ".mp4", "{channel-{message_id}")
    assert err.value.code == ExitCode.INVALID_LINK


def test_build_output_filename_template_rejects_control_chars() -> None:
    with pytest.raises(TelegrabError) as err:
        build_output_filename("A", 1, ".mp4", "bad\nname")
    assert err.value.code == ExitCode.INVALID_LINK


def test_normalize_output_dir_rejects_existing_file(tmp_path: Path) -> None:
    file_path = tmp_path / "artifact.txt"
    file_path.write_text("x", encoding="utf-8")

    with pytest.raises(TelegrabError) as err:
        normalize_output_dir(file_path)
    assert err.value.code == ExitCode.INVALID_LINK


class _FakeGateway:
    def __init__(self, message):
        self._entity = SimpleNamespace(username="demo", id=123)
        self._message = message
        self.download_called = False

    async def resolve_entity(self, parsed_link):
        return self._entity

    async def get_message(self, entity, message_id):
        return self._message

    async def download_media(self, message, destination, progress_callback=None):
        self.download_called = True
        destination.write_text("video", encoding="utf-8")
        return destination


def test_download_dry_run_does_not_create_files(tmp_path: Path) -> None:
    gateway = _FakeGateway(_fake_message(video=object(), file_ext=".mp4"))
    output_dir = tmp_path / "downloads"

    result = asyncio.run(
        download_video_from_link(
            gateway=gateway,
            telegram_link="https://t.me/demo/42",
            output_dir=output_dir,
            dry_run=True,
        )
    )

    assert result.dry_run is True
    assert result.file_path is None
    assert result.would_write_to == str((output_dir / "demo_42.mp4").resolve())
    assert gateway.download_called is False
    assert output_dir.exists() is False
