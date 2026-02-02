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
