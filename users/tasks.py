import os

from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.mail import EmailMessage

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_ticket_email(self, email, pdf_path):
    try:
        if not os.path.exists(pdf_path):
            # No point retrying if the file genuinely doesn't exist --
            # that's a bug elsewhere, not a transient failure.
            logger.error("Ticket PDF not found at %s, not retrying.", pdf_path)
            return "Ticket PDF missing, email not sent"

        mail = EmailMessage(
            subject="🎟 Movie Ticket Confirmation",
            body=(
                "Thank you for booking with MovieVerse.\n"
                "Your ticket has been attached to this email.\n"
                "Please carry either:\n"
                "• A printed copy of the ticket\n"
                "OR\n"
                "• The PDF on your mobile device\n"
                "Enjoy your movie!\n"
                "MovieVerse Team"
            ),
            to=[email],
        )
        mail.attach_file(pdf_path)
        mail.send()
        return "Email sent successfully"

    except Exception as exc:
        logger.warning("send_ticket_email failed (attempt %s): %s", self.request.retries, exc)
        raise self.retry(exc=exc, countdown=60)
