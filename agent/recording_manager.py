"""
Recording manager for call center.
Works with moto (in-process) for dev, or real AWS for production.
"""

import boto3
from datetime import datetime, timezone

BUCKET = "call-center-recordings"


def _get_s3_client():
    """Get S3 client - uses moto mock by default."""
    return boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )


class RecordingManager:
    """Manages call recordings."""

    s3 = _get_s3_client()

    @classmethod
    def upload_recording(cls, call_id: str, audio_data: bytes, fmt: str = "wav") -> str:
        """Upload call recording to S3."""
        now = datetime.now(timezone.utc)
        key = f"recordings/{now.strftime('%Y/%m/%d')}/{call_id}.{fmt}"

        cls.s3.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=audio_data,
            ContentType=f"audio/{fmt}",
        )
        return f"s3://{BUCKET}/{key}"

    @classmethod
    def upload_transcript(cls, call_id: str, transcript: list[dict]) -> str:
        """Save call transcript as JSON to S3."""
        now = datetime.now(timezone.utc)
        key = f"transcripts/{now.strftime('%Y/%m/%d')}/{call_id}.json"

        cls.s3.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=str(transcript),
            ContentType="application/json",
        )
        return f"s3://{BUCKET}/{key}"

    @classmethod
    def list_recordings(cls, call_id: str = None) -> list[dict]:
        """List recordings."""
        prefix = "recordings/"
        if call_id:
            prefix += call_id

        response = cls.s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
        return [
            {
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
            }
            for obj in response.get("Contents", [])
        ]

    @classmethod
    def delete_recording(cls, key: str) -> bool:
        """Delete a recording."""
        cls.s3.delete_object(Bucket=BUCKET, Key=key)
        return True
