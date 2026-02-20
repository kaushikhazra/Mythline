# Project Root Structure Blueprint

**Purpose:** Guidelines for organizing the project root directory to maintain clarity and reduce clutter.

**Philosophy:** Prefer a clean, organized root while allowing flexibility for runtime artifacts and project-specific needs.

---

## Overview

The project root is the first thing developers see. It should be:
- **Clean** - Only essential files at the top level
- **Organized** - Clear purpose for each file/directory
- **Flexible** - Allow runtime artifacts and project-specific tools
- **Documented** - README explains the project

**Key Principle:** These are **preferred guidelines**, not strict rules. Runtime artifacts and project-specific needs may require exceptions.

---

## Preferred Root Files

### Essential Configuration (REQUIRED)

**`.env.example`**
- Environment variable template
- Shows all required and optional variables
- Never contains actual secrets
- Committed to git

**`requirements.txt`**
- Python dependencies
- Pin versions for reproducibility
- Used by `pip install -r requirements.txt`

**`.gitignore`**
- Git ignore rules
- Prevents committing secrets, runtime data, IDE files
- Essential for repository hygiene

### Documentation (RECOMMENDED)

**`README.md`**
- Project overview and purpose
- Quick start guide
- Links to detailed documentation
- First thing developers read

**`CLAUDE.md`** (OPTIONAL)
- AI agent development guide
- Project-specific coding standards
- Agent-specific instructions
- Only if using AI coding assistants

### Version History (PREFERRED: `docs/changelog/`)

**`CHANGELOG.md`**
- Version history and release notes
- **Preferred location:** `docs/changelog/CHANGELOG.md`
- **Acceptable in root** for small projects
- Follow [Keep a Changelog](https://keepachangelog.com) format

---

## Root Directories

### Essential Directories (REQUIRED)

**`src/`**
- All application source code
- Agents, graphs, libraries, MCP servers, UI
- See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for details

**`PDs/`** (Product Documents)
- Blueprints and design documentation
- Architecture decisions
- Development guides

### Recommended Directories

**`docs/`**
- User and developer documentation
- Design documents
- Architecture diagrams
- Subdirectories: `design/`, `architecture/`, `changelog/`

**`tests/`**
- Test suite
- Unit tests, integration tests, e2e tests
- Mirror `src/` structure

**`.{project_name}/`** (Runtime Data)
- Agent memory and context
- Knowledge base (vector DB)
- Generated artifacts
- **MUST be gitignored**
- Created automatically at runtime

### Configuration Directories (Auto-Generated)

**`.git/`** - Git repository (created by `git init`)
**`.vscode/`** - VS Code settings (optional)
**`.claude/`** - Claude Code settings (optional)
**`.apex/`** - Framework settings (if using Apex)

---

## Batch/Script Files

### Guideline: Create Only What's Needed

Batch files should be created on-demand for frequently used operations:

**MCP Server Launchers:**
```
start_all_mcps.bat          - Starts all MCP servers
start_web_search_mcp.bat    - Web search server
start_filesystem_mcp.bat    - Filesystem server
start_knowledge_base_mcp.bat - Knowledge base server
```

**Agent Runners:**
```
start_{agent_name}.bat      - Launch specific agent
```

**Utility Scripts:**
```
manage_knowledge_base.bat   - Knowledge base operations
```

**Rules:**
- ✅ Create for frequently used operations
- ✅ Name clearly: `start_`, `manage_`, `run_`
- ❌ Don't pre-create unused scripts
- ❌ Don't create one-time operation scripts

---

## Runtime Artifacts (ALLOWED)

These directories/files are created during project execution and are **acceptable in the root**:

### Generated Directories

**`output/`** - Generated output files
- Videos, audio, images
- Exports and reports
- **MUST be gitignored**

**`voices/`** - Voice configurations/cache
- TTS voice settings
- Voice model cache
- **MUST be gitignored**

**`logs/`** - Application logs (if created)
- Debug logs, error logs
- **MUST be gitignored**

### Temporary Files

- Build artifacts
- Test reports (`report.txt`, etc.)
- Temporary processing files
- **All MUST be gitignored**

**Guideline:** Runtime artifacts are OK but should be:
1. Gitignored (in `.gitignore`)
2. Documented (in README or docs)
3. Clearly named (obvious they're artifacts)

---

## Should NOT Be in Root

### Move These to Subdirectories

**Test Scripts** → `tests/`
```
❌ test_websocket.py (in root)
✅ tests/websocket/test_websocket.py
```

**Individual Source Files** → `src/`
```
❌ my_utility.py (in root)
✅ src/libs/my_utility.py
```

**Feature-Specific Config** → Feature directory
```
❌ agent_config.json (in root)
✅ src/agents/my_agent/config/agent_config.json
```

**Documentation Files** → `docs/` or `PDs/`
```
❌ architecture_decisions.md (in root)
✅ docs/architecture/decisions.md
```

**Scripts for Specific Features** → Feature directory
```
❌ process_audio.py (in root)
✅ src/libs/audio/process_audio.py
```

---

## Decision Tree: Where Does This File Go?

```
Is it a configuration file (.env, .gitignore, requirements.txt)?
  ✅ YES → Root is fine
  ❌ NO ↓

Is it documentation (README, CHANGELOG)?
  ✅ YES → Root is OK, but prefer docs/ for CHANGELOG
  ❌ NO ↓

Is it a batch/script file for common operations?
  ✅ YES → Root is fine (start_*.bat, manage_*.bat)
  ❌ NO ↓

Is it source code?
  ✅ YES → Must go in src/
  ❌ NO ↓

Is it a test file?
  ✅ YES → Must go in tests/
  ❌ NO ↓

Is it generated at runtime (artifacts, logs)?
  ✅ YES → Root is OK but MUST be gitignored
  ❌ NO ↓

Is it design/blueprint documentation?
  ✅ YES → Must go in PDs/ or docs/
  ❌ NO ↓

When in doubt → Use a subdirectory!
```

---

## Best Practices

### 1. Keep Root Minimal

**Good Root Structure:**
```
project_root/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── CLAUDE.md
├── start_all_mcps.bat
├── src/
├── PDs/
├── docs/
├── tests/
└── .mythline/          # Runtime (gitignored)
```

**Too Cluttered:**
```
project_root/
├── .env.example
├── test1.py
├── test2.py
├── utility.py
├── config.json
├── notes.txt
├── temp_file.md
├── experiment.py
├── src/
└── ... (too many files!)
```

### 2. Use .gitignore Aggressively

Runtime artifacts should be gitignored:

```gitignore
# Runtime data
.mythline/
output/
voices/
logs/

# Temporary files
*.log
*.tmp
report.txt
rebuild_output.txt

# Environment
.env
```

### 3. Document Root Files

In `README.md`, explain non-obvious root files:

```markdown
## Project Structure

- `start_all_mcps.bat` - Launches all MCP servers for development
- `output/` - Generated video/audio files (gitignored)
- `voices/` - TTS voice cache (gitignored)
```

### 4. Prefer Descriptive Names

**Good:**
- `start_web_search_mcp.bat` - Clear purpose
- `manage_knowledge_base.bat` - Clear action
- `requirements.txt` - Standard name

**Bad:**
- `run.bat` - Too vague
- `s.bat` - Cryptic abbreviation
- `script.bat` - What does it do?

### 5. Review Regularly

Periodically check root for:
- Unused batch files → Delete
- Test files in root → Move to `tests/`
- Old artifacts → Clean up
- Temporary files → Delete

---

## Anti-Patterns

### ❌ Anti-Pattern 1: Test Files in Root

```
# DON'T
project_root/
├── test_agent.py
├── test_mcp.py
└── test_integration.py

# DO
project_root/
└── tests/
    ├── agents/test_agent.py
    ├── mcps/test_mcp.py
    └── integration/test_integration.py
```

### ❌ Anti-Pattern 2: One Script Per Feature

```
# DON'T (too many scripts)
start_agent1.bat
start_agent2.bat
start_agent3.bat
start_mcp1.bat
start_mcp2.bat
start_mcp3.bat

# DO (consolidated)
start_all_mcps.bat
start_agent.bat <agent_name>
```

### ❌ Anti-Pattern 3: Committing Runtime Artifacts

```gitignore
# DON'T commit these
output/
voices/
logs/
*.log

# DO gitignore them
# (add to .gitignore)
```

### ❌ Anti-Pattern 4: Source Code in Root

```
# DON'T
project_root/
├── my_agent.py
├── my_tool.py
└── helpers.py

# DO
project_root/
└── src/
    ├── agents/my_agent/
    ├── tools/my_tool.py
    └── libs/helpers.py
```

---

## Template Root Structure

For a new Pydantic AI multi-agent project:

```
project_root/
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
├── README.md                 # Project documentation
├── requirements.txt          # Python dependencies
├── CLAUDE.md                 # AI agent guide (optional)
│
├── src/                      # Source code
│   ├── agents/               # AI agents
│   ├── graphs/               # LangGraph workflows
│   ├── libs/                 # Shared libraries
│   ├── mcp_servers/          # MCP servers
│   └── ui/                   # User interfaces
│
├── PDs/                      # Product documents
│   ├── blueprints/           # Code blueprints
│   └── guides/               # Development guides
│
├── docs/                     # Documentation
│   ├── design/               # Design docs
│   ├── architecture/         # Architecture
│   └── changelog/            # Version history
│
├── tests/                    # Test suite
│   ├── agents/               # Agent tests
│   ├── graphs/               # Graph tests
│   └── libs/                 # Library tests
│
├── .{project_name}/          # Runtime data (gitignored)
│   ├── {agent_id}/           # Agent memory
│   └── knowledge_base/       # Vector DB
│
├── start_all_mcps.bat        # Start all MCP servers
└── [other project-specific batch files as needed]
```

**Runtime Artifacts (gitignored, created during execution):**
```
project_root/
├── output/                   # Generated files
├── voices/                   # Voice cache
├── logs/                     # Application logs
└── [other artifacts as needed]
```

---

## For AI Assistants

When generating code that might create files/directories:

**Ask yourself:**
1. Is this a source file? → Goes in `src/`
2. Is this a test? → Goes in `tests/`
3. Is this documentation? → Goes in `docs/` or `PDs/`
4. Is this a batch file for common operations? → Root is OK
5. Is this generated output? → Goes in runtime directory (e.g., `output/`)

**When creating batch files:**
- Create only if user explicitly requests
- Use clear naming: `start_`, `manage_`, `run_`
- Consolidate related operations when possible

**When creating artifacts:**
- Use dedicated directories (`output/`, `logs/`)
- Ensure they're gitignored
- Document their purpose in README

---

## Summary

**Preferred Root Contents:**
- ✅ Essential config files (.env.example, requirements.txt, .gitignore)
- ✅ Documentation (README.md, CLAUDE.md)
- ✅ Essential directories (src/, PDs/, docs/, tests/)
- ✅ Common operation batch files (start_*.bat)
- ✅ Runtime artifacts (if gitignored and documented)

**Not in Root:**
- ❌ Test files (use tests/)
- ❌ Source code files (use src/)
- ❌ Feature-specific config (use feature directory)
- ❌ One-off scripts (use subdirectory or delete after use)

**Remember:** These are **guidelines, not mandates**. Projects may need flexibility for:
- Runtime artifacts
- Project-specific tools
- Development utilities
- Temporary files during active development

**Golden Rule:** When in doubt, prefer subdirectories over root clutter!
