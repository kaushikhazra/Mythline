from src.agents.story_creator_agent.agent import StoryCreator
from src.libs.utils.argument_parser import get_arguments


args = get_arguments(
    agent_id=StoryCreator.AGENT_ID,
    description='Story Creator CLI'
)
print(f"Session: {args.session_id}\n")
story_creator = StoryCreator(args.session_id)

while True:
    prompt = input("🙍 User‍: ")

    if prompt == "exit":
        print(f"\n🤖 Agent: Good Bye!! \n\n")
        break

    response = story_creator.run(prompt)
    print(f"\n🤖 Agent: {response.output} \n\n")