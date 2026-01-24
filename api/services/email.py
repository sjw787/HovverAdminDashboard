"""
Email service using Resend for sending customer notifications.
"""
from pathlib import Path
import resend

from config import settings


# Get the project root directory (where templates/ is located)
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"


class EmailService:
    """Resend email service for customer notifications."""

    def __init__(self):
        # Initialize Resend with API key
        resend.api_key = settings.resend_api_key
        self.sender_email = settings.sender_email
        self.sender_name = settings.sender_name

    def _load_template(self, template_name: str) -> str:
        """
        Load an email template from the templates directory.

        Args:
            template_name: Name of the template file (e.g., 'customer_welcome.html')

        Returns:
            Template content as string

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        template_path = TEMPLATES_DIR / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        return template_path.read_text(encoding='utf-8')

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
            Exception: If email sending fails (allows customer creation to continue)
        """
        subject = "Welcome to Hover - Your Account Has Been Created"

        # Load template and format with values
        template = self._load_template('customer_welcome.html')
        html_body = template.format(
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            temporary_password=temporary_password,
            login_url=settings.frontend_url
        )

        try:
            # Send email via Resend
            response = resend.Emails.send({
                "from": f"{self.sender_name} <{self.sender_email}>",
                "to": [recipient_email],
                "subject": subject,
                "html": html_body,
            })

            # Log the email ID for tracking
            email_id = response.get('id')
            print(f"Email sent successfully via Resend. Email ID: {email_id}")

            return True

        except Exception as e:
            # Raise regular Exception (not HTTPException)
            # This allows customer creation to succeed even if email fails
            error_message = str(e)
            print(f"Failed to send email via Resend: {error_message}")
            raise Exception(f"Failed to send welcome email: {error_message}")

    def send_admin_welcome_email(
        self,
        recipient_email: str,
        recipient_name: str,
        temporary_password: str
    ) -> bool:
        """
        Send welcome email with temporary password to admin user.

        This method uses the same template structure as customer emails but with admin-specific messaging.
        Use this when manually creating admin users in Cognito console.

        Args:
            recipient_email: Admin's email address
            recipient_name: Admin's name
            temporary_password: Temporary password to include in email

        Returns:
            True if email sent successfully

        Raises:
            Exception: If email sending fails
        """
        subject = "Welcome to Hover Admin - Your Account Has Been Created"

        # Load template and format with values
        template = self._load_template('admin_welcome.html')
        html_body = template.format(
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            temporary_password=temporary_password,
            login_url=settings.frontend_url
        )

        try:
            # Send email via Resend
            response = resend.Emails.send({
                "from": f"{self.sender_name} <{self.sender_email}>",
                "to": [recipient_email],
                "subject": subject,
                "html": html_body,
            })

            # Log the email ID for tracking
            email_id = response.get('id')
            print(f"Admin welcome email sent successfully via Resend. Email ID: {email_id}")

            return True

        except Exception as e:
            # Raise regular Exception
            error_message = str(e)
            print(f"Failed to send admin welcome email via Resend: {error_message}")
            raise Exception(f"Failed to send admin welcome email: {error_message}")


# Global email service instance
email_service = EmailService()
