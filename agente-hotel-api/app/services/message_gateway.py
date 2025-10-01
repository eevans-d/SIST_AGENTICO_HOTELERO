# [PROMPT 2.4] app/services/message_gateway.py

from datetime import datetime, timezone
import logging
from typing import Any, Dict

from ..models.unified_message import UnifiedMessage
from .feature_flag_service import DEFAULT_FLAGS
from .metrics_service import metrics_service

logger = logging.getLogger(__name__)

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

    def normalize_whatsapp_message(self, webhook_payload: Dict[str, Any]) -> UnifiedMessage:
        canal = "whatsapp"
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

                tenant_id = self._resolve_tenant(user_id)

                unified = UnifiedMessage(
                    message_id=msg_id or user_id or "",
                    canal=canal,
                    user_id=user_id or "",
                    timestamp_iso=ts_iso,
                    tipo="audio" if msg_type == "audio" else "text",
                    texto=text,
                    media_url=media_url,
                    metadata={},
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

    def normalize_gmail_message(self, email_object) -> UnifiedMessage:
        # TODO: Implementar Gmail → UnifiedMessage (backlog)
        raise NotImplementedError("normalize_gmail_message no implementado")

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
