#! /bin/bash

echo "Syncing dependencies and cleaning cache..."

curl -LsSf https://astral.sh/uv/install.sh | sh

$HOME/.local/bin/uv sync
$HOME/.local/bin/uv clean cache
$HOME/.local/bin/uv clean size

echo "Running the bot..."

$HOME/.local/bin/uv run main.py