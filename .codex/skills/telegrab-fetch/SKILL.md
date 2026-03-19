---
name: telegrab-fetch
description: Use when the user needs to download one Telegram video from a post link through this repository's telegrab CLI with deterministic preflight checks and machine-readable result fields.
---

# Telegrab Fetch

Use this skill for one practical task: download a single video from one Telegram post link and return the local file path plus fetch metadata.

## When to use

- The user provides (or wants to provide) one `t.me` or `telegram.me` post link.
- The user expects the agent to run the local `telegrab` utility in this repository.
- The user needs a predictable result that can be reused by another step.

## Inputs

- Required:
  - `telegram_link`
- Optional:
  - `output_dir` (default `./downloads`)
  - `name_template` (pass through to `--name-template`)
  - `overwrite` (boolean, default `false`)

If the link is missing, ask only for the link. Do not ask extra questions when defaults are acceptable.

## Required workflow

Always execute in this order, using JSON mode:

1. `doctor --output json`
2. `status --output json`
3. `fetch <link> --output json` (plus optional flags)

Run CLI commands via `bash scripts/run_telegrab.sh` to ensure the repository venv and `PYTHONPATH=src` are used.

## Decision rules

- If `doctor` reports missing credentials (`credentials_present=false`), stop and explain:
  - where config is expected (`config_path` from doctor),
  - that credentials must be set (`TELEGRAB_API_ID`, `TELEGRAB_API_HASH`, or config file).
- If `status` reports `authorized=false`, stop and instruct the user to run `telegrab login` manually.
- Do not try to automate interactive login prompts.
- If preflight passes, run the real `fetch` directly (no mandatory dry-run step).

## Output contract

On success, return:

- `file_path`
- `source_url`
- `message_id`
- `chat_id`
- `exit_code`

On failure, return:

- `exit_code`
- `error_code`
- `error_message`

Preserve telegrab semantics. Do not reinterpret or remap exit codes; treat CLI JSON as source of truth.

## Error handling

For known failures, keep the message short and actionable:

- `2`: invalid link/input
- `3`: credentials or authorization missing
- `4`: channel/message inaccessible
- `5`: message has no video
- `6`: content restriction
- `7`: Telegram/runtime error

When reporting an error, include original `error_message` from CLI output.
