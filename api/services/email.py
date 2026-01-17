"""
Email service using AWS SES for sending customer notifications.
"""
import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

from config import settings


class EmailService:
    """AWS SES email service for customer notifications."""

    def __init__(self):
        self.region = settings.ses_region or settings.aws_region
        self.sender_email = settings.ses_sender_email

        # Initialize SES client
        self.client = boto3.client('ses', region_name=self.region)

    def send_welcome_email(
        self,
        recipient_email: str,
        recipient_name: str,
        temporary_password: str
    ) -> bool:
        """
        Send welcome email with temporary password to customer.

        Args:
            recipient_email: Customer's email address
            recipient_name: Customer's name
            temporary_password: Temporary password to include in email

        Returns:
            True if email sent successfully

        Raises:
            HTTPException: If email sending fails
        """
        subject = "Welcome to Hover - Your Account Has Been Created"

        # Get frontend URL from settings
        login_url = settings.frontend_url

        # HTML email body
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border: 1px solid #ddd;
                    border-radius: 0 0 5px 5px;
                }}
                .credentials {{
                    background-color: #fff;
                    padding: 15px;
                    margin: 20px 0;
                    border-left: 4px solid #4CAF50;
                }}
                .password {{
                    font-family: monospace;
                    font-size: 18px;
                    font-weight: bold;
                    color: #d32f2f;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    margin: 20px 0;
                    background-color: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                }}
                .button:hover {{
                    background-color: #45a049;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Hover!</h1>
                </div>
                <div class="content">
                    <p>Hello {recipient_name},</p>
                    
                    <p>Your Hover account has been created! You can now access your personalized dashboard and view your photos.</p>
                    
                    <div class="credentials">
                        <p><strong>Your Login Credentials:</strong></p>
                        <p><strong>Username:</strong> {recipient_email}</p>
                        <p><strong>Temporary Password:</strong> <span class="password">{temporary_password}</span></p>
                    </div>
                    
                    <p><strong>Important:</strong> For security reasons, you must change this password when you first log in.</p>
                    
                    <div style="text-align: center;">
                        <a href="{login_url}" class="button">Login to Your Account</a>
                    </div>
                    
                    <p>To get started:</p>
                    <ol>
                        <li>Click the button above or visit <a href="{login_url}">{login_url}</a></li>
                        <li>Enter your username and temporary password</li>
                        <li>Follow the prompts to set your new password</li>
                    </ol>
                    
                    <p>If you have any questions or need assistance, please don't hesitate to reach out.</p>
                    
                    <p>Best regards,<br>The Hover Team</p>
                </div>
                <div class="footer">
                    <p>This email was sent to {recipient_email}</p>
                    <p>© 2026 Hover. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Plain text version for email clients that don't support HTML
        text_body = f"""Welcome to Hover!

Hello {recipient_name},

Your Hover account has been created!

Your Login Credentials:
Username: {recipient_email}
Temporary Password: {temporary_password}

IMPORTANT: For security reasons, you must change this password when you first log in.

To get started:
1. Visit {login_url}
2. Enter your username and temporary password
3. Follow the prompts to set your new password

If you have any questions or need assistance, please don't hesitate to reach out.

Best regards,
The Hover Team

---
This email was sent to {recipient_email}
© 2026 Hover. All rights reserved.
"""

        try:
            response = self.client.send_email(
                Source=self.sender_email,
                Destination={
                    'ToAddresses': [recipient_email]
                },
                Message={
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Text': {
                            'Data': text_body,
                            'Charset': 'UTF-8'
                        },
                        'Html': {
                            'Data': html_body,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            )

            # Log the message ID for tracking
            message_id = response.get('MessageId')
            print(f"Email sent successfully. Message ID: {message_id}")

            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']

            # For sandbox mode errors, raise regular Exception (not HTTPException)
            # This allows customer creation to succeed even if email fails
            if error_code == 'MessageRejected':
                # Check if it's a sandbox error
                if 'not verified' in error_message.lower() or 'sandbox' in error_message.lower():
                    raise Exception(f"Email rejected (SES sandbox mode): {error_message}")
                else:
                    raise Exception(f"Email rejected: {error_message}")
            elif error_code == 'MailFromDomainNotVerifiedException':
                raise Exception(f"Email domain not verified in SES: {error_message}")
            elif error_code == 'ConfigurationSetDoesNotExistException':
                raise Exception(f"SES configuration error: {error_message}")
            else:
                raise Exception(f"Failed to send email: {error_message}")


# Global email service instance
email_service = EmailService()
