## General Instruction
- Place the `cli.py` file as instructed in the folder structure file `pydantic_ai_project_structure.md`


## `cli.py`
```python
# Imports at the top

# Argument parsing using arg parser

# Invoke the agent to produce output
```

## Example CLI With Session Loading

```python
from src.agents.story_creator_agent.agent import StoryCreator
from src.libs.utils.argument_parser import get_session


session_id = get_session(StoryCreator.AGENT_ID)
print(f"Session: {session_id}\n")
story_creator = StoryCreator(session_id)

while True:
    prompt = input("🙍 User‍: ")

    if prompt == "exit":
        break

    response = story_creator.run(prompt)
    print(f"\n🤖 Agent: {response.output} \n\n")
```