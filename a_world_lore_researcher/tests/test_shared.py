"""Tests for shared utilities — prompt_loader and config_loader."""

import json
import os

import pytest

import src.agent as agent_module
from shared.prompt_loader import load_prompt
from shared.config_loader import load_mcp_config, _expand_env_vars


class TestPromptLoader:
    def test_loads_existing_prompt(self):
        prompt = load_prompt(agent_module.__file__, "system_prompt")
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_raises_for_missing_prompt(self):
        with pytest.raises(FileNotFoundError):
            load_prompt(agent_module.__file__, "nonexistent_prompt")


class TestExpandEnvVars:
    def test_expands_set_variable(self, monkeypatch):
        monkeypatch.setenv("TEST_VAR", "hello")
        assert _expand_env_vars("${TEST_VAR}") == "hello"

    def test_expands_with_default(self, monkeypatch):
        monkeypatch.delenv("UNSET_VAR", raising=False)
        assert _expand_env_vars("${UNSET_VAR:-fallback}") == "fallback"

    def test_uses_value_over_default(self, monkeypatch):
        monkeypatch.setenv("SET_VAR", "real")
        assert _expand_env_vars("${SET_VAR:-fallback}") == "real"

    def test_raises_for_unset_no_default(self, monkeypatch):
        monkeypatch.delenv("MISSING_VAR", raising=False)
        with pytest.raises(ValueError, match="MISSING_VAR"):
            _expand_env_vars("${MISSING_VAR}")

    def test_leaves_plain_strings_alone(self):
        assert _expand_env_vars("no vars here") == "no vars here"

    def test_multiple_vars_in_string(self, monkeypatch):
        monkeypatch.setenv("HOST", "localhost")
        monkeypatch.setenv("PORT", "8006")
        assert _expand_env_vars("http://${HOST}:${PORT}/mcp") == "http://localhost:8006/mcp"


class TestLoadMcpConfig:
    def test_loads_servers_from_json(self, monkeypatch):
        monkeypatch.setenv("MCP_WEB_SEARCH_URL", "http://localhost:8006/mcp")

        servers = load_mcp_config(agent_module.__file__)

        assert len(servers) == 1
        prefixes = {s.tool_prefix for s in servers}
        assert prefixes == {"search"}

    def test_timeout_passed_through(self, monkeypatch):
        monkeypatch.setenv("MCP_WEB_SEARCH_URL", "http://localhost:8006/mcp")

        servers = load_mcp_config(agent_module.__file__)

        by_prefix = {s.tool_prefix: s for s in servers}
        assert by_prefix["search"].timeout == 30

    def test_url_expanded_from_env(self, monkeypatch):
        monkeypatch.setenv("MCP_WEB_SEARCH_URL", "http://custom-host:9999/mcp")

        servers = load_mcp_config(agent_module.__file__)

        by_prefix = {s.tool_prefix: s for s in servers}
        assert by_prefix["search"].url == "http://custom-host:9999/mcp"

    def test_raises_for_missing_config(self, tmp_path):
        fake_file = str(tmp_path / "src" / "agent.py")
        os.makedirs(os.path.dirname(fake_file), exist_ok=True)
        with open(fake_file, "w") as f:
            f.write("")

        with pytest.raises(FileNotFoundError):
            load_mcp_config(fake_file)
