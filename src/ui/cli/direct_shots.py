from src.agents.video_director_agent.agent import VideoDirector
from src.libs.utils.argument_parser import get_arguments


args = get_arguments(
    agent_id=VideoDirector.AGENT_ID,
    description='Video Director CLI',
    require_input=False
)

print(f"Session: {args.session_id}\n")

director = VideoDirector(args.session_id)

if args.input_file:
    initial_prompt = f"Direct the shots from {args.input_file}"
    response = director.run(initial_prompt)
    print(f"\n🎬 Director: {response.output}\n\n")
else:
    response = director.run("Continue directing")
    print(f"\n🎬 Director: {response.output}\n\n")

while True:
    user_input = input("You: ")

    if user_input.lower() in ["exit", "quit"]:
        print(f"\n🎬 Director: That's a wrap! Good work.\n\n")
        break

    response = director.run(user_input)
    print(f"\n🎬 Director: {response.output}\n\n")
