"""Load MCP server configuration from a per-agent JSON file.

Each agent stores its MCP wiring in ``config/mcp_config.json``.  The JSON
uses the same ``mcpServers`` schema as pydantic-ai, but we parse it
ourselves so that *all* constructor arguments (timeout, etc.) pass through
— pydantic-ai's built-in ``load_mcp_servers`` only accepts ``url`` and
``headers``.

Environment variable expansion is supported::

    "${MCP_WEB_SEARCH_URL}"          -> value of MCP_WEB_SEARCH_URL (error if unset)
    "${MCP_WEB_SEARCH_URL:-fallback}" -> value or "fallback"

Usage::

    from shared.config_loader import load_mcp_config

    servers = load_mcp_config(__file__)        # list of MCPServerStreamableHTTP
    agent = Agent(model, toolsets=servers)
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from pydantic_ai.mcp import MCPServerStreamableHTTP


_ENV_VAR_RE = re.compile(r"\$\{([^}]+)\}")


def _expand_env_vars(value: str) -> str:
    """Replace ``${VAR}`` / ``${VAR:-default}`` in a string."""

    def _replacer(match: re.Match) -> str:
        expr = match.group(1)
        if ":-" in expr:
            var_name, default = expr.split(":-", 1)
            return os.environ.get(var_name.strip(), default)
        var_name = expr.strip()
        val = os.environ.get(var_name)
        if val is None:
            raise ValueError(f"Environment variable '{var_name}' is not set and no default provided")
        return val

    return _ENV_VAR_RE.sub(_replacer, value)


def _expand_recursive(obj: object) -> object:
    """Walk a JSON-like structure and expand env vars in all strings."""
    if isinstance(obj, str):
        return _expand_env_vars(obj)
    if isinstance(obj, dict):
        return {k: _expand_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_recursive(item) for item in obj]
    return obj


def load_mcp_config(caller_file: str) -> list[MCPServerStreamableHTTP]:
    """Load MCP servers from the agent's ``config/mcp_config.json``.

    The config file sits at ``<agent_root>/config/mcp_config.json``, where
    ``<agent_root>`` is the grandparent of the caller (two levels up from
    ``src/agent.py``).

    The JSON schema mirrors pydantic-ai's convention::

        {
          "mcpServers": {
            "search": { "url": "${MCP_WEB_SEARCH_URL}", "timeout": 30 },
            "crawler": { "url": "${MCP_WEB_CRAWLER_URL}", "timeout": 60 }
          }
        }

    The dict key becomes the ``tool_prefix``.  All other keys are forwarded
    as keyword arguments to :class:`MCPServerStreamableHTTP`.

    Args:
        caller_file: The ``__file__`` of the calling module.

    Returns:
        A list of configured MCP server instances.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If a referenced env var is unset with no default.
    """
    agent_root = Path(caller_file).resolve().parent.parent
    config_path = agent_root / "config" / "mcp_config.json"

    raw = json.loads(config_path.read_text(encoding="utf-8"))
    expanded = _expand_recursive(raw)

    servers: list[MCPServerStreamableHTTP] = []
    for name, params in expanded["mcpServers"].items():
        params.setdefault("tool_prefix", name)
        servers.append(MCPServerStreamableHTTP(**params))

    return servers
