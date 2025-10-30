# Pydantic AI Coding Guide
_How to build an Agentic AI application using Pydantic AI and Pydantic echo system_
## Folder Structure
The folder structure is described in:
```bash
.\pydantic_ai_project_structure.md
```

## Configurations
The configurations are described in:
```bash
.\pydantic_ai_configurations.md
```

## System Prompts
The system prompts are described in:
```bash
.\pydantic_ai_prompt_guide.md
```

## Agents
The agents are described in:
```bash
.\pydantic_ai_agent_guide.md
```

## MCPs
The mcp server template and examples are described in:
```bash
.\mcps.md
```

## Libraries
The libraries are described in:
```bash
.\libs.md
```

## Interface
### CLI
The CLI interface is described in:
```bash
.\interface_cli.md
```

## Coding Style
- All imports should be at the top. Do NOT use inline imports
- Use Object Oriented Programming where necessary
- Use KISS philosophy.
- Avoid any extra validation and verification.
- Avoid adding any log statement.
- Follow the indentation as described in the sample codes.
- Follow the naming convention as used in the sample codes.
- The above structure is the sum of all. Pick and choose what is necessary for the project. 
- Avoid using version in `requirement.txt` so that latest can be used all the time.
- String indentation style
    ```python
    # Single string
    str = "Some value"

    # Multiline string
    str="""
        This is line 1
        this is line 2
    """
    ```