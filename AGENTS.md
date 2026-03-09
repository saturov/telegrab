# AGENTS.md

## Project Purpose

`telegrab` is a Python CLI utility for downloading a single video from a specific Telegram post link via a user MTProto session. The project does not use the Bot API, does not bypass protected content restrictions, and must remain predictable for automation: commands expose stable exit codes and JSON responses.

## Project Structure

- `src/telegrab/cli.py` - Typer-based CLI entrypoint, text/JSON output formatting, commands `login`, `status`, `fetch`, `doctor`, `describe`.
- `src/telegrab/config.py` - runtime config loading from env and JSON file, path resolution via `platformdirs`.
- `src/telegrab/telegram_client.py` - wrapper around `Telethon`, login, authorization checks, entity/message lookup, media download, and Telegram error mapping into internal exit codes.
- `src/telegrab/downloader.py` - download preparation flow, path normalization, filename template validation, `.part` handling, and atomic move into the final path.
- `src/telegrab/link_parser.py` and `src/telegrab/validation.py` - input validation and Telegram link parsing.
- `src/telegrab/models.py` - domain dataclasses, shared JSON result schema, `ExitCode`, `TelegrabError`.
- `src/telegrab/introspection.py` - machine-readable command descriptions for agent workflows.
- `tests/` - unit, CLI, and integration tests.
- `README.md` - user-facing documentation and common usage examples.
- `pyproject.toml` - dependencies, entrypoint, and pytest configuration.

## Important Technical Aspects

- Minimum Python version: `3.12+`.
- Primary stack: `typer`, `rich`, `telethon`, `platformdirs`, `pytest`.
- The codebase uses a `src/` layout, so new modules should be added under `src/telegrab/`.
- Runtime config is loaded from `TELEGRAB_API_ID` / `TELEGRAB_API_HASH` or from a JSON config file; environment variables take precedence.
- The local Telegram session is stored outside the repository via `platformdirs`; never hardcode or commit real credentials or session files.
- The `fetch` command must preserve its contract:
  - one input URL;
  - one video output;
  - reproducible exit codes;
  - stable JSON when `--output json` is used.
- Telegram errors should go through the centralized mapping in `telegram_client.py`; avoid scattered `except` branches with inconsistent behavior.
- Downloads use a temporary `.part` file followed by rename; changes in this flow must preserve protection against partially written output.
- Access to private channels works only if the current Telegram user is already a member.
- Integration tests require real Telegram credentials and test links passed through environment variables.

## Quality Control

- Dev environment setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

- Baseline verification before finishing work:

```bash
pytest
```

- Run integration checks separately and only when the required env vars are present:

```bash
pytest -m integration
```

- For safe manual CLI verification without writing files, prefer:

```bash
telegrab doctor
telegrab describe fetch
telegrab fetch "<telegram-link>" --dry-run --output json
```

- When changing the CLI, preserve:
  - backward-compatible exit codes;
  - JSON response structure;
  - test coverage for the affected behavior.

## AI Development Process

1. Read `README.md`, `pyproject.toml`, and the affected modules first instead of assuming the architecture.
2. Before changing CLI behavior, determine whether the user-facing contract changes: arguments, error text, JSON shape, exit codes, or path formatting.
3. Keep changes localized:
   - Telegram behavior belongs in `telegram_client.py`;
   - file preparation rules belong in `downloader.py`;
   - interface and response serialization belong in `cli.py` and `models.py`.
4. For every meaningful behavioral change, add or update a test in `tests/`.
5. For network-related scenarios, prefer unit/CLI tests and `--dry-run` first; real Telegram calls are for cases that cannot be validated otherwise.
6. Do not commit artifacts from `downloads/`, `__pycache__`, real private channel links, API credentials, or session files.
7. If the change affects agent workflows, verify `doctor`, `describe`, and JSON output as part of acceptance.
8. All commit messages must follow the Conventional Commits format, for example: `feat: add JSON output for status` or `docs: add agent workflow notes`.

## Practical Guidance For Future Agents

- If the result schema changes, update the dataclass in `models.py` first, then adjust serialization/output and CLI tests.
- If Telegram error handling changes, update the single mapping point in `map_telegram_error`.
- If filename or path behavior changes, account for `ensure_no_control_chars`, the `{channel}-{message_id}.{ext}` template, and the ban on path separators in templates.
- If a new CLI command is added, support both human-readable and JSON output modes.
