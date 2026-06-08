#! /bin/bash

echo "Syncing dependencies and cleaning cache..."

curl -LsSf https://astral.sh/uv/install.sh | sh

$HOME/.local/bin/uv sync
$HOME/.local/bin/uv clean cache
$HOME/.local/bin/uv clean size

git clean -fdx
git gc --prune=now
git rm --cached -r .

echo "Running the bot..."

$HOME/.local/bin/uv run main.py