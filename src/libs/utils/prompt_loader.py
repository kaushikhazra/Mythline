import os


def load_agent_prompt(caller_file, prompt_name="system_prompt.md"):
    """
    Load a prompt file from the agent's prompts directory.

    Args:
        caller_file: The __file__ variable from the calling agent script
        prompt_name: Name of the prompt file (default: "system_prompt.md")

    Returns:
        str: Content of the prompt file
    """
    agent_dir = os.path.dirname(os.path.abspath(caller_file))
    prompt_path = os.path.join(agent_dir, "prompts", prompt_name)

    with open(prompt_path, "r") as file:
        return file.read()
