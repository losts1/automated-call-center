#!/usr/bin/env python3
"""
Setup moto server for local AWS mocking.
Starts moto_server for S3 (port 5000) and DynamoDB (port 5001).
Creates all required resources (buckets, tables, queues, topics).
"""

import subprocess
import time
import sys
import json
import boto3
import httpx
from rich.console import Console

console = Console()

# Configuration
S3_PORT = 5000
DYNAMODB_PORT = 5001
AWS_REGION = "us-east-1"
AWS_ACCESS_KEY = "testing"
AWS_SECRET_KEY = "testing"
S3_BUCKET = "call-center-recordings"
DYNAMODB_TABLE = "call-center-state"
SQS_QUEUE = "call-processing-queue"
SNS_TOPIC = "call-center-notifications"


def start_moto_servers():
    """Start moto S3 and DynamoDB servers."""
    console.print("\n[bold]Starting moto servers...[/bold]")

    # Start moto server for S3
    proc_s3 = subprocess.Popen(
        ["moto_server", "s3", "-p", str(S3_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    console.print(f"  [green]✓ S3 server started on port {S3_PORT}[/green]")

    # Start moto server for DynamoDB
    proc_ddb = subprocess.Popen(
        ["moto_server", "dynamodb", "-p", str(DYNAMODB_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    console.print(f"  [green]✓ DynamoDB server started on port {DYNAMODB_PORT}[/green]")

    return proc_s3, proc_ddb


def wait_for_ready(port, name, retries=40):
    """Wait for moto server to be ready."""
    for i in range(retries):
        try:
            resp = httpx.get(f"http://127.0.0.1:{port}", timeout=2)
            if resp.status_code == 200 or "Service" in resp.text:
                console.print(f"  [green]✓ {name} is ready[/green]")
                return True
        except Exception:
            pass
        time.sleep(1)

    console.print(f"  [red]✗ {name} not ready after {retries} attempts[/red]")
    return False


def create_resources():
    """Create all AWS resources."""
    console.print("\n[bold]Creating resources...[/bold]")

    s3 = boto3.client("s3", endpoint_url=f"http://127.0.0.1:{S3_PORT}", region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    ddb = boto3.client("dynamodb", endpoint_url=f"http://127.0.0.1:{DYNAMODB_PORT}", region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    sqs = boto3.client("sqs", endpoint_url=f"http://127.0.0.1:{S3_PORT}", region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    sns = boto3.client("sns", endpoint_url=f"http://127.0.0.1:{S3_PORT}", region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)

    # S3 bucket
    try:
        s3.create_bucket(Bucket=S3_BUCKET)
        console.print(f"  [green]✓ S3 bucket created: {S3_BUCKET}[/green]")
    except Exception as e:
        if "BucketAlreadyOwnedByYou" in str(e):
            console.print(f"  [yellow]⚠ S3 bucket already exists[/yellow]")
        else:
            console.print(f"  [red]✗ S3 bucket creation failed: {e}[/red]")

    # DynamoDB table
    try:
        ddb.create_table(
            TableName=DYNAMODB_TABLE,
            KeySchema=[{"AttributeName": "call_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "call_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        console.print(f"  [green]✓ DynamoDB table created: {DYNAMODB_TABLE}[/green]")
    except Exception as e:
        if "ResourceInUseException" in str(e):
            console.print(f"  [yellow]⚠ DynamoDB table already exists[/yellow]")
        else:
            console.print(f"  [red]✗ DynamoDB table creation failed: {e}[/red]")

    # SQS queue
    try:
        queue_url = sqs.create_queue(QueueName=SQS_QUEUE)["QueueUrl"]
        console.print(f"  [green]✓ SQS queue created: {SQS_QUEUE}[/green]")
    except Exception as e:
        if "QueueAlreadyExists" in str(e):
            queue_url = sqs.get_queue_url(QueueName=SQS_QUEUE)["QueueUrl"]
            console.print(f"  [yellow]⚠ SQS queue already exists[/yellow]")
        else:
            console.print(f"  [red]✗ SQS queue creation failed: {e}[/red]")

    # SNS topic
    try:
        topic_arn = sns.create_topic(Name=SNS_TOPIC)["TopicArn"]
        console.print(f"  [green]✓ SNS topic created: {SNS_TOPIC}[/green]")
    except Exception as e:
        if "TopicAlreadyExists" in str(e):
            topic_arn = sns.get_topic_arn(TopicName=SNS_TOPIC)
            console.print(f"  [yellow]⚠ SNS topic already exists[/yellow]")
        else:
            console.print(f"  [red]✗ SNS topic creation failed: {e}[/red]")

    # Save config
    config = {
        "s3_bucket": S3_BUCKET,
        "dynamodb_table": DYNAMODB_TABLE,
        "sqs_queue_url": queue_url,
        "sns_topic_arn": topic_arn,
        "moto_s3_url": f"http://127.0.0.1:{S3_PORT}",
        "moto_dynamodb_url": f"http://127.0.0.1:{DYNAMODB_PORT}",
    }

    with open("../config/moto.json", "w") as f:
        json.dump(config, f, indent=2)

    console.print(f"\n[bold green]✓ All resources created and saved to config/moto.json[/bold green]")
    return config


def main():
    console.print("[bold cyan]╔══════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║    Moto AWS Mock Setup                   ║[/bold cyan]")
    console.print("[bold cyan]╚══════════════════════════════════════════╝[/bold cyan]")

    # Start servers
    proc_s3, proc_ddb = start_moto_servers()

    # Wait for ready
    if not wait_for_ready(S3_PORT, "S3"):
        console.print("[red]Failed to start S3 server[/red]")
        sys.exit(1)
    if not wait_for_ready(DYNAMODB_PORT, "DynamoDB"):
        console.print("[red]Failed to start DynamoDB server[/red]")
        sys.exit(1)

    # Create resources
    config = create_resources()

    console.print("\n[bold]Resources created:[/bold]")
    for k, v in config.items():
        if k == "sns_topic_arn":
            console.print(f"  {k}: {v}")
        else:
            console.print(f"  {k}: {v}")

    console.print("\n[dim]Servers running in background. Stop with: pkill -f moto_server[/dim]")


if __name__ == "__main__":
    main()
