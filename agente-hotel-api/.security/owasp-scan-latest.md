# 🔐 OWASP Top 10 2021 Validation Report - P013
**Scan Date**: 2025-10-17T04:18:28.593471
**Duration**: 33.45 seconds
**Compliance Score**: 0/100
**Status**: 🔴 **HIGH RISK**

## 📊 Summary

- **Total Findings**: 538

### By Severity

- **HIGH**: 300
- **CRITICAL**: 144
- **MEDIUM**: 94

### By OWASP Category

- **A01** (Broken Access Control): 134
- **A02** (Cryptographic Failures): 199
- **A03** (Injection): 16
- **A07** (Identification and Authentication Failures): 89
- **A08** (Software and Data Integrity Failures): 92
- **A09** (Security Logging and Monitoring Failures): 7
- **A10** (Server-Side Request Forgery): 1

## 🐛 Findings

### 1. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/performance.py`
- **Line**: 26
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/status")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 2. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/performance.py`
- **Line**: 72
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/metrics")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 3. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/performance.py`
- **Line**: 104
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/optimization/report")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 4. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/performance.py`
- **Line**: 121
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/optimization/execute")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 5. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/performance.py`
- **Line**: 163
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/database/report")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 6. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/performance.py`
- **Line**: 186
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/database/optimize")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 7. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/performance.py`
- **Line**: 232
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/cache/report")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 8. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/performance.py`
- **Line**: 256
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/cache/optimize")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 9. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/performance.py`
- **Line**: 310
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/scaling/status")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 10. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/performance.py`
- **Line**: 325
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/scaling/evaluate")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 11. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/performance.py`
- **Line**: 364
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/scaling/execute")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 12. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/performance.py`
- **Line**: 402
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.put("/scaling/rule/{service_name}/{rule_name}")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 13. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/performance.py`
- **Line**: 449
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/alerts")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 14. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/performance.py`
- **Line**: 490
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/alerts/{alert_id}/resolve")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 15. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/performance.py`
- **Line**: 519
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/benchmark")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 16. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/performance.py`
- **Line**: 561
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/recommendations")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 17. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/health.py`
- **Line**: 21
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/health", response_model=HealthCheck)`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 18. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/health.py`
- **Line**: 27
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/health/ready", response_model=ReadinessCheck)`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 19. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/health.py`
- **Line**: 86
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/health/live", response_model=LivenessCheck)`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 20. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/security.py`
- **Line**: 115
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/auth/register", response_model=Dict[str, Any])`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 21. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/security.py`
- **Line**: 158
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/auth/login", response_model=LoginResponse)`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 22. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/security.py`
- **Line**: 216
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/auth/refresh", response_model=Dict[str, Any])`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 23. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/security.py`
- **Line**: 250
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/auth/logout")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 24. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/security.py`
- **Line**: 289
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/mfa/setup", response_model=MFASetupResponse)`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 25. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/security.py`
- **Line**: 346
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/mfa/verify")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 26. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/security.py`
- **Line**: 395
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/mfa/disable")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 27. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/security.py`
- **Line**: 431
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/profile")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 28. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/security.py`
- **Line**: 455
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.put("/profile")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 29. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/security.py`
- **Line**: 484
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/change-password")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 30. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/security.py`
- **Line**: 537
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/events", response_model=List[SecurityEventResponse])`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 31. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/security.py`
- **Line**: 578
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/rate-limits/{ip}", response_model=RateLimitStatusResponse)`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 32. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/security.py`
- **Line**: 604
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/rate-limits/{ip}/whitelist")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 33. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/security.py`
- **Line**: 638
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/rate-limits/{ip}/blacklist")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 34. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/security.py`
- **Line**: 677
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/health")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 35. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/security.py`
- **Line**: 720
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/stats")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 36. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/webhooks.py`
- **Line**: 45
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/whatsapp")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 37. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/webhooks.py`
- **Line**: 359
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/gmail")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 38. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/pms.py`
- **Line**: 156
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/health")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 39. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/pms.py`
- **Line**: 175
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/availability/check")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 40. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/pms.py`
- **Line**: 241
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/reservations")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 41. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/pms.py`
- **Line**: 319
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/reservations/{reservation_id}")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 42. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/pms.py`
- **Line**: 365
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.put("/reservations/{reservation_id}")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 43. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/pms.py`
- **Line**: 419
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.delete("/reservations/{reservation_id}")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 44. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/pms.py`
- **Line**: 453
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/workflows/start")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 45. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/pms.py`
- **Line**: 481
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/workflows/{workflow_id}/step")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 46. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/pms.py`
- **Line**: 516
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/workflows/{workflow_id}/status")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 47. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/pms.py`
- **Line**: 535
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.delete("/workflows/{workflow_id}")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 48. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/pms.py`
- **Line**: 562
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/confirmations/send")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 49. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/pms.py`
- **Line**: 603
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/confirmations/{delivery_id}/status")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 50. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/nlp.py`
- **Line**: 129
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/message", response_model=MessageResponse)`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 51. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/nlp.py`
- **Line**: 186
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/conversation/{session_id}", response_model=ConversationSummaryResponse)`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 52. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/nlp.py`
- **Line**: 217
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.delete("/conversation/{session_id}")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 53. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/nlp.py`
- **Line**: 247
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/suggestions", response_model=List[IntentSuggestion])`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 54. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/nlp.py`
- **Line**: 276
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/analytics", response_model=AnalyticsResponse)`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 55. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/nlp.py`
- **Line**: 325
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/health", response_model=HealthCheckResponse)`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 56. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/nlp.py`
- **Line**: 359
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/batch", response_model=List[MessageResponse])`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 57. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/nlp.py`
- **Line**: 418
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/admin/sessions")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 58. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/nlp.py`
- **Line**: 442
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/admin/cleanup")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 59. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/metrics.py`
- **Line**: 19
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/metrics")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 60. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/admin.py`
- **Line**: 23
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/tenants")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 61. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/admin.py`
- **Line**: 29
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/tenants/refresh")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 62. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/admin.py`
- **Line**: 39
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/tenants")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 63. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/admin.py`
- **Line**: 57
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/tenants/{tenant_id}/identifiers")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 64. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/admin.py`
- **Line**: 77
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.delete("/tenants/{tenant_id}/identifiers/{identifier}")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 65. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/admin.py`
- **Line**: 99
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.patch("/tenants/{tenant_id}")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 66. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/admin.py`
- **Line**: 115
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/audio-cache/stats")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 67. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/admin.py`
- **Line**: 123
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.delete("/audio-cache")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 68. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/admin.py`
- **Line**: 132
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.delete("/audio-cache/entry")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 69. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/admin.py`
- **Line**: 146
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/audio-cache/cleanup")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 70. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/admin.py`
- **Line**: 163
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/reviews/send")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 71. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/admin.py`
- **Line**: 192
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/reviews/schedule")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 72. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/admin.py`
- **Line**: 242
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/reviews/mark-submitted")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 73. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/admin.py`
- **Line**: 276
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/reviews/analytics")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 74. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/admin.py`
- **Line**: 302
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/audit-logs")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 75. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 34
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/business/metrics")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 76. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 62
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/business/kpis")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 77. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 84
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/business/alerts")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 78. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 98
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/dashboards")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 79. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 111
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/dashboards/{dashboard_id}")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 80. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 138
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/dashboards/{dashboard_id}/widgets")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 81. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 153
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/dashboards/executive/summary")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 82. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 176
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/alerts")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 83. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 217
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/alerts/{alert_id}/acknowledge")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 84. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 232
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/alerts/{alert_id}/resolve")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 85. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 247
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/alerts/statistics")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 86. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 261
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/performance")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 87. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 300
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/performance/realtime")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 88. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 326
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/performance/insights/{metric_name}")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 89. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 341
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/performance/optimize/{recommendation_id}")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 90. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 362
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/health")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 91. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 408
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/health/liveness")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 92. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 433
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/health/readiness")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 93. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 464
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/health/dependencies")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 94. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 492
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/health/diagnose")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 95. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 506
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/traces")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 96. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 549
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/traces/{trace_id}")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 97. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 604
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/traces/{trace_id}/critical-path")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 98. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 617
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/traces/analytics/operations")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 99. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 630
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/traces/analytics/service-map")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 100. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 643
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.post("/traces/search")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 101. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 673
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/overview")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 102. Missing Authorization (HIGH)

- **Category**: A01 - Broken Access Control
- **File**: `app/routers/monitoring.py`
- **Line**: 738
- **CWE**: CWE-284
- **Description**: Route endpoint without authorization decorator
- **Evidence**: `@router.get("/export/prometheus")`
- **Recommendation**: Add Depends(get_current_user) or @requires_auth decorator

### 103. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/PIL/TiffImagePlugin.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 104. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/PIL/FontFile.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 105. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/PIL/Image.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 106. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/prometheus_client/mmap_dict.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 107. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/torch/hub.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 108. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/torch/serialization.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 109. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/multipart/multipart.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 110. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/fsspec/caching.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 111. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/anyio/_core/_fileio.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 112. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/torch/_dynamo/utils.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 113. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/torch/_inductor/codecache.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 114. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/torch/distributed/elastic/multiprocessing/redirects.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 115. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/torch/utils/model_dump/__init__.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 116. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/torch/_export/db/gen_example.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 117. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/sympy/utilities/_compilation/compilation.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 118. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/sympy/parsing/latex/_build_latex_antlr.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 119. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/sympy/parsing/autolev/_build_autolev_antlr.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 120. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/sympy/sets/tests/test_sets.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 121. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/sympy/stats/tests/test_stochastic_process.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 122. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/sympy/external/tests/test_autowrap.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 123. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/numpy/lib/_format_impl.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 124. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/numpy/lib/tests/test_format.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 125. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/numpy/lib/tests/test_nanfunctions.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 126. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/numpy/_core/tests/test_multiarray.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 127. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/fsspec/implementations/http.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 128. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/psutil/tests/__init__.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 129. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/psutil/tests/test_linux.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 130. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/networkx/readwrite/tests/test_graph6.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 131. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/networkx/readwrite/tests/test_gml.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 132. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/numba/core/caching.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 133. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/numba/pycc/compiler.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 134. Path Traversal (CRITICAL)

- **Category**: A01 - Broken Access Control
- **File**: `.venv/lib/python3.12/site-packages/numba/misc/help/inspector.py`
- **CWE**: CWE-22
- **Description**: Potential path traversal vulnerability
- **Evidence**: `Dynamic file path construction detected`
- **Recommendation**: Use Path.resolve() and validate against allowed directories

### 135. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/torchgen/utils.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 136. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/aiohttp/web_ws.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 137. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/aiohttp/client_middleware_digest_auth.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 138. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/aiohttp/client_middleware_digest_auth.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 139. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/aiohttp/client.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 140. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/aiohttp/hdrs.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 141. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/aiohttp/client_reqrep.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 142. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/aiohttp/client_reqrep.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 143. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/websockets/utils.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 144. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/ecdsa/test_pyecdsa.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 145. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/ecdsa/ecdsa.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 146. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/ecdsa/test_malformed_sigs.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 147. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/ecdsa/test_malformed_sigs.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 148. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/ecdsa/keys.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 149. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/ecdsa/test_keys.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 150. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/ecdsa/der.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 151. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/ecdsa/rfc6979.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 152. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/totp.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 153. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/hosts.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 154. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/hosts.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 155. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/hosts.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 156. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/win32.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 157. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/jinja2/loaders.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 158. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/jinja2/bccache.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 159. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/distlib/database.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 160. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/distlib/database.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 161. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/distlib/index.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 162. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/distlib/locators.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 163. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/requests/auth.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 164. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/requests/auth.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 165. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/rsa/pkcs1.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 166. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/rsa/pkcs1.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 167. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/redis/ocsp.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 168. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/tiktoken/load.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 169. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/fsspec/utils.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 170. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/dns/entropy.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 171. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/dns/tsig.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 172. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/dns/tsig.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 173. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/dns/dnssec.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 174. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/dns/dnssectypes.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 175. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/httpx/_auth.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 176. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/httpx/_auth.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 177. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/httpx/_config.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 178. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/starlette/_compat.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 179. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/jose/backends/cryptography_backend.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 180. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/_stata_builtins.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 181. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/prolog.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 182. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/ride.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 183. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/ride.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 184. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/scripting.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 185. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/scripting.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 186. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/_mysql_builtins.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 187. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/_mysql_builtins.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 188. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/erlang.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 189. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/_openedge_builtins.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 190. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/_openedge_builtins.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 191. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/dsls.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 192. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/dsls.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 193. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/_lilypond_builtins.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 194. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/installers.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 195. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/configs.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 196. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/configs.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 197. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/rdf.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 198. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/rdf.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 199. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/lisp.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 200. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/q.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 201. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/_php_builtins.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 202. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/_php_builtins.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 203. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/_googlesql_builtins.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 204. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/_googlesql_builtins.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 205. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/cryptography/x509/ocsp.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 206. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/cryptography/x509/extensions.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 207. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/cryptography/hazmat/_oid.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 208. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/cryptography/hazmat/_oid.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 209. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/hashes.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 210. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/hashes.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 211. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/_serialization.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 212. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/cryptography/hazmat/decrepit/ciphers/algorithms.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: RC4
- **Evidence**: `Usage of RC4 found in code`
- **Recommendation**: Replace RC4 with SHA256 or better

### 213. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/twofactor/hotp.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 214. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/serialization/ssh.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 215. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/serialization/ssh.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 216. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/cryptography/hazmat/backends/openssl/backend.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 217. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/distributed/distributed_c10d.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 218. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/utils/_config_module.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 219. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/utils/_content_store.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 220. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/_logging/_internal.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 221. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/fx/passes/graph_drawer.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 222. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/utils/__init__.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 223. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/utils/binary.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 224. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/utils/des.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 225. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/utils/pbkdf2.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 226. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/utils/pbkdf2.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 227. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/django.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 228. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/django.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 229. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/django.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 230. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/roundup.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 231. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/md5_crypt.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 232. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/phpass.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 233. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/scram.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 234. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/digests.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 235. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/digests.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 236. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/cisco.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 237. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/windows.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 238. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/windows.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 239. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/mssql.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 240. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/fshp.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 241. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/des_crypt.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 242. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/sun_md5_crypt.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 243. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/sha1_crypt.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 244. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/mysql.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 245. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/pbkdf2.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 246. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/postgres.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 247. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/ldap_digests.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 248. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/ldap_digests.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 249. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/oracle.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 250. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/oracle.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 251. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/crypto/digest.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 252. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/crypto/digest.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 253. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/crypto/des.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 254. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_apps.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 255. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_apps.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 256. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_handlers_django.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 257. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_handlers_django.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 258. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_utils_handlers.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 259. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_utils_handlers.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 260. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_crypto_digest.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 261. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_crypto_digest.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 262. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_crypto_digest.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 263. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_handlers_bcrypt.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 264. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_context.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 265. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_context.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 266. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_crypto_des.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 267. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_handlers.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 268. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_handlers.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 269. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_handlers.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 270. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_handlers_pbkdf2.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 271. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_handlers_pbkdf2.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 272. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_utils_pbkdf2.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 273. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_utils_pbkdf2.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 274. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_totp.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 275. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/ext/django/utils.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 276. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/ext/django/utils.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 277. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/util/compat.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 278. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/orm/interfaces.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 279. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/dialects/mysql/base.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 280. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/sympy/utilities/misc.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 281. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/sympy/utilities/codegen.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 282. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/sympy/series/formal.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 283. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/urllib3/util/ssl_.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 284. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/urllib3/util/ssl_.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 285. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/_core/tests/test_cpu_features.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 286. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/redis/commands/core.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 287. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/fsspec/implementations/http.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 288. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/fsspec/implementations/http_sync.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 289. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/fsspec/tests/abstract/__init__.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 290. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/fsspec/tests/abstract/copy.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 291. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/fsspec/tests/abstract/get.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 292. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/fsspec/tests/abstract/put.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 293. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pip/_internal/req/req_install.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 294. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pip/_internal/vcs/git.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 295. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pip/_internal/models/link.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 296. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pip/_internal/models/link.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 297. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pip/_vendor/requests/auth.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 298. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pip/_vendor/requests/auth.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 299. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pip/_vendor/urllib3/util/ssl_.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 300. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/pip/_vendor/urllib3/util/ssl_.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 301. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/dns/dnssecalgs/rsa.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 302. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/dns/dnssecalgs/rsa.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 303. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/dns/dnssecalgs/dsa.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 304. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/dns/rdtypes/ANY/NSEC3.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 305. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/networkx/generators/trees.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 306. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/networkx/algorithms/centrality/eigenvector.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 307. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/triton/compiler/compiler.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 308. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/triton/compiler/make_launcher.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 309. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/triton/runtime/driver.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 310. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/triton/runtime/jit.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 311. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/triton/common/backend.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 312. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/triton/compiler/backends/cuda.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 313. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/core/caching.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 314. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/core/pythonapi.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 315. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/core/callconv.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 316. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `scripts/security/owasp_validator.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 317. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `scripts/security/owasp_validator.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 318. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `scripts/security/owasp_validator.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 319. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `scripts/security/owasp_validator.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: RC4
- **Evidence**: `Usage of RC4 found in code`
- **Recommendation**: Replace RC4 with SHA256 or better

### 320. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `app/services/audio_cache_service.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 321. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `app/services/pms/enhanced_pms_service.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 322. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `tests/integration/test_whatsapp_integration.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 323. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `tests/agent/test_agent_consistency_concrete.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 324. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `tests/security/test_owasp_top10.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 325. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `tests/security/test_owasp_top10.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 326. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `tests/security/test_owasp_top10.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: DES
- **Evidence**: `Usage of DES found in code`
- **Recommendation**: Replace DES with SHA256 or better

### 327. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `tests/security/test_owasp_top10.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: RC4
- **Evidence**: `Usage of RC4 found in code`
- **Recommendation**: Replace RC4 with SHA256 or better

### 328. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `tests/security/test_penetration_testing.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: MD5
- **Evidence**: `Usage of MD5 found in code`
- **Recommendation**: Replace MD5 with SHA256 or better

### 329. Weak Cryptography (HIGH)

- **Category**: A02 - Cryptographic Failures
- **File**: `tests/security/test_penetration_testing.py`
- **CWE**: CWE-327
- **Description**: Weak cryptographic algorithm detected: SHA1
- **Evidence**: `Usage of SHA1 found in code`
- **Recommendation**: Replace SHA1 with SHA256 or better

### 330. Hardcoded Encryption Key (CRITICAL)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/ecdsa/test_ecdh.py`
- **CWE**: CWE-798
- **Description**: Hardcoded encryption key detected
- **Evidence**: `key = "..." pattern found`
- **Recommendation**: Use environment variables or secrets manager

### 331. Hardcoded Encryption Key (CRITICAL)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/distributed/rpc/_utils.py`
- **CWE**: CWE-798
- **Description**: Hardcoded encryption key detected
- **Evidence**: `key = "..." pattern found`
- **Recommendation**: Use environment variables or secrets manager

### 332. Hardcoded Encryption Key (CRITICAL)

- **Category**: A02 - Cryptographic Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_totp.py`
- **CWE**: CWE-798
- **Description**: Hardcoded encryption key detected
- **Evidence**: `key = "..." pattern found`
- **Recommendation**: Use environment variables or secrets manager

### 333. Hardcoded Encryption Key (CRITICAL)

- **Category**: A02 - Cryptographic Failures
- **File**: `tests/security/test_secret_scanning.py`
- **CWE**: CWE-798
- **Description**: Hardcoded encryption key detected
- **Evidence**: `key = "..." pattern found`
- **Recommendation**: Use environment variables or secrets manager

### 334. Sql Injection (CRITICAL)

- **Category**: A03 - Injection
- **File**: `.venv/lib/python3.12/site-packages/torch/profiler/profiler.py`
- **Line**: 436
- **CWE**: CWE-89
- **Description**: Potential sql injection vulnerability
- **Evidence**: `raise RuntimeError("Can't create directory: " + dir_name) from e`
- **Recommendation**: Use parameterized queries or input validation

### 335. Command Injection (CRITICAL)

- **Category**: A03 - Injection
- **File**: `.venv/lib/python3.12/site-packages/torch/_dynamo/guards.py`
- **Line**: 491
- **CWE**: CWE-78
- **Description**: Potential command injection vulnerability
- **Evidence**: `# I.e `eval(f"{compile('2+2','','exec')!r}")` raises SyntaxError`
- **Recommendation**: Use parameterized queries or input validation

### 336. Command Injection (CRITICAL)

- **Category**: A03 - Injection
- **File**: `.venv/lib/python3.12/site-packages/torch/distributed/fsdp/_runtime_utils.py`
- **Line**: 744
- **CWE**: CWE-78
- **Description**: Potential command injection vulnerability
- **Evidence**: `# (i.e. model.eval() + full precision in eval was configured), don't downcast gradient.`
- **Recommendation**: Use parameterized queries or input validation

### 337. Sql Injection (CRITICAL)

- **Category**: A03 - Injection
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/sql/selectable.py`
- **Line**: 559
- **CWE**: CWE-89
- **Description**: Potential sql injection vulnerability
- **Evidence**: `select /*+ index(mytable ix_mytable) */ ... from mytable`
- **Recommendation**: Use parameterized queries or input validation

### 338. Sql Injection (CRITICAL)

- **Category**: A03 - Injection
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/testing/requirements.py`
- **Line**: 358
- **CWE**: CWE-89
- **Description**: Potential sql injection vulnerability
- **Evidence**: `SELECT x + y AS somelabel FROM table GROUP BY x + y`
- **Recommendation**: Use parameterized queries or input validation

### 339. Command Injection (CRITICAL)

- **Category**: A03 - Injection
- **File**: `.venv/lib/python3.12/site-packages/sympy/codegen/cfunctions.py`
- **Line**: 142
- **CWE**: CWE-78
- **Description**: Potential command injection vulnerability
- **Evidence**: `return log.eval(arg + S.One)`
- **Recommendation**: Use parameterized queries or input validation

### 340. Command Injection (CRITICAL)

- **Category**: A03 - Injection
- **File**: `.venv/lib/python3.12/site-packages/sympy/polys/rootisolation.py`
- **Line**: 1055
- **CWE**: CWE-78
- **Description**: Potential command injection vulnerability
- **Evidence**: `if dup_eval(f2, (s + a)/2, F) > 0:`
- **Recommendation**: Use parameterized queries or input validation

### 341. Command Injection (CRITICAL)

- **Category**: A03 - Injection
- **File**: `.venv/lib/python3.12/site-packages/sympy/polys/rootisolation.py`
- **Line**: 1097
- **CWE**: CWE-78
- **Description**: Potential command injection vulnerability
- **Evidence**: `if dup_eval(f1, (s + a)/2, F) > 0:`
- **Recommendation**: Use parameterized queries or input validation

### 342. Command Injection (CRITICAL)

- **Category**: A03 - Injection
- **File**: `.venv/lib/python3.12/site-packages/sympy/polys/rootisolation.py`
- **Line**: 1139
- **CWE**: CWE-78
- **Description**: Potential command injection vulnerability
- **Evidence**: `re = dup_eval(f1, (s + a)/2, F)`
- **Recommendation**: Use parameterized queries or input validation

### 343. Command Injection (CRITICAL)

- **Category**: A03 - Injection
- **File**: `.venv/lib/python3.12/site-packages/sympy/polys/rootisolation.py`
- **Line**: 1140
- **CWE**: CWE-78
- **Description**: Potential command injection vulnerability
- **Evidence**: `im = dup_eval(f2, (s + a)/2, F)`
- **Recommendation**: Use parameterized queries or input validation

### 344. Command Injection (CRITICAL)

- **Category**: A03 - Injection
- **File**: `.venv/lib/python3.12/site-packages/sympy/polys/densetools.py`
- **Line**: 272
- **CWE**: CWE-78
- **Description**: Potential command injection vulnerability
- **Evidence**: `>>> R.dup_eval(x**2 + 2*x + 3, 2)`
- **Recommendation**: Use parameterized queries or input validation

### 345. Command Injection (CRITICAL)

- **Category**: A03 - Injection
- **File**: `.venv/lib/python3.12/site-packages/sympy/polys/densetools.py`
- **Line**: 298
- **CWE**: CWE-78
- **Description**: Potential command injection vulnerability
- **Evidence**: `>>> R.dmp_eval(2*x*y + 3*x + y + 2, 2)`
- **Recommendation**: Use parameterized queries or input validation

### 346. Command Injection (CRITICAL)

- **Category**: A03 - Injection
- **File**: `.venv/lib/python3.12/site-packages/sympy/polys/densetools.py`
- **Line**: 361
- **CWE**: CWE-78
- **Description**: Potential command injection vulnerability
- **Evidence**: `return dup_eval(h, A[-u + i - 1], K)`
- **Recommendation**: Use parameterized queries or input validation

### 347. Command Injection (CRITICAL)

- **Category**: A03 - Injection
- **File**: `.venv/lib/python3.12/site-packages/sympy/functions/elementary/trigonometric.py`
- **Line**: 1580
- **CWE**: CWE-78
- **Description**: Potential command injection vulnerability
- **Evidence**: `# trigonometric functions eval() like even/odd, func(x+2*k*pi), etc.`
- **Recommendation**: Use parameterized queries or input validation

### 348. Nosql Injection (HIGH)

- **Category**: A03 - Injection
- **File**: `scripts/security/owasp_validator.py`
- **Line**: 117
- **CWE**: CWE-943
- **Description**: Potential nosql injection vulnerability
- **Evidence**: `"pattern": r'\$where.*\$ne.*\$or.*\$and',`
- **Recommendation**: Use parameterized queries or input validation

### 349. Ldap Injection (HIGH)

- **Category**: A03 - Injection
- **File**: `scripts/security/owasp_validator.py`
- **Line**: 127
- **CWE**: CWE-90
- **Description**: Potential ldap injection vulnerability
- **Evidence**: `"pattern": r'ldap.*search.*\+.*\)',`
- **Recommendation**: Use parameterized queries or input validation

### 350. Weak JWT Configuration (CRITICAL)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/jose/jwt.py`
- **CWE**: CWE-798
- **Description**: JWT with hardcoded secret
- **Evidence**: `jwt.encode with HS256 and no env var`
- **Recommendation**: Use SECRET_KEY from environment variables

### 351. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/click/decorators.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 352. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/click/__init__.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 353. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/uvicorn/workers.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 354. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/uvicorn/main.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 355. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/rich/logging.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 356. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/prometheus_client/exposition.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 357. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/rich_toolkit/toolkit.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 358. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/ifc.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 359. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/__init__.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 360. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/hosts.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 361. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/exc.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 362. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/requests/auth.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 363. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/urllib3/_base_connection.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 364. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/redis/credentials.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 365. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/fsspec/json.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 366. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/httpx/_auth.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 367. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/httpx/_api.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 368. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/httpx/_types.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 369. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/fastapi/applications.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 370. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/teraterm.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 371. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/verifpal.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 372. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/pygments/lexers/thingsdb.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 373. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/httpcore/_sync/socks_proxy.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 374. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/httpcore/_sync/http_proxy.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 375. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/httpcore/_async/socks_proxy.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 376. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/httpcore/_async/http_proxy.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 377. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/websockets/legacy/auth.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 378. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/limits/storage/redis_sentinel.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 379. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/limits/storage/redis_cluster.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 380. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/limits/storage/mongodb.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 381. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/limits/storage/redis.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 382. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/limits/aio/storage/mongodb.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 383. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/limits/aio/storage/redis/__init__.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 384. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/limits/aio/storage/redis/bridge.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 385. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/limits/aio/storage/memcached/bridge.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 386. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/phpass.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 387. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/mysql.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 388. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/postgres.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 389. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/handlers/ldap_digests.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 390. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_ext_django.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 391. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_apache.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 392. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_ext_django_source.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 393. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_handlers_django.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 394. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_handlers_cisco.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 395. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_context.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 396. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_handlers_pbkdf2.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 397. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/tests/test_handlers_scrypt.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 398. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/utils/compat/__init__.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 399. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/passlib/ext/django/models.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 400. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/engine/url.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 401. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/connectors/pyodbc.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 402. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/ext/hybrid.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 403. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/testing/plugin/plugin_base.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 404. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/dialects/sqlite/pysqlite.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 405. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/dialects/sqlite/provision.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 406. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/dialects/sqlite/pysqlcipher.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 407. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/dialects/mssql/aioodbc.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 408. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/dialects/mssql/pymssql.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 409. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/psycopg2.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 410. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/psycopg2cffi.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 411. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/dialects/mysql/mysqlconnector.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 412. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/dialects/mysql/pymysql.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 413. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/dialects/mysql/aiomysql.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 414. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/dialects/mysql/mariadbconnector.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 415. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/dialects/mysql/cymysql.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 416. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/dialects/mysql/pyodbc.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 417. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/dialects/mysql/mysqldb.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 418. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/dialects/mysql/asyncmy.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 419. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/dialects/oracle/oracledb.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 420. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/urllib3/contrib/emscripten/connection.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 421. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/fsspec/implementations/webhdfs.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 422. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/fsspec/implementations/smb.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 423. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/fsspec/implementations/sftp.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 424. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/pip/_internal/vcs/versioncontrol.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 425. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/pip/_internal/network/auth.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 426. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/pip/_vendor/rich/logging.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 427. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/pip/_vendor/truststore/_api.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 428. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/pip/_vendor/requests/auth.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 429. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/pip/_vendor/urllib3/util/request.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 430. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/pip/_vendor/urllib3/contrib/ntlmpool.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 431. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/dns/dnssecalgs/base.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 432. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/dns/dnssecalgs/cryptography.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 433. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/fastapi/security/http.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 434. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `.venv/lib/python3.12/site-packages/fastapi/security/oauth2.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 435. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `app/core/redis_client.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 436. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `app/security/audit_logger.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 437. Weak Password Policy (MEDIUM)

- **Category**: A07 - Authentication Failures
- **File**: `tests/unit/test_qr_service.py`
- **CWE**: CWE-521
- **Description**: No password complexity validation
- **Evidence**: `password field without validation`
- **Recommendation**: Implement password complexity requirements (min 8 chars, uppercase, number, special)

### 438. Weak JWT Configuration (CRITICAL)

- **Category**: A07 - Authentication Failures
- **File**: `tests/security/test_advanced_jwt_auth.py`
- **CWE**: CWE-798
- **Description**: JWT with hardcoded secret
- **Evidence**: `jwt.encode with HS256 and no env var`
- **Recommendation**: Use SECRET_KEY from environment variables

### 439. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/anyio/to_process.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 440. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/anyio/to_interpreter.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 441. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/pytz/__init__.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 442. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/aiohttp/cookiejar.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 443. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/ecdsa/test_jacobi.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 444. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/ecdsa/test_eddsa.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 445. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/jinja2/bccache.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 446. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/regex/test_regex.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 447. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/pycparser/ply/yacc.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 448. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/llvmlite/tests/test_ir.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 449. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/mpmath/tests/test_pickle.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 450. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/pydantic/deprecated/parse.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 451. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/pydantic/v1/parse.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 452. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/cuda/_memory_viz.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 453. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/utils/_config_module.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 454. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/_functorch/compilers.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 455. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/_inductor/debug.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 456. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/_inductor/codecache.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 457. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/multiprocessing/spawn.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 458. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/multiprocessing/queue.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 459. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/distributed/checkpoint/filesystem.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 460. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/distributed/_tools/memory_tracker.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 461. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/distributed/elastic/rendezvous/dynamic_rendezvous.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 462. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/utils/model_dump/__init__.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 463. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/utils/data/datapipes/datapipe.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 464. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/utils/data/datapipes/utils/decoder.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 465. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/utils/benchmark/examples/compare.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 466. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/utils/benchmark/utils/valgrind_wrapper/timer_interface.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 467. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/torch/testing/_internal/jit_utils.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 468. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/sql/sqltypes.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 469. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/testing/util.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 470. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/sqlalchemy/ext/serializer.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 471. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/sympy/utilities/tests/test_matchpy_connector.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 472. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/sympy/utilities/tests/test_pickling.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 473. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/sympy/polys/tests/test_polytools.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 474. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/sympy/polys/matrices/tests/test_domainmatrix.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 475. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/sympy/printing/tests/test_latex.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 476. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/sympy/physics/vector/tests/test_frame.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 477. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/sympy/external/tests/test_pythonmpq.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 478. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/lib/_npyio_impl.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 479. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/lib/_format_impl.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 480. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/_core/_add_newdocs.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 481. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/_core/records.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 482. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/tests/test_reloading.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 483. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/polynomial/tests/test_polynomial.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 484. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/random/tests/test_smoke.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 485. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/random/tests/test_generator_mt19937.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 486. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/random/tests/test_direct.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 487. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/random/tests/test_randomstate.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 488. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/matrixlib/tests/test_masked_matrix.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 489. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/_core/tests/test_regression.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 490. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/_core/tests/test_datetime.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 491. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/_core/tests/test_overrides.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 492. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/_core/tests/test_records.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 493. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/_core/tests/test_ufunc.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 494. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/_core/tests/test__exceptions.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 495. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/_core/tests/test_custom_dtypes.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 496. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/_core/tests/test_dtype.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 497. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/_core/tests/test_stringdtype.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 498. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/_core/tests/test_multiarray.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 499. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/ma/tests/test_mrecords.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 500. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/ma/tests/test_old_ma.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 501. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numpy/ma/tests/test_core.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 502. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/fsspec/implementations/cache_metadata.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 503. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/psutil/tests/test_misc.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 504. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/networkx/classes/tests/test_coreviews.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 505. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/networkx/classes/tests/test_reportviews.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 506. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/networkx/classes/tests/test_graphviews.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 507. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/networkx/classes/tests/test_graph.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 508. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/networkx/utils/tests/test_config.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 509. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/networkx/utils/tests/test_backends.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 510. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/networkx/algorithms/flow/tests/test_mincost.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 511. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/networkx/algorithms/flow/tests/test_networksimplex.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 512. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/networkx/algorithms/flow/tests/test_maxflow_large_graph.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 513. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/cloudpickle/cloudpickle.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 514. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/core/caching.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 515. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/core/serialize.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 516. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/tests/test_codegen.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 517. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/tests/test_types.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 518. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/tests/test_extending.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 519. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/tests/test_jitclasses.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 520. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/tests/test_unpickle_without_module.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 521. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/tests/test_dispatcher.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 522. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/tests/test_serialize.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 523. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/cuda/tests/cudapy/test_ipc.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 524. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/cuda/tests/cudapy/test_serialize.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 525. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/tests/npyufunc/test_ufuncbuilding.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 526. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/tests/npyufunc/test_dufunc.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 527. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `.venv/lib/python3.12/site-packages/numba/tests/npyufunc/test_gufunc.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 528. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `scripts/security/owasp_validator.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 529. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `app/services/audio_cache_optimizer.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 530. Insecure Deserialization (CRITICAL)

- **Category**: A08 - Data Integrity Failures
- **File**: `tests/security/test_owasp_top10.py`
- **CWE**: CWE-502
- **Description**: Insecure deserialization with pickle
- **Evidence**: `pickle.loads() detected`
- **Recommendation**: Use JSON or validate data before unpickling

### 531. Missing Security Logging (MEDIUM)

- **Category**: A09 - Logging and Monitoring Failures
- **File**: `.venv/lib/python3.12/site-packages/aiohttp/client_middleware_digest_auth.py`
- **CWE**: CWE-778
- **Description**: Authentication logic without logging
- **Evidence**: `No logger usage in auth module`
- **Recommendation**: Log all authentication failures and suspicious activities

### 532. Missing Security Logging (MEDIUM)

- **Category**: A09 - Logging and Monitoring Failures
- **File**: `.venv/lib/python3.12/site-packages/requests/auth.py`
- **CWE**: CWE-778
- **Description**: Authentication logic without logging
- **Evidence**: `No logger usage in auth module`
- **Recommendation**: Log all authentication failures and suspicious activities

### 533. Missing Security Logging (MEDIUM)

- **Category**: A09 - Logging and Monitoring Failures
- **File**: `.venv/lib/python3.12/site-packages/httpx/_auth.py`
- **CWE**: CWE-778
- **Description**: Authentication logic without logging
- **Evidence**: `No logger usage in auth module`
- **Recommendation**: Log all authentication failures and suspicious activities

### 534. Missing Security Logging (MEDIUM)

- **Category**: A09 - Logging and Monitoring Failures
- **File**: `.venv/lib/python3.12/site-packages/websockets/legacy/auth.py`
- **CWE**: CWE-778
- **Description**: Authentication logic without logging
- **Evidence**: `No logger usage in auth module`
- **Recommendation**: Log all authentication failures and suspicious activities

### 535. Missing Security Logging (MEDIUM)

- **Category**: A09 - Logging and Monitoring Failures
- **File**: `.venv/lib/python3.12/site-packages/pip/_vendor/requests/auth.py`
- **CWE**: CWE-778
- **Description**: Authentication logic without logging
- **Evidence**: `No logger usage in auth module`
- **Recommendation**: Log all authentication failures and suspicious activities

### 536. Missing Security Logging (MEDIUM)

- **Category**: A09 - Logging and Monitoring Failures
- **File**: `.venv/lib/python3.12/site-packages/fastapi/security/oauth2.py`
- **CWE**: CWE-778
- **Description**: Authentication logic without logging
- **Evidence**: `No logger usage in auth module`
- **Recommendation**: Log all authentication failures and suspicious activities

### 537. Missing Security Logging (MEDIUM)

- **Category**: A09 - Logging and Monitoring Failures
- **File**: `tests/security/test_advanced_jwt_auth.py`
- **CWE**: CWE-778
- **Description**: Authentication logic without logging
- **Evidence**: `No logger usage in auth module`
- **Recommendation**: Log all authentication failures and suspicious activities

### 538. Unvalidated Redirect (HIGH)

- **Category**: A10 - Server-Side Request Forgery
- **File**: `.venv/lib/python3.12/site-packages/httpx/_client.py`
- **Line**: 533
- **CWE**: CWE-601
- **Description**: Potential unvalidated redirect vulnerability
- **Evidence**: `if not is_https_redirect(request.url, url):`
- **Recommendation**: Validate and whitelist URLs before making requests

