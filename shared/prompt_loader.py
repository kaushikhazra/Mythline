"""Load prompt files from an agent's prompts/ directory.

Every agent stores its prompts as .md files under a ``prompts/`` folder
that sits alongside the agent's source code.  This module provides a
single helper that resolves prompts relative to the *caller's* location,
so each agent can simply call::

    from shared.prompt_loader import load_prompt

    system = load_prompt(__file__, "system_prompt")
    xref   = load_prompt(__file__, "cross_reference")

The caller passes ``__file__`` so the resolver always finds the correct
``prompts/`` directory regardless of the working directory at runtime.
"""

from pathlib import Path


def load_prompt(caller_file: str, prompt_name: str) -> str:
    """Read a prompt markdown file relative to the caller's agent root.

    The prompts directory is expected at ``<agent_root>/prompts/``, where
    ``<agent_root>`` is the grandparent of the caller file (i.e. two
    levels up from ``src/agent.py`` -> ``a_<agent>/prompts/``).

    Args:
        caller_file: The ``__file__`` of the calling module.
        prompt_name: Name of the prompt (without .md extension).

    Returns:
        The prompt text.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    agent_root = Path(caller_file).resolve().parent.parent
    prompt_path = agent_root / "prompts" / f"{prompt_name}.md"
    return prompt_path.read_text(encoding="utf-8")
