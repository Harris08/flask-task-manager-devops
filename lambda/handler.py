import boto3
import os
import json

def lambda_handler(event, context):
    ses = boto3.client('ses', region_name='ap-south-1')
    
    # Get uploaded file details from S3 event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    # Send email notification via SES
    ses.send_email(
        Source=os.environ['SES_FROM_EMAIL'],
        Destination={
            'ToAddresses': [os.environ['SES_TO_EMAIL']]
        },
        Message={
            'Subject': {
                'Data': 'New File Uploaded — Flask Task Manager'
            },
            'Body': {
                'Text': {
                    'Data': f'A new file has been uploaded.\n\nBucket: {bucket}\nFile: {key}'
                }
            }
        }
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps('Email notification sent successfully')
    }