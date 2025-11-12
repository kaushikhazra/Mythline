# World of Warcraft Themed UI Implementation Plan

## Overview

This document outlines the implementation plan for a World of Warcraft-inspired web interface for the Mythline storytelling system. The design uses WoW's iconic visual language while remaining practical for web implementation.

## Design Philosophy

**Approach:** WoW-inspired aesthetic with practical web implementation
- Use WoW color palette and general design patterns
- Simplified decorations suitable for web (no heavy textures)
- Focus on recognizable WoW UI components
- No audio implementation
- Free/open-source fonts only

## Visual Design System

### Color Palette

```css
:root {
  /* Brand Colors */
  --wow-blue: #0787AC;
  --wow-navy: #00437A;
  --wow-gold: #FFCC00;
  --wow-orange: #CD650E;

  /* UI Colors */
  --wow-gold-accent: #D7913A;
  --wow-panel-brown: #A28F65;
  --wow-dark-bg: #364652;
  --wow-darker-bg: #1a1a1a;
  --wow-shadow: #5F4C0C;
  --wow-border: #2C2416;

  /* Item Rarity Colors */
  --wow-poor: #9D9D9D;
  --wow-common: #FFFFFF;
  --wow-uncommon: #1EFF00;
  --wow-rare: #0070DD;
  --wow-epic: #A335EE;
  --wow-legendary: #FF8000;
  --wow-artifact: #E6CC80;
  --wow-heirloom: #00CCFF;

  /* Class Colors (for potential future use) */
  --wow-druid: #FF7D0A;
  --wow-hunter: #ABD473;
  --wow-mage: #40C7EB;
  --wow-paladin: #F58CBA;
  --wow-priest: #FFFFFF;
  --wow-rogue: #FFF569;
  --wow-shaman: #0070DE;
  --wow-warlock: #8787ED;
  --wow-warrior: #C79C6E;

  /* Status Colors */
  --wow-health: #FF0000;
  --wow-mana: #0070DD;
  --wow-energy: #FFF569;
  --wow-success: #1EFF00;
  --wow-warning: #FF8000;
  --wow-error: #FF0000;
}
```

### Typography

**Font Stack:**
```css
/* Primary Font - Medieval/Fantasy Headers */
--font-primary: 'Cinzel', 'IM Fell DW Pica', 'Georgia', serif;

/* Secondary Font - UI Text */
--font-secondary: 'Roboto Condensed', 'Arial Narrow', Arial, sans-serif;

/* Monospace - for story content/code */
--font-mono: 'Roboto Mono', 'Courier New', monospace;
```

**Font Recommendations (Google Fonts):**
- **Cinzel** - Elegant serif, great for titles (Friz Quadrata alternative)
- **IM Fell DW Pica** - Medieval book font (Morpheus alternative)
- **Roboto Condensed** - Clean, narrow sans-serif (Arial Narrow alternative)
- **Roboto Mono** - For monospace needs

### Component Styling Standards

#### WoW Frame/Panel Style

```css
.wow-frame {
  background: linear-gradient(135deg, #364652 0%, #2a3840 100%);
  border: 2px solid var(--wow-gold-accent);
  box-shadow:
    inset 0 0 20px rgba(0, 0, 0, 0.4),
    0 4px 6px rgba(0, 0, 0, 0.5);
  position: relative;
}

/* Corner decorations */
.wow-frame::before {
  content: '';
  position: absolute;
  top: -2px;
  left: -2px;
  right: -2px;
  bottom: -2px;
  border: 1px solid var(--wow-gold);
  pointer-events: none;
  opacity: 0.3;
}
```

#### WoW Button Style

```css
.wow-button {
  background: linear-gradient(to bottom,
    var(--wow-panel-brown) 0%,
    var(--wow-shadow) 100%);
  border: 2px solid var(--wow-gold-accent);
  color: var(--wow-gold);
  font-family: var(--font-primary);
  font-weight: 600;
  padding: 8px 16px;
  cursor: pointer;
  position: relative;
  transition: all 0.2s ease;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
}

.wow-button:hover {
  border-color: var(--wow-gold);
  box-shadow: 0 0 15px rgba(255, 204, 0, 0.5);
  transform: translateY(-1px);
}

.wow-button:active {
  transform: translateY(0);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.5);
}
```

#### WoW Input Field Style

```css
.wow-input {
  background: rgba(26, 26, 26, 0.8);
  border: 2px solid var(--wow-border);
  color: var(--wow-common);
  font-family: var(--font-secondary);
  padding: 8px 12px;
  transition: border-color 0.2s ease;
}

.wow-input:focus {
  border-color: var(--wow-gold-accent);
  outline: none;
  box-shadow: 0 0 10px rgba(215, 145, 58, 0.3);
}
```

#### WoW Progress Bar Style

```css
.wow-progress-bar {
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid var(--wow-border);
  height: 24px;
  position: relative;
  overflow: hidden;
}

.wow-progress-fill {
  background: linear-gradient(to bottom,
    var(--wow-gold) 0%,
    var(--wow-gold-accent) 50%,
    var(--wow-orange) 100%);
  height: 100%;
  transition: width 0.3s ease;
  box-shadow: inset 0 -2px 4px rgba(0, 0, 0, 0.3);
}

.wow-progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: var(--wow-common);
  font-family: var(--font-secondary);
  font-weight: bold;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.9);
}
```

## Component-Specific Designs

### 1. Research Chat Interface (Quest Log Style)

**Visual Reference:** WoW Quest Log UI

**Layout:**
```
┌──────────────────────────────────────────────┐
│  🗡️ STORY RESEARCH                           │ Golden title bar
├────────────────┬─────────────────────────────┤
│ Sessions       │  💬 Chat Area               │
│ ┌────────────┐│  ┌─────────────────────────┐│
│ │ New Session││  │ User: Research...        ││
│ │ 01/10 14:30││  │ Agent: Shadowglen is...  ││
│ │ 01/09 16:45││  │ [Tool: NarratorAgent]    ││
│ └────────────┘│  │ ...                      ││
│                │  └─────────────────────────┘│
│                │  ┌─────────────────────────┐│
│                │  │ Type your message...    ││
│                │  └─────────────────────────┘│
└────────────────┴─────────────────────────────┘
```

**Key Features:**
- Left sidebar: Session list (like quest list)
- Right panel: Chat messages (like quest text)
- Golden frame with corner decorations
- Messages styled as parchment/scroll entries
- Tool calls shown as colored status messages
- Input box at bottom with WoW button styling

**Color Coding:**
- User messages: Gold text (#FFCC00)
- Agent messages: White text (#FFFFFF)
- Tool calls: Blue text (#0070DD) with icon
- System messages: Gray text (#9D9D9D)

### 2. Story Creator Interface (Character Sheet/Profession Style)

**Visual Reference:** WoW Character Sheet / Profession UI

**Layout:**
```
┌────────────────────────────────────────────────────────┐
│  📖 STORY CREATION                                     │
├────────────────────────────────────────────────────────┤
│  Subject: [_______________]  Player: [_______________] │
│  [🔍 Validate Research]        [⚔️ Create Story]       │
├────────────────────────────────────────────────────────┤
│  Progress: [████████░░░░░░░░░░] 8/12 Complete         │
│  Current: Creating dialogue for quest acceptance       │
├────────────────────────────────────────────────────────┤
│  📜 Activity Log                                       │
│  ┌──────────────────────────────────────────────────┐ │
│  │ [✓] Research loaded successfully                 │ │
│  │ [*] Generating story plan...                     │ │
│  │ [✓] Plan created with 12 segments                │ │
│  │ [*] Creating introduction narration...           │ │
│  │ [✓] Content validated (score: 0.92)              │ │
│  │ [*] Processing quest 1 dialogue...               │ │
│  └──────────────────────────────────────────────────┘ │
│  [⏸️ Pause]  [❌ Cancel]  [📥 View Story]              │
└────────────────────────────────────────────────────────┘
```

**Key Features:**
- Top section: Input form with WoW-styled inputs
- Progress bar with gold gradient fill
- Activity log with color-coded status icons
- Action buttons at bottom (styled like ability buttons)
- Review scores shown with colored badges

**Status Icons:**
- In Progress: [*] Blue (#0070DD)
- Complete: [✓] Green (#1EFF00)
- Error: [!] Red (#FF0000)
- Warning: [!] Orange (#FF8000)

### 3. Story Viewer (Quest/Achievement Detail Style)

**Visual Reference:** WoW Quest Detail / Achievement UI

**Layout:**
```
┌──────────────────────────────────────────────┐
│  📖 STORY: Shadowglen                        │
├──────────────────────────────────────────────┤
│  Player: Sarephine                           │
│  Created: 2025-01-10 15:30                   │
├──────────────────────────────────────────────┤
│  📋 Table of Contents                        │
│  ├─ Introduction                             │
│  ├─ 🔵 Quest: The Balance of Nature          │
│  │   ├─ Introduction                         │
│  │   ├─ Dialogue                             │
│  │   ├─ Execution                            │
│  │   └─ Completion                           │
│  ├─ 🔵 Quest: Webwood Corruption             │
│  └─ Conclusion                               │
├──────────────────────────────────────────────┤
│  📜 Content Preview                          │
│  ┌────────────────────────────────────────┐ │
│  │ The forest of Shadowglen awakens...    │ │
│  │                                         │ │
│  │ Ancient trees tower overhead...        │ │
│  └────────────────────────────────────────┘ │
│  [📥 Download JSON]  [📄 Export Markdown]   │
└──────────────────────────────────────────────┘
```

**Key Features:**
- Tree view with expandable sections
- Quest markers (blue diamonds like WoW)
- Content preview with parchment styling
- Export buttons with WoW styling
- Scrollable content area

### 4. File Explorer (Bag/Inventory Style)

**Visual Reference:** WoW Bag Interface

**Layout:**
```
┌────────────────────────────────────────────┐
│  🎒 FILE STORAGE                           │
├────────────────────────────────────────────┤
│  [Research Files 📜] [Story Files 📖]      │
├────────────────────────────────────────────┤
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐      │
│  │📜  │ │📜  │ │📜  │ │    │ │    │      │
│  │shad│ │elwn│ │iron│ │    │ │    │      │
│  └────┘ └────┘ └────┘ └────┘ └────┘      │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐      │
│  │📖  │ │📖  │ │    │ │    │ │    │      │
│  │shad│ │elwn│ │    │ │    │ │    │      │
│  └────┘ └────┘ └────┘ └────┘ └────┘      │
├────────────────────────────────────────────┤
│  Selected: shadowglen_research.md          │
│  Size: 15.2 KB  |  Modified: 2025-01-10   │
│  [👁️ View]  [📥 Download]  [🗑️ Delete]     │
└────────────────────────────────────────────┘
```

**Key Features:**
- Grid layout (5x4 or similar)
- File icons styled like WoW item icons
- Hover tooltip showing file details
- Color-coded borders by file type
- Selection highlights with golden glow
- Action buttons at bottom

**File Type Colors:**
- Research files: Blue border (#0070DD)
- Story files: Purple border (#A335EE)
- Empty slots: Dark transparent

### 5. Navigation Bar (Action Bar Style)

**Visual Reference:** WoW Bottom Action Bar

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│ [🔍 Research] [📖 Create] [👁️ Stories] [📁 Files]    │
│                                       [⚙️ Settings]   │
└──────────────────────────────────────────────────────┘
```

**Key Features:**
- Fixed bottom position (like WoW action bar)
- Large icon-style buttons
- Active page highlighted with golden glow
- Hover effects with tooltip
- Dark background with gold accents

## Layout Structure

### Overall Application Layout

```
┌────────────────────────────────────────────────────┐
│  🎮 MYTHLINE - STORY RESEARCH                      │ Top banner
├────────────────────────────────────────────────────┤
│                                                    │
│                                                    │
│              MAIN CONTENT AREA                     │
│         (Component-specific layout)                │
│                                                    │
│                                                    │
├────────────────────────────────────────────────────┤
│ [🔍 Research] [📖 Create] [👁️ Stories] [📁 Files] │ Bottom nav
└────────────────────────────────────────────────────┘
```

### Background Treatment

- Dark gradient background (#1a1a1a to #0d0d0d)
- Optional subtle texture overlay
- Main content area centered with max-width
- Golden corner accents on main frame

## Frontend Implementation Details

### CSS Architecture

```
src/ui/web/frontend/src/styles/
├── wow-theme.css           # Core WoW theme variables and base styles
├── wow-components.css      # Reusable WoW-styled components
├── wow-animations.css      # Hover effects and transitions
└── layouts/
    ├── research-layout.css     # Research chat specific styles
    ├── creator-layout.css      # Story creator specific styles
    ├── viewer-layout.css       # Story viewer specific styles
    └── explorer-layout.css     # File explorer specific styles
```

### Component Structure Updates

```
src/ui/web/frontend/src/components/
├── common/
│   ├── WowFrame.jsx           # Reusable WoW-styled frame
│   ├── WowButton.jsx          # WoW-styled button
│   ├── WowInput.jsx           # WoW-styled input
│   ├── WowProgressBar.jsx     # WoW-styled progress bar
│   ├── WowTooltip.jsx         # WoW-styled tooltip
│   ├── WowStatusBadge.jsx     # Color-coded status indicator
│   └── ActionBar.jsx          # Bottom navigation bar
├── ResearchChat/
│   ├── ResearchChat.jsx       # Quest log styled layout
│   ├── SessionList.jsx        # Left sidebar quest list
│   ├── ChatArea.jsx           # Quest text area
│   ├── MessageBubble.jsx      # Individual message styling
│   └── ChatInput.jsx          # Message input box
├── StoryCreator/
│   ├── StoryCreator.jsx       # Character sheet layout
│   ├── CreationForm.jsx       # Top input form
│   ├── ProgressPanel.jsx      # Progress bar and status
│   ├── ActivityLog.jsx        # Scrollable log area
│   └── ControlPanel.jsx       # Pause/cancel/view buttons
├── StoryViewer/
│   ├── StoryViewer.jsx        # Quest detail layout
│   ├── StoryTOC.jsx           # Tree view table of contents
│   ├── ContentPreview.jsx     # Parchment-styled content
│   └── ExportPanel.jsx        # Download buttons
└── FileExplorer/
    ├── FileExplorer.jsx       # Bag layout
    ├── FileGrid.jsx           # Grid of file icons
    ├── FileIcon.jsx           # Individual file icon with rarity border
    ├── FileDetails.jsx        # Selected file info panel
    └── FileActions.jsx        # View/download/delete buttons
```

## Implementation Phases

### Phase 1: WoW Theme Foundation (2-3 hours)

**Tasks:**
1. Create base CSS file with WoW color variables
2. Import Google Fonts (Cinzel, IM Fell, Roboto Condensed)
3. Create reusable WoW component styles:
   - `.wow-frame` base styles
   - `.wow-button` with hover effects
   - `.wow-input` form styling
   - `.wow-progress-bar` with gradient
4. Build React wrapper components:
   - `WowFrame.jsx`
   - `WowButton.jsx`
   - `WowInput.jsx`
   - `WowProgressBar.jsx`
5. Create background and layout structure
6. Test components in isolation

**Deliverables:**
- `src/ui/web/frontend/src/styles/wow-theme.css`
- `src/ui/web/frontend/src/styles/wow-components.css`
- `src/ui/web/frontend/src/components/common/Wow*.jsx` components

### Phase 2: Navigation and Layout (1-2 hours)

**Tasks:**
1. Create ActionBar component (bottom navigation)
2. Implement page routing with React Router
3. Create main app layout structure
4. Add golden corner decorations
5. Style top banner
6. Implement active page highlighting

**Deliverables:**
- `src/ui/web/frontend/src/components/common/ActionBar.jsx`
- `src/ui/web/frontend/src/components/common/Layout.jsx`
- `src/ui/web/frontend/src/App.jsx` with routing

### Phase 3: Research Chat UI (2-3 hours)

**Tasks:**
1. Create quest log-styled layout
2. Build SessionList component (left sidebar)
3. Build ChatArea with message styling
4. Create MessageBubble with color coding
5. Style user vs assistant messages
6. Add tool call indicators
7. Create ChatInput with WoW styling
8. Add loading/thinking indicators
9. Implement scrolling behavior

**Deliverables:**
- `src/ui/web/frontend/src/components/ResearchChat/*`
- `src/ui/web/frontend/src/styles/layouts/research-layout.css`

### Phase 4: Story Creator UI (2-3 hours)

**Tasks:**
1. Create character sheet-styled layout
2. Build CreationForm with WoW inputs
3. Create ProgressPanel with gold progress bar
4. Build ActivityLog with color-coded entries
5. Add status icons and badges
6. Create ControlPanel with action buttons
7. Implement real-time progress updates
8. Add review score display
9. Style validation messages

**Deliverables:**
- `src/ui/web/frontend/src/components/StoryCreator/*`
- `src/ui/web/frontend/src/styles/layouts/creator-layout.css`

### Phase 5: Story Viewer UI (1-2 hours)

**Tasks:**
1. Create quest detail-styled layout
2. Build StoryTOC with tree view
3. Add quest markers (blue diamonds)
4. Create ContentPreview with parchment styling
5. Build ExportPanel with download buttons
6. Implement section expansion/collapse
7. Style content display
8. Add copy-to-clipboard functionality

**Deliverables:**
- `src/ui/web/frontend/src/components/StoryViewer/*`
- `src/ui/web/frontend/src/styles/layouts/viewer-layout.css`

### Phase 6: File Explorer UI (1-2 hours)

**Tasks:**
1. Create bag-styled layout
2. Build FileGrid with grid layout
3. Create FileIcon with rarity borders
4. Add hover tooltips
5. Build FileDetails panel
6. Create FileActions with WoW buttons
7. Implement file type color coding
8. Add empty slot styling

**Deliverables:**
- `src/ui/web/frontend/src/components/FileExplorer/*`
- `src/ui/web/frontend/src/styles/layouts/explorer-layout.css`

### Phase 7: Polish and Animations (1-2 hours)

**Tasks:**
1. Add hover glow effects to all buttons
2. Implement smooth transitions
3. Add loading animations
4. Create tooltip system
5. Add box-shadow effects
6. Fine-tune colors and spacing
7. Test responsive behavior
8. Optimize for different screen sizes

**Deliverables:**
- `src/ui/web/frontend/src/styles/wow-animations.css`
- Polished component animations
- Responsive CSS adjustments

### Phase 8: Integration and Testing (2 hours)

**Tasks:**
1. Connect WoW UI to existing backend API
2. Test WebSocket integration with styled components
3. Verify all workflows work with new UI
4. Test browser compatibility
5. Fix any styling issues
6. Performance optimization
7. Documentation updates

**Deliverables:**
- Fully integrated WoW-themed UI
- Updated documentation
- Test results

## Technical Implementation Notes

### React Component Pattern for WoW Styling

**Example: WowButton Component**

```jsx
import React from 'react';
import '../styles/wow-components.css';

export const WowButton = ({
  children,
  onClick,
  variant = 'primary',
  disabled = false,
  icon = null,
  ...props
}) => {
  const classNames = [
    'wow-button',
    `wow-button-${variant}`,
    disabled && 'wow-button-disabled'
  ].filter(Boolean).join(' ');

  return (
    <button
      className={classNames}
      onClick={onClick}
      disabled={disabled}
      {...props}
    >
      {icon && <span className="wow-button-icon">{icon}</span>}
      <span className="wow-button-text">{children}</span>
    </button>
  );
};
```

### CSS Module Pattern

```css
/* wow-components.css */

.wow-button {
  background: linear-gradient(to bottom, var(--wow-panel-brown) 0%, var(--wow-shadow) 100%);
  border: 2px solid var(--wow-gold-accent);
  color: var(--wow-gold);
  font-family: var(--font-primary);
  font-weight: 600;
  padding: 10px 20px;
  cursor: pointer;
  position: relative;
  transition: all 0.2s ease;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.wow-button:hover:not(.wow-button-disabled) {
  border-color: var(--wow-gold);
  box-shadow: 0 0 15px rgba(255, 204, 0, 0.5);
  transform: translateY(-2px);
}

.wow-button:active:not(.wow-button-disabled) {
  transform: translateY(0);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.5);
}

.wow-button-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.wow-button-icon {
  margin-right: 8px;
}
```

### Responsive Design Considerations

```css
/* Mobile adjustments */
@media (max-width: 768px) {
  .wow-frame {
    border-width: 1px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
  }

  .wow-button {
    padding: 8px 16px;
    font-size: 14px;
  }

  .action-bar {
    flex-direction: column;
  }
}

/* Tablet adjustments */
@media (min-width: 769px) and (max-width: 1024px) {
  .research-chat-layout {
    grid-template-columns: 200px 1fr;
  }
}
```

## Assets and Resources

### Required Fonts (Google Fonts)

Add to `index.html`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=IM+Fell+DW+Pica:ital@0;1&family=Roboto+Condensed:wght@400;700&family=Roboto+Mono&display=swap" rel="stylesheet">
```

### Icon Library

Use **React Icons** or **Font Awesome** for UI icons:
- 🔍 Search (research)
- 📖 Book (create story)
- 👁️ Eye (view stories)
- 📁 Folder (files)
- ⚙️ Gear (settings)
- ⚔️ Sword (action/combat)
- ✓ Checkmark (complete)
- ⏸️ Pause
- ❌ Cancel
- 📥 Download

### Optional Texture Images

For enhanced authenticity (optional):
- Stone texture for backgrounds (subtle, dark)
- Parchment texture for content areas (very subtle)
- Golden ornamental corners (SVG or PNG)
- File type icons styled like WoW items

## Testing Checklist

### Visual Testing
- [ ] All WoW colors render correctly
- [ ] Fonts load and display properly
- [ ] Golden borders and shadows appear
- [ ] Hover effects work on all buttons
- [ ] Progress bars animate smoothly
- [ ] Tooltips display correctly
- [ ] Responsive layout works on mobile/tablet

### Functional Testing
- [ ] Navigation between pages works
- [ ] Research chat displays messages correctly
- [ ] Story creator form submits properly
- [ ] Progress updates display in real-time
- [ ] Story viewer shows content correctly
- [ ] File explorer loads and displays files
- [ ] Download/delete actions work
- [ ] WebSocket connections maintain styling

### Browser Compatibility
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (if Mac available)
- [ ] Mobile browsers

## Success Criteria

1. UI successfully captures WoW aesthetic with color palette and typography
2. All four main interfaces styled appropriately:
   - Research Chat = Quest Log style
   - Story Creator = Character Sheet style
   - Story Viewer = Quest Detail style
   - File Explorer = Bag/Inventory style
3. Navigation bar styled like WoW action bar
4. Hover effects and animations enhance interactivity
5. Responsive design works on multiple screen sizes
6. All existing functionality preserved with new styling
7. UI feels cohesive and thematically consistent
8. Performance remains smooth (no lag from styling)

## Timeline Estimate

- Phase 1 (Foundation): 2-3 hours
- Phase 2 (Navigation): 1-2 hours
- Phase 3 (Research Chat): 2-3 hours
- Phase 4 (Story Creator): 2-3 hours
- Phase 5 (Story Viewer): 1-2 hours
- Phase 6 (File Explorer): 1-2 hours
- Phase 7 (Polish): 1-2 hours
- Phase 8 (Integration): 2 hours

**Total: 12-18 hours**

## Future Enhancements (Out of Scope)

- Sound effects for button clicks and notifications
- Animated spell effects for loading states
- Class-themed color schemes (user selectable)
- Achievement system for completed stories
- Minimap-style navigation component
- Combat log-style detailed activity viewer
- Guild roster-style multi-user management
- Talent tree-style preferences configuration
- More elaborate corner decorations and borders
- Particle effects on hover
- Day/night theme toggle (lighter/darker palettes)