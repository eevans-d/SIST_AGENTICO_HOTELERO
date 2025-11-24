"""
Dead Letter Queue (DLQ) Service.

Redis-backed queue for failed messages with automatic retry logic and exponential backoff.

Architecture:
    MessageGateway → Orchestrator
           ↓ (error)
       DLQService
           ↓
       Redis List (dlq:messages)
           ↓ (retry worker)
       RetryWorker → Orchestrator
           ↓ (3 failures)
       Permanent Failure (PostgreSQL)
"""

import json
import traceback
import uuid
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.settings import get_settings
from app.models.dlq import DLQEntry
from app.models.unified_message import UnifiedMessage
from app.monitoring.dlq_metrics import (
    dlq_messages_expired_total,
    dlq_messages_total,
    dlq_oldest_message_age_seconds,
    dlq_permanent_failures_total,
    dlq_queue_size,
    dlq_retries_total,
    dlq_retry_latency_seconds,
)

settings = get_settings()


class DLQService:
    """
    Dead Letter Queue service for handling failed message processing.

    Features:
    - Redis-backed queue with sorted set for scheduled retries
    - Exponential backoff retry strategy (60s → 120s → 240s)
    - Permanent failure storage in PostgreSQL after max retries
    - TTL-based message expiration (default 7 days)
    - Prometheus metrics integration
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        db_session: AsyncSession,
        max_retries: int = 3,
        retry_backoff_base: int = 60,
        ttl_days: int = 7,
    ):
        """
        Initialize DLQ service.

        Args:
            redis_client: Async Redis client
            db_session: Async SQLAlchemy session
            max_retries: Maximum retry attempts before permanent failure (default: 3)
            retry_backoff_base: Base delay in seconds for exponential backoff (default: 60)
            ttl_days: Time-to-live for messages in days (default: 7)
        """
        self.redis = redis_client
        self.db = db_session
        self.max_retries = max_retries
        self.retry_backoff_base = retry_backoff_base
        self.ttl_seconds = ttl_days * 24 * 60 * 60

        # Redis key prefixes
        self.DLQ_MESSAGE_PREFIX = "dlq:messages:"
        self.DLQ_RETRY_SCHEDULE = "dlq:retry_schedule"
        self.DLQ_STATS_TOTAL = "dlq:stats:total"

    async def enqueue_failed_message(
        self,
        message: UnifiedMessage,
        error: Exception,
        retry_count: int = 0,
        correlation_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> str:
        """
        Enqueue a failed message to DLQ for retry.

        Args:
            message: The failed UnifiedMessage
            error: Exception that caused the failure
            retry_count: Current retry count (default: 0 for first failure)
            correlation_id: Optional correlation ID for tracing
            reason: Optional human-readable failure reason (e.g., "audio_processing_failure")

        Returns:
            str: DLQ entry ID (UUID)
        """
        dlq_id = str(uuid.uuid4())
        error_type = reason or type(error).__name__
        error_msg = str(error)

        # Calculate next retry time with exponential backoff
        backoff_seconds = self.retry_backoff_base * (2**retry_count)
        retry_at = datetime.now(UTC) + timedelta(seconds=backoff_seconds)

        # Prepare DLQ entry data
        dlq_data = {
            "dlq_id": dlq_id,
            "message": {
                "message_id": message.message_id,
                "canal": message.canal,
                "user_id": message.user_id,
                "timestamp_iso": message.timestamp_iso,
                "tipo": message.tipo,
                "texto": message.texto,
                "media_url": message.media_url,
                "metadata": message.metadata,
                "tenant_id": message.tenant_id,
            },
            "error_type": error_type,
            "error_message": error_msg,
            "error_traceback": traceback.format_exc(),
            "retry_count": retry_count,
            "first_failed_at": datetime.now(UTC).isoformat(),
            "retry_at": retry_at.isoformat(),
            "correlation_id": correlation_id or message.metadata.get("correlation_id"),
        }

        # Store in Redis hash with TTL
        message_key = f"{self.DLQ_MESSAGE_PREFIX}{dlq_id}"
        await self.redis.hset(message_key, mapping={k: json.dumps(v) for k, v in dlq_data.items()})
        await self.redis.expire(message_key, self.ttl_seconds)

        # Add to retry schedule (sorted set, score = retry timestamp)
        retry_timestamp = retry_at.timestamp()
        await self.redis.zadd(self.DLQ_RETRY_SCHEDULE, {dlq_id: retry_timestamp})

        # Increment stats counter
        await self.redis.incr(self.DLQ_STATS_TOTAL)

        # Update metrics
        dlq_messages_total.labels(reason=error_type).inc()
        await self._update_queue_size_metric()

        logger.info(
            "dlq_message_enqueued",
            dlq_id=dlq_id,
            error_type=error_type,
            retry_count=retry_count,
            retry_at=retry_at.isoformat(),
            backoff_seconds=backoff_seconds,
            correlation_id=correlation_id,
        )

        return dlq_id

    async def get_retry_candidates(self) -> List[Dict[str, Any]]:
        """
        Get messages ready for retry based on current time.

        Returns:
            List of DLQ entry dictionaries ready for retry
        """
        current_timestamp = datetime.now(UTC).timestamp()

        # Get all messages with retry_at <= now
        candidates_ids = await self.redis.zrangebyscore(
            self.DLQ_RETRY_SCHEDULE, min=0, max=current_timestamp
        )

        candidates = []
        for dlq_id in candidates_ids:
            dlq_id_str = dlq_id.decode("utf-8") if isinstance(dlq_id, bytes) else dlq_id
            message_key = f"{self.DLQ_MESSAGE_PREFIX}{dlq_id_str}"

            # Get message data from hash
            dlq_data_raw = await self.redis.hgetall(message_key)
            if not dlq_data_raw:
                # Message expired or deleted, remove from schedule
                await self.redis.zrem(self.DLQ_RETRY_SCHEDULE, dlq_id_str)
                continue

            # Deserialize data
            dlq_data = {
                k.decode("utf-8"): json.loads(v.decode("utf-8"))
                for k, v in dlq_data_raw.items()
            }
            candidates.append(dlq_data)

        logger.info("dlq_retry_candidates_found", count=len(candidates))
        return candidates

    async def retry_message(self, dlq_id: str) -> bool:
        """
        Retry processing a message from DLQ.

        Args:
            dlq_id: DLQ entry ID

        Returns:
            bool: True if retry succeeded, False otherwise
        """
        start_time = datetime.now(UTC)
        message_key = f"{self.DLQ_MESSAGE_PREFIX}{dlq_id}"

        # Get message data
        dlq_data_raw = await self.redis.hgetall(message_key)
        if not dlq_data_raw:
            logger.warning("dlq_message_not_found", dlq_id=dlq_id)
            await self.redis.zrem(self.DLQ_RETRY_SCHEDULE, dlq_id)
            return False

        dlq_data = {
            k.decode("utf-8"): json.loads(v.decode("utf-8")) for k, v in dlq_data_raw.items()
        }

        retry_count = dlq_data["retry_count"]
        message_data = dlq_data["message"]

        logger.info(
            "dlq_retry_attempt",
            dlq_id=dlq_id,
            retry_count=retry_count,
            correlation_id=dlq_data.get("correlation_id"),
        )

        try:
            # Reconstruct UnifiedMessage from dict
            from app.models.unified_message import UnifiedMessage
            
            message = UnifiedMessage(
                message_id=message_data.get("message_id", ""),
                canal=message_data.get("canal", "whatsapp"),
                user_id=message_data.get("user_id", ""),
                timestamp_iso=message_data.get("timestamp_iso", ""),
                timestamp=message_data.get("timestamp"),
                tipo=message_data.get("tipo", "text"),
                texto=message_data.get("texto"),
                media_url=message_data.get("media_url"),
                metadata=message_data.get("metadata", {}),
                tenant_id=message_data.get("tenant_id"),
            )

            # Obtener instancia de Orchestrator
            # 1) Preferir instancia inyectada en self.orchestrator (tests/overrides)
            # 2) Fallback al singleton global inicializado en app lifespan
            orch = getattr(self, "orchestrator", None)
            if orch is None:
                # Import lazily para evitar ciclos
                from app.services import orchestrator
                orch = await orchestrator.get_orchestrator()
            if orch is None:
                raise RuntimeError("Orchestrator not initialized")

            # Retry processing
            await orch.process_message(message)

            # Success - remove from DLQ
            await self.redis.delete(message_key)
            await self.redis.zrem(self.DLQ_RETRY_SCHEDULE, dlq_id)
            await self.redis.decr(self.DLQ_STATS_TOTAL)

            # Update metrics
            dlq_retries_total.labels(result="success").inc()
            elapsed = (datetime.now(UTC) - start_time).total_seconds()
            dlq_retry_latency_seconds.observe(elapsed)
            await self._update_queue_size_metric()

            logger.info(
                "dlq_retry_success",
                dlq_id=dlq_id,
                retry_count=retry_count,
                latency_seconds=elapsed,
            )

            return True

        except Exception as e:
            logger.error(
                "dlq_retry_failed",
                dlq_id=dlq_id,
                retry_count=retry_count,
                error=str(e),
            )

            # Increment retry count
            new_retry_count = retry_count + 1

            if new_retry_count >= self.max_retries:
                # Max retries exceeded - move to permanent failure
                await self._mark_permanent_failure(dlq_id, dlq_data, e)
                dlq_retries_total.labels(result="max_retries_exceeded").inc()
                return False
            else:
                # Reschedule with new backoff
                backoff_seconds = self.retry_backoff_base * (2**new_retry_count)
                retry_at = datetime.now(UTC) + timedelta(seconds=backoff_seconds)

                # Update retry count and retry_at
                dlq_data["retry_count"] = new_retry_count
                dlq_data["retry_at"] = retry_at.isoformat()
                dlq_data["last_retry_at"] = datetime.now(UTC).isoformat()

                # Update Redis hash
                await self.redis.hset(
                    message_key, mapping={k: json.dumps(v) for k, v in dlq_data.items()}
                )

                # Update retry schedule
                retry_timestamp = retry_at.timestamp()
                await self.redis.zadd(self.DLQ_RETRY_SCHEDULE, {dlq_id: retry_timestamp})

                dlq_retries_total.labels(result="failure").inc()

                logger.info(
                    "dlq_retry_rescheduled",
                    dlq_id=dlq_id,
                    retry_count=new_retry_count,
                    retry_at=retry_at.isoformat(),
                    backoff_seconds=backoff_seconds,
                )

                return False

    async def _mark_permanent_failure(
        self, dlq_id: str, dlq_data: Dict[str, Any], error: Exception
    ) -> None:
        """
        Mark message as permanent failure and store in PostgreSQL.

        Args:
            dlq_id: DLQ entry ID
            dlq_data: DLQ entry data
            error: Latest exception
        """
        logger.warning(
            "dlq_permanent_failure",
            dlq_id=dlq_id,
            retry_count=dlq_data["retry_count"],
            error_type=type(error).__name__,
        )

        # Create DLQEntry for PostgreSQL
        # Ensure datetimes are naive UTC for SQLAlchemy/Postgres TIMESTAMP WITHOUT TIME ZONE
        first_failed_dt = datetime.fromisoformat(dlq_data["first_failed_at"])
        if first_failed_dt.tzinfo is not None:
            first_failed_dt = first_failed_dt.astimezone(UTC).replace(tzinfo=None)

        dlq_entry = DLQEntry(
            id=dlq_id,
            message_data=dlq_data["message"],
            error_message=str(error),
            error_traceback=dlq_data.get("error_traceback", ""),
            error_type=type(error).__name__,
            retry_count=dlq_data["retry_count"],
            first_failed_at=first_failed_dt,
            last_retry_at=datetime.utcnow(),
        )

        # Save to database
        self.db.add(dlq_entry)
        await self.db.commit()

        # Remove from Redis
        message_key = f"{self.DLQ_MESSAGE_PREFIX}{dlq_id}"
        await self.redis.delete(message_key)
        await self.redis.zrem(self.DLQ_RETRY_SCHEDULE, dlq_id)
        await self.redis.decr(self.DLQ_STATS_TOTAL)

        # Update metrics
        dlq_permanent_failures_total.labels(reason=dlq_data["error_type"]).inc()
        await self._update_queue_size_metric()

    async def get_queue_size(self) -> int:
        """Get current size of DLQ."""
        total = await self.redis.get(self.DLQ_STATS_TOTAL)
        return int(total) if total else 0

    async def get_oldest_message_age(self) -> Optional[float]:
        """Get age of oldest message in seconds."""
        # Get message with smallest score (earliest retry_at)
        oldest = await self.redis.zrange(self.DLQ_RETRY_SCHEDULE, 0, 0, withscores=True)
        if not oldest:
            return None

        dlq_id, retry_timestamp = oldest[0]
        dlq_id_str = dlq_id.decode("utf-8") if isinstance(dlq_id, bytes) else dlq_id

        message_key = f"{self.DLQ_MESSAGE_PREFIX}{dlq_id_str}"
        dlq_data_raw = await self.redis.hgetall(message_key)

        if not dlq_data_raw:
            return None

        dlq_data = {
            k.decode("utf-8"): json.loads(v.decode("utf-8")) for k, v in dlq_data_raw.items()
        }

        first_failed_at = datetime.fromisoformat(dlq_data["first_failed_at"])
        age_seconds = (datetime.now(UTC) - first_failed_at).total_seconds()
        return age_seconds

    async def cleanup_expired_messages(self) -> int:
        """
        Clean up expired messages from DLQ (called periodically by worker).

        Returns:
            int: Number of messages cleaned up
        """
        current_timestamp = datetime.now(UTC).timestamp()
        ttl_cutoff = current_timestamp - self.ttl_seconds

        # Get all messages older than TTL
        expired_ids = await self.redis.zrangebyscore(
            self.DLQ_RETRY_SCHEDULE, min=0, max=ttl_cutoff
        )

        count = 0
        for dlq_id in expired_ids:
            dlq_id_str = dlq_id.decode("utf-8") if isinstance(dlq_id, bytes) else dlq_id
            message_key = f"{self.DLQ_MESSAGE_PREFIX}{dlq_id_str}"

            # Delete from Redis
            await self.redis.delete(message_key)
            await self.redis.zrem(self.DLQ_RETRY_SCHEDULE, dlq_id_str)
            await self.redis.decr(self.DLQ_STATS_TOTAL)
            count += 1

        if count > 0:
            dlq_messages_expired_total.inc(count)
            logger.info("dlq_expired_messages_cleaned", count=count)

        return count

    async def _update_queue_size_metric(self):
        """Update Prometheus gauge for queue size."""
        size = await self.get_queue_size()
        dlq_queue_size.set(size)

        # Update oldest message age
        age = await self.get_oldest_message_age()
        if age is not None:
            dlq_oldest_message_age_seconds.set(age)


# Singleton instance (initialized in app lifespan)
_dlq_service: Optional[DLQService] = None


async def get_dlq_service() -> DLQService:
    """Get DLQ service singleton."""
    if _dlq_service is None:
        raise RuntimeError("DLQ service not initialized. Call init_dlq_service() first.")
    return _dlq_service


async def init_dlq_service(redis_client: redis.Redis, db_session: AsyncSession) -> DLQService:
    """Initialize DLQ service singleton."""
    global _dlq_service
    _dlq_service = DLQService(
        redis_client=redis_client,
        db_session=db_session,
        max_retries=settings.DLQ_MAX_RETRIES,
        retry_backoff_base=settings.DLQ_RETRY_BACKOFF_BASE,
        ttl_days=settings.DLQ_TTL_DAYS,
    )
    logger.info(
        "dlq_service_initialized",
        max_retries=settings.DLQ_MAX_RETRIES,
        backoff_base=settings.DLQ_RETRY_BACKOFF_BASE,
        ttl_days=settings.DLQ_TTL_DAYS,
    )
    return _dlq_service
