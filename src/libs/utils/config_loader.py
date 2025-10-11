import os


def load_mcp_config(caller_file):
    """
    Load the MCP config file path from the agent's config folder.

    Args:
        caller_file: The __file__ variable from the calling agent script

    Returns:
        str: Full path to mcp_config.json in agent's config folder
    """
    # Get agent directory
    agent_dir = os.path.dirname(os.path.abspath(caller_file))

    # Build path to config/mcp_config.json in agent folder
    config_path = os.path.join(agent_dir, "config", "mcp_config.json")

    return config_path
