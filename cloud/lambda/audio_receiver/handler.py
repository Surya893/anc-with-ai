"""
Lambda function: Audio Receiver
Receives incoming audio chunks via WebSocket, validates, and queues for processing
"""

import json
import base64
import boto3
import os
import numpy as np
from datetime import datetime
import hashlib

# AWS clients
sqs = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')

# Environment variables
AUDIO_QUEUE_URL = os.environ['AUDIO_QUEUE_URL']
SESSIONS_TABLE = os.environ['SESSIONS_TABLE']
CONNECTIONS_TABLE = os.environ['CONNECTIONS_TABLE']

# Constants
SAMPLE_RATE = 48000
MAX_CHUNK_SIZE = 4096  # samples

def lambda_handler(event, context):
    """
    Handle incoming audio chunks from WebSocket clients

    Event structure:
    {
        "requestContext": {
            "connectionId": "abc123",
            "routeKey": "audioChunk"
        },
        "body": {
            "sessionId": "session-uuid",
            "audioData": "base64-encoded-float32-array",
            "sampleRate": 48000,
            "timestamp": 1234567890
        }
    }
    """

    try:
        # Parse event
        connection_id = event['requestContext']['connectionId']
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']

        session_id = body['session_id']
        audio_data_b64 = body['audio_data']
        sample_rate = body.get('sample_rate', SAMPLE_RATE)
        timestamp = body.get('timestamp', datetime.utcnow().timestamp())

        # Validate session
        session = get_session(session_id)
        if not session:
            return error_response(404, 'Session not found')

        # Validate connection matches session
        if session['connectionId'] != connection_id:
            return error_response(403, 'Connection ID mismatch')

        # Decode audio data
        try:
            audio_bytes = base64.b64decode(audio_data_b64)
            audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
        except Exception as e:
            return error_response(400, f'Invalid audio data: {str(e)}')

        # Validate audio chunk
        if len(audio_array) > MAX_CHUNK_SIZE:
            return error_response(400, f'Chunk too large: {len(audio_array)} samples (max: {MAX_CHUNK_SIZE})')

        if sample_rate != SAMPLE_RATE:
            return error_response(400, f'Invalid sample rate: {sample_rate} (expected: {SAMPLE_RATE})')

        # Generate chunk ID
        chunk_id = generate_chunk_id(session_id, timestamp)

        # Prepare message for SQS
        message = {
            'chunkId': chunk_id,
            'sessionId': session_id,
            'connectionId': connection_id,
            'audioData': audio_data_b64,  # Keep as base64 for SQS
            'sampleRate': sample_rate,
            'numSamples': len(audio_array),
            'timestamp': timestamp,
            'receivedAt': datetime.utcnow().isoformat(),
            'config': {
                'ancEnabled': session['config'].get('anc_enabled', True),
                'ancIntensity': session['config'].get('anc_intensity', 1.0),
                'algorithm': session['config'].get('algorithm', 'nlms'),
                'noiseType': session.get('noiseType', 'unknown')
            }
        }

        # Send to SQS for processing
        sqs_response = sqs.send_message(
            QueueUrl=AUDIO_QUEUE_URL,
            MessageBody=json.dumps(message),
            MessageAttributes={
                'sessionId': {
                    'StringValue': session_id,
                    'DataType': 'String'
                },
                'priority': {
                    'StringValue': 'high',  # Real-time processing
                    'DataType': 'String'
                }
            }
        )

        # Update session metrics
        update_session_metrics(session_id, len(audio_array))

        # Send CloudWatch metrics
        send_metrics({
            'AudioChunksReceived': 1,
            'AudioSamplesReceived': len(audio_array),
            'ReceiveLatency': (datetime.utcnow().timestamp() - timestamp) * 1000  # ms
        })

        # Return acknowledgment
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'received',
                'chunkId': chunk_id,
                'queuedAt': sqs_response['MessageId'],
                'numSamples': len(audio_array)
            })
        }

    except Exception as e:
        print(f"Error processing audio chunk: {str(e)}")
        send_metrics({'ErrorCount': 1})
        return error_response(500, f'Internal error: {str(e)}')


def get_session(session_id):
    """Retrieve session from DynamoDB"""
    table = dynamodb.Table(SESSIONS_TABLE)

    try:
        response = table.get_item(Key={'sessionId': session_id})
        return response.get('Item')
    except Exception as e:
        print(f"Error retrieving session: {str(e)}")
        return None


def update_session_metrics(session_id, num_samples):
    """Update session metrics in DynamoDB"""
    table = dynamodb.Table(SESSIONS_TABLE)

    try:
        table.update_item(
            Key={'sessionId': session_id},
            UpdateExpression='ADD totalSamples :samples SET lastActivityAt = :timestamp',
            ExpressionAttributeValues={
                ':samples': num_samples,
                ':timestamp': datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        print(f"Error updating session metrics: {str(e)}")


def generate_chunk_id(session_id, timestamp):
    """Generate unique chunk ID"""
    data = f"{session_id}:{timestamp}".encode('utf-8')
    return hashlib.sha256(data).hexdigest()[:16]


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
            Namespace='ANC-Platform/AudioReceiver',
            MetricData=metric_data
        )
    except Exception as e:
        print(f"Error sending metrics: {str(e)}")


def error_response(status_code, message):
    """Return error response"""
    return {
        'statusCode': status_code,
        'body': json.dumps({
            'error': message
        })
    }
