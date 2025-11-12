from src.agents.llm_tester_agent import LLMTester
from src.libs.utils.argument_parser import get_arguments


args = get_arguments(LLMTester.AGENT_ID, description="LLM Tester Agent")
print(f"Session: {args.session_id}\n")
llm_tester = LLMTester(args.session_id)

print("LLM Tester Agent - Type 'exit' to quit\n")

while True:
    prompt = input("🙍 User: ")

    if prompt == "exit":
        break

    response = llm_tester.run(prompt)
    print(f"\n🤖 Agent: {response.output}\n\n")
