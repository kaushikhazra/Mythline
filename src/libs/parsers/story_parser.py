import json
from pathlib import Path


def chunk_story_by_quests(file_path: str) -> list[dict]:
    with open(file_path, 'r', encoding='utf-8') as f:
        story = json.load(f)

    chunks = []
    story_subject = story.get('subject', Path(file_path).parent.name)
    story_title = story.get('title', 'Untitled Story')

    if story.get('introduction'):
        chunks.append({
            'text': story['introduction'].get('text', ''),
            'story_subject': story_subject,
            'story_title': story_title,
            'quest_title': None,
            'quest_index': -1,
            'npcs': [],
            'section_header': 'Story Introduction'
        })

    for quest_index, quest in enumerate(story.get('quests', [])):
        quest_title = quest.get('title', f'Quest {quest_index + 1}')
        sections = quest.get('sections', {})

        text_parts = []
        npcs = set()

        if sections.get('introduction'):
            text_parts.append(sections['introduction'].get('text', ''))

        if sections.get('dialogue'):
            for line in sections['dialogue'].get('lines', []):
                actor = line.get('actor', '')
                spoken = line.get('line', '')
                text_parts.append(f"{actor}: {spoken}")
                if actor:
                    npcs.add(actor)

        if sections.get('execution'):
            text_parts.append(sections['execution'].get('text', ''))

        if sections.get('completion'):
            for line in sections['completion'].get('lines', []):
                actor = line.get('actor', '')
                spoken = line.get('line', '')
                text_parts.append(f"{actor}: {spoken}")
                if actor:
                    npcs.add(actor)

        chunks.append({
            'text': '\n\n'.join(text_parts),
            'story_subject': story_subject,
            'story_title': story_title,
            'quest_title': quest_title,
            'quest_index': quest_index,
            'npcs': list(npcs),
            'section_header': f'Quest: {quest_title}'
        })

    if story.get('conclusion'):
        chunks.append({
            'text': story['conclusion'].get('text', ''),
            'story_subject': story_subject,
            'story_title': story_title,
            'quest_title': None,
            'quest_index': len(story.get('quests', [])),
            'npcs': [],
            'section_header': 'Story Conclusion'
        })

    return chunks
