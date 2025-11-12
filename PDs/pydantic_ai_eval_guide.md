# Agent Evaluation Guide 
_Powered By Pydantic Evaluation Framework. Refer to https://ai.pydantic.dev/evals/ for more details_

## Evaluator Template
```python
import asyncio
from pathlib import Path

from pydantic import BaseModel, Field

from pydantic_evals import Dataset

from pydantic_evals.evaluators.common import LLMJudge, OutputConfig
from pydantic_evals.generation import generate_dataset

from src.agents.{agent_name}.agent import {AgentClass}
from src.libs.utils.prompt_loader import load_prompt

{agent_name} = {Agentclass}(sessionid="{eval_session_id}")

eval_file = Path('eval_{name}.yml')
data_gen_{name} = load_prompt(__file__, "data_gen_for_{name}.md")

rubric_{name} = load_prompt(__file__, "rubric_for_{rubric_name}.md")
rubric_{name} = load_prompt(__file__, "rubric_for_{rubric_name}.md")
...

class {InputClass}(BaseModel, use_attribute_docstrings=True):
    """{Description of the class}"""
    property_1: type
    property_2: type
    ...

class {OutputClass}(BaseModel, use_attribute_docstrings=True):
    """Model for expected answer"""
    property_1: type
    property_2: type


class MetadataType(BaseModel, use_attribute_docstrings=True):
    """Metadata model for test cases"""
    property_1: type
    property_2: type

async def execute_agent(question: Question) -> OutputClass:
    # Use async if agent.run is async, otherwise use sync
    result = {agent_name}.run(question.question) 

    {the_output_object} = ... # Prepare the output object with output class
    return {the_output_object}

async def main():

    if not Path.exists(eval_file):
        dataset = await generate_dataset(  
                model='openai:gpt-5-mini',
                dataset_type=Dataset[Question, Answer, MetadataType],
                n_examples=5,
                extra_instructions=data_gen_{name},
            )
        
        output_file = Path(eval_file)
        dataset.to_file(output_file)

    datasets = Dataset[Question, Answer, MetadataType].from_file(eval_file)
    datasets.add_evaluator(LLMJudge(
        include_input=True,
        score=OutputConfig(evaluation_name="{rubric_name}", include_reason=True),
        model='openai:gpt-5-mini',
        rubric=rubric_{name}
    ))

    #If multiple rubric is required then add them as below

    datasets.add_evaluator(LLMJudge(
        include_input=True,
        score=OutputConfig(evaluation_name="{rubric_name}", include_reason=True),
        model='openai:gpt-5-mini',
        rubric=rubric_{name}
    ))

    report = await datasets.evaluate(execute_agent)
    report.print(include_input=True, include_output=True, include_durations=True)

if __name__ == '__main__':
    asyncio.run(main())
```