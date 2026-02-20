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
            'quest_ids': [],
            'phase': None,
            'section': 'introduction',
            'npcs': [],
            'section_header': 'Story Introduction'
        })

    for segment in story.get('segments', []):
        quest_ids = segment.get('quest_ids', [])
        phase = segment.get('phase', '')
        section = segment.get('section', '')
        quest_ids_str = ', '.join(quest_ids)

        text_parts = []
        npcs = set()

        if segment.get('text'):
            text_parts.append(segment['text'])

        if segment.get('lines'):
            for line in segment['lines']:
                actor = line.get('actor', '')
                spoken = line.get('line', '')
                text_parts.append(f"{actor}: {spoken}")
                if actor:
                    npcs.add(actor)

        chunks.append({
            'text': '\n\n'.join(text_parts),
            'story_subject': story_subject,
            'story_title': story_title,
            'quest_ids': quest_ids,
            'phase': phase,
            'section': section,
            'npcs': list(npcs),
            'section_header': f'Quest {quest_ids_str} - {phase.capitalize()} {section.capitalize()}'
        })

    if story.get('conclusion'):
        chunks.append({
            'text': story['conclusion'].get('text', ''),
            'story_subject': story_subject,
            'story_title': story_title,
            'quest_ids': [],
            'phase': None,
            'section': 'conclusion',
            'npcs': [],
            'section_header': 'Story Conclusion'
        })

    return chunks
