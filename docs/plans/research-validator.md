# Research Validator - Implementation Plan

## Problem Statement

The story agent deviates from accurate lore because web-scraped data goes directly into `research.json` without human validation. Incorrect information, outdated lore, or parsing errors propagate to generated stories.

## Solution Overview

Add a human-in-the-loop validation step: after the research graph extracts data, display it in a web UI where the user can review and correct before the story agent consumes it.

```
Research Graph → research.json → Web UI (Review/Edit) → Updated research.json → Story Agent
                 (auto)              (human)              (validated)
```

## Data Model Reference

The `research.json` file follows the `ResearchBrief` Pydantic model:

```
ResearchBrief
├── chain_title: str
├── setting: Setting
│   ├── zone: str
│   ├── starting_location: str | None
│   ├── journey: str | None
│   ├── description: str
│   └── lore_context: str
├── quests: list[QuestResearch]
│   ├── id: str
│   ├── title: str
│   ├── story_beat: str
│   ├── objectives: Objectives
│   │   ├── summary: str
│   │   └── details: str
│   ├── quest_giver: NPC
│   │   ├── name: str
│   │   ├── title: str
│   │   ├── personality: str
│   │   ├── lore: str
│   │   └── location: Location
│   │       ├── area: Area (name, x, y)
│   │       ├── position: str
│   │       ├── visual: str
│   │       └── landmarks: str
│   ├── turn_in_npc: NPC (same structure)
│   ├── execution_location: ExecutionLocation
│   │   ├── area: Area (name, x, y)
│   │   ├── visual: str
│   │   ├── landmarks: str
│   │   └── enemies: str
│   ├── story_text: str
│   └── completion_text: str
├── roleplay: dict[str, str]
└── execution_order: list[FlowSegment]
```

## Implementation Plan

### Phase 1: Backend API

**File:** `src/ui/web/backend/routers/research.py`

Extend the existing router (which handles chat sessions) with three new endpoints for JSON data:

#### 1.1 List Available Subjects
```
GET /api/research/subjects
```
- Scan `output/` directory for subdirectories containing `research.json`
- Return list of subject names

#### 1.2 Load Research Data
```
GET /api/research/{subject}/data
```
- Read `output/{subject}/research.json`
- Return as JSON (already valid structure)
- Return 404 if not found

#### 1.3 Save Research Data
```
POST /api/research/{subject}/data
```
- Accept JSON body matching `ResearchBrief` schema
- Validate against Pydantic model (automatic type checking)
- Write to `output/{subject}/research.json`
- Return success/error

### Phase 2: Frontend - ResearchValidator Page

**File:** `src/ui/web/frontend/src/pages/ResearchValidator.jsx`

#### 2.1 Layout Structure

```
┌──────────────────────────────────────────────────────────────┐
│  Research Validator                          [Save Changes]  │
├──────────────────────────────────────────────────────────────┤
│  Subject: [Dropdown ▼]                                       │
├──────────────────────────────────────────────────────────────┤
│  [Setting] [Quests] [Roleplay]                    (tabs)     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Tab Content Area                                            │
│  - Editable forms based on selected tab                      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### 2.2 Setting Tab

Editable fields:
- Zone (text input)
- Starting Location (text input)
- Journey (textarea)
- Description (textarea)
- Lore Context (textarea)

#### 2.3 Quests Tab

Accordion/expandable list of quests. Each quest card contains:

**Quest Header (collapsed view):**
- `[quest_id] Quest Title`

**Quest Details (expanded view):**

| Section | Fields | Priority |
|---------|--------|----------|
| Basic Info | title, story_beat | Normal |
| Objectives | summary (textarea), details (textarea) | Normal |
| Quest Giver | name, title, personality, lore (textarea) | Normal |
| **Quest Giver Location** | area.name, area.x, area.y, position, visual, landmarks | **HIGH** |
| Turn-in NPC | name, title, personality, lore (textarea) | Normal |
| **Turn-in NPC Location** | area.name, area.x, area.y, position, visual, landmarks | **HIGH** |
| **Execution Location** | area.name, area.x, area.y, visual, landmarks, enemies | **HIGH** |
| Story Text | story_text (textarea) | Normal |
| Completion Text | completion_text (textarea) | Normal |

**UI Note:** Location sections should be visually prominent (e.g., highlighted background, expanded by default) since these are most frequently corrected.

#### 2.4 Roleplay Tab

Key-value editor for roleplay dictionary:
- Display existing keys with editable values (textarea)
- Add new key-value pair button
- Delete key button

### Phase 3: Frontend Integration

#### 3.1 Add Route

**File:** `src/ui/web/frontend/src/App.jsx`

Add route for `/validator` pointing to `ResearchValidator` component.

#### 3.2 Add Navigation

**File:** `src/ui/web/frontend/src/components/Navigation.jsx` (or equivalent)

Add "Research Validator" link to navigation menu.

#### 3.3 Styling

**File:** `src/ui/web/frontend/src/pages/ResearchValidator.css`

- Match existing app styling patterns
- Accordion styles for quest cards
- Form input styles
- Tab styles
- Save button (sticky header or floating)

### Phase 4: State Management

#### 4.1 Component State

```javascript
// Core state
const [subjects, setSubjects] = useState([])           // Available subjects
const [selectedSubject, setSelectedSubject] = useState(null)
const [researchData, setResearchData] = useState(null) // Full ResearchBrief
const [activeTab, setActiveTab] = useState('setting')  // setting|quests|roleplay
const [hasChanges, setHasChanges] = useState(false)    // Dirty flag
const [saving, setSaving] = useState(false)
const [expandedQuest, setExpandedQuest] = useState(null) // Which quest is expanded

// Handlers
const handleFieldChange = (path, value) => {
  // Update nested field in researchData
  // Set hasChanges = true
}

const handleSave = async () => {
  // POST to /api/research/{subject}/data
  // Reset hasChanges on success
}
```

#### 4.2 Nested Field Updates

Use a utility function to update deeply nested fields:
```javascript
// Example: updateField('quests.0.quest_giver.name', 'New Name')
```

### Phase 5: UX Enhancements

#### 5.1 Unsaved Changes Warning
- Show indicator when `hasChanges = true`
- Warn on navigation away if unsaved changes

#### 5.2 Validation Feedback
- Highlight required fields
- Show error messages if save fails validation

#### 5.3 Loading States
- Show spinner while loading subject data
- Disable save button while saving

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `src/ui/web/backend/routers/research.py` | Modify | Add 3 new endpoints (existing file handles chat sessions) |
| `src/ui/web/frontend/src/pages/ResearchValidator.jsx` | Create | New validation page |
| `src/ui/web/frontend/src/pages/ResearchValidator.css` | Create | Page styles |
| `src/ui/web/frontend/src/App.jsx` | Modify | Add route |
| `src/ui/web/frontend/src/components/Navigation.jsx` | Modify | Add nav link (if exists) |

**Note:** `SimpleResearch.jsx` is for chat-based research conversations with the agent - different purpose, cannot be reused for structured data editing.

## API Contract

### GET /api/research/subjects
**Response:**
```json
["shadowglen", "westfall", "darkshore"]
```

### GET /api/research/{subject}/data
**Response:** Full `ResearchBrief` JSON

**Error (404):**
```json
{"detail": "Research data not found for subject: {subject}"}
```

### POST /api/research/{subject}/data
**Request Body:** Full `ResearchBrief` JSON

**Response (200):**
```json
{"status": "saved", "subject": "{subject}"}
```

**Error (422):**
```json
{"detail": "Validation error: {field} - {message}"}
```

## Testing Checklist

- [ ] Load subject list on page mount
- [ ] Select subject loads research data
- [ ] Edit setting fields and save
- [ ] Edit quest fields (all sections) and save
- [ ] Add/edit/delete roleplay entries and save
- [ ] Unsaved changes warning works
- [ ] Validation errors display properly
- [ ] Saved data persists (reload and verify)
- [ ] Story creation uses validated data

## Future Enhancements (Out of Scope)

- Side-by-side diff view (original vs edited)
- Undo/redo functionality
- Bulk editing across quests
- Import/export to different formats
- Version history of edits
