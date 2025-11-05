# Post-Launch Monitoring Plan

**Version**: 1.0  
**Date**: 2024-10-15  
**Purpose**: Comprehensive monitoring strategy after production launch  
**Owner**: Operations Team

---

## Table of Contents

1. [Overview](#overview)
2. [Monitoring Phases](#monitoring-phases)
3. [Metrics to Monitor](#metrics-to-monitor)
4. [Monitoring Schedule](#monitoring-schedule)
5. [Alert Thresholds](#alert-thresholds)
6. [Dashboards](#dashboards)
7. [Escalation Procedures](#escalation-procedures)
8. [Team Rotation](#team-rotation)

---

## Overview

### Purpose
This plan defines the intensive monitoring strategy for the first 48 hours and ongoing monitoring for the first month after production launch.

### Objectives
1. **Detect issues early**: Identify problems before users experience them
2. **Validate stability**: Confirm system performs as expected under real load
3. **Gather baseline**: Establish production performance baseline
4. **Build confidence**: Demonstrate system readiness to stakeholders

### Monitoring Intensity

| Phase | Duration | Check Frequency | Team Coverage | Focus |
|-------|----------|-----------------|---------------|-------|
| **Critical** | 0-2 hours | Every 5-15 min | 100% (all hands) | Real-time anomaly detection |
| **High** | 2-24 hours | Every 2 hours | On-call + backup | Stability validation |
| **Medium** | 24-48 hours | Every 4 hours | On-call engineer | Trend analysis |
| **Standard** | 48h-1 week | Daily (15 min) | On-call engineer | Pattern identification |
| **Normal** | Week 1-4 | Weekly (30 min) | Team review | Baseline establishment |

---

## Monitoring Phases

### Phase 1: Critical (0-2 Hours)

**Duration**: First 2 hours after go-live (T+0 to T+2h)  
**Intensity**: Maximum  
**Team**: All launch team members active

**Frequency**: Check dashboards every 5-15 minutes

**Focus Areas**:
1. **Error rate**: Must stay <0.1%
2. **Latency**: P95 <1s, P99 <2s
3. **Request rate**: Matches expected load
4. **Health checks**: All passing continuously
5. **Alerts**: None should fire (AlertManager quiet)

**Activities**:
```
T+0:   Go live, start continuous monitoring
T+5:   First validation checkpoint
T+10:  Second validation checkpoint
T+15:  Initial validation complete (see PRODUCTION-LAUNCH-RUNBOOK.md)
T+30:  Full validation checkpoint
T+60:  Monitoring handoff (end of critical phase)
T+90:  First post-handoff checkpoint
T+120: End of critical phase (move to High intensity)
```

**Success Criteria**:
- No alerts fired
- Error rate <0.1% sustained
- Latency within SLAs sustained
- No user-reported issues
- Team confident to reduce intensity

**Escalation**: Any anomaly triggers immediate team discussion (Slack call)

---

### Phase 2: High Intensity (2-24 Hours)

**Duration**: 2 hours to 24 hours after go-live  
**Intensity**: High  
**Team**: On-call engineer + backup on standby

**Frequency**: Check dashboards every 2 hours

**Focus Areas**:
1. **Sustained performance**: Metrics remain stable
2. **No degradation**: No slow creep of error rate or latency
3. **Resource usage**: Memory/CPU/disk not increasing abnormally
4. **External integrations**: PMS, WhatsApp, Gmail all healthy
5. **User feedback**: Monitor support channels for issues

**Checkpoint Schedule**:
```
T+2h:  First high-intensity checkpoint
T+4h:  Second checkpoint
T+6h:  Third checkpoint (dinner time coverage)
T+8h:  Fourth checkpoint
T+10h: Fifth checkpoint (late evening)
T+12h: Sixth checkpoint (midnight, overnight coverage)
T+14h: Seventh checkpoint (early morning)
T+16h: Eighth checkpoint
T+18h: Ninth checkpoint
T+20h: Tenth checkpoint
T+22h: Eleventh checkpoint
T+24h: 24-hour review (formal checkpoint, see below)
```

**Checkpoint Tasks** (10 minutes each):
1. Open main dashboard: `http://grafana/d/agente-hotel-overview`
2. Review key metrics:
   - Request rate: Compare to baseline (±20% acceptable)
   - Error rate: Must be <0.5%
   - Latency: P95 <1s, P99 <2s
   - Database: Connection pool <80% capacity
   - Redis: Hit rate >70%
3. Check AlertManager: `http://alertmanager:9093`
   - Should be quiet (no firing alerts)
4. Check logs: `docker compose logs --since 2h agente-api | grep -i error`
   - Should return minimal results (<10 errors in 2h)
5. Review business metrics:
   - Messages processed: Should be normal distribution
   - Sessions created: Should match expected user activity
   - PMS calls: Success rate >99%
6. Document status in Slack `#agente-hotel-launch`:
   ```
   ✅ T+[X]h checkpoint: [Status]
   Request rate: [X] req/s (baseline: [Y] req/s)
   Error rate: [X]%
   P95 latency: [X]ms
   Issues: [None / Description]
   Next check: T+[Y]h
   ```

**Success Criteria**:
- All checkpoints show stable metrics
- No trends toward degradation
- No user issues reported
- Team confident to reduce intensity further

**Escalation**: 
- Error rate >0.5%: Notify backup engineer
- Error rate >1%: Wake launch commander
- P95 latency >1.5s: Investigate immediately
- Any critical alert: Page on-call team

---

### Phase 3: Medium Intensity (24-48 Hours)

**Duration**: 24 hours to 48 hours after go-live  
**Intensity**: Medium  
**Team**: On-call engineer (backup available if needed)

**Frequency**: Check dashboards every 4 hours

**Focus Areas**:
1. **24-hour trends**: Look for daily patterns
2. **Peak load handling**: Validate performance during busy hours
3. **Resource efficiency**: Optimize if needed
4. **User satisfaction**: Check feedback, support tickets
5. **Cost monitoring**: Verify infrastructure costs as expected

**Checkpoint Schedule**:
```
T+24h: 24-hour formal review (30-minute meeting)
T+28h: Standard checkpoint
T+32h: Standard checkpoint
T+36h: Standard checkpoint
T+40h: Standard checkpoint
T+44h: Standard checkpoint
T+48h: 48-hour formal review (30-minute meeting)
```

**24-Hour Review Meeting** (T+24h):
**Duration**: 30 minutes  
**Attendees**: Launch Commander, On-Call Engineer, Ops Lead

**Agenda**:
1. **Metrics Review** (10 min):
   - Compare 24h metrics to baseline
   - Identify any anomalies or trends
   - Review peak performance periods
2. **Incidents** (5 min):
   - Any alerts fired? Root cause?
   - Any user-reported issues?
   - Any manual interventions needed?
3. **Resource Usage** (5 min):
   - CPU, memory, disk trends
   - Database performance
   - Cost vs. budget
4. **User Feedback** (5 min):
   - Support tickets
   - User surveys (if any)
   - Internal feedback
5. **Decision** (5 min):
   - Continue monitoring at medium intensity? **Yes**
   - Any adjustments needed?
   - Plan for 48h review

**Deliverable**: 24-hour status report posted to `#agente-hotel-launch`

**48-Hour Review Meeting** (T+48h):
**Duration**: 30 minutes  
**Attendees**: Launch Commander, Engineering Lead, Ops Lead, Product Lead

**Agenda**:
1. **Metrics Summary** (10 min):
   - 48-hour aggregated metrics vs. baseline
   - Performance stability demonstrated
   - Resource utilization optimal
2. **Issues Summary** (5 min):
   - Total incidents: [X]
   - User-reported issues: [X]
   - All resolved? Pending items?
3. **User Feedback** (5 min):
   - Overall satisfaction
   - Feature usage
   - Pain points identified
4. **Financial Review** (5 min):
   - Infrastructure costs vs. budget
   - Optimization opportunities
5. **Decision** (5 min):
   - **Declare launch stable** (move to standard monitoring)?
   - Or extend high-intensity monitoring?
   - Plan for week-1 review

**Deliverable**: 48-hour status report + decision (stable or not)

**Success Criteria**:
- 48 hours of stable metrics
- Error rate <0.1% sustained
- Latency within SLAs consistently
- No critical incidents
- User feedback positive or neutral
- **Decision: Declare launch STABLE** ✅

**Escalation**: Same as Phase 2

---

### Phase 4: Standard Monitoring (48h - 1 Week)

**Duration**: 48 hours to 1 week after go-live  
**Intensity**: Standard  
**Team**: On-call rotation (normal schedule)

**Frequency**: Daily check (15 minutes)

**Focus Areas**:
1. **Weekly patterns**: Identify weekday vs. weekend trends
2. **Optimization opportunities**: Fine-tune based on data
3. **Proactive improvements**: Address minor issues before they escalate
4. **Documentation updates**: Capture operational learnings

**Daily Check Tasks** (15 minutes):
1. Open weekly trends dashboard
2. Review past 24h metrics:
   - Request rate
   - Error rate
   - Latency (P50, P95, P99)
   - Database query performance
   - Cache hit rate
3. Check for any alerts fired in past 24h (even if auto-resolved)
4. Review logs for any warnings or errors
5. Check support channels for user issues
6. Document any observations in `#agente-hotel-ops`

**Week-1 Review Meeting** (Day 7):
**Duration**: 60 minutes  
**Attendees**: Full engineering team

**Agenda**:
1. **Metrics Overview** (15 min):
   - Week-1 aggregated metrics
   - Compare to pre-launch baseline
   - Identify performance improvements or regressions
2. **Incidents & Issues** (15 min):
   - Review all incidents (even minor)
   - Root cause analysis
   - Preventive measures
3. **User Experience** (10 min):
   - User feedback summary
   - Feature adoption
   - Pain points and requests
4. **Optimizations** (10 min):
   - What can we optimize now?
   - Database indexes needed?
   - Cache tuning?
   - Infrastructure right-sizing?
5. **Lessons Learned** (10 min):
   - What went well?
   - What could be better?
   - Update runbooks/procedures?

**Deliverable**: Week-1 retrospective document

**Success Criteria**:
- Consistent stable performance
- Clear baseline established
- Team confident in production readiness
- **Transition to normal monitoring cadence** ✅

---

### Phase 5: Normal Monitoring (Week 1-4)

**Duration**: Week 1 to Month 1  
**Intensity**: Normal operations  
**Team**: On-call rotation

**Frequency**: Weekly review (30 minutes)

**Focus Areas**:
1. **Monthly trends**: Identify long-term patterns
2. **Capacity planning**: Project future scaling needs
3. **Continuous improvement**: Implement optimizations
4. **Cost optimization**: Right-size infrastructure

**Weekly Review** (30 minutes):
- Review weekly metrics summary
- Compare to baseline (week 1)
- Identify trends (improving or degrading?)
- Plan optimizations for next week
- Update documentation as needed

**Month-1 Review Meeting** (Day 30):
**Duration**: 90 minutes  
**Attendees**: Engineering, Product, Operations, Management

**Agenda**:
1. **Launch Success Summary** (15 min):
   - Metrics vs. goals
   - Uptime: [X]% (target: >99.9%)
   - Performance: Stable, improving, degrading?
2. **Business Impact** (15 min):
   - User adoption
   - Feature usage
   - Customer satisfaction
3. **Technical Health** (15 min):
   - Infrastructure stability
   - Code quality (bugs, technical debt)
   - Monitoring coverage
4. **Financial Review** (10 min):
   - Actual costs vs. budget
   - ROI of optimizations
5. **Roadmap Planning** (20 min):
   - Features for next quarter
   - Technical improvements
   - Scaling strategy
6. **Retrospective** (15 min):
   - Overall launch success
   - Key learnings
   - Process improvements

**Deliverable**: Month-1 retrospective + next quarter plan

---

## Metrics to Monitor

### Application Metrics

#### 1. Request Rate
**Metric**: `rate(http_requests_total[5m])`  
**Target**: Stable, matches expected load (baseline ±20%)  
**Alert**: Sudden drop >50% (possible outage)

**What to look for**:
- Steady rate during business hours
- Expected dips overnight/weekends
- No sudden drops (service down)
- No sudden spikes (DDoS, bot traffic)

#### 2. Error Rate
**Metric**: `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])`  
**Target**: <0.1%  
**Alert**: >1% (critical), >0.5% (warning)

**What to look for**:
- Sustained low error rate
- No error spikes
- Error types (500 vs 502 vs 503)

#### 3. Latency
**Metrics**:
- P50: `histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))`
- P95: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
- P99: `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))`

**Target**: P95 <1s, P99 <2s  
**Alert**: P95 >1.5s (warning), >2s (critical)

**What to look for**:
- Stable latency distribution
- No increasing trend
- Identify slow endpoints

#### 4. Throughput
**Metric**: `rate(http_requests_total[1m])`  
**Target**: Handles peak load (e.g., 100 req/s)  
**Alert**: Approaching capacity (>80%)

---

### Infrastructure Metrics

#### 5. CPU Usage
**Metric**: `rate(process_cpu_seconds_total[5m])`  
**Target**: <70% average  
**Alert**: >80% sustained (warning), >90% (critical)

**What to look for**:
- Stable CPU utilization
- Spikes during peak traffic (expected)
- No sustained high usage (may need scaling)

#### 6. Memory Usage
**Metric**: `process_resident_memory_bytes`  
**Target**: <80% of limit  
**Alert**: >90% (warning), >95% (critical, possible OOM)

**What to look for**:
- Stable memory usage (no leaks)
- Normal sawtooth pattern (GC cycles)
- No continuous increase (memory leak)

#### 7. Disk Usage
**Metric**: `disk_used_percent`  
**Target**: <70%  
**Alert**: >80% (warning), >90% (critical)

**What to look for**:
- Slow, steady increase (logs, data)
- No sudden jumps
- Cleanup jobs running (log rotation)

---

### Database Metrics

#### 8. Connection Pool
**Metric**: `postgres_connections_active`  
**Target**: <80% of pool size  
**Alert**: >90% (warning), 100% (critical, pool exhausted)

**What to look for**:
- Pool usage matches request rate
- No connection leaks
- Pool size adequate

#### 9. Query Performance
**Metric**: `postgres_query_duration_seconds`  
**Target**: P95 <100ms  
**Alert**: P95 >500ms (warning), >1s (critical)

**What to look for**:
- Fast queries
- No slow query trends
- Identify optimization opportunities

#### 10. Database Size
**Metric**: `postgres_database_size_bytes`  
**Target**: Grows as expected (monitor rate)  
**Alert**: Unexpected growth (>20% per day)

---

### Cache Metrics

#### 11. Redis Hit Rate
**Metric**: `redis_keyspace_hits / (redis_keyspace_hits + redis_keyspace_misses)`  
**Target**: >70%  
**Alert**: <50% (warning, ineffective caching)

**What to look for**:
- High hit rate (cache effective)
- Stable rate
- Adjust TTL if rate low

#### 12. Redis Operations
**Metric**: `rate(redis_commands_total[5m])`  
**Target**: Proportional to request rate  
**Alert**: Sudden drop (Redis down)

---

### External Integration Metrics

#### 13. PMS API Latency
**Metric**: `histogram_quantile(0.95, rate(pms_api_latency_seconds_bucket[5m]))`  
**Target**: P95 <500ms  
**Alert**: P95 >1s (warning), >2s (critical)

#### 14. PMS Success Rate
**Metric**: `rate(pms_operations_total{status="success"}[5m]) / rate(pms_operations_total[5m])`  
**Target**: >99%  
**Alert**: <95% (warning), <90% (critical)

#### 15. Circuit Breaker State
**Metric**: `pms_circuit_breaker_state`  
**Target**: 0 (closed)  
**Alert**: 1 (open, service down)

**What to look for**:
- Always closed (healthy)
- If open, identify PMS issue

---

### Business Metrics

#### 16. Messages Processed
**Metric**: `rate(messages_processed_total[5m])`  
**Target**: Matches expected user activity  
**Alert**: Sudden drop >50%

#### 17. Sessions Created
**Metric**: `rate(sessions_created_total[5m])`  
**Target**: Stable, matches user growth

#### 18. Reservations Handled
**Metric**: `rate(reservations_total[5m])`  
**Target**: Stable, matches business expectations

---

## Monitoring Schedule

### Dashboard Check Schedule

| Phase | Frequency | Duration | Who | Dashboards |
|-------|-----------|----------|-----|------------|
| Critical (0-2h) | Every 5-15 min | 5 min | All team | Main overview |
| High (2-24h) | Every 2 hours | 10 min | On-call + backup | Main + errors |
| Medium (24-48h) | Every 4 hours | 10 min | On-call | Main + business |
| Standard (48h-1wk) | Daily | 15 min | On-call | Weekly trends |
| Normal (1wk-1mo) | Weekly | 30 min | Team | Monthly trends |

### Formal Review Schedule

| Checkpoint | When | Duration | Attendees | Deliverable |
|------------|------|----------|-----------|-------------|
| Initial validation | T+15min | 10 min | All team | Status update |
| Full validation | T+30min | 15 min | All team | Status update |
| Handoff | T+60min | 15 min | All team | Handoff brief |
| **24-hour review** | **T+24h** | **30 min** | **Commander + Ops** | **24h report** |
| **48-hour review** | **T+48h** | **30 min** | **Leadership** | **48h report + decision** |
| **Week-1 review** | **Day 7** | **60 min** | **Full team** | **Retrospective** |
| **Month-1 review** | **Day 30** | **90 min** | **All stakeholders** | **Month-1 report** |

---

## Alert Thresholds

### Critical Alerts (Page Immediately)

| Alert | Condition | Threshold | Action |
|-------|-----------|-----------|--------|
| **Service Down** | `up == 0` | N/A | Page on-call, investigate immediately |
| **High Error Rate** | `error_rate > X%` | 5% | Page on-call, consider rollback |
| **Database Down** | `postgres_up == 0` | N/A | Page on-call + DBA, restore ASAP |
| **Disk Full** | `disk_used > X%` | 95% | Page on-call, cleanup immediately |
| **Memory OOM** | `memory_used > X%` | 98% | Page on-call, restart or scale |
| **Circuit Breaker Open** | `pms_circuit_breaker_state == 1` | N/A | Notify on-call, investigate PMS |

### Warning Alerts (Notify, Investigate)

| Alert | Condition | Threshold | Action |
|-------|-----------|-----------|--------|
| **Elevated Error Rate** | `error_rate > X%` | 1% | Notify on-call, monitor, investigate |
| **High Latency** | `p95_latency > Xms` | 1500ms | Notify on-call, investigate slow queries |
| **Low Cache Hit Rate** | `cache_hit_rate < X%` | 50% | Notify ops, review cache strategy |
| **High CPU** | `cpu_usage > X%` | 80% | Notify ops, consider scaling |
| **High Memory** | `memory_used > X%` | 90% | Notify ops, investigate memory leak |
| **Disk Space Low** | `disk_used > X%` | 80% | Notify ops, plan cleanup |

### Info Alerts (Log, Review Later)

| Alert | Condition | Threshold | Action |
|-------|-----------|-----------|--------|
| **Low Traffic** | `request_rate < X` | 10 req/s | Log, may be normal (overnight) |
| **PMS Slow** | `pms_latency > Xms` | 1000ms | Log, discuss with PMS team |
| **Cache Miss** | `cache_hit_rate < X%` | 65% | Log, optimize cache TTL |

---

## Dashboards

### 1. Main Overview Dashboard
**URL**: `http://grafana/d/agente-hotel-overview`

**Panels**:
- **Top Row**: Request rate, Error rate, P95 latency (5-minute windows)
- **Middle Row**: CPU, Memory, Disk usage
- **Bottom Row**: Database connections, Redis hit rate, PMS health

**Use**: Primary dashboard for all checkpoints

---

### 2. Errors Dashboard
**URL**: `http://grafana/d/agente-hotel-errors`

**Panels**:
- **Error rate by endpoint**: Identify problematic endpoints
- **Error types**: 500 vs 502 vs 503 vs 504
- **Error logs**: Recent errors (last 50)
- **Error trends**: 24-hour error rate trend

**Use**: Investigating elevated error rates

---

### 3. Performance Dashboard
**URL**: `http://grafana/d/agente-hotel-performance`

**Panels**:
- **Latency distribution**: P50, P75, P95, P99
- **Latency by endpoint**: Identify slow endpoints
- **Database query performance**: Slow queries
- **PMS API latency**: External service performance

**Use**: Investigating high latency

---

### 4. Database Dashboard
**URL**: `http://grafana/d/postgres-dashboard`

**Panels**:
- **Connection pool**: Active, idle, waiting
- **Query performance**: P95 duration, slow queries
- **Database size**: Disk usage trend
- **Replication lag**: If using replication

**Use**: Database-specific monitoring

---

### 5. Business Metrics Dashboard
**URL**: `http://grafana/d/business-metrics`

**Panels**:
- **Messages processed**: Rate over time
- **Sessions created**: Active sessions
- **Reservations handled**: Success vs. failure
- **User engagement**: Active users, message types

**Use**: Validating business goals

---

### 6. Weekly Trends Dashboard
**URL**: `http://grafana/d/weekly-trends`

**Panels**:
- **7-day request rate**: Identify weekly patterns
- **7-day error rate**: Trend analysis
- **7-day latency**: Performance stability
- **Cost trends**: Infrastructure costs over time

**Use**: Week-1 and beyond monitoring

---

## Escalation Procedures

### Level 1: On-Call Engineer (Primary)
**Response Time**: 15 minutes  
**Authority**: Investigate, mitigate, escalate

**When to escalate to Level 2**:
- Unable to resolve within 30 minutes
- Issue requires database expertise
- Rollback decision needed
- Critical user impact

---

### Level 2: Backup Engineer + Database DBA
**Response Time**: 30 minutes  
**Authority**: Deep investigation, database changes, recommend rollback

**When to escalate to Level 3**:
- Rollback needed (requires commander approval)
- Multi-service outage
- Data integrity concerns
- Executive visibility required

---

### Level 3: Launch Commander + Engineering Lead
**Response Time**: 1 hour (or immediately if critical)  
**Authority**: Rollback decision, external communication, executive updates

**When to escalate to Level 4**:
- Complete outage >1 hour
- Data loss or breach
- Legal/compliance implications
- Press/public visibility

---

### Level 4: CTO + Executive Team
**Response Time**: 2 hours (or immediately for crisis)  
**Authority**: Final decisions, external communications, crisis management

---

### Escalation Contact List

| Level | Role | Name | Phone | Slack | Backup |
|-------|------|------|-------|-------|--------|
| L1 | On-Call | [Schedule] | PagerDuty | @oncall | [Backup] |
| L2 | Backup | [Name] | [Phone] | @backup | [Name] |
| L2 | DBA | [Name] | [Phone] | @dba | [Name] |
| L3 | Commander | [Name] | [Phone] | @commander | [Name] |
| L3 | Eng Lead | [Name] | [Phone] | @eng-lead | N/A |
| L4 | CTO | [Name] | [Phone] | @cto | N/A |

---

## Team Rotation

### Critical Phase (0-2h): All Hands
- Launch Commander: [Name]
- Deployment Engineer: [Name]
- Database Engineer: [Name]
- Monitoring Engineer: [Name]
- Communication Lead: [Name]

---

### High Intensity (2-24h): Shifts

**Shift 1: Morning (8am-4pm)**
- Primary On-Call: [Name]
- Backup: [Name]

**Shift 2: Evening (4pm-12am)**
- Primary On-Call: [Name]
- Backup: [Name]

**Shift 3: Overnight (12am-8am)**
- Primary On-Call: [Name]
- Backup: [Name]

---

### Medium Intensity (24-48h): Regular On-Call
- Standard on-call rotation
- Backup available if needed

---

### Standard Monitoring (48h+): Normal Operations
- Regular on-call rotation (1 week per engineer)

---

## Appendix

### A. Monitoring Checklist

**Critical Phase (0-2h)** - Every 5-15 minutes:
- [ ] Main dashboard green
- [ ] Error rate <0.1%
- [ ] Latency within SLAs
- [ ] No alerts firing
- [ ] Logs clean

**High Intensity (2-24h)** - Every 2 hours:
- [ ] Request rate normal
- [ ] Error rate <0.5%
- [ ] P95 latency <1s
- [ ] Database healthy
- [ ] Redis healthy
- [ ] PMS integration healthy
- [ ] No user issues
- [ ] Status posted to Slack

**Medium Intensity (24-48h)** - Every 4 hours:
- [ ] All above checks
- [ ] Resource usage stable
- [ ] No cost anomalies
- [ ] User feedback reviewed

---

### B. Quick Reference

**Dashboards**:
- Main: `http://grafana/d/agente-hotel-overview`
- Errors: `http://grafana/d/agente-hotel-errors`
- Performance: `http://grafana/d/agente-hotel-performance`

**Alert Manager**: `http://alertmanager:9093`

**Logs**: `docker compose logs -f --tail=100 agente-api`

**Emergency Rollback**: `docker compose rollback agente-api`

---

### C. Status Update Template

```
[EMOJI] T+[X]h Checkpoint

Status: 🟢 Healthy / 🟡 Investigating / 🔴 Issue
Request rate: [X] req/s (baseline: [Y] req/s)
Error rate: [X]% (target: <0.1%)
P95 latency: [X]ms (target: <1000ms)
Database: [Healthy / Warning / Critical]
Redis: [Healthy / Warning / Critical]
PMS: [Healthy / Warning / Critical]

Issues: [None / Description]
Actions: [None / Investigation / Mitigation]
Next check: T+[Y]h
```

---

**Document Owner**: Operations Team  
**Last Updated**: 2024-10-15  
**Next Review**: After launch  
**Version**: 1.0  
**Status**: Active
