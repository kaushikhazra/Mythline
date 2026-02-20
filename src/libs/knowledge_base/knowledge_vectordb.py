import os
import time
from pathlib import Path
from contextlib import contextmanager

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from src.libs.embedding import generate_embedding
from src.libs.parsers import chunk_markdown_by_headers, chunk_story_by_quests

load_dotenv()

STORIES_COLLECTION = "stories_knowledge"


@contextmanager
def qdrant_client():
    qdrant_path = os.getenv('QDRANT_PATH', '.mythline/knowledge_base')
    client = QdrantClient(path=qdrant_path)
    try:
        yield client
    finally:
        try:
            client.close()
        except:
            pass


def derive_collection_name(knowledge_dir: str) -> str:
    dir_name = Path(knowledge_dir).name
    return f"{dir_name}_knowledge"


def get_all_knowledge_collections() -> list[str]:
    with qdrant_client() as client:
        collections = client.get_collections().collections
        return [c.name for c in collections if c.name.endswith('_knowledge')]


def collection_exists(knowledge_dir: str) -> bool:
    with qdrant_client() as client:
        collection_name = derive_collection_name(knowledge_dir)
        collections = client.get_collections().collections
        return any(c.name == collection_name for c in collections)


def create_collection(knowledge_dir: str):
    if collection_exists(knowledge_dir):
        return

    with qdrant_client() as client:
        collection_name = derive_collection_name(knowledge_dir)
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )


def clear_collection(knowledge_dir: str):
    if collection_exists(knowledge_dir):
        collection_name = derive_collection_name(knowledge_dir)

        with qdrant_client() as client:
            client.delete_collection(collection_name=collection_name)

            for i in range(10):
                time.sleep(0.5)
                try:
                    client.get_collection(collection_name)
                    print(f"Waiting for collection '{collection_name}' to be deleted...")
                except Exception:
                    print(f"Collection '{collection_name}' successfully deleted.")
                    break
            else:
                raise RuntimeError(f"Failed to delete collection '{collection_name}' after 5 seconds")

    create_collection(knowledge_dir)


def index_knowledge(knowledge_dir: str, fresh: bool = False):
    create_collection(knowledge_dir)

    collection_name = derive_collection_name(knowledge_dir)
    knowledge_path = Path(knowledge_dir)
    markdown_files = list(knowledge_path.glob('*.md'))

    points = []
    point_id = 0

    if not fresh and collection_exists(knowledge_dir):
        with qdrant_client() as client:
            collection_info = client.get_collection(collection_name)
            points_count = collection_info.points_count

            if points_count > 0:
                records, _ = client.scroll(collection_name=collection_name, limit=10000)
                if records:
                    max_id = max([r.id for r in records], default=-1)
                    point_id = max_id + 1

    for md_file in markdown_files:
        chunks = chunk_markdown_by_headers(str(md_file))

        for chunk in chunks:
            embedding = generate_embedding(chunk['text'])

            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    'text': chunk['text'],
                    'source_file': chunk['source_file'],
                    'section_header': chunk['section_header'],
                    'chunk_index': chunk['chunk_index']
                }
            )

            points.append(point)
            point_id += 1

    if points:
        with qdrant_client() as client:
            client.upsert(
                collection_name=collection_name,
                points=points
            )

    return len(points)


def search_knowledge(query: str, top_k: int = 3) -> list[dict]:
    all_collections = [c for c in get_all_knowledge_collections() if c != STORIES_COLLECTION]

    if not all_collections:
        return []

    query_embedding = generate_embedding(query)
    all_results = []

    with qdrant_client() as client:
        for collection_name in all_collections:
            results = client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=top_k
            )

            for hit in results:
                all_results.append({
                    'text': hit.payload['text'],
                    'source_file': hit.payload['source_file'],
                    'section_header': hit.payload['section_header'],
                    'score': hit.score,
                    'collection': collection_name
                })

    all_results.sort(key=lambda x: x['score'], reverse=True)
    return all_results[:top_k]


def list_all_chunks(knowledge_dir: str) -> list[dict]:
    if not collection_exists(knowledge_dir):
        return []

    collection_name = derive_collection_name(knowledge_dir)

    with qdrant_client() as client:
        records, _ = client.scroll(
            collection_name=collection_name,
            limit=1000
        )

        return [
            {
                'id': record.id,
                'source_file': record.payload['source_file'],
                'section_header': record.payload['section_header'],
                'chunk_index': record.payload['chunk_index'],
                'text_preview': record.payload['text'][:100] + '...' if len(record.payload['text']) > 100 else record.payload['text'],
                'collection': collection_name
            }
            for record in records
        ]


def _ensure_stories_collection():
    with qdrant_client() as client:
        collections = client.get_collections().collections
        if not any(c.name == STORIES_COLLECTION for c in collections):
            client.create_collection(
                collection_name=STORIES_COLLECTION,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )


def index_story(story_path: str) -> int:
    _ensure_stories_collection()

    chunks = chunk_story_by_quests(story_path)

    if not chunks:
        return 0

    points = []
    point_id = 0

    with qdrant_client() as client:
        collection_info = client.get_collection(STORIES_COLLECTION)
        if collection_info.points_count > 0:
            records, _ = client.scroll(collection_name=STORIES_COLLECTION, limit=10000)
            if records:
                max_id = max([r.id for r in records], default=-1)
                point_id = max_id + 1

    for chunk in chunks:
        embedding = generate_embedding(chunk['text'])

        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                'text': chunk['text'],
                'story_subject': chunk['story_subject'],
                'story_title': chunk['story_title'],
                'quest_ids': chunk['quest_ids'],
                'phase': chunk['phase'],
                'section': chunk['section'],
                'npcs': chunk['npcs'],
                'section_header': chunk['section_header']
            }
        )

        points.append(point)
        point_id += 1

    if points:
        with qdrant_client() as client:
            client.upsert(
                collection_name=STORIES_COLLECTION,
                points=points
            )

    return len(points)


def search_story_knowledge(query: str, top_k: int = 3) -> list[dict]:
    with qdrant_client() as client:
        collections = client.get_collections().collections
        if not any(c.name == STORIES_COLLECTION for c in collections):
            return []

    query_embedding = generate_embedding(query)

    with qdrant_client() as client:
        results = client.search(
            collection_name=STORIES_COLLECTION,
            query_vector=query_embedding,
            limit=top_k
        )

        return [
            {
                'text': hit.payload['text'],
                'story_subject': hit.payload['story_subject'],
                'story_title': hit.payload['story_title'],
                'quest_ids': hit.payload.get('quest_ids', []),
                'phase': hit.payload.get('phase'),
                'section': hit.payload.get('section'),
                'npcs': hit.payload['npcs'],
                'section_header': hit.payload['section_header'],
                'score': hit.score
            }
            for hit in results
        ]


def list_all_story_chunks() -> list[dict]:
    with qdrant_client() as client:
        collections = client.get_collections().collections
        if not any(c.name == STORIES_COLLECTION for c in collections):
            return []

        records, _ = client.scroll(collection_name=STORIES_COLLECTION, limit=1000)

        return [
            {
                'id': record.id,
                'story_subject': record.payload['story_subject'],
                'story_title': record.payload['story_title'],
                'quest_ids': record.payload.get('quest_ids', []),
                'phase': record.payload.get('phase'),
                'section': record.payload.get('section'),
                'npcs': record.payload['npcs'],
                'section_header': record.payload['section_header'],
                'text_preview': record.payload['text'][:100] + '...' if len(record.payload['text']) > 100 else record.payload['text']
            }
            for record in records
        ]


def delete_story_by_subject(subject: str) -> int:
    with qdrant_client() as client:
        collections = client.get_collections().collections
        if not any(c.name == STORIES_COLLECTION for c in collections):
            return 0

        records, _ = client.scroll(collection_name=STORIES_COLLECTION, limit=10000)

        ids_to_delete = [
            record.id for record in records
            if record.payload.get('story_subject') == subject
        ]

        if ids_to_delete:
            client.delete(
                collection_name=STORIES_COLLECTION,
                points_selector=ids_to_delete
            )

        return len(ids_to_delete)


def deduplicate_collection(knowledge_dir: str) -> tuple[int, int]:
    if not collection_exists(knowledge_dir):
        return 0, 0

    collection_name = derive_collection_name(knowledge_dir)

    with qdrant_client() as client:
        records, _ = client.scroll(collection_name=collection_name, limit=10000)

        if not records:
            return 0, 0

        seen = {}
        duplicates = []

        for record in records:
            key = (record.payload['source_file'], record.payload['section_header'])
            if key in seen:
                duplicates.append(record.id)
            else:
                seen[key] = record.id

        if duplicates:
            client.delete(
                collection_name=collection_name,
                points_selector=duplicates
            )

        return len(records), len(duplicates)
