# WEEKLY OPERATIONS PLAYBOOK - DÍA 5-11 Template

**Phase**: 2A - Weekly Operations  
**Duration**: 7 days (DÍA 5 to DÍA 11)  
**Effort**: 1-2 hours/day  
**Objective**: Continuous monitoring + weekly trend analysis  

---

## 📋 Daily Checklist Template

### Daily Health Check (Every Morning 08:00 UTC)

```
Date: ___________
Time: ___________

1. Services Health
   □ postgres-prod: _____ (✅/⚠️/❌)
   □ redis-prod: _____ (✅/⚠️/❌)
   □ agente-api-prod: _____ (✅/⚠️/❌)
   □ prometheus-prod: _____ (✅/⚠️/❌)
   □ grafana-prod: _____ (✅/⚠️/❌)
   □ alertmanager-prod: _____ (✅/⚠️/❌)
   □ jaeger-prod: _____ (✅/⚠️/❌)

2. Alert Review
   □ CRITICAL alerts: _____
   □ WARNING alerts: _____
   □ INFO alerts: _____
   □ Actions taken: _____

3. Performance Check
   □ P95 Latency: _____ ms (vs baseline: ____)
   □ Error Rate: _____ % (vs baseline: ____)
   □ Cache Hit: _____ % (vs baseline: ____)
   □ Trend: ↑↓→

4. Resources
   □ Memory: _____ % (stable/elevated/critical)
   □ CPU: _____ % (stable/elevated/critical)
   □ Disk: _____ % (stable/elevated/critical)

5. Issues Found
   □ None
   □ Minor (describe): _____
   □ Major (describe): _____

Notes: _____________________________________

Completed by: ____________ Time: __________
```

---

## 📊 Weekly Metrics Tracking

### Performance Baseline (from DÍA 4)

| Metric | Target | Baseline | Day 5 | Day 6 | Day 7 | Day 8 | Day 9 | Day 10 | Day 11 |
|--------|--------|----------|-------|-------|-------|-------|-------|--------|--------|
| P95 Latency (ms) | <10 | 4.87 | 4.85 | - | - | - | - | - | - |
| P99 Latency (ms) | <20 | 15.08 | 15.05 | - | - | - | - | - | - |
| Error Rate (%) | <0.1 | 0.0 | 0.0 | - | - | - | - | - | - |
| Success Rate (%) | >99.9 | 100 | 100 | - | - | - | - | - | - |
| Cache Hit (%) | >85 | 87.5 | 88.5 | - | - | - | - | - | - |
| Memory (MB) | <700 | 496 | 515 | - | - | - | - | - | - |
| CPU (%) | <50 | 24 | 21 | - | - | - | - | - | - |
| Uptime (h) | >168 | 24.5 | 25+ | - | - | - | - | - | - |

---

## 🚨 Alert Thresholds & Actions

### Threshold Definitions

| Alert Type | Threshold | Action |
|------------|-----------|--------|
| P95 Latency High | > 100ms | Review PMS / DB queries |
| Error Rate High | > 1% | Check logs for errors |
| Memory Leak | Growing > 10%/h | Restart service |
| CPU Spike | > 80% | Check running processes |
| Cache Miss Spike | < 70% | Analyze cache eviction |

### Response Procedures

**If latency alert triggers**:
1. Check Prometheus dashboard
2. Analyze slow queries
3. Review PMS circuit breaker status
4. Refer to GUIA_TROUBLESHOOTING.md section "P95 Latency > 300ms"

**If error rate alert triggers**:
1. Check error logs
2. Identify error type
3. Review recent deployments
4. Check dependencies (PMS, DB, Redis)

**If resource alert triggers**:
1. Check docker stats
2. Restart service if needed
3. Analyze for memory leaks
4. Refer to emergency guide if critical

---

## 📈 Weekly Trend Analysis (DÍA 11)

### Template for End-of-Week Report

**Week**: DÍA 5-11  
**Date Range**: 2025-10-24 to 2025-10-30  

#### Performance Trends
```
Latency Trend (P95):
  DÍA 5: 4.85ms
  DÍA 6: _____ms
  DÍA 7: _____ms
  DÍA 8: _____ms
  DÍA 9: _____ms
  DÍA 10: _____ms
  DÍA 11: _____ms
  
  Weekly Change: _____ (↑/↓/→)
  Assessment: _____________________
```

```
Error Rate Trend:
  All Days: 0.0%
  Weekly Change: STABLE ✅
  Assessment: Perfect error rate maintained
```

```
Cache Hit Trend:
  DÍA 5: 88.5%
  DÍA 6: _____% 
  ...
  
  Weekly Change: _____ (↑/↓/→)
  Assessment: _____________________
```

#### Alerts & Incidents
- **CRITICAL alerts this week**: _____
- **WARNING alerts this week**: _____
- **Incidents**: _____
- **Mitigation actions taken**: _____

#### Resource Utilization
- **Peak memory**: _____% (day: ____)
- **Peak CPU**: _____% (day: ____)
- **Trend**: Stable / Increasing / Decreasing
- **Assessment**: _____________________

#### Security Status
- **New CVEs detected**: _____
- **Vulnerabilities patched**: _____
- **Security incidents**: _____

#### Recommendations
1. _____________________________
2. _____________________________
3. _____________________________

---

## 🎯 Daily Operations SLOs

### Service Level Objectives (SLOs)

| SLO | Target | Current | Status |
|-----|--------|---------|--------|
| Uptime | 99.99% | 100% | ✅ Exceeded |
| Latency P95 | <100ms | 4.85ms | ✅ Exceeded |
| Error Rate | <0.1% | 0.0% | ✅ Exceeded |
| Alert Response | <5min | <30s | ✅ Exceeded |

### Success Criteria (All must be met)
- ✅ 7/7 services operational
- ✅ Zero CRITICAL alerts
- ✅ Performance stable or improving
- ✅ No anomalies detected
- ✅ Resource utilization normal
- ✅ All health checks passing

---

## 📞 Escalation Matrix

### By Severity Level

**🟢 GREEN (Normal)**
- All checks passing
- Metrics within baseline ±5%
- No alerts
- Action: Continue monitoring

**🟡 YELLOW (Caution)**
- Minor metric deviation (±5% to ±15%)
- INFO level alerts
- Single service slightly elevated
- Action: Investigate root cause, monitor closely

**🟠 ORANGE (Warning)**
- Significant metric deviation (±15% to ±30%)
- WARNING level alerts
- Multiple services affected or major service degraded
- Action: Review GUIA_TROUBLESHOOTING.md, prepare mitigation

**🔴 RED (Critical)**
- Major metric deviation (>±30%)
- CRITICAL alerts
- Service down or severe degradation
- Action: Execute emergency procedures, escalate to on-call

---

## ✅ Weekly Completion Checklist

### DÍA 5-10 (Daily tasks)
- [ ] Daily health check (08:00 UTC)
- [ ] Alert log review (ongoing)
- [ ] Performance verification (vs baseline)
- [ ] Resource check (no anomalies)
- [ ] Anomaly scan (0 issues)

### DÍA 11 (End-of-week)
- [ ] Compile weekly metrics
- [ ] Generate trend analysis
- [ ] Review all daily reports
- [ ] Identify patterns/recommendations
- [ ] Create weekly summary report
- [ ] Validate SLOs achieved
- [ ] Document any optimizations
- [ ] Commit report to GitHub

---

## 📋 Resources & References

**Documentation**:
- GUIA_TROUBLESHOOTING.md - Emergency procedures
- DIA_4_SESSION_SUMMARY.md - Baseline metrics
- OPERATIONS_MANUAL.md - Daily procedures
- README-Infra.md - Infrastructure details

**Dashboards**:
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- AlertManager: http://localhost:9094
- Jaeger: http://localhost:16687

**Health Endpoints**:
- /health/live (liveness)
- /health/ready (readiness)

---

## 🎉 Success Definition

✅ **Weekly operations successful if**:
1. 100% uptime maintained (7 days)
2. Zero CRITICAL alerts
3. Performance stable or improving
4. All SLOs met or exceeded
5. No incidents requiring escalation
6. Weekly report completed and committed
7. Team confident in system stability

---

**Document Purpose**: Daily checklist and weekly trend analysis template  
**Updated**: 2025-10-24  
**Next Review**: DÍA 11 (2025-10-30)  
**Maintained By**: Operations Team
