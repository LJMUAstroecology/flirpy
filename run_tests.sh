#!/bin/sh
uv run pytest test
uv run coverage-badge -f -o coverage.svg
