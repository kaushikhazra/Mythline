"""Test environment setup — adds repo root to sys.path for shared/ imports."""

import os
import sys
from pathlib import Path

# Set dummy API key before any pydantic-ai Agent is constructed at import time.
# Tests mock the agent — the key is never used for real API calls.
os.environ.setdefault("OPENROUTER_API_KEY", "test-key-for-tests")

repo_root = str(Path(__file__).resolve().parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
