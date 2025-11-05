# On-Call Guide

**Purpose**: Define on-call responsibilities, rotation, escalation, and handoff procedures for the Agente Hotelero IA system.

---

## Table of Contents

1. [On-Call Overview](#on-call-overview)
2. [On-Call Rotation](#on-call-rotation)
3. [Responsibilities](#responsibilities)
4. [Escalation Procedures](#escalation-procedures)
5. [Handoff Procedures](#handoff-procedures)
6. [Tools & Access](#tools--access)
7. [Common Scenarios](#common-scenarios)
8. [Compensation & Time Off](#compensation--time-off)

---

## On-Call Overview

### Purpose
On-call engineers are the first responders for production incidents, ensuring 24/7 coverage and rapid response to system issues.

### Coverage Model
- **Primary On-Call**: First responder, handles all alerts
- **Secondary On-Call**: Backup, escalation point for complex issues
- **Incident Commander**: Senior engineer, coordinates major incidents

### Rotation Schedule
- **Duration**: 1 week (Monday 9:00 AM to Monday 9:00 AM)
- **Handoff Time**: Monday 9:00 AM local time
- **Time Zones**: Coordinated across team locations
- **Advance Notice**: 2 weeks minimum

---

## On-Call Rotation

### Current Rotation (Example)

| Week | Primary | Secondary | Incident Commander |
|------|---------|-----------|-------------------|
| Nov 4-10 | @engineer1 | @engineer2 | @senior1 |
| Nov 11-17 | @engineer2 | @engineer3 | @senior2 |
| Nov 18-24 | @engineer3 | @engineer1 | @senior1 |
| Nov 25-Dec 1 | @engineer1 | @engineer2 | @senior2 |

### Eligibility
**Primary On-Call**:
- 6+ months with the team
- Completed incident response training
- Access to all production systems
- Familiar with runbooks and escalation procedures

**Secondary On-Call**:
- 1+ year with the team
- Deep system knowledge
- Experience with major incidents

**Incident Commander**:
- Senior engineer or team lead
- Crisis management experience
- Authority to make critical decisions

### Rotation Management
- **Schedule Tool**: PagerDuty / OpsGenie / Google Calendar
- **View Schedule**: [Link to schedule]
- **Request Swap**: Use #on-call Slack channel
- **Override**: Contact team lead

---

## Responsibilities

### Primary On-Call Engineer

#### During Business Hours (9 AM - 6 PM Local)
- ✅ Monitor #alerts Slack channel
- ✅ Respond to alerts within 15 minutes
- ✅ Investigate and resolve incidents
- ✅ Update incident status in Slack
- ✅ Escalate if needed
- ✅ Document incidents

#### After Hours & Weekends
- ✅ Respond to pages within 15 minutes
- ✅ Acknowledge alert in PagerDuty
- ✅ Assess severity immediately
- ✅ Engage secondary if needed
- ✅ Update status page for user-facing issues

#### All Times
- ✅ Keep phone on and charged
- ✅ Maintain internet access
- ✅ Be near computer during on-call hours
- ✅ Be sober and alert
- ✅ Communicate availability issues immediately

### Secondary On-Call Engineer

- ✅ Be available for escalation
- ✅ Respond to escalations within 30 minutes
- ✅ Provide guidance on complex issues
- ✅ Take over if primary is unavailable
- ✅ Coordinate with vendors if needed

### Incident Commander

- ✅ Coordinate major incidents (SEV1/SEV2)
- ✅ Make critical decisions
- ✅ Manage communication with stakeholders
- ✅ Ensure post-mortem completion
- ✅ Be available 24/7 during assigned week

---

## Escalation Procedures

### When to Escalate

**Escalate to Secondary** if:
- Issue is beyond your expertise
- Multiple services affected
- No progress after 30 minutes
- Database or infrastructure issue
- External vendor needed

**Escalate to Incident Commander** if:
- Severity 1 (Critical) incident
- Multiple teams needed
- Executive notification required
- Data loss or security breach
- Vendor escalation needed

**Escalate to Management** if:
- Major customer impact
- Extended outage (> 2 hours)
- Requires business decision
- Resource allocation needed
- Legal or compliance issue

### Escalation Contacts

```
Primary → Secondary → Incident Commander → Team Lead → Director

Emergency Escalation (Bypasses Chain):
- Security Breach: security@company.com
- Data Loss: data-protection@company.com  
- Legal Issue: legal@company.com
```

### Escalation Template

**Slack Message**:
```
@secondary-oncall ESCALATION NEEDED
Incident: [INC-ID]
Severity: [SEV1/SEV2]
Issue: [Brief description]
Progress: [What you've tried]
Need: [Specific help needed]
Status Page: [Link]
```

**Phone Call** (for urgent escalations):
```
"This is [Your Name], primary on-call engineer.
I need to escalate a Severity [X] incident affecting [System].
[Brief description of issue and current status]
I need [specific help]. Can you join the incident channel?"
```

---

## Handoff Procedures

### Pre-Handoff (Day Before)

**Outgoing Engineer**:
- ✅ Review open incidents
- ✅ Document ongoing issues
- ✅ Prepare handoff notes
- ✅ Update runbooks if needed
- ✅ Schedule handoff meeting

**Incoming Engineer**:
- ✅ Review handoff notes
- ✅ Test access to all systems
- ✅ Review recent incidents
- ✅ Prepare questions
- ✅ Ensure alert notifications enabled

### Handoff Meeting (Monday 9:00 AM)

**Agenda** (15-30 minutes):
1. **Open Incidents** (5 min)
   - Current status
   - Actions needed
   - Context and history

2. **Recent Incidents** (10 min)
   - Last week's major incidents
   - Lessons learned
   - Watch-outs

3. **System Status** (5 min)
   - Any degraded services
   - Ongoing maintenance
   - Expected changes

4. **Handoff Items** (5 min)
   - Pending tasks
   - Follow-ups needed
   - Escalation context

5. **Questions** (5 min)
   - Incoming engineer asks questions
   - Clarify ambiguities

### Handoff Template

```markdown
# On-Call Handoff: Week of [Date]

## Outgoing: @engineer1
## Incoming: @engineer2

### Open Incidents
- **INC-001**: Database slow queries
  - Status: Monitoring
  - Actions: Review performance at 2 PM
  - Contact: @dba-team

### Recent Incidents (Last Week)
- **INC-055**: Redis connection issues (Nov 5, 14:00)
  - Duration: 45 minutes
  - Resolution: Restarted Redis, increased connection pool
  - Follow-up: Monitor memory usage

- **INC-056**: High API latency (Nov 7, 22:30)
  - Duration: 2 hours
  - Resolution: Optimized slow PMS query
  - Follow-up: Deploy index creation on Wednesday

### System Status
- ✅ All services: Healthy
- ⚠️ PMS Integration: Slightly elevated latency (monitoring)
- ℹ️ Scheduled: Database backup at 3 AM daily

### Watch-Outs
- PMS API may be slow during peak hours (2-4 PM)
- Backup WhatsApp number configured (use if primary fails)
- Known issue: Redis memory usage trending up (review Friday)

### Pending Actions
- [ ] Review PMS cache hit rate trend
- [ ] Test backup WhatsApp number
- [ ] Verify new deployment validation tests

### Questions & Clarifications
[To be filled during handoff meeting]

### Handoff Confirmed
- Outgoing: @engineer1 - [Time]
- Incoming: @engineer2 - [Time]
```

### Post-Handoff

**Outgoing Engineer**:
- ✅ Disable alert notifications
- ✅ Update PagerDuty schedule
- ✅ Post handoff summary in #on-call channel
- ✅ Be available for questions (1-2 hours)

**Incoming Engineer**:
- ✅ Enable alert notifications
- ✅ Confirm PagerDuty assignment
- ✅ Post in #on-call: "I'm now on-call this week"
- ✅ Do a quick health check of all systems

---

## Tools & Access

### Required Access

**Monitoring & Alerts**:
- [ ] PagerDuty account configured
- [ ] Slack #alerts channel notifications enabled
- [ ] Grafana dashboards access
- [ ] Prometheus query access

**Production Systems**:
- [ ] SSH access to production servers
- [ ] Docker/Kubernetes access
- [ ] Database read/write access (with restrictions)
- [ ] Redis access

**External Services**:
- [ ] WhatsApp Business API access
- [ ] PMS (QloApps) admin access
- [ ] Gmail API credentials
- [ ] AWS/Cloud provider console

**Documentation**:
- [ ] Runbooks repository access
- [ ] Internal wiki/documentation
- [ ] Incident management system
- [ ] Post-mortem template

**Communication**:
- [ ] Slack workspace
- [ ] Status page admin (if updating customers)
- [ ] On-call phone number published

### Tool Quick Reference

```bash
# Check system health
make health

# View logs
make logs

# Check metrics
open http://localhost:3000/dashboards  # Grafana

# Run diagnostic
scripts/health-check.sh

# Incident detector
python scripts/incident-detector.py --report

# Rollback deployment
make rollback
```

### Emergency Contacts

| Role | Contact | When to Use |
|------|---------|-------------|
| Secondary On-Call | [Phone] | Escalation, complex issues |
| Incident Commander | [Phone] | SEV1/SEV2 incidents |
| Team Lead | [Phone] | Business decisions, resources |
| Database Admin | [Phone] | Database issues, data loss |
| Security Team | [Email] | Security incidents |
| Vendor Support | [Portal] | External service issues |

---

## Common Scenarios

### Scenario 1: Alert Fired at 2 AM

**Response**:
1. Wake up, grab phone/laptop (within 5 min)
2. Acknowledge alert in PagerDuty (within 15 min)
3. Check Grafana dashboard for context
4. Review runbook for alert type
5. Start incident response
6. Update #incidents Slack channel
7. Resolve or escalate
8. Document in incident tracker

### Scenario 2: Multiple Alerts Firing

**Response**:
1. Acknowledge all alerts
2. Identify if single root cause or multiple issues
3. Prioritize: User-facing > Internal
4. Address root cause first
5. Escalate to secondary if overwhelmed
6. Communicate status in Slack
7. Don't try to be a hero - escalate early

### Scenario 3: Unsure How to Proceed

**Response**:
1. Don't panic
2. Check runbook for scenario
3. Search incident history for similar issues
4. Ask in #engineering Slack channel
5. Escalate to secondary (don't wait > 30 min)
6. Document what you tried

### Scenario 4: Can't Acknowledge Alert

**Response**:
1. Notify secondary immediately (phone call)
2. Notify team lead
3. Secondary takes over
4. Fix notification issue during business hours

### Scenario 5: Major Incident During Dinner

**Response**:
1. Acknowledge alert immediately
2. Find a quiet place
3. Open laptop if available
4. Use phone for initial triage
5. Escalate to secondary if laptop unavailable
6. Communicate availability honestly
7. Don't let dinner get cold for non-critical issues

---

## Compensation & Time Off

### On-Call Compensation
- **Weekday On-Call**: [X hours/week] regular pay
- **Weekend On-Call**: [Y hours] regular pay
- **Incident Response**: Actual hours worked at 1.5x
- **Major Incident (> 4 hours)**: Comp day next week

### Time Off During On-Call
- **Planned Vacation**: Swap with teammate (2 weeks notice)
- **Sick Leave**: Notify secondary and team lead ASAP
- **Family Emergency**: Notify team lead, automatic swap

### Burnout Prevention
- **Max Consecutive Weeks**: 2 weeks
- **Break Between Rotations**: Minimum 2 weeks
- **Incident Limit**: If > 10 incidents in week, skip next rotation
- **Sleep Disruption**: Comp time for > 2 hours after midnight

### Opt-Out Policy
- On-call is **voluntary** (but expected for senior engineers)
- Can opt out with 1 month notice
- No impact on performance reviews
- Alternative contribution expected

---

## Best Practices

### Before Your Week
- ✅ Review recent incidents
- ✅ Test all access
- ✅ Read new runbooks
- ✅ Clear calendar for handoff
- ✅ Inform family you're on-call

### During Your Week
- ✅ Keep phone charged and near you
- ✅ Test alerts daily
- ✅ Review dashboards proactively
- ✅ Update runbooks as you learn
- ✅ Document all incidents

### After Your Week
- ✅ Complete all post-mortems
- ✅ Update runbooks
- ✅ Provide feedback on process
- ✅ Take a break!

### Mental Health
- On-call can be stressful
- It's okay to escalate
- It's okay to say "I don't know"
- Team supports you
- Talk to manager if feeling burned out

---

## Continuous Improvement

### After Each Rotation
- Update this guide with learnings
- Share feedback in retrospective
- Propose automation opportunities
- Suggest monitoring improvements

### Quarterly Review
- Review on-call metrics
- Analyze alert noise
- Update rotation if needed
- Adjust compensation if needed

---

**Document Owner**: @team-lead  
**Last Updated**: 2024-10-15  
**Next Review**: 2025-01-15  
**Feedback**: #on-call Slack channel
