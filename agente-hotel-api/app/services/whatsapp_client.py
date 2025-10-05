# [PROMPT 2.4] app/services/whatsapp_client.py

import hashlib
import hmac
import time
from typing import Optional, Dict, Any, List

import httpx
import structlog
from prometheus_client import Counter, Histogram, Gauge

from ..core.settings import settings
from ..exceptions.whatsapp_exceptions import (
    WhatsAppError,
    WhatsAppAuthError,
    WhatsAppRateLimitError,
    WhatsAppMediaError,
    WhatsAppTemplateError,
    WhatsAppWebhookError,
    WhatsAppNetworkError,
)

logger = structlog.get_logger(__name__)

# Prometheus metrics
whatsapp_messages_sent = Counter(
    "whatsapp_messages_sent_total",
    "Total WhatsApp messages sent",
    ["type", "status"]
)
whatsapp_media_downloads = Counter(
    "whatsapp_media_downloads_total",
    "Total WhatsApp media downloads",
    ["status"]
)
whatsapp_api_latency = Histogram(
    "whatsapp_api_latency_seconds",
    "WhatsApp API request latency",
    ["endpoint", "method"]
)
whatsapp_rate_limit_remaining = Gauge(
    "whatsapp_rate_limit_remaining",
    "Remaining WhatsApp API rate limit"
)


class WhatsAppMetaClient:
    """
    WhatsApp Business Cloud API v18.0 client.
    
    Features:
    - Text message sending
    - Template message sending (with parameters)
    - Media download (2-step process)
    - Webhook signature verification
    - Rate limiting tracking
    - Comprehensive error handling
    - Prometheus metrics
    """
    
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v18.0"
        self.access_token = settings.whatsapp_access_token.get_secret_value()
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.app_secret = settings.whatsapp_app_secret.get_secret_value()
        
        # Configuración de timeouts explícitos
        timeout_config = httpx.Timeout(
            connect=5.0,  # Timeout para establecer conexión
            read=30.0,    # Timeout para leer respuesta (permite mensajes largos)
            write=10.0,   # Timeout para enviar datos
            pool=30.0     # Timeout para obtener conexión del pool
        )
        
        # Límites de conexión
        limits = httpx.Limits(
            max_keepalive_connections=20,  # Conexiones keepalive máximas
            max_connections=100,            # Conexiones totales máximas
            keepalive_expiry=30.0           # Expiración de keepalive en segundos
        )
        
        self.client = httpx.AsyncClient(timeout=timeout_config, limits=limits)
        
        logger.info("whatsapp.client.initialized", phone_number_id=self.phone_number_id)

    async def send_message(self, to: str, text: str) -> Dict[str, Any]:
        """
        Send text message to WhatsApp number.
        
        Args:
            to: Recipient phone number (E.164 format, e.g., "14155552671")
            text: Message text (max 4096 characters)
            
        Returns:
            API response with message_id
            
        Raises:
            WhatsAppAuthError: Authentication failed
            WhatsAppRateLimitError: Rate limit exceeded
            WhatsAppError: Other API errors
        """
        endpoint = f"{self.base_url}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": text}
        }
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        logger.info("whatsapp.send_message.start", to=to, text_length=len(text))
        
        try:
            with whatsapp_api_latency.labels(endpoint="messages", method="POST").time():
                response = await self.client.post(endpoint, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                message_id = result.get("messages", [{}])[0].get("id")
                
                whatsapp_messages_sent.labels(type="text", status="success").inc()
                logger.info("whatsapp.send_message.success", to=to, message_id=message_id)
                
                return result
            
            # Handle error responses
            error_data = response.json() if response.text else {}
            self._handle_error_response(response.status_code, error_data, "send_message")
            
        except httpx.TimeoutException as e:
            whatsapp_messages_sent.labels(type="text", status="timeout").inc()
            logger.error("whatsapp.send_message.timeout", to=to, error=str(e))
            raise WhatsAppNetworkError(f"Timeout sending message: {e}")
        except httpx.NetworkError as e:
            whatsapp_messages_sent.labels(type="text", status="network_error").inc()
            logger.error("whatsapp.send_message.network_error", to=to, error=str(e))
            raise WhatsAppNetworkError(f"Network error: {e}")
        except Exception as e:
            whatsapp_messages_sent.labels(type="text", status="error").inc()
            logger.error("whatsapp.send_message.error", to=to, error=str(e))
            raise
        
        # This line should never be reached due to _handle_error_response raising
        raise WhatsAppError("Unexpected response from WhatsApp API")  # pragma: no cover

    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "es",
        parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Send template message (pre-approved message template).
        
        Args:
            to: Recipient phone number (E.164 format)
            template_name: Name of approved template
            language_code: Template language (default: "es")
            parameters: Template parameters (body, header, footer)
            
        Returns:
            API response with message_id
            
        Raises:
            WhatsAppTemplateError: Template not found or invalid
            WhatsAppAuthError: Authentication failed
            WhatsAppRateLimitError: Rate limit exceeded
            
        Example:
            ```python
            parameters = [{"type": "text", "text": "John Doe"}]
            await client.send_template_message(
                to="14155552671",
                template_name="welcome_message",
                parameters=parameters
            )
            ```
        """
        endpoint = f"{self.base_url}/{self.phone_number_id}/messages"
        
        template_components = []
        if parameters:
            template_components.append({
                "type": "body",
                "parameters": parameters
            })
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": template_components
            }
        }
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        logger.info(
            "whatsapp.send_template.start",
            to=to,
            template=template_name,
            language=language_code
        )
        
        try:
            with whatsapp_api_latency.labels(endpoint="messages/template", method="POST").time():
                response = await self.client.post(endpoint, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                message_id = result.get("messages", [{}])[0].get("id")
                
                whatsapp_messages_sent.labels(type="template", status="success").inc()
                logger.info(
                    "whatsapp.send_template.success",
                    to=to,
                    template=template_name,
                    message_id=message_id
                )
                
                return result
            
            # Handle error responses
            error_data = response.json() if response.text else {}
            
            # Template-specific error handling
            if response.status_code == 400:
                error_message = error_data.get("error", {}).get("message", "Template error")
                raise WhatsAppTemplateError(
                    error_message,
                    template_name=template_name,
                    context=error_data
                )
            
            self._handle_error_response(response.status_code, error_data, "send_template")
            
        except WhatsAppTemplateError:
            whatsapp_messages_sent.labels(type="template", status="template_error").inc()
            raise
        except httpx.TimeoutException as e:
            whatsapp_messages_sent.labels(type="template", status="timeout").inc()
            logger.error("whatsapp.send_template.timeout", to=to, template=template_name, error=str(e))
            raise WhatsAppNetworkError(f"Timeout sending template: {e}")
        except Exception as e:
            whatsapp_messages_sent.labels(type="template", status="error").inc()
            logger.error("whatsapp.send_template.error", to=to, template=template_name, error=str(e))
            raise
        
        raise WhatsAppError("Unexpected response from WhatsApp API")  # pragma: no cover

    async def download_media(self, media_id: str) -> Optional[bytes]:
        """
        Download media file from WhatsApp (2-step process).
        
        Step 1: GET media URL from media_id
        Step 2: Download actual file from URL
        
        Args:
            media_id: WhatsApp media ID from webhook
            
        Returns:
            Media file bytes, or None if not found
            
        Raises:
            WhatsAppMediaError: Media download failed
            WhatsAppAuthError: Authentication failed
            
        Supported formats:
        - Audio: opus, ogg, mp3, aac, amr, m4a
        - Images: jpeg, png
        - Video: mp4, 3gp
        - Documents: pdf, doc, docx, xls, xlsx
        """
        # Step 1: Get media URL
        media_url_endpoint = f"{self.base_url}/{media_id}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        logger.info("whatsapp.download_media.start", media_id=media_id)
        
        try:
            # Get media URL
            with whatsapp_api_latency.labels(endpoint="media/url", method="GET").time():
                url_response = await self.client.get(media_url_endpoint, headers=headers)
            
            if url_response.status_code != 200:
                error_data = url_response.json() if url_response.text else {}
                
                if url_response.status_code == 404:
                    whatsapp_media_downloads.labels(status="not_found").inc()
                    logger.warning("whatsapp.download_media.not_found", media_id=media_id)
                    raise WhatsAppMediaError(
                        f"Media not found: {media_id}",
                        media_id=media_id,
                        status_code=404
                    )
                
                self._handle_error_response(url_response.status_code, error_data, "download_media_url")
            
            url_data = url_response.json()
            download_url = url_data.get("url")
            
            if not download_url:
                whatsapp_media_downloads.labels(status="no_url").inc()
                logger.error("whatsapp.download_media.no_url", media_id=media_id, response=url_data)
                raise WhatsAppMediaError(
                    f"No download URL in response for media: {media_id}",
                    media_id=media_id
                )
            
            # Step 2: Download actual file
            with whatsapp_api_latency.labels(endpoint="media/download", method="GET").time():
                download_response = await self.client.get(download_url, headers=headers)
            
            if download_response.status_code != 200:
                whatsapp_media_downloads.labels(status="download_failed").inc()
                logger.error(
                    "whatsapp.download_media.failed",
                    media_id=media_id,
                    status=download_response.status_code
                )
                raise WhatsAppMediaError(
                    f"Failed to download media: HTTP {download_response.status_code}",
                    media_id=media_id,
                    status_code=download_response.status_code
                )
            
            media_bytes = download_response.content
            media_size = len(media_bytes)
            
            whatsapp_media_downloads.labels(status="success").inc()
            logger.info(
                "whatsapp.download_media.success",
                media_id=media_id,
                size_bytes=media_size,
                content_type=download_response.headers.get("content-type")
            )
            
            return media_bytes
            
        except WhatsAppMediaError:
            raise
        except httpx.TimeoutException as e:
            whatsapp_media_downloads.labels(status="timeout").inc()
            logger.error("whatsapp.download_media.timeout", media_id=media_id, error=str(e))
            raise WhatsAppNetworkError(f"Timeout downloading media: {e}")
        except Exception as e:
            whatsapp_media_downloads.labels(status="error").inc()
            logger.error("whatsapp.download_media.error", media_id=media_id, error=str(e))
            raise WhatsAppMediaError(f"Error downloading media: {e}", media_id=media_id)

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature_header: str
    ) -> bool:
        """
        Verify webhook signature using HMAC-SHA256.
        
        Args:
            payload: Raw webhook payload bytes
            signature_header: X-Hub-Signature-256 header value
            
        Returns:
            True if signature is valid, False otherwise
            
        Security:
        - Uses timing-safe comparison (hmac.compare_digest)
        - Validates signature format (sha256=...)
        - Logs all verification attempts
        
        Example:
            ```python
            payload = request.body
            signature = request.headers.get("X-Hub-Signature-256")
            
            if not client.verify_webhook_signature(payload, signature):
                raise WhatsAppWebhookError("Invalid signature")
            ```
        """
        if not signature_header:
            logger.warning("whatsapp.webhook.signature_missing")
            return False
        
        # Signature format: "sha256=<hex_digest>"
        if not signature_header.startswith("sha256="):
            logger.warning("whatsapp.webhook.signature_invalid_format", signature=signature_header)
            return False
        
        expected_signature = signature_header[7:]  # Remove "sha256=" prefix
        
        # Compute HMAC-SHA256
        computed_hmac = hmac.new(
            key=self.app_secret.encode(),
            msg=payload,
            digestmod=hashlib.sha256
        )
        computed_signature = computed_hmac.hexdigest()
        
        # Timing-safe comparison
        is_valid = hmac.compare_digest(expected_signature, computed_signature)
        
        if is_valid:
            logger.info("whatsapp.webhook.signature_valid")
        else:
            logger.warning(
                "whatsapp.webhook.signature_invalid",
                expected=expected_signature[:10] + "...",
                computed=computed_signature[:10] + "..."
            )
        
        return is_valid

    def _handle_error_response(
        self,
        status_code: int,
        error_data: Dict[str, Any],
        operation: str
    ) -> None:
        """
        Handle WhatsApp API error responses.
        
        Raises appropriate exception based on status code.
        """
        error_info = error_data.get("error", {})
        error_message = error_info.get("message", "Unknown error")
        error_code = error_info.get("code")
        
        logger.error(
            f"whatsapp.{operation}.api_error",
            status=status_code,
            error_code=error_code,
            message=error_message,
            data=error_data
        )
        
        if status_code in (401, 403):
            raise WhatsAppAuthError(
                error_message,
                status_code=status_code,
                error_code=str(error_code),
                context=error_data
            )
        elif status_code == 429:
            retry_after = error_info.get("retry_after", 60)
            raise WhatsAppRateLimitError(
                error_message,
                retry_after=retry_after,
                error_code=str(error_code),
                context=error_data
            )
        else:
            raise WhatsAppError(
                error_message,
                status_code=status_code,
                error_code=str(error_code),
                context=error_data
            )

    async def close(self):
        """Close HTTP client connection pool."""
        await self.client.aclose()
        logger.info("whatsapp.client.closed")
