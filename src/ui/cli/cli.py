from src.agents.story_creator_agent.agent import StoryCreator
from src.libs.utils.argument_parser import get_session


session_id = get_session(StoryCreator.AGENT_ID)
print(f"Session: {session_id}\n")
story_creator = StoryCreator(session_id)

while True:
    prompt = input("🙍 User‍: ")

    if prompt == "exit":
        print(f"\n🤖 Agent: Good Bye!! \n\n")
        break

    response = story_creator.run(prompt)
    print(f"\n🤖 Agent: {response.output} \n\n")