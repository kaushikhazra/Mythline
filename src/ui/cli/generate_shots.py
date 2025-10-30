from tqdm import tqdm

from src.agents.shot_creator_agent.agent import ShotCreator
from src.libs.utils.markdown_parser import parse_markdown
from src.libs.utils.argument_parser import get_arguments
from src.libs.filesystem.file_operations import read_file, append_file

args = get_arguments(
    agent_id='shot_creator',
    description='Shot Generator CLI',
    require_input=True,
    require_output=True
)
input_file = args.input_file
output_file = args.output_file
verbose = args.verbose

story_md = read_file(input_file)

chunks = parse_markdown(story_md)

shot_creator = ShotCreator()

shot_number = 1
for i, chunk_md in tqdm(enumerate(chunks, 1), total=len(chunks), desc="Processing chunks"):
    if verbose:
        print(f"\n{'='*60}")
        print(f"CHUNK {i}")
        print(f"{'='*60}\n")

    if verbose:
        print(chunk_md)
    response = shot_creator.run(chunk_md)
    shots = response.output\
               .replace('```markdown','')\
               .replace('```','')\
               .split("---")

    for shot in shots:
        if (shot.strip() != ""):
            shot_chunk = f"## Shot {shot_number}{shot}"
            if verbose:
                print(shot_chunk)
            append_file(output_file, shot_chunk + '\n')
            shot_number += 1


