Hello Mindgate,

Hope you are doing well.

Today I’m going to talk about Mythline, an AI story-writing agent.

Let me begin with the problem.
If you’ve ever created story-based content for social media, you already know how hard it is. You have to research, write the story, review it, fact-check it, and then plan the right video shots to shape the final content. It takes time, effort, and a lot of iteration.

Now imagine an AI agent that can help you with all of that.
Yes, we can use normal AI chat programs — but getting consistent and accurate output from them is difficult because they are non-deterministic.
When we give the AI a proper persona, guardrails, and instructions, the results become predictable and reliable.

That is exactly what Mythline does.

The goal of Mythline is simple:
to provide a frictionless AI system that can research and build a video-ready story from end to end.

How does it work?
I used OpenAI GPT-5 Mini as the story-writing engine, Pydantic AI as the framework that binds everything together, and a set of MCP servers to support functions like web search, crawling the web, doing filesystem operations, and storing knowledge for RAG.

Now, about the data.
Since this is a story creator, it handles free-form content, mainly in Markdown and JSON.
Research comes directly from the web as plain text.
The system then creates a research document, and from that, it generates structured JSON for the story sections and the video shots.

Why JSON?
Two reasons:
First, structured data makes it easier to feed into later stages for voice direction and production.
Second, structure forces determinism — so the AI behaves consistently.

Finally, the architecture.
Mythline is built on Pydantic AI and uses a Finite State Machine, managed through Pydantic Graph, to move cleanly through each operation.
The web-search component is custom-built and open-source.
The system uses FastMCP for MCP servers and Qdrant as the vector knowledge base.

The result is the story you see on the screen.