# Phase E.2 - WhatsApp Real Client Implementation

## 🎯 Objective
Implement complete WhatsApp Business API integration with Meta Cloud API v18.0, including media handling, templates, signature verification, and comprehensive error handling.

## 📋 Current State Analysis

### Existing Implementation
- ✅ Basic WhatsAppMetaClient class
- ✅ Simple send_message() method
- ✅ HTTP client with timeouts and limits
- ⚠️  Incomplete download_media() (pass statement)
- ❌ No template message support
- ❌ No webhook signature verification
- ❌ No rate limiting específico de WhatsApp
- ❌ No comprehensive error handling
- ❌ No tests

### Settings Available
- whatsapp_access_token (SecretStr)
- whatsapp_phone_number_id (str)
- whatsapp_verify_token (SecretStr)
- whatsapp_app_secret (SecretStr)

## 🔧 Tasks Breakdown

### Task 1: Complete Media Download Implementation (30 min)
**File**: `app/services/whatsapp_client.py`
**Requirements**:
- Implement download_media() with 2-step process:
  1. GET media URL from media_id
  2. Download actual file from URL
- Support audio formats (ogg, opus, mp3, wav)
- Add timeout handling (30s max per step)
- Structured logging for media operations
- Error handling (MediaNotFoundError, MediaDownloadError)

### Task 2: Implement Template Message Sending (30 min)
**File**: `app/services/whatsapp_client.py`
**Requirements**:
- Add send_template_message() method
- Support template parameters (header, body, footer)
- Support button components
- Validate template structure
- Handle rate limits (1000 msg/day Business API)
- Structured logging

### Task 3: Webhook Signature Verification (20 min)
**File**: `app/services/whatsapp_client.py`
**Requirements**:
- Add verify_webhook_signature() method
- HMAC-SHA256 signature validation
- Use whatsapp_app_secret from settings
- Timing-safe comparison
- Detailed error logging

### Task 4: Enhanced Error Handling (20 min)
**File**: `app/exceptions/whatsapp_exceptions.py` (NEW)
**Requirements**:
- Create exception hierarchy:
  - WhatsAppError (base)
  - WhatsAppAuthError (401, 403)
  - WhatsAppRateLimitError (429)
  - WhatsAppMediaError (media issues)
  - WhatsAppTemplateError (template issues)
- HTTP status code mapping
- Structured error context

### Task 5: Rate Limiting & Monitoring (20 min)
**File**: `app/services/whatsapp_client.py`
**Requirements**:
- Add rate limit tracking (Redis-backed)
- Prometheus metrics:
  - whatsapp_messages_sent_total{type=text|template|media}
  - whatsapp_media_downloads_total{status=success|error}
  - whatsapp_api_latency_seconds{endpoint}
  - whatsapp_rate_limit_remaining
- Circuit breaker for repeated failures

### Task 6: Webhook Validation in Router (30 min)
**File**: `app/routers/webhooks.py`
**Requirements**:
- Add signature verification to POST /webhooks/whatsapp
- Validate webhook structure
- Handle hub.challenge for verification
- Add specific logging for WhatsApp events
- Error responses with proper status codes

### Task 7: Integration Tests (45 min)
**File**: `tests/integration/test_whatsapp_integration.py` (NEW)
**Requirements**:
- TestWhatsAppClient (8+ tests):
  - test_send_message_success
  - test_send_message_auth_error
  - test_download_media_success
  - test_download_media_not_found
  - test_send_template_message
  - test_verify_signature_valid
  - test_verify_signature_invalid
  - test_rate_limit_tracking
- Mock httpx responses
- Fixture for client instance

### Task 8: E2E Tests (30 min)
**File**: `tests/e2e/test_whatsapp_e2e.py` (NEW)
**Requirements**:
- Test complete flow: Webhook → Process → Response
- Test audio message flow: Webhook → Download → STT → NLP → Response
- Test template message flow
- Mock WhatsApp API responses

### Task 9: Documentation (30 min)
**File**: `PROJECT_GUIDE.md`
**Requirements**:
- New section: "## 📱 WhatsApp Business API Setup"
- Prerequisites (Meta Business Account, App setup)
- Configuration (.env variables)
- Webhook verification process
- Template message examples
- Rate limiting documentation
- Error handling guide
- Monitoring/logging patterns

## 📊 Success Criteria

✅ **Functionality**:
- [ ] Media download working (audio files)
- [ ] Template messages sending
- [ ] Webhook signature verification
- [ ] Rate limiting enforced
- [ ] Circuit breaker operational

✅ **Testing**:
- [ ] 8+ integration tests passing
- [ ] 2+ E2E tests passing
- [ ] Mock WhatsApp API responses
- [ ] No type errors

✅ **Documentation**:
- [ ] PROJECT_GUIDE.md updated (150+ lines)
- [ ] Error handling documented
- [ ] Rate limits documented
- [ ] Examples provided

✅ **Observability**:
- [ ] Structured logging (whatsapp.*)
- [ ] Prometheus metrics (4+ new metrics)
- [ ] Error tracking
- [ ] Performance monitoring

## 📈 Expected Impact

### Metrics Before E.2:
- Quality Score: 9.6/10
- Test Coverage: 48 tests
- WhatsApp Features: Basic (text only)
- Code Completeness: ~90%

### Metrics After E.2:
- Quality Score: 9.7/10 ⬆️ (+0.1)
- Test Coverage: 60+ tests ⬆️ (+12 tests, +25%)
- WhatsApp Features: Complete (text, media, templates) ⬆️
- Code Completeness: ~95% ⬆️ (+5%)

## ⏱️ Timeline

| Task | Duration | Status |
|------|----------|--------|
| 1. Media Download | 30 min | 🔜 NEXT |
| 2. Template Messages | 30 min | ⏳ PENDING |
| 3. Webhook Signature | 20 min | ⏳ PENDING |
| 4. Error Handling | 20 min | ⏳ PENDING |
| 5. Rate Limiting | 20 min | ⏳ PENDING |
| 6. Webhook Validation | 30 min | ⏳ PENDING |
| 7. Integration Tests | 45 min | ⏳ PENDING |
| 8. E2E Tests | 30 min | ⏳ PENDING |
| 9. Documentation | 30 min | ⏳ PENDING |
| **TOTAL** | **3h 45min** | **0%** |

## 🚀 Execution Start

Date: October 5, 2025 04:20 UTC
Priority: HIGH (Critical communication channel)
Next Action: Task 1 - Media Download Implementation
