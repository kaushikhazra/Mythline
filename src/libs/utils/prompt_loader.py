import os


def load_system_prompt(caller_file):
    agent_dir = os.path.dirname(os.path.abspath(caller_file))
    prompt_path = os.path.join(agent_dir, "prompts", "system_prompt.md")

    with open(prompt_path, "r") as file:
        return file.read()


def load_prompt(caller_file, prompt_name):
    agent_dir = os.path.dirname(os.path.abspath(caller_file))
    prompt_path = os.path.join(agent_dir, "prompts", f"{prompt_name}.md")

    with open(prompt_path, "r") as file:
        return file.read()
