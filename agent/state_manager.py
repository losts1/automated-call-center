"""
State management for call center.
Works with moto (in-process) for dev, or real AWS for production.
"""

import boto3
import uuid
from datetime import datetime, timezone
from typing import Optional

TABLE_NAME = "call-center-state"


def _get_dynamodb_client():
    """Get DynamoDB client - uses moto mock by default."""
    return boto3.client(
        "dynamodb",
        region_name="us-east-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )


class StateManager:
    """Manages call state."""

    @classmethod
    def create_call_record(cls, room_name: str, participant_identity: str, phone_number: str = None) -> dict:
        """Create a new call record."""
        call_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()

        item = {
            "call_id": {"S": call_id},
            "timestamp": {"S": now},
            "room_name": {"S": room_name},
            "participant_identity": {"S": participant_identity},
            "state": {"S": "active"},
            "created_at": {"S": now},
            "updated_at": {"S": now},
        }
        if phone_number:
            item["phone_number"] = {"S": phone_number}

        ddb = _get_dynamodb_client()
        ddb.put_item(TableName=TABLE_NAME, Item=item)
        return {"call_id": call_id, "room_name": room_name}

    @classmethod
    def update_call_state(cls, call_id: str, state: str, disposition: str = None) -> bool:
        """Update call state."""
        now = datetime.now(timezone.utc).isoformat()
        update_expr = "SET #state = :s, updated_at = :t"
        expr_vals = {":s": {"S": state}, ":t": {"S": now}}
        expr_names = {"#state": "state"}

        if disposition:
            update_expr += ", disposition = :d"
            expr_vals[":d"] = {"S": disposition}

        ddb = _get_dynamodb_client()
        ddb.update_item(
            TableName=TABLE_NAME,
            Key={"call_id": {"S": call_id}},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_vals,
        )
        return True

    @classmethod
    def add_transcript_entry(cls, call_id: str, entry: dict):
        """Add a transcript entry."""
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "M": {
                "role": {"S": entry.get("role", "user")},
                "text": {"S": entry.get("text", "")},
                "timestamp": {"S": now},
                "source": {"S": entry.get("source", "customer")},
            }
        }
        if "metadata" in entry:
            item["M"]["metadata"] = {"S": entry["metadata"]}

        ddb = _get_dynamodb_client()
        ddb.update_item(
            TableName=TABLE_NAME,
            Key={"call_id": {"S": call_id}},
            UpdateExpression="SET transcript = list_append(if_not_exists(transcript, :empty), :entry)",
            ExpressionAttributeValues={":empty": {"L": []}, ":entry": [item]},
        )

    @classmethod
    def get_call_record(cls, call_id: str) -> Optional[dict]:
        """Get a call record."""
        try:
            ddb = _get_dynamodb_client()
            resp = ddb.get_item(TableName=TABLE_NAME, Key={"call_id": {"S": call_id}})
            return resp.get("Item")
        except Exception:
            return None

    @classmethod
    def complete_call(cls, call_id: str, disposition: str, summary: dict = None) -> bool:
        """Mark call as completed."""
        now = datetime.now(timezone.utc).isoformat()
        ddb = _get_dynamodb_client()

        ddb.update_item(
            TableName=TABLE_NAME,
            Key={"call_id": {"S": call_id}},
            UpdateExpression="SET #state = :s, disposition = :d, completed_at = :t",
            ExpressionAttributeNames={"#state": "state"},
            ExpressionAttributeValues={
                ":s": {"S": "completed"},
                ":d": {"S": disposition},
                ":t": {"S": now},
            },
        )

        if summary:
            ddb.put_item(
                TableName=TABLE_NAME,
                Item={
                    "call_id": {"S": call_id},
                    "summary": {"S": summary.get("summary", "")},
                    "disposition": {"S": disposition},
                    "completed_at": {"S": now},
                },
            )
        return True

    @classmethod
    def get_active_calls(cls) -> list[dict]:
        """Get all active calls."""
        ddb = _get_dynamodb_client()
        resp = ddb.scan(
            TableName=TABLE_NAME,
            FilterExpression="#state = :active",
            ExpressionAttributeNames={"#state": "state"},
            ExpressionAttributeValues={":active": {"S": "active"}},
        )
        return resp.get("Items", [])
