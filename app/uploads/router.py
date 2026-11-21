"""Photo uploads for vendor and menu item pictures.

The frontend shrinks the photo first, then sends the file itself as the request
body (Content-Type image/jpeg etc.); the response gives the address to store in
image_url / cover_image_url. Files are saved under settings.upload_dir and served
at /uploads/<name> (see app.main).
"""

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.auth.dependencies import require_roles
from app.auth.models import User
from app.auth.states import UserRole
from app.core.errors import BadRequestError, PayloadTooLargeError

router = APIRouter(prefix="/uploads", tags=["uploads"])

MAX_BYTES = 5 * 1024 * 1024

# Only raster images, recognised by their first bytes (not by what the client
# claims). SVG is left out on purpose: it can carry scripts.
_SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
)

# Vendor staff (menu photos, store photos) and admins (photos for a new vendor)
Uploader = Annotated[User, Depends(require_roles(UserRole.STAFF, UserRole.ADMIN))]


class UploadRead(BaseModel):
    url: str


def image_extension(data: bytes) -> str | None:
    for signature, extension in _SIGNATURES:
        if data.startswith(signature):
            return extension
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


@router.post("", response_model=UploadRead, status_code=status.HTTP_201_CREATED)
async def upload_image(request: Request, _user: Uploader) -> UploadRead:
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_BYTES:
        raise PayloadTooLargeError("Photos can be at most 5 MB")
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_BYTES:
            raise PayloadTooLargeError("Photos can be at most 5 MB")

    extension = image_extension(bytes(body))
    if extension is None:
        raise BadRequestError("Upload a PNG, JPEG, GIF or WebP image")

    folder = request.app.state.app_settings.upload_dir
    # Random, so names cannot be guessed or clash
    name = secrets.token_hex(16) + extension
    await run_in_threadpool((folder / name).write_bytes, bytes(body))
    return UploadRead(url=f"/uploads/{name}")
