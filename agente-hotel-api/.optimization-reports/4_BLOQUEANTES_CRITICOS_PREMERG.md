# 🔴 4 BLOQUEANTES: FIXES CRÍTICOS PRE-MERGE

**Prioridad**: CRÍTICA  
**Esfuerzo**: 5.5 horas  
**Deadlines**: 1-2 días  

---

## 📍 BLOQUEANTE 1: TENANT ISOLATION VALIDATION

**Ubicación**: `refactored_critical_functions_part2.py:normalize_message()`  
**Severidad**: 🔴 CRÍTICA (Data Leak Risk)  
**Risk**: Multi-tenant data confusion  

### El Problema

```python
# ACTUAL (INSEGURO):
async def normalize_message(self, raw_payload: dict) -> UnifiedMessage:
    tenant_id = await self._resolve_tenant_dynamic(user_id)
    if not tenant_id:
        tenant_id = self.default_tenant_id  # Silent fallback!
    
    # No validation that user_id belongs to tenant_id
    return UnifiedMessage(user_id=user_id, tenant_id=tenant_id)

# ESCENARIO DE ATAQUE:
# 1. Attacker en tenant_A
# 2. Adivina user_id de guest en tenant_B (e.g., "user_123")
# 3. Envía mensaje con:
#    - channel: "whatsapp"
#    - sender_id: "user_123"  (belongs to tenant_B)
#    - Pero a través de tenant_A webhook
# 4. El sistema normaliza sin validar tenant_id ← SEGURIDAD ROTA
# 5. Attacker accede datos de tenant_B
```

### La Solución

```python
async def normalize_message(self, raw_payload: dict) -> UnifiedMessage:
    """Normalize with tenant isolation validation"""
    
    user_id = raw_payload.get("sender_id")
    channel = raw_payload.get("channel")
    
    # ✅ 1. Resolve tenant (existing logic)
    tenant_id = await self._resolve_tenant_dynamic(user_id, channel)
    if not tenant_id:
        tenant_id = self.default_tenant_id
    
    # ✅ 2. NUEVO: Validate user belongs to tenant
    # Query DB to verify user_id is under this tenant
    user_tenant = await self.db.execute(
        select(TenantUserIdentifier.tenant_id)
        .where(
            (TenantUserIdentifier.user_id == user_id) &
            (TenantUserIdentifier.channel == channel)
        )
    )
    
    if user_tenant and user_tenant != tenant_id:
        logger.error(
            "tenant_isolation_violation",
            user_id=user_id,
            expected_tenant=tenant_id,
            actual_tenant=user_tenant,
            correlation_id=raw_payload.get("correlation_id")
        )
        # Reject message - do not process
        raise TenantIsolationError(
            f"User {user_id} does not belong to tenant {tenant_id}"
        )
    
    logger.info(
        "tenant_validation_passed",
        user_id=user_id,
        tenant_id=tenant_id,
        correlation_id=raw_payload.get("correlation_id")
    )
    
    return UnifiedMessage(
        user_id=user_id,
        tenant_id=tenant_id,
        canal=channel
    )
```

### Checklist de Implementación

- [ ] Agregar validación en `normalize_message()`
- [ ] Agregar excepción `TenantIsolationError`
- [ ] Test: User A tries to access User B's data → Should reject
- [ ] Test: User A accesses own data → Should accept
- [ ] Monitor: Log all rejection events
- [ ] **Tiempo**: ~2 horas

### Validación

```bash
# Test 1: Valid case
curl -X POST /webhook/whatsapp \
  -H "X-User-ID: user_from_tenant_A" \
  -d '{"sender_id": "user_from_tenant_A", "channel": "whatsapp"}'
# Resultado esperado: ✅ 200 OK

# Test 2: Tenant confusion attack
curl -X POST /webhook/whatsapp \
  -H "X-User-ID: user_from_tenant_A" \
  -d '{"sender_id": "user_from_tenant_B", "channel": "whatsapp"}'
# Resultado esperado: ❌ 403 Forbidden + TenantIsolationError log
```

---

## 📍 BLOQUEANTE 2: METADATA WHITELIST

**Ubicación**: `refactored_critical_functions_part2.py:normalize_message()`  
**Severidad**: 🔴 CRÍTICA (Injection Attack Risk)  
**Risk**: Attacker injects malicious metadata  

### El Problema

```python
# ACTUAL (INSEGURO):
async def normalize_message(self, raw_payload: dict) -> UnifiedMessage:
    metadata = raw_payload.get("metadata", {})
    
    # ❌ Copiar metadata directamente sin validación
    return UnifiedMessage(
        ...,
        metadata=metadata  # Attacker controls ALL keys!
    )

# ESCENARIO DE ATAQUE:
raw_payload = {
    "sender_id": "user_123",
    "channel": "whatsapp",
    "metadata": {
        "admin": True,                    # ← Malicious!
        "bypass_validation": True,        # ← Malicious!
        "override_tenant_id": "admin",    # ← Malicious!
        "role": "system"                  # ← Malicious!
    }
}

# Sin validación, todo entra en metadata
# Downstream code podría: if message.metadata.get("admin"): grant_access()
```

### La Solución

```python
# Define allowed metadata keys
ALLOWED_METADATA_KEYS = {
    "user_context",         # User-specific context
    "custom_fields",        # Custom data from CRM
    "source",              # Message source (webhook, API, etc)
    "external_request_id",  # External tracking ID
    "language_hint",        # User preferred language
}

async def normalize_message(self, raw_payload: dict) -> UnifiedMessage:
    """Normalize with metadata whitelist validation"""
    
    # Get metadata from payload
    raw_metadata = raw_payload.get("metadata", {})
    
    # ✅ Filter: only keep whitelisted keys
    filtered_metadata = {
        key: value
        for key, value in raw_metadata.items()
        if key in ALLOWED_METADATA_KEYS
    }
    
    # ✅ Log if unexpected keys were dropped
    unexpected_keys = set(raw_metadata.keys()) - ALLOWED_METADATA_KEYS
    if unexpected_keys:
        logger.warning(
            "metadata_keys_dropped",
            dropped_keys=list(unexpected_keys),
            correlation_id=raw_payload.get("correlation_id"),
            user_id=raw_payload.get("sender_id")
        )
    
    # ✅ Validate metadata value types
    for key, value in filtered_metadata.items():
        if not isinstance(value, (str, int, float, bool, type(None))):
            logger.error(
                "metadata_value_type_invalid",
                key=key,
                type=type(value).__name__
            )
            del filtered_metadata[key]
    
    # ✅ Validate metadata value sizes (prevent DoS)
    for key, value in filtered_metadata.items():
        if isinstance(value, str) and len(value) > 1000:
            logger.warning(
                "metadata_value_too_long",
                key=key,
                length=len(value)
            )
            filtered_metadata[key] = value[:1000]
    
    return UnifiedMessage(
        ...,
        metadata=filtered_metadata  # ✅ Only safe metadata
    )
```

### Checklist de Implementación

- [ ] Define `ALLOWED_METADATA_KEYS` constant
- [ ] Agregar filtering logic en `normalize_message()`
- [ ] Agregar validation de tipos
- [ ] Agregar size limits
- [ ] Test: Inject admin metadata → Should be dropped
- [ ] Test: Valid metadata → Should be preserved
- [ ] Monitor: Log dropped keys for detection of attacks
- [ ] **Tiempo**: ~1 hora

### Validación

```bash
# Test 1: Valid metadata (only allowed keys)
curl -X POST /webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "user_123",
    "metadata": {
      "user_context": "customer",
      "language_hint": "es"
    }
  }'
# Resultado: ✅ Metadata preserved

# Test 2: Injection attack (malicious keys)
curl -X POST /webhook/whatsapp \
  -d '{
    "sender_id": "user_123",
    "metadata": {
      "admin": true,
      "bypass_validation": true,
      "user_context": "customer"
    }
  }'
# Resultado: ✅ Malicious keys dropped, user_context preserved
# Log: ⚠️ "metadata_keys_dropped" (contains: admin, bypass_validation)
```

---

## 📍 BLOQUEANTE 3: CHANNEL SPOOFING PROTECTION

**Ubicación**: `refactored_critical_functions_part2.py:normalize_message()`  
**Severidad**: 🔴 CRÍTICA (Message Authenticity)  
**Risk**: Attacker fakes message channel  

### El Problema

```python
# ACTUAL (INSEGURO):
async def normalize_message(self, raw_payload: dict) -> UnifiedMessage:
    # ❌ Channel from payload (attacker-controlled)
    channel = raw_payload.get("channel")
    
    # If channel is used for:
    # - Rate limiting per channel
    # - Message routing logic
    # - Vendor-specific behavior
    # Then attacker can bypass controls

# ESCENARIO DE ATAQUE:
# 1. Attacker sends SMS via whatsapp endpoint
# raw_payload = {
#     "channel": "sms",               # ← Claimed (attacker lies)
#     "sender_id": "user_123",
#     "texto": "URGENT_BROADCAST"
# }
# 2. Sistema cree que es SMS, pero llegó por WhatsApp webhook
# 3. SMS tiene rate limits diferentes, attacker bypassa
# 4. Broadcasting falsos SMSes
```

### La Solución

```python
async def normalize_message(
    self, 
    raw_payload: dict,
    request_source: str  # ← From webhook endpoint, NOT from payload
) -> UnifiedMessage:
    """Normalize with channel spoofing protection"""
    
    # Map request source to actual channel
    REQUEST_SOURCE_TO_CHANNEL = {
        "webhook_whatsapp": "whatsapp",
        "webhook_gmail": "gmail",
        "webhook_sms": "sms",
        "api_internal": "internal",
    }
    
    # ✅ Get actual channel from request source
    actual_channel = REQUEST_SOURCE_TO_CHANNEL.get(request_source)
    if not actual_channel:
        logger.error(
            "unknown_request_source",
            source=request_source
        )
        raise ValueError(f"Unknown request source: {request_source}")
    
    # ✅ Get claimed channel from payload
    claimed_channel = raw_payload.get("channel")
    
    # ✅ Verify they match
    if claimed_channel and claimed_channel != actual_channel:
        logger.error(
            "channel_spoofing_attempt",
            claimed=claimed_channel,
            actual=actual_channel,
            user_id=raw_payload.get("sender_id"),
            correlation_id=raw_payload.get("correlation_id")
        )
        # Option 1: Reject
        raise ChannelSpoofingError(
            f"Claimed channel {claimed_channel} != actual {actual_channel}"
        )
        # Option 2: Override (safer, but logs the mismatch)
        # channel = actual_channel
    
    # ✅ Use actual channel, not claimed
    return UnifiedMessage(
        ...,
        canal=actual_channel  # ✅ From request source, not payload
    )
```

### Integration con FastAPI Routers

```python
# app/routers/webhooks.py

@router.post("/webhook/whatsapp")
async def webhook_whatsapp(payload: dict):
    """WhatsApp webhook endpoint"""
    # Pass request source explicitly
    message = await gateway.normalize_message(
        raw_payload=payload,
        request_source="webhook_whatsapp"  # ✅ Explicit source
    )
    return await orchestrator.handle_unified_message(message)

@router.post("/webhook/gmail")
async def webhook_gmail(payload: dict):
    """Gmail webhook endpoint"""
    message = await gateway.normalize_message(
        raw_payload=payload,
        request_source="webhook_gmail"  # ✅ Different source
    )
    return await orchestrator.handle_unified_message(message)
```

### Checklist de Implementación

- [ ] Agregar `request_source` parameter a `normalize_message()`
- [ ] Add `REQUEST_SOURCE_TO_CHANNEL` mapping
- [ ] Add validation logic
- [ ] Add `ChannelSpoofingError` exception
- [ ] Update all webhook endpoints to pass `request_source`
- [ ] Test: Send SMS payload to whatsapp endpoint → Should reject
- [ ] Test: Send valid payload to correct endpoint → Should accept
- [ ] **Tiempo**: ~1 hora

### Validación

```bash
# Test 1: Valid channel
curl -X POST http://localhost:8002/api/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "5511999999999",
    "channel": "whatsapp",
    "texto": "Hola"
  }'
# Resultado: ✅ 200 OK (channel matches endpoint)

# Test 2: Spoofing attempt
curl -X POST http://localhost:8002/api/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "user@gmail.com",
    "channel": "gmail",  # ← Claiming Gmail but sent to WhatsApp
    "texto": "Hola"
  }'
# Resultado: ❌ 400 Bad Request + ChannelSpoofingError
# Log: 🚨 "channel_spoofing_attempt"
```

---

## 📍 BLOQUEANTE 4: STALE CACHE MARKING

**Ubicación**: `refactored_critical_functions_part1.py:check_availability()`  
**Severidad**: 🔴 CRÍTICA (Data Staleness)  
**Risk**: Guests booked unavailable rooms due to stale cache  

### El Problema

```python
# ACTUAL (INSEGURO):
async def check_availability(self, check_in, check_out):
    cache_key = f"availability:{check_in}:{check_out}"
    
    try:
        response = await self._call_pms_with_retry(...)
        await cache.set(cache_key, response, ex=300)  # 5 min TTL
        return response
        
    except PMSError:
        # PMS down - use stale cache
        cached = await cache.get(cache_key)
        if cached:
            logger.warning("using_stale_cache")
            return cached  # ❌ No indication it's stale!
        raise

# ESCENARIO:
# T=0:00  Guest A checks availability → cache HIT
# T=0:05  PMS experiences outage (all rooms become unavailable)
# T=0:06  Guest B checks availability
# T=0:06  PMS timeout → Falls back to cache from T=0:00
# T=0:06  Guest B sees old data (rooms available) → Books room
# T=0:06  Confirmation sent, but room actually not available ← OVERBOOKING!
```

### La Solución

```python
async def check_availability(self, check_in, check_out):
    """Check availability with stale cache detection"""
    
    cache_key = f"availability:{check_in}:{check_out}"
    
    try:
        response = await self._call_pms_with_retry(...)
        
        # ✅ Success: Store fresh data
        await cache.set(cache_key, response, ex=300)
        
        # ✅ Clear stale marker if exists
        await cache.delete(f"{cache_key}:stale")
        
        logger.info(
            "availability_fresh",
            check_in=check_in,
            check_out=check_out,
            rooms_available=len(response.get("rooms", []))
        )
        
        return response
        
    except PMSError as e:
        logger.error("pms_call_failed", error=str(e))
        
        # Try cache with stale marker
        cached = await cache.get(cache_key)
        stale_marker = await cache.get(f"{cache_key}:stale")
        
        if cached and not stale_marker:
            # Cache exists and NOT marked stale yet
            logger.warning("using_cache_marking_stale")
            
            # ✅ Mark cache as potentially stale
            # Expires after 1 minute or when PMS recovers
            await cache.set(f"{cache_key}:stale", "true", ex=60)
            
            # ✅ Modify response to indicate staleness
            response_with_warning = cached.copy()
            response_with_warning["_cached"] = True
            response_with_warning["_stale_warning"] = (
                "Data may be outdated. PMS temporarily unavailable."
            )
            response_with_warning["_refresh_at"] = (
                datetime.utcnow() + timedelta(minutes=1)
            ).isoformat()
            
            return response_with_warning
        
        elif cached and stale_marker:
            # Cache marked stale for > 60 sec, reject it
            logger.error(
                "stale_cache_rejected",
                stale_duration=await cache.ttl(f"{cache_key}:stale")
            )
            raise PMSError("Data stale. Please retry after 1 minute.")
        
        else:
            # No cache available
            logger.error("no_cache_available")
            raise PMSError("PMS unavailable and no cache available")
```

### Frontend Handling

```python
# app/services/template_service.py

def render_availability_response(data):
    """Render availability with stale data warning"""
    
    if data.get("_cached"):
        warning_msg = data.get("_stale_warning", "")
        refresh_at = data.get("_refresh_at", "")
        
        # Include warning in response
        template = f"""
        ⚠️ {warning_msg}
        
        Disponibilidad:
        {format_rooms(data)}
        
        Actualización disponible en: {refresh_at}
        """
        return template
    
    else:
        # Fresh data - normal template
        template = f"""
        Disponibilidad:
        {format_rooms(data)}
        """
        return template
```

### Checklist de Implementación

- [ ] Add stale marker logic in `check_availability()`
- [ ] Modify response to include `_cached` and `_stale_warning`
- [ ] Update frontend to handle stale data warnings
- [ ] Add metrics: `stale_cache_served`, `stale_cache_rejected`
- [ ] Test: PMS timeout → Should serve cache with warning
- [ ] Test: Stale marker expires after 60s → Should reject
- [ ] Test: PMS recovers → Should clear stale marker
- [ ] **Tiempo**: ~1.5 horas

### Validación

```bash
# Scenario 1: Fresh data
curl http://localhost:8002/api/availability?check_in=2025-10-20&check_out=2025-10-22
# Resultado: {"rooms": [...], "_cached": false}

# Scenario 2: Cache serving (PMS down < 60s)
# (Simulate PMS error)
curl http://localhost:8002/api/availability?check_in=2025-10-20&check_out=2025-10-22
# Resultado: {"rooms": [...], "_cached": true, "_stale_warning": "..."}
# Log: ✅ "using_cache_marking_stale"

# Scenario 3: Cache stale (PMS down > 60s)
curl http://localhost:8002/api/availability?check_in=2025-10-20&check_out=2025-10-22
# Resultado: ❌ 503 Service Unavailable
# Error: "Data stale. Please retry after 1 minute."
```

---

## ✅ CHECKLIST PRE-MERGE COMPLETO

```
BLOQUEANTE 1: TENANT ISOLATION VALIDATION
┌─────────────────────────────────────────┐
│ □ Agregar validación en normalize_message()
│ □ Query DB: verificar user pertenece a tenant
│ □ Crear excepción TenantIsolationError
│ □ Test: tenant confusion attack → reject
│ □ Test: valid user → accept
│ □ Monitor: log all violations
│ Tiempo: 2 horas
└─────────────────────────────────────────┘

BLOQUEANTE 2: METADATA WHITELIST
┌─────────────────────────────────────────┐
│ □ Define ALLOWED_METADATA_KEYS
│ □ Filter en normalize_message()
│ □ Validate tipos (str, int, bool only)
│ □ Enforce size limits
│ □ Test: admin metadata → dropped
│ □ Test: valid metadata → preserved
│ □ Monitor: log dropped keys
│ Tiempo: 1 hora
└─────────────────────────────────────────┘

BLOQUEANTE 3: CHANNEL SPOOFING PROTECTION
┌─────────────────────────────────────────┐
│ □ Add request_source parameter
│ □ Define REQUEST_SOURCE_TO_CHANNEL map
│ □ Validate claimed vs actual
│ □ Create ChannelSpoofingError
│ □ Update webhook endpoints
│ □ Test: SMS to whatsapp → reject
│ □ Test: valid channel → accept
│ Tiempo: 1 hora
└─────────────────────────────────────────┘

BLOQUEANTE 4: STALE CACHE MARKING
┌─────────────────────────────────────────┐
│ □ Add stale marker logic
│ □ Modify response with _cached flag
│ □ Include _stale_warning in response
│ □ Set marker expiry 60 seconds
│ □ Update frontend handling
│ □ Add metrics exposition
│ □ Test: PMS down < 60s → stale warning
│ □ Test: PMS down > 60s → reject cache
│ Tiempo: 1.5 horas
└─────────────────────────────────────────┘

TOTAL PRE-MERGE: 5.5 HORAS
```

---

## 🚀 ORDEN DE IMPLEMENTACIÓN

### DÍA 1: Bloqueantes 1 & 2 (3 horas)

```bash
# 1. Tenant Isolation Validation (2h)
#    - Edit refactored_critical_functions_part2.py
#    - Add _validate_tenant_isolation() method
#    - Test with pytest

# 2. Metadata Whitelist (1h)
#    - Define ALLOWED_METADATA_KEYS
#    - Add filtering logic
#    - Quick test
```

### DÍA 2: Bloqueantes 3 & 4 (2.5 horas)

```bash
# 3. Channel Spoofing Protection (1h)
#    - Update routers
#    - Add request_source to normalize_message
#    - Test endpoints

# 4. Stale Cache Marking (1.5h)
#    - Edit refactored_critical_functions_part1.py
#    - Add stale marker logic
#    - Test scenarios
```

### DÍA 3: Testing + Review (1 hora)

```bash
# 1. Run full test suite
# 2. Security scan (gitleaks)
# 3. Code review
# 4. Ready for merge
```

---

**Resumen**: 4 bloqueantes críticos, 5.5 horas de trabajo, aplicables antes de merge.

Después de esto, el código es production-ready.
