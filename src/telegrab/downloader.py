from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from telegrab.link_parser import parse_telegram_post_link
from telegrab.models import ExitCode, PreparedDownload, TelegrabError
from telegrab.validation import ensure_no_control_chars

ProgressCallback = Callable[[int, int], Any]

_MIME_TO_EXT = {
    "video/mp4": ".mp4",
    "video/x-matroska": ".mkv",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}


def _sanitize_filename_component(value: str) -> str:
    sanitized = re.sub(r"[^\w.-]+", "_", value.strip())
    sanitized = sanitized.strip("._")
    return sanitized or "channel"


def normalize_output_dir(output_dir: Path) -> Path:
    output_dir_text = ensure_no_control_chars(str(output_dir), "Output directory")
    normalized = Path(output_dir_text).expanduser()

    if normalized.exists() and not normalized.is_dir():
        raise TelegrabError(ExitCode.INVALID_LINK, f"Output directory points to a file: {normalized}")

    return normalized.resolve(strict=False)


def is_video_message(message: Any) -> bool:
    if getattr(message, "video", None) is not None:
        return True

    document = getattr(message, "document", None)
    if document is None:
        return False

    mime_type = getattr(document, "mime_type", "") or ""
    if mime_type.startswith("video/"):
        return True

    attributes = getattr(document, "attributes", None) or []
    return any(attr.__class__.__name__ == "DocumentAttributeVideo" for attr in attributes)


def guess_video_extension(message: Any) -> str:
    file_obj = getattr(message, "file", None)
    ext = getattr(file_obj, "ext", None) if file_obj else None
    if isinstance(ext, str) and ext.strip():
        ext = ext.strip()
        return ext if ext.startswith(".") else f".{ext}"

    document = getattr(message, "document", None)
    mime_type = getattr(document, "mime_type", "") if document else ""
    mapped = _MIME_TO_EXT.get(mime_type.lower())
    return mapped or ".mp4"


def build_output_filename(
    channel_name: str,
    message_id: int,
    extension: str,
    name_template: str | None = None,
) -> str:
    safe_channel = _sanitize_filename_component(channel_name)
    normalized_ext = extension if extension.startswith(".") else f".{extension}"
    ext_without_dot = normalized_ext.lstrip(".")

    if name_template:
        ensure_no_control_chars(name_template, "Name template")
        try:
            name = name_template.format(
                channel=safe_channel,
                message_id=message_id,
                ext=ext_without_dot,
            )
        except (KeyError, ValueError) as exc:
            raise TelegrabError(ExitCode.INVALID_LINK, f"Invalid name template: {exc}") from exc
        if "/" in name or "\\" in name:
            raise TelegrabError(ExitCode.INVALID_LINK, "Name template must not include path separators.")
        if not Path(name).suffix:
            name = f"{name}{normalized_ext}"
        return name

    return f"{safe_channel}_{message_id}{normalized_ext}"


def extract_channel_label(entity: Any) -> str:
    return (
        getattr(entity, "username", None)
        or getattr(entity, "title", None)
        or str(getattr(entity, "id", "channel"))
    )


def _extract_chat_id(entity: Any) -> int | None:
    try:
        from telethon import utils as telethon_utils

        return telethon_utils.get_peer_id(entity)
    except Exception:
        value = getattr(entity, "id", None)
        return int(value) if isinstance(value, int) else None


async def prepare_download(
    gateway: Any,
    telegram_link: str,
    output_dir: Path,
    name_template: str | None = None,
    overwrite: bool = False,
) -> tuple[PreparedDownload, Any]:
    parsed_link = parse_telegram_post_link(telegram_link)
    normalized_output_dir = normalize_output_dir(output_dir)

    entity = await gateway.resolve_entity(parsed_link)
    message = await gateway.get_message(entity, parsed_link.message_id)

    if not is_video_message(message):
        raise TelegrabError(ExitCode.NO_VIDEO, "The referenced Telegram message does not contain a video.")

    extension = guess_video_extension(message)
    channel_label = extract_channel_label(entity)
    file_name = build_output_filename(channel_label, parsed_link.message_id, extension, name_template)
    final_path = normalized_output_dir / file_name

    if final_path.exists() and not overwrite:
        raise TelegrabError(
            ExitCode.API_ERROR,
            f"Destination file already exists: {final_path}. Use --overwrite to replace it.",
        )

    prepared = PreparedDownload(
        source_url=parsed_link.source_url,
        message_id=parsed_link.message_id,
        would_write_to=str(final_path.resolve(strict=False)),
        chat_id=_extract_chat_id(entity),
    )
    return prepared, message


async def download_video_from_link(
    gateway: Any,
    telegram_link: str,
    output_dir: Path,
    name_template: str | None = None,
    overwrite: bool = False,
    progress_callback: ProgressCallback | None = None,
    dry_run: bool = False,
) -> PreparedDownload:
    prepared, message = await prepare_download(
        gateway=gateway,
        telegram_link=telegram_link,
        output_dir=output_dir,
        name_template=name_template,
        overwrite=overwrite,
    )

    if dry_run:
        return PreparedDownload(
            source_url=prepared.source_url,
            message_id=prepared.message_id,
            would_write_to=prepared.would_write_to,
            chat_id=prepared.chat_id,
            dry_run=True,
        )

    final_path = Path(prepared.would_write_to or "")
    final_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = final_path.with_name(f"{final_path.name}.part")
    if tmp_path.exists():
        tmp_path.unlink()

    downloaded_path = await gateway.download_media(message, tmp_path, progress_callback=progress_callback)
    if downloaded_path != tmp_path and downloaded_path.exists():
        tmp_path = downloaded_path

    tmp_path.replace(final_path)

    return PreparedDownload(
        source_url=prepared.source_url,
        message_id=prepared.message_id,
        file_path=str(final_path.resolve()),
        would_write_to=str(final_path.resolve()),
        chat_id=prepared.chat_id,
        dry_run=False,
    )
