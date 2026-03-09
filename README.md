# Telegrab

CLI utility for downloading a single video from a Telegram post link using your own Telegram user session (MTProto).

## Features

- Downloads video from a post link:
  - `https://t.me/<username>/<message_id>`
  - `https://t.me/c/<internal_channel_id>/<message_id>`
  - `https://telegram.me/...` equivalents
- Works with private channels if your logged-in Telegram account is already a member.
- Stores Telethon session locally via `platformdirs`.
- Provides stable machine-readable output with `--output json`.
- Supports `doctor`, `describe`, and `fetch --dry-run` for automation and agent workflows.

## Requirements

- Python 3.12+
- Telegram API credentials: `api_id` and `api_hash`

Get credentials at: https://my.telegram.org

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Configuration

Preferred way is environment variables:

```bash
export TELEGRAB_API_ID=123456
export TELEGRAB_API_HASH=0123456789abcdef0123456789abcdef
```

Alternative config file:

- Path: run `telegrab doctor` to see the exact config path for your environment.
- Content:

```json
{
  "api_id": 123456,
  "api_hash": "0123456789abcdef0123456789abcdef"
}
```

## Usage

First-time login:

```bash
telegrab login
```

Check authorization:

```bash
telegrab status
```

Download a video:

```bash
telegrab fetch "https://t.me/some_channel/123"
```

Download to custom folder:

```bash
telegrab fetch "https://t.me/c/123456/789" --output-dir ./downloads
```

With template and JSON output:

```bash
telegrab fetch "https://t.me/some_channel/123" --name-template "{channel}-{message_id}.{ext}" --output json
```

Overwrite existing file:

```bash
telegrab fetch "https://t.me/some_channel/123" --overwrite
```

Dry-run a download without writing files:

```bash
telegrab fetch "https://t.me/some_channel/123" --dry-run
```

Inspect local configuration and session paths:

```bash
telegrab doctor
```

Describe the CLI in JSON:

```bash
telegrab describe fetch
```

## Exit codes

- `0` success
- `2` invalid link/input
- `3` not authorized / missing credentials
- `4` channel/message inaccessible
- `5` message has no video
- `6` Telegram content restriction
- `7` Telegram/network/runtime API error

## Notes

- This tool does not use Bot API.
- This tool does not bypass Telegram protected content restrictions.
- It only downloads one video from the exact message in the provided link.
- Telegram links with query parameters or fragments are rejected.
