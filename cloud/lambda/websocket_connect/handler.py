"""
Lambda function: WebSocket Connect
Handles WebSocket connection establishment
"""

import json
import boto3
import os
from datetime import datetime
import uuid

# AWS clients
dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')

# Environment variables
CONNECTIONS_TABLE = os.environ['CONNECTIONS_TABLE']


def lambda_handler(event, context):
    """
    Handle WebSocket $connect route

    Event structure:
    {
        "requestContext": {
            "connectionId": "abc123",
            "routeKey": "$connect"
        },
        "queryStringParameters": {
            "token": "jwt-token"
        }
    }
    """

    try:
        connection_id = event['requestContext']['connectionId']
        query_params = event.get('queryStringParameters', {}) or {}

        print(f"New WebSocket connection: {connection_id}")

        # Validate JWT token (simplified - in production use full JWT verification)
        token = query_params.get('token')
        if not token:
            print("No authentication token provided")
            return {'statusCode': 401, 'body': 'Unauthorized'}

        # Extract user ID from token (simplified)
        user_id = extract_user_id(token)
        if not user_id:
            print("Invalid token")
            return {'statusCode': 401, 'body': 'Unauthorized'}

        # Store connection in DynamoDB
        table = dynamodb.Table(CONNECTIONS_TABLE)

        table.put_item(
            Item={
                'connectionId': connection_id,
                'userId': user_id,
                'connectedAt': datetime.utcnow().isoformat(),
                'lastActivity': datetime.utcnow().isoformat(),
                'status': 'connected'
            }
        )

        # Send metrics
        send_metrics({'ConnectionsEstablished': 1})

        print(f"Connection {connection_id} stored for user {user_id}")

        return {'statusCode': 200, 'body': 'Connected'}

    except Exception as e:
        print(f"Error in connect handler: {str(e)}")
        send_metrics({'ErrorCount': 1})
        return {'statusCode': 500, 'body': str(e)}


def extract_user_id(token):
    """
    Extract user ID from JWT token
    In production, use proper JWT verification with PyJWT
    """
    try:
        # Simplified - just decode base64 payload
        import base64
        parts = token.split('.')
        if len(parts) != 3:
            return None

        payload = base64.urlsafe_b64decode(parts[1] + '==')
        data = json.loads(payload)

        return data.get('user_id') or data.get('sub')

    except Exception as e:
        print(f"Error extracting user ID: {str(e)}")
        return None


def send_metrics(metrics):
    """Send custom metrics to CloudWatch"""
    try:
        metric_data = []
        for metric_name, value in metrics.items():
            metric_data.append({
                'MetricName': metric_name,
                'Value': value,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            })

        cloudwatch.put_metric_data(
            Namespace='ANC-Platform/WebSocket',
            MetricData=metric_data
        )
    except Exception as e:
        print(f"Error sending metrics: {str(e)}")
