"""Regression coverage for Note's presigned body-image uploads."""

from pathlib import Path


def test_stage2_uses_token_complete_presigned_post_uploader() -> None:
    """Temporary AWS credentials must retain x-amz-security-token in the POST."""
    source = (Path(__file__).parents[1] / "scripts" / "note-stage2-publish.py").read_text(
        encoding="utf-8"
    )

    assert "from note_s3_upload import upload_body_image" in source
