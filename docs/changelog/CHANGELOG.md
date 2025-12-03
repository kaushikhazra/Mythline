# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-12

### Added

#### Story Creator Agent
- Main orchestrator agent for WoW story creation
- Automated lore research using MCP web search and crawler
- Session-based context memory for coherent multi-part stories
- Long-term memory for user preference tracking
- Integration with narrator and dialog creator sub-agents

#### Narrator Agent
- Stateful sub-agent for third-person narration
- Context memory for coherent story segments
- Word count compliance enforcement
- Session-aware narrative generation

#### Dialog Creator Agent
- Stateful sub-agent for character dialogue generation
- Maintains consistent character voices
- Ensures all actors have speaking parts
- Context-aware dialogue creation

#### User Preference Agent
- Stateless preference analyzer
- Extracts memorable user preferences from interactions
- Feeds into long-term memory system
- Cross-session preference tracking

#### Shot Creator Agent
- Visual scene description generator
- Cinematic storytelling support
- Shot-by-shot scene breakdown
- Camera angle and visual element descriptions

#### MCP Servers
- **mcp_web_search**: DuckDuckGo search with auto-crawling of top 5 results
- **mcp_web_crawler**: Web page content extraction with markdown conversion
- **mcp_filesystem**: File read/write operations and directory management

#### Memory System
- Context memory: Session-based conversation history per agent
- Long-term memory: Cross-session preference storage
- Agent-specific memory namespaces
- Automatic persistence to `.mythline/` directory

#### Documentation
- Comprehensive README with installation and usage guide
- CLAUDE.md with AI agent development guidelines
- Pydantic AI coding guide in `PDs/pydantic_ai_coding_guide.md`
- Git-flow workflow documentation

#### CLI Interface
- Interactive story creator CLI
- Session management (new, resume, load specific)
- Story-to-shots parser for visual scene generation
- Batch scripts for easy startup

### Changed

#### Refactored Prompt Loading System
- Centralized prompt loader utility
- Automatic prompt file discovery using `__file__`
- Support for both system prompts and sub-prompts
- Simplified agent prompt management

#### Story-to-Shots Parser
- Improved markdown parsing for shot generation
- Better scene extraction from narrative stories
- Enhanced shot creator agent integration

### Infrastructure
- Python 3.8+ support
- OpenAI GPT-4o integration
- Environment-based configuration
- Modular architecture with agent/sub-agent pattern

[1.0.0]: https://github.com/kaushikhazra/Mythline/releases/tag/1.0.0
