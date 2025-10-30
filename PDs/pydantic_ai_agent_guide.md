## General Instruction
- Place the relevant agent code in `agent.py` file
- Place the `agent.py` file as instructed in the folder structure file `pydantic_ai_project_structure.md`


### Base Agent Template
```python
import os

from dotenv import load_dotenv

from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import load_mcp_servers
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_agent_prompt
from src.libs.utils.config_loader import load_mcp_config
from src.libs.agent_memory.context_memory import save_context, load_context

load_dotenv()

class {AgentName}:
    AGENT_ID = "{agent_name}"

    def __init__(self, session_id: str):
        self.session_id = session_id

        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = load_agent_prompt(__file__)

        servers = load_mcp_servers(load_mcp_config(__file__))

        self.messages = load_context(self.AGENT_ID, session_id)

        self.agent = Agent(
            llm_model,
            system_prompt=system_prompt,
            toolsets=servers
        )
    
    def run(self, prompt: str) -> AgentRunResult:
        agent_output = self.agent.run_sync(prompt, message_history=self.messages)
        self.messages = agent_output.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
        return agent_output
```