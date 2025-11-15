# CLI Pattern: Batch Processing

## Overview

This pattern creates a CLI that processes input files in batches with progress tracking. Ideal for transforming large files or collections of data through a stateless agent.

**Use this pattern when:**
- Processing input files chunk by chunk
- Need progress bar for long operations
- Agent is stateless (no session context needed)
- Transforming data from one format to another
- Appending results incrementally to output file

**Example in codebase:**
- `src/ui/cli/generate_shots.py` - Converts story markdown into individual shots

---

## Common Components Template

```python
# ============================================================
# IMPORTS
# ============================================================
from tqdm import tqdm
from src.agents.{agent_module}.agent import {AgentClass}
from src.libs.utils.markdown_parser import parse_markdown
from src.libs.utils.argument_parser import get_arguments
from src.libs.filesystem.file_operations import read_file, append_file


# ============================================================
# ARGUMENT PARSING
# ============================================================
args = get_arguments(
    agent_id='{agent_id}',
    description='{AgentName} CLI',
    require_input=True,
    require_output=True
)
input_file = args.input_file
output_file = args.output_file
verbose = args.verbose


# ============================================================
# READ AND PARSE INPUT
# ============================================================
input_content = read_file(input_file)
chunks = {parse_function}(input_content)


# ============================================================
# STATELESS AGENT INSTANTIATION
# ============================================================
agent = {AgentClass}()


# ============================================================
# BATCH PROCESSING WITH PROGRESS BAR
# ============================================================
{counter_init}
for i, chunk in tqdm(enumerate(chunks, 1), total=len(chunks), desc="Processing chunks"):
    if verbose:
        print(f"\n{'='*60}")
        print(f"CHUNK {i}")
        print(f"{'='*60}\n")
        print(chunk)

    response = agent.run(chunk)

    {post_process_output}

    for item in processed_items:
        if item.strip() != "":
            {format_output}
            if verbose:
                print(formatted_item)
            append_file(output_file, formatted_item + '\n')
            {increment_counter}
```

---

## Function-Specific Customization Points

### 1. Agent Import
```python
# CUSTOMIZE: Import your stateless agent
from src.agents.{agent_module}.agent import {AgentClass}
```

**Example:**
```python
from src.agents.shot_creator_agent.agent import ShotCreator
```

### 2. Parser Import
```python
# CUSTOMIZE: Import appropriate parser for your input format
from src.libs.utils.markdown_parser import parse_markdown
# OR
from src.libs.utils.json_parser import parse_json
# OR write custom parser
```

### 3. Agent ID
```python
# CUSTOMIZE: Use agent ID string (stateless agents may not have AGENT_ID constant)
agent_id='{agent_id}'
```

**Example:**
```python
agent_id='shot_creator'
```

### 4. Input Parsing
```python
# CUSTOMIZE: Parse input into processable chunks
chunks = {parse_function}(input_content)
```

**Examples:**
```python
# Markdown sections
chunks = parse_markdown(input_content)

# Split by delimiter
chunks = input_content.split('---')

# Line by line
chunks = input_content.split('\n')

# JSON array
import json
chunks = json.loads(input_content)

# Custom chunking
chunks = custom_chunk_function(input_content, chunk_size=1000)
```

### 5. Counter Initialization (Optional)
```python
# CUSTOMIZE: Initialize counter if needed for output formatting
{counter_init}
```

**Examples:**
```python
shot_number = 1
item_count = 0
page_number = 1
```

### 6. Post-Processing Output
```python
# CUSTOMIZE: Process agent output before writing
{post_process_output}
```

**Examples:**
```python
# Clean markdown formatting
processed_output = response.output.replace('```markdown','').replace('```','')

# Split into items
items = processed_output.split("---")

# Parse JSON response
import json
items = json.loads(response.output)

# No processing needed
items = [response.output]
```

### 7. Format Output
```python
# CUSTOMIZE: Format each item before appending
{format_output}
```

**Examples:**
```python
# Add shot number
formatted_item = f"## Shot {shot_number}{item}"

# Add timestamp
from datetime import datetime
formatted_item = f"{datetime.now()}: {item}"

# Add JSON formatting
formatted_item = json.dumps(item, indent=2)

# No formatting
formatted_item = item
```

### 8. Increment Counter (Optional)
```python
# CUSTOMIZE: Update counter if used
{increment_counter}
```

**Examples:**
```python
shot_number += 1
item_count += 1
```

---

## Complete Working Example

**File:** `src/ui/cli/generate_shots.py`

```python
from tqdm import tqdm
from src.agents.shot_creator_agent.agent import ShotCreator
from src.libs.utils.markdown_parser import parse_markdown
from src.libs.utils.argument_parser import get_arguments
from src.libs.filesystem.file_operations import read_file, append_file

args = get_arguments(
    agent_id='shot_creator',
    description='Shot Generator CLI',
    require_input=True,
    require_output=True
)
input_file = args.input_file
output_file = args.output_file
verbose = args.verbose

story_md = read_file(input_file)
chunks = parse_markdown(story_md)

shot_creator = ShotCreator()

shot_number = 1
for i, chunk_md in tqdm(enumerate(chunks, 1), total=len(chunks), desc="Processing chunks"):
    if verbose:
        print(f"\n{'='*60}")
        print(f"CHUNK {i}")
        print(f"{'='*60}\n")
        print(chunk_md)

    response = shot_creator.run(chunk_md)
    shots = response.output.replace('```markdown','').replace('```','').split("---")

    for shot in shots:
        if shot.strip() != "":
            shot_chunk = f"## Shot {shot_number}{shot}"
            if verbose:
                print(shot_chunk)
            append_file(output_file, shot_chunk + '\n')
            shot_number += 1
```

---

## Usage

### Running the CLI

```bash
# Basic execution
python -m src.ui.cli.generate_shots -i input.md -o output.md

# With verbose output
python -m src.ui.cli.generate_shots -i input.md -o output.md -v

# Using long flags
python -m src.ui.cli.generate_shots --input input.md --output output.md --verbose
```

### Execution Flow

```
$ python -m src.ui.cli.generate_shots -i story.md -o shots.md
Processing chunks: 100%|██████████| 25/25 [00:45<00:00,  1.82s/chunk]
```

### Verbose Output

```
$ python -m src.ui.cli.generate_shots -i story.md -o shots.md -v
Processing chunks:   4%|▍         | 1/25 [00:02<00:43,  1.82s/chunk]
============================================================
CHUNK 1
============================================================

# Opening Scene
The sun rises over Shadowglen...

## Shot 1
**Type:** Establishing
**Camera:** Wide aerial shot
**Description:** Sun rising over Shadowglen...

Processing chunks:   8%|▊         | 2/25 [00:04<00:41,  1.80s/chunk]
...
```

---

## Key Features

### Progress Bar
- Uses `tqdm` for visual progress indication
- Shows completion percentage, elapsed time, ETA
- Items per second processing rate

### Stateless Agent
- No session management needed
- Each chunk processed independently
- Lightweight and fast

### Incremental Output
- Results appended to file as they're generated
- Partial results preserved if interrupted
- Can resume by processing remaining chunks

### Verbose Mode
- Optional detailed output for debugging
- Shows each chunk and its processed result
- Controlled by `-v` or `--verbose` flag

### File I/O Utilities
- Uses `read_file()` for input
- Uses `append_file()` for incremental output
- Handles file operations cleanly

---

## Decision Guide

**Choose this pattern if:**
- ✅ Processing files in chunks or batches
- ✅ Need progress tracking for long operations
- ✅ Agent is stateless (no conversation context)
- ✅ Transforming input to different output format
- ✅ Want incremental output writing

**Choose a different pattern if:**
- ❌ Need user interaction → Use `interface_cli_interactive.md`
- ❌ Single async operation → Use `interface_cli_async.md`
- ❌ Need conversation context → Use `interface_cli_interactive.md`
- ❌ Multiple subcommands → Use `interface_cli_subcommand.md`

---

## Related Patterns

- **interface_cli_common.md** - Shared components reference
- **interface_cli_async.md** - Async single execution
- **interface_cli_subcommand.md** - Multiple commands

---

## Common Modifications

### Add File Validation

```python
import os

if not os.path.exists(input_file):
    print(f"Error: Input file not found: {input_file}")
    sys.exit(1)

if os.path.exists(output_file):
    response = input(f"Output file {output_file} exists. Overwrite? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        sys.exit(0)
```

### Clear Output File Before Processing

```python
from src.libs.filesystem.file_operations import write_file

write_file(output_file, "")

for chunk in tqdm(chunks, desc="Processing"):
    response = agent.run(chunk)
    append_file(output_file, response.output + '\n')
```

### Add Error Handling Per Chunk

```python
errors = []
for i, chunk in tqdm(enumerate(chunks, 1), total=len(chunks)):
    try:
        response = agent.run(chunk)
        append_file(output_file, response.output + '\n')
    except Exception as e:
        errors.append((i, str(e)))
        if verbose:
            print(f"Error processing chunk {i}: {e}")

if errors:
    print(f"\n{len(errors)} chunks failed:")
    for chunk_num, error in errors:
        print(f"  Chunk {chunk_num}: {error}")
```

### Add Summary Statistics

```python
total_items = 0
start_time = time.time()

for chunk in tqdm(chunks, desc="Processing"):
    response = agent.run(chunk)
    items = process_output(response.output)
    total_items += len(items)
    for item in items:
        append_file(output_file, item + '\n')

elapsed = time.time() - start_time
print(f"\nProcessed {total_items} items in {elapsed:.2f} seconds")
print(f"Average: {total_items/elapsed:.2f} items/second")
```

### Process Multiple Files

```python
import glob

input_pattern = "input/*.md"
input_files = glob.glob(input_pattern)

for input_file in input_files:
    output_file = input_file.replace('input/', 'output/')
    print(f"\nProcessing {input_file}...")

    content = read_file(input_file)
    chunks = parse_markdown(content)

    for chunk in tqdm(chunks, desc=f"Processing {input_file}"):
        response = agent.run(chunk)
        append_file(output_file, response.output + '\n')
```

### Add Parallel Processing

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

def process_chunk(chunk):
    response = agent.run(chunk)
    return response.output

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(tqdm(
        executor.map(process_chunk, chunks),
        total=len(chunks),
        desc="Processing"
    ))

for result in results:
    append_file(output_file, result + '\n')
```

---

## Advanced Variations

### Batch Processing with Grouping

```python
batch_size = 10
for i in range(0, len(chunks), batch_size):
    batch = chunks[i:i+batch_size]
    batch_text = "\n---\n".join(batch)

    response = agent.run(batch_text)
    append_file(output_file, response.output + '\n')

    if verbose:
        print(f"Processed batch {i//batch_size + 1}")
```

### Resume from Checkpoint

```python
import json

checkpoint_file = "processing_checkpoint.json"
if os.path.exists(checkpoint_file):
    with open(checkpoint_file, 'r') as f:
        checkpoint = json.load(f)
        start_index = checkpoint['last_processed'] + 1
    print(f"Resuming from chunk {start_index}")
else:
    start_index = 0

for i, chunk in tqdm(
    enumerate(chunks[start_index:], start_index),
    initial=start_index,
    total=len(chunks),
    desc="Processing"
):
    response = agent.run(chunk)
    append_file(output_file, response.output + '\n')

    with open(checkpoint_file, 'w') as f:
        json.dump({'last_processed': i}, f)

os.remove(checkpoint_file)
print("Processing complete!")
```

### Conditional Processing

```python
def should_process(chunk):
    return len(chunk) > 100 and 'important' in chunk.lower()

chunks_to_process = [c for c in chunks if should_process(c)]
print(f"Processing {len(chunks_to_process)} of {len(chunks)} chunks")

for chunk in tqdm(chunks_to_process, desc="Processing"):
    response = agent.run(chunk)
    append_file(output_file, response.output + '\n')
```

### Multi-Format Output

```python
output_md = args.output_file
output_json = output_md.replace('.md', '.json')
output_html = output_md.replace('.md', '.html')

results = []
for chunk in tqdm(chunks, desc="Processing"):
    response = agent.run(chunk)
    results.append(response.output)

    append_file(output_md, response.output + '\n')

import json
write_file(output_json, json.dumps(results, indent=2))

html_content = '\n'.join([f"<div>{r}</div>" for r in results])
write_file(output_html, f"<html><body>{html_content}</body></html>")
```

---

## Troubleshooting

**Issue:** Progress bar not updating smoothly
- Ensure loop iterations are not too fast (< 0.1s each)
- Use `tqdm.write()` instead of `print()` for output during loop
- Check terminal supports ANSI escape codes

**Issue:** Output file corrupted or incomplete
- Use `append_file()` which handles encoding properly
- Add try/except to ensure file is closed on error
- Consider adding newlines between items

**Issue:** Running out of memory with large files
- Process chunks in smaller batches
- Use generators instead of loading all chunks at once
- Consider streaming parser for very large files

**Issue:** Agent processing too slow
- Profile agent execution to find bottlenecks
- Consider parallel processing with ThreadPoolExecutor
- Batch multiple small chunks together

**Issue:** Verbose output interferes with progress bar
- Use `tqdm.write()` instead of `print()`
- Disable progress bar when verbose is enabled
- Write verbose output to separate log file

**Example with tqdm.write:**
```python
for chunk in tqdm(chunks, desc="Processing"):
    if verbose:
        tqdm.write(f"Processing chunk: {chunk[:50]}...")
    response = agent.run(chunk)
    append_file(output_file, response.output + '\n')
```
