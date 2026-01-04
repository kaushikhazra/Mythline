import re
from pathlib import Path
from collections import defaultdict


def parse_quest_chain(file_path: str) -> dict:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    quests = _parse_quests_section(content)
    edges, nodes = _parse_mermaid_graph(content)
    setting = _parse_setting_section(content)
    roleplay = _parse_roleplay_section(content, quests.keys())

    return {
        'quests': quests,
        'edges': edges,
        'nodes': nodes,
        'graph': _build_adjacency_list(edges),
        'setting': setting,
        'roleplay': roleplay
    }


def _parse_setting_section(content: str) -> dict:
    setting = {
        'start': None,
        'zone': None,
        'journey': None
    }

    start_match = re.search(r'^- Start:\s*(.+)$', content, re.MULTILINE)
    if start_match:
        setting['start'] = start_match.group(1).strip()

    zone_match = re.search(r'^- Zone:\s*(.+)$', content, re.MULTILINE)
    if zone_match:
        setting['zone'] = zone_match.group(1).strip()

    journey_match = re.search(r'^- Journey:\s*(.+)$', content, re.MULTILINE)
    if journey_match:
        setting['journey'] = journey_match.group(1).strip()

    return setting


def _parse_roleplay_section(content: str, quest_ids: list[str]) -> dict:
    roleplay_match = re.search(r'## Roleplay\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if not roleplay_match:
        return {}

    roleplay_content = roleplay_match.group(1)

    valid_keys = _build_roleplay_keys(quest_ids)
    key_pattern = re.compile(r'^(' + '|'.join(re.escape(k) for k in valid_keys) + r'):\s*$', re.MULTILINE)

    matches = list(key_pattern.finditer(roleplay_content))
    if not matches:
        return {}

    roleplay = {}
    for i, match in enumerate(matches):
        key = match.group(1)
        start_pos = match.end()

        if i + 1 < len(matches):
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(roleplay_content)

        value = roleplay_content[start_pos:end_pos].strip()
        if value:
            roleplay[key] = value

    return roleplay


def _build_roleplay_keys(quest_ids: list[str]) -> list[str]:
    keys = ['Introduction', 'Conclusion']
    for qid in quest_ids:
        keys.extend([f'{qid}.accept', f'{qid}.exec', f'{qid}.complete'])
    return keys


def _parse_quests_section(content: str) -> dict:
    quests = {}
    quest_pattern = re.compile(r'^- ([A-Z]):\s*(https?://\S+)', re.MULTILINE)

    for match in quest_pattern.finditer(content):
        quest_id = match.group(1)
        url = match.group(2)
        quests[quest_id] = url

    return quests


def _parse_mermaid_graph(content: str) -> tuple[list, set]:
    mermaid_match = re.search(r'```mermaid\s*\n(.*?)```', content, re.DOTALL)
    if not mermaid_match:
        return [], set()

    mermaid_content = mermaid_match.group(1)
    edge_pattern = re.compile(r'(\S+)\s*-->\s*(\S+)')

    edges = []
    nodes = set()

    for match in edge_pattern.finditer(mermaid_content):
        source = match.group(1)
        target = match.group(2)
        edges.append((source, target))
        nodes.add(source)
        nodes.add(target)

    return edges, nodes


def _build_adjacency_list(edges: list) -> dict:
    graph = defaultdict(list)
    for source, target in edges:
        graph[source].append(target)
    return dict(graph)


def get_node_info(node: str) -> tuple[str, str]:
    if node == 'Start':
        return None, 'start'

    parts = node.split('.')
    if len(parts) == 2:
        return parts[0], parts[1]

    return None, None


def get_execution_order(quest_chain: dict) -> list[dict]:
    graph = quest_chain['graph']
    edges = quest_chain['edges']

    in_degree = defaultdict(int)
    for node in quest_chain['nodes']:
        in_degree[node] = 0
    for source, target in edges:
        in_degree[target] += 1

    reverse_graph = defaultdict(list)
    for source, target in edges:
        reverse_graph[target].append(source)

    segments = []
    visited = set()
    queue = ['Start']

    while queue:
        level_nodes = []
        next_queue = []

        for node in queue:
            if node in visited:
                continue
            visited.add(node)

            if node != 'Start':
                level_nodes.append(node)

            for neighbor in graph.get(node, []):
                all_deps_visited = all(dep in visited for dep in reverse_graph[neighbor])
                if all_deps_visited and neighbor not in visited:
                    next_queue.append(neighbor)

        if level_nodes:
            parallel_groups = _group_parallel_nodes(level_nodes)
            for group in parallel_groups:
                segments.append({
                    'nodes': group,
                    'is_parallel': len(group) > 1,
                    'phase': get_node_info(group[0])[1] if group else None
                })

        queue = list(set(next_queue))

    return segments


def _group_parallel_nodes(nodes: list) -> list[list]:
    phase_groups = defaultdict(list)
    for node in nodes:
        quest_id, phase = get_node_info(node)
        phase_groups[phase].append(node)

    return [group for group in phase_groups.values()]


def get_quest_ids_in_order(quest_chain: dict) -> list[str]:
    segments = get_execution_order(quest_chain)
    seen = set()
    order = []

    for segment in segments:
        for node in segment['nodes']:
            quest_id, _ = get_node_info(node)
            if quest_id and quest_id not in seen:
                seen.add(quest_id)
                order.append(quest_id)

    return order


def find_parallel_executions(quest_chain: dict) -> list[list[str]]:
    segments = get_execution_order(quest_chain)
    parallel_execs = []

    for segment in segments:
        if segment['is_parallel'] and segment['phase'] == 'exec':
            quest_ids = [get_node_info(node)[0] for node in segment['nodes']]
            parallel_execs.append(quest_ids)

    return parallel_execs
