#! /bin/bash
export LD_LIBRARY_PATH="$(pwd)/bin/lib:${LD_LIBRARY_PATH:-}"
export PATH="$(pwd)/bin/bin:${PATH}"

echo "Syncing dependencies and cleaning cache..."

curl -LsSf https://astral.sh/uv/install.sh | sh

$HOME/.local/bin/uv sync
$HOME/.local/bin/uv clean cache
$HOME/.local/bin/uv clean size

echo "Running the bot..."

$HOME/.local/bin/uv run main.py