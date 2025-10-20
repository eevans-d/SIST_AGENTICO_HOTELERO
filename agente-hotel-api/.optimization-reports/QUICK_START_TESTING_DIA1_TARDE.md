# 🚀 QUICK START - TESTING DÍA 1 TARDE

**Objetivo**: Validar 4 bloqueantes implementados  
**Timeline**: 2-3 horas  
**Next Deadline**: DÍA 2 mañana (9:00 AM)

---

## ⚡ QUICK COMMANDS

```bash
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api

# 1. Setup (if needed)
poetry install --all-extras

# 2. Tests
pytest tests/unit/test_lock_service.py -v  # Quick validation
pytest tests/ -v --cov=app                  # Full test suite

# 3. Linting
ruff check app/ --fix                       # Auto-fix lint issues
ruff format app/                            # Format code

# 4. Security
gitleaks detect --report-path gitleaks-report.json

# 5. Manual Testing
# See validation scenarios below
```

---

## 📋 VALIDACIÓN MANUAL

### Test 1: Tenant Isolation

**Objetivo**: Verificar que user de un tenant no puede acceder datos de otro

```python
# En tests/integration/test_bloqueante1_tenant_isolation.py
# (Crear este test)

async def test_tenant_isolation_prevents_cross_tenant():
    gateway = MessageGateway()
    
    # Simulación: user_A from tenant_A
    payload = {
        "sender_id": "user_A",
        "tenant_id": "tenant_A",
        "channel": "whatsapp",
        # ... rest of payload
    }
    
    # Este debería pasar (user belongs to tenant)
    unified = await gateway.normalize_message(payload)
    assert unified.tenant_id == "tenant_A"
    
    # Simulación: attacker from tenant_A claiming to be user_B (tenant_B)
    payload_attack = {
        "sender_id": "user_B",  # belongs to tenant_B
        "tenant_id": "tenant_A",  # but claims tenant_A
        "channel": "whatsapp",
    }
    
    # Este debería fallar (DB validation will reject)
    with pytest.raises(TenantIsolationError):
        await gateway.normalize_message(payload_attack)
```

**Run**:
```bash
pytest tests/integration/test_bloqueante1_tenant_isolation.py -v
```

---

### Test 2: Metadata Whitelist

**Objetivo**: Verificar que keys maliciosas se rechazan

```python
# En tests/unit/test_bloqueante2_metadata.py
# (Crear este test)

def test_metadata_whitelist_rejects_admin():
    gateway = MessageGateway()
    
    raw_metadata = {
        "admin": True,              # ❌ Malicious
        "bypass_validation": True,  # ❌ Malicious
        "subject": "Hello",         # ✅ Allowed
    }
    
    filtered = gateway._filter_metadata(raw_metadata)
    
    assert "admin" not in filtered
    assert "bypass_validation" not in filtered
    assert "subject" in filtered
    assert filtered["subject"] == "Hello"


def test_metadata_size_limit():
    gateway = MessageGateway()
    
    raw_metadata = {
        "user_context": "x" * 5000,  # ❌ Too long (> 1000)
    }
    
    filtered = gateway._filter_metadata(raw_metadata)
    
    assert "user_context" not in filtered  # Should be dropped
```

**Run**:
```bash
pytest tests/unit/test_bloqueante2_metadata.py -v
```

---

### Test 3: Channel Spoofing

**Objetivo**: Verificar que channel spoofing se detecta

```python
# En tests/unit/test_bloqueante3_channel_spoofing.py
# (Crear este test)

def test_channel_spoofing_detection():
    gateway = MessageGateway()
    
    # Attacker claims SMS but sent to WhatsApp endpoint
    with pytest.raises(ChannelSpoofingError):
        gateway._validate_channel_not_spoofed(
            claimed_channel="sms",
            actual_channel="whatsapp"
        )


def test_channel_validation_passes():
    gateway = MessageGateway()
    
    # Valid: channels match
    # Should NOT raise exception
    gateway._validate_channel_not_spoofed(
        claimed_channel="whatsapp",
        actual_channel="whatsapp"
    )


def test_channel_not_claimed_passes():
    gateway = MessageGateway()
    
    # Valid: if channel not claimed, skip validation
    gateway._validate_channel_not_spoofed(
        claimed_channel=None,
        actual_channel="whatsapp"
    )
```

**Run**:
```bash
pytest tests/unit/test_bloqueante3_channel_spoofing.py -v
```

---

### Test 4: Stale Cache

**Objetivo**: Verificar que cache stale se marca correctamente

```python
# En tests/integration/test_bloqueante4_stale_cache.py
# (Crear este test)

async def test_stale_cache_marking_on_error():
    redis_client = await get_redis()
    adapter = QloAppsAdapter(redis_client)
    
    # 1. Warm cache with fresh data
    check_in = date(2025, 10, 25)
    check_out = date(2025, 10, 26)
    
    # Mock PMS to return data
    with patch.object(adapter.qloapps, 'check_availability') as mock_pms:
        mock_pms.return_value = [
            {"room_id": "101", "price": 100}
        ]
        
        data1 = await adapter.check_availability(check_in, check_out)
        assert data1[0]["potentially_stale"] == False  # or not present
    
    # 2. Simulate PMS error
    with patch.object(adapter.qloapps, 'check_availability') as mock_pms:
        mock_pms.side_effect = PMSError("PMS Down")
        
        # Should return stale data with marker
        data2 = await adapter.check_availability(check_in, check_out)
        
        assert data2[0]["potentially_stale"] == True
        assert data2[0]["room_id"] == "101"  # Old data


async def test_stale_cache_expires_in_60s():
    redis_client = await get_redis()
    adapter = QloAppsAdapter(redis_client)
    
    check_in = date(2025, 10, 25)
    check_out = date(2025, 10, 26)
    cache_key = f"availability:{check_in}:{check_out}:1:any"
    stale_key = f"{cache_key}:stale"
    
    # Warm cache
    with patch.object(adapter.qloapps, 'check_availability') as mock_pms:
        mock_pms.return_value = [{"room_id": "101", "price": 100}]
        await adapter.check_availability(check_in, check_out)
    
    # Simulate error (marks as stale)
    with patch.object(adapter.qloapps, 'check_availability') as mock_pms:
        mock_pms.side_effect = PMSError("PMS Down")
        await adapter.check_availability(check_in, check_out)
    
    # Check stale marker exists
    stale_marker = await redis_client.get(stale_key)
    assert stale_marker is not None
    
    # Check TTL is ~60s
    ttl = await redis_client.ttl(stale_key)
    assert 50 < ttl <= 60
```

**Run**:
```bash
pytest tests/integration/test_bloqueante4_stale_cache.py -v
```

---

## 🧪 TESTING SEQUENCE

### Step 1: Unit Tests (30 min)
```bash
pytest tests/unit/ -v --tb=short
```

Expected: All pass ✅

### Step 2: Integration Tests (30 min)
```bash
pytest tests/integration/ -v --tb=short
```

Expected: All pass ✅ (Bloqueante tests will be new)

### Step 3: Full Suite (20 min)
```bash
pytest tests/ -v --cov=app --cov-report=html
```

Expected: Coverage increase, no failures

### Step 4: Lint Check (10 min)
```bash
ruff check app/
```

Expected: No errors (use --fix to auto-correct)

### Step 5: Security Scan (10 min)
```bash
gitleaks detect --report-path gitleaks-report.json
```

Expected: No new secrets detected

---

## 🔍 MANUAL VALIDATION

### Bloqueante 1: Tenant Isolation

**Paso 1**: Check logs para validar tenant validation
```bash
grep -r "tenant_isolation" logs/
```

Expected: `tenant_isolation_validation_passed` entries

**Paso 2**: Simular webhook
```bash
curl -X POST http://localhost:8002/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=valid_sig" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "id": "msg1",
            "from": "1234567890",
            "type": "text",
            "text": {"body": "hello"}
          }]
        }
      }]
    }]
  }'
```

Expected: 200 OK, message processed

---

### Bloqueante 2: Metadata Whitelist

**Paso 1**: Check logs para dropped keys
```bash
grep -r "metadata_keys_dropped" logs/
```

**Paso 2**: Simular injection
```bash
curl -X POST http://localhost:8002/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=valid_sig" \
  -d '{
    "metadata": {
      "admin": true,
      "bypass": true,
      "subject": "OK"
    },
    "entry": [...]
  }'
```

Expected: admin/bypass dropped, subject kept (in logs)

---

### Bloqueante 3: Channel Spoofing

**Paso 1**: Check para ChannelSpoofingError
```bash
grep -r "channel_spoofing_attempt" logs/
```

**Paso 2**: Simular spoofing (SMS claiming WhatsApp)
```bash
# This should fail in real implementation
# when channel validation is in place
```

---

### Bloqueante 4: Stale Cache

**Paso 1**: Force PMS failure
```bash
# Stop PMS mock or real service
docker-compose stop qloapps  # if using real PMS
```

**Paso 2**: Check availability
```bash
curl -X POST http://localhost:8002/api/check-availability \
  -H "Content-Type: application/json" \
  -d '{
    "check_in": "2025-10-25",
    "check_out": "2025-10-26"
  }'
```

Expected: 
- Response includes `"potentially_stale": true`
- Warning log: "using stale cache"

**Paso 3**: Wait 60s and retry
```bash
# After 60s, stale marker should expire
# Next error should not mark as stale (no cache)
```

---

## 📊 SUCCESS CRITERIA

| Bloqueante | Unit Test | Integration Test | Manual Test | Status |
|-----------|-----------|-----------------|------------|--------|
| 1 (Tenant) | ✅ PASS | ✅ PASS | ✅ PASS | GO |
| 2 (Metadata) | ✅ PASS | ✅ PASS | ✅ PASS | GO |
| 3 (Channel) | ✅ PASS | ✅ PASS | ✅ PASS | GO |
| 4 (Cache) | ✅ PASS | ✅ PASS | ✅ PASS | GO |

**All Must Pass**: ✅ YES → Ready for DÍA 2

---

## 🛑 TROUBLESHOOTING

### Test Fails: "ImportError: cannot import name ..."
**Solution**: 
```bash
poetry install --all-extras
pytest --cache-clear
```

### Test Fails: "Connection refused"
**Solution**: Make sure services are running
```bash
docker-compose up -d
sleep 5
pytest tests/integration/
```

### Linting Errors
**Solution**: Auto-fix
```bash
ruff check app/ --fix
ruff format app/
```

---

## 📝 REPORTING

### Create Summary Report
```bash
cat > /tmp/testing_report.txt << 'EOF'
DÍA 1 TARDE - TESTING SUMMARY
==============================

Unit Tests: PASS/FAIL
Integration Tests: PASS/FAIL
Linting: PASS/FAIL
Security: PASS/FAIL

Bloqueantes Status:
  1 (Tenant Isolation): READY/PENDING DB
  2 (Metadata Whitelist): READY
  3 (Channel Spoofing): READY
  4 (Stale Cache): READY

Next Steps: [List pending items]
EOF
```

---

## ✅ SIGN-OFF

When all tests pass:

```bash
# 1. Create test summary
cat > TESTING_SUMMARY_DIA1_TARDE.txt

# 2. Commit status
git status

# 3. Next phase confirmation
echo "✅ TESTING COMPLETE - READY FOR DÍA 2"
```

---

**Timeline**: DÍA 1 Tarde (2-3 horas)  
**Next**: DÍA 2 Integration Testing  
**Final**: DÍA 3 Merge + Deploy

¡Empecemos! 🚀
