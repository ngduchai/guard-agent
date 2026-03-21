"""
File upload/download routes.

Routes:
  POST /api/upload                  – accept a ZIP of user code
  GET  /api/download/{upload_id}    – download generated code as ZIP
  POST /api/download-written-files  – zip and download LLM-written files
"""

from __future__ import annotations

import io
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from agents.veloc.config import get_project_root

router = APIRouter()


@router.post("/api/upload")
async def api_upload(file: UploadFile = File(...)) -> JSONResponse:
    """
    Accept a ZIP file containing the user's code directory.

    The archive is extracted to ``BUILD_DIR/upload_code/<upload_id>/`` where
    ``upload_id`` is a freshly generated UUID4.  The response contains:

    - ``upload_id``   – the unique identifier for this upload.
    - ``upload_path`` – the absolute path where the code was extracted.
    - ``generated_code_path`` – the path where the LLM should write output.

    The frontend should pass ``upload_path`` to the LLM as the source
    directory and ``generated_code_path`` as the target directory.
    """
    if not file.filename:
        return JSONResponse({"error": "No file provided."}, status_code=400)

    build_dir = Path(get_project_root())
    upload_id = str(uuid.uuid4())

    upload_dest = build_dir / "upload_code" / upload_id
    generated_dest = build_dir / "generated_code" / upload_id

    upload_dest.mkdir(parents=True, exist_ok=True)
    generated_dest.mkdir(parents=True, exist_ok=True)

    # Read the uploaded bytes
    content = await file.read()

    # Validate it is a ZIP archive
    if not zipfile.is_zipfile(io.BytesIO(content)):
        shutil.rmtree(upload_dest, ignore_errors=True)
        shutil.rmtree(generated_dest, ignore_errors=True)
        return JSONResponse(
            {"error": "Uploaded file is not a valid ZIP archive."},
            status_code=400,
        )

    # Extract, stripping a single top-level directory if the zip was created
    # with one (e.g. ``zip -r mycode.zip mycode/``).
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        members = zf.namelist()
        # Detect common prefix (top-level folder inside the zip)
        top_dirs = {m.split("/")[0] for m in members if m}
        strip_prefix: str | None = None
        if len(top_dirs) == 1:
            prefix = next(iter(top_dirs)) + "/"
            if all(m.startswith(prefix) or m == prefix.rstrip("/") for m in members):
                strip_prefix = prefix

        for member in zf.infolist():
            target_name = member.filename
            if strip_prefix and target_name.startswith(strip_prefix):
                target_name = target_name[len(strip_prefix):]
            if not target_name:
                continue  # skip the top-level directory entry itself
            target_path = upload_dest / target_name
            if member.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(target_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)

    return JSONResponse(
        {
            "upload_id": upload_id,
            "upload_path": str(upload_dest),
            "generated_code_path": str(generated_dest),
        }
    )


@router.get("/api/download/{upload_id}")
async def api_download(upload_id: str) -> Response:
    """
    Zip the generated code for ``upload_id`` and return it as a download.

    The generated code is expected at ``BUILD_DIR/generated_code/<upload_id>/``.
    Returns 404 if the directory does not exist or is empty.
    """
    build_dir = Path(get_project_root())
    generated_dir = build_dir / "generated_code" / upload_id

    if not generated_dir.exists() or not any(generated_dir.iterdir()):
        return JSONResponse(
            {"error": "Generated code not found. The agent may not have produced output yet."},
            status_code=404,
        )

    # Build the zip in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(generated_dir.rglob("*")):
            if path.is_file():
                arcname = path.relative_to(generated_dir)
                zf.write(path, arcname)
    buf.seek(0)

    filename = f"generated_code_{upload_id[:8]}.zip"
    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/api/download-written-files")
async def api_download_written_files(request: Request) -> Response:
    """
    Zip a list of files written by the LLM during a session and return as download.

    Accepts JSON body: ``{"file_paths": ["path/to/file1", "path/to/file2", ...]}``

    Each path must resolve to a file inside BUILD_DIR (the project root).
    Returns a ZIP archive containing all found files, preserving their relative
    paths from BUILD_DIR.  Returns 404 if no valid files are found.
    """
    payload: Dict[str, Any] = await request.json()
    file_paths: List[str] = payload.get("file_paths") or []

    if not file_paths:
        return JSONResponse({"error": "No file paths provided."}, status_code=400)

    build_dir = Path(get_project_root()).resolve()

    # Collect valid, existing files that are inside BUILD_DIR
    valid_files: List[Path] = []
    for fp in file_paths:
        p = Path(fp)
        if not p.is_absolute():
            p = build_dir / p
        p = p.resolve()
        # Security: only allow files inside BUILD_DIR
        try:
            p.relative_to(build_dir)
        except ValueError:
            continue  # skip paths outside BUILD_DIR
        if p.is_file():
            valid_files.append(p)

    if not valid_files:
        return JSONResponse(
            {"error": "No generated files found. The agent may not have written any files yet."},
            status_code=404,
        )

    # Build the zip in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(valid_files):
            try:
                arcname = path.relative_to(build_dir)
            except ValueError:
                arcname = path.name
            zf.write(path, arcname)
    buf.seek(0)

    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="generated_code.zip"',
        },
    )
