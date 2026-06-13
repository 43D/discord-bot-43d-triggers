#! /bin/bash
export LD_LIBRARY_PATH="$(pwd)/bin/lib:${LD_LIBRARY_PATH:-}"
export PATH="$(pwd)/bin/bin:${PATH}"
uv sync
echo "Running the bot..."
uv run main.py