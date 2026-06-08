#! /bin/bash

echo "Syncing dependencies and cleaning cache..."

$HOME/.local/bin/uv sync
$HOME/.local/bin/uv clean cache
$HOME/.local/bin/uv clean size

echo "Running the bot..."

$HOME/.local/bin/uv run main.py