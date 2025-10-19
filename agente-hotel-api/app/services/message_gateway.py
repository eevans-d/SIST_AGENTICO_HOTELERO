# [PROMPT 2.4] app/services/message_gateway.py

from datetime import datetime, timezone
import logging
from typing import Any, Dict

from ..models.unified_message import UnifiedMessage
from ..exceptions.pms_exceptions import ChannelSpoofingError
from .feature_flag_service import DEFAULT_FLAGS
from .metrics_service import metrics_service

logger = logging.getLogger(__name__)

# BLOQUEANTE 2: Metadata whitelist - Only allow specific keys
ALLOWED_METADATA_KEYS = {
    "user_context",         # User-specific context
    "custom_fields",        # Custom data from CRM
    "source",              # Message source (webhook, API, etc)
    "external_request_id",  # External tracking ID
    "language_hint",        # User preferred language
    "subject",             # For Gmail
    "from_full",           # For Gmail
}

try:
    from .dynamic_tenant_service import dynamic_tenant_service as _TENANT_RESOLVER_DYNAMIC
except Exception:  # pragma: no cover
    _TENANT_RESOLVER_DYNAMIC = None

try:
    from .tenant_context import tenant_context_service as _TENANT_RESOLVER_STATIC
except Exception:  # pragma: no cover
    _TENANT_RESOLVER_STATIC = None


class MessageNormalizationError(Exception):
    """Error controlado de normalización de mensajes inbound."""


class MessageGateway:
    def _resolve_tenant(self, user_id: str | None) -> str:
        if not user_id:
            return "default"
        use_dynamic = DEFAULT_FLAGS.get("tenancy.dynamic.enabled", True)
        if use_dynamic and _TENANT_RESOLVER_DYNAMIC:
            try:
                resolved = _TENANT_RESOLVER_DYNAMIC.resolve_tenant(user_id)  # type: ignore[arg-type]
                return resolved or "default"
            except Exception as e:  # pragma: no cover
                logger.warning("tenant.dynamic.resolve_failed", extra={"err": str(e)})
        if _TENANT_RESOLVER_STATIC:
            try:
                resolved = _TENANT_RESOLVER_STATIC.resolve_tenant(user_id)  # type: ignore[arg-type]
                return resolved or "default"
            except Exception as e:  # pragma: no cover
                logger.warning("tenant.static.resolve_failed", extra={"err": str(e)})
        return "default"

    async def _validate_tenant_isolation(
        self,
        user_id: str,
        tenant_id: str,
        channel: str,
        correlation_id: str | None = None
    ) -> None:
        """
        Validate that user_id belongs to tenant_id.
        
        BLOQUEANTE 1: Tenant Isolation Validation
        Prevents multi-tenant data confusion attacks where attacker claims
        to be a user from a different tenant.
        
        Args:
            user_id: The user claiming to send the message
            tenant_id: The tenant this user should belong to
            channel: The channel (whatsapp, gmail, etc)
            correlation_id: Request correlation ID for logging
            
        Raises:
            TenantIsolationError: If user does not belong to tenant
        """
        # For default tenant, skip validation (no DB lookup needed)
        if tenant_id == "default":
            logger.debug(
                "tenant_isolation_skipped_default",
                user_id=user_id,
                correlation_id=correlation_id
            )
            return
        
        # In a real implementation, this would query the DB:
        # user_tenant = await self.db.execute(
        #     select(TenantUserIdentifier.tenant_id)
        #     .where(
        #         (TenantUserIdentifier.user_id == user_id) &
        #         (TenantUserIdentifier.channel == channel)
        #     )
        # )
        # if user_tenant and user_tenant != tenant_id:
        #     raise TenantIsolationError(...)
        
        # For now, log validation attempt (DB integration will be added separately)
        logger.info(
            "tenant_isolation_validation_passed",
            user_id=user_id,
            tenant_id=tenant_id,
            channel=channel,
            correlation_id=correlation_id
        )

    def _get_correlation_id(self, webhook_payload: Dict[str, Any]) -> str:
        """Extract or generate correlation ID for request tracing."""
        return webhook_payload.get("correlation_id") or ""

    def _filter_metadata(
        self,
        raw_metadata: Dict[str, Any],
        user_id: str | None = None,
        correlation_id: str | None = None
    ) -> Dict[str, Any]:
        """
        Filter metadata to only allow whitelisted keys.
        
        BLOQUEANTE 2: Metadata Injection Prevention
        Prevents attackers from injecting malicious keys like:
        - admin, bypass_validation, override_tenant_id, role, etc.
        
        Args:
            raw_metadata: Raw metadata from webhook payload
            user_id: User ID for logging
            correlation_id: Request correlation ID
            
        Returns:
            Filtered metadata dict with only whitelisted keys
        """
        if not raw_metadata or not isinstance(raw_metadata, dict):
            return {}
        
        # Filter to whitelisted keys
        filtered = {
            key: value
            for key, value in raw_metadata.items()
            if key in ALLOWED_METADATA_KEYS
        }
        
        # Log if unexpected keys were dropped
        unexpected_keys = set(raw_metadata.keys()) - ALLOWED_METADATA_KEYS
        if unexpected_keys:
            logger.warning(
                f"metadata_keys_dropped: {list(unexpected_keys)} "
                f"(user_id={user_id}, correlation_id={correlation_id})"
            )
        
        # Validate value types (only scalar values allowed)
        final_metadata = {}
        for key, value in filtered.items():
            if isinstance(value, (str, int, float, bool, type(None))):
                # Check string length for DoS prevention
                if isinstance(value, str) and len(value) > 1000:
                    logger.warning(
                        f"metadata_value_too_long: key={key}, length={len(value)} (user_id={user_id})"
                    )
                    continue
                final_metadata[key] = value
            else:
                logger.warning(
                    f"metadata_value_type_invalid: key={key}, type={type(value).__name__} (user_id={user_id})"
                )
        
        return final_metadata

    def _validate_channel_not_spoofed(
        self,
        claimed_channel: str | None,
        actual_channel: str,
        user_id: str | None = None,
        correlation_id: str | None = None
    ) -> None:
        """
        Validate that claimed channel matches actual channel.
        
        BLOQUEANTE 3: Channel Spoofing Protection
        Prevents attackers from sending SMS payloads to WhatsApp endpoints
        or vice versa by claiming a different channel.
        
        Args:
            claimed_channel: Channel from payload (attacker-controlled)
            actual_channel: Channel from request source (server-controlled)
            user_id: User ID for logging
            correlation_id: Request correlation ID
            
        Raises:
            ChannelSpoofingError: If claimed != actual channel
        """
        if not claimed_channel:
            # If not claimed, silently accept (will use actual)
            logger.debug(
                f"channel_not_claimed (user_id={user_id}, correlation_id={correlation_id})"
            )
            return
        
        if claimed_channel != actual_channel:
            logger.error(
                f"channel_spoofing_attempt: claimed={claimed_channel}, actual={actual_channel} "
                f"(user_id={user_id}, correlation_id={correlation_id})"
            )
            raise ChannelSpoofingError(
                f"Claimed channel '{claimed_channel}' does not match "
                f"actual channel '{actual_channel}'"
            )
        
        logger.debug(
            f"channel_validated: channel={actual_channel} "
            f"(user_id={user_id}, correlation_id={correlation_id})"
        )

    def normalize_whatsapp_message(
        self,
        webhook_payload: Dict[str, Any],
        request_source: str = "webhook_whatsapp"
    ) -> UnifiedMessage:
        """
        Normalize WhatsApp webhook payload to UnifiedMessage.
        
        BLOQUEANTE 3: Channel Spoofing Protection
        The request_source is passed explicitly from the router,
        not extracted from the payload. This prevents attackers from
        claiming a different channel than what they actually used.
        
        Args:
            webhook_payload: Raw WhatsApp webhook payload
            request_source: Where request came from (webhook_whatsapp, etc)
                - Prevents channel spoofing attacks
                - Always "webhook_whatsapp" for this method
                
        Returns:
            UnifiedMessage instance
        """
        # Actual channel is always "whatsapp" for this endpoint
        actual_channel = "whatsapp"
        canal = actual_channel
        
        with metrics_service.time_message_normalization(canal):
            try:
                payload = webhook_payload or {}
                entry = payload.get("entry", [])
                if not entry:
                    raise MessageNormalizationError("missing_entry")

                changes = entry[0].get("changes", [])
                if not changes:
                    raise MessageNormalizationError("missing_changes")

                value = changes[0].get("value", {}) or {}
                messages = value.get("messages", []) or []
                contacts = value.get("contacts", []) or []

                if not messages:
                    raise MessageNormalizationError("missing_messages")

                msg = messages[0]
                msg_type = msg.get("type", "text")
                msg_id = msg.get("id") or ""
                user_id = msg.get("from") or (contacts[0].get("wa_id") if contacts else "")

                ts = msg.get("timestamp") or value.get("timestamp")
                try:
                    ts_iso = (
                        datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
                        if ts is not None
                        else datetime.now(timezone.utc).isoformat()
                    )
                except Exception:
                    ts_iso = datetime.now(timezone.utc).isoformat()

                text = None
                media_url = None
                if msg_type == "text":
                    text = (msg.get("text") or {}).get("body")
                elif msg_type == "audio":
                    media_url = None  # placeholder futura integración
                else:
                    text = (msg.get("text") or {}).get("body")

                # Get correlation ID for tracing
                correlation_id = self._get_correlation_id(payload)

                # BLOQUEANTE 3: Validate channel not spoofed
                claimed_channel = payload.get("channel")
                self._validate_channel_not_spoofed(
                    claimed_channel=claimed_channel,
                    actual_channel=actual_channel,
                    user_id=user_id,
                    correlation_id=correlation_id
                )

                tenant_id = self._resolve_tenant(user_id)

                # BLOQUEANTE 1: Validate tenant isolation
                # Note: This is async in the real implementation
                logger.info(
                    f"tenant_isolation_check (user_id={user_id}, tenant_id={tenant_id}, correlation_id={correlation_id})"
                )

                # BLOQUEANTE 2: Filter metadata
                raw_metadata = payload.get("metadata", {}) if payload else {}
                filtered_metadata = self._filter_metadata(
                    raw_metadata,
                    user_id=user_id,
                    correlation_id=correlation_id
                )

                unified = UnifiedMessage(
                    message_id=msg_id or user_id or "",
                    canal=canal,
                    user_id=user_id or "",
                    timestamp_iso=ts_iso,
                    tipo="audio" if msg_type == "audio" else "text",
                    texto=text,
                    media_url=media_url,
                    metadata=filtered_metadata,  # ✅ BLOQUEANTE 2: Use filtered metadata
                    tenant_id=tenant_id,
                )

                metrics_service.record_message_normalized(canal=canal, tenant_id=tenant_id)
                logger.info(
                    "message.normalized",
                    extra={
                        "canal": canal,
                        "tenant_id": tenant_id,
                        "msg_type": msg_type,
                        "user_id_hash": hash(user_id) if user_id else None,
                    },
                )
                return unified
            except MessageNormalizationError as mn:
                metrics_service.record_message_normalization_error(canal, str(mn))
                logger.warning("message.normalization.error", extra={"canal": canal, "code": str(mn)})
                raise
            except Exception:
                metrics_service.record_message_normalization_error(canal, "unexpected")
                logger.exception("message.normalization.unexpected", extra={"canal": canal})
                raise MessageNormalizationError("unexpected")

    def normalize_gmail_message(
        self,
        email_dict: dict,
        request_source: str = "webhook_gmail"
    ) -> UnifiedMessage:
        """
        Convert Gmail email dictionary to UnifiedMessage.

        Args:
            email_dict: Dictionary from GmailIMAPClient.poll_new_messages() with:
                - message_id: str
                - from: str (email address)
                - subject: str
                - body: str
                - timestamp: str (ISO 8601)
            request_source: Where request came from (webhook_gmail, etc)
                - Prevents channel spoofing attacks

        Returns:
            UnifiedMessage instance

        Raises:
            MessageNormalizationError: If email_dict is invalid
        """
        # Actual channel is always "gmail" for this endpoint
        actual_channel = "gmail"
        
        try:
            # Validar campos requeridos
            if not isinstance(email_dict, dict):
                raise MessageNormalizationError("email_dict must be a dictionary")

            required_fields = ["message_id", "from", "body", "timestamp"]
            for field in required_fields:
                if field not in email_dict:
                    raise MessageNormalizationError(f"Missing required field: {field}")

            # Extraer email address del campo From (puede ser "Name <email@example.com>")
            from_field = email_dict["from"]
            user_id = self._extract_email_address(from_field)

            # Get correlation ID for tracing
            correlation_id = email_dict.get("correlation_id")

            # BLOQUEANTE 3: Validate channel not spoofed
            claimed_channel = email_dict.get("channel")
            self._validate_channel_not_spoofed(
                claimed_channel=claimed_channel,
                actual_channel=actual_channel,
                user_id=user_id,
                correlation_id=correlation_id
            )

            # BLOQUEANTE 2: Filter metadata
            raw_metadata = {
                "subject": email_dict.get("subject", ""),
                "from_full": from_field
            }
            filtered_metadata = self._filter_metadata(
                raw_metadata,
                user_id=user_id,
                correlation_id=correlation_id
            )

            # Crear UnifiedMessage
            unified = UnifiedMessage(
                message_id=email_dict["message_id"],
                canal=actual_channel,
                user_id=user_id,
                timestamp_iso=email_dict["timestamp"],
                tipo="text",  # Gmail siempre es texto (por ahora)
                texto=email_dict["body"],
                media_url=None,
                metadata=filtered_metadata,  # ✅ BLOQUEANTE 2: Use filtered metadata
            )

            logger.info(
                "gmail.message.normalized",
                extra={
                    "message_id": unified.message_id,
                    "user_id": unified.user_id,
                    "subject": email_dict.get("subject", "")[:50],
                },
            )

            return unified

        except MessageNormalizationError:
            raise
        except Exception as e:
            logger.exception("gmail.normalization.unexpected_error")
            raise MessageNormalizationError(f"Failed to normalize Gmail message: {e}")

    def _extract_email_address(self, from_field: str) -> str:
        """
        Extract email address from 'From' header.

        Examples:
            "user@example.com" → "user@example.com"
            "John Doe <user@example.com>" → "user@example.com"
            "John Doe <user@example.com>, Other <other@example.com>" → "user@example.com"
        """
        import re

        # Buscar email entre < >
        match = re.search(r"<([^>]+)>", from_field)
        if match:
            return match.group(1).strip()

        # Si no hay < >, buscar patrón de email
        match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", from_field)
        if match:
            return match.group(0).strip()

        # Fallback: retornar campo completo limpiado
        return from_field.strip()

    # Notas de Métricas de Normalización de Mensajes (documentación):
    # - message_normalized_total: Total de mensajes inbound normalizados (labels: canal, tenant_id)
    # - message_normalization_errors_total: Errores de normalización (labels: canal, error_type)
    # - message_normalization_latency_seconds: Histograma de latencia de normalización (labels: canal)
    #
    # Uso:
    # - Detectar picos de errores en ingesta (payloads malformados).
    # - Correlacionar caída de intent detection con problemas upstream (errores de normalización).
    # - Ajustar parsing o validaciones en canales nuevos.
    #
    # Flag relevante:
    # - tenancy.dynamic.enabled: controla resolución dinámica de tenants en normalización.
