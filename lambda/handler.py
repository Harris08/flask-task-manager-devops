import boto3
import os
import json
import urllib.parse

ses = boto3.client('ses', region_name='ap-south-1')

def lambda_handler(event, context):
    for record in event['Records']:
        bucket   = record['s3']['bucket']['name']
        key      = urllib.parse.unquote_plus(record['s3']['object']['key'])
        filename = key.split('/')[-1]
        size     = record['s3']['object'].get('size', 0)

        # Format file size
        if size >= 1024 * 1024:
            size_str = f"{size / (1024*1024):.1f} MB"
        elif size >= 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size} bytes"

        from_email = os.environ.get('SES_FROM_EMAIL', 'haarisraja08@gmail.com')
        to_email   = os.environ.get('SES_TO_EMAIL',   'haarisraja08@gmail.com')

        html_body = f"""
        <div style="font-family:DM Sans,Arial,sans-serif;max-width:520px;margin:0 auto;
                    background:#ffffff;border:1.5px solid #dbeafe;border-radius:16px;
                    overflow:hidden;">

          <!-- header -->
          <div style="background:linear-gradient(135deg,#1d4ed8,#3b82f6);
                      padding:22px 28px;display:flex;align-items:center;gap:12px;">
            <div style="font-size:22px;">🗂</div>
            <h1 style="color:#ffffff;font-size:18px;margin:0;font-weight:700;">
              Task Manager
            </h1>
          </div>

          <!-- body -->
          <div style="padding:28px;">
            <h2 style="color:#0f172a;font-size:16px;margin:0 0 6px;">
              📎 New File Uploaded to S3
            </h2>
            <p style="color:#64748b;font-size:13px;margin:0 0 20px;">
              A task file has been uploaded to your S3 bucket.
            </p>

            <!-- details card -->
            <div style="background:#f0f4ff;border:1.5px solid #dbeafe;
                        border-radius:10px;padding:16px 20px;margin-bottom:20px;">
              <p style="margin:0 0 8px;font-size:11px;color:#64748b;
                         font-weight:700;text-transform:uppercase;letter-spacing:.5px;">
                Upload Details
              </p>
              <table style="width:100%;border-collapse:collapse;font-size:13px;">
                <tr>
                  <td style="color:#64748b;padding:3px 0;width:90px;">File</td>
                  <td style="color:#0f172a;font-weight:600;">{filename}</td>
                </tr>
                <tr>
                  <td style="color:#64748b;padding:3px 0;">Size</td>
                  <td style="color:#0f172a;font-weight:600;">{size_str}</td>
                </tr>
                <tr>
                  <td style="color:#64748b;padding:3px 0;">Bucket</td>
                  <td style="color:#0f172a;font-weight:600;">{bucket}</td>
                </tr>
                <tr>
                  <td style="color:#64748b;padding:3px 0;">Path</td>
                  <td style="color:#0f172a;font-weight:600;word-break:break-all;">{key}</td>
                </tr>
              </table>
            </div>

            <a href="http://13.203.97.210"
               style="display:inline-block;
                      background:linear-gradient(135deg,#1d4ed8,#3b82f6);
                      color:#ffffff;text-decoration:none;
                      padding:10px 24px;border-radius:9px;
                      font-weight:700;font-size:13px;">
              View Dashboard →
            </a>
          </div>

          <!-- footer -->
          <div style="background:#f8faff;border-top:1px solid #dbeafe;
                      padding:12px 28px;font-size:11px;color:#94a3b8;">
            Task Manager © 2026 · Powered by AWS Lambda + S3 + SES
          </div>
        </div>
        """

        ses.send_email(
            Source=from_email,
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {
                    'Data': f'📎 File Uploaded: {filename} — Task Manager',
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Html': {
                        'Data': html_body,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )

    return {
        'statusCode': 200,
        'body': json.dumps('File upload notification sent.')
    }