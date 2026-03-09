from __future__ import annotations

import asyncio
import json
from enum import Enum
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeRemainingColumn

from telegrab import __version__
from telegrab.config import RuntimeEnvironment, inspect_runtime_environment, load_runtime_config
from telegrab.downloader import download_video_from_link
from telegrab.introspection import describe_command
from telegrab.models import CommandResult, DescribeResult, DoctorResult, ExitCode, FetchResult, StatusResult, TelegrabError
from telegrab.telegram_client import TelegramGateway
from telegrab.validation import ensure_no_control_chars


class OutputMode(str, Enum):
    TEXT = "text"
    JSON = "json"


app = typer.Typer(no_args_is_help=True, help="Download a single Telegram video from one message link.")
stderr_console = Console(stderr=True)


def _print_json(payload: dict[str, Any]) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False))


def _emit_fetch_result(result: FetchResult, output: OutputMode) -> None:
    if output is OutputMode.JSON:
        _print_json(result.to_dict())
        return

    if result.status == "ok":
        if result.dry_run:
            typer.echo(f"Would write to: {result.would_write_to}")
        else:
            typer.echo(result.file_path or "")
        return

    typer.echo(result.error_message or "Unknown error.", err=True)


def _emit_status_result(result: StatusResult, output: OutputMode) -> None:
    if output is OutputMode.JSON:
        _print_json(result.to_dict())
        return

    if result.status == "ok" and result.authorized:
        display_name = result.username or result.user_id or "unknown"
        typer.echo(f"Authorized: {display_name}")
        return

    if result.error_message:
        typer.echo(result.error_message, err=True)
        return

    typer.echo("Not authorized. Run: telegrab login", err=True)


def _emit_doctor_result(result: DoctorResult, output: OutputMode) -> None:
    if output is OutputMode.JSON:
        _print_json(result.to_dict())
        return

    if result.status != "ok":
        typer.echo(result.error_message or "Unknown error.", err=True)
        return

    typer.echo(f"Version: {result.version}")
    typer.echo(f"Config path: {result.config_path}")
    typer.echo(f"Data dir: {result.data_dir}")
    typer.echo(f"Session path: {result.session_path}")
    typer.echo(f"Credentials present: {'yes' if result.credentials_present else 'no'}")
    typer.echo(f"Credentials source: {result.credentials_source}")
    typer.echo(f"Session present: {'yes' if result.session_present else 'no'}")


def _emit_describe_result(result: DescribeResult, output: OutputMode) -> None:
    if output is OutputMode.JSON:
        _print_json(result.to_dict())
        return

    typer.echo(f"Target: {result.target}")
    typer.echo(result.description.get("summary", ""))
    commands = result.description.get("commands")
    if commands:
        typer.echo(f"Commands: {', '.join(commands)}")

    arguments = result.description.get("arguments", [])
    if arguments:
        typer.echo("Arguments:")
        for argument in arguments:
            requirement = "required" if argument.get("required") else "optional"
            typer.echo(f"- {argument['name']} ({argument['type']}, {requirement})")

    options = result.description.get("options", [])
    if options:
        typer.echo("Options:")
        for option in options:
            default = option.get("default")
            typer.echo(f"- {option['name']} ({option['type']}, default={default})")


def _emit_command_error(result: CommandResult, output: OutputMode) -> None:
    if output is OutputMode.JSON:
        _print_json(result.to_dict())
    else:
        typer.echo(result.error_message or "Unknown error.", err=True)


def _fetch_error_result(source_url: str, dry_run: bool, err: TelegrabError) -> FetchResult:
    return FetchResult(
        command="fetch",
        status="error",
        exit_code=int(err.code),
        error_code=int(err.code),
        error_message=err.message,
        source_url=source_url,
        dry_run=dry_run,
    )


def _status_error_result(command: str, err: TelegrabError) -> StatusResult:
    return StatusResult(
        command=command,
        status="error",
        exit_code=int(err.code),
        error_code=int(err.code),
        error_message=err.message,
        authorized=False,
    )


def _doctor_error_result(err: TelegrabError) -> DoctorResult:
    return DoctorResult(
        command="doctor",
        status="error",
        exit_code=int(err.code),
        error_code=int(err.code),
        error_message=err.message,
        version=__version__,
        config_path="",
        data_dir="",
        session_path="",
        credentials_present=False,
        credentials_source="missing",
        session_present=False,
    )


def _describe_error_result(target: str, err: TelegrabError) -> DescribeResult:
    return DescribeResult(
        command="describe",
        status="error",
        exit_code=int(err.code),
        error_code=int(err.code),
        error_message=err.message,
        target=target,
        description={},
    )


def _session_present(environment: RuntimeEnvironment) -> bool:
    session_file = environment.session_stem.with_suffix(".session")
    if session_file.exists():
        return True
    return any(environment.data_dir.glob(f"{environment.session_stem.name}.session*"))


async def _login(cfg: Any, phone: str | None) -> None:
    async with TelegramGateway(cfg) as gateway:
        await gateway.login(phone=phone)


async def _status(cfg: Any) -> tuple[bool, Any]:
    async with TelegramGateway(cfg) as gateway:
        authorized = await gateway.is_authorized()
        user = await gateway.get_self_user() if authorized else None
        return authorized, user


async def _fetch(
    cfg: Any,
    telegram_link: str,
    output_dir: Path,
    name_template: str | None,
    overwrite: bool,
    dry_run: bool,
    output: OutputMode,
) -> FetchResult:
    async with TelegramGateway(cfg) as gateway:
        if not await gateway.is_authorized():
            raise TelegrabError(ExitCode.NOT_AUTHORIZED, "Not authorized. Run: telegrab login")

        if dry_run or output is OutputMode.JSON or not stderr_console.is_terminal:
            prepared = await download_video_from_link(
                gateway=gateway,
                telegram_link=telegram_link,
                output_dir=output_dir,
                name_template=name_template,
                overwrite=overwrite,
                dry_run=dry_run,
            )
            return prepared.to_fetch_result()

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=stderr_console,
            transient=True,
        ) as progress:
            task_id = progress.add_task("Downloading video", total=100)

            def on_progress(current: int, total: int) -> None:
                progress.update(task_id, completed=current, total=max(total, 1))

            prepared = await download_video_from_link(
                gateway=gateway,
                telegram_link=telegram_link,
                output_dir=output_dir,
                name_template=name_template,
                overwrite=overwrite,
                progress_callback=on_progress,
                dry_run=False,
            )
            return prepared.to_fetch_result()


@app.command("fetch")
def fetch(
    telegram_link: str = typer.Argument(..., help="Telegram post link."),
    output_dir: Path = typer.Option(Path("./downloads"), "--output-dir", help="Directory for downloaded video."),
    name_template: str | None = typer.Option(
        None,
        "--name-template",
        help="Optional filename template. Supported placeholders: {channel}, {message_id}, {ext}.",
    ),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite destination file if it exists."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate and inspect the download without writing files."),
    output: OutputMode = typer.Option(OutputMode.TEXT, "--output", help="Output mode: text or json."),
) -> None:
    try:
        telegram_link = ensure_no_control_chars(telegram_link, "Telegram post link")
        cfg = load_runtime_config()
        result = asyncio.run(
            _fetch(
                cfg=cfg,
                telegram_link=telegram_link,
                output_dir=output_dir,
                name_template=name_template,
                overwrite=overwrite,
                dry_run=dry_run,
                output=output,
            )
        )
        _emit_fetch_result(result, output)
        raise typer.Exit(code=int(ExitCode.SUCCESS))
    except TelegrabError as err:
        result = _fetch_error_result(telegram_link, dry_run, err)
        _emit_fetch_result(result, output)
        raise typer.Exit(code=int(err.code))


@app.command("login")
def login(
    phone: str | None = typer.Option(None, "--phone", help="Phone number including country code."),
    output: OutputMode = typer.Option(OutputMode.TEXT, "--output", help="Output mode: text or json."),
) -> None:
    try:
        phone_value = ensure_no_control_chars(phone, "Phone number", code=ExitCode.NOT_AUTHORIZED) if phone else None
        cfg = load_runtime_config()
        asyncio.run(_login(cfg, phone_value))
        result = StatusResult(
            command="login",
            status="ok",
            exit_code=int(ExitCode.SUCCESS),
            authorized=True,
        )
        if output is OutputMode.JSON:
            _print_json(result.to_dict())
        else:
            typer.echo("Login successful.")
        raise typer.Exit(code=int(ExitCode.SUCCESS))
    except TelegrabError as err:
        result = _status_error_result("login", err)
        _emit_command_error(result, output)
        raise typer.Exit(code=int(err.code))


@app.command("status")
def status(
    output: OutputMode = typer.Option(OutputMode.TEXT, "--output", help="Output mode: text or json."),
) -> None:
    try:
        cfg = load_runtime_config()
        authorized, user = asyncio.run(_status(cfg))
        result = StatusResult(
            command="status",
            status="ok" if authorized else "error",
            exit_code=int(ExitCode.SUCCESS if authorized else ExitCode.NOT_AUTHORIZED),
            error_code=None if authorized else int(ExitCode.NOT_AUTHORIZED),
            error_message=None if authorized else "Not authorized. Run: telegrab login",
            authorized=authorized,
            user_id=getattr(user, "id", None) if user else None,
            username=getattr(user, "username", None) if user else None,
        )
        _emit_status_result(result, output)
        raise typer.Exit(code=result.exit_code)
    except TelegrabError as err:
        result = _status_error_result("status", err)
        _emit_status_result(result, output)
        raise typer.Exit(code=int(err.code))


@app.command("doctor")
def doctor(
    output: OutputMode = typer.Option(OutputMode.TEXT, "--output", help="Output mode: text or json."),
) -> None:
    try:
        environment = inspect_runtime_environment()
        result = DoctorResult(
            command="doctor",
            status="ok",
            exit_code=int(ExitCode.SUCCESS),
            version=__version__,
            config_path=str(environment.config_path),
            data_dir=str(environment.data_dir),
            session_path=str(environment.session_stem.with_suffix(".session")),
            credentials_present=environment.credentials_present,
            credentials_source=environment.credentials_source,
            session_present=_session_present(environment),
        )
        _emit_doctor_result(result, output)
        raise typer.Exit(code=int(ExitCode.SUCCESS))
    except TelegrabError as err:
        result = _doctor_error_result(err)
        _emit_doctor_result(result, output)
        raise typer.Exit(code=int(err.code))


@app.command("describe")
def describe(
    command_name: str | None = typer.Argument(None, help="Optional command name to describe."),
    output: OutputMode = typer.Option(OutputMode.JSON, "--output", help="Output mode: text or json."),
) -> None:
    target = (command_name or "telegrab").strip()

    try:
        normalized, description = describe_command(command_name)
        result = DescribeResult(
            command="describe",
            status="ok",
            exit_code=int(ExitCode.SUCCESS),
            target=normalized,
            description=description,
        )
        _emit_describe_result(result, output)
        raise typer.Exit(code=int(ExitCode.SUCCESS))
    except TelegrabError as err:
        result = _describe_error_result(target, err)
        _emit_describe_result(result, output)
        raise typer.Exit(code=int(err.code))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
