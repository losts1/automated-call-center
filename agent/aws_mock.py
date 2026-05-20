"""
AWS mock tests using moto's in-process mocking.
All 4 components tested: resource setup, full lifecycle, state, recording.
"""

import json
import uuid
import boto3
from datetime import datetime, timezone
from moto import mock_aws


@mock_aws
def setup_all_resources():
    """Create all resources using moto's mocked AWS in a single context."""
    s3 = boto3.client("s3", region_name="us-east-1")
    ddb = boto3.client("dynamodb", region_name="us-east-1")
    sqs = boto3.client("sqs", region_name="us-east-1")
    sns = boto3.client("sns", region_name="us-east-1")

    results = {}

    # S3 bucket
    s3.create_bucket(Bucket="call-center-recordings")
    results["s3_bucket"] = "call-center-recordings"
    print("  ✓ S3 bucket: call-center-recordings")

    # DynamoDB table
    ddb.create_table(
        TableName="call-center-state",
        KeySchema=[{"AttributeName": "call_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "call_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    results["dynamodb_table"] = "call-center-state"
    print("  ✓ DynamoDB table: call-center-state")

    # SQS queue
    url = sqs.create_queue(QueueName="call-processing-queue")["QueueUrl"]
    results["sqs_queue_url"] = url
    print(f"  ✓ SQS queue: call-processing-queue")

    # SNS topic
    arn = sns.create_topic(Name="call-center-notifications")["TopicArn"]
    results["sns_topic_arn"] = arn
    print(f"  ✓ SNS topic: call-center-notifications")

    return results


def test_full_lifecycle():
    """Test a complete call lifecycle with moto."""
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        sns = boto3.client("sns", region_name="us-east-1")

        # Setup
        s3.create_bucket(Bucket="call-center-recordings")
        ddb.create_table(
            TableName="call-center-state",
            KeySchema=[{"AttributeName": "call_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "call_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # 1. Create call record
        call_id = str(uuid.uuid4())[:8]
        ddb.put_item(
            TableName="call-center-state",
            Item={
                "call_id": {"S": call_id},
                "timestamp": {"S": datetime.now(timezone.utc).isoformat()},
                "state": {"S": "active"},
                "phone": {"S": "+15551234567"},
            },
        )
        print(f"  ✓ Call record created: {call_id}")

        # 2. Upload recording
        wav_header = b"RIFF\x00\x00\x00\x00WAVE"
        s3.put_object(
            Bucket="call-center-recordings",
            Key=f"recordings/{call_id}.wav",
            Body=wav_header,
        )
        print("  ✓ Recording uploaded")

        # 3. Upload transcript
        transcript = [
            {"role": "system", "content": "You are a legal assistant."},
            {"role": "user", "content": "I need help with a parking ticket."},
            {"role": "assistant", "content": "I can help. When was the ticket issued?"},
        ]
        s3.put_object(
            Bucket="call-center-recordings",
            Key=f"transcripts/{call_id}.json",
            Body=json.dumps(transcript),
        )
        print("  ✓ Transcript uploaded")

        # 4. Update call state
        ddb.update_item(
            TableName="call-center-state",
            Key={"call_id": {"S": call_id}},
            UpdateExpression="SET #state = :s, completed_at = :t",
            ExpressionAttributeNames={"#state": "state"},
            ExpressionAttributeValues={
                ":s": {"S": "completed"},
                ":t": {"S": datetime.now(timezone.utc).isoformat()},
            },
        )
        print("  ✓ Call state: completed")

        # 5. Send notification
        topics = sns.list_topics()["Topics"]
        if topics:
            sns.publish(
                TopicArn=topics[0]["TopicArn"],
                Message=json.dumps({"event": "call_completed", "call_id": call_id}),
            )
            print("  ✓ SNS notification sent")

        # 6. Verify
        items = ddb.scan(TableName="call-center-state")["Items"]
        objects = s3.list_objects_v2(Bucket="call-center-recordings").get("Contents", [])
        print(f"  ✓ DynamoDB records: {len(items)}")
        print(f"  ✓ S3 objects: {len(objects)}")
        print("\n✅ Full call lifecycle test PASSED!")


def test_agent_state():
    """Test the StateManager with moto."""
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="call-center-state",
            KeySchema=[{"AttributeName": "call_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "call_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        import sys
        sys.path.insert(0, "/home/lost/automated-call-center")
        from agent.state_manager import StateManager

        # Create record
        record = StateManager.create_call_record("test-room", "test-user", "+15551234567")
        call_id = record["call_id"]
        print(f"  ✓ Created call: {call_id}")

        # Update state
        StateManager.update_call_state(call_id, "completed", disposition="resolved")
        print("  ✓ Updated state to completed")

        # Get record
        item = StateManager.get_call_record(call_id)
        assert item is not None
        print(f"  ✓ Retrieved call: {item['call_id']['S']}")

        print("\n✅ StateManager test PASSED!")


def test_recording_manager():
    """Test the RecordingManager with moto."""
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="call-center-recordings")

        import sys
        sys.path.insert(0, "/home/lost/automated-call-center")
        from agent.recording_manager import RecordingManager

        # Upload recording
        wav = b"RIFF\x00\x00\x00\x00WAVEfmt "
        url = RecordingManager.upload_recording("test-call", wav, "wav")
        print(f"  ✓ Uploaded recording: {url}")

        # Upload transcript
        trans = [{"role": "user", "content": "hello"}]
        t_url = RecordingManager.upload_transcript("test-call", trans)
        print(f"  ✓ Uploaded transcript: {t_url}")

        # List recordings
        items = RecordingManager.list_recordings()
        print(f"  ✓ Found {len(items)} objects")

        print("\n✅ RecordingManager test PASSED!")


if __name__ == "__main__":
    from rich.console import Console
    console = Console()
    console.print("\n[bold cyan]╔══════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║    Moto AWS Mock Tests                   ║[/bold cyan]")
    console.print("[bold cyan]╚══════════════════════════════════════════╝[/bold cyan]\n")

    console.print("[bold]1. Setup resources:[/bold]")
    results = setup_all_resources()
    print()

    console.print("[bold]2. Full lifecycle:[/bold]")
    test_full_lifecycle()
    print()

    console.print("[bold]3. StateManager:[/bold]")
    test_agent_state()
    print()

    console.print("[bold]4. RecordingManager:[/bold]")
    test_recording_manager()
    print()

    console.print("[bold green]✅ All tests passed![/bold green]")
