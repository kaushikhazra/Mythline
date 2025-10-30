## General Instructions
- Store the system prompt in `system_prompt.md` in the folder described in `pydantic_ai_project_structure.md`
- Every system should have only one system prompt to make it responsible for only one kind of task

## System Prompt Templates
Templates are allowed to be mixed and matched after confirming from user

### Basic Template

```markdown
## Persona
You are a|an {Persona}

## Task
Your task is to {the task}

## Instructions
Follow the below instructions to perform your task
- Instruction 1
- Instruction 2
...
- Instruction n

## Constraints
- Avoid {what to avoid}
- Important {what is important}
...
- {Any other constraint}

## Output
{specify output format based on the requirement}

```

### Conditional Operation Template
```markdown
## Persona
You are a|an {Persona}

## Task
Your task is to {the task}

## Instructions
1. {Describe an operation step}
2. If {describe a condition from the outcome of the above operation}
    1. {Describe an operation step}
    2. {describe an operation step}
    3. If {describe a condition from the outcome of the above operation}
        {Repeat same conditional approach}


## Constraints
- Avoid {what to avoid}
- Important {what is important}
...
- {Any other constraint}

## Output
{specify output format based on the requirement}
```