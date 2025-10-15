# Runbook: WhatsApp API Outage

**Severity**: HIGH  
**SLA**: 1 hour to mitigation  
**On-Call**: Backend Team + Integrations Team

---

## Symptoms

- WhatsApp webhook not receiving messages
- Cannot send WhatsApp messages
- 401/403/500 errors from Meta API
- Metric: `whatsapp_api_errors_total` increasing

## Detection

```promql
# WhatsApp API error rate
rate(whatsapp_api_calls_total{status="error"}[5m]) > 0.1

# Webhook not receiving messages
rate(whatsapp_messages_received_total[10m]) == 0
```

## Impact Assessment

- **User Impact**: Cannot communicate via WhatsApp
- **Business Impact**: Lost customer interactions, manual intervention needed
- **Alternative Channels**: Gmail still available

---

## Immediate Actions (0-10 minutes)

### 1. Verify WhatsApp API Status

```bash
# Check Meta API status page
open https://developers.facebook.com/status/

# Test WhatsApp API manually
curl -X GET "https://graph.facebook.com/v18.0/me/phone_numbers" \
  -H "Authorization: Bearer $WHATSAPP_ACCESS_TOKEN"

# Check recent errors
docker logs agente-api | grep "WhatsApp" | tail -50
```

### 2. Check API Credentials

```bash
# Verify token is set
docker exec agente-api env | grep WHATSAPP_ACCESS_TOKEN

# Test token validity
curl -X GET "https://graph.facebook.com/v18.0/debug_token?input_token=$WHATSAPP_ACCESS_TOKEN" \
  -H "Authorization: Bearer $WHATSAPP_APP_TOKEN"

# Check token expiration
docker logs agente-api | grep "token\|401\|403"
```

### 3. Quick Mitigation - Switch to Alternate Channel

```bash
# Enable Gmail fallback
docker exec agente-api python -c "
from app.services.feature_flag_service import get_feature_flag_service
import asyncio
async def enable_gmail():
    ff = await get_feature_flag_service()
    await ff.set_flag('channels.gmail.priority', True)
asyncio.run(enable_gmail())
"

# Notify users
echo "WhatsApp temporarily unavailable. Please use email: hotel@example.com"
```

---

## Investigation (10-60 minutes)

### Check Common Causes

#### A. Meta API Outage

```bash
# Check Meta status
curl https://www.facebook.com/ -I

# Check recent Meta incidents
open https://developers.facebook.com/status/dashboard/

# Test alternate endpoint
curl -X GET "https://graph.facebook.com/v18.0/$PHONE_NUMBER_ID" \
  -H "Authorization: Bearer $WHATSAPP_ACCESS_TOKEN"
```

#### B. Access Token Expired/Revoked

```bash
# Check token info
curl -X GET \
  "https://graph.facebook.com/v18.0/debug_token?input_token=$WHATSAPP_ACCESS_TOKEN" \
  -H "Authorization: Bearer $WHATSAPP_APP_TOKEN" | jq .

# Check for token rotation needed
docker logs agente-api | grep "token.*expir"

# Generate new token (if expired)
open https://business.facebook.com/settings/whatsapp-business-accounts/
```

#### C. Webhook Verification Failed

```bash
# Check webhook configuration
curl -X GET "https://graph.facebook.com/v18.0/$WHATSAPP_APP_ID/subscriptions" \
  -H "Authorization: Bearer $WHATSAPP_ACCESS_TOKEN"

# Test webhook endpoint
curl -X GET "https://yourapp.example.com/webhook/whatsapp?hub.mode=subscribe&hub.challenge=test&hub.verify_token=$WEBHOOK_VERIFY_TOKEN"

# Check NGINX logs
docker logs nginx | grep webhook | tail -20
```

#### D. Rate Limiting

```bash
# Check for rate limit headers
curl -I -X POST "https://graph.facebook.com/v18.0/$PHONE_NUMBER_ID/messages" \
  -H "Authorization: Bearer $WHATSAPP_ACCESS_TOKEN"

# Check rate limit metrics
curl 'http://localhost:9090/api/v1/query?query=
  rate(whatsapp_api_calls_total[5m])
'

# Review API usage
docker logs agente-api | grep "429\|rate.*limit" | wc -l
```

#### E. Phone Number Blocked/Suspended

```bash
# Check phone number status
curl -X GET "https://graph.facebook.com/v18.0/$PHONE_NUMBER_ID" \
  -H "Authorization: Bearer $WHATSAPP_ACCESS_TOKEN" | jq .

# Check for quality violations
open https://business.facebook.com/wa/manage/phone-numbers/

# Review recent quality metrics
docker logs agente-api | grep "quality\|blocked\|suspended"
```

---

## Resolution Steps

### Option 1: Refresh Access Token

```bash
# Generate new long-lived token
# Go to: https://business.facebook.com/settings/whatsapp-business-accounts/
# Navigate to: Your App > WhatsApp > API Setup
# Click: "Get Access Token"

# Update token in environment
vi agente-hotel-api/.env
# WHATSAPP_ACCESS_TOKEN=new_token_here

# Restart service
docker-compose restart agente-api

# Test with new token
curl -X GET "https://graph.facebook.com/v18.0/me" \
  -H "Authorization: Bearer $NEW_TOKEN"
```

### Option 2: Re-register Webhook

```bash
# Delete old webhook subscription
curl -X DELETE \
  "https://graph.facebook.com/v18.0/$WHATSAPP_APP_ID/subscriptions" \
  -H "Authorization: Bearer $WHATSAPP_ACCESS_TOKEN"

# Register new webhook
curl -X POST \
  "https://graph.facebook.com/v18.0/$WHATSAPP_APP_ID/subscriptions" \
  -H "Authorization: Bearer $WHATSAPP_ACCESS_TOKEN" \
  -d "object=whatsapp_business_account" \
  -d "callback_url=https://yourapp.example.com/webhook/whatsapp" \
  -d "verify_token=$WEBHOOK_VERIFY_TOKEN" \
  -d "fields=messages"

# Verify registration
curl -X GET "https://graph.facebook.com/v18.0/$WHATSAPP_APP_ID/subscriptions" \
  -H "Authorization: Bearer $WHATSAPP_ACCESS_TOKEN"
```

### Option 3: Switch WhatsApp Phone Number

```bash
# If primary number blocked, use backup
vi agente-hotel-api/.env
# WHATSAPP_PHONE_NUMBER_ID=backup_number_id

# Restart service
docker-compose restart agente-api

# Update webhook for new number
# Follow steps in Option 2
```

### Option 4: Implement Retry Logic with Exponential Backoff

```python
# app/services/whatsapp_client.py
async def send_message(self, to: str, message: str, retry_count: int = 3):
    for attempt in range(retry_count):
        try:
            response = await self._send_message_api(to, message)
            return response
        except Exception as e:
            if attempt < retry_count - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"WhatsApp send failed, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                # Fallback to email after all retries
                await self.gmail_client.send_message(to, message)
                raise
```

---

## Validation

### 1. Test Message Sending

```bash
# Send test message
curl -X POST http://localhost:8000/api/v1/messages/send \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "whatsapp",
    "to": "+1234567890",
    "message": "Test message from runbook"
  }'

# Check logs
docker logs -f agente-api | grep "WhatsApp"
```

### 2. Test Webhook Reception

```bash
# Send test message from WhatsApp to your number
# Check webhook logs
docker logs nginx | grep webhook | tail -10
docker logs agente-api | grep "Received WhatsApp message"

# Verify message processing
curl http://localhost:8000/admin/messages/recent | jq .
```

### 3. Check Metrics

```bash
# Message send success rate
curl 'http://localhost:9090/api/v1/query?query=
  rate(whatsapp_messages_sent_total{status="success"}[5m]) /
  rate(whatsapp_messages_sent_total[5m])
'

# Webhook receive rate
curl 'http://localhost:9090/api/v1/query?query=
  rate(whatsapp_messages_received_total[5m])
'
```

---

## Communication Template

**Initial Alert**:
```
⚠️ INCIDENT: WhatsApp API Outage
Severity: HIGH
Status: INVESTIGATING
Impact: Cannot send/receive WhatsApp messages
Workaround: Using email channel for communications
ETA: Investigating, update in 30 minutes
```

**Update**:
```
📊 WHATSAPP OUTAGE UPDATE
Root Cause: [Meta API issue/Token expired/etc.]
Actions: [Token refreshed/Webhook re-registered/etc.]
Progress: [Test messages successful/Still investigating]
Alternative: Email channel operational
```

**Resolution**:
```
✅ RESOLVED: WhatsApp API Restored
Duration: XX minutes
Root Cause: [Detailed explanation]
Fix: [Token refreshed/Configuration updated/etc.]
Validation: Sending and receiving tested successfully
Backlog: XX messages queued, processing now
```

---

## Post-Incident

### 1. Review Message Queue

```bash
# Check for queued messages
docker exec redis-agente redis-cli LLEN whatsapp_message_queue

# Process backlog
curl -X POST http://localhost:8000/admin/messages/process-queue

# Monitor processing
watch -n 5 'docker exec redis-agente redis-cli LLEN whatsapp_message_queue'
```

### 2. Implement Automatic Failover

```python
# app/services/message_gateway.py
async def send_message(self, message: UnifiedMessage):
    try:
        # Try WhatsApp first
        return await self.whatsapp_client.send_message(message)
    except WhatsAppAPIError as e:
        logger.warning(f"WhatsApp failed: {e}, falling back to email")
        # Automatic fallback to email
        return await self.gmail_client.send_message(message)
```

### 3. Add Token Monitoring

```python
# app/routers/health.py
@router.get("/health/whatsapp")
async def whatsapp_health():
    # Check token validity
    token_valid = await whatsapp_client.verify_token()
    # Check API connectivity
    api_reachable = await whatsapp_client.ping()
    
    return {
        "token_valid": token_valid,
        "api_reachable": api_reachable,
        "status": "healthy" if token_valid and api_reachable else "degraded"
    }
```

### 4. Action Items

- [ ] Set up token expiration alerts (7 days before)
- [ ] Implement automatic token rotation
- [ ] Add backup WhatsApp phone number
- [ ] Create WhatsApp health check endpoint
- [ ] Set up Meta API status monitoring
- [ ] Document token generation process
- [ ] Test failover to email quarterly

---

## Prevention

- **Monitoring**: Token expiration checks daily
- **Alerting**: Alert 7 days before token expiry
- **Failover**: Automatic fallback to email
- **Testing**: Monthly WhatsApp integration tests
- **Backup**: Secondary phone number configured

## WhatsApp SLA Targets

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Message Delivery | > 99% | < 98% | < 95% |
| Webhook Latency | < 1s | > 3s | > 5s |
| API Error Rate | < 0.1% | > 1% | > 5% |
| Token Validity | 60+ days | 7 days | Expired |

## Related Runbooks

- [05-pms-integration-failure.md](./05-pms-integration-failure.md)
- [08-high-error-rate.md](./08-high-error-rate.md)

---

**Last Updated**: 2024-10-15  
**Owner**: Integrations Team  
**Reviewers**: Backend Team, Meta Business Team
