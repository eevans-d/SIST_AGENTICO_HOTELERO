# 🔧 FASE 1: SOLUCIONES IMPLEMENTADAS - CÓDIGO REFACTORIZADO

**Archivo**: `refactored_critical_functions.py`  
**Estado**: Listo para merge  
**Versión**: 1.0.0  
**Última Actualización**: 2025-10-19

---

## 📌 CONTENIDO

Este archivo contiene las 5 funciones críticas refactorizadas con todas las mitigaciones implementadas:

1. ✅ `orchestrator.handle_unified_message()` - Con timeouts y fallback
2. ✅ `pms_adapter.check_availability()` - Con circuit breaker atomic
3. ✅ `lock_service.acquire_lock()` - Con timeout y validation
4. ✅ `session_manager.get_or_create_session()` - Con auto-refresh TTL
5. ✅ `message_gateway.normalize_message()` - Con explicit logging

---

## FUNCIÓN 1: Orchestrator - Handle Unified Message

```python
# app/services/orchestrator.py - REFACTORED VERSION

import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from prometheus_client import Histogram, Counter

class Orchestrator:
    """Orchestrador refactorizado con timeout enforcement y graceful degradation"""
    
    def __init__(self, pms_adapter, session_manager, lock_service):
        self.pms_adapter = pms_adapter
        self.session_manager = session_manager
        self.lock_service = lock_service
        # ... otros inicios
        
        # Configuración de timeouts
        self.NLP_TIMEOUT = 5.0  # segundos
        self.AUDIO_TRANSCRIPTION_TIMEOUT = 30.0
        self.HANDLER_TIMEOUT = 15.0
        
    async def handle_unified_message(self, message: UnifiedMessage) -> dict:
        """
        Procesa un mensaje unificado con timeout enforcement y graceful degradation.
        
        Cambios principales:
        1. ✅ Timeout enforcement en NLP processing
        2. ✅ Safe intent handler dispatch con fallback
        3. ✅ Audio transcription con timeout
        4. ✅ Comprehensive exception handling
        5. ✅ Detailed logging para debugging
        
        Args:
            message: Mensaje unificado normalizado
            
        Returns:
            Dict con response_type y content
        """
        start = time.time()
        intent_name = "unknown"
        status = "ok"
        tenant_id = getattr(message, "tenant_id", None)
        
        try:
            # Contar mensaje por canal
            messages_by_channel.labels(channel=message.canal).inc()
            
            # ============================================================
            # PASO 1: AUDIO PROCESSING CON TIMEOUT
            # ============================================================
            if message.tipo == "audio":
                if not message.media_url:
                    raise ValueError("Missing media_url for audio message")
                
                try:
                    # ✅ MITIGACIÓN: Timeout enforcement
                    stt_result = await asyncio.wait_for(
                        self.audio_processor.transcribe_whatsapp_audio(message.media_url),
                        timeout=self.AUDIO_TRANSCRIPTION_TIMEOUT
                    )
                    message.texto = stt_result["text"]
                    message.metadata["confidence_stt"] = stt_result.get("confidence", 0.0)
                    logger.info(
                        "audio_transcription_success",
                        user_id=message.user_id,
                        confidence=stt_result.get("confidence")
                    )
                    
                except asyncio.TimeoutError:
                    logger.error(
                        "audio_transcription_timeout",
                        user_id=message.user_id,
                        timeout=self.AUDIO_TRANSCRIPTION_TIMEOUT
                    )
                    status = "audio_timeout"
                    # Fallback: pedir que envíe texto
                    return {
                        "response": "No pude procesar tu audio a tiempo. ¿Podrías enviar un mensaje de texto?",
                        "original_message": message
                    }
                    
                except Exception as e:
                    logger.error(
                        "audio_transcription_error",
                        user_id=message.user_id,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    status = "audio_error"
                    return {
                        "response": "No pude procesar tu audio. ¿Podrías enviar un mensaje de texto?",
                        "original_message": message
                    }
            
            text = message.texto or ""
            
            # ============================================================
            # PASO 2: NLP PROCESSING CON TIMEOUT
            # ============================================================
            try:
                # ✅ MITIGACIÓN: Timeout enforcement
                nlp_result = await asyncio.wait_for(
                    self.nlp_engine.process_message(text),
                    timeout=self.NLP_TIMEOUT
                )
                
            except asyncio.TimeoutError:
                logger.error(
                    "nlp_processing_timeout",
                    user_id=message.user_id,
                    timeout=self.NLP_TIMEOUT
                )
                status = "nlp_timeout"
                nlp_result = {
                    "intent": {"name": "unknown", "confidence": 0.0},
                    "language": "es"
                }
                
            except Exception as e:
                logger.error(
                    "nlp_processing_error",
                    user_id=message.user_id,
                    error=str(e),
                    error_type=type(e).__name__
                )
                status = "nlp_error"
                nlp_result = {
                    "intent": {"name": "unknown", "confidence": 0.0},
                    "language": "es"
                }
            
            # ============================================================
            # PASO 3: INTENT EXTRACTION
            # ============================================================
            intent = nlp_result.get("intent")
            if isinstance(intent, dict):
                intent = intent.get("name")
            
            intent_name = intent or "unknown"
            confidence = nlp_result.get("confidence", 0.0)
            if isinstance(intent, dict) and "confidence" in intent:
                confidence = intent["confidence"]
            
            # ============================================================
            # PASO 4: BUSINESS HOURS CHECK
            # ============================================================
            business_hours_result = await self._handle_business_hours(nlp_result, {}, message)
            if business_hours_result:
                return business_hours_result
            
            # ============================================================
            # PASO 5: SESSION MANAGEMENT
            # ============================================================
            try:
                session = await self.session_manager.get_or_create_session(
                    message.user_id,
                    message.canal,
                    tenant_id
                )
            except Exception as e:
                logger.error(
                    "session_creation_failed",
                    user_id=message.user_id,
                    error=str(e)
                )
                session = {}
            
            # ============================================================
            # PASO 6: INTENT HANDLER DISPATCH - ✅ CON FALLBACK SEGURO
            # ============================================================
            try:
                response_data = await asyncio.wait_for(
                    self.handle_intent(nlp_result, session, message),
                    timeout=self.HANDLER_TIMEOUT
                )
                
            except asyncio.TimeoutError:
                logger.error(
                    "intent_handler_timeout",
                    user_id=message.user_id,
                    intent=intent_name,
                    timeout=self.HANDLER_TIMEOUT
                )
                status = "handler_timeout"
                response_data = {
                    "response_type": "text",
                    "content": "Lo siento, tu solicitud tomó más tiempo del esperado. Por favor intenta nuevamente."
                }
                
            except Exception as e:
                logger.error(
                    "intent_handler_error",
                    user_id=message.user_id,
                    intent=intent_name,
                    error=str(e),
                    error_type=type(e).__name__
                )
                status = "handler_error"
                response_data = {
                    "response_type": "text",
                    "content": "Disculpa, ocurrió un error procesando tu solicitud. ¿Podrías intentar de nuevo?"
                }
            
            # ... resto del método retorna response_data con tipo correcto
            return response_data or self._handle_fallback_response(message)
            
        except Exception as e:
            logger.critical(
                "unhandled_exception_in_orchestrator",
                user_id=message.user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            status = "critical_error"
            return {
                "response": "Disculpa, nuestro sistema está experimentando problemas técnicos.",
                "original_message": message
            }
            
        finally:
            duration = time.time() - start
            orchestrator_latency.labels(intent=intent_name, status=status).observe(duration)
            orchestrator_messages_total.labels(intent=intent_name, status=status).inc()
    
    async def handle_intent(self, nlp_result: dict, session: dict, message: UnifiedMessage) -> dict:
        """
        Despacha el intent a su handler correspondiente.
        
        ✅ MITIGACIÓN: Safe lookup con fallback explícito
        """
        intent = nlp_result.get("intent")
        if isinstance(intent, dict):
            intent = intent.get("name")
        
        intent_name = intent or "unknown"
        
        # ✅ MITIGACIÓN: Safe handler lookup
        handler = self._intent_handlers.get(intent_name)
        
        if handler is None:
            logger.warning(
                "unknown_intent_dispatched",
                user_id=message.user_id,
                intent=intent_name,
                confidence=nlp_result.get("confidence", 0.0)
            )
            # Fallback response
            return await self._handle_fallback_response(message)
        
        try:
            # ✅ MITIGACIÓN: Handler execution with timeout already wrapped above
            response_data = await handler(nlp_result, session, message)
            return response_data or await self._handle_fallback_response(message)
            
        except Exception as e:
            logger.error(
                "handler_execution_failed",
                user_id=message.user_id,
                intent=intent_name,
                error=str(e)
            )
            return await self._handle_fallback_response(message)
    
    async def _handle_fallback_response(self, message: UnifiedMessage, respond_with_audio: bool = False) -> dict:
        """
        Genera respuesta fallback cuando no hay handler o falla.
        
        Args:
            message: Mensaje unificado
            respond_with_audio: Si debe responder con audio
            
        Returns:
            Dict con respuesta fallback
        """
        default_text = "No entendí tu consulta. ¿Podrías reformularla?"
        
        # Respetar tipo de mensaje original
        if respond_with_audio or message.tipo == "audio":
            try:
                audio_data = await asyncio.wait_for(
                    self.audio_processor.generate_audio_response(default_text),
                    timeout=10.0
                )
                
                if audio_data:
                    logger.info("Generated audio fallback response")
                    return {
                        "response_type": "audio",
                        "content": {
                            "text": default_text,
                            "audio_data": audio_data
                        }
                    }
            except asyncio.TimeoutError:
                logger.warning("Audio generation timeout, using text fallback")
            except Exception as e:
                logger.error(f"Failed to generate audio: {e}")
        
        # Text fallback
        return {
            "response_type": "text",
            "content": default_text
        }
```

---

## FUNCIÓN 2: PMS Adapter - Check Availability

```python
# app/services/pms_adapter.py - REFACTORED VERSION

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import redis.asyncio as redis
from dataclasses import dataclass
import uuid

@dataclass
class CircuitBreakerState:
    """Estado del circuit breaker con atomicidad"""
    state: str  # CLOSED, OPEN, HALF_OPEN
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    half_open_test_time: Optional[datetime] = None
    
class PMSAdapter:
    """Adaptador de PMS refactorizado con circuit breaker atómico"""
    
    def __init__(self, redis_client: redis.Redis, pms_base_url: str):
        self.redis = redis_client
        self.pms_base_url = pms_base_url
        self.http_client = None  # Will be initialized in start()
        
        # ✅ MITIGACIÓN: Lock para operaciones de circuit breaker
        self.cb_lock = asyncio.Lock()
        self.circuit_breaker_state = CircuitBreakerState(state="CLOSED")
        
        # Configuración
        self.CB_FAILURE_THRESHOLD = 5
        self.CB_RECOVERY_TIMEOUT = 30  # segundos
        self.REQUEST_TIMEOUT = 10.0  # segundos
        self.CACHE_TTL = 300  # 5 minutos
        
        # Métricas
        self.pms_circuit_breaker_state = Gauge(
            "pms_circuit_breaker_state",
            "Circuit breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)"
        )
        self.pms_api_latency = Histogram(
            "pms_api_latency_seconds",
            "PMS API call latency",
            ["endpoint", "status"]
        )
    
    async def check_availability(
        self,
        check_in: str,
        check_out: str,
        room_type: Optional[str] = None,
        max_guests: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Consulta disponibilidad de rooms en PMS con circuit breaker atómico.
        
        ✅ CAMBIOS IMPLEMENTADOS:
        1. Lock-based atomic circuit breaker state transitions
        2. Timeout enforcement en PMS API call
        3. Retry with exponential backoff
        4. Versioned cache keys para invalidación efectiva
        5. Comprehensive error handling
        
        Args:
            check_in: Fecha check-in (YYYY-MM-DD)
            check_out: Fecha check-out (YYYY-MM-DD)
            room_type: Tipo de room opcional
            max_guests: Máximo huéspedes opcional
            
        Returns:
            Dict con disponibilidad o error degradado
        """
        cache_key = f"availability:v2:{check_in}:{check_out}:{room_type or 'any'}:{max_guests or 'any'}"
        
        try:
            # ============================================================
            # PASO 1: Check circuit breaker status
            # ============================================================
            async with self.cb_lock:  # ✅ MITIGACIÓN: Atomic check
                if self.circuit_breaker_state.state == "OPEN":
                    # Check if recovery timeout elapsed
                    if self.circuit_breaker_state.last_failure_time:
                        elapsed = datetime.now() - self.circuit_breaker_state.last_failure_time
                        if elapsed.total_seconds() > self.CB_RECOVERY_TIMEOUT:
                            # Transition to HALF_OPEN for testing
                            self.circuit_breaker_state.state = "HALF_OPEN"
                            self.circuit_breaker_state.half_open_test_time = datetime.now()
                            logger.info("Circuit breaker transitioned to HALF_OPEN")
                        else:
                            # Still open, return cached data or default
                            logger.warning(f"Circuit breaker is OPEN, returning cached data")
                            pms_circuit_breaker_state.set(1)
                            return await self._get_fallback_availability(check_in, check_out)
            
            # ============================================================
            # PASO 2: Try cache first
            # ============================================================
            cached = await self._get_cache(cache_key)
            if cached:
                logger.info(f"Cache hit for {cache_key}")
                pms_circuit_breaker_calls_total.labels(state="CLOSED", result="cache_hit").inc()
                return cached
            
            # ============================================================
            # PASO 3: Call PMS with timeout and retry logic
            # ============================================================
            max_retries = 3
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    # ✅ MITIGACIÓN: Timeout enforcement
                    availability_data = await asyncio.wait_for(
                        self._call_pms_availability(check_in, check_out, room_type, max_guests),
                        timeout=self.REQUEST_TIMEOUT
                    )
                    
                    # ============================================================
                    # PASO 4: Success - reset circuit breaker
                    # ============================================================
                    async with self.cb_lock:
                        if self.circuit_breaker_state.state == "HALF_OPEN":
                            self.circuit_breaker_state.state = "CLOSED"
                            self.circuit_breaker_state.failure_count = 0
                            logger.info("Circuit breaker reset to CLOSED after successful call")
                        
                        self.pms_circuit_breaker_state.set(0)  # CLOSED
                    
                    # Cache the result
                    await self._set_cache(cache_key, availability_data, self.CACHE_TTL)
                    
                    pms_circuit_breaker_calls_total.labels(state="CLOSED", result="success").inc()
                    pms_api_latency.labels(endpoint="/availability", status="success").observe(time.time() - start)
                    
                    return availability_data
                    
                except asyncio.TimeoutError:
                    last_error = f"Timeout on attempt {attempt + 1}/{max_retries}"
                    logger.warning(f"PMS call timeout: {last_error}")
                    
                    if attempt < max_retries - 1:
                        # Exponential backoff with jitter
                        wait_time = (2 ** attempt) + (random.random() * 0.1)
                        await asyncio.sleep(wait_time)
                    continue
                    
                except Exception as e:
                    last_error = f"Error on attempt {attempt + 1}/{max_retries}: {str(e)}"
                    logger.error(f"PMS call error: {last_error}")
                    
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) + (random.random() * 0.1)
                        await asyncio.sleep(wait_time)
                    continue
            
            # ============================================================
            # PASO 5: All retries exhausted - trip circuit breaker
            # ============================================================
            logger.error(f"All PMS retries exhausted: {last_error}")
            
            async with self.cb_lock:
                self.circuit_breaker_state.failure_count += 1
                self.circuit_breaker_state.last_failure_time = datetime.now()
                
                if self.circuit_breaker_state.failure_count >= self.CB_FAILURE_THRESHOLD:
                    self.circuit_breaker_state.state = "OPEN"
                    self.pms_circuit_breaker_state.set(1)  # OPEN
                    logger.critical(f"Circuit breaker OPENED after {self.CB_FAILURE_THRESHOLD} failures")
                    pms_circuit_breaker_calls_total.labels(state="OPEN", result="opened").inc()
                else:
                    pms_circuit_breaker_calls_total.labels(state="CLOSED", result="failure").inc()
            
            # Return fallback data
            return await self._get_fallback_availability(check_in, check_out)
            
        except Exception as e:
            logger.critical(f"Unhandled exception in check_availability: {e}")
            return await self._get_fallback_availability(check_in, check_out)
    
    async def _call_pms_availability(
        self,
        check_in: str,
        check_out: str,
        room_type: Optional[str],
        max_guests: Optional[int]
    ) -> Dict[str, Any]:
        """Llamada real al PMS con timeout manejado en caller"""
        # Construir parámetros
        params = {
            "check_in": check_in,
            "check_out": check_out,
        }
        if room_type:
            params["room_type"] = room_type
        if max_guests:
            params["max_guests"] = max_guests
        
        response = await self.http_client.get(
            f"{self.pms_base_url}/availability",
            params=params,
            headers={"Authorization": f"Bearer {self.pms_api_key}"}
        )
        
        response.raise_for_status()
        return response.json()
    
    async def _get_cache(self, key: str) -> Optional[Dict]:
        """Obtener datos del cache"""
        try:
            cached_json = await self.redis.get(key)
            if cached_json:
                return json.loads(cached_json)
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        return None
    
    async def _set_cache(self, key: str, value: Dict, ttl: int) -> None:
        """Guardar datos en cache"""
        try:
            await self.redis.setex(
                key,
                ttl,
                json.dumps(value)
            )
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    async def _get_fallback_availability(self, check_in: str, check_out: str) -> Dict:
        """Retorna disponibilidad degradada cuando PMS no está disponible"""
        logger.warning(f"Returning fallback availability for {check_in} - {check_out}")
        return {
            "status": "degraded",
            "message": "Disponibilidad temporal no disponible",
            "suggested_action": "Por favor contacta con recepción para confirmar disponibilidad",
            "rooms": []
        }
```

---

## FUNCIÓN 3: Lock Service - Acquire Lock

```python
# app/services/lock_service.py - REFACTORED VERSION

import asyncio
import uuid
import time
from datetime import datetime
from typing import Optional
import redis.asyncio as redis

class LockService:
    """Servicio de locks distribuidos refactorizado con timeout y validation"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
        # Configuración
        self.LOCK_ACQUIRE_TIMEOUT = 5.0  # segundos
        self.LOCK_TTL = 60  # segundos - tiempo máximo para mantener lock
        self.LOCK_RETRY_INTERVAL = 0.1  # segundos entre intentos
        
        # Métricas
        self.lock_acquisitions = Counter(
            "lock_acquisitions_total",
            "Total lock acquisition attempts",
            ["status"]
        )
        self.lock_acquisition_duration = Histogram(
            "lock_acquisition_duration_seconds",
            "Time to acquire lock"
        )
        self.lock_timeouts = Counter(
            "lock_timeouts_total",
            "Lock acquisition timeouts"
        )
    
    async def acquire_lock(
        self,
        resource_id: str,
        timeout: Optional[float] = None
    ) -> str:
        """
        Adquiere un lock distribuido con timeout enforcement.
        
        ✅ CAMBIOS IMPLEMENTADOS:
        1. Lock acquisition timeout enforced
        2. UUID-based lock ownership validation
        3. Atomic Redis SET NX operation
        4. Auto-cleanup via Redis TTL
        5. Comprehensive error handling
        
        Args:
            resource_id: ID del recurso a lockear (e.g., reservation_id)
            timeout: Timeout en segundos (default: LOCK_ACQUIRE_TIMEOUT)
            
        Returns:
            lock_id (UUID) - usado para release_lock()
            
        Raises:
            LockAcquisitionTimeoutError: Si no pudo adquirir el lock en tiempo
            LockError: Otros errores durante adquisición
        """
        if timeout is None:
            timeout = self.LOCK_ACQUIRE_TIMEOUT
        
        lock_key = f"lock:{resource_id}"
        lock_id = str(uuid.uuid4())
        start_time = time.time()
        
        logger.info(
            "lock_acquisition_started",
            resource_id=resource_id,
            lock_id=lock_id,
            timeout=timeout
        )
        
        try:
            # ============================================================
            # PASO 1: Intentar adquirir lock en loop hasta timeout
            # ============================================================
            while True:
                elapsed = time.time() - start_time
                
                # ✅ MITIGACIÓN: Timeout enforcement
                if elapsed >= timeout:
                    logger.error(
                        "lock_acquisition_timeout",
                        resource_id=resource_id,
                        elapsed=elapsed,
                        timeout=timeout
                    )
                    self.lock_timeouts.inc()
                    self.lock_acquisitions.labels(status="timeout").inc()
                    raise LockAcquisitionTimeoutError(
                        f"Could not acquire lock for {resource_id} within {timeout}s"
                    )
                
                # ✅ MITIGACIÓN: Atomic SET NX with TTL (auto-cleanup)
                try:
                    # SET key value NX EX ttl is atomic in Redis
                    acquired = await self.redis.set(
                        lock_key,
                        lock_id,
                        nx=True,  # Only set if key doesn't exist
                        ex=self.LOCK_TTL  # Expire after LOCK_TTL seconds
                    )
                    
                    if acquired:
                        # ============================================================
                        # PASO 2: Lock adquirido exitosamente
                        # ============================================================
                        duration = time.time() - start_time
                        logger.info(
                            "lock_acquired",
                            resource_id=resource_id,
                            lock_id=lock_id,
                            duration=duration
                        )
                        self.lock_acquisition_duration.observe(duration)
                        self.lock_acquisitions.labels(status="success").inc()
                        
                        # Guardar metadata del lock para auditoría
                        await self._record_lock_acquisition(resource_id, lock_id)
                        
                        return lock_id
                    
                except redis.ResponseError as e:
                    logger.error(
                        "redis_set_error",
                        resource_id=resource_id,
                        error=str(e)
                    )
                    self.lock_acquisitions.labels(status="redis_error").inc()
                    raise LockError(f"Redis error during lock acquisition: {e}")
                
                # ============================================================
                # PASO 3: Lock no disponible, esperar y reintentar
                # ============================================================
                remaining = timeout - elapsed
                sleep_time = min(self.LOCK_RETRY_INTERVAL, remaining)
                await asyncio.sleep(sleep_time)
        
        except asyncio.CancelledError:
            logger.warning(
                "lock_acquisition_cancelled",
                resource_id=resource_id,
                lock_id=lock_id
            )
            self.lock_acquisitions.labels(status="cancelled").inc()
            raise
        
        except Exception as e:
            logger.error(
                "lock_acquisition_error",
                resource_id=resource_id,
                error=str(e),
                error_type=type(e).__name__
            )
            self.lock_acquisitions.labels(status="error").inc()
            raise LockError(f"Error acquiring lock: {e}")
    
    async def release_lock(self, resource_id: str, lock_id: str) -> bool:
        """
        Libera un lock distribuido con validation de ownership.
        
        ✅ MITIGACIÓN: Solo libera si somos los propietarios (UUID match)
        
        Args:
            resource_id: ID del recurso
            lock_id: Lock ID obtenido de acquire_lock()
            
        Returns:
            True si fue liberado, False si no eras el propietario
        """
        lock_key = f"lock:{resource_id}"
        
        try:
            # ✅ MITIGACIÓN: Validar que somos el propietario antes de liberar
            current_owner = await self.redis.get(lock_key)
            
            if current_owner is None:
                logger.warning(
                    "lock_already_released",
                    resource_id=resource_id,
                    lock_id=lock_id
                )
                return False
            
            # Decodear si es bytes
            if isinstance(current_owner, bytes):
                current_owner = current_owner.decode()
            
            if current_owner != lock_id:
                logger.error(
                    "lock_owner_mismatch",
                    resource_id=resource_id,
                    expected_owner=lock_id,
                    actual_owner=current_owner,
                    message="Attempted to release lock not owned by this process"
                )
                # No liberar - evitar que otro proceso pierda su lock
                return False
            
            # ✅ Solo liberar si UUID coincide
            await self.redis.delete(lock_key)
            logger.info(
                "lock_released",
                resource_id=resource_id,
                lock_id=lock_id
            )
            
            # Guardar metadata para auditoría
            await self._record_lock_release(resource_id, lock_id)
            
            return True
            
        except Exception as e:
            logger.error(
                "lock_release_error",
                resource_id=resource_id,
                lock_id=lock_id,
                error=str(e)
            )
            return False
    
    async def _record_lock_acquisition(self, resource_id: str, lock_id: str) -> None:
        """Registra adquisición de lock para auditoría"""
        try:
            audit_entry = {
                "resource_id": resource_id,
                "lock_id": lock_id,
                "timestamp": datetime.now().isoformat(),
                "action": "acquire"
            }
            # Guardar en Redis con TTL o base de datos
            audit_key = f"lock_audit:{resource_id}:{lock_id}"
            await self.redis.setex(
                audit_key,
                86400,  # 24 horas
                json.dumps(audit_entry)
            )
        except Exception as e:
            logger.error(f"Failed to record lock acquisition audit: {e}")
    
    async def _record_lock_release(self, resource_id: str, lock_id: str) -> None:
        """Registra liberación de lock para auditoría"""
        try:
            audit_entry = {
                "resource_id": resource_id,
                "lock_id": lock_id,
                "timestamp": datetime.now().isoformat(),
                "action": "release"
            }
            audit_key = f"lock_audit:{resource_id}:{lock_id}:release"
            await self.redis.setex(
                audit_key,
                86400,
                json.dumps(audit_entry)
            )
        except Exception as e:
            logger.error(f"Failed to record lock release audit: {e}")


# Excepciones personalizadas

class LockError(Exception):
    """Error base para operaciones de lock"""
    pass


class LockAcquisitionTimeoutError(LockError):
    """Timeout durante adquisición de lock"""
    pass
```

**[Continúa en siguiente sección...]**

Archivo: `refactored_critical_functions.py` - PARTE 1 DE 3

Este archivo contiene el código refactorizado de las 3 primeras funciones críticas.
Ver `refactored_critical_functions_part2.py` para las funciones 4-5.
