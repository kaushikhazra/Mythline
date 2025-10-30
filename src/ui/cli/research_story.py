from src.agents.story_research_agent.agent import StoryResearcher
from src.libs.utils.argument_parser import get_arguments


args = get_arguments(
    agent_id=StoryResearcher.AGENT_ID,
    description='Story Research CLI'
)
print(f"Session: {args.session_id}\n")
story_researcher = StoryResearcher(args.session_id)

while True:
    prompt = input("🙍 User‍: ")

    if prompt == "exit":
        print(f"\n✏️  Story Researcher: Good Bye!! \n\n")
        break

    response = story_researcher.run(prompt)
    print(f"\n✏️  Story Researcher: {response.output} \n\n")