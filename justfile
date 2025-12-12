[private]
default:
    @just --list

check:
    uv run ruff format --check
    uv run ruff check
    uv run mypy .
    uv run python -m unittest

format:
    uv run ruff format
    uv run ruff check --fix-only
