#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../" && pwd)"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "telegrab-fetch: missing virtualenv python at ${PYTHON_BIN}" >&2
  echo "telegrab-fetch: create env and install deps: python3 -m venv .venv && .venv/bin/pip install -e .[dev]" >&2
  exit 3
fi

if [[ ! -f "${REPO_ROOT}/src/telegrab/cli.py" ]]; then
  echo "telegrab-fetch: telegrab sources not found under ${REPO_ROOT}/src/telegrab" >&2
  exit 7
fi

cd "${REPO_ROOT}"
exec env PYTHONPATH=src "${PYTHON_BIN}" -m telegrab.cli "$@"
