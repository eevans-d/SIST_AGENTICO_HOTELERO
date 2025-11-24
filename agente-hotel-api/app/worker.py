from app.core.celery_app import celery_app
from app.services.gmail_client import GmailIMAPClient, GmailClientError
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@celery_app.task(acks_late=True)
def test_task(word: str) -> str:
    return f"test task return {word}"

@celery_app.task(
    acks_late=True,
    autoretry_for=(GmailClientError,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3}
)
def send_email_task(to_email: str, subject: str, body: str):
    """
    Celery task to send emails asynchronously via Gmail.
    """
    logger.info(f"Starting send_email_task to {to_email}")
    try:
        client = GmailIMAPClient()
        client.send_response(to=to_email, subject=subject, body=body)
        logger.info(f"Successfully sent email to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        raise
