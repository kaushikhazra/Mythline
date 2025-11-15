import os
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

from pydantic_evals import Dataset
from pydantic_evals.evaluators.common import LLMJudge, OutputConfig
from pydantic_evals.generation import generate_dataset

from src.agents.llm_tester_agent.agent import LLMTester
from src.libs.utils.prompt_loader import load_prompt
from src.libs.filesystem.file_operations import write_file

load_dotenv()

llm_tester = LLMTester(session_id="eval_session")

eval_file = Path(__file__).parent / 'eval_llm_tester.yml'
data_gen_research = load_prompt(__file__, "data_gen_for_research")

rubric_relevance = load_prompt(__file__, "rubric_for_relevance")
rubric_formatting = load_prompt(__file__, "rubric_for_formatting")
rubric_sources = load_prompt(__file__, "rubric_for_sources")
rubric_structure = load_prompt(__file__, "rubric_for_structure")

class ResearchInput(BaseModel, use_attribute_docstrings=True):
    """Input model for research queries"""
    research_query: str
    save_to_file: bool
    filename: str | None

class ResearchOutput(BaseModel, use_attribute_docstrings=True):
    """Model for expected research output"""
    research_summary: str
    sources_used: list[str]
    file_content: str | None

class ResearchMetadata(BaseModel, use_attribute_docstrings=True):
    """Metadata model for research test cases"""
    topic_category: str
    complexity_level: str

async def execute_agent(input: ResearchInput) -> ResearchOutput:
    prompt = input.research_query
    if input.save_to_file and input.filename:
        prompt += f"\nPlease save the research to {input.filename}"

    result = await llm_tester.run(prompt)
    output_text = result.output

    sources = []
    if "http" in output_text.lower():
        sources = [line.strip() for line in output_text.split('\n') if 'http' in line.lower()]

    file_content = None
    if input.save_to_file and input.filename:
        file_path = Path(input.filename)
        if file_path.exists():
            file_content = file_path.read_text(encoding='utf-8')
        else:
            print(f'\nWarning: File {input.filename} was not created by agent')

    output = ResearchOutput(
        research_summary=output_text,
        sources_used=sources,
        file_content=file_content
    )

    return output

async def main():
    llm_model = f"openrouter:{os.getenv('LLM_MODEL')}"

    if not eval_file.exists():
        dataset = await generate_dataset(
            model=llm_model,
            dataset_type=Dataset[ResearchInput, ResearchOutput, ResearchMetadata],
            n_examples=5,
            extra_instructions=data_gen_research,
        )

        output_file = Path(eval_file)
        dataset.to_file(output_file)

    datasets = Dataset[ResearchInput, ResearchOutput, ResearchMetadata].from_file(eval_file)

    datasets.add_evaluator(LLMJudge(
        include_input=True,
        score=OutputConfig(evaluation_name="relevance", include_reason=True),
        model=llm_model,
        rubric=rubric_relevance
    ))

    datasets.add_evaluator(LLMJudge(
        include_input=True,
        score=OutputConfig(evaluation_name="formatting", include_reason=True),
        model=llm_model,
        rubric=rubric_formatting
    ))

    datasets.add_evaluator(LLMJudge(
        include_input=True,
        score=OutputConfig(evaluation_name="sources", include_reason=True),
        model=llm_model,
        rubric=rubric_sources
    ))

    datasets.add_evaluator(LLMJudge(
        include_input=True,
        score=OutputConfig(evaluation_name="structure", include_reason=True),
        model=llm_model,
        rubric=rubric_structure
    ))

    report = await datasets.evaluate(execute_agent, max_concurrency=1)
    report_data = report.render(include_input=True, include_output=True, include_durations=True)
    write_file('report.txt', report_data)

if __name__ == '__main__':
    asyncio.run(main())
