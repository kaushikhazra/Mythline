# Backend: File Operations

File upload, download, and management in FastAPI.

---

## Overview

**Use when:** File uploads, file downloads, directory listing, file validation.

**Pattern:**
```
Upload File → Validate → Process → Store → Return Response
```

---

## File Download

### Basic File Download

```python
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter()

@router.get("/download/{filename}")
async def download_file(filename: str):
    file_path = Path(f"output/{filename}")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )
```

### Download with Custom Name

```python
@router.get("/download/{filename}")
async def download_file(filename: str):
    file_path = Path(f"output/{filename}")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename="custom_name.txt",  # Different download name
        media_type='text/plain'
    )
```

### Download Specific File Types

```python
# Markdown file
@router.get("/stories/{subject}/download")
async def download_story(subject: str):
    story_file = Path(f"output/{subject}/story.md")

    if not story_file.exists():
        raise HTTPException(status_code=404, detail="Story not found")

    return FileResponse(
        path=story_file,
        filename=f"{subject}_story.md",
        media_type='text/markdown'
    )

# JSON file
@router.get("/stories/{subject}/json")
async def download_story_json(subject: str):
    json_file = Path(f"output/{subject}/story.json")

    if not json_file.exists():
        raise HTTPException(status_code=404, detail="Story not found")

    return FileResponse(
        path=json_file,
        filename=f"{subject}.json",
        media_type='application/json'
    )
```

---

## File Upload

### Single File Upload

```python
from fastapi import UploadFile, File

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Read file content
    content = await file.read()

    # Save file
    file_path = Path(f"uploads/{file.filename}")
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'wb') as f:
        f.write(content)

    return {
        "filename": file.filename,
        "size": len(content),
        "content_type": file.content_type
    }
```

### File Validation

```python
@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Validate file extension
    allowed_extensions = ['.txt', '.md', '.json']
    file_ext = Path(file.filename).suffix

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {allowed_extensions}"
        )

    # Validate file size
    content = await file.read()
    max_size = 5 * 1024 * 1024  # 5MB

    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: 5MB"
        )

    # Save file
    file_path = Path(f"uploads/{file.filename}")
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'wb') as f:
        f.write(content)

    return {"filename": file.filename, "size": len(content)}
```

### Multiple File Upload

```python
from typing import List

@router.post("/upload-multiple")
async def upload_multiple(files: List[UploadFile] = File(...)):
    results = []

    for file in files:
        content = await file.read()

        file_path = Path(f"uploads/{file.filename}")
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'wb') as f:
            f.write(content)

        results.append({
            "filename": file.filename,
            "size": len(content)
        })

    return {"files": results}
```

---

## Directory Operations

### List Files in Directory

```python
@router.get("/stories/list")
async def list_stories():
    output_dir = Path("output")

    if not output_dir.exists():
        return []

    stories = []
    for item in output_dir.iterdir():
        if item.is_dir():
            story_file = item / "story.json"
            if story_file.exists():
                stories.append(item.name)

    return sorted(stories)
```

### List with Metadata

```python
from datetime import datetime

@router.get("/files/list")
async def list_files():
    files_dir = Path("output")

    if not files_dir.exists():
        return []

    files = []
    for file_path in files_dir.glob("**/*.md"):
        stat = file_path.stat()
        files.append({
            "name": file_path.name,
            "path": str(file_path),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })

    return files
```

---

## File Content Operations

### Read File Content

```python
@router.get("/stories/{subject}")
async def get_story(subject: str):
    story_file = Path(f"output/{subject}/story.json")

    if not story_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Story not found for subject: {subject}"
        )

    import json
    return json.loads(story_file.read_text())
```

### Read Text File

```python
@router.get("/files/{filename}")
async def get_file_content(filename: str):
    file_path = Path(f"data/{filename}")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    content = file_path.read_text(encoding='utf-8')
    return {"content": content}
```

---

## File Deletion

### Delete Single File

```python
@router.delete("/files/{filename}")
async def delete_file(filename: str):
    file_path = Path(f"uploads/{filename}")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    file_path.unlink()
    return {"status": "deleted", "filename": filename}
```

### Delete Directory

```python
import shutil

@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    project_dir = Path(f"output/{project_id}")

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    shutil.rmtree(project_dir)
    return {"status": "deleted", "project_id": project_id}
```

---

## Path Validation

### Prevent Path Traversal

```python
@router.get("/files/{filename}")
async def get_file(filename: str):
    # Validate filename (prevent path traversal)
    if '..' in filename or filename.startswith('/'):
        raise HTTPException(
            status_code=400,
            detail="Invalid filename"
        )

    file_path = Path("data") / filename

    # Ensure file is within allowed directory
    allowed_dir = Path("data").resolve()
    if not file_path.resolve().is_relative_to(allowed_dir):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path=file_path)
```

---

## Complete Example

### Story File Management

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import json

router = APIRouter()

@router.get("/stories/list")
async def list_stories():
    output_dir = Path("output")
    if not output_dir.exists():
        return []

    stories = []
    for item in output_dir.iterdir():
        if item.is_dir():
            story_file = item / "story.json"
            if story_file.exists():
                stories.append(item.name)

    return sorted(stories)

@router.get("/stories/{subject}")
async def get_story(subject: str):
    story_file = Path(f"output/{subject}/story.json")

    if not story_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Story not found for subject: {subject}"
        )

    return json.loads(story_file.read_text())

@router.get("/stories/{subject}/download")
async def download_story(subject: str):
    story_file = Path(f"output/{subject}/story.md")

    if not story_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Story file not found"
        )

    return FileResponse(
        path=story_file,
        filename=f"{subject}_story.md",
        media_type='text/markdown'
    )

@router.delete("/stories/{subject}")
async def delete_story(subject: str):
    story_dir = Path(f"output/{subject}")

    if not story_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Story not found"
        )

    import shutil
    shutil.rmtree(story_dir)

    return {"status": "deleted", "subject": subject}
```

---

## Streaming Large Files

### Stream File Response

```python
from fastapi.responses import StreamingResponse

@router.get("/download/large/{filename}")
async def download_large_file(filename: str):
    file_path = Path(f"output/{filename}")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    def file_iterator():
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(
        file_iterator(),
        media_type='application/octet-stream',
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
```

---

## MIME Types

### Common MIME Types

```python
MIME_TYPES = {
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.json': 'application/json',
    '.pdf': 'application/pdf',
    '.zip': 'application/zip',
    '.jpg': 'image/jpeg',
    '.png': 'image/png'
}

@router.get("/download/{filename}")
async def download_file(filename: str):
    file_path = Path(f"output/{filename}")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    extension = file_path.suffix
    media_type = MIME_TYPES.get(extension, 'application/octet-stream')

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
    )
```

---

## Best Practices

**DO:**
- Validate file extensions
- Validate file sizes
- Use Path for file operations
- Prevent path traversal attacks
- Set appropriate MIME types
- Handle file not found errors
- Use encoding='utf-8' for text files

**DON'T:**
- Trust user-provided filenames
- Allow unlimited file sizes
- Expose internal file paths
- Forget to check file existence
- Use string concatenation for paths
- Store uploaded files without validation
- Forget to clean up temporary files

---

## Related Documentation

- `router_module.md` - Endpoint organization
- `session_management.md` - Session file operations
- `../COMMON.md` - Common backend patterns
- `../../libs/filesystem/` - File operation libraries
