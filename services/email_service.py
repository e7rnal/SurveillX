"""Email Service - AWS SES Integration with Development Mode"""
import boto3
from botocore.exceptions import ClientError
import logging
import os

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self, aws_access_key, aws_secret_key, aws_region, sender_email, development_mode=None):
        self.sender_email = sender_email
        
        # Check for development mode from environment or parameter
        if development_mode is None:
            development_mode = os.getenv('EMAIL_DEVELOPMENT_MODE', 'true').lower() == 'true'
        
        self.development_mode = development_mode
        
        if self.development_mode:
            logger.info("Email service in DEVELOPMENT MODE - emails will be logged, not sent")
            self.ses_client = None
        else:
            self.ses_client = boto3.client(
                'ses',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )
            logger.info(f"Email service initialized with sender: {sender_email}")
    
    def send_enrollment_email(self, recipient_email, token, base_url, roll_no=None):
        """Send enrollment invitation email"""
        enrollment_link = f"{base_url}/templates/enroll.html?token={token}"
        if roll_no:
            enrollment_link += f"&roll_no={roll_no}"
        
        subject = "SurveillX - Complete Your Enrollment"
        
        html_body = f"""
        <html>
        <body>
            <h2>Complete Your Enrollment</h2>
            <p>You have been invited to enroll in the SurveillX surveillance system.</p>
            <p><a href="{enrollment_link}">Click here to complete enrollment</a></p>
            <p>This link will expire in 24 hours.</p>
        </body>
        </html>
        """
        
        text_body = f"""
        SurveillX Student Enrollment
        
        You have been invited to enroll. Please visit: {enrollment_link}
        
        This link will expire in 24 hours.
        """
        
        # Development mode - log instead of sending
        if self.development_mode:
            logger.info("=" * 60)
            logger.info("DEVELOPMENT MODE - Email NOT sent")
            logger.info(f"To: {recipient_email}")
            logger.info(f"Subject: {subject}")
            logger.info(f"Enrollment Link: {enrollment_link}")
            logger.info("=" * 60)
            return f"dev_mode_{token[:8]}"  # Return fake message ID
        
        # Production mode - send via SES
        try:
            response = self.ses_client.send_email(
                Source=self.sender_email,
                Destination={'ToAddresses': [recipient_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                        'Html': {'Data': html_body, 'Charset': 'UTF-8'}
                    }
                }
            )
            logger.info(f"Email sent to {recipient_email}")
            return response['MessageId']
        except ClientError as e:
            logger.error(f"Failed to send email: {e}")
            return None

    def send_alert_email(self, recipient_email, alert_data, base_url=None):
        """Send alert notification email."""
        event_type = alert_data.get('event_type', 'unknown').replace('_', ' ').title()
        severity = alert_data.get('severity', 'medium').upper()
        camera_id = alert_data.get('camera_id', 'N/A')
        description = alert_data.get('description', 'Activity detected')
        timestamp = alert_data.get('timestamp', 'N/A')

        severity_colors = {
            'HIGH': '#ef4444',
            'MEDIUM': '#f59e0b',
            'LOW': '#3b82f6',
        }
        color = severity_colors.get(severity, '#f59e0b')

        subject = f"🚨 SurveillX Alert — {event_type} ({severity})"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background: #0a0c10; color: #e6edf3; padding: 2rem;">
            <div style="max-width: 500px; margin: 0 auto; background: #1a1d23; border-radius: 8px; border: 1px solid #30363d; overflow: hidden;">
                <div style="background: {color}; padding: 1rem; text-align: center;">
                    <h2 style="margin: 0; color: white;">⚠ {severity} ALERT</h2>
                </div>
                <div style="padding: 1.5rem;">
                    <h3 style="margin-top: 0;">{event_type}</h3>
                    <p>{description}</p>
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                        <tr><td style="padding: 6px 0; color: #8b949e;">Camera</td><td style="padding: 6px 0;">{camera_id}</td></tr>
                        <tr><td style="padding: 6px 0; color: #8b949e;">Time</td><td style="padding: 6px 0;">{timestamp}</td></tr>
                        <tr><td style="padding: 6px 0; color: #8b949e;">Severity</td><td style="padding: 6px 0; color: {color}; font-weight: bold;">{severity}</td></tr>
                    </table>
                    {f'<p style="margin-top: 1rem;"><a href="{base_url}" style="color: #2563eb;">Open SurveillX Dashboard →</a></p>' if base_url else ''}
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""SurveillX Alert: {event_type}
Severity: {severity}
Camera: {camera_id}
Time: {timestamp}
Description: {description}
"""

        if self.development_mode:
            logger.info("=" * 60)
            logger.info("DEVELOPMENT MODE - Alert Email NOT sent")
            logger.info(f"To: {recipient_email}")
            logger.info(f"Subject: {subject}")
            logger.info(f"Event: {event_type} | Severity: {severity} | Camera: {camera_id}")
            logger.info("=" * 60)
            return "dev_mode_alert"

        try:
            response = self.ses_client.send_email(
                Source=self.sender_email,
                Destination={'ToAddresses': [recipient_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                        'Html': {'Data': html_body, 'Charset': 'UTF-8'}
                    }
                }
            )
            logger.info(f"Alert email sent to {recipient_email}")
            return response['MessageId']
        except ClientError as e:
            logger.error(f"Failed to send alert email: {e}")
            return None
