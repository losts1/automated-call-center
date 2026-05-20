#!/usr/bin/env python3
"""
Initialize Localstack resources for the call center.
Creates S3 buckets, DynamoDB tables, SQS queues, and SNS topics.
"""

import boto3
import json
import time
import sys
from botocore.exceptions import ClientError

# Configuration
ENDPOINT_URL = "http://localhost:4566"
REGION = "us-east-1"
S3_BUCKET = "call-center-recordings"
DYNAMODB_TABLE = "call-center-state"
SQS_QUEUE = "call-processing-queue"
SNS_TOPIC = "call-center-notifications"


def create_resources():
    """Create all Localstack resources."""
    print("🔧 Setting up Localstack resources...")
    print()

    # S3
    s3 = boto3.client("s3", endpoint_url=ENDPOINT_URL, region_name=REGION)
    try:
        s3.create_bucket(Bucket=S3_BUCKET)
        print(f"✅ S3 bucket created: {S3_BUCKET}")
    except ClientError as e:
        if "BucketAlreadyOwnedByYou" in str(e):
            print(f"⚠️  S3 bucket already exists: {S3_BUCKET}")
        else:
            raise

    # DynamoDB
    dynamodb = boto3.client("dynamodb", endpoint_url=ENDPOINT_URL, region_name=REGION)
    try:
        dynamodb.create_table(
            TableName=DYNAMODB_TABLE,
            KeySchema=[
                {"AttributeName": "call_id", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "call_id", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        print(f"✅ DynamoDB table created: {DYNAMODB_TABLE}")
    except ClientError as e:
        if "ResourceInUseException" in str(e):
            print(f"⚠️  DynamoDB table already exists: {DYNAMODB_TABLE}")
        else:
            raise

    # SQS
    sqs = boto3.client("sqs", endpoint_url=ENDPOINT_URL, region_name=REGION)
    try:
        queue_url = sqs.create_queue(QueueName=SQS_QUEUE)["QueueUrl"]
        print(f"✅ SQS queue created: {SQS_QUEUE}")
        print(f"   URL: {queue_url}")
    except ClientError as e:
        if "QueueAlreadyExists" in str(e):
            queue_url = sqs.get_queue_url(QueueName=SQS_QUEUE)["QueueUrl"]
            print(f"⚠️  SQS queue already exists: {SQS_QUEUE}")
            print(f"   URL: {queue_url}")
        else:
            raise

    # SNS
    sns = boto3.client("sns", endpoint_url=ENDPOINT_URL, region_name=REGION)
    try:
        topic_arn = sns.create_topic(Name=SNS_TOPIC)["TopicArn"]
        print(f"✅ SNS topic created: {SNS_TOPIC}")
        print(f"   ARN: {topic_arn}")
    except ClientError as e:
        if "TopicAlreadyExists" in str(e):
            topic_arn = sns.get_topic_arn(TopicName=SNS_TOPIC)
            print(f"⚠️  SNS topic already exists: {SNS_TOPIC}")
            print(f"   ARN: {topic_arn}")
        else:
            raise

    print()
    print("🎉 All Localstack resources ready!")
    print()
    print("Resource Summary:")
    print(f"  S3 Bucket:      {S3_BUCKET}")
    print(f"  DynamoDB Table: {DYNAMODB_TABLE}")
    print(f"  SQS Queue:      {SQS_QUEUE}")
    print(f"  SNS Topic:      {SNS_TOPIC}")

    return {
        "s3_bucket": S3_BUCKET,
        "dynamodb_table": DYNAMODB_TABLE,
        "sqs_queue_url": queue_url,
        "sns_topic_arn": topic_arn,
    }


if __name__ == "__main__":
    # Wait for Localstack to be ready
    import httpx

    max_retries = 30
    for i in range(max_retries):
        try:
            resp = httpx.get(f"{ENDPOINT_URL}/_localstack/health", timeout=5)
            if resp.status_code == 200:
                services = resp.json().get("services", {})
                print(f"🟢 Localstack healthy. Services: {', '.join(services.keys())}")
                break
        except Exception:
            if i == max_retries - 1:
                print("❌ Localstack not ready after 30 retries")
                sys.exit(1)
            print(f"⏳ Waiting for Localstack... ({i+1}/{max_retries})")
            time.sleep(2)
    else:
        print("❌ Localstack health check failed")
        sys.exit(1)

    result = create_resources()
    # Save config
    with open("../config/localstack.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n💾 Config saved to config/localstack.json")
