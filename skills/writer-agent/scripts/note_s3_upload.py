"""Token-complete body-image upload for Note's presigned POST endpoint."""

from pathlib import Path
import time

import httpx

from note_mcp.api.client import NoteAPIClient
from note_mcp.api.images import CONTENT_TYPE_MAP, validate_image_file
from note_mcp.models import ErrorCode, Image, ImageType, NoteAPIError, Session


async def upload_body_image(session: Session, file_path: str, _note_id: str) -> Image:
    """Upload an inline image without dropping fields signed into the AWS POST policy."""
    validate_image_file(file_path)
    path = Path(file_path)

    async with NoteAPIClient(session) as client:
        response = await client.post("/v3/images/upload/presigned_post", data={"filename": path.name})

    presigned = response.get("data", {})
    action = presigned.get("action")
    image_url = presigned.get("url")
    post = presigned.get("post")
    if not action or not image_url or not isinstance(post, dict) or not post:
        raise NoteAPIError(
            code=ErrorCode.API_ERROR,
            message="Failed to get presigned URL for image upload",
            details={"response": response},
        )

    # STS-backed Note uploads include x-amz-security-token.  Sending a hand-picked
    # subset makes the S3 policy reject the upload with 403, so retain every signed field.
    fields = {key: (None, str(value)) for key, value in post.items() if value is not None}
    with path.open("rb") as image:
        fields["file"] = (path.name, image.read(), CONTENT_TYPE_MAP.get(path.suffix.lower(), "application/octet-stream"))

    async with httpx.AsyncClient() as client:
        uploaded = await client.post(action, files=fields)
    if not uploaded.is_success:
        raise NoteAPIError(
            code=ErrorCode.API_ERROR,
            message=f"Failed to upload image to S3: {uploaded.status_code}",
            details={"status": uploaded.status_code, "response": uploaded.text},
        )

    return Image(
        key=str(post.get("key", "")),
        url=str(image_url),
        original_path=file_path,
        size_bytes=path.stat().st_size,
        uploaded_at=int(time.time()),
        image_type=ImageType.BODY,
    )
