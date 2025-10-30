## Overview
World of Warcraft is an MMORPG. Role-playing is a very big aspect of the game. I am trying to exploit the role-playing side of the game to create narration and dialog-based storytelling videos for a YouTube audience.

This story guide explains how to write such a story so that it can be used to create an engaging YouTube gameplay video, which is narration and dialog-rich and engaging.

## Theme
The stories are themed as a journey of a female character finding her way in the world of World of Warcraft.

Each story is part of a continuing series that takes the audience through a journey.

The story of each character starts from their respective starting zone and follows a path based on the usual questing flow in World of Warcraft. For example, the human warlock Eliryssa started from Northshire Abbey in Elwynn Forest and is working her way through Goldshire. 

The stories are structured so that the quests become the main topic of the journey. There is an introduction to the story, which usually pulls context from the previous story and then gives an idea of the current story. Then the story is broken into quest blocks, where the quests are first introduced with a bit of backstory and why the character is doing this quest. The actual quest text is then converted to a dialog between the NPC or a narration depending on the quest giver. After that, a narration describes how the character fulfils the quest, and the completion follows the same pattern as the quest start.


## Story Structure
Each story should have the following sections:
  - Introduction
  - Quests
    - Quest Introduction
    - Quest Dialog
    - Quest Execution
    - Quest Completion
  - Conclusion

The sequence of the above sections should be maintained at all costs.

### Introduction Section
- The introduction section must have an "## Introduction" header
- The introduction section must have at least 200 words
- The introduction section should set the plot of the story with a little backstory information.

### Quest Sections:
- Each quest in the story should have its own section
- The quest section must have a heading "## {Quest Name}"
- This section must have 3 subsections:
  - **Quest Introduction:** This is where you help me write an introduction to the quest. Mainly it will talk about the backstory of the quest while keeping continuity from the previous section.
  - **Quest Dialog:** This section is a bit complex:
    - If the character is interacting with an object:
      - Then describe the quest in 3rd person
    - If the character is interacting with an NPC:
      - Then break the quest text into a dialog between the character and the NPC
  - **Quest Execution:** In this section, you describe how the character achieves their objective. Describe it in 3rd person.
  - **Quest Completion:** This is the same as "Quest Dialog":
    - If the character is interacting with an object:
      - Then describe the quest in 3rd person
    - If the character is interacting with an NPC:
      - Then break the quest completion text into a dialog between the character and the NPC
- Example of a quest section in markdown:
```markdown
## {Quest1 Name}
### Quest Introduction
{quest introduction}
### Quest Dialogue
{quest dialogue}
### Quest Execution
{quest execution narration}
### Quest Completion
{quest completion dialogue}

## {Quest2 Name}
### Quest Introduction
{quest introduction}
### Quest Dialogue
{quest dialogue}
### Quest Execution
{quest execution narration}
### Quest Completion
{quest completion dialogue}
```

### Conclusion Section
- The conclusion section must have a "## Conclusion" header.
- This section should end the story with a satisfying conclusion, yet give a hint that the story is going to continue.
