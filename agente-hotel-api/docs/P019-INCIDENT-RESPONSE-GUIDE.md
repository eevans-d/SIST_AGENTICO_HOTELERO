# P019: Incident Response & Recovery Guide

**Version**: 1.0  
**Date**: 2024-10-15  
**Status**: Production Ready

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Incident Detection System](#incident-detection-system)
4. [Incident Response Runbooks](#incident-response-runbooks)
5. [Communication Procedures](#communication-procedures)
6. [On-Call Procedures](#on-call-procedures)
7. [Recovery Objectives (RTO/RPO)](#recovery-objectives-rtorpo)
8. [Post-Mortem Process](#post-mortem-process)
9. [Testing & Validation](#testing--validation)
10. [Continuous Improvement](#continuous-improvement)

---

## Executive Summary

### Purpose
This guide establishes comprehensive incident response and recovery procedures for the Agente Hotelero IA system, ensuring rapid detection, effective response, and minimal business impact during service disruptions.

### Key Capabilities
- **Automated Detection**: 10 incident detection rules with severity classification
- **Response Runbooks**: 10 detailed runbooks for common scenarios
- **Communication Templates**: Standardized stakeholder communication
- **Recovery Procedures**: Documented RTO/RPO targets and procedures
- **Post-Mortem Process**: Blameless learning and continuous improvement

### Business Impact
- **MTTR Reduction**: Target < 15 minutes for critical incidents
- **Data Protection**: RPO of 15 minutes ensures minimal data loss
- **Availability**: 99.9% uptime SLA supported by rapid response
- **Cost Savings**: Reduced incident duration saves $500/hour in lost revenue

---

## System Overview

### Service Tiers

| Tier | Services | RTO | RPO | Business Impact |
|------|----------|-----|-----|-----------------|
| **Tier 1 (Critical)** | API, Database | 1 hour | 15 min | Complete outage |
| **Tier 2 (High)** | Redis, PMS, WhatsApp | 4 hours | 1 hour | Degraded service |
| **Tier 3 (Medium)** | Monitoring | 24 hours | 24 hours | Reduced visibility |
| **Tier 4 (Low)** | Dev/Test | 1 week | 1 week | No production impact |

### Severity Levels

| Severity | Definition | Response Time | Update Frequency |
|----------|------------|---------------|------------------|
| **SEV1 (Critical)** | Complete outage | 15 minutes | Every 30 minutes |
| **SEV2 (High)** | Degraded service | 30 minutes | Every hour |
| **SEV3 (Medium)** | Minor issues | 1 hour | When status changes |
| **SEV4 (Low)** | Informational | Next business day | Weekly summary |

---

## Incident Detection System

### Overview
Automated incident detection system (`scripts/incident-detector.py`) continuously monitors Prometheus metrics and triggers alerts when thresholds are breached.

### Architecture
```
Prometheus → Incident Detector → Alert Classification → Notification
                    ↓
            Incident History
```

### Detection Rules

#### 1. Service Down (SEV1)
```yaml
Name: service_down
Query: up{job="agente-api"}
Threshold: < 1
Duration: 60 seconds
Description: Service is down or unreachable
```

#### 2. High Error Rate (SEV1)
```yaml
Name: high_error_rate
Query: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
Threshold: > 5%
Duration: 120 seconds
Description: Error rate exceeds acceptable limit
```

#### 3. Database Connection Failures (SEV2)
```yaml
Name: database_connection_failures
Query: rate(database_connection_errors_total[5m])
Threshold: > 1
Duration: 60 seconds
Description: Database connection failures detected
```

#### 4. High Latency P95 (SEV2)
```yaml
Name: high_latency_p95
Query: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
Threshold: > 3 seconds
Duration: 300 seconds
Description: P95 latency exceeds SLA
```

#### 5. High Memory Usage (SEV2)
```yaml
Name: high_memory_usage
Query: process_resident_memory_bytes / 1024 / 1024 / 1024
Threshold: > 2GB
Duration: 300 seconds
Description: Memory usage critical
```

#### 6. Redis Connection Issues (SEV3)
```yaml
Name: redis_connection_issues
Query: redis_up
Threshold: < 1
Duration: 120 seconds
Description: Redis unavailable
```

#### 7. PMS Circuit Breaker Open (SEV3)
```yaml
Name: pms_circuit_breaker_open
Query: pms_circuit_breaker_state
Threshold: = 1 (OPEN)
Duration: 180 seconds
Description: PMS integration protected
```

#### 8. High CPU Usage (SEV3)
```yaml
Name: high_cpu_usage
Query: rate(process_cpu_seconds_total[5m]) * 100
Threshold: > 80%
Duration: 300 seconds
Description: CPU usage critical
```

#### 9. Slow Response P50 (SEV4)
```yaml
Name: slow_response_p50
Query: histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))
Threshold: > 1 second
Duration: 600 seconds
Description: Median response time degraded
```

#### 10. Low Cache Hit Rate (SEV4)
```yaml
Name: low_cache_hit_rate
Query: rate(redis_cache_hits_total[5m]) / (rate(redis_cache_hits_total[5m]) + rate(redis_cache_misses_total[5m]))
Threshold: < 70%
Duration: 600 seconds
Description: Cache efficiency low
```

### Usage

```bash
# Run incident detector once
make incident-detect

# Generate incident report
make incident-report

# Monitor continuously
python scripts/incident-detector.py --interval 30
```

### Alert Integration
- **Slack Webhook**: Posts to #incidents channel
- **PagerDuty**: Escalates critical incidents
- **Email**: Sends to incident-response@company.com

---

## Incident Response Runbooks

### Available Runbooks

1. **Database Down** (`docs/runbooks/01-database-down.md`)
   - Severity: CRITICAL
   - RTO: 15 minutes
   - Covers: Connection failures, crashes, corruption

2. **High API Latency** (`docs/runbooks/02-high-api-latency.md`)
   - Severity: HIGH
   - RTO: 30 minutes
   - Covers: Slow queries, external API delays, resource exhaustion

3. **Memory Leak** (`docs/runbooks/03-memory-leak.md`)
   - Severity: HIGH
   - RTO: 1 hour
   - Covers: Continuous memory growth, OOM kills

4. **Disk Space Critical** (`docs/runbooks/04-disk-space-critical.md`)
   - Severity: CRITICAL
   - RTO: 15 minutes
   - Covers: Disk full, log growth, backup issues

5. **PMS Integration Failure** (`docs/runbooks/05-pms-integration-failure.md`)
   - Severity: HIGH
   - RTO: 30 minutes
   - Covers: API failures, authentication, rate limiting

6. **WhatsApp API Outage** (`docs/runbooks/06-whatsapp-api-outage.md`)
   - Severity: HIGH
   - RTO: 1 hour
   - Covers: Meta API issues, webhook failures, token expiration

7. **Redis Connection Issues** (`docs/runbooks/07-redis-connection-issues.md`)
   - Severity: MEDIUM
   - RTO: 30 minutes
   - Covers: Cache failures, connection pool exhaustion, OOM

8. **High Error Rate** (`docs/runbooks/08-high-error-rate.md`)
   - Severity: CRITICAL
   - RTO: 15 minutes
   - Covers: Multiple 5xx errors, code bugs, deployment issues

9. **Circuit Breaker Open** (`docs/runbooks/09-circuit-breaker-open.md`)
   - Severity: MEDIUM
   - RTO: 30 minutes
   - Covers: External service protection, recovery procedures

10. **Deployment Failure** (`docs/runbooks/10-deployment-failure.md`)
    - Severity: CRITICAL
    - RTO: 15 minutes (rollback)
    - Covers: Build failures, health check failures, rollback procedures

### Runbook Structure
Each runbook contains:
- **Symptoms**: How to recognize the issue
- **Detection**: Metrics and alerts
- **Impact Assessment**: Business and technical impact
- **Immediate Actions**: Steps to take in first 5-10 minutes
- **Investigation**: Diagnostic procedures
- **Resolution Steps**: Multiple resolution options
- **Validation**: How to verify resolution
- **Communication Templates**: Stakeholder messaging
- **Post-Incident**: Analysis and prevention

---

## Communication Procedures

### Communication Principles
1. **Transparency**: Honest about status
2. **Timeliness**: Update frequently
3. **Consistency**: Use templates
4. **Empathy**: Acknowledge impact
5. **Blameless**: Focus on resolution

### Stakeholder Matrix

**SEV1 (Critical)**:
- Engineering: Immediate
- Management: Within 15 min
- All Users: Status page within 15 min
- Enterprise Customers: Phone call within 30 min

**SEV2 (High)**:
- Engineering: Within 30 min
- Management: Within 2 hours
- Affected Users: Status page + Email

### Communication Channels
- **Internal**: Slack #incidents, Email threads
- **External**: Status page, Email, Phone (VIPs)
- **Social Media**: Major outages only (coordinate with marketing)

### Templates
See `docs/INCIDENT-COMMUNICATION.md` for complete templates:
- Initial Alert (Internal)
- Status Page Updates
- Email to Affected Users
- Management Updates
- Customer Call Scripts

### Timeline Requirements
| Milestone | SEV1 | SEV2 |
|-----------|------|------|
| Detection → Internal Alert | < 10 min | < 30 min |
| Detection → Status Page | < 15 min | < 30 min |
| Detection → Management | < 15 min | < 30 min |
| Update Frequency | Every 30 min | Every hour |
| Post-Resolution Communication | Within 2 hours | Within 4 hours |

---

## On-Call Procedures

### On-Call Roles
- **Primary On-Call**: First responder
- **Secondary On-Call**: Escalation point
- **Incident Commander**: Coordinates major incidents

### Rotation Schedule
- **Duration**: 1 week (Monday-Monday)
- **Handoff Time**: Monday 9:00 AM
- **Advance Notice**: 2 weeks minimum

### Responsibilities

**Primary On-Call**:
- Monitor #alerts channel
- Respond within 15 minutes
- Investigate and resolve
- Escalate if needed
- Document incidents

**Secondary On-Call**:
- Available for escalation
- Respond within 30 minutes
- Provide guidance
- Take over if primary unavailable

**Incident Commander**:
- Coordinate SEV1/SEV2 incidents
- Make critical decisions
- Manage stakeholder communication
- Ensure post-mortem completion

### Escalation Flow
```
Primary → Secondary → Incident Commander → Team Lead → Director
```

**Escalate Immediately For**:
- SEV1 incidents
- Beyond your expertise
- No progress after 30 minutes
- Data loss or security breach

### Handoff Procedure
1. **Pre-Handoff** (Day Before)
   - Review open incidents
   - Prepare handoff notes
   - Schedule meeting

2. **Handoff Meeting** (15-30 min)
   - Review open incidents
   - Discuss recent incidents
   - Share watch-outs
   - Answer questions

3. **Post-Handoff**
   - Disable/enable alert notifications
   - Update PagerDuty schedule
   - Post in #on-call channel

### See Full Guide
`docs/ON-CALL-GUIDE.md` for complete procedures, compensation, and best practices.

---

## Recovery Objectives (RTO/RPO)

### RTO (Recovery Time Objective)
**Definition**: Maximum acceptable time to restore service after outage.

### RPO (Recovery Point Objective)
**Definition**: Maximum acceptable amount of data loss (in time).

### Service Tier Objectives

| Service | RTO | RPO | Backup Strategy |
|---------|-----|-----|-----------------|
| **Database** | 1 hour | 15 min | Full daily + WAL continuous |
| **Application** | 1 hour | 0 min | Git + Docker images |
| **Redis Cache** | 4 hours | 1 hour | RDB hourly + AOF |
| **PMS Database** | 2 hours | 2 hours | Full daily + binlog every 2h |

### Backup Schedule

**Database (PostgreSQL)**:
```bash
# Full backup daily at 3:00 AM UTC
0 3 * * * /app/scripts/backup.sh full

# WAL archiving continuous (15-minute RPO)
archive_mode = on
archive_command = 'cp %p /var/lib/postgresql/wal_archive/%f'
```

**Redis**:
```bash
# RDB snapshot every hour
0 * * * * redis-cli BGSAVE

# AOF continuous
appendonly yes
appendfsync everysec
```

**Application Config**:
- Version controlled in Git
- Secrets backed up encrypted daily

### Recovery Procedures

#### Database Loss (RTO: 1 hour, RPO: 15 min)
1. Assess damage (5 min)
2. Prepare environment (10 min)
3. Restore latest backup (20 min)
4. Apply WAL archives (15 min)
5. Validate (10 min)

#### Complete Infrastructure Failure (RTO: 4 hours)
1. Activate DR plan (15 min)
2. Deploy infrastructure in DR region (60 min)
3. Restore database from off-site (90 min)
4. Deploy application (45 min)
5. Validate & switch traffic (30 min)

### Testing Schedule
- **Automated Validation**: Daily
- **Restore Test**: Weekly
- **Full DR Drill**: Monthly (Database), Quarterly (All Systems)

### See Full Procedures
`docs/RTO-RPO-PROCEDURES.md` for complete recovery procedures and disaster recovery plan.

---

## Post-Mortem Process

### Purpose
Learn from incidents in a **blameless** manner to prevent recurrence and improve systems.

### Timeline
- **Creation**: Within 24 hours of incident resolution
- **Meeting**: Within 48-72 hours
- **Publication**: Within 1 week

### Template
Use `templates/post-mortem-template.md` which includes:
- Executive Summary
- Timeline
- Impact Analysis
- Root Cause Analysis
- Resolution & Recovery
- Action Items (with owners and due dates)
- Lessons Learned
- Prevention Measures

### Creating Post-Mortem

```bash
# Use Makefile command
make post-mortem

# Prompts for:
# - Incident ID
# - Incident Title
# Creates: docs/post-mortems/INC-YYYYMMDD-XXX-title.md
```

### Post-Mortem Meeting
- **Duration**: 30-60 minutes
- **Attendees**: All responders + relevant stakeholders
- **Facilitator**: Incident Commander or Team Lead
- **Goal**: Understand what happened and how to prevent

### Action Items
- Create GitHub issues for all action items
- Assign owners and due dates
- Track to completion
- Review progress in team meetings

### Blameless Culture
- Focus on **systems**, not individuals
- Human error is a symptom, not a root cause
- Encourage honest discussion
- Learn and improve together
- No punishment for mistakes

---

## Testing & Validation

### Incident Response Tests
```bash
# Run test suite
make incident-test

# Simulates:
# - Incident detection
# - Rule evaluation
# - Alert triggering
# - Incident lifecycle
# - Runbook integration
```

### Test Coverage
- ✅ Rule threshold evaluation
- ✅ Incident creation
- ✅ Incident resolution
- ✅ Alert sending
- ✅ History persistence
- ✅ Report generation
- ✅ Runbook mapping
- ✅ Complete incident lifecycle

### Simulation Testing
```bash
# Simulate incident scenarios
make incident-simulate

# Available scenarios:
# 1. Database down
# 2. High latency
# 3. High error rate
# 4. Circuit breaker open
```

### Chaos Engineering
```bash
# Test system resilience
make chaos-database    # Database failures
make chaos-service     # Service crashes
make chaos-network     # Network issues
make chaos-pms         # PMS integration failures
```

### DR Drill Schedule
| Test Type | Frequency | Purpose |
|-----------|-----------|---------|
| Incident Simulation | Monthly | Test runbooks |
| Backup Validation | Weekly | Verify backups |
| Restore Test | Weekly | Test recovery |
| Full DR Drill | Quarterly | End-to-end validation |
| Chaos Test | Monthly | Resilience validation |

---

## Continuous Improvement

### Metrics to Track

**Incident Metrics**:
- MTTR (Mean Time To Recovery)
- MTTD (Mean Time To Detection)
- Incident frequency
- Incidents by severity
- Recurring incidents

**Process Metrics**:
- Runbook usage
- Escalation rate
- Communication delays
- Post-mortem completion rate
- Action item completion rate

**System Metrics**:
- Backup success rate
- Restore test success rate
- Alert accuracy (true vs. false positives)
- RTO/RPO adherence

### Monthly Review
- Review incident metrics
- Analyze patterns and trends
- Update runbooks based on learnings
- Review on-call feedback
- Assess training needs

### Quarterly Goals
- Reduce MTTR by 10%
- Increase runbook coverage
- Improve alert accuracy
- Complete all DR drills
- Update all documentation

### Feedback Loop
```
Incident → Response → Post-Mortem → Action Items → 
Process Improvement → Updated Runbooks → Better Response → Fewer Incidents
```

### Team Training
- **Monthly**: Runbook review session
- **Quarterly**: Incident simulation exercise
- **Bi-Annual**: DR drill with full team
- **Annual**: Incident response certification

---

## Quick Reference

### Incident Response Checklist
- [ ] Detect and acknowledge (< 15 min)
- [ ] Assess severity
- [ ] Post initial alert in #incidents
- [ ] Consult relevant runbook
- [ ] Execute immediate actions
- [ ] Communicate to stakeholders
- [ ] Investigate root cause
- [ ] Apply resolution
- [ ] Validate fix
- [ ] Monitor for stability
- [ ] Post resolution notice
- [ ] Create post-mortem
- [ ] Track action items

### Key Commands
```bash
# Detection & Monitoring
make incident-detect              # Run detector once
make incident-report              # Generate report
make on-call-schedule             # View rotation

# Testing
make incident-test                # Run test suite
make incident-simulate            # Simulate scenarios

# Documentation
make post-mortem                  # Create post-mortem
```

### Important Files
- **Runbooks**: `docs/runbooks/*.md`
- **Communication Guide**: `docs/INCIDENT-COMMUNICATION.md`
- **On-Call Guide**: `docs/ON-CALL-GUIDE.md`
- **RTO/RPO Procedures**: `docs/RTO-RPO-PROCEDURES.md`
- **Post-Mortem Template**: `templates/post-mortem-template.md`
- **Incident Detector**: `scripts/incident-detector.py`
- **Tests**: `tests/incident/test_incident_response.py`

### Support Contacts
- **Primary On-Call**: [Check #on-call]
- **Secondary On-Call**: [Check #on-call]
- **Incident Commander**: [Check schedule]
- **Team Lead**: [Contact info]
- **Emergency Escalation**: [Contact info]

---

## Appendix

### A. Incident Severity Matrix

| Severity | Response Time | Update Frequency | Escalation | Examples |
|----------|---------------|------------------|------------|----------|
| SEV1 | 15 min | 30 min | Automatic | Complete outage, data loss |
| SEV2 | 30 min | 1 hour | If > 2 hours | Degraded performance, partial outage |
| SEV3 | 1 hour | On change | If escalates | Minor bugs, isolated failures |
| SEV4 | Next day | Weekly | N/A | Informational, planned maintenance |

### B. Escalation Decision Tree

```
Incident Detected
    ↓
Is it SEV1? → Yes → Escalate immediately to IC
    ↓ No
Can you resolve in 30 min? → No → Escalate to Secondary
    ↓ Yes
Proceed with runbook
    ↓
Resolved? → Yes → Document & Close
    ↓ No (after 30 min)
Escalate to Secondary
```

### C. Communication Timing Chart

| Event | SEV1 | SEV2 | SEV3 |
|-------|------|------|------|
| Internal Alert | < 10 min | < 30 min | < 1 hour |
| Status Page | < 15 min | < 30 min | N/A |
| Management | < 15 min | < 30 min | Daily summary |
| Customer Email | < 30 min | Post-resolution | Post-resolution |
| Updates | Every 30 min | Every hour | On change |

---

**Document Owner**: SRE Team  
**Last Updated**: 2024-10-15  
**Next Review**: 2025-01-15  
**Version**: 1.0  
**Status**: Production Ready

---

## Feedback & Contributions

This is a living document. Please provide feedback and suggestions:
- **Slack**: #incidents or #sre channels
- **GitHub**: Open issue or PR
- **Email**: sre-team@company.com

**Recent Changes**:
- 2024-10-15: Initial release with 10 runbooks and complete procedures
