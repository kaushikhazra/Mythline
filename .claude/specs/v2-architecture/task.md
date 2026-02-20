# Mythline v2 Architecture — Tasks

## Phase 0: Discovery
- [x] Capture architectural pain points and vision
  _Requirement: understand what needs to change and why_
- [x] Resolve MCP architecture questions (Q1-Q3)
  _Requirement: MCP as data microservices — 5 stores, agents write/read_
- [x] Resolve orchestration questions (Q4-Q6)
  _Requirement: no orchestrator, no graphs. Autonomous daemons + message queue swarm_
- [x] Resolve memory & context questions (Q7-Q9)
  _Requirement: 5 knowledge domains, MMORPG-generic data model_
- [x] Define Knowledge Acquisition architecture
  _Requirement: Research Agent → Validator Agent → MCP Store × 5 domains_
- [x] Define Drama Production architecture
  _Requirement: 8 agents with message queue, quality-gated convergence_
- [ ] Research existing patterns/libraries for modern agentic architecture
  _Requirement: don't build from scratch if solutions exist_

## Phase 1: Design (detailed)
- [ ] Design MCP store schemas per domain
  _Requirement: storage tech, data models, query patterns_
- [ ] Design message queue system for Drama Production
  _Requirement: tech choice, message format, channel conventions_
- [ ] Design agent prompt structures
  _Requirement: autonomous knowledge agents + collaborative drama agents_
- [ ] Design quality scoring rubric
  _Requirement: dimensions, weights, threshold, iteration cap_
- [ ] Design game constraint system (emotes/gestures)
  _Requirement: Character Director needs finite palette of available expressions_
- [ ] Design context window budget strategy
  _Requirement: Q9 deferred — agents query multiple MCPs, need token management_
- [ ] Define migration strategy (v1 → v2)
  _Requirement: preserve working functionality where applicable_

## Phase 2: Implementation
_Tasks to be created after Phase 1 design is approved_
